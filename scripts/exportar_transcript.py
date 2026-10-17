"""Copia transcripts do Claude Code para PROMPTS/sessoes/, sem dados pessoais.

A instrução do case pede o histórico de todas as sessões de IA, sem edição,
removendo só chaves de API e dados pessoais. Para cada sessão gera:
  - <nome>.jsonl: o transcript original, só com e-mails pessoais e chaves trocados;
  - <nome>.md: uma visão legível (pedidos, respostas e ferramentas usadas).

Uso (cada pessoa, no fim do dia, na própria máquina):
  python scripts/exportar_transcript.py --autor "Pessoa A"
  python scripts/exportar_transcript.py --autor "Pessoa A" --redigir fulano@empresa.com
Por padrão lê ~/.claude/projects/<pasta-do-projeto>/*.jsonl.
"""
import argparse
import json
import re
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DOMINIOS_PESSOAIS = r"gmail|hotmail|outlook|live|yahoo|icloud|uol|bol|terra"
SEGREDOS = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]{10,}"),
    re.compile(r"gh[opsu]_[A-Za-z0-9]{20,}"),
    re.compile(rf"[\w.+-]+@(?:{DOMINIOS_PESSOAIS})\.[a-z.]+", re.I),
]
LEMBRETE = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)


def pasta_padrao() -> Path:
    nome = re.sub(r"[^A-Za-z0-9]", "-", str(RAIZ))
    return Path.home() / ".claude" / "projects" / nome


def redigir(texto: str, extras: list[str]) -> str:
    for padrao in SEGREDOS:
        texto = padrao.sub("[REMOVIDO]", texto)
    for valor in extras:
        texto = texto.replace(valor, "[REMOVIDO]")
    return texto


def _hora(ts: str | None) -> str:
    if not ts:
        return ""
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%d/%m %H:%M")


def _resumo_ferramenta(bloco: dict) -> str:
    entrada = bloco.get("input") or {}
    detalhe = entrada.get("description") or entrada.get("file_path") or entrada.get("pattern") or ""
    return f"- `{bloco.get('name')}` {detalhe}".rstrip()


def legivel(linhas: list[dict], autor: str, sessao: str) -> str:
    saida = [f"# Sessão Claude Code `{sessao}`", "", f"Autor: {autor}. Visão legível gerada do `.jsonl` "
             "(o arquivo original completo está ao lado). Resultados de ferramentas e raciocínio interno "
             "ficam só no `.jsonl`.", ""]
    for o in linhas:
        msg = o.get("message")
        if not isinstance(msg, dict) or o.get("type") not in ("user", "assistant"):
            continue
        conteudo = msg["content"]
        blocos = [{"type": "text", "text": conteudo}] if isinstance(conteudo, str) else conteudo
        textos = [LEMBRETE.sub("", b["text"]).strip() for b in blocos if b.get("type") == "text"]
        textos = [t for t in textos if t]
        ferramentas = [_resumo_ferramenta(b) for b in blocos if b.get("type") == "tool_use"]
        imagens = sum(1 for b in blocos if b.get("type") == "image")
        if o["type"] == "user" and (textos or imagens):
            saida += [f"## Pedido — {_hora(o.get('timestamp'))}", "", *textos]
            saida += ["", f"*({imagens} imagem anexada)*"] if imagens else []
            saida.append("")
        elif o["type"] == "assistant" and (textos or ferramentas):
            saida += [*(f"**IA:** {t}" for t in textos), *ferramentas, ""]
    return "\n".join(saida)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--autor", required=True)
    p.add_argument("--origem", type=Path, default=pasta_padrao())
    p.add_argument("--destino", type=Path, default=RAIZ / "PROMPTS" / "sessoes")
    p.add_argument("--redigir", action="append", default=[], help="texto extra a remover (repetível)")
    a = p.parse_args()
    a.destino.mkdir(parents=True, exist_ok=True)
    for arquivo in sorted(a.origem.glob("*.jsonl")):
        bruto = redigir(arquivo.read_text(encoding="utf-8"), a.redigir)
        linhas = [json.loads(l) for l in bruto.splitlines() if l.strip()]
        inicio = next((o["timestamp"] for o in linhas if o.get("timestamp")), "")
        dia = datetime.fromisoformat(inicio.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d") if inicio else "sem-data"
        nome = f"{dia}_{a.autor.lower().replace(' ', '-')}_{arquivo.stem[:8]}"
        (a.destino / f"{nome}.jsonl").write_text(bruto, encoding="utf-8")
        (a.destino / f"{nome}.md").write_text(legivel(linhas, a.autor, arquivo.stem), encoding="utf-8")
        print(f"{arquivo.name} -> PROMPTS/sessoes/{nome}.(jsonl|md)")


if __name__ == "__main__":
    main()
