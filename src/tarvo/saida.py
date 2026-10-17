"""Infraestrutura de saída: itens rastreáveis, escrita e validação dos 6 CSVs. Sem regra de negócio.

Cada ItemSaida vira uma linha num dos 5 arquivos de resultado e uma ou mais linhas no rastro.csv.
A soma das origens precisa fechar com o valor reportado já na criação do item.
A escrita nunca arredonda: valor com casas a mais é erro, quem arredonda é a regra de negócio.
Pelo mesmo motivo, a escrita nunca troca o separador: texto com ";" é erro, quem monta o texto usa texto_saida.
"""

from __future__ import annotations

import codecs
import csv
import io
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Callable, Iterable, NamedTuple

from tarvo.leitores.comum import CENTAVO

ENCODING = "utf-8"
SEPARADOR = ";"
FIM_DE_LINHA = "\n"
SEPARADOR_REFS = "|"
CASAS_TAXA = Decimal("0.0001")

LINHAS_NEGOCIO = ("CHECKOUT", "REMESSA")
BANCOS = ("AURORA", "MERIDIANO")
METODOS = ("REGRA", "IA", "HUMANO")


class ErroSaida(ValueError):
    """Item ou arquivo de saída fora do formato, ou rastro que não fecha."""


class Origem(NamedTuple):
    arquivo_origem: str
    ref_origem: str
    valor: Decimal


# ---------------------------------------------------------------- tipos de coluna

def texto_saida(texto: str) -> str:
    """Texto pronto para a saída: cada ";" (com os espaços em volta) vira " - ". Os módulos chamam ao montar o texto."""
    return re.sub(r"\s*;\s*", " - ", texto)


def _decimal(v, coluna: str, casas: Decimal) -> Decimal:
    if isinstance(v, bool) or not isinstance(v, Decimal):
        raise ErroSaida(f"{coluna}: esperado Decimal, veio {type(v).__name__} ({v!r})")
    if not v.is_finite():
        raise ErroSaida(f"{coluna}: valor não finito ({v!r})")
    if v != v.quantize(casas):
        raise ErroSaida(f"{coluna}: {v} tem mais casas que {casas}; arredonde antes de gravar")
    return v


def _fmt_decimal(v, coluna: str, casas: Decimal) -> str:
    v = _decimal(v, coluna, casas)
    if v == 0:
        v = abs(v)  # nunca "-0.00"
    return format(v.quantize(casas), "f")


