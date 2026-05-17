# MeliSim Design System

## Overview

**MeliSim** is a portfolio project by [@mzmvyp](https://github.com/mzmvyp) that simulates the Mercado Livre (MeLi) e-commerce ecosystem as a polyglot, event-driven microservices playground. It is not a real product — it's a demonstration of distributed systems engineering patterns built across 8 services in 4 languages.

**Source:** https://github.com/mzmvyp/MeliSim

### Products / Surfaces

| Surface | Description |
|---|---|
| **Marketplace UI** (simulated) | A frontend that doesn't exist yet — this design system imagines what it would look like, inspired by Mercado Livre's brand |
| **API Gateway / Swagger** | Developer-facing API docs at `/docs` (FastAPI auto-generated) |
| **Grafana Dashboard** | Observability UI: "MeliSim overview" — dark theme, Prometheus-backed metrics |
| **Email Notifications** | Transactional HTML emails for order/payment events |

### Services

- `api-gateway` — Python/FastAPI, JWT, rate-limit, reverse proxy
- `users-service` — Java/Spring Boot, MySQL, JWT issuer
- `products-service` — Go/chi, Postgres + Redis + Kafka
- `orders-service` — Kotlin/Spring Boot, Transactional Outbox, Resilience4j
- `payments-service` — Python/FastAPI, idempotency, Kafka
- `notifications-service` — Python/FastAPI, multi-topic Kafka consumer, HTML emails
- `search-service` — Python/FastAPI, Elasticsearch
- `stock-monitor` — Go, scheduled stock alerts

---

## CONTENT FUNDAMENTALS

### Tone & Voice
- **Technical and direct.** MeliSim speaks like a senior engineer writing documentation — precise, no fluff.
- **Third person for the system** ("MeliSim", "the service", "the gateway"); **second person for users** ("You can", "Your order").
- **No filler marketing language.** Features are described by what they do, not how amazing they are.
- **Portuguese currency (R$)** — the simulated market is Brazil. Currency amounts use `R$ 0.00` format.
- **Emoji: none** in technical docs or system UI. Email templates can use sparingly (none currently do).
- **Casing:** Sentence case for headings; Title Case for proper names (Kafka, Redis, Elasticsearch, Grafana).
- **Code identifiers** are always in backticks: `order-created`, `Idempotency-Key`, `OutboxStatus`.

### Examples
- ✅ "Your payment for order #1234 has been confirmed. Amount: R$ 99.90 via credit card."
- ✅ "We received your order #5678. We'll notify you once payment is confirmed."
- ❌ "🎉 Amazing! Your order is on its way!"
- ✅ "Circuit breaker opens after 50% failure rate in a 20-call window."

---

## VISUAL FOUNDATIONS

### Colors
Inspired by Mercado Livre's iconic yellow/blue palette.

- **Primary yellow:** `#FFE600` — hero CTAs, highlights, brand moments
- **Primary blue (dark):** `#2D3277` — headers, nav, primary text on light bg
- **Link/action blue:** `#3483FA` — links, interactive elements
- **Success green:** `#00A650` — confirmed states, availability
- **Error red:** `#F23D4F` — errors, failures, payment failed
- **Neutral dark:** `#333333` — body text
- **Neutral mid:** `#666666` — secondary text, metadata
- **Neutral light:** `#EBEBEB` — page backgrounds, dividers
- **Surface white:** `#FFFFFF` — card surfaces

### Typography
- **Display / Headings:** "Nunito Sans" (Google Fonts substitute for Proxima Nova — see font note below)
- **Body:** "Nunito Sans" — clean, geometric, highly legible
- **Mono / Code:** "JetBrains Mono" — for API endpoints, code snippets, IDs
- Scale: 12px base → 14px body → 16px large body → 20px h4 → 24px h3 → 32px h2 → 48px h1

**⚠️ Font substitution:** The real Mercado Livre uses a licensed version of Proxima Nova. This design system substitutes **Nunito Sans** from Google Fonts as the closest free match. If you have access to Proxima Nova, drop the `.woff2` files into `fonts/` and update `colors_and_type.css`.

### Spacing
- Base unit: `4px`
- Scale: 4, 8, 12, 16, 24, 32, 48, 64, 96px
- Component padding: typically `12px 16px` for compact, `16px 24px` for comfortable

### Backgrounds
- Page bg: `#EBEBEB` (light neutral gray — classic MeLi)
- Card bg: `#FFFFFF` with subtle shadow
- Hero sections: `#FFE600` (yellow) or `#2D3277` (deep blue)
- No gradients on primary surfaces; very flat, clean aesthetic
- Dark mode (Grafana dashboard): `#111217` bg, `#1F2028` panels

### Cards
- Background: white
- Border: none (shadow instead)
- Border radius: `4px` (very subtle — MeLi is quite square)
- Shadow: `0 1px 4px rgba(0,0,0,0.12)`
- Hover shadow: `0 4px 12px rgba(0,0,0,0.16)`

### Borders & Radius
- Corner radius: `4px` (cards, inputs, buttons) — tight, not pill-shaped
- Inputs: `1px solid #EBEBEB` border, `4px` radius
- Dividers: `1px solid #EBEBEB`

### Animation
- Minimal. Fast transitions only: `150ms ease` for hover states.
- No bounces, springs, or dramatic entrances.
- Button hover: slight shadow increase + cursor change.
- No skeleton loaders shown (simplified), but they exist in real MeLi.

### Hover / Press States
- Buttons: yellow → `#F0D900` (slightly darker yellow) on hover
- Links: color stays, underline appears
- Cards: shadow deepens on hover
- Press: `scale(0.98)` + slightly darker

### Iconography
See ICONOGRAPHY section below.

### Imagery
- Product photos: square crops, white background
- No stock photography for UI chrome
- Illustration style: flat, geometric, minimal — no hand-drawn

### Layout
- Max content width: `1200px`, centered
- Sidebar nav: `240px` fixed (desktop)
- Grid: 12-column with `24px` gutters
- Mobile: single column, `16px` horizontal padding

---

## ICONOGRAPHY

MeliSim has no custom icon set. In the UI kit, **Lucide Icons** (CDN) is used as the primary icon library — it's a clean, 1.5px stroke-weight line icon set that fits the flat/clean aesthetic of Mercado Livre.

```html
<script src="https://unpkg.com/lucide@latest/dist/umd/lucide.min.js"></script>
```

Usage: `<i data-lucide="shopping-cart"></i>` then `lucide.createIcons()`.

- No emoji used as icons anywhere in the UI
- No unicode chars used as icons
- SVG icons are inline in components where needed for custom shapes (logo)
- The MeliSim wordmark/logo is created as inline SVG in the UI kit

---

## File Index

```
melisim-design-system/
├── README.md                    ← You are here
├── SKILL.md                     ← Agent skill definition
├── colors_and_type.css          ← CSS custom properties: colors, type, spacing
├── assets/
│   └── logo.svg                 ← MeliSim wordmark (inline SVG)
├── fonts/                       ← (empty — using Google Fonts CDN)
├── preview/                     ← Design System tab cards
│   ├── colors-brand.html
│   ├── colors-semantic.html
│   ├── colors-status.html
│   ├── type-scale.html
│   ├── type-specimens.html
│   ├── spacing-tokens.html
│   ├── elevation-shadows.html
│   ├── components-buttons.html
│   ├── components-inputs.html
│   ├── components-cards.html
│   ├── components-badges.html
│   └── components-nav.html
└── ui_kits/
    └── app/
        ├── README.md
        ├── index.html           ← Interactive prototype (marketplace)
        ├── Header.jsx
        ├── ProductCard.jsx
        ├── SearchBar.jsx
        ├── OrderFlow.jsx
        └── Sidebar.jsx
```
