# CLAUDE.md — Diretrizes Oficiais do Projeto (Desafio Barte AI: Case Tarvo)

## 1. Contexto e Objetivo da Missão
Este repositório resolve o case **"Tarvo: o mês que só fecha na cabeça de quem fecha"** (Fechamento Financeiro de Setembro/2026 da **Tarvo Pagamentos Ltda**, CNPJ `84.626.315/0001-39`).
A Tarvo opera duas linhas de receita para agências de intercâmbio, escolas de idiomas e turismo educacional:
1. **Checkout (Cartão/PIX)** via adquirente **Orbe Adquirência S.A.** (`99.876.669/0001-09`) e conta no **Banco Aurora** (`Ag 0318 / CC 4471-0`).
2. **Remessas Internacionais (Câmbio)** via parceira **Ponte Câmbio S.A.** (`75.374.179/0001-46`) e conta no **Banco Meridiano** (`Ag 0091 / CC 90233-5`).

> **FONTE DA VERDADE:** Todas as regras abaixo foram confirmadas oficialmente pela **`Helena, financeiro da Tarvo`** no canal de dúvidas do hackathon e validadas matematicamente em Python (`Decimal`) sobre os arquivos de `dados/` (revalidação completa em `16/10/2026`). O formato de saída segue o documento oficial `01_instrucoes_participantes.docx` — ele prevalece sobre qualquer outra fonte.

---

## 2. Regras Inegociáveis de Arquitetura e Formatação
1. **Determinismo Financeiro Absoluto (`Decimal` + `ROUND_HALF_UP`):**
   - **PROIBIDO** usar LLM para somar valores, calcular percentuais ou arredondar centavos. Toda a matemática deve usar `decimal.Decimal` em Python.
   - **Regra Oficial de Arredondamento da Helena:** Arredondamento comum para o centavo (`0.01`), meio centavo vai para cima afastando do zero (`ROUND_HALF_UP`: `0.005 -> 0.01` e `-0.005 -> -0.01`), aplicado **linha por linha (por operação/transação)** antes de somar.
2. **Padrão Estrito dos 6 CSVs em `saida/` (parte da correção é automática):**
   - Codificação: **`UTF-8`** (sem BOM).
   - Separador de colunas: **ponto e vírgula (`;`)**.
   - Valores em R$: **ponto (`.`) decimal** com **2 casas** (`1234.56`), **sem separador de milhar** e **sem `R$`**.
   - Colunas `*_pct`: **pontos percentuais** com ponto decimal, sem `%` (`2.49` = 2,49%; spread de remessa com até 4 casas, ex. `1.5007`).
   - Datas: **`AAAA-MM-DD`** (ex: `2026-09-30`).
   - CNPJs: **14 dígitos numéricos com zero à esquerda preservado** (`str.zfill(14)`, sem pontos, barras ou traços). *Atenção:* na planilha Excel, `Fluente Idiomas` (`03229837000103`) e `Campus Global` (`08780784000120`) estão salvos como inteiros de 13 dígitos — sempre aplicar `.zfill(14)`.
   - Todo número de saída tem `id_saida` e é rastreável em `rastro.csv`: **a soma de `valor` por `id_saida` no rastro tem que bater ao centavo com o número reportado.**
