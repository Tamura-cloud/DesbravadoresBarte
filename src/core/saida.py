"""Escrita dos 6 CSVs de saida/ no formato oficial, com rastro.csv validado."""
import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from .dinheiro import fmt_brl, fmt_pct
from .modelos import TIPOS_SAIDA, ResultadoModulo

COLUNAS_PCT = {"taxa_contratada_pct", "taxa_aplicada_pct"}
COLUNAS_RASTRO = ["id_saida", "arquivo_origem", "ref_origem", "valor"]


class RastroNaoFecha(Exception):
    """Linha de saída cujo rastro não soma o número reportado."""


def _formatar(coluna: str, valor) -> str:
    if valor is None:
        return ""
    if coluna in COLUNAS_PCT:
        return fmt_pct(valor)
    if coluna == "confianca":
        return f"{Decimal(valor):.2f}"
    if isinstance(valor, Decimal):
        return fmt_brl(valor)
    if isinstance(valor, date):
        return valor.isoformat()
    return str(valor)


def validar_rastro(linha, id_saida: str) -> None:
    soma = sum((item.valor for item in linha.rastro), Decimal("0"))
    if not linha.rastro or soma != linha.valor_reportado:
        raise RastroNaoFecha(
            f"{id_saida}: rastro soma {soma} ({len(linha.rastro)} itens), reportado {linha.valor_reportado}"
        )


def escrever(resultado: ResultadoModulo, pasta: Path) -> dict[str, int]:
    """Numera id_saida, valida o rastro e grava os 6 CSVs. Devolve contagens por arquivo."""
    pasta.mkdir(parents=True, exist_ok=True)
    linhas_por_tipo = {tipo: [l for l in resultado.todas() if isinstance(l, tipo)] for tipo in TIPOS_SAIDA}
    rastro = []
    contagens = {}
    for tipo, linhas in linhas_por_tipo.items():
        colunas = ["id_saida", *tipo.COLUNAS, *tipo.EXTRAS]
        with open(pasta / f"{tipo.ARQUIVO}.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";", lineterminator="\n")
            w.writerow(colunas)
            for n, linha in enumerate(linhas, start=1):
                id_saida = f"{tipo.PREFIXO}-{n:04d}"
                validar_rastro(linha, id_saida)
                w.writerow([id_saida, *(_formatar(c, getattr(linha, c)) for c in colunas[1:])])
                rastro += [[id_saida, i.arquivo_origem, i.ref_origem, fmt_brl(i.valor)] for i in linha.rastro]
        contagens[tipo.ARQUIVO] = len(linhas)
    with open(pasta / "rastro.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n")
        w.writerow(COLUNAS_RASTRO)
        w.writerows(rastro)
    contagens["rastro"] = len(rastro)
    return contagens
