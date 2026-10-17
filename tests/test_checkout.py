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


def _rodar(linhas_orbe, taxas, cfg):
    return calcular_checkout(_df(linhas_orbe, leitor_orbe.COLUNAS_SAIDA), taxas, "2031-03", cfg)


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


def test_condicao_especial_sobrepoe_planilha_na_data_de_referencia(taxas, cfg):
    cfg = replace(cfg, condicoes=(CondicaoEspecial("RX", CNPJ_B, date(2031, 3, 1), date(2031, 3, 31),
                                                   {c: D("0") for c in ("taxa_debito", "taxa_antecipacao")}),))
    itens = _rodar([
        _orbe("T1", EC_B, "1000.00", "1.00"),
        _orbe("AN", EC_B, "500.00", "2.00", tipo="ANTECIPACAO"),
        _orbe("E1", EC_B, "-200.00", "1.00", tipo="ESTORNO", id_referencia="V0", data_venda_original=date(2031, 2, 27)),
    ], taxas, cfg)
    div = _por_prefixo(itens, "DIV-")
    assert set(div) == {"DIV-CHK-T1", "DIV-CHK-AN"}
    assert div["DIV-CHK-T1"].valor_reportado == D("10.00")
    assert div["DIV-CHK-T1"].campos["taxa_contratada_pct"] == D("0")
    assert div["DIV-CHK-AN"].valor_reportado == D("10.00")

    pen = _por_prefixo(itens, "PEN-")
    # comissão = só o estorno de fevereiro, pela planilha: -2.00 -> sem nota, pendência
    assert _por_prefixo(itens, "COM-")[f"COM-CHK-{CNPJ_B}"].valor_reportado == D("-2.00")
    assert not _por_prefixo(itens, "NF-")
    nf = pen[f"PEN-NF-CHK-{CNPJ_B}"]
    assert nf.campos["tipo"] == "NOTA_NAO_EMITIDA" and nf.campos["quem_decide"] == "Financeiro (Helena)"
    devol = pen[f"PEN-DEVOL-CHK-{CNPJ_B}"]
    assert devol.valor_reportado == D("20.00") and devol.campos["ref_origem"] == ["T1", "AN"]
    assert devol.campos["tipo"] == "DEVOLUCAO_LOJISTA"


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


@pytest.fixture(scope="module")
def entradas():
    return ler_entradas(ENTRADA, "2026-09")


@pytest.fixture(scope="module")
def itens(entradas):
    return checkout(entradas)


def test_set_comissao_total_e_lojistas(itens):
    com = _por_prefixo(itens, "COM-")
    assert len(com) == 21
    assert sum(i.valor_reportado for i in com.values()) == D("207039.73")
    assert all(i.campos["linha_negocio"] == "CHECKOUT" for i in com.values())


@pytest.mark.parametrize("cnpj, valor", [
    (OXFORD, D("16077.90")),
    (ROTA_GLOBAL, D("15621.27")),
    (BRIDGE, D("11916.02")),
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
    assert len(div) == 210
    assert sum(i.valor_reportado for i in div.values()) == D("16973.65")
    por_lojista = defaultdict(lambda: [0, D("0")])
    for i in div.values():
        por_lojista[i.campos["cnpj"]][0] += 1
        por_lojista[i.campos["cnpj"]][1] += i.valor_reportado
    assert dict(por_lojista) == {
        CASA_ESTUDANTE: [118, D("15397.42")],
        ROTA_GLOBAL: [87, D("1546.28")],
        BRIDGE: [5, D("29.95")],
    }
    pen = _por_prefixo(itens, "PEN-DEVOL-")
    assert {k: (len(v.origens), v.valor_reportado) for k, v in pen.items()} == {
        f"PEN-DEVOL-CHK-{CASA_ESTUDANTE}": (118, D("15397.42")),
        f"PEN-DEVOL-CHK-{ROTA_GLOBAL}": (87, D("1546.28")),
        f"PEN-DEVOL-CHK-{BRIDGE}": (5, D("29.95")),
    }


def test_set_atlas_sem_contrato(itens):
    pen = _por_prefixo(itens, "PEN-SEMCONTRATO-")
    assert set(pen) == {f"PEN-SEMCONTRATO-{EC_ATLAS}"}
    atlas = pen[f"PEN-SEMCONTRATO-{EC_ATLAS}"]
    assert len(atlas.origens) == 57
    assert atlas.valor_reportado == D("7876.05")
    assert atlas.campos["tipo"] == "LOJISTA_SEM_CONTRATO" and atlas.campos["quem_decide"] == "Comercial"
    # sem comissão, divergência ou nota para os CNPJs que não vieram de contrato
    refs_atlas = {o.ref_origem for o in atlas.origens}
    assert not any(o.ref_origem in refs_atlas for i in itens if not i.id_saida.startswith("PEN-SEMCONTRATO-")
                   for o in i.origens)


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
