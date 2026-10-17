"""Leitor do extrato CSV do Banco Aurora (UTF-8, ";", vírgula decimal, cabeçalho e rodapé livres)."""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd

from tarvo.leitores.comum import cnpj14, data_br, dinheiro, num_br, sem_acento
from tarvo.leitores.layout import avisos_layout
from tarvo.leitores.rejeitadas import LinhaRejeitada

COLUNAS = ["arquivo_origem", "ref_origem", "data", "descricao", "documento", "valor", "saldo"]

# Nome normalizado (sem_acento) de cada coluna da linha de títulos do extrato.
_TITULOS = {
    "data": "DATA",
    "descricao": "LANCAMENTO",
    "documento": "DOCUMENTO",
    "valor": "VALOR (R$)",
    "saldo": "SALDO (R$)",
}
_RE_DATA = re.compile(r"^\d{2}/\d{2}/\d{4}$")


def _campo(campos: list[str], i: int) -> str:
    return campos[i].strip() if i < len(campos) else ""


def _metadado(campos: list[str], meta: dict) -> None:
    """Lê os pares "Chave: valor" das linhas de cabeçalho (agência, conta, CNPJ)."""
    for campo in campos:
        chave, sep, valor = campo.partition(":")
        if not sep:
            continue
        chave, valor = sem_acento(chave), valor.strip()
        if chave == "AGENCIA":
            meta["agencia"] = valor
        elif chave == "CONTA":
            meta["conta"] = valor
        elif chave == "CNPJ":
            meta["cnpj_titular"] = cnpj14(valor)


def ler_aurora(caminho, avisos: list[str] | None = None,
               rejeitadas: list[LinhaRejeitada] | None = None) -> tuple[pd.DataFrame, dict]:
    """Lê o extrato do Aurora. Devolve (lançamentos, metadados).

    Lançamento é a linha cuja 1ª coluna é uma data e cuja descrição não é "SALDO ANTERIOR".
    ref_origem = "L" + número da linha física no arquivo (a primeira linha é a L1).
    avisos (opcional) recebe as colunas a mais ou fora de ordem (a leitura é pelo nome, R44). Com rejeitadas, o
    lançamento com dado inválido vai para a lista e a leitura segue (R44); sem ela, é erro.
    """
    caminho = Path(caminho)
    with open(caminho, encoding="utf-8", newline="") as f:
        linhas = f.read().splitlines()

    meta: dict = {"agencia": None, "conta": None, "cnpj_titular": None,
                  "saldo_anterior": None, "saldo_final": None}
    idx: dict[str, int] | None = None
    registros = []
    for n, linha in enumerate(linhas, start=1):
        campos = next(csv.reader([linha], delimiter=";")) if linha else []
        if not any(c.strip() for c in campos):
            continue
        if idx is None:
            normalizados = [sem_acento(c) for c in campos]
            if normalizados and normalizados[0] == _TITULOS["data"]:
                faltando = [t for t in _TITULOS.values() if t not in normalizados]
                if faltando:
                    raise ValueError(f"{caminho.name} L{n}: colunas ausentes no título: {faltando}")
                idx = {nome: normalizados.index(t) for nome, t in _TITULOS.items()}
                if avisos is not None:
                    avisos += avisos_layout(f"{caminho.name} L{n}", normalizados, _TITULOS.values())
            else:
                _metadado(campos, meta)
            continue

        primeira = _campo(campos, idx["data"])
        descricao = _campo(campos, idx["descricao"])
        rotulo = sem_acento(descricao)
        if rotulo == "SALDO ANTERIOR":
            meta["saldo_anterior"] = dinheiro(num_br(_campo(campos, idx["saldo"])))
            continue
        if rotulo == "SALDO FINAL":
            meta["saldo_final"] = dinheiro(num_br(_campo(campos, idx["saldo"])))
            continue
        if not _RE_DATA.match(primeira):
            continue  # rodapé

        try:
            valor = num_br(_campo(campos, idx["valor"]))
            saldo = num_br(_campo(campos, idx["saldo"]))
            if valor is None:
                raise ValueError("lançamento sem valor")
            registros.append({
                "arquivo_origem": caminho.name,
                "ref_origem": f"L{n}",
                "data": data_br(primeira),
                "descricao": descricao,
                "documento": _campo(campos, idx["documento"]) or None,
                "valor": dinheiro(valor),
                "saldo": dinheiro(saldo) if saldo is not None else None,
            })
        except ValueError as e:
            if rejeitadas is None:
                raise ValueError(f"{caminho.name} L{n}: {e}") from None
            rejeitadas.append(LinhaRejeitada(caminho.name, f"L{n}", f"{caminho.name} L{n}: {e}"))

    if idx is None:
        raise ValueError(f"{caminho.name}: linha de títulos 'Data;Lançamento;...' não encontrada")
    ausentes = [k for k, v in meta.items() if v is None]
    if ausentes:
        raise ValueError(f"{caminho.name}: metadados não encontrados: {ausentes}")
    return pd.DataFrame(registros, columns=COLUNAS, dtype=object), meta
