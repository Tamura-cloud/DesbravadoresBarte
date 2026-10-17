"""R31: ajuste da Ponte (linha nova, Nº de Operação próprio, Spread R$ negativo, observação "AJUSTE REF PC-...").

Substitui a versão anterior deste arquivo, que supunha outro formato: a linha de ajuste com o MESMO Nº de Operação e a
MESMA data da operação original e uma observação livre. A Helena (17/10/2026, 11h33) descreveu o formato real: Nº próprio,
Spread R$ negativo e a observação "AJUSTE REF <Nº da original>". O ajuste entra no mês em que aparece e abate a participação
da Tarvo dentro da nota única (P25); nunca é spread negativo (R23), divergência nem operação nova.

Parte 1: pack de outubro gerado em pasta temporária (dados/ só é lido), com a pasta de setembro ao lado.
Parte 2: casos sintéticos direto no módulo da remessa.
"""

import csv
import io
import shutil
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from email import policy
from email.parser import BytesParser
from pathlib import Path

import openpyxl
import pandas as pd
import pytest

from gerar_outubro import gerar
from tarvo.fechamento import fechar
from tarvo.leitores import ponte as leitor_ponte
from tarvo.leitores import taxas as leitor_taxas
from tarvo.leitores.ponte import ler_ponte
from tarvo.remessa import (
    Anterior,
    ErroRemessa,
    calcular_remessa,
    carregar_config,
    competencia_anterior,
    pasta_anterior,
)
from tarvo.saida import gravar_saida, validar_saida

D = Decimal
RAIZ = Path(__file__).resolve().parents[1]
SETEMBRO = RAIZ / "dados" / "2026-09"
MUNDO_ABERTO, CANGURU = "17217888000111", "53857560000123"
NF_REM = "NF-REM-75374179000146"
AJUSTE_A, AJUSTE_B = "PC-1026-9101", "PC-1026-9102"
ORIGINAL_A = "PC-0926-0434"   # uma das 23 da Mundo Aberto contestadas em setembro
ORIGINAL_INEXISTENTE = "PC-0926-9999"


