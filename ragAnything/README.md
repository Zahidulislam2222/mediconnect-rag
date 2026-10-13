# RAG-Anything document processor

Reviewed 2026-10-13. Current platform acceptance is tracked in the [release ledger](https://github.com/Zahidulislam2222/mediconnect-infrastructure-production/blob/main/docs/RELEASE-STATUS.md); this guide retains its bounded component contract.

This optional CLI validates approved public documents before invoking the model provider. It never diagnoses or prescribes. Real generation and embeddings may cost money: verify account eligibility and obtain the owner’s cost approval before `--execute`. Do not submit identifiable health data without the required provider agreement.

## Plan first

The local CLI requires exactly one of `--plan` or `--execute`. Planning imports no provider SDK, makes no provider request and does not require API credentials or models. It checks supported current files and configured bounds.

```bash
python ragAnything/process.py --dir /app/data/inputs --plan
python ragAnything/process.py /app/data/inputs/document.pdf --plan
```

Container entry points use the same arguments, after an authorized image build:

```bash
docker compose --profile rag run --rm raganything --dir /app/data/inputs --plan
```

Only after explicit provider-cost and data approval, substitute `--execute`. Query execution also requires approval:

```bash
python ragAnything/process.py --query "Approved public question" --plan
```

## Results and failures

`PLANNED` means source validation only. `PROCESSED` requires explicit storage initialization, the pinned ordinary API’s expected `None` return, a confirmed fully processed document status and an unfailed provider operation. It does not establish retrieval quality or clinical acceptance. An unexpected result, unconfirmed status, exception or failed query produces a sanitized `FAILED` summary and nonzero exit. Processing stops at the first failure. Completed earlier documents remain; there is no automatic retry or multi-document rollback. Reconcile uncertain effects before an approved rerun. SDK output is suppressed because it can include document content and provider error bodies; the CLI reports stage and attempted/completed counts.

Nested documents keep distinct output directories, including equal basenames and different extensions. The input, parsed-output and knowledge-storage roots must be separate, operator-owned and quiescent; symlinks and oversized/empty inputs are rejected. No concurrent filesystem replacement is supported.

## Configuration and compatibility

`settings.py` is the typed boundary. `processor.json` owns parser, supported extensions, query mode, container paths, feature flags, input bounds and provider endpoint/version/timeouts/limits. Its tokenizer model is used only for local token counting; tokenizer data is cached at build time and makes no model-provider call. LibreOffice Writer/Calc/Impress are installed for the declared Office parser inputs. Models have no source-code fallback: `GEMINI_API_KEY`, `LLM_MODEL`, `EMBEDDING_MODEL` and `EMBEDDING_DIM` must be configured for execution. Both environment examples document optional `RAGANYTHING_*` overrides.

The provider adapter uses the official pinned `google-genai` SDK. It supports text/history and bounded inline images, rejects remote image URLs, requests the configured embedding dimensionality, validates returned vectors and closes clients. Provider requests have one total attempt and run serially. The first failure closes the operation to further provider requests, including retries or fallbacks attempted inside the pinned engine; the CLI checks this failure latch even if the engine swallows an exception. The processor owns a sequential multimodal stage boundary instead of the pinned SDK batch/fallback wrapper. Unsupported content, invalid descriptions and storage/entity/status errors propagate immediately; an uncertain write never triggers individual regeneration or a completion mark. Actual storage I/O errors also latch the operation failed when nested SDK helpers suppress them; final status writes and flushes propagate failures. Image-only parses receive a source/status record before model effects. No paid fallback is configured. The old nonexistent `lightrag.llm.gemini` import is removed. LightRAG matches the explicitly pinned stack version; package installation and runtime compatibility remain release gates.

Existing persistent mounts are `/app/data` for inputs, `/app/output` for parsed documents and `/app/storage` for the separate multimodal knowledge store. These do not establish isolation from other workspaces or complete backup coverage. Deployment, real ingestion/search and application-consistent recovery require their separate phase gates.
