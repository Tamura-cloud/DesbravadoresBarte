# Hipóteses — fechamento de setembro/2026

Fontes deste arquivo:
- **Fonte 1:** HIPOTESES.md do colega em `origin/main` (commit `d425cd4`). Todo o conteúdo dela está aqui, nas seções 2, 4 e 5, identificado como `F1-H01` a `F1-H10`.
- **Fonte 2:** respostas públicas da Helena (financeiro da Tarvo) no canal #tarvo-financeiro em 16/10/2026. As perguntas foram feitas por outros times; as respostas valem para todos.

Pela regra do CLAUDE.md, só entra no código regra de negócio que esteja aqui. Os valores de setembro citados neste arquivo são referência para os testes, nunca para `src/` ou `config/`.

---

## 1. Regras confirmadas pelo financeiro (fonte: Slack, com horário)

### Checkout (Orbe)

- **R01** — Comissão de checkout = valor_bruto × taxa contratada da planilha, linha a linha. O valor_taxa da Orbe NÃO é a comissão. A nota fiscal vai pela taxa contratada. *(pergunta de Fox AI, resposta da Helena às 20h05)*
- **R02** — Arredondamento comum para o centavo (meio centavo para longe do zero: -0,005 vira -0,01), linha a linha e depois soma. A Orbe trunca; truncamento não é divergência. *(pergunta de Fox AI, resposta da Helena às 21h13)*
- **R03** — Divergência de checkout existe só quando a taxa aplicada ≠ contratada. Valor = valor_bruto × (aplicada − contratada). A devolução ao lojista é decisão da Helena, caso a caso. *(pergunta de Fox AI, resposta da Helena às 20h05; pergunta de Fox AI, resposta da Helena às 21h13)*
- **R04** — Estorno abate a comissão no mês do estorno (inclusive de venda de agosto), pela taxa contratada vigente na data da venda original. *(pergunta de MN AI, resposta da Helena às 20h06)*
- **R05** — Antecipação entra na mesma nota do lojista; a reversão anula só a taxa da antecipação que ela reverte. *(pergunta de MN AI, resposta da Helena às 20h47)*
- **R06** — Nota de checkout: uma por lojista por mês. Zero ou negativo não emite nota e vira pendência da Helena (não passa para o mês seguinte). Discriminação simples: serviço + competência. *(pergunta de MN AI, resposta da Helena às 20h47)*

### Cadastro de lojistas

- **R07** — EC 1043300981 = Novo Horizonte Intercâmbio; EC 1043396662 = Horizonte Viagens e Turismo (empresas diferentes); EC 1038867654 = Kiwi Experience. CNPJ e taxas pelas linhas delas na aba vigente. *(pergunta de Fox AI, resposta da Helena às 20h24)*
- **R08** — Atlas Idiomas (EC 1076801732): começou em 10/09, sem contrato vigente, taxa desconhecida. Não faturar até o comercial confirmar. A aba de 2025 não vale. *(pergunta de Fox AI, resposta da Helena às 20h24)*
- **R09** — Rota Global: o contrato não mudou em 2026; as taxas acima da planilha são divergência. *(pergunta de Lucca Landeiro, resposta da Helena às 20h49)*
- **R10** — Casa do Estudante: tarifa zerada no checkout (MDR e antecipação) de setembro a dezembro de 2026, por acordo do comercial. A remessa segue normal. O que a Orbe cobrou é devolvido ao lojista. *(pergunta de Lucca Landeiro, resposta da Helena às 20h49)*

### Remessa (Ponte Câmbio)

