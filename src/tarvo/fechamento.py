"""Orquestra o fechamento: lê as entradas, junta os itens dos módulos registrados, grava e valida a saída.

Fechamento parcial (R44): uma fonte ausente, ambígua ou ilegível fica bloqueada; o que depende dela não é gerado
(mapa em tarvo.dependencias) e o resto fecha normalmente, com uma pendência PEN-BLOQUEIO por fonte.
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

from tarvo import dependencias as dep
from tarvo.bancos import bancos
from tarvo.checkout import checkout
from tarvo.cli import (AMBIGUA, CONFIG_PADRAO, arquivos_ignorados, carregar_padroes, localizar_tolerante_pela_config,
                       o_que_fazer_ambigua)
from tarvo.contestacao import carregar_config as carregar_config_contestacao
from tarvo.contestacao import gerar_contestacoes, pasta_padrao
from tarvo.leitores.aurora import ler_aurora
from tarvo.leitores.meridiano import ler_meridiano
from tarvo.leitores.orbe import FIM_CONFLITO, ErroArquivoOrbe, Repetida, ler_orbe_parcial
from tarvo.leitores.plano_contas import ler_plano
from tarvo.leitores.ponte import ler_ponte
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
    bloqueios: tuple[dep.Bloqueio, ...] = ()   # fontes (ou arquivos da Orbe) que não entraram (R44)
    avisos: tuple[dep.Aviso, ...] = ()         # coluna a mais ou fora de ordem; a leitura seguiu pelo nome (R44)


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
    bloqueios: tuple[dep.Bloqueio, ...] = ()   # R44: vazio = fechamento completo
    avisos: tuple[str, ...] = ()               # R44: diferenças de layout que não bloquearam

    @property
    def completo(self) -> bool:
        return not self.bloqueios

    def quadro(self) -> str:
        return dep.quadro(self.bloqueios)


def _erro(e: Exception) -> str:
    texto = " ".join(str(e).split())
    return texto if isinstance(e, ValueError) and texto else f"{type(e).__name__}: {texto}"


# Leitor de cada tipo de arquivo único: (caminho, lista de avisos de layout) -> o que o leitor devolve.
LEITORES = {
    "taxas": ler_taxas,
    "ponte_eml": ler_ponte,
    "plano_de_contas": ler_plano,
    "aurora": ler_aurora,
    "meridiano": lambda caminho, _avisos: ler_meridiano(caminho),  # OFX: tags, sem cabeçalho de colunas
}


def _ler(fonte: str, arquivo: Path, leitor, bloqueios: list, avisos: list):
    """Roda o leitor da fonte; qualquer erro de leitura bloqueia a fonte (ILEGIVEL) e devolve None."""
    textos: list[str] = []
    try:
        resultado = leitor(arquivo, textos)
    except Exception as e:  # noqa: BLE001 - xlsx corrompido, e-mail sem anexo, encoding: tudo é arquivo ilegível
        bloqueios.append(dep.Bloqueio(fonte, dep.ILEGIVEL, _erro(e), ((arquivo.name, "arquivo"),),
                                      dep.PASSO[dep.ILEGIVEL].format(fonte=fonte)))
        return None
    avisos += [dep.Aviso(fonte, arquivo.name, t) for t in textos]
    return resultado


def _ler_orbe(arquivos: tuple[Path, ...], bloqueios: list, avisos: list):
    """Relatório e ajustes da Orbe (O05). Arquivo de ajustes com problema fica bloqueado sozinho (R44)."""
    try:
        leitura = ler_orbe_parcial(arquivos)
    except Exception as e:  # noqa: BLE001 - o relatório (primeiro arquivo) ilegível bloqueia a fonte inteira
        linha = f"L{e.linha}" if isinstance(e, ErroArquivoOrbe) else "arquivo"
        bloqueios.append(dep.Bloqueio("orbe", dep.ILEGIVEL, _erro(e), ((arquivos[0].name, linha),),
                                      dep.PASSO[dep.ILEGIVEL].format(fonte="orbe")))
        return None, ()
    for b in leitura.bloqueados:
        conflito = b.erro.endswith(FIM_CONFLITO)  # id repetido com dados diferentes: a pendência cita os ids
        bloqueios.append(dep.Bloqueio(
            "orbe", dep.ILEGIVEL, b.erro, b.origens, dep.PASSO_ORBE_CONFLITO if conflito else dep.PASSO_ORBE_LAYOUT,
            arquivo=b.arquivo, linhas=b.linhas, refs=tuple(dict.fromkeys(r for _, r in b.origens)) if conflito else ()))
    avisos += [dep.Aviso("orbe", arquivos[0].name, t) for t in leitura.avisos]
    return leitura.quadro, tuple(leitura.repetidas)


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

    orbe, repetidas = _ler_orbe(arquivos["orbe"], bloqueios, avisos) if "orbe" in arquivos else (None, ())
    lidos = {tipo: _ler(tipo, arquivos[tipo], leitor, bloqueios, avisos) if tipo in arquivos else None
             for tipo, leitor in LEITORES.items()}
    taxas, ponte, plano, aurora, meridiano = (lidos[t] for t in LEITORES)
    ordem = {tipo: i for i, tipo in enumerate(carregar_padroes(Path(config)))}
    return Entradas(
        competencia=competencia,
        arquivos=arquivos,
        orbe=orbe,
        taxas=taxas,
        ponte=ponte[0] if ponte else None,
        ponte_rodape=ponte[1] if ponte else None,
        plano_contas=plano,
        aurora=aurora[0] if aurora else None,
        aurora_meta=aurora[1] if aurora else None,
        meridiano=meridiano[0] if meridiano else None,
        meridiano_meta=meridiano[1] if meridiano else None,
        usar_ia=usar_ia,
        orbe_repetidas=repetidas,
        bloqueios=tuple(sorted(bloqueios, key=lambda b: (ordem.get(b.fonte, len(ordem)), b.arquivo or ""))),
        avisos=tuple(avisos),
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


def fechar(entrada, saida, competencia: str, *, config=CONFIG_PADRAO,
           modulos: Iterable[Modulo] | None = None, usar_ia: bool = True,
           contestacoes: Path | str | bool | None = None) -> ResultadoFechamento:
    """Lê as entradas, roda os módulos, valida os 6 CSVs e só então os grava em saida.

    Fonte bloqueada não para o fechamento (R44): o resultado traz os bloqueios, e a saída, as PEN-BLOQUEIO.

    Tudo é gravado antes numa pasta temporária ao lado de saida e validado lá (validar_saida). Se a validação
    falhar (ErroFechamento) ou qualquer passo der erro, saida e a pasta de contestações ficam como estavam.
    usar_ia=False força o fluxo sem IA nos extratos (P09 em vez de P14).
    Os rascunhos de contestação (R29) vão para uma pasta irmã de saida (config/contestacao.yaml);
    contestacoes=<pasta> escolhe outra, contestacoes=False não grava.
    """
    if not isinstance(competencia, str) or not RE_COMPETENCIA.fullmatch(competencia):
        raise ValueError(f"competência deve ser AAAA-MM, veio {competencia!r}")
    entradas = ler_entradas(entrada, competencia, config, usar_ia)
    ignorados = arquivos_ignorados(Path(entrada), carregar_padroes(Path(config)))
    itens: list[ItemSaida] = []
    for modulo in MODULOS if modulos is None else modulos:  # cada módulo gera só os produtos com as fontes dele
        itens.extend(modulo(entradas))
    itens += dep.pendencias_bloqueio(entradas) + dep.pendencias_aviso(entradas)  # R44

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
        gravados = _publicar(preparados, saida)
        rascunhos = _publicar(rascunhos_preparados, destino_contestacoes) if destino_contestacoes else {}
    return ResultadoFechamento(entradas.arquivos, gravados, len(itens), rascunhos, ignorados, entradas.bloqueios,
                               tuple(a.texto for a in entradas.avisos))
