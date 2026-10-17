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
from tarvo.cli import ErroEntrada, localizar_pela_config
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


def _pendencias(pasta: Path) -> dict[str, dict]:
    import csv
    with open(pasta / PENDENCIAS.nome, encoding="utf-8", newline="") as f:
        return {l["id_saida"]: l for l in csv.DictReader(f, delimiter=";")}


def test_arquivo_a_mais_no_mesmo_padrao_bloqueia_a_fonte_e_diz_o_que_fazer(copia, tmp_path):
    # R44: o fechamento não escolhe; a fonte fica bloqueada, sem parar o resto
    taxas = _arquivo(copia, "*taxas*.xlsx")
    shutil.copyfile(taxas, copia / f"{taxas.stem}_v2.xlsx")
    resultado = fechar(copia, tmp_path / "saida", "2026-09", modulos=[], contestacoes=False)
    assert not resultado.completo and [b.fonte for b in resultado.bloqueios] == ["taxas"]
    motivo = _pendencias(tmp_path / "saida")["PEN-BLOQUEIO-TAXAS"]["motivo"]
    assert f"{taxas.name}, {taxas.stem}_v2.xlsx" in motivo and "'*taxas*.xlsx'" in motivo
    assert ("se o arquivo novo é uma CORREÇÃO, substitua o antigo - se é um COMPLEMENTO (mais linhas do mesmo mês), "
            "avise quem mantém o fechamento para o tipo taxas aceitar vários arquivos, como a Orbe") in motivo
    assert "substitua o antigo pela versão nova" not in motivo
    assert validar_saida(tmp_path / "saida") == []


def test_localizar_estrito_continua_dizendo_o_que_fazer(copia):
    # a competência anterior (alerta e ajuste da Ponte) ainda usa a pasta inteira: a mensagem traz o mesmo texto
    taxas = _arquivo(copia, "*taxas*.xlsx")
    shutil.copyfile(taxas, copia / f"{taxas.stem}_v2.xlsx")
    with pytest.raises(ErroEntrada) as erro:
        localizar_pela_config(copia)
    assert "se o arquivo novo é uma CORREÇÃO, substitua o antigo; se é um COMPLEMENTO" in str(erro.value)


def test_arquivo_faltando_bloqueia_e_diz_o_padrao_e_o_que_sobrou_na_pasta(copia, tmp_path):
    _arquivo(copia, "*.ofx").unlink()
    (copia / "extrato meridiano.txt").write_text("x", encoding="utf-8")
    resultado = fechar(copia, tmp_path / "saida", "2026-09", modulos=[], contestacoes=False)
    assert [(b.fonte, b.natureza) for b in resultado.bloqueios] == [("meridiano", "AUSENTE")]
    motivo = _pendencias(tmp_path / "saida")["PEN-BLOQUEIO-MERIDIANO"]["motivo"]
    assert "meridiano (extrato do Banco Meridiano, OFX) bloqueada (ausente, R44)" in motivo
    assert "nenhum arquivo casa com o padrão '*.ofx'" in motivo and "extrato meridiano.txt" in motivo
    assert "com um nome que case com '*.ofx'" in motivo


def test_arquivo_estranho_e_temporario_do_office_so_avisam(copia, tmp_path):
    taxas = _arquivo(copia, "*taxas*.xlsx")
    (copia / "anotações da Helena.txt").write_text("x", encoding="utf-8")
    shutil.copyfile(taxas, copia / f"~${taxas.name}")  # Excel aberto: casa com *taxas*.xlsx, mas não é candidato
    resultado = fechar(copia, tmp_path / "saida", "2026-09", modulos=[], contestacoes=False)
    assert resultado.arquivos_entrada["taxas"] == taxas
    ignorados = {p.name: motivo for p, motivo in resultado.arquivos_ignorados}
    assert "nenhum padrão" in ignorados["anotações da Helena.txt"]
    assert "temporário do Office" in ignorados[f"~${taxas.name}"]


def test_cli_entrada_ambigua_sai_com_3_e_grava_o_resto(copia, tmp_path, capsys):
    eml = _arquivo(copia, "*.eml")
    shutil.copyfile(eml, copia / "reenvio da ponte.eml")
    saida = tmp_path / "saida"
    assert cli.main(["fechar", "--competencia", "2026-09", "--entrada", str(copia), "--saida", str(saida),
                     "--sem-contestacao"]) == 3
    texto = capsys.readouterr().out
    assert "FECHAMENTO PARCIAL — fontes bloqueadas: ponte_eml (ambígua); não gerado: remessa" in texto
    assert texto.rstrip().endswith("ver pendências PEN-BLOQUEIO")
    pen = _pendencias(saida)["PEN-BLOQUEIO-PONTE_EML"]
    assert pen["ref_origem"] == f"{eml.name}|reenvio da ponte.eml" and pen["valor_brl"] == "0.00"
    assert validar_saida(saida) == []


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


def _situacoes(pasta: Path, nome: str) -> set[str]:
    import csv
    with open(pasta / nome, encoding="utf-8", newline="") as f:
        return {l.get("situacao") or "" for l in csv.DictReader(f, delimiter=";") if l["id_saida"].startswith(("COM-CHK", "NF-CHK"))}


