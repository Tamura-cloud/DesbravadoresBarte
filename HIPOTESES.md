# Hipóteses — fechamento de setembro/2026

Fontes deste arquivo:
- **Fonte 1:** HIPOTESES.md do colega em `origin/main` (commit `d425cd4`). Todo o conteúdo dela está aqui, nas seções 2, 4 e 5, identificado como `F1-H01` a `F1-H10`.
- **Fonte 2:** respostas públicas da Helena (financeiro da Tarvo) no canal #tarvo-financeiro em 16/10/2026. As perguntas foram feitas por outros times; as respostas valem para todos. Exceção: as perguntas do nosso time (Desbravadores Barte), respondidas em 17/10/2026: duas às 9h45 (viraram R22 e a validação de P04) e três às 9h48 (viraram R23, R24 e a validação de P16; na R23 a Helena remeteu à resposta pública dada à MN AI às 9h44). Ver seção 3.
- **Fonte 2, 17/10/2026:** respostas públicas da Helena a outros times às 9h47 (R30), 9h49 (R28), 9h53 (R29), 10h44 (itens 4 a 6: R25, R26 e R27), 11h33 (R31), 11h37 (R32 a R34, ao Theo Garcia), 11h38 (R35 a R38, à Southlands) e 11h41 (R39 e R40, à Prime). Os itens 1 a 3 das 10h44 descrevem o processo e não viraram regra. As citações literais estão em cada regra.
- **Aprovado por:** cada regra diz quem aprovou e quando, pelo critério da R28. Toda premissa (P01 a P26) diz o status.
- **Fonte 3:** respostas da Organização do hackathon no canal de Logística, 17/10/2026 (O01 a O04, seção 7). São decisões de formato, escopo e avaliação, não regra de negócio: não usam R nem P e não mudam nenhum cálculo.

Pela regra do CLAUDE.md, só entra no código regra de negócio que esteja aqui. Os valores de setembro citados neste arquivo são referência para os testes, nunca para `src/` ou `config/`.

---

## 1. Regras confirmadas pelo financeiro (fonte: Slack, com horário)

### Checkout (Orbe)

- **R01** — Comissão de checkout = valor_bruto × taxa contratada da planilha, linha a linha. O valor_taxa da Orbe NÃO é a comissão. A nota fiscal vai pela taxa contratada. *(pergunta de Fox AI, resposta da Helena às 20h05)* **Aprovado por:** Helena — 16/10/2026, 20h05.
- **R02** — Arredondamento comum para o centavo (meio centavo para longe do zero: -0,005 vira -0,01), linha a linha e depois soma. A Orbe trunca; truncamento não é divergência. *(pergunta de Fox AI, resposta da Helena às 21h13)* **Aprovado por:** Helena — 16/10/2026, 21h13.
- **R03** — Divergência de checkout existe só quando a taxa aplicada ≠ contratada. Valor = valor_bruto × (aplicada − contratada). A devolução ao lojista é decisão da Helena, caso a caso. *(pergunta de Fox AI, resposta da Helena às 20h05; pergunta de Fox AI, resposta da Helena às 21h13)* **Aprovado por:** Helena — 16/10/2026, 20h05 e 21h13; a devolução deixou de ser caso a caso com a R25 (17/10/2026, 10h44).
- **R04** — Estorno abate a comissão no mês do estorno (inclusive de venda de agosto), pela taxa contratada vigente na data da venda original. *(pergunta de MN AI, resposta da Helena às 20h06)* **Aprovado por:** Helena — 16/10/2026, 20h06.
- **R05** — Antecipação entra na mesma nota do lojista; a reversão anula só a taxa da antecipação que ela reverte. *(pergunta de MN AI, resposta da Helena às 20h47)* **Aprovado por:** Helena — 16/10/2026, 20h47.
- **R06** — Nota de checkout: uma por lojista por mês. Zero ou negativo não emite nota e vira pendência da Helena (não passa para o mês seguinte). Discriminação simples: serviço + competência. *(pergunta de MN AI, resposta da Helena às 20h47)* **Aprovado por:** Helena — 16/10/2026, 20h47.
- **R25** — A nota de checkout só documenta a taxa já descontada pela Orbe, pela taxa contratada (R01). O que a Orbe cobra a mais que o contratado é valor a devolver ao lojista: a devolução deixa de ser caso a caso (R03). A nota não soma divergência. *(resposta da Helena à Turma do Barulho, 17/10/2026, 10h44, item 4: "A nota só documenta a taxa que já foi descontada e não gera cobrança nova. Por isso, quando a Orbe cobra a mais, o lojista já recebeu a menos e eu preciso devolver.")* **Aprovado por:** Helena — 17/10/2026, 10h44.

### Cadastro de lojistas

- **R07** — EC 1043300981 = Novo Horizonte Intercâmbio; EC 1043396662 = Horizonte Viagens e Turismo (empresas diferentes); EC 1038867654 = Kiwi Experience. CNPJ e taxas pelas linhas delas na aba vigente. *(pergunta de Fox AI, resposta da Helena às 20h24)* **Aprovado por:** Helena — 16/10/2026, 20h24.
- **R08** — Atlas Idiomas (EC 1076801732): começou em 10/09, sem contrato vigente, taxa desconhecida. Não faturar até o comercial confirmar. A aba de 2025 não vale. *(pergunta de Fox AI, resposta da Helena às 20h24)* **Aprovado por:** Helena — 16/10/2026, 20h24; faturamento quando o Comercial confirmar: R30.
- **R09** — Rota Global: o contrato não mudou em 2026; as taxas acima da planilha são divergência. *(pergunta de Lucca Landeiro, resposta da Helena às 20h49)* **Aprovado por:** Comercial (condição do contrato da Rota Global), registrada pela Helena — 16/10/2026, 20h49.
- **R10** — Casa do Estudante: tarifa zerada no checkout (MDR e antecipação) de setembro a dezembro de 2026, por acordo do comercial. A remessa segue normal. O que a Orbe cobrou é devolvido ao lojista. *(pergunta de Lucca Landeiro, resposta da Helena às 20h49)* **Aprovado por:** Comercial (acordo comercial da Casa do Estudante), registrada pela Helena — 16/10/2026, 20h49. **Substituída em parte por R32:** a isenção é concessão comercial fora do contrato. Ela zera a comissão, não é divergência, e a devolução é custo da Tarvo, não se cobra da Orbe (R38).
- **R30** — Atlas Idiomas (EC 1076801732): quando o Comercial confirmar a taxa, ela vale desde 10/09 (a primeira transação), e setembro é faturado junto com outubro. Até lá vale a R08: nenhuma comissão, nota ou divergência, só a pendência pelo que a Orbe cobrou. Na confirmação, o fechamento de outubro precisa puxar as linhas da Atlas de setembro que ficaram pendentes (ainda não implementado, ver seção 4). O EC fica em config/checkout.yaml (faturamento_retroativo); a data da primeira transação, a quantidade, o bruto e a competência seguinte saem dos dados. *(resposta da Helena à MN AI, 17/10/2026, 9h47: "Quando o comercial confirmar, a taxa vale desde o começo (10/09) e eu faturo setembro junto com outubro. Então sim, outubro precisa puxar as linhas da Atlas de setembro que ficaram pendentes.")* **Aprovado por:** Comercial (taxa da Atlas), registrada pela Helena — 17/10/2026, 9h47.

### Remessa (Ponte Câmbio)

- **R11** — Comissão de remessa = 50% do Spread R$ realizado (e-mail da Ponte), arredondado por operação. A competência é a data de contratação. O status de compliance não muda nada. *(pergunta de MN AI, resposta da Helena às 20h48; arredondamento: pergunta de Fox AI, resposta da Helena às 21h13)* **Aprovado por:** Comercial (participação de 50% no contrato com a Ponte), registrada pela Helena; arredondamento e competência: Helena — 16/10/2026, 20h48 e 21h13.
- **R12** — Spread negativo (trava D-1 vencida, a trava vale 2h): fora da comissão e da nota; a Helena contesta. *(pergunta de MN AI, resposta da Helena às 20h48)* **Aprovado por:** Helena — 16/10/2026, 20h48.
- **R13** — Nº de operação é único: a duplicata conta uma vez e entra na lista de correção para a Ponte. *(pergunta de MN AI, resposta da Helena às 20h48; pergunta de Insper AI, resposta da Helena às 22h34)* **Aprovado por:** Helena — 16/10/2026, 20h48 e 22h34.
- **R14** — Spread "padrão" ou célula em branco = 1,5% sobre a PTAX de referência. *(pergunta de MN AI, resposta da Helena às 20h48)* **Aprovado por:** Comercial (spread padrão é taxa), registrada pela Helena — 16/10/2026, 20h48.
- **R15** — Divergência de remessa = valor cheio (o que o lojista pagou a mais), não a nossa metade. A tolerância é decisão nossa, escrita com o motivo. *(pergunta de Fox AI, resposta da Helena às 20h58)* **Aprovado por:** Helena — 16/10/2026, 20h58.
- **R16** — A nota de remessa sai pelo realizado, inclusive o excesso da Mundo Aberto; o ajuste vem no mês em que a Ponte devolver. Fica como pendência da Helena. *(pergunta de Theo Garcia, resposta da Helena às 21h45)* **Aprovado por:** Helena — 16/10/2026, 21h45.
- **R17** — Nota de remessa: uma só, tomadora Ponte Câmbio, pelo total da participação no mês. *(pergunta de MN AI, resposta da Helena às 20h47)* **Aprovado por:** Helena — 16/10/2026, 20h47.
- **R18** — Nada foi contestado ainda e o prazo está ok. Pendência de contestação com valor e operações. Não supor desconto no repasse; conferir o TED de outubro é pendência da Helena. *(pergunta de Lucca Landeiro, resposta da Helena às 22h33; pergunta de Insper AI, resposta da Helena às 22h34)* **Aprovado por:** Helena — 16/10/2026, 22h33 e 22h34.
- **R23** — Divergência é quando o lojista pagou diferente do contrato. No spread negativo o lojista não pagou a mais: o prejuízo é da Tarvo com a Ponte, então é pendência de contestação (R12, R18). Listar também nas divergências é permitido, desde que fique claro que é outra natureza.
  - **Decisão nossa:** o spread negativo NÃO entra em divergencias_taxa.csv, para a lista não misturar outra natureza nem gerar alarme falso. Fica só a PEN-NEG-REM, com o mesmo valor (P18). Substitui P02 e P15.
  - *(pergunta de MN AI, resposta da Helena às 9h44: "Para mim, divergência é quando o lojista pagou diferente do contrato. No spread negativo o lojista não pagou a mais. O prejuízo é nosso com a Ponte, então é pendência de contestação. Se quiserem listar também nas divergências, tudo bem, desde que fique claro que é outra natureza." Citada pela Helena às 9h48 em resposta à pergunta do nosso time, Desbravadores Barte)*
  - **Aprovado por:** Helena — 17/10/2026, 9h44, citada às 9h48.
  - **Respaldo da Organização (O04):** "Alarme falso é marcar uma divergência onde não existe." Pela R23 não existe divergência no spread negativo (o lojista não pagou a mais); listá-lo em divergencias_taxa.csv seria esse alarme falso. A decisão de deixá-lo só na PEN-NEG-REM fica mantida.
