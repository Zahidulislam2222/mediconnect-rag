# MediConnect Architecture Summary

## Public release and source capabilities
MediConnect is a connected-care engineering project with a React/TypeScript website, Strapi CMS, backend services, infrastructure definitions and a separate LightRAG stack. The current public website is a showcase: account access, payments and clinical services are unavailable. Source capabilities below do not establish a complete operating healthcare service, compliance certification or measured capacity.

## Repository responsibilities

| Component | Responsibility |
|---|---|
| Website and preserved Capacitor client | Public pages, CMS-backed guides and protected-role interface source |
| Strapi CMS | Editorial article and media source for public guides |
| Production infrastructure repository | Backend application source, regional configuration, infrastructure and deployment definitions |
| Historical development implementation | Historical reference; not the current backend authority |
| RAG stack | Separate medical and codebase knowledge workspaces, ingestion, model integration and operational tooling |

## Backend source
Node/TypeScript services cover patient, doctor, booking, communication and staff responsibilities. Python/FastAPI source covers administration and DICOM-oriented imaging. Shared modules provide request validation, authentication and regional context, encryption helpers, audit/logging, subscriptions and event integration. Each deployed flow requires its own live authorization, regional, provider and data-integrity acceptance evidence.

The application has AWS-oriented data and identity integrations alongside configured external compute and infrastructure definitions. Current resource inventory, deployment status, ports, providers, quotas and counts must be obtained from configuration and platform-native evidence; historical source counts are not a live inventory. Regional routing intent does not prove that every service or third party prevents cross-region transfer.

## Current isolated RAG verification
Medical and codebase workspaces use separate persistent data roots and API keys. The configured self-hosted model provider uses shared local CPU resources, persistent model and identity storage, internal workspace networks and loopback-only ingress. Actual synthetic generation and embedding have passed; full ingestion/retrieval acceptance, application wiring, workload limits, monitoring and coordinated restore are separate gates. No public patient-data RAG endpoint or clinical-quality claim is established here.

## Deployment and recovery evidence
Application publication, deployment, exact local/live file parity, real HTTP/UI behavior, independent review and backup/restore are distinct checks. A successful build, queued ingestion request or healthy container alone does not establish a finished phase. Clinical launch also depends on verified operating-entity, address, provider, privacy and contractual requirements.