def test_reenvio_com_linha_diferente_bloqueia_so_o_arquivo_posterior(com_e_sem_o_06, copia, tmp_path, capsys):
    # R44 (i)(2): o 07 traz o TX88446992 do 06 com a taxa diferente; só o 07 fica de fora, o 01 e o 06 entram
    com, _ = com_e_sem_o_06["com"]
    ajustes = _orbe(copia)[-1]
    linhas = ajustes.read_text(encoding="utf-8").splitlines()
    linhas[1] = linhas[1].replace("-1147,05;2,59;-29,70;-1117,35", "-1147,05;2,69;-30,85;-1116,20")
    (copia / "07_orbe_reenvio_ajustes.csv").write_text("\r\n".join(linhas) + "\r\n", encoding="utf-8", newline="")
    saida = tmp_path / "saida"
    assert cli.main(["fechar", "--competencia", "2026-09", "--entrada", str(copia), "--saida", str(saida),
                     "--sem-contestacao"]) == 3
    assert "orbe (só o arquivo 07_orbe_reenvio_ajustes.csv); não gerado: nada" in capsys.readouterr().out
    assert _comissao_total(saida) == _comissao_total(com / "saida")
    pen = _pendencias(saida)["PEN-BLOQUEIO-ORBE-07_orbe_reenvio_ajustes.csv"]
    assert pen["tipo"] == "ARQUIVO_BLOQUEADO" and pen["ref_origem"] == "TX88446992"
    assert (f"id_transacao TX88446992 aparece em {ajustes.name} (linha física 2) e em 07_orbe_reenvio_ajustes.csv "
            "(linha física 2) com valores diferentes em taxa_aplicada_pct, valor_taxa, valor_liquido") in pen["motivo"]
    assert "não escolhe" in pen["motivo"] and "PROVISÓRIOS: checkout" in pen["motivo"]
    rastro = (saida / "rastro.csv").read_text(encoding="utf-8")
    assert (f"PEN-BLOQUEIO-ORBE-07_orbe_reenvio_ajustes.csv;{ajustes.name};TX88446992;0.00\n"
            "PEN-BLOQUEIO-ORBE-07_orbe_reenvio_ajustes.csv;07_orbe_reenvio_ajustes.csv;TX88446992;0.00\n") in rastro
    assert _situacoes(saida, "comissoes_por_lojista.csv") == {"PROVISORIO"}
    assert validar_saida(saida) == []


def test_ajustes_com_cabecalho_diferente_bloqueia_so_o_06(com_e_sem_o_06, copia, tmp_path, capsys):
    # R44 (e): o relatório 01 é lido; o checkout sai sem o 06 e marcado como provisório
    sem, _ = com_e_sem_o_06["sem"]
    ajustes = _orbe(copia)[-1]
    texto = ajustes.read_text(encoding="utf-8").replace("id_transacao;", "id_trans;", 1)
    ajustes.write_text(texto, encoding="utf-8", newline="")
    assert cli.main(["fechar", "--competencia", "2026-09", "--entrada", str(copia), "--saida", str(tmp_path / "s"),
                     "--sem-contestacao"]) == 3
    assert "provisório (coluna situacao = PROVISORIO nos CSVs" in capsys.readouterr().out
    assert _comissao_total(tmp_path / "s") == _comissao_total(sem / "saida")
    motivo = _pendencias(tmp_path / "s")[f"PEN-BLOQUEIO-ORBE-{ajustes.name}"]["motivo"]
    assert f"{ajustes.name}: colunas ausentes no cabeçalho: ['id_transacao']" in motivo
    assert "nenhuma linha dele entrou no fechamento (14 linha(s) de dados)" in motivo
    assert _situacoes(tmp_path / "s", "notas_a_emitir.csv") == {"PROVISORIO"}


def test_ajustes_com_colunas_trocadas_bloqueia_o_06_e_diz_a_coluna(copia, tmp_path):
    # R44 (i)(1): cabeçalho diferente do do primeiro arquivo bloqueia só esse arquivo (a leitura pelo nome leria
    # valor_liquido como valor_taxa se a troca for só no cabeçalho)
    ajustes = _orbe(copia)[-1]
    texto = ajustes.read_text(encoding="utf-8").replace("valor_taxa;valor_liquido", "valor_liquido;valor_taxa", 1)
    ajustes.write_text(texto, encoding="utf-8", newline="")
    fechar(copia, tmp_path / "s", "2026-09", contestacoes=False)
    motivo = _pendencias(tmp_path / "s")[f"PEN-BLOQUEIO-ORBE-{ajustes.name}"]["motivo"]
    assert f"{ajustes.name}: cabeçalho diferente do de {_orbe(copia)[0].name}: a coluna 11 é 'valor_liquido'" in motivo


def test_taxas_duplicada_com_os_ajustes_da_orbe_na_pasta_bloqueia_so_as_taxas(copia, tmp_path):
    taxas = _arquivo(copia, "*taxas*.xlsx")
    shutil.copyfile(taxas, copia / f"{taxas.stem}_v2.xlsx")
    assert len(_orbe(copia)) == 2
    resultado = fechar(copia, tmp_path / "saida", "2026-09", modulos=[], contestacoes=False)
    assert [b.fonte for b in resultado.bloqueios] == ["taxas"]
    assert len(resultado.arquivos_entrada["orbe"]) == 2