- **R27** — O ajuste de contestação da Ponte vem no relatório do mês seguinte, como crédito ou débito, e é registrado no mês em que aparece (não reabre o mês contestado). *(resposta da Helena à Turma do Barulho, 17/10/2026, 10h44, item 6: "A Ponte responde por e-mail e manda o ajuste no relatório do mês seguinte, como crédito ou débito. Eu confiro e registro no fechamento do mês em que o ajuste aparece.")* **Aprovado por:** Helena — 17/10/2026, 10h44.
  - **Como o código trata:** o formato da linha, o abatimento e a nota estão na R31 (Helena, 17/10/2026, 11h33). O trecho anterior deste item, que supunha o mesmo Nº de Operação da original, foi substituído.
- **R31** — A Ponte manda o ajuste como uma linha nova, com Nº de Operação próprio e Spread R$ negativo; a observação traz o Nº da operação original ("AJUSTE REF PC-..."). O ajuste entra no mês em que aparece e abate a participação da Tarvo desse mês, dentro da nota única para a Ponte; o rastro aponta para a operação original. Não há nota complementar. Se o mês fechar zerado ou negativo, não emite nota e vira pendência para a Helena (R06, R17). Esclarece a R27. *(resposta da Helena aos Desbravadores Barte, 17/10/2026, 11h33: "A Ponte manda o ajuste como uma linha nova, com Nº de Operação próprio e o Spread R$ negativo. A observação traz o número da operação original (\"AJUSTE REF PC-…\"). Ele entra no mês em que aparece. Abate a nossa participação daquele mês, dentro da nota única para a Ponte, e o rastro aponta para a operação original. Nota complementar não fazemos. Se o mês fechar zerado ou negativo, vale a regra que já está no canal: não emite e vira pendência para mim. No relatório de setembro não tem nenhum ajuste desse tipo. Isso conta para outubro em diante.")* **Aprovado por:** Helena — 17/10/2026, 11h33.
  - **Identificação:** a observação casa com o padrão de config/remessa.yaml (ajuste.padrao_observacao, inicial "AJUSTE REF (PC-\S+)", sem diferenciar maiúsculas). A checagem vem antes da R23: um ajuste nunca é spread negativo (PEN-NEG), divergência nem operação nova. O leitor aceita a linha sem CNPJ; o lojista é o da linha ou, se faltar, o da operação original quando ela é achada (senão o fechamento para).
  - **Efeito:** o abatimento entra na COM-REM do lojista e na NF-REM, que sai líquida (P25). Rastro: ref_origem = Nº de Operação da linha de ajuste (que é a linha de origem). O rastro.csv não tem coluna de descrição: a descrição "AJUSTE REF <PC original>" (com a competência da original e, se ela estava numa contestação do mês anterior, "contestada em AAAA-MM") vai na discriminação da NF-REM. Quando a original está no relatório da competência anterior, ela entra também no rastro da COM-REM e da NF-REM com valor 0,00 e o arquivo de origem do mês anterior.
  - **Competência anterior:** o fechamento procura a pasta ao lado da atual (troca a competência no nome da pasta ou usa a pasta com o nome da competência anterior). Se ela existe, confere ali se a original existe; se não existe, o abatimento acontece mesmo assim e abre PEN-AJUSTE-SEMORIG-<Nº do ajuste> para a Helena. Se a pasta anterior não existe, só registra a referência, sem pendência.
  - **Setembro:** nenhum ajuste, então nada mudou (Helena, 11h33).

### Extratos e classificação contábil

- **R19** — conta_codigo = contrapartida do movimento no banco. Folha, ISS, INSS, FGTS e DARFs de agosto e o repasse da Ponte de 04/09 já estavam registrados: baixam passivo ou recebível. Tarifas, aluguel, cloud, assinaturas e serviços entram direto na despesa do mês. Quando o extrato não deixar claro: premissa no HIPOTESES.md. *(pergunta de Fox AI, resposta da Helena às 21h14)* **Aprovado por:** Helena — 16/10/2026, 21h14.
- **R20** — PIX de R$ 7.350 sem identificação: não é receita até identificar. Devolução de PIX da Mundo Aberto: repasse que voltou, motivo desconhecido. Transferência de R$ 300 mil: sai do Aurora em 30/09 e cai no Meridiano em 01/10. *(pergunta de Lucca Landeiro, resposta da Helena às 20h49)* **Aprovado por:** Helena — 16/10/2026, 20h49.
- **R21** — A Orbe deposita tudo no Aurora. O saldo negativo é a conta garantida. Conciliar Orbe × banco parcela a parcela está fora do escopo: só classificar os créditos. *(pergunta de Insper AI, resposta da Helena às 22h34)* **Aprovado por:** Helena — 16/10/2026, 22h34.
- **R22** — PIX recebido de lojista acima das remessas do mês = adiantamento de remessa futura: é recurso de lojista em 2.1.02.001 e não é pendência. A Ponte Aérea Estudantil (lojista, CNPJ 95739378000118) não tem relação com a Ponte Câmbio. *(pergunta do nosso time, Desbravadores Barte, resposta da Helena às 9h45: "É a Ponte Aérea mandando dinheiro de uma remessa que ainda não foi feita. A operação sai em outubro.")* **Aprovado por:** Helena — 17/10/2026, 9h45.
- **R24** — Folha, ISS, INSS, FGTS e DARFs ficam provisionados todo mês: no fechamento, a folha e os impostos do mês são provisionados, e o pagamento no mês seguinte baixa a provisão. Vale para qualquer mês, não só para agosto (generaliza a parte de R19 sobre agosto). É o que config/bancos.yaml já faz. *(pergunta do nosso time, Desbravadores Barte, resposta da Helena às 9h48: "Sempre. Todo mês a folha e os impostos do mês ficam provisionados no fechamento, e o pagamento no mês seguinte baixa a provisão.")* **Aprovado por:** Helena — 17/10/2026, 9h48.
- **R26** — O repasse aos lojistas sai perto dos dias 10 e 24, conforme o contrato de adesão. Não reconciliar repasse parcela a parcela: só classificar (como na R21 para a Orbe). *(resposta da Helena à Turma do Barulho, 17/10/2026, 10h44, item 5: "A gente repassa duas vezes por mês, perto do dia 10 e perto do dia 24, o que a Orbe já liquidou até ali. A regra está no contrato de adesão de cada lojista, que fica numa pasta do comercial.")* **Aprovado por:** Helena (regra de fechamento; o prazo vem do contrato de adesão) — 17/10/2026, 10h44.

### Aprovação e contestação

- **R28** — Quem aprova cada tipo de regra: regra de fechamento é aprovada pela Helena; taxa ou condição comercial é aprovada pelo Comercial e registrada pela Helena. É o critério do campo "Aprovado por" deste arquivo. Premissa nossa (P01 a P24) fica "aguardando aprovação" até a pessoa certa aprovar. *(resposta da Helena à MN AI, 17/10/2026, 9h49: "Taxa e condição comercial, quem aprova é o comercial, e eu registro. Regra de como fechar, aprovo eu. [...] Registrar quem aprovou e quando é ótimo.")* **Aprovado por:** Helena — 17/10/2026, 9h49.
- **R29** — Contestação: um rascunho de e-mail por contraparte, com as operações anexadas. A Helena revisa e envia. *(resposta da Helena à MN AI, 17/10/2026, 9h53, à proposta de entregar "um rascunho de e-mail por contraparte com as operações em anexo: Orbe (Casa 118, Rota 87, Bridge 5) e Ponte (Mundo Aberto 23, os 4 spreads negativos e a PC-0926-0162 repetida)": "Ninguém tem essa função hoje. O comercial fecha e, quando lembra, manda um e-mail para a Orbe ou a Ponte. A Bridge foi avisada alguns dias depois de 15/09, e a Casa do Estudante e a Mundo Aberto não foram avisadas. Serve, e muito. Um rascunho por contraparte, com as operações anexadas, eu reviso e envio. Quantas operações vão em cada um é com vocês.")* **Aprovado por:** Helena — 17/10/2026, 9h53.
  - **Contrapartes:** Orbe e Ponte (a proposta citava as duas e a Helena aprovou). Os avisos de condição ficam em config/contestacao.yaml.
  - **Decisão nossa ("quantas operações vão em cada um é com vocês"):** todas as operações de cada contraparte vão no anexo: as divergências de checkout (DIV-CHK) para a Orbe; as divergências de remessa (DIV-REM), os spreads negativos (PEN-NEG-REM, R23) e a operação duplicada (PEN-DUP-REM) para a Ponte. Estornos ficam no total, com uma linha explicando.
  - **Implementação:** src/tarvo/contestacao.py, chamado pelo fechar. Usa os itens já calculados e grava numa pasta irmã de saida/ (padrão contestacoes/, em config/contestacao.yaml): orbe.md + orbe_operacoes.csv e ponte.md + ponte_operacoes.csv. saida/ continua com exatamente 6 CSVs. Cabeçalho "[RASCUNHO — Helena revisa antes de enviar]"; destinatário só como <e-mail da Orbe> e <e-mail da Ponte>. Cada .md abre com um bloco "NOTAS PARA A HELENA — apagar antes de enviar" (quem foi ou não avisado, valor a devolver a cada lojista pela R25, ressalvas); o corpo do e-mail não fala de aviso do Comercial. Lojista com condição comercial a comunicar (Casa do Estudante, Mundo Aberto) vai numa seção de comunicação e pedido de regularização; taxa acima do contrato (Bridge, Rota) e a contestação da Ponte (spreads negativos, duplicada) vão como cobrança. Qual seção cada lojista usa fica em config/contestacao.yaml. As partes da Tarvo mostradas são a P24. **Substituído por R32** quanto às seções: a Mundo Aberto vai como contestação de contrato, e a Casa sai do e-mail (só nas notas, como concessão).


### Respostas de 17/10/2026, 11h37 a 11h41 (Theo Garcia, Southlands e Prime)

- **R32** — O que decide é o contrato, não o aviso. Bridge (aditivo de 2,19% a partir de 15/09) e Mundo Aberto (1,20% registrado desde julho) são divergência: a contraparte cobrou diferente de uma condição contratada; a Helena contesta com a Orbe e com a Ponte, e o lojista é ressarcido. A Casa do Estudante é concessão comercial fora do contrato: a Orbe cobrou o contratado, quem abriu mão da receita foi a Tarvo, e a devolução sai do bolso da Tarvo. *(resposta da Helena ao Theo Garcia, 17/10/2026, 11h37, item 1: "O que decide é o contrato, não o aviso. A Bridge tem aditivo assinado (2,19% a partir de 15/09). A Mundo Aberto tem o 1,20% negociado e registrado desde julho. Nos dois casos a contraparte cobrou diferente de uma condição contratada. Isso é divergência: eu contesto com a Orbe e com a Ponte, e o lojista é ressarcido. O aviso atrasado é problema nosso de processo, mas não muda quem deve. A Casa é outra coisa. É uma concessão do comercial, fora do contrato, para segurar o cliente. A Orbe cobrou o que estava contratado. Quem abriu mão da receita fomos nós, então a devolução sai do nosso bolso.")* **Aprovado por:** Helena — 17/10/2026, 11h37.
  - **Respaldo da Organização (O04):** "Alarme falso é marcar uma divergência onde não existe." Na Casa a Orbe cobrou o contratado: não há divergência, e as 118 transações fora de divergencias_taxa.csv evitam esse alarme falso. A devolução é pendência de acompanhamento (PEN-CONCESSAO-CHK), com motivo e próximo passo, o que a O04 diz não ser alarme falso.
  - **No código:** a concessão (config/checkout.yaml, condicoes_especiais) muda só a taxa da comissão. A divergência é medida contra a planilha. As 118 transações isentas da Casa vieram pela taxa da planilha e saíram de divergencias_taxa.csv; a devolução delas é a PEN-CONCESSAO-CHK (R38). No ponte.md, a Mundo Aberto passou de "comunicação de condição" para "contestação: spread acima do contratado"; no orbe.md, a Casa saiu do corpo do e-mail e ficou só nas notas internas.
