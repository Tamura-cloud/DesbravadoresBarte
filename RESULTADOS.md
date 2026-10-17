# Resultados do fechamento — setembro/2026

| | |
|---|---|
| Data | 2026-10-17 |
| Commit do código | branch `regras-helena-2`, sobre `fd0db20` (R29). Em relação a `fd0db20`, os 6 CSVs de `saida/` estão idênticos byte a byte; mudou só `contestacoes/` (estrutura dos .md e colunas novas no ponte_operacoes.csv) |
| Fechamento | `python -m tarvo fechar --competencia 2026-09 --entrada dados/2026-09 --saida saida/` (IA conforme `config/ia.yaml`; em setembro todo lançamento casa uma regra, então a IA não é chamada nenhuma vez, P14) |
| Resumo | `python -m tarvo resumo --saida saida` |
| pytest | **347 passed** (`python -m pytest -q`, 23,4 s) |
| `validar_saida(saida/)` | `[]`, **sem problemas** |
| Rastro | 488 de 488 itens com soma do rastro por id_saida = valor reportado |

**R25 a R30 (Helena, 17/10, respostas a outros times às 9h47, 9h49, 9h53 e 10h44):** nenhum número mudou. Mudaram só 4 textos de motivo em pendencias.csv:
- PEN-DEVOL-CHK-22224579000109 e PEN-DEVOL-CHK-95927868000148 (R25): o motivo dizia que a devolução era "decidida caso a caso (R03)"; agora diz que o que a Orbe cobrou a mais é valor a devolver ao lojista. A PEN-DEVOL da Casa do Estudante já dizia isso (R10).
- PEN-CONTEST-REM-17217888000111 (R15, R27): o motivo diz que o valor cheio é o que o lojista pagou a mais e é a devolver, e que o ajuste vem no relatório da Ponte do mês seguinte.
- PEN-SEMCONTRATO-1076801732 (R30): o motivo diz que as 57 transações (R$ 262.138,61 brutos) serão faturadas na competência 2026-10, com a taxa retroativa a 2026-09-10, quando o Comercial confirmar.

Auditoria das regras novas contra este fechamento:

| regra | o que foi conferido | resultado |
|---|---|---|
| R25 | notas pela taxa contratada, sem somar divergência; nenhuma taxa aplicada abaixo da contratada (as 5 diferenças negativas são estornos, -107,53) | OK; texto da PEN-DEVOL-CHK corrigido |
| R26 | os 44 repasses (PIX ENVIADO, Aurora) estão em 2.1.01.001 e saíram entre os dias 08 e 10 ou 22 e 24; o Meridiano não tem repasse a lojista | OK |
| R27 | o relatório de setembro não tem linha de ajuste de agosto; um ajuste em outubro vira PEN-FORA-REM, sem comissão nem nota, com a referência da operação original (`test_ajuste_ponte.py`) | OK; texto da PEN-CONTEST-REM ajustado |
| R28 | campo "Aprovado por" em R01 a R30; P01 a P23 aguardando aprovação | registrado no HIPOTESES.md |
| R29 | o fechamento não gera o rascunho de e-mail por contraparte | **CONFLITO, não corrigido** (ver HIPOTESES.md, seção 4) |
| R30 | 57 linhas no rastro da PEN-SEMCONTRATO-1076801732, primeira transação em 2026-09-10 | OK; texto corrigido |

**R29 — rascunhos de contestação (`contestacoes/`, ao lado de `saida/`).** O `fechar` grava 4 arquivos a partir dos itens já calculados; `saida/` continua com os 6 CSVs. Todo total do texto é a soma do CSV ao lado (`test_contestacao.py`):

| arquivo | conteúdo | linhas | total | Esperado | teste de origem | |
|---|---|---:|---:|---|---|:-:|
| orbe_operacoes.csv | DIV-CHK: Casa 118, Rota 87, Bridge 5 | 210 | 16.973,65 | 210 · 16.973,65 (= divergências de CHECKOUT, seção 4); estornos 5 · -107,53 | `test_contestacao.py::test_orbe_totais_do_texto_saem_do_csv`, `::test_orbe_estornos_ficam_no_total_e_sao_explicados` | ✓ |
| ponte_operacoes.csv · SPREAD_ACIMA_CONTRATADO | DIV-REM: Mundo Aberto | 23 | 1.418,85 | 23 · 1.418,85 (= PEN-CONTEST-REM) | `test_contestacao.py::test_ponte_csv_bate_com_divergencias_e_pendencias` | ✓ |
| ponte_operacoes.csv · SPREAD_NEGATIVO | PEN-NEG-REM (R23) | 4 | -3.565,98 | 4 · -3.565,98 | idem | ✓ |
| ponte_operacoes.csv · OPERACAO_DUPLICADA | PEN-DUP-REM-PC-0926-0162 | 1 | 821,88 | 1 · 821,88 | idem | ✓ |

Cada .md abre com um bloco "NOTAS PARA A HELENA — apagar antes de enviar" (avisos, valor a devolver pela R25, ressalvas); o corpo não fala de aviso do Comercial. Orbe: "Comunicação de condição comercial" (Casa, 0% de 2026-09-01 a 2026-12-31) e "Taxas aplicadas acima do contrato" (Bridge e Rota). Ponte: Mundo Aberto como comunicação de condição, mais os spreads negativos e a duplicada como contestação. Os destinatários são `<e-mail da Orbe>` e `<e-mail da Ponte>`.