3. **Arquivos de Entrada em `dados/` (Nomes e Encodings Reais):**
   - `dados/01_orbe_relatorio_comissoes_set2026.csv` (`utf-8`, sep `;`, decimal `,`, `1.943` linhas: `1.840` vendas, `59` estornos, `38` antecipações, `6` reversões; `22` ECs).
   - `dados/02_tabela_taxas_contratadas.xlsx` (`openpyxl`, aba ativa `'Taxas vigentes'`, cabeçalho na linha `5`; ignorar aba `'ANTIGO 2025 - nao usar'`; taxas ora fração `0.0259`, ora texto `'2,59%'`).
   - `dados/03_email_ponte_cambio_relatorio_set2026.eml` (extrair o anexo `.xlsx` via biblioteca padrão `email`; `skiprows=4`, `233` linhas brutas de operação `PC-`, `232` números únicos; ignorar rodapé de totais e aba `Resumo`).
   - `dados/04_plano_de_contas_fenix_erp.csv` (**encoding `cp1252`**, sep `;`, `52` contas, `32` analíticas com `ACEITA_LANCTO = S`).
   - `dados/05a_extrato_banco_aurora_cc4471_set2026.csv` (`utf-8`, sep `;`, decimal `,`, milhar `.`). **`84` lançamentos nas linhas físicas `9` a `92`** (linha `7` = cabeçalho, linha `8` = `SALDO ANTERIOR`, linha `94` = `SALDO FINAL`, linha `95` = rodapé). **`ref_origem` = número da linha física: `L9` … `L92`** (instrução oficial).
   - `dados/05b_extrato_banco_meridiano_cc90233_set2026.ofx` (**encoding `cp1252`** — bytes `C9`=`É`, `C2`=`Â` conferidos; SGML sem tags de fechamento; `100` blocos `<STMTTRN>`; **`ref_origem` = `FITID`**, `MRD2026090003` a `MRD2026090696`).

---

## 3. Regras de Negócio Oficiais (Confirmadas pela Helena no Slack até 22h35)

### 3.1. Mapeamento de Lojistas e ECs (`02_tabela_taxas_contratadas.xlsx` vs. Orbe)
* **Chave de casamento:** sempre `cod_estabelecimento` (Orbe) e `CNPJ` (planilha, Ponte). Nome é só evidência — nunca chave.
* **3 ECs sem código na planilha vigente (confirmados pela Helena — R07):**
  * `EC 1043300981` (`HORIZONTE INTERCAMBIO`) $\rightarrow$ **Novo Horizonte Intercambio** (`CNPJ 66564512000199`).
  * `EC 1043396662` (`HORIZONTE VIAGENS TURISMO`) $\rightarrow$ **Horizonte Viagens** (`CNPJ 78576234000179`).
  * `EC 1038867654` (`KIWI EXPERIENCE TURISMO`) $\rightarrow$ **Kiwi Experience** (`CNPJ 07752116000126`).
* **`Atlas Idiomas` (`EC 1076801732`, CNPJ `39566044000119` na aba 2025 — R08):**
  * Começou a transacionar em `10/09/2026` (`57` transações, `R$ 262.138,61` brutos, `R$ 7.876,05` de taxa cobrada pela Orbe), mas **não possui contrato assinado na aba vigente**. A Tarvo já repassou `R$ 249.301,77` à Atlas por PIX no Aurora (`L34` e `L60`).
  * **Ordem expressa da Helena:** *"Não sei qual taxa vale. Não fatura a Atlas até o comercial confirmar."*
  * **Tratamento:** **NÃO emitir NF** para a Atlas em `notas_a_emitir.csv`, **NÃO gerar linhas em `divergencias_taxa.csv`** (pois não há taxa contratada confirmada) e registrar em `pendencias.csv` para confirmação do Comercial (Diego).
* **`Globo Trotter Viagens Ltda` (`EC 1157874034`, `22348118000148`):** Inativo desde jul/26, sem transações em setembro.
* **Lojistas só de remessa (sem EC):** `Ponte Aérea Estudantil` (`95739378000118`) e `Nórdica Educação Internacional` (`14760206000124`, spread `1,25%`).

