# 🏦 01. PRODUTOS, INFRAESTRUTURA E ECOSSISTEMA BARTE (DEEP DIVE TÉCNICO E DE NEGÓCIO)

Este documento detalha todos os produtos de tecnologia financeira da **Barte** (`https://www.barte.com/`), como cada um funciona na prática, sua arquitetura técnica via API (`https://docs.barte.com/`) e **como a Inteligência Artificial é aplicada em cada camada do ecossistema**.

---

## 1. Visão Arquitetural do Ecossistema Barte

A Barte não é apenas um gateway de pagamentos nem apenas uma consultoria de IA: ela construiu uma **infraestrutura financeira modular completa para médias e grandes empresas (B2B / Mid-Market & Enterprise)** que conecta o dinheiro desde o momento em que o cliente final paga (**Adquirência/Pagamentos**) até a gestão do caixa (**Corporate Banking/Tesouraria**), a distribuição para parceiros (**White-Label/Multiadquirência**) e a automação completa do backoffice financeiro (**Barte AI Services / Finanças Autônomas**).

```
[Cliente Final / Comprador]
        │
        ▼ (Pix, Cartão até 24x, Boleto, Apple/Google Pay, Link, POS SyncPay, Tap-to-Pay)
┌───────────────────────────────────────────────────────────────────────────────┐
│ 1. BARTE PAGAMENTOS & MULTIADQUIRÊNCIA                                        │
│  • Orquestração Inteligente (Roteamento menor custo / maior aprovação até 98%)│
│  • Retentativa Automática Multi-Adquirente + Recuperação de Vendas com IA     │
│  • Antifraude Agêntico (+1.000 variáveis, 3DS 2.0, Parceria Oscilar + Master) │
│  • Barte SyncPay (TEF em nuvem sem fio + impressão NF-e na maquininha)        │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │ Liquidação / Split Multidirecional
                                        ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│ 2. BARTE CORPORATE BANKING & TESOURARIA (/banking)                            │
│  • Conta PJ Remunerada (até 105% do CDI com liquidez D+2)                     │
│  • Antecipação Inteligente sob Demanda (antecipa só o gap de caixa necessário)│
│  • Cartões Corporativos (limites até 20x maiores atrelados ao saldo/volume)   │
│  • Contas a Pagar em Lote (Pix, Boleto, TED) com Fluxo de Alçadas Multi-Perfil│
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │ Eventos via API / Webhooks v2 / Extratos
                                        ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│ 3. BARTE AI SERVICES — FINANÇAS AUTÔNOMAS (/ai-services)                      │
│  • Camada Agêntica conectada ao ERP do cliente (SAP, TOTVS, Omie, Conta Azul) │
│  • 6 Agentes Auditáveis: Compras, Contas a Pagar, Contas a Receber, Fiscal,   │
│    Conciliação em Cascata e Fechamento/FP&A (DRE + Board Pack em tempo real)  │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Vertical 1: Pagamentos, Orquestração e SyncPay (`barte.com` e `/syncpay`)

### 2.1. Meios de Pagamento e Conversão Comercial
* **Cartão de Crédito com Parcelamento Estendido:** Permite que o comprador parcele em **até 21x ou 24x**, enquanto o lojista recebe à vista (D+1/D+2) mediante antecipação configurável.
* **Pix e Boleto Inteligente:** Emissão instantânea de QR Codes Pix (estáticos e dinâmicos) e boletos registrados com configuração automática de **multa, juros de mora e descontos por antecipação**.
* **Carteiras Digitais e Métodos Alternativos:** Apple Pay, Google Pay, Cartão de Débito, Cartão Tokenizado (1-Click Buy) e +50 métodos alternativos.
* **Links de Pagamento (Pontuais e Recorrentes / Assinaturas):**
  * Criação sem código ou via API de links para cobrança avulsa ou planos de assinatura recorrente.
  * **Flexibilidade de Taxas:** Permite definir no link quem assume o custo da taxa de parcelamento (lojista ou comprador).
  * **Régua Automática Gratuita:** Disparo automático de lembretes de vencimento via **WhatsApp e E-mail**.
  * **Automação Fiscal Nativa:** Emissão automática da **Nota Fiscal (NF-e)** assim que o pagamento é confirmado.
* **Plugins Nativos de E-commerce:** Integração pronta para **VTEX, Shopify, WooCommerce, Magento e Uappi**.

### 2.2. Barte SyncPay (`/syncpay`) — O TEF Sem Fio 100% em Nuvem
* **O Problema que Resolve:** No varejo físico tradicional, o operador de caixa precisa digitar manualmente o valor da venda na maquininha (gerando erros de digitação, filas, fraudes de troca de valor e pesadelo na conciliação posterior) ou usar um TEF cabeado antigo e caro preso ao computador e a uma impressora fiscal térmica.
* **Como Funciona o SyncPay:**
  1. **Pedido no Sistema:** O vendedor registra a venda no ERP/PDV da loja e seleciona a maquininha desejada na tela.
  2. **Envio Automático via Nuvem:** A API da Barte envia o valor exato e os metadados do pedido para a maquininha POS via Wi-Fi/4G (sem cabos).
  3. **Pagamento pelo Cliente:** O cliente aproxima ou insere o cartão/Pix na maquininha sem que o caixa possa alterar o valor.
  4. **Impressão da NF-e na Própria Maquininha:** Após a aprovação, **a própria maquininha imprime o comprovante e a Nota Fiscal (NF-e/NFC-e)**, eliminando a necessidade de impressoras extras no balcão.
  5. **Conciliação Instantânea:** O status do pagamento volta via Webhook em tempo real para o PDV/ERP e fica conciliado automaticamente no portal da Barte com o `uuid` do pedido.

### 2.3. BarteToPay (`/tap-to-pay`)
* Transforma qualquer smartphone com antena NFC em um terminal de pagamento POS completo da Barte.
* Aceita cartões por aproximação, carteiras digitais (Apple/Google Pay) e QR Code Pix, parcelando em até 21x sem custo de aluguel de maquininha física.

### 2.4. Onde a IA Entra nos Pagamentos da Barte
1. **Orquestração e Roteamento Inteligente Multi-Adquirente:**
   * A Barte opera conectada a múltiplas adquirentes simultaneamente.
   * Para cada transação, o motor inteligente decide a rota ideal combinando **maior probabilidade de aprovação (chegando a até 98% de aprovação)** e **menor custo de MDR por bandeira/MCC**.
   * **Retentativa Inteligente (Smart Retry):** Se uma transação falha por instabilidade ou falso-positivo na Adquirente A, a Barte reprocessa automaticamente em milissegundos na Adquirente B antes de retornar resposta ao comprador, salvando vendas que seriam perdidas.
2. **Recuperação de Vendas e Carrinhos com IA (`/v2/charges/sales-recovery-ai`):**
   * Endpoint nativo na API da Barte que recebe o `uuid_charge` de uma cobrança recusada ou expirada e aciona agentes de IA para contatar o comprador no canal e momento ideais com alternativa de pagamento (ex: Pix ou novo link), recuperando receita automaticamente.
3. **Motor Antifraude Agêntico (Parceria Estratégica Barte + Oscilar + Mastercard):**
   * Avalia **+1.000 variáveis** por transação (comportamento de navegação, device fingerprinting, histórico, geolocalização, velocidade de compra), combinado com **3DS 2.0 (Step-Up dinâmico)**, **Pré-Captura** e **Alertas de Pré-Chargeback**.
   * A Barte implementou a plataforma **Oscilar AI Risk Decisioning** (integrada à inteligência de risco da Mastercard) para unificar em tempo real **Onboarding (KYB/KYC), Prevenção a Fraudes, Risco de Crédito e AML (Prevenção à Lavagem de Dinheiro)**.
   * Com a IA agêntica da Oscilar, o time de risco da Barte reduziu o tempo para criar, testar e publicar novas políticas antifraude e de crédito de **semanas para minutos**, sem depender de filas de engenharia.

---

## 3. Vertical 2: Corporate Banking & Tesouraria Inteligente (`/banking`)

A tese da Barte no Corporate Banking é eliminar a fragmentação entre "onde a empresa recebe suas vendas" e "onde ela guarda, rende e paga suas contas". Mais de **35% da base de clientes** já opera de forma integrada.

### 3.1. Funcionalidades Core
1. **Conta Corporativa com Rendimento Automático de até 105% do CDI:**
   * Os valores liquidados das vendas na adquirência Barte (ou transferidos para a conta) rendem automaticamente **até 105% do CDI** (superior aos bancos tradicionais que pagam zero sobre conta corrente ou exigem aplicação manual), com liquidez D+2.
2. **Cartões Corporativos de Alto Limite:**
   * Emissão de cartões físicos e virtuais para despesas da empresa (marketing digital, AWS/cloud, viagens, compras) com **limites até 20x superiores aos bancos tradicionais**, ajustados dinamicamente com base no fluxo de recebíveis e no saldo aplicado na Barte.
3. **Gestão de Contas a Pagar e Liquidação em Lote:**
   * Pagamento de fornecedores, impostos e utilidades via Pix, Boleto ou TED de forma unitária ou **em lote com poucos cliques**.
   * **Governança e Alçadas Multi-Perfil:** Configuração de permissões granulares (ex: o analista financeiro sobe o lote de pagamentos, o gerente revisa e o CFO aprova com 1 clique).
4. **Antecipação Inteligente de Recebíveis (Capital de Giro sem Depender de Banco):**
   * Conforme explicado nos artigos técnicos da Barte sobre *Capital de Giro* e *Fluxo de Caixa*, os bancos e adquirentes tradicionais empurram a "antecipação automática de 100% da agenda", corroendo de 2% a 4% da margem bruta da empresa mesmo nos dias em que ela já tem caixa sobrando.
   * Na Barte, a tesouraria cruza o **Contas a Pagar futuro** com a **Agenda de Recebíveis de Cartão** e permite antecipar **apenas a fração exata necessária para cobrir um descasamento de caixa pontual**, com liquidação garantida em **D+1** e taxas transparentes.
5. **Ecossistema Clube Barte & Casa Barte:**
   * Clientes do Corporate Banking e startups parceiras têm acesso ao **Clube Barte** (mais de 40 eventos exclusivos por ano na **Casa Barte** na Vila Madalena, conectando +250 C-Levels, além de programas de incentivo que oferecem até R$ 100.000 em rendimentos *equity-free* e matchmaking com fundos de Venture Capital).

---

## 4. Vertical 3: Adquirência como Serviço / Infraestrutura White-Label (`/adquirencia-como-servico`)

Voltada para **Marketplaces, Plataformas SaaS, ERPs verticais, Franqueadoras e Fintechs** que desejam embutir pagamentos e serviços financeiros (*Embedded Finance*) na sua própria oferta.

### 4.1. Recursos da Plataforma de Intermediadores
* **100% White-Label:** Maquininhas POS customizadas com a marca e cores do parceiro, Portal do Vendedor com logo e URL próprios, e fatura de cartão identificada.
* **Split de Pagamento Multidirecional:**
  * Permite dividir uma única venda entre N participantes (ex: Marketplace retém 12% de comissão + Seller A recebe 70% dos produtos + Transportadora recebe R$ 25 de frete + Afiliado recebe 3%), com regras distintas de retenção de taxa por recebedor.
* **Motor de Planos de Taxas (`Plano de Taxas API`):**
  * O intermediador define *tiers* comerciais para seus sellers (ex: Plano Bronze, Prata, Ouro), configurando o MDR e o spread de antecipação por bandeira (Visa, Mastercard, Elo, Amex, Hipercard), modalidade (débito, crédito à vista, parcelado 2–6x, 7–12x, 13–21x) e prazo de repasse (`D+1`, `D+2`, `D+15`, `D+30`).
* **Antecipação de Recebíveis para Sellers de Marketplace:**
  * Estruturação completa em conformidade com a **Resolução BCB nº 349/2023** (integração com registradoras de recebíveis e suporte a funding próprio ou via FIDC da Barte), evitando os 3 riscos clássicos de marketplaces (antecipar pedido antes da confirmação de entrega/chargeback, travar agenda em registradora errada e descasar taxa de captação vs. ponta).
* **Central de Disputas e Chargebacks Automatizada:**
  * Fluxo integrado via portal e Webhook para notificação de chargeback, coleta de documentos comprobatórios junto ao seller e geração/envio de cartas de contestação.

---

## 5. Vertical 4: Plataforma de Desenvolvedores e APIs (`https://docs.barte.com/`)

