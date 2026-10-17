"""Leitores das 6 fontes, como elas chegam (sem limpeza manual).

Os arquivos são achados por padrão de nome, não por nome fixo, para o
mesmo pipeline rodar em outubro. Dono: Pessoa C (camada compartilhada).
"""
from dataclasses import dataclass
from pathlib import Path

from . import aurora, meridiano, orbe, plano_contas, ponte, taxas

PADROES = {
    "orbe": "*orbe*.csv",
    "taxas": "*taxas*.xlsx",
    "ponte": "*.eml",
    "plano_contas": "*plano*contas*.csv",
    "aurora": "*aurora*.csv",
    "meridiano": "*.ofx",
}


@dataclass
class Dados:
    arquivos: dict[str, str]                       # chave -> nome do arquivo (vai no rastro)
    orbe: list[orbe.TransacaoOrbe]
    taxas: list[taxas.TaxaContratada]
    taxas_2025: dict[str, str]
    ponte: ponte.EmailPonte
    plano_contas: dict[str, plano_contas.Conta]
    aurora: aurora.ExtratoAurora
    meridiano: meridiano.ExtratoMeridiano


def localizar(entrada: Path) -> dict[str, Path]:
    achados = {}
    for chave, padrao in PADROES.items():
        candidatos = sorted(entrada.glob(padrao))
        if len(candidatos) != 1:
            raise FileNotFoundError(f"Esperava 1 arquivo '{padrao}' em {entrada}, achei {len(candidatos)}")
        achados[chave] = candidatos[0]
    return achados


def carregar_tudo(entrada: Path) -> Dados:
    a = localizar(Path(entrada))
    return Dados(
        arquivos={k: p.name for k, p in a.items()},
        orbe=orbe.ler(a["orbe"]),
        taxas=taxas.ler(a["taxas"]),
        taxas_2025=taxas.ler_aba_antiga(a["taxas"]),
        ponte=ponte.ler(a["ponte"]),
        plano_contas=plano_contas.ler(a["plano_contas"]),
        aurora=aurora.ler(a["aurora"]),
        meridiano=meridiano.ler(a["meridiano"]),
    )
