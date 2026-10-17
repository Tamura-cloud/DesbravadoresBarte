from datetime import date, datetime
from decimal import Decimal

import pytest

from tarvo.leitores.comum import cnpj14, data_br, dinheiro, num_br, pct, sem_acento


@pytest.mark.parametrize("entrada, esperado", [
    ("1.234,56", Decimal("1234.56")),
    ("-389,00", Decimal("-389.00")),
    ("2,59%", Decimal("2.59")),
    ("  12,5 ", Decimal("12.5")),
    ("1.000.000,01", Decimal("1000000.01")),
    ("", None),
    ("   ", None),
    (None, None),
    (1234, Decimal("1234")),
    (0.1, Decimal("0.1")),
    (1234.56, Decimal("1234.56")),
])
def test_num_br(entrada, esperado):
    assert num_br(entrada) == esperado


def test_num_br_float_sem_erro_binario():
    assert num_br(0.1) + num_br(0.2) == Decimal("0.3")
    assert str(num_br(1234.56)) == "1234.56"


@pytest.mark.parametrize("entrada", ["abc", "12,34,56"])
def test_num_br_invalido(entrada):
    with pytest.raises(ValueError):
        num_br(entrada)


def test_dinheiro_half_up():
    assert dinheiro(Decimal("2.345")) == Decimal("2.35")
    assert dinheiro(Decimal("-2.345")) == Decimal("-2.35")
    assert str(dinheiro(Decimal("10"))) == "10.00"


@pytest.mark.parametrize("entrada, esperado", [
    (0.0259, Decimal("2.59")),
    (0.035, Decimal("3.5")),
    ("2,59%", Decimal("2.59")),
    (" 1,9 % ", Decimal("1.9")),
    (0, Decimal("0")),
    (None, None),
    ("", None),
])
def test_pct(entrada, esperado):
    assert pct(entrada) == esperado


def test_pct_resultado_eh_decimal():
    assert isinstance(pct(0.0259), Decimal)


@pytest.mark.parametrize("entrada", ["2,59", 2.59])
def test_pct_ambiguo_falha(entrada):
    with pytest.raises(ValueError):
        pct(entrada)


@pytest.mark.parametrize("entrada, esperado", [
    ("22.224.579/0001-09", "22224579000109"),
    ("07752116000126", "07752116000126"),
    (3229837000103, "03229837000103"),
    (3229837000103.0, "03229837000103"),
    ("123", None),
    ("123456789012345", None),
    ("", None),
    (None, None),
])
def test_cnpj14(entrada, esperado):
    assert cnpj14(entrada) == esperado


@pytest.mark.parametrize("entrada, esperado", [
    ("30/09/2026", date(2026, 9, 30)),
    (" 01/09/2026 ", date(2026, 9, 1)),
    (datetime(2026, 9, 15, 13, 45), date(2026, 9, 15)),
    (date(2026, 9, 15), date(2026, 9, 15)),
    ("", None),
    (None, None),
])
def test_data_br(entrada, esperado):
    resultado = data_br(entrada)
    assert resultado == esperado
    assert resultado is None or type(resultado) is date


def test_data_br_invalida():
    with pytest.raises(ValueError):
        data_br("2026-09-30")


@pytest.mark.parametrize("entrada, esperado", [
    ("Padaria São João", "PADARIA SAO JOAO"),
    ("  açaí   da   Vovó ", "ACAI DA VOVO"),
    ("CONFEIT�RIA  Ltda", "CONFEITRIA LTDA"),
    ("linha\tcom\nquebras", "LINHA COM QUEBRAS"),
    (None, ""),
])
def test_sem_acento(entrada, esperado):
    assert sem_acento(entrada) == esperado
