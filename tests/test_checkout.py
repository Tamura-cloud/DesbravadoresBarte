"""Linha CHECKOUT: regras com dados sintéticos e valores de referência de setembro/2026.

Os valores de referência vêm de uma análise independente. Se algum não bater, não ajuste o teste:
investigue as linhas responsáveis.
"""

from collections import defaultdict
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from tarvo.checkout import (
    CondicaoEspecial,
    ErroCheckout,
    calcular_checkout,
    calcular_linhas,
    carregar_config,
    checkout,
)
from tarvo.fechamento import ler_entradas
from tarvo.leitores import orbe as leitor_orbe
from tarvo.leitores import taxas as leitor_taxas
from tarvo.saida import gravar_saida, validar_saida

D = Decimal
ENTRADA = Path(__file__).resolve().parents[1] / "dados" / "2026-09"


def _por_prefixo(itens, prefixo):
    return {i.id_saida: i for i in itens if i.id_saida.startswith(prefixo)}


# ================================================================ dados sintéticos

CNPJ_A = "00111222000133"
CNPJ_B = "44555666000177"
CNPJ_SEM_EC = "88999000000111"
EC_A, EC_B, EC_SEM_COD, EC_DESCONHECIDO = "9000000001", "9000000002", "9000000003", "9000000099"
ARQ = "orbe_teste.csv"


def _taxa(lojista, cnpj, ec, ref, inicio=date(2031, 1, 1), fim=None, **taxas):
    base = {"taxa_debito": D("1.00"), "taxa_credito_vista": D("2.00"), "taxa_parc_2_6": D("3.00"),
            "taxa_parc_7_12": D("4.00"), "taxa_pix": D("0.50"), "taxa_antecipacao": D("2.00")}
    return {"arquivo_origem": "taxas_teste.xlsx", "ref_origem": ref, "lojista": lojista, "cnpj": cnpj, "ec": ec,
            **base, **taxas, "spread_remessa_pct": None, "spread_remessa_texto": None,
            "vigencia_inicio": inicio, "vigencia_fim": fim, "obs": None}


def _orbe(ref, ec, bruto, aplicada, tipo="VENDA", modalidade="DEBITO", parcelas=1, dia=date(2031, 3, 10),
          nome="QUALQUER NOME", id_referencia=None, data_venda_original=None):
    bruto, aplicada = D(bruto), D(aplicada)
    if tipo in ("ANTECIPACAO", "REVERSAO ANTECIPACAO"):
        modalidade = parcelas = None
    valor_taxa = (bruto * aplicada / 100).quantize(D("0.01"), rounding="ROUND_DOWN")
    return {"arquivo_origem": ARQ, "ref_origem": ref, "data_movimento": dia, "cod_estabelecimento": ec,
            "nome_estabelecimento": nome, "tipo_lancamento": tipo, "modalidade": modalidade,
            "qtd_parcelas": parcelas, "bandeira": None, "valor_bruto": bruto, "taxa_aplicada_pct": aplicada,
            "valor_taxa": valor_taxa, "valor_liquido": bruto - valor_taxa, "id_referencia": id_referencia,
            "data_venda_original": data_venda_original}


def _df(linhas, colunas):
    return pd.DataFrame(linhas, columns=colunas, dtype=object)


@pytest.fixture
def cfg():
    return replace(carregar_config(), ec_sem_codigo={EC_SEM_COD: CNPJ_SEM_EC}, condicoes=())


@pytest.fixture
def taxas():
    return _df([
        _taxa("Loja A Ltda", CNPJ_A, EC_A, "linha 4", inicio=None, fim=date(2031, 3, 14)),
        _taxa("Loja A Nova", CNPJ_A, EC_A, "linha 5", inicio=date(2031, 3, 15), taxa_credito_vista=D("1.50")),
        _taxa("Loja B Ltda", CNPJ_B, EC_B, "linha 6"),
        _taxa("Loja Sem EC Ltda", CNPJ_SEM_EC, None, "linha 7"),
    ], leitor_taxas.COLUNAS_SAIDA)


def _rodar(linhas_orbe, taxas, cfg, competencia="2031-03"):
    return calcular_checkout(_df(linhas_orbe, leitor_orbe.COLUNAS_SAIDA), taxas, competencia, cfg)