- **R11** — Comissão de remessa = 50% do Spread R$ realizado (e-mail da Ponte), arredondado por operação. A competência é a data de contratação. O status de compliance não muda nada. *(pergunta de MN AI, resposta da Helena às 20h48; arredondamento: pergunta de Fox AI, resposta da Helena às 21h13)*
- **R12** — Spread negativo (trava D-1 vencida, a trava vale 2h): fora da comissão e da nota; a Helena contesta. *(pergunta de MN AI, resposta da Helena às 20h48)*
- **R13** — Nº de operação é único: a duplicata conta uma vez e entra na lista de correção para a Ponte. *(pergunta de MN AI, resposta da Helena às 20h48; pergunta de Insper AI, resposta da Helena às 22h34)*
- **R14** — Spread "padrão" ou célula em branco = 1,5% sobre a PTAX de referência. *(pergunta de MN AI, resposta da Helena às 20h48)*
- **R15** — Divergência de remessa = valor cheio (o que o lojista pagou a mais), não a nossa metade. A tolerância é decisão nossa, escrita com o motivo. *(pergunta de Fox AI, resposta da Helena às 20h58)*
- **R16** — A nota de remessa sai pelo realizado, inclusive o excesso da Mundo Aberto; o ajuste vem no mês em que a Ponte devolver. Fica como pendência da Helena. *(pergunta de Theo Garcia, resposta da Helena às 21h45)*
- **R17** — Nota de remessa: uma só, tomadora Ponte Câmbio, pelo total da participação no mês. *(pergunta de MN AI, resposta da Helena às 20h47)*
- **R18** — Nada foi contestado ainda e o prazo está ok. Pendência de contestação com valor e operações. Não supor desconto no repasse; conferir o TED de outubro é pendência da Helena. *(pergunta de Lucca Landeiro, resposta da Helena às 22h33; pergunta de Insper AI, resposta da Helena às 22h34)*

### Extratos e classificação contábil

- **R19** — conta_codigo = contrapartida do movimento no banco. Folha, ISS, INSS, FGTS e DARFs de agosto e o repasse da Ponte de 04/09 já estavam registrados: baixam passivo ou recebível. Tarifas, aluguel, cloud, assinaturas e serviços entram direto na despesa do mês. Quando o extrato não deixar claro: premissa no HIPOTESES.md. *(pergunta de Fox AI, resposta da Helena às 21h14)*
- **R20** — PIX de R$ 7.350 sem identificação: não é receita até identificar. Devolução de PIX da Mundo Aberto: repasse que voltou, motivo desconhecido. Transferência de R$ 300 mil: sai do Aurora em 30/09 e cai no Meridiano em 01/10. *(pergunta de Lucca Landeiro, resposta da Helena às 20h49)*
- **R21** — A Orbe deposita tudo no Aurora. O saldo negativo é a conta garantida. Conciliar Orbe × banco parcela a parcela está fora do escopo: só classificar os créditos. *(pergunta de Insper AI, resposta da Helena às 22h34)*

---

## 2. Premissas nossas (com o motivo)

### 2.1 Premissas definidas pelo time

- **P01 — Tolerância de divergência de remessa:** diferença de spread abaixo de 0,01 p.p. não é divergência.
  - **Motivo:** a Ponte arredonda o spread entre 1,4984% e 1,5015%. A maior oscilação observada é de ±0,002 p.p., e a menor divergência real (Mundo Aberto) é de 0,3 p.p. É a tolerância que R15 deixa a nosso cargo. A Fonte 1 adota o mesmo critério (ver F1-H08).
- **P02 — Spread negativo também é divergência:** entra em divergencias_taxa.csv, com diferença negativa contra o contratado, e em pendencias.csv como contestação.
  - **Motivo:** a taxa aplicada é diferente da contratada (R15), e R12 manda contestar. A Fonte 1 faz o mesmo (ver F1-H08).
- **P03 — Truncamento da Orbe:** a Orbe trunca valor_taxa no centavo (verificado: as 1943 linhas batem com ROUND_DOWN, e 1001 não batem com ROUND_HALF_UP). Por isso a divergência compara taxa aplicada × contratada, nunca valores (R02).

### 2.2 Premissas e achados do HIPOTESES.md do colega (Fonte 1)

O conteúdo da Fonte 1 está reproduzido abaixo. Onde ela contradizia a Helena, o trecho foi ajustado à regra dela, e a versão original ficou registrada em "Conflitos resolvidos" na seção 4. Onde ela diz "confirmado pelo financeiro", a confirmação corresponde às respostas públicas da seção 1, e a regra correspondente está indicada. Os valores numéricos foram calculados pelo colega e **ainda não foram reconferidos pelo nosso código**.

