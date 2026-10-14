# Isolated local-model target

Updated 2026-10-13: independently reviewed source and local runtime tests passed. VPS deployment, actual model weights/output/dimensions, ingestion/retrieval and restore remain open.

This release design uses the existing VPS without adding hosting or paid provider usage. It is separate from the broad monitoring/security Compose stack. Deployment is gated on capacity, immutable image/model verification, local tests, independent review and current live drift evidence.

The private `.env` is the deployment configuration owner. LightRAG's pinned typed configuration validates its application environment; Compose validates deployment variables. Keep real API/signing keys in the ignored environment and root recovery file. Never use the example placeholders live. Medical and codebase services use separate persistent volumes. API ports bind host loopback only; Protected requests require the workspace API key or an authorized account bearer token. Distinct private AUTH_ACCOUNTS must be configured: the pinned version otherwise issues guest tokens that bypass API-key checks. Test guest issuance and unauthorized requests before activation. Ollama disables cloud features, accepts only local models and uses an internal network. No public proxy or clinical activation is established by this release design.

The combined configured cap is 9.9375 GiB RAM and 4 CPU cores. Fresh capacity must retain at least 6 GiB available RAM after that budget. The Qwen2.5 7B selection avoids the 3B model's separate research license; both selected models require license/digest and actual embedding dimension verification before activation. Small local models require measured grounded retrieval and safety evaluation; a working model endpoint does not establish clinical quality.

Ollama and both RAG services have no host ports and use separate internal medical and codebase networks; Ollama joins both and each RAG service joins only its own. A small proxy without credentials joins both internal networks and a separate ingress bridge; only its two authenticated upstream routes are published to host loopback. The proxy does not log requests, retries no upstream failures and runs nonroot with a read-only filesystem. Model and RAG processes have no internet egress. Bootstrap approved public weights by temporarily attaching only Ollama to the downloads network with bootstrap.compose.yaml, then recreate only Ollama without that override before normal operation. Both workspace networks remain internal throughout. Dynamic Docker DNS refresh avoids permanently stale upstream addresses; separate subnets prevent an old medical address being reused by codebase. Stop ingress before replacing backend containers and restart it after backend readiness checks. No cloud credentials may be provided. Preserve models, both knowledge volumes, private configuration and recovery keys in the backup inventory; demonstrate an application-consistent restore before closing phase6.

The derived runtime adds SELFHOST_EMBEDDING_TIMEOUT_SECONDS in a central typed settings layer. It forwards the deadline to the actual Ollama client and wraps the await with an asyncio deadline; cancellation propagates without retry. The Docker build requires the exact LIGHTRAG_BASE_IMAGE argument, caches SDK-owned tokenizer data and runs as UID1000. Build the small runtime locally and transfer its verified image archive; do not rebuild application source on production.

Current release state: source and local validation only. There is no deployment or ingestion success claim in this document.

Request privacy: ingress access and error logs are disabled. Python logging records discard upstream message arguments, exceptions and stack content before handlers see them; Uvicorn access logging is disabled. Operational logs retain the fixed runtime-event label, logger, timestamp and severity. This deliberately limits diagnostic detail; use authenticated health, pipeline state and resource metrics instead of recording document/request text. Startup console output can still describe non-secret configuration. This is not permission to process patient data.

Ollama's documented application home has a distinct named `identity` volume at `/root/.ollama`; the existing model store remains at `/models`. Inventory the generated identity in the private recovery register and include this volume in encrypted consistent recovery. Before replacing an existing local container without this mount, preserve and verify its identity bytes in the owned volume and recovery register. Recreation must retain the same identity; a newly generated key is not recovery of the original. No identity value belongs in public artifacts or logs.

The added identity volume passed controlled local recreation: both existing identity files retained their bytes, the model store stayed unchanged, and authenticated workspace HTTP plus sibling/resource/network checks passed. VPS deployment and application-consistent recovery remain open.

Network allocation uses four explicit subnet settings in the private `.env`:
`MEDICAL_NETWORK_SUBNET`, `CODEBASE_NETWORK_SUBNET`, `INGRESS_NETWORK_SUBNET`
and `DOWNLOAD_NETWORK_SUBNET`. The example CIDRs are illustrative; before each
deployment verify their nonoverlap with every current Docker IPAM subnet, host
interface address and non-default route, and with one another. Preserve an
existing owned network's exact subnet when recovering a partial activation.
Check its Compose project/network labels, internal flag and attached containers
before reuse. Never prune other networks or change the shared daemon to obtain
address capacity. Keep medical and codebase internal; only the temporary Ollama
download network permits model-download egress. The failed automatic allocation
does not establish successful activation, model availability or retrieval.