- **R33** — A antecipação é sobre a agenda inteira do lojista, inclusive parcelas de vendas de meses anteriores que o relatório do mês não traz; comparar com as vendas do mês acende lojista demais. O risco é lojista novo, sem histórico, antecipando alto. Não há limite definido: o critério é nosso (P26). *(resposta da Helena ao Theo Garcia, 17/10/2026, 11h37, item 2: "A antecipação é sobre a agenda inteira do lojista, inclusive parcelas de vendas de meses anteriores que o relatório de setembro não traz. Por isso a comparação com as vendas do mês acende lojista demais. O que me preocupa é lojista novo, sem histórico, antecipando alto. Não temos um limite definido. O critério é de vocês: escrevam no HIPOTESES.md.")* **Aprovado por:** Helena — 17/10/2026, 11h37.
- **R34** — Spread negativo: a pendência traz os dois valores, deixando claro qual é qual: o spread negativo do relatório (o que aconteceu) e a diferença até o spread do contrato (o que se pede à Ponte, porque a trava deveria ter sido honrada). O valor da PEN-NEG-REM continua sendo a diferença até o contrato (P18). *(resposta da Helena ao Theo Garcia, 17/10/2026, 11h37, item 3: "Coloquem os dois na pendência, deixando claro qual é qual: o spread negativo do relatório, que é o que aconteceu, e a diferença até o spread do contrato, que é o que eu vou pedir à Ponte, porque a trava deveria ter sido honrada.")* **Aprovado por:** Helena — 17/10/2026, 11h37.
- **R35** — Estorno: vale a taxa da data da venda original, e a faixa sai da própria linha do estorno (modalidade e parcelas). Confirma a R04. *(resposta da Helena à Southlands, 17/10/2026, 11h38, item 1: "Vale a taxa da data da venda original, e a faixa sai da própria linha do estorno (modalidade e parcelas).")* **Aprovado por:** Helena — 17/10/2026, 11h38.
- **R36** — Lojista sem contrato (Atlas): não fatura, vira pendência, e o repasse continua normal. Aparecer com zero ou ficar fora do arquivo de comissões é decisão nossa. *(resposta da Helena à Southlands, 17/10/2026, 11h38, item 2: "Não fatura, vira pendência, e o repasse continua normal. Se ele aparece com zero ou fica fora do arquivo de comissões é com vocês.")* **Aprovado por:** Helena — 17/10/2026, 11h38.
  - **Forma escolhida:** fora de comissoes_por_lojista.csv, como já era (P21, agora regra). O que a Orbe cobrou fica na PEN-SEMCONTRATO; os repasses à Atlas no Aurora (L34 e L60) seguem em 2.1.01.001 pela regra do PIX ENVIADO.
- **R37** — A lista de divergências é transação por transação; o estorno de uma venda que veio com taxa errada também entra, com valor negativo. *(resposta da Helena à Southlands, 17/10/2026, 11h38, item 3: "Sobre a lista: é transação por transação. O estorno de uma venda que veio com taxa errada também entra, com valor negativo.")* **Aprovado por:** Helena — 17/10/2026, 11h38.
- **R38** — Casa do Estudante: não emite nota e vira pendência; a devolução da Casa fica separada das divergências. *(resposta da Helena à Southlands, 17/10/2026, 11h38, item 4: "Não emite nota e vira pendência. A devolução da Casa fica separada das divergências.")* **Aprovado por:** Helena — 17/10/2026, 11h38.
  - **No código:** PEN-CONCESSAO-CHK-<CNPJ>, tipo DEVOLUCAO_CONCESSAO, com o valor_taxa cobrado nas transações da concessão e rastro por transação; motivo "concessão comercial - custo da Tarvo - não é divergência - não se cobra da Orbe" (o ";" vira " - " na saída). Era a PEN-DEVOL-CHK da Casa.
- **R39** — Atlas: o CNPJ da aba de 2025 é da Atlas e pode identificá-la; só a taxa daquela aba não vale. Zerada com pendência ou fora do arquivo, as duas formas servem, mas não se fatura (ver R36). O alerta de antecipação é alerta, e os números ficam com a Tarvo. *(respostas da Helena à Prime, 17/10/2026, 11h41: "Sim, o CNPJ é da Atlas, é a mesma empresa. Podem usar para identificar. Só a taxa daquela aba é que não vale." / "Zerada com pendência ou fora do arquivo, as duas formas servem. O que não pode é faturar. Escolham uma e registrem no HIPOTESES.md." / "É alerta, como já está no canal. Os números ficam com vocês, eu não confiro.")* **Aprovado por:** Helena — 17/10/2026, 11h41.
  - **No código:** config/checkout.yaml, cnpj_identificacao: EC 1076801732 → CNPJ 39566044000119, só para o id da pendência (PEN-SEMCONTRATO-39566044000119 e PEN-ALERTA-ANTEC-39566044000119) e o motivo. A planilha continua lendo só a aba vigente.
- **R40** — Casa do Estudante: a isenção vale para venda a partir de 01/09, e estorno de venda anterior segue a taxa da venda. Se o mês da Casa fechar negativo, vale a regra das notas (R06). *(resposta da Helena à Prime, 17/10/2026, 11h41: "A regra já está no canal: a isenção vale para venda a partir de 01/09, e estorno de venda anterior segue a taxa da venda. Os números eu não confiro. Se o mês da Casa fechar negativo, vale a regra das notas.")* **Aprovado por:** Helena — 17/10/2026, 11h41.

---

## 2. Premissas nossas (com o motivo)

### 2.1 Premissas definidas pelo time

Cada premissa ativa traz a linha "Se estiver errada, para a Helena": a consequência de negócio (o que ela deixaria de cobrar, contestar ou devolver, ou faria à toa), com lojista e valor em reais quando há. Nenhuma fala em contagem de linhas. As abertas estão reunidas no RESULTADOS.md, "Premissas abertas".

- **P01 — Tolerância de divergência de remessa:** diferença de spread abaixo de 0,01 p.p. não é divergência. **Status:** aguardando aprovação.
  - **Motivo:** a Ponte arredonda o spread entre 1,4984% e 1,5015%. A maior oscilação observada é de ±0,002 p.p., e a menor divergência real (Mundo Aberto) é de 0,3 p.p. É a tolerância que R15 deixa a nosso cargo. A Fonte 1 adota o mesmo critério (ver F1-H08).
  - **Se estiver errada, para a Helena:** com a tolerância larga demais, deixa de contestar com a Ponte diferenças reais de spread de outros lojistas (a menor diferença real de setembro, a da Mundo Aberto, é de 0,3 p.p., cerca de 30 vezes a tolerância, e soma R$ 1.418,85); com ela estreita demais, contesta centavos de arredondamento da PTAX (R$ 24,58 no mês todo, somando os valores sem sinal, nenhum acima de 0,002 p.p.).
- **P02 — Spread negativo também é divergência:** **substituída por R23** (Helena às 9h44 e 9h48: spread negativo não é divergência; saiu de divergencias_taxa.csv e fica só como contestação). Texto original: entra em divergencias_taxa.csv, com diferença negativa contra o contratado, e em pendencias.csv como contestação. **Status:** substituída por R23 (não aguarda aprovação).
  - **Motivo:** a taxa aplicada é diferente da contratada (R15), e R12 manda contestar. A Fonte 1 faz o mesmo (ver F1-H08). Reforçada em P15.
- **P03 — Truncamento da Orbe:** a Orbe trunca valor_taxa no centavo (verificado: as 1943 linhas batem com ROUND_DOWN, e 1001 não batem com ROUND_HALF_UP). Por isso a divergência compara taxa aplicada × contratada, nunca valores (R02). **Status:** aguardando aprovação.
  - **Se estiver errada, para a Helena:** se o truncamento da Orbe fosse erro a cobrar, deixaria de pedir à Orbe cerca de R$ 9,37 no mês (centavos de arredondamento das taxas); se a divergência fosse medida por valor e não por taxa, abriria contestação à toa por R$ 0,01 em vendas cuja taxa aplicada é a contratada.

**Remessa (remessa.py)**

- **P04 — CNPJ da Ponte fora da planilha de taxas:** a comissão é calculada mesmo assim (50% do spread realizado, R11) e entra na nota; o CNPJ vira pendência LOJISTA_NAO_CADASTRADO (cadastrar o lojista). Não gera divergência. **Status:** aguardando aprovação (a Helena achou o tratamento razoável às 9h45 e mandou registrar como premissa).
  - **Motivo:** a Ponte paga a participação pelo realizado, com ou sem cadastro nosso (R11, R16). Sem spread contratado, não há com que comparar a taxa aplicada (R15).
  - **Validada pela Helena às 9h45** ("tratamento razoável; registrem como premissa"). Não aconteceu em setembro. Continua premissa, não vira regra.
  - **Se estiver errada, para a Helena:** se o CNPJ da Ponte fora da planilha não devesse entrar na nota, emitiria a nota da Ponte com comissão que a Ponte não reconhece e teria de refazê-la; se a nota devesse esperar o cadastro, atrasaria o faturamento de uma comissão que a Ponte paga mesmo assim (R11, R16). Em setembro não aconteceu: R$ 0,00 em jogo. O spread contratado é condição comercial (R28): quem cadastra é o Comercial.
- **P05 — Spread negativo de CNPJ fora da planilha:** é erro e para o fechamento. **Status:** aguardando aprovação.
  - **Motivo:** R12 manda contestar e P18 valora a contestação pela diferença contra o contratado, que nesse caso não existe. Sem regra para o valor da contestação, preferimos parar a inventar um.
  - **Se estiver errada, para a Helena:** o fechamento para e ela fica sem a lista de contestação do mês até o Comercial cadastrar o lojista; se preferisse seguir, teria de decidir sozinha quanto pedir à Ponte, sem spread contratado como referência. Em setembro não aconteceu: R$ 0,00 em jogo.

**Extratos (bancos.py)**

- **P06 — Devolução de PIX ao Aurora:** contrapartida 2.1.01.001 (Repasses a lojistas a pagar), confiança 0,80, e pendência DEVOLUCAO_PIX com o valor, para apurar o motivo. **Status:** aguardando aprovação.
  - **Motivo:** R20 diz só "repasse que voltou, motivo desconhecido". Se o repasse voltou, ele volta a ser devido ao lojista; a conta é premissa nossa (a mesma da Fonte 1, F1-H10), por isso a confiança menor. Ver P16.
  - **Se estiver errada, para a Helena:** os R$ 12.400,00 que voltaram da Mundo Aberto (L65) estão na conta errada do passivo: até ela apurar o motivo, o saldo de repasses a pagar fica R$ 12.400,00 menor ou maior do que deveria. A mudança é de conta no passivo, não de resultado.
- **P07 — Favorecidos de "PIX ENVIADO" (Aurora):** só é repasse a lojista (2.1.01.001) o favorecido que estiver em config/favorecidos.yaml, com o texto exato do extrato e o CNPJ da aba vigente escrito à mão. A Atlas Idiomas, sem CNPJ na aba vigente, entra pelo EC 1076801732 e marcada "sem contrato" (R08). **Status:** aguardando aprovação.
  - Nunca casamento por nome aproximado: favorecido fora da lista não casa a regra e vira lançamento sem regra (P09). "HORIZONTE VIAGENS E TURISM" e "NOVO HORIZONTE INTERCAMBIO" são empresas diferentes (R07).
  - **Motivo:** pelo CLAUDE.md o nome é só evidência. A lista explícita deixa cada par revisável; a carga falha se o CNPJ não estiver na planilha.
  - **Se estiver errada, para a Helena:** favorecido na lista com CNPJ errado leva um repasse ao lojista errado (os repasses por PIX somam R$ 4.230.267,61 em setembro), e ela pagaria ou cobraria o lojista errado na conciliação; favorecido que faltou na lista vira lançamento que ela classifica à mão, sem perda de valor, mas com trabalho dela. Nunca por nome aproximado.
