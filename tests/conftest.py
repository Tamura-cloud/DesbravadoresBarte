"""Guarda da sessão de testes: nenhum teste grava em dados/, saida/, contestacoes/ ou cache/ do repositório.

Os testes (inclusive o outubro simulado) usam só pastas temporárias. Se algum gravar nessas pastas, a sessão
termina com erro apontando o arquivo.
"""

import hashlib
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
PROTEGIDAS = ("dados", "saida", "contestacoes", "cache")


def _retrato() -> dict[str, str]:
    return {str(p.relative_to(RAIZ)): hashlib.sha256(p.read_bytes()).hexdigest()
            for pasta in PROTEGIDAS if (RAIZ / pasta).is_dir()
            for p in sorted((RAIZ / pasta).rglob("*")) if p.is_file()}


@pytest.fixture(scope="session", autouse=True)
def pastas_do_repositorio_intactas():
    antes = _retrato()
    yield
    depois = _retrato()
    mudados = sorted(k for k in antes.keys() | depois.keys() if antes.get(k) != depois.get(k))
    assert not mudados, f"teste gravou no repositório (use tmp_path): {mudados}"
