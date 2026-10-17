"""Infraestrutura de saída com itens sintéticos (nenhum valor de competência real)."""

import csv
from datetime import date, datetime
from decimal import Decimal

import pytest

from tarvo.saida import (
    ARQUIVOS,
    COMISSOES,
    DIVERGENCIAS,
    LANCAMENTOS,
    NOTAS,
    PENDENCIAS,
    RASTRO,
    ErroSaida,
    ItemSaida,
    Origem,
    gravar_saida,
    validar_saida,
)

D = Decimal
CNPJ_A = "00123456000190"  # zeros à esquerda de propósito
CNPJ_B = "98765432000155"


def comissao(id_saida="COM-1", valor=D("10.50"), **campos):
    base = {"cnpj": CNPJ_A, "lojista": "Loja Teste Ltda", "linha_negocio": "CHECKOUT"}
    return ItemSaida(id_saida, COMISSOES.nome, {**base, **campos}, valor,
                     [("entrada_a.csv", "T1", D("4.25")), ("entrada_a.csv", "T2", valor - D("4.25"))])


def divergencia(id_saida="DIV-1", **campos):
    base = {"cnpj": CNPJ_B, "linha_negocio": "REMESSA", "ref_origem": "OP-7",
            "taxa_contratada_pct": D("1.2"), "taxa_aplicada_pct": D("1.5012")}
    return ItemSaida(id_saida, DIVERGENCIAS.nome, {**base, **campos}, D("-3.10"),
                     [("entrada_b.eml", "OP-7", D("-3.10"))])


def nota(id_saida="NF-1", **campos):
    base = {"tomador_cnpj": CNPJ_A, "tomador": "Loja Teste Ltda", "linha_negocio": "CHECKOUT",
            "discriminacao": "Serviço de teste; competência 2031-03"}
    return ItemSaida(id_saida, NOTAS.nome, {**base, **campos}, D("10.50"),
                     [("entrada_a.csv", "T1", D("4.25")), ("entrada_a.csv", "T2", D("6.25"))])


def lancamento(id_saida="LAN-1", **campos):
    base = {"banco": "AURORA", "ref_origem": "L12", "data": date(2031, 3, 15),
            "descricao": "TARIFA DE TESTE", "conta_codigo": "9.9.99", "metodo": "REGRA",
            "confianca": D("1")}
    return ItemSaida(id_saida, LANCAMENTOS.nome, {**base, **campos}, D("-0.99"),
                     [("extrato.csv", "L12", D("-0.99"))])


def pendencia(id_saida="PEN-1", **campos):
    base = {"tipo": "TESTE", "ref_origem": ["T1", "T2"], "motivo": "agrupa duas linhas",
            "quem_decide": "Financeiro"}
    return ItemSaida(id_saida, PENDENCIAS.nome, {**base, **campos}, D("1000.00"),
                     [("entrada_a.csv", "T1", D("999.99")), ("entrada_a.csv", "T2", D("0.01"))])


def ler(caminho):
    with open(caminho, encoding="utf-8", newline="") as f:
        return list(csv.reader(f, delimiter=";"))


# ---------------------------------------------------------------- criação do item

def test_soma_das_origens_diferente_gera_erro_na_criacao():
    with pytest.raises(ErroSaida, match="soma das origens"):
        ItemSaida("COM-1", COMISSOES.nome, {}, D("10.00"), [("a.csv", "T1", D("9.99"))])


def test_origem_sem_valor_so_fecha_com_zero():
    ItemSaida("PEN-Z", PENDENCIAS.nome, {}, D("0.00"), [])
    with pytest.raises(ErroSaida, match="soma das origens"):
        ItemSaida("PEN-Z", PENDENCIAS.nome, {}, D("0.01"), [])


def test_origens_viram_origem_e_valor_float_eh_recusado():
    item = comissao()
    assert all(isinstance(o, Origem) for o in item.origens)
    with pytest.raises(ErroSaida, match="Decimal"):
        ItemSaida("COM-1", COMISSOES.nome, {}, D("0.10"), [("a.csv", "T1", 0.1)])
    with pytest.raises(ErroSaida, match="Decimal"):
        ItemSaida("COM-1", COMISSOES.nome, {}, 0.1, [("a.csv", "T1", D("0.10"))])


