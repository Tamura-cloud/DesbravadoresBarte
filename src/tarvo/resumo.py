"""Resumo em Markdown dos 6 CSVs de uma pasta de saída: python -m tarvo resumo --saida <dir>.

Só lê a saída já gravada; não recalcula regra de negócio e não tem valor de competência nenhuma.
Cada número do resumo é soma ou contagem de linhas dos CSVs, e a última seção confere o rastro.csv.
"""

from __future__ import annotations

import csv
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from tarvo.saida import (
    ARQUIVOS,
    ARQUIVOS_ITENS,
    COMISSOES,
    DIVERGENCIAS,
    ENCODING,
    LANCAMENTOS,
    METODOS,
    NOTAS,
    PENDENCIAS,
    RASTRO,
    SEPARADOR,
    SEPARADOR_REFS,
    validar_saida,
)

ZERO = Decimal("0.00")
MAIORES = 5
RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
SEM_COMMIT = "commit indisponível"
TIPOS_BLOQUEIO = ("FONTE_BLOQUEADA", "ARQUIVO_BLOQUEADO", "ITEM_BLOQUEADO")  # PEN-BLOQUEIO e PEN-REGRA (R44)
COLUNA_SITUACAO = "situacao"  # coluna extra dos itens provisórios (R44)


class ErroResumo(Exception):
    """Pasta de saída sem os 6 CSVs."""


# ---------------------------------------------------------------- leitura

def ler_saida(pasta) -> dict[str, list[dict[str, str]]]:
    """Os 6 CSVs da pasta, cada um como lista de linhas (coluna -> texto)."""
    pasta = Path(pasta)
    faltando = [e.nome for e in ARQUIVOS if not (pasta / e.nome).is_file()]
    if faltando:
        raise ErroResumo(f"faltam em {pasta}: {', '.join(faltando)}")
    lidos = {}
    for espec in ARQUIVOS:
        with open(pasta / espec.nome, encoding=ENCODING, newline="") as f:
            lidos[espec.nome] = list(csv.DictReader(f, delimiter=SEPARADOR))
    return lidos


def _valor(linha: dict[str, str], coluna: str) -> Decimal:
    return Decimal(linha[coluna])


# ---------------------------------------------------------------- conferência do rastro

@dataclass(frozen=True)
class ConferenciaRastro:
    itens: int                                         # linhas nos 5 arquivos de resultado
    conferidos: int                                    # itens cuja soma do rastro bate com o valor reportado
    divergentes: list[tuple[str, Decimal, Decimal]]    # (id_saida, reportado, soma do rastro)
    sem_rastro: list[str]                              # itens sem nenhuma linha no rastro
    orfaos: list[str]                                  # id_saida do rastro que não existe nos 5 arquivos

    @property
    def ok(self) -> bool:
        return not self.divergentes and not self.sem_rastro and not self.orfaos


def conferir_rastro(lidos: dict[str, list[dict[str, str]]]) -> ConferenciaRastro:
    """Soma o valor do rastro.csv por id_saida e compara com o valor reportado em cada arquivo."""
    soma: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for l in lidos[RASTRO.nome]:
        soma[l["id_saida"]] += _valor(l, RASTRO.coluna_valor)
    reportados = {l["id_saida"]: _valor(l, e.coluna_valor) for e in ARQUIVOS_ITENS for l in lidos[e.nome]}
    divergentes = [(i, v, soma[i]) for i, v in reportados.items() if i in soma and soma[i] != v]
    sem_rastro = [i for i in reportados if i not in soma]
    orfaos = sorted(i for i in soma if i not in reportados)
    return ConferenciaRastro(len(reportados), len(reportados) - len(divergentes) - len(sem_rastro),
                             divergentes, sem_rastro, orfaos)


# ---------------------------------------------------------------- formatação

def brl(v: Decimal) -> str:
    """Decimal para o formato brasileiro com 2 casas: -1234.5 vira "-1.234,50"."""
    texto = format(abs(v).quantize(ZERO), ",f").replace(",", "_").replace(".", ",").replace("_", ".")
    return f"-{texto}" if v < 0 else texto


def _tabela(cabecalho: list[str], linhas: list[list], numericas: set[int] = frozenset()) -> str:
    if not linhas:
        return "_(nenhuma linha)_"
    alinhamento = ["---:" if i in numericas else "---" for i in range(len(cabecalho))]
    texto = [f"| {' | '.join(cabecalho)} |", f"| {' | '.join(alinhamento)} |"]
    texto += [f"| {' | '.join(str(c).replace('|', '/') for c in l)} |" for l in linhas]
    return "\n".join(texto)


