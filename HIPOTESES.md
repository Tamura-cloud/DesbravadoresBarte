# HIPOTESES.md — Premissas Contábeis, Operacionais e Regras de Fechamento (Setembro/2026)

Este documento registra todas as premissas, regras de negócio confirmadas com o financeiro da Tarvo (Helena) e decisões técnicas adotadas no fechamento de setembro/2026.

---

## 1. Mapeamento Cadastral, Contratos e Condições Comerciais

* **H01 — Vínculo dos 3 ECs sem código na aba `'Taxas vigentes'` (`02_tabela_taxas_contratadas.xlsx`):**
  * Confirmado pelo financeiro e validado pelo cruzamento de razão social e taxas aplicadas pela Orbe:
    * `EC 1043300981` (`HORIZONTE INTERCAMBIO`) $\rightarrow$ **Novo Horizonte Intercambio** (`CNPJ 66564512000199`).
    * `EC 1043396662` (`HORIZONTE VIAGENS TURISMO`) $\rightarrow$ **Horizonte Viagens** (`CNPJ 78576234000179`).
    * `EC 1038867654` (`KIWI EXPERIENCE TURISMO`) $\rightarrow$ **Kiwi Experience** (`CNPJ 07752116000126`).
* **H02 — `Atlas Idiomas Ltda` (`EC 1076801732`, `CNPJ 39566044000119`):**
  * Começou a transacionar em `10/09/2026` (`57` transações, `R$ 262.138,61` brutos, `R$ 7.876,05` de taxa retida pela Orbe), mas consta apenas na aba histórica `'ANTIGO 2025 - nao usar'` sem contrato assinado na aba vigente.
  * **Decisão:** Conforme orientação expressa do financeiro (*"Não fatura a Atlas até o comercial confirmar"*), a Atlas Idiomas **não tem NF emitida em `notas_a_emitir.csv`**, não gera apontamentos em `divergencias_taxa.csv` (por ausência de taxa contratada confirmada) e é registrada integralmente em `pendencias.csv` para validação contratual junto ao Comercial (Diego).
* **H03 — Condição Especial de Isenção (`0,00%`) da `Casa do Estudante Viagens Ltda` (`EC 1018325654`, `CNPJ 00520815000100`):**
  * A célula `A13` da planilha vigente possui comentário indicando condição especial acordada com o comercial (Diego). Conforme confirmação do financeiro, a Casa do Estudante possui **tarifa zerada (`0,00%`) no Checkout (MDR e Antecipação) de setembro a dezembro/2026** (mantendo-se o spread contratado normal de `1,50%` apenas em Remessas de Câmbio).
  * Como a Orbe não foi parametrizada a tempo, cobrou indevidamente `R$ 15.391,27` nas `119` movimentações do mês.
  * **Tratamento do Estorno de Venda de Agosto (`TX88445133`):** Em `07/09/2026`, ocorreu o estorno de débito `TX88445133` (`-R$ 369,39`) referente a uma venda realizada em **`21/08/2026`**. Pela regra de que o estorno utiliza a taxa vigente na `data_venda_original` (`1,49%` em agosto, antes do início da isenção de setembro a dezembro), esse estorno gera comissão contratada de **`-R$ 5,50`** em setembro (sem divergência de taxa), enquanto as demais **118** transações de setembro têm taxa contratada de `0,00%` (gerando `R$ 15.397,32` de divergência a devolver ao lojista pelo cálculo arredondado linha a linha). Como o saldo líquido de comissão de Checkout da Casa do Estudante em setembro fica negativo (`-R$ 5,50`), **não se emite NF de Checkout** e registra-se o saldo negativo e a devolução das taxas cobradas pela Orbe em `pendencias.csv`.
* **H04 — Preservação de Zeros à Esquerda em CNPJs:**
  * Na planilha de taxas contratadas, os CNPJs de `Fluente Idiomas Online Ltda` (`03229837000103`) e `Campus Global Ltda` (`08780784000120`) estavam formatados como números inteiros de 13 dígitos. Todos os CNPJs foram padronizados para `14` dígitos numéricos com preenchimento de zero à esquerda (`zfill(14)`).

---

## 2. Regras de Cálculo de Comissões, Arredondamento e Divergências