### 3.2. Motor 1 — Checkout (`01_orbe_relatorio_comissoes_set2026.csv`)
* **Base da Comissão e da NF de Checkout = TAXA CONTRATADA INTEIRA (R01, R02, R03, R22):**
  * A comissão da Tarvo é a taxa contratada inteira (sem desconto de custo de adquirente), calculada como `comissao_contratada = ROUND_HALF_UP(valor_bruto * taxa_contratada_pct / 100, 2)` e somada linha a linha.
  * A Orbe **trunca** centavos em todas as `1.943` linhas (`R$ 608,88 × 2,69% = 16,3788` $\rightarrow$ Orbe grava `16,37`; Tarvo arredonda para `16,38`). Por isso a soma de `valor_taxa` da Orbe (`R$ 231.880,36`) **não** é a comissão da Tarvo.
  * **Regra da Helena para Divergências de Checkout:** Diferença de 1 centavo causada pelo truncamento da Orbe **NÃO É DIVERGÊNCIA**. Só existe divergência quando `taxa_aplicada_pct != taxa_contratada_pct`. O valor da divergência é `ROUND_HALF_UP(valor_bruto * (taxa_aplicada_pct - taxa_contratada_pct) / 100, 2)`.
  * **Valores de referência (sem Atlas):** comissão contratada total `R$ 207.039,73` (vendas `195.091,51` + antecipações `22.709,25` − estornos `6.983,25` − reversões `3.777,78`); **`20` NFs de Checkout somando `R$ 207.045,23`** (todos os lojistas com saldo > 0; fica de fora só a Casa do Estudante com `-R$ 5,50`).
* **Condição Especial Oculta — `Casa do Estudante Viagens Ltda` (`EC 1018325654`, `00520815000100` — R10, R04, R06):**
  * Comentário na célula `A13` (*"conversar com Diego (comercial) sobre condição especial"*).
  * **Regra revelada pela Helena:** *"A Casa do Estudante tem tarifa zerada no checkout de setembro a dezembro, por acordo do comercial para segurar o cliente. Vale para MDR e antecipação. Remessa segue normal. Ninguém avisou a Orbe, então ela cobrou. O que foi cobrado eu devolvo ao lojista, junto com o comercial."*
  * **Detalhe cirúrgico da transação `TX88445133`:** Em `07/09/2026`, a Casa do Estudante teve um `ESTORNO` de Débito (`-R$ 369,39`) referente a uma venda original de **`21/08/2026`** (`data_venda_original = 21/08/2026`). Pela regra da Helena (`R04`: *"A taxa usada no estorno é a que valia na data da venda original"*), em agosto/2026 valia `1,49%` (`-R$ 5,50`), enquanto todas as **118** transações de setembro (`113` vendas, `4` antecipações, `1` estorno de venda de setembro) têm taxa contratada `0,00%` (`R$ 0,00`). Isso deixa a Casa do Estudante com saldo de comissão de Checkout negativo (`-R$ 5,50`): pela regra `R06` (*"Zero ou negativo não emite nota. O negativo não passa para o mês seguinte automaticamente. Eu trato com o lojista, então coloca como pendência para mim"*), **não se emite NF de Checkout** e tanto o saldo zero/negativo quanto a devolução das cobranças indevidas da Orbe (`118` linhas somando **`R$ 15.397,42`** pelo cálculo arredondado linha a linha / `R$ 15.396,77` cobrados pela Orbe nessas `118` linhas / `R$ 15.391,27` líquido nas `119` linhas) entram em `divergencias_taxa.csv` + `pendencias.csv`.
* **Estornos (`ESTORNO`), Antecipações (`ANTECIPACAO`) e Reversões (`REVERSAO ANTECIPACAO` — R04, R05, R06):**
  * Estornos ocorridos em setembro de vendas de agosto (`9` casos) **entram no fechamento de setembro**, abatendo a comissão pela **taxa contratada vigente na `data_venda_original`**.
  * `ANTECIPACAO` (`2,10%` contratado, exceto Casa do Estudante `0,00%`) e `REVERSAO ANTECIPACAO` (que anula a taxa da antecipação referenciada em `id_referencia`; as `6` reversões batem com as antecipações originais) entram na **mesma NF de Checkout** do lojista. Antecipação não tem modalidade/parcelas no arquivo.
  * Qualquer lojista com saldo mensal de comissão **zero ou negativo** não emite NF e entra obrigatoriamente em `pendencias.csv` para a Helena.
