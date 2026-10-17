# Momentos que importaram

Quatro momentos, em ordem. Dois são erros da IA que pegamos, dois são decisões nossas que mudaram o rumo. Cada um aponta para o transcript onde dá para conferir.

---

## 1. Os dossiês de pesquisa iam contaminar o case: isolamos (decisão do time)

- **Pedimos:** no Antigravity (16/10, 21h32–21h44), uma avaliação do Graphify e se os 5 dossiês de pesquisa sobre a Barte atrapalhariam a construção.
- **A IA devolveu:** que o Graphify não compensa num projeto deste tamanho, e que os dossiês traziam a receita do case Buser (casar cliente por nome aproximado), que aplicada aqui misturaria os dois "Horizonte" e erraria 233 transações.
- **Fizemos:** recusamos o Graphify, guardamos os dossiês numa branch de backup, tiramos do contexto da IA e travamos a regra "casar só por EC e CNPJ" (commit `7d06117`).
- **Fonte:** `sessoes/2026-10-16_pessoa-3_antigravity_40ab3010`, 16/10 21:32–21:44.

## 2. "Faça se tiver 100% de certeza": trocamos teoria por varredura dos dados (decisão do time)

- **Pedimos:** que nenhuma regra entrasse no `CLAUDE.md` sem conferência linha a linha nos arquivos reais.
- **A IA devolveu:** a varredura em Python achou o que ninguém tinha visto: dois arquivos em cp1252, CNPJs com 13 dígitos na planilha, 5 vendas da Bridge na taxa antiga e o estorno de agosto que deixa a Casa do Estudante com comissão negativa.
- **Fizemos:** essas descobertas viraram regras e, depois, testes (commit `d425cd4`).
- **Fonte:** `sessoes/2026-10-16_pessoa-3_antigravity_40ab3010`, 16/10 22:26.

## 3. O documento que a IA ajudou a escrever tinha 8 erros (a IA errou)

- **Pedimos:** no Claude Code (16/10, 23h16), que conferisse o `CLAUDE.md` contra os dados, o Slack e as instruções oficiais.
- **A IA devolveu:** recalculou tudo e achou 8 erros herdados da preparação: aumento de taxa da Rota no débito que não existe, duplicata atribuída à loja errada, 85 lançamentos em vez de 84, R$ 0,10 a menos na Casa do Estudante e 5 arquivos de saída em vez dos 6 oficiais.
- **Fizemos:** corrigimos (commit `0beccf8`) e mudamos o método: número só vale se vier do código, e os valores conferidos viraram testes.
- **Fonte:** `sessoes/2026-10-16_pessoa-3_claude_be5d287e`, 16/10 23:16–23:21.

## 4. O status da IA dizia que existiam duas implementações; não existiam (a IA errou)

- **Pedimos:** na manhã de 17/10, que o Claude Code analisasse a branch `pix` e o status escrito pela IA do colega, sem fazer merge.
- **A IA devolveu:** rodou a `pix` numa cópia isolada (314 testes, saída idêntica byte a byte) e mostrou que o status estava errado: dizia que o `main` tinha "uma segunda implementação completa", mas o `main` só tinha o esqueleto.
- **Fizemos:** escolhemos entregar o código da `pix`, mudamos a frase do pitch para "recalculamos tudo por fora e bateu ao centavo" e dividimos o dia em 3 papéis paralelos.
- **Fonte:** `sessoes/2026-10-17_pessoa-3_claude_82f695ad`, 17/10 06:13–06:36.

---

**Reserva:** a duplicata `PC-0926-0162` provada pelo extrato do Meridiano e a revisão adversarial que questionou 7 premissas (P15–P21) aconteceram nas sessões do autor da `pix`. Entram no lugar de um dos momentos acima quando esses transcripts estiverem em `sessoes/`.
