# Momentos que importaram

## 1. Os dossiês de pesquisa iam contaminar o case (decisão do time)

Pedimos ao Antigravity uma avaliação do Graphify e dos dossiês sobre a Barte, e a IA respondeu que o Graphify não compensava e que os dossiês traziam a receita do case Buser (casar cliente por nome aproximado), que aqui misturaria os dois "Horizonte". Recusamos o Graphify, tiramos os dossiês do contexto da IA e travamos a regra de casar só por EC e CNPJ (commit `7d06117`).

*Fonte: `sessoes/2026-10-16_pessoa-3_antigravity_40ab3010`, 16/10 21:32–21:44.*

## 2. Trocamos teoria por varredura dos dados (decisão do time)

Pedimos que nenhuma regra entrasse sem conferência linha a linha, e a varredura em Python achou dois arquivos em cp1252, CNPJs com 13 dígitos, 5 vendas da Bridge na taxa antiga e o estorno de agosto que deixa a Casa do Estudante negativa. Essas descobertas viraram regras e, depois, testes (commit `d425cd4`).

*Fonte: `sessoes/2026-10-16_pessoa-3_antigravity_40ab3010`, 16/10 22:26.*

## 3. O documento que a IA ajudou a escrever tinha 8 erros (a IA errou)

Pedimos ao Claude Code que conferisse o `CLAUDE.md` contra os dados, e o recálculo achou 8 erros herdados da preparação, como um aumento de taxa da Rota no débito que não existe e 5 arquivos de saída em vez dos 6 oficiais. Corrigimos (commit `0beccf8`) e passamos a aceitar número só se ele vier do código e estiver num teste.

*Fonte: `sessoes/2026-10-16_pessoa-3_claude_be5d287e`, 16/10 23:16–23:21.*

## 4. O status escrito pela IA inventou uma segunda implementação (a IA errou)

Pedimos ao Claude Code que analisasse a branch `pix` sem fazer merge, e ele rodou a branch numa cópia isolada (314 testes, saída idêntica) e mostrou que o status dizia, sem base, que o `main` tinha "uma segunda implementação completa". Escolhemos entregar o código da `pix`, corrigimos a frase do pitch para "recalculamos tudo por fora e bateu ao centavo" e dividimos o dia em 3 papéis paralelos.

*Fonte: `sessoes/2026-10-17_pessoa-3_claude_82f695ad`, 17/10 06:13–06:36.*

---

**Reserva:** a duplicata `PC-0926-0162` provada pelo extrato do Meridiano e a revisão adversarial das premissas P15–P21, quando os transcripts das sessões da `pix` estiverem em `sessoes/`.
