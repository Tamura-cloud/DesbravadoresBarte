"""Conversões e arredondamento financeiro. Toda a matemática usa Decimal."""
import re
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

CENTAVO = Decimal("0.01")


def arred(valor: Decimal) -> Decimal:
    """Arredondamento da Helena: meio centavo afasta do zero (-0,005 -> -0,01)."""
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def brl(texto: str) -> Decimal:
    """Converte valor pt-BR ('1.234,56', '-369,39') em Decimal."""
    texto = texto.strip()
    if not texto:
        return Decimal("0")
    return Decimal(texto.replace(".", "").replace(",", "."))


def decimal_de_celula(valor) -> Decimal | None:
    """Converte célula numérica do Excel (float/int) sem herdar erro binário."""
    if valor is None or valor == "":
        return None
    return Decimal(str(valor))


def pct_planilha(valor) -> Decimal | None:
    """Taxa da planilha em pontos percentuais: 0.0259 e '2,59%' viram Decimal('2.59')."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, str):
        texto = valor.strip().replace("%", "").replace(",", ".")
        try:
            return Decimal(texto)
        except ArithmeticError:
            return None
    return (Decimal(str(valor)) * 100).normalize()


def data_br(texto: str | None) -> date | None:
    """'21/08/2026' -> date(2026, 8, 21)."""
    if not texto or not texto.strip():
        return None
    return datetime.strptime(texto.strip(), "%d/%m/%Y").date()


def cnpj(valor) -> str:
    """CNPJ só com dígitos e 14 posições (preserva zero à esquerda)."""
    return re.sub(r"\D", "", str(valor)).zfill(14)


def fmt_brl(valor: Decimal) -> str:
    """Formato de saída: ponto decimal, 2 casas, sem milhar."""
    return f"{arred(valor):.2f}"


def fmt_pct(valor: Decimal | None) -> str:
    """Pontos percentuais com 2 a 4 casas ('2.49', '1.5007')."""
    if valor is None:
        return ""
    texto = f"{valor.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP):.4f}".rstrip("0")
    inteiro, _, casas = texto.partition(".")
    return f"{inteiro}.{casas.ljust(2, '0')}"
