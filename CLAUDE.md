# CLAUDE.md — Diretrizes do Projeto (Desafio Barte AI: Case Tarvo)

> **Instrução ao Claude Code:** Este arquivo é a sua fonte primária de contexto. Estamos construindo a solução de fechamento mensal da **Tarvo Pagamentos** (competência `2026-09`, parametrizada para rodar em `2026-10` sem retrabalho). Seja conciso, priorize exatidão matemática e **nunca invente regras de negócio sem registrá-las em `HIPOTESES.md`**.

---

## 1. Contexto do Negócio (Tarvo Pagamentos)

Subadquirente de nicho para educação internacional (~25 lojistas ativos) com **duas linhas de negócio**:
1. **`CHECKOUT`:** Alunos pagam os lojistas por cartão e Pix via adquirente **Orbe**. A Tarvo ganha a taxa (**MDR**) e a **taxa de antecipação**.
2. **`REMESSA`:** Lojistas pagam escolas no exterior via parceiro **Ponte Câmbio**. A Tarvo ganha participação no spread cambial (**50% do spread realizado**, conforme e-mail de set/2026).

---

## 2. Regra Central Inegociável (Eliminatória — 25% da Nota)

* **Todo número em qualquer arquivo de `saida/` DEVE apontar para a(s) linha(s) de origem em `saida/rastro.csv`.**
* Para cada `id_saida`, a soma de `valor` em `rastro.csv` tem que bater **ao centavo** com o valor reportado no arquivo de saída correspondente.
* **Comissão sem rastro até as transações que a compõem não conta.** Total que não fecha com a soma das linhas de origem conta como **número inventado**.
* **Alarmes falsos contam contra:** Não reporte divergência onde a diferença é mero arredondamento ou quando o lojista não possui contrato cadastrado (nesse caso, gere pendência).
* **Proibido editar manualmente os arquivos de `dados/`:** O pipeline deve consumir os 6 arquivos exatamente como vêm.

---

## 3. Estrutura Obrigatória na Raiz do Repositório

```text
.
├── CLAUDE.md                  # Diretrizes técnicas e de negócio para o Claude Code
├── README.md                  # Como instalar e rodar do zero, variáveis de ambiente e limitações
├── HIPOTESES.md               # Premissas assumidas + Perguntas/respostas do #tarvo-financeiro
├── PROMPTS/
│   ├── MOMENTOS.md            # 2 a 4 momentos decisivos com a IA (incluindo >=1 erro da IA corrigido)
│   └── ...                    # Transcripts / exports das sessões de IA
├── dados/                     # Os 6 arquivos brutos do data pack (somente leitura)
├── saida/                     # Os 6 CSVs gerados pelo pipeline
├── src/                       # Código-fonte do pipeline
└── tests/                     # Testes automatizados de validação (rastro, somas, formatos)
```

---

## 4. Os 6 Arquivos de Entrada (`dados/`) e Armadilhas de Parsing

| Arquivo em `dados/` | `ref_origem` exigido | Armadilhas que o Parser DEVE tratar via código |
| :--- | :--- | :--- |
| `01_orbe_relatorio_comissoes_set2026.csv` | `id_transacao` (ex: `TX88410932`) | Separador `;`, vírgula decimal. Contém vendas, estornos, antecipações e reversões. Mesmo `cod_estabelecimento` (EC) tem até 3 grafias de nome. Há dois "Horizonte" (`HORIZONTE INTERCAMBIO` e `HORIZONTE VIAGENS TURISMO`). **Proibido fazer fuzzy match por nome; usar sempre `cod_estabelecimento`.** |
| `02_tabela_taxas_contratadas.xlsx` | Linha da planilha | Ignorar a aba `"ANTIGO 2025 - nao usar"` como contrato vigente. Na aba `"Taxas vigentes"`, o cabeçalho está na linha 5; taxas misturam decimal (`0.0259`) e texto (`"2,59%"`); CNPJs sem zero à esquerda (usar `zfill(14)`); 4 lojistas sem código EC; *Escola Bridge* com 2 linhas de vigência em set/2026; *Atlas Idiomas* opera na Orbe mas não está na aba vigente. |
| `03_email_ponte_cambio_relatorio_set2026.eml` | `Nº Operação` (ex: `PC-0926-0002`) | Extrair anexo `.xlsx` via `email` stdlib. Na aba `"Operações"`, cabeçalho na linha 5 e linhas de total no rodapé. Contém operação duplicada/reprocessada (`PC-0926-0162`), 4 operações com spread negativo (`Taxa travada no pedido (D-1)`), 16 `"APROVADO C/ RESSALVA"` e 6 contratadas em `30/09` com liquidação em `01/10`. |
| `04_plano_de_contas_fenix_erp.csv` | `COD_CONTA` | Encoding `cp1252` (`latin1`), separador `;`. Apenas contas analíticas (`ACEITA_LANCTO=S`) podem receber lançamentos em `lancamentos_classificados.csv`. |
| `05a_extrato_banco_aurora_cc4471_set2026.csv` | Número da linha física do arquivo (`L10`, `L11`...) | Encoding `cp1252`, separador `;`. Possui cabeçalho institucional no topo e linhas de `"SALDO ANTERIOR"` / `"SALDO DO DIA"` / rodapé que **não** são lançamentos. Valores usam ponto de milhar e vírgula decimal. |
| `05b_extrato_banco_meridiano_cc90233_set2026.ofx` | `FITID` | SGML sem tags de fechamento; declara `CHARSET:1252`, mas contém bytes UTF-8/corrompidos; `MEMO` truncado em 34 caracteres. As 21 TEDs `"LIQ OPERACOES"` somam `R$ 5.611.447,12` e provam que a duplicata `PC-0926-0162` da Ponte não foi paga duas vezes. |

