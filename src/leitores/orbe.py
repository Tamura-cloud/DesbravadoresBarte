"""Relatório de comissões da Orbe (CSV utf-8, ';', vírgula decimal)."""
import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from ..core.dinheiro import brl, data_br


@dataclass
class TransacaoOrbe:
    ref_origem: str            # id_transacao
    linha: int                 # linha física no arquivo
    data_movimento: date
    cod_estabelecimento: str
    nome_estabelecimento: str
    tipo_lancamento: str       # VENDA | ESTORNO | ANTECIPACAO | REVERSAO ANTECIPACAO
    modalidade: str | None     # DEBITO | CREDITO A VISTA | CREDITO PARCELADO | PIX | None (antecipação)
    qtd_parcelas: int | None
    bandeira: str
    valor_bruto: Decimal       # negativo em estorno/reversão
    taxa_aplicada_pct: Decimal # pontos percentuais (2.69 = 2,69%)
    valor_taxa: Decimal        # o que a Orbe cobrou (truncado)
    valor_liquido: Decimal
    id_referencia: str | None
    data_venda_original: date | None

    @property
    def data_referencia_taxa(self) -> date:
        """Data que define a taxa contratada: a venda original, no estorno (regra R04)."""
        return self.data_venda_original or self.data_movimento


def ler(caminho: Path) -> list[TransacaoOrbe]:
    with open(caminho, encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))
    return [
        TransacaoOrbe(
            ref_origem=r["id_transacao"].strip(),
            linha=n,
            data_movimento=data_br(r["data_movimento"]),
            cod_estabelecimento=r["cod_estabelecimento"].strip(),
            nome_estabelecimento=r["nome_estabelecimento"].strip(),
            tipo_lancamento=r["tipo_lancamento"].strip(),
            modalidade=r["modalidade"].strip() or None,
            qtd_parcelas=int(r["qtd_parcelas"]) if r["qtd_parcelas"].strip() else None,
            bandeira=r["bandeira"].strip(),
            valor_bruto=brl(r["valor_bruto"]),
            taxa_aplicada_pct=brl(r["taxa_aplicada_pct"]),
            valor_taxa=brl(r["valor_taxa"]),
            valor_liquido=brl(r["valor_liquido"]),
            id_referencia=r["id_referencia"].strip() or None,
            data_venda_original=data_br(r["data_venda_original"]),
        )
        for n, r in enumerate(linhas, start=2)
    ]