* **As 3 Divergências Reais de Taxa no Checkout (`divergencias_taxa.csv`, `210` linhas):**
  1. **`Casa do Estudante` (`EC 1018325654`):** Cobrança indevida pela Orbe em setembro quando a tarifa acordada era `0,00%` (`118` transações = **`R$ 15.397,42`** arredondado por linha).
  2. **`Rota Global Intercâmbio Ltda` (`EC 1074504011` — R09):** Não houve reajuste contratual em 2026. A partir de `12/09/2026`, a Orbe cobrou `+0,50 p.p.` a mais em Crédito à Vista (`2,49% -> 2,99%`), Créd. 2-6x (`2,99% -> 3,49%`) e Créd. 7-12x (`3,59% -> 4,09%`) em **`87` transações** (`83` vendas e `4` estornos), gerando divergência líquida de **`R$ 1.546,28`**. **Débito (`1,49%`) e PIX (`0,89%`) NÃO mudaram.**
  3. **`Escola Bridge de Idiomas Ltda` (`EC 1075624862`):** Renegociou Crédito à Vista de `2,59%` (até `14/09/2026`) para `2,19%` (a partir de `15/09/2026`). Entre `15/09` e `18/09`, a Orbe continuou aplicando `2,59%` em **`5` vendas** (`TX88428053`, `TX88429199`, `TX88428930`, `TX88429931`, `TX88431123`), gerando divergência de **`R$ 29,95`**.

### 3.3. Motor 2 — Remessas de Câmbio (`03_email_ponte_cambio_relatorio_set2026.eml`)
* **Base da Comissão e da NF de Remessa = 50% DO SPREAD REALIZADO (R11 a R18):**
  * Na remessa, quem paga a Tarvo é a **Ponte Câmbio S.A.** (`75374179000146`). Emite-se **uma única NF de intermediação de câmbio** contra a Ponte Câmbio pelo total da participação da Tarvo no mês. O e-mail de `02/10` condiciona o repasse de `06/10/2026` a essa NF.
  * **Cálculo Oficial da Helena (`R11`):** Em cada operação válida, a comissão da Tarvo é `ROUND_HALF_UP(Spread_BRL * 0.50, 2)`, somada operação por operação.
  * Spread em branco ou escrito `"padrão"` na planilha contratada vale **`1,50%` sobre a PTAX de referência** (`PTAX Ref. × Valor ME`).
* **O que FICA DE FORA da Comissão e da NF de Remessa (`R12`, `R13`, `R18`):**
  1. **Linha duplicada `PC-0926-0162` (`Bagagem Livre Turismo`, `50900987000179`, contratada em `22/09`, `Spread R$ 821,88`):** O número da operação é único; a segunda linha (Observação `"reprocessada"`) é duplicata e deve ser excluída do cálculo (contar `PC-0926-0162` apenas 1 vez) e registrada em `pendencias.csv` na lista para a Ponte corrigir o relatório (`R18`). O Meridiano confirma: as `21` TEDs `LIQ OPERACOES` (`R$ 5.611.447,12`) só fecham com a duplicata excluída.
  2. **4 Operações com Spread Negativo (`PC-0926-0210` Ponte Aérea, `PC-0926-0326` Canguru, `PC-0926-0491` Dublin Hub, `PC-0926-0545` Novo Horizonte; soma `Spread R$ = -R$ 1.834,05`):** Marcadas com `"Taxa travada no pedido (D-1)"`. **Ordem da Helena (`R12`):** *"Não aceito. A trava vale 2 horas pelo contrato, e essas passaram do prazo. Fica fora da comissão e da nota, e eu contesto."* Excluir das comissões e da NF, e listar em `divergencias_taxa.csv` e `pendencias.csv`.
