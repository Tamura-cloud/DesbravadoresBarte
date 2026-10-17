# Fechamento mensal — Tarvo Pagamentos

**Time Desbravadores Barte** · Desafio Barte AI, case Tarvo (17/10/2026)

Fecha o mês da Tarvo a partir dos 6 arquivos do data pack, lidos como vêm (sem edição manual), e gera os
6 CSVs de `saida/`. Cada número de saída é rastreável até a linha do arquivo de origem pelo `rastro.csv`,
e a execução falha se algum valor não fechar com o rastro.

## Histórico de IA

O histórico completo das sessões de IA, de preparação e de construção, está em [`PROMPTS/`](PROMPTS/), sem
edição além da remoção de chaves e e-mails pessoais. Em [`PROMPTS/MOMENTOS.md`](PROMPTS/MOMENTOS.md) estão os
momentos que mudaram o projeto, inclusive os erros da IA que corrigimos. A tabela de prompts-chave de
[`PROMPTS/README.md`](PROMPTS/README.md) lista cada prompt que mudou uma regra, um número ou a arquitetura, com
o commit que ele gerou.

## Rodar do zero

Requisito: Python 3.11 ou mais novo. Testado a partir de um clone limpo no Windows 11 (Python 3.14) e no
Linux (Python 3.11): instalação, fechamento e testes. A saída gerada é idêntica, byte a byte, à de `saida/`.

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

**Arquivos de entrada:** os 6 arquivos do mês ficam em `dados/<AAAA-MM>/`, como chegaram. Setembro já está
em `dados/2026-09/`. Cada arquivo é achado pelo padrão de nome de `config/entradas.yaml`, não pelo nome exato:

| tipo | padrão | formato |
|------|--------|---------|
| Orbe (transações) | `*orbe*.csv` | `;`, vírgula decimal, UTF-8 |
| Taxas contratadas | `*taxas*.xlsx` | aba "Taxas vigentes"; taxa em fração ou texto ("2,59%") |
| Ponte Câmbio | `*.eml` | e-mail com o relatório XLSX anexo em base64 |
| Plano de contas | `*plano_de_contas*.csv` | `;`, Windows-1252 |
| Extrato Aurora | `*aurora*.csv` | `;`, UTF-8, cabeçalho e rodapé livres |
| Extrato Meridiano | `*.ofx` | OFX 1.02 SGML, cp1252 |

Precisa haver exatamente um arquivo por padrão. Se faltar ou sobrar, o comando para e diz qual.

**Fechamento:**

```bash
python -m tarvo fechar --competencia 2026-09 --entrada dados/2026-09 --saida saida/
```

O comando lista os arquivos encontrados, grava os 6 CSVs em `--saida` e relê o que gravou. Sai com código 0
só se a validação não achar problema; sai com 1 ou 2 se a saída ou uma entrada estiver com problema.

**Testes:**

```bash
python -m pytest
```

São 303 testes, sem acesso à rede. Incluem o fechamento de um outubro simulado (ver "Como rodar outubro").

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
| `comissoes_por_lojista.csv` | comissão do mês por lojista e linha de negócio | 35 | `comissao_brl` = 246583.18 |
| `divergencias_taxa.csv` | transação ou operação com taxa aplicada ≠ contratada | 233 | `diferenca_brl` = 18392.50 |
| `notas_a_emitir.csv` | notas fiscais a emitir: uma por lojista (checkout) e uma para a Ponte (remessa) | 21 | `valor_brl` = 246588.68 |
| `lancamentos_classificados.csv` | cada lançamento dos dois extratos com a conta contábil (contrapartida) | 184 | `valor` = -1416088.18 |
| `pendencias.csv` | o que precisa de decisão humana, com valor, origem e quem decide | 15 | `valor_brl` = 382811.75 |
| `rastro.csv` | as linhas de origem de cada id_saida dos 5 arquivos acima | 5171 | `valor` = -521712.07 |

Por linha de negócio:

| arquivo | CHECKOUT | REMESSA |
|---------|----------|---------|
| `comissoes_por_lojista.csv` | 21 linhas, 207039.73 | 14 linhas, 39543.45 |
| `divergencias_taxa.csv` | 210 linhas, 16973.65 | 23 linhas, 1418.85 |
| `notas_a_emitir.csv` | 20 notas, 207045.23 | 1 nota, 39543.45 |

- A comissão de checkout (207039.73) é 5.50 menor que as notas de checkout (207045.23) porque a Casa do
  Estudante fechou o mês em -5.50: comissão zero ou negativa não emite nota e vira pendência (R06).
- Lançamentos: 84 do Aurora e 100 do Meridiano, todos com `metodo` REGRA.
- **Como o rastro fecha:** o `rastro.csv` tem uma ou mais linhas por id_saida (`arquivo_origem`, `ref_origem`,
  `valor`). Para cada id_saida, a soma do `valor` no rastro é igual ao valor reportado. Por isso a soma do
  rastro inteiro (-521712.07) é a soma das cinco colunas de valor acima. São 488 id_saida.
- **ref_origem:** `id_transacao` (Orbe), Nº Operação (Ponte), `L<n>` = número da linha física no arquivo (Aurora),
  FITID (Meridiano).

