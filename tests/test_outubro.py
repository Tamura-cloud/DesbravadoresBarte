"""Fechamento de outubro sobre um pack gerado a partir de setembro por tests/gerar_outubro.py.

Prova que o fechamento roda em outro mês sem retrabalho: mesmo código, mesma config, arquivos novos no
mesmo formato. NÃO compara totais com setembro (os números mudam legitimamente com as datas): confere
formato, datas, os quatro casos novos e as condições comerciais com vigência.
Roda sem IA (--sem-ia): os casos (b) e (c) conferem o fluxo de P09. O fluxo com IA (P14), com cliente falso,
está em tests/test_ia.py.
"""

import csv
import hashlib
import os
import re
import subprocess
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pytest

from gerar_outubro import deslocar, deslocar_texto, gerar, mes_seguinte
from tarvo.checkout import calcular_linhas
from tarvo.checkout import carregar_config as carregar_config_checkout
from tarvo.fechamento import fechar, ler_entradas
from tarvo.leitores.aurora import ler_aurora
from tarvo.leitores.comum import dinheiro
from tarvo.leitores.meridiano import ler_meridiano
from tarvo.leitores.orbe import ler_orbe
from tarvo.leitores.ponte import ler_ponte
from tarvo.remessa import carregar_config as carregar_config_remessa
from tarvo.saida import ARQUIVOS, validar_saida

RAIZ = Path(__file__).resolve().parents[1]
SETEMBRO = RAIZ / "dados" / "2026-09"
COMPETENCIA = "2026-10"
TOMADOR_PONTE = "75374179000146"
CNPJ_CASA = "00520815000100"      # R10: tarifa zerada no checkout de setembro a dezembro/2026
CNPJ_BRIDGE = "22224579000109"    # crédito à vista renegociado para 2,19% a partir de 15/09/2026
TAXA_NOVA_BRIDGE = Decimal("2.19")


def _hashes(pasta: Path) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(pasta.iterdir()) if p.is_file()}