Colunas novas no ponte_operacoes.csv (P24, exibição, aguardando aprovação):

| natureza | coluna | total | Esperado | teste de origem | |
|---|---|---:|---|---|:-:|
| SPREAD_ACIMA_CONTRATADO | parte_tarvo_brl (50% da diferença, por operação) | 709,46 | 709,46 | `test_contestacao.py::test_ponte_partes_da_tarvo_no_csv` | ✓ |
| SPREAD_NEGATIVO | tarvo_deixou_de_receber_brl (50% do spread contratado) | 865,98 | 865,98 | idem | ✓ |
| OPERACAO_DUPLICADA | parte_tarvo_brl · valor_operacao_brl | 410,94 · 55.811,47 | 410,94 · 55.811,47 | idem | ✓ |

O `fechar` pelo CLI lista os 4 arquivos gravados e aceita `--sem-contestacao` (`test_contestacao.py::test_cli_lista_os_rascunhos_e_grava_na_pasta_irma`, `::test_cli_sem_contestacao_nao_grava_a_pasta`).

A mudança anterior (R23, 9h48: spread negativo só como contestação, fora das divergências) está no commit `292a3eb`.

**Coluna "Esperado":** valor copiado de um assert dos testes, com o teste de origem (`arquivo::função`). Quando o número do relatório é a soma de dois asserts, a conta aparece na coluna. "—" quer dizer que nenhum teste fixa esse número.
✓ = bate com o esperado; ✗ = não bate.

**Resultado: nenhuma linha com ✗.** Todos os números com valor de referência batem.

Valores em R$, no formato brasileiro.

---

## 1. Quantidade de linhas e rastro

| arquivo | linhas | Esperado | teste de origem | |
|---|---:|---:|---|:-:|
| comissoes_por_lojista.csv | 35 | 21 + 14 | `test_checkout.py::test_set_comissao_total_e_lojistas` (21) + `test_remessa.py::test_set_comissao_total_e_lojistas` (14) | ✓ |
| divergencias_taxa.csv | 233 | 210 + 23 | `test_checkout.py::test_set_divergencias` (210) + `test_remessa.py::test_set_divergencias` (23) | ✓ |
| notas_a_emitir.csv | 21 | 20 + 1 | `test_checkout.py::test_set_notas` (20) + `test_remessa.py::test_set_nota_unica` (1) | ✓ |
| lancamentos_classificados.csv | 184 | 184 | `test_bancos.py::test_setembro_184_lancamentos_todos_por_regra` | ✓ |
| pendencias.csv | 15 | — | nenhum teste fixa o total; as 15 aparecem uma a uma na seção 6 | |
| rastro.csv | 5.171 | — | | |

| checagem | resultado | Esperado | teste de origem | |
|---|---|---|---|:-:|
| `validar_saida` (formato, id único, soma do rastro) | `[]` | `[]` | `test_bancos.py::test_setembro_validar_saida_com_os_tres_modulos` | ✓ |
| itens com soma do rastro = valor reportado | 488 de 488 | — | | |
| itens com soma diferente, itens sem rastro, id do rastro sem item | 0, 0, 0 | — | | |

---

## 2. Comissões

### Por linha de negócio

| linha_negocio | lojistas | comissão | Esperado | teste de origem | |
|---|---:|---:|---|---|:-:|
| CHECKOUT | 21 | 207.039,73 | 21 · 207.039,73 | `test_checkout.py::test_set_comissao_total_e_lojistas` | ✓ |
| REMESSA | 14 | 39.543,45 | 14 · 39.543,45 | `test_remessa.py::test_set_comissao_total_e_lojistas` | ✓ |
| **total** | 35 | 246.583,18 | — | | |

### CHECKOUT por lojista

| CNPJ | lojista | comissão | Esperado | teste de origem | |
|---|---|---:|---:|---|:-:|
| 17217888000111 | Mundo Aberto | 18.522,09 | — | | |
| 23109187000161 | Oxford Prep Cursos Ltda | 16.077,90 | 16.077,90 | `test_checkout.py::test_set_comissao_por_lojista` | ✓ |
| 95927868000148 | Rota Global Intercâmbio Ltda | 15.621,27 | 15.621,27 | `test_checkout.py::test_set_comissao_por_lojista` | ✓ |
| 34671260000100 | Maple Study Assessoria Educacional Ltda | 15.010,78 | — | | |
| 16181276000153 | EduAbroad | 12.070,17 | — | | |
| 22224579000109 | Escola Bridge de Idiomas Ltda | 11.916,02 | 11.916,02 | `test_checkout.py::test_set_comissao_por_lojista` | ✓ |
| 68567965000102 | Dublin Hub Intercâmbio Ltda | 11.906,08 | — | | |
| 53857560000123 | Canguru | 11.679,43 | — | | |
| 07752116000126 | Kiwi Experience | 10.711,41 | — | | |
| 08780784000120 | Campus Global Ltda | 9.336,06 | — | | |
| 20987545000140 | Vela | 9.315,31 | — | | |
| 67869675000142 | Bem-Vindo Exchange Ltda | 9.259,74 | — | | |
| 78576234000179 | Horizonte Viagens | 9.014,42 | — | | |
| 61720397000180 | Lisboa Cursos e Viagens Ltda | 8.470,78 | — | | |
| 66564512000199 | Novo Horizonte Intercambio | 7.767,78 | — | | |
| 50900987000179 | Bagagem Livre Turismo Ltda | 7.703,98 | — | | |
| 03229837000103 | Fluente Idiomas Online Ltda | 7.316,07 | — | | |
| 89779285000114 | Sol Nascente Viagens Ltda | 5.898,02 | — | | |
| 21394880000106 | Trilha Jovem Turismo Ltda | 5.628,57 | — | | |
| 85694108000184 | Andes Expedições Ltda | 3.819,35 | — | | |
| 00520815000100 | Casa do Estudante Viagens Ltda | -5,50 | -5,50 | `test_checkout.py::test_set_comissao_por_lojista` | ✓ |

