"""Resumo da saída com itens sintéticos (nenhum valor de competência real)."""

import os
import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from tarvo.resumo import ErroResumo, brl, conferir_rastro, ler_saida, resumir
from tarvo.saida import COMISSOES, DIVERGENCIAS, LANCAMENTOS, NOTAS, PENDENCIAS, RASTRO, ItemSaida, gravar_saida

D = Decimal
RAIZ = Path(__file__).resolve().parents[1]
CNPJ_A = "00111222000133"
CNPJ_B = "44555666000177"
TOMADOR = "99888777000166"


def _item(id_saida, arquivo, campos, valor, refs=None):
    """Item com rastro em uma origem por ref, o valor todo na última."""
    refs = refs or [id_saida]
    origens = [("teste.csv", r, D("0.00")) for r in refs[:-1]] + [("teste.csv", refs[-1], valor)]
    return ItemSaida(id_saida, arquivo, campos, valor, origens)


def _com(cnpj, nome, linha, valor):
    return _item(f"COM-{linha[:3]}-{cnpj}", COMISSOES.nome,
                 {"cnpj": cnpj, "lojista": nome, "linha_negocio": linha}, D(valor))


def _div(ref, cnpj, linha, valor):
    return _item(f"DIV-{ref}", DIVERGENCIAS.nome,
                 {"cnpj": cnpj, "linha_negocio": linha, "ref_origem": ref,
                  "taxa_contratada_pct": D("1.0000"), "taxa_aplicada_pct": D("2.0000")}, D(valor))


def _lan(ref, banco, conta, metodo, valor):
    return _item(f"LAN-{ref}", LANCAMENTOS.nome,
                 {"banco": banco, "ref_origem": ref, "data": date(2031, 3, 10), "descricao": f"LANC {ref}",
                  "conta_codigo": conta, "metodo": metodo, "confianca": D("1.00")}, D(valor))


def _pen(id_saida, tipo, quem, valor, refs):
    return _item(id_saida, PENDENCIAS.nome,
                 {"tipo": tipo, "ref_origem": refs, "motivo": f"motivo de {id_saida}", "quem_decide": quem},
                 D(valor), refs)


ITENS = [
    _com(CNPJ_A, "Loja A Ltda", "CHECKOUT", "1500.25"),
    _com(CNPJ_B, "Loja B Ltda", "CHECKOUT", "-3.00"),
    _com(CNPJ_A, "Loja A Ltda", "REMESSA", "200.00"),
    _item(f"NF-CHK-{CNPJ_A}", NOTAS.nome, {"tomador_cnpj": CNPJ_A, "tomador": "Loja A Ltda",
          "linha_negocio": "CHECKOUT", "discriminacao": "serviço - competência 2031-03"}, D("1500.25")),
    _item(f"NF-REM-{TOMADOR}", NOTAS.nome, {"tomador_cnpj": TOMADOR, "tomador": "Corretora",
          "linha_negocio": "REMESSA", "discriminacao": "intermediação - competência 2031-03"}, D("200.00")),
    *[_div(f"T{n}", CNPJ_A, "CHECKOUT", f"{n}.00") for n in range(1, 8)],   # 1 a 7: as 5 maiores são 7 a 3
    _div("T8", CNPJ_B, "CHECKOUT", "-4.50"),
    _div("OP1", CNPJ_A, "REMESSA", "-10.00"),
    _lan("L1", "AURORA", "1.1.03.001", "REGRA", "1000.00"),
    _lan("L2", "AURORA", "1.1.03.001", "REGRA", "500.00"),
    _lan("L3", "AURORA", "A_CLASSIFICAR", "HUMANO", "-20.00"),
    _lan("M1", "MERIDIANO", "4.2.01", "IA", "-7.30"),
    _pen("PEN-A", "TIPO_X", "Financeiro", "3.00", ["T1", "T2"]),
    _pen("PEN-B", "TIPO_X", "Comercial", "-1.00", ["T3"]),
    _pen("PEN-C", "TIPO_Y", "Financeiro", "1234567.89", ["L1"]),
]


@pytest.fixture
def saida(tmp_path):
    gravar_saida(tmp_path, ITENS)
    return tmp_path


def test_brl():
    assert brl(D("1234567.8")) == "1.234.567,80"
    assert brl(D("-0.5")) == "-0,50"
    assert brl(D("0")) == "0,00"
    assert brl(D("-1234.56")) == "-1.234,56"


def test_comissoes_por_linha_e_por_lojista(saida):
    texto = resumir(saida)
    assert "| CHECKOUT | 2 | 1.497,25 |" in texto
    assert "| REMESSA | 1 | 200,00 |" in texto
    assert "| **total** | 3 | 1.697,25 |" in texto
    assert f"| {CNPJ_A} | Loja A Ltda | 1.500,25 |" in texto
    assert f"| {CNPJ_B} | Loja B Ltda | -3,00 |" in texto
    # a maior comissão vem primeiro dentro da linha de negócio
    assert texto.index(f"| {CNPJ_A} | Loja A Ltda | 1.500,25 |") < texto.index(f"| {CNPJ_B} | Loja B Ltda | -3,00 |")


def test_notas_e_total(saida):
    texto = resumir(saida)
    assert f"| {CNPJ_A} | Loja A Ltda | CHECKOUT | 1.500,25 |" in texto
    assert f"| {TOMADOR} | Corretora | REMESSA | 200,00 |" in texto
    assert "| **total** | 2 notas |  | **1.700,25** |" in texto


