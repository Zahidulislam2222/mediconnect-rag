# Third-party notices

The MIT Licence in [LICENSE](LICENSE) covers the original source code in this repository written for
MediConnect. It does **not** relicense third-party material. Each third-party component below keeps
its own licence and copyright.

## Container images (used unmodified, pulled at runtime)

| Component | Image | Licence (upstream) |
|---|---|---|
| LightRAG | `ghcr.io/hkuds/lightrag` | MIT |
| Grafana | `grafana/grafana` | AGPL-3.0 |
| Loki | `grafana/loki` | AGPL-3.0 |
| Prometheus, Alertmanager | `prom/prometheus`, `prom/alertmanager` | Apache-2.0 |
| Jaeger | `jaegertracing/all-in-one` | Apache-2.0 |
| Authelia | `authelia/authelia` | Apache-2.0 |
| Nginx | `nginx` | BSD-2-Clause |
| Redis | `redis` | Check the upstream licence for the pinned version (Redis changed licences in 2024–2025) |
| Certbot | `certbot/certbot` | Apache-2.0 |
| Trivy | `aquasec/trivy` | Apache-2.0 |
| Checkov | `bridgecrew/checkov` | Apache-2.0 |
| Prowler | `prowlercloud/prowler` | Apache-2.0 |
| OWASP ZAP | `ghcr.io/zaproxy/zaproxy` | Apache-2.0 |
| SonarQube Community | `sonarqube` | Check upstream (LGPL-3.0 historically) |
| HAPI FHIR | `hapiproject/hapi` | Apache-2.0 |
| Inferno validator | `infernocommunity/inferno-resource-validator` | Apache-2.0 |

These images are not distributed in this repository. Licences shown are the upstream projects' stated
licences at the time of writing; check the pinned versions before redistribution. Python packages in
`requirements*.txt` keep their own licences.
