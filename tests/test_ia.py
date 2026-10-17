"""Fallback com IA nos extratos (P14), sempre com cliente FALSO: nenhum teste chama a rede.

O cliente falso imita client.messages.create do SDK anthropic e devolve o texto que o teste manda.
O cache de cada teste fica em tmp_path, nunca no cache/ do repositório.
"""

import csv
import dataclasses
import json
from datetime import date
from decimal import Decimal
from functools import partial
from pathlib import Path
from types import SimpleNamespace

import httpx2
import pytest
import yaml

from gerar_outubro import gerar
from tarvo import ia
from tarvo.bancos import (
    AURORA,
    FallbackIA,
    bancos,
    carregar_config,
    classificar,
    item_lancamento,
    pendencias_lancamentos,
    sugestoes_ia,
)
from tarvo.checkout import checkout
from tarvo.cli import construir_parser
from tarvo.fechamento import fechar, ler_entradas
from tarvo.remessa import remessa
from tarvo.saida import validar_saida

D = Decimal
RAIZ = Path(__file__).resolve().parents[1]
SETEMBRO = RAIZ / "dados" / "2026-09"
CONTA_ANALITICA = "4.2.04"   # Softwares e assinaturas (aceita lançamento)
CONTA_SINTETICA = "4.2"      # DESPESAS ADMINISTRATIVAS (não aceita lançamento)


class ClienteFalso:
    """Responde, em ordem, os textos dados (ou (texto, stop_reason), ou uma exceção). Guarda as chamadas."""

    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.chamadas = []
        self.messages = self

    def create(self, **kw):
        self.chamadas.append(kw)
        r = self.respostas.pop(0)
        if isinstance(r, Exception):
            raise r
        texto, stop = r if isinstance(r, tuple) else (r, "end_turn")
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=texto)], stop_reason=stop)


class ClienteProibido:
    def __init__(self):
        self.messages = self

    def create(self, **kw):
        raise AssertionError("a IA não deveria ser chamada")


def _json(conta=CONTA_ANALITICA, confianca=0.92, justificativa="Gráfica é serviço do mês."):
    return json.dumps({"conta_codigo": conta, "confianca": confianca, "justificativa": justificativa})


@pytest.fixture(autouse=True)
def sem_chave(monkeypatch):
    monkeypatch.delenv(ia.VARIAVEL_CHAVE, raising=False)


@pytest.fixture(scope="module")
def entradas():
    return ler_entradas(SETEMBRO, "2026-09")


@pytest.fixture(scope="module")
def contas(entradas):
    return ia.contas_analiticas(entradas.plano_contas)


@pytest.fixture(scope="module")
def cfg_bancos(entradas):
    return carregar_config(entradas.plano_contas, entradas.taxas)


@pytest.fixture
def cfg_ia(tmp_path):
    return dataclasses.replace(ia.carregar_config(), habilitada=True, cache=tmp_path / "cache.json")


def _lanc(descricao="PIX ENVIADO FORNECEDOR TESTE", valor="-100.00", ref="R1"):
    return SimpleNamespace(banco=AURORA, ref_origem=ref, data=date(2031, 3, 10), descricao=descricao,
                           valor=D(valor))


# ---------------------------------------------------------------- configuração e contexto

def test_config_do_repositorio():
    cfg = ia.carregar_config()
    assert cfg.modelo == "claude-sonnet-5-5"
    assert cfg.limiar_confianca == D("0.80")
    assert cfg.regras_contexto == ("R19",)
    assert cfg.cache == RAIZ / "cache" / "ia_sugestoes.json"


def test_contas_analiticas_so_as_que_aceitam_lancamento(entradas, contas):
    plano = {r["cod_conta"]: r["aceita_lancto"] for r in entradas.plano_contas.to_dict("records")}
    assert set(contas) == {c for c, aceita in plano.items() if aceita}
    assert plano[CONTA_SINTETICA] is False and CONTA_SINTETICA not in contas
    assert CONTA_ANALITICA in contas


def test_regra_r19_vem_do_hipoteses():
    [r19] = ia.texto_regras(["R19"])
    assert r19.startswith("R19: conta_codigo = contrapartida do movimento no banco.")
    with pytest.raises(ia.ErroIA):
        ia.texto_regras(["R99"])


# ---------------------------------------------------------------- sugerir_conta

