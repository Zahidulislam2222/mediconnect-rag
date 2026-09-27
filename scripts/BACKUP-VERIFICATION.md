# Local backup verification

Run `bash scripts/verify-backup.sh` with Python 3.11+ and Restic installed.
Both backup commands use `config/backup-policy.json` for paths, groups,
exclusions and retention. Keep password contents in the ignored password file.

Verification requires the newest exact-source snapshot for every configured
group, checks all stored data, and restores each selected snapshot with content
verification. Missing groups or failed checks return a nonzero exit status.
It never creates, prunes or deletes snapshots and never starts services.

Each run keeps its logs, atomic `verification.json` report and restored files in
a unique directory under the ignored configured verification directory. These
files can contain private data. Do not commit or share them. When changing the
verification directory, also maintain its Git ignore rule and access controls.
An explicit `--output-root` overrides that directory; it must be a private
location outside the backup sources and repository. `--project-root` supports
verifying an existing local repository from an isolated tool checkout.

A passing result proves restoration of the selected snapshots, not that a
snapshot includes subsequent edits or excluded databases. It does not prove
application consistency, service startup, external state, or off-machine
disaster recovery. Check snapshot dates and the retained group inventory.

`backup.sh` retains its separate snapshot creation and retention/pruning
behavior. Verification never invokes it. Review backup policy and retention
before running that mutating command.

## SQLite databases

The policy includes an additional `sqlite-databases` group for Authelia and
Grafana. Before creating any Restic snapshot, `backup.sh` uses SQLite online
backup through read-only source connections. Each output passes
`PRAGMA integrity_check`; its hash and completion time enter an atomic manifest.
The staging lock remains held until the complete Restic backup and retention
sequence ends. Missing, corrupt or unavailable databases prevent all Restic
commands. An existing repository that fails access checks is never initialized.
Raw database and journal/WAL files are excluded from the ordinary file groups.

Paths and timing/page limits live in `config/backup-policy.json`. Staging files
and retained failed partial copies live under ignored `backup-staging/` and
contain sensitive database data. Restrict access like the original databases.
An interrupted run can leave a `.lock` directory: confirm that no backup process
is active before removing that empty lock and retrying; never delete databases
or a lock belonging to an active run. Previous partial files are retained outside
the published SQLite group for investigation.

`python3 scripts/sqlite_snapshots.py` prepares and verifies local copies only.
`bash scripts/backup.sh` additionally creates Restic snapshots and prunes according
to the configured retention policy. `bash scripts/verify-backup.sh` verifies the
restored SQLite manifest, each file hash and database integrity. Old repositories
without the SQLite group now fail coverage verification until a new complete
backup is created. Neither preparation nor verification restarts services.

These are individually consistent SQLite snapshots, not a coordinated transaction
across services. LightRAG's other storage, off-machine copies and successful
service recovery still require separate operational verification.

Reference: https://www.sqlite.org/backup.html

Restores select each exact source subtree by full snapshot ID, so unrelated
ancestor ownership metadata is not applied to the verification directory. This
also avoids WSL/Windows drive metadata failures while keeping content verification.
