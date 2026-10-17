"""Leitor do relatório de comissões da Orbe (CSV com ';' e vírgula decimal).

Só lê e converte tipos: uma linha de saída por linha do arquivo, sem regra de negócio. ler_orbe_arquivos junta
vários arquivos no mesmo formato (relatório e ajustes tardios, O05); ler_orbe_parcial faz o mesmo, mas um arquivo
de ajustes com problema fica bloqueado sozinho e os outros são lidos (R44). Um id_transacao que reaparece num arquivo
posterior com dados diferentes é correção: a linha posterior substitui a anterior (P27) e volta em Correcao.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple

import pandas as pd

from tarvo.leitores.comum import data_br, dinheiro, num_br
from tarvo.leitores.layout import avisos_layout
from tarvo.leitores.rejeitadas import LinhaRejeitada

# Bytes conferidos: só ASCII, sem BOM. utf-8 explícito falha alto se vier byte fora do padrão.
ENCODING = "utf-8"

COLUNAS_ARQUIVO = [
    "id_transacao", "data_movimento", "cod_estabelecimento", "nome_estabelecimento",
    "tipo_lancamento", "modalidade", "qtd_parcelas", "bandeira", "valor_bruto",
    "taxa_aplicada_pct", "valor_taxa", "valor_liquido", "id_referencia", "data_venda_original",
]

COLUNAS_SAIDA = [
    "arquivo_origem", "ref_origem", "data_movimento", "cod_estabelecimento", "nome_estabelecimento",
    "tipo_lancamento", "modalidade", "qtd_parcelas", "bandeira", "valor_bruto", "taxa_aplicada_pct",
    "valor_taxa", "valor_liquido", "id_referencia", "data_venda_original",
]


def _vazio_none(s: str) -> str | None:
    return s if s.strip() else None


def _dinheiro_exato(s: str) -> Decimal:
    """Valor monetário do arquivo com 2 casas. Falha se vier vazio ou com mais de 2 casas (não arredonda a entrada)."""
    v = num_br(s)
    if v is None:
        raise ValueError("valor monetário vazio")
    q = dinheiro(v)
    if q != v:
        raise ValueError(f"valor monetário com mais de 2 casas: {s!r}")
    return q


def _obrigatorio(s: str, campo: str) -> str:
    if not s.strip():
        raise ValueError(f"{campo} vazio")
    return s


def _converter(linha: dict[str, str], arquivo_origem: str) -> dict:
    qtd = linha["qtd_parcelas"].strip()
    taxa = num_br(linha["taxa_aplicada_pct"])
    if taxa is None:
        raise ValueError("taxa_aplicada_pct vazia")
    return {
        "arquivo_origem": arquivo_origem,
        "ref_origem": _obrigatorio(linha["id_transacao"], "id_transacao").strip(),
        "data_movimento": data_br(_obrigatorio(linha["data_movimento"], "data_movimento")),
        "cod_estabelecimento": _obrigatorio(linha["cod_estabelecimento"], "cod_estabelecimento").strip(),
        "nome_estabelecimento": linha["nome_estabelecimento"],
        "tipo_lancamento": _obrigatorio(linha["tipo_lancamento"], "tipo_lancamento").strip(),
        "modalidade": _vazio_none(linha["modalidade"]),
        "qtd_parcelas": int(qtd) if qtd else None,
        "bandeira": _vazio_none(linha["bandeira"]),
        "valor_bruto": _dinheiro_exato(linha["valor_bruto"]),
        "taxa_aplicada_pct": taxa,
        "valor_taxa": _dinheiro_exato(linha["valor_taxa"]),
        "valor_liquido": _dinheiro_exato(linha["valor_liquido"]),
        "id_referencia": _vazio_none(linha["id_referencia"]),
        "data_venda_original": data_br(linha["data_venda_original"]),
    }


class ErroArquivoOrbe(ValueError):
    """Arquivo da Orbe que não pode ser lido. linha = linha física do problema (1 = cabeçalho)."""

    def __init__(self, mensagem: str, linha: int):
        super().__init__(mensagem)
        self.linha = linha


class Repetida(NamedTuple):
    """id_transacao que veio em dois arquivos da Orbe com a linha igual: contada uma vez só."""

    ref_origem: str
    arquivo_mantido: str
    linha_mantida: int
    arquivo_repetido: str
    linha_repetida: int


def _ler(caminho: Path, rejeitadas: list[LinhaRejeitada] | None = None) -> tuple[list[str], list[tuple[int, dict]]]:
    """Cabeçalho do arquivo e (linha física, registro convertido) de cada linha.

    Com rejeitadas, a linha com dado inválido vai para a lista e a leitura segue (R44); sem ela, é erro."""
    with open(caminho, encoding=ENCODING, newline="") as f:
        leitor = csv.DictReader(f, delimiter=";")
        cabecalho = list(leitor.fieldnames or [])
        faltando = [c for c in COLUNAS_ARQUIVO if c not in cabecalho]
        if faltando:
            raise ErroArquivoOrbe(f"{caminho.name}: colunas ausentes no cabeçalho: {faltando}", 1)
        registros = []
        for linha in leitor:
            n = leitor.line_num
            try:
                if None in linha or None in linha.values():
                    raise ValueError("número de campos diferente do cabeçalho")
                registros.append((n, _converter(linha, caminho.name)))
            except ValueError as e:
                mensagem = f"{caminho.name}, linha física {n}: {e}"
                if rejeitadas is None:
                    raise ErroArquivoOrbe(mensagem, n) from None
                rejeitadas.append(LinhaRejeitada(caminho.name, f"L{n}", mensagem,
                                                 ident=_texto_ou_none(linha.get("id_transacao")),
                                                 ec=_texto_ou_none(linha.get("cod_estabelecimento"))))
    return cabecalho, registros


def _texto_ou_none(v) -> str | None:
    return v.strip() or None if isinstance(v, str) else None


def _quadro(registros: list[dict]) -> pd.DataFrame:
    # dtype=object: mantém Decimal, date e None (sem virar float/NaN)
    return pd.DataFrame(registros, columns=COLUNAS_SAIDA, dtype=object)


def ler_orbe(caminho) -> pd.DataFrame:
    """Lê um CSV da Orbe. ref_origem = id_transacao; cod_estabelecimento fica str (preserva zeros)."""
    _, registros = _ler(Path(caminho))
    return _quadro([r for _, r in registros])


def _cabecalho_diferente(arquivo: str, cabecalho: list[str], referencia: str, esperado: list[str]) -> str:
    for i, (veio, deveria) in enumerate(zip(cabecalho, esperado), start=1):
        if veio != deveria:
            return (f"{arquivo}: cabeçalho diferente do de {referencia}: a coluna {i} é {veio!r}, "
                    f"no {referencia} é {deveria!r}")
    return (f"{arquivo}: cabeçalho diferente do de {referencia}: {len(cabecalho)} colunas, "
            f"o {referencia} tem {len(esperado)} (a diferença começa na coluna {min(len(cabecalho), len(esperado)) + 1})")


class Correcao(NamedTuple):
    """id_transacao que voltou num arquivo posterior com algum campo diferente: a linha posterior (a correção)
    substituiu a anterior no quadro (P27). antes e depois são os registros convertidos; campos, os que mudaram."""

    ref_origem: str
    arquivo_antes: str
    linha_antes: int
    antes: dict
    arquivo_depois: str
    linha_depois: int
    depois: dict
    campos: tuple[str, ...]


class ArquivoBloqueado(NamedTuple):
    """Arquivo de ajustes da Orbe que não entrou no fechamento (R44). origens: (arquivo, ref) de cada ponto citado."""

    arquivo: str
    erro: str
    origens: tuple[tuple[str, str], ...]
    linhas: int | None = None   # linhas de dados que ficaram de fora (None: o arquivo nem pôde ser lido)


@dataclass
class LeituraOrbe:
    quadro: pd.DataFrame
    repetidas: list[Repetida] = field(default_factory=list)
    bloqueados: list[ArquivoBloqueado] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    lidos: list[str] = field(default_factory=list)
    rejeitadas: list[LinhaRejeitada] = field(default_factory=list)  # linhas com dado inválido (R44)
    correcoes: list[Correcao] = field(default_factory=list)          # id corrigido num arquivo posterior (P27)
    linhas_lidas: dict[str, int] = field(default_factory=dict)       # arquivo -> linhas de dados convertidas


def _diferentes(antes: dict, depois: dict) -> tuple[str, ...]:
    """Campos do registro convertido que mudaram entre duas versões do mesmo id_transacao (fora o arquivo)."""
    return tuple(c for c in COLUNAS_SAIDA if c != "arquivo_origem" and antes[c] != depois[c])


def _linhas_de_dados(caminho: Path) -> int | None:
    """Linhas não vazias depois do cabeçalho, para dizer quanto ficou de fora; None se nem isso dá para ler."""
    try:
        with open(caminho, encoding=ENCODING, newline="") as f:
            return max(sum(1 for linha in f if linha.strip()) - 1, 0)
    except (OSError, UnicodeDecodeError):
        return None


def ler_orbe_parcial(caminhos) -> LeituraOrbe:
    """Lê os arquivos da Orbe do mês, em ordem de nome, bloqueando só o arquivo de ajustes com problema (R44).

    Linha com dado inválido fica de fora sozinha (LeituraOrbe.rejeitadas, R44).
    O primeiro arquivo (o relatório) é a referência: se o cabeçalho dele não serve, sobe ErroArquivoOrbe e a fonte
    inteira fica bloqueada. Um arquivo posterior fica bloqueado sozinho (nenhuma linha dele entra) quando não pode
    ser lido ou quando o cabeçalho é diferente do do primeiro; os demais são lidos. id de arquivo anterior repetido
    com a linha igual conta uma vez (Repetida); com algum campo diferente, a linha do arquivo posterior substitui a
    anterior, no lugar dela (Correcao), e o resto do arquivo é lido normalmente (P27).
    Coluna a mais ou fora de ordem no primeiro arquivo é aviso: a leitura é pelo nome.
    """
    if isinstance(caminhos, (str, Path)):
        caminhos = [caminhos]
    caminhos = sorted((Path(c) for c in caminhos), key=lambda p: p.name)
    if not caminhos:
        raise ValueError("nenhum arquivo da Orbe")
    referencia, esperado = caminhos[0].name, None
    leitura = LeituraOrbe(_quadro([]))
    vistos: dict[str, tuple[int, dict]] = {}
    registros: list[dict] = []
    posicao: dict[str, int] = {}  # id_transacao -> índice em registros da versão que vale
    for caminho in caminhos:
        rejeitadas: list[LinhaRejeitada] = []
        try:
            cabecalho, linhas = _ler(caminho, rejeitadas)
        except ErroArquivoOrbe as e:
            if esperado is None:
                raise
            leitura.bloqueados.append(ArquivoBloqueado(caminho.name, str(e), ((caminho.name, f"L{e.linha}"),),
                                                       _linhas_de_dados(caminho)))
            continue
        if esperado is None:
            esperado = cabecalho
            leitura.avisos += avisos_layout(caminho.name, cabecalho, COLUNAS_ARQUIVO)
        elif cabecalho != esperado:
            leitura.bloqueados.append(ArquivoBloqueado(
                caminho.name, _cabecalho_diferente(caminho.name, cabecalho, referencia, esperado),
                ((caminho.name, "L1"), (referencia, "L1")), len(linhas)))
            continue
        for n, r in linhas:
            ref = r["ref_origem"]
            anterior = vistos.get(ref)
            if anterior is None or anterior[1]["arquivo_origem"] == r["arquivo_origem"]:
                if anterior is None:
                    vistos[ref], posicao[ref] = (n, r), len(registros)
                registros.append(r)
                continue
            n_ant, ant = anterior
            campos = _diferentes(ant, r)
            if not campos:
                leitura.repetidas.append(Repetida(ref, ant["arquivo_origem"], n_ant, caminho.name, n))
                continue
            # P27: a linha do arquivo posterior é a correção e fica no lugar da anterior
            leitura.correcoes.append(Correcao(ref, ant["arquivo_origem"], n_ant, ant, caminho.name, n, r, campos))
            registros[posicao[ref]] = r
            vistos[ref] = (n, r)
        leitura.lidos.append(caminho.name)
        leitura.linhas_lidas[caminho.name] = len(linhas)
        leitura.rejeitadas += rejeitadas
    leitura.quadro = _quadro(registros)
    return leitura


def ler_orbe_arquivos(caminhos) -> tuple[pd.DataFrame, list[Repetida]]:
    """Lê todos os arquivos da Orbe do mês (relatório e ajustes, O05), em ordem de nome, num quadro só.

    Cada linha guarda o próprio arquivo_origem. O cabeçalho de cada arquivo tem de ser idêntico ao do primeiro.
    Um id_transacao que reaparece em outro arquivo com a linha igual conta uma vez (e volta em Repetida); com
    algum campo diferente, a linha do arquivo posterior substitui a anterior (P27; ler_orbe_parcial devolve a
    Correcao). Dentro do mesmo arquivo nada muda.
    Versão estrita de ler_orbe_parcial: o primeiro arquivo bloqueado ou a primeira linha inválida vira ValueError.
    """
    leitura = ler_orbe_parcial(caminhos)
    if leitura.bloqueados:
        raise ValueError(leitura.bloqueados[0].erro)
    if leitura.rejeitadas:
        raise ValueError(leitura.rejeitadas[0].erro)
    return leitura.quadro, leitura.repetidas