* **O que ENTRA normalmente em Setembro (`228` operações válidas $\rightarrow$ NF Ponte = `R$ 39.543,45`):**
  1. Operações com status `"APROVADO C/ RESSALVA"` entram normalmente (`R11`) — `16` operações, `R$ 4.829,37` de spread.
  2. Operações contratadas em `30/09/2026` e liquidadas em `01/10/2026` **entram em setembro** (*"vale a data de contratação"* — `R11`) — são **`6`**: `PC-0926-0002`, `PC-0926-0110`, `PC-0926-0249`, `PC-0926-0384`, `PC-0926-0549`, `PC-0926-0566` (`R$ 2.078,71` de spread).
  3. **`Mundo Aberto` (`17217888000111`) — 23 operações de câmbio (`R15`, `R16`):** Renegociou spread para `1,20%` em jul/2026, mas a Ponte aplicou `~1,50%`. **Ordem da Helena (`R16`):** O valor realizado (`~1,50%`) **ENTRA na comissão e na NF de setembro contra a Ponte** (pois é o que a Ponte repassará agora), mas as **23 operações** entram em `divergencias_taxa.csv` pelo **valor cheio pago a mais pelo lojista (`R$ 1.418,85` = `ROUND_HALF_UP((Spread % aplicado − 1,20%) × PTAX Ref. × Valor ME)` por operação)** e em `pendencias.csv` para contestação com a Ponte. *(Base `Valor R$` em vez de `PTAX × ME` daria `R$ 1.440,14` — não usar.)*
  4. **Filtro de Tolerância de PTAX (`0,01 p.p.`):** Oscilações de `±0,002 p.p.` no `Spread %` dos demais lojistas (ex: `1,4984%` a `1,5015%` para taxa de `1,50%`) decorrem de arredondamento da taxa final de câmbio em 4 casas decimais e **não devem ser reportadas como divergência** (adotar tolerância de `0,01 p.p.`). Conferido: com essa tolerância, só a Mundo Aberto diverge.
  5. **Contestação e Conferência do TED de Outubro (`R18` — Respostas da Helena às 22h33/22h34):**
     * A Helena confirmou que **ainda não abriu a contestação** e que estamos **dentro do prazo de 5 dias úteis**: devemos listar em `pendencias.csv` as contestações com valor e códigos das operações (Mundo Aberto `23` ops `R$ 1.418,85`, 4 spreads negativos `-R$ 1.834,05` de spread realizado, e duplicata `PC-0926-0162` `R$ 821,88`) + uma pendência para a Helena **conferir o TED de outubro quando cair**, **sem supor que a Ponte descontará valor do repasse antes da contestação**.
     * *(Nota matemática de reconciliação para testes: a soma de `ROUND_HALF_UP(Spread_BRL * 0.50, 2)` nas `228` operações válidas é `R$ 39.543,45`, enquanto `50%` da soma sem arredondar por linha `R$ 79.085,76 / 2` seria `R$ 39.542,88` — diferença de `R$ 0,57` decorrente do arredondamento por operação exigido em `R11`).*

### 3.4. Motor 3 — Classificação Contábil dos Extratos (`lancamentos_classificados.csv`)
* **Total de Lançamentos:** **`184`** linhas (`84` do Banco Aurora `L9` a `L92` + `100` do Banco Meridiano `MRD2026090003` a `MRD2026090696`), cada uma exatamente uma vez e sempre em conta analítica.
* **Fluxo Orbe × Banco Aurora e Conta Garantida (`R21` — Resposta da Helena às 22h34):**
  * A Orbe deposita tudo no Banco Aurora (Débito e PIX em D+1; Crédito e parcelado ao longo dos meses seguintes conforme as parcelas). O saldo negativo do Aurora (que chega a `-R$ 2.289.532,94` e fecha em `-R$ 1.920.088,60`) é a **conta garantida** usada pela Tarvo para pagar os lojistas antes da liquidação da Orbe. **Conciliar Orbe × banco parcela por parcela está fora do escopo**: basta classificar os `21` créditos da Orbe (`R$ 3.557.246,29`) em `1.1.03.001`.
