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



# ---------------------------------------------------------------- vários arquivos da Orbe (O05)

def _comissao_total(pasta: Path) -> Decimal:
    import csv
    with open(pasta / "comissoes_por_lojista.csv", encoding="utf-8", newline="") as f:
        return sum((Decimal(l["comissao_brl"]) for l in csv.DictReader(f, delimiter=";")), Decimal("0.00"))


def _orbe(pasta: Path) -> list[Path]:
    return sorted(pasta.glob("*orbe*.csv"))


@pytest.fixture(scope="module")
def com_e_sem_o_06(tmp_path_factory):
    """O mesmo setembro fechado com o relatório e os ajustes tardios (06) e só com o relatório."""
    resultado = {}
    for caso in ("com", "sem"):
        raiz = tmp_path_factory.mktemp(caso)
        shutil.copytree(ENTRADA, raiz / "entrada")
        if caso == "sem":
            _orbe(raiz / "entrada")[-1].unlink()
        resultado[caso] = (raiz, fechar(raiz / "entrada", raiz / "saida", "2026-09", contestacoes=False))
    return resultado


def test_fechar_le_os_arquivos_da_orbe_e_o_06_entra_na_comissao(com_e_sem_o_06):
    (com, r_com), (sem, r_sem) = com_e_sem_o_06["com"], com_e_sem_o_06["sem"]
    assert [p.name for p in r_com.arquivos_entrada["orbe"]] == [p.name for p in _orbe(com / "entrada")]
    assert len(r_sem.arquivos_entrada["orbe"]) == 1
    assert validar_saida(com / "saida") == []
    # as 14 linhas do 06: 10 estornos e 3 reversões tiram, 1 venda do Kiwi soma (R35, R05, R07)
    assert _comissao_total(com / "saida") - _comissao_total(sem / "saida") == Decimal("-3304.39")
    rastro = (com / "saida" / "rastro.csv").read_text(encoding="utf-8")
    assert f"COM-CHK-07752116000126;{_orbe(com / 'entrada')[-1].name};TX88447225;174.81" in rastro


def test_reenvio_igual_dos_ajustes_conta_uma_vez_e_abre_pendencia(com_e_sem_o_06, tmp_path):
    com, _ = com_e_sem_o_06["com"]
    shutil.copytree(com / "entrada", tmp_path / "entrada")
    ajustes = _orbe(tmp_path / "entrada")[-1]
    shutil.copyfile(ajustes, tmp_path / "entrada" / "07_orbe_reenvio_ajustes.csv")
    fechar(tmp_path / "entrada", tmp_path / "saida", "2026-09", contestacoes=False)
    assert _comissao_total(tmp_path / "saida") == _comissao_total(com / "saida")
    pendencias = (tmp_path / "saida" / "pendencias.csv").read_text(encoding="utf-8")
    assert pendencias.count("PEN-REPET-CHK-") == 14 and pendencias.count(";TRANSACAO_REPETIDA;") == 14


def test_reenvio_com_linha_diferente_para_e_nao_grava(copia, tmp_path, capsys):
    ajustes = _orbe(copia)[-1]
    linhas = ajustes.read_text(encoding="utf-8").splitlines()
    linhas[1] = linhas[1].replace("-1147,05;2,59;-29,70;-1117,35", "-1147,05;2,69;-30,85;-1116,20")
    (copia / "07_orbe_reenvio_ajustes.csv").write_text("\r\n".join(linhas) + "\r\n", encoding="utf-8", newline="")
    saida = tmp_path / "saida"
    assert cli.main(["fechar", "--competencia", "2026-09", "--entrada", str(copia), "--saida", str(saida),
                     "--sem-contestacao"]) == 2
    erro = capsys.readouterr().err
    assert "Nada foi gravado" in erro and "TX88446992" in erro
    assert "taxa_aplicada_pct, valor_taxa, valor_liquido" in erro and "não escolhe" in erro
    assert not saida.exists()


def test_ajustes_com_cabecalho_diferente_para_e_diz_o_arquivo_e_a_coluna(copia, tmp_path, capsys):
    ajustes = _orbe(copia)[-1]
    texto = ajustes.read_text(encoding="utf-8").replace("id_transacao;", "id_trans;", 1)
    ajustes.write_text(texto, encoding="utf-8", newline="")
    assert cli.main(["fechar", "--competencia", "2026-09", "--entrada", str(copia), "--saida", str(tmp_path / "s"),
                     "--sem-contestacao"]) == 2
    erro = capsys.readouterr().err
    assert f"{ajustes.name}: colunas ausentes no cabeçalho: ['id_transacao']" in erro


def test_ajustes_com_colunas_trocadas_para_e_diz_a_coluna(copia, tmp_path, capsys):
    ajustes = _orbe(copia)[-1]
    texto = ajustes.read_text(encoding="utf-8").replace("valor_taxa;valor_liquido", "valor_liquido;valor_taxa", 1)
    ajustes.write_text(texto, encoding="utf-8", newline="")
    assert cli.main(["fechar", "--competencia", "2026-09", "--entrada", str(copia), "--saida", str(tmp_path / "s"),
                     "--sem-contestacao"]) == 2
    erro = capsys.readouterr().err
    assert f"{ajustes.name}: cabeçalho diferente do de {_orbe(copia)[0].name}: a coluna 11 é 'valor_liquido'" in erro


def test_taxas_continua_exigindo_um_arquivo_so_com_os_ajustes_da_orbe_na_pasta(copia, tmp_path):
    taxas = _arquivo(copia, "*taxas*.xlsx")
    shutil.copyfile(taxas, copia / f"{taxas.stem}_v2.xlsx")
    assert len(_orbe(copia)) == 2
    with pytest.raises(ErroEntrada, match="deixe só um arquivo de taxas na pasta"):
        fechar(copia, tmp_path / "saida", "2026-09", modulos=[], contestacoes=False)
