"""R29: rascunhos de contestação por contraparte (Orbe e Ponte), com os totais do texto vindos dos CSVs."""

import csv
import os
import re
import subprocess
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from tarvo.contestacao import ErroContestacao, carregar_config
from tarvo.fechamento import fechar
from tarvo.leitores.comum import dinheiro
from tarvo.resumo import brl

D = Decimal
RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "dados" / "2026-09"
CASA, ROTA, BRIDGE, MUNDO_ABERTO = "00520815000100", "95927868000148", "22224579000109", "17217888000111"
CABECALHO = "[RASCUNHO — Helena revisa antes de enviar]"
NOTAS = "NOTAS PARA A HELENA — apagar antes de enviar"
SEPARADOR_NOTAS = "\n---\n"
SEIS_CSVS = sorted(["comissoes_por_lojista.csv", "divergencias_taxa.csv", "notas_a_emitir.csv",
                    "lancamentos_classificados.csv", "pendencias.csv", "rastro.csv"])


def _ler(pasta: Path, nome: str) -> list[dict]:
    with open(pasta / nome, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _partes(pasta: Path, nome: str) -> tuple[str, str]:
    """(notas internas, corpo do e-mail)."""
    with open(pasta / nome, encoding="utf-8", newline="") as f:
        notas, corpo = f.read().split(SEPARADOR_NOTAS, 1)
    return notas, corpo


def _rs(v: Decimal) -> str:
    return f"{'-' if v < 0 else ''}R$ {brl(abs(v))}"


def _secao(corpo: str, titulo: str) -> str:
    """Texto da seção "## n. titulo" até a próxima "## " ou o fim."""
    i = corpo.index(titulo)
    resto = corpo[i + len(titulo):]
    m = re.search(r"\n## |\nAtenciosamente", resto)
    return resto[:m.start()] if m else resto


@pytest.fixture(scope="module")
def fechamento(tmp_path_factory):
    raiz = tmp_path_factory.mktemp("fechamento")
    resultado = fechar(ENTRADA, raiz / "saida", "2026-09", usar_ia=False)
    return {"saida": raiz / "saida", "contestacoes": raiz / "contestacoes", "resultado": resultado}


@pytest.fixture(scope="module")
def saida(fechamento):
    return fechamento["saida"]


@pytest.fixture(scope="module")
def cont(fechamento):
    return fechamento["contestacoes"]


# ---------------------------------------------------------------- estrutura

def test_pasta_irma_com_4_arquivos_e_saida_continua_com_6_csvs(fechamento, saida, cont):
    assert sorted(p.name for p in cont.iterdir()) == ["orbe.md", "orbe_operacoes.csv", "ponte.md", "ponte_operacoes.csv"]
    assert sorted(p.name for p in saida.iterdir()) == SEIS_CSVS
    assert set(fechamento["resultado"].arquivos_contestacao) == {p.name for p in cont.iterdir()}


@pytest.mark.parametrize("arquivo, destinatario", [("orbe.md", "<e-mail da Orbe>"), ("ponte.md", "<e-mail da Ponte>")])
def test_cabecalho_notas_internas_e_destinatario_sem_email_inventado(cont, arquivo, destinatario):
    texto = (cont / arquivo).read_text(encoding="utf-8")
    assert texto.startswith(CABECALHO + "\n\n" + NOTAS)
    notas, corpo = _partes(cont, arquivo)
    assert f"Para: {destinatario}" in corpo and "@" not in texto


@pytest.mark.parametrize("arquivo", ["orbe.md", "ponte.md"])
def test_corpo_do_email_nao_fala_de_aviso_nem_cita_regra_interna(cont, arquivo):
    notas, corpo = _partes(cont, arquivo)
    assert not re.search(r"avis", corpo, re.IGNORECASE)
    assert not re.search(r"\b[RP]\d\d\b", corpo)  # códigos de regra e premissa são internos
    assert re.search(r"avis", notas, re.IGNORECASE)


# ---------------------------------------------------------------- Orbe

def test_orbe_csv_tem_as_divergencias_de_checkout_com_o_mesmo_id_e_ref(saida, cont):
    linhas = _ler(cont, "orbe_operacoes.csv")
    div = {l["id_saida"]: l for l in _ler(saida, "divergencias_taxa.csv") if l["linha_negocio"] == "CHECKOUT"}
    assert len(linhas) == len(div) == 210
    assert {l["id_saida"] for l in linhas} == set(div)
    for l in linhas:
        d = div[l["id_saida"]]
        assert l["ref_origem"] == d["ref_origem"] and l["cnpj"] == d["cnpj"]
        assert l["diferenca_brl"] == d["diferenca_brl"]
        assert l["taxa_contratada_pct"] == d["taxa_contratada_pct"] and l["taxa_aplicada_pct"] == d["taxa_aplicada_pct"]


def test_orbe_totais_de_cada_secao_saem_do_csv(cont):
    linhas = _ler(cont, "orbe_operacoes.csv")
    notas, corpo = _partes(cont, "orbe.md")
    por_cnpj = defaultdict(lambda: [0, D("0")])
    for l in linhas:
        por_cnpj[l["cnpj"]][0] += 1
        por_cnpj[l["cnpj"]][1] += D(l["diferenca_brl"])
    assert {k: (v[0], v[1]) for k, v in por_cnpj.items()} == {
        CASA: (118, D("15397.42")), ROTA: (87, D("1546.28")), BRIDGE: (5, D("29.95"))}
    assert "em 210 transações de 3 lojistas" in corpo

    comunicacao = _secao(corpo, "## 1. Comunicação de condição comercial")
    contrato = _secao(corpo, "## 2. Taxas aplicadas acima do contrato")
    assert "Casa do Estudante" in comunicacao and "Bridge" not in comunicacao and "Rota" not in comunicacao
    assert "Bridge" in contrato and "Rota" in contrato and "Casa do Estudante" not in contrato
    assert f"que soma {_rs(por_cnpj[CASA][1])}" in comunicacao
    assert f"O total desta parte é {_rs(por_cnpj[BRIDGE][1] + por_cnpj[ROTA][1])}" in contrato
    for cnpj, secao in ((CASA, comunicacao), (BRIDGE, contrato), (ROTA, contrato)):
        linha = next(l for l in secao.splitlines() if l.startswith("|") and cnpj in l)
        assert f"| {por_cnpj[cnpj][0]} |" in linha and brl(por_cnpj[cnpj][1]) in linha


def test_orbe_estornos_reduzem_o_total_sem_sinal_negativo_no_texto(cont):
    estornos = [l for l in _ler(cont, "orbe_operacoes.csv") if l["tipo_lancamento"] == "ESTORNO"]
    soma = sum(D(l["diferenca_brl"]) for l in estornos)
    assert (len(estornos), soma) == (5, D("-107.53"))
    corpo = _partes(cont, "orbe.md")[1]
    assert f"{len(estornos)} linhas são estornos" in corpo and f"reduzem o total em {_rs(abs(soma))}" in corpo
    assert "diferença negativa" not in corpo and "R$ -" not in corpo


def test_orbe_casa_comunica_a_condicao_com_inicio_e_fim_e_pede_regularizacao(cont):
    comunicacao = _secao(_partes(cont, "orbe.md")[1], "## 1. Comunicação de condição comercial")
    assert "vigente de 2026-09-01 a 2026-12-31" in comunicacao and "0,00%" in comunicacao
    assert "parametrização" in comunicacao and "regularização do período" in comunicacao


def test_orbe_bridge_so_credito_a_vista_de_15_a_18(cont):
    linhas = [l for l in _ler(cont, "orbe_operacoes.csv") if l["cnpj"] == BRIDGE]
    assert len(linhas) == 5 and {l["taxa_contratada_pct"] for l in linhas} == {"2.1900"}
    contrato = _secao(_partes(cont, "orbe.md")[1], "## 2. Taxas aplicadas acima do contrato")
    assert "vigente desde 2026-09-15" in contrato
    assert "5 transações de crédito à vista, de 2026-09-15 a 2026-09-18" in contrato


def test_orbe_rota_taxa_contratada_ate_11_09_e_mais_0_50_depois_so_no_credito(cont):
    contrato = _secao(_partes(cont, "orbe.md")[1], "## 2. Taxas aplicadas acima do contrato")
    assert "Até 2026-09-11 (52 transações), a taxa aplicada foi a contratada." in contrato
    assert ("A partir de 2026-09-12, todas as 83 transações de crédito à vista e crédito parcelado vieram com a taxa "
            "0,50 p.p. acima da contratada; as de antecipação, débito e PIX seguiram a taxa contratada.") in contrato
    assert "não há registro" not in contrato.lower()


def test_orbe_notas_avisos_e_valor_a_devolver_vindo_das_pendencias(saida, cont):
    notas = _partes(cont, "orbe.md")[0]
    assert "Casa do Estudante Viagens Ltda: nunca foi avisada" in notas
    assert "Escola Bridge de Idiomas Ltda: foi avisada só alguns dias depois do início da vigência (2026-09-15)" in notas
    pen = {l["id_saida"]: D(l["valor_brl"]) for l in _ler(saida, "pendencias.csv")}
    assert pen[f"PEN-DEVOL-CHK-{BRIDGE}"] == D("29.95") and f"Bridge de Idiomas Ltda: {_rs(D('29.95'))}." in notas
    assert pen[f"PEN-DEVOL-CHK-{ROTA}"] == D("1546.28") and f"Rota Global Intercâmbio Ltda: {_rs(D('1546.28'))}." in notas
    # Casa: o e-mail usa taxa × bruto; a devolução é o valor_taxa que a Orbe cobrou (truncado)
    divergencia = sum(D(l["diferenca_brl"]) for l in _ler(cont, "orbe_operacoes.csv") if l["cnpj"] == CASA)
    assert (divergencia, pen[f"PEN-DEVOL-CHK-{CASA}"]) == (D("15397.42"), D("15396.77"))
    assert f"**{_rs(D('15396.77'))}**. O e-mail usa {_rs(D('15397.42'))}" in notas
    assert f"a diferença de {_rs(D('0.65'))} é o truncamento" in notas


# ---------------------------------------------------------------- Ponte

def test_ponte_csv_bate_com_divergencias_e_pendencias(saida, cont):
    linhas = _ler(cont, "ponte_operacoes.csv")
    por_natureza = defaultdict(list)
    for l in linhas:
        por_natureza[l["natureza"]].append(l)
    assert {k: len(v) for k, v in por_natureza.items()} == {
        "SPREAD_ACIMA_CONTRATADO": 23, "SPREAD_NEGATIVO": 4, "OPERACAO_DUPLICADA": 1}

    div = {l["id_saida"]: l for l in _ler(saida, "divergencias_taxa.csv") if l["linha_negocio"] == "REMESSA"}
    pen = {l["id_saida"]: l for l in _ler(saida, "pendencias.csv")}
    acima = por_natureza["SPREAD_ACIMA_CONTRATADO"]
    assert {l["id_saida"] for l in acima} == set(div)
    assert all(l["cnpj"] == MUNDO_ABERTO and l["valor_brl"] == div[l["id_saida"]]["diferenca_brl"] for l in acima)
    assert sum(D(l["valor_brl"]) for l in acima) == D(pen[f"PEN-CONTEST-REM-{MUNDO_ABERTO}"]["valor_brl"]) == D("1418.85")
    for l in por_natureza["SPREAD_NEGATIVO"] + por_natureza["OPERACAO_DUPLICADA"]:
        assert l["id_saida"] in pen and l["valor_brl"] == pen[l["id_saida"]]["valor_brl"]
        assert l["ref_origem"] == pen[l["id_saida"]]["ref_origem"]
    assert sum(D(l["valor_brl"]) for l in por_natureza["SPREAD_NEGATIVO"]) == D("-3565.98")
    dup = por_natureza["OPERACAO_DUPLICADA"][0]
    assert (dup["id_saida"], dup["ref_origem"], dup["valor_brl"]) == ("PEN-DUP-REM-PC-0926-0162", "PC-0926-0162", "821.88")


def test_ponte_partes_da_tarvo_no_csv(cont):
    linhas = _ler(cont, "ponte_operacoes.csv")
    acima = [l for l in linhas if l["natureza"] == "SPREAD_ACIMA_CONTRATADO"]
    assert all(D(l["parte_tarvo_brl"]) == dinheiro(D(l["valor_brl"]) * D("0.5")) for l in acima)
    assert sum(D(l["parte_tarvo_brl"]) for l in acima) == D("709.46")
    neg = {l["ref_origem"]: l for l in linhas if l["natureza"] == "SPREAD_NEGATIVO"}
    assert {r: (l["spread_aplicado_brl"], l["spread_contratado_brl"], l["tarvo_deixou_de_receber_brl"]) for r, l in neg.items()} == {
        "PC-0926-0210": ("-687.52", "664.35", "332.18"), "PC-0926-0326": ("-509.22", "492.07", "246.04"),
        "PC-0926-0491": ("-292.28", "282.63", "141.32"), "PC-0926-0545": ("-345.03", "292.88", "146.44")}
    assert sum(D(l["tarvo_deixou_de_receber_brl"]) for l in neg.values()) == D("865.98")
    assert all(D(l["tarvo_deixou_de_receber_brl"]) > 0 for l in neg.values())
    dup = next(l for l in linhas if l["natureza"] == "OPERACAO_DUPLICADA")
    assert (dup["valor_brl"], dup["parte_tarvo_brl"], dup["valor_operacao_brl"]) == ("821.88", "410.94", "55811.47")


def test_ponte_totais_de_cada_secao_saem_do_csv(cont):
    linhas = _ler(cont, "ponte_operacoes.csv")
    notas, corpo = _partes(cont, "ponte.md")
    por = {n: [l for l in linhas if l["natureza"] == n] for n in ("SPREAD_ACIMA_CONTRATADO", "SPREAD_NEGATIVO", "OPERACAO_DUPLICADA")}
    assert "identificou 28 operações" in corpo

    comunicacao = _secao(corpo, "## 1. Comunicação de condição comercial")
    total_acima = sum(D(l["valor_brl"]) for l in por["SPREAD_ACIMA_CONTRATADO"])
    assert "Mundo Aberto (CNPJ 17217888000111): spread contratado de 1,20%" in comunicacao
    assert "23 operações contratadas de 2026-09-01 a 2026-09-30" in comunicacao
    assert comunicacao.count(_rs(total_acima)) == 2 and "regularização do período" in comunicacao

    negativos = _secao(corpo, "## 2. Contestação: spreads negativos")
    perdido = sum(D(l["tarvo_deixou_de_receber_brl"]) for l in por["SPREAD_NEGATIVO"])
    assert "4 operações saíram com spread negativo" in negativos and f"deixou de receber {_rs(perdido)}" in negativos
    for l in por["SPREAD_NEGATIVO"]:
        linha = next(x for x in negativos.splitlines() if x.startswith("|") and l["ref_origem"] in x)
        assert brl(D(l["tarvo_deixou_de_receber_brl"])) in linha and brl(D(l["spread_aplicado_brl"])) in linha
    assert "-R$" not in negativos.split("|")[0]  # a frase de resumo não mostra o valor como negativo

    duplicada = _secao(corpo, "## 3. Contestação: operação repetida no relatório")
    dup = por["OPERACAO_DUPLICADA"][0]
    assert "aparece 2 vezes no relatório (linhas 76 e 77)" in duplicada
    assert f"operação de {_rs(D(dup['valor_operacao_brl']))}" in duplicada
    assert f"spread da operação: {_rs(D(dup['valor_brl']))}" in duplicada
    assert f"parte da Tarvo (50% do spread): {_rs(D(dup['parte_tarvo_brl']))}" in duplicada
    assert "confirme se o cliente foi cobrado duas vezes e corrija o relatório" in duplicada

    # as notas internas repetem os números do CSV
    assert _rs(total_acima) in notas and _rs(perdido) in notas and _rs(D(dup["valor_brl"])) in notas


def test_ponte_notas_aviso_e_ressalva_da_vigencia_da_mundo_aberto(cont):
    notas = _partes(cont, "ponte.md")[0]
    assert "Mundo Aberto: nunca foi avisada" in notas
    assert 'a planilha registra a condição como vigente desde 2026-01-01 e a observação "spread negociado em jul/26"' in notas
    assert "confirme a data da condição antes de enviar" in notas
    assert "PEN-NEG" in notas and "não a parte da Tarvo" in notas


def test_textos_sem_ponto_e_virgula_nos_csvs(cont):
    for nome in ("orbe_operacoes.csv", "ponte_operacoes.csv"):
        for l in _ler(cont, nome):
            assert all(";" not in (v or "") for v in l.values())


# ---------------------------------------------------------------- casos de borda e CLI

def test_sem_itens_grava_os_arquivos_avisando_que_nao_ha_o_que_enviar(tmp_path):
    fechar(ENTRADA, tmp_path / "saida", "2026-09", modulos=[])
    cont = tmp_path / "contestacoes"
    assert _ler(cont, "orbe_operacoes.csv") == [] and _ler(cont, "ponte_operacoes.csv") == []
    assert "Não há o que enviar à Orbe" in (cont / "orbe.md").read_text(encoding="utf-8")
    assert "Não há o que enviar à Ponte Câmbio S.A." in (cont / "ponte.md").read_text(encoding="utf-8")


def test_pasta_escolhida_e_desligada(tmp_path):
    escolhida = tmp_path / "rascunhos"
    fechar(ENTRADA, tmp_path / "saida", "2026-09", modulos=[], contestacoes=escolhida)
    assert (escolhida / "orbe.md").is_file() and not (tmp_path / "contestacoes").exists()
    resultado = fechar(ENTRADA, tmp_path / "saida2", "2026-09", modulos=[], contestacoes=False)
    assert resultado.arquivos_contestacao == {} and not (tmp_path / "contestacoes").exists()


def _cli(tmp_path, *extra):
    env = {**os.environ, "PYTHONPATH": str(RAIZ / "src"), "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        [sys.executable, "-m", "tarvo", "fechar", "--competencia", "2026-09", "--entrada", str(ENTRADA),
         "--saida", str(tmp_path / "saida"), *extra],
        capture_output=True, text=True, encoding="utf-8", env=env, cwd=RAIZ)


