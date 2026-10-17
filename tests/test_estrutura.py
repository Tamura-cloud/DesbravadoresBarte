import os
import subprocess
import sys
from pathlib import Path

from tarvo.cli import CONFIG_PADRAO, carregar_padroes, localizar_arquivos

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "dados" / "2026-09"


def test_localiza_os_6_arquivos_por_padrao():
    padroes = carregar_padroes(CONFIG_PADRAO)
    encontrados = localizar_arquivos(ENTRADA, padroes)

    assert set(encontrados) == {"orbe", "taxas", "ponte_eml", "plano_de_contas", "aurora", "meridiano"}
    assert len(set(encontrados.values())) == 6
    assert all(p.is_file() for p in encontrados.values())


def test_cli_fechar_lista_os_6_arquivos(tmp_path):
    env = {**os.environ, "PYTHONPATH": str(RAIZ / "src"), "PYTHONIOENCODING": "utf-8"}
    resultado = subprocess.run(
        [sys.executable, "-m", "tarvo", "fechar",
         "--competencia", "2026-09", "--entrada", str(ENTRADA), "--saida", str(tmp_path)],
        capture_output=True, text=True, encoding="utf-8", env=env, cwd=RAIZ,
    )

    assert resultado.returncode == 0, resultado.stderr
    assert "Arquivos encontrados (6)" in resultado.stdout
