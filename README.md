# rag-production-stack

Production-hardened RAG infrastructure with enterprise observability, zero-trust authentication, and compliance scanning.

Built on [LightRAG](https://github.com/HKUDS/LightRAG) + [RAG-Anything](https://github.com/HKUDS/RAG-Anything) with Gemini 2.5 Flash.

## Architecture

```
                    ┌──────────────────────────────────────────────────┐
                    │                  Internet                        │
                    └────────────────────┬─────────────────────────────┘
                                        │ :80 / :443
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
| LightRAG | `1.4.6` | 9621 | Knowledge graph RAG engine |
| RAG-Anything | `1.2.10` | - | Multimodal document processor (PDF, images, tables, equations) |
| Nginx | `1.28-alpine` | 80, 443 | Reverse proxy, TLS, rate limiting, forward-auth |
| Authelia | `4.39.15` | 9091 | Two-factor authentication (TOTP/WebAuthn) |
| Prometheus | `v2.53.5` | 9090 | Metrics collection (7 scrape targets) |
| Loki | `3.6.0` | 3100 | Log aggregation (31-day retention, 4MB/s rate limit) |
| Grafana | `10.2.3` | 3000 | Dashboards, auto-provisioned datasources |
| Jaeger | `1.53` | 16686 | Distributed tracing via OpenTelemetry |
| AlertManager | `v0.27.0` | 9093 | Alert routing (service down, high CPU/memory, Loki errors) |
| SonarQube | `10.8-community` | 9000 | Static code analysis |
| Checkov | `latest` | - | HIPAA compliance scanning (on-demand) |
| Trivy | `0.69.3` | - | Container CVE scanning (on-demand) |
| Certbot | `v3.3.0` | - | SSL certificate auto-renewal (on-demand) |

All images pinned to specific versions. No `:latest` on production services.

## Security

**Authentication** — Authelia forward-auth on all proxied endpoints. Two-factor (TOTP/WebAuthn) enforced. Unauthenticated requests get 302 to login portal.

**Transport** — TLS 1.2/1.3 only. HSTS with `includeSubDomains; preload`. Strict cipher suite (`HIGH:!aNULL:!MD5`).

**Headers** — `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` restricting camera/mic/geo.

**Rate Limiting** — 10 req/s per IP, burst of 20, `nodelay`.

**Container Hardening** — Nginx runs with `read_only` root filesystem (tmpfs for `/tmp`, `/var/cache/nginx`, `/run`), `no-new-privileges`, `cap_drop: ALL` + only `NET_BIND_SERVICE`, `CHOWN`, `SETGID`, `SETUID`.

**Network Isolation** — Three Docker networks:
- `frontend` (bridge) — Nginx, Authelia
- `backend` (internal) — LightRAG, Authelia, Nginx
- `monitoring` (internal) — Prometheus, Loki, Grafana, Jaeger, SonarQube, AlertManager

**Secrets** — All secrets externalized. No credentials in version control. Example templates provided for configuration.

## Observability

**Metrics** — Prometheus scrapes 7 targets: LightRAG, Nginx (`stub_status`), Grafana, Jaeger, Loki, SonarQube, self. 15s scrape interval.

**Logs** — Loki Docker log driver on all services (non-blocking mode, `loki-retries: 2`, `loki-max-backoff: 800ms`). Loki and Nginx use `json-file` driver with rotation (`10m` max, 3 files) to avoid circular dependency.

**Traces** — LightRAG instrumented with `OTEL_EXPORTER_OTLP_ENDPOINT` pointing to Jaeger gRPC (`:4317`).

**Alerts** — AlertManager with rules for: container down (1m), high memory (>400MB, 5m), high CPU (>80%, 5m), Prometheus target missing (5m), Loki 5xx errors.

**Dashboards** — Grafana auto-provisioned with Prometheus, Loki, and Jaeger datasources. Includes a Docker Services Overview dashboard (targets status, memory, CPU, scrape duration).

## Resource Allocation

Calibrated for an 8GB RAM host (~4.3GB container budget):

| Service | Memory | CPU |
|---------|--------|-----|
| SonarQube | 1536M | 2.0 |
| LightRAG | 1024M | 2.0 |
| RAG-Anything | 1024M | 2.0 (on-demand) |
| Prometheus | 384M | 1.0 |
| Grafana | 384M | 1.0 |
| Loki | 384M | 1.0 |
| Jaeger | 256M | 1.0 |
| Nginx | 128M | 0.5 |
| Authelia | 128M | 0.5 |
| AlertManager | 128M | 0.5 |

All services have Docker healthchecks with configurable intervals, timeouts, retries, and start periods.

## Getting Started

### Prerequisites

- Docker Desktop 4.0+ (allocate 4.5GB+ memory)
- [Loki Docker driver plugin](https://grafana.com/docs/loki/latest/send-data/docker-driver/)
- SSL certificates for your domain
- [Gemini API key](https://aistudio.google.com/apikey)

### Configuration

1. **Environment** — Create `configs/.env`:

```env
GEMINI_API_KEY=<your-key>
LLM_BINDING=gemini
LLM_MODEL=gemini-2.5-flash
EMBEDDING_BINDING=gemini
EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIM=1536
GRAFANA_ADMIN_PASSWORD=<your-password>
```

2. **Authelia** — Copy and configure from example templates:

```bash
cp configs/authelia/configuration.yml.example configs/authelia/configuration.yml
cp configs/authelia/users_database.yml.example configs/authelia/users_database.yml

# Generate secrets
openssl rand -hex 32  # jwt_secret
openssl rand -hex 32  # session.secret
openssl rand -hex 32  # storage.encryption_key

# Generate user password hash
docker run --rm authelia/authelia:4.39.15 authelia crypto hash generate argon2
```

3. **SSL** — Place certificates in `configs/ssl/`:
   - `fullchain.pem`
   - `privkey.pem`

4. **Loki driver** — Install the Docker plugin:

```bash
docker plugin install grafana/loki-docker-driver:latest --alias loki --grant-all-permissions
```

### Deploy

```bash
cd configs
docker compose up -d
```

### RAG-Anything

```bash
# Build
docker compose --profile rag build raganything

# Process documents
docker compose --profile rag run --rm raganything /app/data/inputs/document.pdf
docker compose --profile rag run --rm raganything --dir /app/data/inputs/

# Query
docker compose --profile rag run --rm raganything -q "your question" --mode hybrid
```

### Security Scans

```bash
# HIPAA compliance (Terraform)
docker compose --profile scan run --rm checkov

# Container CVE scan
docker compose --profile scan run --rm trivy
```

### Backup

```bash
bash scripts/backup.sh           # Run backup
bash scripts/verify-backup.sh    # Verify integrity + test restore
```

## Project Structure

```
rag-production-stack/
├── configs/
│   ├── docker-compose.yml
│   ├── nginx/
│   │   └── default.conf
│   └── authelia/
│       ├── configuration.yml.example
│       └── users_database.yml.example
├── monitoring/
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   └── alert.rules
│   ├── loki/
│   │   └── loki-config.yml
│   ├── alertmanager/
│   │   └── alertmanager.yml
│   └── grafana/
│       └── provisioning/
│           ├── datasources/
│           │   └── datasources.yml
│           └── dashboards/
│               ├── dashboards.yml
│               └── docker-monitoring.json
├── ragAnything/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── config.py
│   └── process.py
├── scripts/
│   ├── backup.sh
│   └── verify-backup.sh
└── reports/
    ├── hipaa/
    ├── soc2/
    └── gdpr/
```

## Network Topology

```
┌─────────────────────────────────────────────────────────────┐
│  frontend                                                    │
│  ┌─────────┐  ┌──────────┐                                  │
│  │  Nginx  │──│ Authelia  │                                  │
│  └────┬────┘  └────┬─────┘                                  │
├───────┼─────────────┼───────────────────────────────────────┤
│  backend (internal — no external access)                     │
│  ┌──────────┐  ┌────┴─────┐  ┌──────────────┐              │
│  │ LightRAG │  │ Authelia  │  │ RAG-Anything │              │
│  └──────────┘  └──────────┘  └──────────────┘              │
├─────────────────────────────────────────────────────────────┤
│  monitoring (internal — no external access)                  │
│  ┌──────────┐ ┌──────┐ ┌──────┐ ┌───────┐ ┌─────────────┐ │
│  │Prometheus│ │ Loki │ │Jaeger│ │Grafana│ │  SonarQube  │ │
│  │+AlertMgr │ │      │ │      │ │       │ │             │ │
│  └──────────┘ └──────┘ └──────┘ └───────┘ └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## License

MIT

## Author

**Zahidul Islam** — [healthcodeanalysis.com](https://healthcodeanalysis.com)
