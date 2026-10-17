"""Extratos bancários: regras com dados sintéticos e valores de referência de setembro/2026.

Os valores de referência vêm de uma análise independente. Se algum não bater, não ajuste o teste:
investigue os lançamentos responsáveis.
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from tarvo.bancos import (
    AURORA,
    MERIDIANO,
    ErroBancos,
    bancos,
    carregar_config,
    classificar,
    conferir_pix_remessas,
    conferir_ted_liquidacao,
    conferir_transferencias,
    item_lancamento,
    pendencias_lancamentos,
    proximo_dia_util,
)
from tarvo.checkout import checkout
from tarvo.fechamento import ler_entradas
from tarvo.remessa import remessa
from tarvo.saida import gravar_saida, validar_saida

D = Decimal
ENTRADA = Path(__file__).resolve().parents[1] / "dados" / "2026-09"
CONFIG = Path(__file__).resolve().parents[1] / "config"


@pytest.fixture(scope="module")
def entradas():
    return ler_entradas(ENTRADA, "2026-09")


@pytest.fixture(scope="module")
def cfg(entradas):
    return carregar_config(entradas.plano_contas, entradas.taxas)


@pytest.fixture(scope="module")
def itens(entradas):
    return bancos(entradas)


def _por_prefixo(itens, prefixo):
    return {i.id_saida: i for i in itens if i.id_saida.startswith(prefixo)}


# ================================================================ dados sintéticos

_ref = iter(range(1, 10_000))


def _linha(descricao, valor, dia=date(2031, 3, 10), ref=None, arquivo="extrato_teste"):
    return {"arquivo_origem": arquivo, "ref_origem": ref or f"R{next(_ref)}", "data": dia,
            "descricao": descricao, "valor": D(valor)}


def _um(banco, cfg, descricao, valor, **kw):
    return classificar(banco, [_linha(descricao, valor, **kw)], cfg)[0]


def _op(ref, cnpj, valor_brl, iof="0.00", dia=date(2031, 3, 10)):
    return {"arquivo_origem": "ponte_teste.xlsx", "ref_origem": ref, "data_contratacao": dia, "cnpj": cnpj,
            "valor_brl": D(valor_brl), "iof_brl": D(iof)}


def _gravar_yaml(caminho, conteudo):
    with open(caminho, "w", encoding="utf-8") as f:
        yaml.safe_dump(conteudo, f, allow_unicode=True)
    return caminho


def _config_bruta():
    with open(CONFIG / "bancos.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_primeira_regra_que_casa_vence(cfg):
    l = _um(AURORA, cfg, "PIX ENVIADO CONTABILIDADE EXATA LTDA", "-10.00")
    assert (l.regra.conta_codigo, l.regra.fonte) == ("4.2.06", "R19")


def test_favorecido_da_lista_e_repasse_com_o_cnpj_da_lista(cfg):
    novo = _um(AURORA, cfg, "PIX ENVIADO NOVO HORIZONTE INTERCAMBIO", "-10.00")
    viagens = _um(AURORA, cfg, "PIX ENVIADO HORIZONTE VIAGENS E TURISM", "-10.00")
    assert novo.regra.conta_codigo == viagens.regra.conta_codigo == "2.1.01.001"
    assert (novo.contraparte.cnpj, viagens.contraparte.cnpj) == ("66564512000199", "78576234000179")
    atlas = _um(AURORA, cfg, "PIX ENVIADO ATLAS IDIOMAS LTDA", "-10.00")
    assert (atlas.contraparte.cnpj, atlas.contraparte.ec, atlas.contraparte.sem_contrato) == (None, "1076801732", True)


@pytest.mark.parametrize("descricao", ["PIX ENVIADO HORIZONTE VIAGENS", "PIX ENVIADO FORNECEDOR QUALQUER",
                                       "PIX ENVIADO novo horizonte intercambio"])
def test_favorecido_fora_da_lista_fica_sem_regra_humano_com_pendencia(cfg, descricao):
    l = _um(AURORA, cfg, descricao, "-10.00", ref="L7")
    assert l.regra is None
    item = item_lancamento(l, cfg)
    assert (item.campos["metodo"], item.campos["confianca"], item.campos["conta_codigo"]) == ("HUMANO", D("0.00"), "A_CLASSIFICAR")
    [pen] = pendencias_lancamentos([l], cfg)
    assert (pen.id_saida, pen.campos["tipo"], pen.valor_reportado) == ("PEN-SEMREGRA-L7", "LANCAMENTO_SEM_REGRA", D("-10.00"))
    assert [(o.ref_origem, o.valor) for o in pen.origens] == [("L7", D("-10.00"))]


def test_sentido_errado_nao_casa(cfg):
    assert _um(AURORA, cfg, "TED RECEBIDA 99.876.669/0001-09 ORBE ADQUIRENCIA SA", "-5.00").regra is None
    assert _um(MERIDIANO, cfg, "TARIFA PACOTE CAMBIO", "5.00").regra is None


def test_lancamento_classificado_rastro_e_a_propria_linha(cfg):
    l = _um(MERIDIANO, cfg, "IOF S/ OPERACAO CREDITO", "-48.21", ref="MRDX1", arquivo="mer.ofx")
    item = item_lancamento(l, cfg)
    assert item.id_saida == "LAN-MER-MRDX1"
    assert item.campos == {"banco": "MERIDIANO", "ref_origem": "MRDX1", "data": date(2031, 3, 10),
                           "descricao": "IOF S/ OPERACAO CREDITO", "conta_codigo": "4.3.01", "metodo": "REGRA",
                           "confianca": D("1.00")}
    assert [tuple(o) for o in item.origens] == [("mer.ofx", "MRDX1", D("-48.21"))]


def test_textos_sem_ponto_e_virgula(cfg):
    # a descrição é só exibição: a regra casa pelo texto original, a saída troca ";" por " - "
    l = _um(AURORA, cfg, "PIX ENVIADO FORNECEDOR; QUALQUER", "-10.00", ref="L8")
    devol = _um(AURORA, cfg, "DEVOLUCAO PIX - MUNDO ABERTO INTERC", "12.00", ref="L9")
    item = item_lancamento(l, cfg)
    assert item.campos["descricao"] == "PIX ENVIADO FORNECEDOR - QUALQUER"
    textos = [v for i in [item, *pendencias_lancamentos([l, devol], cfg)] for v in i.campos.values()
              if isinstance(v, str)]
    assert textos and not [t for t in textos if ";" in t]


def test_pendencias_r20(cfg):
    naoid = _um(AURORA, cfg, "PIX RECEBIDO 00000000000000 SEM IDENTIFICACAO", "50.00", ref="L3")
    devol = _um(AURORA, cfg, "DEVOLUCAO PIX - LOJA QUALQUER", "20.00", ref="L4")
    assert devol.regra.confianca == D("0.80") and devol.regra.conta_codigo == "2.1.01.001"
    pens = {p.id_saida: p for p in pendencias_lancamentos([naoid, devol], cfg)}
    assert set(pens) == {"PEN-NAOID-L3", "PEN-DEVOL-PIX-L4"}
    assert pens["PEN-NAOID-L3"].valor_reportado == D("50.00")
    assert pens["PEN-DEVOL-PIX-L4"].campos["quem_decide"] == "Financeiro (Helena)"


def test_conta_inexistente_ou_sintetica_no_config_e_erro(entradas, tmp_path):
    for conta in ("9.9.99", "1.1.09"):  # inexistente; sintética (aceita_lancto=N)
        bruta = _config_bruta()
        bruta["regras"]["AURORA"][0]["conta_codigo"] = conta
        caminho = _gravar_yaml(tmp_path / "bancos.yaml", bruta)
        with pytest.raises(ErroBancos, match="não aceita lançamento"):
            carregar_config(entradas.plano_contas, entradas.taxas, caminho)


def test_cnpj_da_lista_fora_da_planilha_e_erro(entradas, tmp_path):
    caminho = _gravar_yaml(tmp_path / "fav.yaml", {"favorecidos": {"LOJA X": {"cnpj": "11111111000111"}}})
    with pytest.raises(ErroBancos, match="não está na planilha"):
        carregar_config(entradas.plano_contas, entradas.taxas, favorecidos=caminho)


def test_ted_liquidacao_por_data_de_contratacao(cfg):
    teds = classificar(MERIDIANO, [_linha("TED ENVIADA PONTE CAMBIO SA LIQ OPERACOES", "-110.50", ref="T1"),
                                   _linha("TED ENVIADA PONTE CAMBIO SA LIQ OPERACOES", "-50.00", ref="T2",
                                          dia=date(2031, 3, 11))], cfg)
    ops = [_op("OP-1", "00520815000100", "100.00", "0.50"), _op("OP-2", "00520815000100", "10.00"),
           _op("OP-3", "00520815000100", "40.00", dia=date(2031, 3, 11)),
           _op("OP-FORA", "00520815000100", "99.00", dia=date(2031, 4, 1))]  # fora do período do extrato
    [pen] = conferir_ted_liquidacao(teds, ops, date(2031, 3, 1), date(2031, 3, 31), cfg)
    assert pen.id_saida == "PEN-TED-LIQ-2031-03-11"
    assert pen.valor_reportado == D("-10.00")  # operações - TEDs pagas
    assert {o.ref_origem for o in pen.origens} == {"T2", "OP-3"}


def test_pix_a_mais_e_adiantamento_e_pix_a_menos_e_pendencia(cfg):
    # R22: PIX do lojista acima das remessas do mês é adiantamento de remessa futura, sem pendência,
    # haja ou não um PIX único igual à sobra. PIX abaixo das remessas continua pendência no cliente (P12).
    pix = classificar(MERIDIANO, [_linha("PIX RECEB KIWI EXPERIENCE TURISMO", "100.00", ref="P1"),
                                  _linha("PIX RECEB KIWI EXPERIENCE TURISMO", "30.00", ref="P2"),
                                  _linha("PIX RECEB DUBLIN HUB INTERCÂMBIO L", "40.00", ref="P4"),
                                  _linha("PIX RECEB CANGURU INTERCÂMBIOS LTD", "70.00", ref="P3")], cfg)
    ops = [_op("OP-1", "07752116000126", "99.50", "0.50"), _op("OP-2", "53857560000123", "75.00"),
           _op("OP-3", "68567965000102", "25.00")]
    itens = conferir_pix_remessas(pix, ops, cfg)
    pens = {p.id_saida: p for p in itens}
    assert set(pens) == {"PEN-PIX-REM-53857560000123"}  # Kiwi (+30) e Dublin (+15) são adiantamento
    cliente = pens["PEN-PIX-REM-53857560000123"]
    assert cliente.campos["tipo"] == "DIFERENCA_PIX_REMESSA"
    assert cliente.valor_reportado == D("-5.00")  # PIX - operações
    assert [(o.ref_origem, o.valor) for o in cliente.origens] == [("P3", D("70.00")), ("OP-2", D("-75.00"))]
    adiantado = item_lancamento(pix[1], cfg)
    assert (adiantado.campos["conta_codigo"], adiantado.campos["metodo"], adiantado.campos["confianca"]) == (
        "2.1.02.001", "REGRA", D("1.00"))


def test_remessa_sem_pix_do_cliente_e_pendencia(cfg):
    itens = conferir_pix_remessas([], [_op("OP-9", "07752116000126", "50.00", "0.25")], cfg)
    assert [(p.id_saida, p.valor_reportado) for p in itens] == [("PEN-PIX-REM-07752116000126", D("-50.25"))]


@pytest.mark.parametrize("descricao, valor", [
    ("TED RECEB PONTE AEREA ESTUDANTIL REPASSE COMISSAO", "10.00"),
    ("TED ENVIADA PONTE AEREA ESTUDANTIL LIQ OPERACOES", "-10.00"),
])
def test_ponte_aerea_nao_casa_regra_da_ponte_cambio(cfg, descricao, valor):
    # R22: a Ponte Aérea Estudantil é lojista e não tem relação com a Ponte Câmbio
    assert _um(MERIDIANO, cfg, descricao, valor).regra is None


def test_pix_da_ponte_aerea_e_lojista_nas_duas_grafias(cfg):
    for descricao in ("PIX RECEB PONTE AÉREA ESTUDANTIL L", "PIX RECEB PONTE AEREA ESTUDANTIL L"):
        l = _um(MERIDIANO, cfg, descricao, "10.00")
        assert (l.regra.conta_codigo, l.papel, l.contraparte.cnpj) == ("2.1.02.001", "pix_cliente", "95739378000118")


def test_proximo_dia_util():
    assert proximo_dia_util(date(2031, 3, 14)) == date(2031, 3, 17)  # sexta -> segunda
    assert proximo_dia_util(date(2031, 3, 12)) == date(2031, 3, 13)


def test_transferencias_entre_contas(cfg):
    transf = "TRANSF ENTRE CONTAS P/ BCO MERIDIANO AG 0091 CC 90233-5"
    ted = "TED RECEBIDA TARVO PAGAMENTOS LTDA - MESMA TITULARIDADE"
    aur = classificar(AURORA, [_linha(transf, "-100.00", dia=date(2031, 3, 14), ref="L1"),   # sexta: chega segunda
                               _linha(transf, "-200.00", dia=date(2031, 3, 10), ref="L2"),   # sem par
                               _linha(transf, "-300.00", dia=date(2031, 3, 31), ref="L3")], cfg)  # em trânsito
    mer = classificar(MERIDIANO, [_linha(ted, "100.00", dia=date(2031, 3, 17), ref="M1"),
                                  _linha(ted, "200.00", dia=date(2031, 3, 12), ref="M2")], cfg)  # D+2: não casa
    pens = {p.id_saida: p for p in conferir_transferencias(aur, mer, date(2031, 3, 31), cfg)}
    assert set(pens) == {"PEN-TRANSF-L2", "PEN-TRANSF-L3"}
    assert pens["PEN-TRANSF-L2"].campos["tipo"] == "TRANSFERENCIA_SEM_PAR"
    l3 = pens["PEN-TRANSF-L3"]
    assert (l3.campos["tipo"], l3.valor_reportado) == ("TRANSFERENCIA_EM_TRANSITO", D("300.00"))
    assert "R20" in l3.campos["motivo"] and "01/04" in l3.campos["motivo"] and "abril" in l3.campos["motivo"]


# ================================================================ setembro/2026 (valores de referência)

def _lancamentos(itens):
    return [i for i in itens if i.id_saida.startswith("LAN-")]


def _por_conta(itens, banco):
    contas = defaultdict(lambda: [0, D("0.00")])
    for i in _lancamentos(itens):
        if i.campos["banco"] == banco:
            contas[i.campos["conta_codigo"]][0] += 1
            contas[i.campos["conta_codigo"]][1] += i.valor_reportado
    return {c: tuple(v) for c, v in contas.items()}


def test_setembro_184_lancamentos_todos_por_regra(itens):
    lan = _lancamentos(itens)
    assert len(lan) == 184
    assert sum(1 for i in lan if i.campos["banco"] == "AURORA") == 84
    assert sum(1 for i in lan if i.campos["banco"] == "MERIDIANO") == 100
    assert {i.campos["metodo"] for i in lan} == {"REGRA"}
    assert not _por_prefixo(itens, "PEN-SEMREGRA-")


def test_setembro_aurora_por_conta(itens):
    contas = _por_conta(itens, "AURORA")
    assert contas["1.1.03.001"] == (21, D("3557246.29"))
    assert contas["2.1.01.001"] == (45, D("-4217867.61"))
    assert contas["4.2.06"] == (1, D("-6800.00"))
    assert contas["1.1.09.001"] == (4, D("-1450000.00"))
    assert contas["4.2.01"] == (2, D("-576.50"))
    assert contas["1.1.09.002"] == (1, D("7350.00"))


def test_setembro_aurora_repasses_sao_44_pix_mais_a_devolucao(itens):
    repasses = [i for i in _lancamentos(itens) if i.campos["banco"] == "AURORA" and i.campos["conta_codigo"] == "2.1.01.001"]
    assert sum(1 for i in repasses if i.campos["descricao"].startswith("PIX ENVIADO ")) == 44
    assert [i.campos["ref_origem"] for i in repasses if i.campos["descricao"].startswith("DEVOLUCAO PIX")] == ["L65"]


def test_setembro_meridiano_por_conta(itens):
    contas = _por_conta(itens, "MERIDIANO")
    assert contas["2.1.02.001"] == (85, D("18240.00"))
    assert contas["1.1.09.001"] == (3, D("1150000.00"))
    assert contas["1.1.02.001"] == (6, D("-115243.00"))
    assert contas["1.1.03.002"] == (1, D("61884.12"))
    assert contas["4.2.01"] == (2, D("-579.90"))
    assert contas["3.2.01"][0] == contas["4.2.05"][0] == contas["4.3.01"][0] == 1
    passivo = [i for i in _lancamentos(itens) if i.campos["banco"] == "MERIDIANO" and i.campos["conta_codigo"] == "2.1.02.001"]
    assert sum(1 for i in passivo if i.campos["descricao"].startswith("PIX RECEB ")) == 64
    assert sum(1 for i in passivo if i.campos["descricao"].startswith("TED ENVIADA ")) == 21


def test_setembro_ted_liq_bate_com_a_ponte(itens):
    assert not _por_prefixo(itens, "PEN-TED-LIQ-")


def test_setembro_pix_da_ponte_aerea_e_adiantamento_sem_pendencia(itens):
    # R22 (Helena, 9h45): o PIX de 17/09 da Ponte Aérea Estudantil adianta uma remessa de outubro.
    assert not _por_prefixo(itens, "PEN-PIX-SEMREM-")
    assert not _por_prefixo(itens, "PEN-PIX-REM-")  # os 14 clientes fecham ou só adiantaram
    lan = _por_prefixo(itens, "LAN-MER-MRD2026090425")["LAN-MER-MRD2026090425"]
    assert lan.valor_reportado == D("18240.00")
    assert (lan.campos["conta_codigo"], lan.campos["metodo"], lan.campos["confianca"]) == ("2.1.02.001", "REGRA", D("1.00"))
    assert not [i for i in itens if i.id_saida.startswith("PEN-") and "MRD2026090425" in str(i.campos["ref_origem"])]


def test_setembro_uma_transferencia_em_transito(itens):
    transf = _por_prefixo(itens, "PEN-TRANSF-")
    assert list(transf) == ["PEN-TRANSF-L92"]
    pen = transf["PEN-TRANSF-L92"]
    assert pen.valor_reportado == D("300000.00")
    assert pen.campos["tipo"] == "TRANSFERENCIA_EM_TRANSITO"
    assert "R20" in pen.campos["motivo"] and "01/10" in pen.campos["motivo"] and "outubro" in pen.campos["motivo"]


def test_setembro_pendencias_r20(itens):
    naoid, devol = _por_prefixo(itens, "PEN-NAOID-"), _por_prefixo(itens, "PEN-DEVOL-PIX-")
    assert {k: v.valor_reportado for k, v in naoid.items()} == {"PEN-NAOID-L50": D("7350.00")}
    assert {k: v.valor_reportado for k, v in devol.items()} == {"PEN-DEVOL-PIX-L65": D("12400.00")}
    assert {p.campos["quem_decide"] for p in [*naoid.values(), *devol.values()]} == {"Financeiro (Helena)"}


def test_setembro_validar_saida_com_os_tres_modulos(entradas, itens, tmp_path):
    gravar_saida(tmp_path, [*checkout(entradas), *remessa(entradas), *itens])
    assert validar_saida(tmp_path) == []
