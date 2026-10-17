"""Copia transcripts do Claude Code e do Antigravity para PROMPTS/sessoes/, sem dados pessoais.

A instrução do case pede o histórico de todas as sessões de IA, sem edição,
removendo só chaves de API e dados pessoais. Para cada sessão gera:
  - <nome>.jsonl: o transcript original, só com e-mails pessoais e chaves trocados;
  - <nome>.md: uma visão legível (pedidos, respostas e ferramentas usadas).

Uso (cada pessoa, na própria máquina):
  python scripts/exportar_transcript.py --autor "pessoa-a"
  python scripts/exportar_transcript.py --autor "pessoa-a" --antigravity
  python scripts/exportar_transcript.py --autor "pessoa-a" --redigir fulano@empresa.com
Claude Code: lê ~/.claude/projects/<pasta-do-projeto>/*.jsonl.
Antigravity: lê ~/.gemini/antigravity/brain/*/.system_generated/logs/transcript_full.jsonl.
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
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"gh[opsu]_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
    re.compile(rf"[\w.+-]{{1,64}}@(?:{DOMINIOS_PESSOAIS})\.[a-z.]{{2,10}}", re.I),
]
LEMBRETE = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
PEDIDO_AG = re.compile(r"</?USER_REQUEST>")


def pasta_claude() -> Path:
    nome = re.sub(r"[^A-Za-z0-9]", "-", str(RAIZ))
    return Path.home() / ".claude" / "projects" / nome


def arquivos(origem: Path | None, antigravity: bool) -> list[Path]:
    if antigravity:
        base = origem or Path.home() / ".gemini" / "antigravity" / "brain"
        return sorted(base.glob("*/.system_generated/logs/transcript_full.jsonl"))
    return sorted((origem or pasta_claude()).glob("*.jsonl"))


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


def _resumo_ferramenta(nome: str, entrada) -> str:
    entrada = entrada if isinstance(entrada, dict) else {}
    detalhe = (entrada.get("description") or entrada.get("file_path") or entrada.get("pattern")
               or entrada.get("CommandLine") or entrada.get("AbsolutePath") or "")
    return f"- `{nome}` {str(detalhe)[:160]}".rstrip()


def _cabecalho(ferramenta: str, autor: str, sessao: str) -> list[str]:
    return [f"# Sessão {ferramenta} `{sessao}`", "", f"Autor: {autor}. Visão legível gerada do `.jsonl` "
            "(o arquivo original completo está ao lado). Resultados de ferramentas e raciocínio interno "
            "ficam só no `.jsonl`.", ""]


def legivel_claude(linhas: list[dict], autor: str, sessao: str) -> str:
    saida = _cabecalho("Claude Code", autor, sessao)
    for o in linhas:
        msg = o.get("message")
        if not isinstance(msg, dict) or o.get("type") not in ("user", "assistant"):
            continue
        conteudo = msg["content"]
        blocos = [{"type": "text", "text": conteudo}] if isinstance(conteudo, str) else conteudo
        textos = [LEMBRETE.sub("", b["text"]).strip() for b in blocos if b.get("type") == "text"]
        textos = [t for t in textos if t]
        ferramentas = [_resumo_ferramenta(b.get("name"), b.get("input")) for b in blocos if b.get("type") == "tool_use"]
        imagens = sum(1 for b in blocos if b.get("type") == "image")
        if o["type"] == "user" and (textos or imagens):
            saida += [f"## Pedido — {_hora(o.get('timestamp'))}", "", *textos]
            saida += ["", f"*({imagens} imagem anexada)*"] if imagens else []
            saida.append("")
        elif o["type"] == "assistant" and (textos or ferramentas):
            saida += [*(f"**IA:** {t}" for t in textos), *ferramentas, ""]
    return "\n".join(saida)


def legivel_antigravity(linhas: list[dict], autor: str, sessao: str) -> str:
    saida = _cabecalho("Antigravity", autor, sessao)
    for o in linhas:
        tipo, conteudo = o.get("type"), o.get("content")
        if tipo == "USER_INPUT" and isinstance(conteudo, str):
            saida += [f"## Pedido — {_hora(o.get('created_at'))}", "", PEDIDO_AG.sub("", conteudo).strip()]
            saida += ["", "*(anexo)*"] if o.get("media") else []
            saida.append("")
        elif tipo == "PLANNER_RESPONSE":
            if isinstance(conteudo, str) and conteudo.strip():
                saida.append(f"**IA:** {conteudo.strip()}")
            for chamada in o.get("tool_calls") or []:
                if isinstance(chamada, dict):
                    args = chamada.get("args") or chamada.get("arguments") or chamada.get("input")
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except ValueError:
                            args = {}
                    saida.append(_resumo_ferramenta(chamada.get("name"), args))
            saida.append("")
    return "\n".join(saida)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--autor", required=True)
    p.add_argument("--antigravity", action="store_true", help="exportar sessões do Antigravity")
    p.add_argument("--origem", type=Path, default=None)
    p.add_argument("--destino", type=Path, default=RAIZ / "PROMPTS" / "sessoes")
    p.add_argument("--redigir", action="append", default=[], help="texto extra a remover (repetível)")
    a = p.parse_args()
    a.destino.mkdir(parents=True, exist_ok=True)
    for arquivo in arquivos(a.origem, a.antigravity):
        bruto = redigir(arquivo.read_text(encoding="utf-8", errors="replace"), a.redigir)
        linhas = [json.loads(l) for l in bruto.splitlines() if l.strip()]
        sessao = arquivo.parents[2].name if a.antigravity else arquivo.stem
        inicio = next((o.get("timestamp") or o.get("created_at") for o in linhas
                       if o.get("timestamp") or o.get("created_at")), "")
        dia = datetime.fromisoformat(inicio.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d") if inicio else "sem-data"
        ferramenta = "antigravity" if a.antigravity else "claude"
        nome = f"{dia}_{a.autor.lower().replace(' ', '-')}_{ferramenta}_{sessao[:8]}"
        texto = (legivel_antigravity if a.antigravity else legivel_claude)(linhas, a.autor, sessao)
        (a.destino / f"{nome}.jsonl").write_text(bruto, encoding="utf-8")
        (a.destino / f"{nome}.md").write_text(texto, encoding="utf-8")
        print(f"{arquivo.name} ({sessao[:8]}) -> PROMPTS/sessoes/{nome}.(jsonl|md)")


if __name__ == "__main__":
    main()
