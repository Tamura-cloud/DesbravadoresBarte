# HIPOTESES.md — Premissas Assumidas e Interações com o Financeiro (`#tarvo-financeiro`)

Este documento separa explicitamente **o que é fato comprovado nos arquivos do Data Pack** daquilo que **estamos assumindo como premissa de negócio**, além de registrar todas as perguntas enviadas ao time financeiro da Tarvo no canal `#tarvo-financeiro` e suas respectivas respostas.

---

## 1. Fatos Comprovados nos Dados vs. Premissas de Partida

| ID | Tema / Linha | O que Sabemos com Certeza (Fato nos Arquivos) | O que Assumimos (Premissa Provisória até Resposta do Financeiro) | Impacto em R$ (Set/2026) |
| :-: | :--- | :--- | :--- | :--- |
| **H01** | **Identificação de Lojistas (Orbe)** | O mesmo `cod_estabelecimento` (EC) aparece com até 3 grafias de nome na Orbe. Existem dois lojistas com "Horizonte" no nome (`1043300981` = `HORIZONTE INTERCAMBIO` aplicando taxas de `2,39% / 2,89%`, que são as taxas da **Novo Horizonte**; e `1043396662` = `HORIZONTE VIAGENS TURISMO`). Além disso, `1038867654` é a **Kiwi**. | **Nunca casar lojista por aproximação de nome.** Usar `cod_estabelecimento` como chave única e mapear os ECs ausentes da planilha (`1043300981` -> Novo Horizonte `66564512000199`; `1043396662` -> Horizonte Viagens `78576234000179`; `1038867654` -> Kiwi) registrando a pendência de atualização cadastral para a Bia. | R$ 27.492,62 em taxas nas 233 transações desses 3 ECs. |
| **H02** | **Lojista Atlas Idiomas (`EC 1076801732`)** | Opera 57 transações na Orbe em set/2026, mas **não consta na aba `"Taxas vigentes"`** da planilha `02_tabela_taxas_contratadas.xlsx` (consta apenas na aba `"ANTIGO 2025 - nao usar"`). | A aba de 2025 **não** é usada como contrato vigente sem autorização. Calculamos a comissão pela taxa efetivamente aplicada pela Orbe, **não geramos falso positivo em `divergencias_taxa.csv`** e abrimos item em `pendencias.csv` (`quem_decide`: Comercial / Bia). | R$ 7.876,05 em taxas da Atlas Idiomas. |
| **H03** | **Vigência de Taxa no Meio do Mês (Escola Bridge)** | A planilha de taxas traz duas linhas para a *Escola Bridge de Idiomas*, com redução da taxa de crédito à vista de `2,59%` para `2,19%` a partir de `15/09/2026`. Na Orbe, 5 vendas a partir de `15/09` continuaram sendo cobradas a `2,59%`. | Para vendas, vale a taxa vigente na `data_movimento`; para estornos/reversões, vale a taxa vigente na `data_venda_original`. As 5 vendas pós-15/09 a `2,59%` entram em `divergencias_taxa.csv`. | R$ 29,95 cobrados a mais. |
| **H04** | **Divergência de Taxas na Rota Global** | A Orbe aplicou as taxas antigas de 2025 (`2,99% / 3,49% / 4,09%`) em vez das taxas vigentes (`2,49% / 2,99% / 3,59%`) em 83 vendas e 4 estornos da *Rota Global*. | Reportamos cada transação em `divergencias_taxa.csv` (incluindo o sinal negativo nos estornos) e geramos pendência de ressarcimento/ajuste. | R$ 1.546,28 cobrados a mais no líquido. |
| **H05** | **Base da Comissão e NF de Checkout** | A soma total de `valor_taxa` na Orbe em set/2026 (vendas, estornos, antecipações e reversões) é de `R$ 231.880,36`. | A comissão reportada em `comissoes_por_lojista.csv` reflete o `valor_taxa` líquido apurado no relatório da Orbe (com estornos e reversões deduzindo no mês em que ocorreram), emitindo 1 NF por lojista tomador. *(Sujeito a ajuste caso o financeiro determine faturar pelo valor contratado).* | R$ 231.880,36 no total de Checkout. |
| **H06** | **Operação Duplicada na Ponte Câmbio (`PC-0926-0162`)** | A operação `PC-0926-0162` (Bagagem Livre) aparece duas vezes na planilha da Ponte (a segunda com observação `"reprocessada"`). O extrato OFX do Banco Meridiano comprova que as 21 TEDs de liquidação (`R$ 5.611.447,12`) batem exatamente com as operações **sem** a duplicata. | Excluímos a cópia duplicada do cálculo de comissão e de nota fiscal para não inflar a receita, e registramos a duplicata descartada em `pendencias.csv`. | R$ 821,88 de spread bruto (R$ 410,94 de comissão Tarvo). |
| **H07** | **Spread `"padrão"` ou em Branco na Planilha** | Três lojistas (Kiwi, Canguru, Ponte Aérea) estão com spread `"padrão"` ou em branco na planilha comercial, e a Ponte Câmbio aplicou `1,50%` a todos eles. | Assumimos que o spread padrão da Tarvo é `1,50%` e ignoramos variações de arredondamento menores que `0,01 p.p.` no cálculo de divergência. | Zero alarmes falsos de arredondamento. |
| **H08** | **Divergência de Spread na Mundo Aberto** | A *Mundo Aberto* renegociou spread para `1,20%` em jul/2026 na planilha, mas a Ponte Câmbio cobrou `1,50%` nas 23 remessas de setembro. | Registramos as 23 operações em `divergencias_taxa.csv` (`linha_negocio=REMESSA`) e abrimos pendência para acerto comercial/financeiro. | R$ 1.440,38 cobrados a mais. |
| **H09** | **Spread Negativo (`Taxa travada no pedido D-1`)** | Existem 4 operações na Ponte Câmbio com `Spread R$` realizado negativo (`R$ -1.834,05` no total), embora o spread estimado em D-1 fosse positivo (`R$ +1.622,90`). | Mantemos o valor realizado no cálculo base (ou seguimos a resposta oficial do financeiro) e registramos obrigatoriamente as 4 operações em `pendencias.csv` para decisão sobre quem absorve a variação cambial. | R$ -1.834,05 de spread realizado. |
| **H10** | **Status `"APROVADO C/ RESSALVA"` e Competência 30/09** | O corpo do e-mail da Ponte informa que `"APROVADO C/ RESSALVA"` segue normalmente para liquidação, e que o repasse é de `50%` do spread mediante emissão de **uma nota fiscal de intermediação** contra a Ponte Câmbio (`CNPJ 75374179000146`). Há 6 operações contratadas em `30/09` e liquidadas em `01/10`. | Incluímos as operações `"APROVADO C/ RESSALVA"` e as contratadas em `30/09` (regime de competência da contratação constante no relatório de 09/2026), emitindo 1 NF contra a Ponte Câmbio por 50% do spread total. | R$ 4.829,37 e R$ 2.078,71 de spread bruto. |
| **H11** | **Conciliação Bancária e Itens Sem Par** | No Meridiano, há um PIX de `R$ 18.240,00` (`17/09`, Ponte Aérea) sem remessa na Ponte. No Aurora, há uma TED de `R$ 300.000,00` (`30/09`) ainda não compensada no Meridiano, um PIX de `R$ 7.350,00` sem identificação e uma devolução de PIX de `R$ 12.400,00` (Mundo Aberto). | Todos os 84 lançamentos do Aurora e 100 do Meridiano são classificados em contas analíticas (`ACEITA_LANCTO=S`), e os 4 itens sem par / não identificados geram registros detalhados em `pendencias.csv`. | R$ 337.990,00 em itens pendentes de conciliação/identificação. |