def test_lojista_casado_pelo_ec_e_nome_vem_da_planilha(taxas, cfg):
    itens = _rodar([
        _orbe("T1", EC_A, "100.00", "1.00", nome="LOJA B LTDA"),          # nome de outro lojista: ignorado
        _orbe("T2", EC_SEM_COD, "100.00", "1.00", nome="LOJA A LTDA"),    # EC sem código, via config
        _orbe("T3", EC_DESCONHECIDO, "100.00", "1.00", nome="Loja A Ltda"),  # mesmo nome, EC desconhecido
    ], taxas, cfg)
    com = _por_prefixo(itens, "COM-")
    assert set(com) == {f"COM-CHK-{CNPJ_A}", f"COM-CHK-{CNPJ_SEM_EC}"}
    assert com[f"COM-CHK-{CNPJ_A}"].campos["lojista"] == "Loja A Ltda"
    assert com[f"COM-CHK-{CNPJ_SEM_EC}"].campos["lojista"] == "Loja Sem EC Ltda"
    assert f"PEN-SEMCONTRATO-{EC_DESCONHECIDO}" in _por_prefixo(itens, "PEN-")


def test_taxa_pela_modalidade_e_faixa_de_parcelas(taxas, cfg):
    linhas = calcular_linhas(_df([
        _orbe("DEB", EC_B, "1000.00", "1.00", modalidade="DEBITO"),
        _orbe("CAV", EC_B, "1000.00", "2.00", modalidade="CREDITO A VISTA"),
        _orbe("P2", EC_B, "1000.00", "3.00", modalidade="CREDITO PARCELADO", parcelas=2),
        _orbe("P6", EC_B, "1000.00", "3.00", modalidade="CREDITO PARCELADO", parcelas=6),
        _orbe("P7", EC_B, "1000.00", "4.00", modalidade="CREDITO PARCELADO", parcelas=7),
        _orbe("P12", EC_B, "1000.00", "4.00", modalidade="CREDITO PARCELADO", parcelas=12),
        _orbe("PIX", EC_B, "1000.00", "0.50", modalidade="PIX"),
        _orbe("AN", EC_B, "1000.00", "2.00", tipo="ANTECIPACAO"),
    ], leitor_orbe.COLUNAS_SAIDA), taxas, cfg)
    assert {l.ref_origem: l.taxa_contratada for l in linhas} == {
        "DEB": D("1.00"), "CAV": D("2.00"), "P2": D("3.00"), "P6": D("3.00"), "P7": D("4.00"),
        "P12": D("4.00"), "PIX": D("0.50"), "AN": D("2.00"),
    }
    assert not any(l.divergente for l in linhas)


@pytest.mark.parametrize("parcelas", [1, 13, None])
def test_parcelado_fora_de_2_a_12_gera_erro(taxas, cfg, parcelas):
    with pytest.raises(ErroCheckout, match="parcelas"):
        _rodar([_orbe("P", EC_B, "100.00", "3.00", modalidade="CREDITO PARCELADO", parcelas=parcelas)], taxas, cfg)


def test_arredondamento_half_up_para_longe_do_zero_e_truncamento_nao_e_divergencia(taxas, cfg):
    linhas = calcular_linhas(_df([
        _orbe("POS", EC_B, "0.50", "1.00"),    # 0.005 -> 0.01; a Orbe trunca para 0.00
        _orbe("NEG", EC_B, "-0.50", "1.00", tipo="ESTORNO", id_referencia="X", data_venda_original=date(2031, 3, 1)),
    ], leitor_orbe.COLUNAS_SAIDA), taxas, cfg)
    pos, neg = linhas
    assert pos.comissao == D("0.01") and pos.valor_taxa_orbe == D("0.00")
    assert neg.comissao == D("-0.01")
    assert not pos.divergente and not neg.divergente


def test_comissao_nunca_usa_valor_taxa_da_orbe(taxas, cfg):
    linha = _orbe("T1", EC_B, "1000.00", "1.00")
    linha["valor_taxa"] = D("999.99")
    com = _por_prefixo(_rodar([linha], taxas, cfg), "COM-")
    assert com[f"COM-CHK-{CNPJ_B}"].valor_reportado == D("10.00")