def _agrupar(linhas: list[dict[str, str]], chave, coluna_valor: str) -> dict:
    """chave(linha) -> [quantidade, soma], na ordem em que a chave aparece."""
    grupos: dict = {}
    for l in linhas:
        g = grupos.setdefault(chave(l), [0, ZERO])
        g[0] += 1
        g[1] += _valor(l, coluna_valor)
    return grupos


def _total(linhas: list[dict[str, str]], coluna_valor: str) -> tuple[int, Decimal]:
    return len(linhas), sum((_valor(l, coluna_valor) for l in linhas), ZERO)


def _nomes_por_cnpj(lidos) -> dict[tuple[str, str], str]:
    """(cnpj, linha_negocio) -> nome do lojista, pelo comissoes_por_lojista.csv (nome é só evidência)."""
    return {(l["cnpj"], l["linha_negocio"]): l["lojista"] for l in lidos[COMISSOES.nome]}


# ---------------------------------------------------------------- seções

def _git(*args: str, raiz: Path) -> str | None:
    try:
        r = subprocess.run(["git", *args], cwd=raiz, capture_output=True, text=True, encoding="utf-8", timeout=10)
    except (OSError, subprocess.SubprocessError):  # sem git instalado ou sem resposta
        return None
    return r.stdout.strip() or None if r.returncode == 0 else None


def versao_do_codigo(raiz: Path = RAIZ_REPOSITORIO) -> str:
    """Commit atual (git rev-parse --short HEAD) e branch do código que gerou o resumo; sem git, "commit indisponível"."""
    commit = _git("rev-parse", "--short", "HEAD", raiz=raiz)
    if commit is None:
        return SEM_COMMIT
    branch = _git("rev-parse", "--abbrev-ref", "HEAD", raiz=raiz)
    return f"{commit} (branch {branch})" if branch else commit


def status(lidos) -> tuple[str, list[str], int]:
    """("COMPLETO" ou "PARCIAL", id das pendências de bloqueio, itens provisórios), pelos próprios CSVs (R44)."""
    bloqueios = [l["id_saida"] for l in lidos[PENDENCIAS.nome] if l["tipo"] in TIPOS_BLOQUEIO]
    provisorios = sum(1 for e in ARQUIVOS_ITENS for l in lidos[e.nome] if l.get(COLUNA_SITUACAO))
    return ("PARCIAL" if bloqueios else "COMPLETO"), bloqueios, provisorios


def _secao_status(lidos) -> list[str]:
    situacao, bloqueios, provisorios = status(lidos)
    if situacao == "COMPLETO":
        return ["**Status do fechamento: COMPLETO** — nenhuma fonte bloqueada."]
    fontes = [b for b in bloqueios if b.startswith("PEN-BLOQUEIO")]
    itens = [b for b in bloqueios if not b.startswith("PEN-BLOQUEIO")]
    texto = "**Status do fechamento: PARCIAL** —"
    if fontes:
        texto += f" fontes bloqueadas: {', '.join(fontes)}."
    if itens:
        texto += f" Itens fora por erro de dado: {', '.join(itens)}."
    if provisorios:
        texto += f" Itens provisórios (coluna situacao): {provisorios}."
    return [texto + " O que não foi gerado e o próximo passo estão no motivo de cada pendência."]


def _secao_comissoes(lidos) -> list[str]:
    linhas = lidos[COMISSOES.nome]
    v = COMISSOES.coluna_valor
    partes = ["## Comissões por linha de negócio", ""]
    por_linha = _agrupar(linhas, lambda l: l["linha_negocio"], v)
    qtd, soma = _total(linhas, v)
    partes.append(_tabela(["linha_negocio", "lojistas", "comissão (R$)"],
                          [[k, q, brl(s)] for k, (q, s) in sorted(por_linha.items())] + [["**total**", qtd, brl(soma)]],
                          {1, 2}))
    for linha_negocio in sorted(por_linha):
        do_negocio = sorted((l for l in linhas if l["linha_negocio"] == linha_negocio),
                            key=lambda l: (-_valor(l, v), l["cnpj"]))
        partes += ["", f"### Comissões {linha_negocio} por lojista", ""]
        partes.append(_tabela(["CNPJ", "lojista", "comissão (R$)"],
                              [[l["cnpj"], l["lojista"], brl(_valor(l, v))] for l in do_negocio], {2}))
    return partes