def _texto(v, coluna: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise ErroSaida(f"{coluna}: esperado texto não vazio, veio {v!r}")
    if "\n" in v or "\r" in v:
        raise ErroSaida(f"{coluna}: texto com quebra de linha ({v!r})")
    if SEPARADOR in v:
        raise ErroSaida(f"{coluna}: texto com '{SEPARADOR}', o separador do CSV; monte o texto com texto_saida ({v!r})")
    return v


def _ref(v, coluna: str) -> str:
    v = _texto(v, coluna)
    if SEPARADOR_REFS in v:
        raise ErroSaida(f"{coluna}: ref_origem única não pode conter '{SEPARADOR_REFS}' ({v!r})")
    return v


def _refs(v, coluna: str) -> str:
    if isinstance(v, (list, tuple)):
        if not v:
            raise ErroSaida(f"{coluna}: lista de ref_origem vazia")
        return SEPARADOR_REFS.join(_ref(r, coluna) for r in v)
    return SEPARADOR_REFS.join(_ref(r, coluna) for r in _texto(v, coluna).split(SEPARADOR_REFS))


def _data(v, coluna: str) -> str:
    if isinstance(v, datetime) or not isinstance(v, date):
        raise ErroSaida(f"{coluna}: esperado datetime.date, veio {type(v).__name__} ({v!r})")
    return v.isoformat()


def _cnpj(v, coluna: str) -> str:
    if not isinstance(v, str) or not re.fullmatch(r"[0-9]{14}", v):
        raise ErroSaida(f"{coluna}: CNPJ precisa ser texto com exatamente 14 dígitos, veio {v!r}")
    return v


def _confianca(v, coluna: str) -> str:
    v = _decimal(v, coluna, CENTAVO)
    if not 0 <= v <= 1:
        raise ErroSaida(f"{coluna}: confiança fora de 0 a 1 ({v})")
    return _fmt_decimal(v, coluna, CENTAVO)


def _dominio(valores: tuple[str, ...]) -> Callable[[object, str], str]:
    def formatar(v, coluna: str) -> str:
        if v not in valores:
            raise ErroSaida(f"{coluna}: {v!r} fora do domínio {'|'.join(valores)}")
        return v
    return formatar


def _data_valida(s: str) -> bool:
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", s):
        return False
    try:
        date.fromisoformat(s)
    except ValueError:
        return False
    return True


def _refs_validas(s: str) -> bool:
    return SEPARADOR not in s and all(r.strip() and "\n" not in r for r in s.split(SEPARADOR_REFS))


@dataclass(frozen=True)
class TipoColuna:
    descricao: str
    formatar: Callable[[object, str], str]  # valor Python -> texto; ErroSaida se fora do formato
    conferir: Callable[[str], bool]          # texto relido do CSV -> está no formato?


DINHEIRO = TipoColuna(
    "dinheiro com 2 casas (ex.: -12.30)",
    lambda v, c: _fmt_decimal(v, c, CENTAVO),
    lambda s: bool(re.fullmatch(r"-?[0-9]+\.[0-9]{2}", s)),
)
TAXA = TipoColuna(
    "taxa em pontos percentuais com 4 casas (ex.: 2.6900)",
    lambda v, c: _fmt_decimal(v, c, CASAS_TAXA),
    lambda s: bool(re.fullmatch(r"-?[0-9]+\.[0-9]{4}", s)),
)
DATA = TipoColuna("data AAAA-MM-DD", _data, _data_valida)
CNPJ = TipoColuna("CNPJ com 14 dígitos", _cnpj, lambda s: bool(re.fullmatch(r"[0-9]{14}", s)))
TEXTO = TipoColuna(
    f"texto não vazio (sem '{SEPARADOR}')",
    _texto,
    lambda s: bool(s.strip()) and "\n" not in s and SEPARADOR not in s,
)
REF = TipoColuna(
    f"ref_origem única (sem '{SEPARADOR_REFS}' nem '{SEPARADOR}')",
    _ref,
    lambda s: bool(s.strip()) and SEPARADOR_REFS not in s and SEPARADOR not in s and "\n" not in s,
)
REFS = TipoColuna(f"ref_origem ou lista separada por '{SEPARADOR_REFS}'", _refs, _refs_validas)
LINHA_NEGOCIO = TipoColuna("|".join(LINHAS_NEGOCIO), _dominio(LINHAS_NEGOCIO), lambda s: s in LINHAS_NEGOCIO)
BANCO = TipoColuna("|".join(BANCOS), _dominio(BANCOS), lambda s: s in BANCOS)
METODO = TipoColuna("|".join(METODOS), _dominio(METODOS), lambda s: s in METODOS)
CONFIANCA = TipoColuna(
    "confiança de 0 a 1 com 2 casas",
    _confianca,
    lambda s: bool(re.fullmatch(r"0\.[0-9]{2}|1\.00", s)),
)


# ---------------------------------------------------------------- os 6 arquivos

@dataclass(frozen=True)
class EspecArquivo:
    nome: str
    prefixo: str | None                     # None no rastro.csv
    colunas: tuple[tuple[str, TipoColuna], ...]  # obrigatórias, nesta ordem; a 1ª é id_saida
    coluna_valor: str

    @property
    def nomes(self) -> tuple[str, ...]:
        return tuple(nome for nome, _ in self.colunas)


ID = TipoColuna("id_saida", lambda v, c: v, lambda s: bool(s))  # conferido à parte, por prefixo

COMISSOES = EspecArquivo(
    "comissoes_por_lojista.csv", "COM-",
    (("id_saida", ID), ("cnpj", CNPJ), ("lojista", TEXTO), ("linha_negocio", LINHA_NEGOCIO),
     ("comissao_brl", DINHEIRO)),
    "comissao_brl",
)
DIVERGENCIAS = EspecArquivo(
    "divergencias_taxa.csv", "DIV-",
    (("id_saida", ID), ("cnpj", CNPJ), ("linha_negocio", LINHA_NEGOCIO), ("ref_origem", REF),
     ("taxa_contratada_pct", TAXA), ("taxa_aplicada_pct", TAXA), ("diferenca_brl", DINHEIRO)),
    "diferenca_brl",
)
NOTAS = EspecArquivo(
    "notas_a_emitir.csv", "NF-",
    (("id_saida", ID), ("tomador_cnpj", CNPJ), ("tomador", TEXTO), ("linha_negocio", LINHA_NEGOCIO),
     ("valor_brl", DINHEIRO), ("discriminacao", TEXTO)),
    "valor_brl",
)
LANCAMENTOS = EspecArquivo(
    "lancamentos_classificados.csv", "LAN-",
    (("id_saida", ID), ("banco", BANCO), ("ref_origem", REF), ("data", DATA), ("descricao", TEXTO),
     ("valor", DINHEIRO), ("conta_codigo", TEXTO), ("metodo", METODO), ("confianca", CONFIANCA)),
    "valor",
)
PENDENCIAS = EspecArquivo(
    "pendencias.csv", "PEN-",
    (("id_saida", ID), ("tipo", TEXTO), ("ref_origem", REFS), ("valor_brl", DINHEIRO),
     ("motivo", TEXTO), ("quem_decide", TEXTO)),
    "valor_brl",
)
RASTRO = EspecArquivo(
    "rastro.csv", None,
    (("id_saida", ID), ("arquivo_origem", TEXTO), ("ref_origem", REF), ("valor", DINHEIRO)),
    "valor",
)

ARQUIVOS_ITENS = (COMISSOES, DIVERGENCIAS, NOTAS, LANCAMENTOS, PENDENCIAS)
ARQUIVOS = ARQUIVOS_ITENS + (RASTRO,)
ESPEC_POR_NOME = {e.nome: e for e in ARQUIVOS_ITENS}


def _id_valido(id_saida, prefixos: Iterable[str]) -> bool:
    return isinstance(id_saida, str) and any(
        re.fullmatch(re.escape(p) + r"[A-Za-z0-9][A-Za-z0-9._-]*", id_saida) for p in prefixos
    )


# ---------------------------------------------------------------- item

def _origem(o, id_saida: str) -> Origem:
    try:
        arquivo_origem, ref_origem, valor = o
    except (TypeError, ValueError):
        raise ErroSaida(f"{id_saida}: origem deve ser (arquivo_origem, ref_origem, valor), veio {o!r}") from None
    return Origem(
        _texto(arquivo_origem, f"{id_saida}: arquivo_origem"),
        _ref(ref_origem, f"{id_saida}: ref_origem"),
        _decimal(valor, f"{id_saida}: valor da origem {ref_origem!r}", CENTAVO),
    )


@dataclass(frozen=True)
class ItemSaida:
    """Uma linha de um dos 5 arquivos de resultado, com as origens que somam o valor reportado.

    campos traz as colunas da linha. id_saida e a coluna de valor saem de id_saida e valor_reportado;
    se vierem também em campos, precisam ser iguais. Colunas fora das obrigatórias são extras.
    """

    id_saida: str
    arquivo: str
    campos: dict
    valor_reportado: Decimal
    origens: tuple[Origem, ...]

    def __post_init__(self) -> None:
        espec = ESPEC_POR_NOME.get(self.arquivo)
        if espec is None:
            raise ErroSaida(f"{self.id_saida!r}: arquivo {self.arquivo!r} não é um dos {sorted(ESPEC_POR_NOME)}")
        if not _id_valido(self.id_saida, [espec.prefixo]):
            raise ErroSaida(f"id_saida {self.id_saida!r} inválido para {espec.nome}: use o prefixo {espec.prefixo}")
        _decimal(self.valor_reportado, f"{self.id_saida}: valor_reportado", CENTAVO)

        origens = tuple(_origem(o, self.id_saida) for o in self.origens)
        soma = sum((o.valor for o in origens), Decimal("0.00"))
        if soma != self.valor_reportado:
            raise ErroSaida(
                f"{self.id_saida}: soma das origens ({soma}) diferente do valor reportado ({self.valor_reportado})"
            )

        campos = dict(self.campos)
        for chave, esperado in (("id_saida", self.id_saida), (espec.coluna_valor, self.valor_reportado)):
            if chave in campos and campos[chave] != esperado:
                raise ErroSaida(f"{self.id_saida}: campos[{chave!r}]={campos[chave]!r} difere de {esperado!r}")

        object.__setattr__(self, "origens", origens)
        object.__setattr__(self, "campos", campos)

    @property
    def espec(self) -> EspecArquivo:
        return ESPEC_POR_NOME[self.arquivo]


# ---------------------------------------------------------------- escrita

def _fmt_extra(v, coluna: str) -> str:
    if v is None:
        return ""
    if isinstance(v, (bool, float)):
        raise ErroSaida(f"{coluna}: tipo {type(v).__name__} não é aceito ({v!r})")
    if isinstance(v, Decimal):
        if not v.is_finite():
            raise ErroSaida(f"{coluna}: valor não finito ({v!r})")
        return format(v, "f")
    if isinstance(v, date) and not isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, (str, int)):
        texto = str(v)
        if "\n" in texto or "\r" in texto:
            raise ErroSaida(f"{coluna}: texto com quebra de linha ({texto!r})")
        if SEPARADOR in texto:
            raise ErroSaida(f"{coluna}: texto com '{SEPARADOR}', o separador do CSV; monte o texto com texto_saida ({texto!r})")
        return texto
    raise ErroSaida(f"{coluna}: tipo {type(v).__name__} não é aceito ({v!r})")


