"""Aceite do módulo Remessa (Pessoa B). Pula até o motor existir."""
import unittest
from decimal import Decimal as D

from src.remessa import motor
from tests.base import TesteModulo, soma

MUNDO = "17217888000111"
NEGATIVOS = {"PC-0926-0210", "PC-0926-0326", "PC-0926-0491", "PC-0926-0545"}


class TestRemessa(TesteModulo):
    modulo, nome = motor, "remessa"

    def test_nota_unica_contra_a_ponte(self):
        notas = [n for n in self.r.notas if n.linha_negocio == "REMESSA"]
        self.assertEqual(len(notas), 1)
        self.assertEqual(notas[0].tomador_cnpj, "75374179000146")
        self.assertEqual(notas[0].valor_brl, D("39543.45"))

    def test_comissao_por_lojista_fecha_com_a_nota(self):
        comissoes = [c for c in self.r.comissoes if c.linha_negocio == "REMESSA"]
        self.assertEqual(soma(c.comissao_brl for c in comissoes), D("39543.45"))
        refs = [i.ref_origem for c in comissoes for i in c.rastro]
        self.assertEqual(len(refs), 228)
        self.assertEqual(refs.count("PC-0926-0162"), 1)
        self.assertFalse(NEGATIVOS & set(refs))

    def test_divergencias_mundo_aberto(self):
        mundo = [d for d in self.r.divergencias if d.cnpj == MUNDO]
        self.assertEqual(len(mundo), 23)
        self.assertEqual(soma(d.diferenca_brl for d in mundo), D("1418.85"))

    def test_pendencias_de_contestacao(self):
        refs = " ".join(p.ref_origem for p in self.r.pendencias)
        self.assertIn("PC-0926-0162", refs)
        for op in NEGATIVOS:
            self.assertIn(op, refs)


if __name__ == "__main__":
    unittest.main()
