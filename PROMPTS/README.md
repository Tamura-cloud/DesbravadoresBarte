# PROMPTS — Histórico de uso de IA

O case pede **o histórico de todas as sessões de IA, de preparação e de construção** (transcript do Claude Code, link da conversa, export ou print), **sem edição** além de remover chaves de API e dados pessoais, e o `MOMENTOS.md` com 2 a 4 momentos (um deles com erro da IA).

## Como está organizado

| Onde | O quê |
|---|---|
| `sessoes/*_claude_*.jsonl` | Transcript original do Claude Code (só e-mails pessoais e chaves trocados por `[REMOVIDO]`) |
| `sessoes/*_antigravity_*.jsonl` | Transcript original do Antigravity, a preparação de 16/10 das 16h54 às 23h (mesma remoção) |
| `sessoes/*.md` | Visão legível de cada transcript: pedidos, respostas e ferramentas usadas |
| `antigravity_resumo_prompts_16-10.txt` | Resumo dos 17 prompts do Antigravity, escrito pela própria IA a pedido do time (índice; a prova é o `.jsonl`) |
| `sessoes/links.md` | Links e prints de conversas fora do Claude Code (claude.ai, ChatGPT etc.) |
| `MOMENTOS.md` | Os 2 a 4 momentos que importaram |
| Este arquivo | Índice dos prompts que mudaram algo de verdade, com o commit |

**Cada pessoa, no fim de cada bloco de trabalho (e obrigatoriamente antes das 18h15):**
```bash
python scripts/exportar_transcript.py --autor "pessoa-a"                  # sessões do Claude Code
python scripts/exportar_transcript.py --autor "pessoa-a" --antigravity    # sessões do Antigravity
```
O script lê os transcripts da própria máquina, remove e-mails pessoais e chaves (Anthropic, OpenAI, GitHub, Google) e grava em `sessoes/`. Use `--redigir "texto"` para tirar qualquer outro dado pessoal. Rodar de novo atualiza os arquivos da mesma sessão.

**Correções ao resumo do Antigravity** (o `.txt` foi mantido como a IA escreveu; os números certos estão no `HIPOTESES.md`):

| Prompt | O resumo diz | O correto |
|---|---|---|
| #5 | "5 arquivos CSV obrigatórios" | 6, incluindo `rastro.csv` |
| #13 | Casa do Estudante: "R$ 15.391,27 em 119 transações a devolver" | divergência de R$ 15.397,42 em 118 transações (R$ 15.391,27 é o que a Orbe cobrou nas 119) |
| #16 | Orbe paga o parcelado em "D+30" | "ao longo dos meses seguintes, conforme as parcelas" (Helena) |
| #17 | uso de IA vale 15% | vale 20% (15% é causa raiz) |

## Linha do tempo completa (desde o primeiro prompt)

Todos os pedidos feitos à IA, na ordem. O texto integral de cada um está nos transcripts de `sessoes/`.

| Quando | Ferramenta | O que pedimos |
|---|---|---|
| 16/10 16:54 | Antigravity | Preparar o computador (VS Code, Python, Claude, Git) e pesquisar tudo sobre a Barte, seus produtos, a área de AI Services, vídeos, notícias e cases; gerar os dossiês |
| 16/10 16:56 | Antigravity (subagente de pesquisa) | Buscas na web disparadas pelo pedido anterior: site, sitemap, notícias e cases da Barte |
| 16/10 17:55 | Antigravity | Destravar o push para o GitHub |
| 16/10 18:02 | Antigravity | Qual o papel de Jev e Laya neste case |
| 16/10 18:05 | Antigravity | Escrever uma proposta de projeto com Jev ou Laya |
| 16/10 19:34 | Antigravity | Ler as instruções e o data pack do case, sem alterar nada |
| 16/10 19:58 | Antigravity | Analisar o relatório do colega e as 14 dúvidas, sem tomá-lo como fio condutor |
| 16/10 21:32 | Antigravity | Avaliar o Graphify |
| 16/10 21:35 | Antigravity | Decidir não usar o Graphify |
| 16/10 21:39 | Antigravity | Criar o `CLAUDE.md` e avaliar se os dossiês atrapalham |
| 16/10 21:44 | Antigravity | Isolar os dossiês sem perder nada e montar o esqueleto do repositório |
| 16/10 21:54 | Antigravity | Como acompanhar as dúvidas do Slack |
| 16/10 21:59 | Antigravity | Ler a primeira cópia do Slack |
| 16/10 22:15 | Antigravity | Analisar perguntas e respostas do Slack com senso crítico |
| 16/10 22:26 | Antigravity | Conferir as regras nos dados com 100% de certeza |
| 16/10 22:57 | Antigravity | Analisar a branch `pix` do colega |
| 16/10 23:02 | Antigravity | Incorporar as respostas finais da Helena e publicar |
| 16/10 23:13 | Claude Code | Acesso ao GitHub a partir do app |
| 16/10 23:16 | Claude Code | Ler todos os arquivos e apontar erros de relação |
| 16/10 23:21 | Claude Code | Corrigir `CLAUDE.md`, `HIPOTESES.md` e o guia de pitch |
| 16/10 23:28 | Claude Code | Conferir o arquivo do Slack |
| 16/10 23:30 | Claude Code | Avaliar a organização e planejar o dia 17 |
| 16/10 23:35 | Claude Code | Organizar o trabalho do trio a partir de uma imagem de arquitetura |
| 17/10 06:05 | Claude Code | Verificar o que o case exige do histórico de prompts |
| 17/10 06:13 | Claude Code | Analisar a branch `pix`, os prints e as anotações, e gerar um PDF por pessoa |
| 17/10 06:33 | Claude Code | Refazer a divisão para trabalho em paralelo |
| 17/10 08:20 | Antigravity | Gerar o resumo dos prompts desde o início (`antigravity_resumo_prompts_16-10.txt`) |
| 17/10 08:35 | Claude Code | Incluir o histórico do Antigravity no `PROMPTS/` |
| 17/10 08:36 | Antigravity | Ler os PDFs de orientação do time para tirar dúvidas ao longo do dia |