### REMESSA por lojista

| CNPJ | lojista | comissão | Esperado | teste de origem | |
|---|---|---:|---:|---|:-:|
| 95927868000148 | Rota Global Intercâmbio Ltda | 4.918,34 | 4.918,34 | `test_remessa.py::test_set_comissao_por_lojista` | ✓ |
| 34671260000100 | Maple Study Assessoria Educacional Ltda | 4.295,03 | 4.295,03 | `test_remessa.py::test_set_comissao_por_lojista` | ✓ |
| 53857560000123 | Canguru | 3.764,05 | — | | |
| 17217888000111 | Mundo Aberto | 3.547,69 | 3.547,69 | `test_remessa.py::test_set_comissao_por_lojista` | ✓ |
| 61720397000180 | Lisboa Cursos e Viagens Ltda | 3.196,36 | — | | |
| 00520815000100 | Casa do Estudante Viagens Ltda | 3.075,91 | — | | |
| 95739378000118 | Ponte Aérea Estudantil Ltda | 3.007,30 | — | | |
| 14760206000124 | Nórdica Educação Internacional Ltda | 2.914,18 | — | | |
| 07752116000126 | Kiwi Experience | 2.668,36 | — | | |
| 16181276000153 | EduAbroad | 2.520,25 | — | | |
| 66564512000199 | Novo Horizonte Intercambio | 2.207,48 | — | | |
| 68567965000102 | Dublin Hub Intercâmbio Ltda | 1.772,61 | — | | |
| 50900987000179 | Bagagem Livre Turismo Ltda | 1.292,67 | 1.292,67 | `test_remessa.py::test_set_comissao_por_lojista` | ✓ |
| 67869675000142 | Bem-Vindo Exchange Ltda | 363,22 | 363,22 | `test_remessa.py::test_set_comissao_por_lojista` | ✓ |

A Atlas Idiomas (EC 1076801732) não tem linha de comissão (P21; ver seção 6 e "Escolhas de interpretação").

---

## 3. Notas a emitir

| tomador_cnpj | tomador | linha | valor | Esperado | teste de origem | |
|---|---|---|---:|---:|---|:-:|
| 75374179000146 | Ponte Câmbio S.A. | REMESSA | 39.543,45 | 39.543,45, única nota de remessa, tomadora 75374179000146 | `test_remessa.py::test_set_nota_unica` | ✓ |
| | | | | 228 operações no rastro da nota | `test_remessa.py::test_set_operacoes_unicas_e_na_comissao` | ✓ |
| 17217888000111 | Mundo Aberto | CHECKOUT | 18.522,09 | — | | |
| 23109187000161 | Oxford Prep Cursos Ltda | CHECKOUT | 16.077,90 | — | | |
| 95927868000148 | Rota Global Intercâmbio Ltda | CHECKOUT | 15.621,27 | — | | |
| 34671260000100 | Maple Study Assessoria Educacional Ltda | CHECKOUT | 15.010,78 | — | | |
| 16181276000153 | EduAbroad | CHECKOUT | 12.070,17 | — | | |
| 22224579000109 | Escola Bridge de Idiomas Ltda | CHECKOUT | 11.916,02 | — | | |
| 68567965000102 | Dublin Hub Intercâmbio Ltda | CHECKOUT | 11.906,08 | — | | |
| 53857560000123 | Canguru | CHECKOUT | 11.679,43 | — | | |
| 07752116000126 | Kiwi Experience | CHECKOUT | 10.711,41 | — | | |
| 08780784000120 | Campus Global Ltda | CHECKOUT | 9.336,06 | — | | |
| 20987545000140 | Vela | CHECKOUT | 9.315,31 | — | | |
| 67869675000142 | Bem-Vindo Exchange Ltda | CHECKOUT | 9.259,74 | — | | |
| 78576234000179 | Horizonte Viagens | CHECKOUT | 9.014,42 | — | | |
| 61720397000180 | Lisboa Cursos e Viagens Ltda | CHECKOUT | 8.470,78 | — | | |
| 66564512000199 | Novo Horizonte Intercambio | CHECKOUT | 7.767,78 | — | | |
| 50900987000179 | Bagagem Livre Turismo Ltda | CHECKOUT | 7.703,98 | — | | |
| 03229837000103 | Fluente Idiomas Online Ltda | CHECKOUT | 7.316,07 | — | | |
| 89779285000114 | Sol Nascente Viagens Ltda | CHECKOUT | 5.898,02 | — | | |
| 21394880000106 | Trilha Jovem Turismo Ltda | CHECKOUT | 5.628,57 | — | | |
| 85694108000184 | Andes Expedições Ltda | CHECKOUT | 3.819,35 | — | | |

| linha | notas | valor | Esperado | teste de origem | |
|---|---:|---:|---|---|:-:|
| CHECKOUT | 20 | 207.045,23 | 20 notas, nenhuma da Casa do Estudante (00520815000100) | `test_checkout.py::test_set_notas` | ✓ |
| REMESSA | 1 | 39.543,45 | 39.543,45 | `test_remessa.py::test_set_nota_unica` | ✓ |
| **total** | 21 | **246.588,68** | — | | |

