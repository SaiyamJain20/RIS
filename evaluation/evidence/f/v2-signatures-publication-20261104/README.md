# Successful code publication; SSH read-back remains unavailable

The normal `git push origin agent-3` exited0 at2026-11-04T11:05:42.637019Z,
with server acknowledgement `2f2af3c..55a0c37 agent-3 -> agent-3`. It published
both6db895955472e02328539a9800acecde4b0ee6fe and
55a0c37309bf9dee83e3d3c4bc19b5bf2f1068f4. Notices A3-0074/A3-0075 were delivered.
The live pre-publication blocked/local status is superseded by this receipt;
original checkpoint evidence/messages remain immutable at their commits.

The separate ls-remote and post-publication fetch both failed publickey. This
is a successful server-acknowledged push with failed independent read-back,
not a failed push or a fresh review of peer branches. Local origin/agent-3
matches55a0c37 because the successful push updated it. Remote state after that
acknowledgement and new peer activity remain unverified. Authentication appears
intermittent; no credential/configuration/remote change was made here.

Exact argv, exits, UTC and retained server/error text: receipt.json. This receipt
adds documentation only. The previously measured131 focused/1857 root tests
and195 stable inputs are historical unchanged-source evidence; no test rerun,
new F schedule or gate is claimed. All32 F cases/F gate NOT_RUN; G locked.