def test_sugestao_valida(contas, cfg_ia):
    cliente = ClienteFalso(_json())
    exemplos = [ia.Exemplo("TAR PACOTE SERVICOS", D("-50.00"), "4.2.01")]
    s = ia.sugerir_conta(_lanc(), contas, exemplos, cfg=cfg_ia, cliente=cliente)
    assert s == (CONTA_ANALITICA, D("0.92"), "Gráfica é serviço do mês.")
    assert isinstance(s.confianca, Decimal)

    [pedido] = cliente.chamadas
    assert pedido["model"] == "claude-sonnet-5-5"
    assert pedido["max_tokens"] == cfg_ia.max_tokens
    formato = pedido["output_config"]["format"]
    assert formato["type"] == "json_schema"
    assert formato["schema"]["required"] == ["conta_codigo", "confianca", "justificativa"]
    assert set(formato["schema"]["properties"]["conta_codigo"]["enum"]) == set(contas)
    assert "R19: conta_codigo = contrapartida" in pedido["system"]
    assert f"{CONTA_ANALITICA} | {contas[CONTA_ANALITICA]}" in pedido["system"]
    assert f"{CONTA_SINTETICA} |" not in pedido["system"]
    pergunta = pedido["messages"][0]["content"]
    assert "'TAR PACOTE SERVICOS' | valor -50.00 | conta 4.2.01" in pergunta
    assert "'PIX ENVIADO FORNECEDOR TESTE'" in pergunta and "valor: -100.00" in pergunta


@pytest.mark.parametrize("resposta", [
    _json(conta="9.9.99"),                       # conta inexistente
    _json(conta=CONTA_SINTETICA),                # conta sintética (existe, não aceita lançamento)
    _json(conta="A_CLASSIFICAR"),
    "isto não é JSON",                           # JSON malformado
    '{"conta_codigo": "4.2.04", "confianca": 0.9',  # cortado
    "[1, 2]",
    _json(confianca=1.5),
    _json(confianca=-0.1),
    _json(confianca=True),
    _json(confianca="0.9"),
    _json(justificativa="  "),
    (_json(), "refusal"),
    (_json(), "max_tokens"),
], ids=["inexistente", "sintetica", "a_classificar", "malformado", "cortado", "lista", "conf>1", "conf<0",
        "conf_bool", "conf_texto", "sem_justificativa", "refusal", "max_tokens"])
def test_sugestao_invalida_e_descartada(contas, cfg_ia, resposta):
    assert ia.sugerir_conta(_lanc(), contas, [], cfg=cfg_ia, cliente=ClienteFalso(resposta)) is None


def test_sem_chave_devolve_none_sem_chamar(contas, cfg_ia):
    assert ia.sugerir_conta(_lanc(), contas, [], cfg=cfg_ia) is None
    assert not cfg_ia.cache.exists()


def test_desabilitada_devolve_none_sem_chamar(contas, cfg_ia):
    cfg = dataclasses.replace(cfg_ia, habilitada=False)
    assert ia.sugerir_conta(_lanc(), contas, [], cfg=cfg, cliente=ClienteProibido()) is None
    assert not cfg.cache.exists()


def test_erro_da_api_devolve_none_e_nao_vai_para_o_cache(contas, cfg_ia):
    anthropic = pytest.importorskip("anthropic")  # o pacote é opcional; só este teste usa a exceção do SDK
    erro = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    assert ia.sugerir_conta(_lanc(), contas, [], cfg=cfg_ia, cliente=ClienteFalso(erro)) is None
    assert not cfg_ia.cache.exists()


def test_cache_acertado(contas, cfg_ia):
    cliente = ClienteFalso(_json())
    primeira = ia.sugerir_conta(_lanc(), contas, [], cfg=cfg_ia, cliente=cliente)
    assert len(cliente.chamadas) == 1

    # mesma entrada: mesma saída, sem chamada, e sem chave (a banca reproduz só com o cache)
    assert ia.sugerir_conta(_lanc(), contas, [], cfg=cfg_ia, cliente=ClienteProibido()) == primeira
    assert ia.sugerir_conta(_lanc(), contas, [], cfg=cfg_ia) == primeira

    with open(cfg_ia.cache, encoding="utf-8") as f:
        cache = json.load(f)
    [(chave, entrada)] = cache.items()
    assert chave == ia.chave_cache(_lanc(), cfg_ia.modelo)
    assert entrada["modelo"] == cfg_ia.modelo
    assert entrada["lancamento"]["descricao"] == "PIX ENVIADO FORNECEDOR TESTE"
    assert entrada["resposta"] == {"stop_reason": "end_turn", "texto": _json()}


