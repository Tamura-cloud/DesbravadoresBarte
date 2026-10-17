"""Conversões puras compartilhadas pelos leitores. Arquivo compartilhado: mude só com o time avisado."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENTAVO = Decimal("0.01")


def dinheiro(v: Decimal) -> Decimal:
    """Arredonda valor monetário para 2 casas, ROUND_HALF_UP."""
    return v.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def num_br(s) -> Decimal | None:
    """Número em formato brasileiro ("1.234,56", "-1.234,56", "2,59%") ou int/float do Excel para Decimal.

    Vazio/None vira None. O "%" é só removido: "2,59%" vira Decimal("2.59").
    Não arredonda; para dinheiro, use dinheiro() em seguida.
    """
    if s is None:
        return None
    if isinstance(s, bool):
        raise TypeError(f"valor booleano não é número: {s!r}")
    if isinstance(s, Decimal):
        return s
    if isinstance(s, (int, float)):
        # via str: Decimal(0.1) traria o erro binário; Decimal(str(0.1)) == Decimal("0.1")
        return Decimal(str(s))
    texto = str(s).replace(" ", " ").strip()
    if texto.endswith("%"):
        texto = texto[:-1].strip()
    if not texto:
        return None
    texto = texto.replace(".", "").replace(",", ".")
    try:
        return Decimal(texto)
    except InvalidOperation:
        raise ValueError(f"número em formato brasileiro inválido: {s!r}") from None


def pct(v) -> Decimal | None:
    """Taxa da planilha para pontos percentuais.

    Número do Excel é fração (0.0259 vira Decimal("2.59")); texto precisa ter "%" ("2,59%" vira Decimal("2.59")).
    """
    if v is None:
        return None
    if isinstance(v, str):
        texto = v.strip()
        if not texto:
            return None
        if not texto.endswith("%"):
            raise ValueError(f"taxa em texto sem '%': {v!r}")
        return num_br(texto)
    fracao = num_br(v)
    if abs(fracao) > 1:
        raise ValueError(f"taxa numérica deveria ser fração (<= 1): {v!r}")
    return fracao * 100


def cnpj14(v) -> str | None:
    """CNPJ só com dígitos, completado com zeros à esquerda até 14. None se não houver 11 a 14 dígitos."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, float):
        if not v.is_integer():
            return None
        v = int(v)
    digitos = re.sub(r"\D", "", str(v))
    if not 11 <= len(digitos) <= 14:
        return None
    return digitos.zfill(14)


def data_br(s) -> date | None:
    """"dd/mm/aaaa" ou datetime/date do Excel para date. Vazio/None vira None."""
    if s is None:
        return None
    if isinstance(s, datetime):
        return s.date()
    if isinstance(s, date):
        return s
    texto = str(s).strip()
    if not texto:
        return None
    return datetime.strptime(texto, "%d/%m/%Y").date()


def sem_acento(s) -> str:
    """Maiúsculas, sem acentos, sem U+FFFD e com espaços colapsados.

    Só para exibição e evidência. NUNCA use como chave de casamento.
    """
    if s is None:
        return ""
    texto = unicodedata.normalize("NFKD", str(s).replace("�", ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.upper().split())
