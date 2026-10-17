# Tarvo Pagamentos — Fechamento Mensal Auditável (Desafio Barte AI)

Solução automatizada e auditável para o fechamento mensal da **Tarvo Pagamentos** (competência **setembro/2026**, preparada para execução contínua em **outubro/2026**), desenvolvida pelo time **Desbravadores Barte**.

---

## 1. Visão Geral da Arquitetura

O pipeline consome os **6 arquivos brutos originais** exportados pelos sistemas da Tarvo (Portal Orbe, Planilha Comercial de Taxas, E-mail Ponte Câmbio, ERP Fênix, Banco Aurora e Banco Meridiano) **sem necessidade de limpeza manual prévia** e gera os **6 arquivos padronizados em `saida/`** com rastreabilidade linha a linha (`rastro.csv`).

### Princípios de Projeto
1. **Rastreabilidade Nativa (`rastro.csv`):** Cada número de saída nasce a partir da lista de transações de origem que o compõem. Nenhuma soma existe sem verificação automática (`soma(rastro) == valor_reportado`).
2. **Determinismo + IA Cirúrgica + Governança Humana:**
   * **`REGRA`:** Cálculos matemáticos, cruzamento de taxas por código de estabelecimento (`EC`) / `CNPJ` e conciliações exatas rodam de forma 100% determinística.
   * **`IA`:** Acionada com *structured outputs* apenas para lançamentos e descrições sem regra determinística prévia, registrando score de `confianca`.
   * **`HUMANO` (`pendencias.csv`):** Casos sem cobertura contratual, spreads negativos, operações duplicadas e créditos não identificados são isolados com o motivo exato e o responsável pela decisão (`quem_decide`).
3. **Pronto para Outubro/2026:** Parametrização completa de competência e regras de negócio desacopladas do código.

---

## 2. Estrutura do Repositório

```text
.
├── README.md                  # Instruções de instalação, execução e limitações conhecidas
├── HIPOTESES.md               # Premissas assumidas e registro de perguntas/respostas (#tarvo-financeiro)
├── CLAUDE.md                  # Diretrizes técnicas e de arquitetura para o Claude Code
├── PROMPTS/
│   ├── MOMENTOS.md            # Registro dos momentos decisivos no uso de IA (acertos e correções)
│   └── ...                    # Histórico completo das sessões de IA
├── dados/                     # Arquivos brutos do Tarvo_Data_Pack_set2026 (intactos)
├── saida/                     # Os 6 arquivos CSV gerados pelo fechamento
├── src/                       # Código-fonte modular do pipeline
└── tests/                     # Testes automatizados de integridade contábil e de rastro
```

---

## 3. Como Instalar e Rodar do Zero

### Pré-requisitos
* **Python 3.11+**
* Dependências listadas em `requirements.txt` (ou via `uv`):

```powershell
python -m pip install pandas openpyxl pypdf pydantic anthropic python-dotenv pytest
```

### Configuração de Variáveis de Ambiente (Opcional para etapa de IA)
Caso utilize a classificação assistida por IA em lançamentos inéditos, configure sua chave de API:

```powershell
# No PowerShell
$env:ANTHROPIC_API_KEY="sua_chave_aqui"
```
*(O pipeline possui fallback determinístico e registro em `pendencias.csv` caso nenhuma chave de API seja fornecida).*

### Executando o Fechamento de Setembro/2026
*(Comando será habilitado assim que o módulo principal em `src/` for gerado)*:

```powershell
python -m src.cli --entrada ./dados --saida ./saida --competencia 2026-09
```

### Executando a Suíte de Testes e Auditoria de Rastro
```powershell
pytest tests/
```

---

## 4. Limitações Conhecidas

* As decisões contábeis dependentes de confirmação humana ou aditivo comercial (documentadas em [`HIPOTESES.md`](./HIPOTESES.md)) seguem as premissas explícitas configuradas e são listadas em `saida/pendencias.csv` para deliberação do time financeiro/comercial da Tarvo.
