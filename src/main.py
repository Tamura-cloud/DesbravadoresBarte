"""Orquestrador do fechamento: lê as fontes, roda os 3 módulos e grava saida/.

Uso: python -m src.main --entrada dados --saida saida --competencia 2026-09

Os módulos não se importam entre si: cada um recebe os mesmos Dados e
devolve um ResultadoModulo. Módulo ainda não implementado é pulado com aviso,
para que cada pessoa rode o pipeline sem depender das outras.
"""
import argparse
from pathlib import Path

from .bancos import motor as bancos
from .checkout import motor as checkout
from .core import config, saida
from .core.modelos import ResultadoModulo
from .leitores import carregar_tudo
from .remessa import motor as remessa

MODULOS = [("checkout", checkout), ("remessa", remessa), ("bancos", bancos)]


def fechar(entrada: Path, pasta_saida: Path, competencia: str) -> dict[str, int]:
    dados = carregar_tudo(entrada)
    total = ResultadoModulo()
    for nome, modulo in MODULOS:
        try:
            total.juntar(modulo.executar(dados, config.carregar(nome), competencia))
            print(f"[ok] {nome}")
        except NotImplementedError as e:
            print(f"[pulado] {e}")
    return saida.escrever(total, pasta_saida)


def main() -> None:
    p = argparse.ArgumentParser(description="Fechamento mensal Tarvo")
    p.add_argument("--entrada", default="dados")
    p.add_argument("--saida", default="saida")
    p.add_argument("--competencia", default="2026-09")
    a = p.parse_args()
    contagens = fechar(Path(a.entrada), Path(a.saida), a.competencia)
    for arquivo, n in contagens.items():
        print(f"  {arquivo}: {n} linhas")


if __name__ == "__main__":
    main()
