"""Linha de um arquivo de entrada que não pôde ser convertida (R44: o erro de uma linha não para o mês).

O leitor, chamado com uma lista de rejeitadas, guarda nela a linha com o dado inválido e segue para a próxima; sem
a lista, a linha inválida continua sendo erro. O fechamento transforma cada rejeitada numa pendência PEN-REGRA.
"""

from __future__ import annotations

from decimal import Decimal
from typing import NamedTuple


class LinhaRejeitada(NamedTuple):
    arquivo: str
    ref: str                      # onde está: "L<n>" (linha física), "linha N" (planilha) ou o FITID
    erro: str                     # o dado exato que impediu a leitura
    ident: str | None = None      # id da linha, se deu para ler: id_transacao, Nº Operação, FITID
    cnpj: str | None = None       # CNPJ da linha, se deu para ler (Ponte, planilha de taxas)
    ec: str | None = None         # EC da linha, se deu para ler (Orbe, planilha de taxas)
    valor: Decimal | None = None  # valor da linha, se deu para ler (extratos)
