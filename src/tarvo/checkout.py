"""Linha CHECKOUT (Orbe): comissão pela taxa contratada, divergências, notas e pendências por lojista.

Regras do HIPOTESES.md, seção 1: R01 a R10, R25, R30, R32, R33 e R35 a R40; premissas P23 e P26. Mapeamentos e condições especiais em config/checkout.yaml.
O lojista é casado só pelo EC (coluna "EC Orbe" da planilha ou ec_sem_codigo da config) e depois pelo CNPJ;
o nome da Orbe nunca é usado.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
import yaml

from tarvo.leitores.comum import dinheiro
from tarvo.saida import COMISSOES, DIVERGENCIAS, NOTAS, PENDENCIAS, ItemSaida, texto_saida

if TYPE_CHECKING:
    from tarvo.fechamento import Entradas

CONFIG_CHECKOUT = Path(__file__).resolve().parents[2] / "config" / "checkout.yaml"
LINHA_NEGOCIO = "CHECKOUT"
ZERO = Decimal("0.00")
VENDA, ANTECIPACAO, REVERSAO = "VENDA", "ANTECIPACAO", "REVERSAO ANTECIPACAO"  # tipos da Orbe (P26)

MOTIVO_NOTA_NAO_EMITIDA = "comissão de checkout do mês zero ou negativa: não emite nota e não passa para o mês seguinte (R06)"
MOTIVO_SEM_CONTRATO = (
    "EC sem taxa contratada na aba vigente nem em ec_sem_codigo: não faturar até o comercial confirmar (R08) - "
    "valor = taxa cobrada pela Orbe"
)
MOTIVO_RETROATIVO = (
    "EC sem contrato vigente: não faturar até o Comercial confirmar (R08) - quando o Comercial confirmar, "
    "as {qtd} transações do mês (R$ {bruto} brutos) são faturadas na competência {seguinte}, com a taxa "
    "retroativa a {primeira}, data da primeira transação ({regra}) - valor = taxa cobrada pela Orbe"
)
MOTIVO_DEVOLUCAO = (
    "taxa aplicada pela Orbe diferente da contratada - a nota documenta só a taxa contratada e o que a Orbe "
    "cobrou a mais é valor a devolver ao lojista - valor = diferença pela taxa contratada (R03, R25, R32)"
)
MOTIVO_CONCESSAO = (
    "concessão comercial; custo da Tarvo; não é divergência; não se cobra da Orbe ({regra}, R32, R38) - "
    "valor = taxa cobrada pela Orbe nas transações da concessão"
)
MOTIVO_IDENTIFICACAO = "EC {ec}, CNPJ {cnpj} (identificado pela aba de 2025, sem usar a taxa dela - R39) - "
MOTIVO_ALERTA = (
    "alerta informativo (P26, R33): lojista sem histórico ({historico}) antecipou R$ {antecipado} brutos "
    "(R$ {liquido} líquidos das reversões) contra R$ {vendido} de vendas no mês - não muda nenhum valor"
)


class ErroCheckout(ValueError):
    """Dado de entrada ou configuração que impede aplicar as regras do checkout."""


# ---------------------------------------------------------------- configuração

@dataclass(frozen=True)
class CondicaoEspecial:
    regra: str
    cnpj: str
    inicio: date
    fim: date
    taxas: dict[str, Decimal]

    def vale_em(self, d: date) -> bool:
        return self.inicio <= d <= self.fim


@dataclass(frozen=True)
class ConfigCheckout:
    ec_sem_codigo: dict[str, str]
    condicoes: tuple[CondicaoEspecial, ...]
    taxa_por_tipo: dict[str, str]
    taxa_por_modalidade: dict[str, str]
    modalidade_parcelado: str
    faixas_parcelado: tuple[tuple[int, int, str], ...]
    discriminacao_nota: str
    quem_decide: dict[str, str]
    faturamento_retroativo: dict[str, str] = field(default_factory=dict)  # EC -> regra (R30)
    cnpj_identificacao: dict[str, str] = field(default_factory=dict)      # EC sem contrato -> CNPJ, só para identificar (R39)


def _data_cfg(v, campo: str) -> date:
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v))
    except ValueError:
        raise ErroCheckout(f"config: {campo} deveria ser data AAAA-MM-DD, veio {v!r}") from None


def _str_cfg(v, campo: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise ErroCheckout(f"config: {campo} deveria ser texto entre aspas, veio {v!r}")
    return v


def carregar_config(caminho=CONFIG_CHECKOUT) -> ConfigCheckout:
    with open(caminho, encoding="utf-8") as f:
        bruto = yaml.safe_load(f)
    condicoes = tuple(
        CondicaoEspecial(
            regra=_str_cfg(c["regra"], "regra"),
            cnpj=_str_cfg(c["cnpj"], "cnpj"),
            inicio=_data_cfg(c["vigencia_inicio"], "vigencia_inicio"),
            fim=_data_cfg(c["vigencia_fim"], "vigencia_fim"),
            taxas={campo: Decimal(_str_cfg(t, campo)) for campo, t in c["taxas"].items()},
        )
        for c in bruto.get("condicoes_especiais") or []
        if c["linha_negocio"] == LINHA_NEGOCIO
    )
    parcelado = bruto["taxa_parcelado"]
    return ConfigCheckout(
        ec_sem_codigo={_str_cfg(ec, "ec_sem_codigo"): _str_cfg(cnpj, "ec_sem_codigo")
                       for ec, cnpj in bruto["ec_sem_codigo"].items()},
        condicoes=condicoes,
        taxa_por_tipo=dict(bruto["taxa_por_tipo_lancamento"]),
        taxa_por_modalidade=dict(bruto["taxa_por_modalidade"]),
        modalidade_parcelado=parcelado["modalidade"],
        faixas_parcelado=tuple((int(f["de"]), int(f["ate"]), f["taxa"]) for f in parcelado["faixas"]),
        discriminacao_nota=_str_cfg(bruto["discriminacao_nota"], "discriminacao_nota"),
        quem_decide=dict(bruto["quem_decide"]),
        faturamento_retroativo={_str_cfg(ec, "faturamento_retroativo"): _str_cfg(r, "faturamento_retroativo")
                                for ec, r in (bruto.get("faturamento_retroativo") or {}).items()},
        cnpj_identificacao={_str_cfg(ec, "cnpj_identificacao"): _str_cfg(c, "cnpj_identificacao")
                            for ec, c in (bruto.get("cnpj_identificacao") or {}).items()},
    )


# ---------------------------------------------------------------- planilha de taxas

class Contratos:
    """EC -> CNPJ e, por CNPJ, a linha da planilha vigente numa data."""

    def __init__(self, taxas: pd.DataFrame, cfg: ConfigCheckout):
        self.linhas: dict[str, list[dict]] = defaultdict(list)
        self.ec_cnpj: dict[str, str] = {}
        for linha in taxas.to_dict("records"):
            self.linhas[linha["cnpj"]].append(linha)
            ec = linha["ec"]
            if ec is None:
                continue
            if self.ec_cnpj.get(ec, linha["cnpj"]) != linha["cnpj"]:
                raise ErroCheckout(f"EC {ec} aparece com dois CNPJs na planilha ({self.ec_cnpj[ec]} e {linha['cnpj']})")
            self.ec_cnpj[ec] = linha["cnpj"]
        for ec, cnpj in cfg.ec_sem_codigo.items():
            if ec in self.ec_cnpj and self.ec_cnpj[ec] != cnpj:
                raise ErroCheckout(f"EC {ec}: ec_sem_codigo diz {cnpj}, a planilha diz {self.ec_cnpj[ec]}")
            if cnpj not in self.linhas:
                raise ErroCheckout(f"EC {ec}: CNPJ {cnpj} de ec_sem_codigo não está na planilha")
            self.ec_cnpj[ec] = cnpj

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
            raise ErroCheckout(f"CNPJ {cnpj}: esperada 1 linha vigente em {d}, achei {len(vigentes)} ({refs})")
        return vigentes[0]


def _campo_taxa(linha_orbe: dict, cfg: ConfigCheckout) -> str:
    tipo, modalidade, parcelas = linha_orbe["tipo_lancamento"], linha_orbe["modalidade"], linha_orbe["qtd_parcelas"]
    if tipo in cfg.taxa_por_tipo:
        return cfg.taxa_por_tipo[tipo]
    if modalidade == cfg.modalidade_parcelado:
        for de, ate, campo in cfg.faixas_parcelado:
            if parcelas is not None and de <= parcelas <= ate:
                return campo
        raise ErroCheckout(f"{linha_orbe['ref_origem']}: {modalidade} com {parcelas} parcelas fora das faixas da config")
    if modalidade in cfg.taxa_por_modalidade:
        return cfg.taxa_por_modalidade[modalidade]
    raise ErroCheckout(f"{linha_orbe['ref_origem']}: tipo {tipo!r} / modalidade {modalidade!r} sem taxa na config")


# ---------------------------------------------------------------- cálculo linha a linha

@dataclass(frozen=True)
class LinhaCheckout:
    arquivo_origem: str
    ref_origem: str
    ec: str
    cnpj: str | None              # None: EC sem taxa contratada
    tipo_lancamento: str
    id_referencia: str | None
    data_referencia: date
    valor_bruto: Decimal
    valor_taxa_orbe: Decimal
    taxa_aplicada: Decimal
    taxa_contratada: Decimal | None   # taxa do contrato (planilha): base da divergência (R03, R32)
    origem_taxa: str | None       # ref da linha da planilha
    comissao: Decimal | None
    diferenca: Decimal | None     # None quando não há divergência
    data_movimento: date | None = None
    taxa_comissao: Decimal | None = None  # taxa da comissão: a do contrato ou a da concessão comercial (R10, R32)
    concessao: str | None = None          # regra da concessão comercial que zerou a comissão, se houver

    @property
    def divergente(self) -> bool:
        return self.diferenca is not None


def calcular_linhas(orbe: pd.DataFrame, taxas: pd.DataFrame, cfg: ConfigCheckout) -> list[LinhaCheckout]:
    contratos = Contratos(taxas, cfg)
    resultado = []
    for l in orbe.to_dict("records"):
        # R04/R05: estorno e reversão usam a taxa vigente na data da venda (ou antecipação) original
        data_ref = l["data_venda_original"] or l["data_movimento"]
        base = dict(
            arquivo_origem=l["arquivo_origem"], ref_origem=l["ref_origem"], ec=l["cod_estabelecimento"],
            tipo_lancamento=l["tipo_lancamento"], id_referencia=l["id_referencia"], data_referencia=data_ref,
            valor_bruto=l["valor_bruto"], valor_taxa_orbe=l["valor_taxa"], taxa_aplicada=l["taxa_aplicada_pct"],
            data_movimento=l["data_movimento"],
        )
        cnpj = contratos.ec_cnpj.get(l["cod_estabelecimento"])
        if cnpj is None:  # R08
            resultado.append(LinhaCheckout(**base, cnpj=None, taxa_contratada=None, origem_taxa=None,
                                           comissao=None, diferenca=None, taxa_comissao=None))
            continue

        # R35: a faixa (modalidade, parcelas) sai da própria linha, inclusive a do estorno
        campo = _campo_taxa(l, cfg)
        linha_taxa = contratos.vigente(cnpj, data_ref)
        contratada, origem_taxa = linha_taxa[campo], linha_taxa["ref_origem"]
        if contratada is None:
            raise ErroCheckout(f"{l['ref_origem']}: CNPJ {cnpj} sem {campo} na {origem_taxa} da planilha")
        # R10, R32, R40: a concessão comercial muda só a comissão (a Tarvo abre mão da receita); o contrato continua
        # sendo a planilha, e é contra ele que se mede a divergência
        condicao = next((c for c in cfg.condicoes if c.cnpj == cnpj and c.vale_em(data_ref) and campo in c.taxas), None)
        taxa_comissao = condicao.taxas[campo] if condicao is not None else contratada

        comissao = dinheiro(l["valor_bruto"] * taxa_comissao / 100)  # R01, R02
        diferenca = None
        if l["taxa_aplicada_pct"] != contratada:  # R03, R37: compara taxas, nunca valores (P03); estorno entra com sinal
            diferenca = dinheiro(l["valor_bruto"] * (l["taxa_aplicada_pct"] - contratada) / 100)
        resultado.append(LinhaCheckout(**base, cnpj=cnpj, taxa_contratada=contratada, origem_taxa=origem_taxa,
                                       comissao=comissao, diferenca=diferenca, taxa_comissao=taxa_comissao,
                                       concessao=condicao.regra if condicao is not None else None))
    return resultado


# ---------------------------------------------------------------- itens de saída

def _soma(valores) -> Decimal:
    return sum(valores, ZERO)


def _competencia_seguinte(competencia: str) -> str:
    """AAAA-MM do mês seguinte."""
    ano, mes = (int(p) for p in competencia.split("-"))
    return f"{ano + mes // 12:04d}-{mes % 12 + 1:02d}"


def _pendencia_devolucao(cnpj: str, divergentes: list[LinhaCheckout], cfg: ConfigCheckout) -> ItemSaida:
    """R03, R25, R32: a contraparte cobrou diferente do contrato; o lojista é ressarcido pela diferença."""
    origens = [(l.arquivo_origem, l.ref_origem, l.diferenca) for l in divergentes]
    return ItemSaida(f"PEN-DEVOL-CHK-{cnpj}", PENDENCIAS.nome,
                     {"tipo": "DEVOLUCAO_LOJISTA", "ref_origem": [l.ref_origem for l in divergentes],
                      "motivo": texto_saida(MOTIVO_DEVOLUCAO), "quem_decide": cfg.quem_decide["devolucao_lojista"]},
                     _soma(o[2] for o in origens), origens)


def _pendencia_concessao(cnpj: str, linhas: list[LinhaCheckout], cfg: ConfigCheckout) -> ItemSaida:
    """R10, R32, R38: a Tarvo devolve ao lojista o que a Orbe descontou dentro do contrato nas transações da concessão.
    Custo da Tarvo, separado das divergências. Se a mesma linha também diverge do contrato, a parte acima do contrato
    já está na PEN-DEVOL-CHK e sai daqui (P23)."""
    regras = sorted({l.concessao for l in linhas})
    origens = [(l.arquivo_origem, l.ref_origem, l.valor_taxa_orbe - (l.diferenca or ZERO)) for l in linhas]
    return ItemSaida(f"PEN-CONCESSAO-CHK-{cnpj}", PENDENCIAS.nome,
                     {"tipo": "DEVOLUCAO_CONCESSAO", "ref_origem": [l.ref_origem for l in linhas],
                      "motivo": texto_saida(MOTIVO_CONCESSAO.format(regra=", ".join(regras))),
                      "quem_decide": cfg.quem_decide["devolucao_lojista"]},
                     _soma(o[2] for o in origens), origens)


def _primeiro_dia(competencia: str) -> date:
    ano, mes = (int(p) for p in competencia.split("-"))
    return date(ano, mes, 1)


def _alertas_antecipacao(grupos: dict[str, list[LinhaCheckout]], contratos, competencia: str, cfg: ConfigCheckout,
                         ecs_anteriores: frozenset[str] | None) -> list[ItemSaida]:
    """P26 (R33): alerta informativo quando lojista sem histórico antecipa mais do que vendeu no mês.

    Sem histórico: com a competência anterior disponível, nenhuma transação do EC nela. Sem ela, nenhuma linha do mês
    ligada a venda anterior ao mês (estorno ou reversão de antecipação de data anterior) e primeira transação depois
    do dia 1, ou o primeiro contrato do lojista começando no mês. Pendência com valor zero: não muda nenhum valor.
    """
    inicio = _primeiro_dia(competencia)
    itens = []
    for chave, doc in sorted(grupos.items()):
        antecipacoes = [l for l in doc if l.tipo_lancamento == ANTECIPACAO]
        if not antecipacoes:
            continue
        antecipado = _soma(l.valor_bruto for l in antecipacoes)
        reversoes = _soma(l.valor_bruto for l in doc if l.tipo_lancamento == REVERSAO)
        vendido = _soma(l.valor_bruto for l in doc if l.tipo_lancamento == VENDA)
        if antecipado <= vendido:
            continue
        ecs = {l.ec for l in doc}
        primeira = min(l.data_movimento for l in doc)
        if ecs_anteriores is not None:
            if ecs & ecs_anteriores:
                continue
            historico = "nenhuma transação na competência anterior"
        else:
            ligada_a_anterior = any(l.data_referencia < inicio for l in doc)
            cnpj = doc[0].cnpj
            inicios = [r["vigencia_inicio"] for r in contratos.linhas.get(cnpj, [])] if cnpj else []
            contrato_no_mes = bool(inicios) and None not in inicios and min(inicios) >= inicio
            if ligada_a_anterior or not (primeira > inicio or contrato_no_mes):
                continue
            historico = f"primeira transação em {primeira.isoformat()}, nenhuma linha de venda anterior ao mês"
        itens.append(ItemSaida(
            f"PEN-ALERTA-ANTEC-{chave}", PENDENCIAS.nome,
            {"tipo": "ALERTA_ANTECIPACAO", "ref_origem": [l.ref_origem for l in antecipacoes],
             "motivo": texto_saida(MOTIVO_ALERTA.format(historico=historico, antecipado=antecipado,
                                                        liquido=antecipado + reversoes, vendido=vendido)),
             "quem_decide": cfg.quem_decide["alerta_antecipacao"]},
            ZERO, [(l.arquivo_origem, l.ref_origem, ZERO) for l in antecipacoes]))
    return itens



def gerar_itens(linhas: list[LinhaCheckout], contratos_nome, competencia: str, cfg: ConfigCheckout,
                contratos: Contratos | None = None, ecs_anteriores: frozenset[str] | None = None) -> list[ItemSaida]:
    """contratos_nome: CNPJ -> nome do lojista na planilha."""
    itens: list[ItemSaida] = []
    por_cnpj: dict[str, list[LinhaCheckout]] = defaultdict(list)
    sem_contrato: dict[str, list[LinhaCheckout]] = defaultdict(list)
    for l in linhas:
        (por_cnpj[l.cnpj] if l.cnpj else sem_contrato[l.ec]).append(l)

    for cnpj in sorted(por_cnpj):
        doc = por_cnpj[cnpj]
        nome = texto_saida(contratos_nome(cnpj))
        rastro_comissao = [(l.arquivo_origem, l.ref_origem, l.comissao) for l in doc]
        comissao = _soma(l.comissao for l in doc)
        itens.append(ItemSaida(f"COM-CHK-{cnpj}", COMISSOES.nome,
                               {"cnpj": cnpj, "lojista": nome, "linha_negocio": LINHA_NEGOCIO},
                               comissao, rastro_comissao))

        if comissao > 0:  # R05, R06: uma nota por lojista, antecipação na mesma nota
            itens.append(ItemSaida(f"NF-CHK-{cnpj}", NOTAS.nome,
                                   {"tomador_cnpj": cnpj, "tomador": nome, "linha_negocio": LINHA_NEGOCIO,
                                    "discriminacao": texto_saida(cfg.discriminacao_nota.format(competencia=competencia))},
                                   comissao, rastro_comissao))
        else:
            itens.append(ItemSaida(f"PEN-NF-CHK-{cnpj}", PENDENCIAS.nome,
                                   {"tipo": "NOTA_NAO_EMITIDA", "ref_origem": [l.ref_origem for l in doc],
                                    "motivo": texto_saida(MOTIVO_NOTA_NAO_EMITIDA),
                                    "quem_decide": cfg.quem_decide["nota_nao_emitida"]},
                                   comissao, rastro_comissao))

        divergentes = [l for l in doc if l.divergente]
        for l in divergentes:
            itens.append(ItemSaida(f"DIV-CHK-{l.ref_origem}", DIVERGENCIAS.nome,
                                   {"cnpj": cnpj, "linha_negocio": LINHA_NEGOCIO, "ref_origem": l.ref_origem,
                                    "taxa_contratada_pct": l.taxa_contratada, "taxa_aplicada_pct": l.taxa_aplicada},
                                   l.diferenca, [(l.arquivo_origem, l.ref_origem, l.diferenca)]))
        if divergentes:
            itens.append(_pendencia_devolucao(cnpj, divergentes, cfg))
        concedidas = [l for l in doc if l.concessao is not None and l.taxa_comissao != l.taxa_contratada]
        if concedidas:  # R32, R38: devolução da concessão, separada das divergências
            itens.append(_pendencia_concessao(cnpj, concedidas, cfg))

    for ec in sorted(sem_contrato):  # R08, R36: uma pendência por EC, fora de comissão, divergência e nota
        doc = sem_contrato[ec]
        motivo = MOTIVO_SEM_CONTRATO
        if ec in cfg.faturamento_retroativo:  # R30
            motivo = MOTIVO_RETROATIVO.format(
                qtd=len(doc), bruto=_soma(l.valor_bruto for l in doc),
                primeira=min(l.data_referencia for l in doc).isoformat(),
                seguinte=_competencia_seguinte(competencia), regra=cfg.faturamento_retroativo[ec])
        identificacao = cfg.cnpj_identificacao.get(ec)  # R39: o CNPJ só identifica; a taxa daquela aba não vale
        if identificacao:
            motivo = MOTIVO_IDENTIFICACAO.format(ec=ec, cnpj=identificacao) + motivo
        itens.append(ItemSaida(f"PEN-SEMCONTRATO-{identificacao or ec}", PENDENCIAS.nome,
                               {"tipo": "LOJISTA_SEM_CONTRATO", "ref_origem": [l.ref_origem for l in doc],
                                "motivo": texto_saida(motivo), "quem_decide": cfg.quem_decide["lojista_sem_contrato"]},
                               _soma(l.valor_taxa_orbe for l in doc),
                               [(l.arquivo_origem, l.ref_origem, l.valor_taxa_orbe) for l in doc]))

    if contratos is not None:  # P26: alerta informativo de antecipação
        grupos = {**{c: d for c, d in por_cnpj.items()},
                  **{cfg.cnpj_identificacao.get(ec, ec): d for ec, d in sem_contrato.items()}}
        itens += _alertas_antecipacao(grupos, contratos, competencia, cfg, ecs_anteriores)
    return itens


def calcular_checkout(orbe: pd.DataFrame, taxas: pd.DataFrame, competencia: str,
                      cfg: ConfigCheckout, ecs_anteriores: frozenset[str] | None = None) -> list[ItemSaida]:
    contratos = Contratos(taxas, cfg)
    return gerar_itens(calcular_linhas(orbe, taxas, cfg), contratos.nome, competencia, cfg, contratos, ecs_anteriores)


def ecs_competencia_anterior(entradas: Entradas) -> frozenset[str] | None:
    """ECs com transação no relatório da Orbe da competência anterior, se a pasta dela existir ao lado desta (P26)."""
    from tarvo.cli import CONFIG_PADRAO, ErroEntrada, carregar_padroes, localizar_arquivos
    from tarvo.leitores.orbe import ler_orbe
    from tarvo.remessa import pasta_anterior

    pasta = pasta_anterior(entradas.arquivos["orbe"].parent, entradas.competencia)
    if pasta is None:
        return None
    try:
        arquivos = localizar_arquivos(pasta, carregar_padroes(CONFIG_PADRAO))
    except ErroEntrada:
        return None
    return frozenset(ler_orbe(arquivos["orbe"])["cod_estabelecimento"])


def checkout(entradas: Entradas, config=CONFIG_CHECKOUT) -> list[ItemSaida]:
    """Módulo do fechamento: itens da linha CHECKOUT a partir da Orbe e da planilha de taxas."""
    return calcular_checkout(entradas.orbe, entradas.taxas, entradas.competencia, carregar_config(config),
                             ecs_competencia_anterior(entradas))