def _ler(pasta: Path, nome: str) -> list[dict]:
    with open(pasta / nome, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _por_id(pasta: Path, nome: str) -> dict[str, dict]:
    return {l["id_saida"]: l for l in _ler(pasta, nome)}


def _inserir_linhas(eml: Path, linhas: list[dict]) -> None:
    """Insere linhas depois da última operação da aba "Operações" do anexo (chaves = cabeçalhos da planilha)."""
    with open(eml, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)
    anexo = next(p for p in msg.iter_attachments() if p.get_filename().lower().endswith(".xlsx"))
    wb = openpyxl.load_workbook(io.BytesIO(anexo.get_content()))
    ws = wb["Operações"]
    for linha in ws.iter_rows():
        valores = [c.value for c in linha]
        if "Nº Operação" in valores:
            titulos = {v: c.column for v, c in zip(valores, linha) if v}
            ultima = linha[0].row
            break
    while ws.cell(ultima + 1, titulos["Nº Operação"]).value:
        ultima += 1
    for nova in linhas:
        ws.insert_rows(ultima + 1)
        for titulo, valor in nova.items():
            c = ws.cell(ultima + 1, titulos[titulo], valor)
            c.number_format = ws.cell(ultima, titulos[titulo]).number_format
        ultima += 1
    saida = io.BytesIO()
    wb.save(saida)
    maintype, subtype = anexo.get_content_type().split("/")
    anexo.set_content(saida.getvalue(), maintype=maintype, subtype=subtype, disposition="attachment",
                      filename=anexo.get_filename())
    eml.write_bytes(msg.as_bytes())


def _montar_pack(raiz: Path, ajustes: bool) -> Path:
    """raiz/dados/2026-10 (outubro mínimo gerado de setembro) ao lado de raiz/dados/2026-09 (cópia de setembro)."""
    dados = raiz / "dados"
    shutil.copytree(SETEMBRO, dados / "2026-09")
    casos = gerar(SETEMBRO, dados / "2026-10")
    if ajustes:
        df, _ = ler_ponte(casos["ponte"]["arquivo"])
        dia = df["data_contratacao"].iloc[0].replace(day=15)
        data = datetime.combine(dia, datetime.min.time())
        _inserir_linhas(casos["ponte"]["arquivo"], [
            # CNPJ em branco: o lojista vem da operação original, achada em setembro
            {"Nº Operação": AJUSTE_A, "Data Contratação": data, "Spread R$": -235.74,
             "Observação": f"AJUSTE REF {ORIGINAL_A}"},
            # CNPJ preenchido, maiúsculas diferentes e ponto final; a original não existe em setembro
            {"Nº Operação": AJUSTE_B, "Data Contratação": data, "CNPJ Cliente": CANGURU, "Spread R$": -20.00,
             "Observação": f"ajuste ref {ORIGINAL_INEXISTENTE}."},
        ])
    return dados / "2026-10"


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    raiz = tmp_path_factory.mktemp("sem_ajuste")
    saida = raiz / "saida"
    return {"saida": saida, "resultado": fechar(_montar_pack(raiz, ajustes=False), saida, "2026-10", usar_ia=False)}


@pytest.fixture(scope="module")
def com(tmp_path_factory):
    raiz = tmp_path_factory.mktemp("com_ajuste")
    saida = raiz / "saida"
    return {"saida": saida, "resultado": fechar(_montar_pack(raiz, ajustes=True), saida, "2026-10", usar_ia=False),
            "eml_setembro": next((raiz / "dados" / "2026-09").glob("*.eml"))}


def _valor(saida: Path, arquivo: str, id_saida: str) -> Decimal:
    coluna = {"comissoes_por_lojista.csv": "comissao_brl", "notas_a_emitir.csv": "valor_brl", "pendencias.csv": "valor_brl"}[arquivo]
    return D(_por_id(saida, arquivo)[id_saida][coluna])


# ---------------------------------------------------------------- parte 1: pack de outubro

def test_outubro_sem_ajuste_continua_com_506_itens_e_sem_pendencia_de_ajuste(base):
    assert base["resultado"].itens == 506
    assert not [i for i in _ler(base["saida"], "pendencias.csv") if "AJUSTE" in i["id_saida"]]
    nf = _por_id(base["saida"], "notas_a_emitir.csv")[NF_REM]
    assert "ajuste" not in nf["discriminacao"]


def test_a_ajuste_abate_a_comissao_da_mundo_aberto_e_a_nota_pela_metade_do_spread(base, com):
    comissao = f"COM-REM-{MUNDO_ABERTO}"
    antes, depois = (_valor(x["saida"], "comissoes_por_lojista.csv", comissao) for x in (base, com))
    assert depois - antes == D("-117.87")  # 50% de -235,74 (P25), CNPJ em branco no ajuste
    nf_antes, nf_depois = (_valor(x["saida"], "notas_a_emitir.csv", NF_REM) for x in (base, com))
    # a nota cai também os -10,00 do ajuste B (Canguru): -117,87 e -10,00
    assert nf_depois - nf_antes == D("-127.87")
    assert _valor(com["saida"], "comissoes_por_lojista.csv", "COM-REM-" + CANGURU) - \
        _valor(base["saida"], "comissoes_por_lojista.csv", "COM-REM-" + CANGURU) == D("-10.00")


def test_a_ajuste_nao_vira_pen_neg_divergencia_nem_operacao_nova(com):
    ids = {i["id_saida"] for arquivo in ("pendencias.csv", "divergencias_taxa.csv") for i in _ler(com["saida"], arquivo)}
    for ref in (AJUSTE_A, AJUSTE_B):
        assert not [i for i in ids if i.endswith(ref) and not i.startswith("PEN-AJUSTE-")]
        assert f"PEN-NEG-REM-{ref}" not in ids and f"DIV-REM-{ref}" not in ids
    rastro = _ler(com["saida"], "rastro.csv")
    assert {l["id_saida"] for l in rastro if l["ref_origem"] == AJUSTE_A} == {f"COM-REM-{MUNDO_ABERTO}", NF_REM, "PEN-TED-PONTE"}
    assert com["resultado"].itens == 507  # os 506 de antes mais a PEN-AJUSTE-SEMORIG do ajuste B


def test_a_rastro_aponta_para_a_linha_de_ajuste_e_para_a_original_de_setembro(com):
    arquivo_setembro = ler_ponte(com["eml_setembro"])[1]["arquivo_origem"]
    linhas = [l for l in _ler(com["saida"], "rastro.csv") if l["id_saida"] == f"COM-REM-{MUNDO_ABERTO}"]
    ajuste = [l for l in linhas if l["ref_origem"] == AJUSTE_A]
    assert [(l["valor"], l["arquivo_origem"].startswith(com["eml_setembro"].name.replace("set2026", "out2026"))) for l in ajuste] == [("-117.87", True)]
    original = [l for l in linhas if l["ref_origem"] == ORIGINAL_A]
    assert [(l["valor"], l["arquivo_origem"]) for l in original] == [("0.00", arquivo_setembro)]
    assert sum(D(l["valor"]) for l in linhas) == _valor(com["saida"], "comissoes_por_lojista.csv", f"COM-REM-{MUNDO_ABERTO}")


def test_a_descricao_do_ajuste_cita_a_original_a_competencia_e_a_contestacao(com):
    nf = _por_id(com["saida"], "notas_a_emitir.csv")[NF_REM]["discriminacao"]
    assert f"AJUSTE REF {ORIGINAL_A} (operação de 2026-09, contestada em 2026-09)" in nf
    assert f"AJUSTE REF {ORIGINAL_INEXISTENTE} (operação original não encontrada em 2026-09)" in nf
    assert ";" not in nf


def test_b_original_inexistente_abate_mesmo_assim_e_abre_pendencia_para_a_helena(com):
    pen = _por_id(com["saida"], "pendencias.csv")
    p = pen[f"PEN-AJUSTE-SEMORIG-{AJUSTE_B}"]
    assert (p["tipo"], p["quem_decide"], D(p["valor_brl"]), p["ref_origem"]) == (
        "AJUSTE_SEM_OPERACAO_ORIGINAL", "Financeiro (Helena)", D("-10.00"), AJUSTE_B)
    assert ORIGINAL_INEXISTENTE in p["motivo"] and "2026-09" in p["motivo"]
    assert f"PEN-AJUSTE-SEMORIG-{AJUSTE_A}" not in pen  # a A tem original em setembro


def test_pack_com_ajuste_valida_e_o_rastro_fecha(com):
    assert validar_saida(com["saida"]) == []
    assert [l for l in _ler(com["saida"], "divergencias_taxa.csv") if l["ref_origem"] in (AJUSTE_A, AJUSTE_B)] == []


# ---------------------------------------------------------------- parte 2: casos sintéticos

CNPJ_A, CNPJ_B = "00111222000133", "44555666000177"
ARQ = "ponte_teste.eml#ops.xlsx"
COMP = "2031-03"
_linha = iter(range(6, 10_000))


def _taxa(lojista, cnpj, ref, spread=None):
    return {"arquivo_origem": "taxas_teste.xlsx", "ref_origem": ref, "lojista": lojista, "cnpj": cnpj, "ec": None,
            **{c: None for c in leitor_taxas.CAMPOS_TAXA}, "spread_remessa_pct": spread, "spread_remessa_texto": None,
            "vigencia_inicio": date(2031, 1, 1), "vigencia_fim": None, "obs": None}


def _op(ref, cnpj, spread_brl, spread_pct="1.2000", dia=date(2031, 3, 10), observacao=None, arquivo=ARQ):
    return {"arquivo_origem": arquivo, "ref_origem": ref, "linha_planilha": next(_linha), "data_contratacao": dia,
            "data_liquidacao": dia, "cnpj": cnpj, "cliente": "QUALQUER", "moeda": "USD", "valor_me": D("1000.00"),
            "taxa_cliente": D("5.1"), "ptax_ref": D("5.0000"), "valor_brl": D("5100.00"), "spread_brl": D(spread_brl),
            "spread_pct": None if spread_pct is None else D(spread_pct), "spread_estimado_d1_brl": D("0.00"),
            "iof_brl": D("0.00"), "status_compliance": "APROVADO", "observacao": observacao}


def _ajuste(ref, original, spread_brl, cnpj=CNPJ_A, **kw):
    return _op(ref, cnpj, spread_brl, spread_pct=None, observacao=f"AJUSTE REF {original}", **kw)


@pytest.fixture
def cfg():
    return carregar_config()


@pytest.fixture
def taxas():
    return pd.DataFrame([_taxa("Loja A Ltda", CNPJ_A, "linha 4", spread=D("1.200")),
                         _taxa("Loja B Ltda", CNPJ_B, "linha 5", spread=D("1.200"))],
                        columns=leitor_taxas.COLUNAS_SAIDA, dtype=object)


def _calc(taxas, cfg, *ops, anterior=None):
    ponte = pd.DataFrame(list(ops), columns=leitor_ponte.COLUNAS_SAIDA, dtype=object)
    return calcular_remessa(ponte, taxas, COMP, ARQ, cfg, anterior)


def _pref(itens, prefixo):
    return {i.id_saida: i for i in itens if i.id_saida.startswith(prefixo)}


def test_config_do_ajuste(cfg):
    assert cfg.ajuste_participacao == D("0.5")
    assert cfg.ajuste_padrao.search("ajuste ref pc-0001.").group(1) == "pc-0001."
    assert cfg.ajuste_padrao.search("Taxa travada no pedido (D-1)") is None


def test_ajuste_checado_antes_da_r23_nao_e_pen_neg_nem_divergencia(taxas, cfg):
    itens = _calc(taxas, cfg, _op("OP-1", CNPJ_A, "100.00"), _ajuste("AJ-1", "PC-X", "-40.00"))
    assert not _pref(itens, "PEN-NEG-") and not _pref(itens, "DIV-")
    com = _pref(itens, "COM-REM-")[f"COM-REM-{CNPJ_A}"]
    assert [(o.ref_origem, o.valor) for o in com.origens] == [("OP-1", D("50.00")), ("AJ-1", D("-20.00"))]
    assert com.valor_reportado == D("30.00")
    nf = _pref(itens, "NF-")["NF-REM-75374179000146"]
    assert nf.valor_reportado == D("30.00") and "AJUSTE REF PC-X" in nf.campos["discriminacao"]
    ted = _pref(itens, "PEN-TED-PONTE")["PEN-TED-PONTE"]
    assert ted.valor_reportado == nf.valor_reportado


def test_regressao_spread_negativo_comum_continua_na_r23(taxas, cfg):
    for obs in (None, "Taxa travada no pedido (D-1)", "ajuste de contestação"):  # nenhuma casa "AJUSTE REF"
        itens = _calc(taxas, cfg, _op("OP-1", CNPJ_A, "100.00"),
                      _op("OP-NEG", CNPJ_A, "-60.00", "-1.3000", observacao=obs))
        assert set(_pref(itens, "PEN-NEG-")) == {"PEN-NEG-REM-OP-NEG"}
        assert not _pref(itens, "DIV-") and not _pref(itens, "PEN-AJUSTE-")
        assert _pref(itens, "COM-REM-")[f"COM-REM-{CNPJ_A}"].valor_reportado == D("50.00")  # fora da comissão (R12)


def test_c_mes_zerado_pelo_ajuste_nao_emite_nota_e_vira_pendencia(taxas, cfg, tmp_path):
    itens = _calc(taxas, cfg, _op("OP-1", CNPJ_A, "10.00"), _ajuste("AJ-1", "PC-X", "-10.00"))
    assert not _pref(itens, "NF-")
    pen = _pref(itens, "PEN-NF-REM-")["PEN-NF-REM-75374179000146"]
    assert (pen.campos["tipo"], pen.valor_reportado, pen.campos["quem_decide"]) == ("NOTA_NAO_EMITIDA", D("0.00"), "Financeiro (Helena)")
    assert all(r in pen.campos["motivo"] for r in ("R31", "R06", "R17"))
    assert _pref(itens, "COM-REM-")[f"COM-REM-{CNPJ_A}"].valor_reportado == D("0.00")
    gravar_saida(tmp_path, itens)
    assert validar_saida(tmp_path) == []


def test_c_mes_negativado_pelo_ajuste_tambem_nao_emite_nota(taxas, cfg):
    itens = _calc(taxas, cfg, _op("OP-1", CNPJ_A, "10.00"), _ajuste("AJ-1", "PC-X", "-30.00", cnpj=CNPJ_B))
    assert not _pref(itens, "NF-")
    assert _pref(itens, "PEN-NF-REM-")["PEN-NF-REM-75374179000146"].valor_reportado == D("-10.00")
    assert _pref(itens, "COM-REM-")[f"COM-REM-{CNPJ_B}"].valor_reportado == D("-15.00")  # lojista só com ajuste


def test_ajuste_sem_cnpj_usa_o_da_original_do_mes(taxas, cfg):
    aj = _ajuste("AJ-1", "PC-ORIG", "-10.00", cnpj=None)
    itens = _calc(taxas, cfg, _op("PC-ORIG", CNPJ_B, "100.00"), aj)
    assert _pref(itens, "COM-REM-")[f"COM-REM-{CNPJ_B}"].valor_reportado == D("45.00")
    assert f"COM-REM-{CNPJ_A}" not in _pref(itens, "COM-REM-")
    assert "AJUSTE REF PC-ORIG (operação de 2031-03)" in _pref(itens, "NF-")["NF-REM-75374179000146"].campos["discriminacao"]


def test_ajuste_sem_cnpj_e_sem_original_para_o_fechamento(taxas, cfg):
    with pytest.raises(ErroRemessa, match="ajuste sem CNPJ"):
        _calc(taxas, cfg, _op("OP-1", CNPJ_A, "10.00"), _ajuste("AJ-1", "PC-X", "-10.00", cnpj=None))


def test_linha_sem_cnpj_que_nao_e_ajuste_para_o_fechamento(taxas, cfg):
    with pytest.raises(ErroRemessa, match="CNPJ vazio"):
        _calc(taxas, cfg, _op("OP-1", None, "10.00"))


def _anterior(contestadas=("PC-FEV",)):
    original = _op("PC-FEV", CNPJ_A, "80.00", dia=date(2031, 2, 20), arquivo="ponte_fev.eml#ops.xlsx")
    return Anterior("2031-02", "ponte_fev.eml#ops.xlsx", {"PC-FEV": original}, frozenset(contestadas))


def test_original_no_relatorio_anterior_vai_no_rastro_com_zero_e_cita_a_contestacao(taxas, cfg):
    itens = _calc(taxas, cfg, _op("OP-1", CNPJ_A, "100.00"), _ajuste("AJ-1", "PC-FEV", "-8.00"), anterior=_anterior())
    com = _pref(itens, "COM-REM-")[f"COM-REM-{CNPJ_A}"]
    assert [(o.arquivo_origem, o.ref_origem, o.valor) for o in com.origens] == [
        (ARQ, "OP-1", D("50.00")), (ARQ, "AJ-1", D("-4.00")), ("ponte_fev.eml#ops.xlsx", "PC-FEV", D("0.00"))]
    nf = _pref(itens, "NF-")["NF-REM-75374179000146"]
    assert nf.valor_reportado == D("46.00")
    assert "AJUSTE REF PC-FEV (operação de 2031-02, contestada em 2031-02)" in nf.campos["discriminacao"]
    assert not _pref(itens, "PEN-AJUSTE-")


def test_original_nao_contestada_nao_diz_contestada(taxas, cfg):
    itens = _calc(taxas, cfg, _op("OP-1", CNPJ_A, "100.00"), _ajuste("AJ-1", "PC-FEV", "-8.00"),
                  anterior=_anterior(contestadas=()))
    disc = _pref(itens, "NF-")["NF-REM-75374179000146"].campos["discriminacao"]
    assert "AJUSTE REF PC-FEV (operação de 2031-02)" in disc and "contestada" not in disc


def test_b_original_ausente_com_anterior_abate_e_abre_pendencia(taxas, cfg):
    itens = _calc(taxas, cfg, _op("OP-1", CNPJ_A, "100.00"), _ajuste("AJ-1", "PC-NAO-EXISTE", "-8.00"), anterior=_anterior())
    assert _pref(itens, "COM-REM-")[f"COM-REM-{CNPJ_A}"].valor_reportado == D("46.00")
    pen = _pref(itens, "PEN-AJUSTE-SEMORIG-")["PEN-AJUSTE-SEMORIG-AJ-1"]
    assert pen.valor_reportado == D("-4.00") and pen.campos["ref_origem"] == "AJ-1"
    assert "PC-NAO-EXISTE" in pen.campos["motivo"] and "2031-02" in pen.campos["motivo"]


def test_sem_pasta_anterior_so_registra_a_referencia_sem_pendencia(taxas, cfg):
    itens = _calc(taxas, cfg, _op("OP-1", CNPJ_A, "100.00"), _ajuste("AJ-1", "PC-NAO-EXISTE", "-8.00"))
    assert _pref(itens, "COM-REM-")[f"COM-REM-{CNPJ_A}"].valor_reportado == D("46.00")
    assert not _pref(itens, "PEN-AJUSTE-")
    assert "AJUSTE REF PC-NAO-EXISTE" in _pref(itens, "NF-")["NF-REM-75374179000146"].campos["discriminacao"]


def test_p25_percentual_configuravel_e_credito_soma(taxas, cfg):
    itens = _calc(taxas, cfg, _op("OP-1", CNPJ_A, "100.00"), _ajuste("AJ-1", "PC-X", "-10.00"), _ajuste("AJ-2", "PC-Y", "5.00"))
    assert _pref(itens, "COM-REM-")[f"COM-REM-{CNPJ_A}"].valor_reportado == D("47.50")  # 50 - 5 + 2,50
    itens = _calc(taxas, replace(cfg, ajuste_participacao=D("0.4")), _op("OP-1", CNPJ_A, "100.00"), _ajuste("AJ-1", "PC-X", "-10.00"))
    assert _pref(itens, "COM-REM-")[f"COM-REM-{CNPJ_A}"].valor_reportado == D("46.00")  # 50 - 4


def test_ajuste_fora_da_competencia_nao_abate(taxas, cfg):
    itens = _calc(taxas, cfg, _op("OP-1", CNPJ_A, "100.00"), _ajuste("AJ-1", "PC-X", "-10.00", dia=date(2031, 4, 2)))
    assert _pref(itens, "COM-REM-")[f"COM-REM-{CNPJ_A}"].valor_reportado == D("50.00")
    assert set(_pref(itens, "PEN-FORA-")) == {"PEN-FORA-REM-AJ-1"}


def test_padrao_de_ajuste_sem_grupo_e_erro(tmp_path):
    texto = (RAIZ / "config" / "remessa.yaml").read_text(encoding="utf-8").replace("AJUSTE REF (PC-", "AJUSTE REF (?:PC-")
    caminho = tmp_path / "remessa.yaml"
    caminho.write_text(texto, encoding="utf-8")
    with pytest.raises(ErroRemessa, match="1 grupo"):
        carregar_config(caminho)


def test_competencia_anterior_e_pasta_ao_lado(tmp_path):
    assert (competencia_anterior("2026-10"), competencia_anterior("2027-01")) == ("2026-09", "2026-12")
    (tmp_path / "2026-09").mkdir()
    assert pasta_anterior(tmp_path / "2026-10", "2026-10") == tmp_path / "2026-09"
    assert pasta_anterior(tmp_path / "2026-09", "2026-09") is None          # 2026-08 não existe
    (tmp_path / "pacote").mkdir()
    assert pasta_anterior(tmp_path / "pacote", "2026-10") == tmp_path / "2026-09"  # nome sem a competência
