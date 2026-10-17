"""Leitor do relatório de comissões da Orbe (CSV com ';' e vírgula decimal).

Só lê e converte tipos: uma linha de saída por linha do arquivo, sem regra de negócio. ler_orbe_arquivos junta
vários arquivos no mesmo formato (relatório e ajustes tardios, O05).
"""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple

import pandas as pd

from tarvo.leitores.comum import data_br, dinheiro, num_br

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


class Repetida(NamedTuple):
    """id_transacao que veio em dois arquivos da Orbe com a linha igual: contada uma vez só."""

    ref_origem: str
    arquivo_mantido: str
    linha_mantida: int
    arquivo_repetido: str
    linha_repetida: int


def _ler(caminho: Path) -> tuple[list[str], list[tuple[int, dict]]]:
    """Cabeçalho do arquivo e (linha física, registro convertido) de cada linha."""
    with open(caminho, encoding=ENCODING, newline="") as f:
        leitor = csv.DictReader(f, delimiter=";")
        cabecalho = list(leitor.fieldnames or [])
        faltando = [c for c in COLUNAS_ARQUIVO if c not in cabecalho]
        if faltando:
            raise ValueError(f"{caminho.name}: colunas ausentes no cabeçalho: {faltando}")
        registros = []
        for linha in leitor:
            if None in linha or None in linha.values():
                raise ValueError(f"{caminho.name}, linha física {leitor.line_num}: número de campos diferente do cabeçalho")
            try:
                registros.append((leitor.line_num, _converter(linha, caminho.name)))
            except ValueError as e:
                raise ValueError(f"{caminho.name}, linha física {leitor.line_num}: {e}") from None
    return cabecalho, registros


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


def ler_orbe_arquivos(caminhos) -> tuple[pd.DataFrame, list[Repetida]]:
    """Lê todos os arquivos da Orbe do mês (relatório e ajustes, O05), em ordem de nome, num quadro só.

    Cada linha guarda o próprio arquivo_origem. O cabeçalho de cada arquivo tem de ser idêntico ao do primeiro.
    Um id_transacao que reaparece em outro arquivo com a linha igual conta uma vez (e volta em Repetida); com
    qualquer campo diferente é erro: o leitor não escolhe qual vale. Dentro do mesmo arquivo nada muda.
    """
    if isinstance(caminhos, (str, Path)):
        caminhos = [caminhos]
    caminhos = sorted((Path(c) for c in caminhos), key=lambda p: p.name)
    if not caminhos:
        raise ValueError("nenhum arquivo da Orbe")
    referencia, esperado = caminhos[0].name, None
    vistos: dict[str, tuple[int, dict]] = {}
    registros: list[dict] = []
    repetidas: list[Repetida] = []
    for caminho in caminhos:
        cabecalho, linhas = _ler(caminho)
        if esperado is None:
            esperado = cabecalho
        elif cabecalho != esperado:
            raise ValueError(_cabecalho_diferente(caminho.name, cabecalho, referencia, esperado))
        for n, r in linhas:
            anterior = vistos.get(r["ref_origem"])
            if anterior is None or anterior[1]["arquivo_origem"] == r["arquivo_origem"]:
                vistos.setdefault(r["ref_origem"], (n, r))
                registros.append(r)
                continue
            n_ant, ant = anterior
            diferentes = [c for c in COLUNAS_SAIDA if c != "arquivo_origem" and ant[c] != r[c]]
            if diferentes:
                raise ValueError(
                    f"id_transacao {r['ref_origem']} aparece em {ant['arquivo_origem']} (linha física {n_ant}) e em "
                    f"{caminho.name} (linha física {n}) com valores diferentes em {', '.join(diferentes)}. O fechamento "
                    "não escolhe qual vale: peça à Orbe a versão correta e deixe na pasta só os arquivos certos.")
            repetidas.append(Repetida(r["ref_origem"], ant["arquivo_origem"], n_ant, caminho.name, n))
    return _quadro(registros), repetidas
