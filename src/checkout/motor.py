"""Comissão, divergências e notas do checkout. Dono: Pessoa A.

Entrada: dados.orbe, dados.taxas, cfg = config/checkout.toml.
Saída: ResultadoModulo com comissoes, divergencias, notas e pendencias (CHECKOUT).

Regras (CLAUDE.md, seção 3.2):
1. Lojista pelo cod_estabelecimento -> linha da planilha pelo EC; se o EC está
   vazio na planilha, usar cfg['ec_sem_codigo'] (EC -> CNPJ). Nunca pelo nome.
2. Taxa contratada pela modalidade (débito, crédito à vista, 2-6x, 7-12x, PIX,
   antecipação) na linha cuja vigência vale na `data_referencia_taxa` (Bridge
   tem 2 linhas). REVERSAO ANTECIPACAO usa a taxa de antecipação.
   cfg['condicoes_especiais'] sobrepõe a taxa no período (Casa do Estudante).
3. comissao_linha = arred(valor_bruto * taxa_contratada / 100); soma por lojista.
4. Divergência só se taxa_aplicada != contratada:
   arred(valor_bruto * (aplicada - contratada) / 100). Centavo de truncamento não conta.
5. EC em cfg['sem_contrato'] (Atlas): sem nota, sem divergência, uma pendência.
6. Uma nota por lojista com saldo > 0; saldo <= 0 vira pendência (Helena decide).
7. Todo número com rastro: ItemRastro(arquivo Orbe, id_transacao, valor da linha).

Aceite (tests/test_checkout.py): 20 notas somando 207045.23; 210 divergências
(Casa 15397.42, Rota 1546.28, Bridge 29.95); Casa com saldo -5.50 em pendência;
nenhuma nota ou divergência da Atlas.
"""
from ..core.modelos import ResultadoModulo
from ..leitores import Dados


def executar(dados: Dados, cfg: dict, competencia: str) -> ResultadoModulo:
    raise NotImplementedError("checkout: implementar (Pessoa A)")