**Mapeamento cadastral, contratos e condições comerciais**

- **F1-H01 — Vínculo dos 3 ECs sem código na aba "Taxas vigentes"** (regra: R07)
  - EC 1043300981 (HORIZONTE INTERCAMBIO) → Novo Horizonte Intercambio, CNPJ 66564512000199.
  - EC 1043396662 (HORIZONTE VIAGENS TURISMO) → Horizonte Viagens, CNPJ 78576234000179.
  - EC 1038867654 (KIWI EXPERIENCE TURISMO) → Kiwi Experience, CNPJ 07752116000126.
  - **Motivo dado na Fonte 1:** "confirmado pelo financeiro e validado pelo cruzamento de razão social e taxas aplicadas pela Orbe".
  - **Nota nossa:**
    - O vínculo vale pela resposta da Helena (R07), não pelo nome. Pelo CLAUDE.md, o nome serve só de evidência.
    - Conferimos na aba "Taxas vigentes": os 3 CNPJs acima são os das linhas Novo Horizonte Intercambio, Horizonte Viagens e Kiwi Experience. Nessas linhas a coluna "EC Orbe" está vazia, e a da Kiwi tem a observação "EC pendente".
- **F1-H02 — Atlas Idiomas Ltda (EC 1076801732, CNPJ 39566044000119)** (regra: R08)
  - Começou a transacionar em 10/09/2026, com 57 transações, R$ 262.138,61 brutos e R$ 7.876,05 de taxa retida pela Orbe. Consta apenas na aba histórica "ANTIGO 2025 - nao usar", sem contrato assinado na aba vigente.
  - **Decisão da Fonte 1:**
    - Não emitir NF em notas_a_emitir.csv, conforme a orientação "Não fatura a Atlas até o comercial confirmar".
    - Não gerar linhas em divergencias_taxa.csv, por não haver taxa contratada confirmada.
    - Registrar integralmente em pendencias.csv, para validação contratual com o Comercial (Diego).
  - **Motivo:** R08 diz "taxa desconhecida". Sem taxa contratada, não há como calcular divergência (R03). A Helena não disse explicitamente "não gerar divergência"; isso é premissa.
- **F1-H03 — Isenção (0,00%) da Casa do Estudante Viagens Ltda (EC 1018325654, CNPJ 00520815000100)** (regras: R10, R04, R06)
  - **Isenção:** a célula A13 da planilha vigente tem o comentário "conversar com Diego (comercial) sobre condição especial". A tarifa no Checkout (MDR e antecipação) é zerada de setembro a dezembro/2026. Nas remessas de câmbio se mantém o spread contratado normal de 1,50%.
  - **Cobrança indevida:** como a Orbe não foi parametrizada a tempo, cobrou indevidamente R$ 15.391,27 nas 119 movimentações do mês.
  - **Estorno TX88445133:** em 07/09/2026, a Orbe estornou um débito de -R$ 369,39, referente a venda de 21/08/2026.
    - Pela regra de que o estorno usa a taxa vigente na data_venda_original, vale 1,49% (agosto, antes da isenção). O estorno gera comissão contratada de -R$ 5,50 em setembro, sem divergência de taxa.
    - As demais 118 transações de setembro têm taxa contratada de 0,00%. Elas geram R$ 15.397,32 de divergência a devolver ao lojista, pelo cálculo arredondado linha a linha.
  - **Consequência:** o saldo líquido de comissão de Checkout de setembro fica negativo (-R$ 5,50). Não se emite NF de Checkout, e o saldo negativo e a devolução das taxas cobradas pela Orbe vão para pendencias.csv.
  - **Nota nossa:**
    - Os dois totais são compatíveis: R$ 15.391,27 é o que a Orbe cobrou nas 119 linhas (inclui os -R$ 5,50 do estorno), e R$ 15.397,32 é a divergência arredondada nas 118 linhas.
    - A linha da Casa do Estudante na aba vigente tem vigência desde 01/01/2026 e Débito de 1,49%, o que sustenta a taxa de agosto usada no estorno.
- **F1-H04 — Zeros à esquerda em CNPJs:** ver seção 5.

