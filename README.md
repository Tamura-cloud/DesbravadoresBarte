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

Por enquanto o comando só localiza e lista os arquivos de entrada.

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
| meridiano | `*.ofx` | SGML; declara CHARSET 1252, mas os bytes são UTF-8 com caracteres já corrompidos |

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
