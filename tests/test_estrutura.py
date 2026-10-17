import os
import subprocess
import sys
from pathlib import Path

from tarvo.cli import CONFIG_PADRAO, carregar_padroes, localizar_arquivos

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "dados" / "2026-09"


def test_localiza_os_6_arquivos_por_padrao():
    padroes = carregar_padroes(CONFIG_PADRAO)
    encontrados = localizar_arquivos(ENTRADA, padroes)

    assert set(encontrados) == {"orbe", "taxas", "ponte_eml", "plano_de_contas", "aurora", "meridiano"}
    assert len(set(encontrados.values())) == 6
    assert all(p.is_file() for p in encontrados.values())


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
    "remessa.MOTIVO_TED": "conferir se o TED",
    "checkout.MOTIVO_SEM_CONTRATO": "não faturar até o comercial confirmar",
    "checkout.MOTIVO_RETROATIVO": "quando o Comercial confirmar",
    "bancos.MOTIVO_DEVOLUCAO": "apurar o motivo",
    "bancos.MOTIVO_SEM_REGRA": "classificar manualmente",
    "bancos.MOTIVO_IA": "Uma pessoa revisa antes de lançar",
    "bancos.MOTIVO_TRANSITO": "conferir no extrato de",
}
PREFIXOS_DE_MOTIVO = {"checkout.MOTIVO_IDENTIFICACAO"}  # vai na frente de outro motivo, não é motivo sozinho


def test_todo_modelo_de_motivo_de_pendencia_tem_proximo_passo():
    from tarvo import bancos, checkout, remessa

    vistos = set()
    for modulo in (remessa, checkout, bancos):
        for nome, texto in vars(modulo).items():
            chave = f"{modulo.__name__.rsplit('.', 1)[1]}.{nome}"
            if not nome.startswith("MOTIVO_") or not isinstance(texto, str) or chave in PREFIXOS_DE_MOTIVO:
                continue
            vistos.add(chave)
            assert ACAO_JA_ESCRITA.get(chave, "próximo passo:") in texto, chave
    assert set(ACAO_JA_ESCRITA) <= vistos