A documentação técnica da Barte é construída sobre uma arquitetura **AI-Ready** (com arquivo nativo `https://docs.barte.com/llms.txt` para leitura por agentes de IA e suporte a consultas semânticas via URL `?ask=<pergunta>&goal=<objetivo>`).

### 5.1. API de Pagamentos e Intermediadores (`api.barte.com`)
* **Ambientes:**
  * Produção: `https://api.barte.com`
  * Sandbox: `https://sandbox-api.barte.com`
* **Autenticação:** Header `X-Token-Api: <SEU_TOKEN_UUID>` sob TLS 1.2+.
* **Diferença Conceitual Importante na Arquitetura Barte:**
  * **`Order` (Pedido):** Representa a intenção comercial da venda (comprador, valor total, itens, regras de parcelamento, tentativas).
  * **`Charge` (Cobrança):** Representa cada cobrança/parcela financeira gerada a partir de um pedido (possui `uuid_charge`, data de vencimento, status de liquidação, estorno ou falha).
* **Principais Grupos de Endpoints:**
  * **Compradores (`Buyers`) & Cartões Tokenizados:** Criação, listagem e cofre de cartões (PCI-compliant).
  * **Pedidos (`Orders`) & Cobranças (`Charges`):** Criação de pedidos Pix, Boleto, Cartão (com suporte a **Pré-Captura** e autenticação **EMV 3DS 2.0**), estornos parciais/totais e simulação de aprovação em Sandbox.
  * **Links de Pagamento & Assinaturas (`Subscriptions`):** Criação de planos recorrentes e links únicos ou multi-uso.
  * **Recuperação de Vendas com IA:** `POST /v2/charges/sales-recovery-ai` (Envia `uuid_charge` e `company_name` para o agente de IA recuperar a venda).
  * **Gestão de Sellers e Financeiro do Intermediador:** Onboarding de vendedores, configuração de conta de payout, bloqueio de saque/lojista, consulta de **Extrato Financeiro** (`GET` com `uuid` de transação), listagem de transferências, detalhamento de lançamentos de repasse, consulta de **Saldo Disponível** e **Recebíveis Futuros (Agenda)**, e criação/atualização de **Planos de Taxas**.
  * **Terminais Físicos (POS / SyncPay):** Vinculação/desvinculação de maquininha ao seller e envio de pedidos físicos (`PHYSICAL_ORDER`).
