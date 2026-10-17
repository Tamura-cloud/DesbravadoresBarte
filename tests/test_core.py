import tempfile
import unittest
from datetime import date
from decimal import Decimal as D
from pathlib import Path

from src.core.dinheiro import arred, brl, cnpj, fmt_brl, fmt_pct, pct_planilha
from src.core.modelos import ItemRastro, Lancamento, Pendencia, ResultadoModulo
from src.core.saida import RastroNaoFecha, escrever


class TestDinheiro(unittest.TestCase):
    def test_arredondamento_da_helena(self):
        self.assertEqual(arred(D("131.005")), D("131.01"))
        self.assertEqual(arred(D("-0.005")), D("-0.01"))
        self.assertEqual(arred(D("16.3788")), D("16.38"))   # a Orbe truncaria em 16.37

    def test_brl(self):
        self.assertEqual(brl("1.234,56"), D("1234.56"))
        self.assertEqual(brl("-369,39"), D("-369.39"))

    def test_pct_planilha(self):
        self.assertEqual(pct_planilha(0.0259), D("2.59"))
        self.assertEqual(pct_planilha("2,59%"), D("2.59"))
        self.assertIsNone(pct_planilha("padrão"))

    def test_cnpj_zero_a_esquerda(self):
        self.assertEqual(cnpj(3229837000103), "03229837000103")
        self.assertEqual(cnpj("17.217.888/0001-11"), "17217888000111")

    def test_formatos(self):
        self.assertEqual(fmt_brl(D("1234.5")), "1234.50")
        self.assertEqual(fmt_pct(D("2.49")), "2.49")
        self.assertEqual(fmt_pct(D("1.50070")), "1.5007")


class TestSaida(unittest.TestCase):
    def _lanc(self, valor, rastro):
        return Lancamento("AURORA", "L9", date(2026, 9, 1), "TED", D(valor), "1.1.03.001", "REGRA", D("1"),
                          rastro=[ItemRastro("aurora.csv", "L9", D(v)) for v in rastro])

    def test_escreve_formato_oficial_e_rastro(self):
        r = ResultadoModulo(lancamentos=[self._lanc("10.50", ["10.50"])],
                            pendencias=[Pendencia("X", "L9", D("3"), "m", "Helena",
                                                  rastro=[ItemRastro("a", "1", D("1")), ItemRastro("a", "2", D("2"))])])
        with tempfile.TemporaryDirectory() as tmp:
            escrever(r, Path(tmp))
            lanc = (Path(tmp) / "lancamentos_classificados.csv").read_bytes().decode("utf-8").splitlines()
            self.assertEqual(lanc[0], "id_saida;banco;ref_origem;data;descricao;valor;conta_codigo;metodo;confianca;conta_descricao;justificativa")
            self.assertEqual(lanc[1], "LAN-0001;AURORA;L9;2026-09-01;TED;10.50;1.1.03.001;REGRA;1.00;;")
            rastro = (Path(tmp) / "rastro.csv").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(rastro), 4)
            self.assertEqual(len(list(Path(tmp).glob("*.csv"))), 6)

    def test_rastro_que_nao_fecha_quebra(self):
        r = ResultadoModulo(lancamentos=[self._lanc("10.50", ["10.49"])])
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(RastroNaoFecha):
            escrever(r, Path(tmp))


if __name__ == "__main__":
    unittest.main()