* **H05 — Arredondamento Padrão (`ROUND_HALF_UP`) Linha a Linha:**
  * Enquanto a adquirente Orbe trunca os centavos na segunda casa decimal, a Tarvo adota **arredondamento padrão para o centavo (`ROUND_HALF_UP`: `0,005 -> 0,01` e `-0,005 -> -0,01`) aplicado individualmente em cada transação/operação** antes da soma por lojista/modalidade.
* **H06 — Base da Comissão e Divergências no Checkout (`CHECKOUT`):**
  * O faturamento de Checkout (comissão e Nota Fiscal por lojista) é apurado pela **taxa contratada** (`ROUND_HALF_UP(valor_bruto * taxa_contratada_pct / 100, 2)`).
  * Diferenças de `R$ 0,01` decorrentes exclusivamente do truncamento da Orbe **não constituem divergência**.
  * Só há registro em `divergencias_taxa.csv` quando `taxa_aplicada_pct != taxa_contratada_pct`, sendo a diferença calculada como `ROUND_HALF_UP(valor_bruto * (taxa_aplicada_pct - taxa_contratada_pct) / 100, 2)`. Isso ocorre em 3 lojistas no Checkout:
    1. **`Casa do Estudante` (`EC 1018325654`):** cobrança de MDR e antecipação pela Orbe durante vigência da tarifa `0,00%` (`118` transações de setembro, `R$ 15.397,32`).
    2. **`Rota Global Intercâmbio Ltda` (`EC 1074504011`):** cobrança indevida de `+0,50 p.p.` pela Orbe a partir de `12/09/2026` sem reajuste contratual (`87` transações, diferença líquida de **`R$ 1.546,28`**).
    3. **`Escola Bridge de Idiomas Ltda` (`EC 1075624862`):** cobrança de `2,59%` em vez da taxa renegociada de `2,19%` (vigente a partir de `15/09/2026`) em **`5` vendas** de Crédito à Vista entre `15/09` e `18/09`, somando **`R$ 29,95`**.
* **H07 — Estornos, Antecipações e Reversões no Checkout:**
  * Estornos (`ESTORNO`) ocorridos em setembro referentes a vendas de agosto entram na competência setembro (pois agosto já está fechado), abatendo a comissão pela taxa contratada vigente na `data_venda_original`.
  * Lançamentos de `ANTECIPACAO` (`2,10%`, exceto Casa do Estudante `0,00%`) e `REVERSAO ANTECIPACAO` (que anula a taxa da antecipação referenciada em `id_referencia`) compõem a base da **mesma Nota Fiscal mensal de Checkout** de cada lojista.
  * Lojistas com saldo mensal de comissão igual a zero ou negativo não têm NF emitida, sendo eventual saldo negativo reportado em `pendencias.csv`.
* **H08 — Base da Comissão, Exceções e Divergências em Remessas (`REMESSA` — Ponte Câmbio):**
  * Diferentemente do Checkout, nas remessas internacionais a comissão da Tarvo e a **Nota Fiscal única emitida contra a Ponte Câmbio S.A. (`75374179000146`)** são calculadas como **50% do `Spread R$` realizado**, arredondado (`ROUND_HALF_UP`) **operação por operação**.
  * Células de spread em branco ou com texto `"padrão"` na planilha de taxas correspondem a **`1,50%` sobre a PTAX de referência** (`PTAX Ref. × Valor ME`).
  * **Operações Incluídas em Setembro (`228` operações válidas $\rightarrow$ NF Ponte Câmbio = `R$ 39.543,45`):**
    * Operações contratadas em `30/09/2026` e liquidadas em `01/10/2026` (`PC-0926-0002`, `PC-0926-0077`, `PC-0926-0148`) entram em setembro pelo regime de competência (data de contratação).
    * Operações com status `"APROVADO C/ RESSALVA"` entram normalmente.
    * As **23 operações da `Mundo Aberto` (`17217888000111`)** em que a Ponte aplicou `~1,50%` em vez dos `1,20%` renegociados em jul/2026 **entram na comissão e na NF de setembro pelo valor realizado** (pois compõem o repasse imediato da Ponte), mas são reportadas em `divergencias_taxa.csv` pelo **valor cheio pago a mais pelo lojista (`R$ 1.418,85` = `(Spread % aplicado − 1,20%) × PTAX × Valor ME`)** e em `pendencias.csv` para contestação junto à Ponte Câmbio.
  * **Operações Excluídas da Comissão e da NF de Remessa:**
    * **Duplicidade (`PC-0926-0162`):** a segunda linha com mesmo número de operação e observação `"Operação reprocessada"` (`Spread R$ 821,88`) é descartada do cálculo e reportada em `pendencias.csv`.
    * **4 Operações com Spread Negativo (`PC-0926-0210`, `PC-0926-0326`, `PC-0926-0491`, `PC-0926-0545`, soma `Spread R$ = -R$ 1.834,05`):** decorrentes de `"Taxa travada no pedido (D-1)"` fora do limite contratual de 2 horas. São excluídas da comissão e da NF, e reportadas em `divergencias_taxa.csv` e `pendencias.csv` para contestação.
  * **Critério de Tolerância de Arredondamento PTAX (`0,01 p.p.`):** Oscilações inferiores a `0,01 p.p.` entre o `Spread %` reportado pela Ponte e a taxa contratada (ex.: `1,4984%` a `1,5015%` para taxa de `1,50%`) decorrem do arredondamento da taxa final de câmbio em 4 casas decimais e não são reportadas como divergência.
  * **Conciliação Preventiva do TED da Ponte em `06/10`:** Como o total bruto do relatório da Ponte (`R$ 78.073,59`) soma a duplicata (`+R$ 410,94` na cota de 50% da Tarvo) e deduz os 4 spreads negativos (`-R$ 917,03` na cota da Tarvo), o TED automático previsto pela Ponte (`R$ 39.036,80`) apresentará diferença de **`R$ 506,65`** frente à NF emitida pela Tarvo (`R$ 39.543,45`), registrada preventivamente em `pendencias.csv`.

