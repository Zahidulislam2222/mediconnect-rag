# MediConnect Knowledge Services

LightRAG-based medical and codebase knowledge processing, isolated local-model runtime, and retained monitoring/security/backup tooling.

**Maintainer:** Zahidul Islam · [Platform documentation](https://github.com/Zahidulislam2222/mediconnect-infrastructure-production/blob/main/docs/README.md) · [Release acceptance](https://github.com/Zahidulislam2222/mediconnect-infrastructure-production/blob/main/docs/RELEASE-STATUS.md)

## Current delivery — 2026-10-13

The document processor and isolated runtime source are published and independently reviewed. Processor verification passed 98 regressions, type/lint/security checks and container/lifecycle checks. Actual local runtime verification covered authentication, workspace isolation, SDK deadlines, request privacy and container recreation. Live VPS deployment, selected-model output/dimensions, grounded ingestion/retrieval, monitoring and consistent recovery remain open.

| Boundary | Entry point |
|---|---|
| Approved public medical knowledge | `knowledge/medical/` |
| Approved developer knowledge | `knowledge/codebase/` |
| Isolated existing-host local-model application | [deploy/selfhost/README.md](deploy/selfhost/README.md) |
| Optional explicit document processor | [ragAnything/README.md](ragAnything/README.md) |
| Historical broader operations stack | `configs/`; separate deployment project and acceptance |
| Maintenance/backup tooling | [scripts/README.md](scripts/README.md) |

## Safe setup

Read the selected deployment contract before operating containers. Configure only from the corresponding environment example, validate typed settings, verify immutable images/model licenses, inspect target drift and fresh capacity, and keep private credentials outside Git. Medical and codebase workspaces require separate keys/accounts/storage and tested access denial.

The processor's `--plan` mode performs source validation without a model request. Real ingestion/search is a distinct approved action. The optional external-provider processor is not the selected free-only local-model deployment; paid provider execution requires separate explicit cost approval. Never start the broad monitoring stack through the isolated application's Compose file.

No identifiable patient data is approved for this corpus. Source permissions, clinical review, model safety and applicable provider/operator agreements remain prerequisites for a broader service. A scanner finding control patterns is not compliance certification, and plausible generated text is not grounded-answer acceptance.

## Public contracts

[AI governance](https://github.com/Zahidulislam2222/mediconnect-infrastructure-production/blob/main/docs/AI-GOVERNANCE.md) · [Security](https://github.com/Zahidulislam2222/mediconnect-infrastructure-production/blob/main/docs/SECURITY-ARCHITECTURE.md) · [Privacy](https://github.com/Zahidulislam2222/mediconnect-infrastructure-production/blob/main/docs/PRIVACY-AND-DATA.md) · [Law](https://github.com/Zahidulislam2222/mediconnect-infrastructure-production/blob/main/docs/COMPLIANCE-AND-LAW.md) · [Operations/recovery](https://github.com/Zahidulislam2222/mediconnect-infrastructure-production/blob/main/docs/OPERATIONS.md) · [Future scale](https://github.com/Zahidulislam2222/mediconnect-infrastructure-production/blob/main/docs/SCALABILITY.md)

[Contributing](CONTRIBUTING.md) · [Code of conduct](CODE_OF_CONDUCT.md) · [Private vulnerability reporting](SECURITY.md) · [MIT license](LICENSE) · [Third-party notices](THIRD-PARTY-NOTICES.md)
