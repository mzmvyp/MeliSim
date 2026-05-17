# Prompt para Claude Design — MeliSim UI completa

Cole este arquivo inteiro na primeira mensagem do **Claude Design** (Design tab em claude.ai). Ele aceita conversa iterativa: depois desta mensagem inicial você pode pedir refinamentos por tela ("ajusta o card do produto: aumenta o espaçamento", "muda a paleta para um tom mais quente", etc.). No fim de cada conversa exporte para HTML/PDF/PPTX/Canva.

> **Como usar este prompt:**
> 1. Cole tudo na primeira mensagem do Claude Design.
> 2. Espere ele gerar o **design system + screen list**.
> 3. Em mensagens seguintes, peça uma tela por vez: *"agora gera a tela de **product detail** com base nessa especificação"*.
> 4. Refine inline (Claude Design tem comentários e sliders).
> 5. Exporte para Canva quando estiver pronto, ou pegue o HTML para integrar.

---

## ⬇️ Início do prompt — copie a partir daqui

---

# Construa a UI completa do **MeliSim**

Você é um designer/engenheiro full-stack sênior. Vou te dar contexto, design system e o catálogo completo de telas a entregar. Trabalhe em **HTML semântico + Tailwind CSS** (mobile-first), com componentes reutilizáveis. Use **dados realistas** (sem `lorem ipsum`) e cubra os 4 estados (loading / empty / success / error) em toda tela com lista ou form.

## 1. Contexto do produto

**MeliSim** é um marketplace simulado nos moldes do Mercado Livre, com 8 microserviços (Python/Java/Kotlin/Go) atrás de um API gateway. A UI consome endpoints REST e precisa cobrir três personas:

- **Buyer (comprador)** — busca, vê produto, compra, paga, acompanha pedido.
- **Seller (vendedor)** — gerencia catálogo, vê vendas, recebe alertas de estoque baixo.
- **Admin/SRE** — observa saúde do sistema, métricas Prometheus, traces Jaeger, DLQs Kafka, outbox.

A inspiração visual é o **Mercado Livre** (não copiar logo nem assets — referência de hierarquia, densidade de informação e paleta).

## 2. Design system — gere primeiro

Comece criando uma página `00-design-system.html` com:

### 2.1 Paleta

```
Primary (yellow ML):    #FFE600
Primary contrast:       #2D3277  (azul escuro ML — usado em CTAs e navegação)
Surface:                #FFFFFF
Surface alt:            #F5F5F5  (background da grid de produtos)
Border:                 #E5E5E5
Text primary:           #333333
Text secondary:         #666666
Text muted:             #999999
Success:                #00A650  (verde ML do "frete grátis")
Warning:                #F2A900
Danger:                 #E62B2B
Info:                   #3483FA  (azul link ML)
```

Inclua versões de **dark mode** (toggle no header) com surface `#1A1A1A`, text `#E5E5E5`.

### 2.2 Tipografia

- Família: `'Proxima Nova', 'Inter', system-ui, sans-serif`
- Escala: `12 / 14 / 16 / 18 / 20 / 24 / 32 / 48` px
- Peso: 400 / 500 / 600 / 700
- Preço grande: 32px, weight 300 (estilo ML)
- Número de parcelas: 14px, secondary color

### 2.3 Espaçamento e raio

- Spacing scale: `4 / 8 / 12 / 16 / 24 / 32 / 48 / 64`
- Border radius: `4` (cards), `6` (botões), `8` (modais), `999` (chips)
- Sombras: leve em cards (`0 1px 2px rgba(0,0,0,0.08)`), elevada em dropdowns/modais.

### 2.4 Componentes-base (mostrar todos os estados)