As notas somam R$ 5,50 a mais que as comissões (246.583,18): é a comissão negativa da Casa do Estudante, que não emite nota (R06) e vira PEN-NF-CHK.

---

## 4. Divergências de taxa

### Por linha de negócio

| linha | linhas | soma | Esperado | teste de origem | |
|---|---:|---:|---|---|:-:|
| CHECKOUT | 210 | 16.973,65 | 210 · 16.973,65 | `test_checkout.py::test_set_divergencias` | ✓ |
| REMESSA | 23 | 1.418,85 | 23 · 1.418,85, todas da Mundo Aberto, nenhuma DIV-REM dos 4 spreads negativos (R23) | `test_remessa.py::test_set_divergencias` | ✓ |
| **total** | 233 | 18.392,50 | — | | |

### Por lojista e linha

| linha | CNPJ | lojista | linhas | soma | Esperado | teste de origem | |
|---|---|---|---:|---:|---|---|:-:|
| CHECKOUT | 00520815000100 | Casa do Estudante Viagens Ltda | 118 | 15.397,42 | 118 · 15.397,42 | `test_checkout.py::test_set_divergencias` | ✓ |
| CHECKOUT | 95927868000148 | Rota Global Intercâmbio Ltda | 87 | 1.546,28 | 87 · 1.546,28 | `test_checkout.py::test_set_divergencias` | ✓ |
| CHECKOUT | 22224579000109 | Escola Bridge de Idiomas Ltda | 5 | 29,95 | 5 · 29,95 | `test_checkout.py::test_set_divergencias` | ✓ |
| REMESSA | 17217888000111 | Mundo Aberto | 23 | 1.418,85 | 23 · 1.418,85 | `test_remessa.py::test_set_divergencias` | ✓ |

Os 4 spreads negativos (PC-0926-0210, -0326, -0491 e -0545) não entram aqui: pela R23 não são divergência. Ficam só como PEN-NEG-REM na seção 6, com os mesmos valores (P18).

Abaixo da tolerância de 0,01 p.p. (P01), a maior oscilação das operações não divergentes e sem spread negativo é 0,0016 p.p. (`test_remessa.py::test_set_oscilacao_dos_demais_abaixo_da_tolerancia`), um número que não aparece nos CSVs.

### As 5 maiores

| id_saida | CNPJ | contratada (%) | aplicada (%) | diferença | Esperado |
|---|---|---:|---:|---:|---|
| DIV-CHK-AN88445802 | 00520815000100 | 0.0000 | 2.1000 | 1.206,58 | — |
| DIV-CHK-AN88445486 | 00520815000100 | 0.0000 | 2.1000 | 910,93 | — |
| DIV-CHK-TX88419350 | 00520815000100 | 0.0000 | 3.7900 | 663,48 | — |
| DIV-CHK-AN88445740 | 00520815000100 | 0.0000 | 2.1000 | 606,36 | — |
| DIV-CHK-TX88433069 | 00520815000100 | 0.0000 | 3.7900 | 587,10 | — |

As cinco são da Casa do Estudante: antecipações (AN) e vendas cobradas durante a tarifa zerada da R10.

### Negativas (5 linhas, soma -107,53)

| id_saida | CNPJ | contratada (%) | aplicada (%) | diferença | Esperado | teste de origem | |
|---|---|---:|---:|---:|---:|---|:-:|
| DIV-CHK-TX88446419 | 95927868000148 | 3.5900 | 4.0900 | -52,10 | — | | |
| DIV-CHK-TX88446596 | 95927868000148 | 2.9900 | 3.4900 | -29,98 | — | | |
| DIV-CHK-TX88446647 | 95927868000148 | 2.9900 | 3.4900 | -11,23 | — | | |
| DIV-CHK-TX88446763 | 00520815000100 | 0.0000 | 0.8900 | -9,09 | — | | |
| DIV-CHK-TX88446585 | 95927868000148 | 2.4900 | 2.9900 | -5,13 | — | | |
| **5 linhas, todas ESTORNO** | | | | **-107,53** | 5 · -107,53; nenhuma taxa aplicada abaixo da contratada | `test_checkout.py::test_set_nenhuma_divergencia_com_taxa_aplicada_abaixo_da_contratada` | ✓ |

As 5 são estornos de checkout de vendas que já tinham sido cobradas acima do contratado: o estorno devolve a diferença, com sinal negativo. Os 4 spreads negativos da remessa, que estavam nesta lista, saíram pela R23.

---

## 5. Lançamentos classificados

### Por banco

| banco | lançamentos | soma | Esperado | teste de origem | |
|---|---:|---:|---|---|:-:|
| AURORA | 84 | -2.532.423,41 | 84 | `test_bancos.py::test_setembro_184_lancamentos_todos_por_regra` | ✓ |
| MERIDIANO | 100 | 1.116.335,23 | 100 | `test_bancos.py::test_setembro_184_lancamentos_todos_por_regra` | ✓ |
| **total** | 184 | -1.416.088,18 | 184 | `test_bancos.py::test_setembro_184_lancamentos_todos_por_regra` | ✓ |

### Por banco e conta

