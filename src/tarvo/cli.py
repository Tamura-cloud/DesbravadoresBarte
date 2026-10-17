"""CLI do fechamento: python -m tarvo fechar --competencia AAAA-MM --entrada <dir> --saida <dir>."""

from __future__ import annotations

import argparse
import fnmatch
import sys
from pathlib import Path

import yaml

CONFIG_PADRAO = Path(__file__).resolve().parents[2] / "config" / "entradas.yaml"


class ErroEntrada(Exception):
    """Arquivo de entrada ausente ou ambíguo."""


def carregar_padroes(caminho_config: Path) -> dict[str, str]:
    with open(caminho_config, encoding="utf-8") as f:
        return yaml.safe_load(f)["arquivos"]


def localizar_arquivos(entrada: Path, padroes: dict[str, str]) -> dict[str, Path]:
    """Acha um arquivo por tipo usando o padrão de nome. Falha se faltar ou houver mais de um."""
    arquivos = sorted(p for p in entrada.iterdir() if p.is_file())
    encontrados: dict[str, Path] = {}
    problemas: list[str] = []
    for tipo, padrao in padroes.items():
        casados = [p for p in arquivos if fnmatch.fnmatch(p.name.lower(), padrao.lower())]
        if len(casados) == 1:
            encontrados[tipo] = casados[0]
        elif not casados:
            problemas.append(f"{tipo}: nenhum arquivo casa com '{padrao}'")
        else:
            nomes = ", ".join(p.name for p in casados)
            problemas.append(f"{tipo}: mais de um arquivo casa com '{padrao}': {nomes}")
    if problemas:
        raise ErroEntrada("\n".join(problemas))
    return encontrados


def cmd_fechar(args: argparse.Namespace) -> int:
    entrada = Path(args.entrada)
    if not entrada.is_dir():
        print(f"Diretório de entrada não encontrado: {entrada}", file=sys.stderr)
        return 2
    padroes = carregar_padroes(Path(args.config))
    try:
        encontrados = localizar_arquivos(entrada, padroes)
    except ErroEntrada as e:
        print(f"Erro ao localizar arquivos de entrada:\n{e}", file=sys.stderr)
        return 2

    print(f"Competência: {args.competencia}")
    print(f"Entrada: {entrada}")
    print(f"Saída: {args.saida}")
    print(f"Arquivos encontrados ({len(encontrados)}):")
    for tipo, caminho in encontrados.items():
        print(f"  {tipo}: {caminho.name}")
    return 0


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tarvo", description="Fechamento mensal da Tarvo Pagamentos")
    sub = parser.add_subparsers(dest="comando", required=True)

    fechar = sub.add_parser("fechar", help="Executa o fechamento de uma competência")
    fechar.add_argument("--competencia", required=True, help="AAAA-MM")
    fechar.add_argument("--entrada", required=True, help="Diretório com os arquivos de entrada")
    fechar.add_argument("--saida", required=True, help="Diretório de saída")
    fechar.add_argument("--config", default=str(CONFIG_PADRAO), help="YAML com os padrões de nome")
    fechar.set_defaults(func=cmd_fechar)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
