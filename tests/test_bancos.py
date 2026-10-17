"""Aceite do módulo Bancos (Pessoa C). Pula até o motor existir."""
import unittest
from collections import Counter

from src.bancos import motor
from tests.base import TesteModulo, dados

ESPERADO = {
    "L15": "2.1.04.001",            # folha 08/2026 provisionada
    "L42": "2.1.03.003",            # ISS 08/2026
    "L50": "1.1.09.002",            # PIX sem identificação
    "L65": "2.1.01.001",            # devolução de PIX da Mundo Aberto
    "L92": "1.1.09.001",            # transferência de 30/09
    "MRD2026090132": "1.1.03.002",  # repasse da Ponte de agosto
    "MRD2026090292": "4.2.05",      # seguro
    "MRD2026090425": "2.1.02.001",  # PIX de R$ 18.240 sem remessa
    "MRD2026090680": "3.2.01",      # rendimento
}


class TestBancos(TesteModulo):
    modulo, nome = motor, "bancos"

    def test_cada_lancamento_uma_vez(self):
        refs = Counter(l.ref_origem for l in self.r.lancamentos)
        self.assertEqual(len(self.r.lancamentos), 184)
        self.assertEqual(max(refs.values()), 1)

    def test_so_conta_analitica(self):
        plano = dados().plano_contas
        for l in self.r.lancamentos:
            self.assertTrue(plano[l.conta_codigo].aceita_lancto, l.ref_origem)

    def test_classificacoes_conhecidas(self):
        conta = {l.ref_origem: l.conta_codigo for l in self.r.lancamentos}
        for ref, esperado in ESPERADO.items():
            self.assertEqual(conta[ref], esperado, ref)

    def test_pendencias_bancarias(self):
        refs = " ".join(p.ref_origem for p in self.r.pendencias)
        for ref in ("L50", "L65", "L92", "MRD2026090425"):
            self.assertIn(ref, refs)


if __name__ == "__main__":
    unittest.main()
