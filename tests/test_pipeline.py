"""Ponta a ponta: o pipeline roda e grava os 6 CSVs com o rastro fechando."""
import csv
import tempfile
import unittest
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from src.main import fechar
from tests.base import RAIZ

OBRIGATORIAS = {
    "comissoes_por_lojista": "id_saida;cnpj;lojista;linha_negocio;comissao_brl",
    "divergencias_taxa": "id_saida;cnpj;linha_negocio;ref_origem;taxa_contratada_pct;taxa_aplicada_pct;diferenca_brl",
    "notas_a_emitir": "id_saida;tomador_cnpj;tomador;linha_negocio;valor_brl;discriminacao",
    "lancamentos_classificados": "id_saida;banco;ref_origem;data;descricao;valor;conta_codigo;metodo;confianca",
    "pendencias": "id_saida;tipo;ref_origem;valor_brl;motivo;quem_decide",
    "rastro": "id_saida;arquivo_origem;ref_origem;valor",
}
COLUNA_VALOR = {"comissoes_por_lojista": "comissao_brl", "divergencias_taxa": "diferenca_brl",
                "notas_a_emitir": "valor_brl", "lancamentos_classificados": "valor", "pendencias": "valor_brl"}


class TestPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.saida = Path(cls.tmp.name)
        fechar(RAIZ / "dados", cls.saida, "2026-09")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _ler(self, nome):
        with open(self.saida / f"{nome}.csv", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f, delimiter=";"))

    def test_seis_arquivos_com_colunas_oficiais(self):
        for nome, cabecalho in OBRIGATORIAS.items():
            primeira = (self.saida / f"{nome}.csv").read_text(encoding="utf-8").splitlines()[0]
            self.assertTrue(primeira.startswith(cabecalho), nome)

    def test_rastro_fecha_com_cada_numero(self):
        rastro = defaultdict(Decimal)
        for r in self._ler("rastro"):
            rastro[r["id_saida"]] += Decimal(r["valor"])
        for nome, coluna in COLUNA_VALOR.items():
            for linha in self._ler(nome):
                self.assertEqual(rastro[linha["id_saida"]], Decimal(linha[coluna]), linha["id_saida"])


if __name__ == "__main__":
    unittest.main()
