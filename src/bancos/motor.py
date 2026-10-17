"""Classificação dos dois extratos no plano de contas. Dono: Pessoa C.

Entrada: dados.aurora, dados.meridiano, dados.plano_contas, dados.ponte
(para casar PIX recebidos), cfg = config/bancos.toml.
Saída: ResultadoModulo com lancamentos e pendencias.

Regras (CLAUDE.md, seção 3.4):
1. Cada lançamento aparece exatamente uma vez; ref_origem = L<linha> (Aurora)
   ou FITID (Meridiano).
2. Primeira regra de cfg['regras'] que casa (regex no histórico + banco) define
   a conta; metodo=REGRA, confianca=1. Conta tem que ser analítica
   (plano_contas[conta].aceita_lancto).
3. Regra com 'pendencia' gera também uma Pendencia.
4. Sem regra: metodo=IA com confianca; abaixo de 0.80 vira pendência (HUMANO).
5. Conciliação que gera pendência mesmo com regra:
   - transferência do Aurora sem par no Meridiano no mês (L92, R$ 300.000,00);
   - PIX recebido no Meridiano que não fecha com Valor R$ + IOF da Ponte
     (MRD2026090425, R$ 18.240,00).

Aceite (tests/test_bancos.py): 184 lançamentos, todos em conta analítica;
L15 -> 2.1.04.001; MRD2026090132 -> 1.1.03.002; L50 -> 1.1.09.002 + pendência;
MRD2026090425 -> 2.1.02.001 + pendência; L92 + pendência.
"""
from ..core.modelos import ResultadoModulo
from ..leitores import Dados


def executar(dados: Dados, cfg: dict, competencia: str) -> ResultadoModulo:
    raise NotImplementedError("bancos: implementar (Pessoa C)")
