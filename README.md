# Fechamento mensal — Tarvo Pagamentos

Solução do hackathon para o fechamento mensal da Tarvo Pagamentos (subadquirente).

## Instalação

Python 3.11+.

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows (no Linux/macOS: source .venv/bin/activate)
pip install -e ".[dev]"       # ou: pip install -r requirements.txt
```

## Uso

```bash
python -m tarvo fechar --competencia 2026-09 --entrada dados/2026-09 --saida saida/
```

O comando lê as entradas, roda checkout, remessa e extratos, grava os 6 CSVs em `--saida` e falha se a
validação da saída (formato e fechamento com o `rastro.csv`) achar problema.

## Como rodar outubro

1. Ponha os 6 arquivos de outubro, como chegaram (sem editar), em `dados/2026-10/`. O nome pode mudar:
   cada um é achado pelo padrão de `config/entradas.yaml` (tabela abaixo), e precisa haver exatamente um por padrão.
2. Rode:
   ```bash
   python -m tarvo fechar --competencia 2026-10 --entrada dados/2026-10 --saida saida/
   ```
   Isso substitui os CSVs de setembro em `saida/` (eles ficam no git); para manter os dois meses, use outra pasta.
3. Confira `pendencias.csv`, onde fica tudo o que o código não decide sozinho:
   - `LANCAMENTO_SEM_REGRA`: lançamento de extrato que nenhuma regra cobre (fornecedor novo, pagador fora da
     lista). Fica `A_CLASSIFICAR` / `HUMANO` em `lancamentos_classificados.csv`. Se for lojista, cadastre o texto
     exato em `config/favorecidos.yaml` ou `config/pagadores_meridiano.yaml` (P07, P08) e rode de novo.
   - `REVISAR_SUGESTAO_IA`: o mesmo caso, com uma conta sugerida pela IA (`metodo` IA, ver a seção "IA"). A
     sugestão só vale depois que alguém do Financeiro revisar.
   - `LOJISTA_SEM_CONTRATO`: EC da Orbe fora da planilha; não fatura (R08). `LOJISTA_NAO_CADASTRADO`: CNPJ da
     Ponte fora da planilha; a comissão entra na nota (P04), falta cadastrar.
   - `DIVERGENCIA_TED_LIQUIDACAO`, `DIFERENCA_PIX_REMESSA`, `RECURSO_SEM_REMESSA`: conferências Ponte × Meridiano.
   - O que vem de setembro não é conferido automaticamente: a TED de mesma titularidade do início de outubro no
     Meridiano é a transferência que estava em trânsito, e o TED de repasse da Ponte deve ser conferido contra a
     nota de remessa de setembro (R18). Baixe essas pendências de setembro à mão.

Ensaio sem os arquivos reais: `pytest tests/test_outubro.py` gera um outubro simulado a partir de setembro
(`tests/gerar_outubro.py`, com quatro casos novos) e roda o fechamento sobre ele.

## IA

A IA é plano B só na classificação dos extratos (premissa P14 do `HIPOTESES.md`). Ela sugere a conta de um
lançamento que nenhuma regra cobre e nunca decide regra de negócio. A sugestão sai com `metodo` IA e sempre
gera a pendência `PEN-IA-<ref>` (`REVISAR_SUGESTAO_IA`) para o Financeiro revisar. Abaixo do limiar de
confiança, o motivo diz "baixa confiança".

- **Chave:** defina `ANTHROPIC_API_KEY` no ambiente com a sua chave da API da Anthropic. Ela não fica no
  repositório.
  ```powershell
  $env:ANTHROPIC_API_KEY = "<sua chave>"   # PowerShell; no bash: export ANTHROPIC_API_KEY=...
  ```
- **Configuração:** `config/ia.yaml` (modelo `claude-sonnet-5-5`, limiar 0,80, `max_tokens`, esforço, caminho
  do cache).
- **Como desligar:** `--sem-ia` no comando (`python -m tarvo fechar ... --sem-ia`) ou `habilitada: false` no
  `config/ia.yaml`. Sem chave, a IA também não é chamada. Nos três casos, o lançamento sem regra fica
  `A_CLASSIFICAR` / `HUMANO`, com a pendência `PEN-SEMREGRA-<ref>` (P09).
- **Cache:** as respostas ficam em `cache/ia_sugestoes.json`, por hash do lançamento + modelo, e vão para o
  git. Assim a mesma entrada dá a mesma saída, e quem rodar sem chave reproduz as sugestões já obtidas.
- **Custo esperado:** uma chamada por lançamento sem regra que não esteja no cache.
  - Setembro: zero chamadas, porque todo lançamento casa uma regra.
  - Outubro simulado (`tests/gerar_outubro.py`): duas chamadas ("PIX ENVIADO GRAFICA RAPIDA LTDA" e o PIX
    do pagador fora da lista).
  - Cada chamada envia em torno de 2 mil tokens: o plano de contas analítico, R19 e os exemplos. A estimativa
    é de menos de US$ 0,01 por chamada nos preços do Sonnet 5.5, mas ainda não foi medida.
- **Testes:** `tests/test_ia.py` usa um cliente falso. Nenhum teste chama a rede.

## Entradas

Os arquivos em `dados/<competencia>/` **nunca são editados à mão**: são lidos como vêm.
São localizados por padrão de nome (definidos em `config/entradas.yaml`), nunca pelo nome exato:

| tipo | padrão | observações |
|------|--------|-------------|
| orbe | `*orbe*.csv` | separador `;`, vírgula decimal |
| taxas | `*taxas*.xlsx` | cabeçalho na linha 5; taxa em fração ou texto ("2,59%"); CNPJ formatado ou numérico sem zero à esquerda |
| ponte_eml | `*.eml` | e-mail da Ponte Câmbio com XLSX anexo em base64 |
| plano_de_contas | `*plano_de_contas*.csv` | Windows-1252 |
| aurora | `*aurora*.csv` | 6 linhas de cabeçalho e rodapé |
| meridiano | `*.ofx` | SGML; cp1252 válido, coerente com o cabeçalho `CHARSET:1252` (não é UTF-8 corrompido) |

## Estrutura

- `config/` — regras de negócio e mapeamentos (YAML)
- `src/tarvo/` — código; `leitores/` tem um leitor por arquivo de entrada
- `tests/` — testes (`pytest`)
- `saida/` — arquivos gerados
- `HIPOTESES.md` — premissas, perguntas ao financeiro e decisões de formato
- `CLAUDE.md` — regras para quem (humano ou IA) mexer no código
- `PROMPTS/MOMENTOS.md` — registro de prompts

## Testes

```bash
pytest
```
