"""CLI do fechamento: python -m tarvo fechar --competencia AAAA-MM --entrada <dir> --saida <dir> [--sem-ia] [--sem-contestacao]

e o resumo da saída: python -m tarvo resumo --saida <dir>.

Códigos de saída do fechar (R44): 0 = fechamento completo; 3 = fechamento parcial (alguma fonte bloqueada, ver as
pendências PEN-BLOQUEIO) ou item fora por erro de dado (PEN-REGRA); 1 = a saída gerada não passou na validação;
2 = pasta de entrada inexistente, erro de configuração (config/*.yaml) ou erro interno de programa. Com 1 e 2 nada é
gravado.
"""

from __future__ import annotations

import argparse
import fnmatch
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

CONFIG_PADRAO = Path(__file__).resolve().parents[2] / "config" / "entradas.yaml"


class ErroEntrada(Exception):
    """Arquivo de entrada ausente ou ambíguo."""


AUSENTE, AMBIGUA = "AUSENTE", "AMBIGUA"
COMPLETO, PARCIAL = 0, 3  # códigos de saída do fechar (R44)


@dataclass(frozen=True)
class ProblemaArquivo:
    """Tipo de arquivo sem arquivo na pasta (AUSENTE) ou com vários num tipo de arquivo único (AMBIGUA)."""

    tipo: str
    nome: str                       # tipo com a descrição, como aparece nas mensagens
    padrao: str
    natureza: str                   # AUSENTE ou AMBIGUA
    candidatos: tuple[str, ...]     # na AMBIGUA, os arquivos que casam; na AUSENTE, os que não casam com nada
    mensagem: str


PREFIXO_TEMPORARIO_OFFICE = "~$"  # arquivo de trava que o Excel/Word cria enquanto o documento está aberto


def _ler_config(caminho_config: Path) -> dict:
    with open(caminho_config, encoding="utf-8") as f:
        return yaml.safe_load(f)


def carregar_padroes(caminho_config: Path) -> dict[str, str]:
    """Padrão de nome de cada tipo. O tipo vem como texto ("*.ofx") ou como {padrao: ..., multiplos: true}."""
    return {tipo: (v["padrao"] if isinstance(v, dict) else v) for tipo, v in _ler_config(caminho_config)["arquivos"].items()}


def carregar_multiplos(caminho_config: Path) -> frozenset[str]:
    """Tipos que aceitam vários arquivos no mesmo formato (multiplos: true): todos são lidos, em ordem de nome."""
    return frozenset(tipo for tipo, v in _ler_config(caminho_config)["arquivos"].items()
                     if isinstance(v, dict) and v.get("multiplos") is True)


def carregar_descricoes(caminho_config: Path) -> dict[str, str]:
    """Nome de cada tipo de arquivo nas mensagens (chave descricoes de config/entradas.yaml; opcional)."""
    return _ler_config(caminho_config).get("descricoes") or {}


def _casa(arquivo: Path, padrao: str) -> bool:
    return fnmatch.fnmatch(arquivo.name.lower(), padrao.lower())


def _temporario_office(arquivo: Path) -> bool:
    return arquivo.name.startswith(PREFIXO_TEMPORARIO_OFFICE)


def _arquivos(entrada: Path) -> list[Path]:
    return sorted(p for p in Path(entrada).iterdir() if p.is_file())


def o_que_fazer_ambigua(tipo: str) -> str:
    """Próximo passo quando um tipo de arquivo único tem vários arquivos na pasta (R44)."""
    return (f"se o arquivo novo é uma CORREÇÃO, substitua o antigo; se é um COMPLEMENTO (mais linhas do mesmo mês), "
            f"avise quem mantém o fechamento para o tipo {tipo} aceitar vários arquivos, como a Orbe")


def localizar_tolerante(entrada: Path, padroes: dict[str, str], descricoes: dict[str, str] | None = None,
                        multiplos: frozenset[str] = frozenset()
                        ) -> tuple[dict[str, Path | tuple[Path, ...]], dict[str, ProblemaArquivo]]:
    """Acha os arquivos de cada tipo pelo padrão de nome, sem parar: (encontrados, problemas por tipo).

    Tipo em multiplos (por exemplo, relatório e ajustes da Orbe) devolve todos os arquivos que casam, em ordem de
    nome, numa tupla; precisa de pelo menos um. Nos outros tipos, nenhum arquivo é AUSENTE e mais de um é AMBIGUA:
    o fechamento nunca escolhe um arquivo sozinho. O arquivo temporário do Office (~$...) não é candidato.
    """
    descricoes = descricoes or {}
    arquivos = [p for p in _arquivos(entrada) if not _temporario_office(p)]
    soltos = tuple(p.name for p in arquivos if not any(_casa(p, padrao) for padrao in padroes.values()))
    encontrados: dict[str, Path | tuple[Path, ...]] = {}
    problemas: dict[str, ProblemaArquivo] = {}
    for tipo, padrao in padroes.items():
        casados = [p for p in arquivos if _casa(p, padrao)]
        nome = f"{tipo} ({descricoes[tipo]})" if tipo in descricoes else tipo
        if tipo in multiplos and casados:
            encontrados[tipo] = tuple(casados)
        elif len(casados) == 1:
            encontrados[tipo] = casados[0]
        elif not casados:
            problemas[tipo] = ProblemaArquivo(tipo, nome, padrao, AUSENTE, soltos, (
                f"- {nome}: nenhum arquivo casa com o padrão '{padrao}'.\n"
                f"  Arquivos da pasta que não casam com nenhum padrão: {', '.join(soltos) or '(nenhum)'}.\n"
                f"  O que fazer: ponha na pasta o arquivo de {tipo}, como chegou, com um nome que case com '{padrao}'."))
        else:
            candidatos = tuple(p.name for p in casados)
            problemas[tipo] = ProblemaArquivo(tipo, nome, padrao, AMBIGUA, candidatos, (
                f"- {nome}: {len(casados)} arquivos casam com o padrão '{padrao}': {', '.join(candidatos)}.\n"
                f"  O que fazer: {o_que_fazer_ambigua(tipo)}. O fechamento não escolhe um deles sozinho."))
    return encontrados, problemas