def _formatar(item: ItemSaida) -> tuple[list[str], dict[str, str]]:
    espec = item.espec
    valores = {**item.campos, "id_saida": item.id_saida, espec.coluna_valor: item.valor_reportado}
    obrigatorias = []
    for nome, tipo in espec.colunas:
        if nome not in valores:
            raise ErroSaida(f"{item.id_saida}: falta a coluna obrigatória {nome!r} de {espec.nome}")
        obrigatorias.append(tipo.formatar(valores[nome], f"{item.id_saida}: {nome}"))
    extras = {}
    for nome, v in item.campos.items():
        if nome in espec.nomes:
            continue
        if not isinstance(nome, str) or not nome.strip() or any(c in nome for c in ";\n\r\""):
            raise ErroSaida(f"{item.id_saida}: nome de coluna extra inválido {nome!r}")
        extras[nome] = _fmt_extra(v, f"{item.id_saida}: {nome}")
    return obrigatorias, extras


def _gravar_csv(caminho: Path, cabecalho: list[str], linhas: list[list[str]]) -> None:
    with open(caminho, "w", encoding=ENCODING, newline="") as f:
        escritor = csv.writer(f, delimiter=SEPARADOR, lineterminator=FIM_DE_LINHA, quoting=csv.QUOTE_MINIMAL)
        escritor.writerow(cabecalho)
        escritor.writerows(linhas)


