"""Leitor do extrato OFX 1.02 (SGML) do Banco Meridiano.

As tags SGML não fecham (<TRNAMT>1234.56 sem </TRNAMT>), então não há parser XML:
cada campo é lido por regex dentro do seu bloco.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from tarvo.leitores.comum import dinheiro, sem_acento
from tarvo.leitores.rejeitadas import LinhaRejeitada

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
        try:
            return bruto.decode(codec), codec  # erro de decodificação sobe
        except LookupError:
            raise ValueError(f"CHARSET {charset!r} do cabeçalho OFX não é um encoding conhecido") from None
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
    """"AAAAMMDDHHMMSS[-3:BRT]" para date (a data como o banco gravou)."""
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


def _valor_seguro(s: str | None) -> Decimal | None:
    try:
        return _valor_ofx(s)
    except ValueError:
        return None


def ler_meridiano(caminho, rejeitadas: list[LinhaRejeitada] | None = None) -> tuple[pd.DataFrame, dict]:
    """Lê o OFX do Meridiano. Devolve (lançamentos, metadados). ref_origem = FITID.

    Com rejeitadas, o <STMTTRN> com dado inválido vai para a lista e a leitura segue (R44); FITID repetido rejeita
    todas as cópias (o leitor não escolhe uma). Sem a lista, é erro.
    """
    caminho = Path(caminho)
    with open(caminho, "rb") as f:
        bruto = f.read()
    cabecalho = _cabecalho(bruto)
    texto, charset = _decodificar(bruto, cabecalho)

    registros = []
    vistos: set[str] = set()
    for n, bloco in enumerate(_RE_STMTTRN.findall(texto), start=1):
        fitid = _tag(bloco, "FITID")
        try:
            data = _data_ofx(_tag(bloco, "DTPOSTED"))
            valor = _valor_ofx(_tag(bloco, "TRNAMT"))
            if not fitid or data is None or valor is None:
                raise ValueError(f"<STMTTRN> sem FITID, DTPOSTED ou TRNAMT: {bloco.strip()[:200]!r}")
            if fitid in vistos:
                raise ValueError(f"FITID repetido: {fitid}")
        except ValueError as e:
            if rejeitadas is None:
                raise ValueError(f"{caminho.name}: {e}") from None
            if fitid and fitid in vistos:  # as cópias saem todas: o leitor não escolhe qual vale
                for primeira in [r for r in registros if r["ref_origem"] == fitid]:
                    registros.remove(primeira)
                    rejeitadas.append(LinhaRejeitada(caminho.name, fitid, f"{caminho.name}: FITID repetido: {fitid}",
                                                     ident=fitid, valor=primeira["valor"]))
            vistos.add(fitid or "")
            rejeitadas.append(LinhaRejeitada(caminho.name, fitid or f"STMTTRN {n}", f"{caminho.name}: {e}",
                                             ident=fitid, valor=_valor_seguro(_tag(bloco, "TRNAMT"))))
            continue
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
