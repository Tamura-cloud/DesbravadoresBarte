# HIPOTESES.md — Premissas Contábeis, Regras da Helena e Provas Matemáticas (Setembro/2026)

Este documento consolida todas as regras de negócio confirmadas pela **Helena (financeiro da Tarvo)** no canal oficial do Slack (até `22h35` de `16/10/2026`), as premissas do time e as **provas matemáticas exatas** (auditadas em Python sobre os arquivos de `dados/`), resolvendo integralmente os pontos levantados na branch `origin/pix` (`CONFLITO C1`, `C2`, `C3` e verificações numéricas).

> **Revisão de `16/10/2026` (recálculo independente em Python/`Decimal`):** corrigidos (1) divergência da Casa do Estudante `15.397,32` → **`15.397,42`**; (2) Rota Global: o `+0,50 p.p.` foi em Crédito à Vista, 2-6x e 7-12x, **não em Débito**; (3) duplicata `PC-0926-0162` é da **Bagagem Livre**; (4) são **`6`** (não `3`) operações de `30/09` liquidadas em `01/10`; (5) Aurora tem **`84`** lançamentos (linhas `9` a `92`, total `184`), com `ref_origem` = linha física `L9…L92`; (6) `21` (não `19`) TEDs da Orbe; (7) incluído o `SEGURO EMPRESARIAL` (`4.2.05`), que não estava mapeado; (8) spread negativo da Novo Horizonte comparado com `1,40%`. Os schemas de saída foram alinhados à instrução oficial (6 CSVs, incluindo `rastro.csv`).

---

## 1. Mapeamento Cadastral, Contratos e Condições Comerciais

* **H01 — Vínculo dos 3 ECs sem código na aba `'Taxas vigentes'` (`R07`):**
  * Confirmado pela Helena às `20h24`:
    * `EC 1043300981` (`HORIZONTE INTERCAMBIO`) $\rightarrow$ **Novo Horizonte Intercambio** (`CNPJ 66564512000199`).
    * `EC 1043396662` (`HORIZONTE VIAGENS TURISMO`) $\rightarrow$ **Horizonte Viagens** (`CNPJ 78576234000179`).
    * `EC 1038867654` (`KIWI EXPERIENCE TURISMO`) $\rightarrow$ **Kiwi Experience** (`CNPJ 07752116000126`).
  * *Regra de pareamento no código:* casar sempre por `cod_estabelecimento` (Orbe) e `CNPJ` de 14 dígitos (planilha e Ponte), usando nome apenas como evidência.
* **H02 — `Atlas Idiomas Ltda` (`EC 1076801732`, `CNPJ 39566044000119` — `R08`):**
  * Começou a transacionar em `10/09/2026` (`57` transações, `R$ 262.138,61` brutos, `R$ 7.876,05` de taxa retida pela Orbe), mas consta apenas na aba histórica `'ANTIGO 2025 - nao usar'` sem contrato assinado na aba vigente.
  * **Decisão (`R08`):** Conforme orientação expressa da Helena (*"Não sei qual taxa vale. Não fatura a Atlas até o comercial confirmar"*), a Atlas Idiomas **não tem NF emitida em `notas_a_emitir.csv`**, não gera linhas em `divergencias_taxa.csv` (premissa técnica necessária pois, sem taxa contratada vigente, `taxa_aplicada − taxa_contratada` é indefinida) e é registrada em `pendencias.csv` para validação contratual junto ao Comercial (Diego).
