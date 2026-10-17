# Resultados do fechamento — setembro/2026

**Status do fechamento: COMPLETO** — nenhuma fonte bloqueada: o `fechar` terminou com "FECHAMENTO COMPLETO" e código 0 (R44).

| | |
|---|---|
| Data | 2026-10-17 |
| Commit do código | o commit que contém este arquivo (`git log -1 --format=%h -- RESULTADOS.md`; um hash escrito aqui ficaria velho no commit seguinte). O resumo gerado (`python -m tarvo resumo`, `resumo.versao_do_codigo`) imprime o commit atual (`git rev-parse --short HEAD`) e a branch; sem git, "commit indisponível" |
| Fechamento | `python -m tarvo fechar --competencia 2026-09 --entrada dados/2026-09 --saida saida/` (IA conforme `config/ia.yaml`; em setembro todo lançamento casa uma regra, então a IA não é chamada nenhuma vez, P14) |
| Resumo | `python -m tarvo resumo --saida saida` |
| Registro da execução (O06) | `auditoria/execucao.md` e `auditoria/execucao.json`: a última execução do `fechar`, com data e hora, commit, comando, cada arquivo de entrada (tipo, tamanho, SHA-256, linhas lidas), arquivos ignorados, fontes bloqueadas, status e código de saída, e linhas e total de cada CSV de `saida/` |
| pytest | **489 passed** (`python -m pytest -q`) |
| `validar_saida(saida/)` | `[]`, **sem problemas** |
| Rastro | 371 de 371 itens com soma do rastro por id_saida = valor reportado |

**R49 a R60 (Helena, 17/10, 10h59 a 16h08) e O07 (Organização, 15h54).** Nenhum número de setembro mudou: saida/ tem os mesmos 6 CSVs, e só o pendencias.csv mudou, em motivo e quem_decide de 5 linhas (valores, referências e rastro iguais); contestacoes/ ficou idêntico byte a byte. O que mudou nas 5 pendências: PEN-TED-PONTE (o motivo não supõe como a Ponte vai pagar, R18), PEN-NAOID-L50 (o Caio identifica o pagador com o banco até o fechamento de outubro), PEN-TRANSF-L92 (se não aparecer no extrato de outubro, vira pendência da tesouraria), PEN-CONCESSAO-CHK (acrescenta a renovação da isenção depois de 31/12/2026, Comercial) e PEN-SEMCONTRATO da Atlas (quem_decide "Comercial (Diego)"). Conferido nos dados: as 4 antecipações da Casa estão na concessão pela data da antecipação (R49); nenhuma transação com mais de 12 parcelas (R50); Fluente a 0,79% sem divergência nem pendência (R58); CNPJ da Fluente e da Campus Global com 14 dígitos em toda a saída (R57); classificação do Pix da contabilidade, rendimento, seguro, IOF e CDB como antes (R59). Código: uma transação com mais de 12 parcelas vira PEN-REGRA-TAXA (R50) e as PEN-REGRA de cadastro, vigência e taxa passam a "Comercial" (R51), sem caso em setembro.

**R46 a R48 (Helena, 17/10, 13h34 a 14h10) e O06 (Organização, 14h11).** Com todos os arquivos, o fechamento continua completo (código 0). Nenhum número de setembro mudou: as três regras novas não têm caso em setembro (nenhuma linha de agosto nos arquivos da Orbe, nenhum id corrigido, toda original do 06 está no 01), e a R47 confirma o que o código já fazia. O rastro.csv ganhou duas colunas no fim (O06).

| arquivo | linhas antes → depois | total antes → depois | o que mudou e a regra |
|---|---:|---:|---|
| comissoes_por_lojista.csv, divergencias_taxa.csv, notas_a_emitir.csv, lancamentos_classificados.csv, pendencias.csv | 35, 115, 21, 184, 16 (iguais) | iguais | idênticos byte a byte |
| rastro.csv | 5.086 → 5.086 | -543.718,70 → -543.718,70 | colunas extras no fim, `regra` e `detalhe` (O06); as 4 obrigatórias, idênticas linha a linha e na mesma ordem (conferido por script: as 4 primeiras colunas de cada linha, antes e depois). Nenhuma linha sem regra: R01 3.358, R11 684, R32 236, R45 210, R19 154, R35 134, R03 88, R05 72, R30 57, R15 46, R21 21, R20 11, R34 4, R37 4, P26 5, R13 1, P06 1 |
| contestacoes/ (orbe.md, orbe_operacoes.csv, ponte.md, ponte_operacoes.csv) | iguais | iguais | idênticos byte a byte |
| auditoria/execucao.json, execucao.md | não existiam | | registro da execução (O06) |

O que cada regra muda quando o caso aparecer (testes em pastas temporárias):

| regra | o que o fechamento faz | teste |
|---|---|---|
| P27 (critério nosso, Helena 13h34) | id_transacao que volta num arquivo posterior com dados diferentes: a linha do arquivo posterior substitui a do relatório, o resto do arquivo é lido, e a PEN-CORRECAO-ORBE-<id> traz antes → depois, o efeito em R$ na comissão e na nota, "a Helena confirma a correção com a Orbe" e "Financeiro (Helena)". Valor = efeito na comissão. O checkout não fica provisório, e o fechamento sai COMPLETO (código 0). Antes: o arquivo inteiro ficava bloqueado e o checkout, provisório | `test_fechamento.py::test_reenvio_com_linha_diferente_vale_a_correcao_e_o_resto_e_lido` (07 corrige a venda TX88447225 do Kiwi de 5.480,00 para 5.000,00: PEN-CORRECAO-ORBE-TX88447225 de -15,31) |
| R46 (13h34) | linha da Orbe com data_movimento de mês anterior na pasta da competência: é lida e entra no mês (não há filtro por data); PEN-TARDIO-CHK-<mês>-<arquivo>, 0,00, "ajuste de 2026-08 recebido depois da aprovação, entra em 2026-09 (regra 13h34)" | `test_fechamento.py::test_ajuste_de_agosto_na_pasta_de_setembro_entra_em_setembro` |
| R47 (14h08) | bandeira não entra na taxa nem no vínculo do estorno; os 7 estornos do 06 com bandeira diferente da venda (TX88447011, -030, -044, -057, -070, -093, -109) só aparecem em COM-CHK e NF-CHK | `test_checkout.py::test_set_estornos_com_bandeira_diferente_da_venda_sem_pendencia_nem_divergencia` |
| R48 (14h10) | estorno ou reversão sem a original entra pelo valor que veio; a PEN-SEMORIG-CHK vale o efeito na comissão (era 0,00), com "a Helena pede a venda original à Orbe" | `test_checkout.py::test_estorno_sem_a_original_entra_pelo_valor_que_veio_e_a_pendencia_vale_o_efeito` |

**R41 a R45 (Helena, 17/10, 11h49 a 12h50).** Com todos os arquivos, o fechamento continua completo (código 0). Mudaram só o valor das devoluções (R45, centavos) e textos (R41, R43, R45); a R42 e a R44 não mudam nenhum número de setembro.

| arquivo | linhas antes → depois | total antes → depois | o que mudou e a regra |
|---|---:|---:|---|
| comissoes_por_lojista.csv | 35 → 35 | 243.278,79 → 243.278,79 | idêntico byte a byte |
| divergencias_taxa.csv | 115 → 115 | 2.995,08 → 2.995,08 | idêntico: a divergência continua pela fórmula da R03 (R45) |
| notas_a_emitir.csv | 21 → 21 | 243.284,29 → 243.284,29 | idêntico |
| lancamentos_classificados.csv | 184 → 184 | -1.416.088,18 → -1.416.088,18 | idêntico (R42: o fechamento só classifica o que passou nos extratos, como já fazia) |
| pendencias.csv | 16 → 16 | 382.811,75 → **382.811,32** | R45: PEN-DEVOL-CHK-22224579000109 (Bridge) 29,95 → **29,94**; PEN-DEVOL-CHK-95927868000148 (Rota Global) 1.546,28 → **1.545,86**; o motivo das duas diz "valor_taxa descontado pela Orbe menos a comissão pela taxa contratada, transação a transação (R45)". PEN-CONCESSAO-CHK-00520815000100: valor igual (15.396,77), motivo com R41 e R45. PEN-ALERTA-ANTEC-39566044000119: valor 0,00, motivo pelo pico (P26, R43) |
| rastro.csv | 5.086 → 5.086 | -543.718,27 → **-543.718,70** | mesmas linhas, na mesma ordem; mudou o valor de 47 linhas das PEN-DEVOL-CHK, todas por 1 centavo (o descontado de fato contra a fórmula): 1 da Bridge (-0,01) e 46 da Rota (44 com -0,01 e 2 com +0,01) |
| contestacoes/orbe_operacoes.csv | 92 → 92 | 1.576,23 → 1.576,23 | idêntico: o e-mail cobra da Orbe pela fórmula |
| contestacoes/orbe.md | 51 → 51 linhas | | notas internas, "Valor a devolver a cada lojista (R25, R45)": Bridge **R$ 29,94** e Rota **R$ 1.545,86**, com a cobrança à Orbe pela fórmula ao lado (R$ 29,95 e R$ 1.546,28) e a diferença explicada (a Orbe trunca o valor_taxa, P03). O corpo do e-mail não mudou |
| contestacoes/ponte_operacoes.csv, ponte.md | 28 → 28 | -1.325,25 → -1.325,25 | idênticos |

