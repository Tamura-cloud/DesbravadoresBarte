# Remoções nos transcripts

Os transcripts em `sessoes/` são cópias fiéis das sessões. O script `scripts/exportar_transcript.py` troca e-mails pessoais e chaves por `[REMOVIDO]` na exportação. Quando algo escapa, a troca é feita à mão e registrada aqui. Nada além do dado pessoal é apagado.

| Quando | Arquivos | O que foi trocado por `[REMOVIDO]` | Motivo |
|---|---|---|---|
| 17/10 ~16h | `sessoes/2026-10-17_pessoa-1_claude_6a4fd205.jsonl` e `sessoes/2026-10-17_pessoa-1_claude_ef2a5f84.jsonl` (1 ocorrência em cada) | e-mail corporativo nominal de um organizador do desafio | dado pessoal; a exportação da Pessoa 1 não tinha a opção `--redigir` para esse endereço |

| 17/10 ~17h50 | os mesmos dois arquivos, reexportados pela Pessoa 1, e `sessoes/2026-10-17_pessoa-1_claude_79de05b7.jsonl` (2 ocorrências, com o domínio já mascarado) | o mesmo e-mail do organizador | a reexportação trouxe o endereço de volta |

Os endereços genéricos de empresa que aparecem nos transcripts (como ouvidoria, suporte e financeiro) ficam, porque não identificam uma pessoa. A pesquisa sobre a Barte e os organizadores, feita no Antigravity em 16/10 a partir da página pública do evento, também fica: ela serviu para entender a empresa e o desafio antes do case.

O histórico do git ainda tem a versão anterior desses arquivos; ele não foi reescrito.