def test_valor_com_mais_de_2_casas_eh_recusado_sem_arredondar():
    with pytest.raises(ErroSaida, match="mais casas"):
        ItemSaida("COM-1", COMISSOES.nome, {}, D("0.005"), [("a.csv", "T1", D("0.005"))])


def test_prefixo_e_arquivo_validados_na_criacao():
    with pytest.raises(ErroSaida, match="prefixo COM-"):
        ItemSaida("NF-1", COMISSOES.nome, {}, D("0.00"), [])
    with pytest.raises(ErroSaida, match="não é um dos"):
        ItemSaida("COM-1", "rastro.csv", {}, D("0.00"), [])


def test_campo_de_valor_divergente_do_valor_reportado_gera_erro():
    with pytest.raises(ErroSaida, match="comissao_brl"):
        comissao(comissao_brl=D("99.00"))


# ---------------------------------------------------------------- escrita: unicidade e domínios

def test_id_saida_duplicado_gera_erro(tmp_path):
    with pytest.raises(ErroSaida, match="duplicado: COM-1"):
        gravar_saida(tmp_path, [comissao("COM-1"), comissao("COM-1")])
    assert not any(tmp_path.iterdir())  # nada gravado


@pytest.mark.parametrize("item, trecho", [
    (lambda: comissao(linha_negocio="OUTRA"), "linha_negocio"),
    (lambda: lancamento(banco="ITAU"), "banco"),
    (lambda: lancamento(metodo="CHUTE"), "metodo"),
    (lambda: lancamento(confianca=D("1.01")), "fora de 0 a 1"),
    (lambda: lancamento(confianca=D("-0.01")), "fora de 0 a 1"),
    (lambda: lancamento(confianca=D("0.875")), "mais casas"),
    (lambda: lancamento(data=datetime(2031, 3, 15, 10, 0)), "datetime.date"),
    (lambda: lancamento(data="2031-03-15"), "datetime.date"),
    (lambda: comissao(cnpj="0123456000190"), "14 dígitos"),
    (lambda: comissao(cnpj="00.123.456/0001-90"), "14 dígitos"),
    (lambda: comissao(cnpj=123456000190), "14 dígitos"),
    (lambda: divergencia(taxa_aplicada_pct=D("1.50123")), "mais casas"),
    (lambda: divergencia(taxa_contratada_pct=1.2), "Decimal"),
    (lambda: divergencia(ref_origem="OP-1|OP-2"), "não pode conter"),
    (lambda: pendencia(ref_origem=[]), "vazia"),
    (lambda: pendencia(ref_origem=["T1", ""]), "não vazio"),
    (lambda: nota(discriminacao="duas\nlinhas"), "quebra de linha"),
    (lambda: nota(tomador="  "), "não vazio"),
], ids=lambda x: x if isinstance(x, str) else "")
def test_dominio_invalido_gera_erro_na_escrita(tmp_path, item, trecho):
    with pytest.raises(ErroSaida, match=trecho):
        gravar_saida(tmp_path, [item()])


def test_coluna_obrigatoria_ausente_gera_erro(tmp_path):
    item = ItemSaida("COM-9", COMISSOES.nome, {"cnpj": CNPJ_A, "linha_negocio": "CHECKOUT"}, D("0.00"), [])
    with pytest.raises(ErroSaida, match="'lojista'"):
        gravar_saida(tmp_path, [item])


# ---------------------------------------------------------------- formato

def test_formato_de_numero_data_e_cnpj(tmp_path):
    zero_negativo = ItemSaida("COM-0", COMISSOES.nome,
                              {"cnpj": CNPJ_B, "lojista": "Zero", "linha_negocio": "REMESSA"},
                              D("-0.00"), [("a.csv", "T9", D("-0.00"))])
    gravar_saida(tmp_path, [comissao(valor=D("1234.5")), zero_negativo, divergencia(), lancamento()])

    com = ler(tmp_path / COMISSOES.nome)
    assert com[1] == ["COM-1", CNPJ_A, "Loja Teste Ltda", "CHECKOUT", "1234.50"]
    assert com[2][-1] == "0.00"

    div = ler(tmp_path / DIVERGENCIAS.nome)
    assert div[1] == ["DIV-1", CNPJ_B, "REMESSA", "OP-7", "1.2000", "1.5012", "-3.10"]

    lan = ler(tmp_path / LANCAMENTOS.nome)
    assert lan[1] == ["LAN-1", "AURORA", "L12", "2031-03-15", "TARIFA DE TESTE", "-0.99", "9.9.99", "REGRA", "1.00"]

    rastro = ler(tmp_path / RASTRO.nome)
    assert ["COM-1", "entrada_a.csv", "T2", "1230.25"] in rastro
    assert ["COM-0", "a.csv", "T9", "0.00"] in rastro