* **H03 — Isenção (`0,00%`) da `Casa do Estudante Viagens Ltda` (`EC 1018325654`, `CNPJ 00520815000100` — `R10`, `R04`, `R06`):**
  * A célula `A13` da planilha vigente possui o comentário `"conversar com Diego (comercial) sobre condição especial"`. Conforme confirmação da Helena às `20h49` (`R10`), a Casa do Estudante possui **tarifa zerada (`0,00%`) no Checkout (MDR e Antecipação) de setembro a dezembro/2026** (mantendo-se o spread contratado normal de `1,50%` apenas em Remessas de Câmbio).
  * Como a Orbe não foi avisada, cobrou indevidamente `R$ 15.391,27` líquidos nas `119` movimentações do mês.
  * **Tratamento do Estorno de Venda de Agosto (`TX88445133` — linha física `433` da Orbe):** Em `07/09/2026`, ocorreu o estorno de débito `TX88445133` (`-R$ 369,39`) referente a uma venda realizada em **`21/08/2026`** (`data_venda_original = 21/08/2026`). Pela regra `R04` (*"A taxa usada é a que valia na data da venda original"*), em agosto/2026 (antes do acordo de setembro a dezembro) valia a taxa contratada da planilha desde `01/01/2026` (`1,49%`), gerando comissão contratada de **`-R$ 5,50`** em setembro (sem divergência de taxa nessa linha). As demais **`118`** transações de setembro (`113` vendas, `4` antecipações, `1` estorno de venda de setembro) têm taxa contratada `0,00%`, gerando **`R$ 15.397,42`** de divergência a devolver ao lojista pelo cálculo arredondado linha a linha (`R$ 15.396,77` retidos pela Orbe nessas `118` linhas).
  * **Resolução do `CONFLITO C3` (Saldo zero ou negativo):** Pela regra `R06` (*"Zero ou negativo não emite nota... coloca como pendência para mim"*), **tanto saldo zero quanto saldo negativo não emitem NF e ambos geram pendência para a Helena**. Na Casa do Estudante, o saldo líquido de comissão de Checkout em setembro é `-R$ 5,50` (negativo), não emitindo NF e indo obrigatoriamente para `pendencias.csv`.
* **H04 — Preservação de Zeros à Esquerda em CNPJs:**
  * Na planilha de taxas contratadas, os CNPJs de `Fluente Idiomas Online Ltda` (`03229837000103`) e `Campus Global Ltda` (`08780784000120`) estão gravados como inteiros de 13 dígitos. Todos os CNPJs são normalizados para `14` dígitos numéricos (`zfill(14)`).

---

## 2. Regras de Cálculo de Comissões, Arredondamento e Divergências

* **H05 — Arredondamento Padrão (`ROUND_HALF_UP`) Linha a Linha (`R02`, `R11`):**
  * Enquanto a Orbe trunca os centavos na segunda casa decimal, a Tarvo aplica **arredondamento comum para o centavo (`ROUND_HALF_UP`: `0,005 -> 0,01` e `-0,005 -> -0,01`) linha por linha (operação por operação)** antes de somar.
* **H06 — Base da Comissão e Divergências no Checkout (`R01`, `R03`, `R09`, `R22`):**
  * A comissão da Tarvo no Checkout é a **taxa contratada inteira** (sem desconto de custo da Orbe, conforme reiterado pela Helena em `R22`), calculada como `ROUND_HALF_UP(valor_bruto * taxa_contratada_pct / 100, 2)` por transação.
  * Diferenças de `R$ 0,01` causadas pelo truncamento da Orbe **não são divergência** (`R02`, `R03`).
  * Só entra em `divergencias_taxa.csv` quando `taxa_aplicada_pct != taxa_contratada_pct`, com valor `ROUND_HALF_UP(valor_bruto * (taxa_aplicada_pct - taxa_contratada_pct) / 100, 2)`. Casos em setembro (`210` transações com taxa divergente):
    1. **`Casa do Estudante` (`EC 1018325654`):** `118` transações de setembro cobradas pela Orbe durante vigência da tarifa `0,00%`, somando **`R$ 15.397,42`** (arredondado por linha).
    2. **`Rota Global Intercâmbio Ltda` (`EC 1074504011` — `R09`):** `87` transações (`83` vendas e `4` estornos) a partir de `12/09/2026` com `+0,50 p.p.` cobrados a mais pela Orbe sem alteração contratual — Crédito à Vista `2,49% -> 2,99%`, Créd. 2-6x `2,99% -> 3,49%`, Créd. 7-12x `3,59% -> 4,09%` (Débito `1,49%` e PIX `0,89%` não mudaram) —, somando diferença líquida de **`R$ 1.546,28`**.
    3. **`Escola Bridge de Idiomas Ltda` (`EC 1075624862`):** renegociou Crédito à Vista de `2,59%` (`até 14/09/2026`) para `2,19%` (`a partir de 15/09/2026`). Em **`5` vendas** de Crédito à Vista entre `15/09` e `18/09` (`TX88428053`, `TX88429199`, `TX88428930`, `TX88429931`, `TX88431123`), a Orbe aplicou `2,59%` em vez de `2,19%`, gerando divergência de **`R$ 29,95`**.
