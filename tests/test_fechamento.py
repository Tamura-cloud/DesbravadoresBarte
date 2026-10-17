"""fechar(): lê as entradas reais, roda módulos sintéticos, grava e valida. Sem valores de referência."""

import os
import shutil
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from tarvo import cli
from tarvo import fechamento
from tarvo.bancos import bancos
from tarvo.checkout import checkout
from tarvo.cli import ErroEntrada
from tarvo.fechamento import MODULOS, PREFIXO_PREPARO, Entradas, fechar
from tarvo.remessa import remessa
from tarvo.saida import ARQUIVOS, PENDENCIAS, ErroSaida, ItemSaida, validar_saida

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "dados" / "2026-09"


def test_sem_modulos_grava_os_6_arquivos_validos(tmp_path):
    resultado = fechar(ENTRADA, tmp_path, "2026-09", modulos=[])
    assert resultado.itens == 0
    assert set(resultado.arquivos_saida) == {e.nome for e in ARQUIVOS}
    assert len(resultado.arquivos_entrada) == 6
    assert validar_saida(tmp_path) == []


def test_grava_direto_na_pasta_de_saida_sem_subpasta_da_competencia(tmp_path):
    resultado = fechar(ENTRADA, tmp_path, "2026-09")
    assert resultado.arquivos_saida == {e.nome: tmp_path / e.nome for e in ARQUIVOS}
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(e.nome for e in ARQUIVOS)
    assert not any(p.is_dir() for p in tmp_path.iterdir())


def test_modulos_registrados():
    assert MODULOS == [checkout, remessa, bancos]


def test_modulo_recebe_entradas_e_seus_itens_sao_gravados(tmp_path):
    recebidas = []

    def modulo(entradas):
        recebidas.append(entradas)
        yield ItemSaida("PEN-TESTE-1", PENDENCIAS.nome,
                        {"tipo": "TESTE", "ref_origem": "R1", "motivo": "sintético", "quem_decide": "Ninguém"},
                        Decimal("1.00"), [("x.csv", "R1", Decimal("1.00"))])

    resultado = fechar(ENTRADA, tmp_path, "2026-09", modulos=[modulo])
    assert resultado.itens == 1
    assert isinstance(recebidas[0], Entradas) and recebidas[0].competencia == "2026-09"
    assert "PEN-TESTE-1" in (tmp_path / PENDENCIAS.nome).read_text(encoding="utf-8")


def test_ids_repetidos_entre_modulos_falham(tmp_path):
    def modulo(_):
        return [ItemSaida("PEN-X", PENDENCIAS.nome, {}, Decimal("0.00"), [])]

    with pytest.raises(ErroSaida, match="duplicado"):
        fechar(ENTRADA, tmp_path, "2026-09", modulos=[modulo, modulo])


@pytest.mark.parametrize("competencia", ["2026-9", "2026-13", "09/2026", ""])
def test_competencia_invalida(tmp_path, competencia):
    with pytest.raises(ValueError, match="AAAA-MM"):
        fechar(ENTRADA, tmp_path, competencia, modulos=[])


# ---------------------------------------------------------------- entrada que muda durante o dia (O01)

@pytest.fixture
def copia(tmp_path):
    """Cópia de dados/2026-09 numa pasta temporária: os testes mexem nela, nunca em dados/."""
    pasta = tmp_path / "entrada"
    shutil.copytree(ENTRADA, pasta)
    return pasta


def _arquivo(pasta: Path, padrao: str) -> Path:
    (arquivo,) = pasta.glob(padrao)
    return arquivo


def test_arquivo_a_mais_no_mesmo_padrao_para_e_diz_o_que_fazer(copia, tmp_path):
    taxas = _arquivo(copia, "*taxas*.xlsx")
    shutil.copyfile(taxas, copia / f"{taxas.stem}_v2.xlsx")
    with pytest.raises(ErroEntrada) as erro:
        fechar(copia, tmp_path / "saida", "2026-09", modulos=[], contestacoes=False)
    texto = str(erro.value)
    assert f"{taxas.name}, {taxas.stem}_v2.xlsx" in texto and "'*taxas*.xlsx'" in texto
    assert "deixe só um arquivo de taxas na pasta; substitua o antigo pela versão nova" in texto
    assert not (tmp_path / "saida").exists()