Motivo da PEN-ALERTA-ANTEC-39566044000119 (Atlas), antes → depois:
- antes: "lojista sem histórico (...) antecipou R$ 235943.10 brutos (R$ 127230.96 líquidos das reversões) contra R$ 135428.90 de vendas no mês"
- depois: "lojista sem histórico (...) - pico em 2026-09-15: R$ 179592.82 antecipados contra R$ 55357.50 vendidos, acumulados desde a primeira transação - reversões, que não apagam o alerta: AN88445637 revertida em 2026-09-17 (AN88446030), AN88446517 revertida em 2026-09-26 (AN88446660) - fim do mês: R$ 127230.96 antecipados, líquidos das reversões, contra R$ 135428.90 de vendas (R$ 235943.10 antecipados brutos)"

Conferências pedidas:

| item | o que foi conferido | resultado |
|---|---|---|
| 1. Casa (R41) | PEN-CONCESSAO-CHK-00520815000100: 15.396,77, tipo DEVOLUCAO_CONCESSAO, 118 linhas no rastro somando 15.396,77; o CNPJ 00520815000100 não está em divergencias_taxa.csv, nem em orbe_operacoes.csv, nem no corpo do orbe.md (só nas notas internas) | OK, sem mudança |
| 2. Provisão (R42) | os 184 lançamentos têm exatamente uma origem no rastro, cada uma numa linha do Aurora (L9 a L92) ou do Meridiano (FITID); nenhuma pendência fala em provisão; R24 e os comentários de config/bancos.yaml reescritos ("o pagamento de competência anterior baixa a provisão feita pela contabilidade; a provisão do mês fica fora do fechamento") | OK, nenhum número mudou |
| 3. Alerta (P26, R43) | só a Atlas acende, pelo pico em 15/09 (179.592,82 × 55.357,50). Kiwi, Mundo Aberto, Oxford, Dublin Hub e Canguru têm um dia acima, mas têm histórico. **Com o 06, ninguém acende nem apaga:** a Atlas não tem linha no 06, e o pico de cada lojista com linha no 06 é o mesmo com e sem ele (as 3 reversões do 06 são de 30/09; os estornos e a venda do Kiwi têm a original em setembro e não mudam o histórico) | OK |
| 4. Devolução (R45) | Bridge 29,95 → 29,94; Rota 1.546,28 → 1.545,86; Casa 15.396,77 → 15.396,77 (na concessão a comissão é 0%, a devolução já era o valor_taxa) | OK |
| 6. Completo | só mudaram as PEN-DEVOL (valor) e textos com regra; nenhuma diferença sem regra | OK |

**Fechamento parcial (R44).** Uma fonte ausente, ambígua (dois arquivos num tipo de arquivo único) ou ilegível (coluna obrigatória faltando, erro de leitura) fica bloqueada: o que depende dela não sai, o resto fecha, e a PEN-BLOQUEIO-<tipo> (valor 0,00) diz o arquivo, o erro, o que não foi gerado e o próximo passo. Mapa de dependências, tirado do código (`src/tarvo/dependencias.py`):

| produto | fontes | |
|---|---|---|
| checkout (comissões, notas NF-CHK, divergências, pendências de checkout) | orbe + taxas | |
| remessa (comissões, nota NF-REM, divergências, pendências, PEN-TED-PONTE) | ponte_eml + taxas | |
| lançamentos do Aurora | aurora + plano_de_contas | lê a planilha de taxas só para conferir os CNPJs de favorecidos.yaml (P07) |
| lançamentos do Meridiano | meridiano + plano_de_contas | idem, pagadores_meridiano.yaml (P08) |
| conferência TEDs × operações da Ponte (P11) | meridiano + plano_de_contas + ponte_eml | sem um lado: PEN-SEMCONF-TED-LIQ |
| conferência PIX × remessas (P12) | meridiano + plano_de_contas + ponte_eml | sem um lado: PEN-SEMCONF-PIX-REM |
| conferência transferências Aurora × Meridiano (P13) | aurora + meridiano + plano_de_contas | sem um lado: PEN-SEMCONF-TRANSF |
| rascunho orbe.md (R29) | orbe + taxas | bloqueado: aviso no .md, CSV só com cabeçalho |
| rascunho ponte.md (R29) | ponte_eml + taxas | idem |

Os casos de teste, em cópias temporárias de `dados/2026-09` (`tests/test_parcial.py`, `tests/test_fechamento.py`):

| caso | código | o que fechou | o que ficou bloqueado (não gerado) | pendências geradas |
|---|:-:|---|---|---|
| sem o `.ofx` | 3 | checkout, remessa, Aurora (84 lançamentos), as 2 contestações | Meridiano (100 lançamentos), P11, P12, P13 (a PEN-TRANSF-L92 não sai) | PEN-BLOQUEIO-MERIDIANO; PEN-SEMCONF-TED-LIQ e PEN-SEMCONF-PIX-REM (5.611.447,12, as operações da Ponte do mês); PEN-SEMCONF-TRANSF (-1.450.000,00, as transferências do Aurora) |
| sem o `.eml` | 3 | checkout, Aurora, Meridiano, P13, orbe.md | remessa (COM-REM, NF-REM, DIV-REM, PEN-*-REM, PEN-TED-PONTE), P11, P12, ponte.md | PEN-BLOQUEIO-PONTE_EML; PEN-SEMCONF-TED-LIQ (-5.611.447,12, as TEDs LIQ OPERACOES) e PEN-SEMCONF-PIX-REM (5.629.687,12, os PIX de clientes), com rastro em cada FITID |
| planilha de taxas duplicada (`_v2` ou ` (1)`) | 3 | Aurora, Meridiano, P11, P12, P13 (CNPJs das listas sem conferência com a planilha) | checkout, remessa, as 2 contestações | PEN-BLOQUEIO-TAXAS, quem_decide "Comercial e Financeiro (Helena)", com o texto de CORREÇÃO ou COMPLEMENTO |
| relatório da Orbe com `valor_taxa` renomeada | 3 | remessa, Aurora, Meridiano, conferências, ponte.md | checkout, orbe.md | PEN-BLOQUEIO-ORBE: "01_orbe_relatorio_comissoes_set2026.csv: colunas ausentes no cabeçalho: ['valor_taxa']", rastro na L1 |
| arquivo 06 com cabeçalho diferente | 3 | tudo; o checkout sem o 06, com `situacao` = PROVISORIO, e o orbe.md com aviso de provisório | só o 06 (14 linhas) | PEN-BLOQUEIO-ORBE-06_orbe_ajustes_tardios_set2026.csv (ARQUIVO_BLOQUEADO) |
| coluna a mais (Aurora com "Categoria") | 0 | tudo, igual ao completo byte a byte, fora pendencias.csv e rastro.csv | nada | PEN-AVISO-LAYOUT-AURORA (AVISO_LAYOUT, 0,00) |
| outros (`tests/test_fechamento.py`, `test_parcial.py`) | 3 | id do 06 reenviado num 07 com dados diferentes: desde a P27 de 17/10, 13h34, não bloqueia mais (código 0, a linha do 07 vale e abre PEN-CORRECAO-ORBE); segundo `.eml`: ponte ambígua; planilha que não é xlsx: ilegível (BadZipFile); pasta vazia: as 6 fontes bloqueadas, saída válida | | |

Saída real da CLI, sem o `.eml` (código 3):

```
Competência: 2026-09
Entrada: C:\Users\anton\AppData\Local\Temp\cen_sem_eml_9_s9g3u7\entrada
Saída: C:\Users\anton\AppData\Local\Temp\cen_sem_eml_9_s9g3u7\saida
IA nos extratos: conforme config/ia.yaml
Arquivos encontrados (5):
  orbe: 01_orbe_relatorio_comissoes_set2026.csv, 06_orbe_ajustes_tardios_set2026.csv
  taxas: 02_tabela_taxas_contratadas.xlsx
  plano_de_contas: 04_plano_de_contas_fenix_erp.csv
  aurora: 05a_extrato_banco_aurora_cc4471_set2026.csv
  meridiano: 05b_extrato_banco_meridiano_cc90233_set2026.ofx
Aviso: 2 arquivo(s) da pasta de entrada não foram lidos (não afetam o fechamento; se algum deles é um arquivo do mês, renomeie para casar com o padrão):
  00_LEIA-ME.md: não casa com nenhum padrão de config/entradas.yaml
  01_instrucoes_participantes.docx: não casa com nenhum padrão de config/entradas.yaml
Itens de saída: 329
Arquivos gravados (6), validados sem problemas:
  comissoes_por_lojista.csv
  divergencias_taxa.csv
  notas_a_emitir.csv
  lancamentos_classificados.csv
  pendencias.csv
  rastro.csv
Rascunhos de contestação gravados (4), a Helena revisa antes de enviar:
  orbe.md (C:\Users\anton\AppData\Local\Temp\cen_sem_eml_9_s9g3u7\contestacoes)
  orbe_operacoes.csv (C:\Users\anton\AppData\Local\Temp\cen_sem_eml_9_s9g3u7\contestacoes)
  ponte.md (C:\Users\anton\AppData\Local\Temp\cen_sem_eml_9_s9g3u7\contestacoes)
  ponte_operacoes.csv (C:\Users\anton\AppData\Local\Temp\cen_sem_eml_9_s9g3u7\contestacoes)

FECHAMENTO PARCIAL — fontes bloqueadas: ponte_eml (ausente); não gerado: remessa (comissões, nota da Ponte, divergências e pendências de remessa, inclusive a conferência do TED de repasse PEN-TED-PONTE); conferência das TEDs de liquidação com as operações da Ponte (P11); conferência dos PIX recebidos com as remessas por cliente (P12); rascunho de contestação da Ponte (R29); ver pendências PEN-BLOQUEIO
```

