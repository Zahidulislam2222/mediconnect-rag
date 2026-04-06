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
                    │ Gemini  │  │ Prometheus │ Loki        │
                    │2.5 Flash│  │ AlertMgr   │ 31d retain  │
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

## Knowledge Bases

### Medical (Patient Chatbot)
```
knowledge/medical/
├── faqs/
│   ├── appointments.md      ← Booking, rescheduling, cancellation
│   ├── billing.md           ← Payments, refunds, pricing
│   ├── subscriptions.md     ← Plans, discounts, family sharing
│   └── health-records.md    ← FHIR data, export, GDPR rights
└── policies/
    └── privacy-summary.md   ← Privacy policy for chatbot context
```

### Codebase (Developer Intelligence)
```
knowledge/codebase/
└── architecture.md           ← Service architecture, APIs, compliance controls
```

## Getting Started

### Prerequisites
- Docker Desktop 4.0+ (allocate 4.5GB+ memory)
- Gemini API key

### Setup
```bash
# 1. Configure environment
cp configs/.env.example configs/.env
# Edit .env — add GEMINI_API_KEY

# 2. Start platform
cd configs && docker compose up -d

# 3. Ingest medical knowledge
bash scripts/ingest-medical.sh

# 4. Ingest codebase knowledge
bash scripts/ingest-codebase.sh
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
