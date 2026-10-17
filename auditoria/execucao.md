# Registro de execução — competência 2026-09

Última execução do `fechar`. Gerado pelo próprio fechamento (src/tarvo/auditoria.py); a versão completa está em `execucao.json`, ao lado.

| campo | valor |
|---|---|
| data e hora | 2026-10-17T16:25:38-03:00 |
| commit do código | 7e4f53f (regras-helena-2) |
| competência | 2026-09 |
| comando | `python -m tarvo fechar --competencia 2026-09 --entrada "dados/2026-09" --saida "saida"` |
| pasta de entrada | dados/2026-09 |
| pasta de saída | saida |
| pasta dos rascunhos de contestação | contestacoes |
| status | **COMPLETO** |
| código de saída | 0 |

## Arquivos de entrada

| arquivo | tipo | tamanho (bytes) | SHA-256 | situação | linhas lidas | o que conta | linhas rejeitadas |
|---|---|---|---|---|---|---|---|
| 01_orbe_relatorio_comissoes_set2026.csv | orbe | 221518 | `fdbc2bad2dd38dde8bf3af9d5c1f21116f0eae8d71d6a5a16b0dfd82de3cc7ec` | lido | 1943 | linhas de dados convertidas (repetidas e corrigidas incluídas) | 0 |
| 02_tabela_taxas_contratadas.xlsx | taxas | 10092 | `d0c7d2b13ac41c2a036a40362eb26c341666feef74d7199284742c255885dfc4` | lido | 25 | linhas da aba "Taxas vigentes" | 0 |
| 03_email_ponte_cambio_relatorio_set2026.eml | ponte_eml | 42076 | `e36808cab907df4b598d0022ae92af99c9b7c281a5d619d91e64d163f42e6f8f` | lido | 233 | operações da aba "Operações" do anexo | 0 |
| 04_plano_de_contas_fenix_erp.csv | plano_de_contas | 3205 | `fb99c63b151c2a029c86475eb2551e4af7722a055dc24137244a2411e7876d72` | lido | 52 | contas | 0 |
| 05a_extrato_banco_aurora_cc4471_set2026.csv | aurora | 6896 | `7303b72fa76d227a863279a36726411605d93fb63237f0cae638c111a70d2d92` | lido | 84 | lançamentos | 0 |
| 05b_extrato_banco_meridiano_cc90233_set2026.ofx | meridiano | 18306 | `27f11fae20c1fb69e2ca47885f6082690fe5db5cd13ddf3e407ef3cb29e33283` | lido | 100 | transações (STMTTRN) | 0 |
| 06_orbe_ajustes_tardios_set2026.csv | orbe | 2088 | `b1cfd183945fb194e05cfbe9455ab364c31b676427e6653562f6821f57240292` | lido | 14 | linhas de dados convertidas (repetidas e corrigidas incluídas) | 0 |

## Arquivos ignorados

| arquivo | por quê |
|---|---|
| 00_LEIA-ME.md | não casa com nenhum padrão de config/entradas.yaml |
| 01_instrucoes_participantes.docx | não casa com nenhum padrão de config/entradas.yaml |

## Fontes bloqueadas

Nenhuma.

## Saída (pasta de saída)

| arquivo | linhas | total | coluna somada | SHA-256 |
|---|---|---|---|---|
| comissoes_por_lojista.csv | 35 | 243278.79 | comissao_brl | `f9ca1ea72210b25939f3840e974450a4c9b10f987876227fd9c2a0e67f6f8971` |
| divergencias_taxa.csv | 115 | 2995.08 | diferenca_brl | `d10b45e1616293b4dcf4258fbb4c936e77a02d140a49bb8356b5a04e93e85843` |
| notas_a_emitir.csv | 21 | 243284.29 | valor_brl | `5b8ae84a9d40d2ebf3899e448ccfbdcee84a668f21c544eeab1c614d2e299c35` |
| lancamentos_classificados.csv | 184 | -1416088.18 | valor | `0d291a9e3b99646a245fdd7570238dfad70c931624171382c5f2e65a06ab32d3` |
| pendencias.csv | 16 | 382811.32 | valor_brl | `378b5e76ff76bf92c56201ad71c51dddc93017e917622bf1915d3fd18b034b14` |
| rastro.csv | 5086 | -543718.70 | valor | `30fa238104fc63aae496c4d03ddd79f877e51843bcf4d6d7175b9ab78b8cc5c7` |

## Rascunhos de contestação

| arquivo | linhas | SHA-256 |
|---|---|---|
| orbe.md | 51 | `c4aee7707ad68ad81b1710ecc80c10d8ed037f0555605a3c9328952bec7c57fb` |
| orbe_operacoes.csv | 93 | `e7596fbd393fb30f6969982c8f1ae17981e1108235c337a87ba8e40170bcda0c` |
| ponte.md | 55 | `e91240d9e91690730ba3967d451cd522ba26f3b0ce347fa6c04fb4b2ed3e5291` |
| ponte_operacoes.csv | 29 | `81b17d9c5b7e00b24c86785fe74c5678beb863159a20627db85cc2f9d0cfd193` |

## Como refazer qualquer número

1. Confira o SHA-256 de cada arquivo de entrada (`certutil -hashfile <arquivo> SHA256` no Windows, `sha256sum <arquivo>` no Linux): igual ao da tabela, é o mesmo arquivo.
2. Faça checkout do commit `7e4f53f` e rode o comando acima.
3. Cada número da saída tem as linhas de origem no rastro.csv (id_saida; arquivo_origem; ref_origem; valor; regra; detalhe): a soma de valor por id_saida é o número reportado, e a regra e o detalhe dizem a taxa, a isenção ou a venda original usada em cada linha (HIPOTESES.md).
