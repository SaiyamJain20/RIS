# A2-0065 RPC view review — 2026-11-06

**C-F1 remains WORKING; integrated execution remains LOCKED.** This is a
synthetic source review of a paper-derived HMBC2020 reconstruction.

Source/publication: `3b86183b8f537e32fc2f2c3be8b650735ab8173a`; new RPC module's
file-changing commit: `90bfac1` (full hash in inputs-before.json). Agent1 remains
`8c0285ffa6986858caeb0140b930bf5db759fdc0`; ledger READY source `85c59f5` is
unchanged. The21changed paths since A2-0064 are pinned individually, including
A2-0065, ABI copies and owner live/mutation logs. This delta has **no owner runtime
READY**. Agent3's434entry inventory is review provenance only.

Fresh results:

- **2072 PASS / 201 SKIP / 206 DESELECT**, exit0; pytest42.25s, command42.663s.
  All26new synthetic RPC tests are included; all7new live tests are excluded.
  Scope skips are200ScenarioResult and1FileHash. Exact IDs/reasons are retained.
- **15 independent public-API controls pass.** Twelve diagnostic property probes
  show8permissive acceptances. `0x1_0` becomes`16`; trailing ABI data and a
  non-minimal dynamic layout are tolerated. No altered authorization or binding
  value is shown. Four negative/signed/space/negative-block suspicions are refuted.
- Default9export files match. No live test or owner mutation result independently
  rerun; no full owner/evaluator root rerun, new E parity, timing or F gate claim.
- All434owner source entries,248selected local inputs and4review helpers remain
  unchanged across testing.429ledgerREADY entries/52F0pins/31publishedfiles/
  7copiedABIs/4interfacefixtures verify.376communication paths; no divergent
  revisions. Previous408entryREADY verifies at its original source/publication;
  only its af2-state README differs at the later source.

See [REVIEW.md](REVIEW.md) for the owner parser finding, ABI-prose limitation,
positive controls, refuted suspicion and pending runtime duties. A2-0065's Foundry
correction and reported live deployment results are recorded as owner evidence,
without adoption of the test totals. D56's additional evaluator Governance reads
remain separate from D50 S0; no request count or shared interface changed.

Exact commands/UTC/exits/output hashes: commands.json and lossless `*.txt.gz`.
Complete source/delta/tool/fixture provenance: inputs-before.json and
communication-provenance*.json. Final verification: verification.json SHA256
`7cd1e2c0dfd6d3c46525a9f0e6cfde98a47d43487196720a989aea9d8ed08b99`. All7recorded commands exit0; verification checks the prior6
commands' raw/compressed hashes. Tools: Python3.13.13, Git2.54.0, pytest9.0.2,
jsonschema4.26.0, eth-account0.14.0, eth-abi6.0.0. Environment is inherited with
explicit review paths; environmentSha256=null is not a full environment capture.

Reproduce with record.py/audit.py before, probe.py, the exact isolated/export
argv in commands.json, audit.py after/peers and the saved verification command.
`before` refuses an existing scratch snapshot. no_live.py excludes chain/build/
completeness fixtures and guards their setup; local fake HTTP fixtures are used.
No existing evaluator consumer, frozen interface, dependency or peer source is
changed. No additional agents or worktrees. Author review remains correlated.

Full runtime READY/mapping and separate exact execution FREEZE ACKs still precede
services/scenarios. Historical qualified E unchanged;32Fcases/GateF NOT_RUN/G
locked. A3-0091 communicates the source review and owner action. No human action.
Publication and persistent-file lock cleanup are verified in automation memory.
