"""Extratos bancários (Aurora e Meridiano): classificação contábil, conferências cruzadas e pendências.

Regras do HIPOTESES.md: R19 a R21; premissas P06 a P13. Regras em config/bancos.yaml; lojistas dos PIX em
config/favorecidos.yaml (Aurora) e config/pagadores_meridiano.yaml (Meridiano).
O lojista de um PIX é identificado só pela lista explícita (texto exato do extrato -> CNPJ); a Ponte é casada
com os PIX pelo CNPJ. Sem IA: o que nenhuma regra cobre fica com metodo HUMANO e vira pendência.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
import yaml

from tarvo.leitores.comum import dinheiro
from tarvo.remessa import carregar_config as carregar_config_remessa
from tarvo.remessa import deduplicar, na_competencia
from tarvo.saida import LANCAMENTOS, PENDENCIAS, ItemSaida

if TYPE_CHECKING:
    from tarvo.fechamento import Entradas

PASTA_CONFIG = Path(__file__).resolve().parents[2] / "config"
CONFIG_BANCOS = PASTA_CONFIG / "bancos.yaml"
CONFIG_FAVORECIDOS = PASTA_CONFIG / "favorecidos.yaml"
CONFIG_PAGADORES = PASTA_CONFIG / "pagadores_meridiano.yaml"
ZERO = Decimal("0.00")

AURORA, MERIDIANO = "AURORA", "MERIDIANO"
PREFIXO_ID = {AURORA: "AUR", MERIDIANO: "MER"}
SENTIDOS = ("C", "D")
GRUPO_CONTRAPARTE = "contraparte"
# nome da lista usado nas regras -> chave de topo do YAML da lista
LISTAS = {"favorecidos": "favorecidos", "pagadores": "pagadores"}
PAPEIS = ("transferencia_enviada", "transferencia_recebida", "ted_liquidacao", "pix_cliente",
          "credito_nao_identificado", "devolucao_pix")
MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
         "outubro", "novembro", "dezembro")

MOTIVO_NAO_IDENTIFICADO = "PIX recebido sem identificação: não é receita até identificar a origem (R20)"
MOTIVO_DEVOLUCAO = "devolução de PIX: repasse que voltou, motivo desconhecido (R20); apurar o motivo (P06)"
MOTIVO_SEM_REGRA = "nenhuma regra de config/bancos.yaml cobre o lançamento: classificar manualmente (P09)"
MOTIVO_TED_LIQ = (
    "TEDs LIQ OPERACOES do dia diferentes de valor_brl + iof_brl das operações únicas da Ponte contratadas "
    "no dia (P11); valor = operações - TEDs pagas"
)
MOTIVO_PIX_SEM_REMESSA = (
    "PIX do cliente sem operação correspondente da Ponte no mês: a soma dos PIX excede a das operações "
    "exatamente neste valor (P12)"
)
MOTIVO_PIX_DIFERENCA = (
    "soma dos PIX do cliente no mês diferente de valor_brl + iof_brl das operações únicas da Ponte no mês, "
    "sem um PIX único que explique a diferença (P12); valor = PIX - operações"
)
MOTIVO_TRANSITO = (
    "transferência entre contas sem TED de mesma titularidade no Meridiano até {fim}: pela R20 cai no "
    "Meridiano em {chegada}; conferir no extrato de {mes}"
)
MOTIVO_SEM_PAR = (
    "transferência entre contas sem TED de mesma titularidade e mesmo valor no Meridiano na mesma data "
    "nem no dia útil seguinte (P13)"
)


class ErroBancos(ValueError):
    """Dado de entrada ou configuração que impede classificar os extratos."""


# ---------------------------------------------------------------- configuração

@dataclass(frozen=True)
class Contraparte:
    """Lojista de um PIX, pela lista explícita. cnpj None só para quem não tem CNPJ na planilha (R08)."""

    cnpj: str | None
    ec: str | None
    sem_contrato: bool


@dataclass(frozen=True)
class Regra:
    padrao: re.Pattern
    sentido: str
    conta_codigo: str
    confianca: Decimal
    fonte: str
    lista: str | None
    papel: str | None


@dataclass(frozen=True)
class ConfigBancos:
    regras: dict[str, tuple[Regra, ...]]
    listas: dict[str, dict[str, Contraparte]]
    confianca_pix_sem_remessa: Decimal
    conta_sem_regra: str
    confianca_sem_regra: Decimal
    quem_decide: str


def _str_cfg(v, campo: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise ErroBancos(f"config: {campo} deveria ser texto entre aspas, veio {v!r}")
    return v


def _confianca_cfg(v, campo: str) -> Decimal:
    c = Decimal(_str_cfg(v, campo))
    if not ZERO <= c <= 1 or c != c.quantize(Decimal("0.01")):
        raise ErroBancos(f"config: {campo} deveria ser de 0 a 1 com 2 casas, veio {v!r}")
    return c


def _ler_yaml(caminho) -> dict:
    with open(caminho, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _contas_lancaveis(plano: pd.DataFrame) -> set[str]:
    return {r["cod_conta"] for r in plano.to_dict("records") if r["aceita_lancto"]}


def _regra(bruto: dict, campo: str, contas: set[str]) -> Regra:
    try:
        padrao = re.compile(_str_cfg(bruto.get("padrao"), f"{campo}.padrao"))
    except re.error as e:
        raise ErroBancos(f"config: {campo}.padrao não é regex válida ({e})") from None
    sentido = bruto.get("sentido")
    if sentido not in SENTIDOS:
        raise ErroBancos(f"config: {campo}.sentido deveria ser {'|'.join(SENTIDOS)}, veio {sentido!r}")
    conta = _str_cfg(bruto.get("conta_codigo"), f"{campo}.conta_codigo")
    if conta not in contas:
        raise ErroBancos(f"config: {campo}.conta_codigo {conta!r} não existe no plano de contas ou não aceita lançamento")
    fonte = _str_cfg(bruto.get("fonte"), f"{campo}.fonte")
    if not re.fullmatch(r"[RP][0-9]{2}", fonte):
        raise ErroBancos(f"config: {campo}.fonte deveria ser R## ou P##, veio {fonte!r}")
    lista = bruto.get("lista")
    if lista is not None and lista not in LISTAS:
        raise ErroBancos(f"config: {campo}.lista {lista!r} não é uma de {sorted(LISTAS)}")
    if (lista is not None) != (GRUPO_CONTRAPARTE in padrao.groupindex):
        raise ErroBancos(f"config: {campo}: regra com lista precisa do grupo (?P<{GRUPO_CONTRAPARTE}>...) e vice-versa")
    papel = bruto.get("papel")
    if papel is not None and papel not in PAPEIS:
        raise ErroBancos(f"config: {campo}.papel {papel!r} não é um de {PAPEIS}")
    return Regra(padrao, sentido, conta, _confianca_cfg(bruto.get("confianca"), f"{campo}.confianca"),
                 fonte, lista, papel)


def _contrapartes(bruto: dict, nome: str, cnpjs_planilha: set[str]) -> dict[str, Contraparte]:
    if not isinstance(bruto, dict) or not bruto:
        raise ErroBancos(f"config: lista {nome} vazia ou ausente")
    lista = {}
    for texto, v in bruto.items():
        campo = f"{nome}[{texto!r}]"
        _str_cfg(texto, campo)
        if texto != texto.strip():
            raise ErroBancos(f"config: {campo}: o texto não pode ter espaço nas pontas")
        cnpj, ec, sem_contrato = v.get("cnpj"), v.get("ec"), v.get("sem_contrato", False)
        if cnpj is not None:
            if not isinstance(cnpj, str) or not re.fullmatch(r"[0-9]{14}", cnpj):
                raise ErroBancos(f"config: {campo}.cnpj deveria ser texto com 14 dígitos, veio {cnpj!r}")
            if cnpj not in cnpjs_planilha:
                raise ErroBancos(f"config: {campo}.cnpj {cnpj} não está na planilha de taxas")
            if sem_contrato:
                raise ErroBancos(f"config: {campo}: com CNPJ da planilha não pode ser sem_contrato")
        elif not (isinstance(ec, str) and ec.isdigit() and sem_contrato is True):
            raise ErroBancos(f"config: {campo}: sem cnpj, precisa de ec (texto com dígitos) e sem_contrato: true")
        lista[texto] = Contraparte(cnpj, ec, bool(sem_contrato))
    return lista


def carregar_config(plano: pd.DataFrame, taxas: pd.DataFrame, caminho=CONFIG_BANCOS,
                    favorecidos=CONFIG_FAVORECIDOS, pagadores=CONFIG_PAGADORES) -> ConfigBancos:
    """Lê as regras e as listas. Falha se uma conta não existir no plano ou não aceitar lançamento,
    ou se um CNPJ das listas não estiver na planilha de taxas."""
    bruto = _ler_yaml(caminho)
    contas = _contas_lancaveis(plano)
    regras = {}
    for banco in PREFIXO_ID:
        lista = (bruto.get("regras") or {}).get(banco)
        if not lista:
            raise ErroBancos(f"config: regras.{banco} vazia ou ausente")
        regras[banco] = tuple(_regra(r, f"regras.{banco}[{i}]", contas) for i, r in enumerate(lista))
    cnpjs = set(taxas["cnpj"])
    listas = {
        "favorecidos": _contrapartes(_ler_yaml(favorecidos).get(LISTAS["favorecidos"]), "favorecidos", cnpjs),
        "pagadores": _contrapartes(_ler_yaml(pagadores).get(LISTAS["pagadores"]), "pagadores", cnpjs),
    }
    sem_cnpj = [t for t, c in listas["pagadores"].items() if c.cnpj is None]
    if sem_cnpj:
        raise ErroBancos(f"config: pagadores sem CNPJ não podem ser conferidos com a Ponte: {sem_cnpj}")
    sem_regra = bruto.get("sem_regra") or {}
    return ConfigBancos(
        regras=regras,
        listas=listas,
        confianca_pix_sem_remessa=_confianca_cfg(bruto.get("confianca_pix_sem_remessa"), "confianca_pix_sem_remessa"),
        conta_sem_regra=_str_cfg(sem_regra.get("conta_codigo"), "sem_regra.conta_codigo"),
        confianca_sem_regra=_confianca_cfg(sem_regra.get("confianca"), "sem_regra.confianca"),
        quem_decide=_str_cfg(bruto.get("quem_decide"), "quem_decide"),
    )


# ---------------------------------------------------------------- classificação (R19 a R21)

@dataclass(frozen=True)
class Lancamento:
    banco: str
    arquivo_origem: str
    ref_origem: str
    data: date
    descricao: str
    valor: Decimal
    regra: Regra | None          # None: nenhuma regra cobre (P09)
    contraparte: Contraparte | None

    @property
    def id_saida(self) -> str:
        return f"LAN-{PREFIXO_ID[self.banco]}-{self.ref_origem}"

    @property
    def papel(self) -> str | None:
        return self.regra.papel if self.regra else None

    def origem(self, valor: Decimal | None = None) -> tuple[str, str, Decimal]:
        return (self.arquivo_origem, self.ref_origem, self.valor if valor is None else valor)


def _casar(regra: Regra, texto: str, valor: Decimal, cfg: ConfigBancos) -> tuple[bool, Contraparte | None]:
    if (regra.sentido == "C" and not valor > 0) or (regra.sentido == "D" and not valor < 0):
        return False, None
    m = regra.padrao.search(texto)
    if not m:
        return False, None
    if regra.lista is None:
        return True, None
    contraparte = cfg.listas[regra.lista].get(m.group(GRUPO_CONTRAPARTE))  # texto exato (P07, P08)
    return contraparte is not None, contraparte


def classificar(banco: str, linhas: list[dict], cfg: ConfigBancos) -> list[Lancamento]:
    """linhas: dicts com arquivo_origem, ref_origem, data, descricao, valor. A primeira regra que casa vence."""
    lancamentos = []
    for linha in linhas:
        texto, valor = linha["descricao"], linha["valor"]
        if not isinstance(texto, str) or not texto.strip():
            raise ErroBancos(f"{linha['ref_origem']}: lançamento sem descrição")
        escolhida, contraparte = None, None
        for regra in cfg.regras[banco]:
            casou, contraparte = _casar(regra, texto, valor, cfg)
            if casou:
                escolhida = regra
                break
        lancamentos.append(Lancamento(banco, linha["arquivo_origem"], linha["ref_origem"], linha["data"],
                                      texto, valor, escolhida, contraparte if escolhida else None))
    return lancamentos


def _linhas(df: pd.DataFrame, coluna_texto: str) -> list[dict]:
    return [{"arquivo_origem": r["arquivo_origem"], "ref_origem": r["ref_origem"], "data": r["data"],
             "descricao": r[coluna_texto], "valor": r["valor"]} for r in df.to_dict("records")]


def item_lancamento(l: Lancamento, cfg: ConfigBancos, sem_remessa: set[str]) -> ItemSaida:
    if l.regra is None:  # P09
        conta, metodo, confianca = cfg.conta_sem_regra, "HUMANO", cfg.confianca_sem_regra
    else:
        conta, metodo, confianca = l.regra.conta_codigo, "REGRA", l.regra.confianca
        if l.ref_origem in sem_remessa:  # P10
            confianca = min(confianca, cfg.confianca_pix_sem_remessa)
    return ItemSaida(l.id_saida, LANCAMENTOS.nome,
                     {"banco": l.banco, "ref_origem": l.ref_origem, "data": l.data, "descricao": l.descricao,
                      "conta_codigo": conta, "metodo": metodo, "confianca": confianca},
                     l.valor, [l.origem()])


# ---------------------------------------------------------------- pendências

def _soma(valores) -> Decimal:
    return sum(valores, ZERO)


def _pendencia(id_saida: str, tipo: str, refs, motivo: str, valor: Decimal, origens, cfg: ConfigBancos) -> ItemSaida:
    return ItemSaida(id_saida, PENDENCIAS.nome,
                     {"tipo": tipo, "ref_origem": refs, "motivo": motivo, "quem_decide": cfg.quem_decide},
                     valor, origens)


def pendencias_lancamentos(lancamentos: list[Lancamento], cfg: ConfigBancos) -> list[ItemSaida]:
    """R20 (PIX sem identificação, devolução de PIX) e P09 (lançamento sem regra)."""
    itens = []
    for l in lancamentos:
        if l.regra is None:
            itens.append(_pendencia(f"PEN-SEMREGRA-{l.ref_origem}", "LANCAMENTO_SEM_REGRA", l.ref_origem,
                                    MOTIVO_SEM_REGRA, l.valor, [l.origem()], cfg))
        elif l.papel == "credito_nao_identificado":
            itens.append(_pendencia(f"PEN-NAOID-{l.ref_origem}", "CREDITO_NAO_IDENTIFICADO", l.ref_origem,
                                    MOTIVO_NAO_IDENTIFICADO, l.valor, [l.origem()], cfg))
        elif l.papel == "devolucao_pix":
            itens.append(_pendencia(f"PEN-DEVOL-PIX-{l.ref_origem}", "DEVOLUCAO_PIX", l.ref_origem,
                                    MOTIVO_DEVOLUCAO, l.valor, [l.origem()], cfg))
    return itens


# ---------------------------------------------------------------- conferências cruzadas

def _valor_operacao(op: dict) -> Decimal:
    """valor_brl + iof_brl: o que o cliente paga e a Tarvo liquida com a Ponte pela operação."""
    for campo in ("valor_brl", "iof_brl"):
        if op[campo] is None:
            raise ErroBancos(f"{op['ref_origem']}: {campo} vazio")
    return dinheiro(op["valor_brl"] + op["iof_brl"])


def _origem_op(op: dict, sinal: int) -> tuple[str, str, Decimal]:
    return (op["arquivo_origem"], op["ref_origem"], _valor_operacao(op) * sinal)


def conferir_ted_liquidacao(meridiano: list[Lancamento], unicas: list[dict], inicio: date, fim: date,
                            cfg: ConfigBancos) -> list[ItemSaida]:
    """P11: por data, TEDs LIQ OPERACOES (com sinal) + operações únicas contratadas no dia = 0."""
    teds: dict[date, list[Lancamento]] = defaultdict(list)
    for l in meridiano:
        if l.papel == "ted_liquidacao":
            teds[l.data].append(l)
    ops: dict[date, list[dict]] = defaultdict(list)
    for op in unicas:
        d = op["data_contratacao"]
        if d is None:
            raise ErroBancos(f"{op['ref_origem']}: data_contratacao vazia")
        if inicio <= d <= fim:  # só o período do extrato
            ops[d].append(op)

    itens = []
    for d in sorted(set(teds) | set(ops)):
        origens = [l.origem() for l in teds[d]] + [_origem_op(op, +1) for op in sorted(ops[d], key=lambda o: o["ref_origem"])]
        diferenca = _soma(o[2] for o in origens)
        if diferenca != 0:
            itens.append(_pendencia(f"PEN-TED-LIQ-{d.isoformat()}", "DIVERGENCIA_TED_LIQUIDACAO",
                                    [o[1] for o in origens], MOTIVO_TED_LIQ, diferenca, origens, cfg))
    return itens


def conferir_pix_remessas(meridiano: list[Lancamento], unicas_mes: list[dict],
                          cfg: ConfigBancos) -> tuple[list[ItemSaida], set[str]]:
    """P12: por CNPJ, PIX do mês = operações únicas do mês. Devolve (pendências, FITIDs de PIX sem remessa)."""
    pix: dict[str, list[Lancamento]] = defaultdict(list)
    for l in meridiano:
        if l.papel == "pix_cliente":
            pix[l.contraparte.cnpj].append(l)
    ops: dict[str, list[dict]] = defaultdict(list)
    for op in unicas_mes:
        ops[op["cnpj"]].append(op)

    itens, sem_remessa = [], set()
    for cnpj in sorted(set(pix) | set(ops)):
        diferenca = _soma(l.valor for l in pix[cnpj]) - _soma(_valor_operacao(op) for op in ops[cnpj])
        if diferenca == 0:
            continue
        iguais = [l for l in pix[cnpj] if l.valor == diferenca]
        if len(iguais) == 1:
            l = iguais[0]
            sem_remessa.add(l.ref_origem)
            itens.append(_pendencia(f"PEN-PIX-SEMREM-{l.ref_origem}", "RECURSO_SEM_REMESSA", l.ref_origem,
                                    MOTIVO_PIX_SEM_REMESSA, l.valor, [l.origem()], cfg))
        else:
            origens = ([l.origem() for l in sorted(pix[cnpj], key=lambda l: l.ref_origem)]
                       + [_origem_op(op, -1) for op in sorted(ops[cnpj], key=lambda o: o["ref_origem"])])
            itens.append(_pendencia(f"PEN-PIX-REM-{cnpj}", "DIFERENCA_PIX_REMESSA", [o[1] for o in origens],
                                    MOTIVO_PIX_DIFERENCA, diferenca, origens, cfg))
    return itens, sem_remessa


def proximo_dia_util(d: date) -> date:
    """Dia seguinte de segunda a sexta (sem calendário de feriados, P13)."""
    d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def conferir_transferencias(aurora: list[Lancamento], meridiano: list[Lancamento], fim_meridiano: date,
                            cfg: ConfigBancos) -> list[ItemSaida]:
    """P13: cada TRANSF do Aurora casa com uma TED de mesma titularidade do Meridiano de mesmo valor,
    na mesma data ou no dia útil seguinte. Cada TED casa uma vez."""
    recebidas = [l for l in meridiano if l.papel == "transferencia_recebida"]
    usadas: set[str] = set()
    itens = []
    for env in sorted((l for l in aurora if l.papel == "transferencia_enviada"), key=lambda l: (l.data, l.ref_origem)):
        chegada = proximo_dia_util(env.data)
        candidatas = sorted(
            (r for r in recebidas
             if r.ref_origem not in usadas and r.valor == -env.valor and r.data in (env.data, chegada)),
            key=lambda r: (r.data != env.data, r.ref_origem),
        )
        if candidatas:
            usadas.add(candidatas[0].ref_origem)
            continue
        em_transito = -env.valor  # o valor que saiu do Aurora e ainda não entrou no Meridiano
        if chegada > fim_meridiano:  # R20
            tipo = "TRANSFERENCIA_EM_TRANSITO"
            motivo = MOTIVO_TRANSITO.format(fim=fim_meridiano.strftime("%d/%m"), chegada=chegada.strftime("%d/%m"),
                                            mes=MESES[chegada.month - 1])
        else:
            tipo, motivo = "TRANSFERENCIA_SEM_PAR", MOTIVO_SEM_PAR
        itens.append(_pendencia(f"PEN-TRANSF-{env.ref_origem}", tipo, env.ref_origem, motivo, em_transito,
                                [env.origem(em_transito)], cfg))
    return itens


# ---------------------------------------------------------------- módulo

def calcular_bancos(aurora: pd.DataFrame, meridiano: pd.DataFrame, meridiano_meta: dict, ponte: pd.DataFrame,
                    competencia: str, cfg: ConfigBancos, cfg_remessa) -> list[ItemSaida]:
    aur = classificar(AURORA, _linhas(aurora, "descricao"), cfg)
    mer = classificar(MERIDIANO, _linhas(meridiano, "memo"), cfg)
    inicio, fim = meridiano_meta.get("dtstart"), meridiano_meta.get("dtend")
    if inicio is None or fim is None:
        raise ErroBancos("extrato do Meridiano sem DTSTART/DTEND: não há período para as conferências")

    unicas, _ = deduplicar(ponte, cfg_remessa)  # R13: a duplicata conta uma vez
    pend_pix, sem_remessa = conferir_pix_remessas(mer, [op for op in unicas if na_competencia(op, competencia)], cfg)

    itens = [item_lancamento(l, cfg, sem_remessa) for l in aur + mer]
    itens += pendencias_lancamentos(aur + mer, cfg)
    itens += conferir_ted_liquidacao(mer, unicas, inicio, fim, cfg)
    itens += pend_pix
    itens += conferir_transferencias(aur, mer, fim, cfg)
    return itens


def bancos(entradas: Entradas, config=CONFIG_BANCOS, favorecidos=CONFIG_FAVORECIDOS,
           pagadores=CONFIG_PAGADORES) -> list[ItemSaida]:
    """Módulo do fechamento: lançamentos classificados e pendências bancárias."""
    cfg = carregar_config(entradas.plano_contas, entradas.taxas, config, favorecidos, pagadores)
    return calcular_bancos(entradas.aurora, entradas.meridiano, entradas.meridiano_meta, entradas.ponte,
                           entradas.competencia, cfg, carregar_config_remessa())