## Verificação independente

Os números de setembro foram conferidos por um **recálculo independente em script**, feito sem o código do
pipeline, e bateram ao centavo. A prova está em três lugares:

- **Commit `d588ad9`** (16/10, 23h43), no histórico do `main`: os testes daquele commit guardam os valores do
  recálculo, feito direto de `dados/`. São 20 notas de checkout = 207045.23, nota da Ponte = 39543.45,
  210 divergências de checkout e 184 lançamentos, os mesmos quatro números da `saida/` atual.
- **Transcript `be5d287e`**, em `PROMPTS/sessoes/`: a sessão em que esse recálculo foi feito.
- **Revisão adversarial:** uma sessão só de leitura, sem importar `src/`, recalculou tudo e questionou 7
  premissas (P15–P21). A decisão sobre cada uma, com o número alternativo, está no `HIPOTESES.md`.

Essa conferência usou as regras confirmadas até 16/10. As respostas da Helena que vieram depois estão no
`HIPOTESES.md`, e os números que elas mudaram são conferidos pelos testes em `tests/` e no `RESULTADOS.md`.

## Como funciona

Cinco etapas, orquestradas por `src/tarvo/fechamento.py`:

| etapa | o que faz | código | configuração |
|-------|-----------|--------|--------------|
| 1. Leitura | acha os 6 arquivos pelo padrão de nome e lê cada um com o encoding explícito; cada linha sai com `arquivo_origem` e `ref_origem` | `cli.py`, `leitores/orbe.py`, `taxas.py`, `ponte.py`, `plano_contas.py`, `aurora.py`, `meridiano.py` | `config/entradas.yaml` |
| 2. Normalização | número brasileiro → `Decimal`, data → `datetime.date`, CNPJ → 14 dígitos, taxa → pontos percentuais. Os leitores só convertem tipos, sem regra de negócio | `leitores/comum.py` e os leitores | — |
| 3. Cálculo por regra | comissão, divergência, nota e pendência do checkout e da remessa; classificação contábil dos extratos. Cada regra cita o seu R## ou P## do `HIPOTESES.md` | `checkout.py`, `remessa.py`, `bancos.py` (e `ia.py`, só para lançamento sem regra) | `config/checkout.yaml`, `remessa.yaml`, `bancos.yaml`, `favorecidos.yaml`, `pagadores_meridiano.yaml`, `ia.yaml` |
| 4. Conferências cruzadas | Orbe × planilha (EC sem contrato), duplicatas da Ponte (R13), TED de liquidação Ponte × Meridiano (P11), PIX recebidos × remessas por CNPJ (P12), transferência Aurora × Meridiano (P13), TED de repasse × nota de remessa (R18, P22). Toda diferença vira pendência | `checkout.py`, `remessa.py`, `bancos.py` | as mesmas da etapa 3 |
| 5. Saída com rastro | cada resultado é um `ItemSaida` com as suas origens, e o item não é criado se a soma das origens não fechar com o valor. Grava os 6 CSVs e relê tudo: formato, domínios, id_saida único e soma do rastro por id_saida | `saida.py`, `fechamento.py` | — |

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

1. Ponha os 6 arquivos de outubro, como chegaram, em `dados/2026-10/`. Os nomes podem mudar, desde que casem
   com os padrões da tabela de entradas.
2. Rode:
   ```bash
   python -m tarvo fechar --competencia 2026-10 --entrada dados/2026-10 --saida saida/
   ```
   Isso substitui os CSVs de setembro em `saida/` (setembro continua no git). Para manter os dois meses lado a
   lado, use outra pasta, por exemplo `--saida saida/2026-10/`.
3. Siga "Como a analista usa no fechamento", abaixo. Atenção às pendências que vêm de setembro (ver "Limitações").

**Ensaio sem os arquivos reais:** `tests/gerar_outubro.py` gera um outubro simulado a partir de setembro (datas
+1 mês e quatro casos novos: venda de EC fora da planilha, PIX enviado a favorecido desconhecido, PIX recebido
de pagador fora da lista, operação da Ponte de CNPJ fora da planilha).

```bash
python tests/gerar_outubro.py dados/2026-09 dados/2026-10
python -m tarvo fechar --competencia 2026-10 --entrada dados/2026-10 --saida saida_outubro/ --sem-ia
```

O mesmo ensaio roda dentro de `python -m pytest tests/test_outubro.py`, em pasta temporária. Apague
`dados/2026-10/` antes de colocar os arquivos reais: o simulado não é o outubro de verdade.

## Como a analista usa no fechamento

1. **Rodar** o fechamento do mês (comando acima). Se ele parar com erro, a mensagem diz o arquivo, a linha e o
   motivo (ver "Casos que param com erro").
