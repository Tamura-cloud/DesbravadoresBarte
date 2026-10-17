# Momentos que importaram

## 1. Os dossiês de pesquisa iam contaminar o case (decisão do time)

Pedimos ao Antigravity uma avaliação do Graphify e dos dossiês sobre a Barte, e a IA respondeu que o Graphify não compensava e que os dossiês traziam a receita do case Buser (casar cliente por nome aproximado), que aqui misturaria os dois "Horizonte". Recusamos o Graphify, tiramos os dossiês do contexto da IA e travamos a regra de casar só por EC e CNPJ (commit `7d06117`).

*Fonte: `sessoes/2026-10-16_pessoa-3_antigravity_40ab3010`, 16/10 21:32–21:44.*

## 2. A regra escrita pela IA confundia a Ponte Aérea com a Ponte Câmbio (a IA errou)

Quando a Helena disse que a Ponte Aérea Estudantil é lojista e não tem nada a ver com a Ponte Câmbio, pedimos ao Claude Code que conferisse se alguma regra confundia as duas, e ele confirmou que o padrão do repasse da Ponte, escrito por ele na véspera, procurava só "PONTE" e pegaria a Ponte Aérea. Restringimos o padrão a "PONTE CAMBIO" e deixamos um teste que impede a volta do erro (commit `db29cf0`).

*Fonte: `sessoes/2026-10-17_pessoa-2_claude_7c85056d` (horário do computador da Pessoa 2: 17/10 07:08–07:44).*

## 3. O documento que a IA ajudou a escrever tinha 8 erros (a IA errou)

Pedimos ao Claude Code que conferisse o `CLAUDE.md` contra os dados, e o recálculo achou 8 erros herdados da preparação, como um aumento de taxa da Rota no débito que não existe e 5 arquivos de saída em vez dos 6 oficiais. Corrigimos (commit `0beccf8`) e passamos a aceitar número só se ele vier do código e estiver num teste.

*Fonte: `sessoes/2026-10-16_pessoa-3_claude_be5d287e`, 16/10 23:16–23:21.*

## 4. O status escrito pela IA inventou uma segunda implementação (a IA errou)

Pedimos ao Claude Code que analisasse a branch `pix` sem fazer merge, e ele rodou a branch numa cópia isolada (314 testes, saída idêntica) e mostrou que o status dizia, sem base, que o `main` tinha "uma segunda implementação completa". Escolhemos entregar o código da `pix`, corrigimos a frase do pitch para "recalculamos tudo por fora e bateu ao centavo" e dividimos o dia em 3 papéis paralelos.

*Fonte: `sessoes/2026-10-17_pessoa-3_claude_82f695ad`, 17/10 06:13–06:36.*

---

**Reserva:**
- Varredura de 100% das linhas antes de aceitar qualquer regra (encodings, CNPJs de 13 dígitos, Bridge, estorno de agosto), em `sessoes/2026-10-16_pessoa-3_antigravity_40ab3010`, 16/10 22:26, commit `d425cd4`.
- Revisão independente das saídas, que questionou 7 premissas (P15–P21) e manteve cada uma com o número alternativo, em `sessoes/*_pessoa-2_claude_e749f188` e `656c59d7`, commit `329831b`.
- A regra da Casa do Estudante que mudou no meio do dia ("o que decide é o contrato, não o aviso"), em `sessoes/*_pessoa-2_claude_56449fe8`, commit `2b679b3`.
- O arquivo novo da Orbe (13h10) testado numa cópia isolada antes de entrar no `main`: o fechamento parava e as notas corretas foram simuladas antes da correção, em `sessoes/*_pessoa-1_claude_6a4fd205`, 17/10 13h22–13h30.
- A cronologia em UTC que sugeria código descartado, corrigida conferindo a autoria no horário de Brasília, em `sessoes/*_pessoa-1_claude_6a4fd205`, 17/10 00h45 e 08h10.