Saída real da CLI, com o 06 de cabeçalho diferente (`id_transacao` → `id_trans`; código 3):

```
Competência: 2026-09
Entrada: C:\Users\anton\AppData\Local\Temp\cen_ajustes_cabecalho_8483oy2b\entrada
Saída: C:\Users\anton\AppData\Local\Temp\cen_ajustes_cabecalho_8483oy2b\saida
IA nos extratos: conforme config/ia.yaml
Arquivos encontrados (6):
  orbe: 01_orbe_relatorio_comissoes_set2026.csv, 06_orbe_ajustes_tardios_set2026.csv
  taxas: 02_tabela_taxas_contratadas.xlsx
  ponte_eml: 03_email_ponte_cambio_relatorio_set2026.eml
  plano_de_contas: 04_plano_de_contas_fenix_erp.csv
  aurora: 05a_extrato_banco_aurora_cc4471_set2026.csv
  meridiano: 05b_extrato_banco_meridiano_cc90233_set2026.ofx
Aviso: 2 arquivo(s) da pasta de entrada não foram lidos (não afetam o fechamento; se algum deles é um arquivo do mês, renomeie para casar com o padrão):
  00_LEIA-ME.md: não casa com nenhum padrão de config/entradas.yaml
  01_instrucoes_participantes.docx: não casa com nenhum padrão de config/entradas.yaml
Itens de saída: 372
Arquivos gravados (6), validados sem problemas:
  comissoes_por_lojista.csv
  divergencias_taxa.csv
  notas_a_emitir.csv
  lancamentos_classificados.csv
  pendencias.csv
  rastro.csv
Rascunhos de contestação gravados (4), a Helena revisa antes de enviar:
  orbe.md (C:\Users\anton\AppData\Local\Temp\cen_ajustes_cabecalho_8483oy2b\contestacoes)
  orbe_operacoes.csv (C:\Users\anton\AppData\Local\Temp\cen_ajustes_cabecalho_8483oy2b\contestacoes)
  ponte.md (C:\Users\anton\AppData\Local\Temp\cen_ajustes_cabecalho_8483oy2b\contestacoes)
  ponte_operacoes.csv (C:\Users\anton\AppData\Local\Temp\cen_ajustes_cabecalho_8483oy2b\contestacoes)

FECHAMENTO PARCIAL — fontes bloqueadas: orbe (só o arquivo 06_orbe_ajustes_tardios_set2026.csv); não gerado: nada; ver pendências PEN-BLOQUEIO
  provisório (coluna situacao = PROVISORIO nos CSVs; aviso nas notas do rascunho): checkout (comissões, notas, divergências e pendências de checkout); rascunho de contestação da Orbe (R29)
```

Testes: 408 → 437. Mudaram, por regra:
- `test_checkout.py::test_set_divergencias`: PEN-DEVOL 1.546,28 → 1.545,86 e 29,95 → 29,94 (R45); as DIV-CHK não mudam.
- `test_checkout.py::test_devolucao_sem_condicao_continua_pela_formula_da_r03` → `test_devolucao_e_o_descontado_de_fato_e_a_divergencia_continua_pela_formula` (R45: 10,01 → 10,00; a DIV continua 10,01).
- `test_checkout.py::test_set_alerta_de_antecipacao_so_a_atlas` e `::test_alerta_de_antecipacao_so_para_lojista_sem_historico`: o motivo pelo pico (P26, R43). `::test_concessao_zera_a_comissao_mas_a_divergencia_e_contra_o_contrato`: o motivo cita a R41.
- `test_contestacao.py::test_orbe_notas_avisos_e_valor_a_devolver_vindo_das_pendencias`: as notas mostram o descontado de fato e a cobrança pela fórmula.
- `test_fechamento.py`: os 7 testes que esperavam parada (código 2) agora esperam bloqueio (código 3, saída gravada e válida): taxas duplicada, `.ofx` faltando, `.eml` repetido, 07 com id diferente, 06 sem `id_transacao`, 06 com colunas trocadas, taxas `_v2` com a Orbe em dois arquivos.
- Novos: `test_parcial.py` (os 6 casos, ilegível, pasta vazia, gravação atômica no parcial, o mapa de dependências rodando cada produto só com as suas fontes, conferências sem um lado, o status no topo do RESULTADOS.md), 4 em `test_orbe.py` (`ler_orbe_parcial`), 2 em `test_checkout.py` (pico e reversão posterior), 1 em `test_fechamento.py` (mensagem da competência anterior).

**Arquivo recebido às 13h10 (06_orbe_ajustes_tardios)** (O05, Organização, canal de Logística, 17/10/2026). A Orbe mandou 14 linhas de setembro que ficaram fora do relatório, no mesmo formato do arquivo 01.

*Antes da mudança*, o fechamento com o 06 na pasta parava (código 2, nada gravado):

```
- orbe (relatório de transações da Orbe, CSV): 2 arquivos casam com o padrão '*orbe*.csv': 01_orbe_relatorio_comissoes_set2026.csv, 06_orbe_ajustes_tardios_set2026.csv.
  O que fazer: deixe só um arquivo de orbe na pasta; substitua o antigo pela versão nova. O fechamento não escolhe um deles sozinho.
```

*Agora* a Orbe aceita vários arquivos no mesmo formato (`config/entradas.yaml`, `multiplos: true`), lidos todos em ordem de nome. As condições:
- o cabeçalho de cada arquivo tem de ser idêntico ao do primeiro; se não for, o fechamento para e diz o arquivo e a coluna;
- id_transacao repetido em outro arquivo: com a linha igual conta uma vez e abre pendência informativa (P27); com qualquer campo diferente, para sem escolher;
- estorno ou reversão de transação do mesmo mês sem a original em nenhum arquivo abre pendência informativa (P28).

Os outros tipos continuam exigindo exatamente um arquivo: uma `02_tabela_taxas_contratadas_v2.xlsx` na pasta ainda para.

| arquivo | linhas antes → depois | total antes → depois | o que mudou |
|---|---:|---:|---|
| comissoes_por_lojista.csv | 35 → 35 | 246.583,18 → **243.278,79** | -3.304,39 em 7 lojistas de checkout (tabela abaixo) |
| divergencias_taxa.csv | 115 → 115 | 2.995,08 → 2.995,08 | nenhuma: nas 14 linhas a taxa aplicada é a contratada (R03, R37) |
| notas_a_emitir.csv | 21 → 21 | 246.588,68 → **243.284,29** | as mesmas 7 notas de checkout, -3.304,39 |
| lancamentos_classificados.csv | 184 → 184 | -1.416.088,18 → -1.416.088,18 | nenhuma (o 06 é da Orbe; os extratos não mudam) |
| pendencias.csv | 16 → 16 | 382.811,75 → 382.811,75 | nenhuma: nenhum id repete o 01 (P27), toda original está no 01 (P28), o alerta de antecipação não muda (P26) |
| rastro.csv | 5.058 → **5.086** | -537.109,49 → **-543.718,27** | +28: cada linha do 06 entra no rastro da comissão e da nota, com `arquivo_origem` = 06 e `ref_origem` = id_transacao |
| contestacoes/ (4 arquivos) | idênticos byte a byte | | nenhuma linha do 06 diverge do contrato, então nada entra na contestação com a Orbe |

As 14 linhas, uma a uma (todas com a taxa aplicada igual à contratada; a original de cada estorno e reversão está no 01, com o mesmo EC, modalidade, parcelas e valor):

| linha do 06 | lojista (CNPJ) | lançamento | bruto | taxa | comissão | regra |
|---|---|---|---:|---:|---:|---|
| TX88446992 | Dublin Hub (68567965000102) | estorno de TX88431689, crédito à vista, 18/09 | -1.147,05 | 2,59% | -29,71 | R04, R35 |
| TX88447011 | Maple Study (34671260000100) | estorno de TX88413573, débito, 03/09 | -420,77 | 1,49% | -6,27 | R04, R35 |
| TX88447030 | Mundo Aberto (17217888000111) | estorno de TX88438558, crédito à vista, 25/09 | -562,44 | 2,49% | -14,00 | R04, R35 |
| TX88447044 | Bridge (22224579000109) | estorno de TX88425142, parcelado 2x, 13/09 | -1.982,10 | 3,19% | -63,23 | R04, R35 |
| TX88447057 | EduAbroad (16181276000153) | estorno de TX88430977, parcelado 2x, 18/09 | -3.898,29 | 3,19% | -124,36 | R04, R35 |
| TX88447070 | Bridge (22224579000109) | estorno de TX88424537, parcelado 6x, 12/09 | -2.603,31 | 3,19% | -83,05 | R04, R35 |
| TX88447087 | Oxford (23109187000161) | estorno de TX88422829, parcelado 9x, 11/09 | -8.647,36 | 3,79% | -327,73 | R04, R35 |
| TX88447093 | Maple Study (34671260000100) | estorno de TX88416714, crédito à vista, 06/09 | -2.620,34 | 2,69% | -70,49 | R04, R35 |
| TX88447109 | EduAbroad (16181276000153) | estorno de TX88428997, parcelado 3x, 16/09 | -2.747,67 | 3,19% | -87,65 | R04, R35 |
| TX88447140 | Oxford (23109187000161) | estorno de TX88432148, crédito à vista, 19/09 | -2.366,18 | 2,59% | -61,28 | R04, R35 |
| AN88447152 | Oxford (23109187000161) | reversão de AN88446397, 22/09 (reverte a antecipação inteira) | -46.080,41 | 2,10% | -967,69 | R05 |
| AN88447178 | Oxford (23109187000161) | reversão de AN88446748, 29/09 (inteira) | -41.690,09 | 2,10% | -875,49 | R05 |
| AN88447194 | Maple Study (34671260000100) | reversão de AN88446551, 24/09 (inteira) | -36.583,37 | 2,10% | -768,25 | R05 |
| TX88447225 | Kiwi Experience (07752116000126) | venda, parcelado 3x, 30/09 | 5.480,00 | 3,19% | 174,81 | R01, R07 |