def test_vigencia_pela_data_da_venda_original(taxas, cfg):
    linhas = calcular_linhas(_df([
        _orbe("V1", EC_A, "1000.00", "2.00", modalidade="CREDITO A VISTA", dia=date(2031, 3, 14)),
        _orbe("V2", EC_A, "1000.00", "1.50", modalidade="CREDITO A VISTA", dia=date(2031, 3, 15)),
        # estorno depois da troca, de venda anterior: taxa antiga
        _orbe("E1", EC_A, "-1000.00", "2.00", tipo="ESTORNO", modalidade="CREDITO A VISTA", dia=date(2031, 3, 20),
              id_referencia="V0", data_venda_original=date(2031, 3, 1)),
        # cobrada a taxa antiga depois da troca: divergência
        _orbe("V3", EC_A, "1000.00", "2.00", modalidade="CREDITO A VISTA", dia=date(2031, 3, 16)),
    ], leitor_orbe.COLUNAS_SAIDA), taxas, cfg)
    por_ref = {l.ref_origem: l for l in linhas}
    assert por_ref["V1"].origem_taxa == "linha 4" and por_ref["V1"].taxa_contratada == D("2.00")
    assert por_ref["V2"].origem_taxa == "linha 5" and por_ref["V2"].taxa_contratada == D("1.50")
    assert por_ref["E1"].origem_taxa == "linha 4" and por_ref["E1"].comissao == D("-20.00")
    assert not por_ref["E1"].divergente
    assert por_ref["V3"].diferenca == D("5.00")


def test_sem_linha_vigente_gera_erro(taxas, cfg):
    taxas = taxas.copy()
    taxas.loc[taxas["cnpj"] == CNPJ_B, "vigencia_inicio"] = date(2031, 4, 1)
    with pytest.raises(ErroCheckout, match="linha vigente"):
        _rodar([_orbe("T1", EC_B, "100.00", "1.00")], taxas, cfg)


def test_concessao_zera_a_comissao_mas_a_divergencia_e_contra_o_contrato(taxas, cfg):
    # R32: a concessão comercial muda só a comissão; a Orbe cobrou o contratado (1,00% no débito, 2,00% na antecipação)
    cfg = replace(cfg, condicoes=(CondicaoEspecial("RX", CNPJ_B, date(2031, 3, 1), date(2031, 3, 31),
                                                   {c: D("0") for c in ("taxa_debito", "taxa_antecipacao")}),))
    itens = _rodar([
        _orbe("T1", EC_B, "1000.00", "1.00"),
        _orbe("AN", EC_B, "500.00", "2.00", tipo="ANTECIPACAO"),
        _orbe("E1", EC_B, "-200.00", "1.00", tipo="ESTORNO", id_referencia="V0", data_venda_original=date(2031, 2, 27)),
    ], taxas, cfg)
    assert not _por_prefixo(itens, "DIV-") and not _por_prefixo(itens, "PEN-DEVOL-")

    pen = _por_prefixo(itens, "PEN-")
    # comissão = só o estorno de fevereiro (fora da concessão), pela planilha: -2.00 -> sem nota, pendência (R38, R40)
    assert _por_prefixo(itens, "COM-")[f"COM-CHK-{CNPJ_B}"].valor_reportado == D("-2.00")
    assert not _por_prefixo(itens, "NF-")
    nf = pen[f"PEN-NF-CHK-{CNPJ_B}"]
    assert nf.campos["tipo"] == "NOTA_NAO_EMITIDA" and nf.campos["quem_decide"] == "Financeiro (Helena)"
    conc = pen[f"PEN-CONCESSAO-CHK-{CNPJ_B}"]
    assert conc.valor_reportado == D("20.00") and conc.campos["ref_origem"] == ["T1", "AN"]
    assert conc.campos["tipo"] == "DEVOLUCAO_CONCESSAO"
    assert conc.campos["motivo"].startswith(
        "concessão comercial - custo da Tarvo - não é divergência - não se cobra da Orbe (RX, R32, R38)")
    assert "R25" not in conc.campos["motivo"]
    # O04 e R32: próximo passo da Helena com o Comercial, que decide a parametrização na Orbe
    assert "próximo passo: a Helena paga a devolução ao lojista e decide com o Comercial" in conc.campos["motivo"]
    assert conc.campos["quem_decide"] == "Financeiro (Helena) e Comercial"


def test_concessao_devolve_o_valor_taxa_cobrado_truncado(taxas, cfg):
    # R10, R38: o lojista recebe de volta o que a Orbe descontou (truncado), linha a linha
    cfg = replace(cfg, condicoes=(CondicaoEspecial("RX", CNPJ_B, date(2031, 3, 1), date(2031, 3, 31),
                                                   {"taxa_debito": D("0")}),))
    itens = _rodar([_orbe("T1", EC_B, "1000.55", "1.00"), _orbe("T2", EC_B, "333.33", "1.00")], taxas, cfg)
    assert not _por_prefixo(itens, "DIV-")
    conc = _por_prefixo(itens, "PEN-CONCESSAO-")[f"PEN-CONCESSAO-CHK-{CNPJ_B}"]
    assert [(o.ref_origem, o.valor) for o in conc.origens] == [("T1", D("10.00")), ("T2", D("3.33"))]
    assert conc.valor_reportado == D("13.33")


