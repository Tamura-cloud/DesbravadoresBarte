"""Leitor do extrato OFX 1.02 (SGML) do Banco Meridiano.

As tags SGML não fecham (<TRNAMT>207215.87 sem </TRNAMT>), então não há parser XML:
cada campo é lido por regex dentro do seu bloco.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from tarvo.leitores.comum import dinheiro, sem_acento

COLUNAS = ["arquivo_origem", "ref_origem", "data", "valor", "tipo", "memo", "memo_norm", "checknum"]

_RE_CABECALHO = re.compile(rb"^\s*([A-Z]+):(.*?)\s*$")
_RE_STMTTRN = re.compile(r"<STMTTRN>(.*?)(?=</STMTTRN>|<STMTTRN>|</BANKTRANLIST>)", re.S | re.I)
_ENTIDADES = {"&lt;": "<", "&gt;": ">", "&amp;": "&"}


def _cabecalho(bruto: bytes) -> dict[str, str]:
    """Pares CHAVE:VALOR antes da primeira tag (cabeçalho OFX 1.x, sempre ASCII)."""
    inicio = bruto.find(b"<")
    trecho = bruto if inicio < 0 else bruto[:inicio]
    pares = {}
    for linha in trecho.splitlines():
        m = _RE_CABECALHO.match(linha)
        if m:
            pares[m.group(1).decode("ascii")] = m.group(2).decode("ascii")
    return pares


def _decodificar(bruto: bytes, cabecalho: dict[str, str]) -> tuple[str, str]:
    """Decodifica pelo CHARSET declarado; sem CHARSET, UTF-8 estrito e depois cp1252. Nunca substitui bytes."""
    charset = cabecalho.get("CHARSET", "").strip().upper()
    if charset and charset != "NONE":
        codec = f"cp{charset}" if charset.isdigit() else charset.lower()
        return bruto.decode(codec), codec  # erro de decodificação sobe
    try:
        return bruto.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return bruto.decode("cp1252"), "cp1252"


def _tag(bloco: str, nome: str) -> str | None:
    m = re.search(rf"<{nome}>([^<\r\n]*)", bloco, re.I)
    if not m:
        return None
    valor = m.group(1)
    for entidade, char in _ENTIDADES.items():
        valor = valor.replace(entidade, char)
    return valor.strip()


def _data_ofx(s: str | None) -> date | None:
    """"20260901120000[-3:BRT]" para date (a data como o banco gravou)."""
    if not s:
        return None
    if not re.match(r"^\d{8}", s):
        raise ValueError(f"data OFX inválida: {s!r}")
    return date(int(s[0:4]), int(s[4:6]), int(s[6:8]))


def _valor_ofx(s: str | None) -> Decimal | None:
    if not s:
        return None
    texto = s.replace(",", ".") if "." not in s else s
    try:
        return dinheiro(Decimal(texto))
    except InvalidOperation:
        raise ValueError(f"valor OFX inválido: {s!r}") from None


def ler_meridiano(caminho) -> tuple[pd.DataFrame, dict]:
    """Lê o OFX do Meridiano. Devolve (lançamentos, metadados). ref_origem = FITID."""
    caminho = Path(caminho)
    with open(caminho, "rb") as f:
        bruto = f.read()
    cabecalho = _cabecalho(bruto)
    texto, charset = _decodificar(bruto, cabecalho)

    registros = []
    vistos: set[str] = set()
    for bloco in _RE_STMTTRN.findall(texto):
        fitid = _tag(bloco, "FITID")
        data = _data_ofx(_tag(bloco, "DTPOSTED"))
        valor = _valor_ofx(_tag(bloco, "TRNAMT"))
        if not fitid or data is None or valor is None:
            raise ValueError(f"{caminho.name}: <STMTTRN> sem FITID, DTPOSTED ou TRNAMT: {bloco.strip()[:200]!r}")
        if fitid in vistos:
            raise ValueError(f"{caminho.name}: FITID repetido: {fitid}")
        vistos.add(fitid)
        memo = _tag(bloco, "MEMO")
        registros.append({
            "arquivo_origem": caminho.name,
            "ref_origem": fitid,
            "data": data,
            "valor": valor,
            "tipo": _tag(bloco, "TRNTYPE"),
            "memo": memo,
            "memo_norm": sem_acento(memo),
            "checknum": _tag(bloco, "CHECKNUM") or None,
        })

    ledger = re.search(r"<LEDGERBAL>(.*?)(?=</LEDGERBAL>|<AVAILBAL>|</STMTRS>)", texto, re.S | re.I)
    meta = {
        "bankid": _tag(texto, "BANKID"),
        "branchid": _tag(texto, "BRANCHID"),
        "acctid": _tag(texto, "ACCTID"),
        "dtstart": _data_ofx(_tag(texto, "DTSTART")),
        "dtend": _data_ofx(_tag(texto, "DTEND")),
        "saldo_ledger": _valor_ofx(_tag(ledger.group(1), "BALAMT")) if ledger else None,
        "charset": charset,
    }
    return pd.DataFrame(registros, columns=COLUNAS, dtype=object), meta