def _ler(pasta: Path, nome: str) -> list[dict]:
    with open(pasta / nome, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _por_id(pasta: Path, nome: str) -> dict[str, dict]:
    return {l["id_saida"]: l for l in _ler(pasta, nome)}


def _ids_com_ref(saida: Path, ref: str) -> set[str]:
    """id_saida de todo item cujo rastro passa por essa ref_origem."""
    return {l["id_saida"] for l in _ler(saida, "rastro.csv") if l["ref_origem"] == ref}


@pytest.fixture(scope="module")
def pack(tmp_path_factory):
    antes = _hashes(SETEMBRO)
    pasta = tmp_path_factory.mktemp("dados") / "2026-10"
    casos = gerar(SETEMBRO, pasta)
    return {"pasta": pasta, "casos": casos, "antes": antes, "depois": _hashes(SETEMBRO)}


@pytest.fixture(scope="module")
def saida(pack, tmp_path_factory):
    pasta = tmp_path_factory.mktemp("saida")
    fechar(pack["pasta"], pasta, COMPETENCIA, usar_ia=False)  # ErroFechamento aqui já reprova
    return pasta


@pytest.fixture(scope="module")
def entradas(pack):
    return ler_entradas(pack["pasta"], COMPETENCIA)


# ---------------------------------------------------------------- o gerador

def test_gerador_nao_toca_nos_originais(pack):
    assert pack["depois"] == pack["antes"]


def test_nomes_assunto_e_anexo_de_outubro(pack):
    nomes = sorted(p.name for p in pack["pasta"].iterdir())
    assert len(nomes) == 6
    assert not any("set2026" in n for n in nomes)
    originais = [n for n in pack["antes"] if "set2026" in n]
    assert originais and all(n.replace("set2026", "out2026") in nomes for n in originais)

    _, meta = ler_ponte(pack["casos"]["ponte"]["arquivo"])
    assert meta["assunto"].endswith("10/2026") and "09/2026" not in meta["assunto"]
    assert meta["arquivo_origem"].endswith("_102026.xlsx")
    assert "competência 10/2026" in meta["corpo"]
    assert meta["data_email"].month == 11  # o e-mail de setembro chegou em outubro


def test_orbe_datas_deslocadas_e_uma_venda_nova(pack):
    original = {r["ref_origem"]: r for r in ler_orbe(next(SETEMBRO.glob("*orbe*.csv"))).to_dict("records")}
    novo = {r["ref_origem"]: r for r in ler_orbe(pack["casos"]["orbe"]["arquivo"]).to_dict("records")}
    assert set(novo) - set(original) == {pack["casos"]["orbe"]["ref_origem"]}
    for ref, o in original.items():
        n = novo[ref]
        assert n["data_movimento"] == deslocar(o["data_movimento"])
        assert n["data_venda_original"] == (deslocar(o["data_venda_original"]) if o["data_venda_original"] else None)
        assert (n["valor_bruto"], n["taxa_aplicada_pct"], n["cod_estabelecimento"]) == \
               (o["valor_bruto"], o["taxa_aplicada_pct"], o["cod_estabelecimento"])
    assert {r["data_movimento"].strftime("%Y-%m") for r in novo.values()} == {COMPETENCIA}


def test_aurora_datas_deslocadas_e_saldo_corrido_recalculado(pack):
    caso = pack["casos"]["aurora"]
    orig, meta_orig = ler_aurora(next(SETEMBRO.glob("*aurora*.csv")))
    novo, meta = ler_aurora(caso["arquivo"])
    linhas = novo.to_dict("records")

    saldo = meta["saldo_anterior"]
    for l in linhas:
        saldo += l["valor"]
        assert l["saldo"] == saldo, l["ref_origem"]
    assert meta["saldo_final"] == saldo == meta_orig["saldo_final"] + caso["valor"]

    inserida = [l for l in linhas if l["ref_origem"] == caso["ref_origem"]]
    assert [(l["descricao"], l["valor"]) for l in inserida] == [("PIX ENVIADO GRAFICA RAPIDA LTDA", caso["valor"])]
    resto = [l for l in linhas if l["ref_origem"] != caso["ref_origem"]]
    assert len(resto) == len(orig)
    for o, n in zip(orig.to_dict("records"), resto):
        assert (n["data"], n["valor"], n["descricao"]) == (deslocar(o["data"]), o["valor"], deslocar_texto(o["descricao"]))
    assert {l["data"].strftime("%Y-%m") for l in linhas} == {COMPETENCIA}


def test_meridiano_datas_e_fitid_deslocados_e_pix_novo(pack):
    caso = pack["casos"]["meridiano"]
    orig, meta_orig = ler_meridiano(next(SETEMBRO.glob("*.ofx")))
    novo, meta = ler_meridiano(caso["arquivo"])
    por_fitid = {r["ref_origem"]: r for r in novo.to_dict("records")}
    assert len(por_fitid) == len(orig) + 1

    for o in orig.to_dict("records"):
        ano, mes, seq = re.fullmatch(r"MRD(\d{4})(\d{2})(\d{4})", o["ref_origem"]).groups()
        ano, mes = mes_seguinte(int(ano), int(mes))
        n = por_fitid[f"MRD{ano}{mes:02d}{seq}"]
        assert (n["data"], n["valor"], n["memo"]) == (deslocar(o["data"]), o["valor"], o["memo"])
    assert (meta["dtstart"], meta["dtend"]) == (deslocar(meta_orig["dtstart"]), deslocar(meta_orig["dtend"]))
    assert meta["dtend"].isoformat() == "2026-10-31"
    assert meta["saldo_ledger"] == meta_orig["saldo_ledger"] + caso["valor"]
    assert por_fitid[caso["ref_origem"]]["memo"] == "PIX RECEB INSTITUTO SAKURA IDIOMAS"


def test_ponte_datas_deslocadas_rodape_e_operacao_nova(pack):
    caso = pack["casos"]["ponte"]
    orig, meta_orig = ler_ponte(next(SETEMBRO.glob("*.eml")))
    novo, meta = ler_ponte(caso["arquivo"])
    assert len(novo) == len(orig) + 1
    for o, n in zip(orig.to_dict("records"), novo.to_dict("records")):
        assert n["data_contratacao"] == deslocar(o["data_contratacao"])
        assert n["data_liquidacao"] == deslocar(o["data_liquidacao"])
        assert (n["cnpj"], n["spread_brl"], n["valor_brl"]) == (o["cnpj"], o["spread_brl"], o["valor_brl"])
        assert n["ref_origem"] == o["ref_origem"].replace("PC-0926-", "PC-1026-")
    nova = novo.to_dict("records")[-1]
    assert (nova["ref_origem"], nova["cnpj"], nova["spread_brl"]) == (caso["ref_origem"], caso["cnpj"], caso["spread_brl"])
    assert meta["total_operacoes_rodape"] == meta_orig["total_operacoes_rodape"] + 1 == len(novo)
    assert meta["spread_total_rodape"] == meta_orig["spread_total_rodape"] + caso["spread_brl"]


# ---------------------------------------------------------------- o fechamento de outubro

def test_fechar_outubro_sem_erro_e_saida_valida(saida):
    assert sorted(p.name for p in saida.iterdir()) == sorted(e.nome for e in ARQUIVOS)
    assert validar_saida(saida) == []


def test_cli_fechar_outubro(pack, tmp_path):
    env = {**os.environ, "PYTHONPATH": str(RAIZ / "src"), "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run(
        [sys.executable, "-m", "tarvo", "fechar", "--competencia", COMPETENCIA,
         "--entrada", str(pack["pasta"]), "--saida", str(tmp_path), "--sem-ia"],
        capture_output=True, text=True, encoding="utf-8", env=env, cwd=RAIZ,
    )
    assert r.returncode == 0, r.stderr
    assert "validados sem problemas" in r.stdout
    assert "desligada (--sem-ia)" in r.stdout


def test_datas_de_saida_todas_em_outubro_e_nenhuma_de_setembro(pack, saida):
    lancamentos = _ler(saida, "lancamentos_classificados.csv")
    assert lancamentos and all(l["data"].startswith(COMPETENCIA + "-") for l in lancamentos)

    # cada lançamento tem a data deslocada do original (nada ficou com a data de setembro)
    aurora, _ = ler_aurora(next(SETEMBRO.glob("*aurora*.csv")))
    meridiano, _ = ler_meridiano(next(SETEMBRO.glob("*.ofx")))
    esperado = Counter((deslocar(r["data"]).isoformat(), format(r["valor"], "f"))
                       for df in (aurora, meridiano) for r in df.to_dict("records"))
    for tipo in ("aurora", "meridiano"):
        c = pack["casos"][tipo]
        esperado[(c["data"].isoformat(), format(c["valor"], "f"))] += 1
    assert Counter((l["data"], l["valor"]) for l in lancamentos) == esperado

    for espec in ARQUIVOS:
        texto = (saida / espec.nome).read_text(encoding="utf-8")
        assert "2026-09" not in texto, espec.nome
        assert not re.search(r"\b\d{2}/09/2026\b", texto), espec.nome
    for nota in _ler(saida, "notas_a_emitir.csv"):
        assert nota["discriminacao"].endswith(f"competência {COMPETENCIA}")
    for p in _ler(saida, "pendencias.csv"):
        if m := re.search(r"\d{4}-\d{2}-\d{2}", p["id_saida"]):
            assert m.group(0).startswith(COMPETENCIA), p["id_saida"]


def test_caso_a_venda_de_ec_fora_da_planilha_vira_so_pendencia(pack, saida, entradas):
    caso = pack["casos"]["orbe"]
    ec = caso["cod_estabelecimento"]
    assert ec not in set(entradas.taxas["ec"].dropna()) and ec not in carregar_config_checkout().ec_sem_codigo

    id_pen = f"PEN-SEMCONTRATO-{ec}"
    assert _ids_com_ref(saida, caso["ref_origem"]) == {id_pen}  # sem comissão, nota nem divergência
    p = _por_id(saida, "pendencias.csv")[id_pen]
    assert p["tipo"] == "LOJISTA_SEM_CONTRATO"
    assert p["ref_origem"] == caso["ref_origem"]
    assert Decimal(p["valor_brl"]) == caso["valor_taxa"]  # o que a Orbe cobrou
    assert "R08" in p["motivo"] and "não faturar" in p["motivo"]
    assert p["quem_decide"] == "Comercial"


@pytest.mark.parametrize("tipo, banco", [("aurora", "AUR"), ("meridiano", "MER")])
def test_casos_b_c_pix_fora_das_listas_ficam_a_classificar(pack, saida, tipo, banco):
    caso = pack["casos"][tipo]
    ref = caso["ref_origem"]
    id_lan, id_pen = f"LAN-{banco}-{ref}", f"PEN-SEMREGRA-{ref}"
    assert _ids_com_ref(saida, ref) == {id_lan, id_pen}  # nem conferência PIX × remessa, nem outra pendência

    lan = _por_id(saida, "lancamentos_classificados.csv")[id_lan]
    assert (lan["conta_codigo"], lan["metodo"], lan["confianca"]) == ("A_CLASSIFICAR", "HUMANO", "0.00")
    assert Decimal(lan["valor"]) == caso["valor"]
    pen = _por_id(saida, "pendencias.csv")[id_pen]
    assert (pen["tipo"], pen["ref_origem"]) == ("LANCAMENTO_SEM_REGRA", ref)
    assert Decimal(pen["valor_brl"]) == caso["valor"]
    assert "P09" in pen["motivo"]


def test_caso_d_operacao_de_cnpj_fora_da_planilha(pack, saida, entradas):
    """P04: a comissão é calculada mesmo assim e entra na nota da Ponte, COM a pendência de cadastro;
    sem divergência (não há spread contratado). As conferências P11 e P12 apontam a falta de TED e de PIX."""
    caso = pack["casos"]["ponte"]
    cnpj, ref = caso["cnpj"], caso["ref_origem"]
    assert cnpj not in set(entradas.taxas["cnpj"])
    total = caso["valor_brl"] + caso["iof_brl"]
    id_ted = f"PEN-TED-LIQ-{caso['data_contratacao'].isoformat()}"
    # PEN-TED-PONTE tem as mesmas origens da NF-REM (P22)
    ids = {f"COM-REM-{cnpj}", f"NF-REM-{TOMADOR_PONTE}", "PEN-TED-PONTE", f"PEN-NAOCAD-REM-{cnpj}", id_ted,
           f"PEN-PIX-REM-{cnpj}"}
    assert _ids_com_ref(saida, ref) == ids
    assert not any(i.startswith("DIV-") for i in _ids_com_ref(saida, ref))

    comissao = dinheiro(caso["spread_brl"] * carregar_config_remessa().participacao)  # R11
    rastro = {(l["id_saida"], l["ref_origem"]): Decimal(l["valor"]) for l in _ler(saida, "rastro.csv")}
    assert (rastro[(f"COM-REM-{cnpj}", ref)] == rastro[(f"NF-REM-{TOMADOR_PONTE}", ref)]
            == rastro[("PEN-TED-PONTE", ref)] == comissao)

    pend = _por_id(saida, "pendencias.csv")
    naocad = pend[f"PEN-NAOCAD-REM-{cnpj}"]
    assert (naocad["tipo"], naocad["ref_origem"], Decimal(naocad["valor_brl"])) == ("LOJISTA_NAO_CADASTRADO", ref, comissao)
    assert "cadastrar" in naocad["motivo"]
    # o resto do dia fecha com as TEDs: a diferença é exatamente a operação nova, sem TED paga
    assert pend[id_ted]["tipo"] == "DIVERGENCIA_TED_LIQUIDACAO" and Decimal(pend[id_ted]["valor_brl"]) == total
    pix = pend[f"PEN-PIX-REM-{cnpj}"]
    assert (pix["tipo"], pix["ref_origem"], Decimal(pix["valor_brl"])) == ("DIFERENCA_PIX_REMESSA", ref, -total)


def test_casa_do_estudante_tarifa_zerada_em_outubro(saida, entradas):
    linhas = [l for l in calcular_linhas(entradas.orbe, entradas.taxas, carregar_config_checkout())
              if l.cnpj == CNPJ_CASA]
    assert linhas
    assert all(l.taxa_contratada == 0 and l.origem_taxa == "R10" for l in linhas)

    com = _por_id(saida, "comissoes_por_lojista.csv")[f"COM-CHK-{CNPJ_CASA}"]
    assert Decimal(com["comissao_brl"]) == 0
    assert f"NF-CHK-{CNPJ_CASA}" not in _por_id(saida, "notas_a_emitir.csv")
    assert _por_id(saida, "pendencias.csv")[f"PEN-NF-CHK-{CNPJ_CASA}"]["tipo"] == "NOTA_NAO_EMITIDA"
    div = [d for d in _ler(saida, "divergencias_taxa.csv") if d["cnpj"] == CNPJ_CASA]
    assert div and all(d["taxa_contratada_pct"] == "0.0000" for d in div)
    # R10 vale só no checkout: a remessa da Casa segue com comissão
    assert Decimal(_por_id(saida, "comissoes_por_lojista.csv")[f"COM-REM-{CNPJ_CASA}"]["comissao_brl"]) > 0


def test_bridge_vendas_de_outubro_na_taxa_nova(saida, entradas):
    nova = [t for t in entradas.taxas.to_dict("records")
            if t["cnpj"] == CNPJ_BRIDGE and t["vigencia_inicio"] is not None and t["vigencia_fim"] is None]
    assert len(nova) == 1 and nova[0]["taxa_credito_vista"] == TAXA_NOVA_BRIDGE

    vista = {r["ref_origem"]: r for r in entradas.orbe.to_dict("records")
             if r["tipo_lancamento"] == "VENDA" and r["modalidade"] == "CREDITO A VISTA"}
    linhas = [l for l in calcular_linhas(entradas.orbe, entradas.taxas, carregar_config_checkout())
              if l.cnpj == CNPJ_BRIDGE and l.ref_origem in vista]
    assert linhas and all(l.data_referencia.strftime("%Y-%m") == COMPETENCIA for l in linhas)
    assert all(l.taxa_contratada == TAXA_NOVA_BRIDGE and l.origem_taxa == nova[0]["ref_origem"] for l in linhas)

    rastro = {l["ref_origem"]: Decimal(l["valor"]) for l in _ler(saida, "rastro.csv")
              if l["id_saida"] == f"COM-CHK-{CNPJ_BRIDGE}"}
    for l in linhas:
        assert rastro[l.ref_origem] == dinheiro(vista[l.ref_origem]["valor_bruto"] * TAXA_NOVA_BRIDGE / 100)
    div = {d["ref_origem"]: d for d in _ler(saida, "divergencias_taxa.csv") if d["cnpj"] == CNPJ_BRIDGE}
    vendas_div = [div[l.ref_origem] for l in linhas if l.ref_origem in div]
    assert vendas_div and all(d["taxa_contratada_pct"] == "2.1900" for d in vendas_div)
