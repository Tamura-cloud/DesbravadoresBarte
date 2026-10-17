"""Registro de execução (O06): auditoria/execucao.json e execucao.md da última execução, numa pasta irmã de saida/.

Os valores de setembro (linhas lidas, totais) aparecem aqui só como referência."""

import csv
import hashlib
import json
import re
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from tarvo import cli
from tarvo import fechamento
from tarvo.auditoria import ARQUIVO_JSON, ARQUIVO_MD, carregar_config
from tarvo.fechamento import fechar
from tarvo.saida import ARQUIVOS

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "dados" / "2026-09"


def _json(pasta: Path) -> dict:
    with open(pasta / ARQUIVO_JSON, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def completo(tmp_path_factory):
    raiz = tmp_path_factory.mktemp("auditoria")
    shutil.copytree(ENTRADA, raiz / "entrada")
    codigo = cli.main(["fechar", "--competencia", "2026-09", "--entrada", str(raiz / "entrada"),
                       "--saida", str(raiz / "saida"), "--sem-ia"])
    return raiz, codigo


def test_grava_json_e_md_na_pasta_irma_e_saida_continua_com_6_csvs(completo):
    raiz, codigo = completo
    assert codigo == 0
    assert carregar_config().pasta == "auditoria"
    assert sorted(p.name for p in (raiz / "auditoria").iterdir()) == [ARQUIVO_JSON, ARQUIVO_MD]
    assert sorted(p.name for p in (raiz / "saida").iterdir()) == sorted(e.nome for e in ARQUIVOS)
    assert not any(p.name.startswith(fechamento.PREFIXO_PREPARO) for p in raiz.iterdir())


def test_registro_tem_execucao_entradas_e_saida(completo):
    raiz, _ = completo
    r = _json(raiz / "auditoria")
    assert r["competencia"] == "2026-09" and r["status"] == "COMPLETO" and r["codigo_saida"] == 0
    assert r["data_hora"][:4] == "2026" or r["data_hora"][:2] == "20"
    assert r["codigo"]["commit"]  # o hash curto ou "indisponível"
    assert r["comando"].startswith("python -m tarvo fechar --competencia 2026-09 --entrada ")
    assert "--sem-ia" in r["comando"] and r["fontes_bloqueadas"] == []
    entradas = {a["nome"]: a for a in r["arquivos_entrada"]}
    assert sorted(entradas) == sorted(p.name for p in (raiz / "entrada").iterdir()
                                      if p.name not in ("00_LEIA-ME.md", "01_instrucoes_participantes.docx"))
    for nome, a in entradas.items():
        caminho = raiz / "entrada" / nome
        assert a["sha256"] == hashlib.sha256(caminho.read_bytes()).hexdigest()
        assert a["tamanho_bytes"] == caminho.stat().st_size and a["situacao"] == "lido"
    # valores de referência de setembro
    lidas = {a["tipo"] + ":" + a["nome"][:3]: a["linhas_lidas"] for a in entradas.values()}
    assert lidas == {"orbe:01_": 1943, "orbe:06_": 14, "taxas:02_": 25, "ponte_eml:03_": 233,
                     "plano_de_contas:04_": 52, "aurora:05a": 84, "meridiano:05b": 100}
    assert {a["nome"] for a in r["arquivos_ignorados"]} == {"00_LEIA-ME.md", "01_instrucoes_participantes.docx"}


def test_linhas_e_totais_da_saida_batem_com_os_csvs(completo):
    raiz, _ = completo
    r = _json(raiz / "auditoria")
    for s, espec in zip(r["saida"], ARQUIVOS):
        with open(raiz / "saida" / espec.nome, encoding="utf-8", newline="") as f:
            linhas = list(csv.DictReader(f, delimiter=";"))
        assert s["arquivo"] == espec.nome and s["linhas"] == len(linhas)
        assert Decimal(s["total"]) == sum((Decimal(l[espec.coluna_valor]) for l in linhas), Decimal("0.00"))
        assert s["sha256"] == hashlib.sha256((raiz / "saida" / espec.nome).read_bytes()).hexdigest()
    assert {s["arquivo"]: s["linhas"] for s in r["saida"]}["comissoes_por_lojista.csv"] == 35
    assert [c["arquivo"] for c in r["contestacoes"]] == ["orbe.md", "orbe_operacoes.csv", "ponte.md",
                                                         "ponte_operacoes.csv"]
    md = (raiz / "auditoria" / ARQUIVO_MD).read_text(encoding="utf-8")
    assert "**COMPLETO**" in md and "## Arquivos de entrada" in md and "## Arquivos ignorados" in md
    assert "06_orbe_ajustes_tardios_set2026.csv" in md and "| rastro.csv |" in md


def test_parcial_registra_fonte_bloqueada_e_codigo_3(tmp_path):
    shutil.copytree(ENTRADA, tmp_path / "entrada")
    next((tmp_path / "entrada").glob("*.ofx")).unlink()
    assert cli.main(["fechar", "--competencia", "2026-09", "--entrada", str(tmp_path / "entrada"),
                     "--saida", str(tmp_path / "saida"), "--sem-ia", "--sem-contestacao"]) == 3
    r = _json(tmp_path / "auditoria")
    assert r["status"] == "PARCIAL" and r["codigo_saida"] == 3 and r["contestacoes"] == []
    assert [(b["fonte"], b["natureza"]) for b in r["fontes_bloqueadas"]] == [("meridiano", "ausente")]
    assert "--sem-contestacao" in r["comando"]


def test_ajustes_bloqueados_aparecem_como_bloqueados(tmp_path):
    shutil.copytree(ENTRADA, tmp_path / "entrada")
    ajustes = sorted((tmp_path / "entrada").glob("*orbe*.csv"))[-1]
    ajustes.write_text(ajustes.read_text(encoding="utf-8").replace("id_transacao;", "id_trans;", 1), encoding="utf-8",
                       newline="")
    fechar(tmp_path / "entrada", tmp_path / "saida", "2026-09", contestacoes=False)
    entradas = {a["nome"]: a for a in _json(tmp_path / "auditoria")["arquivos_entrada"]}
    assert entradas[ajustes.name]["situacao"] == "bloqueado (ilegivel)" and entradas[ajustes.name]["linhas_lidas"] is None
    assert entradas["01_orbe_relatorio_comissoes_set2026.csv"]["situacao"] == "lido"


def test_validacao_que_falha_nao_toca_a_auditoria(tmp_path, monkeypatch):
    auditoria = tmp_path / "auditoria"
    auditoria.mkdir()
    (auditoria / ARQUIVO_JSON).write_text("{}", encoding="utf-8")
    monkeypatch.setattr(fechamento, "MODULOS", [])
    monkeypatch.setattr(fechamento, "validar_saida", lambda pasta: ["problema simulado"])
    with pytest.raises(fechamento.ErroFechamento):
        fechar(ENTRADA, tmp_path / "saida", "2026-09")
    assert sorted(p.name for p in auditoria.iterdir()) == [ARQUIVO_JSON]
    assert (auditoria / ARQUIVO_JSON).read_text(encoding="utf-8") == "{}"


def test_auditoria_false_nao_grava_e_outra_pasta_pode_ser_escolhida(tmp_path):
    resultado = fechar(ENTRADA, tmp_path / "s1", "2026-09", modulos=[], contestacoes=False, auditoria=False)
    assert resultado.arquivos_auditoria == {} and not (tmp_path / "auditoria").exists()
    resultado = fechar(ENTRADA, tmp_path / "s2", "2026-09", modulos=[], contestacoes=False,
                       auditoria=tmp_path / "registro")
    assert set(resultado.arquivos_auditoria) == {ARQUIVO_JSON, ARQUIVO_MD}
    assert (tmp_path / "registro" / ARQUIVO_JSON).is_file()


def test_guarda_dos_testes_cobre_a_pasta_auditoria_e_resultados_aponta_para_ela():
    from conftest import PROTEGIDAS
    assert "auditoria" in PROTEGIDAS
    assert "auditoria/execucao.md" in (RAIZ / "RESULTADOS.md").read_text(encoding="utf-8")


def test_rastro_de_setembro_toda_linha_tem_regra(completo):
    raiz, _ = completo
    with open(raiz / "saida" / "rastro.csv", encoding="utf-8", newline="") as f:
        rastro = list(csv.DictReader(f, delimiter=";"))
    assert [l for l in rastro if not l["regra"] or not l["detalhe"]] == []
    assert not [l for l in rastro if ";" in l["detalhe"]]


# ---------------------------------------------------------------- nenhum caminho absoluto (o repositório é público)

CAMINHO_ABSOLUTO = re.compile(r"[A-Za-z]:[\/]|(?<![\w.])/(?:Users|home|tmp|var|private)/")


def _achados(texto: str) -> list[str]:
    import getpass
    achados = [m.group(0) for m in CAMINHO_ABSOLUTO.finditer(texto)]
    usuario = getpass.getuser()
    if usuario and usuario.lower() in texto.lower():
        achados.append(f"nome de usuário {usuario!r}")
    return achados


def test_registro_sem_caminho_absoluto_nem_nome_de_usuario(completo):
    raiz, _ = completo  # a execução do teste está fora do repositório (pasta temporária do usuário)
    for nome in (ARQUIVO_JSON, ARQUIVO_MD):
        texto = (raiz / "auditoria" / nome).read_text(encoding="utf-8")
        assert _achados(texto) == [], nome
    r = _json(raiz / "auditoria")
    assert r["pasta_entrada"] == "<fora do repositório>/entrada" and r["pasta_saida"] == "<fora do repositório>/saida"
    assert r["comando"] == ('python -m tarvo fechar --competencia 2026-09 --entrada "<fora do repositório>/entrada" '
                            '--saida "<fora do repositório>/saida" --sem-ia')


def test_erro_de_leitura_com_caminho_absoluto_e_limpo(tmp_path):
    from tarvo.auditoria import RAIZ, sem_caminho_absoluto
    BS = chr(92)
    sujo = {"erro": f"não abriu {RAIZ}{BS}dados{BS}x.csv e {RAIZ.as_posix()}/dados/y.csv", "lista": [str(Path.home())]}
    limpo = sem_caminho_absoluto(sujo)
    assert limpo == {"erro": f"não abriu .{BS}dados{BS}x.csv e ./dados/y.csv", "lista": ["~"]}


def test_registro_versionado_no_repositorio_sem_caminho_absoluto():
    pasta = RAIZ / "auditoria"
    if not (pasta / ARQUIVO_JSON).is_file():
        pytest.skip("auditoria/ ainda não foi gerada")
    for nome in (ARQUIVO_JSON, ARQUIVO_MD):
        assert _achados((pasta / nome).read_text(encoding="utf-8")) == [], nome
    r = _json(pasta)
    assert r["pasta_entrada"] == "dados/2026-09" and r["pasta_saida"] == "saida"
    assert r["pasta_contestacoes"] == "contestacoes"
