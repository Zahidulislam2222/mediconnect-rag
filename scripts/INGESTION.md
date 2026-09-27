# Local knowledge ingestion

All three shell entry points require `--plan` or `--execute`. Importing the
Python entry point does not run ingestion. Install the existing
`scripts/requirements-hyde.txt` in an isolated Python environment first.

`--plan` validates current local documents without generation or submission:

```bash
bash scripts/ingest-medical.sh --plan
bash scripts/ingest-codebase.sh --plan
bash scripts/ingest-with-questions.sh --plan
```

Set explicit `LIGHTRAG_MEDICAL_URL` and `LIGHTRAG_CODEBASE_URL` origins in the
environment or `configs/.env`. Execution also requires `LIGHTRAG_API_KEY`.
HyDE execution additionally requires `GEMINI_API_KEY` and `HYDE_MODEL`.
Inherited environment values take precedence, including empty values. Dotenv
values are data; shell expressions and variable interpolation are not executed.

**Execution may incur generation and embedding charges.** Obtain the owner's
explicit approval of the actual cost before running `--execute`; planning does
not grant execution approval. Only approved public knowledge may be submitted.
No production ingestion has been verified by the local fixture tests.

`config/ingestion.json` owns the source groups, output location, byte/file limits
and timeout. `config/hyde.json` owns generation settings and appended heading.
Only HTTPS and loopback HTTP origins are permitted; redirects are rejected.
The LightRAG 1.4.6 text contract is isolated in `ingestion_protocol.py`.

Medical and codebase target origins must be configured deliberately. Workspace
isolation is a server property: the old client-side `metadata.workspace` did
not select a LightRAG workspace. Separate URLs alone do not prove isolation;
verify the server's configured workspace and storage before real ingestion.

Every required source group must contain valid current documents. Preflight
rejects symlinks, empty/invalid text, changes during reading and configured
limit violations before any request. The source/output tree must be owned by
the operator and quiescent; this is not a sandbox against concurrent directory
replacement by another process. Generated documents preserve relative source
identity under the configured output directory. Stale output is retained but
never selected for upload. All generation must succeed before any output is
replaced or any submission begins; individual replacements are atomic, not a
multi-file transaction.

Success reports `ACCEPTED`: the server acknowledged background processing with
a track identifier. It does **not** establish completed indexing or retrieval
quality. A failed or uncertain submission stops with a nonzero exit and counts
only acknowledged requests. There is no automatic retry; a lost response may
mean the server accepted a document without the local count advancing. Check
server processing state before an operator-approved rerun.

Personal regression scripts remain in the umbrella project's private `tests/`
folder. They use synthetic documents, mocked generation and a loopback server.
