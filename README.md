# MediConnect RAG — AI Knowledge & Compliance Platform

<div align="center">

![LightRAG](https://img.shields.io/badge/LightRAG-1.4.6-FF6B35)
![Prometheus](https://img.shields.io/badge/Prometheus-v2.53-E6522C?logo=prometheus&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-10.2-F46800?logo=grafana&logoColor=white)
![Authelia](https://img.shields.io/badge/Authelia-2FA-1ABC9C)
![HIPAA](https://img.shields.io/badge/HIPAA-Scanning-22C55E)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

**MediConnect's dedicated RAG, monitoring, security scanning, and compliance platform.**
**Powers the AI chatbot with graph-based knowledge retrieval and enterprise observability.**

</div>

---

## Purpose

This platform serves two functions for MediConnect:

1. **AI Knowledge Engine** — LightRAG provides graph-based retrieval for the patient chatbot (medical FAQs, doctor articles, subscription info, codebase intelligence)
2. **Security & Compliance** — Scanning tools verify MediConnect's HIPAA, GDPR, SOC 2, and FHIR compliance

## Architecture

```
                    ┌──────────────────────────────────────────────────┐
                    │             MediConnect Services                  │
                    │  (communication-service calls LightRAG API)      │
                    └────────────────────┬─────────────────────────────┘
                                        │ POST /query
                    ┌───────────────────┐│
                    │   Nginx           ││  TLS termination
                    │   Rate limiting   ├┘  Security headers
                    │   Forward-auth    │   HSTS, CSP, X-Frame
                    └──┬────┬────┬────┬─┘
                       │    │    │    │
            ┌──────────┘    │    │    └──────────┐
            ▼               ▼    ▼               ▼
     ┌──────────┐   ┌──────────┐ ┌──────────┐ ┌──────────┐
     │ Authelia  │   │ LightRAG │ │ Grafana  │ │  Jaeger  │
     │   2FA     │   │  + RAG-  │ │Dashboard │ │ Tracing  │
     │  TOTP     │   │ Anything │ │          │ │  OTEL    │
     └──────────┘   └────┬─────┘ └────┬─────┘ └──────────┘
                         │            │
                    ┌────┴────┐  ┌────┴────────────────────┐
                    │   LLM   │  │ Prometheus │ Loki        │
                    │ Provider│  │ AlertMgr   │ 31d retain  │
                    └─────────┘  └────────────┴─────────────┘
```

## Services

| Service | Version | Port | Purpose |
|---------|---------|------|---------|
| **LightRAG** | 1.4.6 | 9621 | Knowledge graph RAG engine (medical + codebase) |
| **RAG-Anything** | 1.2.10 | - | Multimodal document processor (PDF, images, tables) |
| **Nginx** | 1.28-alpine | 80, 443 | Reverse proxy, TLS, rate limiting |
| **Authelia** | 4.39.15 | 9091 | Two-factor authentication (TOTP/WebAuthn) |
| **Prometheus** | v2.53.5 | 9090 | Metrics collection |
| **Loki** | 3.6.0 | 3100 | Log aggregation (31-day retention) |
| **Grafana** | 10.2.3 | 3000 | Dashboards |
| **Jaeger** | 1.53 | 16686 | Distributed tracing (OpenTelemetry) |
| **AlertManager** | v0.27.0 | 9093 | Alert routing |
| **SonarQube** | 10.8 | 9000 | Static code analysis |
| **Checkov** | latest | - | HIPAA compliance scanning (on-demand) |
| **Trivy** | 0.69.3 | - | Container CVE scanning (on-demand) |
| **Healthcare Scanner** | custom | - | Medical compliance checks |
| **OWASP ZAP** | latest | - | API security scanning |
| **Inferno** | latest | - | ONC g(10) FHIR conformance testing |
| **Certbot** | v3.3.0 | - | SSL certificate auto-renewal |

## Production RAG Pipeline

The backend's chatbot controller runs a **13-step pipeline** with enterprise RAG features:

| Step | Component | Cost |
|------|-----------|------|
| 1-7 | Rate limit, token budget, abuse detection, PII scrub, intent detection, cache | Free |
| 8 | **Query Planner** — decomposes complex queries into sub-queries | Free (heuristic) or 1 LLM call (ambiguous) |
| 9 | **LightRAG Query** — graph-based retrieval (supports multi-query) | Free |
| 10 | **Confidence Scoring + Reranking** — TF-IDF overlap + cosine similarity | Free |
| 11 | **AI Generation** via Model Router — dynamic model selection per task | 1 LLM call |
| 12 | **Auditor + Strategist Validation** — hallucination/contradiction check | 1 LLM call (skipped if confidence > 0.85) |
| 13 | Response pipeline — cache, audit, CloudWatch metrics, event bus | Free |

### Dynamic Model Selection (No Hardcoded Models)

All models are configured via environment variables:

| Task Type | Purpose | Env Var Prefix |
|-----------|---------|---------------|
| `generation` | Main chatbot response | `MODEL_GENERATION_*` |
| `validation` | Auditor + Strategist | `MODEL_VALIDATION_*` |
| `planning` | Query decomposition | `MODEL_PLANNING_*` |
| `evaluation` | Offline LLM judge | `MODEL_EVALUATION_*` |

Each task type supports Bedrock, Vertex AI, and Azure OpenAI with automatic failover.

### HyDE (Hypothetical Document Embeddings)

At ingestion time, 3-5 hypothetical patient questions are generated per document. This improves retrieval by enabling question-to-question matching.

```bash
# Enhanced ingestion with HyDE
bash scripts/ingest-with-questions.sh
```

## Knowledge Bases

### Medical (Patient Chatbot)
```
knowledge/medical/
├── faqs/
│   ├── appointments.md      <- Booking, rescheduling, cancellation
│   ├── billing.md           <- Payments, refunds, pricing
│   ├── subscriptions.md     <- Plans, discounts, family sharing
│   └── health-records.md    <- FHIR data, export, GDPR rights
├── policies/
│   └── privacy-summary.md   <- Privacy policy for chatbot context
└── augmented/               <- HyDE-enhanced versions (auto-generated)
```

### Codebase (Developer Intelligence)
```
knowledge/codebase/
└── architecture.md           <- Service architecture, APIs, compliance controls
```

## Getting Started

### Prerequisites
- Docker Desktop 4.0+ (allocate 4.5GB+ memory)
- LLM API key (configure in `.env`)

### Setup
```bash
# 1. Configure environment
cp configs/.env.example configs/.env
# Edit .env — add your LLM API key

# 2. Start platform
cd configs && docker compose up -d

# 3. Ingest with HyDE question generation (enhanced)
bash scripts/ingest-with-questions.sh

# 4. Ingest codebase knowledge
bash scripts/ingest-codebase.sh
```

### Run Tests (Free, No AI Calls)
```bash
cd mediconnect-infrastructure-production/backend_v2
npx ts-node --project communication-service/tsconfig.json shared/__tests__/rag-pipeline.test.ts   # 53 assertions
npx ts-node --project communication-service/tsconfig.json shared/__tests__/rag-red-team.test.ts   # 50 assertions
npx ts-node --project communication-service/tsconfig.json shared/__tests__/rag-evaluation.test.ts # 15+ assertions
```

### Run Compliance Scans
```bash
# HIPAA compliance (Terraform)
docker compose --profile scan run --rm checkov

# Container vulnerability scan
docker compose --profile scan run --rm trivy

# Healthcare compliance check
docker compose --profile scan run --rm healthcare-scanner
```

## Related Repositories

| Repository | Purpose |
|-----------|---------|
| [mediconnect-infrastructure-production](https://github.com/Zahidulislam2222/mediconnect-infrastructure-production) | Backend — 7 microservices, Terraform IaC, Kafka |
| [mediconnect-hub](https://github.com/Zahidulislam2222/mediconnect-hub) | Frontend — React, Stripe, ChatWidget |

---

<div align="center">

**MediConnect RAG** — Enterprise knowledge retrieval and compliance scanning.
Built with LightRAG. Monitored with Prometheus. Secured with Authelia.

*Part of the MediConnect healthcare platform.*

</div>