- **P08 — Pagadores de "PIX RECEB" (Meridiano):** mesmo método de P07, em config/pagadores_meridiano.yaml (texto exato do MEMO → CNPJ). Pagador fora da lista não casa a regra e fica sem regra (P09). O mesmo pagador pode ter mais de uma grafia no MEMO (ex.: "PONTE AÉREA" e "PONTE AEREA"); cada grafia é um par escrito à mão. **Status:** aguardando aprovação.
  - **Motivo:** o CNPJ do pagador é a chave da conferência PIX × remessas (P12); sem CNPJ não há conferência.
  - **Se estiver errada, para a Helena:** a conferência de PIX × remessas (P12) usaria o CNPJ errado: ela cobraria de um cliente uma diferença que é de outro, ou deixaria passar um PIX a menos. Os PIX recebidos de clientes somam R$ 5.629.687,12 em setembro (R$ 18.240,00 deles são adiantamento de remessa, R22).
- **P09 — Lançamento sem regra:** entra em lancamentos_classificados.csv sem classificação definitiva: conta_codigo "A_CLASSIFICAR", metodo HUMANO, confiança 0,00, e pendência PEN-SEMREGRA-<ref> com o valor do lançamento. Vale para crédito e débito. **Status:** aguardando aprovação.
  - **Motivo:** não lançar crédito desconhecido em 1.1.09.002 por regra: R20 cobre um caso conhecido (PIX sem identificação), não qualquer linha que as regras não reconhecem, e para débito não há conta transitória no plano. "A_CLASSIFICAR" não é conta do plano de propósito, para o lançamento não ser importado como definitivo. Esses lançamentos são a entrada do fallback com IA.
  - **Se estiver errada, para a Helena:** se o lançamento sem regra devesse ir para uma conta transitória em vez de ficar sem classificação, um crédito desconhecido entraria no razão sem aviso a ela; como está, ela classifica cada um à mão, com a pendência trazendo o valor. Em setembro todo lançamento casou uma regra: R$ 0,00 em jogo.
- **P10 — Confiança:** 1,00 para regra confirmada pela Helena (R19 a R22); 0,80 para regra que é premissa nossa: devolução de PIX (P06). Até a R22, o PIX identificado como recurso sem remessa (P12) também saía com 0,80; com a R22 ele é adiantamento confirmado e sai com 1,00. **Status:** aguardando aprovação.
  - **Se estiver errada, para a Helena:** a confiança só ordena a revisão dela. Com 0,80, a devolução de PIX de R$ 12.400,00 (Mundo Aberto, L65) é revista antes das demais; se ela confia nessa conta tanto quanto nas regras que confirmou, revisa à toa; se a confiança estivesse alta demais, deixaria de olhar R$ 12.400,00 que mereciam atenção. O resto do extrato está com 1,00.
- **P11 — Ponte × Meridiano (TED de liquidação):** para cada data, a soma das TEDs "LIQ OPERACOES" (com sinal) + a soma de valor_brl + iof_brl das operações únicas da Ponte (R13) contratadas nessa data tem que ser zero. Só entram as datas do período do extrato (DTSTART a DTEND). Diferença vira PEN-TED-LIQ-<data>, valor = operações − TEDs pagas. **Status:** aguardando aprovação.
  - **Se estiver errada, para a Helena:** se a TED de liquidação do dia não devesse bater com as operações contratadas no mesmo dia, ela investigaria com a Ponte uma diferença que não existe; sem a conferência, não veria que a Ponte pagou TED menor ou maior que as operações (as TEDs de liquidação de setembro somam R$ 5.611.447,12 e fecharam com as operações em todos os dias do extrato).
- **P12 — PIX recebidos × remessas, por cliente (CNPJ):** a soma dos PIX do mês é comparada com a soma de valor_brl + iof_brl das operações únicas do mês (competência pela data de contratação, R11). **Status:** aguardando aprovação.
  - **PIX a mais** (soma dos PIX > operações): a sobra é adiantamento de remessa futura (R22). Os PIX ficam em 2.1.02.001 pela regra do PIX, com metodo REGRA, e não há pendência. Todo pagador de "PIX RECEB" com regra é lojista com CNPJ da planilha (P08), então a R22 vale para todos.
  - **PIX a menos** (remessa sem o dinheiro do cliente): pendência no nível do cliente, PEN-PIX-REM-<CNPJ>, DIFERENCA_PIX_REMESSA, valor = PIX − operações (negativo).
  - A pendência PEN-PIX-SEMREM-<FITID> (RECURSO_SEM_REMESSA), para um PIX único igual à sobra, deixou de existir com a R22.
  - **Se estiver errada, para a Helena:** se a comparação por cliente devesse ser outra (por exemplo, pelo caixa do cliente e não pelas operações contratadas no mês), ela cobraria de um cliente que pagou adiantado, como a Ponte Aérea Estudantil (R$ 18.240,00 de remessa que sai em outubro), ou deixaria de cobrar um que não pagou. Em setembro os PIX de clientes (R$ 5.629.687,12) excedem as operações só nesses R$ 18.240,00, e nenhum cliente pagou a menos.
- **P13 — Aurora × Meridiano (transferência entre contas):** cada "TRANSF ENTRE CONTAS" do Aurora casa com uma TED "MESMA TITULARIDADE" do Meridiano de mesmo valor, na mesma data ou no dia útil seguinte (segunda a sexta, sem calendário de feriados); cada TED casa uma vez. **Status:** aguardando aprovação.
  - Sem par e com o dia útil seguinte depois do fim do extrato do Meridiano: PEN-TRANSF-<ref>, TRANSFERENCIA_EM_TRANSITO, valor positivo em trânsito (R20: cai no Meridiano no dia útil seguinte; conferir no extrato do mês seguinte).
  - Sem par dentro do período do extrato: PEN-TRANSF-<ref>, TRANSFERENCIA_SEM_PAR.
  - **Motivo:** R20 descreve a transferência do fim do mês que sai do Aurora e cai no Meridiano no dia seguinte. Uma transferência do meio do mês sem par não está em trânsito, é outra coisa, e o tipo diferente evita esconder isso.
  - **Se estiver errada, para a Helena:** se a TED de mesma titularidade pudesse chegar depois do dia útil seguinte (feriado, que o código não conhece), ela receberia como "sem par" uma transferência que só atrasou; se o pareamento fosse frouxo demais, daria como chegada uma transferência que não chegou. Em setembro, R$ 1.150.000,00 casaram com a TED do Meridiano e R$ 300.000,00 (30/09) estão em trânsito (P20).

**IA como plano B (ia.py, bancos.py; config/ia.yaml)**

- **P14 — IA só sugere, e só para lançamento de extrato sem regra:** **Status:** aguardando aprovação.
  - **Onde atua:** só no lançamento que nenhuma regra de config/bancos.yaml cobre (P09). O modelo sugere a contrapartida (R19) entre as contas analíticas do plano (aceita_lancto = S), com confiança de 0 a 1 e uma frase de justificativa. Recebe como contexto as contas analíticas, o texto de R19 deste arquivo e lançamentos do mesmo extrato já classificados por regra (um por regra).
    - O item sai com metodo IA, a conta sugerida e a confiança dada pelo modelo (não as confianças de P10).
    - Sempre há pendência PEN-IA-<ref>, tipo REVISAR_SUGESTAO_IA, com a justificativa no motivo e quem decide "Financeiro". Ela entra no lugar da PEN-SEMREGRA-<ref>.
    - Abaixo do limiar de config/ia.yaml, o motivo diz "baixa confiança".
  - **Onde não atua:**
    - Lançamento que alguma regra casou nunca passa pela IA.
    - Fica de fora de checkout, remessa, divergências, notas e das conferências cruzadas (P11 a P13). Lançamento com sugestão da IA não tem papel nas conferências.
    - Não cria regra e não mexe nas listas de favorecidos e pagadores (P07, P08). O nome continua sendo só evidência: um PIX de pagador fora da lista não vira cliente da Ponte por causa da IA.
    - A sugestão é descartada, e o lançamento volta ao fluxo de P09 (A_CLASSIFICAR, HUMANO, PEN-SEMREGRA), quando a conta não existe no plano ou é sintética, a confiança está fora de 0 a 1, o JSON é inválido, a resposta é cortada ou recusada, ou a chamada falha.
  - **Desligada:** com habilitada: false, com a flag --sem-ia, ou sem ANTHROPIC_API_KEY e sem a resposta no cache, o resultado é exatamente o de P09. Em setembro, todo lançamento casa uma regra: zero chamadas.
  - **Reprodutível:** a resposta bruta do modelo fica em cache/ia_sugestoes.json, por hash do lançamento (banco, ref_origem, data, descrição, valor) + modelo, e vai para o git. A mesma entrada dá sempre a mesma saída, sem chave e sem nova chamada. A validação roda de novo a cada leitura.
  - **Motivo:** pelo CLAUDE.md, regra de negócio só vem deste arquivo, e a Helena não deu à IA autoridade para classificar. A IA só adianta o trabalho de quem classifica. Por isso nenhuma sugestão vira lançamento definitivo sem uma pessoa olhar.
  - **Se estiver errada, para a Helena:** se a IA pudesse lançar sem revisão, uma conta errada entraria no razão sem ela ver; com a revisão obrigatória, cada sugestão é uma pendência dela e o ganho é só adiantar a classificação. Em setembro nenhum lançamento passou pela IA: R$ 0,00 em jogo.

**Escolhas mantidas após a revisão independente das saídas (P15 a P21)**

Uma revisão independente questionou as escolhas abaixo. Todas foram mantidas, menos a P15, substituída depois pela R23; o motivo de cada uma fica registrado aqui.

- **P15 — Spread negativo listado também como divergência (reforça P02):** **substituída por R23** (Helena às 9h44 e 9h48: spread negativo não é divergência). As 4 operações saíram de divergencias_taxa.csv; a contestação em pendencias.csv não mudou. Texto original: as 4 operações com spread negativo entram em divergencias_taxa.csv, além da contestação em pendencias.csv. **Status:** substituída por R23 (não aguarda aprovação).
  - **Motivo:** o docx do desafio define divergência como "taxa contratada ≠ aplicada", e no spread negativo a taxa aplicada é diferente da contratada. R12 tira a operação da comissão e da nota, mas não diz que deixa de ser divergência. Aguardando a confirmação da Helena.
- **P16 — Devolução de PIX em 2.1.01.001, não em 2.1.01.002 (reforça P06):** **Status:** aguardando aprovação (a Helena aceitou as duas contas às 9h48; a escolha é nossa).
  - **Motivo:** a Helena disse "PIX de repasse que voltou" (R20). Se o repasse voltou, ele volta a ser devido ao lojista: é Repasses a lojistas a pagar (2.1.01.001). A conta 2.1.01.002 (Devoluções e créditos a lojistas) é para devolução ao lojista, e a Helena não descreveu o caso como devolução ao lojista.
  - **Validada pela Helena às 9h48:** as duas contas servem ("Escolham uma, mantenham o mesmo critério e escrevam o motivo"). Escolhemos 2.1.01.001 pelo motivo acima, com critério fixo: toda devolução de PIX de repasse vai para 2.1.01.001, porque o repasse volta a ser devido ao lojista; 2.1.01.002 fica para devoluções e créditos a lojistas originados pela Tarvo (ex.: taxa cobrada a mais). Continua premissa nossa (a escolha entre duas contas válidas), com a confiança de P06 e P10.
  - **Se estiver errada, para a Helena:** os R$ 12.400,00 da devolução da Mundo Aberto estariam em 2.1.01.001 (Repasses a lojistas a pagar) em vez de 2.1.01.002 (Devoluções e créditos a lojistas): ela só mudaria de conta no passivo, sem efeito no resultado nem no valor devido. Ela aceitou as duas contas (9h48): o risco é de critério, não de valor.
