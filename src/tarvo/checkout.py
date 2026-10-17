"""Linha CHECKOUT (Orbe): comissão pela taxa contratada, divergências, notas e pendências por lojista.

Regras do HIPOTESES.md, seção 1: R01 a R10, R25, R30, R32, R33, R35 a R41, R43 a R45; premissas P23 e P26. Mapeamentos e condições especiais em config/checkout.yaml.
O lojista é casado só pelo EC (coluna "EC Orbe" da planilha ou ec_sem_codigo da config) e depois pelo CNPJ;
o nome da Orbe nunca é usado.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import pandas as pd
import yaml

from tarvo import dependencias as dep
from tarvo.leitores.comum import dinheiro
from tarvo.saida import COMISSOES, DIVERGENCIAS, NOTAS, PENDENCIAS, ItemSaida, texto_saida

if TYPE_CHECKING:
    from tarvo.fechamento import Entradas

CONFIG_CHECKOUT = Path(__file__).resolve().parents[2] / "config" / "checkout.yaml"
LINHA_NEGOCIO = "CHECKOUT"
ZERO = Decimal("0.00")
VENDA, ANTECIPACAO, REVERSAO = "VENDA", "ANTECIPACAO", "REVERSAO ANTECIPACAO"  # tipos da Orbe (P26)

MOTIVO_NOTA_NAO_EMITIDA = (
    "comissão de checkout do mês zero ou negativa: não emite nota e não passa para o mês seguinte - próximo passo: "
    "a Helena decide o tratamento do saldo (R06)"
)
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
    "cobrou a mais é valor a devolver ao lojista - valor = valor_taxa descontado pela Orbe menos a comissão pela taxa "
    "contratada, transação a transação (R45) - próximo passo: a Helena devolve o valor ao lojista e contesta com a "
    "Orbe, pelo rascunho de e-mail em {rascunho} (R03, R25, R29, R32)"
)
MOTIVO_CONCESSAO = (
    "concessão comercial; custo da Tarvo; não é divergência; não se cobra da Orbe ({regra}, R32, R38, R41) - "
    "valor = valor_taxa descontado pela Orbe menos a comissão da Tarvo nas transações da concessão, transação a "
    "transação (R45) - próximo passo: a Helena paga a devolução ao lojista e decide com o Comercial se pede à Orbe "
    "parametrizar {taxa} daqui em diante (nota interna em {rascunho})"
)
MOTIVO_REPETIDA = (
    "id_transacao {ref} veio em {mantido} (linha física {n_mantida}) e de novo, com a linha igual, em {repetido} "
    "(linha física {n_repetida}): contado uma vez no fechamento (P27) - próximo passo: a Helena confirma com a Orbe que "
    "é a mesma transação enviada duas vezes"
)
MOTIVO_SEM_ORIGINAL = (
    "{tipo} de {data} referente a {original}, transação do mesmo mês que não está em nenhum arquivo da Orbe: entra "
    "pela taxa da data da original e pela faixa da própria linha (R35), sem conferir com a original (P28) - próximo "
    "passo: a Helena pede à Orbe a transação original {original}"
)
MOTIVO_IDENTIFICACAO = "EC {ec}, CNPJ {cnpj} (identificado pela aba de 2025, sem usar a taxa dela - R39) - "
MOTIVO_ALERTA = (
    "alerta informativo (P26, R33, R43): lojista sem histórico ({historico}) - pico em {pico}: R$ {antecipado_pico} "
    "antecipados contra R$ {vendido_pico} vendidos, acumulados desde a primeira transação - {reversoes} - fim do mês: "
    "R$ {liquido} antecipados, líquidos das reversões, contra R$ {vendido} de vendas (R$ {antecipado} antecipados "
    "brutos) - não muda nenhum valor - próximo passo: a Helena e o Comercial avaliam o risco do lojista (R33)"
)
TEXTO_ALERTA_REVERSOES = "reversões, que não apagam o alerta: {lista}"
TEXTO_ALERTA_SEM_REVERSAO = "nenhuma reversão no mês"


class ErroCheckout(ValueError):
    """Dado de entrada ou configuração que impede aplicar as regras do checkout."""


class ErroDadoCheckout(ErroCheckout, dep.ErroDado):
    """Dado da Orbe ou da planilha que impede aplicar a regra a um lojista ou a uma transação (R44): no fechamento,
    vira PEN-REGRA e o resto do checkout fecha."""


class ProblemaCheckout(NamedTuple):
    erro: dep.ErroDado
    linha: dict          # a linha da Orbe, como o leitor devolveu
    chave: str           # CNPJ do lojista, ou o EC quando não dá para saber o CNPJ


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
    """EC -> CNPJ e, por CNPJ, a linha da planilha vigente numa data.

    estrito (padrão): cadastro inconsistente é erro. Sem estrito (o fechamento, R44), o EC com cadastro inconsistente
    fica em problemas_ec e o CNPJ com linha da planilha ilegível (rejeitadas do leitor) fica em cnpj_suspeito: as
    transações deles viram PEN-REGRA-CADASTRO em vez de parar o checkout.
    """

    def __init__(self, taxas: pd.DataFrame, cfg: ConfigCheckout, estrito: bool = True, rejeitadas=()):
        self.linhas: dict[str, list[dict]] = defaultdict(list)
        self.ec_cnpj: dict[str, str] = {}
        self.problemas_ec: dict[str, str] = {}
        self.cnpj_suspeito: dict[str, str] = {}

        def problema(ec: str, mensagem: str) -> None:
            if estrito:
                raise ErroDadoCheckout(dep.CADASTRO, mensagem, do_lojista=True)
            self.problemas_ec.setdefault(ec, mensagem)

        for linha in taxas.to_dict("records"):
            self.linhas[linha["cnpj"]].append(linha)
            ec = linha["ec"]
            if ec is None:
                continue
            if self.ec_cnpj.get(ec, linha["cnpj"]) != linha["cnpj"]:
                problema(ec, f"EC {ec} aparece com dois CNPJs na planilha ({self.ec_cnpj[ec]} e {linha['cnpj']})")
            self.ec_cnpj.setdefault(ec, linha["cnpj"])
        for ec, cnpj in cfg.ec_sem_codigo.items():
            if ec in self.ec_cnpj and self.ec_cnpj[ec] != cnpj:
                problema(ec, f"EC {ec}: ec_sem_codigo diz {cnpj}, a planilha diz {self.ec_cnpj[ec]}")
            elif cnpj not in self.linhas and cnpj not in {r.cnpj for r in rejeitadas}:
                problema(ec, f"EC {ec}: CNPJ {cnpj} de ec_sem_codigo não está na planilha")
            self.ec_cnpj.setdefault(ec, cnpj)
        for r in rejeitadas:  # linha da planilha que o leitor não converteu: o lojista dela fica sob suspeita
            self.cnpj_suspeito.setdefault(r.cnpj, r.erro)
            if r.ec:
                self.ec_cnpj.setdefault(r.ec, r.cnpj)
        for ec in self.problemas_ec:
            self.ec_cnpj.pop(ec, None)

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
            raise ErroDadoCheckout(dep.VIGENCIA, f"CNPJ {cnpj}: esperada 1 linha vigente na planilha de taxas em {d}, "
                                   f"achei {len(vigentes)} ({refs})", do_lojista=True)
        return vigentes[0]


def _campo_taxa(linha_orbe: dict, cfg: ConfigCheckout) -> str:
    tipo, modalidade, parcelas = linha_orbe["tipo_lancamento"], linha_orbe["modalidade"], linha_orbe["qtd_parcelas"]
    if tipo in cfg.taxa_por_tipo:
        return cfg.taxa_por_tipo[tipo]
    if modalidade == cfg.modalidade_parcelado:
        for de, ate, campo in cfg.faixas_parcelado:
            if parcelas is not None and de <= parcelas <= ate:
                return campo
        raise ErroDadoCheckout(dep.TAXA, f"{linha_orbe['ref_origem']}: {modalidade} com {parcelas} parcelas fora das "
                               "faixas de config/checkout.yaml (taxa_parcelado)")
    if modalidade in cfg.taxa_por_modalidade:
        return cfg.taxa_por_modalidade[modalidade]
    raise ErroDadoCheckout(dep.TAXA, f"{linha_orbe['ref_origem']}: tipo {tipo!r} / modalidade {modalidade!r} sem taxa "
                           "em config/checkout.yaml")


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


def calcular_linhas(orbe: pd.DataFrame, taxas: pd.DataFrame, cfg: ConfigCheckout,
                    problemas: list[ProblemaCheckout] | None = None, rejeitadas_taxas=()) -> list[LinhaCheckout]:
    """Uma LinhaCheckout por linha da Orbe. Com problemas (o fechamento, R44), a linha cujo dado impede a regra vai
    para a lista (ErroDado) e fica de fora; sem a lista, é erro."""
    contratos = Contratos(taxas, cfg, estrito=problemas is None, rejeitadas=rejeitadas_taxas)
    resultado = []
    for l in orbe.to_dict("records"):
        try:
            resultado.append(_calcular_linha(l, contratos, cfg))
        except dep.ErroDado as e:
            if problemas is None:
                raise
            ec = l["cod_estabelecimento"]
            problemas.append(ProblemaCheckout(e, l, contratos.ec_cnpj.get(ec) or ec))
    return resultado


def _calcular_linha(l: dict, contratos: Contratos, cfg: ConfigCheckout) -> LinhaCheckout:
    # R04/R05: estorno e reversão usam a taxa vigente na data da venda (ou antecipação) original
    data_ref = l["data_venda_original"] or l["data_movimento"]
    base = dict(
        arquivo_origem=l["arquivo_origem"], ref_origem=l["ref_origem"], ec=l["cod_estabelecimento"],
        tipo_lancamento=l["tipo_lancamento"], id_referencia=l["id_referencia"], data_referencia=data_ref,
        valor_bruto=l["valor_bruto"], valor_taxa_orbe=l["valor_taxa"], taxa_aplicada=l["taxa_aplicada_pct"],
        data_movimento=l["data_movimento"],
    )
    ec = l["cod_estabelecimento"]
    if ec in contratos.problemas_ec:
        raise ErroDadoCheckout(dep.CADASTRO, contratos.problemas_ec[ec], do_lojista=True)
    cnpj = contratos.ec_cnpj.get(ec)
    if cnpj is None:  # R08
        return LinhaCheckout(**base, cnpj=None, taxa_contratada=None, origem_taxa=None,
                             comissao=None, diferenca=None, taxa_comissao=None)
    if cnpj in contratos.cnpj_suspeito:
        raise ErroDadoCheckout(dep.CADASTRO, f"a linha do CNPJ {cnpj} na planilha de taxas não pôde ser lida "
                               f"({contratos.cnpj_suspeito[cnpj]})", do_lojista=True)

    # R35: a faixa (modalidade, parcelas) sai da própria linha, inclusive a do estorno
    campo = _campo_taxa(l, cfg)
    linha_taxa = contratos.vigente(cnpj, data_ref)
    contratada, origem_taxa = linha_taxa[campo], linha_taxa["ref_origem"]
    if contratada is None:
        raise ErroDadoCheckout(dep.TAXA, f"{l['ref_origem']}: CNPJ {cnpj} sem {campo} na {origem_taxa} da "
                               "planilha de taxas", do_lojista=True)
    # R10, R32, R40: a concessão comercial muda só a comissão (a Tarvo abre mão da receita); o contrato continua
    # sendo a planilha, e é contra ele que se mede a divergência
    condicao = next((c for c in cfg.condicoes if c.cnpj == cnpj and c.vale_em(data_ref) and campo in c.taxas), None)
    taxa_comissao = condicao.taxas[campo] if condicao is not None else contratada

    comissao = dinheiro(l["valor_bruto"] * taxa_comissao / 100)  # R01, R02
    diferenca = None
    if l["taxa_aplicada_pct"] != contratada:  # R03, R37: compara taxas, nunca valores (P03); estorno entra com sinal
        diferenca = dinheiro(l["valor_bruto"] * (l["taxa_aplicada_pct"] - contratada) / 100)
    return LinhaCheckout(**base, cnpj=cnpj, taxa_contratada=contratada, origem_taxa=origem_taxa,
                         comissao=comissao, diferenca=diferenca, taxa_comissao=taxa_comissao,
                         concessao=condicao.regra if condicao is not None else None)


# ---------------------------------------------------------------- itens de saída

def _soma(valores) -> Decimal:
    return sum(valores, ZERO)


def _competencia_seguinte(competencia: str) -> str:
    """AAAA-MM do mês seguinte."""
    ano, mes = (int(p) for p in competencia.split("-"))
    return f"{ano + mes // 12:04d}-{mes % 12 + 1:02d}"


def taxa_concessao(cnpj: str, cfg: ConfigCheckout) -> str:
    """Taxa(s) da concessão do lojista como texto ("0%"), das condições especiais do config."""
    valores = sorted({v for c in cfg.condicoes if c.cnpj == cnpj for v in c.taxas.values()})
    return " ou ".join(f"{v.normalize():f}".replace(".", ",") + "%" for v in valores) or "a taxa da concessão"


def _rascunho_orbe() -> str:
    """Onde fica o rascunho de contestação da Orbe (R29), como o motivo da pendência o cita: <pasta>/orbe.md."""
    from tarvo.contestacao import ARQUIVO_ORBE, carregar_config  # import tardio: contestacao importa este módulo
    return f"{carregar_config().pasta}/{ARQUIVO_ORBE[0]}"


def comissao_contratada(l: LinhaCheckout) -> Decimal:
    """Comissão da linha pela taxa do contrato (a planilha), arredondada (R01, R02)."""
    return dinheiro(l.valor_bruto * l.taxa_contratada / 100)


def _pendencia_devolucao(cnpj: str, divergentes: list[LinhaCheckout], cfg: ConfigCheckout) -> ItemSaida:
    """R03, R25, R32: a contraparte cobrou diferente do contrato; o lojista é ressarcido.
    R45: o que se devolve é o que saiu do bolso do lojista, transação a transação: o valor_taxa descontado pela Orbe
    menos a comissão pela taxa contratada. A divergência (DIV-CHK) continua pela fórmula da R03."""
    origens = [(l.arquivo_origem, l.ref_origem, l.valor_taxa_orbe - comissao_contratada(l)) for l in divergentes]
    return ItemSaida(f"PEN-DEVOL-CHK-{cnpj}", PENDENCIAS.nome,
                     {"tipo": "DEVOLUCAO_LOJISTA", "ref_origem": [l.ref_origem for l in divergentes],
                      "motivo": texto_saida(MOTIVO_DEVOLUCAO.format(rascunho=_rascunho_orbe())),
                      "quem_decide": cfg.quem_decide["devolucao_lojista"]},
                     _soma(o[2] for o in origens), origens)


def _pendencia_concessao(cnpj: str, linhas: list[LinhaCheckout], cfg: ConfigCheckout) -> ItemSaida:
    """R10, R32, R38, R41: a Tarvo devolve ao lojista o que a Orbe descontou nas transações da concessão, menos a
    comissão da Tarvo pela concessão (R45: o descontado de fato, transação a transação). Custo da Tarvo, separado das
    divergências. Se a mesma linha também diverge do contrato, a parte acima do contrato (valor_taxa menos a comissão
    contratada) já está na PEN-DEVOL-CHK e aqui fica só a comissão contratada menos a da concessão (P23)."""
    regras = sorted({l.concessao for l in linhas})
    origens = [(l.arquivo_origem, l.ref_origem,
                (comissao_contratada(l) if l.divergente else l.valor_taxa_orbe) - l.comissao) for l in linhas]
    return ItemSaida(f"PEN-CONCESSAO-CHK-{cnpj}", PENDENCIAS.nome,
                     {"tipo": "DEVOLUCAO_CONCESSAO", "ref_origem": [l.ref_origem for l in linhas],
                      "motivo": texto_saida(MOTIVO_CONCESSAO.format(regra=", ".join(regras), rascunho=_rascunho_orbe(),
                                                                    taxa=taxa_concessao(cnpj, cfg))),
                      "quem_decide": cfg.quem_decide["devolucao_concessao"]},
                     _soma(o[2] for o in origens), origens)


def _primeiro_dia(competencia: str) -> date:
    ano, mes = (int(p) for p in competencia.split("-"))
    return date(ano, mes, 1)


def pico_antecipacao(doc: list[LinhaCheckout]) -> tuple[date, Decimal, Decimal] | None:
    """P26: (data, antecipado, vendido) acumulados desde a primeira transação, na data em que o antecipado mais passa
    as vendas; None se nunca passa. O antecipado é líquido das reversões já feitas até a data (a reversão posterior
    não apaga o pico). Empate: a primeira data."""
    antecipado = vendido = ZERO
    pico = None
    for d in sorted({l.data_movimento for l in doc}):
        do_dia = [l for l in doc if l.data_movimento == d]
        antecipado += _soma(l.valor_bruto for l in do_dia if l.tipo_lancamento in (ANTECIPACAO, REVERSAO))
        vendido += _soma(l.valor_bruto for l in do_dia if l.tipo_lancamento == VENDA)
        if antecipado > vendido and (pico is None or antecipado - vendido > pico[1] - pico[2]):
            pico = (d, antecipado, vendido)
    return pico


def _alertas_antecipacao(grupos: dict[str, list[LinhaCheckout]], contratos, competencia: str, cfg: ConfigCheckout,
                         ecs_anteriores: frozenset[str] | None) -> list[ItemSaida]:
    """P26 (R33, R43): alerta informativo quando lojista sem histórico, em alguma data do mês, tem o antecipado
    acumulado desde a primeira transação acima das vendas acumuladas até a data (o pico).

    Reversões posteriores não apagam o alerta: o motivo cita cada reversão (antecipação revertida, data e id da
    reversão) e mostra o saldo líquido do fim do mês.
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
        reversoes = [l for l in doc if l.tipo_lancamento == REVERSAO]
        vendido = _soma(l.valor_bruto for l in doc if l.tipo_lancamento == VENDA)
        pico = pico_antecipacao(doc)
        if pico is None:
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
        lista = [f"{l.id_referencia} revertida em {l.data_movimento.isoformat()} ({l.ref_origem})"
                 for l in sorted(reversoes, key=lambda l: (l.data_movimento, l.ref_origem))]
        texto_reversoes = (TEXTO_ALERTA_REVERSOES.format(lista=", ".join(lista)) if lista
                           else TEXTO_ALERTA_SEM_REVERSAO)
        itens.append(ItemSaida(
            f"PEN-ALERTA-ANTEC-{chave}", PENDENCIAS.nome,
            {"tipo": "ALERTA_ANTECIPACAO", "ref_origem": [l.ref_origem for l in antecipacoes],
             "motivo": texto_saida(MOTIVO_ALERTA.format(
                 historico=historico, pico=pico[0].isoformat(), antecipado_pico=pico[1], vendido_pico=pico[2],
                 reversoes=texto_reversoes, liquido=antecipado + _soma(l.valor_bruto for l in reversoes),
                 vendido=vendido, antecipado=antecipado)),
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


EFEITO_ANTERIOR = ("o alerta de antecipação (P26) usou o histórico do próprio mês, sem a competência anterior - "
                   "nenhum valor muda")
EFEITO_LOJISTA = ("as {n} transações do lojista ({quem}) ficaram fora de comissão, nota e divergência - valor = taxa "
                  "cobrada pela Orbe nelas")
EFEITO_TRANSACAO = ("a transação ficou fora de comissão, nota e divergência; o checkout do lojista (CNPJ {cnpj}) saiu "
                    "PROVISÓRIO - valor = taxa cobrada pela Orbe na transação")


def _pendencias_regra(orbe: pd.DataFrame, problemas: list[ProblemaCheckout],
                      fora: dict[str, list[str]]) -> list[ItemSaida]:
    """R44: PEN-REGRA-<tipo>-CHK-<CNPJ ou EC> por lojista com cadastro ou contrato que impede a regra (todas as
    transações dele) e PEN-REGRA-<tipo>-CHK-<id_transacao> por transação com dado que impede a regra."""
    por_ref = {(l["arquivo_origem"], l["ref_origem"]): l for l in orbe.to_dict("records")}
    do_lojista: dict[str, list[ProblemaCheckout]] = defaultdict(list)
    itens = []
    for p in problemas:
        if p.erro.do_lojista or p.chave in fora:
            do_lojista[p.chave].append(p)
            continue
        l = p.linha
        itens.append(dep.pendencia_regra(
            p.erro.tipo, f"CHK-{l['ref_origem']}", str(p.erro), EFEITO_TRANSACAO.format(cnpj=p.chave), l["valor_taxa"],
            [(l["arquivo_origem"], l["ref_origem"], l["valor_taxa"])]))
    for chave, ps in sorted(do_lojista.items()):
        refs = {(p.linha["arquivo_origem"], p.linha["ref_origem"]) for p in ps} | set(fora.get(chave, ()))
        origens = [(a, r, por_ref[(a, r)]["valor_taxa"]) for a, r in por_ref if (a, r) in refs]
        quem = f"CNPJ {chave}" if len(chave) == 14 else f"EC {chave}"
        dado = " | ".join(dict.fromkeys(str(p.erro) for p in ps))
        itens.append(dep.pendencia_regra(ps[0].erro.tipo, f"CHK-{chave}", dado,
                                         EFEITO_LOJISTA.format(n=len(origens), quem=quem),
                                         _soma(o[2] for o in origens), origens))
    return itens


def calcular_checkout(orbe: pd.DataFrame, taxas: pd.DataFrame, competencia: str,
                      cfg: ConfigCheckout, ecs_anteriores: frozenset[str] | None = None,
                      rejeitadas_taxas=()) -> list[ItemSaida]:
    """Itens do checkout. Lojista ou transação com dado que impede a regra fica fora e vira PEN-REGRA (R44)."""
    problemas: list[ProblemaCheckout] = []
    linhas = calcular_linhas(orbe, taxas, cfg, problemas, rejeitadas_taxas)
    contratos = Contratos(taxas, cfg, estrito=False, rejeitadas=rejeitadas_taxas)
    lojistas_fora = {p.chave for p in problemas if p.erro.do_lojista}
    fora: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for l in linhas:
        if (l.cnpj or l.ec) in lojistas_fora:
            fora[l.cnpj or l.ec].append((l.arquivo_origem, l.ref_origem))
    validas = [l for l in linhas if (l.cnpj or l.ec) not in lojistas_fora]
    itens = gerar_itens(validas, contratos.nome, competencia, cfg, contratos, ecs_anteriores)
    provisorios = {p.chave for p in problemas if p.chave not in lojistas_fora}
    if provisorios:
        itens = dep.marcar_provisorio(itens, provisorios)
    return itens + _pendencias_regra(orbe, problemas, {c: fora.get(c, []) for c in lojistas_fora})


def ecs_competencia_anterior(entradas: Entradas) -> frozenset[str] | None:
    """ECs com transação nos arquivos da Orbe da competência anterior, se a pasta dela existir ao lado desta (P26).

    Linha ilegível da competência anterior ainda conta o EC dela; arquivo ilegível é ErroDadoCheckout (ANTERIOR)."""
    from tarvo.cli import ErroEntrada, localizar_pela_config
    from tarvo.leitores.orbe import ler_orbe_parcial
    from tarvo.remessa import pasta_anterior

    orbe = entradas.arquivos["orbe"]
    pasta = pasta_anterior((orbe[0] if isinstance(orbe, tuple) else orbe).parent, entradas.competencia)
    if pasta is None:
        return None
    try:
        arquivos = localizar_pela_config(pasta)
    except ErroEntrada:
        return None
    try:
        leitura = ler_orbe_parcial(arquivos["orbe"])
    except (ValueError, OSError) as e:
        raise ErroDadoCheckout(dep.ANTERIOR, f"Orbe da competência anterior ({pasta.name}) ilegível: {e}") from None
    return frozenset(leitura.quadro["cod_estabelecimento"]) | {r.ec for r in leitura.rejeitadas if r.ec}


def pendencias_arquivos_orbe(orbe: pd.DataFrame, repetidas, competencia: str, cfg: ConfigCheckout) -> list[ItemSaida]:
    """Pendências informativas (valor 0,00) da leitura de vários arquivos da Orbe (O05); não mudam nenhum valor.

    P27: id_transacao igual em dois arquivos, contado uma vez. P28: estorno ou reversão de transação do mesmo mês
    que não está em nenhum arquivo da Orbe (a de mês anterior é o caso normal da R04 e não abre pendência).
    """
    itens = []
    for r in repetidas:
        itens.append(ItemSaida(
            f"PEN-REPET-CHK-{r.ref_origem}", PENDENCIAS.nome,
            {"tipo": "TRANSACAO_REPETIDA", "ref_origem": [r.ref_origem],
             "motivo": texto_saida(MOTIVO_REPETIDA.format(ref=r.ref_origem, mantido=r.arquivo_mantido,
                                                          n_mantida=r.linha_mantida, repetido=r.arquivo_repetido,
                                                          n_repetida=r.linha_repetida)),
             "quem_decide": cfg.quem_decide["transacao_repetida"]},
            ZERO, [(r.arquivo_mantido, r.ref_origem, ZERO), (r.arquivo_repetido, r.ref_origem, ZERO)]))
    ids = set(orbe["ref_origem"])
    for l in orbe.to_dict("records"):
        original, data = l["id_referencia"], l["data_venda_original"]
        if original and data and data.strftime("%Y-%m") == competencia and original not in ids:
            itens.append(ItemSaida(
                f"PEN-SEMORIG-CHK-{l['ref_origem']}", PENDENCIAS.nome,
                {"tipo": "REFERENCIA_NAO_ENCONTRADA", "ref_origem": [l["ref_origem"]],
                 "motivo": texto_saida(MOTIVO_SEM_ORIGINAL.format(tipo=l["tipo_lancamento"], data=l["data_movimento"],
                                                                  original=original)),
                 "quem_decide": cfg.quem_decide["referencia_nao_encontrada"]},
                ZERO, [(l["arquivo_origem"], l["ref_origem"], ZERO)]))
    return itens


def checkout(entradas: Entradas, config=CONFIG_CHECKOUT) -> list[ItemSaida]:
    """Módulo do fechamento: itens da linha CHECKOUT a partir da Orbe e da planilha de taxas.

    Sem uma das duas (fonte bloqueada), não gera nada; com um arquivo de ajustes da Orbe bloqueado, os itens saem
    marcados como provisórios (R44)."""
    if not dep.gera("checkout", entradas):
        return []
    cfg = carregar_config(config)
    rejeitadas_taxas = entradas.rejeitadas.get("taxas", ())
    anterior: list[ItemSaida] = []
    try:
        ecs_anteriores = ecs_competencia_anterior(entradas)
    except dep.ErroDado as e:  # R44: sem a competência anterior, o alerta usa a heurística do mês (P26)
        ecs_anteriores = None
        anterior = [dep.pendencia_regra(e.tipo, "CHK", str(e), EFEITO_ANTERIOR, ZERO,
                                        [(entradas.competencia, "competencia anterior", ZERO)])]
    itens = (calcular_checkout(entradas.orbe, entradas.taxas, entradas.competencia, cfg, ecs_anteriores,
                               rejeitadas_taxas)
             + pendencias_arquivos_orbe(entradas.orbe, entradas.orbe_repetidas, entradas.competencia, cfg) + anterior)
    if dep.provisorio("checkout", entradas):
        return dep.marcar_provisorio(itens)
    # R44: transação da Orbe que o leitor não converteu deixa o checkout do lojista dela provisório
    ecs = {r.ec for r in entradas.rejeitadas.get("orbe", ()) if r.ec}
    if ecs:
        mapa = Contratos(entradas.taxas, cfg, estrito=False, rejeitadas=rejeitadas_taxas).ec_cnpj
        cnpjs = {mapa[ec] for ec in ecs if ec in mapa}
        if cnpjs:
            itens = dep.marcar_provisorio(itens, cnpjs)
    return itens
