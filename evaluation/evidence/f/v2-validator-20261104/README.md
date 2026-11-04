# C-F1: first successor validator slice

This is an isolated, synthetic evaluator result for the HMBC2020 paper-derived
reconstruction and its accepted F extension. It is not a measured F schedule,
module READY acceptance, integrated regression or passing research gate.

`evaluation/schema_v2.py` explicitly consumes the published v2 schema. Existing
`evaluation/schema.py`, its E consumers, frozen v1, all proposals and the14
published v2 payloads remain unchanged. No dependency or producer is switched.

The68 focused tests pass. They preserve all12 frozen checkpoint wire examples,
four operation-specific pool successes and three fixed D50 binding vectors, and
reject malformed uints, nonascending governance admins, bad immutable ranges or
hashes, inconsistent profiles/sets/masks, illegal q2 mutants, bad export hashes,
incorrect retry partitions/selection/timing, nested credential-order corruption
and duplicate-key/nonfinite/oversized JSON. Exactly2000ms reserve skips;
2001ms permits a declared send. This is field consistency, not observed timing.

RED67 failed/1passed against unimplemented stubs. The first implementation run
had67passed/1failed because the test fixture put an all-replied event at the
forbidden5000ms boundary. The fixture was corrected to1000/999ms; no runtime
bound or expectation was relaxed. The original RED output is preserved losslessly
as gzip with both compressed/raw hashes. It expanded a1MiB parametrized input;
the final tests use short case IDs. See REVIEW.md and exact commands.json/logs.

Fresh root evaluator suite: **1726 passed in393.55s, exit0** (393.817s command
wall time). `inputs-before.json` pins193 local source/schema/vector/config inputs
plus tool versions and fetched peer refs. `audit.py after` passed with all193
unchanged; exact results are in verification.json and root-suite.txt. This is
extension implementation test evidence, not an integrated E/F regression.

Initial successful fetch reviewed Agent1 at
`aef3daa5ebbe434f97b016719f8762d4aaf09441` and Agent2 at
`5639e8f638645acf0bf122109f8bae2ffc2b6fc4`. All418 ledger manifest entries,
142 historical protocol entries and52 F0 pins verify at their exact owner
commits;344 communication paths have no incomparable-content conflict. Owner
logs describe316 Forge tests,13 A-F1 controls and26 v2 vector checks, but were
only read/hash-verified here, not rerun or adopted. The HEAD powers-inventory
check intentionally exits1 against changed F source; its historical check exits0.
The newest owner outboxes remain A1-0110/A2-0058 (design freeze ACKs). A commit
title containing READY and a refreshed manifest do not supply a source READY
handoff. No peer source was consumed for execution or changed.

Refresh fetches then failed with SSH public-key authentication errors; the
agent reported no loaded identities. The connected GitHub account returned404
for this repository. See publication-blocker.json and retained failed commands.
No authentication/configuration/remote was changed. New remote state after the
successful initial fetch is unverified. An unpushed message is not delivered.

Still required: anchored B reconstruction/getters/wiring/fixture joins, signature
recovery, full exporter-history/completeness and WAL/native joins; the fault
oracle/model; exact owner source READY and separate complete execution FREEZE
ACKs before services/scenarios. All32 F cases remain NOT_RUN; G locked and the
qualified historical E record unchanged. No services, Forge/TLC/ProVerif/RPC,
integrated F/E run or new gate result in this slice. Self-review is correlated;
no extra agents, worktrees, peer edits, deployment or main push.

Reproduce the focused checks from the repository root in the existing environment:

```sh
.venv/bin/python -m pytest evaluation/tests/test_schema_v2.py -q
.venv/bin/python -m pytest -q
```

The full root suite selects evaluation/tests via pyproject.toml; it is not the
owner protocol/ledger suites or an integrated F/E gate.