- **Botões**: primary (yellow + dark text), secondary (outline azul), ghost, danger, link. Tamanhos sm/md/lg. Estados: default/hover/active/disabled/loading.
- **Inputs**: text, email, password, number, search (com ícone lupa), textarea, select. Com label flutuante e mensagem de erro abaixo.
- **Cards**: produto (com badge "frete grátis"), info, métrica (ver §5.4).
- **Badges/Chips**: status do pedido (`CREATED`, `PAYMENT_PENDING`, `PAID`, `SHIPPED`, `DELIVERED`, `CANCELLED`), categoria, "novo", "promo".
- **Tabela**: zebrada, header sticky, ordenação por coluna, paginação rodapé.
- **Modal**: overlay 60% black, fechar via ESC + backdrop click.
- **Toast**: top-right, 4 tipos (success/error/warning/info), auto-dismiss 4s.
- **Skeleton loaders**: para card de produto, linha de tabela, métrica.
- **Empty state**: ícone + título + descrição + CTA.
- **Breadcrumb**: separador `>`, último item sem link.
- **Pagination**: numérica + prev/next, mobile colapsa para "1 / 12".
- **Sidebar nav**: colapsável, ícones + texto, indicador de ativo (barra lateral amarela).

## 3. Layout global

### 3.1 Header (público + autenticado)

- Linha 1 (apenas mobile some): logo MeliSim + barra de busca **gigante** (50% da largura) com select de categoria embutido + ícones de carrinho/notificações/usuário à direita.
- Linha 2: chips de categorias rápidas ("Eletrônicos", "Computadores", "Casa", "Moda", "Esportes"...).
- Sticky no scroll, sombra ao descer.

### 3.2 Footer

- 4 colunas: "Sobre", "Comprar", "Vender", "Suporte" + linha inferior com idioma/região + selo de pagamentos.

### 3.3 Sidebar (área autenticada — buyer/seller/admin)

- Larga 240px desktop, off-canvas no mobile.
- Avatar do usuário no topo + role badge.
- Menu por persona (ver §4 / §5 / §6).

## 4. Telas — Buyer (comprador)

> Para cada tela: forneça desktop (1440px) + tablet (768px) + mobile (375px).

### 4.1 `/` — Home (pública)

- Hero rotativo com 3 banners (promoções).
- Grid 4 colunas: "Mais vendidos" (8 produtos), "Ofertas do dia" (8), "Eletrônicos" (4 + ver mais), "Recomendados pra você" (4).
- Cada **card de produto**: imagem 200×200, título 2 linhas, preço grande + parcelas ("12x R$ 99,90 sem juros"), badge "FRETE GRÁTIS" verde se aplicável, estrelas + nº de avaliações, ícone coração (favoritar).

### 4.2 `/login` e `/register`

- Layout split: 60% imagem ilustrativa (lifestyle de compra), 40% formulário centralizado.
- Login: email + senha + checkbox "lembrar de mim" + link "esqueci senha" + botão amarelo + "criar conta" embaixo + login social (Google/Facebook desenhados, sem implementar).
- Register: nome / email / senha (com indicador de força) / confirmar senha / radio Buyer ⟷ Seller / aceite de termos + botão.

### 4.3 `/products?q=...` — Resultado de busca

- Layout em 2 colunas: filtros à esquerda (sticky, 280px), grid à direita.
- Filtros: faixa de preço (slider duplo), categoria (checkbox), condição (novo/usado), avaliação mínima, frete grátis (toggle).
- Header da grid: "X resultados para 'iphone'" + ordenação (Mais relevantes / Menor preço / Maior preço / Mais recentes) + view toggle (grid / lista).
- Cada card igual ao da home + botão "Adicionar ao carrinho" hover.
- Paginação no rodapé.
- **Empty state**: "Não encontramos resultados para 'X' — tente ajustar os filtros".

### 4.4 `/products/{id}` — Detalhe do produto

- Layout 3 colunas: galeria (40%) + info (35%) + box de compra (25%).
- Galeria: imagem grande + 5 thumbnails verticais + zoom on hover.
- Info: breadcrumb categoria > sub > produto, título 24px, vendedor com selo "MercadoLíder Platinum", avaliação + nº de reviews, descrição rica (markdown), tabs "Descrição / Características / Avaliações".
- Box de compra: preço gigante, parcelamento, "estoque: 15 disponíveis" verde / "últimas 2 unidades!" laranja, seletor de quantidade, botão "Comprar agora" amarelo, botão "Adicionar ao carrinho" outline, calculadora de frete (CEP), "Devolução grátis" + "Compra garantida" + "Mercado Pago" badges.

### 4.5 `/cart` — Carrinho

