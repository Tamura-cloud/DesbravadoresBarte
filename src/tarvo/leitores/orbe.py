"""Leitor do relatório de comissões da Orbe (CSV com ';' e vírgula decimal).

Só lê e converte tipos: uma linha de saída por linha do arquivo, sem regra de negócio.
"""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

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


def ler_orbe(caminho) -> pd.DataFrame:
    """Lê o CSV da Orbe. ref_origem = id_transacao; cod_estabelecimento fica str (preserva zeros)."""
    caminho = Path(caminho)
    with open(caminho, encoding=ENCODING, newline="") as f:
        leitor = csv.DictReader(f, delimiter=";")
        faltando = [c for c in COLUNAS_ARQUIVO if c not in (leitor.fieldnames or [])]
        if faltando:
            raise ValueError(f"{caminho.name}: colunas ausentes no cabeçalho: {faltando}")
        registros = []
        for linha in leitor:
            if None in linha or None in linha.values():
                raise ValueError(f"{caminho.name}, linha física {leitor.line_num}: número de campos diferente do cabeçalho")
            try:
                registros.append(_converter(linha, caminho.name))
            except ValueError as e:
                raise ValueError(f"{caminho.name}, linha física {leitor.line_num}: {e}") from None
    # dtype=object: mantém Decimal, date e None (sem virar float/NaN)
    return pd.DataFrame(registros, columns=COLUNAS_SAIDA, dtype=object)