- **P17 — Diferença de remessa calculada sobre o Spread % do relatório:** diferenca_brl = (Spread % aplicado − spread contratado) / 100 × PTAX de referência × Valor ME, arredondada por operação. **Status:** aguardando aprovação.
  - **Motivo:** assim a coluna diferenca_brl é exatamente reproduzível pelas colunas taxa_contratada_pct e taxa_aplicada_pct do mesmo arquivo. Pelo Spread R$ (Spread R$ − contratado × PTAX × Valor ME), o total da Mundo Aberto seria R$ 1.418,88 em vez de R$ 1.418,85: a diferença vem do arredondamento do Spread % no relatório da Ponte.
  - **Se estiver errada, para a Helena:** ela pediria à Ponte R$ 1.418,85 pela Mundo Aberto em vez de R$ 1.418,88 (se a conta fosse pelo Spread R$ do relatório): R$ 0,03 de diferença. Nos spreads negativos o total pedido não muda (R$ 3.565,98 nos dois cálculos), só a divisão entre as quatro operações, em centavos.
- **P18 — Contestação dos spreads negativos valorada pela diferença contra o contrato:** cada PEN-NEG-REM vale a diferenca_brl da operação (mesmo cálculo de P17), não o Spread R$ negativo. **Status:** confirmada pela R34 (Helena, 17/10/2026, 11h37: a diferença até o spread do contrato é o que ela vai pedir à Ponte).
  - **Motivo:** o que se contesta é a distância até o contratado. Antes da R23 era também o valor da linha em divergencias_taxa.csv (P15); com a R23 a linha saiu de lá, e o valor da PEN-NEG-REM continua o mesmo.
  - **Se estiver errada, para a Helena:** ela pediria à Ponte R$ 1.834,05 (o spread negativo do relatório, o que aconteceu) em vez de R$ 3.565,98 (a diferença até o spread contratado): R$ 1.731,93 a menos. **Confirmada pela R34:** a Helena disse que o que ela vai pedir à Ponte é a diferença até o contrato (R$ 3.565,98), com o spread do relatório (R$ 1.834,05) ao lado como o que aconteceu. Sem risco aberto.
- **P19 — PEN-DUP valorada pelo Spread R$ da cópia descartada (R$ 821,88 em setembro):** **Status:** aguardando aprovação.
  - **Motivo:** é exatamente quanto o total do relatório da Ponte está inflado: o rodapé soma R$ 78.073,59, e as operações únicas somam R$ 77.251,71 (R13). É o valor que a Ponte precisa corrigir no relatório.
  - **Se estiver errada, para a Helena:** ela pediria à Ponte que corrigisse o relatório em R$ 821,88 (o quanto o total está inflado) quando o que pesa para a Tarvo é a metade, R$ 410,94 (a parte de 50%): R$ 410,94 de diferença no pedido. A nota de remessa não muda, porque a operação conta uma vez só.
- **P20 — PEN-TRANSF mantida como item de conciliação para outubro:** a transferência de 30/09 continua em pendencias.csv como TRANSFERENCIA_EM_TRANSITO (P13), embora a R20 explique a transferência. **Status:** aguardando aprovação.
  - **Motivo:** a R20 explica o fato, mas o crédito no Meridiano só aparece no extrato de outubro. A pendência é o controle de que o dinheiro de fato chegou; ela se encerra na conciliação de outubro.
  - **Se estiver errada, para a Helena:** a pendência dos R$ 300.000,00 (saíram do Aurora em 30/09 e devem cair no Meridiano em 01/10) é de acompanhamento e a Organização aceitou esse tipo de pendência, com motivo e próximo passo (O04). Se fosse retirada e a transferência não chegasse, nenhum item do fechamento avisaria que R$ 300.000,00 saíram de um banco e não entraram no outro; mantida sem necessidade, custa a ela conferir a chegada no extrato de outubro.
- **P21 — Atlas fora de comissoes_por_lojista:** **Status:** aguardando aprovação. **Substituída por R36 e R39:** a Helena aceitou as duas formas; a escolhida (fora do arquivo) virou regra.
  - **Motivo:** o único CNPJ da Atlas está na aba "ANTIGO 2025 - nao usar", que a R08 proíbe ("a aba de 2025 não vale"). Sem CNPJ da aba vigente e sem taxa contratada, não há linha de comissão. O que a Orbe cobrou fica em PEN-SEMCONTRATO, pelo EC (F1-H02).

**Valor das pendências de conferência e de devolução (P22, P23)**

- **P22 — PEN-TED-PONTE tem o valor e o rastro da nota de remessa:** valor = valor da NF-REM; rastro = as mesmas origens da NF-REM (as operações da nota); ref_origem = a lista dessas operações, separada por "|". Sem nota no mês, valor zero e a referência é o relatório da Ponte. **Status:** aguardando aprovação.
  - **Motivo:** R18 manda conferir o TED, sem supor desconto. A referência da conferência é a nota de intermediação (R17), que é o que a Ponte paga "mediante recebimento da nota fiscal". Assim a pendência diz quanto conferir, e todo id_saida tem rastro.
  - **Se estiver errada, para a Helena:** ao conferir o TED da Ponte ela compararia o repasse com o número errado: se o valor certo não fosse o da nota de intermediação (R$ 39.543,45 em setembro), aceitaria um repasse menor ou cobraria um maior sem base. A R18 manda não supor desconto: o esperado é o valor da nota.
- **P23 — Devolução de checkout com condição especial vigente vale o que a Orbe cobrou:** para lojista com condição especial vigente (config/checkout.yaml, condicoes_especiais), a pendência de devolução vale a soma do valor_taxa efetivamente cobrado pela Orbe, com rastro por transação, e o motivo cita a regra da condição (R10). **Status:** aguardando aprovação. **Atualizada pela R32/R38:** a devolução da concessão é a PEN-CONCESSAO-CHK, separada das divergências. Se uma linha da concessão também divergir do contrato, a parte acima do contrato fica na PEN-DEVOL-CHK (a Orbe deve) e sai da PEN-CONCESSAO-CHK (premissa nossa, aguardando aprovação).
  - **Motivo:** R10 já decidiu a devolução ("o que a Orbe cobrou é devolvido ao lojista"). Para os outros lojistas, a R25 decidiu que o que a Orbe cobra a mais é devolvido; o valor continua pela fórmula da R03.
  - ~~As divergências em divergencias_taxa.csv não mudam: continuam pela fórmula da R03 (ver F1-H03).~~ **Substituída por R32:** a isenção não é divergência; a divergência é medida contra a planilha.
  - Se o mesmo lojista tiver no mês divergências com e sem condição especial, o fechamento para: não há regra para juntar as duas devoluções. **Substituída por R32:** as duas pendências (PEN-DEVOL-CHK e PEN-CONCESSAO-CHK) convivem; o fechamento não para mais.
  - **Se estiver errada, para a Helena:** ela devolveria à Casa do Estudante R$ 15.396,77 (o que a Orbe cobrou nas transações da concessão); se o valor certo fosse o da fórmula da R03, R$ 15.397,42, ficaria R$ 0,65 abaixo (o truncamento da Orbe, P03). Na parte que também divirja do contrato, ela contestaria com a Orbe mais ou menos do que a Orbe deve de fato.

**Rascunhos de contestação (P24)**

- **P24 — Partes da Tarvo mostradas nos rascunhos da Ponte (R29):** em ponte_operacoes.csv e ponte.md, três números que não estão nos CSVs de saida/:
  - spread acima do contratado: `parte_tarvo_brl` = participação (R11, 50%) × a diferença da DIV-REM, por operação, arredondada (R02);
  - operação duplicada: `parte_tarvo_brl` = participação × o spread da cópia (a PEN-DUP vale o spread inteiro, P19), mais `valor_operacao_brl` = valor em R$ + IOF, o que o cliente pagou;
  - spread negativo: `tarvo_deixou_de_receber_brl` = participação × o spread contratado em R$ (contratado % × PTAX de referência × valor em ME). É o que a Tarvo receberia pelo contrato e não recebeu, porque a operação sai da comissão (R12). A PEN-NEG continua valendo a diferença do spread inteiro (P18). **Atualizado pela R34:** o e-mail pede à Ponte a diferença até o spread contratado (o valor da PEN-NEG, sem sinal), mostrando o spread do relatório ao lado; a parte da Tarvo (`tarvo_deixou_de_receber_brl`) fica só nas notas internas.
  - **Motivo:** a Helena pediu que o e-mail deixe claro o que é do cliente e o que é da Tarvo. R11 dá a participação, e o contrato dá o spread. Os números são exibição: nenhum deles entra em comissão, nota, divergência ou pendência.
  - **Status:** aguardando aprovação. A leitura "a Tarvo também dividiria o prejuízo do spread negativo" (50% do spread aplicado negativo) não foi adotada: a Helena disse que o prejuízo é da Tarvo com a Ponte (R23) e não pediu para somá-lo.
  - **Se estiver errada, para a Helena:** os números são só de exibição, mas ela os lê antes de enviar: se a parte da Tarvo não for de 50% (R11), as notas internas mostram um valor errado (R$ 709,46 na Mundo Aberto, R$ 410,94 na operação repetida, R$ 865,98 que a Tarvo deixou de receber nos spreads negativos), sem alterar o que se pede à Ponte (R$ 1.418,85, R$ 821,88 e R$ 3.565,98).

**Alerta de antecipação (P26)**

- **P26 — Alerta quando lojista sem histórico antecipa mais do que vendeu no mês (R33):** pendência informativa PEN-ALERTA-ANTEC-<CNPJ>, tipo ALERTA_ANTECIPACAO, valor 0,00 (não muda nenhum valor), rastro com as antecipações a 0,00, para Financeiro (Helena) e Comercial. Compara a soma bruta das antecipações com a soma bruta das vendas do mês; o motivo traz também o líquido das reversões.
  - **Sem histórico:** se a pasta da competência anterior existe ao lado da atual, é não ter transação nela (o dado mais forte). Se não existe: nenhuma linha do mês ligada a venda anterior ao mês (estorno ou reversão com data de origem anterior) e primeira transação depois do dia 1, ou o primeiro contrato do lojista começando no mês.
  - **Motivo:** a Helena disse que o risco é lojista novo antecipando alto (R33) e deixou o critério conosco. A competência anterior é melhor que a heurística porque mostra o histórico de fato; a heurística fica para quando ela não está disponível.
  - **Setembro:** só a Atlas acende (R$ 235.943,10 antecipados contra R$ 135.428,90 vendidos, primeira transação em 10/09). A Oxford antecipou mais do que vendeu (112,5%), mas tem histórico (estorno de venda anterior) e não acende. Sem as reversões, a Atlas ficaria em R$ 127.230,96 e não acenderia; mantivemos o bruto porque a reversão não desfaz o pedido de antecipação.
  - **Status:** aguardando aprovação.
  - **Se estiver errada, para a Helena:** o alerta só avisa. Se o critério fosse frouxo, ela não veria um lojista novo antecipando alto (a Atlas antecipou R$ 235.943,10 brutos, R$ 127.230,96 líquidos das reversões, contra R$ 135.428,90 de vendas, sem contrato confirmado); se fosse apertado, olharia à toa lojistas com histórico, como a Oxford (antecipou 112,5% do que vendeu, mas tem histórico). Não muda nenhuma comissão, nota ou devolução.

