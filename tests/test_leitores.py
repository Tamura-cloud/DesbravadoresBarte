"""Os leitores entregam as fontes inteiras e com os totais das próprias fontes."""
import unittest
from collections import Counter
from decimal import Decimal as D

from tests.base import dados, soma


class TestLeitores(unittest.TestCase):
    def setUp(self):
        self.d = dados()

    def test_orbe(self):
        tipos = Counter(t.tipo_lancamento for t in self.d.orbe)
        self.assertEqual(len(self.d.orbe), 1943)
        self.assertEqual(tipos, {"VENDA": 1840, "ESTORNO": 59, "ANTECIPACAO": 38, "REVERSAO ANTECIPACAO": 6})
        self.assertEqual(soma(t.valor_taxa for t in self.d.orbe), D("231880.36"))
        self.assertEqual(len({t.cod_estabelecimento for t in self.d.orbe}), 22)

    def test_taxas(self):
        por_cnpj = {t.cnpj: t for t in self.d.taxas}
        self.assertEqual(len(self.d.taxas), 25)
        self.assertIn("03229837000103", por_cnpj)                       # Fluente sem zero na planilha
        self.assertEqual(por_cnpj["23109187000161"].credito_2_6, D("3.09"))  # Oxford em texto '3,09%'
        self.assertTrue(por_cnpj["53857560000123"].spread_padrao)       # Canguru 'padrão'
        self.assertIn("Diego", por_cnpj["00520815000100"].comentario)   # comentário da Casa do Estudante
        bridge = [t for t in self.d.taxas if t.ec == "1075624862"]
        self.assertEqual(len(bridge), 2)

    def test_ponte(self):
        ops = self.d.ponte.operacoes
        self.assertEqual(len(ops), 233)
        self.assertEqual(len({o.ref_origem for o in ops}), 232)
        self.assertEqual(soma(o.spread_brl for o in ops), D("78073.59"))

    def test_plano_de_contas(self):
        self.assertEqual(len(self.d.plano_contas), 52)
        self.assertEqual(sum(c.aceita_lancto for c in self.d.plano_contas.values()), 32)

    def test_aurora(self):
        a = self.d.aurora
        self.assertEqual(len(a.lancamentos), 84)
        self.assertEqual((a.lancamentos[0].ref_origem, a.lancamentos[-1].ref_origem), ("L9", "L92"))
        self.assertEqual(a.saldo_anterior + soma(l.valor for l in a.lancamentos), a.saldo_final)

    def test_meridiano(self):
        m = self.d.meridiano
        self.assertEqual(len(m.lancamentos), 100)
        self.assertEqual(len({l.ref_origem for l in m.lancamentos}), 100)
        self.assertTrue(any("AÉREA" in l.memo for l in m.lancamentos))   # cp1252 decodificado


if __name__ == "__main__":
    unittest.main()
