"""Orquestra o fechamento: lê as entradas, junta os itens dos módulos registrados, grava e valida a saída.

Fechamento parcial (R44): uma fonte ausente, ambígua ou ilegível fica bloqueada; o que depende dela não é gerado
(mapa em tarvo.dependencias) e o resto fecha normalmente, com uma pendência PEN-BLOQUEIO por fonte. Um dado que
impede a regra de um item (linha ilegível, cadastro ou contrato inconsistente) tira só o item: PEN-REGRA.
Erro de programa continua parando: a leitura só trata ValueError (dado) e OSError (arquivo).
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd

from tarvo import auditoria as registro_execucao
from tarvo import dependencias as dep
from tarvo.bancos import bancos
from tarvo.checkout import checkout
from tarvo.cli import (AMBIGUA, CONFIG_PADRAO, arquivos_ignorados, carregar_padroes, localizar_tolerante_pela_config,
                       o_que_fazer_ambigua)
from tarvo.contestacao import carregar_config as carregar_config_contestacao
from tarvo.contestacao import gerar_contestacoes, pasta_padrao
from tarvo.leitores.aurora import ler_aurora
from tarvo.leitores.meridiano import ler_meridiano
from tarvo.leitores.orbe import Correcao, ErroArquivoOrbe, LeituraOrbe, Repetida, ler_orbe_parcial
from tarvo.leitores.plano_contas import ler_plano
from tarvo.leitores.ponte import ler_ponte
from tarvo.leitores.rejeitadas import LinhaRejeitada
from tarvo.leitores.taxas import ler_taxas
from tarvo.remessa import remessa
from tarvo.saida import ItemSaida, gravar_saida, validar_saida

RE_COMPETENCIA = re.compile(r"[0-9]{4}-(0[1-9]|1[0-2])")
PREFIXO_PREPARO = ".tarvo-fechamento-"  # pasta temporária ao lado da saída, apagada ao fim de toda execução


@dataclass(frozen=True)
class Entradas:
    """Tudo o que os leitores devolveram, entregue a cada módulo. Fonte bloqueada vem como None (R44)."""

    competencia: str
    arquivos: dict[str, Path]       # arquivos localizados (inclusive os que não puderam ser lidos)
    orbe: pd.DataFrame | None
    taxas: pd.DataFrame | None
    ponte: pd.DataFrame | None
    ponte_rodape: dict | None
    plano_contas: pd.DataFrame | None
    aurora: pd.DataFrame | None
    aurora_meta: dict | None
    meridiano: pd.DataFrame | None
    meridiano_meta: dict | None
    usar_ia: bool = True  # opção da execução: False com --sem-ia (fallback de IA dos extratos, P14)
    orbe_repetidas: tuple[Repetida, ...] = ()  # id_transacao igual em dois arquivos da Orbe, contado uma vez (P27)
    orbe_correcoes: tuple[Correcao, ...] = ()  # id_transacao corrigido num arquivo posterior da Orbe (P27)
    orbe_linhas_lidas: dict[str, int] = field(default_factory=dict)  # arquivo da Orbe -> linhas convertidas
    bloqueios: tuple[dep.Bloqueio, ...] = ()   # fontes (ou arquivos da Orbe) que não entraram (R44)
    avisos: tuple[dep.Aviso, ...] = ()         # coluna a mais ou fora de ordem; a leitura seguiu pelo nome (R44)
    # linhas que o leitor não converteu, por fonte (R44): ficam fora e viram PEN-REGRA-LINHA
    rejeitadas: dict[str, tuple[LinhaRejeitada, ...]] = field(default_factory=dict)


Modulo = Callable[[Entradas], Iterable[ItemSaida]]

# Módulos que geram itens de saída. Cada um recebe as Entradas e devolve ItemSaida.
MODULOS: list[Modulo] = [checkout, remessa, bancos]


class ErroFechamento(Exception):
    """A saída gravada não passou em validar_saida."""

    def __init__(self, problemas: list[str]):
        self.problemas = list(problemas)
        super().__init__("\n".join(self.problemas))


@dataclass(frozen=True)
class ResultadoFechamento:
    arquivos_entrada: dict[str, Path]
    arquivos_saida: dict[str, Path]
    itens: int
    arquivos_contestacao: dict[str, Path] = field(default_factory=dict)  # R29; vazio com contestacoes=False
    arquivos_ignorados: list[tuple[Path, str]] = field(default_factory=list)  # na entrada, não lidos (só aviso)
    bloqueios: tuple[dep.Bloqueio, ...] = ()   # R44: fontes bloqueadas
    avisos: tuple[str, ...] = ()               # R44: diferenças de layout que não bloquearam
    regras: tuple[str, ...] = ()               # R44: pendências PEN-REGRA (itens fora por erro de dado)
    arquivos_auditoria: dict[str, Path] = field(default_factory=dict)  # O06: registro da execução; vazio com False

    @property
    def completo(self) -> bool:
        return not self.bloqueios and not self.regras

    def quadro(self) -> str:
        return dep.quadro(self.bloqueios, self.regras)


def _erro(e: Exception) -> str:
    texto = " ".join(str(e).split())
    return texto if isinstance(e, ValueError) and texto else f"{type(e).__name__}: {texto}"


# Leitor de cada tipo de arquivo único: (caminho, avisos de layout, linhas rejeitadas) -> o que o leitor devolve.
LEITORES = {
    "taxas": ler_taxas,
    "ponte_eml": ler_ponte,
    # plano de contas: a linha ilegível bloqueia o plano (a conta dela pode ser a de uma regra de config/bancos.yaml)
    "plano_de_contas": lambda caminho, avisos, _rejeitadas: ler_plano(caminho, avisos),
    "aurora": ler_aurora,
    "meridiano": lambda caminho, _avisos, rejeitadas: ler_meridiano(caminho, rejeitadas),  # OFX: sem colunas
}
ERROS_DE_LEITURA = (ValueError, OSError)  # dado inválido (inclui encoding) e arquivo; o resto é erro de programa


def _ler(fonte: str, arquivo: Path, leitor, bloqueios: list, avisos: list, rejeitadas: dict):
    """Roda o leitor da fonte. Erro de leitura do arquivo bloqueia a fonte (ILEGIVEL) e devolve None; linha com
    dado inválido fica de fora sozinha (rejeitadas)."""
    textos: list[str] = []
    linhas: list[LinhaRejeitada] = []
    try:
        resultado = leitor(arquivo, textos, linhas)
    except ERROS_DE_LEITURA as e:
        bloqueios.append(dep.Bloqueio(fonte, dep.ILEGIVEL, _erro(e), ((arquivo.name, "arquivo"),),
                                      dep.PASSO[dep.ILEGIVEL].format(fonte=fonte)))
        return None
    avisos += [dep.Aviso(fonte, arquivo.name, t) for t in textos]
    if linhas:
        rejeitadas[fonte] = tuple(linhas)
    return resultado


def _ler_orbe(arquivos: tuple[Path, ...], bloqueios: list, avisos: list, rejeitadas: dict) -> LeituraOrbe | None:
    """Relatório e ajustes da Orbe (O05). Arquivo de ajustes com problema fica bloqueado sozinho, e linha com dado
    inválido fica de fora sozinha (R44); id corrigido num arquivo posterior vale pela correção (P27)."""
    try:
        leitura = ler_orbe_parcial(arquivos)
    except ERROS_DE_LEITURA as e:  # o relatório (primeiro arquivo) ilegível bloqueia a fonte inteira
        linha = f"L{e.linha}" if isinstance(e, ErroArquivoOrbe) else "arquivo"
        bloqueios.append(dep.Bloqueio("orbe", dep.ILEGIVEL, _erro(e), ((arquivos[0].name, linha),),
                                      dep.PASSO[dep.ILEGIVEL].format(fonte="orbe")))
        return None
    for b in leitura.bloqueados:
        bloqueios.append(dep.Bloqueio("orbe", dep.ILEGIVEL, b.erro, b.origens, dep.PASSO_ORBE_LAYOUT,
                                      arquivo=b.arquivo, linhas=b.linhas))
    avisos += [dep.Aviso("orbe", arquivos[0].name, t) for t in leitura.avisos]
    if leitura.rejeitadas:
        rejeitadas["orbe"] = tuple(leitura.rejeitadas)
    return leitura


def ler_entradas(entrada, competencia: str, config=CONFIG_PADRAO, usar_ia: bool = True) -> Entradas:
    """Localiza e lê cada fonte. Fonte ausente, ambígua ou ilegível vem como None, com o Bloqueio (R44)."""
    arquivos, problemas = localizar_tolerante_pela_config(entrada, config)
    bloqueios: list[dep.Bloqueio] = []
    avisos: list[dep.Aviso] = []
    for tipo, p in problemas.items():
        if p.natureza == AMBIGUA:
            erro = f"{len(p.candidatos)} arquivos casam com o padrão '{p.padrao}': {', '.join(p.candidatos)}"
            bloqueios.append(dep.Bloqueio(tipo, dep.AMBIGUA, erro, tuple((c, "arquivo") for c in p.candidatos),
                                          o_que_fazer_ambigua(tipo) + " (o fechamento não escolhe um deles sozinho)"))
        else:
            erro = (f"nenhum arquivo casa com o padrão '{p.padrao}' (arquivos da pasta que não casam com nenhum "
                    f"padrão: {', '.join(p.candidatos) or 'nenhum'})")
            bloqueios.append(dep.Bloqueio(tipo, dep.AUSENTE, erro, ((p.padrao, "nenhum arquivo"),),
                                          dep.PASSO[dep.AUSENTE].format(fonte=tipo, padrao=p.padrao)))

    rejeitadas: dict[str, tuple[LinhaRejeitada, ...]] = {}
    leitura_orbe = _ler_orbe(arquivos["orbe"], bloqueios, avisos, rejeitadas) if "orbe" in arquivos else None
    lidos = {tipo: _ler(tipo, arquivos[tipo], leitor, bloqueios, avisos, rejeitadas) if tipo in arquivos else None
             for tipo, leitor in LEITORES.items()}
    taxas, ponte, plano, aurora, meridiano = (lidos[t] for t in LEITORES)
    ordem = {tipo: i for i, tipo in enumerate(carregar_padroes(Path(config)))}
    return Entradas(
        competencia=competencia,
        arquivos=arquivos,
        orbe=leitura_orbe.quadro if leitura_orbe else None,
        taxas=taxas,
        ponte=ponte[0] if ponte else None,
        ponte_rodape=ponte[1] if ponte else None,
        plano_contas=plano,
        aurora=aurora[0] if aurora else None,
        aurora_meta=aurora[1] if aurora else None,
        meridiano=meridiano[0] if meridiano else None,
        meridiano_meta=meridiano[1] if meridiano else None,
        usar_ia=usar_ia,
        orbe_repetidas=tuple(leitura_orbe.repetidas) if leitura_orbe else (),
        orbe_correcoes=tuple(leitura_orbe.correcoes) if leitura_orbe else (),
        orbe_linhas_lidas=dict(leitura_orbe.linhas_lidas) if leitura_orbe else {},
        bloqueios=tuple(sorted(bloqueios, key=lambda b: (ordem.get(b.fonte, len(ordem)), b.arquivo or ""))),
        avisos=tuple(avisos),
        rejeitadas=rejeitadas,
    )


def _publicar(preparados: dict[str, Path], destino: Path) -> dict[str, Path]:
    """Põe cada arquivo preparado no destino, por cima do anterior (os.replace: troca atômica por arquivo)."""
    destino.mkdir(parents=True, exist_ok=True)
    publicados = {}
    for nome, origem in preparados.items():
        alvo = destino / nome
        try:
            os.replace(origem, alvo)
        except OSError:  # outra unidade de disco: os.replace não atravessa volumes
            shutil.copyfile(origem, alvo)
        publicados[nome] = alvo
    return publicados


def comando_equivalente(entrada, saida, competencia: str, config, usar_ia: bool, contestacoes) -> str:
    """A linha de comando da CLI que refaz esta execução (para o registro de execução, O06)."""
    rel = registro_execucao.caminho_relativo  # caminhos relativos à raiz do repositório (o registro é público)
    partes = ["python -m tarvo fechar", f"--competencia {competencia}", f'--entrada "{rel(entrada)}"',
              f'--saida "{rel(saida)}"']
    if Path(config).resolve() != Path(CONFIG_PADRAO).resolve():
        partes.append(f'--config "{rel(config)}"')
    if not usar_ia:
        partes.append("--sem-ia")
    if contestacoes is False:
        partes.append("--sem-contestacao")
    elif contestacoes:
        partes.append(f"(rascunhos de contestação em {rel(contestacoes)}: só pela função fechar)")
    return " ".join(partes)


def fechar(entrada, saida, competencia: str, *, config=CONFIG_PADRAO,
           modulos: Iterable[Modulo] | None = None, usar_ia: bool = True,
           contestacoes: Path | str | bool | None = None,
           auditoria: Path | str | bool | None = None) -> ResultadoFechamento:
    """Lê as entradas, roda os módulos, valida os 6 CSVs e só então os grava em saida.

    Fonte bloqueada não para o fechamento (R44): o resultado traz os bloqueios, e a saída, as PEN-BLOQUEIO.

    Tudo é gravado antes numa pasta temporária ao lado de saida e validado lá (validar_saida). Se a validação
    falhar (ErroFechamento) ou qualquer passo der erro, saida e a pasta de contestações ficam como estavam.
    usar_ia=False força o fluxo sem IA nos extratos (P09 em vez de P14).
    Os rascunhos de contestação (R29) vão para uma pasta irmã de saida (config/contestacao.yaml);
    contestacoes=<pasta> escolhe outra, contestacoes=False não grava.
    O registro da execução (O06: execucao.json e execucao.md) vai para outra pasta irmã (config/auditoria.yaml),
    publicado junto com a saída; auditoria=<pasta> escolhe outra, auditoria=False não grava.
    """
    if not isinstance(competencia, str) or not RE_COMPETENCIA.fullmatch(competencia):
        raise ValueError(f"competência deve ser AAAA-MM, veio {competencia!r}")
    entradas = ler_entradas(entrada, competencia, config, usar_ia)
    ignorados = arquivos_ignorados(Path(entrada), carregar_padroes(Path(config)))
    comando = comando_equivalente(entrada, saida, competencia, config, usar_ia, contestacoes)
    itens: list[ItemSaida] = []
    for modulo in MODULOS if modulos is None else modulos:  # cada módulo gera só os produtos com as fontes dele
        itens.extend(modulo(entradas))
    itens += dep.pendencias_bloqueio(entradas) + dep.pendencias_rejeitadas(entradas) + dep.pendencias_aviso(entradas)

    saida = Path(saida).resolve()
    saida.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=PREFIXO_PREPARO, dir=saida.parent) as preparo:
        preparo = Path(preparo)
        preparados = gravar_saida(preparo / "saida", itens)
        problemas = validar_saida(preparo / "saida")
        if problemas:
            raise ErroFechamento(problemas)
        rascunhos_preparados, destino_contestacoes = {}, None
        if contestacoes is not False:
            cfg = carregar_config_contestacao()
            destino_contestacoes = Path(contestacoes or pasta_padrao(saida, cfg)).resolve()
            rascunhos_preparados = gerar_contestacoes(itens, entradas, preparo / "contestacoes", cfg)
        regras = tuple(dep.regras(itens))
        registro_preparado, destino_auditoria = {}, None
        if auditoria is not False:  # O06: descreve os arquivos já validados, antes de publicar
            destino_auditoria = Path(auditoria or registro_execucao.pasta_padrao(
                saida, registro_execucao.carregar_config())).resolve()
            registro = registro_execucao.registro(
                entradas, Path(entrada).resolve(), saida, comando, preparo / "saida", rascunhos_preparados,
                destino_contestacoes, ignorados, not entradas.bloqueios and not regras, regras)
            registro_preparado = registro_execucao.gravar(registro, preparo / "auditoria")
        gravados = _publicar(preparados, saida)
        rascunhos = _publicar(rascunhos_preparados, destino_contestacoes) if destino_contestacoes else {}
        registros = _publicar(registro_preparado, destino_auditoria) if destino_auditoria else {}
    return ResultadoFechamento(entradas.arquivos, gravados, len(itens), rascunhos, ignorados, entradas.bloqueios,
                               tuple(a.texto for a in entradas.avisos), regras, registros)