* **H07 — Estornos, Antecipações e Reversões no Checkout (`R04`, `R05`, `R06`):**
  * Estornos (`ESTORNO`) ocorridos em setembro (inclusive os `9` estornos de vendas de agosto) entram em setembro, abatendo a comissão pela taxa contratada vigente na `data_venda_original`.
  * `ANTECIPACAO` (`2,10%`, exceto Casa do Estudante `0,00%`) e `REVERSAO ANTECIPACAO` (que anula a taxa da antecipação referenciada em `id_referencia`) entram na **mesma Nota Fiscal mensal de Checkout** do lojista.
  * Saldo mensal zero ou negativo não emite NF e entra em `pendencias.csv` para a Helena.
* **H08 — Remessas de Câmbio (`REMESSA` — Ponte Câmbio — `R11` a `R18`):**
  * Na remessa, a comissão da Tarvo e a **Nota Fiscal única contra a Ponte Câmbio S.A. (`75374179000146`)** são **50% do `Spread R$` realizado**, arredondado (`ROUND_HALF_UP`) **operação por operação** (`R11`, `R17`).
  * Células de spread em branco ou `"padrão"` na planilha valem **`1,50%` sobre a PTAX de referência** (`PTAX Ref. × Valor ME` — `R14`).
  * **Operações Incluídas em Setembro (`228` operações válidas $\rightarrow$ NF Ponte Câmbio = `R$ 39.543,45`):**
    * As **`6`** operações contratadas em `30/09/2026` e liquidadas em `01/10/2026` (`PC-0926-0002`, `PC-0926-0110`, `PC-0926-0249`, `PC-0926-0384`, `PC-0926-0549`, `PC-0926-0566`; `R$ 2.078,71` de spread) entram em setembro pela data de contratação (`R11`).
    * Operações com status `"APROVADO C/ RESSALVA"` entram normalmente (`R11`).
    * **`Mundo Aberto` (`17217888000111` — `R15`, `R16`):** as **23 operações** em que a Ponte aplicou `~1,50%` em vez dos `1,20%` renegociados em jul/2026 **entram na comissão e na NF de setembro pelo valor realizado** (`R16`), são reportadas em `divergencias_taxa.csv` pelo **valor cheio pago a mais pelo lojista (`R$ 1.418,85` = `(Spread % aplicado − 1,20%) × PTAX × Valor ME` — `R15`)** e vão para `pendencias.csv` para contestação com a Ponte.
  * **Operações Excluídas da Comissão e da NF de Remessa (`R12`, `R13`, `R18`):**
    * **Duplicidade (`PC-0926-0162`, `Bagagem Livre Turismo`, `50900987000179`, contratada em `22/09` — `R13`, `R18`):** a segunda linha com mesmo número de operação (Observação `"reprocessada"`, `Spread R$ 821,88`) é descartada do cálculo e incluída em `pendencias.csv` na lista para a Ponte corrigir o relatório (`R18`).
    * **4 Operações com Spread Negativo (`PC-0926-0210`, `PC-0926-0326`, `PC-0926-0491`, `PC-0926-0545`, soma `Spread R$ = -R$ 1.834,05` — `R12`, `P02`):** decorrentes de `"Taxa travada no pedido (D-1)"` vencida (trava contratual vale 2 horas). Ficam fora da comissão e da NF, e entram em `divergencias_taxa.csv` (diferença contra o spread contratado de cada lojista: `1,50%` para Ponte Aérea, Canguru e Dublin Hub; **`1,40%` para Novo Horizonte**) e em `pendencias.csv` para contestação.
  * **Critério de Tolerância de Arredondamento PTAX (`0,01 p.p.` — `P01`, `R15`):** Oscilações inferiores a `0,01 p.p.` entre o `Spread %` reportado e a taxa contratada (ex.: `1,4984%` a `1,5015%` para `1,50%`) decorrem do arredondamento da taxa final de câmbio em 4 casas decimais e não são reportadas como divergência.
  * **Resolução do `CONFLITO C1` e Prova Matemática dos `R$ 0,56 / R$ 0,57` (`R18` — respostas da Helena às `22h33/22h34`):**
    * Conforme a resposta da Helena ao Lucca Landeiro e à Insper AI (`R18`): *"Ainda não contestei nada... Considerem que estamos dentro do prazo... Não sei ainda como a Ponte vai pagar, porque a contestação nem foi aberta. Não conte que ela vai descontar nada do repasse. Conferir o TED quando ele cair é uma pendência boa. Fica comigo."*
    * Portanto, **não supomos desconto no repasse de outubro**: registramos em `pendencias.csv` as contestações com seus valores e códigos de operação (Mundo Aberto `23` ops `R$ 1.418,85`, 4 spreads negativos `-R$ 1.834,05` e duplicata `PC-0926-0162` `R$ 821,88`) e a pendência para a Helena **conferir o TED de outubro quando cair**.
    * **Explicação matemática da diferença de `R$ 0,56 / R$ 0,57` apontada na branch `origin/pix`:**
      * Soma do `Spread R$` das `228` operações válidas = `R$ 79.085,76`.
      * Se calculássemos `50%` sobre a soma total (`79.085,76 × 0,50`), daria `R$ 39.542,88`.
      * Porém, aplicando a regra `R11` da Helena (`50%` arredondado `ROUND_HALF_UP` **operação por operação**), existem `114` operações com centavo ímpar no `Spread R$` (cujo meio centavo `0,005` arredonda para `+0,01`), totalizando exatamente **`R$ 39.543,45`** (`39.543,45 − 39.542,88 = +R$ 0,57`). Daí vinha a diferença entre `917,03 − 410,94 = 506,09` e `39.543,45 − 39.036,80 = 506,65`!