def test_concessao_com_taxa_acima_do_contrato_separa_divergencia_e_concessao(taxas, cfg):
    # R32: a parte acima do contrato é divergência (a Orbe deve); o resto da taxa cobrada é custo da Tarvo (P23)
    cfg = replace(cfg, condicoes=(CondicaoEspecial("RX", CNPJ_B, date(2031, 3, 1), date(2031, 3, 31),
                                                   {"taxa_debito": D("0")}),))
    itens = _rodar([_orbe("T1", EC_B, "1000.00", "1.50")], taxas, cfg)  # contrato 1,00%, cobrou 1,50%
    div = _por_prefixo(itens, "DIV-")["DIV-CHK-T1"]
    assert (div.valor_reportado, div.campos["taxa_contratada_pct"]) == (D("5.00"), D("1.00"))
    assert _por_prefixo(itens, "PEN-DEVOL-")[f"PEN-DEVOL-CHK-{CNPJ_B}"].valor_reportado == D("5.00")
    assert _por_prefixo(itens, "PEN-CONCESSAO-")[f"PEN-CONCESSAO-CHK-{CNPJ_B}"].valor_reportado == D("10.00")


def test_devolucao_sem_condicao_continua_pela_formula_da_r03(taxas, cfg):
    itens = _rodar([_orbe("T1", EC_B, "1000.55", "2.00")], taxas, cfg)
    devol = _por_prefixo(itens, "PEN-DEVOL-")[f"PEN-DEVOL-CHK-{CNPJ_B}"]
    assert devol.valor_reportado == D("10.01")
    assert devol.campos["motivo"].endswith("(R03, R25, R29, R32)")
    assert "a devolver ao lojista" in devol.campos["motivo"]  # R25
    assert "próximo passo: a Helena devolve o valor ao lojista e contesta com a Orbe" in devol.campos["motivo"]  # O04


def test_estorno_usa_a_data_da_venda_original_e_a_faixa_da_propria_linha(taxas, cfg):
    # R35: taxa vigente na data da venda original; a coluna (modalidade, parcelas) vem da linha do estorno.
    # R37: estorno de venda com taxa errada entra na divergência com valor negativo.
    linhas = calcular_linhas(_df([
        _orbe("E1", EC_A, "-1000.00", "4.50", tipo="ESTORNO", modalidade="CREDITO PARCELADO", parcelas=8,
              id_referencia="V0", data_venda_original=date(2031, 3, 1), dia=date(2031, 3, 20)),
    ], leitor_orbe.COLUNAS_SAIDA), taxas, cfg)
    e1 = linhas[0]
    assert e1.data_referencia == date(2031, 3, 1) and e1.origem_taxa == "linha 4"  # linha vigente em 01/03, não em 20/03
    assert e1.taxa_contratada == D("4.00")  # taxa_parc_7_12, pelas 8 parcelas do próprio estorno
    assert e1.diferenca == D("-5.00")


def test_alerta_de_antecipacao_so_para_lojista_sem_historico(taxas, cfg):
    # P26: sem histórico (primeira transação depois do dia 1, nada ligado a venda anterior) e antecipou mais que vendeu
    novo = [_orbe("V1", EC_B, "100.00", "1.00", dia=date(2031, 3, 5)),
            _orbe("AN", EC_B, "500.00", "2.00", tipo="ANTECIPACAO", dia=date(2031, 3, 6))]
    itens = _rodar(novo, taxas, cfg)
    alerta = _por_prefixo(itens, "PEN-ALERTA-ANTEC-")[f"PEN-ALERTA-ANTEC-{CNPJ_B}"]
    assert (alerta.campos["tipo"], alerta.valor_reportado, alerta.campos["ref_origem"]) == ("ALERTA_ANTECIPACAO", D("0.00"), ["AN"])
    assert alerta.campos["quem_decide"] == "Financeiro (Helena) e Comercial"
    assert "R$ 500.00 brutos" in alerta.campos["motivo"] and "R$ 100.00 de vendas" in alerta.campos["motivo"]
    # com histórico (uma linha ligada a venda anterior ao mês), não acende
    com_historico = novo + [_orbe("E1", EC_B, "-10.00", "1.00", tipo="ESTORNO", id_referencia="V0",
                                  data_venda_original=date(2031, 2, 27), dia=date(2031, 3, 7))]
    assert not _por_prefixo(_rodar(com_historico, taxas, cfg), "PEN-ALERTA-")
    # primeira transação no dia 1 e contrato anterior ao mês: não acende
    no_dia_1 = [_orbe("V1", EC_B, "100.00", "1.00", dia=date(2031, 3, 1)), novo[1]]
    assert not _por_prefixo(_rodar(no_dia_1, taxas, cfg), "PEN-ALERTA-")
    # antecipou menos do que vendeu: não acende
    pouco = [_orbe("V1", EC_B, "1000.00", "1.00", dia=date(2031, 3, 5)), novo[1]]
    assert not _por_prefixo(_rodar(pouco, taxas, cfg), "PEN-ALERTA-")


