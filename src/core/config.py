"""Leitura das regras que mudam de mês para mês (config/*.toml)."""
import tomllib
from pathlib import Path

PASTA_CONFIG = Path(__file__).resolve().parents[2] / "config"


def carregar(nome: str, pasta: Path = PASTA_CONFIG) -> dict:
    """carregar('checkout') -> conteúdo de config/checkout.toml."""
    with open(pasta / f"{nome}.toml", "rb") as f:
        return tomllib.load(f)