def test_divergencias_por_lojista_maiores_e_negativas(saida):
    texto = resumir(saida)
    assert "| CHECKOUT | 8 | 23,50 |" in texto                       # 1+...+7 - 4,50
    assert "| **total** | 9 | 13,50 |" in texto
    assert f"| CHECKOUT | {CNPJ_A} | Loja A Ltda | 7 | 28,00 |" in texto
    assert f"| CHECKOUT | {CNPJ_B} | Loja B Ltda | 1 | -4,50 |" in texto
    assert f"| REMESSA | {CNPJ_A} | Loja A Ltda | 1 | -10,00 |" in texto

    maiores = texto.split("### As 5 maiores")[1].split("###")[0]
    assert [f"DIV-T{n}" for n in (7, 6, 5, 4, 3)] == [l.split(" | ")[0][2:] for l in maiores.splitlines()
                                                    if l.startswith("| DIV-")]
    negativas = texto.split("### Negativas")[1].split("##")[0]
    assert negativas.startswith(" (2 linhas, soma R$ -14,50)")
    assert [l.split(" | ")[0][2:] for l in negativas.splitlines() if l.startswith("| DIV-")] == ["DIV-OP1", "DIV-T8"]


def test_lancamentos_por_banco_conta_e_metodo(saida):
    texto = resumir(saida)
    assert "| AURORA | 3 | 1.480,00 |" in texto
    assert "| AURORA | 1.1.03.001 | 2 | 1.500,00 |" in texto
    assert "| AURORA | A_CLASSIFICAR | 1 | -20,00 |" in texto
    assert "| MERIDIANO | 4.2.01 | 1 | -7,30 |" in texto
    metodos = texto.split("### Por método")[1].split("##")[0]
    assert "| REGRA | 2 | 1.500,00 |" in metodos
    assert "| IA | 1 | -7,30 |" in metodos
    assert "| HUMANO | 1 | -20,00 |" in metodos


def test_pendencias_por_tipo_quem_decide_e_lista(saida):
    texto = resumir(saida)
    assert "| TIPO_X | 2 | 2,00 |" in texto
    assert "| TIPO_Y | 1 | 1.234.567,89 |" in texto
    assert "| **total** | 3 | 1.234.569,89 |" in texto
    assert "| Financeiro | 2 | 1.234.570,89 |" in texto
    assert "| Comercial | 1 | -1,00 |" in texto
    assert "| PEN-A | TIPO_X | 2 | 3,00 | Financeiro | motivo de PEN-A |" in texto


def test_rastro_fecha(saida):
    conf = conferir_rastro(ler_saida(saida))
    assert conf.ok and conf.itens == conf.conferidos == len(ITENS)
    texto = resumir(saida)
    assert "| rastro.csv | " in texto and "| divergencias_taxa.csv | 9 |" in texto
    assert "**rastro fecha**" in texto and "validar_saida: sem problemas" in texto


def test_rastro_que_nao_fecha_aparece_no_resumo(saida):
    caminho = saida / RASTRO.nome
    texto = caminho.read_text(encoding="utf-8")
    assert "PEN-C;teste.csv;L1;1234567.89\n" in texto
    caminho.write_text(texto.replace("PEN-C;teste.csv;L1;1234567.89\n", "PEN-C;teste.csv;L1;1234567.88\n")
                       + "COM-ORFAO;teste.csv;X;1.00\n", encoding="utf-8", newline="")

    conf = conferir_rastro(ler_saida(saida))
    assert conf.divergentes == [("PEN-C", D("1234567.89"), D("1234567.88"))]
    assert conf.orfaos == ["COM-ORFAO"] and not conf.ok
    resumo = resumir(saida)
    assert "**rastro NÃO fecha**" in resumo
    assert "PEN-C: reportado 1.234.567,89, rastro 1.234.567,88" in resumo
    assert "COM-ORFAO: no rastro, fora dos 5 arquivos" in resumo


def test_pasta_sem_os_6_csvs(tmp_path):
    with pytest.raises(ErroResumo, match="rastro.csv"):
        resumir(tmp_path)


def test_cli_resumo(saida):
    env = {**os.environ, "PYTHONPATH": str(RAIZ / "src"), "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, "-m", "tarvo", "resumo", "--saida", str(saida)],
                       capture_output=True, text=True, encoding="utf-8", env=env, cwd=RAIZ)
    assert r.returncode == 0, r.stderr
    assert r.stdout == resumir(saida)


def test_cli_resumo_pasta_vazia(tmp_path):
    env = {**os.environ, "PYTHONPATH": str(RAIZ / "src"), "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, "-m", "tarvo", "resumo", "--saida", str(tmp_path)],
                       capture_output=True, text=True, encoding="utf-8", env=env, cwd=RAIZ)
    assert r.returncode == 2 and "faltam" in r.stderr


def test_resumo_traz_o_commit_e_a_branch_atuais(saida):
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, capture_output=True, text=True).stdout.strip()
    branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=RAIZ, capture_output=True, text=True).stdout.strip()
    assert f"Commit do código: {commit} (branch {branch})" in resumir(saida)


def test_sem_git_o_resumo_diz_commit_indisponivel(saida, monkeypatch):
    import tarvo.resumo as resumo

    def sem_git(*_, **__):
        raise FileNotFoundError("git")
    monkeypatch.setattr(resumo.subprocess, "run", sem_git)
    assert "Commit do código: commit indisponível" in resumir(saida)
    assert resumo.versao_do_codigo(Path("/")) == "commit indisponível"