def test_bytes_utf8_sem_bom_com_fim_de_linha_lf(tmp_path):
    gravar_saida(tmp_path, [nota(tomador="Ação Câmbio Ltda")])
    bruto = (tmp_path / NOTAS.nome).read_bytes()
    assert not bruto.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in bruto
    assert bruto.endswith(b"\n")
    assert "Ação Câmbio Ltda".encode("utf-8") in bruto
    assert bruto.split(b"\n")[0] == b"id_saida;tomador_cnpj;tomador;linha_negocio;valor_brl;discriminacao"


def test_cabecalhos_obrigatorios_mesmo_sem_itens(tmp_path):
    gravar_saida(tmp_path, [])
    esperados = {
        "comissoes_por_lojista.csv": "id_saida;cnpj;lojista;linha_negocio;comissao_brl",
        "divergencias_taxa.csv": "id_saida;cnpj;linha_negocio;ref_origem;taxa_contratada_pct;taxa_aplicada_pct;diferenca_brl",
        "notas_a_emitir.csv": "id_saida;tomador_cnpj;tomador;linha_negocio;valor_brl;discriminacao",
        "lancamentos_classificados.csv": "id_saida;banco;ref_origem;data;descricao;valor;conta_codigo;metodo;confianca",
        "pendencias.csv": "id_saida;tipo;ref_origem;valor_brl;motivo;quem_decide",
        "rastro.csv": "id_saida;arquivo_origem;ref_origem;valor",
    }
    for nome, cabecalho in esperados.items():
        assert (tmp_path / nome).read_text(encoding="utf-8") == cabecalho + "\n"
    assert validar_saida(tmp_path) == []


def test_colunas_extras_vem_depois_das_obrigatorias(tmp_path):
    a = comissao("COM-1", observacao="primeira")
    b = comissao("COM-2", qtd_transacoes=3, data_ref=date(2031, 3, 1))
    gravar_saida(tmp_path, [a, b])
    linhas = ler(tmp_path / COMISSOES.nome)
    assert linhas[0] == list(COMISSOES.nomes) + ["observacao", "qtd_transacoes", "data_ref"]
    assert linhas[1][-3:] == ["primeira", "", ""]
    assert linhas[2][-3:] == ["", "3", "2031-03-01"]
    assert validar_saida(tmp_path) == []


# ---------------------------------------------------------------- validar_saida

@pytest.fixture
def saida_valida(tmp_path):
    gravar_saida(tmp_path, [comissao(), divergencia(), nota(), lancamento(), pendencia()])
    assert validar_saida(tmp_path) == []
    return tmp_path


def _reescrever(caminho, antigo, novo):
    texto = caminho.read_text(encoding="utf-8")
    assert antigo in texto
    caminho.write_text(texto.replace(antigo, novo), encoding="utf-8", newline="")


def test_validar_acha_rastro_adulterado(saida_valida):
    _reescrever(saida_valida / RASTRO.nome, "PEN-1;entrada_a.csv;T2;0.01", "PEN-1;entrada_a.csv;T2;0.02")
    problemas = validar_saida(saida_valida)
    assert len(problemas) == 1
    assert "PEN-1" in problemas[0] and "1000.01" in problemas[0] and "1000.00" in problemas[0]


def test_validar_acha_linha_de_rastro_removida(saida_valida):
    _reescrever(saida_valida / RASTRO.nome, "DIV-1;entrada_b.eml;OP-7;-3.10\n", "")
    problemas = validar_saida(saida_valida)
    assert any("DIV-1" in p and "soma do rastro (0.00)" in p for p in problemas)


def test_validar_acha_id_do_rastro_inexistente(saida_valida):
    with open(saida_valida / RASTRO.nome, "a", encoding="utf-8", newline="") as f:
        f.write("COM-404;x.csv;T1;0.00\n")
    problemas = validar_saida(saida_valida)
    assert any("COM-404" in p and "não existe" in p for p in problemas)


def test_validar_acha_valor_reportado_adulterado(saida_valida):
    _reescrever(saida_valida / NOTAS.nome, ";10.50;", ";10.51;")
    problemas = validar_saida(saida_valida)
    assert any("NF-1" in p and "10.51" in p for p in problemas)