def localizar_arquivos(entrada: Path, padroes: dict[str, str], descricoes: dict[str, str] | None = None,
                       multiplos: frozenset[str] = frozenset()) -> dict[str, Path | tuple[Path, ...]]:
    """Como localizar_tolerante, mas falha (ErroEntrada) se algum tipo faltar ou for ambíguo, dizendo o que fazer.

    Usado onde só serve a pasta inteira (a competência anterior, nas consultas do alerta e do ajuste da Ponte).
    """
    encontrados, problemas = localizar_tolerante(entrada, padroes, descricoes, multiplos)
    if problemas:
        raise ErroEntrada(f"Pasta de entrada: {entrada}\n" + "\n".join(p.mensagem for p in problemas.values())
                          + "\nOs padrões de nome estão em config/entradas.yaml.")
    return encontrados


def localizar_pela_config(entrada, config: Path = CONFIG_PADRAO) -> dict[str, Path | tuple[Path, ...]]:
    """localizar_arquivos com padrões, descrições e tipos múltiplos de config/entradas.yaml."""
    config = Path(config)
    return localizar_arquivos(Path(entrada), carregar_padroes(config), carregar_descricoes(config),
                              carregar_multiplos(config))


def localizar_tolerante_pela_config(entrada, config: Path = CONFIG_PADRAO):
    """localizar_tolerante com padrões, descrições e tipos múltiplos de config/entradas.yaml."""
    config = Path(config)
    return localizar_tolerante(Path(entrada), carregar_padroes(config), carregar_descricoes(config),
                               carregar_multiplos(config))


def nomes(arquivo: Path | tuple[Path, ...]) -> str:
    """Nome do arquivo de um tipo, ou os nomes separados por vírgula num tipo com vários arquivos."""
    return ", ".join(p.name for p in arquivo) if isinstance(arquivo, tuple) else arquivo.name


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
    from tarvo.fechamento import ErroArquivoTravado, ErroFechamento, fechar
    from tarvo.saida import ErroSaida

    entrada = Path(args.entrada)
    if not entrada.is_dir():
        print(f"Diretório de entrada não encontrado: {entrada}", file=sys.stderr)
        return 2
    try:
        resultado = fechar(entrada, Path(args.saida), args.competencia, config=Path(args.config),
                           usar_ia=not args.sem_ia, contestacoes=False if args.sem_contestacao else None)
    except ErroArquivoTravado as e:  # saida/, contestacoes/ e auditoria/ ficaram como estavam
        print(e, file=sys.stderr)
        return 1
    except (ErroSaida, ErroFechamento) as e:
        print(f"Erro: a saída gerada não passou na validação. Nada foi gravado: {args.saida} e os rascunhos de "
              f"contestação ficaram como estavam.\nProblemas:\n{e}", file=sys.stderr)
        return 1
    except yaml.YAMLError as e:  # config/*.yaml com sintaxe inválida: diz o arquivo e a linha, sem traceback
        marca = getattr(e, "problem_mark", None) or getattr(e, "context_mark", None)
        onde = f"{marca.name}, linha {marca.line + 1}" if marca is not None else "arquivo de config/"
        problema = getattr(e, "problem", None) or "sintaxe inválida"
        print(f"Erro de configuração em {onde}: {problema}. Corrija o arquivo e rode de novo. Nada foi gravado: "
              f"{args.saida} ficou como estava.", file=sys.stderr)
        return 2
    except ValueError as e:  # dado de entrada não chega aqui (R44): é configuração ou erro de programa
        print(f"Erro de configuração ou interno. Nada foi gravado: {args.saida} ficou como estava.\n{e}",
              file=sys.stderr)
        return 2

    print(f"Competência: {args.competencia}")
    print(f"Entrada: {entrada}")
    print(f"Saída: {args.saida}")
    print(f"IA nos extratos: {'desligada (--sem-ia)' if args.sem_ia else 'conforme config/ia.yaml'}")
    print(f"Arquivos encontrados ({len(resultado.arquivos_entrada)}):")
    for tipo, caminho in resultado.arquivos_entrada.items():
        print(f"  {tipo}: {nomes(caminho)}")
    if resultado.avisos:
        print(f"Aviso: {len(resultado.avisos)} diferença(s) de layout; a leitura seguiu pelo nome da coluna "
              "(pendências PEN-AVISO-LAYOUT):")
        for aviso in resultado.avisos:
            print(f"  {aviso}")
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
    print()
    print(resultado.quadro())
    return COMPLETO if resultado.completo else PARCIAL


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