def test_alerta_usa_a_competencia_anterior_quando_ela_existe(taxas, cfg):
    novo = [_orbe("V1", EC_B, "100.00", "1.00", dia=date(2031, 3, 5)),
            _orbe("AN", EC_B, "500.00", "2.00", tipo="ANTECIPACAO", dia=date(2031, 3, 6))]
    orbe = _df(novo, leitor_orbe.COLUNAS_SAIDA)
    assert not _por_prefixo(calcular_checkout(orbe, taxas, "2031-03", cfg, frozenset({EC_B})), "PEN-ALERTA-")
    assert _por_prefixo(calcular_checkout(orbe, taxas, "2031-03", cfg, frozenset({EC_A})), "PEN-ALERTA-")


def test_textos_sem_ponto_e_virgula(taxas, cfg):
    taxas = taxas.copy()
    taxas.loc[taxas["cnpj"] == CNPJ_B, "lojista"] = "Loja B; Filial"
    itens = _rodar([_orbe("V1", EC_B, "1000.00", "1.00"), _orbe("T1", EC_B, "1000.00", "2.00")], taxas, cfg)
    assert _por_prefixo(itens, "COM-")[f"COM-CHK-{CNPJ_B}"].campos["lojista"] == "Loja B - Filial"
    textos = [v for i in itens for k, v in i.campos.items() if isinstance(v, str)]
    assert textos and not [t for t in textos if ";" in t]


def test_comissao_zero_nao_gera_nota(taxas, cfg):
    itens = _rodar([
        _orbe("V1", EC_B, "1000.00", "1.00"),
        _orbe("E1", EC_B, "-1000.00", "1.00", tipo="ESTORNO", id_referencia="V1", data_venda_original=date(2031, 3, 10)),
    ], taxas, cfg)
    assert not _por_prefixo(itens, "NF-")
    assert _por_prefixo(itens, "PEN-")[f"PEN-NF-CHK-{CNPJ_B}"].valor_reportado == D("0.00")


def test_comissao_positiva_gera_nota_com_rastro_da_comissao(taxas, cfg):
    itens = _rodar([_orbe("V1", EC_B, "1000.00", "1.00"), _orbe("V2", EC_B, "333.33", "1.00")], taxas, cfg)
    com = _por_prefixo(itens, "COM-")[f"COM-CHK-{CNPJ_B}"]
    nf = _por_prefixo(itens, "NF-")[f"NF-CHK-{CNPJ_B}"]
    assert nf.valor_reportado == com.valor_reportado == D("13.33")
    assert nf.origens == com.origens
    assert nf.campos["tomador_cnpj"] == CNPJ_B and nf.campos["tomador"] == "Loja B Ltda"
    assert nf.campos["discriminacao"].endswith("competência 2031-03")
    assert {o.arquivo_origem for o in com.origens} == {ARQ}


def test_ec_sem_contrato_so_gera_uma_pendencia_pelo_valor_da_orbe(taxas, cfg):
    itens = _rodar([
        _orbe("X1", EC_DESCONHECIDO, "100.00", "2.00"),
        _orbe("X2", EC_DESCONHECIDO, "333.33", "3.00"),
    ], taxas, cfg)
    assert [i.id_saida for i in itens] == [f"PEN-SEMCONTRATO-{EC_DESCONHECIDO}"]
    pen = itens[0]
    assert pen.valor_reportado == D("2.00") + D("9.99")
    assert pen.campos["tipo"] == "LOJISTA_SEM_CONTRATO" and pen.campos["quem_decide"] == "Comercial"
    assert "R08" in pen.campos["motivo"]
    assert [o.ref_origem for o in pen.origens] == ["X1", "X2"]