| banco | conta_codigo | lançamentos | soma | Esperado | teste de origem | |
|---|---|---:|---:|---|---|:-:|
| AURORA | 1.1.03.001 | 21 | 3.557.246,29 | 21 · 3.557.246,29 | `test_bancos.py::test_setembro_aurora_por_conta` | ✓ |
| AURORA | 1.1.09.001 | 4 | -1.450.000,00 | 4 · -1.450.000,00 | `test_bancos.py::test_setembro_aurora_por_conta` | ✓ |
| AURORA | 1.1.09.002 | 1 | 7.350,00 | 1 · 7.350,00 | `test_bancos.py::test_setembro_aurora_por_conta` | ✓ |
| AURORA | 2.1.01.001 | 45 | -4.217.867,61 | 45 · -4.217.867,61 (44 PIX ENVIADO + a devolução L65) | `test_bancos.py::test_setembro_aurora_por_conta`, `::test_setembro_aurora_repasses_sao_44_pix_mais_a_devolucao` | ✓ |
| AURORA | 2.1.03.001 | 1 | -9.811,20 | — | | |
| AURORA | 2.1.03.002 | 1 | -45.282,46 | — | | |
| AURORA | 2.1.03.003 | 1 | -21.877,40 | — | | |
| AURORA | 2.1.03.004 | 1 | -22.104,35 | — | | |
| AURORA | 2.1.04.001 | 1 | -184.732,18 | — | | |
| AURORA | 2.1.04.002 | 1 | -51.320,66 | — | | |
| AURORA | 2.1.04.003 | 1 | -14.778,57 | — | | |
| AURORA | 4.2.01 | 2 | -576,50 | 2 · -576,50 | `test_bancos.py::test_setembro_aurora_por_conta` | ✓ |
| AURORA | 4.2.02 | 1 | -28.450,00 | — | | |
| AURORA | 4.2.03 | 1 | -41.208,77 | — | | |
| AURORA | 4.2.04 | 1 | -2.210,00 | — | | |
| AURORA | 4.2.06 | 1 | -6.800,00 | 1 · -6.800,00 | `test_bancos.py::test_setembro_aurora_por_conta` | ✓ |
| MERIDIANO | 1.1.02.001 | 6 | -115.243,00 | 6 · -115.243,00 | `test_bancos.py::test_setembro_meridiano_por_conta` | ✓ |
| MERIDIANO | 1.1.03.002 | 1 | 61.884,12 | 1 · 61.884,12 | `test_bancos.py::test_setembro_meridiano_por_conta` | ✓ |
| MERIDIANO | 1.1.09.001 | 3 | 1.150.000,00 | 3 · 1.150.000,00 | `test_bancos.py::test_setembro_meridiano_por_conta` | ✓ |
| MERIDIANO | 2.1.02.001 | 85 | 18.240,00 | 85 · 18.240,00 (64 PIX RECEB + 21 TED ENVIADA) | `test_bancos.py::test_setembro_meridiano_por_conta` | ✓ |
| MERIDIANO | 3.2.01 | 1 | 3.912,66 | 1 lançamento | `test_bancos.py::test_setembro_meridiano_por_conta` | ✓ |
| MERIDIANO | 4.2.01 | 2 | -579,90 | 2 · -579,90 | `test_bancos.py::test_setembro_meridiano_por_conta` | ✓ |
| MERIDIANO | 4.2.05 | 1 | -1.830,44 | 1 lançamento | `test_bancos.py::test_setembro_meridiano_por_conta` | ✓ |
| MERIDIANO | 4.3.01 | 1 | -48,21 | 1 lançamento | `test_bancos.py::test_setembro_meridiano_por_conta` | ✓ |

### Por método

| metodo | lançamentos | soma | Esperado | teste de origem | |
|---|---:|---:|---|---|:-:|
| REGRA | 184 | -1.416.088,18 | todos REGRA | `test_bancos.py::test_setembro_184_lancamentos_todos_por_regra` | ✓ |
| IA | 0 | 0,00 | nenhum | `test_bancos.py::test_setembro_184_lancamentos_todos_por_regra` | ✓ |
| HUMANO | 0 | 0,00 | nenhum, e nenhuma PEN-SEMREGRA | `test_bancos.py::test_setembro_184_lancamentos_todos_por_regra` | ✓ |

---

## 6. Pendências

### Por tipo

| tipo | pendências | soma |
|---|---:|---:|
| CONFERENCIA_REPASSE | 1 | 39.543,45 |
| CONTESTACAO_PONTE | 5 | -2.147,13 |
| CREDITO_NAO_IDENTIFICADO | 1 | 7.350,00 |
| DEVOLUCAO_LOJISTA | 3 | 16.973,00 |
| DEVOLUCAO_PIX | 1 | 12.400,00 |
| LOJISTA_SEM_CONTRATO | 1 | 7.876,05 |
| NOTA_NAO_EMITIDA | 1 | -5,50 |
| OPERACAO_DUPLICADA | 1 | 821,88 |
| TRANSFERENCIA_EM_TRANSITO | 1 | 300.000,00 |
| **total** | 15 | 382.811,75 |

### Por quem decide

| quem_decide | pendências | soma |
|---|---:|---:|
| Comercial | 1 | 7.876,05 |
| Financeiro (Helena) | 14 | 374.935,70 |

Nenhum teste fixa os agregados por tipo ou por quem decide. As 15 pendências estão conferidas uma a uma abaixo.

### Lista completa