- Tabela: imagem + título + preço unitário + qty (stepper) + subtotal + remover (X).
- Resumo lateral: subtotal / frete (com link "calcular") / cupom (campo) / total / botão "Finalizar compra" amarelo grande.
- **Empty**: "Seu carrinho está vazio" + ilustração + CTA "Continuar comprando".

### 4.6 `/checkout` — Stepper de checkout (3 passos)

1. **Endereço de entrega** (form: CEP + busca, rua, número, complemento, bairro, cidade/UF).
2. **Pagamento**: tabs Pix / Cartão de crédito / Boleto.
   - Pix: QR code dummy + chave copy.
   - Cartão: número, nome, validade, CVV (Bandeira detectada), parcelas dropdown.
   - Boleto: aviso de prazo.
   - **Campo `Idempotency-Key`** gerado automático e exibido em ícone "?" no canto (educacional).
3. **Revisão**: resumo do pedido + endereço + pagamento + termos + botão "Confirmar compra".
- Top: stepper visual com 3 bolinhas conectadas.

### 4.7 `/payment/processing` — Tela de espera (2-3s)

- Spinner + "Processando seu pagamento, não feche esta página" + barra de progresso indeterminada + ícone de cadeado "conexão segura".
- Após resposta: redirect para `/orders/{id}/success` ou `/orders/{id}/failed`.

### 4.8 `/orders/{id}/success` e `/failed`

- Success: ícone check verde grande, número do pedido, "previsão de entrega: terça-feira", botão "Ver pedido" + "Continuar comprando".
- Failed: ícone X vermelho, motivo (cartão recusado / saldo insuficiente / expirado), botão "Tentar outro pagamento".

### 4.9 `/orders` — Meus pedidos

- Lista vertical com card por pedido: imagem do produto + título + total + status badge + data + botão "Detalhes".
- Filtros topo: "Todos / Pagos / A caminho / Entregues / Cancelados".
- Search por nº de pedido.

### 4.10 `/orders/{id}` — Detalhe do pedido (com timeline)

- Header: nº do pedido + status + data.
- **Timeline horizontal** (5 etapas): Pedido criado → Pagamento confirmado → Enviado → Em rota → Entregue. Etapa atual highlight + data abaixo de cada step.
- Box do produto + endereço + pagamento + nota fiscal (link).
- Ações contextuais: "Cancelar" (se PAID/CREATED), "Marcar como recebido" (se SHIPPED), "Comprar de novo".

### 4.11 `/notifications` — Histórico de notificações

- Lista vertical estilo timeline:
  - Ícone (categoria: order / payment / shipping / stock / generic) + título + descrição + data relativa ("há 3 horas").
  - Não-lidas com fundo amarelo bem leve.
- Filtros: "Todas / Pedidos / Pagamentos / Estoque".

### 4.12 `/profile` — Perfil do usuário

- Tabs: Dados pessoais / Endereços / Cartões salvos / Segurança (mudar senha + 2FA).
- Form de dados pessoais com avatar upload.

## 5. Telas — Seller (vendedor)

Sidebar: Dashboard / Produtos / Vendas / Estoque / Mensagens / Configurações.

### 5.1 `/seller/dashboard`

- 4 **cards de métrica** no topo: vendas hoje (R$), vendas mês, pedidos pendentes, produtos com estoque baixo. Cada card com seta ↑↓ vs período anterior + sparkline.
- Gráfico grande: vendas últimos 30 dias (linha).
- Lista: top 5 produtos do mês.
- Lista: últimos 10 pedidos com ação rápida "Marcar como enviado".

### 5.2 `/seller/products`

- Tabela com: thumb + título + preço + estoque (com alerta vermelho se < 10) + categoria + status (ativo/pausado) + ações (editar, pausar, deletar).
- Botão "+ Novo produto" amarelo no topo.
- Filtros: categoria, status, faixa de estoque.

### 5.3 `/seller/products/new` e `/seller/products/{id}/edit`

- Form em 2 colunas:
  - Esquerda: título, descrição (rich text), categoria, marca, condição, preço, estoque, SKU.
  - Direita: upload de imagens (drag-n-drop, até 6, primeira é capa), preview.
- Sticky bar com botão "Salvar" + "Salvar e publicar" + cancelar.