**Regras de cálculo de comissões, arredondamento e divergências**

- **F1-H05 — ROUND_HALF_UP linha a linha** (regra: R02)
  - A Orbe trunca os centavos na segunda casa. A Tarvo arredonda para o centavo (0,005 → 0,01 e -0,005 → -0,01) em cada transação/operação, antes da soma por lojista e modalidade.
- **F1-H06 — Base da comissão e divergências no Checkout** (regras: R01, R03, R09)
  - **Base:** comissão e NF de Checkout pela taxa contratada: ROUND_HALF_UP(valor_bruto × taxa_contratada_pct / 100, 2).
  - **Truncamento:** diferenças de R$ 0,01 causadas só pelo truncamento da Orbe não são divergência.
  - **Quando há divergência:** só quando taxa_aplicada_pct ≠ taxa_contratada_pct. O valor é ROUND_HALF_UP(valor_bruto × (taxa_aplicada_pct − taxa_contratada_pct) / 100, 2).
  - **Casos encontrados:** 3 lojistas no Checkout.
    1. **Casa do Estudante (EC 1018325654):** cobrança de MDR e antecipação durante a tarifa 0,00%. São 118 transações de setembro, R$ 15.397,32.
    2. **Rota Global Intercâmbio Ltda (EC 1074504011):** cobrança indevida de +0,50 p.p. a partir de 12/09/2026, sem reajuste contratual. São 87 transações, com diferença líquida de R$ 1.546,28.
    3. **Escola Bridge de Idiomas Ltda (EC 1075624862):** cobrança de 2,59% em vez da taxa renegociada de 2,19% (vigente a partir de 15/09/2026) em 5 vendas de Crédito à Vista entre 15/09 e 18/09, somando R$ 29,95.
  - **Nota nossa:** a planilha confirma a renegociação da Bridge. Há duas linhas com o mesmo CNPJ e EC: Crédito à vista de 2,59% "até 14/09/2026" e de 2,19% "a partir de 15/09/2026" ("só mudou o crédito à vista"). A Helena não comentou a Bridge; o caso decorre de R03 aplicada à planilha.
- **F1-H07 — Estornos, antecipações e reversões no Checkout** (regras: R04, R05, R06)
  - **Estornos:** estornos de setembro referentes a vendas de agosto entram em setembro (agosto já está fechado). Eles abatem a comissão pela taxa contratada vigente na data_venda_original.
  - **Antecipações:** ANTECIPACAO (2,10%, exceto Casa do Estudante a 0,00%) e REVERSAO ANTECIPACAO compõem a base da mesma NF mensal de Checkout do lojista. A reversão anula a taxa da antecipação referenciada em id_referencia.
  - **Saldo zero ou negativo:** o lojista não tem NF emitida, e o saldo, seja zero ou negativo, vai para pendencias.csv (R06, Helena às 20h47). A Fonte 1 previa pendência só para o saldo negativo; ver C3 em "Conflitos resolvidos" na seção 4.