Por lojista (comissão e nota de checkout): Oxford -2.232,19 (16.077,90 → 13.845,71); Maple -845,01 (15.010,78 → 14.165,77); EduAbroad -212,01 (12.070,17 → 11.858,16); Bridge -146,28 (11.916,02 → 11.769,74); Dublin Hub -29,71 (11.906,08 → 11.876,37); Mundo Aberto -14,00 (18.522,09 → 18.508,09); Kiwi +174,81 (10.711,41 → 10.886,22).

- **Kiwi (EC 1038867654):** está na planilha vigente, na linha Kiwi Experience sem o código do EC ("EC pendente"); a R07 liga o EC ao CNPJ 07752116000126 (`config/checkout.yaml`, ec_sem_codigo). A venda é faturada normalmente, a 3,19% (parcelado 2 a 6x). A R08/R36 não se aplica.
- **Mundo Aberto no checkout (EC 1037647039):** a planilha liga o EC ao CNPJ 17217888000111, o mesmo da remessa (COM-REM, DIV-REM e PEN-CONTEST-REM).
- **Reversões e o alerta de antecipação (R33, P26):** a reversão entra na comissão pela taxa de antecipação da data da original (R05) e baixa só o líquido antecipado. O alerta compara o bruto antecipado com as vendas e só acende para lojista sem histórico. A Oxford tem histórico (estorno de venda de agosto) e antecipou 112,5% das vendas antes e depois; o líquido cai de R$ 311.805,27 para R$ 224.034,77. A Maple antecipou 31,7% das vendas. Nenhum alerta muda.
- **Cobertura:** as 1.943 + 14 = 1.957 linhas da Orbe aparecem no rastro.csv, cada uma com o seu arquivo; `validar_saida(saida/)` devolve `[]`.

Testes que fixavam números ou um arquivo só, e mudaram:
- `test_checkout.py::test_set_comissao_total_e_lojistas`: CHECKOUT 207.039,73 → 203.735,34 (as 14 linhas do 06).
- `test_checkout.py::test_set_comissao_por_lojista`: Oxford 16.077,90 → 13.845,71 e Bridge 11.916,02 → 11.769,74 (as linhas deles no 06).
- `test_outubro.py::test_nomes_assunto_e_anexo_de_outubro`: o pack simulado tem 7 arquivos (a Orbe em dois). O gerador desloca as datas do 06 sem inserir caso novo nele.
- `test_outubro.py::test_orbe_datas_deslocadas_e_uma_venda_nova` compara com o relatório (o primeiro em ordem de nome), e não com um `*orbe*.csv` qualquer.
- `test_estrutura.py::test_localiza_os_6_tipos_por_padrao`: a Orbe vem como tupla de arquivos.
- Os testes dos leitores passam a localizar pela config (`localizar_pela_config`); os de `test_orbe.py` continuam conferindo o relatório 01 (1.943 linhas).
- Novos (15): 6 em `test_orbe.py` (o 01 + o 06 lidos juntos, ordem de nome, id repetido igual, id repetido diferente, cabeçalho com colunas trocadas, cabeçalho com coluna a mais); 3 em `test_checkout.py` (P27, P28, nenhum dos dois em setembro); 6 em `test_fechamento.py` (o 06 numa cópia temporária de dados/ muda a comissão em -3.304,39; reenvio igual vira 14 PEN-REPET-CHK; reenvio diferente para com código 2; cabeçalho sem id_transacao; colunas trocadas; taxas `_v2` ainda para).

**O01 a O04 (Organização, 17/10, canal de Logística): nenhum número mudou.** Linhas e totais dos 6 CSVs iguais aos de antes; `rastro.csv`, os 5 outros CSVs e os 4 arquivos de `contestacoes/` idênticos byte a byte. Em `pendencias.csv` mudaram só textos:
- **motivo (O04, toda pendência com próximo passo):** PEN-NF-CHK, PEN-CONCESSAO-CHK, as 2 PEN-DEVOL-CHK, PEN-ALERTA-ANTEC, as 4 PEN-NEG-REM e PEN-NAOID-L50 ganharam "próximo passo: <quem faz o quê>". As outras 6 já traziam a ação e não mudaram.
- **quem_decide:** PEN-CONCESSAO-CHK-00520815000100 passou de "Financeiro (Helena)" para "Financeiro (Helena) e Comercial" (R32: a Helena paga a devolução; parametrizar a Orbe é com o Comercial, R28).
- **Execução (O01):** o fechamento grava numa pasta temporária, valida e só então substitui `saida/` e `contestacoes/`; entrada ambígua ou faltando parava com a instrução do que fazer (desde a R44, bloqueia só aquela fonte, com a PEN-BLOQUEIO, e a CLI sai com 3); arquivo que não casa nenhum padrão só gera aviso. Testes: 374 → 393 (13 com a rodada O01 a O04; 6 com o pacote `anthropic` opcional, a saída em UTF-8 e a linha "Se estiver errada, para a Helena" em toda premissa ativa).

**R32 a R40 e P26 (Helena, 17/10, 11h37 a 11h41): os números de setembro mudam.**

| arquivo | linhas antes → depois | total antes → depois | regra que causou |
|---|---:|---:|---|
| comissoes_por_lojista.csv | 35 → 35 | 246.583,18 → 246.583,18 | nenhuma: a concessão já zerava a comissão da Casa (R10, R40), e o estorno TX88445133 segue 1,49% (-5,50) |
| divergencias_taxa.csv | 233 → **115** | 18.392,50 → **2.995,08** | R32: as 118 linhas da Casa eram só isenção (a Orbe cobrou a taxa da planilha); saíram. CHECKOUT 210 → 92 (16.973,65 → 1.576,23) |
| notas_a_emitir.csv | 21 → 21 | 246.588,68 → 246.588,68 | nenhuma |
| lancamentos_classificados.csv | 184 → 184 | -1.416.088,18 → -1.416.088,18 | nenhuma (os repasses à Atlas, L34 e L60, seguem em 2.1.01.001, R36) |
| pendencias.csv | 15 → **16** | 382.811,75 → 382.811,75 | R38: PEN-DEVOL-CHK da Casa virou PEN-CONCESSAO-CHK (mesmo valor, 15.396,77). R39: PEN-SEMCONTRATO-39566044000119 virou PEN-SEMCONTRATO-39566044000119. P26: entra PEN-ALERTA-ANTEC-39566044000119 (valor 0,00). R34 e R32: textos da PEN-NEG-REM, da PEN-CONTEST-REM e das PEN-DEVOL-CHK |
| rastro.csv | 5.171 → **5.058** | -521.712,07 → -537.109,49 | R32: -118 linhas das DIV-CHK da Casa (-15.397,42); P26: +5 linhas do alerta (0,00) |
| contestacoes/orbe_operacoes.csv | 210 → **92** | 16.973,65 → **1.576,23** | R32: a Casa saiu do e-mail (só Bridge e Rota) |
| contestacoes/orbe.md | 63 → 51 linhas | | R32: a seção "Comunicação de condição comercial" saiu; a Casa ficou nas notas, como concessão |
| contestacoes/ponte_operacoes.csv | 28 → 28 | -1.325,25 → -1.325,25 | nenhuma (mesmas linhas e colunas) |
| contestacoes/ponte.md | 55 → 55 linhas | | R32: Mundo Aberto passa a "Contestação: spread acima do contratado"; R34: o pedido dos spreads negativos é a diferença até o contrato (3.565,98), e a parte da Tarvo (865,98) foi para as notas |

Itens: 488 → 371 (-118 divergências da Casa, +1 alerta). Testes: 368 → 374. Testes que fixavam números e mudaram:
- `test_checkout.py::test_set_divergencias`: 210 · 16.973,65 → 92 · 1.576,23, sem a Casa (R32); a devolução da Casa saiu da lista de PEN-DEVOL-CHK.
- `test_checkout.py::test_set_nenhuma_divergencia_com_taxa_aplicada_abaixo_da_contratada`: estornos negativos 5 · -107,53 → 4 · -98,44 (o estorno TX88446763 da Casa não diverge do contrato).
- `test_checkout.py::test_set_atlas_sem_contrato`: id PEN-SEMCONTRATO-39566044000119 → PEN-SEMCONTRATO-39566044000119 (R39).
- `test_checkout.py` sintéticos: os 4 testes da condição especial viraram testes da concessão (PEN-CONCESSAO-CHK, divergência contra a planilha); o que esperava erro com divergência e concessão no mesmo lojista agora espera as duas pendências.
- `test_contestacao.py`: orbe_operacoes 210 → 92, uma seção só ("Taxas aplicadas acima do contrato"), estornos 4 · -98,44; Mundo Aberto em "Contestação: spread acima do contratado"; negativos pedem 3.565,98.
- `test_outubro.py::test_casa_do_estudante_tarifa_zerada_em_outubro`: a Casa não tem mais divergência em outubro; a devolução é a PEN-CONCESSAO-CHK.
- `test_ajuste_ponte.py`: o outubro do teste tem 387 itens (era 506): -119 divergências da Casa, e sem alerta, porque setembro está ao lado e a Atlas tem histórico (P26).
- Novos: `test_set_casa_concessao_separada_das_divergencias`, `test_set_alerta_de_antecipacao_so_a_atlas`, `test_estorno_usa_a_data_da_venda_original_e_a_faixa_da_propria_linha`, `test_alerta_*`, `test_concessao_*` e `test_ajuste_sem_lojista_nao_abate_vira_pendencia_e_o_fechamento_termina`.

