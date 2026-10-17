"""Linha CHECKOUT (Orbe): comissão pela taxa contratada, divergências, notas e pendências por lojista.

Regras do HIPOTESES.md, seção 1: R01 a R10, R25, R30, R32, R33, R35 a R41, R43 a R48; premissas P23, P26 e P27. Mapeamentos e condições especiais em config/checkout.yaml.
A bandeira da Orbe não entra em nada: nem na taxa nem no vínculo do estorno com a venda, que é pela referência (R47).
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
from tarvo.resumo import brl
from tarvo.saida import COMISSOES, DIVERGENCIAS, NOTAS, PENDENCIAS, ItemSaida, Origem, texto_saida

if TYPE_CHECKING:
    from tarvo.fechamento import Entradas

CONFIG_CHECKOUT = Path(__file__).resolve().parents[2] / "config" / "checkout.yaml"
LINHA_NEGOCIO = "CHECKOUT"
ZERO = Decimal("0.00")
VENDA, ANTECIPACAO, REVERSAO, ESTORNO = "VENDA", "ANTECIPACAO", "REVERSAO ANTECIPACAO", "ESTORNO"  # tipos da Orbe

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
    "{tipo} de {data} referente a {original}, transação do mesmo mês que não está em nenhum arquivo da Orbe: o ajuste "
    "entra na comissão e na nota pelo valor que veio, com a taxa contratada da data da venda original e a faixa da "
    "própria linha (R35, R48) - {efeito} - próximo passo: a Helena pede a venda original {original} à Orbe (R48)"
)
EFEITO_SEM_ORIGINAL = "valor = efeito do ajuste na comissão do lojista (CNPJ {cnpj}): R$ {valor}"
EFEITO_SEM_ORIGINAL_FORA = "valor 0,00: a linha não entrou na comissão ({motivo})"
MOTIVO_CORRECAO = (
    "correção da Orbe (P27, critério nosso pela Helena às 13h34): o id_transacao {ref} veio em {antes} (linha física "
    "{n_antes}) e de novo, com dados diferentes, em {depois} (linha física {n_depois}) - a linha de {depois} substitui "
    "a de {antes}, porque é a correção, e o resto dos arquivos foi lido normalmente - antes → depois: {campos} - "
    "efeito na comissão: R$ {com_antes} → R$ {com_depois} (R$ {efeito}) - efeito na nota: {notas} - valor = efeito na "
    "comissão (no rastro, a comissão da linha nova e a da linha substituída com o sinal trocado) - próximo passo: a "
    "Helena confirma a correção com a Orbe"
)
MOTIVO_APOS_APROVACAO = (
    "ajuste de {mes} recebido depois da aprovação, entra em {competencia} (regra 13h34, R46): {n} linha(s) de "
    "{arquivo} com data_movimento de {mes} ({refs}) entraram na comissão e na nota de {competencia}, pela taxa da data "
    "de referência de cada linha - o fechamento de {mes}, já aprovado, não é reaberto - informativa: valor 0,00, o "
    "efeito já está nos itens do mês - próximo passo: a Helena confere as linhas no fechamento de {competencia}"
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
    rotulo_taxa: dict[str, str] = field(default_factory=dict)             # coluna de taxa -> texto do rastro (O06)


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
        rotulo_taxa={_str_cfg(c, "rotulo_taxa"): _str_cfg(r, "rotulo_taxa")
                     for c, r in (bruto.get("rotulo_taxa") or {}).items()},
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
    campo_taxa: str | None = None         # coluna da planilha usada (taxa_debito, taxa_parc_2_6, ...)
    vigencia_taxa: date | None = None     # início de vigência da linha da planilha usada (None: sem início)

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
                         concessao=condicao.regra if condicao is not None else None,
                         campo_taxa=campo, vigencia_taxa=linha_taxa["vigencia_inicio"])


# ---------------------------------------------------------------- regra e detalhe do rastro (O06)

def pct_texto(v: Decimal) -> str:
    """Taxa em pontos percentuais como texto do rastro: 3.19 vira "3,19"; 0 vira "0"; 2.105 vira "2,105"."""
    if v == 0:
        return "0"
    q = v.quantize(Decimal("0.01"))
    return format(q if q == v else v.normalize(), "f").replace(".", ",")


def _contrato(l: LinhaCheckout, cfg: ConfigCheckout) -> str:
    rotulo = cfg.rotulo_taxa.get(l.campo_taxa, l.campo_taxa)
    desde = f"vigente desde {l.vigencia_taxa.isoformat()}" if l.vigencia_taxa else "sem início de vigência"
    return f"{rotulo}, {desde} ({l.origem_taxa} da planilha)"


def regra_linha(l: LinhaCheckout, cfg: ConfigCheckout, nome: str) -> tuple[str, str]:
    """(regra, detalhe) da comissão de uma transação, para o rastro.csv (O06). Só texto: nenhuma conta."""
    if l.tipo_lancamento == ESTORNO:  # R04, R35: taxa da data da venda, faixa da própria linha; vínculo pela referência
        regra, inicio = "R35", (f"estorno pela venda {l.id_referencia} de {l.data_referencia.isoformat()} a "
                                f"{pct_texto(l.taxa_comissao)}% - faixa da própria linha - taxa contratada ")
    elif l.tipo_lancamento == REVERSAO:  # R05
        regra, inicio = "R05", (f"reversão da antecipação {l.id_referencia} de {l.data_referencia.isoformat()} a "
                                f"{pct_texto(l.taxa_comissao)}% - taxa contratada ")
    else:
        regra, inicio = ("R05" if l.tipo_lancamento == ANTECIPACAO else "R01"), "taxa contratada "
    detalhe = f"{inicio}{pct_texto(l.taxa_contratada)}% {_contrato(l, cfg)}"
    if l.concessao is not None and l.taxa_comissao != l.taxa_contratada:  # R10, R32, R40
        isencao = "isenção" if l.taxa_comissao == 0 else "taxa reduzida"
        detalhe = f"{isencao} (concessão {nome}, {l.concessao}) {pct_texto(l.taxa_comissao)}% - contrato: " + detalhe
        regra = "R32"
    return regra, texto_saida(detalhe)


def origem_comissao(l: LinhaCheckout, cfg: ConfigCheckout, nome: str) -> Origem:
    """Linha do rastro da comissão de uma transação, com a regra e o detalhe (O06)."""
    return Origem(l.arquivo_origem, l.ref_origem, l.comissao, *regra_linha(l, cfg, nome))


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
    origens = [(l.arquivo_origem, l.ref_origem, l.valor_taxa_orbe - comissao_contratada(l), "R45",
                f"valor_taxa descontado pela Orbe R$ {brl(l.valor_taxa_orbe)} a {pct_texto(l.taxa_aplicada)}% menos a "
                f"comissão pela taxa contratada R$ {brl(comissao_contratada(l))} a {pct_texto(l.taxa_contratada)}%")
               for l in divergentes]
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
    def detalhe(l: LinhaCheckout) -> str:
        base = (f"comissão pela taxa contratada R$ {brl(comissao_contratada(l))} a {pct_texto(l.taxa_contratada)}% "
                "(a parte acima do contrato está na PEN-DEVOL-CHK)" if l.divergente
                else f"valor_taxa descontado pela Orbe R$ {brl(l.valor_taxa_orbe)} a {pct_texto(l.taxa_aplicada)}%")
        return f"{base} menos a comissão da concessão ({l.concessao}) R$ {brl(l.comissao)} a {pct_texto(l.taxa_comissao)}%"

    origens = [(l.arquivo_origem, l.ref_origem,
                (comissao_contratada(l) if l.divergente else l.valor_taxa_orbe) - l.comissao, "R45", detalhe(l))
               for l in linhas]
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
            ZERO, [(l.arquivo_origem, l.ref_origem, ZERO, "P26",
                    f"antecipação de {l.data_movimento.isoformat()}, R$ {brl(l.valor_bruto)} brutos - alerta "
                    "informativo, não muda nenhum valor") for l in antecipacoes]))
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
        rastro_comissao = [origem_comissao(l, cfg, nome) for l in doc]
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
                                   l.diferenca, [(l.arquivo_origem, l.ref_origem, l.diferenca,
                                                  "R37" if l.tipo_lancamento == ESTORNO else "R03",
                                                  texto_saida(f"bruto R$ {brl(l.valor_bruto)} × (taxa aplicada pela "
                                                              f"Orbe {pct_texto(l.taxa_aplicada)}% - contratada "
                                                              f"{pct_texto(l.taxa_contratada)}% {_contrato(l, cfg)})"))]))
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
                               [(l.arquivo_origem, l.ref_origem, l.valor_taxa_orbe,
                                 cfg.faturamento_retroativo.get(ec, "R08"),
                                 f"valor_taxa cobrado pela Orbe a {pct_texto(l.taxa_aplicada)}% - EC {ec} sem contrato "
                                 "vigente: sem comissão, nota e divergência (R08, R36)") for l in doc]))

    if contratos is not None:  # P26: alerta informativo de antecipação
        grupos = {**{c: d for c, d in por_cnpj.items()},
                  **{cfg.cnpj_identificacao.get(ec, ec): d for ec, d in sem_contrato.items()}}
        itens += _alertas_antecipacao(grupos, contratos, competencia, cfg, ecs_anteriores)
    return itens


EFEITO_ANTERIOR = ("o alerta de antecipação (P26) usou o histórico do próprio mês, sem a competência anterior - "
                   "nenhum valor muda")
EFEITO_LOJISTA = ("as {n} transações do lojista ({quem}) ficaram fora de comissão, nota e divergência - valor = taxa "
                  "cobrada pela Orbe nelas")
DETALHE_REGRA = "valor_taxa cobrado pela Orbe - transação fora por erro de dado ({tipo})"
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
            [(l["arquivo_origem"], l["ref_origem"], l["valor_taxa"])], detalhe=DETALHE_REGRA.format(tipo=p.erro.tipo.lower())))
    for chave, ps in sorted(do_lojista.items()):
        refs = {(p.linha["arquivo_origem"], p.linha["ref_origem"]) for p in ps} | set(fora.get(chave, ()))
        origens = [(a, r, por_ref[(a, r)]["valor_taxa"]) for a, r in por_ref if (a, r) in refs]
        quem = f"CNPJ {chave}" if len(chave) == 14 else f"EC {chave}"
        dado = " | ".join(dict.fromkeys(str(p.erro) for p in ps))
        itens.append(dep.pendencia_regra(ps[0].erro.tipo, f"CHK-{chave}", dado,
                                         EFEITO_LOJISTA.format(n=len(origens), quem=quem),
                                         _soma(o[2] for o in origens), origens,
                                         detalhe=DETALHE_REGRA.format(tipo=ps[0].erro.tipo.lower())))
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


def _comissoes_por_transacao(itens) -> dict[tuple[str, str], tuple[str, Origem]]:
    """(arquivo, id_transacao) -> (CNPJ, linha do rastro) de cada transação que entrou numa COM-CHK."""
    return {(o.arquivo_origem, o.ref_origem): (i.campos["cnpj"], o)
            for i in itens if i.id_saida.startswith("COM-CHK-") for o in i.origens}


def _valor_texto(v) -> str:
    if v is None:
        return "vazio"
    return v.isoformat() if isinstance(v, date) else str(v)


def _efeito_nota(deltas: dict[str, Decimal], totais: dict[str, Decimal]) -> str:
    """Nota de cada lojista afetado, antes e depois da correção (R06: comissão zero ou negativa não emite nota)."""
    textos = []
    for cnpj, delta in sorted(deltas.items()):
        depois = totais.get(cnpj, ZERO)
        antes = depois - delta
        textos.append(f"NF-CHK-{cnpj}: R$ {brl(max(antes, ZERO))} → R$ {brl(max(depois, ZERO))}"
                      + (" (comissão zero ou negativa não emite nota, R06)" if min(antes, depois) <= 0 else ""))
    return " - ".join(textos) or "nenhum (a transação não entra na comissão, nem antes nem depois)"


def _pendencia_correcao(c, comissoes, totais: dict[str, Decimal], fora: set[str], contratos: Contratos | None,
                        cfg: ConfigCheckout) -> ItemSaida:
    """P27: id_transacao corrigido num arquivo posterior. A linha nova já está na comissão (o leitor a pôs no lugar
    da antiga); a pendência mostra antes → depois e vale o efeito na comissão: no rastro, a comissão da linha nova e a
    da substituída com o sinal trocado."""
    depois = comissoes.get((c.arquivo_depois, c.ref_origem))
    antes = None
    if contratos is not None:
        try:
            l = _calcular_linha(c.antes, contratos, cfg)
        except dep.ErroDado:
            l = None
        if l is not None and l.cnpj is not None and l.cnpj not in fora:
            antes = (l.cnpj, origem_comissao(l, cfg, contratos.nome(l.cnpj)))
    com_antes = antes[1].valor if antes else ZERO
    com_depois = depois[1].valor if depois else ZERO
    deltas: dict[str, Decimal] = defaultdict(lambda: ZERO)
    if depois:
        deltas[depois[0]] += com_depois
    if antes:
        deltas[antes[0]] -= com_antes
    fora_da_comissao = "a linha não entra na comissão (lojista sem contrato ou fora por erro de dado)"
    origens = [
        (c.arquivo_depois, c.ref_origem, com_depois, "P27",
         "comissão pela linha corrigida - " + (depois[1].detalhe if depois else fora_da_comissao)),
        (c.arquivo_antes, c.ref_origem, -com_antes, "P27",
         "comissão da linha substituída, com o sinal trocado - " + (antes[1].detalhe if antes else fora_da_comissao)),
    ]
    campos = ", ".join(f"{campo} {_valor_texto(c.antes[campo])} → {_valor_texto(c.depois[campo])}"
                       for campo in c.campos)
    motivo = MOTIVO_CORRECAO.format(ref=c.ref_origem, antes=c.arquivo_antes, n_antes=c.linha_antes,
                                    depois=c.arquivo_depois, n_depois=c.linha_depois, campos=campos,
                                    com_antes=brl(com_antes), com_depois=brl(com_depois),
                                    efeito=brl(com_depois - com_antes), notas=_efeito_nota(deltas, totais))
    return ItemSaida(f"PEN-CORRECAO-ORBE-{c.ref_origem}", PENDENCIAS.nome,
                     {"tipo": "CORRECAO_ORBE", "ref_origem": [c.ref_origem], "motivo": texto_saida(motivo),
                      "quem_decide": cfg.quem_decide["correcao_orbe"]},
                     com_depois - com_antes, origens)


def pendencias_arquivos_orbe(orbe: pd.DataFrame, repetidas, competencia: str, cfg: ConfigCheckout,
                             itens: list[ItemSaida] = (), taxas: pd.DataFrame | None = None, correcoes=(),
                             rejeitadas_taxas=()) -> list[ItemSaida]:
    """Pendências da leitura de vários arquivos da Orbe (O05). itens: os do checkout, já calculados (a comissão de
    cada transação sai das COM-CHK; nenhuma conta nova de comissão do mês).

    P27: id_transacao igual em dois arquivos, contado uma vez (PEN-REPET-CHK, 0,00); com dados diferentes, a linha do
    arquivo posterior substituiu a anterior (PEN-CORRECAO-ORBE, valor = efeito na comissão). R48: estorno ou reversão
    de transação do mesmo mês que não está em nenhum arquivo da Orbe entra pelo valor que veio (PEN-SEMORIG-CHK,
    valor = efeito na comissão; a de mês anterior é o caso normal da R04 e não abre pendência). R46: linha com
    data_movimento de mês anterior recebida na pasta do mês entra no mês (PEN-TARDIO-CHK, informativa, 0,00).
    """
    comissoes = _comissoes_por_transacao(itens)
    totais = {i.campos["cnpj"]: i.valor_reportado for i in itens if i.id_saida.startswith("COM-CHK-")}
    fora = {i.id_saida.rsplit("-CHK-", 1)[1] for i in itens
            if i.id_saida.startswith("PEN-REGRA-") and "-CHK-" in i.id_saida}
    contratos = Contratos(taxas, cfg, estrito=False, rejeitadas=rejeitadas_taxas) if taxas is not None else None
    resultado = []
    for r in repetidas:
        resultado.append(ItemSaida(
            f"PEN-REPET-CHK-{r.ref_origem}", PENDENCIAS.nome,
            {"tipo": "TRANSACAO_REPETIDA", "ref_origem": [r.ref_origem],
             "motivo": texto_saida(MOTIVO_REPETIDA.format(ref=r.ref_origem, mantido=r.arquivo_mantido,
                                                          n_mantida=r.linha_mantida, repetido=r.arquivo_repetido,
                                                          n_repetida=r.linha_repetida)),
             "quem_decide": cfg.quem_decide["transacao_repetida"]},
            ZERO, [(r.arquivo_mantido, r.ref_origem, ZERO, "P27", "cópia mantida, contada uma vez"),
                   (r.arquivo_repetido, r.ref_origem, ZERO, "P27", "cópia repetida com a linha igual, não contada")]))
    for c in correcoes:
        resultado.append(_pendencia_correcao(c, comissoes, totais, fora, contratos, cfg))

    registros = orbe.to_dict("records")
    ids = set(orbe["ref_origem"])
    for l in registros:
        original, data = l["id_referencia"], l["data_venda_original"]
        if original and data and data.strftime("%Y-%m") == competencia and original not in ids:
            par = comissoes.get((l["arquivo_origem"], l["ref_origem"]))
            if par is not None:
                cnpj, o = par
                valor, efeito = o.valor, EFEITO_SEM_ORIGINAL.format(cnpj=cnpj, valor=brl(o.valor))
                detalhe = f"{o.detalhe} - venda original {original} não encontrada nos arquivos da Orbe"
            else:
                valor = ZERO
                efeito = EFEITO_SEM_ORIGINAL_FORA.format(motivo="lojista sem contrato ou fora por erro de dado: ver "
                                                                "PEN-SEMCONTRATO ou PEN-REGRA")
                detalhe = f"venda original {original} não encontrada - a linha não entrou na comissão"
            resultado.append(ItemSaida(
                f"PEN-SEMORIG-CHK-{l['ref_origem']}", PENDENCIAS.nome,
                {"tipo": "REFERENCIA_NAO_ENCONTRADA", "ref_origem": [l["ref_origem"]],
                 "motivo": texto_saida(MOTIVO_SEM_ORIGINAL.format(tipo=l["tipo_lancamento"], data=l["data_movimento"],
                                                                  original=original, efeito=efeito)),
                 "quem_decide": cfg.quem_decide["referencia_nao_encontrada"]},
                valor, [(l["arquivo_origem"], l["ref_origem"], valor, "R48", detalhe)]))

    inicio = _primeiro_dia(competencia)
    tardias: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for l in registros:  # R46: ajuste de mês já aprovado, recebido depois, entra no mês atual
        if l["data_movimento"] < inicio:
            tardias[(l["arquivo_origem"], l["data_movimento"].strftime("%Y-%m"))].append(l)
    for (arquivo, mes), linhas in sorted(tardias.items()):
        texto = f"ajuste de {mes} recebido depois da aprovação, entra em {competencia} (regra 13h34)"
        resultado.append(ItemSaida(
            f"PEN-TARDIO-CHK-{mes}-{dep.id_saida_seguro(arquivo)}", PENDENCIAS.nome,
            {"tipo": "AJUSTE_APOS_APROVACAO", "ref_origem": [l["ref_origem"] for l in linhas],
             "motivo": texto_saida(MOTIVO_APOS_APROVACAO.format(
                 mes=mes, competencia=competencia, n=len(linhas), arquivo=arquivo,
                 refs=", ".join(f"{l['ref_origem']} de {l['data_movimento'].isoformat()}" for l in linhas))),
             "quem_decide": cfg.quem_decide["ajuste_apos_aprovacao"]},
            ZERO, [(arquivo, l["ref_origem"], ZERO, "R46", texto) for l in linhas]))
    return resultado


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
                                        [(entradas.competencia, "competencia anterior", ZERO)],
                                        detalhe="competência anterior ilegível - valor 0,00")]
    itens = (calcular_checkout(entradas.orbe, entradas.taxas, entradas.competencia, cfg, ecs_anteriores,
                               rejeitadas_taxas)
             + anterior)
    itens += pendencias_arquivos_orbe(entradas.orbe, entradas.orbe_repetidas, entradas.competencia, cfg, itens,
                                      entradas.taxas, entradas.orbe_correcoes, rejeitadas_taxas)
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
