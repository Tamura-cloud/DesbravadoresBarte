from collections import Counter
from datetime import date
from decimal import ROUND_DOWN, Decimal
from pathlib import Path

import pytest

from tarvo.cli import localizar_pela_config
from tarvo.leitores.orbe import (COLUNAS_SAIDA, Correcao, ErroArquivoOrbe, Repetida, ler_orbe, ler_orbe_arquivos,
                                 ler_orbe_parcial)

ENTRADA = Path(__file__).resolve().parents[1] / "dados" / "2026-09"

CABECALHO = (
    "id_transacao;data_movimento;cod_estabelecimento;nome_estabelecimento;tipo_lancamento;modalidade;"
    "qtd_parcelas;bandeira;valor_bruto;taxa_aplicada_pct;valor_taxa;valor_liquido;id_referencia;data_venda_original"
)


@pytest.fixture(scope="module")
def orbe():
    caminho = localizar_pela_config(ENTRADA)["orbe"][0]  # o relatório: o primeiro em ordem de nome (O05)
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
    assert set(orbe["arquivo_origem"]) == {localizar_pela_config(ENTRADA)["orbe"][0].name}


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



# ---------------------------------------------------------------- vários arquivos da Orbe (O05)

def test_le_relatorio_e_ajustes_tardios_do_mes():
    """O05: o relatório (01) e os ajustes tardios (06) do mesmo mês, lidos juntos, cada linha com o seu arquivo."""
    arquivos = localizar_pela_config(ENTRADA)["orbe"]
    df, repetidas = ler_orbe_arquivos(arquivos)
    assert repetidas == []
    assert len(df) == 1943 + 14
    por_arquivo = Counter(df["arquivo_origem"])
    assert por_arquivo == {arquivos[0].name: 1943, arquivos[1].name: 14}
    ajustes = df[df["arquivo_origem"] == arquivos[1].name]
    assert Counter(ajustes["tipo_lancamento"]) == {"ESTORNO": 10, "REVERSAO ANTECIPACAO": 3, "VENDA": 1}
    assert df["ref_origem"].is_unique
    # todo estorno e reversão dos ajustes aponta para uma transação do relatório
    assert set(ajustes["id_referencia"].dropna()) <= set(df["ref_origem"])


def _arquivo(pasta, nome, *linhas, cabecalho=CABECALHO):
    caminho = pasta / nome
    caminho.write_text("\r\n".join([cabecalho, *linhas]) + "\r\n", encoding="utf-8", newline="")
    return caminho


VENDA_1 = "TX1;01/09/2026;0012345678;LOJA;VENDA;DEBITO;1;VISA;1.000,00;1,49;14,90;985,10;;"
VENDA_2 = "TX2;02/09/2026;0012345678;LOJA;VENDA;DEBITO;1;VISA;200,00;1,49;2,98;197,02;;"


def test_varios_arquivos_em_ordem_de_nome(tmp_path):
    b = _arquivo(tmp_path, "06_orbe_b.csv", VENDA_2)
    a = _arquivo(tmp_path, "01_orbe_a.csv", VENDA_1)
    df, repetidas = ler_orbe_arquivos([b, a])
    assert list(df["ref_origem"]) == ["TX1", "TX2"] and list(df["arquivo_origem"]) == ["01_orbe_a.csv", "06_orbe_b.csv"]
    assert repetidas == []


def test_id_repetido_com_a_linha_igual_conta_uma_vez(tmp_path):
    a = _arquivo(tmp_path, "01_orbe_a.csv", VENDA_1, VENDA_2)
    b = _arquivo(tmp_path, "06_orbe_b.csv", VENDA_2)
    df, repetidas = ler_orbe_arquivos([a, b])
    assert list(df["ref_origem"]) == ["TX1", "TX2"] and set(df["arquivo_origem"]) == {"01_orbe_a.csv"}
    assert repetidas == [Repetida("TX2", "01_orbe_a.csv", 3, "06_orbe_b.csv", 2)]


def test_id_repetido_com_a_linha_diferente_vale_a_linha_do_arquivo_posterior(tmp_path):
    # P27 (critério nosso, Helena 13h34): a linha do ajuste é a correção e substitui a do relatório
    a = _arquivo(tmp_path, "01_orbe_a.csv", VENDA_1)
    b = _arquivo(tmp_path, "06_orbe_b.csv", VENDA_1.replace("1.000,00;1,49;14,90;985,10", "1.100,00;1,49;16,39;1.083,61"))
    df, repetidas = ler_orbe_arquivos([a, b])
    assert repetidas == [] and list(df["ref_origem"]) == ["TX1"]
    assert df.loc[0, "arquivo_origem"] == "06_orbe_b.csv" and df.loc[0, "valor_bruto"] == Decimal("1100.00")


def test_cabecalho_diferente_do_relatorio_para_com_o_arquivo_e_a_coluna(tmp_path):
    a = _arquivo(tmp_path, "01_orbe_a.csv", VENDA_1)
    b = _arquivo(tmp_path, "06_orbe_b.csv", VENDA_2,
                 cabecalho=CABECALHO.replace("valor_taxa;valor_liquido", "valor_liquido;valor_taxa"))
    with pytest.raises(ValueError, match=r"06_orbe_b\.csv: cabeçalho diferente do de 01_orbe_a\.csv: a coluna 11 é "
                                         r"'valor_liquido', no 01_orbe_a\.csv é 'valor_taxa'"):
        ler_orbe_arquivos([a, b])


