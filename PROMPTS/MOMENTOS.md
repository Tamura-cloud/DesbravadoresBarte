# MOMENTOS.md — Registro de Interações Decisivas com a IA (15% da Avaliação)

> **Instrução do Edital:** Marque de 2 a 4 momentos que importaram durante a preparação e construção. Para cada um, descreva em uma ou duas frases: **o que você pediu**, **o que a IA devolveu** e **o que você fez com isso**. **Obrigatório incluir pelo menos um momento em que a IA errou ou tentou te levar para o lugar errado e você corrigiu.**

---

## Momento 1 — Correção Crítica: A Armadilha do "Fuzzy Matching" de Nomes nos Dois "Horizonte" (Erro da IA Corrigido pelo Time)

* **O que pedimos:** Durante a preparação inicial e análise dos casos anteriores da Barte (como o case público da Buser), pedimos à IA para propor uma estratégia de conciliação e amarração cadastral entre o relatório da adquirente (`01_orbe_relatorio_comissoes_set2026.csv`) e a planilha comercial (`02_tabela_taxas_contratadas.xlsx`).
* **O que a IA devolveu (Onde a IA errou / induziu ao erro):** Inicialmente, a IA sugeriu aplicar *fuzzy matching* (similaridade textual de nomes) e usar arquiteturas complexas de modelos de decisão/fine-tuning para casar os nomes dos estabelecimentos quando o código EC estivesse vazio na planilha.
* **O que nós fizemos com isso (Nossa intervenção):** Ao inspecionarmos os dados reais da Tarvo, percebemos que o *fuzzy matching* por nome causaria um erro grave: o EC `1043300981` chama-se `"HORIZONTE INTERCAMBIO"` na Orbe, mas aplica as taxas de `2,39%` e `2,89%`, que pertencem contratualmente à **Novo Horizonte Intercâmbio** (`CNPJ 66.564.512/0001-99`), e não à **Horizonte Viagens e Turismo** (`CNPJ 78.576.234/0001-79`, que usa `1043396662`). Rejeitamos o casamento aproximado por nome, bloqueamos o contexto prévio para não enviesar o Claude Code e travamos a regra determinística por `cod_estabelecimento` + evidência de taxa contratada.

---

## Momento 2 — Cruzamento Entre Fontes para Provar a Duplicata da Ponte Câmbio (`PC-0926-0162`)

* **O que pedimos:** Pedimos à IA para auditar a consistência entre o anexo do e-mail da Ponte Câmbio (`PonteCambio_Relatorio_TARVO_092026.xlsx`) e o extrato OFX do Banco Meridiano (`05b_extrato_banco_meridiano_cc90233_set2026.ofx`).
* **O que a IA devolveu:** A análise identificou que a operação `PC-0926-0162` (Bagagem Livre) aparecia duas vezes na planilha da Ponte (a segunda como `"reprocessada"`), e provou matematicamente que a soma diária de `Valor R$ + IOF R$` das 232 operações únicas (`R$ 5.611.447,12`) bate ao centavo com as 21 TEDs `"LIQ OPERACOES"` do extrato do Banco Meridiano — enquanto incluir a duplicata quebrava a conciliação bancária.
* **O que nós fizemos com isso:** Transformamos essa prova cruzada (Relatório de Câmbio × Extrato Bancário) em uma regra de deduplicação auditável que descarta a cópia do cálculo de comissão/NF e a envia automaticamente para `saida/pendencias.csv` com a evidência do extrato bancário.

---

## Momento 3 — Recalcular em vez de confiar: o CLAUDE.md gerado com IA tinha 8 erros (Erro da IA Corrigido pelo Time)

* **O que pedimos:** Na noite de 16/10, pedimos que a IA lesse um por um os documentos que ela mesma tinha ajudado a escrever (`CLAUDE.md`, `HIPOTESES.md`), o Slack com as respostas da Helena e as instruções oficiais, e dissesse se havia erro de relação com os dados.
* **O que a IA devolveu:** Além de reler os textos, recalculou tudo em Python sobre `dados/` e achou 8 erros que vinham de números copiados sem recálculo: um aumento de taxa da Rota Global no débito que não existe (herdado de uma pergunta mal rotulada no Slack), a duplicata `PC-0926-0162` atribuída à EduAbroad (é da Bagagem Livre), 3 em vez de 6 operações de 30/09, 85 em vez de 84 lançamentos no Aurora, R$ 0,10 a menos na Casa do Estudante. Mostrou também que os schemas de saída não seguiam a instrução oficial (faltavam `id_saida`, `ref_origem` e o `rastro.csv`).
* **O que nós fizemos com isso:** Corrigimos os documentos (commit `0beccf8`) e mudamos o método: o número passa a nascer do pipeline, e os valores conferidos viraram testes de aceite em `tests/`, para que nenhum documento volte a ser a fonte da verdade.

---

## Momento 4 — `[Reservado para registrar durante a implementação do código / classificação bancária]`

* **O que pedimos:** `[Preencher durante o desenvolvimento]`
* **O que a IA devolveu:** `[Preencher durante o desenvolvimento]`
* **O que nós fizemos com isso:** `[Preencher durante o desenvolvimento]`
