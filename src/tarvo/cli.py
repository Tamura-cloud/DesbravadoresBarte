"""CLI do fechamento: python -m tarvo fechar --competencia AAAA-MM --entrada <dir> --saida <dir> [--sem-ia] [--sem-contestacao]

e o resumo da saída: python -m tarvo resumo --saida <dir>.
"""

from __future__ import annotations

import argparse
import fnmatch
import sys
from pathlib import Path

import yaml

CONFIG_PADRAO = Path(__file__).resolve().parents[2] / "config" / "entradas.yaml"


class ErroEntrada(Exception):
    """Arquivo de entrada ausente ou ambíguo."""


PREFIXO_TEMPORARIO_OFFICE = "~$"  # arquivo de trava que o Excel/Word cria enquanto o documento está aberto


def carregar_padroes(caminho_config: Path) -> dict[str, str]:
    with open(caminho_config, encoding="utf-8") as f:
        return yaml.safe_load(f)["arquivos"]


def carregar_descricoes(caminho_config: Path) -> dict[str, str]:
    """Nome de cada tipo de arquivo nas mensagens (chave descricoes de config/entradas.yaml; opcional)."""
    with open(caminho_config, encoding="utf-8") as f:
        return yaml.safe_load(f).get("descricoes") or {}


def _casa(arquivo: Path, padrao: str) -> bool:
    return fnmatch.fnmatch(arquivo.name.lower(), padrao.lower())


def _temporario_office(arquivo: Path) -> bool:
    return arquivo.name.startswith(PREFIXO_TEMPORARIO_OFFICE)


def _arquivos(entrada: Path) -> list[Path]:
    return sorted(p for p in Path(entrada).iterdir() if p.is_file())


def localizar_arquivos(entrada: Path, padroes: dict[str, str],
                       descricoes: dict[str, str] | None = None) -> dict[str, Path]:
    """Acha um arquivo por tipo usando o padrão de nome. Falha se faltar ou houver mais de um, dizendo o que fazer.

    Nunca escolhe um arquivo sozinho. O arquivo temporário do Office (~$...) não é candidato: aparece em
    arquivos_ignorados, com aviso.
    """
    descricoes = descricoes or {}
    arquivos = [p for p in _arquivos(entrada) if not _temporario_office(p)]
    soltos = [p.name for p in arquivos if not any(_casa(p, padrao) for padrao in padroes.values())]
    encontrados: dict[str, Path] = {}
    problemas: list[str] = []
    for tipo, padrao in padroes.items():
        casados = [p for p in arquivos if _casa(p, padrao)]
        nome = f"{tipo} ({descricoes[tipo]})" if tipo in descricoes else tipo
        if len(casados) == 1:
            encontrados[tipo] = casados[0]
        elif not casados:
            problemas.append(
                f"- {nome}: nenhum arquivo casa com o padrão '{padrao}'.\n"
                f"  Arquivos da pasta que não casam com nenhum padrão: {', '.join(soltos) or '(nenhum)'}.\n"
                f"  O que fazer: ponha na pasta o arquivo de {tipo}, como chegou, com um nome que case com '{padrao}'."
            )
        else:
            problemas.append(
                f"- {nome}: {len(casados)} arquivos casam com o padrão '{padrao}': "
                f"{', '.join(p.name for p in casados)}.\n"
                f"  O que fazer: deixe só um arquivo de {tipo} na pasta; substitua o antigo pela versão nova. "
                "O fechamento não escolhe um deles sozinho."
            )
    if problemas:
        raise ErroEntrada(f"Pasta de entrada: {entrada}\n" + "\n".join(problemas)
                          + "\nOs padrões de nome estão em config/entradas.yaml.")
    return encontrados


def arquivos_ignorados(entrada: Path, padroes: dict[str, str]) -> list[tuple[Path, str]]:
    """Arquivos da pasta que o fechamento não lê, com o motivo. Só aviso: não derrubam a execução."""
    ignorados = []
    for p in _arquivos(entrada):
        if _temporario_office(p):
            ignorados.append((p, "arquivo temporário do Office, existe enquanto o documento está aberto no Excel ou Word"))
        elif not any(_casa(p, padrao) for padrao in padroes.values()):
            ignorados.append((p, "não casa com nenhum padrão de config/entradas.yaml"))
    return ignorados