def test_cache_por_lancamento_e_modelo(cfg_ia, contas):
    assert ia.chave_cache(_lanc(), "modelo-a") != ia.chave_cache(_lanc(), "modelo-b")
    assert ia.chave_cache(_lanc(), "m") != ia.chave_cache(_lanc(valor="-100.01"), "m")
    assert ia.chave_cache(_lanc(), "m") == ia.chave_cache(_lanc(), "m")


def test_resposta_invalida_em_cache_nao_chama_de_novo(contas, cfg_ia):
    assert ia.sugerir_conta(_lanc(), contas, [], cfg=cfg_ia, cliente=ClienteFalso("lixo")) is None
    assert ia.sugerir_conta(_lanc(), contas, [], cfg=cfg_ia, cliente=ClienteProibido()) is None


# ---------------------------------------------------------------- bancos.py

def _classificar_com_ia(cfg_bancos, contas, cfg_ia, cliente):
    lancs = classificar(AURORA, [
        {"arquivo_origem": "extrato_teste", "ref_origem": "R10", "data": date(2031, 3, 5),
         "descricao": "TAR PACOTE SERVICOS", "valor": D("-50.00")},
        {"arquivo_origem": "extrato_teste", "ref_origem": "R11", "data": date(2031, 3, 10),
         "descricao": "PIX ENVIADO FORNECEDOR TESTE", "valor": D("-100.00")},
    ], cfg_bancos)
    assert lancs[0].regra is not None and lancs[1].regra is None
    fallback = FallbackIA(cfg_ia, contas, cliente)
    sugestoes = sugestoes_ia([lancs], fallback)
    itens = [item_lancamento(l, cfg_bancos, sugestoes.get(l.id_saida)) for l in lancs]
    pendencias = {p.id_saida: p for p in pendencias_lancamentos(lancs, cfg_bancos, sugestoes, cfg_ia)}
    return itens, pendencias


def test_bancos_sugestao_valida_sai_ia_com_pendencia_de_revisao(cfg_bancos, contas, cfg_ia):
    cliente = ClienteFalso(_json(confianca=0.92))
    [regra, sugerido], pendencias = _classificar_com_ia(cfg_bancos, contas, cfg_ia, cliente)
    assert regra.campos["metodo"] == "REGRA"
    assert (sugerido.campos["conta_codigo"], sugerido.campos["metodo"], sugerido.campos["confianca"]) == \
           (CONTA_ANALITICA, "IA", D("0.92"))
    assert sugerido.valor_reportado == D("-100.00")

    assert set(pendencias) == {"PEN-IA-R11"}  # a sugestão substitui a PEN-SEMREGRA, nunca a dispensa
    p = pendencias["PEN-IA-R11"]
    assert p.campos["tipo"] == "REVISAR_SUGESTAO_IA"
    assert p.campos["quem_decide"] == "Financeiro"
    assert p.campos["ref_origem"] == "R11" and p.valor_reportado == D("-100.00")
    assert "Gráfica é serviço do mês." in p.campos["motivo"] and "P14" in p.campos["motivo"]
    assert "baixa confiança" not in p.campos["motivo"]
    # exemplo do mesmo extrato, já classificado por regra
    assert "'TAR PACOTE SERVICOS' | valor -50.00 | conta 4.2.01" in cliente.chamadas[0]["messages"][0]["content"]


def test_bancos_abaixo_do_limiar_diz_baixa_confianca(cfg_bancos, contas, cfg_ia):
    [_, sugerido], pendencias = _classificar_com_ia(cfg_bancos, contas, cfg_ia, ClienteFalso(_json(confianca=0.55)))
    assert (sugerido.campos["metodo"], sugerido.campos["confianca"]) == ("IA", D("0.55"))
    assert "baixa confiança" in pendencias["PEN-IA-R11"].campos["motivo"]
    assert "0.80" in pendencias["PEN-IA-R11"].campos["motivo"]


def test_bancos_no_limiar_nao_e_baixa_confianca(cfg_bancos, contas, cfg_ia):
    _, pendencias = _classificar_com_ia(cfg_bancos, contas, cfg_ia, ClienteFalso(_json(confianca=0.80)))
    assert "baixa confiança" not in pendencias["PEN-IA-R11"].campos["motivo"]


def test_bancos_sugestao_descartada_fica_humano(cfg_bancos, contas, cfg_ia):
    [_, item], pendencias = _classificar_com_ia(cfg_bancos, contas, cfg_ia, ClienteFalso(_json(conta=CONTA_SINTETICA)))
    assert (item.campos["conta_codigo"], item.campos["metodo"], item.campos["confianca"]) == \
           ("A_CLASSIFICAR", "HUMANO", D("0.00"))
    assert set(pendencias) == {"PEN-SEMREGRA-R11"}


