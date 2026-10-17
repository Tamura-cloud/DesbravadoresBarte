# PROMPTS — Histórico de uso de IA

O case pede **o histórico de todas as sessões de IA, de preparação e de construção** (transcript do Claude Code, link da conversa, export ou print), **sem edição** além de remover chaves de API e dados pessoais, e o `MOMENTOS.md` com 2 a 4 momentos (pelo menos um com erro da IA).

**Para ler rápido:** comece pelo [`MOMENTOS.md`](MOMENTOS.md), depois pela tabela de [prompts-chave](#prompts-chave-o-que-mudou-o-projeto). Cada linha aponta para o commit e para o transcript onde dá para conferir.

## Como está organizado

| Onde | O quê |
|---|---|
| `MOMENTOS.md` | Os 4 momentos que importaram, em duas frases cada, com a fonte |
| Este arquivo | Sessões por pessoa, linha do tempo e prompts-chave com o commit que geraram |
| `sessoes/*_claude_*.jsonl` | Transcripts originais do Claude Code |
| `sessoes/*_antigravity_*.jsonl` | Transcripts originais do Antigravity |
| `sessoes/*.md` | Versão legível de cada transcript (pedidos, respostas e ferramentas usadas), gerada a partir do `.jsonl` |
| `sessoes/links.md` | Conversas fora do Claude Code (link público do claude.ai) |
| `antigravity_resumo_prompts_16-10.txt` | Resumo dos 17 prompts do Antigravity, escrito pela própria IA a pedido do time. É só um índice; a prova é o `.jsonl` (errata no fim deste arquivo) |

Nos `.jsonl` a única alteração é a troca de e-mails pessoais e chaves por `[REMOVIDO]`, feita pelo `scripts/exportar_transcript.py`. Nada mais foi editado.

## Sessões por pessoa

| Pessoa | Papel no dia 17/10 | Ferramentas | Arquivos |
|---|---|---|---|
| Pessoa 1 (Pedro Berlato) | Integração, README, configuração do repositório e checkpoints | Claude Code | 1 sessão `*_pessoa-1_claude_6a4fd205` (17/10 00h42–13h36); `ef2a5f84` é uma cópia anterior da mesma conversa, até 11h17 |
| Pessoa 2 (Antonio Miguel) | Código do fechamento (branch `pix`) e regras da Helena | Claude Code (extensão do VS Code) + chat do claude.ai como arquiteto | 18 sessões `*_pessoa-2_claude_*` + link em `sessoes/links.md` |
| Pessoa 3 (Erick Tamura) | Preparação, revisão dos documentos, histórico de IA e pitch | Antigravity + Claude Code (app desktop) | 2 sessões `*_pessoa-3_antigravity_*` + 2 sessões `*_pessoa-3_claude_*` |

> **Sobre os horários:** cada transcript usa o relógio do computador de quem o gerou. Nas sessões da Pessoa 2 de 17/10, os horários estão cerca de 3 horas atrás do real (o commit `db29cf0`, que aplica uma resposta da Helena das 9h45, aparece às 7h15). A ordem dos acontecimentos vale pelos commits e PRs no GitHub.

### Pessoa 2: o que cada sessão fez (horário do computador dela)

| Sessão | Início | O que pediu | Commit |
|---|---|---|---|
| `8c7139d6` | 16/10 19:59 | Esqueleto do repositório, sem lógica de negócio; regras e tipos no `CLAUDE.md` | `05f0482`, `7ebefb0` |
| `505bd3ba` | 16/10 23:02 | Leitor da Ponte Câmbio (`.eml` com XLSX anexo) | `a5f96a0` |
| `7752dae7` | 16/10 23:02 | Leitores do Aurora, do Meridiano e do plano de contas | `ad4c83a` |
| `828e3580` | 16/10 23:02 | Leitores da Orbe e da planilha de taxas | `288ab77` |
| `e4ae71c2` | 16/10 23:13 | Infraestrutura de saída: `ItemSaida`, escrita e validação dos 6 CSVs | `c4e098e` |
| `53a7e61c` | 16/10 23:20 | Linha CHECKOUT (R01–R10) | `804d4ad` |
| `1105e6b3` | 16/10 23:34 | Linha REMESSA (R11–R18) | `67c4044` |
| `1b701693` | 16/10 23:42 | Classificação dos extratos e pendências bancárias (R19–R21) | `214ccce` |
| `b140465b` | 16/10 23:55 | Ensaio de outubro: gerador de mês simulado e teste | `e701732` |
| `4eccea2b` | 17/10 00:07 | IA como plano B, só para lançamento sem regra (P14) | `a04df86` |
| `e749f188` | 17/10 00:17 | Revisão independente, só de leitura, das saídas | — |
| `656c59d7` | 17/10 00:54 | Correções vindas da revisão independente | `329831b` |
| `19b9e7bf` | 17/10 01:03 | README reescrito a partir do código | `f45295f` |
| `fa1611de` | 17/10 01:14 | Ensaio, sem publicar, do merge da `pix` com o `main` | — |
| `c9db715a` | 17/10 01:20 | `RESULTADOS.md` comparando a saída com os testes | `966ecf5` |
| `7c85056d` | 17/10 07:08 | Respostas da Helena: R22 (PIX acima das remessas é adiantamento) e conferência "Ponte Aérea × Ponte Câmbio" | `db29cf0` |
| `2646ca62` | 17/10 07:53 | R23: spread negativo sai das divergências e fica como contestação | `292a3eb` |
| `56449fe8` | 17/10 08:12 | R32–R40: o contrato decide a divergência, a Casa do Estudante é concessão, alerta de antecipação | `2b679b3` |

### Pessoa 1: principais pedidos (sessão `6a4fd205`)

| Quando | O que pediu | Resultado |
|---|---|---|
| 17/10 00:42 | Entender o case a partir do resumo da reunião de abertura e sincronizar com o GitHub como fonte da verdade | Panorama das branches; primeira cronologia em UTC (corrigida às 8h10) |
| 17/10 08:24 | Seguir o PDF de orientação da Pessoa 1 | Integração da `pix` com o `main` |
| 17/10 09:19 | Push, PR e merge da entrega | PR #1 |
| 17/10 09:26 | Ambiente virtual e ensaio de mês novo | Ensaio de outubro rodado |
| 17/10 09:50 | Perguntas necessárias para a banca, com o motivo de cada uma | Perguntas de logística à Organização |
| 17/10 11:11 | README com a saída real; `.gitignore`, `.claudeignore` e `CLAUDE.md` | PR #4 |
| 17/10 11:40 | Redigir o checkpoint 1 | Enviado à Organização |
| 17/10 12:23 | Corrigir a seção de outubro do README depois da resposta da Organização | PR #6 |
| 17/10 12:57 | README com a saída depois do PR #7, com diff antes de publicar | PR #9 |
| 17/10 13:12 | Ajustes 6–9 da revisão do Erick, só com aprovação explícita | PR #10 |
| 17/10 13:22 | Testar a branch que inclui o arquivo novo da Orbe (13h10) antes de juntar no `main` | Mostrou que o fechamento parava e os testes quebravam; simulou as notas corretas (R$ 243.284,29) |
| 17/10 13:35 | Destacar momentos e exportar a conversa | Candidatos A–D e esta exportação |

## Exportar os transcripts

Cada pessoa roda na própria máquina, na pasta do repositório (e de novo antes das 18h15, porque as sessões continuam crescendo):

```bash
python scripts/exportar_transcript.py --autor "pessoa-x"                  # sessões do Claude Code
python scripts/exportar_transcript.py --autor "pessoa-x" --antigravity    # sessões do Antigravity
```

O script lê os transcripts da máquina, troca e-mails pessoais e chaves (Anthropic, OpenAI, GitHub, Google) por `[REMOVIDO]` e grava em `sessoes/`. Use `--redigir "texto"` para tirar qualquer outro dado pessoal e `--origem` quando a sessão rodou em outra pasta. Rodar de novo atualiza os arquivos da mesma sessão.

## Linha do tempo da Pessoa 3 (desde o primeiro prompt)

Todos os pedidos da Pessoa 3, na ordem. Pedidos curtos de execução (commit, push, "pode", dúvidas de comando) ficam só nos transcripts.

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
| 17/10 06:13 | Claude Code | Analisar a branch `pix`, os prints e as anotações, e gerar um PDF de orientação por pessoa |
| 17/10 06:33 | Claude Code | Refazer a divisão para trabalho em paralelo |
| 17/10 08:20 | Antigravity | Gerar o resumo dos prompts desde o início (`antigravity_resumo_prompts_16-10.txt`) |
| 17/10 08:35 | Claude Code | Incluir o histórico do Antigravity no `PROMPTS/` |
| 17/10 08:36 | Antigravity | Ler os PDFs de orientação do time para tirar dúvidas ao longo do dia |
| 17/10 ~09:25 | Claude Code | "O MOMENTOS.md está falando nada com nada" e "a linha do tempo não começa no início" |
| 17/10 ~09:35 | Claude Code | Enxugar cada momento para as duas frases que o case pede |
| 17/10 ~09:45 | Claude Code | Conferir e incluir os transcripts da Pessoa 2 |
| 17/10 ~12:00 | Claude Code | Conferir o link público do chat da Pessoa 2 |
| 17/10 ~12:20 | Claude Code | Conferir as sessões da Pessoa 2 com o R22 e o R23 |
| 17/10 ~12:45 | Claude Code | Auditar o `PROMPTS/` e o README contra as instruções do case |

## Prompts-chave (o que mudou o projeto)

Entra aqui todo prompt que mudou uma regra de negócio, um número, a arquitetura ou corrigiu a IA. Uma linha, com o commit.

| Quando | Quem | Prompt (resumo) | O que a IA fez | O que decidimos / mudou | Commit |
|---|---|---|---|---|---|
| 16/10 18:02 | Pessoa 3 (Antigravity) | "Qual papel de Jev ou Laya nesse case?" | Comparou agente conversacional × motor determinístico | Tese do projeto: cálculo financeiro determinístico, IA só onde há ambiguidade | — |
| 16/10 19:58 | Pessoa 3 (Antigravity) | "Analise o relatório do colega, mas não tome como fio condutor" | Apontou premissas perigosas (faturar pela taxa cobrada pela Orbe) | Nada vira regra sem a Helena; perguntas organizadas para o Slack | — |
| 16/10 21:35 | Pessoa 3 (Antigravity) | "Então não vamos usar [o Graphify]" | Avaliou custo × benefício da ferramenta | Recusamos complexidade sem ganho no tamanho do projeto | — |
| 16/10 21:44 | Pessoa 3 (Antigravity) | "Faça o isolamento, mas sem perder nada" | Backup em branch, dossiês fora do contexto, `CLAUDE.md` focado | Contexto da IA só com o case Tarvo | `7d06117` |
| 16/10 22:15 | Pessoa 3 (Antigravity) | "Analise o Slack e seja crítico, não se deixe levar ao pé da letra" | Cruzou cada resposta da Helena com os dados em Python | Descobertas: Casa do Estudante zerada, Atlas fora, arredondamento linha a linha | — |
| 16/10 22:26 | Pessoa 3 (Antigravity) | "Faça se tiver 100% de certeza" | Varreu 100% das linhas: encodings cp1252, CNPJ com 13 dígitos, Bridge, estorno de agosto | Regras travadas no `CLAUDE.md` e `HIPOTESES.md` | `d425cd4` |
| 16/10 23:02 | Pessoa 3 (Antigravity) | Respostas finais da Helena (22h35) | Provou o PIX de R$ 18.240 sem remessa e resolveu os conflitos com a branch `pix` | Pendências de contestação e TED de outubro sem supor desconto | `f73937d` |
| 16/10 23:16 | Pessoa 3 (Claude Code) | "Analise todos os arquivos um por um e dê um veredito se entendeu ou se há erro de relação" | Recalculou tudo em Python a partir de `dados/` e comparou com o `CLAUDE.md`, o Slack e as instruções oficiais | Achou 8 erros no `CLAUDE.md` gerado antes com IA (ex.: débito da Rota que não existe, duplicata atribuída à EduAbroad, 85 em vez de 84 lançamentos) e o formato de saída fora do oficial | — |
| 16/10 23:21 | Pessoa 3 (Claude Code) | "Corrija CLAUDE.md, HIPOTESES.md e o guia de pitch, alinhando os schemas às instruções oficiais" | Corrigiu os valores e trocou os schemas pelos 6 CSVs oficiais com `rastro.csv` | Documentos passam a citar só valores recalculados | `0beccf8` |
| 16/10 23:28 | Pessoa 3 (Claude Code) | "Você leu o slack_tarvo.txt?" | Mapeou cada regra dos documentos para a resposta da Helena | O erro do débito da Rota veio de uma pergunta mal rotulada no Slack | — |
| 16/10 23:30 | Pessoa 3 (Claude Code) | "O que precisamos melhorar na organização e no plano para amanhã?" | Diagnóstico: muito documento, zero código; números copiados entre 5 documentos | Código como fonte da verdade e valores de referência como testes | — |
| 16/10 23:35 | Pessoa 3 (Claude Code) | Imagem de arquitetura modular + "organize o trabalho para 3 membros" | Propôs monólito modular, um dono por pasta; descartou filas e front da figura | Recálculo independente guardado como testes de aceite (usado depois na verificação) | `d588ad9` |
| 17/10 00:07* | Pessoa 2 (Claude Code) | "Implemente a IA como plano B (fallback) na classificação dos extratos" | IA só para lançamento sem regra, com cache e pendência obrigatória | Em setembro, zero chamadas: todos os 184 lançamentos casam uma regra | `a04df86` |
| 17/10 00:17* | Pessoa 2 (Claude Code) | "Você é um revisor independente que NÃO escreveu este código… somente leitura" | Recalculou as saídas e questionou 7 premissas (P15–P21) | Mantivemos as 7, cada uma com o número alternativo calculado no `RESULTADOS.md`; corrigimos formato e rastro | `329831b` |
| 17/10 06:13 | Pessoa 3 (Claude Code) | "Analise toda a branch pix, os prints e os PDFs; não dê merge" | Rodou a `pix` isolada (testes, saída idêntica) e achou que o status dela inventava uma segunda implementação no `main` | Entregar o código da `pix`; receita de integração ensaiada; 3 papéis em paralelo | — |
| 17/10 07:08* | Pessoa 2 (Claude Code) | Resposta da Helena (R22) + "confira que nenhuma regra confunde Ponte Aérea Estudantil com Ponte Câmbio" | Confirmou que o padrão "PONTE" casava a Ponte Aérea | Padrão restrito a "PONTE CAMBIO", com teste; PIX acima das remessas vira adiantamento | `db29cf0` |
| 17/10 07:53* | Pessoa 2 (Claude Code) | Resposta da Helena (R23) | Tirou os 4 spreads negativos das divergências, mantendo a contestação | Divergências: 237 → 233 | `292a3eb` |
| 17/10 ~08:10 | Pessoa 1 (Claude Code) | Conferir a autoria de cada commit no horário de Brasília | A cronologia anterior, em UTC, sugeria que a `pix` tinha sido descartada; no horário certo, as branches foram feitas ao mesmo tempo | Corrigida a mensagem ao grupo: era trabalho paralelo que ninguém juntou, não descarte | — |
| 17/10 08:12* | Pessoa 2 (Claude Code) | Respostas da Helena (R32–R40): "o que decide é o contrato, não o aviso" | Mediu a divergência contra a planilha; a Casa do Estudante virou concessão do comercial | Divergências: 233 → 115; devolução da Casa como pendência própria; alerta de antecipação da Atlas | `2b679b3` |
| 17/10 08:15 | Pessoa 1 (Claude Code) | Conferir no `.docx` oficial o "erro de schema" apontado pela IA na saída da `pix` | O alerta vinha do `CLAUDE.md` do `main`, não da instrução oficial | Alerta rebaixado, código mantido; a Organização confirmou depois | — |
| 17/10 08:33 | Pessoa 3 (Claude Code) | "Anotei os prompts do Antigravity, veja se importa para o histórico" | Achou o transcript original do Antigravity, um token do GitHub escrito nele e 4 erros no resumo | Exportar o original com token e e-mails removidos; resumo como índice com errata | `2ba7f84` |
| 17/10 ~09:25 | Pessoa 3 (Claude Code) | "O MOMENTOS.md está falando nada com nada" | Conferiu cada momento no transcript: o antigo Momento 1 dizia que a IA sugeriu nome aproximado, mas foi a própria IA que alertou contra | Momentos reescritos só com o que o transcript prova, cada um com a fonte | `a9328d9` |
| 17/10 11:11 | Pessoa 1 (Claude Code) | "Atualize o README com os dados da saída real" | Regerou a saída e leu dela em vez de copiar do chat; achou números desatualizados fora da lista | Todo PR do README passa a sair da `saida/` regerada, com diff antes de publicar | PR #4, #9, #10 |
| 17/10 13:22 | Pessoa 1 (Claude Code) | Testar a branch com o arquivo novo da Orbe antes de juntar no `main` | Rodou numa cópia isolada: o fechamento parava, 17 falhas e 170 erros; conferiu as 14 linhas e simulou as notas corretas | A Pessoa 2 usou essa simulação como gabarito da correção | — |


\* Horário do computador da Pessoa 2 (ver a nota sobre os horários acima).

## Correções ao resumo do Antigravity

O `.txt` foi mantido como a IA escreveu. Os números certos estão no `HIPOTESES.md`:

| Prompt | O resumo diz | O correto |
|---|---|---|
| #5 | "5 arquivos CSV obrigatórios" | 6, incluindo `rastro.csv` |
| #13 | Casa do Estudante: "R$ 15.391,27 em 119 transações a devolver" | R$ 15.396,77 cobrados pela Orbe nas 118 transações de setembro (R$ 15.391,27 inclui o estorno de agosto) |
| #16 | Orbe paga o parcelado em "D+30" | "ao longo dos meses seguintes, conforme as parcelas" (Helena) |
| #17 | uso de IA vale 15% | vale 20% (15% é causa raiz) |

## O que ainda falta juntar

- ~~Sessões da Pessoa 1 até 13h36~~: exportadas.
- Sessões da Pessoa 2 depois de `56449fe8` (respostas da Helena da tarde e o arquivo novo da Orbe).
- Reexportação final das três pessoas antes das 18h15, porque as sessões continuam crescendo.
