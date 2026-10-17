# PROMPTS — Histórico de uso de IA

O case pede **o histórico de todas as sessões de IA, de preparação e de construção** (transcript do Claude Code, link da conversa, export ou print), **sem edição** além de remover chaves de API e dados pessoais, e o `MOMENTOS.md` com 2 a 4 momentos (um deles com erro da IA).

## Como está organizado

| Onde | O quê |
|---|---|
| `sessoes/*.jsonl` | Transcript original do Claude Code (só e-mails pessoais e chaves trocados por `[REMOVIDO]`) |
| `sessoes/*.md` | Visão legível do mesmo transcript: pedidos, respostas e ferramentas usadas |
| `sessoes/links.md` | Links e prints de conversas fora do Claude Code (claude.ai, ChatGPT etc.) |
| `MOMENTOS.md` | Os 2 a 4 momentos que importaram |
| Este arquivo | Índice dos prompts que mudaram algo de verdade, com o commit |

**Cada pessoa, no fim de cada bloco de trabalho (e obrigatoriamente antes das 18h15):**
```bash
python scripts/exportar_transcript.py --autor "pessoa-a"
```
O script lê os transcripts da própria máquina, remove e-mails pessoais e chaves e grava em `sessoes/`. Rodar de novo atualiza os arquivos da mesma sessão.

## Prompts-chave (o que mudou o projeto)

Regra: entra aqui todo prompt que mudou uma regra de negócio, um número, a arquitetura ou corrigiu a IA. Uma linha, com o commit.

| Quando | Quem | Prompt (resumo) | O que a IA fez | O que decidimos / mudou | Commit |
|---|---|---|---|---|---|
| 16/10 23:16 | Time (sessão de preparação) | "Analise todos os arquivos um por um e dê um veredito se entendeu ou se há erro de relação" | Recalculou tudo em Python a partir de `dados/` e comparou com o CLAUDE.md, o Slack e as instruções oficiais | Achou 8 erros no CLAUDE.md gerado antes com IA (ex.: débito da Rota que não existe, duplicata atribuída à EduAbroad, 85 em vez de 84 lançamentos) e o formato de saída fora do oficial | — |
| 16/10 23:21 | Time (sessão de preparação) | "Corrija CLAUDE.md, HIPOTESES.md e o guia de pitch, alinhando os schemas às instruções oficiais" | Corrigiu os valores e trocou os schemas pelos 6 CSVs oficiais com `rastro.csv` | Documentos passam a citar só valores recalculados; errata registrada no HIPOTESES.md | `0beccf8` |
| 16/10 23:28 | Time (sessão de preparação) | "Você leu o slack_tarvo.txt?" | Mapeou cada regra dos documentos para a resposta da Helena | Viu que o erro do débito da Rota veio de uma pergunta mal rotulada no Slack; faltam o registro pergunta → resposta e duas perguntas (seguro, Atlas) | — |
| 16/10 23:30 | Time (sessão de preparação) | "O que precisamos melhorar na organização e no plano para amanhã?" | Diagnóstico: muito documento, zero código; números copiados entre 5 documentos | Decidimos: código como fonte da verdade, valores de referência viram testes, mínimo até 11h | — |
| 16/10 23:35 | Time (sessão de preparação) | Imagem de arquitetura modular + "organize o trabalho para 3 membros" | Propôs monólito modular: leitores e core compartilhados, um motor por pessoa, orquestrador fino; descartou filas e front da figura | Estrutura `src/` com dono por pasta, testes de aceite e `PLANO_17-10.md` | `d588ad9` |
| 17/10 06:05 | Time (sessão de preparação) | "Os prompts importantes devem ser anotados, verifique se o case pede" | Conferiu a instrução: o case pede o histórico **completo**, não só os importantes | Script de exportação com remoção de dados pessoais, este índice e o Momento 3 | (este commit) |

## Sessões que ainda faltam juntar

- Sessões de preparação anteriores a 16/10 23h (dossiês da Barte, relatório técnico do Antonio, branch `pix`): cada autor exporta da própria máquina ou cola o link/print em `sessoes/links.md`.
- Sessões de construção de 17/10 das pessoas A, B e C.
