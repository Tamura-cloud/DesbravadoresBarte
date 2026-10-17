from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from tarvo.cli import CONFIG_PADRAO, carregar_padroes, localizar_arquivos
from tarvo.leitores.aurora import COLUNAS, ler_aurora

ENTRADA = Path(__file__).resolve().parents[1] / "dados" / "2026-09"


@pytest.fixture(scope="module")
def aurora():
    caminho = localizar_arquivos(ENTRADA, carregar_padroes(CONFIG_PADRAO))["aurora"]
    return ler_aurora(caminho)


def test_colunas_e_quantidade(aurora):
    df, _ = aurora
    assert list(df.columns) == COLUNAS
    assert len(df) == 84
    assert df["ref_origem"].is_unique


def test_primeiro_lancamento_eh_l9(aurora):
    df, _ = aurora
    primeiro = df.iloc[0]
    assert primeiro["ref_origem"] == "L9"
    assert primeiro["data"] == date(2026, 9, 1)
    assert primeiro["documento"] == "988044"
    assert primeiro["valor"] == Decimal("66026.00")


def test_tipos(aurora):
    df, _ = aurora
    assert all(type(d) is date for d in df["data"])
    assert all(isinstance(v, Decimal) and v.as_tuple().exponent == -2 for v in df["valor"])
    assert all(isinstance(v, Decimal) for v in df["saldo"])
    assert df["arquivo_origem"].nunique() == 1


def test_documento_vazio_vira_none(aurora):
    df, _ = aurora
    assert df.iloc[1]["documento"] is None
    assert df.iloc[1]["valor"] == Decimal("-389.00")


def test_sem_saldo_anterior_nem_saldo_final_nos_lancamentos(aurora):
    df, _ = aurora
    descricoes = set(df["descricao"].str.upper())
    assert "SALDO ANTERIOR" not in descricoes
    assert "SALDO FINAL" not in descricoes


def test_metadados(aurora):
    _, meta = aurora
    assert meta["agencia"] == "0318"
    assert meta["conta"] == "4471-0"
    assert meta["cnpj_titular"] == "84626315000139"
    assert meta["saldo_anterior"] == Decimal("612334.81")
    assert meta["saldo_final"] == Decimal("-1920088.60")


def test_saldo_anterior_mais_valores_fecha_saldo_final(aurora):
    df, meta = aurora
    assert meta["saldo_anterior"] + sum(df["valor"]) == meta["saldo_final"]


def test_saldo_corrido_bate_linha_a_linha(aurora):
    df, meta = aurora
    saldo = meta["saldo_anterior"]
    for linha in df.itertuples():
        saldo += linha.valor
        assert saldo == linha.saldo, linha.ref_origem


def test_ref_origem_conta_linhas_vazias_e_cabecalho(tmp_path):
    arquivo = tmp_path / "extrato_aurora.csv"
    arquivo.write_text(
        "Banco Aurora S.A.;;;;\n"
        "Cliente: X;CNPJ: 11.222.333/0001-81;;;\n"
        "Agência: 0001;Conta: 123-4;;;\n"
        "\n"
        "Data;Lançamento;Documento;Valor (R$);Saldo (R$)\n"
        "31/08/2026;SALDO ANTERIOR;;;100,00\n"
        "\n"
        "01/09/2026;CREDITO;77;1.000,50;1.100,50\n"
        ";SALDO FINAL;;;1.100,50\n"
        ";rodapé qualquer;;;\n",
        encoding="utf-8",
    )
    df, meta = ler_aurora(arquivo)
    assert list(df["ref_origem"]) == ["L8"]
    assert df.iloc[0]["valor"] == Decimal("1000.50")
    assert meta == {"agencia": "0001", "conta": "123-4", "cnpj_titular": "11222333000181",
                    "saldo_anterior": Decimal("100.00"), "saldo_final": Decimal("1100.50")}


def test_sem_linha_de_titulos_gera_erro(tmp_path):
    arquivo = tmp_path / "extrato_aurora.csv"
    arquivo.write_text("01/09/2026;CREDITO;;1,00;1,00\n", encoding="utf-8")
    with pytest.raises(ValueError):
        ler_aurora(arquivo)
