"""Fechamento parcial (R44): o que cada parte do fechamento lê, fontes bloqueadas e as pendências PEN-BLOQUEIO.

O mapa PRODUTOS foi tirado do que cada módulo lê de Entradas (checkout.py, remessa.py, bancos.py, contestacao.py)
e é conferido por tests/test_dependencias.py: cada produto roda só com as fontes declaradas. Sem uma delas, o
produto não é gerado e o resto do fechamento segue. Fonte bloqueada:
- AUSENTE: nenhum arquivo casa com o padrão de config/entradas.yaml;
- AMBIGUA: dois ou mais arquivos num tipo de arquivo único (o fechamento não escolhe um);
- ILEGIVEL: coluna obrigatória faltando ou erro de leitura.
Na Orbe, que aceita vários arquivos (O05), um arquivo de ajustes com problema fica bloqueado sozinho: os outros são
lidos e o checkout sai PROVISÓRIO (coluna extra situacao). Coluna a mais ou fora de ordem é só aviso (PEN-AVISO-LAYOUT).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

import yaml

from tarvo.saida import PENDENCIAS, ItemSaida, texto_saida

if TYPE_CHECKING:
    from tarvo.fechamento import Entradas

CONFIG_ENTRADAS = Path(__file__).resolve().parents[2] / "config" / "entradas.yaml"
ZERO = Decimal("0.00")
AUSENTE, AMBIGUA, ILEGIVEL = "AUSENTE", "AMBIGUA", "ILEGIVEL"
COLUNA_SITUACAO, PROVISORIO = "situacao", "PROVISORIO"

NATUREZAS = {AUSENTE: "ausente", AMBIGUA: "ambígua", ILEGIVEL: "ilegível"}


@dataclass(frozen=True)
class Produto:
    chave: str
    descricao: str
    fontes: tuple[str, ...]   # sem qualquer uma delas, o produto não é gerado


# Lido do código: o que cada parte do fechamento usa de Entradas.
PRODUTOS: tuple[Produto, ...] = (
    Produto("checkout", "checkout (comissões, notas, divergências e pendências de checkout)", ("orbe", "taxas")),
    Produto("remessa", "remessa (comissões, nota da Ponte, divergências e pendências de remessa, inclusive a "
                       "conferência do TED de repasse PEN-TED-PONTE)", ("ponte_eml", "taxas")),
    Produto("lancamentos_aurora", "lançamentos do Aurora e as pendências deles", ("aurora", "plano_de_contas")),
    Produto("lancamentos_meridiano", "lançamentos do Meridiano e as pendências deles", ("meridiano", "plano_de_contas")),
    Produto("conferencia_ted_liquidacao", "conferência das TEDs de liquidação com as operações da Ponte (P11)",
            ("meridiano", "plano_de_contas", "ponte_eml")),
    Produto("conferencia_pix_remessas", "conferência dos PIX recebidos com as remessas por cliente (P12)",
            ("meridiano", "plano_de_contas", "ponte_eml")),
    Produto("conferencia_transferencias", "conferência das transferências Aurora × Meridiano (P13)",
            ("aurora", "meridiano", "plano_de_contas")),
    Produto("contestacao_orbe", "rascunho de contestação da Orbe (R29)", ("orbe", "taxas")),
    Produto("contestacao_ponte", "rascunho de contestação da Ponte (R29)", ("ponte_eml", "taxas")),
)
POR_CHAVE = {p.chave: p for p in PRODUTOS}

# Fonte que um produto lê só para conferir a configuração: sem ela o produto sai, sem a conferência.
USO_PARCIAL = {
    "taxas": ("os CNPJs de config/favorecidos.yaml e config/pagadores_meridiano.yaml não foram conferidos com a "
              "planilha (P07, P08): os lançamentos e a conferência dos PIX (P12) usam as listas como estão"),
}

MOTIVO_BLOQUEIO = (
    "fonte {fonte} bloqueada ({natureza}, R44): {erro} - não gerado: {nao_gerado}{parcial} - o resto do fechamento "
    "foi gerado normalmente - próximo passo: {passo}; depois rodar o fechamento de novo - quem libera o mês é a "
    "Helena{comercial}"
)
MOTIVO_BLOQUEIO_ARQUIVO = (
    "arquivo {arquivo} da {fonte} bloqueado (R44): {erro} - nenhuma linha dele entrou no fechamento ({linhas}); os "
    "demais arquivos da {fonte} foram lidos - saíram PROVISÓRIOS: {produtos} - próximo passo: {passo}; depois rodar o "
    "fechamento de novo - quem libera o mês é a Helena"
)
MOTIVO_AVISO_LAYOUT = (
    "layout diferente do esperado, mas com todas as colunas obrigatórias (R44): {avisos} - nada deixou de ser gerado - "
    "próximo passo: a Helena confirma com quem mandou o arquivo que o layout mudou e que os valores de cada coluna "
    "estão certos"
)
PASSO = {
    AUSENTE: "pôr na pasta o arquivo de {fonte}, como chegou, com um nome que case com '{padrao}'",
    ILEGIVEL: "pedir a quem mandou o arquivo de {fonte} a versão no layout esperado e pôr na pasta no lugar deste",
}
PASSO_ORBE_LAYOUT = "pedir à Orbe o arquivo no mesmo layout do relatório e pôr na pasta no lugar deste"
PASSO_ORBE_CONFLITO = ("a Helena confirma com a Orbe qual versão da transação vale e deixa na pasta só os arquivos "
                       "certos (o fechamento não escolhe)")


@dataclass(frozen=True)
class Bloqueio:
    fonte: str                          # tipo de config/entradas.yaml
    natureza: str                       # AUSENTE, AMBIGUA ou ILEGIVEL
    erro: str                           # o erro exato: padrão, candidatos, coluna, linha
    origens: tuple[tuple[str, str], ...]  # (arquivo, ref) de cada ponto citado, para o rastro
    passo: str
    arquivo: str | None = None          # só num bloqueio parcial: o arquivo da Orbe que ficou de fora
    linhas: int | None = None           # num bloqueio parcial: linhas de dados que ficaram de fora
    refs: tuple[str, ...] = ()          # ref_origem da pendência; vazio = os arquivos (ou o padrão) das origens

    @property
    def parcial(self) -> bool:
        return self.arquivo is not None


@dataclass(frozen=True)
class Aviso:
    fonte: str
    arquivo: str
    texto: str


@dataclass(frozen=True)
class ConfigBloqueio:
    quem_decide: str
    quem_decide_por_fonte: dict[str, str]
    descricoes: dict[str, str]

    def quem(self, fonte: str) -> str:
        return self.quem_decide_por_fonte.get(fonte, self.quem_decide)


def carregar_config(caminho=CONFIG_ENTRADAS) -> ConfigBloqueio:
    with open(caminho, encoding="utf-8") as f:
        bruto = yaml.safe_load(f)
    bloqueio = bruto["bloqueio"]
    return ConfigBloqueio(bloqueio["quem_decide"], dict(bloqueio.get("quem_decide_por_fonte") or {}),
                          dict(bruto.get("descricoes") or {}))


# ---------------------------------------------------------------- o que pode ser gerado

def bloqueadas(bloqueios: Iterable[Bloqueio]) -> frozenset[str]:
    """Fontes bloqueadas inteiras (o bloqueio de um arquivo só da Orbe não bloqueia a fonte)."""
    return frozenset(b.fonte for b in bloqueios if not b.parcial)


def gera(chave: str, entradas: Entradas) -> bool:
    """O produto pode ser gerado: nenhuma das fontes dele está bloqueada inteira."""
    return not set(POR_CHAVE[chave].fontes) & bloqueadas(entradas.bloqueios)


def provisorio(chave: str, entradas: Entradas) -> bool:
    """O produto sai, mas uma fonte dele perdeu um arquivo (bloqueio parcial)."""
    return gera(chave, entradas) and any(b.parcial and b.fonte in POR_CHAVE[chave].fontes for b in entradas.bloqueios)


def nao_gerados(bloqueios: Iterable[Bloqueio]) -> list[Produto]:
    fora = bloqueadas(bloqueios)
    return [p for p in PRODUTOS if set(p.fontes) & fora]


def _provisorios(bloqueios: Iterable[Bloqueio]) -> list[Produto]:
    """Produtos gerados com uma fonte que perdeu um arquivo (bloqueio parcial)."""
    bloqueios = list(bloqueios)
    fora = bloqueadas(bloqueios)
    parciais = {b.fonte for b in bloqueios if b.parcial}
    return [p for p in PRODUTOS if not set(p.fontes) & fora and set(p.fontes) & parciais]


def marcar_provisorio(itens: Iterable[ItemSaida]) -> list[ItemSaida]:
    """Coluna extra situacao = PROVISORIO em cada item (só aparece nos CSVs quando há item provisório)."""
    return [replace(i, campos={**i.campos, COLUNA_SITUACAO: PROVISORIO}) for i in itens]


# ---------------------------------------------------------------- pendências

def _id(texto: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", texto)


def _refs(b: Bloqueio) -> list[str]:
    return list(b.refs) or list(dict.fromkeys(arquivo for arquivo, _ in b.origens))


def _descricoes(produtos: Iterable[Produto]) -> str:
    return "; ".join(p.descricao for p in produtos) or "nada"


def pendencias_bloqueio(entradas: Entradas, cfg: ConfigBloqueio | None = None) -> list[ItemSaida]:
    """PEN-BLOQUEIO-<FONTE> (fonte inteira) e PEN-BLOQUEIO-ORBE-<arquivo> (um arquivo só), valor 0,00 (R44)."""
    cfg = cfg or carregar_config()
    fora = bloqueadas(entradas.bloqueios)
    itens = []
    for b in entradas.bloqueios:
        nome = f"{b.fonte} ({cfg.descricoes[b.fonte]})" if b.fonte in cfg.descricoes else b.fonte
        if b.parcial:
            linhas = f"{b.linhas} linha(s) de dados" if b.linhas is not None else "o arquivo não pôde ser lido"
            motivo = MOTIVO_BLOQUEIO_ARQUIVO.format(arquivo=b.arquivo, fonte=b.fonte, erro=b.erro, linhas=linhas,
                                                    produtos=_descricoes(_provisorios(entradas.bloqueios)),
                                                    passo=b.passo)
            id_saida = f"PEN-BLOQUEIO-{b.fonte.upper()}-{_id(b.arquivo)}"
            tipo = "ARQUIVO_BLOQUEADO"
        else:
            parcial = f" - gerado sem conferir: {USO_PARCIAL[b.fonte]}" if b.fonte in USO_PARCIAL else ""
            comercial = " (taxa e cadastro: o Comercial decide antes, R28)" if b.fonte == "taxas" else ""
            motivo = MOTIVO_BLOQUEIO.format(fonte=nome, natureza=NATUREZAS[b.natureza], erro=b.erro,
                                            nao_gerado=_descricoes(p for p in PRODUTOS if b.fonte in p.fontes),
                                            parcial=parcial, passo=b.passo, comercial=comercial)
            id_saida = f"PEN-BLOQUEIO-{b.fonte.upper()}"
            tipo = "FONTE_BLOQUEADA"
        itens.append(ItemSaida(id_saida, PENDENCIAS.nome,
                               {"tipo": tipo, "ref_origem": _refs(b), "motivo": texto_saida(motivo),
                                "quem_decide": cfg.quem(b.fonte)},
                               ZERO, [(a, r, ZERO) for a, r in b.origens]))
    return itens


def pendencias_aviso(entradas: Entradas, cfg: ConfigBloqueio | None = None) -> list[ItemSaida]:
    """PEN-AVISO-LAYOUT-<FONTE>: coluna a mais ou fora de ordem, a leitura seguiu pelo nome (R44). Valor 0,00."""
    cfg = cfg or carregar_config()
    por_fonte: dict[str, list[Aviso]] = {}
    for a in entradas.avisos:
        por_fonte.setdefault(a.fonte, []).append(a)
    itens = []
    for fonte, avisos in por_fonte.items():
        origens = list(dict.fromkeys((a.arquivo, "L1") for a in avisos))
        itens.append(ItemSaida(f"PEN-AVISO-LAYOUT-{fonte.upper()}", PENDENCIAS.nome,
                               {"tipo": "AVISO_LAYOUT", "ref_origem": [a for a, _ in origens],
                                "motivo": texto_saida(MOTIVO_AVISO_LAYOUT.format(
                                    avisos=" - ".join(a.texto for a in avisos))),
                                "quem_decide": cfg.quem(fonte)},
                               ZERO, [(a, r, ZERO) for a, r in origens]))
    return itens


# ---------------------------------------------------------------- quadro final

def quadro(bloqueios: Iterable[Bloqueio]) -> str:
    """"FECHAMENTO COMPLETO" ou "FECHAMENTO PARCIAL — fontes bloqueadas: ...; não gerado: ...; ver pendências PEN-BLOQUEIO"."""
    bloqueios = list(bloqueios)
    if not bloqueios:
        return "FECHAMENTO COMPLETO"
    fontes = []
    for b in bloqueios:
        fontes.append(f"{b.fonte} (só o arquivo {b.arquivo})" if b.parcial else f"{b.fonte} ({NATUREZAS[b.natureza]})")
    linhas = [f"FECHAMENTO PARCIAL — fontes bloqueadas: {', '.join(fontes)}; "
              f"não gerado: {_descricoes(nao_gerados(bloqueios))}; ver pendências PEN-BLOQUEIO"]
    provisorios = _provisorios(bloqueios)
    if provisorios:
        linhas.append(f"  provisório (coluna situacao = PROVISORIO nos CSVs; aviso nas notas do rascunho): "
                      f"{_descricoes(provisorios)}")
    return "\n".join(linhas)
