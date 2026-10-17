"""Apoio dos testes: carrega os dados uma vez e roda um módulo (ou pula)."""
import unittest
from decimal import Decimal
from functools import cache
from pathlib import Path

from src.core import config
from src.leitores import carregar_tudo

RAIZ = Path(__file__).resolve().parents[1]
COMPETENCIA = "2026-09"


@cache
def dados():
    return carregar_tudo(RAIZ / "dados")


def soma(valores) -> Decimal:
    return sum(valores, Decimal("0"))


class TesteModulo(unittest.TestCase):
    """Teste de aceite de um módulo: pula enquanto o motor não existir."""
    modulo = None
    nome = ""

    @classmethod
    def setUpClass(cls):
        try:
            cls.r = cls.modulo.executar(dados(), config.carregar(cls.nome), COMPETENCIA)
        except NotImplementedError as e:
            raise unittest.SkipTest(str(e))
