"""Rascunhos de e-mail de contestação (R29): um por contraparte, com as operações em anexo.

Usa os itens que os módulos já calcularam. Dados de apoio (tipo, data e modalidade da linha da Orbe, datas e
spreads da Ponte, vigência do contrato) vêm das entradas, só por consulta. Os únicos números novos são as partes
da Tarvo (R11, P24), calculadas a partir dos valores dos itens e do relatório da Ponte. Grava numa pasta irmã de
saida/ (config/contestacao.yaml), que continua com exatamente os 6 CSVs:
- orbe.md + orbe_operacoes.csv: divergências de checkout (DIV-CHK);
- ponte.md + ponte_operacoes.csv: divergências de remessa (DIV-REM), spreads negativos (PEN-NEG-REM, R23) e
  operação duplicada (PEN-DUP-REM).
Cada .md abre com um bloco de notas internas para a Helena (a apagar antes de enviar); o corpo do e-mail não fala
de aviso do Comercial. Todo total do texto é a soma das linhas do CSV ao lado.
Fechamento parcial (R44): com uma fonte do rascunho bloqueada, o .md diz que não foi gerado e por quê, e o CSV sai só
com o cabeçalho (nunca fica o rascunho de uma execução anterior); com o checkout provisório, as notas avisam.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

import yaml

from tarvo import checkout as mod_checkout
from tarvo import dependencias as dep
from tarvo import remessa as mod_remessa
from tarvo.leitores.comum import dinheiro
from tarvo.resumo import _tabela, brl
from tarvo.saida import ENCODING, FIM_DE_LINHA, SEPARADOR, ItemSaida, texto_saida

if TYPE_CHECKING:
    from tarvo.fechamento import Entradas

CONFIG_CONTESTACAO = Path(__file__).resolve().parents[2] / "config" / "contestacao.yaml"
ZERO = Decimal("0.00")
QUATRO = Decimal("0.0001")

ARQUIVO_ORBE = ("orbe.md", "orbe_operacoes.csv")
ARQUIVO_PONTE = ("ponte.md", "ponte_operacoes.csv")

COLUNAS_ORBE = ["id_saida", "cnpj", "lojista", "ref_origem", "data_movimento", "tipo_lancamento",
                "valor_bruto", "taxa_contratada_pct", "taxa_aplicada_pct", "diferenca_brl"]
COLUNAS_PONTE = ["id_saida", "natureza", "cnpj", "lojista", "ref_origem", "data_contratacao",
                 "taxa_contratada_pct", "taxa_aplicada_pct", "valor_brl", "parte_tarvo_brl",
                 "spread_aplicado_brl", "spread_contratado_brl", "tarvo_deixou_de_receber_brl", "valor_operacao_brl"]

ACIMA, NEGATIVO, DUPLICADA = "SPREAD_ACIMA_CONTRATADO", "SPREAD_NEGATIVO", "OPERACAO_DUPLICADA"
TIPO_ESTORNO = "ESTORNO"
COMUNICACAO, CONTRATO = "comunicacao", "contrato"


class ErroContestacao(ValueError):
    """Configuração ou dado que impede montar os rascunhos."""


@dataclass(frozen=True)
class ConfigContestacao:
    pasta: str
    cabecalho: str
    titulo_notas: str
    destinatarios: dict[str, str]
    nomes: dict[str, str]
    lojistas: dict[str, dict[str, str]]
    padrao_lojista: dict[str, str]
    textos_aviso: dict[str, str]
    modalidades: dict[str, str]
    campos_taxa: dict[str, str]
    nota_concessao: str

    def secao(self, cnpj: str) -> str:
        return self.lojistas.get(cnpj, self.padrao_lojista)["secao"]

    def aviso(self, cnpj: str) -> str:
        return self.lojistas.get(cnpj, self.padrao_lojista)["aviso"]

    def modalidade(self, chave: str) -> str:
        return self.modalidades.get(chave, chave.lower())


def carregar_config(caminho=CONFIG_CONTESTACAO) -> ConfigContestacao:
    with open(caminho, encoding="utf-8") as f:
        bruto = yaml.safe_load(f)
    cfg = ConfigContestacao(
        pasta=bruto["pasta"], cabecalho=bruto["cabecalho"], titulo_notas=bruto["titulo_notas"],
        destinatarios=dict(bruto["destinatarios"]), nomes=dict(bruto["nomes"]),
        lojistas={str(k): dict(v) for k, v in (bruto.get("lojistas") or {}).items()},
        padrao_lojista=dict(bruto["padrao_lojista"]), textos_aviso=dict(bruto["textos_aviso"]),
        modalidades=dict(bruto["modalidades"]), campos_taxa=dict(bruto["campos_taxa"]),
        nota_concessao=bruto["nota_concessao"],
    )
    for cnpj, l in [("padrao_lojista", cfg.padrao_lojista), *cfg.lojistas.items()]:
        if l.get("aviso") not in cfg.textos_aviso:
            raise ErroContestacao(f"config: {cnpj}: aviso {l.get('aviso')!r} sem texto em textos_aviso")
        if l.get("secao") not in (COMUNICACAO, CONTRATO):
            raise ErroContestacao(f"config: {cnpj}: secao deve ser {COMUNICACAO!r} ou {CONTRATO!r}, veio {l.get('secao')!r}")
    return cfg


def pasta_padrao(saida, cfg: ConfigContestacao) -> Path:
    """Pasta irmã da pasta de saída."""
    return Path(saida).resolve().parent / cfg.pasta


# ---------------------------------------------------------------- formatação

def _p4(v: Decimal) -> str:
    return format(v.quantize(QUATRO, rounding=ROUND_HALF_UP), "f")


def _pp_br(v: Decimal) -> str:
    """Pontos percentuais com 2 a 4 casas: 0.5000 vira "0,50" e 1.4991 fica "1,4991"."""
    inteiro, _, frac = _p4(v).partition(".")
    return f"{inteiro},{frac.rstrip('0').ljust(2, '0')}"


def _pct_br(v: Decimal) -> str:
    return _pp_br(v) + "%"


def _rs(v: Decimal) -> str:
    """"R$ 1.234,50"; negativo vira "-R$ 1.234,50"."""
    return f"{'-' if v < 0 else ''}R$ {brl(abs(v))}"


def _faixa_pct(valores: Iterable[Decimal]) -> str:
    vs = sorted(set(v.quantize(QUATRO, rounding=ROUND_HALF_UP) for v in valores))
    return _pct_br(vs[0]) if len(vs) == 1 else f"{_pct_br(vs[0])} a {_pct_br(vs[-1])}"


def _faixa_pp(valores: Iterable[Decimal]) -> str:
    vs = sorted(set(v.quantize(QUATRO, rounding=ROUND_HALF_UP) for v in valores))
    return _pp_br(vs[0]) if len(vs) == 1 else f"{_pp_br(vs[0])} a {_pp_br(vs[-1])}"


def _periodo(datas: Iterable[date]) -> str:
    """"em AAAA-MM-DD" ou "de AAAA-MM-DD a AAAA-MM-DD"."""
    ds = sorted(set(datas))
    return f"em {ds[0].isoformat()}" if len(ds) == 1 else f"de {ds[0].isoformat()} a {ds[-1].isoformat()}"


def _lista(itens: list[str]) -> str:
    return itens[0] if len(itens) == 1 else ", ".join(itens[:-1]) + " e " + itens[-1]


def _d(v) -> str:
    return "" if v is None else format(v, "f")


def _csv(caminho: Path, colunas: list[str], linhas: list[dict]) -> None:
    with open(caminho, "w", encoding=ENCODING, newline="") as f:
        w = csv.writer(f, delimiter=SEPARADOR, lineterminator=FIM_DE_LINHA, quoting=csv.QUOTE_MINIMAL)
        w.writerow(colunas)
        for l in linhas:
            w.writerow([l.get(c, "") for c in colunas])


def _texto(caminho: Path, linhas: list[str]) -> None:
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(linhas).rstrip("\n") + "\n")


@dataclass(frozen=True)
class Condicao:
    descricao: str
    inicio: date | None
    fim: date | None
    ref: str = ""   # linha da planilha ou regra: só nas notas internas
    obs: str = ""   # observação da planilha: só nas notas internas

    def vigencia(self) -> str:
        if self.inicio and self.fim:
            return f"vigente de {self.inicio.isoformat()} a {self.fim.isoformat()}"
        if self.inicio:
            return f"vigente desde {self.inicio.isoformat()}"
        if self.fim:
            return f"vigente até {self.fim.isoformat()}"
        return "sem data de início na planilha"

    def texto(self) -> str:
        return f"{self.descricao} {self.vigencia()}"


def _aviso(cnpj: str, condicoes: list[Condicao], contraparte: str, cfg: ConfigContestacao) -> str:
    inicios = sorted(c.inicio for c in condicoes if c.inicio)
    return cfg.textos_aviso[cfg.aviso(cnpj)].format(
        contraparte=contraparte, inicio=inicios[0].isoformat() if inicios else "data não registrada")


def _por_prefixo(itens: Iterable[ItemSaida], prefixo: str) -> list[ItemSaida]:
    return [i for i in itens if i.id_saida.startswith(prefixo)]


def _por_cnpj(linhas: list[dict]) -> dict[str, list[dict]]:
    grupos: dict[str, list[dict]] = defaultdict(list)
    for l in linhas:
        grupos[l["cnpj"]].append(l)
    return dict(sorted(grupos.items(), key=lambda kv: kv[1][0]["lojista"]))


def _bloco_notas(cfg: ConfigContestacao, notas: list[str]) -> list[str]:
    return [cfg.titulo_notas, "", *notas, "", "---", ""]


# ---------------------------------------------------------------- Orbe

def _linhas_orbe(itens, entradas, contratos, cfg) -> list[dict]:
    orbe = {l["ref_origem"]: l for l in entradas.orbe.to_dict("records")}
    linhas = []
    for i in _por_prefixo(itens, "DIV-CHK-"):
        ref, cnpj = i.campos["ref_origem"], i.campos["cnpj"]
        if ref not in orbe:
            raise ErroContestacao(f"{i.id_saida}: transação {ref} não está no relatório da Orbe")
        o = orbe[ref]
        contratada, aplicada = i.campos["taxa_contratada_pct"], i.campos["taxa_aplicada_pct"]
        linhas.append({
            "id_saida": i.id_saida, "cnpj": cnpj, "lojista": texto_saida(contratos.nome(cnpj)), "ref_origem": ref,
            "data_movimento": o["data_movimento"].isoformat(), "tipo_lancamento": o["tipo_lancamento"],
            "valor_bruto": format(o["valor_bruto"], "f"), "taxa_contratada_pct": _p4(contratada),
            "taxa_aplicada_pct": _p4(aplicada), "diferenca_brl": format(i.valor_reportado, "f"),
            "_data_ref": o["data_venda_original"] or o["data_movimento"], "_mov": o["data_movimento"],
            "_chave": o["modalidade"] or o["tipo_lancamento"], "_delta": aplicada - contratada,
        })
    return sorted(linhas, key=lambda l: (l["lojista"], l["data_movimento"], l["ref_origem"]))


def _condicoes_checkout(cnpj: str, datas: Iterable[date], contratos, cfg_ck) -> list[Condicao]:
    """Condições vigentes nas datas de referência das linhas contestadas (condição especial antes da planilha)."""
    achadas: dict[str, Condicao] = {}
    for d in sorted(set(datas)):
        especial = next((c for c in cfg_ck.condicoes if c.cnpj == cnpj and c.vale_em(d)), None)
        if especial is not None:
            taxas = " e ".join(sorted({f"{v.quantize(Decimal('0.01'))}".replace(".", ",") + "%" for v in especial.taxas.values()}))
            achadas[especial.regra] = Condicao(f"condição especial (taxa contratada de {taxas} nas tarifas de checkout)",
                                               especial.inicio, especial.fim, ref=f"condição especial {especial.regra} do config/checkout.yaml")
            continue
        linha = contratos.vigente(cnpj, d)
        achadas[linha["ref_origem"]] = Condicao("condição contratada", linha["vigencia_inicio"], linha["vigencia_fim"],
                                                ref=f"planilha de taxas, {linha['ref_origem']}", obs=linha["obs"] or "")
    return sorted(achadas.values(), key=lambda c: (c.inicio or date.min, c.descricao))


def _mudanca_contrato(cnpj: str, condicao: Condicao, contratos, cfg: ConfigContestacao) -> str:
    """Quais modalidades mudaram na linha da planilha que começa em condicao.inicio, comparada com a anterior."""
    if condicao.inicio is None or not condicao.ref.startswith("planilha"):
        return ""
    try:
        antes = contratos.vigente(cnpj, condicao.inicio - timedelta(days=1))
        agora = contratos.vigente(cnpj, condicao.inicio)
    except mod_checkout.ErroCheckout:
        return ""
    mudou = [c for c in cfg.campos_taxa if agora.get(c) != antes.get(c) and agora.get(c) is not None]
    if not mudou:
        return ""
    quais = _lista([f"{cfg.campos_taxa[c]} ({_pct_br(agora[c])})" for c in mudou])
    return (f"A nova condição vale só para {quais}, desde {condicao.inicio.isoformat()}; "
            f"as demais modalidades não mudaram.")


def _perfil_orbe(ls: list[dict], todas_do_lojista: list[dict], condicoes: list[Condicao], cfg) -> list[str]:
    """Frases sobre quando a diferença começou, para o lojista cujo contrato já valia antes dela."""
    vendas = [l for l in ls if l["tipo_lancamento"] != TIPO_ESTORNO] or ls
    d1 = min(l["_mov"] for l in vendas)
    inicios = [c.inicio for c in condicoes]
    if any(i is not None and i >= d1 for i in inicios):  # contrato novo a partir da diferença: nada a comparar
        return []
    antes = [l for l in todas_do_lojista if l["data_movimento"] < d1]
    divergentes = {l["ref_origem"] for l in ls}
    div_chaves = sorted({l["_chave"] for l in vendas})
    depois = [l for l in todas_do_lojista if l["data_movimento"] >= d1 and l["tipo_lancamento"] != TIPO_ESTORNO]
    nas_div = [l for l in depois if l["_chave"] in div_chaves]
    outras = sorted({l["_chave"] for l in depois if l["_chave"] not in div_chaves})
    total = len(nas_div)
    qtd = sum(1 for l in nas_div if l["ref_origem"] in divergentes)
    quantas = f"todas as {qtd}" if qtd == total else f"{qtd} das {total}"
    mods = _lista([cfg.modalidade(c) for c in div_chaves])
    frases = []
    if antes:
        frases.append(f"Até {(d1 - timedelta(days=1)).isoformat()} ({len(antes)} transações), a taxa aplicada foi a contratada.")
    frase = (f"A partir de {d1.isoformat()}, {quantas} transações de {mods} vieram com a taxa "
             f"{_faixa_pp(l['_delta'] for l in vendas)} p.p. acima da contratada")
    if outras:
        frase += f"; as de {_lista([cfg.modalidade(c) for c in outras])} seguiram a taxa contratada"
    return frases + [frase + "."]


def _taxa_concessao(cnpj: str, cfg_ck) -> str:
    return mod_checkout.taxa_concessao(cnpj, cfg_ck)


def _notas_concessao(concessoes, contratos, cfg, cfg_ck) -> list[str]:
    """R32, R38: a devolução da concessão é custo da Tarvo e não vai no e-mail; só nas notas."""
    if not concessoes:
        return []
    linhas = ["", "Concessões comerciais (fora do e-mail, R32):"]
    for cnpj, valor in sorted(concessoes.items()):
        linhas.append("- " + cfg.nota_concessao.format(lojista=texto_saida(contratos.nome(cnpj)), valor=_rs(valor),
                                                          contraparte=cfg.nomes["orbe"], taxa=_taxa_concessao(cnpj, cfg_ck)))
    return linhas


def _md_orbe(linhas, todas_orbe, entradas, contratos, cfg, cfg_ck, devolucoes, concessoes) -> list[str]:
    nome, comp = cfg.nomes["orbe"], entradas.competencia
    cabeca = [cfg.cabecalho, ""]
    topo = [f"Para: {cfg.destinatarios['orbe']}", f"Assunto: Taxas de checkout - competência {comp}", ""]
    if not linhas:
        notas = ["- Nenhuma divergência de checkout na competência."] + _notas_concessao(concessoes, contratos, cfg, cfg_ck)
        return cabeca + _bloco_notas(cfg, notas) + topo + [
            f"Nenhuma transação da competência {comp} com taxa aplicada diferente da contratada. Não há o que enviar à {nome}."]
    grupos = _por_cnpj(linhas)
    condicoes = {c: _condicoes_checkout(c, (l["_data_ref"] for l in ls), contratos, cfg_ck) for c, ls in grupos.items()}
    estornos = [l for l in linhas if l["tipo_lancamento"] == TIPO_ESTORNO]
    total = sum((Decimal(l["diferenca_brl"]) for l in linhas), ZERO)

    notas = ["Contexto interno. Nada deste bloco vai para a Orbe.", "",
             "Avisos da condição à contraparte (resposta da Helena às 9h53):"]
    for cnpj, ls in grupos.items():
        notas.append(f"- {ls[0]['lojista']}: {_aviso(cnpj, condicoes[cnpj], nome, cfg)}")
    notas += ["", "Condição usada no texto (referências da planilha, que não vão no e-mail):"]
    for cnpj, ls in grupos.items():
        for c in condicoes[cnpj]:
            notas.append(f"- {ls[0]['lojista']}: {c.ref}" + (f", observação \"{c.obs}\"" if c.obs else "") + f", {c.vigencia()}.")
    notas += ["", "Valor a devolver a cada lojista (R25, R45, pendências PEN-DEVOL-CHK): o que saiu do bolso do lojista, "
                  "o valor_taxa descontado pela Orbe menos a comissão pela taxa contratada, transação a transação."]
    for cnpj, ls in grupos.items():
        formula = sum((Decimal(l["diferenca_brl"]) for l in ls), ZERO)
        devolver = devolucoes.get(cnpj)
        if devolver is None:
            notas.append(f"- {ls[0]['lojista']}: sem pendência de devolução; a divergência soma {_rs(formula)}.")
        elif devolver == formula:
            notas.append(f"- {ls[0]['lojista']}: {_rs(devolver)}.")
        else:
            notas.append(f"- {ls[0]['lojista']}: **{_rs(devolver)}**. O e-mail cobra da {nome} {_rs(formula)} (valor bruto × "
                         f"diferença de taxa, arredondado, como em divergencias_taxa.csv); nas mesmas {len(ls)} transações, "
                         f"o descontado de fato a mais foi {_rs(devolver)}. A diferença de {_rs(formula - devolver)} é "
                         f"arredondamento: a {nome} trunca o valor_taxa no centavo (P03).")
    if estornos:
        notas += ["", f"Os {len(estornos)} estornos entram no total do e-mail e o reduzem."]
    notas += _notas_concessao(concessoes, contratos, cfg, cfg_ck)

    comunicacao = [c for c in grupos if cfg.secao(c) == COMUNICACAO]
    contrato = [c for c in grupos if cfg.secao(c) != COMUNICACAO]
    partes = " Dividimos o assunto em duas partes." if comunicacao and contrato else ""
    texto = cabeca + _bloco_notas(cfg, notas) + topo + [
        "Prezados,", "",
        f"Na conferência da competência {comp}, comparamos as taxas contratadas dos lojistas com as aplicadas pela {nome} "
        f"em {len(linhas)} transações de {len(grupos)} lojistas. As transações estão no anexo orbe_operacoes.csv "
        f"(coluna diferenca_brl = valor bruto × diferença entre a taxa aplicada e a contratada).{partes}", ""]

    def tabela(cnpjs):
        return _tabela(["lojista", "CNPJ", "transações", "taxa contratada", "taxa aplicada", "diferença (R$)"],
                       [[grupos[c][0]["lojista"], c, len(grupos[c]),
                         _faixa_pct(Decimal(l["taxa_contratada_pct"]) for l in grupos[c]),
                         _faixa_pct(Decimal(l["taxa_aplicada_pct"]) for l in grupos[c]),
                         brl(sum((Decimal(l["diferenca_brl"]) for l in grupos[c]), ZERO))] for c in cnpjs],
                       numericas={2, 5})

    n = 1
    if comunicacao:
        texto += [f"## {n}. Comunicação de condição comercial", ""]
        n += 1
        for c in comunicacao:
            ls = grupos[c]
            texto += [f"- {ls[0]['lojista']} (CNPJ {c}): {condicoes[c][0].texto()}."] + \
                     [f"  - {x.texto()}." for x in condicoes[c][1:]]
        texto += ["", tabela(comunicacao), ""]
        frases, rodape = [], []
        for c in comunicacao:
            ls = grupos[c]
            formula = sum((Decimal(l["diferenca_brl"]) for l in ls), ZERO)
            descontado = devolucoes.get(c)
            if descontado is not None and all(Decimal(l["taxa_contratada_pct"]) == 0 for l in ls):
                frases.append(f"Para {ls[0]['lojista']}, com taxa contratada de 0,00%, todo o valor descontado pela {nome} deve ser "
                              f"regularizado: {_rs(descontado)} (soma do valor_taxa das {len(ls)} transações).")
                if descontado != formula:
                    rodape.append(f"Nota: a tabela mostra valor bruto × taxa aplicada, arredondado ({_rs(formula)}); a {nome} trunca o "
                                  f"valor_taxa no centavo, por isso o valor efetivamente descontado é {_rs(formula - descontado)} menor.")
            else:
                frases.append(f"Para {ls[0]['lojista']}, o período soma {_rs(formula)} sobre as transações do anexo.")
        texto += [f"Comunicamos a condição acima e pedimos (1) a parametrização das taxas conforme a condição e (2) a "
                  f"regularização do período já processado. {' '.join(frases)}", ""] + [r for x in rodape for r in (x, "")]
    if contrato:
        soma = sum((Decimal(l["diferenca_brl"]) for c in contrato for l in grupos[c]), ZERO)
        texto += [f"## {n}. Taxas aplicadas acima do contrato", ""]
        for c in contrato:
            ls = grupos[c]
            conds = condicoes[c]
            vendas = [l for l in ls if l["tipo_lancamento"] != TIPO_ESTORNO] or ls
            mods = _lista(sorted({cfg.modalidade(l["_chave"]) for l in vendas}))
            texto.append(f"- {ls[0]['lojista']} (CNPJ {c}): {_lista([x.texto() for x in conds])}. {len(ls)} transações de "
                         f"{mods}, {_periodo(l['_mov'] for l in vendas)}, com taxa aplicada de "
                         f"{_faixa_pct(Decimal(l['taxa_aplicada_pct']) for l in ls)} contra "
                         f"{_faixa_pct(Decimal(l['taxa_contratada_pct']) for l in ls)} contratados, "
                         f"somando {_rs(sum((Decimal(l['diferenca_brl']) for l in ls), ZERO))}.")
            texto += [f"  - {m}" for m in (_mudanca_contrato(c, x, contratos, cfg) for x in conds) if m]
            texto += [f"  - {f}" for f in _perfil_orbe(ls, todas_orbe.get(c, []), conds, cfg)]
        texto += ["", tabela(contrato), "",
                  f"Pedimos que a {nome} informe a causa e corrija a parametrização. O total desta parte é {_rs(soma)}.", ""]
    if estornos:
        texto += [f"Dos totais acima, {len(estornos)} linhas são estornos: eles devolvem o que foi cobrado a maior na venda "
                  f"original e reduzem o total em {_rs(abs(sum((Decimal(l['diferenca_brl']) for l in estornos), ZERO)))}.", ""]
    return texto + ["Atenciosamente,", "[assinatura da Helena]"]


def _todas_orbe_por_cnpj(entradas, contratos) -> dict[str, list[dict]]:
    """Todas as linhas da Orbe de cada lojista com contrato (casadas pelo EC), para comparar com as divergentes."""
    grupos: dict[str, list[dict]] = defaultdict(list)
    for o in entradas.orbe.to_dict("records"):
        cnpj = contratos.ec_cnpj.get(o["cod_estabelecimento"])
        if cnpj is not None:
            grupos[cnpj].append({"ref_origem": o["ref_origem"], "data_movimento": o["data_movimento"],
                                 "tipo_lancamento": o["tipo_lancamento"], "_chave": o["modalidade"] or o["tipo_lancamento"]})
    return grupos


# ---------------------------------------------------------------- Ponte

def _linhas_ponte(itens, entradas, contratos, participacao) -> list[dict]:
    ponte: dict[str, dict] = {}
    for op in sorted(entradas.ponte.to_dict("records"), key=lambda o: o["linha_planilha"]):
        ponte.setdefault(op["ref_origem"], op)

    def nome(cnpj, op):
        return texto_saida(contratos.nome(cnpj) if contratos.cadastrado(cnpj) else (op["cliente"] or cnpj))

    def base(i, natureza, ref):
        if ref not in ponte:
            raise ErroContestacao(f"{i.id_saida}: operação {ref} não está no relatório da Ponte")
        op = ponte[ref]
        return {"id_saida": i.id_saida, "natureza": natureza, "cnpj": op["cnpj"], "lojista": nome(op["cnpj"], op),
                "ref_origem": ref, "data_contratacao": op["data_contratacao"].isoformat(),
                "valor_brl": format(i.valor_reportado, "f"), "_op": op}

    linhas = []
    for i in _por_prefixo(itens, "DIV-REM-"):
        l = base(i, ACIMA, i.campos["ref_origem"])
        l |= {"taxa_contratada_pct": _p4(i.campos["taxa_contratada_pct"]), "taxa_aplicada_pct": _p4(i.campos["taxa_aplicada_pct"]),
              "parte_tarvo_brl": _d(dinheiro(i.valor_reportado * participacao))}
        linhas.append(l)
    for i in _por_prefixo(itens, "PEN-NEG-REM-"):
        l = base(i, NEGATIVO, i.campos["ref_origem"])
        op = l["_op"]
        contratado, _ = contratos.spread_contratado(l["cnpj"], op["data_contratacao"])
        contratado_brl = dinheiro(contratado / 100 * op["ptax_ref"] * op["valor_me"])
        l |= {"taxa_contratada_pct": _p4(contratado), "taxa_aplicada_pct": _p4(op["spread_pct"]),
              "spread_aplicado_brl": _d(op["spread_brl"]), "spread_contratado_brl": _d(contratado_brl),
              "tarvo_deixou_de_receber_brl": _d(dinheiro(contratado_brl * participacao))}
        linhas.append(l)
    for i in _por_prefixo(itens, "PEN-DUP-REM-"):
        l = base(i, DUPLICADA, i.campos["ref_origem"])
        op = l["_op"]
        l |= {"parte_tarvo_brl": _d(dinheiro(i.valor_reportado * participacao)),
              "valor_operacao_brl": _d(dinheiro(op["valor_brl"] + op["iof_brl"]))}
        linhas.append(l)
    ordem = {ACIMA: 0, NEGATIVO: 1, DUPLICADA: 2}
    return sorted(linhas, key=lambda l: (ordem[l["natureza"]], l["lojista"], l["data_contratacao"], l["ref_origem"]))


def _soma(linhas: list[dict], coluna: str = "valor_brl") -> Decimal:
    return sum((Decimal(l[coluna]) for l in linhas), ZERO)


def _md_ponte(linhas, entradas, contratos, cfg, participacao) -> list[str]:
    nome, comp = cfg.nomes["ponte"], entradas.competencia
    pct = f"{(participacao * 100).quantize(Decimal('1'))}%"
    cabeca = [cfg.cabecalho, ""]
    topo = [f"Para: {cfg.destinatarios['ponte']}", f"Assunto: Relatório de operações - competência {comp}", ""]
    if not linhas:
        return cabeca + _bloco_notas(cfg, ["- Nada a contestar na competência."]) + topo + [
            f"Nenhuma operação da competência {comp} a contestar. Não há o que enviar à {nome}."]
    acima = [l for l in linhas if l["natureza"] == ACIMA]
    neg = [l for l in linhas if l["natureza"] == NEGATIVO]
    dup = [l for l in linhas if l["natureza"] == DUPLICADA]
    grupos = _por_cnpj(acima)

    def condicoes_remessa(cnpj, ls):
        achadas = {}
        for l in ls:
            d = l["_op"]["data_contratacao"]
            row = contratos.vigente(cnpj, d)
            achadas[row["ref_origem"]] = row
        return list(achadas.values())

    notas = ["Contexto interno. Nada deste bloco vai para a Ponte.", "", "Avisos da condição à contraparte (resposta da Helena às 9h53):"]
    for cnpj, ls in grupos.items():
        rows = condicoes_remessa(cnpj, ls)
        conds = [Condicao("", r["vigencia_inicio"], r["vigencia_fim"]) for r in rows]
        notas.append(f"- {ls[0]['lojista']}: {_aviso(cnpj, conds, nome, cfg)} (planilha de taxas, {', '.join(r['ref_origem'] for r in rows)})")
    for cnpj, ls in grupos.items():
        if cfg.secao(cnpj) != COMUNICACAO:  # R32: o que decide é o contrato, não o aviso
            obs = "; ".join(r["obs"] for r in condicoes_remessa(cnpj, ls) if r["obs"])
            notas.append(f"- {ls[0]['lojista']}: {_faixa_pct(Decimal(l['taxa_contratada_pct']) for l in ls)} contratado e "
                         f"registrado na planilha" + (f" ({obs})" if obs else "") +
                         " - o que decide é o contrato, não o aviso (Helena, 11h37).")
        else:
            for r in condicoes_remessa(cnpj, ls):
                notas.append(f"- Ressalva ({ls[0]['lojista']}): a planilha registra a condição como {Condicao('', r['vigencia_inicio'], r['vigencia_fim']).vigencia()}"
                             + (f" e a observação \"{r['obs']}\"" if r["obs"] else "")
                             + ". O e-mail não cita data de início; confirme a data da condição antes de enviar.")
    if acima:
        notas += ["", f"Valor a ressarcir ao lojista (R15, R32, PEN-CONTEST-REM): {_rs(_soma(acima))}, o spread inteiro pago a mais pelo cliente. "
                      f"A Tarvo já recebeu {pct} do spread realizado dessas operações na comissão e na nota (R16), ou seja, "
                      f"{_rs(_soma(acima, 'parte_tarvo_brl'))} do excesso, a ajustar quando a Ponte devolver (R27)."]
    if neg:
        notas += ["", f"Spreads negativos (R34): o e-mail pede à Ponte a diferença até o spread contratado, "
                      f"{_rs(abs(_soma(neg)))} no total (o valor da PEN-NEG, P18), e mostra o spread do relatório. Nenhuma dessas "
                      f"operações entrou em COM-REM nem em NF-REM (R12). A parte da Tarvo, {pct} do spread contratado, é o que a Tarvo "
                      f"deixou de receber: {_rs(_soma(neg, 'tarvo_deixou_de_receber_brl'))} (P24, ainda sem aprovação); fica fora do e-mail."]
    if dup:
        notas += ["", f"Duplicada: o valor da PEN-DUP ({_rs(_soma(dup))}) é o spread da cópia (P19); a parte da Tarvo ({_rs(_soma(dup, 'parte_tarvo_brl'))}, "
                      f"{pct}) entrou uma vez só na comissão e na nota (R13)."]

    texto = cabeca + _bloco_notas(cfg, notas) + topo + [
        "Prezados,", "",
        f"Na conferência do relatório de operações da competência {comp}, a Tarvo identificou {len(linhas)} operações para "
        f"tratar, descritas no anexo ponte_operacoes.csv (coluna natureza).", ""]
    def bullets(cnpjs):
        linhas_md = []
        for cnpj in cnpjs:
            ls = grupos[cnpj]
            obs = "; ".join(r["obs"] for r in condicoes_remessa(cnpj, ls) if r["obs"])
            linhas_md.append(f"- {ls[0]['lojista']} (CNPJ {cnpj}): spread contratado de "
                             f"{_faixa_pct(Decimal(l['taxa_contratada_pct']) for l in ls)}" + (f" ({obs})" if obs else "") +
                             f". {len(ls)} operações contratadas {_periodo(l['_op']['data_contratacao'] for l in ls)} saíram com "
                             f"spread de {_faixa_pct(Decimal(l['taxa_aplicada_pct']) for l in ls)}, e o cliente pagou "
                             f"{_rs(_soma(ls))} a maior (spread inteiro, sobre a PTAX de referência).")
        return linhas_md

    n = 1
    comunicacao = [c for c in grupos if cfg.secao(c) == COMUNICACAO]
    contrato = [c for c in grupos if cfg.secao(c) != COMUNICACAO]
    if comunicacao:
        soma = sum((_soma(grupos[c]) for c in comunicacao), ZERO)
        texto += [f"## {n}. Comunicação de condição comercial", "", *bullets(comunicacao), "",
                  f"Comunicamos a condição acima e pedimos a regularização do período: o ajuste das operações do anexo, com a "
                  f"diferença de {_rs(soma)} devolvida ao cliente, no relatório do mês seguinte, como crédito ou débito.", ""]
        n += 1
    if contrato:  # R32: divergência de contrato, a Tarvo contesta e o lojista é ressarcido
        soma = sum((_soma(grupos[c]) for c in contrato), ZERO)
        texto += [f"## {n}. Contestação: spread acima do contratado", "", *bullets(contrato), "",
                  f"Pedimos a correção das operações do anexo e o ressarcimento ao cliente da diferença de {_rs(soma)}, no "
                  f"relatório do mês seguinte, como crédito ou débito.", ""]
        n += 1
    if neg:  # R34: o pedido é a diferença até o spread contratado; o spread do relatório aparece ao lado
        obs = sorted({l["_op"]["observacao"] for l in neg if l["_op"]["observacao"]})
        motivo = f" Observação do relatório: {'; '.join(obs)}." if obs else ""
        total = abs(_soma(neg))
        texto += [f"## {n}. Contestação: spreads negativos", "",
                  f"{len(neg)} operações saíram com spread negativo.{motivo} A trava D-1 deveria ter sido honrada: pedimos à "
                  f"Ponte a diferença até o spread contratado, {_rs(total)} no total.", ""]
        n += 1
        texto += [_tabela(["operação", "lojista", "contratação", "spread contratado (R$)", "spread do relatório (R$)",
                           "diferença pedida (R$)"],
                          [[l["ref_origem"], l["lojista"], l["data_contratacao"], brl(Decimal(l["spread_contratado_brl"])),
                            brl(Decimal(l["spread_aplicado_brl"])), brl(abs(Decimal(l["valor_brl"])))] for l in neg],
                          numericas={3, 4, 5}), "",
                  "Pedimos a revisão das operações e o pagamento da diferença até o spread contratado.", ""]
    if dup:
        texto += [f"## {n}. Contestação: operação repetida no relatório", ""]
        n += 1
        for l in dup:
            copias = entradas.ponte[entradas.ponte["ref_origem"] == l["ref_origem"]]
            onde = " e ".join(str(x) for x in sorted(copias["linha_planilha"]))
            texto += [f"- {l['ref_origem']} ({l['lojista']}, contratada em {l['data_contratacao']}) aparece {len(copias)} vezes "
                      f"no relatório (linhas {onde}), com os mesmos valores. Por cópia:",
                      f"  - cliente: operação de {_rs(Decimal(l['valor_operacao_brl']))} (valor em R$ mais IOF);",
                      f"  - spread da operação: {_rs(Decimal(l['valor_brl']))};",
                      f"  - parte da Tarvo ({pct} do spread): {_rs(Decimal(l['parte_tarvo_brl']))}."]
        texto += ["", "Pedimos que a Ponte confirme se o cliente foi cobrado duas vezes e corrija o relatório. A Tarvo conta a "
                      "operação uma vez só.", ""]
    return texto + ["Atenciosamente,", "[assinatura da Helena]"]


# ---------------------------------------------------------------- entrada do módulo

TEXTO_BLOQUEADO = (
    "[BLOQUEADO — rascunho não gerado nesta execução] A fonte {fontes} está bloqueada (pendência {pendencias} em "
    "pendencias.csv, R44): sem ela não há {conteudo} para contestar. Este arquivo substitui o rascunho de qualquer "
    "execução anterior. Próximo passo: liberar a fonte e rodar o fechamento de novo; o rascunho sai sozinho."
)
AVISO_PROVISORIO = (
    "- **PROVISÓRIO:** {arquivos} da {fonte} ficou fora do fechamento (pendência PEN-BLOQUEIO em pendencias.csv, "
    "R44). As operações e os valores abaixo podem mudar quando o arquivo for liberado; confira antes de enviar."
)


def _bloqueado(chave: str, entradas: Entradas, cfg: ConfigContestacao, conteudo: str) -> list[str]:
    fontes = sorted(set(dep.POR_CHAVE[chave].fontes) & dep.bloqueadas(entradas.bloqueios))
    return [cfg.cabecalho, "", TEXTO_BLOQUEADO.format(
        fontes=" e ".join(fontes), pendencias=", ".join(f"PEN-BLOQUEIO-{f.upper()}" for f in fontes), conteudo=conteudo)]


def _com_aviso_provisorio(texto: list[str], chave: str, entradas: Entradas, cfg: ConfigContestacao) -> list[str]:
    """Põe o aviso de provisório no começo das notas internas, logo depois do título delas."""
    if not dep.provisorio(chave, entradas):
        return texto
    avisos = [AVISO_PROVISORIO.format(arquivos=b.arquivo, fonte=b.fonte) for b in entradas.bloqueios
              if b.parcial and b.fonte in dep.POR_CHAVE[chave].fontes]
    i = texto.index(cfg.titulo_notas) + 2
    return texto[:i] + avisos + [""] + texto[i:]


def gerar_contestacoes(itens: Iterable[ItemSaida], entradas: Entradas, pasta, cfg: ConfigContestacao | None = None,
                       cfg_checkout=None, cfg_remessa=None) -> dict[str, Path]:
    """Grava orbe.md, orbe_operacoes.csv, ponte.md e ponte_operacoes.csv em pasta. Devolve nome -> caminho.

    Rascunho com uma fonte bloqueada sai como aviso de bloqueio, com o CSV só com o cabeçalho (R44)."""
    itens = list(itens)
    cfg = cfg or carregar_config()
    cfg_checkout = cfg_checkout or mod_checkout.carregar_config()
    cfg_remessa = cfg_remessa or mod_remessa.carregar_config()
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)

    if dep.gera("contestacao_orbe", entradas):
        ck = mod_checkout.Contratos(entradas.taxas, cfg_checkout)
        devolucoes = {i.id_saida.removeprefix("PEN-DEVOL-CHK-"): i.valor_reportado
                      for i in _por_prefixo(itens, "PEN-DEVOL-CHK-")}
        orbe = _linhas_orbe(itens, entradas, ck, cfg)
        concessoes = {i.id_saida.removeprefix("PEN-CONCESSAO-CHK-"): i.valor_reportado
                      for i in _por_prefixo(itens, "PEN-CONCESSAO-CHK-")}
        md_orbe = _com_aviso_provisorio(
            _md_orbe(orbe, _todas_orbe_por_cnpj(entradas, ck), entradas, ck, cfg, cfg_checkout, devolucoes, concessoes),
            "contestacao_orbe", entradas, cfg)
    else:
        orbe, md_orbe = [], _bloqueado("contestacao_orbe", entradas, cfg, "taxa de checkout")
    if dep.gera("contestacao_ponte", entradas):
        rm = mod_remessa.Contratos(entradas.taxas, cfg_remessa)
        ponte = _linhas_ponte(itens, entradas, rm, cfg_remessa.participacao)
        md_ponte = _com_aviso_provisorio(_md_ponte(ponte, entradas, rm, cfg, cfg_remessa.participacao),
                                         "contestacao_ponte", entradas, cfg)
    else:
        ponte, md_ponte = [], _bloqueado("contestacao_ponte", entradas, cfg, "operação de remessa")

    gravados = {}
    for (md, csv_nome), colunas, linhas, texto in ((ARQUIVO_ORBE, COLUNAS_ORBE, orbe, md_orbe),
                                                  (ARQUIVO_PONTE, COLUNAS_PONTE, ponte, md_ponte)):
        _csv(pasta / csv_nome, colunas, linhas)
        _texto(pasta / md, texto)
        gravados[md], gravados[csv_nome] = pasta / md, pasta / csv_nome
    return gravados