| id_saida | tipo | refs | valor | quem decide | Esperado | teste de origem | |
|---|---|---:|---:|---|---|---|:-:|
| PEN-NF-CHK-00520815000100 | NOTA_NAO_EMITIDA | 119 | -5,50 | Financeiro (Helena) | NOTA_NAO_EMITIDA · -5,50 | `test_checkout.py::test_set_notas` | ✓ |
| PEN-DEVOL-CHK-00520815000100 | DEVOLUCAO_LOJISTA | 118 | 15.396,77 | Financeiro (Helena) | 118 · 15.396,77 | `test_checkout.py::test_set_divergencias` | ✓ |
| PEN-DEVOL-CHK-22224579000109 | DEVOLUCAO_LOJISTA | 5 | 29,95 | Financeiro (Helena) | 5 · 29,95 | `test_checkout.py::test_set_divergencias` | ✓ |
| PEN-DEVOL-CHK-95927868000148 | DEVOLUCAO_LOJISTA | 87 | 1.546,28 | Financeiro (Helena) | 87 · 1.546,28 | `test_checkout.py::test_set_divergencias` | ✓ |
| PEN-SEMCONTRATO-1076801732 | LOJISTA_SEM_CONTRATO | 57 | 7.876,05 | Comercial | 57 · 7.876,05 · LOJISTA_SEM_CONTRATO · Comercial; motivo com 57 transações, 262138.61 brutos, competência 2026-10 e retroativa a 2026-09-10 (R30) | `test_checkout.py::test_set_atlas_sem_contrato` | ✓ |
| PEN-CONTEST-REM-17217888000111 | CONTESTACAO_PONTE | 23 | 1.418,85 | Financeiro (Helena) | 23 refs · 1.418,85 | `test_remessa.py::test_set_pendencias` | ✓ |
| PEN-NEG-REM-PC-0926-0326 | CONTESTACAO_PONTE | 1 | -1.001,30 | Financeiro (Helena) | -1.001,30 | `test_remessa.py::test_set_pendencias` | ✓ |
| PEN-NEG-REM-PC-0926-0545 | CONTESTACAO_PONTE | 1 | -637,91 | Financeiro (Helena) | -637,91 | `test_remessa.py::test_set_pendencias` | ✓ |
| PEN-NEG-REM-PC-0926-0491 | CONTESTACAO_PONTE | 1 | -574,90 | Financeiro (Helena) | -574,90 | `test_remessa.py::test_set_pendencias` | ✓ |
| PEN-NEG-REM-PC-0926-0210 | CONTESTACAO_PONTE | 1 | -1.351,87 | Financeiro (Helena) | -1.351,87 | `test_remessa.py::test_set_pendencias` | ✓ |
| PEN-DUP-REM-PC-0926-0162 | OPERACAO_DUPLICADA | 1 | 821,88 | Financeiro (Helena) | 821,88; a operação entra uma vez só na COM-REM e na NF-REM (410,94) | `test_remessa.py::test_set_pendencias`, `::test_set_pc_0926_0162_repetida_conta_uma_vez_e_vira_pendencia` | ✓ |
| PEN-TED-PONTE | CONFERENCIA_REPASSE | 228 | 39.543,45 | Financeiro (Helena) | 228 refs · 39.543,45 = NF-REM | `test_remessa.py::test_set_pendencias` | ✓ |
| PEN-NAOID-L50 | CREDITO_NAO_IDENTIFICADO | 1 | 7.350,00 | Financeiro (Helena) | 7.350,00 · Financeiro (Helena) | `test_bancos.py::test_setembro_pendencias_r20` | ✓ |
| PEN-DEVOL-PIX-L65 | DEVOLUCAO_PIX | 1 | 12.400,00 | Financeiro (Helena) | 12.400,00 · Financeiro (Helena) | `test_bancos.py::test_setembro_pendencias_r20` | ✓ |
| PEN-TRANSF-L92 | TRANSFERENCIA_EM_TRANSITO | 1 | 300.000,00 | Financeiro (Helena) | 300.000,00 · TRANSFERENCIA_EM_TRANSITO | `test_bancos.py::test_setembro_uma_transferencia_em_transito` | ✓ |

Pendências que os testes exigem que **não** existam, e de fato não existem:

| ausência | teste de origem | |
|---|---|:-:|
| PEN-SEMREGRA-* (lançamento sem regra) | `test_bancos.py::test_setembro_184_lancamentos_todos_por_regra` | ✓ |
| PEN-TED-LIQ-* (TED de liquidação × Ponte) | `test_bancos.py::test_setembro_ted_liq_bate_com_a_ponte` | ✓ |
| PEN-PIX-REM-* (PIX × remessas por cliente) | `test_bancos.py::test_setembro_pix_da_ponte_aerea_e_adiantamento_sem_pendencia` | ✓ |
| PEN-PIX-SEMREM-* e qualquer pendência com MRD2026090425 (adiantamento, R22); o LAN-MER-MRD2026090425 fica em 2.1.02.001 · REGRA · 1,00 | `test_bancos.py::test_setembro_pix_da_ponte_aerea_e_adiantamento_sem_pendencia` | ✓ |
| PEN-FORA-*, PEN-NAOCAD-*, PEN-NF-* da remessa | `test_remessa.py::test_set_pendencias` | ✓ |
| PEN-NF-CHK de outro lojista além da Casa do Estudante | `test_checkout.py::test_set_notas` | ✓ |

---

## 7. Outubro simulado

O pack de outubro é gerado a partir do de setembro: todas as datas avançam um mês e entram quatro casos novos, um por arquivo (`tests/gerar_outubro.py`). Comandos, com a pasta temporária fora do repositório:

```
python tests/gerar_outubro.py dados/2026-09 <tmp>/dados/2026-10
python -m tarvo fechar --competencia 2026-10 --entrada <tmp>/dados/2026-10 --saida <tmp>/saida --sem-ia
python -m tarvo resumo --saida <tmp>/saida
```

Resultado: 506 itens, `validar_saida` sem problemas, rastro fechando em 506 de 506. Linhas: comissões 36, divergências 242, notas 21, lançamentos 186, pendências 21, rastro 5.209.

### O que cada caso novo gerou

Para cada caso, a tabela lista todos os id_saida que têm a referência nova no rastro.csv:

| caso | referência nova | id_saida que a usam | Esperado | teste de origem | |
|---|---|---|---|---|:-:|
| (a) Orbe: venda de EC fora da planilha (1099300457), R$ 2.450,00 a 2,69% | TX88999001 | **PEN-SEMCONTRATO-1099300457**: LOJISTA_SEM_CONTRATO, 65,90 (o que a Orbe cobrou), Comercial | só a PEN-SEMCONTRATO; sem comissão, nota ou divergência | `test_outubro.py::test_caso_a_venda_de_ec_fora_da_planilha_vira_so_pendencia` | ✓ |
| (b) Aurora: "PIX ENVIADO GRAFICA RAPIDA LTDA", -1.250,00 | L49 | LAN-AUR-L49 (A_CLASSIFICAR · HUMANO · 0,00) e **PEN-SEMREGRA-L49**: LANCAMENTO_SEM_REGRA, -1.250,00 | só esses dois; A_CLASSIFICAR/HUMANO/0.00 | `test_outubro.py::test_casos_b_c_pix_fora_das_listas_ficam_a_classificar` | ✓ |
| (c) Meridiano: "PIX RECEB INSTITUTO SAKURA IDIOMAS", +25.000,00 | MRD2026100446 | LAN-MER-MRD2026100446 (A_CLASSIFICAR · HUMANO · 0,00) e **PEN-SEMREGRA-MRD2026100446**: LANCAMENTO_SEM_REGRA, 25.000,00 | só esses dois; nenhuma conferência PIX × remessa | `test_outubro.py::test_casos_b_c_pix_fora_das_listas_ficam_a_classificar` | ✓ |
| (d) Ponte: operação de CNPJ fora da planilha (41928553000196) | PC-1026-9001 | COM-REM-41928553000196 (121,50), NF-REM-75374179000146 (121,50 dos 39.664,95), PEN-TED-PONTE (121,50), **PEN-NAOCAD-REM-41928553000196**: LOJISTA_NAO_CADASTRADO, 121,50, **PEN-TED-LIQ-2026-10-14**: DIVERGENCIA_TED_LIQUIDACAO, 16.505,48, **PEN-PIX-REM-41928553000196**: DIFERENCA_PIX_REMESSA, -16.505,48 | exatamente esses 6 id_saida, sem DIV-; comissão = 50% do spread | `test_outubro.py::test_caso_d_operacao_de_cnpj_fora_da_planilha` | ✓ |

**Pendências novas: 6** (as que estão em negrito). Elas explicam a diferença entre as 15 pendências de setembro e as 21 de outubro. 16.505,48 é valor_brl + iof_brl da operação nova, que não tem TED de liquidação nem PIX do cliente. O rastro da PEN-TED-LIQ-2026-10-14 traz as 10 referências do dia: as outras 9 (8 operações e a TED do dia) somam zero entre si.

### Nada vira definitivo por engano

| verificação | resultado | |
|---|---|:-:|
| (a), (b) e (c) em comissoes_por_lojista.csv | nenhuma linha | ✓ |
| (a), (b) e (c) em notas_a_emitir.csv | nenhuma | ✓ |
| (a), (b), (c) e (d) em divergencias_taxa.csv | nenhuma | ✓ |
| (b) e (c) em lancamentos_classificados.csv como lançamento definitivo | não: os dois têm conta_codigo A_CLASSIFICAR (não é conta do plano, de propósito), metodo HUMANO e confiança 0,00 (P09). Por método: REGRA 184, IA 0, HUMANO 2 (23.750,00) | ✓ |
| (d) em comissão e nota | **sim, de propósito (P04)** | ver abaixo |

**A exceção da P04.** A operação PC-1026-9001 entra na comissão (COM-REM-41928553000196, R$ 121,50 = 50% do Spread R$ 243,00) e na nota da Ponte (39.543,45 + 121,50 = 39.664,95). A Ponte paga a participação pelo realizado, com ou sem cadastro nosso (R11, R16). Deixar a operação de fora faria a nota sair menor que o repasse. O que falta é o cadastro, e isso vira a PEN-NAOCAD-REM. Não há divergência porque não existe spread contratado para comparar (R15).

### Outras diferenças de outubro, que não vêm dos casos novos

Os números mudam com o deslocamento das datas, como prevê `test_outubro.py`. Nenhum dos id_saida abaixo usa referência nova no rastro.