def gravar_saida(pasta, itens: Iterable[ItemSaida]) -> dict[str, Path]:
    """Valida todos os itens e grava os 6 CSVs em pasta. Nada é gravado se algum item estiver fora do formato."""
    itens = list(itens)
    onde: dict[str, str] = {}
    for item in itens:
        if not isinstance(item, ItemSaida):
            raise ErroSaida(f"esperado ItemSaida, veio {type(item).__name__}")
        if item.id_saida in onde:
            raise ErroSaida(f"id_saida duplicado: {item.id_saida} (em {onde[item.id_saida]} e {item.arquivo})")
        onde[item.id_saida] = item.arquivo

    formatados: dict[str, list[tuple[list[str], dict[str, str]]]] = {e.nome: [] for e in ARQUIVOS_ITENS}
    rastro: list[list[str]] = []
    for item in itens:
        formatados[item.arquivo].append(_formatar(item))
        for o in item.origens:
            rastro.append([item.id_saida, o.arquivo_origem, o.ref_origem, DINHEIRO.formatar(o.valor, "rastro")])

    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    gravados: dict[str, Path] = {}
    for espec in ARQUIVOS_ITENS:
        extras = list(dict.fromkeys(nome for _, ex in formatados[espec.nome] for nome in ex))
        linhas = [obrig + [ex.get(nome, "") for nome in extras] for obrig, ex in formatados[espec.nome]]
        gravados[espec.nome] = pasta / espec.nome
        _gravar_csv(gravados[espec.nome], list(espec.nomes) + extras, linhas)
    gravados[RASTRO.nome] = pasta / RASTRO.nome
    _gravar_csv(gravados[RASTRO.nome], list(RASTRO.nomes), rastro)
    return gravados