**R25 a R30 (Helena, 17/10, respostas a outros times às 9h47, 9h49, 9h53 e 10h44):** nenhum número mudou. Mudaram só 4 textos de motivo em pendencias.csv:
- PEN-DEVOL-CHK-22224579000109 e PEN-DEVOL-CHK-95927868000148 (R25): o motivo dizia que a devolução era "decidida caso a caso (R03)"; agora diz que o que a Orbe cobrou a mais é valor a devolver ao lojista. A PEN-DEVOL da Casa do Estudante já dizia isso (R10).
- PEN-CONTEST-REM-17217888000111 (R15, R27): o motivo diz que o valor cheio é o que o lojista pagou a mais e é a devolver, e que o ajuste vem no relatório da Ponte do mês seguinte.
- PEN-SEMCONTRATO-39566044000119 (R30): o motivo diz que as 57 transações (R$ 262.138,61 brutos) serão faturadas na competência 2026-10, com a taxa retroativa a 2026-09-10, quando o Comercial confirmar.

Auditoria das regras novas contra este fechamento:

| regra | o que foi conferido | resultado |
|---|---|---|
| R25 | notas pela taxa contratada, sem somar divergência; nenhuma taxa aplicada abaixo da contratada (as 5 diferenças negativas são estornos, -107,53) | OK; texto da PEN-DEVOL-CHK corrigido |
| R26 | os 44 repasses (PIX ENVIADO, Aurora) estão em 2.1.01.001 e saíram entre os dias 08 e 10 ou 22 e 24; o Meridiano não tem repasse a lojista | OK |
| R27, R31 | o relatório de setembro não tem linha de ajuste (Helena, 11h33). Um ajuste em outubro, como linha nova com Nº próprio e observação "AJUSTE REF PC-...", abate a COM-REM do lojista e a NF-REM, sem PEN-NEG, divergência nem nota complementar (`test_ajuste_ponte.py`) | OK; texto da PEN-CONTEST-REM ajustado |
| R28 | campo "Aprovado por" em R01 a R30; P01 a P23 aguardando aprovação | registrado no HIPOTESES.md |
| R29 | o fechamento gera o rascunho de e-mail por contraparte | corrigido: o fechar gera contestacoes/ (orbe.md, orbe_operacoes.csv, ponte.md, ponte_operacoes.csv) |
| R30 | 57 linhas no rastro da PEN-SEMCONTRATO-39566044000119, primeira transação em 2026-09-10 | OK; texto corrigido |

**R29 — rascunhos de contestação (`contestacoes/`, ao lado de `saida/`).** O `fechar` grava 4 arquivos a partir dos itens já calculados; `saida/` continua com os 6 CSVs. Todo total do texto é a soma do CSV ao lado (`test_contestacao.py`):

| arquivo | conteúdo | linhas | total | Esperado | teste de origem | |
|---|---|---:|---:|---|---|:-:|
| orbe_operacoes.csv | DIV-CHK: Rota 87, Bridge 5 (a Casa saiu com a R32) | 92 | 1.576,23 | 92 · 1.576,23 (= divergências de CHECKOUT, seção 4); estornos 4 · -98,44 | `test_contestacao.py::test_orbe_csv_tem_as_divergencias_de_checkout_com_o_mesmo_id_e_ref`, `::test_orbe_estornos_reduzem_o_total_sem_sinal_negativo_no_texto` | ✓ |
| ponte_operacoes.csv · SPREAD_ACIMA_CONTRATADO | DIV-REM: Mundo Aberto 23 | 23 | 1.418,85 | 23 · 1.418,85 (= PEN-CONTEST-REM) | `test_contestacao.py::test_ponte_csv_bate_com_divergencias_e_pendencias` | ✓ |
| ponte_operacoes.csv · SPREAD_NEGATIVO | PEN-NEG-REM (R23): Canguru, Dublin Hub, Novo Horizonte, Ponte Aérea, 1 cada | 4 | -3.565,98 | 4 · -3.565,98 | idem | ✓ |
| ponte_operacoes.csv · OPERACAO_DUPLICADA | PEN-DUP-REM-PC-0926-0162 (Bagagem Livre) | 1 | 821,88 | 1 · 821,88 | idem | ✓ |

Valores lidos dos arquivos gravados em contestacoes/ (não digitados). Cada .md abre com um bloco "NOTAS PARA A HELENA — apagar antes de enviar" (avisos, valor a devolver pela R25 e R45, ressalvas); o corpo não fala de aviso do Comercial. Orbe: uma seção, "1. Taxas aplicadas acima do contrato" (Bridge e Rota); a Casa fica só nas notas, em "Concessões comerciais (fora do e-mail, R32)". Ponte: "1. Contestação: spread acima do contratado" (Mundo Aberto, R32), "2. Contestação: spreads negativos" e "3. Contestação: operação repetida no relatório". Os destinatários são `<e-mail da Orbe>` e `<e-mail da Ponte>`.

Colunas novas no ponte_operacoes.csv (P24, exibição, aguardando aprovação):

| natureza | coluna | total | Esperado | teste de origem | |
|---|---|---:|---|---|:-:|
| SPREAD_ACIMA_CONTRATADO | parte_tarvo_brl (50% da diferença, por operação) | 709,46 | 709,46 | `test_contestacao.py::test_ponte_partes_da_tarvo_no_csv` | ✓ |
| SPREAD_NEGATIVO | (sem coluna no anexo) 50% do spread contratado por operação, só nas notas internas do ponte.md | 865,98 | 865,98 | idem | ✓ |
| OPERACAO_DUPLICADA | parte_tarvo_brl · valor_operacao_brl | 410,94 · 55.811,47 | 410,94 · 55.811,47 | idem | ✓ |

O `fechar` pelo CLI lista os 4 arquivos gravados e aceita `--sem-contestacao` (`test_contestacao.py::test_cli_lista_os_rascunhos_e_grava_na_pasta_irma`, `::test_cli_sem_contestacao_nao_grava_a_pasta`).

**R31 — ajuste da Ponte (a partir de outubro).** Setembro não tem ajuste, então a saída de setembro não mudou. Testes: 347 → 368 (+21).

| arquivo de teste | antes | depois |
|---|---:|---:|
| `test_ajuste_ponte.py` | 2 testes, que supunham a linha de ajuste com o mesmo Nº de Operação e a mesma data da original | 23 testes: 7 com o pack de outubro (Mundo Aberto, original em setembro, original inexistente) e 16 sintéticos (nota zerada ou negativa, regressão da R23, sem CNPJ, percentual configurável, pasta anterior) |
| demais (`test_remessa.py`, `test_outubro.py`, ...) | 345 | 345, todos verdes |

Exemplo, caso (a), rodado de novo com as fixtures `base` e `com` de `tests/test_ajuste_ponte.py` (o outubro simulado de hoje: R32, arquivo 06 da Orbe deslocado e R45). No pack de outubro entram três ajustes: A, "AJUSTE REF PC-0926-0434", Spread R$ -235,74, sem CNPJ (PC-1026-9101); B, -20,00 do Canguru, com original inexistente (PC-1026-9102); C, -50,00, sem CNPJ e sem original (PC-1026-9103). Sem os ajustes: 387 itens.

| arquivo | linha | sem ajuste | com ajuste |
|---|---|---:|---:|
| comissoes_por_lojista.csv | COM-REM-17217888000111 (Mundo Aberto) | 3.547,69 | 3.429,82 (-117,87) |
| comissoes_por_lojista.csv | COM-REM-53857560000123 (Canguru) | 3.764,05 | 3.754,05 (-10,00) |
| notas_a_emitir.csv | NF-REM-75374179000146 | 39.664,95 | 39.537,08 (-127,87) |
| pendencias.csv | PEN-TED-PONTE | 39.664,95 | 39.537,08 (-127,87) |
| pendencias.csv | PEN-AJUSTE-SEMORIG-PC-1026-9102 (original inexistente) | não existe | -10,00 |
| pendencias.csv | PEN-AJUSTE-SEMLOJISTA-PC-1026-9103 (sem CNPJ e sem original: não abate) | não existe | -25,00 |
| (itens) | | 387 | 389 |

Rastro da COM-REM da Mundo Aberto (e da NF-REM, que repete as mesmas linhas):

```
COM-REM-17217888000111;03_email_ponte_cambio_relatorio_out2026.eml#PonteCambio_Relatorio_TARVO_102026.xlsx;PC-1026-9101;-117.87
COM-REM-17217888000111;03_email_ponte_cambio_relatorio_set2026.eml#PonteCambio_Relatorio_TARVO_092026.xlsx;PC-0926-0434;0.00
```

A NF-REM traz na discriminação: "... competência 2026-10 - líquida de ajuste da Ponte: AJUSTE REF PC-0926-0434 (operação de 2026-09, contestada em 2026-09) - AJUSTE REF PC-0926-9999 (operação original não encontrada em 2026-09)". O bloco acima mostra as 4 colunas obrigatórias do rastro. Desde a O06, cada linha traz também, no fim, `regra` (R31) e `detalhe` ("ajuste Ponte AJUSTE REF PC-0926-0434 (operação de 2026-09, contestada em 2026-09) - 50% do Spread R$ ... (P25)"; na original, "operação original do ajuste ..., valor 0,00"); a descrição continua também na discriminação da nota e no motivo da PEN-AJUSTE-SEMORIG.

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
| divergencias_taxa.csv | 115 | 92 + 23 | `test_checkout.py::test_set_divergencias` (92) + `test_remessa.py::test_set_divergencias` (23) | ✓ |
| notas_a_emitir.csv | 21 | 20 + 1 | `test_checkout.py::test_set_notas` (20) + `test_remessa.py::test_set_nota_unica` (1) | ✓ |
| lancamentos_classificados.csv | 184 | 184 | `test_bancos.py::test_setembro_184_lancamentos_todos_por_regra` | ✓ |
| pendencias.csv | 16 | — | nenhum teste fixa o total; as 16 aparecem uma a uma na seção 6 | |
| rastro.csv | 5.086 | — | | |