---

## 3. Classificação Contábil dos Extratos Bancários (`lancamentos_classificados.csv`)

* **H09 — Regra da Contrapartida Contábil e Apropriação de Competência:**
  * O campo `conta_codigo` registra a **contrapartida contábil analítica (`ACEITA_LANCTO = S`)** da movimentação bancária:
    1. **Obrigações e Recebíveis de Agosto Já Provisionados:** pagamentos de Folha `08/2026` (`2.1.04.001`), ISS `08/2026` (`2.1.03.003`), INSS `08/2026` (`2.1.04.002`), FGTS `08/2026` (`2.1.04.003`), bem como os DARFs pagos em setembro referentes a fatos geradores de agosto — IRRF `0561` (`2.1.03.004`), PIS `8109` (`2.1.03.001`) e COFINS `2172` (`2.1.03.002`) — baixam os respectivos passivos provisionados. O recebimento do repasse da Ponte Câmbio em `04/09` (`MRD2026090132`, `R$ 61.884,12`, ref. `08/2026`) baixa o ativo `1.1.03.002` (*Comissões de intermediação a receber - câmbio*).
    2. **Despesas do Mês Não Provisionadas:** tarifas bancárias (`4.2.01`), condomínio (`4.2.02`), AWS cloud (`4.2.03`), Google Workspace (`4.2.04`), contabilidade (`4.2.06`) e IOF (`4.3.01`) são lançados diretamente nas respectivas contas de resultado (`4.x`).
* **H10 — Tratamento das Anomalias Bancárias e de Conciliação:**
  * `16/09/2026` (`L042`, Aurora) — `PIX RECEBIDO 38686002000180 SEM IDENTIFICACAO` (`+R$ 7.350,00`): não reconhecido como receita até identificação da origem; classificado na conta transitória `1.1.09.002` (*Créditos não identificados*) + `pendencias.csv`.
  * `23/09/2026` (`L057`, Aurora) — `DEVOLUCAO PIX - MUNDO ABERTO INTERC` (`+R$ 12.400,00`): estorno bancário parcial de repasse enviado ao lojista; classificado em `2.1.01.001` (*Repasses a lojistas a pagar*, recompondo a obrigação de repasse) + `pendencias.csv`.
  * `30/09/2026` (`L084`, Aurora) — `TRANSF ENTRE CONTAS P/ BCO MERIDIANO` (`-R$ 300.000,00`): saída no último dia do mês cuja compensação no Banco Meridiano ocorre em `01/10/2026`; classificado em `1.1.09.001` (*Transferências entre contas próprias*) + `pendencias.csv`.
  * `17/09/2026` (`MRD2026090364`, Meridiano) — `PIX RECEB PONTE AÉREA ESTUDANTIL L` (`+R$ 18.240,00`): recurso recebido na conta de câmbio sem operação correspondente no relatório de setembro da Ponte Câmbio; classificado em `2.1.02.001` (*Recursos de lojistas para remessas a liquidar*) + `pendencias.csv`.
