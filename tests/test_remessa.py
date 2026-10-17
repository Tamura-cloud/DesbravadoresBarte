"""Linha REMESSA: regras com dados sintéticos e valores de referência de setembro/2026.

Os valores de referência vêm de uma análise independente. Se algum não bater, não ajuste o teste:
investigue as operações responsáveis.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from tarvo.checkout import checkout
from tarvo.fechamento import ler_entradas
from tarvo.leitores import ponte as leitor_ponte
from tarvo.leitores import taxas as leitor_taxas
from tarvo.remessa import (
    Contratos,
    ErroRemessa,
    calcular_remessa,
    carregar_config,
    deduplicar,
    remessa,
)
from tarvo.saida import gravar_saida, validar_saida

D = Decimal
ENTRADA = Path(__file__).resolve().parents[1] / "dados" / "2026-09"


def _por_prefixo(itens, prefixo):
    return {i.id_saida: i for i in itens if i.id_saida.startswith(prefixo)}


# ================================================================ dados sintéticos

CNPJ_A = "00111222000133"
CNPJ_B = "44555666000177"
CNPJ_FORA = "88999000000111"
ARQ = "ponte_teste.eml#ops.xlsx"
COMP = "2031-03"


def _taxa(lojista, cnpj, ref, spread=None, texto=None, inicio=date(2031, 1, 1), fim=None):
    return {"arquivo_origem": "taxas_teste.xlsx", "ref_origem": ref, "lojista": lojista, "cnpj": cnpj, "ec": None,
            **{c: None for c in leitor_taxas.CAMPOS_TAXA}, "spread_remessa_pct": spread,
            "spread_remessa_texto": texto, "vigencia_inicio": inicio, "vigencia_fim": fim, "obs": None}


_linha = iter(range(6, 10_000))


def _op(ref, cnpj, spread_brl, spread_pct, valor_me="1000.00", ptax="5.0000", dia=date(2031, 3, 10),
        cliente="QUALQUER NOME", observacao=None, linha=None):
    return {"arquivo_origem": ARQ, "ref_origem": ref, "linha_planilha": linha or next(_linha),
            "data_contratacao": dia, "data_liquidacao": dia, "cnpj": cnpj, "cliente": cliente, "moeda": "USD",
            "valor_me": D(valor_me), "taxa_cliente": D("5.1"), "ptax_ref": D(ptax), "valor_brl": D("5100.00"),
            "spread_brl": D(spread_brl), "spread_pct": D(spread_pct), "spread_estimado_d1_brl": D("0.00"),
            "iof_brl": D("0.00"), "status_compliance": "APROVADO", "observacao": observacao}


def _df(linhas, colunas):
    return pd.DataFrame(linhas, columns=colunas, dtype=object)


def _ponte(*ops):
    return _df(list(ops), leitor_ponte.COLUNAS_SAIDA)


@pytest.fixture
def cfg():
    return carregar_config()


@pytest.fixture
def taxas():
    return _df([
        _taxa("Loja A Ltda", CNPJ_A, "linha 4", spread=D("1.200")),
        _taxa("Loja B Antiga", CNPJ_B, "linha 5", texto="padrão", fim=date(2031, 3, 14)),
        _taxa("Loja B Nova", CNPJ_B, "linha 6", inicio=date(2031, 3, 15)),  # branco
    ], leitor_taxas.COLUNAS_SAIDA)


def _calc(taxas, cfg, *ops, competencia=COMP):
    return calcular_remessa(_ponte(*ops), taxas, competencia, ARQ, cfg)


def test_config_de_remessa(cfg):
    assert cfg.participacao == D("0.5")
    assert cfg.spread_padrao == D("1.5")
    assert cfg.tolerancia_pp == D("0.01")
    assert cfg.tomador_cnpj == "75374179000146"


def test_comissao_por_operacao_arredondada_e_somada_por_lojista(taxas, cfg):
    itens = _calc(taxas, cfg, _op("OP-1", CNPJ_A, "10.01", "1.2000"), _op("OP-2", CNPJ_A, "10.03", "1.2000"))
    com = _por_prefixo(itens, "COM-REM-")[f"COM-REM-{CNPJ_A}"]
    # 5,005 -> 5,01 e 5,015 -> 5,02 por operação (R02), depois soma
    assert com.valor_reportado == D("10.03")
    assert [(o.ref_origem, o.valor) for o in com.origens] == [("OP-1", D("5.01")), ("OP-2", D("5.02"))]
    assert com.campos == {"cnpj": CNPJ_A, "lojista": "Loja A Ltda", "linha_negocio": "REMESSA"}


def test_nome_do_cliente_da_ponte_nao_casa_lojista(taxas, cfg):
    itens = _calc(taxas, cfg, _op("OP-1", CNPJ_A, "10.00", "1.2000", cliente="LOJA B ANTIGA"))
    assert set(_por_prefixo(itens, "COM-REM-")) == {f"COM-REM-{CNPJ_A}"}


def test_nota_unica_tomadora_ponte_com_todas_as_operacoes(taxas, cfg):
    itens = _calc(taxas, cfg, _op("OP-1", CNPJ_A, "10.00", "1.2000"), _op("OP-2", CNPJ_B, "30.00", "1.5000"))
    notas = _por_prefixo(itens, "NF-")
    assert list(notas) == ["NF-REM-75374179000146"]
    nf = notas["NF-REM-75374179000146"]
    assert nf.valor_reportado == D("20.00")
    assert {o.ref_origem for o in nf.origens} == {"OP-1", "OP-2"}
    assert nf.campos["tomador_cnpj"] == "75374179000146" and nf.campos["linha_negocio"] == "REMESSA"
    assert nf.campos["discriminacao"].endswith(f"competência {COMP}")


def test_spread_negativo_fora_da_comissao_e_da_nota_e_vira_divergencia_e_contestacao(taxas, cfg):
    itens = _calc(taxas, cfg, _op("OP-1", CNPJ_A, "10.00", "1.2000"),
                  _op("OP-NEG", CNPJ_A, "-60.00", "-1.3000", valor_me="1000.00", ptax="5.0000"))
    assert _por_prefixo(itens, "COM-REM-")[f"COM-REM-{CNPJ_A}"].valor_reportado == D("5.00")
    nf = _por_prefixo(itens, "NF-")["NF-REM-75374179000146"]
    assert [o.ref_origem for o in nf.origens] == ["OP-1"]
    div = _por_prefixo(itens, "DIV-")["DIV-REM-OP-NEG"]
    # (-1,30 - 1,20) / 100 × 5,0000 × 1000,00 = -125,00 (P02, R15)
    assert div.valor_reportado == D("-125.00")
    assert div.campos["taxa_contratada_pct"] == D("1.200") and div.campos["taxa_aplicada_pct"] == D("-1.3000")
    neg = _por_prefixo(itens, "PEN-NEG-")["PEN-NEG-REM-OP-NEG"]
    assert neg.campos["tipo"] == "CONTESTACAO_PONTE" and neg.valor_reportado == D("-125.00")
    assert "PEN-CONTEST-REM-" + CNPJ_A not in {i.id_saida for i in itens}


def test_divergencia_pela_tolerancia_e_valor_cheio(taxas, cfg):
    itens = _calc(taxas, cfg,
                  _op("OP-DENTRO", CNPJ_A, "10.00", "1.2099"),
                  _op("OP-LIMITE", CNPJ_A, "10.00", "1.2100", valor_me="1000.00", ptax="5.0000"),
                  _op("OP-ACIMA", CNPJ_A, "10.00", "1.5000", valor_me="333.33", ptax="5.1234"))
    div = _por_prefixo(itens, "DIV-")
    assert set(div) == {"DIV-REM-OP-LIMITE", "DIV-REM-OP-ACIMA"}
    assert div["DIV-REM-OP-LIMITE"].valor_reportado == D("0.50")
    # 0,30 / 100 × 5,1234 × 333,33 = 5,12334... -> 5,12 (valor cheio, não a metade)
    assert div["DIV-REM-OP-ACIMA"].valor_reportado == D("5.12")
    pen = _por_prefixo(itens, "PEN-CONTEST-")[f"PEN-CONTEST-REM-{CNPJ_A}"]
    assert pen.valor_reportado == D("5.62")
    assert pen.campos["ref_origem"] == ["OP-ACIMA", "OP-LIMITE"]
    assert pen.campos["tipo"] == "CONTESTACAO_PONTE"


def test_spread_padrao_em_branco_ou_texto_e_vigencia_pela_contratacao(taxas, cfg):
    itens = _calc(taxas, cfg,
                  _op("OP-PADRAO", CNPJ_B, "10.00", "1.6000", dia=date(2031, 3, 14)),
                  _op("OP-BRANCO", CNPJ_B, "10.00", "1.6000", dia=date(2031, 3, 15)))
    div = _por_prefixo(itens, "DIV-")
    assert {i.campos["taxa_contratada_pct"] for i in div.values()} == {D("1.5")}
    assert set(div) == {"DIV-REM-OP-PADRAO", "DIV-REM-OP-BRANCO"}


def test_spread_em_texto_desconhecido_gera_erro(cfg):
    taxas = _df([_taxa("Loja A", CNPJ_A, "linha 4", texto="a combinar")], leitor_taxas.COLUNAS_SAIDA)
    with pytest.raises(ErroRemessa, match="a combinar"):
        _calc(taxas, cfg, _op("OP-1", CNPJ_A, "10.00", "1.5000"))


def test_duplicata_identica_conta_uma_vez_e_gera_pendencia(taxas, cfg):
    itens = _calc(taxas, cfg,
                  _op("OP-1", CNPJ_A, "10.00", "1.2000", linha=6),
                  _op("OP-1", CNPJ_A, "10.00", "1.2000", linha=7, observacao="reprocessada"))
    assert _por_prefixo(itens, "COM-REM-")[f"COM-REM-{CNPJ_A}"].valor_reportado == D("5.00")
    dup = _por_prefixo(itens, "PEN-DUP-")["PEN-DUP-REM-OP-1"]
    assert dup.campos["tipo"] == "OPERACAO_DUPLICADA"
    assert dup.valor_reportado == D("10.00")


def test_duplicata_fica_a_primeira_linha(cfg):
    unicas, descartadas = deduplicar(_ponte(
        _op("OP-1", CNPJ_A, "10.00", "1.2000", linha=9, observacao="reprocessada"),
        _op("OP-1", CNPJ_A, "10.00", "1.2000", linha=8)), cfg)
    assert [u["linha_planilha"] for u in unicas] == [8]
    assert [d["linha_planilha"] for d in descartadas] == [9]


def test_duplicata_com_valores_diferentes_gera_erro(taxas, cfg):
    with pytest.raises(ErroRemessa, match="OP-1.*spread_brl"):
        _calc(taxas, cfg, _op("OP-1", CNPJ_A, "10.00", "1.2000"), _op("OP-1", CNPJ_A, "10.01", "1.2000"))


def test_fora_da_competencia_nao_entra_e_vira_pendencia(taxas, cfg):
    itens = _calc(taxas, cfg, _op("OP-1", CNPJ_A, "10.00", "1.2000"),
                  _op("OP-AGO", CNPJ_A, "20.00", "1.5000", dia=date(2031, 2, 28)))
    assert _por_prefixo(itens, "COM-REM-")[f"COM-REM-{CNPJ_A}"].valor_reportado == D("5.00")
    assert "DIV-REM-OP-AGO" not in {i.id_saida for i in itens}
    pen = _por_prefixo(itens, "PEN-FORA-")["PEN-FORA-REM-OP-AGO"]
    assert pen.valor_reportado == D("20.00")


def test_cnpj_fora_da_planilha_tem_comissao_e_pendencia(taxas, cfg):
    itens = _calc(taxas, cfg, _op("OP-1", CNPJ_FORA, "10.00", "1.9000", cliente="NOVA LOJA"))
    com = _por_prefixo(itens, "COM-REM-")[f"COM-REM-{CNPJ_FORA}"]
    assert com.valor_reportado == D("5.00") and com.campos["lojista"] == "NOVA LOJA"
    pen = _por_prefixo(itens, "PEN-NAOCAD-")[f"PEN-NAOCAD-REM-{CNPJ_FORA}"]
    assert pen.campos["tipo"] == "LOJISTA_NAO_CADASTRADO" and pen.valor_reportado == D("5.00")
    assert not _por_prefixo(itens, "DIV-")
    assert _por_prefixo(itens, "NF-")["NF-REM-75374179000146"].valor_reportado == D("5.00")


def test_total_zero_nao_gera_nota_e_gera_pendencia(taxas, cfg):
    itens = _calc(taxas, cfg, _op("OP-NEG", CNPJ_A, "-10.00", "-1.0000"))
    assert not _por_prefixo(itens, "NF-")
    pen = _por_prefixo(itens, "PEN-NF-")["PEN-NF-REM-75374179000146"]
    assert pen.campos["tipo"] == "NOTA_NAO_EMITIDA" and pen.valor_reportado == D("0.00")


def test_pendencia_do_ted_tem_o_valor_e_as_origens_da_nota(taxas, cfg):
    # R18: conferir o TED contra a nota, sem supor desconto
    itens = _calc(taxas, cfg, _op("OP-1", CNPJ_A, "10.00", "1.2000"), _op("OP-2", CNPJ_B, "7.01", "1.5000"),
                  _op("OP-NEG", CNPJ_B, "-10.00", "-1.0000"))
    nf = _por_prefixo(itens, "NF-")["NF-REM-75374179000146"]
    ted = _por_prefixo(itens, "PEN-TED-")["PEN-TED-PONTE"]
    assert ted.valor_reportado == nf.valor_reportado == D("8.51")
    assert ted.origens == nf.origens
    assert ted.campos["ref_origem"] == ["OP-1", "OP-2"]
    assert ted.campos["tipo"] == "CONFERENCIA_REPASSE"
    assert ted.campos["motivo"] == ("conferir se o TED de repasse da Ponte bate com a nota de intermediação - "
                                    "não supor desconto (R18)")


def test_textos_sem_ponto_e_virgula(taxas, cfg):
    itens = _calc(taxas, cfg, _op("OP-1", CNPJ_FORA, "10.00", "1.9000", cliente="NOVA; LOJA"),
                  _op("OP-1", CNPJ_FORA, "10.00", "1.9000", cliente="NOVA; LOJA", observacao="reprocessada"),
                  _op("OP-NEG", CNPJ_B, "-10.00", "-1.0000"))
    assert _por_prefixo(itens, "COM-")[f"COM-REM-{CNPJ_FORA}"].campos["lojista"] == "NOVA - LOJA"
    textos = [v for i in itens for k, v in i.campos.items() if isinstance(v, str)]
    assert textos and not [t for t in textos if ";" in t]


def test_sinteticos_gravam_e_validam(taxas, cfg, tmp_path):
    itens = _calc(taxas, cfg, _op("OP-1", CNPJ_A, "10.00", "1.5000"),
                  _op("OP-1", CNPJ_A, "10.00", "1.5000", observacao="reprocessada"),
                  _op("OP-NEG", CNPJ_B, "-10.00", "-1.0000"), _op("OP-X", CNPJ_FORA, "3.00", "1.5000"))
    gravar_saida(tmp_path, itens)
    assert validar_saida(tmp_path) == []


# ================================================================ setembro/2026 (referência)

PONTE = "75374179000146"
MUNDO_ABERTO = "17217888000111"
NOVO_HORIZONTE = "66564512000199"
NEGATIVOS = {"PC-0926-0210": D("-1351.87"), "PC-0926-0326": D("-1001.30"),
             "PC-0926-0491": D("-574.90"), "PC-0926-0545": D("-637.91")}


@pytest.fixture(scope="module")
def entradas():
    return ler_entradas(ENTRADA, "2026-09")


@pytest.fixture(scope="module")
def itens(entradas):
    return remessa(entradas)


def test_set_operacoes_unicas_e_na_comissao(entradas, itens):
    unicas, _ = deduplicar(entradas.ponte, carregar_config())
    assert len(unicas) == 232
    nf = _por_prefixo(itens, "NF-")[f"NF-REM-{PONTE}"]
    assert len(nf.origens) == 228


def test_set_comissao_total_e_lojistas(itens):
    com = _por_prefixo(itens, "COM-")
    assert len(com) == 14
    assert sum(i.valor_reportado for i in com.values()) == D("39543.45")
    assert all(i.campos["linha_negocio"] == "REMESSA" for i in com.values())


@pytest.mark.parametrize("cnpj, valor", [
    (MUNDO_ABERTO, "3547.69"),
    ("95927868000148", "4918.34"),  # Rota Global
    ("34671260000100", "4295.03"),  # Maple Study
    ("50900987000179", "1292.67"),  # Bagagem Livre
    ("67869675000142", "363.22"),   # Bem-Vindo
])
def test_set_comissao_por_lojista(itens, cnpj, valor):
    assert _por_prefixo(itens, "COM-")[f"COM-REM-{cnpj}"].valor_reportado == D(valor)


def test_set_nota_unica(itens):
    notas = _por_prefixo(itens, "NF-")
    assert list(notas) == [f"NF-REM-{PONTE}"]
    nf = notas[f"NF-REM-{PONTE}"]
    assert nf.campos["tomador_cnpj"] == PONTE
    assert nf.valor_reportado == D("39543.45")


def test_set_divergencias(itens):
    div = _por_prefixo(itens, "DIV-")
    assert len(div) == 27
    mundo = [i for i in div.values() if i.campos["cnpj"] == MUNDO_ABERTO]
    assert len(mundo) == 23
    assert sum(i.valor_reportado for i in mundo) == D("1418.85")
    outras = {i.campos["ref_origem"]: i for i in div.values() if i.campos["cnpj"] != MUNDO_ABERTO}
    assert {r: i.valor_reportado for r, i in outras.items()} == NEGATIVOS
    assert sum(NEGATIVOS.values()) == D("-3565.98")
    nh = outras["PC-0926-0545"]
    assert nh.campos["cnpj"] == NOVO_HORIZONTE and nh.campos["taxa_contratada_pct"] == D("1.4")


def test_set_oscilacao_dos_demais_abaixo_da_tolerancia(entradas, itens):
    cfg = carregar_config()
    divergentes = {i.campos["ref_origem"] for i in _por_prefixo(itens, "DIV-").values()}
    contratos = Contratos(entradas.taxas, cfg)
    unicas, _ = deduplicar(entradas.ponte, cfg)
    oscilacao = max(abs(op["spread_pct"] - contratos.spread_contratado(op["cnpj"], op["data_contratacao"])[0])
                    for op in unicas if op["ref_origem"] not in divergentes)
    assert oscilacao == D("0.0016")


def test_set_pendencias(itens):
    pen = _por_prefixo(itens, "PEN-")
    assert pen["PEN-DUP-REM-PC-0926-0162"].valor_reportado == D("821.88")
    assert pen[f"PEN-CONTEST-REM-{MUNDO_ABERTO}"].valor_reportado == D("1418.85")
    assert len(pen[f"PEN-CONTEST-REM-{MUNDO_ABERTO}"].campos["ref_origem"]) == 23
    assert {r: pen[f"PEN-NEG-REM-{r}"].valor_reportado for r in NEGATIVOS} == NEGATIVOS
    ted = pen["PEN-TED-PONTE"]
    nf = _por_prefixo(itens, "NF-")[f"NF-REM-{PONTE}"]
    assert ted.valor_reportado == nf.valor_reportado == D("39543.45")
    assert ted.origens == nf.origens and len(ted.campos["ref_origem"]) == 228
    assert not [p for p in pen if p.startswith(("PEN-FORA-", "PEN-NAOCAD-", "PEN-NF-"))]


def test_set_rastro_e_validar_saida_com_checkout(entradas, itens, tmp_path):
    gravar_saida(tmp_path, [*checkout(entradas), *itens])
    assert validar_saida(tmp_path) == []
