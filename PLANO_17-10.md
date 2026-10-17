# Plano de trabalho — 17/10 (3 pessoas)

Objetivo do dia: os 6 CSVs de `saida/` certos e com rastro, um README que roda do zero e o pitch.
**Mínimo antes de tudo:** se às 11h o checkout não fecha, ninguém mexe em outra frente.

---

## 1. Arquitetura: monólito modular

A ideia da figura de referência que vale para nós é separar **um orquestrador fino**, **módulos de negócio independentes** e **uma camada de dados compartilhada**. O resto da figura (filas, workers, busca, front-end) não faz sentido em um pipeline de lote de um dia.

```text
                 python -m src.main  (orquestrador — Pessoa C)
                          │  mesmos Dados para todos
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
  src/checkout/      src/remessa/       src/bancos/          ← um módulo por pessoa
   (Pessoa A)         (Pessoa B)         (Pessoa C)             não importam um ao outro
        │                 │                 │
        └──── ResultadoModulo (src/core/modelos.py) ────┘     ← contrato único
                          │
              src/core/saida.py → 6 CSVs + rastro.csv        ← valida o rastro ao centavo
                          ▲
        src/leitores/ (6 fontes, prontos e testados)           ← camada de dados compartilhada
        config/*.toml (regras que mudam de mês para mês)
```

**Por que isso evita atrapalhar o outro:**
1. Cada pessoa edita só a própria pasta, o próprio `config/<módulo>.toml` e o próprio `tests/test_<módulo>.py`.
2. Os módulos só conversam pelo contrato (`ResultadoModulo` com `Comissao`, `Divergencia`, `Nota`, `Lancamento`, `Pendencia`, cada um com seu `rastro`). Ninguém escreve CSV direto.
3. Os leitores já entregam as fontes limpas e testadas: ninguém reescreve parser.
4. `main.py` pula módulo não implementado: cada pessoa roda o pipeline inteiro sem esperar as outras.

| Camada | Arquivos | Dono | Pode mudar? |
|---|---|---|---|
| Leitores | `src/leitores/*` | C | só com aviso no grupo (afeta todos) |
| Contrato e saída | `src/core/*` | C | só com aviso no grupo (afeta todos) |
| Checkout | `src/checkout/`, `config/checkout.toml`, `tests/test_checkout.py` | **A** | livre |
| Remessa | `src/remessa/`, `config/remessa.toml`, `tests/test_remessa.py` | **B** | livre |
| Bancos | `src/bancos/`, `config/bancos.toml`, `tests/test_bancos.py` | **C** | livre |
| Orquestrador | `src/main.py`, `tests/test_pipeline.py` | C | livre |
| Documentos | `README.md`, `HIPOTESES.md`, `PROMPTS/`, pitch | C (A e B mandam o conteúdo) | livre |

---

## 2. Git sem conflito

- Uma branch por pessoa: `feat/checkout`, `feat/remessa`, `feat/bancos`.
- Commit pequeno e merge em `main` a cada entrega que passa no teste, no mínimo nos checkpoints (11h e 15h30).
- Antes do merge: `git pull origin main` e `python -m unittest discover -s tests` verde.
- Precisa mudar `src/core` ou `src/leitores`? Avise no grupo, faça um commit só com isso e mande para `main` primeiro.
- Cada sessão do Claude Code começa com: *"Sou a Pessoa X, só edite os arquivos do meu módulo (ver PLANO_17-10.md)."*

---

## 3. Contrato em 30 segundos

```python
from src.core.modelos import Comissao, Divergencia, Nota, Pendencia, ItemRastro, ResultadoModulo
from src.core.dinheiro import arred

def executar(dados, cfg, competencia) -> ResultadoModulo:
    r = ResultadoModulo()
    # cada número leva a lista das linhas de origem que o compõem:
    itens = [ItemRastro(dados.arquivos["orbe"], t.ref_origem, arred(t.valor_bruto * taxa / 100)) for t in ...]
    r.comissoes.append(Comissao(cnpj, lojista, "CHECKOUT", sum(i.valor for i in itens), rastro=itens))
    return r
```

- `core/saida.py` numera `id_saida`, formata (ponto decimal, 2 casas, datas ISO, CNPJ com 14 dígitos) e **quebra se o rastro não somar o número**.
- Valores sempre `Decimal`, arredondados com `arred()` linha a linha, antes de somar.

---

## 4. Tarefas por pessoa

Os valores de aceite já estão nos testes. **Pronto = o teste do módulo passa.**

### Pessoa A — Checkout (`src/checkout/motor.py`)
- [ ] Mapa EC → linha da planilha (EC da planilha + `ec_sem_codigo` do config)
- [ ] Taxa contratada por modalidade e faixa de parcelas, com vigência pela `data_referencia_taxa` (Bridge, estornos de agosto)
- [ ] Condição especial da Casa do Estudante (config) → taxa 0 de set a dez
- [ ] Comissão por linha `arred(bruto × taxa / 100)` → `Comissao` por lojista, com rastro
- [ ] Divergência só quando a taxa difere → `Divergencia` por transação (210 linhas)
- [ ] Atlas (`sem_contrato`) → só `Pendencia` para o Diego
- [ ] `Nota` por lojista com saldo > 0 (20 notas, R$ 207.045,23); saldo ≤ 0 → `Pendencia` para a Helena
- [ ] Pendências: devolução da Casa do Estudante (R$ 15.397,42), cobrança a mais da Rota e da Bridge para a Helena cobrar da Orbe