- **PEN-NF-CHK da Casa do Estudante: 0,00 em vez de -5,50.** O estorno TX88445133 era de venda de 21/08 (taxa de 1,49%). Em outubro a venda original cai em 21/09, dentro da tarifa zerada da R10. A comissão do estorno vira 0,00, e os -5,50 passam para a divergência e para a devolução (PEN-DEVOL-CHK: 119 refs, 15.391,27).
- **Bridge: 13 divergências e devolução de 108,84, contra 5 e 29,95.** A Orbe cobrou 2,59% em 13 vendas de crédito à vista. Em setembro, 8 delas (de 01 a 13/09) estavam dentro do contrato antigo, que valia até 14/09. Em outubro todas caem depois de 15/09 e passam a valer a taxa renegociada de 2,19%, então as 13 viram divergência (`test_outubro.py::test_bridge_vendas_de_outubro_na_taxa_nova`).
- **PEN-SEMCONTRATO-1076801732 (R30):** o motivo cita a competência 2026-11 e a data 2026-10-10, porque no pack simulado a Atlas começa em 10/10. O valor (7.876,05) não muda.
- **PEN-TRANSF-L93:** a transferência do fim do mês passa a cair em 02/11, a conferir no extrato de novembro.

---

## Escolhas de interpretação (P15 a P21)

Premissas do HIPOTESES.md (seção 2.1) que a revisão independente questionou e que foram mantidas. Para cada uma: o número de setembro que ela afeta e o valor que esse número teria na leitura alternativa. A P15 foi substituída depois pela R23 e aparece invertida: o valor adotado é o da R23, e a alternativa é a antiga P15.

Os valores alternativos **não são valores de teste**. P16, P19 e P20 são contas sobre os CSVs de `saida/`; a alternativa da P15 é a saída do commit `db29cf0`. P17, P18 e P21 foram calculados à parte, com um script descartável que usa os leitores e `remessa.calcular_operacao` sem alterá-los, sobre `dados/2026-09`.

| premissa | escolha adotada | número afetado | valor adotado | leitura alternativa | valor na alternativa |
|---|---|---|---:|---|---:|
| **P15** (substituída pela R23) | R23: spread negativo só como contestação, fora das divergências | linhas de remessa em divergencias_taxa.csv · soma | 23 · 1.418,85 | P15 antiga: listar também como divergência (a Helena permite, desde que fique claro que é outra natureza) | **27 · -2.147,13** |
| | | total de divergencias_taxa.csv · soma | 233 · 18.392,50 | | 237 · 14.826,52 |
| | | divergências negativas | 5 (só os estornos de checkout) | | 9 |
| **P16** | devolução de PIX (L65, +12.400,00) em 2.1.01.001 (validada pela Helena às 9h48: as duas contas servem; critério fixo) | AURORA 2.1.01.001 · soma | 45 · -4.217.867,61 | L65 em 2.1.01.002 (Devoluções e créditos a lojistas) | **44 · -4.230.267,61**, e 2.1.01.002 com 1 · 12.400,00 |
| **P17** | diferença de remessa pelo Spread % do relatório: (Spread % − contratado) / 100 × PTAX × Valor ME | DIV-REM Mundo Aberto (23 linhas) e PEN-CONTEST-REM-17217888000111 | 1.418,85 | pelo Spread R$: Spread R$ − contratado / 100 × PTAX × Valor ME, por operação | **1.418,88** |
| | | PEN-NEG-REM-PC-0926-0326 · PEN-NEG-REM-PC-0926-0491 | -1.001,30 · -574,90 | | -1.001,29 · -574,91 (os 4 negativos continuam somando -3.565,98) |
| | | CONTESTACAO_PONTE (5 pendências) | -2.147,13 | | -2.147,10 |
| **P18** | contestação do spread negativo pela diferença contra o contrato (mesmo cálculo de P17) | 4 PEN-NEG-REM: PC-0926-0210 · 0326 · 0491 · 0545 | -1.351,87 · -1.001,30 · -574,90 · -637,91 = **-3.565,98** | pelo Spread R$ negativo da operação | -687,52 · -509,22 · -292,28 · -345,03 = **-1.834,05** |
| | | CONTESTACAO_PONTE (5 pendências) · total de pendencias.csv | -2.147,13 · 382.811,75 | | -415,20 · 384.543,68 |
| **P19** | PEN-DUP pelo Spread R$ da cópia descartada | PEN-DUP-REM-PC-0926-0162 | 821,88 (o quanto o rodapé de 78.073,59 está inflado) | pela parte da Tarvo na cópia (50%, R11) | **410,94** |
| **P20** | transferência de 30/09 mantida como pendência até a conciliação de outubro | pendencias.csv: quantidade · soma | 15 · 382.811,75 | sem a PEN-TRANSF-L92, já que a R20 explica a transferência | **14 · 82.811,75** |
| | | "Financeiro (Helena)" | 14 · 374.935,70 | | 13 · 74.935,70 |
| **P21** | Atlas (EC 1076801732) fora de comissoes_por_lojista; o que a Orbe cobrou fica em PEN-SEMCONTRATO | comissões CHECKOUT: lojistas · soma | 21 · 207.039,73 | faturar a Atlas pela aba "ANTIGO 2025 - nao usar" (CNPJ 39566044000119; débito 1,69%, crédito à vista 2,99%, parcelado 3,49%, Pix 0,99%) | **22 · 211.417,02** (+4.377,29 em 50 linhas; as 7 de antecipação e reversão ficam sem taxa, porque a aba de 2025 não tem antecipação) |
| | | notas CHECKOUT | 20 | | 21 |
| | | divergências da Atlas | 0 | | 41 linhas · 827,22 (a Orbe aplicou taxas diferentes das de 2025) |
| | | PEN-SEMCONTRATO-1076801732 | 7.876,05 | | deixa de existir |

A leitura alternativa da P21 contraria a R08 ("a aba de 2025 não vale"). Ela aparece aqui só para mostrar o tamanho do efeito.
