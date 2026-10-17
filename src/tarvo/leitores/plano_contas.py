"""Leitor do plano de contas do ERP Fênix (CSV ";" em Windows-1252)."""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

COLUNAS = ["cod_conta", "descricao", "tipo", "natureza", "aceita_lancto", "cod_superior"]
_SIM_NAO = {"S": True, "N": False}


def ler_plano(caminho) -> pd.DataFrame:
    """Lê o plano de contas. cod_conta e cod_superior ficam como texto; aceita_lancto S/N vira bool."""
    caminho = Path(caminho)
    with open(caminho, encoding="cp1252", newline="") as f:
        leitor = csv.DictReader(f, delimiter=";")
        titulos = {c.strip().upper(): c for c in leitor.fieldnames or []}
        faltando = [c for c in COLUNAS if c.upper() not in titulos]
        if faltando:
            raise ValueError(f"{caminho.name}: colunas ausentes: {faltando}")

        registros = []
        for n, linha in enumerate(leitor, start=2):
            campo = {c: (linha[titulos[c.upper()]] or "").strip() for c in COLUNAS}
            if not any(campo.values()):
                continue
            aceita = campo["aceita_lancto"].upper()
            if aceita not in _SIM_NAO:
                raise ValueError(f"{caminho.name} linha {n}: ACEITA_LANCTO inválido: {campo['aceita_lancto']!r}")
            campo["aceita_lancto"] = _SIM_NAO[aceita]
            campo["cod_superior"] = campo["cod_superior"] or None
            registros.append(campo)

    df = pd.DataFrame(registros, columns=COLUNAS, dtype=object)
    df["aceita_lancto"] = df["aceita_lancto"].astype(bool)
    return df
