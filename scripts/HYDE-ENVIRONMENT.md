# HyDE ingestion environment

Install the dependencies in `scripts/requirements-hyde.txt` before invoking
`bash scripts/ingest-with-questions.sh`. Python 3.10 or newer is required.

The launcher parses the optional `configs/.env` file before starting ingestion.
It preserves quoted spaces, equals signs, comments and empty values. Existing
process environment values take precedence, including explicitly empty values.
An invalid assignment stops the launcher without printing its contents.

Environment files are data: shell commands, backticks and variable references
are never executed or expanded. Write the final value explicitly when a setting
previously relied on interpolation. The parser dependency is pinned because its
binding API is used to reject malformed records rather than silently skip them.

`GEMINI_API_KEY` and `HYDE_MODEL` must be configured. Generation failures stop the
shell caller before ingestion, and do not overwrite the failed document's prior
augmentation. `LIGHTRAG_URL` can come from the environment file or the process
environment and is resolved after loading that file.

The `--environment-loaded` argument is an internal launcher marker, not an
authentication or authorization mechanism. Invoke the shell script normally.

Generation invokes the configured external provider. Local synthetic tests do
not establish provider availability, answer quality or service integration.