| checagem | resultado | Esperado | teste de origem | |
|---|---|---|---|:-:|
| `validar_saida` (formato, id único, soma do rastro) | `[]` | `[]` | `test_bancos.py::test_setembro_validar_saida_com_os_tres_modulos` | ✓ |
| itens com soma do rastro = valor reportado | 371 de 371 | — | | |
| itens com soma diferente, itens sem rastro, id do rastro sem item | 0, 0, 0 | — | | |

---

## 2. Comissões

### Por linha de negócio

| linha_negocio | lojistas | comissão | Esperado | teste de origem | |
|---|---:|---:|---|---|:-:|
| CHECKOUT | 21 | 203.735,34 | 21 · 203.735,34 | `test_checkout.py::test_set_comissao_total_e_lojistas` | ✓ |
| REMESSA | 14 | 39.543,45 | 14 · 39.543,45 | `test_remessa.py::test_set_comissao_total_e_lojistas` | ✓ |
| **total** | 35 | 243.278,79 | — | | |

### CHECKOUT por lojista

| CNPJ | lojista | comissão | Esperado | teste de origem | |
|---|---|---:|---:|---|:-:|
| 17217888000111 | Mundo Aberto | 18.508,09 | — | | |
| 95927868000148 | Rota Global Intercâmbio Ltda | 15.621,27 | 15.621,27 | `test_checkout.py::test_set_comissao_por_lojista` | ✓ |
| 34671260000100 | Maple Study Assessoria Educacional Ltda | 14.165,77 | — | | |
| 23109187000161 | Oxford Prep Cursos Ltda | 13.845,71 | 13.845,71 | `test_checkout.py::test_set_comissao_por_lojista` | ✓ |
| 68567965000102 | Dublin Hub Intercâmbio Ltda | 11.876,37 | — | | |
| 16181276000153 | EduAbroad | 11.858,16 | — | | |
| 22224579000109 | Escola Bridge de Idiomas Ltda | 11.769,74 | 11.769,74 | `test_checkout.py::test_set_comissao_por_lojista` | ✓ |
| 53857560000123 | Canguru | 11.679,43 | — | | |
| 07752116000126 | Kiwi Experience | 10.886,22 | — | | |
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
| 17217888000111 | Mundo Aberto | CHECKOUT | 18.508,09 | — | | |
| 95927868000148 | Rota Global Intercâmbio Ltda | CHECKOUT | 15.621,27 | — | | |
| 34671260000100 | Maple Study Assessoria Educacional Ltda | CHECKOUT | 14.165,77 | — | | |
| 23109187000161 | Oxford Prep Cursos Ltda | CHECKOUT | 13.845,71 | — | | |
| 68567965000102 | Dublin Hub Intercâmbio Ltda | CHECKOUT | 11.876,37 | — | | |
| 16181276000153 | EduAbroad | CHECKOUT | 11.858,16 | — | | |
| 22224579000109 | Escola Bridge de Idiomas Ltda | CHECKOUT | 11.769,74 | — | | |
| 53857560000123 | Canguru | CHECKOUT | 11.679,43 | — | | |
| 07752116000126 | Kiwi Experience | CHECKOUT | 10.886,22 | — | | |
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
| CHECKOUT | 20 | 203.740,84 | 20 notas, nenhuma da Casa do Estudante (00520815000100) | `test_checkout.py::test_set_notas` | ✓ |
| REMESSA | 1 | 39.543,45 | 39.543,45 | `test_remessa.py::test_set_nota_unica` | ✓ |
| **total** | 21 | **243.284,29** | — | | |

As notas somam R$ 5,50 a mais que as comissões (243.278,79): é a comissão negativa da Casa do Estudante, que não emite nota (R06) e vira PEN-NF-CHK.

---

## 4. Divergências de taxa

### Por linha de negócio

| linha | linhas | soma | Esperado | teste de origem | |
|---|---:|---:|---|---|:-:|
| CHECKOUT | 92 | 1.576,23 | 92 · 1.576,23 | `test_checkout.py::test_set_divergencias` | ✓ |
| REMESSA | 23 | 1.418,85 | 23 · 1.418,85, todas da Mundo Aberto, nenhuma DIV-REM dos 4 spreads negativos (R23) | `test_remessa.py::test_set_divergencias` | ✓ |
| **total** | 115 | 2.995,08 | — | | |

### Por lojista e linha

| linha | CNPJ | lojista | linhas | soma | Esperado | teste de origem | |
|---|---|---|---:|---:|---|---|:-:|
| CHECKOUT | 95927868000148 | Rota Global Intercâmbio Ltda | 87 | 1.546,28 | 87 · 1.546,28 | `test_checkout.py::test_set_divergencias` | ✓ |
| CHECKOUT | 22224579000109 | Escola Bridge de Idiomas Ltda | 5 | 29,95 | 5 · 29,95 | `test_checkout.py::test_set_divergencias` | ✓ |
| REMESSA | 17217888000111 | Mundo Aberto | 23 | 1.418,85 | 23 · 1.418,85 | `test_remessa.py::test_set_divergencias` | ✓ |

Os 4 spreads negativos (PC-0926-0210, -0326, -0491 e -0545) não entram aqui: pela R23 não são divergência. Ficam só como PEN-NEG-REM na seção 6, com os mesmos valores (P18).

Abaixo da tolerância de 0,01 p.p. (P01), a maior oscilação das operações não divergentes e sem spread negativo é 0,0016 p.p. (`test_remessa.py::test_set_oscilacao_dos_demais_abaixo_da_tolerancia`), um número que não aparece nos CSVs.

### As 5 maiores

| id_saida | CNPJ | contratada (%) | aplicada (%) | diferença | Esperado |
|---|---|---:|---:|---:|---|
| DIV-REM-PC-0926-0434 | 17217888000111 | 1.2000 | 1.4996 | 235,74 | — |
| DIV-REM-PC-0926-0373 | 17217888000111 | 1.2000 | 1.4998 | 113,41 | — |
| DIV-REM-PC-0926-0566 | 17217888000111 | 1.2000 | 1.5001 | 76,76 | — |
| DIV-REM-PC-0926-0075 | 17217888000111 | 1.2000 | 1.4993 | 75,41 | — |
| DIV-REM-PC-0926-0236 | 17217888000111 | 1.2000 | 1.5009 | 71,36 | — |

As cinco são da Mundo Aberto (remessa). Antes da R32 as cinco maiores eram da Casa do Estudante, que deixou de ser divergência.

### Negativas (4 linhas, soma -98,44)

| id_saida | CNPJ | contratada (%) | aplicada (%) | diferença | Esperado | teste de origem | |
|---|---|---:|---:|---:|---:|---|:-:|
| DIV-CHK-TX88446419 | 95927868000148 | 3.5900 | 4.0900 | -52,10 | — | | |
| DIV-CHK-TX88446596 | 95927868000148 | 2.9900 | 3.4900 | -29,98 | — | | |
| DIV-CHK-TX88446647 | 95927868000148 | 2.9900 | 3.4900 | -11,23 | — | | |
| DIV-CHK-TX88446585 | 95927868000148 | 2.4900 | 2.9900 | -5,13 | — | | |
| **4 linhas, todas ESTORNO** | | | | **-98,44** | 4 · -98,44; nenhuma taxa aplicada abaixo da contratada | `test_checkout.py::test_set_nenhuma_divergencia_com_taxa_aplicada_abaixo_da_contratada` | ✓ |

As 4 são estornos de vendas da Rota que já tinham sido cobradas acima do contratado: o estorno devolve a diferença, com sinal negativo (R37). O estorno TX88446763 da Casa saiu pela R32: ele veio pela taxa da planilha.

---|---|---:|---:|---:|---:|---|:-:|
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
| ALERTA_ANTECIPACAO | 1 | 0,00 |
| CONFERENCIA_REPASSE | 1 | 39.543,45 |
| CONTESTACAO_PONTE | 5 | -2.147,13 |
| CREDITO_NAO_IDENTIFICADO | 1 | 7.350,00 |
| DEVOLUCAO_CONCESSAO | 1 | 15.396,77 |
| DEVOLUCAO_LOJISTA | 2 | 1.575,80 |
| DEVOLUCAO_PIX | 1 | 12.400,00 |
| LOJISTA_SEM_CONTRATO | 1 | 7.876,05 |
| NOTA_NAO_EMITIDA | 1 | -5,50 |
| OPERACAO_DUPLICADA | 1 | 821,88 |
| TRANSFERENCIA_EM_TRANSITO | 1 | 300.000,00 |
| **total** | 16 | 382.811,32 |

### Por quem decide

| quem_decide | pendências | soma |
|---|---:|---:|
| Comercial | 1 | 7.876,05 |
| Financeiro (Helena) | 13 | 359.538,50 |
| Financeiro (Helena) e Comercial | 2 | 15.396,77 |

Nenhum teste fixa os agregados por tipo ou por quem decide. As 16 pendências estão conferidas uma a uma abaixo.

### Lista completa

