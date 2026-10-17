# Regras do projeto

- Nunca casar lojista por nome aproximado. Chaves: cod_estabelecimento (Orbe), CNPJ com 14 dígitos (Ponte e planilha), valor + data (extratos). Nome serve só de evidência.
- Toda linha lida carrega arquivo_origem e ref_origem desde o leitor: id_transacao (Orbe), Nº Operação (Ponte), número da linha física no arquivo, "L<n>" (Aurora), FITID (Meridiano).
- Nenhum valor, data, CNPJ ou nome de arquivo de setembro fixo no código. Regras de negócio e mapeamentos ficam em config/*.yaml.
- Regra de negócio só entra se estiver no HIPOTESES.md. Se faltar regra, pare e pergunte; não invente.
- Formato de saída: CSV com ; como separador, ponto decimal, datas AAAA-MM-DD, CNPJ só com 14 dígitos, linha_negocio CHECKOUT|REMESSA, banco AURORA|MERIDIANO, metodo REGRA|IA|HUMANO, confianca de 0 a 1.
- Todo número de saída precisa fechar com o rastro.csv: a soma de valor por id_saida tem que ser igual ao número reportado. Existe teste para isso.
- Rode pytest antes de dizer que terminou.
- Valores de setembro (contagens, totais) podem aparecer SÓ em tests/, como valores de referência. Nunca em src/ ou config/.
- Dinheiro é sempre decimal.Decimal com 2 casas (quantize ROUND_HALF_UP). Nunca float para valor monetário. Taxas percentuais também são Decimal, em pontos percentuais (2,59% vira Decimal("2.59")).
- Datas são datetime.date.
- Todo arquivo é aberto com encoding explícito. Nunca use o encoding padrão do sistema (estamos no Windows).
- Cada pessoa trabalha na própria branch e só mexe nos próprios arquivos. Arquivos compartilhados (comum.py, cli.py, CLAUDE.md) só mudam com o time avisado.
- Prompt que muda regra de negócio, número ou arquitetura, ou que corrige a IA, ganha uma linha na tabela "Prompts-chave" de PROMPTS/README.md (quando, quem, prompt, o que a IA fez, o que decidimos, commit).
- Transcripts: python scripts/exportar_transcript.py --autor "pessoa-x" (remove e-mails pessoais e chaves).