### 5.4 `/seller/sales`

- Tabela vertical de pedidos recebidos com status filtrável.
- Click no pedido abre drawer lateral com detalhes + ação "Despachar".

### 5.5 `/seller/inventory` — Estoque + alertas

- Tabela: produto / estoque atual / threshold (10) / status / data do último alerta / botão "Repor".
- Conecta ao tópico Kafka `stock-alert` — mostre **toast** quando chega alerta novo (real-time feel).

## 6. Telas — Admin / SRE (observabilidade do sistema)

Esta é a parte que **mais valor agrega** e que diferencia o portfolio. Sidebar: Overview / Services / Traces / Logs / Outbox / DLQ / Kafka / Settings.

### 6.1 `/admin/overview`

Layout estilo "single pane of glass":

- Faixa superior: **8 service tiles** (api-gateway, users, products, orders, payments, notifications, search, stock-monitor). Cada tile com:
  - Nome + linguagem + porta
  - Status dot (verde UP / amarelo DEGRADED / vermelho DOWN)
  - p95 latency atual + sparkline 1h
  - RPS atual
- 4 cards de KPI globais: requests/min total, error rate %, Kafka events/sec, outbox PENDING count.
- Mapa de dependências (force-directed graph com 8 nós e setas direcionais). Setas vermelhas se a chamada está degradada.
- Faixa inferior: timeline de incidentes/deploys (últimas 24h).

### 6.2 `/admin/services/{name}`

- Página de detalhe de um serviço:
  - Header: nome + status + uptime + versão.
  - Aba **Metrics**: 4 gráficos (RPS, p50/p95/p99 latency, error rate, CPU/Mem). Eixo Y com unidades. Tooltip hover mostra valor exato.
  - Aba **Traces**: lista de últimos 50 traces, ordenável por duração. Cada linha colapsa para mostrar a árvore de spans (waterfall) ao clicar.
  - Aba **Logs**: live tail estilo terminal (fundo `#1A1A1A`, texto colorido por nível). Filtro por `request_id`, level, busca livre.
  - Aba **Config**: env vars (mascara secrets), feature flags.

### 6.3 `/admin/traces` — Distributed tracing

Inspirado no Jaeger UI mas mais limpo:

- Search bar: service / operation / tags / `request_id`.
- Lista de traces (cada linha: duração + nº de spans + serviço root + timestamp).
- Click → **waterfall view** com spans coloridos por serviço, indentação por hierarquia, hover mostra atributos do span (incluindo `request_id`).

### 6.4 `/admin/outbox` — Monitor da Outbox table

- 3 cards no topo: PENDING / SENT / FAILED counts.
- Gráfico: drain duration p95 last 1h + outbox depth over time.
- Tabela: id / aggregate_type / event_type / topic / status / attempts / created_at / sent_at / last_error.
- Filtro por status. Botão "Replay" em rows FAILED (modal de confirmação).

### 6.5 `/admin/dlq` — DLQ inspector

- Lista de tópicos DLQ (`order-created.dlq`, `payment-confirmed.dlq`, etc.) com counter de mensagens.
- Click no tópico → tabela de mensagens DLQ com envelope (original_topic, partition, offset, error_type, failed_at).
- Click numa mensagem → drawer com `original_value` (JSON pretty-printed) + stack trace + botões "Replay original" e "Discard".

### 6.6 `/admin/kafka`

- Lista de tópicos com: partições, replicação, msgs/sec produzidas, msgs/sec consumidas, consumer lag por grupo (barra colorida — verde ok / amarelo > 1k / vermelho > 10k).
- Click em consumer group → membros + partition assignment + offset por partição.

### 6.7 `/admin/dashboards/system` — Embedded Grafana view

- Mosaico com os 5 painéis principais (RPS, p95 latency, availability, Kafka events, outbox state) em cards. Botão "Open in Grafana" no canto.

## 7. Mock data realista

Use estes dados (sem lorem ipsum):

### 7.1 Produtos (15 mínimo)

