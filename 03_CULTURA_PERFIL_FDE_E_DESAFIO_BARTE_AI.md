# 🧬 03. CULTURA BARTE, PERFIL FDE / SQUADS AI E GUIA TÁTICO DO DESAFIO BARTE AI

Este documento sintetiza o **Culture Deck oficial da Barte** (`https://vagas.barte.io/cultura-barte.pdf` — 20 páginas), os perfis de contratação e histórias reais de colaboradores (`https://vagas.barte.io/` e `https://www.barte.com/cultura`), o modelo de **Partnership em 24 meses**, a estrutura exata das **AI Squads (Forward Deployed Engineering)** e o **Playbook de Guerra para o Desafio Barte AI** (`https://lu.ma/krxpb49i`).

---

## 1. O DNA Cultural da Barte (`cultura-barte.pdf` & `vagas.barte.io`)

### 1.1. A Regra nº 1: Densidade de Talentos e Partnership em 24 Meses
* **Prioridade #1 da Empresa:** *"Densidade de talentos é nossa prioridade #1. Cada pessoa que entra eleva o nível de quem já está."*
* **O Modelo de Partnership Acelerado:**
  > *"Não temos ninguém com 24 meses de empresa que não seja sócio."*
* **Visão de Raphael Dyxklay sobre Organizações AI-Native:**
  * No podcast *Astella Playbook*, Raphael Dyxklay explica que a Barte deixou de enxergar uma empresa como um "conjunto de cargos ou departamentos" para enxergá-la como um **"conjunto de habilidades alavancado por IA"**.
  * A Barte rejeita currículos tradicionais passivos: prefere testar pessoas construindo soluções reais sob pressão (exatamente o formato do *Desafio Barte AI*).

### 1.2. Os 3 Pilares Culturais Inegociáveis
No Culture Deck oficial, a Barte deixa explícito: *"Três pilares. Sem exceção. Não são valores de parede. São critérios práticos para contratar, promover e desligar."*

#### Pilar 01: PENSANTES (Primeiros Princípios)
* **Definição Oficial:** *"Operamos a partir dos primeiros princípios. Questionamos premissas, separamos objetivo de meio e tomamos decisões com clareza, mesmo quando não há resposta óbvia. 'Pessoas pensantes entendem o porquê das regras e sabem quando quebrá-las.'"*
* **Comportamentos Observáveis (O que a Banca procura no Hackathon):**
  * Não aceitar o problema pelo sintoma superficial; perguntar *"por que esse processo existe?"* antes de automatizá-lo.
  * Separar o **objetivo** (ex: garantir que nenhum pagamento saia errado e fechar o DRE no D+1) do **meio atual** (ex: 4 planilhas manuais que o cliente usa por hábito).
  * Comunicar raciocínios de forma estruturada, direta e sem jargão vazio ("embromation").
* **Exemplos Reais na Barte (`vagas.barte.io`):**
  * **Nicolas Cobra (`Nicolas C. · Pensante`):** *"Como estagiário, lidera a adoção de IA na Barte."* (Hoje é *AI Specialist for Finance* e apresenta o *Finance AI Live*).
  * **Davi V. e Pedro F. (`Pensantes`):** *"Como estagiários, foram a um órgão do governo e voltaram com 4.000 leads."*
  * **Marciel T. (`Pensante`):** *"Construiu a infra que destravou IA com segurança na Barte."*

#### Pilar 02: OBCECADOS (Alavanca, Velocidade e Intensidade)
* **Definição Oficial:** *"Obsessão não é trabalhar mais horas. É alocar atenção onde há mais alavanca. É gastar o cérebro, não só o suor, para encontrar soluções melhores. 'Se passaram 6 meses e seu escopo não mudou drasticamente, você está no piloto automático.'"*
* **Comportamentos Observáveis (O que a Banca procura no Hackathon):**
  * Foco implacável no que gera **80% do impacto financeiro** para o CFO nas primeiras horas do hackathon, em vez de gastar 4 horas escolhendo cor de botão.
  * Inconformismo com lentidão: se dá para validar uma hipótese em 15 minutos usando IA, não demore 2 horas.
* **Exemplos Reais na Barte (`vagas.barte.io`):**
  * **Alex C. (`Obcecado`):** *"Saiu de Jundiaí num sábado pra entregar a maquininha pro seller top 1."*
  * **Nathalia S. (`Obcecada`):** *"No primeiro mês como PM, destravou a integração do maior cliente."*

#### Pilar 03: DONOS (Responsabilidade Individual Radical)
* **Definição Oficial:** *"Colocar o problema debaixo do braço: se intrometer, não deixar combinados morrerem, garantir que as coisas andem, mesmo sem cobrança explícita. 'O dono não é um time, nem uma dupla. É uma única pessoa física que responde pelo resultado.'"*
* **Comportamentos Observáveis (O que a Banca procura no Hackathon):**
  * **Nunca dizer "nós estávamos vendo isso":** Na apresentação e na arguição de 5 minutos, cada integrante do grupo deve ser o **Dono claro** de sua frente (Negócio/Cliente, Finanças/Dados, Engenharia/Agentes), sabendo responder qualquer detalhe com precisão.
  * Se algo quebrar na demo, ter plano B testado e assumir o controle sem desculpas.