- **F1-H08 — Remessas (Ponte Câmbio)** (regras: R11 a R18; premissas P01 e P02)
  - **Base:** a comissão da Tarvo e a NF única contra a Ponte Câmbio S.A. (CNPJ 75374179000146) são 50% do Spread R$ realizado, arredondado (ROUND_HALF_UP) operação por operação. É diferente do Checkout.
  - **Spread padrão:** spread em branco ou "padrão" na planilha de taxas = 1,50% sobre a PTAX de referência (PTAX Ref. × Valor ME).
  - **Incluídas em setembro:** 228 operações válidas, com NF Ponte Câmbio = R$ 39.543,45.
    - Operações contratadas em 30/09/2026 e liquidadas em 01/10/2026 (PC-0926-0002, PC-0926-0077, PC-0926-0148) entram em setembro, pela data de contratação.
    - Operações com status "APROVADO C/ RESSALVA" entram normalmente.
    - **Mundo Aberto (CNPJ 17217888000111):** a Ponte aplicou ~1,50% em vez dos 1,20% renegociados em jul/2026. As 23 operações entram na comissão e na NF de setembro pelo valor realizado, porque compõem o repasse imediato da Ponte.
      - Em divergencias_taxa.csv entram pelo valor cheio pago a mais pelo lojista: R$ 1.418,85 = (Spread % aplicado − 1,20%) × PTAX × Valor ME.
      - Também vão para pendencias.csv, para contestação com a Ponte Câmbio.
  - **Excluídas da comissão e da NF:**
    - **Duplicidade PC-0926-0162:** a segunda linha com o mesmo número de operação e a observação "Operação reprocessada" (Spread R$ 821,88) é descartada do cálculo e reportada em pendencias.csv.
    - **4 operações com spread negativo:** PC-0926-0210, PC-0926-0326, PC-0926-0491 e PC-0926-0545, somando Spread R$ = -R$ 1.834,05. Decorrem de "Taxa travada no pedido (D-1)" fora do limite contratual de 2 horas. São excluídas da comissão e da NF e reportadas em divergencias_taxa.csv e pendencias.csv para contestação.
  - **Tolerância de arredondamento da PTAX (0,01 p.p.):**
    - Oscilações abaixo de 0,01 p.p. entre o Spread % reportado e a taxa contratada não são divergência; por exemplo, 1,4984% a 1,5015% para a taxa de 1,50%.
    - Vêm do arredondamento da taxa final de câmbio em 4 casas decimais. É a mesma tolerância de P01.
  - **TED da Ponte:** não supomos valor nem desconto no repasse (R18). A única pendência é conferir o TED da Ponte quando cair; quem decide é a Helena. A projeção da Fonte 1 foi removida; ver C1 em "Conflitos resolvidos" na seção 4.

**Classificação contábil dos extratos (lancamentos_classificados.csv)**