def test_ec_com_faturamento_retroativo_cita_qtd_bruto_data_e_competencia_seguinte(taxas, cfg):
    # R30: só o texto muda; continua uma pendência pelo valor da Orbe, sem comissão, divergência ou nota
    cfg = replace(cfg, faturamento_retroativo={EC_DESCONHECIDO: "RX"})
    itens = _rodar([
        _orbe("X1", EC_DESCONHECIDO, "100.00", "2.00", dia=date(2031, 12, 12)),
        _orbe("X2", EC_DESCONHECIDO, "333.33", "3.00", dia=date(2031, 12, 10)),
    ], taxas, cfg, competencia="2031-12")
    assert [i.id_saida for i in itens] == [f"PEN-SEMCONTRATO-{EC_DESCONHECIDO}"]
    pen = itens[0]
    assert pen.valor_reportado == D("11.99")
    motivo = pen.campos["motivo"]
    assert "R08" in motivo and "(RX)" in motivo
    assert "2 transações do mês (R$ 433.33 brutos)" in motivo
    assert "competência 2032-01" in motivo and "retroativa a 2031-12-10" in motivo


def test_ec_sem_codigo_com_cnpj_fora_da_planilha_gera_erro(taxas, cfg):
    cfg = replace(cfg, ec_sem_codigo={EC_SEM_COD: "12312312000112"})
    with pytest.raises(ErroCheckout, match="não está na planilha"):
        _rodar([], taxas, cfg)


# ================================================================ setembro/2026 (referência)

CASA_ESTUDANTE = "00520815000100"
OXFORD = "23109187000161"
ROTA_GLOBAL = "95927868000148"
BRIDGE = "22224579000109"
EC_ATLAS = "1076801732"
CNPJ_ATLAS = "39566044000119"   # aba "ANTIGO 2025": só identifica (R39)


@pytest.fixture(scope="module")
def entradas():
    return ler_entradas(ENTRADA, "2026-09")


@pytest.fixture(scope="module")
def itens(entradas):
    return checkout(entradas)


def test_set_comissao_total_e_lojistas(itens):
    com = _por_prefixo(itens, "COM-")
    assert len(com) == 21
    # O05: 207.039,73 só com o relatório; o 06 (ajustes tardios) tira 3.304,39 (10 estornos, 3 reversões, 1 venda Kiwi)
    assert sum(i.valor_reportado for i in com.values()) == D("203735.34")
    assert all(i.campos["linha_negocio"] == "CHECKOUT" for i in com.values())


@pytest.mark.parametrize("cnpj, valor", [
    (OXFORD, D("13845.71")),       # O05: 16.077,90 - 2.232,19 (2 estornos e 2 reversões do 06, R35, R05)
    (ROTA_GLOBAL, D("15621.27")),
    (BRIDGE, D("11769.74")),       # O05: 11.916,02 - 146,28 (2 estornos de parcelado do 06, R35)
    (CASA_ESTUDANTE, D("-5.50")),
])
def test_set_comissao_por_lojista(itens, cnpj, valor):
    assert _por_prefixo(itens, "COM-")[f"COM-CHK-{cnpj}"].valor_reportado == valor


def test_set_notas(itens):
    notas = _por_prefixo(itens, "NF-")
    assert len(notas) == 20
    assert f"NF-CHK-{CASA_ESTUDANTE}" not in notas
    pen = _por_prefixo(itens, "PEN-NF-")
    assert set(pen) == {f"PEN-NF-CHK-{CASA_ESTUDANTE}"}
    assert pen[f"PEN-NF-CHK-{CASA_ESTUDANTE}"].campos["tipo"] == "NOTA_NAO_EMITIDA"
    assert pen[f"PEN-NF-CHK-{CASA_ESTUDANTE}"].valor_reportado == D("-5.50")


def test_set_divergencias(itens):
    div = _por_prefixo(itens, "DIV-")
    # R32: a isenção da Casa é concessão, não divergência; as 118 vieram pela taxa da planilha (era 210 · 16.973,65)
    assert len(div) == 92
    assert sum(i.valor_reportado for i in div.values()) == D("1576.23")
    por_lojista = defaultdict(lambda: [0, D("0")])
    for i in div.values():
        por_lojista[i.campos["cnpj"]][0] += 1
        por_lojista[i.campos["cnpj"]][1] += i.valor_reportado
    assert dict(por_lojista) == {
        ROTA_GLOBAL: [87, D("1546.28")],
        BRIDGE: [5, D("29.95")],
    }
    pen = _por_prefixo(itens, "PEN-DEVOL-")
    assert {k: (len(v.origens), v.valor_reportado) for k, v in pen.items()} == {
        f"PEN-DEVOL-CHK-{ROTA_GLOBAL}": (87, D("1546.28")),
        f"PEN-DEVOL-CHK-{BRIDGE}": (5, D("29.95")),
    }