def test_cli_lista_os_rascunhos_e_grava_na_pasta_irma(tmp_path):
    r = _cli(tmp_path)
    assert r.returncode == 0, r.stderr
    assert "Rascunhos de contestação gravados (4)" in r.stdout
    assert all(n in r.stdout for n in ("orbe.md", "orbe_operacoes.csv", "ponte.md", "ponte_operacoes.csv"))
    assert (tmp_path / "contestacoes" / "orbe.md").is_file()
    assert sorted(p.name for p in (tmp_path / "saida").iterdir()) == SEIS_CSVS


def test_cli_sem_contestacao_nao_grava_a_pasta(tmp_path):
    r = _cli(tmp_path, "--sem-contestacao")
    assert r.returncode == 0, r.stderr
    assert "desligados (--sem-contestacao)" in r.stdout and not (tmp_path / "contestacoes").exists()


# ---------------------------------------------------------------- config

def _config_com(tmp_path, alterar):
    cfg = yaml.safe_load((RAIZ / "config" / "contestacao.yaml").read_text(encoding="utf-8"))
    alterar(cfg)
    caminho = tmp_path / "contestacao.yaml"
    caminho.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return caminho


def test_config_com_aviso_sem_texto_e_erro(tmp_path):
    caminho = _config_com(tmp_path, lambda c: c["lojistas"][BRIDGE].update(aviso="tipo_que_nao_existe"))
    with pytest.raises(ErroContestacao, match="tipo_que_nao_existe"):
        carregar_config(caminho)


def test_config_com_secao_invalida_e_erro(tmp_path):
    caminho = _config_com(tmp_path, lambda c: c["lojistas"][BRIDGE].update(secao="outra"))
    with pytest.raises(ErroContestacao, match="secao"):
        carregar_config(caminho)