* **Webhooks v2 (Envelope Versionado com HMAC-SHA256):**
  * A Barte dispara eventos em tempo real assinados criptograficamente via **HMAC-SHA256** para garantir integridade e autenticidade nos domínios: `ORDER`, `CHARGE`, `SUBSCRIPTION`, `PHYSICAL_ORDER` e `DISPUTE`.

### 5.2. API de Corporate Banking (`api-banking.barte.com`)
* **Ambientes:**
  * Produção: `https://api-banking.barte.com`
  * Sandbox: `https://sandbox-api-banking.barte.com`
* **Autenticação de Alta Segurança (Dupla Camada):**
  1. **mTLS (Mutual TLS):** Certificado digital `.pem` e chave privada `.key` do parceiro na conexão TLS.
  2. **OAuth 2.0 Client Credentials:** Chamada em `POST /auth/token` com `client_id` e `client_secret` retornando o JWT `Bearer {access_token}`.
  * Headers obrigatórios nas chamadas: `Authorization: Bearer {token}`, `X-Request-Id: {uuid_v4}` (rastreabilidade/idempotência) e `X-Seller-Id`.
* **Principais Escopos:**
  * Abertura e gestão de Contas PJ v2 (`Business Accounts v2`) e validação por Sessões Biométricas (`Biometric Sessions`).
  * Consulta de Limites da Conta e Saldo em tempo real.
  * Transferências PIX Cash-Out (`pix-transfers`) e geração/leitura de PIX QR Code.
  * Webhooks bancários v1 e v2 para conciliação instantânea de entradas e saídas.
