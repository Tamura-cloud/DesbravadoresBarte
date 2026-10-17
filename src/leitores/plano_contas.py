"""Plano de contas do ERP Fênix (CSV cp1252)."""
import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Conta:
    codigo: str
    descricao: str
    tipo: str            # SINTETICA | ANALITICA
    natureza: str        # D | C
    aceita_lancto: bool  # só conta analítica recebe lançamento
    superior: str


def ler(caminho: Path) -> dict[str, Conta]:
    with open(caminho, encoding="cp1252", newline="") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))
    return {
        r["COD_CONTA"]: Conta(
            codigo=r["COD_CONTA"],
            descricao=r["DESCRICAO"],
            tipo=r["TIPO"],
            natureza=r["NATUREZA"],
            aceita_lancto=r["ACEITA_LANCTO"] == "S",
            superior=r["COD_SUPERIOR"],
        )
        for r in linhas
    }
