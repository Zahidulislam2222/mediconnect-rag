# Knowledge maintenance and recovery scripts

Reviewed 2026-10-13. Inspect a script, its configuration, target project and effects before execution. Existing ingestion, monitoring, scanning and backup scripts belong to their documented deployment; they do not implicitly operate the isolated local-model release.

Planning and read-only verification are distinct from ingestion, provider calls, container operations or writes. Obtain applicable data, operation and cost authorization before a state-changing run. Keep credentials out of command arguments and output; preserve failed-attempt evidence and reconcile partial effects before retrying.

Backups must cover related stores consistently, use the approved encrypted off-device destination and separate key custody, and pass an isolated application restore. File copying or archive extraction alone does not close recovery acceptance.

See [operations and restore](https://github.com/Zahidulislam2222/mediconnect-infrastructure-production/blob/main/docs/OPERATIONS.md), [AI governance](https://github.com/Zahidulislam2222/mediconnect-infrastructure-production/blob/main/docs/AI-GOVERNANCE.md) and [isolated runtime](../deploy/selfhost/README.md).
