"""Conferência do layout de um arquivo de entrada: colunas a mais ou fora de ordem (R44, item d).

Só compara nomes de coluna. Coluna obrigatória faltando continua sendo erro do leitor (a fonte fica bloqueada);
coluna a mais ou fora de ordem vira aviso, e a leitura segue pelo nome.
"""

from __future__ import annotations

from typing import Iterable


def avisos_layout(arquivo: str, cabecalho: Iterable[str], esperadas: Iterable[str]) -> list[str]:
    """Avisos para coluna que não é do layout e para colunas do layout fora da ordem esperada.

    cabecalho e esperadas já vêm normalizados pelo leitor (do jeito que ele compara os nomes).
    Coluna sem nome não é aviso: leitores de planilha leem a linha inteira, com células vazias.
    """
    cabecalho = [c for c in cabecalho if c]
    esperadas = list(esperadas)
    avisos = []
    extras = [c for c in cabecalho if c not in esperadas]
    if extras:
        avisos.append(f"{arquivo}: coluna(s) fora do layout esperado: {', '.join(extras)} "
                      "(não usadas pelo fechamento)")
    na_ordem = [c for c in cabecalho if c in esperadas]
    ordem_esperada = [c for c in esperadas if c in na_ordem]
    if na_ordem != ordem_esperada:
        i = next(i for i, (a, b) in enumerate(zip(na_ordem, ordem_esperada)) if a != b)
        avisos.append(f"{arquivo}: colunas fora da ordem esperada (a partir de {na_ordem[i]!r}, no lugar de "
                      f"{ordem_esperada[i]!r}); a leitura seguiu pelo nome da coluna")
    return avisos
