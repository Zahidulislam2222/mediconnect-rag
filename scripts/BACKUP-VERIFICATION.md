# Local backup verification

Run `bash scripts/verify-backup.sh` with Python 3.10+ and Restic installed.
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
