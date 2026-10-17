"""Contrato entre os módulos e a escrita de saida/.

Cada módulo (checkout, remessa, bancos) devolve um ResultadoModulo com
linhas destes tipos. Ninguém escreve CSV direto: quem escreve é
core/saida.py, que numera id_saida e grava o rastro.csv.

Regra do rastro: a soma de `valor` dos itens de `rastro` de cada linha
tem que ser igual ao número reportado (`valor_reportado`), ao centavo.
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

CHECKOUT = "CHECKOUT"
REMESSA = "REMESSA"
AURORA = "AURORA"
MERIDIANO = "MERIDIANO"
REGRA, IA, HUMANO = "REGRA", "IA", "HUMANO"


@dataclass
class ItemRastro:
    arquivo_origem: str
    ref_origem: str
    valor: Decimal


@dataclass
class Comissao:
    """Uma linha por lojista x linha de negócio."""
    cnpj: str
    lojista: str
    linha_negocio: str
    comissao_brl: Decimal
    qtd_operacoes: int = 0
    valor_bruto_brl: Decimal = Decimal("0")
    rastro: list[ItemRastro] = field(default_factory=list)

    ARQUIVO = "comissoes_por_lojista"
    PREFIXO = "COM"
    COLUNAS = ["cnpj", "lojista", "linha_negocio", "comissao_brl"]
    EXTRAS = ["qtd_operacoes", "valor_bruto_brl"]

    @property
    def valor_reportado(self) -> Decimal:
        return self.comissao_brl


@dataclass
class Divergencia:
    """Uma linha por transação/operação com taxa aplicada != contratada."""
    cnpj: str
    linha_negocio: str
    ref_origem: str
    taxa_contratada_pct: Decimal
    taxa_aplicada_pct: Decimal
    diferenca_brl: Decimal
    data: date | None = None
    lojista: str = ""
    valor_base_brl: Decimal = Decimal("0")
    descricao: str = ""
    rastro: list[ItemRastro] = field(default_factory=list)

    ARQUIVO = "divergencias_taxa"
    PREFIXO = "DIV"
    COLUNAS = ["cnpj", "linha_negocio", "ref_origem", "taxa_contratada_pct", "taxa_aplicada_pct", "diferenca_brl"]
    EXTRAS = ["data", "lojista", "valor_base_brl", "descricao"]

    @property
    def valor_reportado(self) -> Decimal:
        return self.diferenca_brl


@dataclass
class Nota:
    tomador_cnpj: str
    tomador: str
    linha_negocio: str
    valor_brl: Decimal
    discriminacao: str
    competencia: str = ""
    rastro: list[ItemRastro] = field(default_factory=list)

    ARQUIVO = "notas_a_emitir"
    PREFIXO = "NF"
    COLUNAS = ["tomador_cnpj", "tomador", "linha_negocio", "valor_brl", "discriminacao"]
    EXTRAS = ["competencia"]

    @property
    def valor_reportado(self) -> Decimal:
        return self.valor_brl


@dataclass
class Lancamento:
    banco: str
    ref_origem: str
    data: date
    descricao: str
    valor: Decimal
    conta_codigo: str
    metodo: str
    confianca: Decimal
    conta_descricao: str = ""
    justificativa: str = ""
    rastro: list[ItemRastro] = field(default_factory=list)

    ARQUIVO = "lancamentos_classificados"
    PREFIXO = "LAN"
    COLUNAS = ["banco", "ref_origem", "data", "descricao", "valor", "conta_codigo", "metodo", "confianca"]
    EXTRAS = ["conta_descricao", "justificativa"]

    @property
    def valor_reportado(self) -> Decimal:
        return self.valor


@dataclass
class Pendencia:
    tipo: str
    ref_origem: str
    valor_brl: Decimal
    motivo: str
    quem_decide: str
    cnpj: str = ""
    lojista: str = ""
    acao_sugerida: str = ""
    rastro: list[ItemRastro] = field(default_factory=list)

    ARQUIVO = "pendencias"
    PREFIXO = "PEN"
    COLUNAS = ["tipo", "ref_origem", "valor_brl", "motivo", "quem_decide"]
    EXTRAS = ["cnpj", "lojista", "acao_sugerida"]

    @property
    def valor_reportado(self) -> Decimal:
        return self.valor_brl


TIPOS_SAIDA = [Comissao, Divergencia, Nota, Lancamento, Pendencia]


@dataclass
class ResultadoModulo:
    comissoes: list[Comissao] = field(default_factory=list)
    divergencias: list[Divergencia] = field(default_factory=list)
    notas: list[Nota] = field(default_factory=list)
    lancamentos: list[Lancamento] = field(default_factory=list)
    pendencias: list[Pendencia] = field(default_factory=list)

    def todas(self):
        return [*self.comissoes, *self.divergencias, *self.notas, *self.lancamentos, *self.pendencias]

    def juntar(self, outro: "ResultadoModulo") -> None:
        self.comissoes += outro.comissoes
        self.divergencias += outro.divergencias
        self.notas += outro.notas
        self.lancamentos += outro.lancamentos
        self.pendencias += outro.pendencias