- **F1-H09 — Contrapartida contábil e competência** (regra: R19)
  - **Conta:** conta_codigo registra a contrapartida contábil analítica (ACEITA_LANCTO = S) da movimentação bancária.
  - **Obrigações e recebíveis de agosto já provisionados:** baixam os respectivos passivos ou ativos.
    - Folha 08/2026 → 2.1.04.001.
    - ISS 08/2026 → 2.1.03.003.
    - INSS 08/2026 → 2.1.04.002.
    - FGTS 08/2026 → 2.1.04.003.
    - DARFs pagos em setembro com fato gerador em agosto:
      - IRRF 0561 → 2.1.03.004.
      - PIS 8109 → 2.1.03.001.
      - COFINS 2172 → 2.1.03.002.
    - Repasse da Ponte Câmbio recebido em 04/09 (MRD2026090132, R$ 61.884,12, ref. 08/2026) → baixa o ativo 1.1.03.002 (Comissões de intermediação a receber - câmbio).
  - **Despesas do mês não provisionadas:** vão direto para as contas de resultado (4.x).
    - Tarifas bancárias → 4.2.01.
    - Condomínio → 4.2.02.
    - AWS cloud → 4.2.03.
    - Google Workspace → 4.2.04.
    - Contabilidade → 4.2.06.
    - IOF → 4.3.01.
  - **Motivo:** R19. Os códigos específicos são o mapeamento do colega para o plano de contas.
  - **IOF:** não é premissa. É aplicação de R19 (Helena às 21h14: "além desses, nada estava provisionado"). Como não estava provisionado, vai direto para a despesa 4.3.01.
  - **Nota nossa:** pelo CLAUDE.md, esse mapeamento vai para config/*.yaml, não para o código.
- **F1-H10 — Anomalias bancárias e de conciliação** (regras: R20, R19)
  - **16/09/2026 (L50, Aurora)** — "PIX RECEBIDO 38686002000180 SEM IDENTIFICACAO" (+R$ 7.350,00): não é receita até identificar a origem. Vai para a conta transitória 1.1.09.002 (Créditos não identificados) e para pendencias.csv.
  - **23/09/2026 (L65, Aurora)** — "DEVOLUCAO PIX - MUNDO ABERTO INTERC" (+R$ 12.400,00): repasse que voltou, motivo desconhecido (R20, Helena às 20h49). Vai para 2.1.01.001 (Repasses a lojistas a pagar) e para pendencias.csv, com a pendência de apurar o motivo. Ver C2 em "Conflitos resolvidos" na seção 4.
  - **30/09/2026 (L92, Aurora)** — "TRANSF ENTRE CONTAS P/ BCO MERIDIANO" (-R$ 300.000,00): saída no último dia do mês, compensada no Banco Meridiano em 01/10/2026. Vai para 1.1.09.001 (Transferências entre contas próprias) e para pendencias.csv.
  - **17/09/2026 (MRD2026090425, Meridiano)** — "PIX RECEB PONTE AEREA ESTUDANTIL L" (+R$ 18.240,00): recurso recebido na conta de câmbio sem operação correspondente no relatório de setembro da Ponte Câmbio. Vai para 2.1.02.001 (Recursos de lojistas para remessas a liquidar) e para pendencias.csv.
    - **Verificado:** é o único dos 64 PIX recebidos no Meridiano sem remessa correspondente na Ponte. Continua pendência, aguardando resposta da Helena.
    - **FITID corrigido:** a Fonte 1 citava MRD2026090364, que não existe no OFX. O lançamento de 17/09 de R$ 18.240,00 tem FITID MRD2026090425, e o MEMO no arquivo é "PONTE AEREA", sem acento.
  - **Motivo:** para os três primeiros casos, R20 dá o fato e R19 manda escrever a premissa quando o extrato não é claro. O quarto caso é achado do colega, verificado por nós, ainda sem resposta da Helena.

---

## 3. Perguntas feitas pelo nosso time (pergunta | resposta | horário)

A Fonte 1 não registra nenhuma pergunta feita pelo nosso time. As confirmações que ela cita são as respostas públicas da seção 1, dadas a perguntas de outros times.

| pergunta | resposta | horário |
|----------|----------|---------|

---

## 4. Pendências em aberto

### Pendências abertas

- **TED da Ponte:** conferir o TED da Ponte quando cair. Quem decide é a Helena (R18, 22h33/22h34).
- **Devolução de PIX da Mundo Aberto (L65, +R$ 12.400,00):** o motivo é desconhecido. Classificada em 2.1.01.001, com a pendência de apurar o motivo (R20, 20h49).
- **MRD2026090425 (+R$ 18.240,00, PONTE AEREA ESTUDANTIL):** verificado, é o único dos 64 PIX recebidos no Meridiano sem remessa correspondente na Ponte. Aguarda resposta da Helena.
- **Valores da Fonte 1:** contagens e totais (por exemplo, 228 operações, R$ 39.543,45, R$ 1.546,28 e R$ 1.418,85) ainda precisam ser reconferidos pelo nosso código antes de virar valor de referência nos testes.

### Conflitos resolvidos

Em todos, vale a regra da Helena: ela é a fonte, e a Fonte 1 é a interpretação do colega.

- **C1 — TED da Ponte de outubro**
  - **Fonte 1 (F1-H08):** supunha que o TED automático da Ponte seria 50% do total do relatório (R$ 78.073,59 → R$ 39.036,80). Registrava preventivamente uma diferença de R$ 506,65 frente à NF (R$ 39.543,45), com data de 06/10 sem origem indicada. Também havia uma discrepância não explicada: 917,03 − 410,94 = 506,09, não 506,65.
  - **Fonte 2 (R18, 22h33/22h34):** "Não supor desconto no repasse; conferir o TED de outubro é pendência da Helena."
  - **Decisão:** a projeção, a diferença de R$ 506,65 e a discrepância 506,65 × 506,09 saíram da seção 2. Fica só a pendência "conferir o TED da Ponte quando cair", e quem decide é a Helena.
  - **Motivo:** a Helena proibiu supor desconto no repasse; a projeção era exatamente essa suposição.
- **C2 — Devolução de PIX da Mundo Aberto (L65, +R$ 12.400,00)**
  - **Fonte 1 (F1-H10):** descrevia como "estorno bancário parcial de repasse enviado ao lojista", recompondo a obrigação de repasse.
  - **Fonte 2 (R20, 20h49):** "repasse que voltou, motivo desconhecido".
  - **Decisão:** a descrição passa a ser "repasse que voltou, motivo desconhecido". A classificação continua 2.1.01.001, com a pendência do motivo.
  - **Motivo:** "estorno parcial" afirmava uma causa que a Helena disse não conhecer.
- **C3 — Saldo zero de comissão de checkout**
  - **Fonte 1 (F1-H07):** saldo zero ou negativo não emitia NF, mas só o negativo ia para pendencias.csv.
  - **Fonte 2 (R06, 20h47):** "Zero ou negativo não emite nota e vira pendência da Helena."
  - **Decisão:** saldo de comissão de checkout zero OU negativo não emite nota e vira pendência.
  - **Motivo:** é a regra literal da Helena.

### Pendências resolvidas

- **IOF (4.3.01):** deixou de ser premissa do colega. É aplicação de R19 (Helena às 21h14: "além desses, nada estava provisionado") e vai direto para a despesa 4.3.01.

---

## 5. Decisões de formato

### Saída (CLAUDE.md)

- CSV com `;` como separador, ponto decimal, datas AAAA-MM-DD.
- **CNPJ:** sempre 14 dígitos, sem pontuação, com zeros à esquerda (`zfill(14)`). Isso vem de F1-H04: na planilha de taxas, os CNPJs de Fluente Idiomas Online Ltda (03229837000103) e Campus Global Ltda (08780784000120) estão como inteiros de 13 dígitos. A função `cnpj14` já trata isso.
- **Campos fixos:**
  - linha_negocio: CHECKOUT | REMESSA
  - banco: AURORA | MERIDIANO
  - metodo: REGRA | IA | HUMANO
  - confianca: de 0 a 1
- **Valores:** dinheiro em `Decimal` com 2 casas e ROUND_HALF_UP, linha a linha (R02). Taxas em pontos percentuais.

### Referências de origem (ref_origem)

- ref_origem do Aurora = linha física do arquivo, contando a partir de 1 (primeiro lançamento = L9), sem zeros à esquerda; aguardando confirmação no #hackathon-duvidas.
  - Conferido contra `ler_aurora`: os 84 lançamentos vão de L9 a L92. As referências antigas por posição (L042, L057, L084) viraram L50, L65 e L92 (posição + 8).

### Encoding dos arquivos de entrada (bytes conferidos em 16/10/2026)

O HIPOTESES.md da Fonte 1 não cita encoding. Quem cita é o CLAUDE.md do colega em `origin/main`: Aurora UTF-8, OFX cp1252, plano de contas cp1252. Conferimos os bytes reais dos arquivos de `dados/2026-09/`:

| arquivo | resultado | encoding a usar |
|---------|-----------|-----------------|
| Orbe CSV | só ASCII (0 bytes > 127) | `utf-8` explícito; o resultado é o mesmo em cp1252 |
| E-mail da Ponte (.eml) | só ASCII; o XLSX está em base64 | `ascii`/`utf-8`; o anexo é binário |
| Plano de contas CSV | UTF-8 inválido (falha no byte 320); cp1252 válido | `cp1252`, **confirmado** |
| Extrato Aurora CSV | UTF-8 válido, sem BOM; acentos como pares UTF-8 (ex.: "Jurídica", "Agência", "lançamentos") | `utf-8`, **confirmado** |
| Extrato Meridiano OFX | o cabeçalho declara `ENCODING:USASCII` e `CHARSET:1252`. UTF-8 inválido (falha no byte 924); cp1252 válido. Os 27 bytes > 127 são 0xC2 = "Â" (INTERCÂMBIO) e 0xC9 = "É" (AÉREA), letras corretas em cp1252. Não há U+FFFD nem sequência de UTF-8 corrompido | `cp1252`, **confirmado** |

- **Correção da descrição inicial do OFX:** a descrição que usamos no começo ("declara CHARSET 1252, mas os bytes são UTF-8 com caracteres já corrompidos") **não se confirma nos bytes**. O arquivo é cp1252 coerente com o cabeçalho.
- **Campos cortados no OFX:** alguns MEMO terminam no meio da palavra (ex.: "INTERCÂMB"). É corte de tamanho do campo, não problema de encoding.
