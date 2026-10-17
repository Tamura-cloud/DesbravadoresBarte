# Fechamento mensal — Tarvo Pagamentos

**Time Desbravadores Barte** · Desafio Barte AI, case Tarvo (17/10/2026)

**Equipe:** Pedro (Pessoa 1: integração, dados novos e README) · Antônio (Pessoa 2: regras da Helena, código e testes) ·
Erick (Pessoa 3: histórico de IA e pitch)

**Em um minuto:** lemos os arquivos do mês como chegam, inclusive os ajustes que a Orbe manda depois do relatório,
aplicamos as regras da Helena e entregamos 21 notas (R$ 243.284,29), 115 divergências (R$ 2.995,08) e 16 pendências,
cada uma com quem decide. Cada número aponta para a linha de origem. Um comando fecha o mês; se faltar um arquivo,
ele fecha o que não depende dele e diz o que ficou bloqueado.

Fecha o mês da Tarvo a partir dos arquivos do data pack, lidos como vêm (sem edição manual), e gera os
6 CSVs de `saida/`. Cada número de saída é rastreável até a linha do arquivo de origem pelo `rastro.csv`,
e a execução falha se algum valor não fechar com o rastro.

## Por que o fechamento é lento e erra

Três causas, cada uma com um caso de setembro:

1. **A regra está fora do sistema.** O acordo de tarifa zero da Casa do Estudante (setembro a dezembro) existia só
   num comentário da célula A13 da planilha de taxas e na cabeça do comercial. Ninguém avisou a Orbe, que cobrou:
   são **R$ 15.396,77** que a Tarvo devolve ao lojista (R10, R32). Nas palavras da Helena: "quase tudo que vocês já
   descobriram aqui no canal estava só na minha cabeça".
