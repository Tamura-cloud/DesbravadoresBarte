"""Linha REMESSA (Ponte Câmbio): comissão sobre o spread realizado, divergências, nota única e pendências.

Regras do HIPOTESES.md, seção 1: R11 a R18, R23, R27, R31, R32 e R34; premissas P01, P18 e P25. Parâmetros em config/remessa.yaml.
O lojista é casado só pelo CNPJ da Ponte com o CNPJ da planilha; o nome do cliente da Ponte nunca é usado
para casar (só aparece como nome de exibição de CNPJ que não está na planilha).
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import pandas as pd
import yaml

from tarvo import dependencias as dep
from tarvo.leitores.comum import dinheiro, sem_acento
from tarvo.resumo import brl
from tarvo.saida import COMISSOES, DIVERGENCIAS, NOTAS, PENDENCIAS, ItemSaida, texto_saida

if TYPE_CHECKING:
    from tarvo.fechamento import Entradas

CONFIG_REMESSA = Path(__file__).resolve().parents[2] / "config" / "remessa.yaml"
LINHA_NEGOCIO = "REMESSA"
ZERO = Decimal("0.00")

# Colunas que o leitor acrescenta e que não são conteúdo da operação.
COLUNAS_POSICAO = ("arquivo_origem", "linha_planilha")

MOTIVO_DUPLICATA = "o relatório da Ponte soma a operação duas vezes - pedir correção do relatório"
MOTIVO_FORA_COMPETENCIA = (
    "operação contratada fora da competência {competencia}: não entra no mês (R11) - próximo passo: a Helena decide "
    "em que fechamento a operação entra, pela data de contratação (R11)"
)
MOTIVO_NAO_CADASTRADO = (
    "CNPJ da Ponte fora da planilha de taxas: comissão calculada mesmo assim (a Ponte paga), "
    "sem spread contratado para conferir divergência - próximo passo: o Comercial confirma o spread contratado para "
    "cadastrar o lojista na planilha de taxas (P04, R28)"
)
MOTIVO_CONTESTACAO = (
    "spread aplicado acima do contratado - divergência de contrato: a Tarvo contesta com a Ponte e o lojista é "
    "ressarcido do valor cheio que pagou a mais (R15, R32) - a nota sai pelo realizado (R16) e o ajuste vem no "
    "relatório da Ponte do mês seguinte, registrado no mês em que aparecer (R27, R31)"
)
MOTIVO_NEGATIVO = (
    "spread negativo com trava D-1 vencida, fora da comissão (R12, R34) - spread do relatório: {spread} (o que "
    "aconteceu) - diferença até o spread contratado: {diferenca} (o que se pede à Ponte; a trava D-1 deveria ter "
    "sido honrada) - próximo passo: a Helena contesta com a Ponte, pelo rascunho de e-mail em {rascunho} (R12, R29)"
)
MOTIVO_NOTA_NAO_EMITIDA = (
    "comissão de remessa do mês zero ou negativa: não emite nota (R17) - próximo passo: a Helena decide o tratamento "
    "do saldo (R06, R17)"
)
MOTIVO_NOTA_NAO_EMITIDA_AJUSTE = (
    "comissão de remessa do mês zero ou negativa depois de abater ajuste(s) da Ponte (R31): não emite nota, "
    "vale a regra de nota zerada ou negativa (R06, R17) - próximo passo: a Helena decide o tratamento do saldo"
)
MOTIVO_AJUSTE_SEM_LOJISTA = (
    "ajuste da Ponte (R31) sem CNPJ e sem a operação original {original} - não abatido, porque não há lojista para "
    "a comissão - AJUSTE REF {original} - próximo passo: a Helena confere com a Ponte a operação original e o lojista "
    "do ajuste e decide o abatimento (R31)"
)
MOTIVO_AJUSTE_SEM_ORIGINAL = (
    "ajuste da Ponte (R31) abate a participação do mês, mas a operação original {original} não está no relatório da "
    "competência anterior ({anterior}) nem no deste mês - conferir com a Ponte"
)
MOTIVO_TED = ("conferir o TED de repasse da Ponte quando cair, contra a nota de intermediação - ainda não se sabe como a "
              "Ponte vai pagar e nenhum desconto no repasse é suposto (R18)")


class ErroRemessa(ValueError):
    """Dado de entrada ou configuração que impede aplicar as regras da remessa."""


class ErroDadoRemessa(ErroRemessa, dep.ErroDado):
    """Dado da Ponte ou da planilha que impede aplicar a regra a um lojista ou a uma operação (R44): no fechamento,
    vira PEN-REGRA e o resto da remessa fecha."""


class ProblemaRemessa(NamedTuple):
    erro: dep.ErroDado
    op: dict             # a linha da Ponte, como o leitor devolveu
    chave: str           # CNPJ do lojista, ou o Nº Operação quando a linha não tem CNPJ


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
    quem_decide_cadastro: str | None = None   # P04: pendência de cadastro (LOJISTA_NAO_CADASTRADO); None = quem_decide
    ajuste_padrao: re.Pattern | None = None   # R31: observação que identifica a linha de ajuste
    ajuste_participacao: Decimal = Decimal("0.5")  # P25: participação aplicada ao Spread R$ do ajuste


def _str_cfg(v, campo: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise ErroRemessa(f"config: {campo} deveria ser texto entre aspas, veio {v!r}")
    return v


def _padrao_ajuste(bruto: dict | None) -> tuple[re.Pattern | None, Decimal]:
    if not bruto:
        return None, Decimal("0.5")
    try:
        padrao = re.compile(_str_cfg(bruto["padrao_observacao"], "ajuste.padrao_observacao"), re.IGNORECASE)
    except re.error as e:
        raise ErroRemessa(f"config: ajuste.padrao_observacao inválido: {e}") from None
    if padrao.groups != 1:
        raise ErroRemessa("config: ajuste.padrao_observacao precisa de 1 grupo (o Nº da operação original)")
    return padrao, Decimal(_str_cfg(bruto["participacao_tarvo"], "ajuste.participacao_tarvo"))


def carregar_config(caminho=CONFIG_REMESSA) -> ConfigRemessa:
    with open(caminho, encoding="utf-8") as f:
        bruto = yaml.safe_load(f)
    padrao, participacao_ajuste = _padrao_ajuste(bruto.get("ajuste"))
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
        quem_decide_cadastro=_str_cfg(bruto["quem_decide_cadastro"], "quem_decide_cadastro")
        if "quem_decide_cadastro" in bruto else None,
        ajuste_padrao=padrao, ajuste_participacao=participacao_ajuste,
    )


# ---------------------------------------------------------------- planilha de taxas

class Contratos:
    """Por CNPJ, as linhas da planilha vigente e o spread contratado numa data."""

    def __init__(self, taxas: pd.DataFrame, cfg: ConfigRemessa, rejeitadas=()):
        self.cfg = cfg
        self.linhas: dict[str, list[dict]] = defaultdict(list)
        for linha in taxas.to_dict("records"):
            self.linhas[linha["cnpj"]].append(linha)
        # R44: CNPJ com linha da planilha que o leitor não converteu; as operações dele viram PEN-REGRA-CADASTRO
        self.cnpj_suspeito = {r.cnpj: r.erro for r in rejeitadas}

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
            raise ErroDadoRemessa(dep.VIGENCIA, f"CNPJ {cnpj}: esperada 1 linha vigente na planilha de taxas em {d}, "
                                  f"achei {len(vigentes)} ({refs})", do_lojista=True)
        return vigentes[0]

    def spread_contratado(self, cnpj: str, d: date) -> tuple[Decimal, str]:
        """(spread contratado em p.p., ref da linha da planilha). Branco ou "padrão" = spread padrão (R14)."""
        linha = self.vigente(cnpj, d)
        if linha["spread_remessa_pct"] is not None:
            return linha["spread_remessa_pct"], linha["ref_origem"]
        texto = linha["spread_remessa_texto"]
        if texto is None or sem_acento(texto) in self.cfg.textos_padrao:
            return self.cfg.spread_padrao, linha["ref_origem"]
        raise ErroDadoRemessa(dep.TAXA, f"CNPJ {cnpj}, {linha['ref_origem']} da planilha de taxas: spread de remessa "
                              f"{texto!r} não reconhecido", do_lojista=True)


# ---------------------------------------------------------------- duplicatas (R13)

class Conflito(NamedTuple):
    """Nº Operação repetido com valores diferentes: todas as cópias ficam de fora (R44)."""

    ref_origem: str
    copias: list[dict]
    mensagem: str


def deduplicar(ponte: pd.DataFrame, cfg: ConfigRemessa,
               conflitos: list[Conflito] | None = None) -> tuple[list[dict], list[dict]]:
    """(operações únicas, cópias descartadas). Fica a primeira linha da planilha de cada Nº Operação.

    Cópias com qualquer coluna diferente (fora as de posição e as de duplicata_colunas_ignoradas) não têm regra para
    escolher uma: sem conflitos é erro; com a lista (o fechamento, R44), o Nº sai inteiro e vai para conflitos.
    """
    ignorar = set(COLUNAS_POSICAO) | set(cfg.duplicata_ignora)
    unicas: dict[str, dict] = {}
    descartadas: list[dict] = []
    em_conflito: dict[str, Conflito] = {}
    for op in sorted(ponte.to_dict("records"), key=lambda o: o["linha_planilha"]):
        ref = op["ref_origem"]
        if ref in em_conflito:
            em_conflito[ref].copias.append(op)
            continue
        primeira = unicas.get(ref)
        if primeira is None:
            unicas[ref] = op
            continue
        diferentes = sorted(c for c in op if c not in ignorar and op[c] != primeira[c])
        if diferentes:
            mensagem = (f"Nº Operação {ref} repetido com valores diferentes nas linhas "
                        f"{primeira['linha_planilha']} e {op['linha_planilha']} (colunas: {', '.join(diferentes)})")
            if conflitos is None:
                raise ErroDadoRemessa(dep.DUPLICADA, mensagem)
            copias = [primeira] + [d for d in descartadas if d["ref_origem"] == ref] + [op]
            descartadas = [d for d in descartadas if d["ref_origem"] != ref]
            del unicas[ref]
            em_conflito[ref] = Conflito(ref, copias, mensagem)
            continue
        descartadas.append(op)
    if conflitos is not None:
        conflitos.extend(em_conflito.values())
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
        raise ErroDadoRemessa(dep.LINHA, f"operação {op['ref_origem']} (linha {op.get('linha_planilha')} do relatório "
                              f"da Ponte): {campo} vazio")
    return op[campo]


def calcular_operacao(op: dict, contratos: Contratos, cfg: ConfigRemessa) -> OperacaoRemessa:
    cnpj = op["cnpj"]
    if cnpj in contratos.cnpj_suspeito:
        raise ErroDadoRemessa(dep.CADASTRO, f"a linha do CNPJ {cnpj} na planilha de taxas não pôde ser lida "
                              f"({contratos.cnpj_suspeito[cnpj]})", do_lojista=True)
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
    elif negativa:  # P05: sem spread contratado não há valor de contestação (R44: não para mais o fechamento)
        raise ErroDadoRemessa(dep.CADASTRO, f"{op['ref_origem']}: spread negativo de CNPJ {cnpj} fora da planilha de "
                              "taxas, sem spread contratado para valorar a contestação (P05)")

    return OperacaoRemessa(
        arquivo_origem=op["arquivo_origem"], ref_origem=op["ref_origem"], cnpj=cnpj, cadastrado=cadastrado,
        spread_brl=spread_brl, spread_pct=spread_pct, spread_contratado=contratado,
        comissao=comissao, diferenca=diferenca,
    )


# ---------------------------------------------------------------- ajustes da Ponte (R31)

def referencia_ajuste(op: dict, cfg: ConfigRemessa) -> str | None:
    """Nº da operação original se a observação da linha casa com o padrão de ajuste (config/remessa.yaml), senão None."""
    if cfg.ajuste_padrao is None or not op.get("observacao"):
        return None
    m = cfg.ajuste_padrao.search(op["observacao"])
    return m.group(1).rstrip(".,;:)") if m else None


def separar_ajustes(unicas: list[dict], cfg: ConfigRemessa,
                    problemas: list[ProblemaRemessa] | None = None) -> tuple[list[dict], list[dict]]:
    """(operações, ajustes). A checagem vem antes de qualquer regra de operação: ajuste nunca é spread negativo,
    divergência nem operação nova (R31). Linha sem CNPJ só é aceita se for ajuste; senão é erro ou, com problemas
    (o fechamento, R44), fica de fora e vai para a lista."""
    operacoes, ajustes = [], []
    for op in unicas:
        if referencia_ajuste(op, cfg) is not None:
            ajustes.append(op)
        elif op["cnpj"] is None:
            erro = ErroDadoRemessa(dep.LINHA, f"operação {op['ref_origem']} (linha {op.get('linha_planilha')} do "
                                   "relatório da Ponte): CNPJ vazio e a observação não casa com o padrão de ajuste")
            if problemas is None:
                raise erro
            problemas.append(ProblemaRemessa(erro, op, op["ref_origem"]))
        else:
            operacoes.append(op)
    return operacoes, ajustes


@dataclass(frozen=True)
class Anterior:
    """O que a competência anterior ensina sobre a original de um ajuste."""

    competencia: str
    arquivo_origem: str
    operacoes: dict[str, dict]       # Nº Operação -> operação única do relatório anterior
    contestadas: frozenset[str]      # Nº com DIV-REM, PEN-NEG-REM ou PEN-DUP-REM na competência anterior


@dataclass(frozen=True)
class AjusteRemessa:
    arquivo_origem: str
    ref_origem: str                  # Nº Operação da própria linha de ajuste
    cnpj: str | None                 # None: sem CNPJ na linha e sem original; não é abatido (PEN-AJUSTE-SEMLOJISTA)
    ref_original: str
    spread_brl: Decimal
    comissao: Decimal                # abatimento (ou crédito) da participação, P25
    competencia_original: str | None
    arquivo_original: str | None     # só quando a original está no relatório anterior (outro arquivo)
    sem_original: bool               # há competência anterior e a original não está nela nem neste mês
    contestada: bool
    anterior: str | None

    @property
    def descricao(self) -> str:
        texto = f"AJUSTE REF {self.ref_original}"
        if self.competencia_original:
            texto += f" (operação de {self.competencia_original}"
            texto += f", contestada em {self.anterior})" if self.contestada else ")"
        elif self.sem_original:
            texto += f" (operação original não encontrada em {self.anterior})"
        return texto


def calcular_ajuste(op: dict, ref_original: str, operacoes_mes: dict[str, dict], cfg: ConfigRemessa,
                    anterior: Anterior | None) -> AjusteRemessa:
    spread = _obrigatorio(op, "spread_brl")
    original, onde = operacoes_mes.get(ref_original), "atual"
    if original is None and anterior is not None:
        original, onde = anterior.operacoes.get(ref_original), "anterior"
    cnpj = op["cnpj"] or (original["cnpj"] if original is not None else None)
    return AjusteRemessa(
        arquivo_origem=op["arquivo_origem"], ref_origem=op["ref_origem"], cnpj=cnpj, ref_original=ref_original,
        spread_brl=spread, comissao=dinheiro(spread * cfg.ajuste_participacao),
        competencia_original=(original["data_contratacao"].strftime("%Y-%m")
                              if original is not None and original["data_contratacao"] is not None else None),
        arquivo_original=original["arquivo_origem"] if onde == "anterior" and original is not None else None,
        sem_original=original is None and anterior is not None,
        contestada=onde == "anterior" and original is not None and ref_original in anterior.contestadas,
        anterior=anterior.competencia if anterior is not None else None,
    )


def competencia_anterior(competencia: str) -> str:
    ano, mes = (int(p) for p in competencia.split("-"))
    return f"{ano - (mes == 1):04d}-{(mes - 2) % 12 + 1:02d}"


def pasta_anterior(pasta: Path, competencia: str) -> Path | None:
    """Pasta da competência anterior, ao lado da atual: troca a competência no nome da pasta ou, se o nome não a
    tem, procura uma pasta com o nome da competência anterior. None se não existir."""
    anterior = competencia_anterior(competencia)
    if competencia in pasta.name:
        candidata = pasta.with_name(pasta.name.replace(competencia, anterior))
    else:
        candidata = pasta.parent / anterior
    return candidata if candidata != pasta and candidata.is_dir() else None


def carregar_anterior(entradas: Entradas, cfg: ConfigRemessa) -> Anterior | None:
    """Lê o relatório da Ponte e a planilha da competência anterior, se a pasta dela existir ao lado desta."""
    from tarvo.cli import ErroEntrada, localizar_pela_config
    from tarvo.leitores.ponte import ler_ponte
    from tarvo.leitores.taxas import ler_taxas

    pasta = pasta_anterior(entradas.arquivos["ponte_eml"].parent, entradas.competencia)
    if pasta is None:
        return None
    try:
        arquivos = localizar_pela_config(pasta)  # com os tipos múltiplos (a Orbe pode ter relatório e ajustes, O05)
    except ErroEntrada:
        return None  # pasta sem os arquivos esperados: não há com que conferir
    competencia = competencia_anterior(entradas.competencia)
    try:
        ponte, meta = ler_ponte(arquivos["ponte_eml"], rejeitadas=[])
        taxas = ler_taxas(arquivos["taxas"], rejeitadas=[])
    except (ValueError, OSError) as e:
        raise ErroDadoRemessa(dep.ANTERIOR, f"relatório da Ponte ou planilha da competência anterior ({pasta.name}) "
                              f"ilegível: {e}") from None
    unicas, _ = deduplicar(ponte, cfg, [])
    operacoes, _ = separar_ajustes(unicas, cfg, [])
    itens = calcular_remessa(ponte, taxas, competencia, meta["arquivo_origem"], cfg)
    contestadas = frozenset(i.campos["ref_origem"] for i in itens
                            if i.id_saida.startswith(("DIV-REM-", "PEN-NEG-REM-", "PEN-DUP-REM-")))
    return Anterior(competencia, meta["arquivo_origem"], {o["ref_origem"]: o for o in operacoes}, contestadas)


def na_competencia(op: dict, competencia: str) -> bool:
    return _obrigatorio(op, "data_contratacao").strftime("%Y-%m") == competencia  # R11


# ---------------------------------------------------------------- itens de saída

def _soma(valores) -> Decimal:
    return sum(valores, ZERO)


def _rs(v: Decimal) -> str:
    """"R$ 1.234,50"; negativo vira "-R$ 1.234,50" (texto de motivo)."""
    return f"{'-' if v < 0 else ''}R$ {brl(abs(v))}"


def _pendencia(id_saida: str, tipo: str, refs, motivo: str, valor: Decimal, origens, cfg: ConfigRemessa,
               quem_decide: str | None = None) -> ItemSaida:
    return ItemSaida(id_saida, PENDENCIAS.nome,
                     {"tipo": tipo, "ref_origem": refs, "motivo": texto_saida(motivo),
                      "quem_decide": quem_decide or cfg.quem_decide},
                     valor, origens)


def _pp(v: Decimal) -> str:
    """Spread em pontos percentuais como texto do rastro: 1.4991 vira "1,4991"."""
    return format(v.normalize() if v != 0 else v, "f").replace(".", ",")


def _origem_comissao(o: OperacaoRemessa, cfg: ConfigRemessa) -> tuple:
    """Linha do rastro da comissão de uma operação: R11, a parte da Tarvo no Spread R$ realizado (O06)."""
    return (o.arquivo_origem, o.ref_origem, o.comissao, "R11",
            f"{_pp(cfg.participacao * 100)}% do Spread R$ {brl(o.spread_brl)} realizado (spread {_pp(o.spread_pct)}%)")


def _origem_ajuste(a: AjusteRemessa) -> tuple:
    return (a.arquivo_origem, a.ref_origem, a.comissao, "R31", texto_saida(f"ajuste Ponte {a.descricao}"))


def _origem_diferenca(o: OperacaoRemessa, regra: str) -> tuple:
    """Linha do rastro da diferença até o contrato (R15; P17, P18), com os dois spreads (O06)."""
    return (o.arquivo_origem, o.ref_origem, o.diferenca, regra,
            f"spread aplicado {_pp(o.spread_pct)}% - contratado {_pp(o.spread_contratado)}% sobre PTAX × valor ME")


def _rascunho_ponte() -> str:
    """Onde fica o rascunho de contestação da Ponte (R29), como o motivo da pendência o cita: <pasta>/ponte.md."""
    from tarvo.contestacao import ARQUIVO_PONTE, carregar_config  # import tardio: contestacao importa este módulo
    return f"{carregar_config().pasta}/{ARQUIVO_PONTE[0]}"


def gerar_itens(operacoes: list[OperacaoRemessa], descartadas: list[dict], fora: list[dict],
                nomes: dict[str, str], competencia: str, arquivo_ponte: str, cfg: ConfigRemessa,
                ajustes: list[AjusteRemessa] = ()) -> list[ItemSaida]:
    """nomes: CNPJ -> nome do lojista (planilha; para CNPJ fora dela, o cliente da Ponte)."""
    itens: list[ItemSaida] = []
    por_cnpj: dict[str, list[OperacaoRemessa]] = defaultdict(list)
    for op in operacoes:
        por_cnpj[op.cnpj].append(op)
    sem_lojista = [a for a in ajustes if a.cnpj is None]
    ajustes = [a for a in ajustes if a.cnpj is not None]
    ajuste_por_cnpj: dict[str, list[AjusteRemessa]] = defaultdict(list)
    for a in sorted(ajustes, key=lambda a: a.ref_origem):
        ajuste_por_cnpj[a.cnpj].append(a)

    rastro_nota = []
    for cnpj in sorted(set(por_cnpj) | set(ajuste_por_cnpj)):
        doc = sorted(por_cnpj.get(cnpj, []), key=lambda o: o.ref_origem)
        com_comissao = [o for o in doc if o.comissao is not None]
        rastro = [_origem_comissao(o, cfg) for o in com_comissao]
        rastro_com = list(rastro)
        for a in ajuste_por_cnpj.get(cnpj, []):  # R31, P25: o ajuste abate a participação do mês
            rastro_com.append((a.arquivo_origem, a.ref_origem, a.comissao, "R31",
                               texto_saida(f"ajuste Ponte {a.descricao} - {_pp(cfg.ajuste_participacao * 100)}% do "
                                           f"Spread R$ {brl(a.spread_brl)} (P25)")))
            if a.arquivo_original:  # a original, de outro relatório, vai no rastro com valor zero
                rastro_com.append((a.arquivo_original, a.ref_original, ZERO, "R31",
                                   f"operação original do ajuste {a.ref_origem}, valor 0,00"))
        if rastro_com:
            itens.append(ItemSaida(f"COM-REM-{cnpj}", COMISSOES.nome,
                                   {"cnpj": cnpj, "lojista": texto_saida(nomes[cnpj]), "linha_negocio": LINHA_NEGOCIO},
                                   _soma(o[2] for o in rastro_com), rastro_com))
            rastro_nota.extend(rastro_com)

        if doc and not doc[0].cadastrado and com_comissao:
            itens.append(_pendencia(f"PEN-NAOCAD-REM-{cnpj}", "LOJISTA_NAO_CADASTRADO",
                                    [o.ref_origem for o in com_comissao], MOTIVO_NAO_CADASTRADO,
                                    _soma(o.comissao for o in com_comissao), rastro, cfg, cfg.quem_decide_cadastro))

        # R23: spread negativo não é divergência (o lojista não pagou a mais); fica só na PEN-NEG abaixo
        for o in (o for o in doc if o.divergente and not o.negativa):  # R15, P01
            itens.append(ItemSaida(f"DIV-REM-{o.ref_origem}", DIVERGENCIAS.nome,
                                   {"cnpj": cnpj, "linha_negocio": LINHA_NEGOCIO, "ref_origem": o.ref_origem,
                                    "taxa_contratada_pct": o.spread_contratado, "taxa_aplicada_pct": o.spread_pct},
                                   o.diferenca, [_origem_diferenca(o, "R15")]))

        acima = [o for o in doc if o.divergente and not o.negativa and o.diferenca > 0]
        if acima:  # R16, R18
            itens.append(_pendencia(f"PEN-CONTEST-REM-{cnpj}", "CONTESTACAO_PONTE",
                                    [o.ref_origem for o in acima], MOTIVO_CONTESTACAO,
                                    _soma(o.diferenca for o in acima),
                                    [_origem_diferenca(o, "R15") for o in acima], cfg))

        for o in (o for o in doc if o.negativa):  # R12, R18, R23, R34, P18: o valor é a diferença até o contrato
            motivo = MOTIVO_NEGATIVO.format(spread=_rs(o.spread_brl), diferenca=_rs(o.diferenca),
                                            rascunho=_rascunho_ponte())
            itens.append(_pendencia(f"PEN-NEG-REM-{o.ref_origem}", "CONTESTACAO_PONTE", o.ref_origem,
                                    motivo, o.diferenca, [_origem_diferenca(o, "R34")], cfg))

    copias: dict[str, list[dict]] = defaultdict(list)
    for d in descartadas:
        copias[d["ref_origem"]].append(d)
    for ref in sorted(copias):  # R13
        origens = [(d["arquivo_origem"], d["ref_origem"], d["spread_brl"], "R13",
                    f"Spread R$ da cópia descartada (linha {d['linha_planilha']} do relatório) - contada uma vez")
                   for d in copias[ref]]
        itens.append(_pendencia(f"PEN-DUP-REM-{ref}", "OPERACAO_DUPLICADA", ref, MOTIVO_DUPLICATA,
                                _soma(o[2] for o in origens), origens, cfg))

    for op in sorted(fora, key=lambda o: o["ref_origem"]):  # R11
        itens.append(_pendencia(f"PEN-FORA-REM-{op['ref_origem']}", "OPERACAO_FORA_DA_COMPETENCIA", op["ref_origem"],
                                MOTIVO_FORA_COMPETENCIA.format(competencia=competencia), op["spread_brl"],
                                [(op["arquivo_origem"], op["ref_origem"], op["spread_brl"], "R11",
                                  f"Spread R$ da operação contratada em {op['data_contratacao'].isoformat()}, fora "
                                  f"da competência {competencia}")], cfg))

    for a in sorted(sem_lojista, key=lambda a: a.ref_origem):  # R31: sem lojista não há COM-REM; não abate
        itens.append(_pendencia(f"PEN-AJUSTE-SEMLOJISTA-{a.ref_origem}", "AJUSTE_SEM_LOJISTA", a.ref_origem,
                                MOTIVO_AJUSTE_SEM_LOJISTA.format(original=a.ref_original),
                                a.comissao, [_origem_ajuste(a)], cfg))
    for a in sorted(ajustes, key=lambda a: a.ref_origem):  # R31: sem a original, abate mesmo assim e avisa a Helena
        if a.sem_original:
            itens.append(_pendencia(f"PEN-AJUSTE-SEMORIG-{a.ref_origem}", "AJUSTE_SEM_OPERACAO_ORIGINAL", a.ref_origem,
                                    MOTIVO_AJUSTE_SEM_ORIGINAL.format(original=a.ref_original, anterior=a.anterior),
                                    a.comissao, [_origem_ajuste(a)], cfg))

    total = _soma(o[2] for o in rastro_nota)
    refs_nota = [o[1] for o in rastro_nota] or arquivo_ponte
    discriminacao = cfg.discriminacao_nota.format(competencia=competencia)
    if ajustes:  # R31: a descrição do ajuste (e a referência à original) acompanha a nota
        discriminacao += " - líquida de ajuste da Ponte: " + "; ".join(
            a.descricao for a in sorted(ajustes, key=lambda a: a.ref_origem))
    if total > 0:  # R16, R17: uma nota, tomadora Ponte, pelo realizado (R31: líquido dos ajustes)
        itens.append(ItemSaida(f"NF-REM-{cfg.tomador_cnpj}", NOTAS.nome,
                               {"tomador_cnpj": cfg.tomador_cnpj, "tomador": texto_saida(cfg.tomador_nome),
                                "linha_negocio": LINHA_NEGOCIO, "discriminacao": texto_saida(discriminacao)},
                               total, rastro_nota))
    else:
        itens.append(_pendencia(f"PEN-NF-REM-{cfg.tomador_cnpj}", "NOTA_NAO_EMITIDA", refs_nota,
                                MOTIVO_NOTA_NAO_EMITIDA_AJUSTE if ajustes else MOTIVO_NOTA_NAO_EMITIDA,
                                total, rastro_nota, cfg))

    # R18: o TED é conferido contra a nota (mesmo valor e mesmas operações); nenhum desconto é suposto
    itens.append(_pendencia("PEN-TED-PONTE", "CONFERENCIA_REPASSE", refs_nota, MOTIVO_TED, total, rastro_nota, cfg))
    return itens


EFEITO_LOJISTA = ("as {n} operações do lojista (CNPJ {cnpj}) ficaram fora de comissão, nota da Ponte e divergência; "
                  "a nota da Ponte saiu PROVISÓRIA - valor = Spread R$ delas")
EFEITO_OPERACAO = ("a operação ficou fora de comissão, nota da Ponte e divergência; a nota da Ponte saiu PROVISÓRIA - "
                   "valor = Spread R$ da operação")
EFEITO_DUPLICADA = ("as {n} cópias ficaram fora de comissão, nota da Ponte, divergência e das conferências P11 e P12; a "
                    "nota da Ponte saiu PROVISÓRIA - valor 0,00: o fechamento não escolhe qual cópia vale")
EFEITO_ANTERIOR = ("os ajustes da Ponte (R31) foram conferidos sem a competência anterior: a original de cada ajuste "
                   "fica como não encontrada - nenhum valor muda")
ITENS_DA_NOTA = ("NF-REM-", "PEN-NF-REM-", "PEN-TED-PONTE")


def _spread(op: dict) -> Decimal:
    return op["spread_brl"] if op.get("spread_brl") is not None else ZERO


def _pendencias_regra(problemas: list[ProblemaRemessa], conflitos: list[Conflito],
                      fora: dict[str, list[dict]]) -> list[ItemSaida]:
    """R44: PEN-REGRA-<tipo>-REM-<CNPJ> por lojista com contrato que impede a regra (todas as operações dele),
    PEN-REGRA-<tipo>-REM-<Nº> por operação e PEN-REGRA-DUPLICADA-REM-<Nº> por Nº repetido com valores diferentes."""
    itens = []
    do_lojista: dict[str, list[ProblemaRemessa]] = defaultdict(list)
    for p in problemas:
        if p.erro.do_lojista or p.chave in fora:
            do_lojista[p.chave].append(p)
            continue
        itens.append(dep.pendencia_regra(p.erro.tipo, f"REM-{p.op['ref_origem']}", str(p.erro), EFEITO_OPERACAO,
                                         _spread(p.op), [(p.op["arquivo_origem"], p.op["ref_origem"], _spread(p.op))]))
    for cnpj, ps in sorted(do_lojista.items()):
        ops = {o["ref_origem"]: o for o in [p.op for p in ps] + fora.get(cnpj, [])}
        origens = [(o["arquivo_origem"], o["ref_origem"], _spread(o)) for _, o in sorted(ops.items())]
        itens.append(dep.pendencia_regra(ps[0].erro.tipo, f"REM-{cnpj}",
                                         " | ".join(dict.fromkeys(str(p.erro) for p in ps)),
                                         EFEITO_LOJISTA.format(n=len(origens), cnpj=cnpj),
                                         _soma(o[2] for o in origens), origens))
    for c in sorted(conflitos, key=lambda c: c.ref_origem):
        itens.append(dep.pendencia_regra(dep.DUPLICADA, f"REM-{c.ref_origem}", c.mensagem,
                                         EFEITO_DUPLICADA.format(n=len(c.copias)), ZERO,
                                         [(o["arquivo_origem"], o["ref_origem"], ZERO) for o in c.copias]))
    return itens


def calcular_remessa(ponte: pd.DataFrame, taxas: pd.DataFrame, competencia: str, arquivo_ponte: str,
                     cfg: ConfigRemessa, anterior: Anterior | None = None, rejeitadas_taxas=(),
                     provisorio: bool = False) -> list[ItemSaida]:
    """Itens da remessa. Lojista ou operação com dado que impede a regra fica fora e vira PEN-REGRA (R44); aí a nota
    da Ponte (e a conferência do TED) sai provisória, como quando provisorio=True (linha rejeitada pelo leitor)."""
    contratos = Contratos(taxas, cfg, rejeitadas_taxas)
    problemas: list[ProblemaRemessa] = []
    conflitos: list[Conflito] = []
    unicas, descartadas = deduplicar(ponte, cfg, conflitos)
    operacoes_todas, ajustes_todos = separar_ajustes(unicas, cfg, problemas)  # R31 vem antes da R23

    def no_mes(op: dict) -> bool | None:
        try:
            return na_competencia(op, competencia)
        except dep.ErroDado as e:
            problemas.append(ProblemaRemessa(e, op, op["cnpj"] or op["ref_origem"]))
            return None

    meses = {op["ref_origem"]: no_mes(op) for op in operacoes_todas + ajustes_todos}
    validas = [op for op in operacoes_todas if meses[op["ref_origem"]]]
    ajustes_mes = [op for op in ajustes_todos if meses[op["ref_origem"]]]
    fora = [op for op in unicas if meses.get(op["ref_origem"]) is False]
    operacoes = []
    for op in validas:
        try:
            operacoes.append(calcular_operacao(op, contratos, cfg))
        except dep.ErroDado as e:
            problemas.append(ProblemaRemessa(e, op, op["cnpj"] or op["ref_origem"]))
    por_ref = {op["ref_origem"]: op for op in operacoes_todas}
    ajustes, ajustes_ok = [], []
    for op in ajustes_mes:
        try:
            ajustes.append(calcular_ajuste(op, referencia_ajuste(op, cfg), por_ref, cfg, anterior))
            ajustes_ok.append(op)
        except dep.ErroDado as e:
            problemas.append(ProblemaRemessa(e, op, op["cnpj"] or op["ref_origem"]))

    lojistas_fora = {p.chave for p in problemas if p.erro.do_lojista}
    do_lojista_fora: dict[str, list[dict]] = defaultdict(list)
    for o in operacoes:
        if o.cnpj in lojistas_fora:
            do_lojista_fora[o.cnpj].append(por_ref[o.ref_origem])
    for a, op in zip(ajustes, ajustes_ok):
        if a.cnpj in lojistas_fora:
            do_lojista_fora[a.cnpj].append(op)
    operacoes = [o for o in operacoes if o.cnpj not in lojistas_fora]
    pares = [(a, op) for a, op in zip(ajustes, ajustes_ok) if a.cnpj not in lojistas_fora]
    ajustes = [a for a, _ in pares]

    nomes = {}
    for o in operacoes:
        op = por_ref[o.ref_origem]
        if contratos.cadastrado(o.cnpj):
            nomes[o.cnpj] = contratos.nome(o.cnpj)
        else:  # só exibição: o casamento foi pelo CNPJ (sem o nome do cliente, o próprio CNPJ)
            nomes.setdefault(o.cnpj, op["cliente"] or o.cnpj)
    for a, op in pares:
        if a.cnpj is not None and a.cnpj not in nomes:
            nomes[a.cnpj] = contratos.nome(a.cnpj) if contratos.cadastrado(a.cnpj) else (op["cliente"] or a.cnpj)
    refs_fora = {p.op["ref_origem"] for p in problemas} | {o["ref_origem"] for ops in do_lojista_fora.values() for o in ops}
    descartadas = [d for d in descartadas if d["ref_origem"] not in refs_fora]  # a cópia de quem ficou fora não é PEN-DUP
    itens = gerar_itens(operacoes, descartadas, fora, nomes, competencia, arquivo_ponte, cfg, ajustes)
    pendencias = _pendencias_regra(problemas, conflitos, {c: do_lojista_fora.get(c, []) for c in lojistas_fora})
    if pendencias or provisorio:  # a nota da Ponte é uma só: sem uma operação, ela e o TED ficam provisórios
        cnpjs_linha = {p.chave for p in problemas if p.chave not in lojistas_fora}
        alvo = [i for i in itens if i.id_saida.startswith(ITENS_DA_NOTA) or i.id_saida.rsplit("-", 1)[-1] in cnpjs_linha]
        marcados = {i.id_saida: i for i in dep.marcar_provisorio(alvo)}
        itens = [marcados.get(i.id_saida, i) for i in itens]
    return itens + pendencias


def remessa(entradas: Entradas, config=CONFIG_REMESSA) -> list[ItemSaida]:
    """Módulo do fechamento: itens da linha REMESSA a partir da Ponte e da planilha de taxas.

    Sem uma das duas (fonte bloqueada), não gera nada (R44)."""
    if not dep.gera("remessa", entradas):
        return []
    cfg = carregar_config(config)
    extra: list[ItemSaida] = []
    try:
        anterior = carregar_anterior(entradas, cfg)
    except dep.ErroDado as e:  # R44: sem a competência anterior, o ajuste é conferido só com o mês
        anterior = None
        extra = [dep.pendencia_regra(e.tipo, "REM", str(e), EFEITO_ANTERIOR, ZERO,
                                     [(entradas.competencia, "competencia anterior", ZERO)])]
    rejeitadas = entradas.rejeitadas.get("ponte_eml", ())
    itens = calcular_remessa(entradas.ponte, entradas.taxas, entradas.competencia,
                             entradas.ponte_rodape["arquivo_origem"], cfg, anterior,
                             entradas.rejeitadas.get("taxas", ()), provisorio=bool(rejeitadas))
    if rejeitadas:  # R44: a linha rejeitada pelo leitor deixa a comissão do lojista dela provisória
        cnpjs = {r.cnpj for r in rejeitadas if r.cnpj}
        itens = [dep.marcar_provisorio([i])[0] if i.id_saida.rsplit("-", 1)[-1] in cnpjs else i for i in itens]
    itens += extra
    return dep.marcar_provisorio(itens) if dep.provisorio("remessa", entradas) else itens
