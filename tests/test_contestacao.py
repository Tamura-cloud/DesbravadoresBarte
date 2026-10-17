"""R29: rascunhos de contestação por contraparte (Orbe e Ponte), com os totais do texto vindos dos CSVs."""

import csv
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from tarvo.contestacao import ErroContestacao, carregar_config
from tarvo.fechamento import fechar
from tarvo.resumo import brl

D = Decimal
ENTRADA = Path(__file__).resolve().parents[1] / "dados" / "2026-09"
CASA, ROTA, BRIDGE, MUNDO_ABERTO = "00520815000100", "95927868000148", "22224579000109", "17217888000111"
CABECALHO = "[RASCUNHO — Helena revisa antes de enviar]"


def _ler(pasta: Path, nome: str) -> list[dict]:
    with open(pasta / nome, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _texto(pasta: Path, nome: str) -> str:
    return (pasta / nome).read_text(encoding="utf-8")


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


def test_pasta_irma_com_4_arquivos_e_saida_continua_com_6_csvs(fechamento, saida, cont):
    assert sorted(p.name for p in cont.iterdir()) == ["orbe.md", "orbe_operacoes.csv", "ponte.md", "ponte_operacoes.csv"]
    assert sorted(p.name for p in saida.iterdir()) == sorted(
        ["comissoes_por_lojista.csv", "divergencias_taxa.csv", "notas_a_emitir.csv",
         "lancamentos_classificados.csv", "pendencias.csv", "rastro.csv"])
    assert set(fechamento["resultado"].arquivos_contestacao) == {p.name for p in cont.iterdir()}


def test_rascunho_sem_email_inventado(cont):
    orbe, ponte = _texto(cont, "orbe.md"), _texto(cont, "ponte.md")
    assert orbe.startswith(CABECALHO) and ponte.startswith(CABECALHO)
    assert "Para: <e-mail da Orbe>" in orbe and "Para: <e-mail da Ponte>" in ponte
    assert "@" not in orbe + ponte


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


def test_orbe_totais_do_texto_saem_do_csv(cont):
    linhas = _ler(cont, "orbe_operacoes.csv")
    texto = _texto(cont, "orbe.md")
    por_cnpj = defaultdict(lambda: [0, D("0")])
    for l in linhas:
        por_cnpj[l["cnpj"]][0] += 1
        por_cnpj[l["cnpj"]][1] += D(l["diferenca_brl"])
    assert {k: (v[0], v[1]) for k, v in por_cnpj.items()} == {
        CASA: (118, D("15397.42")), ROTA: (87, D("1546.28")), BRIDGE: (5, D("29.95"))}
    total = sum(D(l["diferenca_brl"]) for l in linhas)
    assert total == D("16973.65") and f"R$ {brl(total)}" in texto
    assert "identificamos 210 transações de 3 lojistas" in texto
    for cnpj, (qtd, soma) in por_cnpj.items():
        linha = next(l for l in texto.splitlines() if l.startswith("|") and cnpj in l)
        assert f"| {qtd} |" in linha and brl(soma) in linha


def test_orbe_estornos_ficam_no_total_e_sao_explicados(cont):
    linhas = _ler(cont, "orbe_operacoes.csv")
    estornos = [l for l in linhas if l["tipo_lancamento"] == "ESTORNO"]
    soma = sum(D(l["diferenca_brl"]) for l in estornos)
    assert (len(estornos), soma) == (5, D("-107.53"))
    assert f"Estornos: {len(estornos)} das linhas acima são estornos, com diferença negativa de -R$ {brl(abs(soma))}" in _texto(cont, "orbe.md")


def test_orbe_avisos_e_condicoes_com_data_de_inicio(cont):
    texto = _texto(cont, "orbe.md")
    casa = texto[texto.index("Casa do Estudante Viagens Ltda (CNPJ"):]
    casa = casa[:casa.index("Escola Bridge de Idiomas Ltda (CNPJ")]
    assert "vigente de 2026-09-01 a 2026-12-31" in casa and "O Comercial não avisou a Orbe" in casa
    bridge = texto[texto.index("Escola Bridge de Idiomas Ltda (CNPJ"):]
    bridge = bridge[:bridge.index("Rota Global")]
    assert "vigente desde 2026-09-15" in bridge
    assert "só foi avisada desta condição alguns dias depois do início da vigência (2026-09-15)" in bridge
    assert "vigente desde 2026-01-01" in texto  # Rota, pela planilha


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


def test_ponte_totais_do_texto_saem_do_csv(cont):
    linhas = _ler(cont, "ponte_operacoes.csv")
    texto = _texto(cont, "ponte.md")
    for natureza, qtd_txt in (("SPREAD_ACIMA_CONTRATADO", "23 operações"), ("SPREAD_NEGATIVO", "4 operações"),
                              ("OPERACAO_DUPLICADA", "1 operação")):
        ls = [l for l in linhas if l["natureza"] == natureza]
        soma = sum(D(l["valor_brl"]) for l in ls)
        rs = f"{'-' if soma < 0 else ''}R$ {brl(abs(soma))}"
        assert f"{qtd_txt}, {rs}" in texto, natureza
    assert "a Tarvo identificou 28 operações" in texto
    assert "aparece 2 vezes no relatório (linhas 76 e 77)" in texto and "cobrança em dobro" in texto


def test_ponte_aviso_da_mundo_aberto_com_inicio_da_condicao(cont):
    texto = _texto(cont, "ponte.md")
    assert "Mundo Aberto (CNPJ 17217888000111): 23 operações" in texto
    assert "vigente desde 2026-01-01" in texto and "O Comercial não avisou a Ponte Câmbio S.A. desta condição." in texto


def test_textos_sem_ponto_e_virgula_nos_csvs(cont):
    for nome in ("orbe_operacoes.csv", "ponte_operacoes.csv"):
        for l in _ler(cont, nome):
            assert all(";" not in (v or "") for v in l.values())


def test_sem_itens_grava_os_arquivos_avisando_que_nao_ha_o_que_enviar(tmp_path):
    fechar(ENTRADA, tmp_path / "saida", "2026-09", modulos=[])
    cont = tmp_path / "contestacoes"
    assert _ler(cont, "orbe_operacoes.csv") == [] and _ler(cont, "ponte_operacoes.csv") == []
    assert "Não há o que enviar à Orbe" in _texto(cont, "orbe.md")
    assert "Não há o que enviar à Ponte Câmbio S.A." in _texto(cont, "ponte.md")


def test_pasta_escolhida_e_desligada(tmp_path):
    escolhida = tmp_path / "rascunhos"
    fechar(ENTRADA, tmp_path / "saida", "2026-09", modulos=[], contestacoes=escolhida)
    assert (escolhida / "orbe.md").is_file() and not (tmp_path / "contestacoes").exists()
    resultado = fechar(ENTRADA, tmp_path / "saida2", "2026-09", modulos=[], contestacoes=False)
    assert resultado.arquivos_contestacao == {} and not (tmp_path / "contestacoes").exists()


def test_config_com_aviso_sem_texto_e_erro(tmp_path):
    cfg = yaml.safe_load((Path(__file__).resolve().parents[1] / "config" / "contestacao.yaml").read_text(encoding="utf-8"))
    cfg["avisos"]["22224579000109"] = "tipo_que_nao_existe"
    caminho = tmp_path / "contestacao.yaml"
    caminho.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ErroContestacao, match="tipo_que_nao_existe"):
        carregar_config(caminho)
