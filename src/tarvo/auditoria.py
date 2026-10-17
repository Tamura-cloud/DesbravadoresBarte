"""Registro de execução do fechar (O06): o que entrou, o que saiu e com que código, para refazer qualquer número.

A cada fechamento que passa na validação, grava execucao.json e execucao.md da ÚLTIMA execução numa pasta irmã de
saida/ (config/auditoria.yaml; saida/ continua com os 6 CSVs). Os dois são preparados na pasta temporária do
fechar e publicados junto com a saída: se a validação falha, nada muda. Só descreve a execução: não recalcula
nenhuma regra. As contagens e os totais são lidos dos CSVs já gravados (soma em Decimal).
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

import yaml

from tarvo.saida import ARQUIVOS, ENCODING, SEPARADOR

if TYPE_CHECKING:
    from tarvo import dependencias as dep
    from tarvo.fechamento import Entradas

RAIZ = Path(__file__).resolve().parents[2]
CONFIG_AUDITORIA = RAIZ / "config" / "auditoria.yaml"
ARQUIVO_JSON, ARQUIVO_MD = "execucao.json", "execucao.md"
SEM_COMMIT = "indisponível"
COMPLETO, PARCIAL = "COMPLETO", "PARCIAL"
CODIGO = {COMPLETO: 0, PARCIAL: 3}  # códigos de saída do fechar (R44, src/tarvo/cli.py)

# O que "linhas lidas" conta em cada tipo de entrada.
UNIDADE = {
    "orbe": "linhas de dados convertidas (repetidas e corrigidas incluídas)",
    "taxas": "linhas da aba \"Taxas vigentes\"",
    "ponte_eml": "operações da aba \"Operações\" do anexo",
    "plano_de_contas": "contas",
    "aurora": "lançamentos",
    "meridiano": "transações (STMTTRN)",
}


@dataclass(frozen=True)
class ConfigAuditoria:
    pasta: str


def carregar_config(caminho=CONFIG_AUDITORIA) -> ConfigAuditoria:
    with open(caminho, encoding="utf-8") as f:
        bruto = yaml.safe_load(f)
    pasta = bruto.get("pasta")
    if not isinstance(pasta, str) or not pasta.strip():
        raise ValueError(f"config/auditoria.yaml: pasta deveria ser texto, veio {pasta!r}")
    return ConfigAuditoria(pasta)


def pasta_padrao(saida, cfg: ConfigAuditoria) -> Path:
    """Pasta irmã da pasta de saída."""
    return Path(saida).resolve().parent / cfg.pasta


# ---------------------------------------------------------------- caminhos relativos

FORA_DO_REPOSITORIO = "<fora do repositório>"


def caminho_relativo(caminho) -> str:
    """Caminho relativo à raiz do repositório, com "/" (o registro é público e a banca roda em outra máquina).
    Fora do repositório, só o nome da pasta: nenhum caminho absoluto nem nome de usuário."""
    p = Path(caminho).resolve()
    try:
        return p.relative_to(RAIZ).as_posix()
    except ValueError:
        return f"{FORA_DO_REPOSITORIO}/{p.name}"


def sem_caminho_absoluto(valor):
    """Troca, em todo texto do registro, a raiz do repositório por "." e a pasta do usuário por "~" (mensagens de
    erro dos leitores podem citar caminhos)."""
    if isinstance(valor, str):
        for base, troca in ((RAIZ, "."), (Path.home(), "~")):
            for forma in {str(base), base.as_posix()}:
                valor = valor.replace(forma, troca)
        return valor
    if isinstance(valor, list):
        return [sem_caminho_absoluto(v) for v in valor]
    if isinstance(valor, dict):
        return {k: sem_caminho_absoluto(v) for k, v in valor.items()}
    return valor


# ---------------------------------------------------------------- versão do código

def _git(*args: str) -> str | None:
    try:
        r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def versao_do_codigo() -> dict:
    """Commit (git rev-parse --short HEAD) e se src/ ou config/ têm alteração não commitada; sem git, indisponível."""
    commit = _git("rev-parse", "--short", "HEAD")
    if not commit:
        return {"commit": SEM_COMMIT, "branch": None, "alteracoes_locais_em_src_config": None}
    alteracoes = _git("status", "--porcelain", "--", "src", "config")
    return {"commit": commit, "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "alteracoes_locais_em_src_config": bool(alteracoes) if alteracoes is not None else None}


# ---------------------------------------------------------------- entradas

def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 16), b""):
            h.update(bloco)
    return h.hexdigest()


def _linhas_lidas(tipo: str, nome: str, entradas: Entradas) -> int | None:
    if tipo == "orbe":
        return entradas.orbe_linhas_lidas.get(nome)
    quadro = {"taxas": entradas.taxas, "ponte_eml": entradas.ponte, "plano_de_contas": entradas.plano_contas,
              "aurora": entradas.aurora, "meridiano": entradas.meridiano}[tipo]
    return None if quadro is None else len(quadro)


def _rejeitadas(tipo: str, nome: str, entradas: Entradas) -> int:
    return sum(1 for r in entradas.rejeitadas.get(tipo, ()) if r.arquivo.split("#")[0] == nome)


def _bloqueio_do_arquivo(tipo: str, nome: str, bloqueios: Iterable[dep.Bloqueio]) -> dep.Bloqueio | None:
    """O bloqueio da fonte inteira ou, na Orbe, o do próprio arquivo de ajustes (R44)."""
    bloqueios = [b for b in bloqueios if b.fonte == tipo]
    return (next((b for b in bloqueios if not b.parcial), None)
            or next((b for b in bloqueios if b.arquivo == nome), None))


def _entrada(caminho: Path, tipo: str, entradas: Entradas) -> dict:
    nome = caminho.name
    bloqueio = _bloqueio_do_arquivo(tipo, nome, entradas.bloqueios)
    lidas = None if bloqueio is not None else _linhas_lidas(tipo, nome, entradas)
    return {
        "nome": nome, "tipo": tipo, "tamanho_bytes": caminho.stat().st_size, "sha256": sha256(caminho),
        "situacao": "lido" if bloqueio is None else f"bloqueado ({bloqueio.natureza.lower()})",
        "linhas_lidas": lidas, "o_que_conta": UNIDADE.get(tipo, "linhas"),
        "linhas_rejeitadas": _rejeitadas(tipo, nome, entradas),
    }


def _arquivos_de_entrada(pasta: Path, entradas: Entradas) -> list[dict]:
    """Cada arquivo de um tipo: os localizados e os candidatos de uma fonte ambígua (que não foram lidos)."""
    por_nome: dict[str, str] = {}
    for tipo, achado in entradas.arquivos.items():
        for p in achado if isinstance(achado, tuple) else (achado,):
            por_nome[p.name] = tipo
    for b in entradas.bloqueios:
        if b.natureza == "AMBIGUA":
            for nome, _ in b.origens:
                por_nome.setdefault(nome, b.fonte)
    return [_entrada(pasta / nome, tipo, entradas) for nome, tipo in sorted(por_nome.items())
            if (pasta / nome).is_file()]


# ---------------------------------------------------------------- saída

def _ler_csv(caminho: Path) -> list[dict[str, str]]:
    with open(caminho, encoding=ENCODING, newline="") as f:
        return list(csv.DictReader(f, delimiter=SEPARADOR))


def resumo_saida(pasta: Path) -> list[dict]:
    """Linhas e total (soma da coluna de valor, em Decimal) de cada um dos 6 CSVs."""
    resultado = []
    for espec in ARQUIVOS:
        caminho = pasta / espec.nome
        linhas = _ler_csv(caminho)
        total = sum((Decimal(l[espec.coluna_valor]) for l in linhas), Decimal("0.00"))
        resultado.append({"arquivo": espec.nome, "linhas": len(linhas), "coluna_total": espec.coluna_valor,
                          "total": format(total, "f"), "sha256": sha256(caminho)})
    return resultado


def resumo_rascunhos(rascunhos: dict[str, Path]) -> list[dict]:
    resultado = []
    for nome, caminho in sorted(rascunhos.items()):
        with open(caminho, encoding="utf-8", newline="") as f:
            linhas = sum(1 for _ in f)
        resultado.append({"arquivo": nome, "linhas": linhas, "sha256": sha256(caminho)})
    return resultado


# ---------------------------------------------------------------- registro

def registro(entradas: Entradas, entrada: Path, saida: Path, comando: str,
             saida_preparada: Path, rascunhos: dict[str, Path], destino_rascunhos: Path | None,
             ignorados: list[tuple[Path, str]], completo: bool, regras: Iterable[str],
             momento: datetime | None = None) -> dict:
    """Tudo o que a execução usou e gerou. saida_preparada e rascunhos: os arquivos já validados, antes de publicar."""
    status = COMPLETO if completo else PARCIAL
    return sem_caminho_absoluto({
        "data_hora": (momento or datetime.now().astimezone()).isoformat(timespec="seconds"),
        "codigo": versao_do_codigo(),
        "competencia": entradas.competencia,
        "comando": comando,
        "pasta_entrada": caminho_relativo(entrada),
        "pasta_saida": caminho_relativo(saida),
        "pasta_contestacoes": caminho_relativo(destino_rascunhos) if destino_rascunhos else None,
        "status": status,
        "codigo_saida": CODIGO[status],
        "arquivos_entrada": _arquivos_de_entrada(Path(entrada), entradas),
        "arquivos_ignorados": [{"nome": p.name, "motivo": motivo} for p, motivo in ignorados],
        "fontes_bloqueadas": [{"fonte": b.fonte, "natureza": b.natureza.lower(), "arquivo": b.arquivo,
                               "erro": b.erro, "proximo_passo": b.passo} for b in entradas.bloqueios],
        "itens_fora_por_erro_de_dado": list(regras),
        "saida": resumo_saida(saida_preparada),
        "contestacoes": resumo_rascunhos(rascunhos),
    })


def _md_celula(v) -> str:
    return "—" if v is None or v == "" else str(v).replace("|", "\\|").replace("\n", " ")


def _md_tabela(cabecalho: list[str], linhas: list[list]) -> list[str]:
    return ["| " + " | ".join(cabecalho) + " |", "|" + "---|" * len(cabecalho)] + [
        "| " + " | ".join(_md_celula(c) for c in l) + " |" for l in linhas]


def markdown(r: dict) -> str:
    codigo = r["codigo"]
    alteracoes = codigo["alteracoes_locais_em_src_config"]
    versao = codigo["commit"] + (f" ({codigo['branch']})" if codigo["branch"] else "") + (
        " - com alterações não commitadas em src/ ou config/" if alteracoes else "")
    texto = [
        f"# Registro de execução — competência {r['competencia']}", "",
        "Última execução do `fechar`. Gerado pelo próprio fechamento (src/tarvo/auditoria.py); a versão completa está "
        f"em `{ARQUIVO_JSON}`, ao lado.", "",
        *_md_tabela(["campo", "valor"], [
            ["data e hora", r["data_hora"]],
            ["commit do código", versao],
            ["competência", r["competencia"]],
            ["comando", f"`{r['comando']}`"],
            ["pasta de entrada", r["pasta_entrada"]],
            ["pasta de saída", r["pasta_saida"]],
            ["pasta dos rascunhos de contestação", r["pasta_contestacoes"] or "não gravados"],
            ["status", f"**{r['status']}**"],
            ["código de saída", r["codigo_saida"]],
        ]), "",
        "## Arquivos de entrada", "",
        *_md_tabela(["arquivo", "tipo", "tamanho (bytes)", "SHA-256", "situação", "linhas lidas", "o que conta",
                     "linhas rejeitadas"],
                    [[a["nome"], a["tipo"], a["tamanho_bytes"], f"`{a['sha256']}`", a["situacao"], a["linhas_lidas"],
                      a["o_que_conta"], a["linhas_rejeitadas"]] for a in r["arquivos_entrada"]]), "",
        "## Arquivos ignorados", "",
    ]
    texto += (_md_tabela(["arquivo", "por quê"], [[a["nome"], a["motivo"]] for a in r["arquivos_ignorados"]])
              if r["arquivos_ignorados"] else ["Nenhum."])
    texto += ["", "## Fontes bloqueadas", ""]
    texto += (_md_tabela(["fonte", "natureza", "arquivo", "erro", "próximo passo"],
                         [[b["fonte"], b["natureza"], b["arquivo"] or "a fonte inteira", b["erro"], b["proximo_passo"]]
                          for b in r["fontes_bloqueadas"]])
              if r["fontes_bloqueadas"] else ["Nenhuma."])
    if r["itens_fora_por_erro_de_dado"]:
        texto += ["", "Itens fora por erro de dado (PEN-REGRA, R44): " + ", ".join(r["itens_fora_por_erro_de_dado"])]
    texto += ["", "## Saída (pasta de saída)", "",
              *_md_tabela(["arquivo", "linhas", "total", "coluna somada", "SHA-256"],
                          [[s["arquivo"], s["linhas"], s["total"], s["coluna_total"], f"`{s['sha256']}`"]
                           for s in r["saida"]]),
              "", "## Rascunhos de contestação", ""]
    texto += (_md_tabela(["arquivo", "linhas", "SHA-256"],
                         [[c["arquivo"], c["linhas"], f"`{c['sha256']}`"] for c in r["contestacoes"]])
              if r["contestacoes"] else ["Não gravados nesta execução."])
    texto += ["", "## Como refazer qualquer número", "",
              "1. Confira o SHA-256 de cada arquivo de entrada (`certutil -hashfile <arquivo> SHA256` no Windows, "
              "`sha256sum <arquivo>` no Linux): igual ao da tabela, é o mesmo arquivo.",
              f"2. Faça checkout do commit `{codigo['commit']}` e rode o comando acima.",
              "3. Cada número da saída tem as linhas de origem no rastro.csv (id_saida; arquivo_origem; ref_origem; "
              "valor; regra; detalhe): a soma de valor por id_saida é o número reportado, e a regra e o detalhe dizem "
              "a taxa, a isenção ou a venda original usada em cada linha (HIPOTESES.md).", ""]
    return "\n".join(texto)


def gravar(r: dict, pasta: Path) -> dict[str, Path]:
    """Grava execucao.json e execucao.md em pasta (a pasta temporária do fechar; quem publica é o fechar)."""
    pasta.mkdir(parents=True, exist_ok=True)
    caminhos = {ARQUIVO_JSON: pasta / ARQUIVO_JSON, ARQUIVO_MD: pasta / ARQUIVO_MD}
    with open(caminhos[ARQUIVO_JSON], "w", encoding="utf-8", newline="\n") as f:
        json.dump(r, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(caminhos[ARQUIVO_MD], "w", encoding="utf-8", newline="\n") as f:
        f.write(markdown(r))
    return caminhos
