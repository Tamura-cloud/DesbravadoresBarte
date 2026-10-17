from pathlib import Path

import pytest

from tarvo.cli import localizar_pela_config
from tarvo.leitores.plano_contas import COLUNAS, ler_plano

ENTRADA = Path(__file__).resolve().parents[1] / "dados" / "2026-09"


@pytest.fixture(scope="module")
def plano():
    caminho = localizar_pela_config(ENTRADA)["plano_de_contas"]
    return ler_plano(caminho)


def _conta(df, cod):
    return df.loc[df["cod_conta"] == cod].iloc[0]


def test_colunas_e_quantidade(plano):
    assert list(plano.columns) == COLUNAS
    assert len(plano) == 52
    assert plano["cod_conta"].is_unique


def test_aceita_lancto(plano):
    assert plano["aceita_lancto"].dtype == bool
    assert plano["aceita_lancto"].sum() == 32


def test_acentos_cp1252(plano):
    assert _conta(plano, "1.1.02")["descricao"] == "APLICAÇÕES FINANCEIRAS"
    assert not plano["descricao"].str.contains("�").any()


def test_tipos_de_codigo(plano):
    raiz = _conta(plano, "1")
    assert raiz["cod_superior"] is None
    assert not raiz["aceita_lancto"]
    analitica = _conta(plano, "1.1.01.001")
    assert analitica["cod_superior"] == "1.1.01"
    assert analitica["aceita_lancto"]
    assert all(isinstance(c, str) for c in plano["cod_conta"])


def test_aceita_lancto_invalido_gera_erro(tmp_path):
    arquivo = tmp_path / "plano_de_contas.csv"
    arquivo.write_bytes(
        "COD_CONTA;DESCRICAO;TIPO;NATUREZA;ACEITA_LANCTO;COD_SUPERIOR\r\n1;ATIVO;SINTETICA;D;X;\r\n".encode("cp1252")
    )
    with pytest.raises(ValueError):
        ler_plano(arquivo)
