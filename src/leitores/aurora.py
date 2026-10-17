"""Extrato do Banco Aurora (CSV utf-8 com cabeçalho, saldos e rodapé).

ref_origem = número da linha física do arquivo (L9 ... L92), como pede a
instrução oficial. Linhas de saldo, cabeçalho e rodapé não são lançamento.
"""
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from ..core.dinheiro import brl, data_br

DATA = re.compile(r"^\d{2}/\d{2}/\d{4}$")


@dataclass
class LancamentoAurora:
    ref_origem: str      # 'L50'
    linha: int
    data: date
    historico: str
    documento: str
    valor: Decimal
    saldo: Decimal


@dataclass
class ExtratoAurora:
    saldo_anterior: Decimal
    saldo_final: Decimal
    lancamentos: list[LancamentoAurora]


def ler(caminho: Path) -> ExtratoAurora:
    with open(caminho, encoding="utf-8") as f:
        linhas = f.read().splitlines()
    saldo_anterior = saldo_final = None
    lancamentos = []
    for n, texto in enumerate(linhas, start=1):
        c = texto.split(";")
        if len(c) < 5:
            continue
        if "SALDO ANTERIOR" in c[1]:
            saldo_anterior = brl(c[4])
        elif "SALDO FINAL" in c[1]:
            saldo_final = brl(c[4])
        elif DATA.match(c[0].strip()):
            lancamentos.append(LancamentoAurora(
                ref_origem=f"L{n}",
                linha=n,
                data=data_br(c[0]),
                historico=c[1].strip(),
                documento=c[2].strip(),
                valor=brl(c[3]),
                saldo=brl(c[4]),
            ))
    return ExtratoAurora(saldo_anterior, saldo_final, lancamentos)