def _secao_notas(lidos) -> list[str]:
    linhas = lidos[NOTAS.nome]
    v = NOTAS.coluna_valor
    qtd, soma = _total(linhas, v)
    ordenadas = sorted(linhas, key=lambda l: (l["linha_negocio"], -_valor(l, v), l["tomador_cnpj"]))
    partes = ["## Notas a emitir", ""]
    partes.append(_tabela(["tomador_cnpj", "tomador", "linha_negocio", "valor (R$)"],
                          [[l["tomador_cnpj"], l["tomador"], l["linha_negocio"], brl(_valor(l, v))] for l in ordenadas]
                          + [["**total**", f"{qtd} notas", "", f"**{brl(soma)}**"]], {3}))
    por_linha = _agrupar(linhas, lambda l: l["linha_negocio"], v)
    partes += ["", _tabela(["linha_negocio", "notas", "valor (R$)"],
                           [[k, q, brl(s)] for k, (q, s) in sorted(por_linha.items())], {1, 2})]
    return partes


def _secao_divergencias(lidos) -> list[str]:
    linhas = lidos[DIVERGENCIAS.nome]
    v = DIVERGENCIAS.coluna_valor
    nomes = _nomes_por_cnpj(lidos)
    qtd, soma = _total(linhas, v)
    partes = ["## Divergências de taxa", ""]
    por_linha = _agrupar(linhas, lambda l: l["linha_negocio"], v)
    partes.append(_tabela(["linha_negocio", "linhas", "soma (R$)"],
                          [[k, q, brl(s)] for k, (q, s) in sorted(por_linha.items())] + [["**total**", qtd, brl(soma)]],
                          {1, 2}))

    por_lojista = _agrupar(linhas, lambda l: (l["linha_negocio"], l["cnpj"]), v)
    partes += ["", "### Por lojista e linha de negócio", ""]
    partes.append(_tabela(
        ["linha_negocio", "CNPJ", "lojista", "linhas", "soma (R$)"],
        [[ln, c, nomes.get((c, ln), "—"), q, brl(s)] for (ln, c), (q, s) in sorted(por_lojista.items())],
        {3, 4}))

    def detalhe(l):
        return [l["id_saida"], l["linha_negocio"], l["cnpj"], l["ref_origem"],
                l["taxa_contratada_pct"], l["taxa_aplicada_pct"], brl(_valor(l, v))]

    cab = ["id_saida", "linha_negocio", "CNPJ", "ref_origem", "contratada (%)", "aplicada (%)", "diferença (R$)"]
    maiores = sorted(linhas, key=lambda l: (-_valor(l, v), l["id_saida"]))[:MAIORES]
    partes += ["", f"### As {MAIORES} maiores", "", _tabela(cab, [detalhe(l) for l in maiores], {4, 5, 6})]
    negativas = sorted((l for l in linhas if _valor(l, v) < 0), key=lambda l: (_valor(l, v), l["id_saida"]))
    q_neg, s_neg = _total(negativas, v)
    partes += ["", f"### Negativas ({q_neg} linhas, soma R$ {brl(s_neg)})", "",
               _tabela(cab, [detalhe(l) for l in negativas], {4, 5, 6})]
    return partes


def _secao_lancamentos(lidos) -> list[str]:
    linhas = lidos[LANCAMENTOS.nome]
    v = LANCAMENTOS.coluna_valor
    qtd, soma = _total(linhas, v)
    partes = ["## Lançamentos classificados", ""]
    por_banco = _agrupar(linhas, lambda l: l["banco"], v)
    partes.append(_tabela(["banco", "lançamentos", "soma (R$)"],
                          [[k, q, brl(s)] for k, (q, s) in sorted(por_banco.items())] + [["**total**", qtd, brl(soma)]],
                          {1, 2}))
    por_conta = _agrupar(linhas, lambda l: (l["banco"], l["conta_codigo"]), v)
    partes += ["", "### Por banco e conta", ""]
    partes.append(_tabela(["banco", "conta_codigo", "lançamentos", "soma (R$)"],
                          [[b, c, q, brl(s)] for (b, c), (q, s) in sorted(por_conta.items())], {2, 3}))
    por_metodo = _agrupar(linhas, lambda l: l["metodo"], v)
    partes += ["", "### Por método", ""]
    linhas_metodo = []
    for metodo in METODOS:  # os 3 sempre aparecem, mesmo com zero
        q, s = por_metodo.get(metodo, (0, ZERO))
        linhas_metodo.append([metodo, q, brl(s)])
    partes.append(_tabela(["metodo", "lançamentos", "soma (R$)"], linhas_metodo, {1, 2}))
    return partes