def cmd_fechar(args: argparse.Namespace) -> int:
    # import tardio: fechamento importa este módulo
    from tarvo.fechamento import ErroFechamento, fechar
    from tarvo.saida import ErroSaida

    entrada = Path(args.entrada)
    if not entrada.is_dir():
        print(f"Diretório de entrada não encontrado: {entrada}", file=sys.stderr)
        return 2
    try:
        resultado = fechar(entrada, Path(args.saida), args.competencia, config=Path(args.config),
                           usar_ia=not args.sem_ia, contestacoes=False if args.sem_contestacao else None)
    except ErroEntrada as e:
        print(f"Erro ao localizar arquivos de entrada. Nada foi gravado: {args.saida} ficou como estava.\n{e}",
              file=sys.stderr)
        return 2
    except (ErroSaida, ErroFechamento) as e:
        print(f"Erro: a saída gerada não passou na validação. Nada foi gravado: {args.saida} e os rascunhos de "
              f"contestação ficaram como estavam.\nProblemas:\n{e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 2

    print(f"Competência: {args.competencia}")
    print(f"Entrada: {entrada}")
    print(f"Saída: {args.saida}")
    print(f"IA nos extratos: {'desligada (--sem-ia)' if args.sem_ia else 'conforme config/ia.yaml'}")
    print(f"Arquivos encontrados ({len(resultado.arquivos_entrada)}):")
    for tipo, caminho in resultado.arquivos_entrada.items():
        print(f"  {tipo}: {caminho.name}")
    if resultado.arquivos_ignorados:
        print(f"Aviso: {len(resultado.arquivos_ignorados)} arquivo(s) da pasta de entrada não foram lidos "
              "(não afetam o fechamento; se algum deles é um arquivo do mês, renomeie para casar com o padrão):")
        for caminho, motivo in resultado.arquivos_ignorados:
            print(f"  {caminho.name}: {motivo}")
    print(f"Itens de saída: {resultado.itens}")
    print(f"Arquivos gravados ({len(resultado.arquivos_saida)}), validados sem problemas:")
    for nome in resultado.arquivos_saida:
        print(f"  {nome}")
    if args.sem_contestacao:
        print("Rascunhos de contestação: desligados (--sem-contestacao)")
    else:
        print(f"Rascunhos de contestação gravados ({len(resultado.arquivos_contestacao)}), a Helena revisa antes de enviar:")
        for nome, caminho in resultado.arquivos_contestacao.items():
            print(f"  {nome} ({caminho.parent})")
    return 0


def cmd_resumo(args: argparse.Namespace) -> int:
    from tarvo.resumo import ErroResumo, resumir

    try:
        texto = resumir(Path(args.saida))
    except ErroResumo as e:
        print(f"Erro ao ler a saída:\n{e}", file=sys.stderr)
        return 2
    print(texto, end="")
    return 0


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tarvo", description="Fechamento mensal da Tarvo Pagamentos")
    sub = parser.add_subparsers(dest="comando", required=True)

    fechar = sub.add_parser("fechar", help="Executa o fechamento de uma competência")
    fechar.add_argument("--competencia", required=True, help="AAAA-MM")
    fechar.add_argument("--entrada", required=True, help="Diretório com os arquivos de entrada")
    fechar.add_argument("--saida", required=True, help="Diretório de saída")
    fechar.add_argument("--config", default=str(CONFIG_PADRAO), help="YAML com os padrões de nome")
    fechar.add_argument("--sem-ia", action="store_true",
                        help="Não usa a IA nos extratos: lançamento sem regra fica A_CLASSIFICAR/HUMANO (P09)")
    fechar.add_argument("--sem-contestacao", action="store_true",
                        help="Não grava os rascunhos de contestação (R29) na pasta irmã da saída")
    fechar.set_defaults(func=cmd_fechar)

    resumo = sub.add_parser("resumo", help="Imprime em Markdown o resumo dos 6 CSVs de uma pasta de saída")
    resumo.add_argument("--saida", required=True, help="Diretório com os 6 CSVs gravados pelo fechar")
    resumo.set_defaults(func=cmd_resumo)
    return parser


def _saida_utf8() -> None:
    """Acentos certos no terminal e em redirecionamento (no Windows o padrão é cp1252 ou o do console)."""
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):  # fluxo trocado (pytest, IDE) que não permite reconfigurar
            pass


def main(argv: list[str] | None = None) -> int:
    _saida_utf8()
    args = construir_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