```
1. iPhone 15 Pro 256GB Titânio Natural — R$ 8.999,00 — eletrônicos — estoque 25
2. Samsung Galaxy S24 Ultra 512GB — R$ 6.499,00 — eletrônicos — estoque 15
3. MacBook Air M3 13" 8GB/256GB — R$ 9.999,00 — computadores — estoque 8
4. Sony WH-1000XM5 Headphone Bluetooth — R$ 2.499,00 — áudio — estoque 42
5. PlayStation 5 Slim 1TB — R$ 4.299,00 — games — estoque 12
6. Air Fryer Mondial 4L — R$ 349,00 — casa — estoque 60
7. Tênis Nike Air Max 90 Preto — R$ 599,00 — moda — estoque 30
8. Smart TV LG OLED 55" 4K — R$ 5.499,00 — eletrônicos — estoque 6
9. Cadeira Gamer DXRacer Air — R$ 2.799,00 — escritório — estoque 4 (estoque baixo!)
10. Kindle Paperwhite 11ª geração — R$ 549,00 — livros — estoque 88
11. Apple Watch Series 9 GPS 45mm — R$ 4.299,00 — eletrônicos — estoque 17
12. iRobot Roomba i3+ — R$ 3.299,00 — casa — estoque 22
13. Bicicleta Caloi Elite Carbon Sport — R$ 12.500,00 — esportes — estoque 3 (estoque baixo!)
14. Cafeteira Nespresso Vertuo Plus — R$ 999,00 — casa — estoque 35
15. Câmera Canon EOS R8 — R$ 14.999,00 — fotografia — estoque 5 (estoque baixo!)
```

### 7.2 Usuários

- Buyer: "Bob Ferreira" — bob@melisim.test — São Paulo/SP
- Seller: "Alice Comércio" — alice@melisim.test — selo MercadoLíder Platinum desde 2023, 4.8★ com 12.450 avaliações
- Admin: "Carlos SRE" — admin@melisim.test

### 7.3 Pedidos exemplo

```
#84129 — iPhone 15 Pro — qty 1 — R$ 8.999,00 — PAID — pago 2026-04-23 — chega 26/04
#84130 — Sony WH-1000XM5 — qty 2 — R$ 4.998,00 — SHIPPED — saiu de SP, em CWB
#84131 — Cadeira DXRacer — qty 1 — R$ 2.799,00 — DELIVERED — 18/04
#84132 — Air Fryer Mondial — qty 1 — R$ 349,00 — PAYMENT_PENDING — aguardando pix
#84133 — Bicicleta Caloi — qty 1 — R$ 12.500,00 — CANCELLED — falha pgto
```

### 7.4 Métricas para dashboards admin (valores realistas)

- api-gateway: 142 RPS, p95 87ms
- users-service: 12 RPS, p95 45ms
- products-service: 380 RPS, p95 23ms (tem cache)
- orders-service: 8 RPS, p95 156ms
- payments-service: 6 RPS, p95 2.1s (simula gateway externo)
- notifications-service: consume 14 events/sec
- search-service: 65 RPS, p95 38ms
- stock-monitor: 1 tick/min

## 8. Estados obrigatórios em toda tela

Sempre mostre os 4 estados:

1. **Loading** — skeletons (não spinners no body, exceto em botões).
2. **Empty** — ilustração + título + descrição + CTA.
3. **Success** — conteúdo populado.
4. **Error** — banner vermelho com `Tentar novamente` + ícone de detalhe expansível.

## 9. Responsividade

Mobile-first. Breakpoints: `sm 640 / md 768 / lg 1024 / xl 1280 / 2xl 1536`. Em mobile:

- Sidebar vira off-canvas (hamburger).
- Header colapsa: lupa vira ícone que abre overlay full-screen.
- Tabela admin vira lista de cards em mobile (cada linha um card).
- Cart usa accordion.
- Checkout stepper vira vertical.

## 10. Acessibilidade

- Contraste WCAG AA (especialmente importante no CTA amarelo: usar texto azul escuro `#2D3277`, NÃO branco).
- Focus visível em todos os interativos (anel azul 2px).
- `aria-label` em ícones-only.
- Form errors anunciados com `aria-live`.
- Navegação por teclado funciona em modais (trap focus + ESC fecha).

## 11. Microinterações

- Hover em card de produto: levanta 2px + sombra mais intensa + revela botão "Adicionar".
- Botão primary: brightness leve + escala 0.98 no active.
- Toast slide-in da direita.
- Skeleton com shimmer animado.
- Number ticker animado nos cards de KPI do admin.

