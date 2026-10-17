"""Fallback com IA na classificação dos extratos (premissa P14 do HIPOTESES.md).

A IA só SUGERE a contrapartida de um lançamento que nenhuma regra cobre (P09); nunca decide regra de negócio.
Toda sugestão sai com metodo IA e vira pendência de revisão em bancos.py. Configuração em config/ia.yaml.

Ordem: com habilitada=false, nada. Senão, a resposta vem do cache em disco (hash do lançamento + modelo);
se não estiver lá, só chama o modelo com ANTHROPIC_API_KEY definida. Sem chave e sem cache: None, e o
lançamento segue o fluxo de P09 (A_CLASSIFICAR, HUMANO). O cache vai para o git: a banca reproduz sem chave.
O pacote anthropic é opcional: só é importado na chamada à API; sem ele vale o mesmo que sem chave.
A resposta guardada é a bruta; a validação (conta do plano com aceita_lancto, confiança de 0 a 1) roda sempre.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import NamedTuple, Protocol

import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[2]
CONFIG_IA = RAIZ / "config" / "ia.yaml"
HIPOTESES = RAIZ / "HIPOTESES.md"
VARIAVEL_CHAVE = "ANTHROPIC_API_KEY"
CENTAVO = Decimal("0.01")
ESFORCOS = ("low", "medium", "high", "xhigh", "max")

log = logging.getLogger(__name__)


def _sdk():
    """SDK anthropic, importado só na hora de chamar a API; None se o pacote não estiver instalado.

    O fechamento funciona sem ele: o cache e as regras não precisam do pacote, e sem o pacote o lançamento sem
    regra segue o fluxo de P09, como sem chave.
    """
    try:
        import anthropic
    except ImportError:
        return None
    return anthropic


class ErroIA(ValueError):
    """Configuração da IA inválida."""


class Sugestao(NamedTuple):
    conta_codigo: str
    confianca: Decimal
    justificativa: str


class Exemplo(NamedTuple):
    """Lançamento do mesmo extrato já classificado por regra."""

    descricao: str
    valor: Decimal
    conta_codigo: str


class LancamentoIA(Protocol):
    banco: str
    ref_origem: str
    data: date
    descricao: str
    valor: Decimal


# ---------------------------------------------------------------- configuração

@dataclass(frozen=True)
class ConfigIA:
    habilitada: bool
    modelo: str
    esforco: str
    max_tokens: int
    limiar_confianca: Decimal
    max_exemplos: int
    regras_contexto: tuple[str, ...]
    cache: Path
    quem_decide: str


def _texto(v, campo: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise ErroIA(f"config ia: {campo} deveria ser texto, veio {v!r}")
    return v


def _inteiro(v, campo: str) -> int:
    if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
        raise ErroIA(f"config ia: {campo} deveria ser inteiro positivo, veio {v!r}")
    return v


def carregar_config(caminho=CONFIG_IA) -> ConfigIA:
    with open(caminho, encoding="utf-8") as f:
        bruto = yaml.safe_load(f) or {}
    habilitada = bruto.get("habilitada")
    if not isinstance(habilitada, bool):
        raise ErroIA(f"config ia: habilitada deveria ser true/false, veio {habilitada!r}")
    esforco = _texto(bruto.get("esforco"), "esforco")
    if esforco not in ESFORCOS:
        raise ErroIA(f"config ia: esforco deveria ser um de {ESFORCOS}, veio {esforco!r}")
    limiar = Decimal(_texto(bruto.get("limiar_confianca"), "limiar_confianca"))
    if not 0 <= limiar <= 1:
        raise ErroIA(f"config ia: limiar_confianca deveria ser de 0 a 1, veio {limiar}")
    regras = bruto.get("regras_contexto")
    if not isinstance(regras, list) or not regras or not all(isinstance(r, str) for r in regras):
        raise ErroIA(f"config ia: regras_contexto deveria ser lista de ids do HIPOTESES.md, veio {regras!r}")
    cache = Path(_texto(bruto.get("cache"), "cache"))
    return ConfigIA(
        habilitada=habilitada,
        modelo=_texto(bruto.get("modelo"), "modelo"),
        esforco=esforco,
        max_tokens=_inteiro(bruto.get("max_tokens"), "max_tokens"),
        limiar_confianca=limiar,
        max_exemplos=_inteiro(bruto.get("max_exemplos"), "max_exemplos"),
        regras_contexto=tuple(regras),
        cache=cache if cache.is_absolute() else RAIZ / cache,
        quem_decide=_texto(bruto.get("quem_decide"), "quem_decide"),
    )


# ---------------------------------------------------------------- contexto

def contas_analiticas(plano: pd.DataFrame) -> dict[str, str]:
    """Contas que aceitam lançamento (aceita_lancto=True): código -> descrição."""
    return {r["cod_conta"]: r["descricao"] for r in plano.to_dict("records") if r["aceita_lancto"]}


def texto_regras(ids, caminho=HIPOTESES) -> list[str]:
    """Texto das regras pedidas, como estão no HIPOTESES.md (linha "- **R19** — ...")."""
    with open(caminho, encoding="utf-8") as f:
        conteudo = f.read()
    textos = []
    for id_regra in ids:
        m = re.search(rf"^- \*\*{re.escape(id_regra)}\*\* — (.+)$", conteudo, re.MULTILINE)
        if not m:
            raise ErroIA(f"config ia: regra {id_regra} não encontrada no HIPOTESES.md")
        textos.append(f"{id_regra}: {m.group(1).strip()}")
    return textos


def _sistema(contas: dict[str, str], regras: list[str]) -> str:
    linhas_contas = "\n".join(f"{cod} | {desc}" for cod, desc in contas.items())
    linhas_regras = "\n".join(f"- {r}" for r in regras)
    return (
        "Você ajuda o financeiro da Tarvo Pagamentos a classificar lançamentos de extrato bancário no plano de "
        "contas do ERP. Para o lançamento informado, sugira a conta de contrapartida do movimento no banco, "
        "escolhida SOMENTE na lista de contas analíticas abaixo.\n"
        "Você só sugere: uma pessoa do financeiro revisa toda sugestão antes de qualquer lançamento. Não crie "
        "regra de negócio nem suponha fatos que o extrato não mostra. Se o texto não deixar clara a "
        "contrapartida, escolha a conta mais provável e dê confiança baixa.\n"
        "Valor positivo é crédito (entrada no banco); valor negativo é débito (saída).\n\n"
        f"Regras do financeiro sobre a contrapartida:\n{linhas_regras}\n\n"
        f"Contas analíticas (código | descrição):\n{linhas_contas}\n\n"
        "Responda com conta_codigo, confianca (de 0 a 1: sua certeza de que a conta está certa) e "
        "justificativa (uma frase, em português)."
    )


def _pergunta(l: LancamentoIA, exemplos: list[Exemplo]) -> str:
    if exemplos:
        linhas = "\n".join(f"- {e.descricao!r} | valor {e.valor} | conta {e.conta_codigo}" for e in exemplos)
    else:
        linhas = "(nenhum)"
    return (
        f"Lançamentos do mesmo extrato (banco {l.banco}) já classificados por regra:\n{linhas}\n\n"
        "Lançamento a classificar:\n"
        f"banco: {l.banco}\ndata: {l.data.isoformat()}\ndescrição: {l.descricao!r}\nvalor: {l.valor}"
    )


def _schema(contas: dict[str, str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "conta_codigo": {"type": "string", "enum": list(contas)},
            "confianca": {"type": "number"},
            "justificativa": {"type": "string"},
        },
        "required": ["conta_codigo", "confianca", "justificativa"],
        "additionalProperties": False,
    }


# ---------------------------------------------------------------- cache

def chave_cache(l: LancamentoIA, modelo: str) -> str:
    """Hash do lançamento + modelo: a mesma entrada dá sempre a mesma saída."""
    bruto = json.dumps(_identidade(l) | {"modelo": modelo}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def _identidade(l: LancamentoIA) -> dict:
    return {"banco": l.banco, "ref_origem": l.ref_origem, "data": l.data.isoformat(), "descricao": l.descricao,
            "valor": format(l.valor, "f")}


def ler_cache(caminho: Path) -> dict:
    if not caminho.exists():
        return {}
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def _gravar_cache(caminho: Path, cache: dict) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


# ---------------------------------------------------------------- chamada e validação

def _perguntar(cliente, l: LancamentoIA, contas: dict[str, str], exemplos: list[Exemplo],
               cfg: ConfigIA) -> dict | None:
    """Resposta bruta do modelo ({"stop_reason", "texto"}), ou None se a chamada falhar (não vai para o cache)."""
    sdk = _sdk()
    erros_da_api = (sdk.APIStatusError, sdk.APIConnectionError) if sdk else ()  # cliente falso sem o pacote
    try:
        resposta = cliente.messages.create(
            model=cfg.modelo,
            max_tokens=cfg.max_tokens,
            system=_sistema(contas, texto_regras(cfg.regras_contexto)),
            messages=[{"role": "user", "content": _pergunta(l, exemplos)}],
            output_config={"effort": cfg.esforco, "format": {"type": "json_schema", "schema": _schema(contas)}},
        )
    except erros_da_api as e:
        log.warning("IA: chamada falhou para %s (%s); segue sem sugestão", l.ref_origem, e)
        return None
    texto = "".join(b.text for b in resposta.content if b.type == "text")
    return {"stop_reason": resposta.stop_reason, "texto": texto}


def validar(resposta: dict, contas: dict[str, str]) -> Sugestao | None:
    """Sugestão só vale com conta do plano que aceita lançamento, confiança de 0 a 1 e justificativa."""
    if resposta.get("stop_reason") != "end_turn":
        return _descartar(f"stop_reason {resposta.get('stop_reason')!r}")
    try:
        dados = json.loads(resposta.get("texto") or "", parse_float=Decimal, parse_int=Decimal)
    except json.JSONDecodeError:
        return _descartar("JSON malformado")
    if not isinstance(dados, dict):
        return _descartar("resposta não é objeto JSON")
    conta, confianca, justificativa = dados.get("conta_codigo"), dados.get("confianca"), dados.get("justificativa")
    if not isinstance(conta, str) or conta not in contas:
        return _descartar(f"conta {conta!r} não existe no plano ou não aceita lançamento")
    if not isinstance(confianca, Decimal) or not 0 <= confianca <= 1:
        return _descartar(f"confiança {confianca!r} fora de 0 a 1")
    if not isinstance(justificativa, str) or not justificativa.strip():
        return _descartar("sem justificativa")
    return Sugestao(conta, confianca.quantize(CENTAVO, rounding=ROUND_HALF_UP), " ".join(justificativa.split()))


def _descartar(motivo: str) -> None:
    log.warning("IA: sugestão descartada (%s); segue para revisão humana", motivo)
    return None


def sugerir_conta(lancamento: LancamentoIA, contas_analiticas: dict[str, str], exemplos: list[Exemplo], *,
                  cfg: ConfigIA | None = None, cliente=None) -> Sugestao | None:
    """(conta_codigo, confianca, justificativa) para um lançamento sem regra, ou None (fica HUMANO).

    cliente: objeto com messages.create (o SDK anthropic ou um falso nos testes). None: cria o cliente do
    SDK com ANTHROPIC_API_KEY, só se a resposta não estiver no cache.
    """
    cfg = cfg or carregar_config()
    if not cfg.habilitada:
        return None
    cache = ler_cache(cfg.cache)
    chave = chave_cache(lancamento, cfg.modelo)
    entrada = cache.get(chave)
    if entrada is None:
        if cliente is None:
            api_key = os.environ.get(VARIAVEL_CHAVE)
            if not api_key:
                return None
            sdk = _sdk()
            if sdk is None:
                log.warning("IA: pacote anthropic não instalado; segue sem sugestão (P09)")
                return None
            cliente = sdk.Anthropic(api_key=api_key)
        resposta = _perguntar(cliente, lancamento, contas_analiticas, exemplos, cfg)
        if resposta is None:
            return None
        entrada = {"modelo": cfg.modelo, "lancamento": _identidade(lancamento), "resposta": resposta}
        cache[chave] = entrada
        _gravar_cache(cfg.cache, cache)
    return validar(entrada["resposta"], contas_analiticas)