Pedidos curtos de execução (commit, push, "pode", dúvidas de comando) ficam só nos transcripts.

## Prompts-chave (o que mudou o projeto)

Regra: entra aqui todo prompt que mudou uma regra de negócio, um número, a arquitetura ou corrigiu a IA. Uma linha, com o commit.

| Quando | Quem | Prompt (resumo) | O que a IA fez | O que decidimos / mudou | Commit |
|---|---|---|---|---|---|
| 16/10 18:02 | Time (Antigravity) | "Qual papel de Jev ou Laya nesse case?" | Comparou agente conversacional × motor determinístico | Tese do projeto: cálculo financeiro determinístico, IA só onde há ambiguidade | — |
| 16/10 19:58 | Time (Antigravity) | "Analise o relatório do colega, mas não tome como fio condutor" | Apontou premissas perigosas (faturar pela taxa cobrada pela Orbe) | Nada vira regra sem a Helena; perguntas organizadas para o Slack | — |
| 16/10 21:35 | Time (Antigravity) | "Então não vamos usar [o Graphify]" | Avaliou custo × benefício da ferramenta | Recusamos complexidade sem ganho no tamanho do projeto | — |
| 16/10 21:44 | Time (Antigravity) | "Faça o isolamento, mas sem perder nada" | Backup em branch, dossiês fora do contexto, `CLAUDE.md` focado | Contexto da IA só com o case Tarvo | `7d06117` |
| 16/10 22:15 | Time (Antigravity) | "Analise o Slack e seja crítico, não se deixe levar ao pé da letra" | Cruzou cada resposta da Helena com os dados em Python | Descobertas: Casa do Estudante zerada, Atlas fora, arredondamento linha a linha | — |
| 16/10 22:26 | Time (Antigravity) | "Faça se tiver 100% de certeza" | Varreu 100% das linhas: encodings cp1252, CNPJ com 13 dígitos, Bridge, estorno de agosto | Regras travadas no `CLAUDE.md` e `HIPOTESES.md` | `d425cd4` |
| 16/10 23:02 | Time (Antigravity) | Respostas finais da Helena (22h35) | Provou o PIX de R$ 18.240 sem remessa e resolveu os conflitos com a branch `pix` | Pendências de contestação e TED de outubro sem supor desconto | `f73937d` |
| 16/10 23:16 | Time (sessão de preparação) | "Analise todos os arquivos um por um e dê um veredito se entendeu ou se há erro de relação" | Recalculou tudo em Python a partir de `dados/` e comparou com o CLAUDE.md, o Slack e as instruções oficiais | Achou 8 erros no CLAUDE.md gerado antes com IA (ex.: débito da Rota que não existe, duplicata atribuída à EduAbroad, 85 em vez de 84 lançamentos) e o formato de saída fora do oficial | — |
| 16/10 23:21 | Time (sessão de preparação) | "Corrija CLAUDE.md, HIPOTESES.md e o guia de pitch, alinhando os schemas às instruções oficiais" | Corrigiu os valores e trocou os schemas pelos 6 CSVs oficiais com `rastro.csv` | Documentos passam a citar só valores recalculados; errata registrada no HIPOTESES.md | `0beccf8` |
| 16/10 23:28 | Time (sessão de preparação) | "Você leu o slack_tarvo.txt?" | Mapeou cada regra dos documentos para a resposta da Helena | Viu que o erro do débito da Rota veio de uma pergunta mal rotulada no Slack; faltam o registro pergunta → resposta e duas perguntas (seguro, Atlas) | — |
| 16/10 23:30 | Time (sessão de preparação) | "O que precisamos melhorar na organização e no plano para amanhã?" | Diagnóstico: muito documento, zero código; números copiados entre 5 documentos | Decidimos: código como fonte da verdade, valores de referência viram testes, mínimo até 11h | — |
| 16/10 23:35 | Time (sessão de preparação) | Imagem de arquitetura modular + "organize o trabalho para 3 membros" | Propôs monólito modular: leitores e core compartilhados, um motor por pessoa, orquestrador fino; descartou filas e front da figura | Estrutura `src/` com dono por pasta, testes de aceite e `PLANO_17-10.md` | `d588ad9` |
| 17/10 06:05 | Time (sessão de preparação) | "Os prompts importantes devem ser anotados, verifique se o case pede" | Conferiu a instrução: o case pede o histórico **completo**, não só os importantes | Script de exportação com remoção de dados pessoais, este índice e o Momento 3 | `ab7e47b` |
| 17/10 08:33 | Pessoa 3 | "Anotei os prompts do Antigravity, veja se importa para o histórico" | Achou o transcript original do Antigravity na máquina, um token do GitHub escrito nele e 4 erros no resumo | Exportar o transcript original (com token e e-mails removidos), manter o resumo como índice com errata, script passa a exportar Antigravity | (este commit) |

## Sessões que ainda faltam juntar

- ~~Preparação no Antigravity (16/10, 16h54–23h)~~: exportada.
- ~~Sessões do Claude Code que geraram a branch `pix` (Pessoa 2, 16/10 19h59 a 17/10 01h30)~~: exportadas, 15 sessões (`sessoes/*_pessoa-2_*`). Conversa no claude.ai: link em `sessoes/links.md`.
- Sessões da Pessoa 1 (integração, merge e PR #1): exportar às 17h30.
- Sessões de construção de 17/10 das três pessoas (exportar de novo às 17h30).