2. **Ninguém confere a cobrança contra o contrato, então ninguém contesta.** A Orbe cobrou 0,5 p.p. a mais da Rota
   Global desde 12/09, sem reajuste de contrato (**R$ 1.545,86** a devolver, R09). A Ponte aplicou 1,50% na Mundo
   Aberto, que tem 1,20% registrado desde julho (**R$ 1.418,85**, R15, R16). A Bridge renegociou para 2,19% a
   partir de 15/09, mas a Orbe seguiu cobrando 2,59% até 18/09, porque o aviso chegou atrasado (**R$ 29,94**; "o
   aviso atrasado é problema nosso de processo", R32). Hoje a cobrança errada só aparece quando o lojista reclama.
3. **O cruzamento é manual.** Dos 8 dias de fechamento, a comissão de checkout leva uns 3: metade casando à mão o
   nome do lojista com o EC e o CNPJ, metade refazendo trabalho quando a planilha está desatualizada
   (`HIPOTESES.md`, seção 6). A solução casa só por código (`cod_estabelecimento` e CNPJ), nunca por nome.

## Dinheiro em jogo em setembro

Os valores abaixo têm naturezas diferentes e **não devem ser somados**. O total de `pendencias.csv`
(R$ 382.811,32) mistura dinheiro a devolver com dinheiro que só precisa ser conferido quando chegar.

| natureza | caso | valor (R$) | pendência |
|----------|------|-----------:|-----------|
| **Custo da Tarvo** (concessão comercial devolvida ao lojista) | Casa do Estudante | 15.396,77 | `PEN-CONCESSAO-CHK` |
| **Cobrado a mais pela Orbe** (devolver ao lojista e contestar com a Orbe) | Rota Global | 1.545,86 | `PEN-DEVOL-CHK` |
| | Escola Bridge | 29,94 | `PEN-DEVOL-CHK` |
| **A contestar com a Ponte** | Mundo Aberto: spread acima do contratado | 1.418,85 | `PEN-CONTEST-REM` |
| | 4 operações com spread negativo: diferença até o spread contratado (o relatório mostra -1.834,05) | 3.565,98 | `PEN-NEG-REM` |
| | operação `PC-0926-0162` repetida no relatório (spread da cópia) | 821,88 | `PEN-DUP-REM` |
| **Receita não faturada até o Comercial confirmar** | Atlas Idiomas, sem contrato: taxa que a Orbe descontou | 7.876,05 | `PEN-SEMCONTRATO` |
| **Caixa a identificar ou apurar** | PIX recebido sem identificação | 7.350,00 | `PEN-NAOID` |
| | PIX de repasse à Mundo Aberto que voltou, motivo desconhecido | 12.400,00 | `PEN-DEVOL-PIX` |
| **Conferir quando chegar** (acompanhamento, não é perda) | transferência Aurora → Meridiano de 30/09, que cai em 01/10 | 300.000,00 | `PEN-TRANSF` |
| | repasse da Ponte a conferir contra a nota de intermediação | 39.543,45 | `PEN-TED-PONTE` |

## Histórico de IA

O histórico completo das sessões de IA, de preparação e de construção, está em [`PROMPTS/`](PROMPTS/), sem
edição além da remoção de chaves e e-mails pessoais. Em [`PROMPTS/MOMENTOS.md`](PROMPTS/MOMENTOS.md) estão os
momentos que mudaram o projeto, inclusive os erros da IA que corrigimos. A tabela de prompts-chave de
[`PROMPTS/README.md`](PROMPTS/README.md) lista cada prompt que mudou uma regra, um número ou a arquitetura, com
o commit que ele gerou.

## Rodar do zero

Requisito: Python 3.11 ou mais novo. Último ensaio, em 17/10/2026 às 17h22: clone limpo do GitHub no commit
`e071606`, no Windows 11 com Python 3.13.14, seguindo só este README e sem chave de API. A instalação funcionou, o
`fechar` terminou com FECHAMENTO COMPLETO (código 0), e os 6 CSVs de `saida/` e os rascunhos de `contestacoes/`
saíram idênticos, byte a byte, aos do repositório; só `auditoria/` muda, porque registra a execução. No pytest,
488 de 489 testes passaram: `tests/test_regra_dados.py::test_data_invalida_numa_linha_da_orbe` falha antes do
Python 3.14, porque compara o texto de uma mensagem de erro do próprio Python. O cálculo não é afetado.

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Se a política de execução bloquear o `Activate.ps1`, troque `python` por `.venv\Scripts\python.exe` nos comandos.

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

No Ubuntu/Debian, o `venv` precisa do pacote do sistema `python3-venv` (`sudo apt install python3-venv`).

**Arquivos de entrada:** os arquivos do mês ficam em `dados/<AAAA-MM>/`, como chegaram. Setembro já está
em `dados/2026-09/`. Cada arquivo é achado pelo padrão de nome de `config/entradas.yaml`, não pelo nome exato:

| tipo | padrão | formato |
|------|--------|---------|
| Orbe (transações) | `*orbe*.csv` (um ou mais) | relatório e ajustes tardios no mesmo layout; `;`, vírgula decimal, UTF-8 |
| Taxas contratadas | `*taxas*.xlsx` | aba "Taxas vigentes"; taxa em fração ou texto ("2,59%") |
| Ponte Câmbio | `*.eml` | e-mail com o relatório XLSX anexo em base64 |
| Plano de contas | `*plano_de_contas*.csv` | `;`, Windows-1252 |
| Extrato Aurora | `*aurora*.csv` | `;`, UTF-8, cabeçalho e rodapé livres |
| Extrato Meridiano | `*.ofx` | OFX 1.02 SGML, cp1252 |

A Orbe aceita mais de um arquivo: o relatório e os ajustes que chegam depois, como o
`06_orbe_ajustes_tardios_set2026.csv`. Todos são lidos, e cada linha guarda no rastro o arquivo de onde veio.
Os outros tipos precisam de exatamente um arquivo. Se um arquivo faltar, sobrar ou não puder ser lido, o
fechamento não para: fecha o que não depende dele (ver "Fechamento parcial").

**Fechamento:**

```bash
python -m tarvo fechar --competencia 2026-09 --entrada dados/2026-09 --saida saida/
```

O comando lista os arquivos encontrados, grava os 6 CSVs em `--saida`, relê o que gravou e termina com um quadro:
**FECHAMENTO COMPLETO** ou **FECHAMENTO PARCIAL**, com as fontes bloqueadas, os itens que ficaram fora por erro de
dado e o que não foi gerado.

| código | significado |
|-------:|-------------|
| 0 | completo: todas as fontes lidas |
| 3 | parcial: alguma fonte bloqueada ou algum item fora por erro de dado; o resto foi gerado e validado, e cada caso vira uma pendência `PEN-BLOQUEIO` ou `PEN-REGRA` (R44) |
| 1 | a saída gerada não passou na validação, ou um arquivo de destino está travado (aberto no Excel: a mensagem diz "Feche <arquivo> e rode de novo"); nada foi gravado |
| 2 | erro que impede o fechamento: pasta de entrada inexistente, competência fora do formato AAAA-MM ou erro na configuração; nada foi gravado |

**Testes:**

```bash
python -m pytest
```

São 489 testes, sem acesso à rede. Incluem o fechamento de um outubro simulado (ver "Como rodar outubro").

## Fechamento parcial

Pedido da Helena (R44): *"Quando falta alguma coisa, eu não seguro o mês inteiro. Fecha o que não depende daquilo,
marca o que é provisório e deixa claro o que está bloqueado e por quê. Quem libera sou eu."*

| situação | o que acontece | código |
|----------|----------------|-------:|
| fonte ausente (nenhum arquivo casa com o padrão) | a fonte fica bloqueada e só o que depende dela não é gerado. Sem o `.ofx`, por exemplo, checkout, remessa e notas fecham; ficam de fora os lançamentos do Meridiano e as conferências P11, P12 e P13 | 3 |
| fonte ambígua (dois arquivos para um tipo que aceita só um) | bloqueada: o fechamento não escolhe um deles. Com dois `.eml`, a remessa e a nota da Ponte não são geradas | 3 |
| arquivo ilegível ou sem coluna obrigatória | bloqueado | 3 |
| arquivo de ajustes da Orbe com cabeçalho diferente do relatório (inclusive coluna a mais) | bloqueia só esse arquivo; o relatório é lido e o checkout sai marcado como provisório (coluna `situacao` = `PROVISORIO` nos CSVs) | 3 |
| coluna a mais ou fora de ordem numa fonte de arquivo único | só aviso (`PEN-AVISO-LAYOUT`); nada deixa de ser gerado | 0 |
| mesmo `id_transacao` com os mesmos dados em dois arquivos da Orbe | conta uma vez e vira pendência informativa (`PEN-REPET-CHK`, P27) | 0 |
| mesmo `id_transacao` com dados diferentes em dois arquivos da Orbe | é uma correção: a linha do arquivo posterior substitui a anterior, e a pendência `PEN-CORRECAO-ORBE` mostra o antes e o depois (P27). O checkout não fica provisório | 0 |
| linha com dado inválido num arquivo (número ou data em formato desconhecido, FITID repetido, campo obrigatório vazio) | só a linha fica de fora e vira `PEN-REGRA-LINHA-...`; o resto do arquivo é lido. Exceção: no plano de contas, uma linha ilegível bloqueia o plano inteiro | 3 |
| dado que nenhuma regra cobre (modalidade sem taxa, parcelas fora das faixas, CNPJ sem linha vigente na planilha, spread em texto, spread negativo de CNPJ fora da planilha, favorecido fora da planilha) | só a transação, a operação ou o lojista afetado fica de fora, com a pendência `PEN-REGRA-<tipo>` (tipo `ITEM_BLOQUEADO`). Testado: uma modalidade nova na Orbe tirou só aquela transação | 3 |

Cada bloqueio vira a pendência `PEN-BLOQUEIO-<fonte>`, de valor 0, com o arquivo, o erro exato, o que não foi
gerado e o próximo passo. Quem libera é a Helena; na planilha de taxas, o Comercial e a Helena (R28). Testamos com
cópias de `dados/2026-09`: sem o `.ofx`, com dois `.eml`, com o arquivo 06 sem uma coluna e com uma coluna a mais.
Todos terminaram com código 3 e o restante da saída validado.

## Chaves

Nenhuma chave é necessária. `ANTHROPIC_API_KEY` é **opcional**: só serve para a IA sugerir a conta de um
lançamento bancário que nenhuma regra cobre (ver "Onde a IA atua"). Sem a chave, tudo funciona, e o lançamento
sem regra fica para classificação humana.

```powershell
$env:ANTHROPIC_API_KEY = "<sua chave>"     # PowerShell
```
```bash
export ANTHROPIC_API_KEY="<sua chave>"     # bash
```

- **Reprodutível sem chave:** cada resposta do modelo fica em `cache/ia_sugestoes.json` (por hash do lançamento
  e do modelo), que vai para o git. Quem roda depois, com ou sem chave, obtém a mesma saída sem nova chamada.
  Em setembro o cache está vazio, porque não houve nenhuma chamada.
- **Desligar a IA:** `--sem-ia` no comando, ou `habilitada: false` em `config/ia.yaml`.

```bash
python -m tarvo fechar --competencia 2026-09 --entrada dados/2026-09 --saida saida/ --sem-ia
```

## O que sai em `saida/`

Todos os arquivos: separador `;`, ponto decimal, datas AAAA-MM-DD, UTF-8, CNPJ com 14 dígitos sem pontuação.
Os totais abaixo foram lidos dos CSVs gerados para setembro/2026 (contagem de linhas sem o cabeçalho).

| arquivo | conteúdo | linhas | soma da coluna de valor |
|---------|----------|-------:|------------------------:|
| `comissoes_por_lojista.csv` | comissão do mês por lojista e linha de negócio | 35 | `comissao_brl` = 243278.79 |
| `divergencias_taxa.csv` | transação ou operação com taxa aplicada ≠ contratada | 115 | `diferenca_brl` = 2995.08 |
| `notas_a_emitir.csv` | notas fiscais a emitir: uma por lojista (checkout) e uma para a Ponte (remessa) | 21 | `valor_brl` = 243284.29 |
| `lancamentos_classificados.csv` | cada lançamento dos dois extratos com a conta contábil (contrapartida) | 184 | `valor` = -1416088.18 |
| `pendencias.csv` | o que precisa de decisão humana, com valor, origem e quem decide | 16 | `valor_brl` = 382811.32 |
| `rastro.csv` | as linhas de origem de cada id_saida dos 5 arquivos acima | 5086 | `valor` = -543718.70 |

Por linha de negócio:

| arquivo | CHECKOUT | REMESSA |
|---------|----------|---------|
| `comissoes_por_lojista.csv` | 21 linhas, 203735.34 | 14 linhas, 39543.45 |
| `divergencias_taxa.csv` | 92 linhas, 1576.23 | 23 linhas, 1418.85 |
| `notas_a_emitir.csv` | 20 notas, 203740.84 | 1 nota, 39543.45 |

- A comissão de checkout (203735.34) é 5.50 menor que as notas de checkout (203740.84) porque a Casa do
  Estudante fechou o mês em -5.50: comissão zero ou negativa não emite nota e vira pendência (R06).
- A devolução da Casa do Estudante (15396.77, concessão comercial: custo da Tarvo, não se cobra da Orbe) fica
  fora das divergências, como pendência `DEVOLUCAO_CONCESSAO` (R10, R32, R38).
- **Ajustes tardios da Orbe:** o `06_orbe_ajustes_tardios_set2026.csv` (14 linhas: 10 estornos, 3 reversões de
  antecipação e 1 venda) entra junto com o relatório 01. As 28 linhas do rastro que vêm dele apontam para o
  arquivo 06.
- Lançamentos: 84 do Aurora e 100 do Meridiano, todos com `metodo` REGRA.
- **Rascunhos de contestação (R29):** além dos 6 CSVs, o fechamento grava em `contestacoes/`, pasta irmã de
  `saida/`, um rascunho de e-mail por contraparte (`orbe.md`, `ponte.md`) com as operações anexadas
  (`orbe_operacoes.csv`, 92 linhas; `ponte_operacoes.csv`, 28 linhas). A Helena revisa e envia.
  `--sem-contestacao` desliga os rascunhos.
- **Registro de execução (O06):** cada `fechar` que passa na validação grava em `auditoria/`, também ao lado de
  `saida/`, o `execucao.md` (legível) e o `execucao.json`: data e hora, commit do código, comando, SHA-256 de cada
  arquivo de entrada, linhas lidas e rejeitadas, status e código de saída. Guarda só a última execução, então rodar
  o fechamento de novo reescreve esses dois arquivos; os CSVs de `saida/` continuam idênticos.
- **Como o rastro fecha:** o `rastro.csv` tem uma ou mais linhas por id_saida (`arquivo_origem`, `ref_origem`,
  `valor`, e as colunas extras `regra` e `detalhe`, que dizem qual regra gerou o valor da linha e como, O06). Para
  cada id_saida, a soma do `valor` no rastro é igual ao valor reportado. Por isso a soma do
  rastro inteiro (-543718.70) é a soma das cinco colunas de valor acima. São 371 id_saida.
- **ref_origem:** `id_transacao` (Orbe), Nº Operação (Ponte), `L<n>` = número da linha física no arquivo (Aurora),
  FITID (Meridiano).

## Verificação independente

Os números de setembro foram conferidos por um **recálculo independente em script**, feito sem o código do
pipeline, e bateram ao centavo. A prova está em três lugares:

- **Commit `d588ad9`** (16/10, 23h43), no histórico do `main`: os testes daquele commit guardam os valores do
  recálculo, feito direto de `dados/`. São 20 notas de checkout = 207045.23, nota da Ponte = 39543.45,
  210 divergências de checkout e 184 lançamentos. A nota da Ponte e os lançamentos continuam iguais na `saida/`
  atual. Dois números mudaram depois, por fatos novos e não por erro do recálculo: as divergências de checkout
  caíram para 92 porque a Helena separou a devolução da Casa do Estudante (118 linhas) das divergências (R32,
  R38), e as notas de checkout foram para 203740.84 com os ajustes tardios da Orbe (arquivo 06).
- **Transcript `be5d287e`**, em `PROMPTS/sessoes/`: a sessão em que esse recálculo foi feito.
- **Revisão adversarial:** uma sessão só de leitura, sem importar `src/`, recalculou tudo e questionou 7
  premissas (P15–P21). A decisão sobre cada uma, com o número alternativo, está no `HIPOTESES.md`.

Essa conferência usou as regras confirmadas até 16/10. As respostas da Helena que vieram depois estão no
`HIPOTESES.md`, e os números que elas mudaram são conferidos pelos testes em `tests/` e no `RESULTADOS.md`.

## Como funciona

Sete etapas, orquestradas por `src/tarvo/fechamento.py`:

| etapa | o que faz | código | configuração |
|-------|-----------|--------|--------------|
| 1. Leitura | acha os arquivos pelo padrão de nome (a Orbe aceita o relatório e os ajustes tardios) e lê cada um com o encoding explícito; fonte ausente, ambígua ou ilegível fica bloqueada (R44); cada linha sai com `arquivo_origem` e `ref_origem` | `cli.py`, `dependencias.py`, `leitores/orbe.py`, `taxas.py`, `ponte.py`, `plano_contas.py`, `aurora.py`, `meridiano.py` | `config/entradas.yaml` |
| 2. Normalização | número brasileiro → `Decimal`, data → `datetime.date`, CNPJ → 14 dígitos, taxa → pontos percentuais. Os leitores só convertem tipos, sem regra de negócio | `leitores/comum.py` e os leitores | — |
| 3. Cálculo por regra | comissão, divergência, nota e pendência do checkout e da remessa; classificação contábil dos extratos. Cada regra cita o seu R## ou P## do `HIPOTESES.md` | `checkout.py`, `remessa.py`, `bancos.py` (e `ia.py`, só para lançamento sem regra) | `config/checkout.yaml`, `remessa.yaml`, `bancos.yaml`, `favorecidos.yaml`, `pagadores_meridiano.yaml`, `ia.yaml` |
| 4. Conferências cruzadas | Orbe × planilha (EC sem contrato), duplicatas da Ponte (R13), TED de liquidação Ponte × Meridiano (P11), PIX recebidos × remessas por CNPJ (P12), transferência Aurora × Meridiano (P13), TED de repasse × nota de remessa (R18, P22). Toda diferença vira pendência | `checkout.py`, `remessa.py`, `bancos.py` | as mesmas da etapa 3 |
| 5. Saída com rastro | cada resultado é um `ItemSaida` com as suas origens, e o item não é criado se a soma das origens não fechar com o valor. Grava os 6 CSVs e relê tudo: formato, domínios, id_saida único e soma do rastro por id_saida | `saida.py`, `fechamento.py` | — |
| 6. Rascunhos de contestação | depois da validação, monta um rascunho de e-mail por contraparte (Orbe e Ponte), com as operações anexadas e uma nota interna para a Helena, e grava em `contestacoes/`, ao lado de `saida/`. Desliga com `--sem-contestacao` | `contestacao.py`, `fechamento.py` | `config/contestacao.yaml` |
| 7. Registro de execução | grava em `auditoria/` o que foi lido (com SHA-256), o comando, o commit, o status e o código de saída da última execução. Antes de gravar, confere que nenhum destino está travado; se um estiver, nada é trocado | `auditoria.py`, `fechamento.py` | `config/auditoria.yaml` |

Dinheiro é sempre `Decimal` com 2 casas, arredondado linha a linha com ROUND_HALF_UP (R02); a escrita nunca
arredonda nem troca texto: valor com casas a mais ou texto com `;` é erro.

## Onde estão as regras

- **`HIPOTESES.md`:** a fonte de toda regra de negócio.
  - **R##:** regras confirmadas pela Helena (financeiro da Tarvo, no Slack), com o horário de cada resposta. A lista completa e atual fica só no `HIPOTESES.md`.
  - **P##:** premissas nossas, cada uma com o motivo. Inclui as escolhas mantidas após a revisão independente (P15–P21).
  - Também traz as pendências em aberto, os conflitos resolvidos e as decisões de formato e encoding.
- **`config/*.yaml`:** os parâmetros e mapeamentos das regras: taxas especiais, ECs sem código, participação de
  50%, spread padrão, tolerância, regras de classificação por extrato, listas de favorecidos e pagadores.
  Nenhum valor, data, CNPJ ou nome de arquivo de setembro fica fixo em `src/`.
- Toda regra do código e da configuração cita o seu R## ou P##. Em `config/bancos.yaml`, a carga falha se o
  campo `fonte` de uma regra não for R## ou P##.

## Onde a IA atua e onde não atua

- **Não atua:** cálculo de comissão, divergência, nota, pendência, conferências cruzadas e classificação por regra.
  Tudo isso é determinístico, sai com `metodo` REGRA, e a mesma entrada dá sempre a mesma saída.
- **Atua só aqui (P14):** um lançamento bancário que nenhuma das regras de `config/bancos.yaml` cobre. O modelo
  (`claude-sonnet-5-5`, em `config/ia.yaml`) recebe as contas analíticas do plano, o texto da R19 e exemplos já
  classificados por regra do mesmo extrato, e sugere a conta com confiança de 0 a 1 e uma justificativa.
  - O lançamento sai com `metodo` IA e **sempre** gera a pendência `REVISAR_SUGESTAO_IA` para o Financeiro revisar.
    Abaixo de 0,80 de confiança, o motivo diz "baixa confiança".
  - Sugestão inválida (conta inexistente ou sintética, JSON inválido, resposta cortada ou recusada, falha de
    chamada) é descartada, e o lançamento volta ao fluxo sem IA: `A_CLASSIFICAR`, `metodo` HUMANO, confiança 0,
    pendência `LANCAMENTO_SEM_REGRA` (P09).
  - A IA não cria regra nem mexe nas listas de favorecidos e pagadores: um PIX de pagador fora da lista não
    vira cliente da Ponte por causa dela.
- **Em setembro: zero chamadas.** Todos os 184 lançamentos casam uma regra.
- **Custo:** uma chamada por lançamento sem regra que ainda não esteja no cache. Os testes usam um cliente falso.

## Como rodar outubro

O mesmo comando fecha qualquer mês, sem mexer no código: só mudam a competência e as pastas.

1. Ponha os arquivos do mês, como chegaram, numa pasta **fora deste repositório**. Os nomes podem mudar,
   desde que casem com os padrões da tabela de entradas.
2. Rode, com a saída também fora do repositório:
   ```bash
   python -m tarvo fechar --competencia 2026-10 --entrada <pasta com os arquivos de outubro> --saida <pasta de saída de outubro>
   ```
   `dados/` (somente leitura) e `saida/` (os 6 CSVs de setembro, que são a entrega) não são tocados.
3. Siga "Como a analista usa no fechamento", abaixo. Atenção às pendências que vêm de setembro (ver "Limitações").

**Ensaio sem os arquivos reais:** `tests/gerar_outubro.py` gera um outubro simulado a partir de setembro (datas
+1 mês e quatro casos novos: venda de EC fora da planilha, PIX enviado a favorecido desconhecido, PIX recebido
de pagador fora da lista, operação da Ponte de CNPJ fora da planilha). Tudo vai para uma pasta temporária:

```bash
python tests/gerar_outubro.py dados/2026-09 <pasta temporária>/dados/2026-10
python -m tarvo fechar --competencia 2026-10 --entrada <pasta temporária>/dados/2026-10 --saida <pasta temporária>/saida --sem-ia
python -m tarvo resumo --saida <pasta temporária>/saida
```

O gerador só lê `dados/2026-09`: nada é gravado no repositório. O mesmo ensaio roda dentro de
`python -m pytest tests/test_outubro.py`, também em pasta temporária, e o resultado está na seção 7 do `RESULTADOS.md`.

## Como a analista usa no fechamento

1. **Rodar** o fechamento do mês (comando acima). Se terminar com **FECHAMENTO PARCIAL**, começar pelas
   pendências `PEN-BLOQUEIO` e `PEN-REGRA`: cada uma diz o arquivo ou o item, o erro e o próximo passo (ver
   "Fechamento parcial"). Se parar com erro, a mensagem diz o arquivo, a linha e o motivo (ver "O que ainda para
   tudo", em "Limitações conhecidas").
2. **Abrir `pendencias.csv`.** Cada linha tem tipo, `ref_origem` (as linhas de origem, separadas por `|`), valor,
   motivo e quem decide. Tipos possíveis:

   | tipo | regra | quem decide | o que fazer | set/2026 |
   |------|-------|-------------|-------------|---------:|
   | `NOTA_NAO_EMITIDA` | R06, R16, R17 | Financeiro (Helena) | comissão do mês zero ou negativa, no checkout ou na nota da Ponte: decidir o tratamento (não passa para o mês seguinte) | 1 |
   | `DEVOLUCAO_LOJISTA` | R03, R25, R32, R45 | Financeiro (Helena) | devolver ao lojista o que foi descontado acima do contrato (taxa descontada pela Orbe menos a comissão contratada) | 2 |
   | `DEVOLUCAO_CONCESSAO` | R10, R32, R38, R41, R45 | Financeiro (Helena) e Comercial | devolver ao lojista a taxa cobrada numa concessão comercial: custo da Tarvo, não se cobra da Orbe | 1 |
   | `ALERTA_ANTECIPACAO` | R33, P26 | Financeiro (Helena) e Comercial | lojista sem histórico antecipou mais do que vendeu no mês: avaliar o risco (não muda nenhum valor) | 1 |
   | `LOJISTA_SEM_CONTRATO` | R08, R60 | Comercial (Diego) | EC da Orbe sem taxa contratada: confirmar o contrato antes de faturar | 1 |
   | `LOJISTA_NAO_CADASTRADO` | P04 | Financeiro (Helena) | CNPJ da Ponte fora da planilha: cadastrar (a comissão já entrou na nota) | 0 |
   | `CONTESTACAO_PONTE` | R12, R15, R16, R18, R23, R34 | Financeiro (Helena) | contestar com a Ponte o spread acima do contrato ou negativo | 5 |
   | `OPERACAO_DUPLICADA` | R13, P19 | Financeiro (Helena) | pedir à Ponte a correção do relatório | 1 |
   | `AJUSTE_SEM_OPERACAO_ORIGINAL` | R31, P25 | Financeiro (Helena) | ajuste da Ponte cuja operação original não está no relatório: conferir (já abatido da participação) | 0 |
   | `AJUSTE_SEM_LOJISTA` | R31 | Financeiro (Helena) | ajuste da Ponte sem CNPJ nem operação original: identificar o lojista (não foi abatido) | 0 |
   | `FONTE_BLOQUEADA` | R44 | Financeiro (Helena); na planilha de taxas, Comercial e Financeiro (Helena) | fonte ausente, ambígua ou ilegível: seguir o próximo passo da pendência e rodar de novo | 0 |
   | `ARQUIVO_BLOQUEADO` | R28, R44 | Financeiro (Helena) | arquivo de ajustes da Orbe com cabeçalho diferente do relatório: pedir à Orbe o arquivo no layout do relatório; até lá o checkout é provisório | 0 |
   | `AVISO_LAYOUT` | R44 | quem decide a fonte | coluna a mais ou fora de ordem: confirmar com quem mandou que o layout mudou | 0 |
   | `TRANSACAO_REPETIDA` | P27 | Financeiro (Helena) | mesmo id_transacao em dois arquivos da Orbe, com os mesmos dados: contado uma vez; confirmar | 0 |
   | `REFERENCIA_NAO_ENCONTRADA` | R48 | Financeiro (Helena) | estorno ou reversão sem a transação original em nenhum arquivo da Orbe: entra pelo valor que veio, e a pendência mostra o efeito na comissão; a Helena pede a venda original à Orbe | 0 |
   | `CORRECAO_ORBE` | P27 | Financeiro (Helena) | id_transacao que veio de novo, com dados diferentes, num arquivo posterior da Orbe: vale a linha nova; conferir o antes e o depois | 0 |
   | `AJUSTE_APOS_APROVACAO` | R46 | Financeiro (Helena) | ajuste da Orbe de um mês já aprovado, recebido depois: entra no mês atual, sem reabrir o mês aprovado | 0 |
   | `ITEM_BLOQUEADO` | R44, R51 | Comercial se for taxa, cadastro ou vigência; Financeiro (Helena) nos demais | dado sem regra ou linha inválida (ids `PEN-REGRA-...`): o item ficou fora do fechamento; corrigir o dado e rodar de novo | 0 |
   | `CONFERENCIA_NAO_FEITA` | R44 | Financeiro (Helena) | conferência cruzada que não rodou porque uma fonte ficou bloqueada: refazer quando a fonte for liberada | 0 |
   | `OPERACAO_FORA_DA_COMPETENCIA` | R11 | Financeiro (Helena) | operação contratada em outro mês: conferir | 0 |
   | `CONFERENCIA_REPASSE` | R18, P22 | Financeiro (Helena) | conferir o TED de repasse da Ponte contra a nota de remessa quando cair | 1 |
   | `CREDITO_NAO_IDENTIFICADO` | R20 | Financeiro (Helena) | identificar o PIX recebido; não é receita até lá | 1 |
   | `DEVOLUCAO_PIX` | R20, P06 | Financeiro (Helena) | apurar o motivo do repasse que voltou | 1 |
   | `DIFERENCA_PIX_REMESSA` | P12 | Financeiro (Helena) | PIX recebidos de um cliente ≠ operações dele no mês | 0 |
   | `DIVERGENCIA_TED_LIQUIDACAO` | P11 | Financeiro (Helena) | TED de liquidação ≠ operações da Ponte na data | 0 |
   | `TRANSFERENCIA_EM_TRANSITO` | R20, P13, P20 | Financeiro (Helena) | conferir a chegada no Meridiano no extrato do mês seguinte | 1 |
   | `TRANSFERENCIA_SEM_PAR` | P13 | Financeiro (Helena) | transferência do Aurora sem TED correspondente no Meridiano | 0 |
   | `LANCAMENTO_SEM_REGRA` | P09 | Financeiro (Helena) | classificar o lançamento (`A_CLASSIFICAR`) | 0 |
   | `REVISAR_SUGESTAO_IA` | P14 | Financeiro | aceitar ou corrigir a conta sugerida pela IA | 0 |

3. **Resolver** cada pendência com quem decide. O código não decide nenhuma delas.
4. **Enviar as contestações.** A Helena revisa os rascunhos em `contestacoes/` (`orbe.md` e `ponte.md`, com as
   operações em CSV), apaga o bloco de notas internas e envia (R29).
5. **Ajustar a configuração**, quando a resolução virar regra:
   - favorecido ou pagador de PIX que é lojista: cadastrar o texto exato do extrato e o CNPJ da planilha em
     `config/favorecidos.yaml` (Aurora, P07) ou `config/pagadores_meridiano.yaml` (Meridiano, P08);
   - tipo de lançamento novo e recorrente: uma regra em `config/bancos.yaml`, com `fonte` R## ou P##;
   - regra de negócio nova: primeiro entra no `HIPOTESES.md` (R## se veio do financeiro, P## se é premissa,
     com o motivo), depois na configuração ou no código, com teste.
6. **Rodar de novo.** As pendências resolvidas por configuração somem, e o restante continua listado.

## Limitações conhecidas

- **O que não fecha automaticamente entre meses.** Cada execução olha só os arquivos do mês:
  - **TED em trânsito:** a transferência de 30/09 aparece em setembro como `TRANSFERENCIA_EM_TRANSITO`. Em
    outubro, a TED de mesma titularidade que chega no Meridiano é classificada por regra (1.1.09.001), mas não é
    casada com a pendência de setembro, porque o Aurora de outubro não traz a saída. A baixa é manual.
  - **Repasse da Ponte:** o TED de repasse da comissão de setembro cai em outubro e é classificado por regra
    (1.1.03.002). A conferência contra a nota de remessa de setembro (`CONFERENCIA_REPASSE`, R18) é manual.
  - Pendências de setembro (contestações, devoluções, crédito não identificado) não são reabertas nem baixadas
    pelo fechamento de outubro.
- **Conciliação Orbe × banco está fora do escopo (R21).** Os créditos da Orbe no Aurora são só classificados,
  não conciliados parcela a parcela com o relatório da Orbe.
- **Favorecidos e pagadores novos dependem de cadastro.** Não há casamento por nome aproximado: quem não estiver
  em `config/favorecidos.yaml` ou `config/pagadores_meridiano.yaml` vira lançamento sem regra (P07–P09), e um PIX
  de cliente fora da lista não entra na conferência PIX × remessas (P12).
- **Dia útil sem calendário de feriados.** O "dia útil seguinte" da transferência entre contas (P13) pula só
  sábado e domingo. Uma transferência na véspera de feriado aparece como em trânsito ou sem par.
- **A conferência de TED de liquidação (P11)** só considera as datas dentro do período do extrato do Meridiano
  (DTSTART a DTEND).
- **Vigências na configuração.** A concessão comercial da Casa do Estudante (R10, R32, R40: isenção para vendas
  a partir de 01/09; estorno de venda anterior segue a taxa da venda) vale até 2026-12-31 em
  `config/checkout.yaml`; renovações e contratos novos precisam ser atualizados lá e na planilha de taxas.
- **Nomes fixos de abas e colunas.** A planilha de taxas precisa ter a aba "Taxas vigentes", e o relatório da
  Ponte, a aba "Operações" com a coluna "Nº Operação". Se o formato mudar, a fonte fica bloqueada (ilegível), sem
  parar o mês.
- **Problema de arquivo ou de dado não para mais o mês (R44):**
  - arquivo ausente, mais de um para um tipo que aceita só um, ou ilegível (coluna obrigatória ausente) bloqueia
    a fonte;
  - linha com número ou data em formato desconhecido, FITID repetido ou campo obrigatório vazio sai sozinha
    (`PEN-REGRA-LINHA`);
  - dado que nenhuma regra cobre tira só o item afetado (`PEN-REGRA-<tipo>`): CNPJ sem linha vigente na
    planilha ou com mais de uma, tipo de lançamento ou modalidade da Orbe sem taxa, parcelas fora das faixas,
    texto de spread que não é número nem "padrão" (R14), Nº Operação repetido com valores diferentes (R13),
    spread negativo de CNPJ fora da planilha (P05), favorecido ou pagador com CNPJ fora da planilha.
  Ver "Fechamento parcial".
- **O que ainda para tudo, sem gravar nada:** pasta de entrada inexistente, competência fora do formato ou erro
  na configuração (código 2), e saída fora do formato ou que não feche com o rastro (código 1).

## Estrutura do repositório

```
├── README.md
├── HIPOTESES.md              regras (R##) e premissas (P##): a fonte de toda regra de negócio
├── CLAUDE.md                 regras para quem (pessoa ou IA) mexe no código
├── RESULTADOS.md             números do fechamento conferidos contra os testes
├── PROMPTS/
│   ├── README.md             como o histórico está organizado e os prompts-chave
│   ├── MOMENTOS.md           momentos em que a IA errou ou ajudou, e o que fizemos
│   ├── antigravity_resumo_prompts_16-10.txt  resumo dos prompts do Antigravity (16/10)
│   └── sessoes/              transcripts das sessões de IA (Claude Code e Antigravity)
├── scripts/exportar_transcript.py  exporta os transcripts sem e-mails pessoais e chaves
├── pyproject.toml            pacote, dependências e configuração do pytest
├── requirements.txt          as mesmas dependências, em lista
├── config/
│   ├── entradas.yaml         padrões de nome de cada fonte (a Orbe aceita vários arquivos)
│   ├── checkout.yaml         ECs sem código, condição especial, taxa por modalidade
│   ├── remessa.yaml          participação, spread padrão, tolerância, tomador da nota
│   ├── bancos.yaml           regras de classificação dos extratos, em ordem
│   ├── favorecidos.yaml      PIX enviados do Aurora que são repasse a lojista (P07)
│   ├── pagadores_meridiano.yaml  PIX recebidos no Meridiano de clientes da remessa (P08)
│   ├── auditoria.yaml        pasta do registro de execução (O06)
│   ├── contestacao.yaml      pasta e textos dos rascunhos de contestação (R29)
│   └── ia.yaml               modelo, limiar e cache da IA (P14)
├── src/tarvo/
│   ├── cli.py, __main__.py   comando `python -m tarvo fechar`
│   ├── fechamento.py         orquestra leitura, módulos, gravação e validação
│   ├── dependencias.py       fontes bloqueadas e o que depende de cada uma (R44)
│   ├── leitores/             um leitor por arquivo + comum.py (conversões) e layout.py (colunas obrigatórias)
│   ├── checkout.py           linha CHECKOUT (Orbe)
│   ├── remessa.py            linha REMESSA (Ponte Câmbio)
│   ├── bancos.py             classificação dos extratos e conferências cruzadas
│   ├── ia.py                 sugestão de conta para lançamento sem regra
│   ├── auditoria.py          registro de execução em auditoria/ (O06)
│   ├── contestacao.py        rascunhos de contestação por contraparte (R29)
│   └── saida.py              ItemSaida, escrita e validação dos 6 CSVs
├── tests/                    489 testes + gerar_outubro.py (outubro simulado)
├── dados/2026-09/            data pack de setembro, como recebido (com os ajustes tardios da Orbe, arquivo 06)
├── cache/ia_sugestoes.json   respostas da IA já obtidas (vazio em setembro)
├── saida/                    os 6 CSVs de setembro
├── contestacoes/             rascunhos de contestação para a Helena revisar (R29)
└── auditoria/                registro da última execução do fechamento (O06)
```