2. **Abrir `pendencias.csv`.** Cada linha tem tipo, `ref_origem` (as linhas de origem, separadas por `|`), valor,
   motivo e quem decide. Tipos possíveis:

   | tipo | regra | quem decide | o que fazer | set/2026 |
   |------|-------|-------------|-------------|---------:|
   | `NOTA_NAO_EMITIDA` | R06 | Financeiro (Helena) | comissão do mês zero ou negativa: decidir o tratamento (não passa para o mês seguinte) | 1 |
   | `DEVOLUCAO_LOJISTA` | R03, R10, P23 | Financeiro (Helena) | devolver ao lojista o que foi cobrado acima do contrato | 3 |
   | `LOJISTA_SEM_CONTRATO` | R08 | Comercial | EC da Orbe sem taxa contratada: confirmar o contrato antes de faturar | 1 |
   | `LOJISTA_NAO_CADASTRADO` | P04 | Financeiro (Helena) | CNPJ da Ponte fora da planilha: cadastrar (a comissão já entrou na nota) | 0 |
   | `CONTESTACAO_PONTE` | R12, R15, R16, R18, R23 | Financeiro (Helena) | contestar com a Ponte o spread acima do contrato ou negativo | 5 |
   | `OPERACAO_DUPLICADA` | R13, P19 | Financeiro (Helena) | pedir à Ponte a correção do relatório | 1 |
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
4. **Ajustar a configuração**, quando a resolução virar regra:
   - favorecido ou pagador de PIX que é lojista: cadastrar o texto exato do extrato e o CNPJ da planilha em
     `config/favorecidos.yaml` (Aurora, P07) ou `config/pagadores_meridiano.yaml` (Meridiano, P08);
   - tipo de lançamento novo e recorrente: uma regra em `config/bancos.yaml`, com `fonte` R## ou P##;
   - regra de negócio nova: primeiro entra no `HIPOTESES.md` (R## se veio do financeiro, P## se é premissa,
     com o motivo), depois na configuração ou no código, com teste.
5. **Rodar de novo.** As pendências resolvidas por configuração somem, e o restante continua listado.

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
- **Vigências na configuração.** A condição especial da Casa do Estudante (R10) vale até 2026-12-31 em
  `config/checkout.yaml`; renovações e contratos novos precisam ser atualizados lá e na planilha de taxas.
- **Nomes fixos de abas e colunas.** A planilha de taxas precisa ter a aba "Taxas vigentes", e o relatório da
  Ponte, a aba "Operações" com a coluna "Nº Operação". Se o formato mudar, a leitura para com erro.
- **Casos que param com erro, de propósito, em vez de supor:**
  - arquivo de entrada ausente, ou mais de um para o mesmo padrão;
  - coluna esperada ausente, número ou data em formato desconhecido, FITID repetido, OFX sem DTSTART/DTEND;
  - CNPJ sem linha vigente na planilha, ou com mais de uma, na data da transação; EC com dois CNPJs;
  - tipo de lançamento ou modalidade da Orbe sem taxa mapeada; parcelas fora das faixas da configuração;
  - texto de spread na planilha que não é número nem "padrão" (R14);
  - Nº Operação repetido com valores diferentes além da observação (R13);
  - spread negativo de CNPJ fora da planilha (P05);
  - lojista com divergências com e sem condição especial no mesmo mês (P23);
  - CNPJ em `favorecidos.yaml` ou `pagadores_meridiano.yaml` que não está na planilha;
  - qualquer saída fora do formato ou que não feche com o rastro.

## Estrutura do repositório

```
├── README.md
├── HIPOTESES.md              regras (R##) e premissas (P##): a fonte de toda regra de negócio
├── CLAUDE.md                 regras para quem (pessoa ou IA) mexe no código
├── PROMPTS/MOMENTOS.md       momentos em que a IA errou ou ajudou, e o que fizemos
├── pyproject.toml            pacote, dependências e configuração do pytest
├── requirements.txt          as mesmas dependências, em lista
├── config/
│   ├── entradas.yaml         padrões de nome dos 6 arquivos
│   ├── checkout.yaml         ECs sem código, condição especial, taxa por modalidade
│   ├── remessa.yaml          participação, spread padrão, tolerância, tomador da nota
│   ├── bancos.yaml           regras de classificação dos extratos, em ordem
│   ├── favorecidos.yaml      PIX enviados do Aurora que são repasse a lojista (P07)
│   ├── pagadores_meridiano.yaml  PIX recebidos no Meridiano de clientes da remessa (P08)
│   └── ia.yaml               modelo, limiar e cache da IA (P14)
├── src/tarvo/
│   ├── cli.py, __main__.py   comando `python -m tarvo fechar`
│   ├── fechamento.py         orquestra leitura, módulos, gravação e validação
│   ├── leitores/             um leitor por arquivo + comum.py (conversões)
│   ├── checkout.py           linha CHECKOUT (Orbe)
│   ├── remessa.py            linha REMESSA (Ponte Câmbio)
│   ├── bancos.py             classificação dos extratos e conferências cruzadas
│   ├── ia.py                 sugestão de conta para lançamento sem regra
│   └── saida.py              ItemSaida, escrita e validação dos 6 CSVs
├── tests/                    303 testes + gerar_outubro.py (outubro simulado)
├── dados/2026-09/            data pack de setembro, como recebido
├── cache/ia_sugestoes.json   respostas da IA já obtidas (vazio em setembro)
└── saida/                    os 6 CSVs de setembro
```