**Ajuste da Ponte (P25)**

- **P25 — O Spread R$ do ajuste vira abatimento pela mesma participação das operações (R31):** abatimento = 50% (R11) do Spread R$ da linha de ajuste, arredondado (R02); o percentual está em config/remessa.yaml (ajuste.participacao_tarvo). Crédito (Spread R$ positivo) soma pelo mesmo critério.
  - **Motivo:** a Helena disse que o ajuste "abate a nossa participação", mas não disse se o Spread R$ da linha já vem como parte da Tarvo ou como o spread inteiro da operação. Adotamos o spread inteiro, como no resto do relatório da Ponte, e aplicamos os 50% da R11.
  - **Status:** aguardando aprovação. Se o valor já vier como parte da Tarvo, basta pôr "1" na configuração.
  - **Se estiver errada, para a Helena:** o ajuste da Ponte abate 50% do Spread R$ do ajuste. Se o valor do ajuste já vier como parte da Tarvo, a nota única da Ponte sairia mais alta que o devido: para cada R$ 100,00 de Spread R$ de ajuste, R$ 50,00 a mais, e ela teria de corrigir depois; no caso inverso, mais baixa. Setembro não teve ajuste: R$ 0,00 em jogo. Ela confirma no primeiro ajuste real; corrigir é pôr "1" na configuração.

### 2.2 Premissas e achados do HIPOTESES.md do colega (Fonte 1)

O conteúdo da Fonte 1 está reproduzido abaixo. Onde ela contradizia a Helena, o trecho foi ajustado à regra dela, e a versão original ficou registrada em "Conflitos resolvidos" na seção 4. Onde ela diz "confirmado pelo financeiro", a confirmação corresponde às respostas públicas da seção 1, e a regra correspondente está indicada. Os valores numéricos foram calculados pelo colega e **ainda não foram reconferidos pelo nosso código**.

**Mapeamento cadastral, contratos e condições comerciais**

- **F1-H01 — Vínculo dos 3 ECs sem código na aba "Taxas vigentes"** (regra: R07)
  - EC 1043300981 (HORIZONTE INTERCAMBIO) → Novo Horizonte Intercambio, CNPJ 66564512000199.
  - EC 1043396662 (HORIZONTE VIAGENS TURISMO) → Horizonte Viagens, CNPJ 78576234000179.
  - EC 1038867654 (KIWI EXPERIENCE TURISMO) → Kiwi Experience, CNPJ 07752116000126.
  - **Motivo dado na Fonte 1:** "confirmado pelo financeiro e validado pelo cruzamento de razão social e taxas aplicadas pela Orbe".
  - **Nota nossa:**
    - O vínculo vale pela resposta da Helena (R07), não pelo nome. Pelo CLAUDE.md, o nome serve só de evidência.
    - Conferimos na aba "Taxas vigentes": os 3 CNPJs acima são os das linhas Novo Horizonte Intercambio, Horizonte Viagens e Kiwi Experience. Nessas linhas a coluna "EC Orbe" está vazia, e a da Kiwi tem a observação "EC pendente".
- **F1-H02 — Atlas Idiomas Ltda (EC 1076801732, CNPJ 39566044000119)** (regra: R08)
  - Começou a transacionar em 10/09/2026, com 57 transações, R$ 262.138,61 brutos e R$ 7.876,05 de taxa retida pela Orbe. Consta apenas na aba histórica "ANTIGO 2025 - nao usar", sem contrato assinado na aba vigente.
  - **Decisão da Fonte 1:**
    - Não emitir NF em notas_a_emitir.csv, conforme a orientação "Não fatura a Atlas até o comercial confirmar".
    - Não gerar linhas em divergencias_taxa.csv, por não haver taxa contratada confirmada.
    - Registrar integralmente em pendencias.csv, para validação contratual com o Comercial (Diego).
  - **Motivo:** R08 diz "taxa desconhecida". Sem taxa contratada, não há como calcular divergência (R03). A Helena não disse explicitamente "não gerar divergência"; isso é premissa.
- **F1-H03 — Isenção (0,00%) da Casa do Estudante Viagens Ltda (EC 1018325654, CNPJ 00520815000100)** (regras: R10, R04, R06)
  - **Isenção:** a célula A13 da planilha vigente tem o comentário "conversar com Diego (comercial) sobre condição especial". A tarifa no Checkout (MDR e antecipação) é zerada de setembro a dezembro/2026. Nas remessas de câmbio se mantém o spread contratado normal de 1,50%.
  - **Cobrança indevida:** como a Orbe não foi parametrizada a tempo, cobrou indevidamente R$ 15.391,27 nas 119 movimentações do mês.
  - **Estorno TX88445133:** em 07/09/2026, a Orbe estornou um débito de -R$ 369,39, referente a venda de 21/08/2026.
    - Pela regra de que o estorno usa a taxa vigente na data_venda_original, vale 1,49% (agosto, antes da isenção). O estorno gera comissão contratada de -R$ 5,50 em setembro, sem divergência de taxa.
    - As demais 118 transações de setembro têm taxa contratada de 0,00%. Elas geram R$ 15.397,42 de divergência a devolver ao lojista, pelo cálculo arredondado linha a linha. *(Corrigido: a Fonte 1 dizia R$ 15.397,32; o valor certo, 15.397,42, foi conferido pelo checkout.py e por uma análise independente.)* **Substituído por R32:** a taxa contratada é a da planilha; as 118 vieram por ela e não são divergência. A devolução é a PEN-CONCESSAO-CHK.
  - **Consequência:** o saldo líquido de comissão de Checkout de setembro fica negativo (-R$ 5,50). Não se emite NF de Checkout, e o saldo negativo e a devolução das taxas cobradas pela Orbe vão para pendencias.csv.
  - **Devolução (P23):** a pendência de devolução vale o valor_taxa que a Orbe efetivamente cobrou nas 118 linhas, R$ 15.396,77, com rastro por transação (R10: "o que a Orbe cobrou é devolvido ao lojista"). A divergência em divergencias_taxa.csv continua pela fórmula da R03, R$ 15.397,42. A diferença de R$ 0,65 é o truncamento da Orbe (P03). **Atualizado pela R32/R38:** agora é a PEN-CONCESSAO-CHK, e não há mais divergência da Casa.
  - **Nota nossa:**
    - Os dois totais são compatíveis: R$ 15.391,27 é o que a Orbe cobrou nas 119 linhas (inclui os -R$ 5,50 do estorno), e R$ 15.397,42 é a divergência arredondada nas 118 linhas. *(Corrigido: a Fonte 1 dizia R$ 15.397,32; conferido pelo checkout.py e por uma análise independente.)*
    - A linha da Casa do Estudante na aba vigente tem vigência desde 01/01/2026 e Débito de 1,49%, o que sustenta a taxa de agosto usada no estorno.
- **F1-H04 — Zeros à esquerda em CNPJs:** ver seção 5.

**Regras de cálculo de comissões, arredondamento e divergências**

- **F1-H05 — ROUND_HALF_UP linha a linha** (regra: R02)
  - A Orbe trunca os centavos na segunda casa. A Tarvo arredonda para o centavo (0,005 → 0,01 e -0,005 → -0,01) em cada transação/operação, antes da soma por lojista e modalidade.
- **F1-H06 — Base da comissão e divergências no Checkout** (regras: R01, R03, R09)
  - **Base:** comissão e NF de Checkout pela taxa contratada: ROUND_HALF_UP(valor_bruto × taxa_contratada_pct / 100, 2).
  - **Truncamento:** diferenças de R$ 0,01 causadas só pelo truncamento da Orbe não são divergência.
  - **Quando há divergência:** só quando taxa_aplicada_pct ≠ taxa_contratada_pct. O valor é ROUND_HALF_UP(valor_bruto × (taxa_aplicada_pct − taxa_contratada_pct) / 100, 2).
  - **Casos encontrados:** 3 lojistas no Checkout.
    1. **Casa do Estudante (EC 1018325654):** cobrança de MDR e antecipação durante a tarifa 0,00%. São 118 transações de setembro, R$ 15.397,42. *(Corrigido: a Fonte 1 dizia R$ 15.397,32; ver F1-H03.)* **Substituído por R32:** não é divergência (concessão comercial).
    2. **Rota Global Intercâmbio Ltda (EC 1074504011):** cobrança indevida de +0,50 p.p. a partir de 12/09/2026, sem reajuste contratual. São 87 transações, com diferença líquida de R$ 1.546,28.
    3. **Escola Bridge de Idiomas Ltda (EC 1075624862):** cobrança de 2,59% em vez da taxa renegociada de 2,19% (vigente a partir de 15/09/2026) em 5 vendas de Crédito à Vista entre 15/09 e 18/09, somando R$ 29,95.
  - **Nota nossa:** a planilha confirma a renegociação da Bridge. Há duas linhas com o mesmo CNPJ e EC: Crédito à vista de 2,59% "até 14/09/2026" e de 2,19% "a partir de 15/09/2026" ("só mudou o crédito à vista"). A Helena não comentou a Bridge; o caso decorre de R03 aplicada à planilha.
- **F1-H07 — Estornos, antecipações e reversões no Checkout** (regras: R04, R05, R06)
  - **Estornos:** estornos de setembro referentes a vendas de agosto entram em setembro (agosto já está fechado). Eles abatem a comissão pela taxa contratada vigente na data_venda_original.
  - **Antecipações:** ANTECIPACAO (2,10%, exceto Casa do Estudante a 0,00%) e REVERSAO ANTECIPACAO compõem a base da mesma NF mensal de Checkout do lojista. A reversão anula a taxa da antecipação referenciada em id_referencia.
  - **Saldo zero ou negativo:** o lojista não tem NF emitida, e o saldo, seja zero ou negativo, vai para pendencias.csv (R06, Helena às 20h47). A Fonte 1 previa pendência só para o saldo negativo; ver C3 em "Conflitos resolvidos" na seção 4.
