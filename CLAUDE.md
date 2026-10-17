# Regras do projeto

- Nunca casar lojista por nome aproximado. Chaves: cod_estabelecimento (Orbe), CNPJ com 14 dígitos (Ponte e planilha), valor + data (extratos). Nome serve só de evidência.
- Toda linha lida carrega arquivo_origem e ref_origem desde o leitor: id_transacao (Orbe), Nº Operação (Ponte), número da linha física no arquivo, "L<n>" (Aurora), FITID (Meridiano).
- Nenhum valor, data, CNPJ ou nome de arquivo de setembro fixo no código. Regras de negócio e mapeamentos ficam em config/*.yaml.
- Regra de negócio só entra se estiver no HIPOTESES.md. Se faltar regra, pare e pergunte; não invente.
- Formato de saída: CSV com ; como separador, ponto decimal, datas AAAA-MM-DD, CNPJ só com 14 dígitos, linha_negocio CHECKOUT|REMESSA, banco AURORA|MERIDIANO, metodo REGRA|IA|HUMANO, confianca de 0 a 1.
- Todo número de saída precisa fechar com o rastro.csv: a soma de valor por id_saida tem que ser igual ao número reportado. Existe teste para isso.
- Rode pytest antes de dizer que terminou.
