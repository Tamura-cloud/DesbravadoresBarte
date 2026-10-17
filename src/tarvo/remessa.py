"""Linha REMESSA (Ponte Câmbio): comissão sobre o spread realizado, divergências, nota única e pendências.

Regras do HIPOTESES.md, seção 1: R11 a R18, R23 e R27; premissas P01 e P18. Parâmetros em config/remessa.yaml.
O lojista é casado só pelo CNPJ da Ponte com o CNPJ da planilha; o nome do cliente da Ponte nunca é usado
para casar (só aparece como nome de exibição de CNPJ que não está na planilha).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
import yaml

from tarvo.leitores.comum import dinheiro, sem_acento
from tarvo.saida import COMISSOES, DIVERGENCIAS, NOTAS, PENDENCIAS, ItemSaida, texto_saida

if TYPE_CHECKING:
    from tarvo.fechamento import Entradas

CONFIG_REMESSA = Path(__file__).resolve().parents[2] / "config" / "remessa.yaml"
LINHA_NEGOCIO = "REMESSA"
ZERO = Decimal("0.00")

# Colunas que o leitor acrescenta e que não são conteúdo da operação.
COLUNAS_POSICAO = ("arquivo_origem", "linha_planilha")

MOTIVO_DUPLICATA = "o relatório da Ponte soma a operação duas vezes - pedir correção do relatório"
MOTIVO_FORA_COMPETENCIA = "operação contratada fora da competência {competencia}: não entra no mês (R11)"
MOTIVO_NAO_CADASTRADO = (
    "CNPJ da Ponte fora da planilha de taxas: comissão calculada mesmo assim (a Ponte paga), "
    "sem spread contratado para conferir divergência - cadastrar o lojista"
)
MOTIVO_CONTESTACAO = (
    "spread aplicado acima do contratado - valor cheio que o lojista pagou a mais, a devolver ao lojista (R15) - "
    "a nota sai pelo realizado (R16) e o ajuste vem no relatório da Ponte do mês seguinte, "
    "registrado no mês em que aparecer (R27)"
)
MOTIVO_NEGATIVO = "spread negativo com trava D-1 vencida (R12) - fora da comissão"
MOTIVO_NOTA_NAO_EMITIDA = "comissão de remessa do mês zero ou negativa: não emite nota (R17)"
MOTIVO_TED = "conferir se o TED de repasse da Ponte bate com a nota de intermediação - não supor desconto (R18)"


class ErroRemessa(ValueError):
    """Dado de entrada ou configuração que impede aplicar as regras da remessa."""


# ---------------------------------------------------------------- configuração

@dataclass(frozen=True)
class ConfigRemessa:
    participacao: Decimal
    spread_padrao: Decimal
    textos_padrao: frozenset[str]
    tolerancia_pp: Decimal
    duplicata_ignora: tuple[str, ...]
    tomador_cnpj: str
    tomador_nome: str
    discriminacao_nota: str
    quem_decide: str


def _str_cfg(v, campo: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise ErroRemessa(f"config: {campo} deveria ser texto entre aspas, veio {v!r}")
    return v


def carregar_config(caminho=CONFIG_REMESSA) -> ConfigRemessa:
    with open(caminho, encoding="utf-8") as f:
        bruto = yaml.safe_load(f)
    return ConfigRemessa(
        participacao=Decimal(_str_cfg(bruto["participacao_tarvo"], "participacao_tarvo")),
        spread_padrao=Decimal(_str_cfg(bruto["spread_padrao_pct"], "spread_padrao_pct")),
        textos_padrao=frozenset(sem_acento(_str_cfg(t, "spread_padrao_textos")) for t in bruto["spread_padrao_textos"]),
        tolerancia_pp=Decimal(_str_cfg(bruto["tolerancia_divergencia_pp"], "tolerancia_divergencia_pp")),
        duplicata_ignora=tuple(bruto.get("duplicata_colunas_ignoradas") or ()),
        tomador_cnpj=_str_cfg(bruto["tomador_nota"]["cnpj"], "tomador_nota.cnpj"),
        tomador_nome=_str_cfg(bruto["tomador_nota"]["nome"], "tomador_nota.nome"),
        discriminacao_nota=_str_cfg(bruto["discriminacao_nota"], "discriminacao_nota"),
        quem_decide=_str_cfg(bruto["quem_decide"], "quem_decide"),
    )


# ---------------------------------------------------------------- planilha de taxas

class Contratos:
    """Por CNPJ, as linhas da planilha vigente e o spread contratado numa data."""

    def __init__(self, taxas: pd.DataFrame, cfg: ConfigRemessa):
        self.cfg = cfg
        self.linhas: dict[str, list[dict]] = defaultdict(list)
        for linha in taxas.to_dict("records"):
            self.linhas[linha["cnpj"]].append(linha)

    def cadastrado(self, cnpj: str) -> bool:
        return cnpj in self.linhas

    def nome(self, cnpj: str) -> str:
        """Nome do lojista = o da primeira linha da planilha com esse CNPJ."""
        return self.linhas[cnpj][0]["lojista"]

    def vigente(self, cnpj: str, d: date) -> dict:
        vigentes = [
            l for l in self.linhas[cnpj]
            if (l["vigencia_inicio"] is None or l["vigencia_inicio"] <= d)
            and (l["vigencia_fim"] is None or d <= l["vigencia_fim"])
        ]
        if len(vigentes) != 1:
            refs = ", ".join(l["ref_origem"] for l in vigentes) or "nenhuma"
            raise ErroRemessa(f"CNPJ {cnpj}: esperada 1 linha vigente em {d}, achei {len(vigentes)} ({refs})")
        return vigentes[0]

    def spread_contratado(self, cnpj: str, d: date) -> tuple[Decimal, str]:
        """(spread contratado em p.p., ref da linha da planilha). Branco ou "padrão" = spread padrão (R14)."""
        linha = self.vigente(cnpj, d)
        if linha["spread_remessa_pct"] is not None:
            return linha["spread_remessa_pct"], linha["ref_origem"]
        texto = linha["spread_remessa_texto"]
        if texto is None or sem_acento(texto) in self.cfg.textos_padrao:
            return self.cfg.spread_padrao, linha["ref_origem"]
        raise ErroRemessa(f"CNPJ {cnpj}, {linha['ref_origem']}: spread de remessa {texto!r} não reconhecido")


# ---------------------------------------------------------------- duplicatas (R13)

def deduplicar(ponte: pd.DataFrame, cfg: ConfigRemessa) -> tuple[list[dict], list[dict]]:
    """(operações únicas, cópias descartadas). Fica a primeira linha da planilha de cada Nº Operação.

    Cópias com qualquer coluna diferente (fora as de posição e as de duplicata_colunas_ignoradas) são erro:
    não há regra para escolher uma.
    """
    ignorar = set(COLUNAS_POSICAO) | set(cfg.duplicata_ignora)
    unicas: dict[str, dict] = {}
    descartadas: list[dict] = []
    for op in sorted(ponte.to_dict("records"), key=lambda o: o["linha_planilha"]):
        primeira = unicas.get(op["ref_origem"])
        if primeira is None:
            unicas[op["ref_origem"]] = op
            continue
        diferentes = sorted(c for c in op if c not in ignorar and op[c] != primeira[c])
        if diferentes:
            raise ErroRemessa(
                f"Nº Operação {op['ref_origem']} repetido com valores diferentes nas linhas "
                f"{primeira['linha_planilha']} e {op['linha_planilha']} (colunas: {', '.join(diferentes)})"
            )
        descartadas.append(op)
    return list(unicas.values()), descartadas


# ---------------------------------------------------------------- cálculo por operação

@dataclass(frozen=True)
class OperacaoRemessa:
    arquivo_origem: str
    ref_origem: str
    cnpj: str
    cadastrado: bool
    spread_brl: Decimal
    spread_pct: Decimal
    spread_contratado: Decimal | None   # None: CNPJ fora da planilha
    comissao: Decimal | None            # None: spread negativo (R12)
    diferenca: Decimal | None           # None: dentro da tolerância ou sem contrato; negativa: valor da PEN-NEG

    @property
    def negativa(self) -> bool:
        return self.spread_brl < 0

    @property
    def divergente(self) -> bool:
        return self.diferenca is not None


def _obrigatorio(op: dict, campo: str):
    if op[campo] is None:
        raise ErroRemessa(f"{op['ref_origem']}: {campo} vazio")
    return op[campo]


def calcular_operacao(op: dict, contratos: Contratos, cfg: ConfigRemessa) -> OperacaoRemessa:
    cnpj = op["cnpj"]
    spread_brl, spread_pct = _obrigatorio(op, "spread_brl"), _obrigatorio(op, "spread_pct")
    data = _obrigatorio(op, "data_contratacao")
    negativa = spread_brl < 0

    comissao = None if negativa else dinheiro(spread_brl * cfg.participacao)  # R11, R02, R12

    contratado = diferenca = None
    cadastrado = contratos.cadastrado(cnpj)
    if cadastrado:
        contratado, _ = contratos.spread_contratado(cnpj, data)
        diff_pp = spread_pct - contratado
        if negativa or abs(diff_pp) >= cfg.tolerancia_pp:  # P01, P18
            # R15: valor cheio, sobre PTAX de referência × valor em moeda estrangeira
            base = _obrigatorio(op, "ptax_ref") * _obrigatorio(op, "valor_me")
            diferenca = dinheiro(diff_pp / 100 * base)
    elif negativa:
        raise ErroRemessa(f"{op['ref_origem']}: spread negativo de CNPJ {cnpj} fora da planilha, sem contratado")

    return OperacaoRemessa(
        arquivo_origem=op["arquivo_origem"], ref_origem=op["ref_origem"], cnpj=cnpj, cadastrado=cadastrado,
        spread_brl=spread_brl, spread_pct=spread_pct, spread_contratado=contratado,
        comissao=comissao, diferenca=diferenca,
    )


def na_competencia(op: dict, competencia: str) -> bool:
    return _obrigatorio(op, "data_contratacao").strftime("%Y-%m") == competencia  # R11


# ---------------------------------------------------------------- itens de saída

def _soma(valores) -> Decimal:
    return sum(valores, ZERO)


def _pendencia(id_saida: str, tipo: str, refs, motivo: str, valor: Decimal, origens, cfg: ConfigRemessa) -> ItemSaida:
    return ItemSaida(id_saida, PENDENCIAS.nome,
                     {"tipo": tipo, "ref_origem": refs, "motivo": texto_saida(motivo), "quem_decide": cfg.quem_decide},
                     valor, origens)


def gerar_itens(operacoes: list[OperacaoRemessa], descartadas: list[dict], fora: list[dict],
                nomes: dict[str, str], competencia: str, arquivo_ponte: str, cfg: ConfigRemessa) -> list[ItemSaida]:
    """nomes: CNPJ -> nome do lojista (planilha; para CNPJ fora dela, o cliente da Ponte)."""
    itens: list[ItemSaida] = []
    por_cnpj: dict[str, list[OperacaoRemessa]] = defaultdict(list)
    for op in operacoes:
        por_cnpj[op.cnpj].append(op)

    rastro_nota = []
    for cnpj in sorted(por_cnpj):
        doc = sorted(por_cnpj[cnpj], key=lambda o: o.ref_origem)
        com_comissao = [o for o in doc if o.comissao is not None]
        rastro = [(o.arquivo_origem, o.ref_origem, o.comissao) for o in com_comissao]
        if com_comissao:
            itens.append(ItemSaida(f"COM-REM-{cnpj}", COMISSOES.nome,
                                   {"cnpj": cnpj, "lojista": texto_saida(nomes[cnpj]), "linha_negocio": LINHA_NEGOCIO},
                                   _soma(o.comissao for o in com_comissao), rastro))
            rastro_nota.extend(rastro)

        if not doc[0].cadastrado and com_comissao:
            itens.append(_pendencia(f"PEN-NAOCAD-REM-{cnpj}", "LOJISTA_NAO_CADASTRADO",
                                    [o.ref_origem for o in com_comissao], MOTIVO_NAO_CADASTRADO,
                                    _soma(o.comissao for o in com_comissao), rastro, cfg))

        # R23: spread negativo não é divergência (o lojista não pagou a mais); fica só na PEN-NEG abaixo
        for o in (o for o in doc if o.divergente and not o.negativa):  # R15, P01
            itens.append(ItemSaida(f"DIV-REM-{o.ref_origem}", DIVERGENCIAS.nome,
                                   {"cnpj": cnpj, "linha_negocio": LINHA_NEGOCIO, "ref_origem": o.ref_origem,
                                    "taxa_contratada_pct": o.spread_contratado, "taxa_aplicada_pct": o.spread_pct},
                                   o.diferenca, [(o.arquivo_origem, o.ref_origem, o.diferenca)]))

        acima = [o for o in doc if o.divergente and not o.negativa and o.diferenca > 0]
        if acima:  # R16, R18
            itens.append(_pendencia(f"PEN-CONTEST-REM-{cnpj}", "CONTESTACAO_PONTE",
                                    [o.ref_origem for o in acima], MOTIVO_CONTESTACAO,
                                    _soma(o.diferenca for o in acima),
                                    [(o.arquivo_origem, o.ref_origem, o.diferenca) for o in acima], cfg))

        for o in (o for o in doc if o.negativa):  # R12, R18, R23, P18
            itens.append(_pendencia(f"PEN-NEG-REM-{o.ref_origem}", "CONTESTACAO_PONTE", o.ref_origem,
                                    MOTIVO_NEGATIVO, o.diferenca, [(o.arquivo_origem, o.ref_origem, o.diferenca)], cfg))

    copias: dict[str, list[dict]] = defaultdict(list)
    for d in descartadas:
        copias[d["ref_origem"]].append(d)
    for ref in sorted(copias):  # R13
        origens = [(d["arquivo_origem"], d["ref_origem"], d["spread_brl"]) for d in copias[ref]]
        itens.append(_pendencia(f"PEN-DUP-REM-{ref}", "OPERACAO_DUPLICADA", ref, MOTIVO_DUPLICATA,
                                _soma(o[2] for o in origens), origens, cfg))

    for op in sorted(fora, key=lambda o: o["ref_origem"]):  # R11
        itens.append(_pendencia(f"PEN-FORA-REM-{op['ref_origem']}", "OPERACAO_FORA_DA_COMPETENCIA", op["ref_origem"],
                                MOTIVO_FORA_COMPETENCIA.format(competencia=competencia), op["spread_brl"],
                                [(op["arquivo_origem"], op["ref_origem"], op["spread_brl"])], cfg))

    total = _soma(o[2] for o in rastro_nota)
    refs_nota = [o[1] for o in rastro_nota] or arquivo_ponte
    if total > 0:  # R16, R17: uma nota, tomadora Ponte, pelo realizado
        itens.append(ItemSaida(f"NF-REM-{cfg.tomador_cnpj}", NOTAS.nome,
                               {"tomador_cnpj": cfg.tomador_cnpj, "tomador": texto_saida(cfg.tomador_nome),
                                "linha_negocio": LINHA_NEGOCIO,
                                "discriminacao": texto_saida(cfg.discriminacao_nota.format(competencia=competencia))},
                               total, rastro_nota))
    else:
        itens.append(_pendencia(f"PEN-NF-REM-{cfg.tomador_cnpj}", "NOTA_NAO_EMITIDA", refs_nota,
                                MOTIVO_NOTA_NAO_EMITIDA, total, rastro_nota, cfg))

    # R18: o TED é conferido contra a nota (mesmo valor e mesmas operações); nenhum desconto é suposto
    itens.append(_pendencia("PEN-TED-PONTE", "CONFERENCIA_REPASSE", refs_nota, MOTIVO_TED, total, rastro_nota, cfg))
    return itens


def calcular_remessa(ponte: pd.DataFrame, taxas: pd.DataFrame, competencia: str, arquivo_ponte: str,
                     cfg: ConfigRemessa) -> list[ItemSaida]:
    contratos = Contratos(taxas, cfg)
    unicas, descartadas = deduplicar(ponte, cfg)
    no_mes = [op for op in unicas if na_competencia(op, competencia)]
    fora = [op for op in unicas if not na_competencia(op, competencia)]
    operacoes = [calcular_operacao(op, contratos, cfg) for op in no_mes]

    nomes = {}
    for op in no_mes:
        if contratos.cadastrado(op["cnpj"]):
            nomes[op["cnpj"]] = contratos.nome(op["cnpj"])
        else:  # só exibição: o casamento foi pelo CNPJ
            nomes.setdefault(op["cnpj"], _obrigatorio(op, "cliente"))
    return gerar_itens(operacoes, descartadas, fora, nomes, competencia, arquivo_ponte, cfg)


def remessa(entradas: Entradas, config=CONFIG_REMESSA) -> list[ItemSaida]:
    """Módulo do fechamento: itens da linha REMESSA a partir da Ponte e da planilha de taxas."""
    return calcular_remessa(entradas.ponte, entradas.taxas, entradas.competencia,
                            entradas.ponte_rodape["arquivo_origem"], carregar_config(config))