- **F1-H08 — Remessas (Ponte Câmbio)** (regras: R11 a R18 e R23; premissas P01 e P18)
  - **Base:** a comissão da Tarvo e a NF única contra a Ponte Câmbio S.A. (CNPJ 75374179000146) são 50% do Spread R$ realizado, arredondado (ROUND_HALF_UP) operação por operação. É diferente do Checkout.
  - **Spread padrão:** spread em branco ou "padrão" na planilha de taxas = 1,50% sobre a PTAX de referência (PTAX Ref. × Valor ME).
  - **Incluídas em setembro:** 228 operações válidas, com NF Ponte Câmbio = R$ 39.543,45.
    - As 6 operações contratadas em 30/09/2026 e liquidadas em 01/10/2026 (PC-0926-0002, PC-0926-0110, PC-0926-0249, PC-0926-0384, PC-0926-0549, PC-0926-0566) entram em setembro, pela data de contratação. *(Corrigido: a Fonte 1 citava 3 operações, PC-0926-0002, -0077 e -0148; conferido no relatório da Ponte, são estas 6.)*
    - Operações com status "APROVADO C/ RESSALVA" entram normalmente.
    - **Mundo Aberto (CNPJ 17217888000111):** a Ponte aplicou ~1,50% em vez dos 1,20% renegociados em jul/2026. As 23 operações entram na comissão e na NF de setembro pelo valor realizado, porque compõem o repasse imediato da Ponte.
      - Em divergencias_taxa.csv entram pelo valor cheio pago a mais pelo lojista: R$ 1.418,85 = (Spread % aplicado − 1,20%) × PTAX × Valor ME.
      - Também vão para pendencias.csv, para contestação com a Ponte Câmbio.
  - **Excluídas da comissão e da NF:**
    - **Duplicidade PC-0926-0162:** a segunda linha com o mesmo número de operação e a observação "Operação reprocessada" (Spread R$ 821,88) é descartada do cálculo e reportada em pendencias.csv.
    - **4 operações com spread negativo:** PC-0926-0210, PC-0926-0326, PC-0926-0491 e PC-0926-0545, somando Spread R$ = -R$ 1.834,05. Decorrem de "Taxa travada no pedido (D-1)" fora do limite contratual de 2 horas. São excluídas da comissão e da NF e reportadas em pendencias.csv para contestação. *(Corrigido pela R23: a Fonte 1 também as reportava em divergencias_taxa.csv; saíram de lá.)*
  - **Tolerância de arredondamento da PTAX (0,01 p.p.):**
    - Oscilações abaixo de 0,01 p.p. entre o Spread % reportado e a taxa contratada não são divergência; por exemplo, 1,4984% a 1,5015% para a taxa de 1,50%.
    - Vêm do arredondamento da taxa final de câmbio em 4 casas decimais. É a mesma tolerância de P01.
  - **TED da Ponte:** não supomos valor nem desconto no repasse (R18). A única pendência é conferir se o TED da Ponte bate com a nota de intermediação; quem decide é a Helena (P22). A projeção da Fonte 1 foi removida; ver C1 em "Conflitos resolvidos" na seção 4.

**Classificação contábil dos extratos (lancamentos_classificados.csv)**

