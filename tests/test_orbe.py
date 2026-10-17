from collections import Counter
from datetime import date
from decimal import ROUND_DOWN, Decimal
from pathlib import Path

import pytest

from tarvo.cli import CONFIG_PADRAO, carregar_padroes, localizar_arquivos
from tarvo.leitores.orbe import COLUNAS_SAIDA, ler_orbe

ENTRADA = Path(__file__).resolve().parents[1] / "dados" / "2026-09"

CABECALHO = (
    "id_transacao;data_movimento;cod_estabelecimento;nome_estabelecimento;tipo_lancamento;modalidade;"
    "qtd_parcelas;bandeira;valor_bruto;taxa_aplicada_pct;valor_taxa;valor_liquido;id_referencia;data_venda_original"
)


@pytest.fixture(scope="module")
def orbe():
    caminho = localizar_arquivos(ENTRADA, carregar_padroes(CONFIG_PADRAO))["orbe"]
    return ler_orbe(caminho)


def test_colunas(orbe):
    assert list(orbe.columns) == COLUNAS_SAIDA


def test_uma_linha_por_linha_do_arquivo(orbe):
    assert len(orbe) == 1943


def test_contagem_por_tipo(orbe):
    assert Counter(orbe["tipo_lancamento"]) == {
        "VENDA": 1840, "ESTORNO": 59, "ANTECIPACAO": 38, "REVERSAO ANTECIPACAO": 6,
    }


def test_soma_valor_taxa(orbe):
    assert sum(orbe["valor_taxa"], Decimal("0")) == Decimal("231880.36")


def test_id_transacao_sem_repeticao(orbe):
    assert orbe["ref_origem"].is_unique


def test_valor_taxa_e_bruto_vezes_taxa_truncado(orbe):
    # A Orbe trunca o centavo (HIPOTESES R02); o arredondamento HALF_UP não fecha em todas as linhas.
    for r in orbe.itertuples():
        esperado = (r.valor_bruto * r.taxa_aplicada_pct / 100).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        assert r.valor_taxa == esperado, r.ref_origem


def test_valor_liquido_e_bruto_menos_taxa(orbe):
    for r in orbe.itertuples():
        assert r.valor_liquido == r.valor_bruto - r.valor_taxa, r.ref_origem


def test_tipos(orbe):
    assert all(isinstance(v, Decimal) for c in ("valor_bruto", "taxa_aplicada_pct", "valor_taxa", "valor_liquido")
               for v in orbe[c])
    assert all(v.as_tuple().exponent == -2 for c in ("valor_bruto", "valor_taxa", "valor_liquido") for v in orbe[c])
    assert all(isinstance(v, date) for v in orbe["data_movimento"])
    assert all(isinstance(v, str) for v in orbe["cod_estabelecimento"])
    assert all(v is None or isinstance(v, int) for v in orbe["qtd_parcelas"])
    assert all(v is None or isinstance(v, date) for v in orbe["data_venda_original"])
    assert set(orbe["arquivo_origem"]) == {localizar_arquivos(ENTRADA, carregar_padroes(CONFIG_PADRAO))["orbe"].name}


def test_antecipacao_sem_modalidade(orbe):
    antecipacoes = orbe[orbe["tipo_lancamento"] == "ANTECIPACAO"]
    assert all(v is None for v in antecipacoes["modalidade"])
    assert all(v is None for v in antecipacoes["qtd_parcelas"])


def test_estorno_e_reversao_tem_referencia(orbe):
    com_ref = orbe[orbe["tipo_lancamento"].isin(["ESTORNO", "REVERSAO ANTECIPACAO"])]
    assert all(v is not None for v in com_ref["id_referencia"])
    assert all(isinstance(v, date) for v in com_ref["data_venda_original"])
    vendas = orbe[orbe["tipo_lancamento"] == "VENDA"]
    assert all(v is None for v in vendas["id_referencia"])


def _escrever(tmp_path, *linhas):
    caminho = tmp_path / "orbe_teste.csv"
    caminho.write_text("\r\n".join([CABECALHO, *linhas]) + "\r\n", encoding="utf-8", newline="")
    return caminho


def test_preserva_zeros_e_nome(tmp_path):
    caminho = _escrever(
        tmp_path,
        "TX1;01/09/2026;0012345678;Loja  com Espaço ;VENDA;CREDITO PARCELADO;3;VISA;1.000,00;3,19;31,90;968,10;;",
        "AN1;02/09/2026;0012345678;LOJA;ANTECIPACAO;;;;500,00;2,10;10,50;489,50;;",
    )
    df = ler_orbe(caminho)
    assert list(df["cod_estabelecimento"]) == ["0012345678", "0012345678"]
    assert df.loc[0, "nome_estabelecimento"] == "Loja  com Espaço "
    assert df.loc[0, "valor_bruto"] == Decimal("1000.00")
    assert df.loc[0, "qtd_parcelas"] == 3
    assert df.loc[1, "modalidade"] is None and df.loc[1, "qtd_parcelas"] is None and df.loc[1, "bandeira"] is None
    assert df.loc[1, "id_referencia"] is None and df.loc[1, "data_venda_original"] is None
    assert list(df["ref_origem"]) == ["TX1", "AN1"]
    assert set(df["arquivo_origem"]) == {"orbe_teste.csv"}


def test_falha_com_linha_quebrada(tmp_path):
    caminho = _escrever(tmp_path, "TX1;01/09/2026;0012345678;LOJA;VENDA")
    with pytest.raises(ValueError, match="linha física 2"):
        ler_orbe(caminho)


def test_falha_com_valor_de_3_casas(tmp_path):
    caminho = _escrever(tmp_path, "TX1;01/09/2026;1;LOJA;VENDA;DEBITO;1;VISA;10,005;1,49;0,14;9,86;;")
    with pytest.raises(ValueError, match="mais de 2 casas"):
        ler_orbe(caminho)