@pytest.mark.parametrize("arquivo, antigo, novo, trecho", [
    (COMISSOES.nome, CNPJ_A, CNPJ_A[1:], "cnpj"),
    (LANCAMENTOS.nome, "2031-03-15", "15/03/2031", "data"),
    (LANCAMENTOS.nome, "2031-03-15", "2031-02-30", "data"),
    (LANCAMENTOS.nome, ";1.00\n", ";1.5\n", "confianca"),
    (LANCAMENTOS.nome, "AURORA", "ITAU", "banco"),
    (LANCAMENTOS.nome, "REGRA", "IA?", "metodo"),
    (DIVERGENCIAS.nome, "1.2000", "1,2000", "taxa_contratada_pct"),
    (DIVERGENCIAS.nome, "REMESSA", "CAMBIO", "linha_negocio"),
    (NOTAS.nome, ";10.50;", ";10.5;", "valor_brl"),
    (COMISSOES.nome, "COM-1;", "NF-77;", "prefixo COM-"),
    (COMISSOES.nome, "linha_negocio;comissao_brl", "comissao_brl;linha_negocio", "cabeçalho"),
])
def test_validar_acha_formato_invalido(saida_valida, arquivo, antigo, novo, trecho):
    _reescrever(saida_valida / arquivo, antigo, novo)
    problemas = validar_saida(saida_valida)
    assert any(trecho in p for p in problemas), problemas


def test_validar_acha_bom_crlf_e_arquivo_ausente(saida_valida):
    caminho = saida_valida / NOTAS.nome
    caminho.write_bytes(b"\xef\xbb\xbf" + caminho.read_bytes().replace(b"\n", b"\r\n"))
    (saida_valida / PENDENCIAS.nome).unlink()
    problemas = validar_saida(saida_valida)
    assert any("BOM" in p for p in problemas)
    assert any("\\r" in p for p in problemas)
    assert any("pendencias.csv: arquivo não encontrado" in p for p in problemas)


def test_validar_acha_id_repetido_entre_arquivos(saida_valida):
    with open(saida_valida / COMISSOES.nome, "a", encoding="utf-8", newline="") as f:
        f.write(f"COM-1;{CNPJ_B};Outra;REMESSA;0.00\n")
    problemas = validar_saida(saida_valida)
    assert any("COM-1" in p and "repetido" in p for p in problemas)


# ---------------------------------------------------------------- ponta a ponta

def test_ponta_a_ponta_grava_e_rele(tmp_path):
    itens = [
        comissao("COM-A", valor=D("10.50")),
        comissao("COM-B", valor=D("-2.00"), cnpj=CNPJ_B, lojista="Loja; com separador", linha_negocio="REMESSA"),
        divergencia("DIV-A"),
        nota("NF-A"),
        lancamento("LAN-A"),
        lancamento("LAN-B", banco="MERIDIANO", ref_origem="FIT-1", metodo="IA", confianca=D("0.73")),
        pendencia("PEN-A"),
        pendencia("PEN-B", ref_origem="X1|X2|X3"),
    ]
    gravados = gravar_saida(tmp_path / "nova" / "pasta", itens)
    assert set(gravados) == {e.nome for e in ARQUIVOS}
    assert validar_saida(tmp_path / "nova" / "pasta") == []

    pasta = tmp_path / "nova" / "pasta"
    com = ler(pasta / COMISSOES.nome)
    assert com[2] == ["COM-B", CNPJ_B, "Loja; com separador", "REMESSA", "-2.00"]
    pen = ler(pasta / PENDENCIAS.nome)
    assert [l[2] for l in pen[1:]] == ["T1|T2", "X1|X2|X3"]
    lan = ler(pasta / LANCAMENTOS.nome)
    assert lan[2][1] == "MERIDIANO" and lan[2][-2:] == ["IA", "0.73"]

    rastro = ler(pasta / RASTRO.nome)
    assert rastro[0] == list(RASTRO.nomes)
    assert len(rastro) - 1 == sum(len(i.origens) for i in itens)
    somas = {}
    for id_saida, _, _, valor in rastro[1:]:
        somas[id_saida] = somas.get(id_saida, D("0")) + D(valor)
    assert somas == {i.id_saida: i.valor_reportado for i in itens}