---

## 3. Classificação Contábil dos Extratos Bancários (`lancamentos_classificados.csv`)

* **H09 — Fluxo Orbe × Aurora, Contrapartida Contábil e Competência (`R19`, `R21`):**
  * **Fluxo Orbe e Conta Garantida (`R21` — resposta da Helena às `22h34`):** A Orbe deposita tudo no Banco Aurora (Débito e PIX em D+1; Crédito e parcelado ao longo dos meses seguintes conforme as parcelas). O saldo negativo do Aurora é a **conta garantida** usada para pagar lojistas antes da liquidação da Orbe. Conciliar Orbe × banco parcela a parcela está fora do escopo: os `21` créditos de TED da Orbe no Aurora (`R$ 3.557.246,29`) são classificados em `1.1.03.001` (*Recebíveis de adquirente - Orbe*).
  * **Obrigações e Recebíveis de Agosto Já Provisionados (`R19`):** baixam passivo ou ativo:
    * Folha `08/2026` (`L15`, `-R$ 184.732,18`) $\rightarrow$ `2.1.04.001` (*Salários a pagar*).
    * ISS `08/2026` (`L42`, `-R$ 21.877,40`) $\rightarrow$ `2.1.03.003` (*ISS a recolher*).
    * INSS `08/2026` (`L54`, `-R$ 51.320,66`) $\rightarrow$ `2.1.04.002` (*INSS a recolher*).
    * FGTS `08/2026` (`L55`, `-R$ 14.778,57`) $\rightarrow$ `2.1.04.003` (*FGTS a recolher*).
    * IRRF `0561` (`L57`, `-R$ 22.104,35`) $\rightarrow$ `2.1.03.004` (*IRRF a recolher*).
    * PIS `8109` (`L86`, `-R$ 9.811,20`) $\rightarrow$ `2.1.03.001` (*PIS a recolher*).
    * COFINS `2172` (`L87`, `-R$ 45.282,46`) $\rightarrow$ `2.1.03.002` (*COFINS a recolher*).
    * Repasse Ponte Câmbio `08/2026` (`MRD2026090132`, `04/09`, `+R$ 61.884,12`) $\rightarrow$ `1.1.03.002` (*Comissões de intermediação a receber - câmbio*).
  * **Despesas de Setembro Não Provisionadas (`R19` + premissa para IOF):** entram direto nas contas de despesa (`4.x`):
    * Tarifas bancárias (`L10`, `L90`, `MRD2026090103`, `MRD2026090696`) $\rightarrow$ `4.2.01` (*Tarifas bancárias*).
    * Condomínio (`L16`, `-R$ 28.450,00`) $\rightarrow$ `4.2.02` (*Aluguel e condomínio*).
    * AWS Cloud (`L47`, `-R$ 41.208,77`) $\rightarrow$ `4.2.03` (*Cloud e infraestrutura*).
    * Google Workspace (`L48`, `-R$ 2.210,00`) $\rightarrow$ `4.2.04` (*Softwares e assinaturas*).
    * Seguro empresarial (`MRD2026090292`, `12/09`, `-R$ 1.830,44`, parcela `09/12`) $\rightarrow$ `4.2.05` (*Seguros* — premissa: parcela do mês, não provisionada, pois a Helena listou só folha, tributos de agosto e repasse da Ponte como provisionados).
    * Contabilidade Exata (`L53`, `-R$ 6.800,00`) $\rightarrow$ `4.2.06` (*Serviços contábeis e jurídicos*).
    * `IOF S/ OPERACAO CREDITO` (`MRD2026090586`, `26/09`, `-R$ 48,21`) $\rightarrow$ `4.3.01` (*IOF* — premissa direta pela natureza da conta `4.3.01` no plano de contas).