def test_arquivo_faltando_diz_o_padrao_e_o_que_sobrou_na_pasta(copia, tmp_path):
    _arquivo(copia, "*.ofx").unlink()
    (copia / "extrato meridiano.txt").write_text("x", encoding="utf-8")
    with pytest.raises(ErroEntrada) as erro:
        fechar(copia, tmp_path / "saida", "2026-09", modulos=[], contestacoes=False)
    texto = str(erro.value)
    assert "meridiano (extrato do Banco Meridiano, OFX): nenhum arquivo casa com o padrão '*.ofx'" in texto
    assert "extrato meridiano.txt" in texto and "com um nome que case com '*.ofx'" in texto


def test_arquivo_estranho_e_temporario_do_office_so_avisam(copia, tmp_path):
    taxas = _arquivo(copia, "*taxas*.xlsx")
    (copia / "anotações da Helena.txt").write_text("x", encoding="utf-8")
    shutil.copyfile(taxas, copia / f"~${taxas.name}")  # Excel aberto: casa com *taxas*.xlsx, mas não é candidato
    resultado = fechar(copia, tmp_path / "saida", "2026-09", modulos=[], contestacoes=False)
    assert resultado.arquivos_entrada["taxas"] == taxas
    ignorados = {p.name: motivo for p, motivo in resultado.arquivos_ignorados}
    assert "nenhum padrão" in ignorados["anotações da Helena.txt"]
    assert "temporário do Office" in ignorados[f"~${taxas.name}"]


def test_cli_entrada_ambigua_sai_com_2_e_nao_cria_saida(copia, tmp_path, capsys):
    shutil.copyfile(_arquivo(copia, "*.eml"), copia / "reenvio da ponte.eml")
    saida = tmp_path / "saida"
    assert cli.main(["fechar", "--competencia", "2026-09", "--entrada", str(copia), "--saida", str(saida),
                     "--sem-contestacao"]) == 2
    erro = capsys.readouterr().err
    assert "Nada foi gravado" in erro and "deixe só um arquivo de ponte_eml na pasta" in erro
    assert not saida.exists()


# ---------------------------------------------------------------- grava só depois de validar

def _pastas_com_versao_antiga(tmp_path: Path) -> tuple[Path, Path, dict[Path, bytes]]:
    saida, contestacoes = tmp_path / "saida", tmp_path / "contestacoes"
    antigos = {}
    for pasta, nomes in ((saida, [e.nome for e in ARQUIVOS]), (contestacoes, ["orbe.md", "ponte.md"])):
        pasta.mkdir()
        for nome in nomes:
            antigos[pasta / nome] = f"versão anterior de {nome}\n".encode("utf-8")
            (pasta / nome).write_bytes(antigos[pasta / nome])
    return saida, contestacoes, antigos


def _sem_preparo(pasta: Path) -> bool:
    return not any(p.name.startswith(PREFIXO_PREPARO) for p in pasta.iterdir())


def test_validacao_que_falha_nao_toca_saida_nem_contestacoes(tmp_path, monkeypatch, capsys):
    saida, contestacoes, antigos = _pastas_com_versao_antiga(tmp_path)
    monkeypatch.setattr(fechamento, "MODULOS", [])
    monkeypatch.setattr(fechamento, "validar_saida", lambda pasta: ["problema simulado"])
    assert cli.main(["fechar", "--competencia", "2026-09", "--entrada", str(ENTRADA), "--saida", str(saida)]) == 1
    erro = capsys.readouterr().err
    assert "não passou na validação. Nada foi gravado" in erro and "problema simulado" in erro
    assert {p: p.read_bytes() for p in antigos} == antigos
    assert sorted(p.name for p in saida.iterdir()) == sorted(e.nome for e in ARQUIVOS)
    assert _sem_preparo(tmp_path)