## 12. Entregáveis

Estruture o Claude Design assim:

1. Página `00-design-system.html` (paleta, tipografia, componentes).
2. Páginas numeradas por fluxo:
   - `10-buyer-home.html`, `11-buyer-search.html`, `12-buyer-product.html`, ... `19-buyer-profile.html`
   - `20-seller-dashboard.html`, `21-seller-products.html`, ... `25-seller-inventory.html`
   - `30-admin-overview.html`, `31-admin-service-detail.html`, `32-admin-traces.html`, ... `36-admin-kafka.html`
3. Um `index.html` com galeria de **todas** as páginas (thumbnails + nome + persona).
4. Uma `flows.html` mostrando o user journey buyer (home → busca → produto → carrinho → checkout → pagamento → tracking).

## 13. Tom e branding

- Profissional mas amigável (não corporativo seco).
- Português brasileiro nos copies.
- Use o nome **MeliSim** (não Mercado Livre).
- Logo: "MeliSim" texto + ícone de carrinho estilizado em amarelo. Não copie o logo do ML.

## 14. O que NÃO fazer

- Não use lorem ipsum (use os mock data acima).
- Não copie identidade visual de marca real além de inspiração de layout.
- Não use Bootstrap (Tailwind only).
- Não use ícones genéricos cinza — prefira lucide ou heroicons consistentes.
- Não use sombras pesadas ou gradientes 2010 — visual flat moderno.

---

**Comece gerando a página `00-design-system.html` completa.** Em seguida me liste todas as 30+ páginas que você vai produzir, agrupadas por persona, e aguarde meu OK para começar a primeira tela buyer (`10-buyer-home.html`).

---

## ⬆️ Fim do prompt

---

# Como iterar depois (mensagens-modelo para colar nas próximas conversas)

```
Agora gere `12-buyer-product.html` (detalhe do produto) seguindo a especificação 4.4.
Use o produto mock #1 (iPhone 15 Pro). Mostre o estado "estoque baixo" — apenas
3 unidades. Inclua a tab de avaliações com 5 reviews mock realistas.
```

```
Refine a `30-admin-overview.html`: deixa o mapa de dependências mais limpo,
nós com bordas arredondadas, e adiciona um indicador de delay médio (em ms)
em cada aresta entre serviços.
```

```
Para mobile, transforma a tabela de `21-seller-products.html` em lista de
cards expansíveis. Mantém as ações (editar/pausar/deletar) acessíveis num
menu kebab à direita de cada card.
```

```
Aplica dark mode em TODAS as telas geradas até agora. Mantém a paleta
amarela ML como destaque mas inverte os neutros. Gera uma versão
side-by-side em `theme-comparison.html` para eu validar.
```

```
Exporta `30-admin-overview.html` para Canva — quero apresentar isso
como slide na entrevista técnica.
```

# Dicas para a conversa com o Claude Design

- **Use sliders inline** (feature dele) para ajustar densidade, tamanhos de fonte e raio de borda em vez de pedir refinamento por texto.
- **Use comentários inline** para apontar exatamente que componente refinar — funciona como o Figma.
- **Peça uma tela por vez** depois do design system. Misturar pedidos atrapalha o output.
- Se a primeira saída ficar genérica, **mostre uma screenshot de referência** do ML real ("queria que o card de produto tivesse essa hierarquia de informação"). Claude Design aceita imagens.
- Ao final, peça **export como zip** para integrar no projeto, ou **send to Canva** para apresentar.

# O que fazer com o output

1. **Para portfolio/entrevista**: exporta tudo em PDF + PPTX. Slides ficam prontos.
2. **Para implementar de verdade**: pega o HTML/Tailwind e converte para componentes React/Vue/Svelte. Como o Claude Design já entende design systems via codebase, você pode jogar o HTML dele de volta no Claude Code e pedir para virar componentes Next.js consumindo a API real do MeliSim.
3. **Para Grafana real**: as telas `30-admin-*` viram referência visual. O Grafana já está na stack (porta 3000) — use as telas como wireframe pra construir dashboards equivalentes em Grafana JSON.
