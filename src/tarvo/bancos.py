"""Extratos bancários (Aurora e Meridiano): classificação contábil, conferências cruzadas e pendências.

Regras do HIPOTESES.md: R19 a R22; premissas P06 a P13. Regras em config/bancos.yaml; lojistas dos PIX em
config/favorecidos.yaml (Aurora) e config/pagadores_meridiano.yaml (Meridiano).
O lojista de um PIX é identificado só pela lista explícita (texto exato do extrato -> CNPJ); a Ponte é casada
com os PIX pelo CNPJ. O que nenhuma regra cobre fica com metodo HUMANO e vira pendência (P09); com o
fallback de IA (P14, tarvo.ia), recebe a conta sugerida com metodo IA e a pendência de revisão PEN-IA-<ref>.
Fechamento parcial (R44): cada extrato e cada conferência (P11 a P13) sai só com as fontes dele (tarvo.dependencias);
a conferência que perdeu um dos lados vira PEN-SEMCONF, com o que ficou sem conferir.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

import pandas as pd
import yaml

from tarvo import dependencias as dep
from tarvo import ia
from tarvo.leitores.comum import dinheiro
from tarvo.remessa import carregar_config as carregar_config_remessa
from tarvo.remessa import deduplicar, na_competencia, separar_ajustes
from tarvo.saida import LANCAMENTOS, PENDENCIAS, ItemSaida, texto_saida

if TYPE_CHECKING:
    from tarvo.fechamento import Entradas

PASTA_CONFIG = Path(__file__).resolve().parents[2] / "config"
CONFIG_BANCOS = PASTA_CONFIG / "bancos.yaml"
CONFIG_FAVORECIDOS = PASTA_CONFIG / "favorecidos.yaml"
CONFIG_PAGADORES = PASTA_CONFIG / "pagadores_meridiano.yaml"
CONFIG_IA = ia.CONFIG_IA
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

MOTIVO_NAO_IDENTIFICADO = (
    "PIX recebido sem identificação: não é receita até identificar a origem (R20) - próximo passo: o Financeiro "
    "(Helena) identifica quem mandou o PIX e reclassifica o lançamento"
)
MOTIVO_DEVOLUCAO = "devolução de PIX: repasse que voltou, motivo desconhecido (R20) - apurar o motivo (P06)"
MOTIVO_SEM_REGRA = "nenhuma regra de config/bancos.yaml cobre o lançamento: classificar manualmente (P09)"
MOTIVO_IA = (
    "nenhuma regra de config/bancos.yaml cobre o lançamento (P09) - sugestão da IA ({modelo}, {nivel} "
    "{confianca}): {justificativa} Uma pessoa revisa antes de lançar (P14)"
)
NIVEL_IA = "confiança"
NIVEL_IA_BAIXO = "baixa confiança, abaixo do limiar {limiar}:"
MOTIVO_TED_LIQ = (
    "TEDs LIQ OPERACOES do dia diferentes de valor_brl + iof_brl das operações únicas da Ponte contratadas "
    "no dia (P11) - valor = operações - TEDs pagas - próximo passo: a Helena confere as TEDs do dia com as operações "
    "da Ponte e apura a diferença (P11)"
)
MOTIVO_PIX_DIFERENCA = (
    "soma dos PIX do cliente no mês menor que valor_brl + iof_brl das operações únicas da Ponte no mês: "
    "remessa sem o dinheiro do cliente (P12) - valor = PIX - operações - próximo passo: a Helena apura de onde veio "
    "o dinheiro dessas remessas (P12)"
)
MOTIVO_TRANSITO = (
    "transferência entre contas sem TED de mesma titularidade no Meridiano até {fim}: pela R20 cai no "
    "Meridiano em {chegada} - conferir no extrato de {mes}"
)
MOTIVO_SEM_CONFERENCIA = (
    "{conferencia} não feita: a fonte {fontes} está bloqueada ({pendencias}, R44) - valor = {lado} sem conferir - "
    "próximo passo: a Helena libera a fonte bloqueada e o fechamento roda de novo; a conferência sai sozinha"
)
MOTIVO_SEM_PAR = (
    "transferência entre contas sem TED de mesma titularidade e mesmo valor no Meridiano na mesma data "
    "nem no dia útil seguinte (P13) - próximo passo: a Helena localiza nos extratos a outra ponta da transferência"
)


class ErroBancos(ValueError):
    """Dado de entrada ou configuração que impede classificar os extratos."""


class ErroDadoBancos(ErroBancos, dep.ErroDado):
    """Dado de um extrato, da Ponte ou da planilha que impede aplicar a regra a um lançamento ou a uma operação
    (R44): no fechamento, vira PEN-REGRA e o resto fecha."""


EFEITO_SEM_DESCRICAO = "o lançamento ficou fora de lancamentos_classificados.csv e das conferências - valor = o do lançamento"
EFEITO_OPERACAO_CONF = ("a operação ficou fora das conferências P11 e P12 (TEDs de liquidação e PIX × remessas) - valor "
                        "0,00: a operação continua no relatório da Ponte")
EFEITO_PERIODO = ("as conferências P11 (TEDs de liquidação) e P13 (transferências) não foram feitas; os lançamentos do "
                  "Meridiano e a conferência P12 saíram normalmente - nenhum valor muda")
EFEITO_LISTA = ("o favorecido ou pagador continua na lista, sem a conferência do CNPJ com a planilha (P07, P08) - nenhum "
                "valor muda")


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


def _contrapartes(bruto: dict, nome: str, cnpjs_planilha: set[str] | None,
                  problemas: list | None = None) -> dict[str, Contraparte]:
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
            if cnpjs_planilha is not None and cnpj not in cnpjs_planilha:
                mensagem = f"config: {campo}.cnpj {cnpj} não está na planilha de taxas"
                if problemas is None:
                    raise ErroBancos(mensagem)
                problemas.append((nome, texto, cnpj, mensagem))  # R44: a planilha perdeu o lojista; a lista segue
            if sem_contrato:
                raise ErroBancos(f"config: {campo}: com CNPJ da planilha não pode ser sem_contrato")
        elif not (isinstance(ec, str) and ec.isdigit() and sem_contrato is True):
            raise ErroBancos(f"config: {campo}: sem cnpj, precisa de ec (texto com dígitos) e sem_contrato: true")
        lista[texto] = Contraparte(cnpj, ec, bool(sem_contrato))
    return lista


def carregar_config(plano: pd.DataFrame, taxas: pd.DataFrame | None, caminho=CONFIG_BANCOS,
                    favorecidos=CONFIG_FAVORECIDOS, pagadores=CONFIG_PAGADORES, problemas: list | None = None,
                    cnpjs_rejeitados=()) -> ConfigBancos:
    """Lê as regras e as listas. Falha se uma conta não existir no plano ou não aceitar lançamento,
    ou se um CNPJ das listas não estiver na planilha de taxas. Sem a planilha (fonte bloqueada, R44), os CNPJs das
    listas não são conferidos (a PEN-BLOQUEIO-TAXAS diz isso). Com problemas (o fechamento, R44), CNPJ das listas
    fora da planilha vai para a lista (lista, texto, CNPJ, mensagem) em vez de parar; cnpjs_rejeitados são os CNPJs
    de linhas da planilha que o leitor não converteu, que existem nela."""
    bruto = _ler_yaml(caminho)
    contas = _contas_lancaveis(plano)
    regras = {}
    for banco in PREFIXO_ID:
        lista = (bruto.get("regras") or {}).get(banco)
        if not lista:
            raise ErroBancos(f"config: regras.{banco} vazia ou ausente")
        regras[banco] = tuple(_regra(r, f"regras.{banco}[{i}]", contas) for i, r in enumerate(lista))
    cnpjs = set(taxas["cnpj"]) | set(cnpjs_rejeitados) if taxas is not None else None
    listas = {
        "favorecidos": _contrapartes(_ler_yaml(favorecidos).get(LISTAS["favorecidos"]), "favorecidos", cnpjs, problemas),
        "pagadores": _contrapartes(_ler_yaml(pagadores).get(LISTAS["pagadores"]), "pagadores", cnpjs, problemas),
    }
    sem_cnpj = [t for t, c in listas["pagadores"].items() if c.cnpj is None]
    if sem_cnpj:
        raise ErroBancos(f"config: pagadores sem CNPJ não podem ser conferidos com a Ponte: {sem_cnpj}")
    sem_regra = bruto.get("sem_regra") or {}
    return ConfigBancos(
        regras=regras,
        listas=listas,
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


def classificar(banco: str, linhas: list[dict], cfg: ConfigBancos,
                problemas: list[tuple[str, dict, dep.ErroDado]] | None = None) -> list[Lancamento]:
    """linhas: dicts com arquivo_origem, ref_origem, data, descricao, valor. A primeira regra que casa vence.

    Lançamento sem descrição é erro; com problemas (o fechamento, R44), fica de fora e vai para a lista."""
    lancamentos = []
    for linha in linhas:
        texto, valor = linha["descricao"], linha["valor"]
        if not isinstance(texto, str) or not texto.strip():
            erro = ErroDadoBancos(dep.LINHA, f"{banco} {linha['ref_origem']} ({linha['arquivo_origem']}): lançamento "
                                  "sem descrição")
            if problemas is None:
                raise erro
            problemas.append((banco, linha, erro))
            continue
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


# ---------------------------------------------------------------- fallback com IA (P14)

@dataclass(frozen=True)
class FallbackIA:
    """Sugestão de conta para lançamento sem regra (P14). cliente None: SDK anthropic com a chave do ambiente."""

    cfg: ia.ConfigIA
    contas: dict[str, str]
    cliente: object | None = None

    def sugerir(self, l: Lancamento, exemplos: list[ia.Exemplo]) -> ia.Sugestao | None:
        return ia.sugerir_conta(l, self.contas, exemplos, cfg=self.cfg, cliente=self.cliente)


def exemplos_ia(lancamentos: list[Lancamento], maximo: int) -> list[ia.Exemplo]:
    """Um lançamento por regra que casou no extrato, na ordem do arquivo, até maximo."""
    vistas, exemplos = set(), []
    for l in lancamentos:
        if l.regra is None or l.regra in vistas:
            continue
        vistas.add(l.regra)
        exemplos.append(ia.Exemplo(l.descricao, l.valor, l.regra.conta_codigo))
        if len(exemplos) == maximo:
            break
    return exemplos


def sugestoes_ia(por_banco: list[list[Lancamento]], fallback: FallbackIA) -> dict[str, ia.Sugestao]:
    """id_saida -> sugestão válida, só para lançamento sem regra. Cada extrato dá os próprios exemplos."""
    sugestoes = {}
    for lancamentos in por_banco:
        sem_regra = [l for l in lancamentos if l.regra is None]
        if not sem_regra:
            continue
        exemplos = exemplos_ia(lancamentos, fallback.cfg.max_exemplos)
        for l in sem_regra:
            s = fallback.sugerir(l, exemplos)
            if s is not None:
                sugestoes[l.id_saida] = s
    return sugestoes


def item_lancamento(l: Lancamento, cfg: ConfigBancos, sugestao: ia.Sugestao | None = None) -> ItemSaida:
    if l.regra is None and sugestao is not None:  # P14: só sugestão, revisada pela pendência PEN-IA
        conta, metodo, confianca = sugestao.conta_codigo, "IA", sugestao.confianca
    elif l.regra is None:  # P09
        conta, metodo, confianca = cfg.conta_sem_regra, "HUMANO", cfg.confianca_sem_regra
    else:
        conta, metodo, confianca = l.regra.conta_codigo, "REGRA", l.regra.confianca
    if l.regra is not None:
        regra, detalhe = l.regra.fonte, (f"regra de config/bancos.yaml: padrão {l.regra.padrao.pattern!r}, sentido "
                                         f"{l.regra.sentido} - conta {conta}")
    elif sugestao is not None:
        regra, detalhe = "P14", f"sem regra - conta {conta} sugerida pela IA, revisão na PEN-IA-{l.ref_origem}"
    else:
        regra, detalhe = "P09", f"sem regra - {conta}, classificação manual na PEN-SEMREGRA-{l.ref_origem}"
    return ItemSaida(l.id_saida, LANCAMENTOS.nome,
                     {"banco": l.banco, "ref_origem": l.ref_origem, "data": l.data,
                      "descricao": texto_saida(l.descricao),
                      "conta_codigo": conta, "metodo": metodo, "confianca": confianca},
                     l.valor, [l.origem()], regra=regra, detalhe=texto_saida(detalhe))


# ---------------------------------------------------------------- pendências

def _soma(valores) -> Decimal:
    return sum(valores, ZERO)


# Regra e detalhe do rastro de cada pendência dos bancos (O06); a linha do extrato herda o detalhe.
REGRA_PENDENCIA = {
    "LANCAMENTO_SEM_REGRA": ("P09", "lançamento do extrato sem regra em config/bancos.yaml"),
    "CREDITO_NAO_IDENTIFICADO": ("R20", "PIX recebido sem identificação - não é receita até identificar"),
    "DEVOLUCAO_PIX": ("R20", "devolução de PIX - repasse que voltou, motivo a apurar (P06)"),
    "DIVERGENCIA_TED_LIQUIDACAO": ("P11", "TED LIQ OPERACOES do dia no Meridiano, com sinal"),
    "DIFERENCA_PIX_REMESSA": ("P12", "PIX recebido do cliente no Meridiano"),
    "TRANSFERENCIA_EM_TRANSITO": ("R20", "transferência enviada do Aurora, ainda sem a chegada no Meridiano"),
    "TRANSFERENCIA_SEM_PAR": ("P13", "transferência enviada do Aurora sem TED de mesma titularidade no Meridiano"),
    "CONFERENCIA_NAO_FEITA": ("R44", "lado que existe da conferência, sem conferir (fonte do outro lado bloqueada)"),
}


def _pendencia(id_saida: str, tipo: str, refs, motivo: str, valor: Decimal, origens, cfg: ConfigBancos) -> ItemSaida:
    regra, detalhe = REGRA_PENDENCIA[tipo]
    return ItemSaida(id_saida, PENDENCIAS.nome,
                     {"tipo": tipo, "ref_origem": refs, "motivo": texto_saida(motivo), "quem_decide": cfg.quem_decide},
                     valor, origens, regra=regra, detalhe=detalhe)


def pendencia_ia(l: Lancamento, s: ia.Sugestao, cfg_ia: ia.ConfigIA) -> ItemSaida:
    """P14: toda sugestão da IA vira pendência de revisão; abaixo do limiar, o motivo diz "baixa confiança"."""
    nivel = NIVEL_IA if s.confianca >= cfg_ia.limiar_confianca else NIVEL_IA_BAIXO.format(limiar=cfg_ia.limiar_confianca)
    motivo = MOTIVO_IA.format(modelo=cfg_ia.modelo, nivel=nivel, confianca=s.confianca, justificativa=s.justificativa)
    return ItemSaida(f"PEN-IA-{l.ref_origem}", PENDENCIAS.nome,
                     {"tipo": "REVISAR_SUGESTAO_IA", "ref_origem": l.ref_origem, "motivo": texto_saida(motivo),
                      "quem_decide": cfg_ia.quem_decide},
                     l.valor, [l.origem()], regra="P14",
                     detalhe=texto_saida(f"sugestão da IA: conta {s.conta_codigo}, confiança {s.confianca} - revisão "
                                         "humana antes de lançar"))


def pendencias_lancamentos(lancamentos: list[Lancamento], cfg: ConfigBancos,
                           sugestoes: dict[str, ia.Sugestao] | None = None,
                           cfg_ia: ia.ConfigIA | None = None) -> list[ItemSaida]:
    """R20 (PIX sem identificação, devolução de PIX), P09 (lançamento sem regra) e P14 (sugestão da IA)."""
    sugestoes = sugestoes or {}
    itens = []
    for l in lancamentos:
        if l.regra is None and l.id_saida in sugestoes:
            itens.append(pendencia_ia(l, sugestoes[l.id_saida], cfg_ia))
        elif l.regra is None:
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


def _origem_op(op: dict, sinal: int) -> tuple:
    """Operação da Ponte no rastro de uma conferência: valor_brl + iof_brl, com o sinal do lado dela; a regra é a da
    pendência (P11, P12 ou R44)."""
    return (op["arquivo_origem"], op["ref_origem"], _valor_operacao(op) * sinal, "",
            f"operação da Ponte contratada em {op['data_contratacao'].isoformat()}: valor_brl + iof_brl"
            + (" com o sinal trocado" if sinal < 0 else ""))


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


def conferir_pix_remessas(meridiano: list[Lancamento], unicas_mes: list[dict], cfg: ConfigBancos) -> list[ItemSaida]:
    """P12: por CNPJ, PIX do mês = operações únicas do mês. PIX a mais é adiantamento (R22); PIX a menos é pendência."""
    pix: dict[str, list[Lancamento]] = defaultdict(list)
    for l in meridiano:
        if l.papel == "pix_cliente":
            pix[l.contraparte.cnpj].append(l)
    ops: dict[str, list[dict]] = defaultdict(list)
    for op in unicas_mes:
        ops[op["cnpj"]].append(op)

    itens = []
    for cnpj in sorted(set(pix) | set(ops)):
        diferenca = _soma(l.valor for l in pix[cnpj]) - _soma(_valor_operacao(op) for op in ops[cnpj])
        # R22: PIX de lojista acima das remessas do mês é adiantamento de remessa futura, fica em 2.1.02.001
        # pela regra do PIX e não é pendência. Todo pagador de pix_cliente é lojista com CNPJ da planilha (P08).
        if diferenca >= 0:
            continue
        origens = ([l.origem() for l in sorted(pix[cnpj], key=lambda l: l.ref_origem)]
                   + [_origem_op(op, -1) for op in sorted(ops[cnpj], key=lambda o: o["ref_origem"])])
        itens.append(_pendencia(f"PEN-PIX-REM-{cnpj}", "DIFERENCA_PIX_REMESSA", [o[1] for o in origens],
                                MOTIVO_PIX_DIFERENCA, diferenca, origens, cfg))
    return itens


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

# Conferências cruzadas (R44): produto do mapa -> (id da PEN-SEMCONF, nome, papel no Meridiano/Aurora, lado da Ponte)
CONFERENCIAS = {
    "conferencia_ted_liquidacao": ("PEN-SEMCONF-TED-LIQ", "conferência das TEDs de liquidação com as operações "
                                   "da Ponte (P11)"),
    "conferencia_pix_remessas": ("PEN-SEMCONF-PIX-REM", "conferência dos PIX recebidos com as remessas (P12)"),
    "conferencia_transferencias": ("PEN-SEMCONF-TRANSF", "conferência das transferências Aurora × Meridiano (P13)"),
}
TODOS_PRODUTOS = frozenset(("lancamentos_aurora", "lancamentos_meridiano", *CONFERENCIAS))


def _sem_conferencia(chave: str, lados: list[tuple[str, list[tuple[str, str, Decimal]]]], bloqueadas: Iterable[str],
                     cfg: ConfigBancos) -> list[ItemSaida]:
    """PEN-SEMCONF-<...>: a conferência não saiu, e o que ficou sem conferir é o lado que existe (R44)."""
    lados = [(nome, origens) for nome, origens in lados if origens]
    if not lados:
        return []
    id_saida, conferencia = CONFERENCIAS[chave]
    fontes = sorted(set(dep.POR_CHAVE[chave].fontes) & set(bloqueadas))
    origens = [o for _, os_ in lados for o in os_]
    motivo = MOTIVO_SEM_CONFERENCIA.format(
        conferencia=conferencia, fontes=" e ".join(fontes),
        pendencias=", ".join(f"PEN-BLOQUEIO-{f.upper()}" for f in fontes), lado=" e ".join(n for n, _ in lados))
    return [_pendencia(id_saida, "CONFERENCIA_NAO_FEITA", [o[1] for o in origens], motivo,
                       _soma(o[2] for o in origens), origens, cfg)]


def calcular_bancos(aurora: pd.DataFrame | None, meridiano: pd.DataFrame | None, meridiano_meta: dict | None,
                    ponte: pd.DataFrame | None, competencia: str, cfg: ConfigBancos, cfg_remessa,
                    fallback: FallbackIA | None = None, produtos: frozenset[str] = TODOS_PRODUTOS,
                    bloqueadas: frozenset[str] = frozenset()) -> list[ItemSaida]:
    """Lançamentos e conferências dos produtos pedidos (todos, no fechamento completo). Fonte bloqueada vem None.

    Conferência fora de produtos (uma fonte dela bloqueada) vira PEN-SEMCONF com o lado que existe (R44).
    Dado que impede a regra (lançamento sem descrição, operação da Ponte sem data ou valor, extrato sem período)
    tira só o item e vira PEN-REGRA (R44)."""
    problemas: list[tuple[str, dict, dep.ErroDado]] = []
    pendencias_regra: list[ItemSaida] = []
    aur = classificar(AURORA, _linhas(aurora, "descricao"), cfg, problemas) if "lancamentos_aurora" in produtos else []
    mer = classificar(MERIDIANO, _linhas(meridiano, "memo"), cfg, problemas) if "lancamentos_meridiano" in produtos else []
    for banco, linha, erro in problemas:
        pendencias_regra.append(dep.pendencia_regra(erro.tipo, f"{PREFIXO_ID[banco]}-{linha['ref_origem']}", str(erro),
                                                    EFEITO_SEM_DESCRICAO, linha["valor"],
                                                    [(linha["arquivo_origem"], linha["ref_origem"], linha["valor"])]))
    inicio = fim = None
    if "lancamentos_meridiano" in produtos:
        inicio, fim = meridiano_meta.get("dtstart"), meridiano_meta.get("dtend")
        if inicio is None or fim is None:  # R44: sem período não há P11 nem P13; o resto sai
            arquivo = meridiano["arquivo_origem"].iloc[0] if len(meridiano) else "extrato do Meridiano"
            pendencias_regra.append(dep.pendencia_regra(
                dep.PERIODO, "MERIDIANO", f"{arquivo}: extrato do Meridiano sem DTSTART/DTEND, não há período para "
                "as conferências", EFEITO_PERIODO, ZERO, [(arquivo, "DTSTART/DTEND", ZERO)]))
            produtos = produtos - {"conferencia_ted_liquidacao", "conferencia_transferencias"}

    unicas = unicas_mes = None
    if ponte is not None:
        conflitos, separacao, fora_conf = [], [], []
        unicas, _ = deduplicar(ponte, cfg_remessa, conflitos)  # R13: a duplicata conta uma vez
        unicas, _ = separar_ajustes(unicas, cfg_remessa, separacao)  # R31: ajuste não é operação (sem TED nem PIX)
        fora_conf = [(c.copias[0], c.mensagem) for c in conflitos] + [(p.op, str(p.erro)) for p in separacao]
        usaveis = []
        for op in unicas:  # R44: operação sem data ou sem valor fica fora das conferências, as outras são conferidas
            vazios = [c for c in ("data_contratacao", "valor_brl", "iof_brl") if op[c] is None]
            if vazios:
                fora_conf.append((op, f"operação {op['ref_origem']} (linha {op['linha_planilha']} do relatório da "
                                      f"Ponte): {', '.join(vazios)} vazio"))
            else:
                usaveis.append(op)
        unicas = usaveis
        unicas_mes = [op for op in unicas if na_competencia(op, competencia)]
        if produtos & {"conferencia_ted_liquidacao", "conferencia_pix_remessas"}:
            for op, mensagem in sorted(fora_conf, key=lambda x: x[0]["ref_origem"]):
                pendencias_regra.append(dep.pendencia_regra(
                    dep.LINHA, f"CONF-{op['ref_origem']}", mensagem, EFEITO_OPERACAO_CONF, ZERO,
                    [(op["arquivo_origem"], op["ref_origem"], ZERO)]))
    pend_pix = (conferir_pix_remessas(mer, unicas_mes, cfg) if "conferencia_pix_remessas" in produtos else [])

    sugestoes = sugestoes_ia([aur, mer], fallback) if fallback is not None else {}
    itens = [item_lancamento(l, cfg, sugestoes.get(l.id_saida)) for l in aur + mer]
    itens += pendencias_lancamentos(aur + mer, cfg, sugestoes, fallback.cfg if fallback else None)
    if "conferencia_ted_liquidacao" in produtos:
        itens += conferir_ted_liquidacao(mer, unicas, inicio, fim, cfg)
    itens += pend_pix
    if "conferencia_transferencias" in produtos:
        itens += conferir_transferencias(aur, mer, fim, cfg)

    def papel(lancamentos, p):
        return [l.origem() for l in lancamentos if l.papel == p]

    ops = sorted(unicas_mes or [], key=lambda o: o["ref_origem"])
    lado_ponte = ("as operações únicas da Ponte contratadas no mês (valor_brl + iof_brl)",
                  [_origem_op(op, +1) for op in ops])
    if "conferencia_ted_liquidacao" not in produtos:
        itens += _sem_conferencia("conferencia_ted_liquidacao", [
            ("as TEDs LIQ OPERACOES do Meridiano", papel(mer, "ted_liquidacao")), lado_ponte], bloqueadas, cfg)
    if "conferencia_pix_remessas" not in produtos:
        itens += _sem_conferencia("conferencia_pix_remessas", [
            ("os PIX recebidos de clientes no Meridiano", papel(mer, "pix_cliente")), lado_ponte], bloqueadas, cfg)
    if "conferencia_transferencias" not in produtos:
        itens += _sem_conferencia("conferencia_transferencias", [
            ("as transferências enviadas do Aurora", papel(aur, "transferencia_enviada")),
            ("as TEDs de mesma titularidade recebidas no Meridiano", papel(mer, "transferencia_recebida"))],
            bloqueadas, cfg)
    return itens + pendencias_regra


def bancos(entradas: Entradas, config=CONFIG_BANCOS, favorecidos=CONFIG_FAVORECIDOS,
           pagadores=CONFIG_PAGADORES, config_ia=CONFIG_IA, cliente_ia=None) -> list[ItemSaida]:
    """Módulo do fechamento: lançamentos classificados e pendências bancárias.

    Fallback de IA (P14) só com entradas.usar_ia (o CLI desliga com --sem-ia) e habilitada em config/ia.yaml.
    Gera só os produtos do mapa (tarvo.dependencias) cujas fontes estão disponíveis (R44).
    """
    produtos = frozenset(p for p in TODOS_PRODUTOS if dep.gera(p, entradas))
    if not produtos & {"lancamentos_aurora", "lancamentos_meridiano"}:
        return []  # sem extrato legível ou sem plano de contas: a PEN-BLOQUEIO diz o que não saiu
    problemas_lista: list = []
    cfg = carregar_config(entradas.plano_contas, entradas.taxas, config, favorecidos, pagadores, problemas_lista,
                          {r.cnpj for r in entradas.rejeitadas.get("taxas", ())})
    regra_lista = [dep.pendencia_regra(dep.CADASTRO, f"LISTA-{lista}-{cnpj}", mensagem, EFEITO_LISTA, ZERO,
                                       [(Path(favorecidos if lista == "favorecidos" else pagadores).name, texto, ZERO)])
                   for lista, texto, cnpj, mensagem in problemas_lista]
    fallback = None
    if entradas.usar_ia:
        cfg_ia = ia.carregar_config(config_ia)
        if cfg_ia.habilitada:
            fallback = FallbackIA(cfg_ia, ia.contas_analiticas(entradas.plano_contas), cliente_ia)
    return calcular_bancos(entradas.aurora, entradas.meridiano, entradas.meridiano_meta, entradas.ponte,
                           entradas.competencia, cfg, carregar_config_remessa(), fallback, produtos,
                           dep.bloqueadas(entradas.bloqueios)) + regra_lista
