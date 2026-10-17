"""Rascunhos de e-mail de contestação (R29): um por contraparte, com as operações em anexo.

Usa os itens que os módulos já calcularam; não recalcula valor nenhum. Dados de apoio (tipo e data da linha da
Orbe, datas e spreads da Ponte, vigência do contrato) vêm das entradas, só por consulta. Grava numa pasta
irmã de saida/ (config/contestacao.yaml), que continua com exatamente os 6 CSVs:
- orbe.md + orbe_operacoes.csv: divergências de checkout (DIV-CHK);
- ponte.md + ponte_operacoes.csv: divergências de remessa (DIV-REM), spreads negativos (PEN-NEG-REM, R23) e
  operação duplicada (PEN-DUP-REM).
Todo total do texto é a soma das linhas do CSV ao lado.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

import yaml

from tarvo import checkout as mod_checkout
from tarvo import remessa as mod_remessa
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
                 "taxa_contratada_pct", "taxa_aplicada_pct", "valor_brl"]

ACIMA, NEGATIVO, DUPLICADA = "SPREAD_ACIMA_CONTRATADO", "SPREAD_NEGATIVO", "OPERACAO_DUPLICADA"
TIPO_ESTORNO = "ESTORNO"


class ErroContestacao(ValueError):
    """Configuração ou dado que impede montar os rascunhos."""


@dataclass(frozen=True)
class ConfigContestacao:
    pasta: str
    cabecalho: str
    destinatarios: dict[str, str]
    nomes: dict[str, str]
    avisos: dict[str, str]
    textos_aviso: dict[str, str]


def carregar_config(caminho=CONFIG_CONTESTACAO) -> ConfigContestacao:
    with open(caminho, encoding="utf-8") as f:
        bruto = yaml.safe_load(f)
    cfg = ConfigContestacao(
        pasta=bruto["pasta"], cabecalho=bruto["cabecalho"], destinatarios=dict(bruto["destinatarios"]),
        nomes=dict(bruto["nomes"]), avisos={str(k): v for k, v in (bruto.get("avisos") or {}).items()},
        textos_aviso=dict(bruto["textos_aviso"]),
    )
    desconhecidos = sorted(set(cfg.avisos.values()) - set(cfg.textos_aviso))
    if desconhecidos:
        raise ErroContestacao(f"config: avisos sem texto em textos_aviso: {desconhecidos}")
    return cfg


def pasta_padrao(saida, cfg: ConfigContestacao) -> Path:
    """Pasta irmã da pasta de saída."""
    return Path(saida).resolve().parent / cfg.pasta


# ---------------------------------------------------------------- formatação

def _p4(v: Decimal) -> str:
    return format(v.quantize(QUATRO, rounding=ROUND_HALF_UP), "f")


def _pct_br(v: Decimal) -> str:
    return _p4(v).replace(".", ",") + "%"


def _rs(v: Decimal) -> str:
    """"R$ 1.234,50"; negativo vira "-R$ 1.234,50"."""
    return f"{'-' if v < 0 else ''}R$ {brl(abs(v))}"


def _faixa_pct(valores: Iterable[Decimal]) -> str:
    vs = sorted(set(v.quantize(QUATRO, rounding=ROUND_HALF_UP) for v in valores))
    return _pct_br(vs[0]) if len(vs) == 1 else f"{_pct_br(vs[0])} a {_pct_br(vs[-1])}"


def _faixa_datas(datas: Iterable[date]) -> str:
    ds = sorted(set(datas))
    return ds[0].isoformat() if len(ds) == 1 else f"{ds[0].isoformat()} a {ds[-1].isoformat()}"


def _csv(caminho: Path, colunas: list[str], linhas: list[dict]) -> None:
    with open(caminho, "w", encoding=ENCODING, newline="") as f:
        w = csv.writer(f, delimiter=SEPARADOR, lineterminator=FIM_DE_LINHA, quoting=csv.QUOTE_MINIMAL)
        w.writerow(colunas)
        for l in linhas:
            w.writerow([l[c] for c in colunas])


def _texto(caminho: Path, linhas: list[str]) -> None:
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(linhas).rstrip("\n") + "\n")


@dataclass(frozen=True)
class Condicao:
    descricao: str
    inicio: date | None
    fim: date | None

    def texto(self) -> str:
        if self.inicio and self.fim:
            vig = f"vigente de {self.inicio.isoformat()} a {self.fim.isoformat()}"
        elif self.inicio:
            vig = f"vigente desde {self.inicio.isoformat()}"
        elif self.fim:
            vig = f"vigente até {self.fim.isoformat()}"
        else:
            vig = "sem data de início na planilha"
        return f"{self.descricao}, {vig}"


def _aviso(cnpj: str, condicoes: list[Condicao], contraparte: str, cfg: ConfigContestacao) -> str:
    chave = cfg.avisos.get(cnpj, "sem_registro")
    inicios = sorted(c.inicio for c in condicoes if c.inicio)
    return cfg.textos_aviso[chave].format(contraparte=contraparte,
                                          inicio=inicios[0].isoformat() if inicios else "data não registrada")


def _por_prefixo(itens: Iterable[ItemSaida], prefixo: str) -> list[ItemSaida]:
    return [i for i in itens if i.id_saida.startswith(prefixo)]


# ---------------------------------------------------------------- Orbe

def _linhas_orbe(itens, entradas, contratos) -> list[dict]:
    orbe = {l["ref_origem"]: l for l in entradas.orbe.to_dict("records")}
    linhas = []
    for i in _por_prefixo(itens, "DIV-CHK-"):
        ref, cnpj = i.campos["ref_origem"], i.campos["cnpj"]
        if ref not in orbe:
            raise ErroContestacao(f"{i.id_saida}: transação {ref} não está no relatório da Orbe")
        o = orbe[ref]
        linhas.append({
            "id_saida": i.id_saida, "cnpj": cnpj, "lojista": texto_saida(contratos.nome(cnpj)), "ref_origem": ref,
            "data_movimento": o["data_movimento"].isoformat(), "tipo_lancamento": o["tipo_lancamento"],
            "valor_bruto": format(o["valor_bruto"], "f"), "taxa_contratada_pct": _p4(i.campos["taxa_contratada_pct"]),
            "taxa_aplicada_pct": _p4(i.campos["taxa_aplicada_pct"]), "diferenca_brl": format(i.valor_reportado, "f"),
            "_data_ref": o["data_venda_original"] or o["data_movimento"],
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
                                               especial.inicio, especial.fim)
            continue
        linha = contratos.vigente(cnpj, d)
        descricao = f"contrato da planilha de taxas ({linha['ref_origem']})"
        if linha["obs"]:
            descricao += f", observação: {linha['obs']}"
        achadas[linha["ref_origem"]] = Condicao(descricao, linha["vigencia_inicio"], linha["vigencia_fim"])
    return sorted(achadas.values(), key=lambda c: (c.inicio or date.min, c.descricao))


def _md_orbe(linhas: list[dict], entradas, contratos, cfg, cfg_ck) -> list[str]:
    nome, comp = cfg.nomes["orbe"], entradas.competencia
    texto = [cfg.cabecalho, "", f"Para: {cfg.destinatarios['orbe']}",
             f"Assunto: Taxas aplicadas diferentes das contratadas - competência {comp}", ""]
    if not linhas:
        return texto + [f"Nenhuma transação da competência {comp} com taxa aplicada diferente da contratada. "
                        f"Não há o que enviar à {nome}."]
    total = sum((Decimal(l["diferenca_brl"]) for l in linhas), ZERO)
    estornos = [l for l in linhas if l["tipo_lancamento"] == TIPO_ESTORNO]
    por_cnpj: dict[str, list[dict]] = defaultdict(list)
    for l in linhas:
        por_cnpj[l["cnpj"]].append(l)

    texto += ["Prezados,", "",
              f"Na conferência da competência {comp}, identificamos {len(linhas)} transações de {len(por_cnpj)} lojistas "
              f"em que a taxa aplicada pela {nome} é diferente da taxa contratada. A diferença total, tomada sobre o valor "
              f"bruto de cada transação, é de {_rs(total)}. As transações estão no anexo orbe_operacoes.csv.", ""]
    resumo = []
    for cnpj, ls in sorted(por_cnpj.items(), key=lambda kv: (-sum(Decimal(l["diferenca_brl"]) for l in kv[1]), kv[0])):
        resumo.append([ls[0]["lojista"], cnpj, len(ls), _faixa_pct(Decimal(l["taxa_contratada_pct"]) for l in ls),
                       _faixa_pct(Decimal(l["taxa_aplicada_pct"]) for l in ls),
                       brl(sum((Decimal(l["diferenca_brl"]) for l in ls), ZERO))])
    texto += [_tabela(["lojista", "CNPJ", "transações", "taxa contratada", "taxa aplicada", "diferença (R$)"], resumo,
                      numericas={2, 5}), ""]
    if estornos:
        texto += [f"Estornos: {len(estornos)} das linhas acima são estornos, com diferença negativa de "
                  f"{_rs(sum((Decimal(l['diferenca_brl']) for l in estornos), ZERO))}. O estorno devolve o que foi "
                  f"cobrado a maior na venda original e fica no total.", ""]

    texto += ["Condições vigentes de cada lojista:", ""]
    for cnpj, ls in sorted(por_cnpj.items(), key=lambda kv: kv[1][0]["lojista"]):
        condicoes = _condicoes_checkout(cnpj, (l["_data_ref"] for l in ls), contratos, cfg_ck)
        texto.append(f"- {ls[0]['lojista']} (CNPJ {cnpj}):")
        texto += [f"  - {c.texto()}." for c in condicoes]
        texto.append(f"  - {_aviso(cnpj, condicoes, nome, cfg)}")
    texto += ["", "Solicitamos a correção da parametrização das taxas dos lojistas acima, conforme as condições "
                  "vigentes, e a informação sobre a regularização dos valores cobrados a maior, que reduziram o "
                  "repasse aos lojistas.", "", "Atenciosamente,", "[assinatura da Helena]"]
    return texto


# ---------------------------------------------------------------- Ponte

def _linhas_ponte(itens, entradas, contratos) -> list[dict]:
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
        l |= {"taxa_contratada_pct": _p4(i.campos["taxa_contratada_pct"]), "taxa_aplicada_pct": _p4(i.campos["taxa_aplicada_pct"])}
        linhas.append(l)
    for i in _por_prefixo(itens, "PEN-NEG-REM-"):
        l = base(i, NEGATIVO, i.campos["ref_origem"])
        contratado, _ = contratos.spread_contratado(l["cnpj"], l["_op"]["data_contratacao"])
        l |= {"taxa_contratada_pct": _p4(contratado), "taxa_aplicada_pct": _p4(l["_op"]["spread_pct"])}
        linhas.append(l)
    for i in _por_prefixo(itens, "PEN-DUP-REM-"):
        l = base(i, DUPLICADA, i.campos["ref_origem"])
        l |= {"taxa_contratada_pct": "", "taxa_aplicada_pct": ""}
        linhas.append(l)
    ordem = {ACIMA: 0, NEGATIVO: 1, DUPLICADA: 2}
    return sorted(linhas, key=lambda l: (ordem[l["natureza"]], l["lojista"], l["data_contratacao"], l["ref_origem"]))


def _soma(linhas: list[dict]) -> Decimal:
    return sum((Decimal(l["valor_brl"]) for l in linhas), ZERO)


def _md_ponte(linhas: list[dict], entradas, contratos, cfg) -> list[str]:
    nome, comp = cfg.nomes["ponte"], entradas.competencia
    texto = [cfg.cabecalho, "", f"Para: {cfg.destinatarios['ponte']}",
             f"Assunto: Contestação do relatório de operações - competência {comp}", ""]
    if not linhas:
        return texto + [f"Nenhuma operação da competência {comp} a contestar. Não há o que enviar à {nome}."]
    acima = [l for l in linhas if l["natureza"] == ACIMA]
    neg = [l for l in linhas if l["natureza"] == NEGATIVO]
    dup = [l for l in linhas if l["natureza"] == DUPLICADA]
    texto += ["Prezados,", "",
              f"Na conferência do relatório de operações da competência {comp}, a Tarvo identificou {len(linhas)} "
              f"operações a contestar, em três grupos. As operações estão no anexo ponte_operacoes.csv "
              f"(coluna natureza).", ""]

    n = 1
    if acima:
        total = _soma(acima)
        texto += [f"{n}. Spread aplicado acima do contratado: {len(acima)} operações, {_rs(total)}", ""]
        n += 1
        por_cnpj: dict[str, list[dict]] = defaultdict(list)
        for l in acima:
            por_cnpj[l["cnpj"]].append(l)
        for cnpj, ls in sorted(por_cnpj.items(), key=lambda kv: kv[1][0]["lojista"]):
            datas = [l["_op"]["data_contratacao"] for l in ls]
            linhas_planilha = {contratos.vigente(cnpj, d)["ref_origem"]: contratos.vigente(cnpj, d) for d in datas}
            condicoes = []
            for ref, row in linhas_planilha.items():
                d = f"contrato da planilha de taxas ({ref}), spread contratado de {_pct_br(Decimal(ls[0]['taxa_contratada_pct']))}"
                if row["obs"]:
                    d += f", observação: {row['obs']}"
                condicoes.append(Condicao(d, row["vigencia_inicio"], row["vigencia_fim"]))
            texto += [f"- {ls[0]['lojista']} (CNPJ {cnpj}): {len(ls)} operações contratadas de {_faixa_datas(datas)}, "
                      f"spread contratado {_faixa_pct(Decimal(l['taxa_contratada_pct']) for l in ls)}, "
                      f"spread aplicado {_faixa_pct(Decimal(l['taxa_aplicada_pct']) for l in ls)}, "
                      f"{_rs(_soma(ls))} pagos a maior pelo lojista."]
            texto += [f"  - Condição: {c.texto()}." for c in condicoes]
            texto.append(f"  - {_aviso(cnpj, condicoes, nome, cfg)}")
        texto.append("")
    if neg:
        obs = sorted({l["_op"]["observacao"] for l in neg if l["_op"]["observacao"]})
        motivo = f" Observação do relatório: {'; '.join(obs)}." if obs else ""
        texto += [f"{n}. Spread negativo: {len(neg)} operações, {_rs(_soma(neg))}", "",
                  f"Operações com spread negativo, que a Tarvo não considera na sua participação.{motivo} O valor é a "
                  f"diferença entre o spread aplicado e o contratado, sobre a PTAX de referência.", ""]
        n += 1
        texto += [_tabela(["operação", "lojista", "contratação", "contratado", "aplicado", "valor (R$)"],
                          [[l["ref_origem"], l["lojista"], l["data_contratacao"], _pct_br(Decimal(l["taxa_contratada_pct"])),
                            _pct_br(Decimal(l["taxa_aplicada_pct"])), brl(Decimal(l["valor_brl"]))] for l in neg],
                          numericas={5}), ""]
    if dup:
        texto += [f"{n}. Operação repetida no relatório: {len(dup)} operação, {_rs(_soma(dup))}", ""]
        for l in dup:
            copias = entradas.ponte[entradas.ponte["ref_origem"] == l["ref_origem"]]
            onde = " e ".join(str(x) for x in sorted(copias["linha_planilha"]))
            texto.append(f"- {l['ref_origem']} ({l['lojista']}, contratada em {l['data_contratacao']}) aparece "
                         f"{len(copias)} vezes no relatório (linhas {onde}). O Nº Operação é único: a Tarvo conta a "
                         f"operação uma vez, e a cópia, de R$ {brl(Decimal(l['valor_brl']))} de spread, é cobrança em "
                         f"dobro. Solicitamos a correção do relatório.")
        texto.append("")
    texto += ["Solicitamos a revisão das operações acima e, quando houver ajuste, o envio no relatório do mês "
              "seguinte, como crédito ou débito.", "", "Atenciosamente,", "[assinatura da Helena]"]
    return texto


# ---------------------------------------------------------------- entrada do módulo

def gerar_contestacoes(itens: Iterable[ItemSaida], entradas: Entradas, pasta, cfg: ConfigContestacao | None = None,
                       cfg_checkout=None, cfg_remessa=None) -> dict[str, Path]:
    """Grava orbe.md, orbe_operacoes.csv, ponte.md e ponte_operacoes.csv em pasta. Devolve nome -> caminho."""
    itens = list(itens)
    cfg = cfg or carregar_config()
    cfg_checkout = cfg_checkout or mod_checkout.carregar_config()
    cfg_remessa = cfg_remessa or mod_remessa.carregar_config()
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)

    ck = mod_checkout.Contratos(entradas.taxas, cfg_checkout)
    rm = mod_remessa.Contratos(entradas.taxas, cfg_remessa)
    orbe, ponte = _linhas_orbe(itens, entradas, ck), _linhas_ponte(itens, entradas, rm)
    md_orbe = _md_orbe(orbe, entradas, ck, cfg, cfg_checkout)
    md_ponte = _md_ponte(ponte, entradas, rm, cfg)

    gravados = {}
    for (md, csv_nome), colunas, linhas, texto in ((ARQUIVO_ORBE, COLUNAS_ORBE, orbe, md_orbe),
                                                  (ARQUIVO_PONTE, COLUNAS_PONTE, ponte, md_ponte)):
        _csv(pasta / csv_nome, colunas, linhas)
        _texto(pasta / md, texto)
        gravados[md], gravados[csv_nome] = pasta / md, pasta / csv_nome
    return gravados
