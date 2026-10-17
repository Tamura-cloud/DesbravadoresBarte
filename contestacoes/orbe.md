[RASCUNHO — Helena revisa antes de enviar]

NOTAS PARA A HELENA — apagar antes de enviar

Contexto interno. Nada deste bloco vai para a Orbe.

Avisos da condição à contraparte (resposta da Helena às 9h53):
- Escola Bridge de Idiomas Ltda: foi avisada só alguns dias depois do início da vigência (2026-09-15).
- Rota Global Intercâmbio Ltda: não há registro de que a Orbe tenha sido avisada.

Condição usada no texto (referências da planilha, que não vão no e-mail):
- Escola Bridge de Idiomas Ltda: planilha de taxas, linha 7, observação "só mudou o crédito à vista", vigente desde 2026-09-15.
- Rota Global Intercâmbio Ltda: planilha de taxas, linha 10, vigente desde 2026-01-01.

Valor a devolver a cada lojista (R25, R45, pendências PEN-DEVOL-CHK): o que saiu do bolso do lojista, o valor_taxa descontado pela Orbe menos a comissão pela taxa contratada, transação a transação.
- Escola Bridge de Idiomas Ltda: **R$ 29,94**. O e-mail cobra da Orbe R$ 29,95 (valor bruto × diferença de taxa, arredondado, como em divergencias_taxa.csv); nas mesmas 5 transações, o descontado de fato a mais foi R$ 29,94. A diferença de R$ 0,01 é arredondamento: a Orbe trunca o valor_taxa no centavo (P03).
- Rota Global Intercâmbio Ltda: **R$ 1.545,86**. O e-mail cobra da Orbe R$ 1.546,28 (valor bruto × diferença de taxa, arredondado, como em divergencias_taxa.csv); nas mesmas 87 transações, o descontado de fato a mais foi R$ 1.545,86. A diferença de R$ 0,42 é arredondamento: a Orbe trunca o valor_taxa no centavo (P03).

Os 4 estornos entram no total do e-mail e o reduzem.

Concessões comerciais (fora do e-mail, R32):
- Casa do Estudante Viagens Ltda: devolução de R$ 15.396,77 paga pela Tarvo (concessão, Helena 11h37). Decidir com o comercial se pede à Orbe parametrizar 0% daqui em diante.

---

Para: <e-mail da Orbe>
Assunto: Taxas de checkout - competência 2026-09

Prezados,

Na conferência da competência 2026-09, comparamos as taxas contratadas dos lojistas com as aplicadas pela Orbe em 92 transações de 2 lojistas. As transações estão no anexo orbe_operacoes.csv (coluna diferenca_brl = valor bruto × diferença entre a taxa aplicada e a contratada).

## 1. Taxas aplicadas acima do contrato

- Escola Bridge de Idiomas Ltda (CNPJ 22224579000109): condição contratada vigente desde 2026-09-15. 5 transações de crédito à vista, de 2026-09-15 a 2026-09-18, com taxa aplicada de 2,59% contra 2,19% contratados, somando R$ 29,95.
  - A nova condição vale só para crédito à vista (2,19%), desde 2026-09-15; as demais modalidades não mudaram.
- Rota Global Intercâmbio Ltda (CNPJ 95927868000148): condição contratada vigente desde 2026-01-01. 87 transações de crédito parcelado e crédito à vista, de 2026-09-12 a 2026-09-30, com taxa aplicada de 2,99% a 4,09% contra 2,49% a 3,59% contratados, somando R$ 1.546,28.
  - Até 2026-09-11 (52 transações), a taxa aplicada foi a contratada.
  - A partir de 2026-09-12, todas as 83 transações de crédito à vista e crédito parcelado vieram com a taxa 0,50 p.p. acima da contratada; as de antecipação, débito e PIX seguiram a taxa contratada.

| lojista | CNPJ | transações | taxa contratada | taxa aplicada | diferença (R$) |
| --- | --- | ---: | --- | --- | ---: |
| Escola Bridge de Idiomas Ltda | 22224579000109 | 5 | 2,19% | 2,59% | 29,95 |
| Rota Global Intercâmbio Ltda | 95927868000148 | 87 | 2,49% a 3,59% | 2,99% a 4,09% | 1.546,28 |

Pedimos que a Orbe informe a causa e corrija a parametrização. O total desta parte é R$ 1.576,23.

Dos totais acima, 4 linhas são estornos: eles devolvem o que foi cobrado a maior na venda original e reduzem o total em R$ 98,44.

Atenciosamente,
[assinatura da Helena]
