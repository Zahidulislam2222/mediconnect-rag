# Knowledge service clients

Reviewed 2026-10-13. Client configuration must use the typed application boundary and the approved workspace endpoint, key/account and deadline settings. Do not put private workspace credentials in browser or native bundles.

Keep medical and codebase clients separate. Validate authorization, workspace routing, bounded requests, cancellation and sanitized failure behavior against the actual runtime before activation. Never use fallback credentials or treat a client configuration as proof of retrieval quality.

See [API contracts](https://github.com/Zahidulislam2222/mediconnect-infrastructure-production/blob/main/docs/API-CONTRACTS.md), [runtime configuration](../deploy/selfhost/README.md) and [AI governance](https://github.com/Zahidulislam2222/mediconnect-infrastructure-production/blob/main/docs/AI-GOVERNANCE.md).
