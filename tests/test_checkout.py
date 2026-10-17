"""Aceite do módulo Checkout (Pessoa A). Pula até o motor existir."""
import unittest
from collections import defaultdict
from decimal import Decimal as D

from src.checkout import motor
from tests.base import TesteModulo, soma

CASA, ROTA, BRIDGE, ATLAS = "00520815000100", "95927868000148", "22224579000109", "39566044000119"


class TestCheckout(TesteModulo):
    modulo, nome = motor, "checkout"

    def test_notas(self):
        notas = [n for n in self.r.notas if n.linha_negocio == "CHECKOUT"]
        self.assertEqual(len(notas), 20)
        self.assertEqual(soma(n.valor_brl for n in notas), D("207045.23"))
        self.assertNotIn(CASA, {n.tomador_cnpj for n in notas})
        self.assertNotIn(ATLAS, {n.tomador_cnpj for n in notas})

    def test_divergencias(self):
        por_cnpj = defaultdict(list)
        for d in self.r.divergencias:
            por_cnpj[d.cnpj].append(d.diferenca_brl)
        self.assertEqual(len(self.r.divergencias), 210)
        self.assertEqual(soma(por_cnpj[CASA]), D("15397.42"))
        self.assertEqual(soma(por_cnpj[ROTA]), D("1546.28"))
        self.assertEqual(soma(por_cnpj[BRIDGE]), D("29.95"))
        self.assertNotIn(ATLAS, por_cnpj)

    def test_casa_do_estudante_negativa(self):
        casa = [c for c in self.r.comissoes if c.cnpj == CASA]
        self.assertEqual(casa[0].comissao_brl, D("-5.50"))
        self.assertTrue(any(p.cnpj == CASA for p in self.r.pendencias))

    def test_atlas_vira_pendencia(self):
        self.assertTrue(any(p.cnpj == ATLAS for p in self.r.pendencias))


if __name__ == "__main__":
    unittest.main()
