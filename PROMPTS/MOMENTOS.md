# Momentos que importaram

Quatro decisões do time, do começo ao fim. Em todas, a IA trabalhou e uma pessoa decidiu o que verificar, o que aceitar e quando parar.

## 1. Os dossiês de pesquisa iam contaminar o case (16/10, Erick)

Antes do data pack, pedimos ao Antigravity uma pesquisa sobre a Barte, e a IA avisou que os dossiês traziam a receita de outro case (casar cliente por nome aproximado), o que aqui misturaria os dois lojistas "Horizonte". Decidimos recusar a ferramenta de grafo, tirar os dossiês do contexto da IA e travar a regra de casar só por EC e CNPJ (commit `7d06117`).

*Fonte: `sessoes/2026-10-16_pessoa-3_antigravity_40ab3010`, 16/10 21:32–21:44.*

## 2. O Antonio levou ao projeto as respostas da Helena a outros times, e 118 alarmes falsos saíram (17/10, Antonio)

O Antonio passou o dia trazendo para a IA as respostas da Helena dadas a outros times e pedindo que conferisse o projeto contra cada uma; na resposta das 11h37 ("o que decide é o contrato, não o aviso"), a IA achou o conflito: a Casa do Estudante era concessão comercial, não divergência. A Casa saiu das divergências, que caíram de 233 para 115 (R$ 2.995,08), e os R$ 15.396,77 viraram devolução por conta da Tarvo (commit `2b679b3`).

*Fonte: chat `sessoes/2026-10-16_pessoa-2_claudeai_ab9fb32b`, pedidos 52–54; sessão `sessoes/2026-10-17_pessoa-2_claude_56449fe8` (relógio do computador da Pessoa 2: 17/10 09:24).*

## 3. Ele segurou o prompt e leu os e-mails antes: a IA tinha errado (17/10, Antonio; a IA errou)

A IA que escrevia os prompts do Antonio preparou o prompt seguinte para corrigir os rascunhos de contestação, mas ele respondeu "Ainda não mandei o B2" e leu os e-mails primeiro; com o texto na mão, a própria IA admitiu que dois itens do prompt dela estavam errados (os R$ 821,88 da operação duplicada e a conta dos spreads negativos) e que notas internas iam no corpo do e-mail para a Orbe e a Ponte. O prompt foi reescrito para conferir cada número nos dados antes de mexer no texto (commit `fd0db20`).

*Fonte: chat `sessoes/2026-10-16_pessoa-2_claudeai_ab9fb32b`, pedidos 46–48; sessão `sessoes/2026-10-17_pessoa-2_claude_56449fe8` (relógio da Pessoa 2: 08:41).*

## 4. O arquivo novo da Orbe chegou às 13h10 e só entrou quando bateu com um cálculo feito por fora (17/10, Pedro e Antonio)

O Pedro testou o arquivo novo numa cópia isolada antes de juntar ao `main`: o fechamento parava, e a mensagem do próprio programa mandava "substituir" o relatório, o que estaria errado. Ele simulou o resultado por fora (notas de R$ 246.588,68 para R$ 243.284,29), e o Antonio respondeu "Se a minha saída não bater, não subo"; a correção entrou às 13h35, batendo ao centavo (commits `9dd06b6` e `9d0db60`).

*Fonte: `sessoes/2026-10-17_pessoa-1_claude_6a4fd205`, 17/10 13h22–13h31; chat `sessoes/2026-10-16_pessoa-2_claudeai_ab9fb32b`, pedidos 65–66.*

---

**Reserva (outras decisões humanas com fonte):**
- O Antonio contrariou a IA e mandou as perguntas à Helena como perguntas abertas, sem levar a nossa proposta pronta (chat, pedido 36).
- O Pedro perguntou à Organização como seria a avaliação dos meses seguintes. Com a resposta (não haveria pacote de outubro), o time cortou a cobrança retroativa da Atlas e priorizou que a solução não quebrasse na mão de outra pessoa (chat, pedido 55).
- O Antonio conferiu as 1.943 linhas da Orbe antes de registrar o truncamento do centavo, depois que a IA errou essa conta (chat, pedidos 13–14).
- O Antonio achou o caminho da própria máquina gravado no registro de execução e escreveu ele mesmo o pedido de correção, "porque o repositório vai ser público" (`sessoes/2026-10-17_pessoa-2_claude_56513f87`, 15:38, commit `d62f927`).
- O documento de regras que a IA ajudou a escrever tinha 8 erros, achados ao recalcular tudo contra os dados (`sessoes/2026-10-16_pessoa-3_claude_be5d287e`, 16/10 23:16–23:21, commit `0beccf8`).
- O Pedro não deixou o README seguir o que o chat dizia: mandou comparar o README com o código atual, achou 10 divergências e só publicou depois de ver o diff (`sessoes/2026-10-17_pessoa-1_claude_6a4fd205`, 16:05–16:26, PR #17).
- Às 17h22 o time decidiu não mexer mais no código e o Pedro conferiu a entrega num clone limpo, como a banca vai rodar (`sessoes/2026-10-17_pessoa-1_claude_6a4fd205`, 17:22–17:25, PR #19).