* **Exemplos Reais na Barte (`vagas.barte.io`):**
  * **Michelle M. (`Dona`):** *"Aprendeu Claude e construiu o cockpit de CX do zero."*
  * **Rafael Milaré (`Rafael M. · Dono`):** *"Cliente prestes a ir embora. Foi até lá, mapeou o problema e saiu com a conta 30x maior."*
  * **Felipe N. (`Dono`):** *"Trocou a stack do produto principal em 2 dias sem o cliente sentir."*

---

## 2. A Estrutura das Squads AI (Modelo FDE da Barte)

Extraído diretamente do código-fonte de `https://vagas.barte.io/`, cada **Squad AI** da Barte atua no modelo **FDE (*Forward Deployed Engineering*)**, atendendo até **10 clientes simultaneamente** e entregando os primeiros agentes em produção em **menos de 10 a 14 dias**.

Cada Squad AI possui exatamente **3 papéis**, que servem como o **molde perfeito para organizar o nosso grupo no Desafio Barte AI**:

### 2.1. Papel 1: `AI Client Partner` (Consultor / Líder de Projeto e Produto)
* **Contexto Oficial da Vaga:**
  > *"Papel de liderança de projeto dentro de squads que atendem 10 clientes simultaneamente. O Consultor entra nos clientes, estrutura os problemas identificados e define o roadmap de solução, coordenando a execução do Finance e do Engineer da squad."*
* **Responsabilidades Oficiais:**
  1. Atender clientes junto com o Finance, mapeando o contexto financeiro e operacional de cada um;
  2. Estruturar os problemas identificados: **transformar dor em diagnóstico claro e acionável**;
  3. Definir e priorizar o roadmap de solução para cada cliente, coordenando o que o Finance e o Engineer vão executar;
  4. Ser o ponto de contato principal com o cliente ao longo do projeto;
  5. Garantir a qualidade e coerência das entregas da squad.
* **Perfil Exigido:**
  * Generalista forte: entra em contextos diferentes rápido, conversa de igual para igual com C-level (CFO) e traduz problema de negócio em escopo de execução;
  * Domínio prático de ferramentas de IA (Claude, Cursor, automação) para prototipar fluxos e especificações.

### 2.2. Papel 2: `AI Finance Specialist` (Especialista Financeiro Sênior / Arquiteto de Regras e Dados)
* **Contexto Oficial da Vaga:**
  > *"Especialista financeiro dentro da squad de AI. Entra na operação real do cliente, abre os processos de controladoria, tesouraria, FP&A, contas a pagar/receber e conciliação, encontra a causa raiz da ineficiência e desenha a lógica financeira que os agentes vão executar."*
* **Responsabilidades Oficiais:**
  1. Diagnosticar gargalos reais em fechamento contábil, conciliação, fluxo de caixa, faturamento, contas a pagar/receber e fiscal;
  2. Estruturar a **fundação de dados** (plano de contas, centros de custo, regras de conciliação em cascata, tabelas *de-para*, matrizes de alçada);
  3. Validar a acurácia financeira das saídas dos agentes contra gabaritos contábeis reais;
  4. Quantificar o ROI financeiro para o CFO (horas salvas, redução de ciclo de fechamento, caixa recuperado).

### 2.3. Papel 3: `AI Engineer` / `Forward Deployed Engineer (FDE)` (Construtor de Agentes e Integrações)
* **Contexto Oficial da Vaga:**
  > *"Engenheiro embarcado na squad de AI. Constrói e coloca em produção agentes de IA, automações e integrações diretamente sobre a stack do cliente em ciclos curtos de dias, não meses."*
* **Responsabilidades Oficiais:**
  1. Desenvolver agentes autônomos e auditáveis usando LLMs (Claude, OpenAI, Gemini), OCR, *function calling* e *structured outputs*;
  2. Construir integrações rápidas via API, Webhooks, bancos de dados (PostgreSQL/Railway/SQLite), orquestradores (`n8n`, Python/FastAPI) e planilhas (Google Sheets/Excel) com ERPs (SAP, Conta Azul, Omie, TOTVS);
  3. Implementar interfaces de comando humano no **Slack / WhatsApp** e **Cockpits Executivos** com score de confiança, botão de aprovação ("Mão Levantada") e loop de retroalimentação ("O Sinal que Volta").

---

## 3. Guia Tático do Desafio Barte AI (`https://lu.ma/krxpb49i`)