def test_set_casa_concessao_separada_das_divergencias(entradas, itens):
    # R32, R38, R40: as 118 vendas isentas vieram pela taxa da planilha; a devolução é custo da Tarvo, à parte
    linhas = [l for l in calcular_linhas(entradas.orbe, entradas.taxas, carregar_config()) if l.cnpj == CASA_ESTUDANTE]
    assert len(linhas) == 119 and all(l.taxa_aplicada == l.taxa_contratada for l in linhas)
    isentas = [l for l in linhas if l.concessao == "R10"]
    assert len(isentas) == 118 and all(l.taxa_comissao == 0 for l in isentas)
    estorno = next(l for l in linhas if l.ref_origem == "TX88445133")  # venda de 21/08: fora da isenção, 1,49%
    assert (estorno.concessao, estorno.taxa_comissao, estorno.comissao) == (None, D("1.4900"), D("-5.50"))
    conc = _por_prefixo(itens, "PEN-CONCESSAO-")[f"PEN-CONCESSAO-CHK-{CASA_ESTUDANTE}"]
    assert (len(conc.origens), conc.valor_reportado, conc.campos["tipo"]) == (118, D("15396.77"), "DEVOLUCAO_CONCESSAO")
    assert "concessão comercial - custo da Tarvo - não é divergência - não se cobra da Orbe" in conc.campos["motivo"]
    assert "R25" not in conc.campos["motivo"]


def test_set_nenhuma_divergencia_com_taxa_aplicada_abaixo_da_contratada(entradas):
    # auditoria R25: a Orbe nunca cobrou menos que o contratado; as 5 diferenças negativas são estornos
    # devolvidos pela taxa cobrada (acima da contratada), que reduzem o que se devolve ao lojista
    linhas = [l for l in calcular_linhas(entradas.orbe, entradas.taxas, carregar_config()) if l.divergente]
    assert not [l for l in linhas if l.taxa_aplicada < l.taxa_contratada]
    negativas = [l for l in linhas if l.diferenca < 0]
    assert {l.tipo_lancamento for l in negativas} == {"ESTORNO"}
    # o estorno da Casa (-9,09) saiu: com a R32 ele não diverge do contrato (era 5 · -107,53)
    assert (len(negativas), sum(l.diferenca for l in negativas)) == (4, D("-98.44"))


def test_set_atlas_sem_contrato(itens):
    pen = _por_prefixo(itens, "PEN-SEMCONTRATO-")
    # R39: a Atlas é identificada pelo CNPJ da aba de 2025 (sem usar a taxa dela); era PEN-SEMCONTRATO-<EC>
    assert set(pen) == {f"PEN-SEMCONTRATO-{CNPJ_ATLAS}"}
    atlas = pen[f"PEN-SEMCONTRATO-{CNPJ_ATLAS}"]
    assert atlas.campos["motivo"].startswith(f"EC {EC_ATLAS}, CNPJ {CNPJ_ATLAS}")
    assert len(atlas.origens) == 57
    assert atlas.valor_reportado == D("7876.05")
    assert atlas.campos["tipo"] == "LOJISTA_SEM_CONTRATO" and atlas.campos["quem_decide"] == "Comercial"
    # R30: 57 transações, R$ 262.138,61 brutos, faturadas em outubro, retroativas à primeira (10/09)
    assert ("as 57 transações do mês (R$ 262138.61 brutos) são faturadas na competência 2026-10, "
            "com a taxa retroativa a 2026-09-10") in atlas.campos["motivo"]
    assert "(R30)" in atlas.campos["motivo"]
    # sem comissão, divergência ou nota para os CNPJs que não vieram de contrato
    refs_atlas = {o.ref_origem for o in atlas.origens}
    assert not any(o.ref_origem in refs_atlas for i in itens
                   if not i.id_saida.startswith(("PEN-SEMCONTRATO-", "PEN-ALERTA-ANTEC-")) for o in i.origens)
    # R36: fora de comissoes_por_lojista (a forma escolhida), sem nota
    assert f"COM-CHK-{CNPJ_ATLAS}" not in _por_prefixo(itens, "COM-") and f"NF-CHK-{CNPJ_ATLAS}" not in _por_prefixo(itens, "NF-")