# ---------------------------------------------------------------- validação

def _ler_csv(caminho: Path, problemas: list[str]) -> list[list[str]] | None:
    nome = caminho.name
    if not caminho.is_file():
        problemas.append(f"{nome}: arquivo não encontrado")
        return None
    bruto = caminho.read_bytes()
    if bruto.startswith(codecs.BOM_UTF8):
        problemas.append(f"{nome}: começa com BOM")
        bruto = bruto[len(codecs.BOM_UTF8):]
    if b"\r" in bruto:
        problemas.append(f"{nome}: fim de linha deve ser \\n, achei \\r")
    try:
        texto = bruto.decode(ENCODING)
    except UnicodeDecodeError as e:
        problemas.append(f"{nome}: não é UTF-8 ({e})")
        return None
    if not texto.endswith(FIM_DE_LINHA):
        problemas.append(f"{nome}: não termina com \\n")
    linhas = list(csv.reader(io.StringIO(texto, newline=""), delimiter=SEPARADOR))
    if not linhas:
        problemas.append(f"{nome}: vazio, sem cabeçalho")
        return None
    return linhas


def validar_saida(pasta) -> list[str]:
    """Relê os 6 CSVs e devolve a lista de problemas (vazia se estiver tudo certo).

    Confere encoding, fim de linha, colunas obrigatórias e ordem, formato de cada campo, id_saida único
    e com o prefixo do arquivo, soma do rastro por id_saida == valor reportado e se todo id do rastro existe.
    """
    pasta = Path(pasta)
    problemas: list[str] = []
    ids: dict[str, str] = {}
    reportados: dict[str, Decimal] = {}
    soma_rastro: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    rastro_lido = False
    todos_prefixos = [e.prefixo for e in ARQUIVOS_ITENS]

    for espec in ARQUIVOS:
        linhas = _ler_csv(pasta / espec.nome, problemas)
        if linhas is None:
            continue
        cabecalho = linhas[0]
        if cabecalho[: len(espec.nomes)] != list(espec.nomes):
            problemas.append(
                f"{espec.nome}: cabeçalho deveria começar com {SEPARADOR.join(espec.nomes)}, "
                f"veio {SEPARADOR.join(cabecalho)}"
            )
            continue
        if len(set(cabecalho)) != len(cabecalho):
            problemas.append(f"{espec.nome}: coluna repetida no cabeçalho")
        i_valor = espec.nomes.index(espec.coluna_valor)
        prefixos = todos_prefixos if espec is RASTRO else [espec.prefixo]
        if espec is RASTRO:
            rastro_lido = True

        for n, campos in enumerate(linhas[1:], start=2):
            onde = f"{espec.nome} linha {n}"
            if len(campos) != len(cabecalho):
                problemas.append(f"{onde}: {len(campos)} campos, o cabeçalho tem {len(cabecalho)}")
                continue
            ok = True
            for (coluna, tipo), valor in zip(espec.colunas, campos):
                if coluna == "id_saida":
                    ok_campo = _id_valido(valor, prefixos)
                else:
                    ok_campo = tipo.conferir(valor)
                if not ok_campo:
                    descricao = f"id_saida com prefixo {'/'.join(prefixos)}" if coluna == "id_saida" else tipo.descricao
                    problemas.append(f"{onde}: {coluna}={valor!r} não é {descricao}")
                    ok = False
            id_saida, valor = campos[0], campos[i_valor]

            if espec is RASTRO:
                if id_saida not in ids:
                    problemas.append(f"{onde}: id_saida {id_saida!r} não existe em nenhum dos 5 arquivos")
                elif ok:
                    soma_rastro[id_saida] += Decimal(valor)
                continue
            if id_saida in ids:
                problemas.append(f"{onde}: id_saida {id_saida!r} repetido (já está em {ids[id_saida]})")
                continue
            ids[id_saida] = onde
            if DINHEIRO.conferir(valor):
                reportados[id_saida] = Decimal(valor)

    if rastro_lido:
        for id_saida, reportado in reportados.items():
            soma = soma_rastro[id_saida]
            if soma != reportado:
                problemas.append(
                    f"{id_saida}: soma do rastro ({soma}) diferente do valor reportado ({reportado}) em {ids[id_saida]}"
                )
    return problemas