| id_saida | tipo | refs | valor | quem decide | Esperado | teste de origem | |
|---|---|---:|---:|---|---|---|:-:|
| PEN-NF-CHK-00520815000100 | NOTA_NAO_EMITIDA | 119 | -5,50 | Financeiro (Helena) | NOTA_NAO_EMITIDA · -5,50 | `test_checkout.py::test_set_notas` | ✓ |
| PEN-CONCESSAO-CHK-00520815000100 | DEVOLUCAO_CONCESSAO | 118 | 15.396,77 | Financeiro (Helena) e Comercial | 118 · 15.396,77 · DEVOLUCAO_CONCESSAO; motivo sem a R25 (R32, R38) | `test_checkout.py::test_set_casa_concessao_separada_das_divergencias` | ✓ |
| PEN-DEVOL-CHK-22224579000109 | DEVOLUCAO_LOJISTA | 5 | 29,94 | Financeiro (Helena) | 5 · 29,94 (R45: descontado de fato) | `test_checkout.py::test_set_divergencias` | ✓ |
| PEN-DEVOL-CHK-95927868000148 | DEVOLUCAO_LOJISTA | 87 | 1.545,86 | Financeiro (Helena) | 87 · 1.545,86 (R45: descontado de fato) | `test_checkout.py::test_set_divergencias` | ✓ |
| PEN-SEMCONTRATO-39566044000119 | LOJISTA_SEM_CONTRATO | 57 | 7.876,05 | Comercial (Diego) | 57 · 7.876,05 · LOJISTA_SEM_CONTRATO · Comercial; id pelo CNPJ da aba de 2025 (R39); motivo com 57 transações, 262138.61 brutos, competência 2026-10 e retroativa a 2026-09-10 (R30) | `test_checkout.py::test_set_atlas_sem_contrato` | ✓ |
| PEN-ALERTA-ANTEC-39566044000119 | ALERTA_ANTECIPACAO | 5 | 0,00 | Financeiro (Helena) e Comercial | só a Atlas acende, pelo pico em 15/09: 179.592,82 antecipados contra 55.357,50 vendidos; reversões AN88445637 (17/09) e AN88446517 (26/09); fim do mês 127.230,96 contra 135.428,90 (P26, R43) | `test_checkout.py::test_set_alerta_de_antecipacao_so_a_atlas` | ✓ |
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

Resultado: 388 itens (eram 506), `validar_saida` sem problemas, rastro fechando em 388 de 388. Linhas: comissões 36, divergências 123 (eram 242; soma 18.465,89 → 3.073,97), notas 21, lançamentos 186, pendências 22 (eram 21), rastro 5.123 (eram 5.209; o pack leva também os ajustes tardios da Orbe deslocados, O05, e as 14 linhas entram em comissão e nota). As diferenças vêm da R32 (saem as 119 divergências da Casa, que em outubro estão todas na concessão) e da P26 (entra o alerta da Atlas: o pack simulado não tem setembro ao lado, e a Atlas começa em 10/10). Comissões, notas e lançamentos não mudam.

### O que cada caso novo gerou

Para cada caso, a tabela lista todos os id_saida que têm a referência nova no rastro.csv:

| caso | referência nova | id_saida que a usam | Esperado | teste de origem | |
|---|---|---|---|---|:-:|
| (a) Orbe: venda de EC fora da planilha (1099300457), R$ 2.450,00 a 2,69% | TX88999001 | **PEN-SEMCONTRATO-1099300457**: LOJISTA_SEM_CONTRATO, 65,90 (o que a Orbe cobrou), Comercial | só a PEN-SEMCONTRATO; sem comissão, nota ou divergência | `test_outubro.py::test_caso_a_venda_de_ec_fora_da_planilha_vira_so_pendencia` | ✓ |
| (b) Aurora: "PIX ENVIADO GRAFICA RAPIDA LTDA", -1.250,00 | L49 | LAN-AUR-L49 (A_CLASSIFICAR · HUMANO · 0,00) e **PEN-SEMREGRA-L49**: LANCAMENTO_SEM_REGRA, -1.250,00 | só esses dois; A_CLASSIFICAR/HUMANO/0.00 | `test_outubro.py::test_casos_b_c_pix_fora_das_listas_ficam_a_classificar` | ✓ |
| (c) Meridiano: "PIX RECEB INSTITUTO SAKURA IDIOMAS", +25.000,00 | MRD2026100446 | LAN-MER-MRD2026100446 (A_CLASSIFICAR · HUMANO · 0,00) e **PEN-SEMREGRA-MRD2026100446**: LANCAMENTO_SEM_REGRA, 25.000,00 | só esses dois; nenhuma conferência PIX × remessa | `test_outubro.py::test_casos_b_c_pix_fora_das_listas_ficam_a_classificar` | ✓ |
| (d) Ponte: operação de CNPJ fora da planilha (41928553000196) | PC-1026-9001 | COM-REM-41928553000196 (121,50), NF-REM-75374179000146 (121,50 dos 39.664,95), PEN-TED-PONTE (121,50), **PEN-NAOCAD-REM-41928553000196**: LOJISTA_NAO_CADASTRADO, 121,50, **PEN-TED-LIQ-2026-10-14**: DIVERGENCIA_TED_LIQUIDACAO, 16.505,48, **PEN-PIX-REM-41928553000196**: DIFERENCA_PIX_REMESSA, -16.505,48 | exatamente esses 6 id_saida, sem DIV-; comissão = 50% do spread | `test_outubro.py::test_caso_d_operacao_de_cnpj_fora_da_planilha` | ✓ |

**Pendências novas: 6** (as que estão em negrito). Elas explicam a diferença entre as 16 pendências de setembro e as 22 de outubro. 16.505,48 é valor_brl + iof_brl da operação nova, que não tem TED de liquidação nem PIX do cliente. O rastro da PEN-TED-LIQ-2026-10-14 traz as 10 referências do dia: as outras 9 (8 operações e a TED do dia) somam zero entre si.

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

- **PEN-NF-CHK da Casa do Estudante: 0,00 em vez de -5,50.** O estorno TX88445133 era de venda de 21/08 (taxa de 1,49%). Em outubro a venda original cai em 21/09, dentro da isenção (R40). A comissão do estorno vira 0,00, e os -5,50 entram na devolução da concessão (PEN-CONCESSAO-CHK: 119 refs, 15.391,27). Não há divergência da Casa (R32).
- **Bridge: 13 divergências (108,84) e devolução de 108,80 (R45: o descontado de fato), contra 5 divergências (29,95) e devolução de 29,94.** A Orbe cobrou 2,59% em 13 vendas de crédito à vista. Em setembro, 8 delas (de 01 a 13/09) estavam dentro do contrato antigo, que valia até 14/09. Em outubro todas caem depois de 15/09 e passam a valer a taxa renegociada de 2,19%, então as 13 viram divergência (`test_outubro.py::test_bridge_vendas_de_outubro_na_taxa_nova`).
- **PEN-SEMCONTRATO-39566044000119 (R30, R39):** o motivo cita a competência 2026-11 e a data 2026-10-10, porque no pack simulado a Atlas começa em 10/10. O valor (7.876,05) não muda.
- **PEN-TRANSF-L93:** a transferência do fim do mês passa a cair em 02/11, a conferir no extrato de novembro.

---

## Escolhas de interpretação (P15 a P21)

Premissas do HIPOTESES.md (seção 2.1) que a revisão independente questionou e que foram mantidas. Para cada uma: o número de setembro que ela afeta e o valor que esse número teria na leitura alternativa. A P15 foi substituída depois pela R23 e aparece invertida: o valor adotado é o da R23, e a alternativa é a antiga P15.

Os valores alternativos **não são valores de teste**. P16, P19 e P20 são contas sobre os CSVs de `saida/`; a alternativa da P15 é a saída do commit `db29cf0`. P17, P18 e P21 foram calculados à parte, com um script descartável que usa os leitores e `remessa.calcular_operacao` sem alterá-los, sobre `dados/2026-09`.