### 3.1. Resumo das Regras Oficiais e Logística
* **Público e Formação:** Estudantes e recém-formados (graduação entre **2024 e 2028**, qualquer curso), em equipes de 1 a 3 integrantes.
* **Organizadores Presentes:** Túlio Lancaster Santos Andrade (`tulio.andrade@barte.com`), Beny Braun, Daniel Dias, Manuel Freitas, além dos founders (**Caetano Lacerda** e **Raphael Dyxklay**) e banca convidada.
* **Agenda Crítica:**
  * **Sexta-feira, 16/10 às 19h00:** Kickoff online obrigatório e liberação do Case.
  * **Sábado, 17/10 na Casa Barte (Vila Madalena, SP):**
    * `08h00`: Check-in e café *(Chegar antes das 07h50! Pontualidade é avaliada!)*.
    * `09h00`: Painel com os founders + Início do desenvolvimento.
    * `18h30`: **Submissão final via GitHub** (`https://github.com/Tamura-cloud/DesbravadoresBarte.git`).
    * `19h00`: Divulgação do **Top 3 Finalistas**.
    * `19h30`: **Pitch dos Finalistas (15 min de apresentação + 5 min de Q&A da banca)**.
    * `20h30`: Premiação (**R$ 5.000** + convites para a turma de **até 5 Junior Fellows**) e Happy Hour.

### 3.2. Checklist dos 7 Diferenciais Competitivos para Tirar Nota Máxima da Banca
Quando a banca (formada pelo time de AI Services da Barte e convidados) abrir o nosso repositório no GitHub às `18h30` e assistir ao nosso pitch às `19h30`, estes 7 pontos vão mostrar que operamos exatamente como uma **Squad FDE nativa da Barte**:

1. **Zero "Automação Cega" — Sempre mostrar o Score de Confiança e a "Mão Levantada":**
   * Como no Case Sallve e nos Demos oficiais, o nosso agente **nunca chuta**. Se a confiança da classificação/conciliação for `>= 95%` e estiver dentro da alçada, ele executa sozinho; se for `< 95%` ou violar uma regra de alçada/política, ele **levanta a mão** para o humano com o contexto mastigado.
2. **Implementar "O Sinal Que Volta" (Maturidade Nível 4):**
   * Como enfatizado nos artigos do blog FDE sobre os 5 Níveis de Maturidade: quando o humano clica em **"Aprovar / Corrigir Regra"** na exceção levantada pelo agente, essa decisão deve ser salva imediatamente na tabela de memória/regras do agente. Na demo ao vivo, mostre um segundo lote passando onde aquela mesma exceção agora é resolvida **100% sozinha** porque o agente aprendeu com o humano!
3. **Respeitar a Regra 20:1 (95% Fundação de Dados + 5% IA):**
   * Mostre um pipeline que primeiro normaliza, limpa e aplica regras determinísticas/cascata sobre os dados brutos (como a cascata de 5 passos da Buser: `CPF -> Nome Fuzzy -> Valor/Soma Múltipla -> Janela de Data -> Forma de Pagamento`) e usa o LLM cirurgicamente onde há ambiguidade semântica ou documentos não estruturados (PDFs/NFs/Contratos/E-mails).
4. **Trilha de Auditoria Completa por Linha (Audit Trail):**
   * Para um CFO confiar na IA (lembre-se: 97% exigem supervisão e só 14% confiam hoje), cada lançamento processado pelo nosso sistema deve exibir: `Timestamp`, `Agente/Regra que executou`, `Critério da Cascata utilizado`, `Score de Confiança`, `Documento de Origem` e `Status (Auto-Conciliado vs. Aprovado por Humano)`.
5. **Integração no Fluxo que o Financeiro Já Usa (Slack + Planilha/ERP + Cockpit):**
   * O CFO e o analista não querem abrir mais um sistema complexo. Mostre os alertas e aprovações de alçada acontecendo estilo **Slack** (como a agente *Ângela* da Comp e os demos `/demo/` da Barte) + exportação limpa para Excel/Google Sheets/ERP + um **Cockpit Executivo de CFO** em tempo real.
6. **Métricas de CFO na Ponta da Língua:**
   * Apresente o resultado como nos cases oficiais da Barte:
     * **Tempo de execução:** *De X horas/dias por mês para Y segundos*;
     * **Taxa de Automação:** *Ex: 94,8% resolvido sem toque humano*;
     * **Acurácia Auditada:** *Ex: 99,3% contra o gabarito*;
     * **Impacto em Caixa (R$):** *R$ X em divergências/inadimplência/duplicidades/juros evitados descobertos nos dados do case*.
7. **Repositório GitHub Impecável às 18h30:**
   * A seleção dos **3 finalistas** ocorre entre `18h30` e `19h00` (apenas 30 minutos para a banca avaliar todos os projetos enviados via GitHub!). Portanto, o `README.md` do nosso repositório `DesbravadoresBarte` precisa ser **visualmente escaneável em 60 segundos**, contendo: Resumo Executivo de CFO, Tabela de Resultados Encontrados nos Dados do Case, Diagrama de Arquitetura (Mermaid), Prints/GIFs da solução rodando e Instruções de 1 comando para rodar.