### Pessoa B — Remessa (`src/remessa/motor.py`)
- [ ] Deduplicar por Nº Operação; a cópia de `PC-0926-0162` vira `Pendencia` (Ponte corrigir relatório)
- [ ] Separar os 4 spreads negativos (trava D-1) → `Divergencia` + `Pendencia` de contestação
- [ ] Comissão `arred(spread × 0,50)` por operação → `Comissao` por CNPJ (228 operações)
- [ ] Spread contratado pelo CNPJ na planilha (branco/`padrão` = 1,50) e tolerância 0,01 p.p. → 23 divergências da Mundo Aberto (R$ 1.418,85)
- [ ] `Nota` única para a Ponte Câmbio (R$ 39.543,45)
- [ ] Pendências: contestação da Mundo Aberto, e conferir o TED de 06/10 quando cair (sem supor desconto)
- [ ] (extra) Conferir as 21 TEDs `LIQ OPERACOES` do Meridiano contra Valor R$ + IOF por dia

### Pessoa C — Bancos + integração (`src/bancos/motor.py` e o resto)
- [ ] Classificar os 184 lançamentos com `config/bancos.toml` (regras já escritas e conferidas)
- [ ] Pendências: L50, L65, L92 (sem par no Meridiano) e MRD2026090425 (PIX sem remessa)
- [ ] IA só para histórico sem regra (`metodo=IA`, `confianca`; abaixo de 0,8 → pendência). Hoje todas as 184 linhas têm regra: a IA fica como rede de segurança para outubro
- [ ] `HIPOTESES.md`: registro **pergunta → resposta da Helena → o que fizemos**, mais as premissas (seguro, tolerância de 0,01 p.p.)
- [ ] `PROMPTS/`: exportar os transcripts de todas as sessões (inclusive a de 16/10) e fechar `MOMENTOS.md`
- [ ] README testado num clone limpo; teste de "outubro" (copiar `dados/` com nomes e datas trocados e rodar)
- [ ] Pitch com os números que o pipeline gerar

---

## 5. Cronograma de 17/10

| Horário | Meta | Pronto quando |
|---|---|---|
| 8h–9h30 | credenciamento e painel | cada pessoa abriu a própria branch e rodou os testes |
| **9h30** | perguntas à Helena (abaixo) | resposta registrada no `HIPOTESES.md` |
| 9h30–11h | **Mínimo:** A entrega o checkout; B e C avançam nos módulos deles | `tests/test_checkout.py` verde e merge em `main` |
| **11h** | Checkpoint 1 no thread do time | texto postado (modelo abaixo) |
| 11h–15h30 | **Alvo:** remessa e bancos fechados; A ajuda quem estiver atrás | todos os testes verdes em `main` |
| **15h30** | Checkpoint 2 | texto postado |
| 15h30–17h30 | pendências completas, teste de outubro, README, HIPOTESES, MOMENTOS; C começa o pitch | clone limpo roda `python -m src.main` |
| **17h30** | **código congelado** | nada de funcionalidade nova |
| 17h30–18h15 | gerar `saida/`, revisar, push | push em `main` até **18h15** |
| 18h30–19h | pitch | link enviado até 19h |

### Perguntas para a Helena às 9h30 (curtas, com a premissa já escrita)
1. *Desbravadores Barte:* o `SEGURO EMPRESARIAL PARC 09/12` (R$ 1.830,44, Meridiano, 12/09) estava provisionado? Premissa: não, vai para despesa de seguros (4.2.05).
2. *Desbravadores Barte:* a Atlas deve aparecer na comissão do mês (calculada sem taxa contratada) ou só como pendência até o Diego confirmar? Premissa: só pendência, com o valor que a Orbe cobrou.

### Modelo do checkpoint 1 (11h)
> **Desbravadores Barte — Checkpoint 1.** Atacando: comissão de checkout com rastro (pronta), remessa e extratos em andamento. Hipóteses principais: taxa contratada linha a linha com arredondamento da Helena; Casa do Estudante zerada de set a dez; Atlas fora até o comercial confirmar; tolerância de 0,01 p.p. no spread. Fora do escopo: conciliar Orbe × banco parcela a parcela (confirmado pela Helena).

---

## 6. Checklist da entrega (17h30–18h15)

- [ ] `python -m unittest discover -s tests` verde
- [ ] `python -m src.main` gera os 6 CSVs em `saida/` e eles estão commitados
- [ ] README roda do zero num clone limpo (`pip install -r requirements.txt` + `python -m src.main`)
- [ ] `HIPOTESES.md` com perguntas, respostas e premissas
- [ ] `PROMPTS/` com os transcripts e `MOMENTOS.md` com 2 a 4 momentos (um em que a IA errou)
- [ ] Repositório público; link no thread `#hackathon-entregas`