| premissa | escolha adotada | número afetado | valor adotado | leitura alternativa | valor na alternativa |
|---|---|---|---:|---|---:|
| **P15** (substituída pela R23) | R23: spread negativo só como contestação, fora das divergências | linhas de remessa em divergencias_taxa.csv · soma | 23 · 1.418,85 | P15 antiga: listar também como divergência (a Helena permite, desde que fique claro que é outra natureza) | **27 · -2.147,13** |
| | | total de divergencias_taxa.csv · soma | 115 · 2.995,08 | | 119 · -570,90 |
| | | divergências negativas | 4 (só os estornos de checkout) | | 8 |
| **P16** | devolução de PIX (L65, +12.400,00) em 2.1.01.001 (validada pela Helena às 9h48: as duas contas servem; critério fixo) | AURORA 2.1.01.001 · soma | 45 · -4.217.867,61 | L65 em 2.1.01.002 (Devoluções e créditos a lojistas) | **44 · -4.230.267,61**, e 2.1.01.002 com 1 · 12.400,00 |
| **P17** | diferença de remessa pelo Spread % do relatório: (Spread % − contratado) / 100 × PTAX × Valor ME | DIV-REM Mundo Aberto (23 linhas) e PEN-CONTEST-REM-17217888000111 | 1.418,85 | pelo Spread R$: Spread R$ − contratado / 100 × PTAX × Valor ME, por operação | **1.418,88** |
| | | PEN-NEG-REM-PC-0926-0326 · PEN-NEG-REM-PC-0926-0491 | -1.001,30 · -574,90 | | -1.001,29 · -574,91 (os 4 negativos continuam somando -3.565,98) |
| | | CONTESTACAO_PONTE (5 pendências) | -2.147,13 | | -2.147,10 |
| **P18** | contestação do spread negativo pela diferença contra o contrato (mesmo cálculo de P17) | 4 PEN-NEG-REM: PC-0926-0210 · 0326 · 0491 · 0545 | -1.351,87 · -1.001,30 · -574,90 · -637,91 = **-3.565,98** | pelo Spread R$ negativo da operação | -687,52 · -509,22 · -292,28 · -345,03 = **-1.834,05** |
| | | CONTESTACAO_PONTE (5 pendências) · total de pendencias.csv | -2.147,13 · 382.811,32 | | -415,20 · 384.543,25 |
| **P19** | PEN-DUP pelo Spread R$ da cópia descartada | PEN-DUP-REM-PC-0926-0162 | 821,88 (o quanto o rodapé de 78.073,59 está inflado) | pela parte da Tarvo na cópia (50%, R11) | **410,94** |
| **P20** | transferência de 30/09 mantida como pendência até a conciliação de outubro | pendencias.csv: quantidade · soma | 16 · 382.811,32 | sem a PEN-TRANSF-L92, já que a R20 explica a transferência | **15 · 82.811,32** |
| | | "Financeiro (Helena)" | 13 · 359.538,50 | | 12 · 59.538,50 |
| **P21** | Atlas (EC 1076801732) fora de comissoes_por_lojista; o que a Orbe cobrou fica em PEN-SEMCONTRATO | comissões CHECKOUT: lojistas · soma | 21 · 203.735,34 | faturar a Atlas pela aba "ANTIGO 2025 - nao usar" (CNPJ 39566044000119; débito 1,69%, crédito à vista 2,99%, parcelado 3,49%, Pix 0,99%) | **22 · 208.112,63** (+4.377,29 em 50 linhas; as 7 de antecipação e reversão ficam sem taxa, porque a aba de 2025 não tem antecipação) |
| | | notas CHECKOUT | 20 | | 21 |
| | | divergências da Atlas | 0 | | 41 linhas · 827,22 (a Orbe aplicou taxas diferentes das de 2025) |
| | | PEN-SEMCONTRATO-39566044000119 | 7.876,05 | | deixa de existir |

A leitura alternativa da P21 contraria a R08 ("a aba de 2025 não vale"). Ela aparece aqui só para mostrar o tamanho do efeito.


## Premissas abertas (checkpoint 2)

Cada premissa abaixo é uma escolha nossa que a Helena (ou o Comercial, nas taxas e condições comerciais, R28) ainda não aprovou, ou que ela aceitou sem fechar. A coluna do meio diz o que muda para ela se estivermos errados; a última, o valor em reais que está em jogo com os dados de setembro. O texto completo de cada uma, com o motivo, está no HIPOTESES.md, seção 2.1.

| id | o que assumimos | se estiver errada, para a Helena | valor em jogo |
|---|---|---|---|
| P01 | diferença de spread da remessa abaixo de 0,01 p.p. não é divergência | deixa de contestar com a Ponte diferenças reais de outros lojistas, ou contesta centavos de arredondamento da PTAX | R$ 24,58 de centavos no mês; a menor diferença real (Mundo Aberto) é R$ 1.418,85 |
| P03 | a Orbe trunca o centavo; truncamento não é divergência, a divergência compara taxas | deixa de pedir à Orbe centavos de arredondamento, ou abre contestação à toa por R$ 0,01 | R$ 9,37 no mês |
| P04 | CNPJ da Ponte fora da planilha: calcula a comissão, entra na nota e abre pendência de cadastro para o Comercial (a Helena achou razoável, 9h45) | emite nota com comissão que a Ponte não reconhece, ou atrasa o faturamento de uma comissão que a Ponte paga | R$ 0,00 (não aconteceu em setembro) |
| P05 | spread negativo de CNPJ fora da planilha para o fechamento | fica sem a lista de contestação até o Comercial cadastrar, ou teria de decidir sozinha quanto pedir | R$ 0,00 (não aconteceu em setembro) |
| P06 | devolução de PIX do Aurora vai para 2.1.01.001 com pendência para apurar o motivo | saldo de repasses a pagar fica errado até apurar o motivo com a Mundo Aberto; só conta do passivo, não resultado | R$ 12.400,00 |
| P07 | só é repasse a lojista o PIX enviado a favorecido que está em `config/favorecidos.yaml`, com CNPJ da aba vigente | repasse ao lojista errado no razão, ou lançamento a classificar à mão | R$ 4.230.267,61 de repasses por PIX |
| P08 | só é cliente da remessa o pagador de PIX que está em `config/pagadores_meridiano.yaml` | cobra de um cliente a diferença de outro, ou deixa passar um PIX a menos | R$ 5.629.687,12 de PIX de clientes |
| P09 | lançamento sem regra fica A_CLASSIFICAR, método HUMANO, com pendência | crédito desconhecido entraria no razão sem aviso a ela, se o certo fosse uma conta transitória | R$ 0,00 (todo lançamento de setembro casou uma regra) |
| P10 | confiança 1,00 para regra confirmada, 0,80 para regra nossa | revisa à toa a devolução de PIX, ou deixa de olhar o que merecia atenção | R$ 12.400,00 |
| P11 | a TED de liquidação do dia fecha com as operações da Ponte contratadas no dia | investiga à toa com a Ponte, ou não vê um repasse menor ou maior que as operações | R$ 5.611.447,12 conferidos; diferença R$ 0,00 |
| P12 | PIX do cliente no mês × operações contratadas no mês; PIX a mais é adiantamento (R22) | cobra de quem pagou adiantado, ou deixa de cobrar quem não pagou | R$ 18.240,00 (adiantamento da Ponte Aérea Estudantil) |
| P13 | transferência entre contas casa por valor, na mesma data ou no dia útil seguinte, sem calendário de feriados | recebe como "sem par" uma transferência que só atrasou, ou dá como chegada uma que não chegou | R$ 1.450.000,00 enviados do Aurora; R$ 300.000,00 em trânsito |
| P14 | a IA só sugere, só para lançamento sem regra, e uma pessoa revisa toda sugestão | uma conta errada entraria no razão sem ela ver, se a IA lançasse sem revisão | R$ 0,00 (nenhuma chamada em setembro) |
| P16 | devolução de PIX em 2.1.01.001, não em 2.1.01.002 (a Helena aceitou as duas, 9h48) | só muda a conta do passivo, sem efeito no resultado nem no valor devido | R$ 12.400,00 |
| P17 | diferença de remessa pelo Spread % do relatório | pede à Ponte R$ 0,03 a mais ou a menos na Mundo Aberto; o total dos negativos não muda | R$ 0,03 |
| P19 | a operação repetida vale o spread inteiro da cópia descartada | pede à Ponte corrigir R$ 821,88 quando o que pesa para a Tarvo é a metade; a nota não muda | R$ 410,94 |
| P20 | a transferência de 30/09 fica como pendência de acompanhamento até aparecer no extrato de outubro (aceita pela O04) | sem a pendência, nada avisaria se os R$ 300.000,00 não chegassem; com ela, uma conferência a mais | R$ 300.000,00 |
| P22 | o TED da Ponte se confere contra o valor da nota de intermediação, sem supor desconto (R18) | compara o repasse com o número errado: aceita um repasse menor ou cobra um maior sem base | R$ 39.543,45 |
| P23 | a devolução da concessão vale o que a Orbe cobrou nas transações (confirmado pela R45 para toda devolução: o descontado de fato); fica aberta só a divisão entre PEN-DEVOL e PEN-CONCESSAO numa linha da concessão que também diverge | contestaria com a Orbe mais ou menos do que ela deve, na linha que fosse as duas coisas | R$ 0,00 em setembro (nenhuma linha da Casa diverge) |
| P24 | os rascunhos mostram a parte da Tarvo como 50% (R11), só como exibição | lê nas notas internas um valor errado, sem mudar o que se pede à Ponte | R$ 709,46, R$ 410,94 e R$ 865,98 de exibição |
| P25 | o ajuste da Ponte abate 50% do Spread R$ da linha | nota da Ponte R$ 50,00 mais alta (ou mais baixa) por R$ 100,00 de ajuste, a corrigir depois | R$ 0,00 em setembro (sem ajuste) |
| P26 | alerta pelo pico: lojista sem histórico com o antecipado acumulado acima das vendas acumuladas em alguma data (critério nosso, delegado pela Helena às 11h37, 11h49 e 12h50) | não vê um lojista novo antecipando alto, ou olha à toa lojistas com histórico | R$ 179.592,82 antecipados contra R$ 55.357,50 vendidos (Atlas, 15/09) |
| P27 | id_transacao repetido em dois arquivos da Orbe com a linha igual conta uma vez, com pendência informativa; com campo diferente, a linha do arquivo posterior (o ajuste) substitui a do relatório e abre PEN-CORRECAO-ORBE com antes → depois e o efeito (critério nosso, delegado pela Helena às 13h34) | se a versão certa fosse a do relatório, a comissão e a nota sairiam pela versão corrigida, e a diferença inteira está na PEN-CORRECAO-ORBE para ela desfazer | R$ 0,00 (nenhum id repetido em setembro) |

**Fechada:** a P18 (contestação dos spreads negativos pela diferença até o contrato, R$ 3.565,98; o spread do relatório, R$ 1.834,05, é o que aconteceu) foi **confirmada pela R34**. **Substituídas** e fora desta lista: P02 e P15 (R23), P21 (R36 e R39) e P28 (R48, Helena às 14h10: o estorno sem a original entra pelo valor que veio, e a pendência vale o efeito na comissão).