def _secao_pendencias(lidos) -> list[str]:
    linhas = lidos[PENDENCIAS.nome]
    v = PENDENCIAS.coluna_valor
    qtd, soma = _total(linhas, v)
    partes = ["## Pendências", ""]
    por_tipo = _agrupar(linhas, lambda l: l["tipo"], v)
    partes.append(_tabela(["tipo", "pendências", "soma (R$)"],
                          [[k, q, brl(s)] for k, (q, s) in sorted(por_tipo.items())] + [["**total**", qtd, brl(soma)]],
                          {1, 2}))
    por_quem = _agrupar(linhas, lambda l: l["quem_decide"], v)
    partes += ["", "### Por quem decide", ""]
    partes.append(_tabela(["quem_decide", "pendências", "soma (R$)"],
                          [[k, q, brl(s)] for k, (q, s) in sorted(por_quem.items())], {1, 2}))
    partes += ["", "### Lista completa", ""]
    partes.append(_tabela(
        ["id_saida", "tipo", "refs", "valor (R$)", "quem_decide", "motivo"],
        [[l["id_saida"], l["tipo"], len(l["ref_origem"].split(SEPARADOR_REFS)), brl(_valor(l, v)),
          l["quem_decide"], l["motivo"]] for l in linhas],
        {2, 3}))
    return partes


def _secao_rastro(lidos, problemas: list[str]) -> list[str]:
    conf = conferir_rastro(lidos)
    partes = ["## Checagem do rastro", ""]
    partes.append(_tabela(["arquivo", "linhas (sem cabeçalho)"],
                          [[e.nome, len(lidos[e.nome])] for e in ARQUIVOS], {1}))
    partes += [
        "",
        f"- Itens nos 5 arquivos de resultado: {conf.itens}",
        f"- Itens com soma do rastro por id_saida = valor reportado: {conf.conferidos} de {conf.itens}",
        f"- Itens com soma diferente: {len(conf.divergentes)}",
        f"- Itens sem rastro: {len(conf.sem_rastro)}",
        f"- id_saida do rastro sem item: {len(conf.orfaos)}",
        f"- validar_saida: {'sem problemas' if not problemas else f'{len(problemas)} problema(s)'}",
        f"- Resultado: **{'rastro fecha' if conf.ok and not problemas else 'rastro NÃO fecha'}**",
    ]
    detalhes = ([f"  - {i}: reportado {brl(r)}, rastro {brl(s)}" for i, r, s in conf.divergentes]
                + [f"  - {i}: sem rastro" for i in conf.sem_rastro]
                + [f"  - {i}: no rastro, fora dos 5 arquivos" for i in conf.orfaos]
                + [f"  - {p}" for p in problemas])
    if detalhes:
        partes += ["", "Detalhes:", *detalhes]
    return partes


def _registro_execucao(pasta: Path) -> Path | None:
    """execucao.md da pasta de auditoria irmã da saída (config/auditoria.yaml), se existir."""
    from tarvo.auditoria import ARQUIVO_MD, carregar_config, pasta_padrao

    caminho = pasta_padrao(pasta, carregar_config()) / ARQUIVO_MD
    return caminho if caminho.is_file() else None


def resumir(pasta) -> str:
    """Resumo em Markdown da pasta de saída."""
    pasta = Path(pasta)
    lidos = ler_saida(pasta)
    problemas = validar_saida(pasta)
    registro = _registro_execucao(pasta)
    secoes = [
        [f"# Resumo da saída — {pasta.name or pasta}", "", f"Commit do código: {versao_do_codigo()}"],
        _secao_status(lidos),
        # O06: o registro da última execução do fechar, na pasta irmã
        [f"Registro da execução (arquivos de entrada com SHA-256, linhas lidas, comando e código de saída): "
         f"`{registro.parent.name}/{registro.name}` e `{registro.with_suffix('.json').name}`"] if registro else [],
        _secao_comissoes(lidos),
        _secao_notas(lidos),
        _secao_divergencias(lidos),
        _secao_lancamentos(lidos),
        _secao_pendencias(lidos),
        _secao_rastro(lidos, problemas),
    ]
    return "\n\n".join(t for t in ("\n".join(s).strip() for s in secoes) if t) + "\n"