* **Regra Oficial da Helena para `conta_codigo` (`R19`, `R20`):** Deve ser a **contrapartida contábil analítica (`ACEITA_LANCTO = S`)** da movimentação bancária:
  1. **Obrigações e Recebíveis de Agosto JÁ PROVISIONADOS (baixam Passivo/Ativo, NÃO vão para Despesa/Receita de setembro):**
     * `PAGTO SALARIOS - FOLHA 08/2026` (`L15`, `-184.732,18`) $\rightarrow$ `2.1.04.001` (*Salários a pagar*).
     * `PAGTO ISS SAO PAULO DAMSP 08/2026` (`L42`, `-21.877,40`) $\rightarrow$ `2.1.03.003` (*ISS a recolher*).
     * `GPS INSS 08/2026` (`L54`, `-51.320,66`) $\rightarrow$ `2.1.04.002` (*INSS a recolher*).
     * `GRF FGTS 08/2026` (`L55`, `-14.778,57`) $\rightarrow$ `2.1.04.003` (*FGTS a recolher*).
     * `DEBITO DARF 0561 IRRF` (`L57`, `-22.104,35`) $\rightarrow$ `2.1.03.004` (*IRRF a recolher*).
     * `DEBITO DARF 8109 PIS` (`L86`, `-9.811,20`) $\rightarrow$ `2.1.03.001` (*PIS a recolher*).
     * `DEBITO DARF 2172 COFINS` (`L87`, `-45.282,46`) $\rightarrow$ `2.1.03.002` (*COFINS a recolher*).
     * `TED RECEB PONTE CAMBIO SA REPASSE COMISSAO 08/2026` (`MRD2026090132`, `+61.884,12`) $\rightarrow$ `1.1.03.002` (*Comissões de intermediação a receber - câmbio*).
  2. **Movimentações Operacionais e de Tesouraria:**
     * `TED RECEBIDA ... ORBE ADQUIRENCIA SA` (Aurora, `21` lançamentos) $\rightarrow$ `1.1.03.001` (*Recebíveis de adquirente - Orbe*).
     * `PIX ENVIADO [LOJISTA]` (Aurora, `44` lançamentos — exceto Contabilidade Exata) $\rightarrow$ `2.1.01.001` (*Repasses a lojistas a pagar*).
     * `PIX RECEB [LOJISTA]` (Meridiano, `64` lançamentos) $\rightarrow$ `2.1.02.001` (*Recursos de lojistas para remessas a liquidar*).
     * `TED ENVIADA PONTE CAMBIO SA LIQ OPERACOES` (Meridiano, `21` lançamentos) $\rightarrow$ `2.1.02.001` (*Recursos de lojistas para remessas a liquidar*).
     * `TRANSF ENTRE CONTAS P/ BCO MERIDIANO` (Aurora, `4`) e `TED RECEBIDA TARVO PAGAMENTOS LTDA - MESMA TITULARIDADE` (Meridiano, `3`) $\rightarrow$ `1.1.09.001` (*Transferências entre contas próprias*).
     * `APLICACAO AUTOMATICA CDB DI` e `RESGATE AUTOMATICO CDB DI` (Meridiano) $\rightarrow$ `1.1.02.001` (*Aplicação automática Meridiano*).
     * `RENDIMENTO APLIC AUTOMATICA` (`MRD2026090680`, `+3.912,66`, Meridiano) $\rightarrow$ `3.2.01` (*Rendimentos de aplicações*).
  3. **Despesas de Setembro NÃO PROVISIONADAS (entram direto na Despesa `4.x`):**
     * `TAR PACOTE SERVICOS PJ` (`L10`), `TAR TED/PIX AVULSAS` (`L90`), `TARIFA MANUTENCAO CONTA PJ` (`MRD2026090103`), `TARIFA PACOTE CAMBIO` (`MRD2026090696`) $\rightarrow$ `4.2.01` (*Tarifas bancárias*).
     * `BOLETO CONDOMINIO ED. FARIA LIMA 3311` (`L16`, `-28.450,00`) $\rightarrow$ `4.2.02` (*Aluguel e condomínio*).
     * `DEB AUT AMAZON WEB SERVICES BR` (`L47`, `-41.208,77`) $\rightarrow$ `4.2.03` (*Cloud e infraestrutura*).
     * `CARTAO PJ - GOOGLE WORKSPACE` (`L48`, `-2.210,00`) $\rightarrow$ `4.2.04` (*Softwares e assinaturas*).
     * `SEGURO EMPRESARIAL PARC 09/12` (`MRD2026090292`, `-1.830,44`, Meridiano) $\rightarrow$ `4.2.05` (*Seguros*).
     * `PIX ENVIADO CONTABILIDADE EXATA LTDA` (`L53`, `-6.800,00`) $\rightarrow$ `4.2.06` (*Serviços contábeis e jurídicos*).
     * `IOF S/ OPERACAO CREDITO` (`MRD2026090586`, `-48,21`, Meridiano) $\rightarrow$ `4.3.01` (*IOF*).
  4. **Os 4 Casos Especiais / Anomalias Bancárias (+ `pendencias.csv` — R20):**
     * `16/09` (`L50`) `PIX RECEBIDO 38686002000180 SEM IDENTIFICACAO` (`+7.350,00`): Não é receita até identificar $\rightarrow$ `1.1.09.002` (*Créditos não identificados*) + item em `pendencias.csv`.
     * `23/09` (`L65`) `DEVOLUCAO PIX - MUNDO ABERTO INTERC` (`+12.400,00`): PIX de repasse que voltou por motivo desconhecido (`R20`) $\rightarrow$ `2.1.01.001` (*Repasses a lojistas a pagar*, mantendo a obrigação em aberto até apuração do motivo) + item em `pendencias.csv`.
     * `30/09` (`L92`) `TRANSF ENTRE CONTAS P/ BCO MERIDIANO` (`-300.000,00`, sai do Aurora em `30/09` e cai no Meridiano em `01/10` — `R20`) $\rightarrow$ `1.1.09.001` (*Transferências entre contas próprias*) + item em `pendencias.csv` para conciliação em `01/10`. As outras 3 transferências (`R$ 1.150.000,00`) têm par no Meridiano.
     * `17/09` (`MRD2026090425`, Meridiano) `PIX RECEB PONTE AEREA ESTUDANTIL L` (`+R$ 18.240,00`): **Prova matemática exata:** Na planilha da Ponte Câmbio, as `15` operações da `Ponte Aérea Estudantil` (`95739378000118`) somam `Valor R$ (450.536,99) + IOF R$ (1.712,04) = R$ 452.249,03`, valor que fecha **ao centavo** com a soma dos **5 PIX semanais de terça-feira** recebidos da Ponte Aérea no Meridiano (`77.595,09 + 148.766,45 + 183.631,12 + 14.091,03 + 28.165,34 = R$ 452.249,03`). No total, os `64` PIX recebidos (`R$ 5.629.687,12`) menos este PIX dão exatamente `Valor R$ + IOF R$` das `232` operações únicas (`R$ 5.611.447,12`). Portanto, o PIX de `17/09` não possui operação de câmbio correspondente em setembro $\rightarrow$ classificar em `2.1.02.001` e registrar em `pendencias.csv`!

