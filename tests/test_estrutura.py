import os
import subprocess
import sys
from pathlib import Path

from tarvo.cli import CONFIG_PADRAO, carregar_multiplos, localizar_pela_config

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "dados" / "2026-09"


def test_localiza_os_6_tipos_por_padrao():
    encontrados = localizar_pela_config(ENTRADA)

    assert set(encontrados) == {"orbe", "taxas", "ponte_eml", "plano_de_contas", "aurora", "meridiano"}
    # O05: a Orbe aceita vários arquivos (relatório e ajustes tardios), em ordem de nome; os outros tipos, um só
    assert carregar_multiplos(CONFIG_PADRAO) == {"orbe"}
    orbe = encontrados.pop("orbe")
    assert isinstance(orbe, tuple) and len(orbe) >= 1 and list(orbe) == sorted(orbe, key=lambda p: p.name)
    assert all(isinstance(p, Path) and p.is_file() for p in [*orbe, *encontrados.values()])
    assert len({*orbe, *encontrados.values()}) == len(orbe) + 5


def test_cli_fechar_lista_os_6_arquivos(tmp_path):
    env = {**os.environ, "PYTHONPATH": str(RAIZ / "src"), "PYTHONIOENCODING": "utf-8"}
    resultado = subprocess.run(
        [sys.executable, "-m", "tarvo", "fechar",
         "--competencia", "2026-09", "--entrada", str(ENTRADA), "--saida", str(tmp_path)],
        capture_output=True, text=True, encoding="utf-8", env=env, cwd=RAIZ,
    )

    assert resultado.returncode == 0, resultado.stderr
    assert "Arquivos encontrados (6)" in resultado.stdout
    # os 6 CSVs ficam direto em --saida, sem subpasta da competência
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(
        ["comissoes_por_lojista.csv", "divergencias_taxa.csv", "notas_a_emitir.csv",
         "lancamentos_classificados.csv", "pendencias.csv", "rastro.csv"])


# O04: pendência de acompanhamento precisa de motivo e próximo passo. Estes modelos já traziam a ação antes
# (verbo no imperativo; quem faz está em quem_decide) e ficam como estão; todo outro motivo diz "próximo passo:".
ACAO_JA_ESCRITA = {
    "remessa.MOTIVO_DUPLICATA": "pedir correção do relatório",
    "remessa.MOTIVO_CONTESTACAO": "a Tarvo contesta com a Ponte",
    "remessa.MOTIVO_AJUSTE_SEM_ORIGINAL": "conferir com a Ponte",
    "remessa.MOTIVO_TED": "conferir o TED",
    "checkout.MOTIVO_SEM_CONTRATO": "não faturar até o comercial confirmar",
    "checkout.MOTIVO_RETROATIVO": "quando o Comercial confirmar",
    "bancos.MOTIVO_DEVOLUCAO": "apurar o motivo",
    "bancos.MOTIVO_SEM_REGRA": "classificar manualmente",
    "bancos.MOTIVO_IA": "Uma pessoa revisa antes de lançar",
    "bancos.MOTIVO_TRANSITO": "conferir no extrato de",
}
PREFIXOS_DE_MOTIVO = {"checkout.MOTIVO_IDENTIFICACAO"}  # vai na frente de outro motivo, não é motivo sozinho


def test_todo_modelo_de_motivo_de_pendencia_tem_proximo_passo():
    from tarvo import bancos, checkout, dependencias, remessa

    vistos = set()
    for modulo in (remessa, checkout, bancos, dependencias):
        for nome, texto in vars(modulo).items():
            chave = f"{modulo.__name__.rsplit('.', 1)[1]}.{nome}"
            if not nome.startswith("MOTIVO_") or not isinstance(texto, str) or chave in PREFIXOS_DE_MOTIVO:
                continue
            vistos.add(chave)
            assert ACAO_JA_ESCRITA.get(chave, "próximo passo:") in texto, chave
    assert set(ACAO_JA_ESCRITA) <= vistos


def test_toda_premissa_ativa_diz_o_que_muda_para_a_helena():
    """A banca pediu premissas escritas pelo que muda para a Helena se estiverem erradas, não pela contagem."""
    import re

    texto = (RAIZ / "HIPOTESES.md").read_text(encoding="utf-8")
    secao = texto.split("### 2.1 Premissas definidas pelo time", 1)[1].split("### 2.2", 1)[0]
    blocos = re.split(r"\n(?=- \*\*P\d\d)", secao)[1:]
    ativas = [b for b in blocos if not re.search(r"substitu[ií]da por", b.split("\n", 1)[0], re.IGNORECASE)]
    assert len(ativas) >= 20  # P01 a P26, menos as substituídas (P02, P15, P21)
    for bloco in ativas:
        pid = re.match(r"- \*\*(P\d\d)", bloco).group(1)
        linha = re.search(r"^ +- \*\*Se estiver errada, para a Helena:\*\* (.+)$", bloco, re.MULTILINE)
        assert linha, f"{pid} sem a linha 'Se estiver errada, para a Helena'"
        assert "R$" in linha.group(1), f"{pid}: a consequência não traz valor em reais"
        assert not re.search(r"\blinhas?\b|contagem", linha.group(1), re.IGNORECASE), f"{pid}: fala em contagem de linhas"
