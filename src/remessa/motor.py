"""Comissão, divergências e nota da remessa. Dono: Pessoa B.

Entrada: dados.ponte.operacoes, dados.taxas (coluna spread), dados.meridiano
(conferência), cfg = config/remessa.toml.
Saída: ResultadoModulo com comissoes, divergencias, notas e pendencias (REMESSA).

Regras (CLAUDE.md, seção 3.3):
1. Deduplicar por Nº Operação antes de somar; a cópia (observação 'reprocessada')
   sai do cálculo e vira pendência para a Ponte corrigir o relatório.
2. Spread negativo com observação 'Taxa travada no pedido (D-1)': fora da
   comissão e da nota; entra em divergências e em pendência de contestação.
3. Competência pela data de contratação (as 6 de 30/09 liquidadas em 01/10 entram).
   'APROVADO C/ RESSALVA' entra normalmente.
4. comissao_operacao = arred(spread_brl * 0.50); soma por lojista (CNPJ).
5. Spread contratado = coluna da planilha pelo CNPJ; em branco/'padrão' = 1.50.
   Divergência se |spread_pct - contratado| >= 0.01 p.p.:
   arred((spread_pct - contratado) / 100 * ptax_ref * valor_me), valor cheio.
6. Uma nota só, tomador Ponte Câmbio, pelo total das comissões.
7. Pendências de contestação (Mundo Aberto, spreads negativos, duplicata) com
   valores e operações, mais 'conferir o TED de outubro quando cair'.
   Não supor desconto no repasse.

Aceite (tests/test_remessa.py): nota única de 39543.45 para 75374179000146;
228 operações na comissão; 23 divergências da Mundo Aberto somando 1418.85;
4 negativos fora da comissão; PC-0926-0162 contado uma vez.
"""
from ..core.modelos import ResultadoModulo
from ..leitores import Dados


def executar(dados: Dados, cfg: dict, competencia: str) -> ResultadoModulo:
    raise NotImplementedError("remessa: implementar (Pessoa B)")