---

## 2. Registro de Perguntas e Respostas — Canal `#tarvo-financeiro`

*(Atualizar abaixo com o horário exato do envio e a resposta literal recebida da banca)*

### Bloco 1 — Checkout e Nível Mínimo
1. **Atlas Idiomas (`EC 1076801732`):**
   * *Pergunta enviada:* `[Horário: --:--]` Atlas Idiomas teve 57 transações em setembro e não está na aba vigente (apenas na aba 2025). Qual é o CNPJ e a taxa contratada vigente?
   * *Resposta do Financeiro:* `[Aguardando resposta]`
   * *Decisão aplicada no pipeline:* `[Ver H02]`
2. **Mapeamento de ECs sem código na planilha (`1043300981`, `1043396662`, `1038867654`):**
   * *Pergunta enviada:* `[Horário: --:--]` Confirmam que EC `1043300981` ("HORIZONTE INTERCAMBIO", taxas 2,39%/2,89%) é a Novo Horizonte (`66564512000199`), EC `1043396662` é a Horizonte Viagens (`78576234000179`) e EC `1038867654` é a Kiwi?
   * *Resposta do Financeiro:* `[Aguardando resposta]`
   * *Decisão aplicada no pipeline:* `[Ver H01]`
3. **Base da Comissão de Checkout e Divergências (Rota Global / Bridge):**
   * *Pergunta enviada:* `[Horário: --:--]` Em `comissoes_por_lojista.csv` e nas NFs de checkout, reportamos a taxa efetivamente cobrada pela Orbe ou a taxa contratada? E estornos/reversões de vendas de agosto abatem a comissão e a nota de setembro?
   * *Resposta do Financeiro:* `[Aguardando resposta]`
   * *Decisão aplicada no pipeline:* `[Ver H04 e H05]`

### Bloco 2 — Remessas e Notas Fiscais
4. **Spread Negativo (`Taxa travada no pedido D-1`), Spread Padrão (`1,50%`) e Competência `30/09`:**
   * *Pergunta enviada:* `[Horário: --:--]` (a) Nas 4 operações com spread negativo (`R$ -1.834,05`), entra o realizado negativo, zera-se ou usa-se o estimado D-1? (b) As 6 operações contratadas em 30/09 e liquidadas em 01/10 entram no fechamento de setembro? (c) A NF de remessa é única contra a Ponte Câmbio?
   * *Resposta do Financeiro:* `[Aguardando resposta]`
   * *Decisão aplicada no pipeline:* `[Ver H07, H09 e H10]`

### Bloco 3 — Classificação Contábil e Pendências
5. **Regime de Caixa vs. Competência nos Extratos e Itens Pendentes:**
   * *Pergunta enviada:* `[Horário: --:--]` Folha, encargos e impostos de agosto pagos no início de setembro devem ser baixados contra as contas de passivo (`2.1.03` / `2.1.04`) ou lançados em despesa (`4.x`)? E como tratar o PIX de `R$ 18.240,00` da Ponte Aérea sem remessa e o PIX de `R$ 7.350,00` sem identificação?
   * *Resposta do Financeiro:* `[Aguardando resposta]`
   * *Decisão aplicada no pipeline:* `[Ver H11]`