def test_cabecalho_com_coluna_a_mais_tambem_para(tmp_path):
    a = _arquivo(tmp_path, "01_orbe_a.csv", VENDA_1)
    b = _arquivo(tmp_path, "06_orbe_b.csv", VENDA_2 + ";x", cabecalho=CABECALHO + ";observacao")
    with pytest.raises(ValueError, match=r"06_orbe_b\.csv: cabeçalho diferente.*15 colunas, o 01_orbe_a\.csv tem 14"):
        ler_orbe_arquivos([a, b])


# ---------------------------------------------------------------- R44: bloqueio só do arquivo de ajustes

def test_parcial_correcao_substitui_so_a_linha_e_o_resto_do_arquivo_e_lido(tmp_path):
    # P27: antes, o id repetido com dados diferentes bloqueava o arquivo de ajustes inteiro; agora é por linha
    a = _arquivo(tmp_path, "01_orbe_a.csv", VENDA_1, VENDA_2)
    corrigida = VENDA_1.replace("1.000,00;1,49;14,90;985,10", "1.100,00;1,49;16,39;1.083,61")
    venda_3 = "TX3;03/09/2026;0012345678;LOJA;VENDA;DEBITO;1;VISA;300,00;1,49;4,47;295,53;;"
    b = _arquivo(tmp_path, "06_orbe_b.csv", venda_3, corrigida)
    leitura = ler_orbe_parcial([a, b])
    assert not leitura.bloqueados and leitura.lidos == ["01_orbe_a.csv", "06_orbe_b.csv"]
    # a correção fica no lugar da linha antiga; o resto do 06 entra normalmente
    assert list(leitura.quadro["ref_origem"]) == ["TX1", "TX2", "TX3"]
    assert list(leitura.quadro["arquivo_origem"]) == ["06_orbe_b.csv", "01_orbe_a.csv", "06_orbe_b.csv"]
    assert leitura.quadro.loc[0, "valor_bruto"] == Decimal("1100.00")
    (c,) = leitura.correcoes
    assert isinstance(c, Correcao) and leitura.repetidas == []
    assert (c.ref_origem, c.arquivo_antes, c.linha_antes, c.arquivo_depois, c.linha_depois) == \
        ("TX1", "01_orbe_a.csv", 2, "06_orbe_b.csv", 3)
    assert c.campos == ("valor_bruto", "valor_taxa", "valor_liquido")
    assert c.antes["valor_bruto"] == Decimal("1000.00") and c.depois["valor_bruto"] == Decimal("1100.00")
    assert leitura.linhas_lidas == {"01_orbe_a.csv": 2, "06_orbe_b.csv": 2}


def test_parcial_correcao_de_correcao_vale_a_ultima(tmp_path):
    a = _arquivo(tmp_path, "01_orbe_a.csv", VENDA_1)
    b = _arquivo(tmp_path, "06_orbe_b.csv", VENDA_1.replace("1.000,00;1,49;14,90;985,10", "1.100,00;1,49;16,39;1.083,61"))
    c = _arquivo(tmp_path, "07_orbe_c.csv", VENDA_1.replace("1.000,00;1,49;14,90;985,10", "1.200,00;1,49;17,88;1.182,12"))
    leitura = ler_orbe_parcial([a, b, c])
    assert list(leitura.quadro["arquivo_origem"]) == ["07_orbe_c.csv"]
    assert [(x.arquivo_antes, x.arquivo_depois) for x in leitura.correcoes] == \
        [("01_orbe_a.csv", "06_orbe_b.csv"), ("06_orbe_b.csv", "07_orbe_c.csv")]


def test_parcial_id_repetido_com_linha_igual_continua_contando_uma_vez(tmp_path):
    a = _arquivo(tmp_path, "01_orbe_a.csv", VENDA_1)
    b = _arquivo(tmp_path, "06_orbe_b.csv", VENDA_1, VENDA_2)
    leitura = ler_orbe_parcial([a, b])
    assert list(leitura.quadro["ref_origem"]) == ["TX1", "TX2"] and leitura.correcoes == []
    assert leitura.repetidas == [Repetida("TX1", "01_orbe_a.csv", 2, "06_orbe_b.csv", 2)]


def test_parcial_cabecalho_diferente_bloqueia_so_o_posterior(tmp_path):
    a = _arquivo(tmp_path, "01_orbe_a.csv", VENDA_1)
    b = _arquivo(tmp_path, "06_orbe_b.csv", VENDA_2 + ";x", cabecalho=CABECALHO + ";observacao")
    leitura = ler_orbe_parcial([a, b])
    assert list(leitura.quadro["ref_origem"]) == ["TX1"]
    assert [x.arquivo for x in leitura.bloqueados] == ["06_orbe_b.csv"]
    assert "15 colunas, o 01_orbe_a.csv tem 14" in leitura.bloqueados[0].erro


def test_parcial_relatorio_ilegivel_bloqueia_a_fonte(tmp_path):
    a = _arquivo(tmp_path, "01_orbe_a.csv", VENDA_1, cabecalho=CABECALHO.replace("valor_taxa", "vlr_taxa"))
    b = _arquivo(tmp_path, "06_orbe_b.csv", VENDA_2)
    with pytest.raises(ErroArquivoOrbe) as erro:
        ler_orbe_parcial([a, b])
    assert erro.value.linha == 1 and "colunas ausentes no cabeçalho: ['valor_taxa']" in str(erro.value)


def test_parcial_coluna_a_mais_no_relatorio_so_avisa(tmp_path):
    a = _arquivo(tmp_path, "01_orbe_a.csv", VENDA_1 + ";x", cabecalho=CABECALHO + ";observacao")
    leitura = ler_orbe_parcial([a])
    assert list(leitura.quadro["ref_origem"]) == ["TX1"] and not leitura.bloqueados
    assert leitura.avisos == ["01_orbe_a.csv: coluna(s) fora do layout esperado: observacao (não usadas pelo fechamento)"]