def test_erro_num_modulo_nao_toca_saida(tmp_path):
    saida, _, antigos = _pastas_com_versao_antiga(tmp_path)

    def quebra(_):
        raise RuntimeError("módulo quebrou")

    with pytest.raises(RuntimeError):
        fechar(ENTRADA, saida, "2026-09", modulos=[quebra])
    assert {p: p.read_bytes() for p in antigos} == antigos
    assert _sem_preparo(tmp_path)


def test_sucesso_substitui_saida_e_contestacoes_e_apaga_o_preparo(tmp_path, monkeypatch):
    saida, contestacoes, antigos = _pastas_com_versao_antiga(tmp_path)
    monkeypatch.setattr(fechamento, "MODULOS", [])
    resultado = fechar(ENTRADA, saida, "2026-09")
    assert validar_saida(saida) == []
    assert all(p.read_bytes() != antigos[p] for p in antigos)
    assert set(resultado.arquivos_contestacao.values()) <= set(contestacoes.iterdir())
    assert _sem_preparo(tmp_path)


# ---------------------------------------------------------------- outra pasta de trabalho, caminho com espaço

def test_cli_roda_de_outra_pasta_com_espaco_no_caminho(tmp_path):
    trabalho = tmp_path / "pasta de trabalho"
    trabalho.mkdir()
    entrada = trabalho / "arquivos do mês"
    shutil.copytree(ENTRADA, entrada)
    env = {**os.environ, "PYTHONPATH": str(RAIZ / "src"), "PYTHONIOENCODING": "utf-8"}
    env.pop("ANTHROPIC_API_KEY", None)
    r = subprocess.run(
        [sys.executable, "-m", "tarvo", "fechar", "--competencia", "2026-09", "--entrada", "arquivos do mês",
         "--saida", "saída de teste"],
        capture_output=True, text=True, encoding="utf-8", env=env, cwd=trabalho,
    )
    assert r.returncode == 0, r.stderr
    assert validar_saida(trabalho / "saída de teste") == []
    for e in ARQUIVOS:  # config/ e cache/ achados pelo caminho do pacote, não pela pasta atual: mesma saída
        assert (trabalho / "saída de teste" / e.nome).read_bytes() == (RAIZ / "saida" / e.nome).read_bytes(), e.nome
    assert sorted(p.name for p in (trabalho / "contestacoes").iterdir()) == \
        sorted(p.name for p in (RAIZ / "contestacoes").iterdir())


# ---------------------------------------------------------------- acentos no terminal

def test_main_reconfigura_stdout_e_stderr_para_utf8():
    import io

    class Fluxo(io.TextIOWrapper):
        pass

    saida = Fluxo(io.BytesIO(), encoding="cp1252")
    erro = Fluxo(io.BytesIO(), encoding="cp1252")
    antigos = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = saida, erro
    try:
        assert cli.main(["fechar", "--competencia", "2026-09", "--entrada", "pasta inexistente", "--saida", "x"]) == 2
    finally:
        sys.stdout, sys.stderr = antigos
    assert saida.encoding == "utf-8" and erro.encoding == "utf-8"
    erro.flush()
    assert "Diretório de entrada não encontrado".encode("utf-8") in erro.buffer.getvalue()


def test_main_aceita_fluxo_que_nao_reconfigura():
    class SemReconfigurar:
        def write(self, _): ...
        def flush(self): ...

    antigos = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = SemReconfigurar()
    try:
        assert cli.main(["fechar", "--competencia", "2026-09", "--entrada", "pasta inexistente", "--saida", "x"]) == 2
    finally:
        sys.stdout, sys.stderr = antigos


def test_cli_em_subprocesso_com_saida_redirecionada_imprime_utf8(tmp_path):
    env = {**os.environ, "PYTHONPATH": str(RAIZ / "src")}
    env.pop("PYTHONIOENCODING", None)  # o padrão do sistema (cp1252 no Windows) é justamente o que se quer vencer
    env["PYTHONUTF8"] = "0"
    r = subprocess.run([sys.executable, "-m", "tarvo", "fechar", "--competencia", "2026-09", "--entrada", str(ENTRADA),
                        "--saida", str(tmp_path / "saida"), "--sem-contestacao"],
                       capture_output=True, env=env, cwd=RAIZ)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    assert "Competência: 2026-09".encode("utf-8") in r.stdout