* **H10 — Anomalias Bancárias, Resolução do `CONFLITO C2` e Prova Matemática de `MRD2026090425` (`R20`):**
  * **Total de linhas do Banco Aurora:** Existem **`84` lançamentos** de movimentação (linhas físicas `9` a `92`, excluindo o cabeçalho na linha `7`, `SALDO ANTERIOR` na linha `8`, `SALDO FINAL` na linha `94` e o rodapé na linha `95`), mais **`100` lançamentos** no OFX do Banco Meridiano = **`184` lançamentos classificados**. Conforme a instrução oficial, o `ref_origem` do Aurora é o número da linha física (`L9` … `L92`) e o do Meridiano é o `FITID`.
  * **`16/09/2026` (`L50` do Aurora) — `PIX RECEBIDO 38686002000180 SEM IDENTIFICACAO` (`+R$ 7.350,00`):** não é receita até identificar a origem (`R20`) $\rightarrow$ classificado em `1.1.09.002` (*Créditos não identificados*) + `pendencias.csv`.
  * **Resolução do `CONFLITO C2` — `23/09/2026` (`L65` do Aurora) — `DEVOLUCAO PIX - MUNDO ABERTO INTERC` (`+R$ 12.400,00`):** conforme `R20`, trata-se de *"um Pix de repasse que voltou, e ainda não sei o motivo"*. Sem afirmar "estorno parcial", classificamos a contrapartida contábil em `2.1.01.001` (*Repasses a lojistas a pagar*, pois o recurso destinado ao repasse retornou à conta bancária da Tarvo e permanece como obrigação pendente de regularização com o lojista) + `pendencias.csv` para apurar o motivo da devolução.
  * **`30/09/2026` (`L92` do Aurora) — `TRANSF ENTRE CONTAS P/ BCO MERIDIANO` (`-R$ 300.000,00`):** saiu do Aurora em `30/09` e compensa no Meridiano em `01/10` (`R20`) $\rightarrow$ classificado em `1.1.09.001` (*Transferências entre contas próprias*) + `pendencias.csv` para conciliação em `01/10`.
  * **Prova Matemática Exata de `MRD2026090425` (`17/09/2026`, Meridiano) — `PIX RECEB PONTE AEREA ESTUDANTIL L` (`+R$ 18.240,00`):**
    * No extrato OFX do Banco Meridiano, a `Ponte Aérea Estudantil Ltda` (`CNPJ 95739378000118`) possui **6 créditos de PIX**:
      1. `MRD2026090082` (`01/09/2026`, terça-feira): `R$ 77.595,09`
      2. `MRD2026090237` (`08/09/2026`, terça-feira): `R$ 148.766,45`
      3. `MRD2026090375` (`15/09/2026`, terça-feira): `R$ 183.631,12`
      4. **`MRD2026090425` (`17/09/2026`, quinta-feira): `R$ 18.240,00`** *(único fora do lote semanal de terça-feira e grafado `PONTE AEREA` sem acento)*
      5. `MRD2026090495` (`22/09/2026`, terça-feira): `R$ 14.091,03`
      6. `MRD2026090648` (`29/09/2026`, terça-feira): `R$ 28.165,34`
    * Na planilha da Ponte Câmbio (`03_email_ponte_cambio_relatorio_set2026.eml`), a `Ponte Aérea Estudantil` possui `15` operações no mês, cuja soma de `Valor R$ (450.536,99) + IOF R$ (1.712,04)` é exatamente **`R$ 452.249,03`**.
    * Somando apenas os **5 PIX de terça-feira** (`77.595,09 + 148.766,45 + 183.631,12 + 14.091,03 + 28.165,34`), obtém-se **exatamente `R$ 452.249,03` (diferença de `R$ 0,00`)**!
    * Isso prova matematicamente que o PIX `MRD2026090425` de `17/09/2026` (`+R$ 18.240,00`) é um valor excedente sem operação de câmbio correspondente em setembro $\rightarrow$ classificado em `2.1.02.001` (*Recursos de lojistas para remessas a liquidar*) e registrado em `pendencias.csv`!