def test_set_alerta_de_antecipacao_so_a_atlas(itens):
    # P26: em setembro só a Atlas acende (a Oxford antecipou mais do que vendeu, mas tem histórico)
    alertas = _por_prefixo(itens, "PEN-ALERTA-ANTEC-")
    assert set(alertas) == {f"PEN-ALERTA-ANTEC-{CNPJ_ATLAS}"}
    a = alertas[f"PEN-ALERTA-ANTEC-{CNPJ_ATLAS}"]
    assert a.valor_reportado == D("0.00") and len(a.origens) == 5
    assert "primeira transação em 2026-09-10" in a.campos["motivo"]
    assert "R$ 235943.10 brutos (R$ 127230.96 líquidos das reversões) contra R$ 135428.90 de vendas" in a.campos["motivo"]


def test_set_reversao_anula_exatamente_a_antecipacao(entradas):
    linhas = {l.ref_origem: l for l in calcular_linhas(entradas.orbe, entradas.taxas, carregar_config())}
    reversoes = [l for l in linhas.values() if l.tipo_lancamento == "REVERSAO ANTECIPACAO" and l.cnpj]
    assert reversoes
    for r in reversoes:
        antecipacao = linhas[r.id_referencia]
        assert antecipacao.tipo_lancamento == "ANTECIPACAO"
        assert r.comissao == -antecipacao.comissao, r.ref_origem


def test_set_rastro_e_validar_saida(itens, tmp_path):
    gravar_saida(tmp_path, itens)
    assert validar_saida(tmp_path) == []



# ---------------------------------------------------------------- vários arquivos da Orbe (O05, P27, P28)

def test_repetida_entre_arquivos_vira_pendencia_informativa(cfg):
    from tarvo.checkout import pendencias_arquivos_orbe
    from tarvo.leitores.orbe import Repetida

    orbe = _df([_orbe("T1", EC_A, "100.00", "1.49")], leitor_orbe.COLUNAS_SAIDA)
    (pen,) = pendencias_arquivos_orbe(orbe, [Repetida("T1", "01_orbe.csv", 7, "06_orbe.csv", 2)], "2031-03", cfg)
    assert pen.id_saida == "PEN-REPET-CHK-T1" and pen.valor_reportado == D("0.00")
    assert pen.campos["tipo"] == "TRANSACAO_REPETIDA"
    assert [(o.arquivo_origem, o.ref_origem, o.valor) for o in pen.origens] == \
        [("01_orbe.csv", "T1", D("0.00")), ("06_orbe.csv", "T1", D("0.00"))]
    assert "contado uma vez" in pen.campos["motivo"] and "próximo passo: a Helena confirma com a Orbe" in pen.campos["motivo"]


def test_estorno_sem_a_original_do_mesmo_mes_vira_pendencia_e_de_mes_anterior_nao(cfg):
    from tarvo.checkout import pendencias_arquivos_orbe

    orbe = _df([
        _orbe("V1", EC_A, "100.00", "1.49"),
        _orbe("E1", EC_A, "-100.00", "1.49", tipo="ESTORNO", id_referencia="V1", data_venda_original=date(2031, 3, 2)),
        _orbe("E2", EC_A, "-50.00", "1.49", tipo="ESTORNO", id_referencia="V9", data_venda_original=date(2031, 3, 5)),
        _orbe("E3", EC_A, "-70.00", "1.49", tipo="ESTORNO", id_referencia="V8", data_venda_original=date(2031, 2, 20)),
    ], leitor_orbe.COLUNAS_SAIDA)
    itens = pendencias_arquivos_orbe(orbe, [], "2031-03", cfg)
    assert [i.id_saida for i in itens] == ["PEN-SEMORIG-CHK-E2"]  # E1 tem a original; E3 é de venda do mês anterior (R04)
    assert itens[0].valor_reportado == D("0.00") and itens[0].campos["tipo"] == "REFERENCIA_NAO_ENCONTRADA"
    assert "próximo passo: a Helena pede à Orbe a transação original V9" in itens[0].campos["motivo"]


def test_set_os_ajustes_tardios_nao_abrem_pendencia_de_arquivo(itens):
    """O05: no 06 nenhum id repete o 01 e toda original está no 01: nenhuma PEN-REPET nem PEN-SEMORIG."""
    assert not [i for i in itens if i.id_saida.startswith(("PEN-REPET-CHK-", "PEN-SEMORIG-CHK-"))]