---

## 4. Schemas dos 6 Arquivos em `saida/` (instrução oficial)

As colunas abaixo, nesta ordem, são **obrigatórias** (correção automática). Colunas extras são permitidas e vêm **depois** das obrigatórias.

* `linha_negocio`: `CHECKOUT` ou `REMESSA`. `banco`: `AURORA` ou `MERIDIANO`. `metodo`: `REGRA`, `IA` ou `HUMANO`. `confianca`: de `0` a `1`.
* `ref_origem`: `id_transacao` (Orbe), `Nº Operação` (Ponte), linha física do Aurora (`L9` … `L92`), `FITID` (Meridiano).
* `id_saida`: identificador único da linha dentro do arquivo (ex.: `COM-0001`, `DIV-0001`, `NF-0001`, `LAN-0001`, `PEN-0001`).

1. **`saida/comissoes_por_lojista.csv`** — uma linha por lojista × linha de negócio.
   `id_saida;cnpj;lojista;linha_negocio;comissao_brl`
   - Extras sugeridos: `qtd_operacoes;valor_bruto_brl`.
   - Rastro: cada transação Orbe / operação Ponte que compõe a comissão, com sua comissão por linha.
2. **`saida/divergencias_taxa.csv`** — uma linha por transação/operação divergente.
   `id_saida;cnpj;linha_negocio;ref_origem;taxa_contratada_pct;taxa_aplicada_pct;diferenca_brl`
   - Extras sugeridos: `data;lojista;valor_base_brl;descricao`.