---

## 5. Especificação Estrita dos 6 CSVs de Saída (`saida/`)

* **Regras globais de formatação:** Separador `;` | Separador decimal `.` (2 casas: `1234.56`, ou 4 casas em percentuais se aplicável) | Datas `AAAA-MM-DD` | CNPJ com 14 dígitos numéricos sem pontuação (`00000000000100`).
* **Enums obrigatórios:**
  * `linha_negocio`: `CHECKOUT` ou `REMESSA`
  * `banco`: `AURORA` ou `MERIDIANO`
  * `metodo`: `REGRA`, `IA` ou `HUMANO`
  * `confianca`: float entre `0` e `1` (ex: `1.00`)

| Arquivo em `saida/` | Colunas Obrigatórias (ordem exata) |
| :--- | :--- |
| `comissoes_por_lojista.csv` | `id_saida;cnpj;lojista;linha_negocio;comissao_brl` |
| `divergencias_taxa.csv` | `id_saida;cnpj;linha_negocio;ref_origem;taxa_contratada_pct;taxa_aplicada_pct;diferenca_brl` |
| `notas_a_emitir.csv` | `id_saida;tomador_cnpj;tomador;linha_negocio;valor_brl;discriminacao` |
| `lancamentos_classificados.csv` | `id_saida;banco;ref_origem;data;descricao;valor;conta_codigo;metodo;confianca` |
| `pendencias.csv` | `id_saida;tipo;ref_origem;valor_brl;motivo;quem_decide` |
| `rastro.csv` | `id_saida;arquivo_origem;ref_origem;valor` |

---

## 6. Diretrizes de Desenvolvimento e Ordem de Prioridade

1. **Níveis de Entrega:**
   * **Nível Mínimo (Prioridade #1 — até Checkpoint 11h00):** `comissoes_por_lojista.csv` (CHECKOUT) + `rastro.csv` batendo 100%.
   * **Nível Alvo (Prioridade #2 — até Checkpoint 15h30):** Comissões das 2 linhas (`CHECKOUT` e `REMESSA`), `divergencias_taxa.csv`, `notas_a_emitir.csv` e `lancamentos_classificados.csv`.
   * **Nível Extra (Prioridade #3 — até 17h30):** `pendencias.csv` completo e explicado, rastro 100% auditado em todos os arquivos e execução limpa para novos arquivos de outubro/2026.
2. **Onde usar Regra vs. IA vs. Humano:**
   * **`REGRA` (`confianca=1.0`):** Cálculos de comissão, cruzamento de taxas contratadas, conciliação exata por chave/valor e históricos bancários recorrentes conhecidos.
   * **`IA` (`confianca` calibrada):** Classificação contábil de descrições bancárias novas/ambíguas ou auxílio estruturado onde não há regra fixa. Abaixo do limiar de segurança, escalar para `pendencias.csv`.
   * **`HUMANO`:** Qualquer exceção de negócio sem regra confirmada (ex: lojista Atlas sem contrato vigente, spreads negativos, duplicatas, PIX sem identificação ou sem remessa correspondente).