def test_setembro_nenhum_lancamento_usa_ia(entradas):
    com_ia = bancos(entradas, cliente_ia=ClienteProibido())  # chamar a IA reprova
    sem_ia = bancos(dataclasses.replace(entradas, usar_ia=False))
    assert com_ia == sem_ia
    assert not any(i.campos.get("metodo") == "IA" for i in com_ia)
    assert not any(i.id_saida.startswith("PEN-IA-") for i in com_ia)


# ---------------------------------------------------------------- outubro simulado, com cliente falso

class ClientePorDescricao(ClienteFalso):
    def __init__(self, por_trecho: dict[str, str]):
        super().__init__()
        self.por_trecho = por_trecho

    def create(self, **kw):
        pergunta = kw["messages"][0]["content"].split("Lançamento a classificar:")[1]
        [texto] = [t for trecho, t in self.por_trecho.items() if trecho in pergunta]
        self.respostas.append(texto)
        return super().create(**kw)


def _ler(pasta: Path, nome: str) -> dict[str, dict]:
    with open(pasta / nome, encoding="utf-8", newline="") as f:
        return {l["id_saida"]: l for l in csv.DictReader(f, delimiter=";")}


def test_outubro_com_ia_falsa(tmp_path):
    casos = gerar(SETEMBRO, tmp_path / "2026-10")
    config_ia = tmp_path / "ia.yaml"
    with open(ia.CONFIG_IA, encoding="utf-8") as f:
        bruto = yaml.safe_load(f)
    bruto |= {"habilitada": True, "cache": str(tmp_path / "cache.json")}
    with open(config_ia, "w", encoding="utf-8") as f:
        yaml.safe_dump(bruto, f, allow_unicode=True)

    cliente = ClientePorDescricao({
        "GRAFICA RAPIDA": _json(conta="4.2.04", confianca=0.62, justificativa="Fornecedor de gráfica."),
        "INSTITUTO SAKURA": _json(conta="1.1.09.002", confianca=0.85, justificativa="Pagador sem cadastro."),
    })
    saida = tmp_path / "saida"
    modulos = [checkout, remessa, partial(bancos, config_ia=config_ia, cliente_ia=cliente)]
    fechar(casos["aurora"]["arquivo"].parent, saida, "2026-10", modulos=modulos)
    assert validar_saida(saida) == []
    assert len(cliente.chamadas) == 2  # só os dois lançamentos sem regra

    lancamentos, pendencias = _ler(saida, "lancamentos_classificados.csv"), _ler(saida, "pendencias.csv")
    for tipo, banco, conta, conf in (("aurora", "AUR", "4.2.04", "0.62"), ("meridiano", "MER", "1.1.09.002", "0.85")):
        ref = casos[tipo]["ref_origem"]
        lan = lancamentos[f"LAN-{banco}-{ref}"]
        assert (lan["conta_codigo"], lan["metodo"], lan["confianca"]) == (conta, "IA", conf)
        pen = pendencias[f"PEN-IA-{ref}"]
        assert (pen["tipo"], pen["quem_decide"]) == ("REVISAR_SUGESTAO_IA", "Financeiro")
        assert Decimal(pen["valor_brl"]) == casos[tipo]["valor"]
        assert f"PEN-SEMREGRA-{ref}" not in pendencias
    assert "baixa confiança" in pendencias[f"PEN-IA-{casos['aurora']['ref_origem']}"]["motivo"]
    assert "baixa confiança" not in pendencias[f"PEN-IA-{casos['meridiano']['ref_origem']}"]["motivo"]
    assert sum(l["metodo"] == "IA" for l in lancamentos.values()) == 2

    # de novo, só com o cache: mesma saída, nenhuma chamada
    saida2 = tmp_path / "saida2"
    modulos = [checkout, remessa, partial(bancos, config_ia=config_ia, cliente_ia=ClienteProibido())]
    fechar(casos["aurora"]["arquivo"].parent, saida2, "2026-10", modulos=modulos)
    for p in saida.iterdir():
        assert (saida2 / p.name).read_bytes() == p.read_bytes(), p.name


# ---------------------------------------------------------------- CLI

def test_cli_flag_sem_ia():
    base = ["fechar", "--competencia", "2026-09", "--entrada", "x", "--saida", "y"]
    assert construir_parser().parse_args(base).sem_ia is False
    assert construir_parser().parse_args(base + ["--sem-ia"]).sem_ia is True