3. **`saida/notas_a_emitir.csv`**
   `id_saida;tomador_cnpj;tomador;linha_negocio;valor_brl;discriminacao`
   - Extras sugeridos: `competencia` (`2026-09`).
   - `CHECKOUT`: uma NF por lojista com saldo de comissão contratada `> 0` em `2026-09` — `20` NFs, `R$ 207.045,23` (exclui `Atlas Idiomas` sem contrato confirmado e `Casa do Estudante` com saldo `-R$ 5,50`).
   - `REMESSA`: **uma única NF** cujo tomador é a **Ponte Câmbio S.A.** (`75374179000146`), `valor_brl = 39543.45`.
4. **`saida/lancamentos_classificados.csv`** — `184` linhas.
   `id_saida;banco;ref_origem;data;descricao;valor;conta_codigo;metodo;confianca`
   - Extras sugeridos: `conta_descricao;justificativa`.
5. **`saida/pendencias.csv`**
   `id_saida;tipo;ref_origem;valor_brl;motivo;quem_decide`
   - Extras sugeridos: `cnpj;lojista;acao_sugerida`.
   - `quem_decide`: `Helena (financeiro)`, `Diego (comercial)` ou `Bia (planilha de taxas)`.
6. **`saida/rastro.csv`** — liga cada número de saída às linhas de origem.
   `id_saida;arquivo_origem;ref_origem;valor`
   - **Para cada `id_saida`, `soma(valor) == número reportado`, ao centavo.**

---

## 5. Estrutura do Repositório, Donos e Comandos
```text
├── CLAUDE.md                  # Este guia mestre com as regras oficiais da Helena
├── PLANO_17-10.md             # Divisão do trabalho, cronograma e checklist de entrega
├── README.md                  # Instruções de execução passo a passo
├── HIPOTESES.md               # Premissas e decisões auditadas
├── PROMPTS/                   # Transcripts das sessões + MOMENTOS.md
├── config/                    # Regras que mudam de mês para mês (checkout/remessa/bancos.toml)
├── dados/                     # Arquivos brutos originais do case (SOMENTE LEITURA)
├── saida/                     # Os 6 CSVs gerados pelo pipeline (inclui rastro.csv)
├── src/
│   ├── main.py                # Orquestrador: lê, roda os 3 módulos, grava saida/   (C)
│   ├── core/                  # Dinheiro (Decimal), contrato de saída, escrita + rastro (C, compartilhado)
│   ├── leitores/              # As 6 fontes como chegam, prontas e testadas          (C, compartilhado)
│   ├── checkout/motor.py      # Comissão, divergências e notas do checkout          (Pessoa A)
│   ├── remessa/motor.py       # Comissão, divergências e nota da Ponte               (Pessoa B)
│   └── bancos/motor.py        # Classificação dos extratos + pendências bancárias    (Pessoa C)
└── tests/                     # test_<módulo>.py = critério de aceite de cada pessoa
```
* **Executar pipeline completo:** `python -m src.main --entrada dados --saida saida --competencia 2026-09`
* **Executar testes de auditoria:** `python -m unittest discover -s tests`

### Regras de trabalho em equipe (valem para toda sessão do Claude Code)
1. **Cada pessoa edita só o próprio módulo**, o próprio `config/<módulo>.toml` e o próprio `tests/test_<módulo>.py`. Pergunte qual pessoa está usando a sessão antes de editar.
2. **`src/core/` e `src/leitores/` são compartilhados:** só mude com pedido explícito, num commit separado.
3. **Módulos não importam uns aos outros.** Eles recebem `Dados` (de `src/leitores`) e devolvem `ResultadoModulo` (de `src/core/modelos.py`). Ninguém escreve CSV direto.
4. **Todo número leva `rastro`** (`ItemRastro` por linha de origem) e a soma do rastro tem que ser o número reportado; `core/saida.py` quebra se não for.
5. **Nenhum valor de setembro fixo no código:** regras e exceções vão em `config/*.toml`, com a fonte (Slack) citada.
6. **Pronto = teste do módulo verde** com os valores de aceite (seção 3).
