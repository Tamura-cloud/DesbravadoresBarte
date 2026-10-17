"""Extrato do Banco Meridiano (OFX SGML, cp1252, sem tags de fechamento)."""
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path


@dataclass
class LancamentoMeridiano:
    ref_origem: str      # FITID
    data: date
    tipo: str            # TRNTYPE (CREDIT/DEBIT/...)
    valor: Decimal
    memo: str            # truncado em 34 caracteres pelo banco


@dataclass
class ExtratoMeridiano:
    saldo_final: Decimal | None
    lancamentos: list[LancamentoMeridiano]


def _tag(bloco: str, nome: str) -> str | None:
    m = re.search(rf"<{nome}>([^<\r\n]*)", bloco)
    return m.group(1).strip() if m else None


def ler(caminho: Path) -> ExtratoMeridiano:
    texto = Path(caminho).read_bytes().decode("cp1252")
    blocos = re.split(r"<STMTTRN>", texto)[1:]
    lancamentos = [
        LancamentoMeridiano(
            ref_origem=_tag(b, "FITID"),
            data=datetime.strptime(_tag(b, "DTPOSTED")[:8], "%Y%m%d").date(),
            tipo=_tag(b, "TRNTYPE") or "",
            valor=Decimal(_tag(b, "TRNAMT")),
            memo=_tag(b, "MEMO") or _tag(b, "NAME") or "",
        )
        for b in blocos
    ]
    saldo = _tag(texto, "BALAMT")
    return ExtratoMeridiano(Decimal(saldo) if saldo else None, lancamentos)
