"""Fechamento parcial (R44) em cópias temporárias de dados/2026-09: o que fecha, o que fica bloqueado, a pendência
gerada e o código de saída. Sem valores de referência: cada caso é comparado com o fechamento completo."""

import csv
import dataclasses
import shutil
from pathlib import Path

import pytest

from tarvo import cli
from tarvo import dependencias as dep
from tarvo.bancos import bancos
from tarvo.checkout import checkout
from tarvo.fechamento import fechar, ler_entradas
from tarvo.leitores.layout import avisos_layout
from tarvo.remessa import remessa
from tarvo.resumo import ler_saida, resumir, status
from tarvo.saida import ARQUIVOS, ARQUIVOS_ITENS, validar_saida

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "dados" / "2026-09"


def _ler(pasta: Path, nome: str) -> list[dict]:
    with open(pasta / nome, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _ids(pasta: Path) -> set[str]:
    return {l["id_saida"] for e in ARQUIVOS_ITENS for l in _ler(pasta, e.nome)}


def _prefixos(pasta: Path) -> set[str]:
    return {"-".join(i.split("-")[:2]) for i in _ids(pasta)}


def _pendencias(pasta: Path) -> dict[str, dict]:
    return {l["id_saida"]: l for l in _ler(pasta, "pendencias.csv")}


def _um(pasta: Path, padrao: str) -> Path:
    (arquivo,) = pasta.glob(padrao)
    return arquivo


@pytest.fixture(scope="module")
def completo(tmp_path_factory):
    raiz = tmp_path_factory.mktemp("completo")
    resultado = fechar(ENTRADA, raiz / "saida", "2026-09", usar_ia=False)
    return raiz / "saida", resultado


@pytest.fixture
def copia(tmp_path):
    pasta = tmp_path / "entrada"
    shutil.copytree(ENTRADA, pasta)
    return pasta


def _rodar(copia: Path, tmp_path: Path, capsys) -> tuple[int, str, Path]:
    saida = tmp_path / "saida"
    codigo = cli.main(["fechar", "--competencia", "2026-09", "--entrada", str(copia), "--saida", str(saida),
                       "--sem-ia"])
    return codigo, capsys.readouterr().out, saida


def _sem_os_itens_de(saida: Path, completo_saida: Path, *prefixos: str) -> None:
    """Todo item do completo continua, menos os dos prefixos, que somem."""
    ids, ref = _ids(saida), _ids(completo_saida)
    assert not {i for i in ids if i.startswith(prefixos)}
    assert {i for i in ref if not i.startswith(prefixos)} <= ids


def test_completo_sai_com_0_e_status_completo(completo):
    saida, resultado = completo
    assert resultado.completo and resultado.quadro() == "FECHAMENTO COMPLETO"
    assert status(ler_saida(saida))[0] == "COMPLETO"
    assert not [l for l in _ler(saida, "pendencias.csv") if l["id_saida"].startswith(("PEN-BLOQUEIO", "PEN-SEMCONF",
                                                                                       "PEN-AVISO"))]
    assert all("situacao" not in _ler(saida, e.nome)[0] for e in ARQUIVOS_ITENS if _ler(saida, e.nome))


# ---------------------------------------------------------------- (h) os seis casos

def test_sem_o_ofx(completo, copia, tmp_path, capsys):
    _um(copia, "*.ofx").unlink()
    codigo, texto, saida = _rodar(copia, tmp_path, capsys)
    assert codigo == 3
    assert "FECHAMENTO PARCIAL — fontes bloqueadas: meridiano (ausente); não gerado: lançamentos do Meridiano" in texto
    # fecha: checkout, remessa, Aurora; não gera: Meridiano e as conferências que dependem dele
    _sem_os_itens_de(saida, completo[0], "LAN-MER-", "PEN-TRANSF-")
    pen = _pendencias(saida)
    assert pen["PEN-BLOQUEIO-MERIDIANO"]["tipo"] == "FONTE_BLOQUEADA"
    assert pen["PEN-BLOQUEIO-MERIDIANO"]["quem_decide"] == "Financeiro (Helena)"
    # as conferências que perderam o Meridiano dizem o que ficou sem conferir (o lado da Ponte e o do Aurora)
    assert {i for i in pen if i.startswith("PEN-SEMCONF-")} == {"PEN-SEMCONF-TED-LIQ", "PEN-SEMCONF-PIX-REM",
                                                                 "PEN-SEMCONF-TRANSF"}
    assert "PEN-BLOQUEIO-MERIDIANO" in pen["PEN-SEMCONF-TRANSF"]["motivo"]
    assert validar_saida(saida) == []


def test_sem_o_eml(completo, copia, tmp_path, capsys):
    _um(copia, "*.eml").unlink()
    codigo, texto, saida = _rodar(copia, tmp_path, capsys)
    assert codigo == 3 and "fontes bloqueadas: ponte_eml (ausente)" in texto
    _sem_os_itens_de(saida, completo[0], "COM-REM-", "NF-REM-", "DIV-REM-", "PEN-CONTEST-REM-", "PEN-NEG-REM-",
                     "PEN-DUP-REM-", "PEN-TED-PONTE")
    pen = _pendencias(saida)
    assert "PEN-BLOQUEIO-PONTE_EML" in pen
    # as TEDs de liquidação e os PIX do Meridiano ficaram sem conferir: pendência explicada, com o rastro em cada um
    ted, pix = pen["PEN-SEMCONF-TED-LIQ"], pen["PEN-SEMCONF-PIX-REM"]
    assert "as TEDs LIQ OPERACOES do Meridiano sem conferir" in ted["motivo"]
    assert "os PIX recebidos de clientes no Meridiano sem conferir" in pix["motivo"]
    lancamentos = {l["ref_origem"]: l for l in _ler(saida, "lancamentos_classificados.csv") if l["banco"] == "MERIDIANO"}
    assert set(ted["ref_origem"].split("|")) <= set(lancamentos)
    assert "PEN-TRANSF-" in "".join(pen)  # a transferência Aurora × Meridiano não depende da Ponte
    ponte_md = (tmp_path / "contestacoes" / "ponte.md").read_text(encoding="utf-8")
    assert "[BLOQUEADO — rascunho não gerado nesta execução]" in ponte_md and "PEN-BLOQUEIO-PONTE_EML" in ponte_md
    assert len(_ler(tmp_path / "contestacoes", "ponte_operacoes.csv")) == 0
    assert validar_saida(saida) == []


def test_planilha_de_taxas_duplicada(completo, copia, tmp_path, capsys):
    taxas = _um(copia, "*taxas*.xlsx")
    shutil.copyfile(taxas, copia / f"{taxas.stem} (1).xlsx")
    codigo, texto, saida = _rodar(copia, tmp_path, capsys)
    assert codigo == 3 and "fontes bloqueadas: taxas (ambígua)" in texto
    assert not _prefixos(saida) & {"COM-CHK", "COM-REM", "NF-CHK", "NF-REM", "DIV-CHK", "DIV-REM"}
    lan = [l["id_saida"] for l in _ler(saida, "lancamentos_classificados.csv")]
    assert lan == [l["id_saida"] for l in _ler(completo[0], "lancamentos_classificados.csv")]
    pen = _pendencias(saida)["PEN-BLOQUEIO-TAXAS"]
    assert pen["quem_decide"] == "Comercial e Financeiro (Helena)"  # R28: taxa, o Comercial decide antes
    assert taxas.name in pen["motivo"] and f"{taxas.stem} (1).xlsx" in pen["motivo"] and "CORREÇÃO" in pen["motivo"]
    assert pen["ref_origem"].split("|") == sorted([taxas.name, f"{taxas.stem} (1).xlsx"])
    assert "não foram conferidos com a planilha (P07, P08)" in pen["motivo"]
    assert validar_saida(saida) == []


def test_relatorio_da_orbe_com_coluna_renomeada(completo, copia, tmp_path, capsys):
    relatorio = sorted(copia.glob("*orbe*.csv"))[0]
    relatorio.write_bytes(relatorio.read_bytes().replace(b";valor_taxa;", b";vlr_taxa;", 1))
    codigo, texto, saida = _rodar(copia, tmp_path, capsys)
    assert codigo == 3 and "fontes bloqueadas: orbe (ilegível)" in texto
    _sem_os_itens_de(saida, completo[0], "COM-CHK-", "NF-CHK-", "DIV-CHK-", "PEN-NF-CHK-", "PEN-DEVOL-CHK-",
                     "PEN-CONCESSAO-CHK-", "PEN-SEMCONTRATO-", "PEN-ALERTA-ANTEC-")
    pen = _pendencias(saida)["PEN-BLOQUEIO-ORBE"]
    assert f"{relatorio.name}: colunas ausentes no cabeçalho: ['valor_taxa']" in pen["motivo"]
    assert _ler(saida, "rastro.csv")[-1] == {"id_saida": "PEN-BLOQUEIO-ORBE", "arquivo_origem": relatorio.name,
                                             "ref_origem": "L1", "valor": "0.00", "regra": "R44",
                                             "detalhe": "fonte bloqueada: orbe - ponto citado no erro, valor 0,00"}
    assert validar_saida(saida) == []


def test_arquivo_06_com_cabecalho_diferente(completo, copia, tmp_path, capsys):
    ajustes = sorted(copia.glob("*orbe*.csv"))[-1]
    ajustes.write_bytes(ajustes.read_bytes().replace(b";tipo_lancamento;", b";tipo;", 1))
    codigo, texto, saida = _rodar(copia, tmp_path, capsys)
    assert codigo == 3
    assert f"fontes bloqueadas: orbe (só o arquivo {ajustes.name}); não gerado: nada" in texto
    # o 01 é lido: todo item do completo continua, provisório no checkout
    assert _ids(saida) - {f"PEN-BLOQUEIO-ORBE-{ajustes.name}"} == _ids(completo[0])
    situacao = {l["id_saida"]: l["situacao"] for l in _ler(saida, "comissoes_por_lojista.csv")}
    assert {s for i, s in situacao.items() if i.startswith("COM-CHK")} == {"PROVISORIO"}
    assert {s for i, s in situacao.items() if i.startswith("COM-REM")} == {""}
    assert "**PROVISÓRIO:**" in (tmp_path / "contestacoes" / "orbe.md").read_text(encoding="utf-8")
    resumo = resumir(saida)
    assert any(l.startswith("**Status do fechamento: PARCIAL**") for l in resumo.splitlines()[:6])
    assert validar_saida(saida) == []


def test_coluna_a_mais_so_avisa(completo, copia, tmp_path, capsys):
    aurora = _um(copia, "*aurora*.csv")
    linhas = aurora.read_text(encoding="utf-8").split("\n")
    titulo = next(i for i, l in enumerate(linhas) if l.lower().startswith("data;"))
    for i in range(titulo, len(linhas)):
        if linhas[i].strip():
            linhas[i] = linhas[i].rstrip("\r") + (";Categoria" if i == titulo else ";x") + ("\r" if linhas[i].endswith("\r") else "")
    aurora.write_text("\n".join(linhas), encoding="utf-8", newline="")
    codigo, texto, saida = _rodar(copia, tmp_path, capsys)
    assert codigo == 0 and "FECHAMENTO COMPLETO" in texto
    assert "coluna(s) fora do layout esperado: CATEGORIA" in texto
    pen = _pendencias(saida)["PEN-AVISO-LAYOUT-AURORA"]
    assert pen["tipo"] == "AVISO_LAYOUT" and pen["valor_brl"] == "0.00" and "próximo passo:" in pen["motivo"]
    for e in ARQUIVOS:  # fora a pendência de aviso, a saída é a do completo
        if e.nome not in ("pendencias.csv", "rastro.csv"):
            assert (saida / e.nome).read_bytes() == (completo[0] / e.nome).read_bytes(), e.nome
    assert status(ler_saida(saida))[0] == "COMPLETO"


# ---------------------------------------------------------------- outros casos

def test_coluna_fora_de_ordem_so_avisa():
    assert avisos_layout("x.csv", ["A", "C", "B"], ["A", "B", "C"]) == [
        "x.csv: colunas fora da ordem esperada (a partir de 'C', no lugar de 'B'); a leitura seguiu pelo nome da coluna"]
    assert avisos_layout("x.csv", ["A", "B", "C", ""], ["A", "B", "C"]) == []


def test_arquivo_ilegivel_bloqueia_com_o_erro(copia, tmp_path, capsys):
    _um(copia, "*taxas*.xlsx").write_bytes(b"isto nao e um xlsx")
    codigo, _, saida = _rodar(copia, tmp_path, capsys)
    assert codigo == 3
    pen = _pendencias(saida)["PEN-BLOQUEIO-TAXAS"]
    assert "bloqueada (ilegível, R44)" in pen["motivo"] and "BadZipFile" in pen["motivo"]


def test_pasta_sem_nenhum_arquivo_do_mes_bloqueia_tudo_e_grava_saida_valida(tmp_path, capsys):
    vazia = tmp_path / "vazia"
    vazia.mkdir()
    codigo, texto, saida = _rodar(vazia, tmp_path, capsys)
    assert codigo == 3
    assert {i for i in _ids(saida)} == {f"PEN-BLOQUEIO-{t.upper()}" for t in
                                       ("orbe", "taxas", "ponte_eml", "plano_de_contas", "aurora", "meridiano")}
    assert validar_saida(saida) == []


def test_parcial_tambem_grava_so_depois_de_validar(copia, tmp_path, monkeypatch, capsys):
    from tarvo import fechamento
    _um(copia, "*.ofx").unlink()
    monkeypatch.setattr(fechamento, "validar_saida", lambda pasta: ["problema simulado"])
    assert cli.main(["fechar", "--competencia", "2026-09", "--entrada", str(copia), "--saida",
                     str(tmp_path / "saida")]) == 1
    assert not (tmp_path / "saida").exists()


# ---------------------------------------------------------------- o mapa de dependências bate com o código

MARCAS = {  # o que só aparece quando o produto é gerado
    "checkout": "COM-CHK-", "remessa": "NF-REM-", "lancamentos_aurora": "LAN-AUR-", "lancamentos_meridiano": "LAN-MER-",
    "conferencia_transferencias": "PEN-TRANSF-",
}


@pytest.fixture(scope="module")
def entradas():
    return ler_entradas(ENTRADA, "2026-09", usar_ia=False)


CAMPOS = {"orbe": ("orbe",), "taxas": ("taxas",), "ponte_eml": ("ponte", "ponte_rodape"),
          "plano_de_contas": ("plano_contas",), "aurora": ("aurora", "aurora_meta"),
          "meridiano": ("meridiano", "meridiano_meta")}


def _so_com(entradas, fontes):
    """Entradas só com as fontes pedidas: as outras viram None, como uma fonte bloqueada."""
    fora = [f for f in CAMPOS if f not in fontes]
    return dataclasses.replace(entradas, **{c: None for f in fora for c in CAMPOS[f]},
                               bloqueios=tuple(dep.Bloqueio(f, dep.AUSENTE, "teste", (("x", "y"),), "teste") for f in fora))


@pytest.mark.parametrize("produto", dep.PRODUTOS, ids=lambda p: p.chave)
def test_cada_produto_roda_so_com_as_fontes_do_mapa(entradas, produto):
    # se um módulo lesse uma fonte fora do mapa, ela viria None e o módulo quebraria
    so = _so_com(entradas, produto.fontes)
    itens = [i.id_saida for m in (checkout, remessa, bancos) for i in m(so)]
    if produto.chave in MARCAS:
        assert any(i.startswith(MARCAS[produto.chave]) for i in itens)
    assert dep.gera(produto.chave, so)
    for fonte in produto.fontes:  # e sem qualquer uma delas o produto não sai
        assert not dep.gera(produto.chave, _so_com(entradas, set(produto.fontes) - {fonte}))


def test_conferencias_sem_um_lado_viram_pendencia_e_com_os_dois_nao(entradas):
    completas = [i.id_saida for i in bancos(entradas)]
    assert not [i for i in completas if i.startswith("PEN-SEMCONF-")]
    sem_ponte = [i.id_saida for i in bancos(_so_com(entradas, ("aurora", "meridiano", "plano_de_contas", "taxas")))]
    assert {i for i in sem_ponte if i.startswith("PEN-SEMCONF-")} == {"PEN-SEMCONF-TED-LIQ", "PEN-SEMCONF-PIX-REM"}


# ---------------------------------------------------------------- RESULTADOS.md

def test_resultados_md_mostra_no_topo_o_status_da_saida_de_setembro():
    situacao = status(ler_saida(RAIZ / "saida"))[0]
    topo = (RAIZ / "RESULTADOS.md").read_text(encoding="utf-8").splitlines()[:6]
    assert any(f"Status do fechamento: {situacao}" in l for l in topo), topo


def test_resultados_md_tabela_dos_rascunhos_bate_com_contestacoes():
    """A tabela da R29 no RESULTADOS.md repete o que está nos arquivos de contestacoes/ (linhas e total)."""
    from decimal import Decimal
    from tarvo.resumo import brl
    texto = (RAIZ / "RESULTADOS.md").read_text(encoding="utf-8")
    orbe = _ler(RAIZ / "contestacoes", "orbe_operacoes.csv")
    total = sum((Decimal(l["diferenca_brl"]) for l in orbe), Decimal("0.00"))
    assert f"| orbe_operacoes.csv | DIV-CHK: " in texto and f" | {len(orbe)} | {brl(total)} | " in texto
    ponte = _ler(RAIZ / "contestacoes", "ponte_operacoes.csv")
    for natureza in {l["natureza"] for l in ponte}:
        ls = [l for l in ponte if l["natureza"] == natureza]
        soma = sum((Decimal(l["valor_brl"]) for l in ls), Decimal("0.00"))
        linha = next(l for l in texto.splitlines() if l.startswith(f"| ponte_operacoes.csv · {natureza} |"))
        assert f" | {len(ls)} | {brl(soma)} | " in linha, linha