- **F1-H09 — Contrapartida contábil e competência** (regra: R19)
  - **Conta:** conta_codigo registra a contrapartida contábil analítica (ACEITA_LANCTO = S) da movimentação bancária.
  - **Obrigações e recebíveis de agosto já provisionados:** baixam os respectivos passivos ou ativos. **Confirmada pela R24** (Helena às 9h48): todo mês a folha e os impostos do mês ficam provisionados no fechamento, e o pagamento no mês seguinte baixa a provisão.
    - Folha 08/2026 → 2.1.04.001.
    - ISS 08/2026 → 2.1.03.003.
    - INSS 08/2026 → 2.1.04.002.
    - FGTS 08/2026 → 2.1.04.003.
    - DARFs pagos em setembro com fato gerador em agosto:
      - IRRF 0561 → 2.1.03.004.
      - PIS 8109 → 2.1.03.001.
      - COFINS 2172 → 2.1.03.002.
    - Repasse da Ponte Câmbio recebido em 04/09 (MRD2026090132, R$ 61.884,12, ref. 08/2026) → baixa o ativo 1.1.03.002 (Comissões de intermediação a receber - câmbio).
  - **Despesas do mês não provisionadas:** vão direto para as contas de resultado (4.x).
    - Tarifas bancárias → 4.2.01.
    - Condomínio → 4.2.02.
    - AWS cloud → 4.2.03.
    - Google Workspace → 4.2.04.
    - Contabilidade → 4.2.06.
    - IOF → 4.3.01.
  - **Motivo:** R19. Os códigos específicos são o mapeamento do colega para o plano de contas.
  - **IOF:** não é premissa. É aplicação de R19 (Helena às 21h14: "além desses, nada estava provisionado"). Como não estava provisionado, vai direto para a despesa 4.3.01.
  - **Nota nossa:** pelo CLAUDE.md, esse mapeamento vai para config/*.yaml, não para o código.
- **F1-H10 — Anomalias bancárias e de conciliação** (regras: R20, R19)
  - **16/09/2026 (L50, Aurora)** — "PIX RECEBIDO 38686002000180 SEM IDENTIFICACAO" (+R$ 7.350,00): não é receita até identificar a origem. Vai para a conta transitória 1.1.09.002 (Créditos não identificados) e para pendencias.csv.
  - **23/09/2026 (L65, Aurora)** — "DEVOLUCAO PIX - MUNDO ABERTO INTERC" (+R$ 12.400,00): repasse que voltou, motivo desconhecido (R20, Helena às 20h49). Vai para 2.1.01.001 (Repasses a lojistas a pagar) e para pendencias.csv, com a pendência de apurar o motivo. Ver C2 em "Conflitos resolvidos" na seção 4.
  - **30/09/2026 (L92, Aurora)** — "TRANSF ENTRE CONTAS P/ BCO MERIDIANO" (-R$ 300.000,00): saída no último dia do mês, compensada no Banco Meridiano em 01/10/2026. Vai para 1.1.09.001 (Transferências entre contas próprias) e para pendencias.csv.
  - **17/09/2026 (MRD2026090425, Meridiano)** — "PIX RECEB PONTE AEREA ESTUDANTIL L" (+R$ 18.240,00): recurso recebido na conta de câmbio antes da operação da Ponte Câmbio. Vai para 2.1.02.001 (Recursos de lojistas para remessas a liquidar), com metodo REGRA.
    - **Resolvido pela R22 (Helena às 9h45):** é adiantamento de uma remessa que sai em outubro, não pendência. A Fonte 1 mandava para pendencias.csv; saiu de lá.
    - **Verificado:** é o único dos 64 PIX recebidos no Meridiano acima das remessas do mês na Ponte.
    - **FITID corrigido:** a Fonte 1 citava MRD2026090364, que não existe no OFX. O lançamento de 17/09 de R$ 18.240,00 tem FITID MRD2026090425, e o MEMO no arquivo é "PONTE AEREA", sem acento.
  - **Motivo:** para os três primeiros casos, R20 dá o fato e R19 manda escrever a premissa quando o extrato não é claro. O quarto caso é achado do colega, verificado por nós e respondido pela Helena (R22).

---

## 3. Perguntas feitas pelo nosso time (pergunta | resposta | horário)

A Fonte 1 não registra nenhuma pergunta feita pelo nosso time. As confirmações que ela cita são as respostas públicas da seção 1, dadas a perguntas de outros times. As perguntas abaixo foram feitas pelo nosso time (Desbravadores Barte) no #tarvo-financeiro.

| pergunta | resposta | horário |
|----------|----------|---------|
| No Meridiano entrou em 17/09 um PIX de R$ 18.240,00 de "PONTE AEREA ESTUDANTIL L" (FITID MRD2026090425), sem remessa correspondente na Ponte. [...] Proposta: 2.1.02.001 + pendência para você confirmar se é adiantamento de outubro ou devolução. | "É a Ponte Aérea mandando dinheiro de uma remessa que ainda não foi feita. A operação sai em outubro. A Ponte Aérea Estudantil é lojista e não tem nada a ver com a Ponte Câmbio." → **R22** | 17/10, 9h45 |
| Se aparecer na Ponte uma operação de um CNPJ que não está na planilha, propomos calcular a nossa metade do spread mesmo assim e abrir pendência de cadastro para o comercial. | "Não aconteceu em setembro. Se acontecer, o tratamento que vocês propuseram é razoável. Registrem como premissa." → **P04** (continua premissa) | 17/10, 9h45 |
| As 4 operações de spread negativo (PC-0926-0210, -0326, -0491, -0545): além da pendência de contestação, elas entram na lista de divergências de taxa? Ou divergência é só quando o lojista paga a mais? | A Helena remeteu à resposta pública dada à MN AI às 9h44: "Para mim, divergência é quando o lojista pagou diferente do contrato. No spread negativo o lojista não pagou a mais. O prejuízo é nosso com a Ponte, então é pendência de contestação. Se quiserem listar também nas divergências, tudo bem, desde que fique claro que é outra natureza." → **R23** (decidimos não listar; P02 e P15 substituídas) | 17/10, 9h48 (citando 9h44) |
| A devolução do PIX de R$ 12.400 da Mundo Aberto: lançamos em 2.1.01.001 (o repasse volta a ser devido). A 2.1.01.002 seria mais adequada? | "As duas contas fazem sentido. Escolham uma, mantenham o mesmo critério e escrevam o motivo." → **P16** (validada; mantida 2.1.01.001 com critério fixo) | 17/10, 9h48 |
| Folha, ISS, INSS, FGTS e DARFs pagos no mês seguinte estão sempre provisionados, ou só os de agosto? | "Sempre. Todo mês a folha e os impostos do mês ficam provisionados no fechamento, e o pagamento no mês seguinte baixa a provisão." → **R24** | 17/10, 9h48 |

---

## 4. Pendências em aberto

### Pendências abertas

- **TED da Ponte:** conferir se o TED da Ponte bate com a nota de intermediação (R$ 39.543,45, P22). Quem decide é a Helena (R18, 22h33/22h34).
- **Devolução de PIX da Mundo Aberto (L65, +R$ 12.400,00):** o motivo é desconhecido. Classificada em 2.1.01.001, com a pendência de apurar o motivo (R20, 20h49). A conta foi validada pela Helena às 9h48 (P16); o motivo continua em aberto.
- **Adiantamento da Ponte Aérea em outubro (pergunta a fazer):** a operação que o PIX de 17/09 adiantou sai em outubro (R22). Se em outubro ela vier sem PIX do mesmo mês, a conferência de outubro (P12) mostra PIX a menos e gera PEN-PIX-REM-95739378000118. Não há regra para abater o adiantamento de um mês anterior; não implementado.
- **Atlas em outubro (R30):** o fechamento de outubro só lê os arquivos de outubro. Faturar setembro junto com outubro exige as linhas da Atlas de setembro (Orbe de setembro) e a taxa confirmada pelo Comercial. Não há regra para trazer o mês anterior nem para onde a taxa confirmada entra (planilha de taxas ou config); perguntar à Helena antes de implementar.
- **Ajuste da Ponte (R27, R31):** formato e registro definidos pela R31. Ficam em aberto: a P25 (o Spread R$ do ajuste já vem como parte da Tarvo?) e o ajuste de uma operação mais antiga que a competência anterior, que hoje aparece como "original não encontrada" e abre PEN-AJUSTE-SEMORIG.
- **Valores da Fonte 1:** contagens e totais (por exemplo, 228 operações, R$ 39.543,45, R$ 1.546,28 e R$ 1.418,85) ainda precisam ser reconferidos pelo nosso código antes de virar valor de referência nos testes.

### Conflitos resolvidos

Em todos, vale a regra da Helena: ela é a fonte, e a Fonte 1 é a interpretação do colega.

- **C1 — TED da Ponte de outubro**
  - **Fonte 1 (F1-H08):** supunha que o TED automático da Ponte seria 50% do total do relatório (R$ 78.073,59 → R$ 39.036,80). Registrava preventivamente uma diferença de R$ 506,65 frente à NF (R$ 39.543,45), com data de 06/10 sem origem indicada. Também havia uma discrepância não explicada: 917,03 − 410,94 = 506,09, não 506,65.
  - **Fonte 2 (R18, 22h33/22h34):** "Não supor desconto no repasse; conferir o TED de outubro é pendência da Helena."
  - **Decisão:** a projeção, a diferença de R$ 506,65 e a discrepância 506,65 × 506,09 saíram da seção 2. Fica só a pendência "conferir o TED da Ponte quando cair", e quem decide é a Helena.
  - **Motivo:** a Helena proibiu supor desconto no repasse; a projeção era exatamente essa suposição.
- **C2 — Devolução de PIX da Mundo Aberto (L65, +R$ 12.400,00)**
  - **Fonte 1 (F1-H10):** descrevia como "estorno bancário parcial de repasse enviado ao lojista", recompondo a obrigação de repasse.
  - **Fonte 2 (R20, 20h49):** "repasse que voltou, motivo desconhecido".
  - **Decisão:** a descrição passa a ser "repasse que voltou, motivo desconhecido". A classificação continua 2.1.01.001, com a pendência do motivo.
  - **Motivo:** "estorno parcial" afirmava uma causa que a Helena disse não conhecer.
- **C3 — Saldo zero de comissão de checkout**
  - **Fonte 1 (F1-H07):** saldo zero ou negativo não emitia NF, mas só o negativo ia para pendencias.csv.
  - **Fonte 2 (R06, 20h47):** "Zero ou negativo não emite nota e vira pendência da Helena."
  - **Decisão:** saldo de comissão de checkout zero OU negativo não emite nota e vira pendência.
  - **Motivo:** é a regra literal da Helena.

### Pendências resolvidas

- **Spread negativo como divergência (P02, P15):** resolvido pela R23 (Helena às 9h44 e 9h48). As 4 operações (PC-0926-0210, -0326, -0491, -0545) saíram de divergencias_taxa.csv; as 4 PEN-NEG-REM continuam com o mesmo valor (P18).
- **Conta da devolução de PIX (P16):** as duas contas servem (Helena às 9h48); mantida 2.1.01.001 com critério fixo.
- **Provisionamento de folha e impostos (F1-H09):** confirmado para todo mês pela R24 (Helena às 9h48).

- **MRD2026090425 (+R$ 18.240,00, PONTE AEREA ESTUDANTIL):** adiantamento de remessa de outubro (R22, Helena às 9h45). Saiu de pendencias.csv; o lançamento continua em 2.1.02.001 com metodo REGRA, agora com confiança 1,00 (P10).
- **IOF (4.3.01):** deixou de ser premissa do colega. É aplicação de R19 (Helena às 21h14: "além desses, nada estava provisionado") e vai direto para a despesa 4.3.01.

---

## 5. Decisões de formato

### Saída (CLAUDE.md)

- CSV com `;` como separador, ponto decimal, datas AAAA-MM-DD.
- **Texto sem `;`:** nenhum campo de texto da saída (motivo, discriminacao, descricao, lojista, tomador e os demais) contém `;`. Os módulos trocam `;` por ` - ` ao montar o texto (`texto_saida`). A escrita não altera conteúdo: texto com `;` é erro, não vira campo entre aspas.
- **CNPJ:** sempre 14 dígitos, sem pontuação, com zeros à esquerda (`zfill(14)`). Isso vem de F1-H04: na planilha de taxas, os CNPJs de Fluente Idiomas Online Ltda (03229837000103) e Campus Global Ltda (08780784000120) estão como inteiros de 13 dígitos. A função `cnpj14` já trata isso.
- **Campos fixos:**
  - linha_negocio: CHECKOUT | REMESSA
  - banco: AURORA | MERIDIANO
  - metodo: REGRA | IA | HUMANO
  - confianca: de 0 a 1
- **Valores:** dinheiro em `Decimal` com 2 casas e ROUND_HALF_UP, linha a linha (R02). Taxas em pontos percentuais.

### Referências de origem (ref_origem)

- ref_origem do Aurora = linha física do arquivo, contando a partir de 1 (primeiro lançamento = L9), sem zeros à esquerda; aguardando confirmação no #hackathon-duvidas.
  - Conferido contra `ler_aurora`: os 84 lançamentos vão de L9 a L92. As referências antigas por posição (L042, L057, L084) viraram L50, L65 e L92 (posição + 8).

### Encoding dos arquivos de entrada (bytes conferidos em 16/10/2026)

O HIPOTESES.md da Fonte 1 não cita encoding. Quem cita é o CLAUDE.md do colega em `origin/main`: Aurora UTF-8, OFX cp1252, plano de contas cp1252. Conferimos os bytes reais dos arquivos de `dados/2026-09/`:

| arquivo | resultado | encoding a usar |
|---------|-----------|-----------------|
| Orbe CSV | só ASCII (0 bytes > 127) | `utf-8` explícito; o resultado é o mesmo em cp1252 |
| E-mail da Ponte (.eml) | só ASCII; o XLSX está em base64 | `ascii`/`utf-8`; o anexo é binário |
| Plano de contas CSV | UTF-8 inválido (falha no byte 320); cp1252 válido | `cp1252`, **confirmado** |
| Extrato Aurora CSV | UTF-8 válido, sem BOM; acentos como pares UTF-8 (ex.: "Jurídica", "Agência", "lançamentos") | `utf-8`, **confirmado** |
| Extrato Meridiano OFX | o cabeçalho declara `ENCODING:USASCII` e `CHARSET:1252`. UTF-8 inválido (falha no byte 924); cp1252 válido. Os 27 bytes > 127 são 0xC2 = "Â" (INTERCÂMBIO) e 0xC9 = "É" (AÉREA), letras corretas em cp1252. Não há U+FFFD nem sequência de UTF-8 corrompido | `cp1252`, **confirmado** |

- **Correção da descrição inicial do OFX:** a descrição que usamos no começo ("declara CHARSET 1252, mas os bytes são UTF-8 com caracteres já corrompidos") **não se confirma nos bytes**. O arquivo é cp1252 coerente com o cabeçalho.
- **Campos cortados no OFX:** alguns MEMO terminam no meio da palavra (ex.: "INTERCÂMB"). É corte de tamanho do campo, não problema de encoding.

---

## 6. Processo atual do financeiro (contexto, não é regra)

Fonte: resposta da Helena à Turma do Barulho, 17/10/2026, 10h44, itens 1 a 3. Descreve como o fechamento é feito hoje; nada daqui entra no código. Resumo, sem citação literal.

- **Sequência:** baixar os arquivos → checkout → remessa → extratos → notas.
- **Quem faz e quem controla (item 1):** "Quem executa são as duas analistas, e quem confere e aprova sou eu. O registro de que uma etapa terminou é uma aba de controle na mesma planilha, onde cada uma marca 'ok' e a data. Não tem nada além disso."
- **Tempo (item 2):** "Comissão de checkout, uns 3 dias. Metade é trabalho manual, casando nome com EC e CNPJ. A outra metade é retrabalho, quando a planilha está desatualizada. Remessa e Ponte, uns 2 dias. A maior parte é espera [...] Classificar os extratos, uns 2 dias. Quase tudo manual, linha por linha. O último dia é para as notas e a minha revisão." Soma: 8 dias.
- **Conhecimento (item 3):** "Quase tudo que vocês já descobriram aqui no canal estava só na minha cabeça [...] Se eu faltar, ninguém sabe essas regras." (ver R28)

---

## 7. Decisões da Organização (formato e avaliação; não são regra de negócio)

Fonte: Organização, canal de Logística, 17/10/2026. Não vêm da Helena e não mudam nenhuma regra de cálculo: em setembro, linhas, totais e rastro ficaram iguais (ver RESULTADOS.md).

- **O01 — A solução tem de servir para o mês que vem, sem mexer no código.** *"Não vai ter pacote de outubro. 'Rodar em outubro' quer dizer que a solução tem que servir para o mês que vem: receber arquivos novos no mesmo formato e gerar o fechamento sem ninguém mexer no código. A banca vai rodar a solução de vocês com os arquivos do case, inclusive os que chegarem durante o dia."* Fonte: Organização, canal de Logística, 17/10/2026.
  - **Como o código atende:**
    - Cada arquivo é achado pelo padrão de config/entradas.yaml (src/tarvo/cli.py, `localizar_arquivos`). O fechamento nunca escolhe um arquivo sozinho. Arquivo a mais no mesmo padrão ou arquivo faltando para a execução com código 2 e diz o tipo, o padrão, os candidatos e o que fazer ("deixe só um arquivo de <tipo> na pasta; substitua o antigo pela versão nova").
    - Arquivo que não casa nenhum padrão só gera aviso (`arquivos_ignorados`). O mesmo vale para o arquivo temporário do Office (~$...), que aparece com a planilha aberta no Excel.
    - Os 6 CSVs e os rascunhos são gravados numa pasta temporária e validados lá (src/tarvo/fechamento.py, `fechar`); só depois substituem saida/ e contestacoes/. Se a validação falhar, as duas pastas ficam como estavam e a CLI sai com 1.
    - Sem ANTHROPIC_API_KEY o fechamento roda com o cache. Lançamento sem regra e sem cache vira PEN-SEMREGRA (P09, P14), não erro.
    - config/ e cache/ são achados pelo caminho do pacote, não pela pasta atual.
- **O02 — saida/ tem só setembro, na raiz.** *"A saida/ tem só setembro, na pasta saida/ da raiz do repositório, como está nas instruções."* Fonte: Organização, canal de Logística, 17/10/2026.
  - **Como o código atende:**
    - saida/ tem só os 6 CSVs de setembro (e o .gitkeep).
    - O outubro simulado (tests/gerar_outubro.py) recusa gravar dentro de dados/, saida/ ou contestacoes/.
    - tests/conftest.py faz a sessão de testes falhar se algum teste gravar em dados/, saida/, contestacoes/ ou cache/.
    - Os rascunhos de contestação ficam em contestacoes/, pasta irmã de saida/ (R29), e não entram em saida/.
- **O03 — pendencias.csv: várias origens e quem_decide.**
  - (a) *"As duas formas valem. Pode ser uma linha por origem ou vários ref_origem na mesma célula separados por |. O que importa é dar para achar cada origem."*
  - (b) *"quem_decide é texto livre, não tem lista de valores. Pode ser a área ou a pessoa (comercial, Helena/financeiro, tesouraria), desde que seja coerente com o que já foi respondido no canal."*
  - Fonte: Organização, canal de Logística, 17/10/2026.
  - **Como o código atende (a):** a coluna ref_origem de pendencias.csv aceita a lista separada por "|" (src/tarvo/saida.py: `SEPARADOR_REFS`, `_refs`, tipo `REFS` na especificação de PENDENCIAS). Cada origem continua com uma linha própria no rastro.csv, com ref_origem única e valor.
  - **Como o código atende (b):** o quem_decide de cada pendência segue a R28 e quem respondeu o assunto no canal. Taxa e condição comercial ficam com o Comercial: PEN-SEMCONTRATO (R08) e PEN-NAOCAD-REM (P04). A concessão da Casa e o alerta de antecipação ficam com "Financeiro (Helena) e Comercial" (R32, R33). As demais regras de fechamento ficam com "Financeiro (Helena)"; a revisão da sugestão da IA, com "Financeiro" (P14).
- **O04 — Pendência de acompanhamento não é alarme falso.** *"Pendência de acompanhamento não é alarme falso, desde que tenha motivo e próximo passo. 'Conferir o TED quando cair' é exatamente isso. Alarme falso é marcar uma divergência onde não existe."* Fonte: Organização, canal de Logística, 17/10/2026.
  - **Como o código atende:**
    - Todo motivo de pendência diz o próximo passo: quem faz o quê. Os modelos que já traziam a ação (PEN-TED-PONTE, PEN-TRANSF, PEN-DEVOL-PIX, PEN-DUP-REM, PEN-CONTEST-REM, PEN-SEMCONTRATO, PEN-SEMREGRA, PEN-IA e PEN-AJUSTE-SEMORIG) ficaram como estavam.
    - Os outros ganharam "próximo passo: ...".
    - tests/test_estrutura.py confere todo modelo de motivo do código.
    - Respalda a R23 (spread negativo fora das divergências) e a R32 (a Casa fora das divergências).
