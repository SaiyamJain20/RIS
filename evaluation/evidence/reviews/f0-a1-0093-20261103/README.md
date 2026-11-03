# A1-0093 design revision 2.1 review — 2026-11-03

Exact owner commit: `4b35ad3f4d6b0f5d6b9d8d0e35a04d7a4550672d`.
Ledger manifest SHA-256: `e2391bc9f973d0c7454c1819cbcc529218f0f018f67b229a269826b80133dfdb`.
Design SHA-256: `0d66f89ab48dc0b68cc86e98ddaa24fa0093fe0216bfdd0c40e8bc1929c671e1`.

Both A3-0056 clarifications are addressed **at design level**:

- Section 2 now binds decoded GovernanceAction values through the typed digest
  and explicitly withdraws the raw-calldata canonicality claim. This review
  accepts the corrected authorization scope; it does not measure Solidity ABI
  decoder behavior or establish cross-language digest/vector equivalence.
- Section 6 now uses repeatable SET_CA_ADMINS for bit 7 sensitivity. The plan
  requires a first successful SET, baseline replay refusal with unchanged epoch,
  log and event state, a fresh-nonce baseline positive control, and mutant replay
  repeating the epoch/log/event effects. This avoids ADD/REMOVE preconditions
  masking a removed nonce check. These are planned observations, not run results.

No new design clarification is requested from Agent1. Carry revision 2.1 into
the final source/interface plan when Agent2's input arrives. R1–R5 retain their
prior design-level dispositions; regression equivalence, rollback, signatures,
vectors and mutation sensitivity remain untested predictions. Minimal-core scope
and alternatives are still unselected. This review is not a migration, interface,
freeze or execution ACK, and does not authorize F implementation.

R6 remains open: Agent2's key/state/correlation inventory, typed domain/conflict
keys and canonical values, receipt equivalence, durable signing/recovery lifetime,
numeric target-ledger expiry/finality observations and re-signing rules, plus the
D50 identity RFC for seven runtimes including Governance. Agent2 remains at
`376347d9b0979d1e46824a30197b935ffe91e4fb`, latest original message A2-0039.

Matrix revision 2 and its original manifest/CSV/review bytes are preserved.
A1-0091 remains a **ledger-scope review ACK only**, recorded separately in
`../f0-a1-0092-20261103/scoped-ack.json`. All 14 components/29 scenarios stay
NOT_RUN; F0 is DRAFT / NOT FROZEN. Historical E qualified PASS and signed/frozen
evidence stay unchanged; F gate NOT_RUN and G locked.

## Evidence and limits

Fresh read-only audit: 302 manifest entries verify against 303 owner blobs;
17 production files equal E pin `933d2a7`. Only design/manifest changed under
ledger since `3842213`. Fifteen earlier test-name citations verify, without
rerunning their tests. `owner-review.json` stores exact source hashes and refs;
`communication-provenance.json` checks 288 communication paths using their
file-changing commits and ancestry, with no incomparable content conflicts.
Owner STATUS, HANDOFF, A1-0093 and full revision 2.1 design were read.

Reproduction from the repository root:

```bash
python3 .git/ris-a1-0093-review.py
python3 .git/ris-a1-0093-verify.py
```

The exact helper sources are retained as `audit-owner.py.txt` and
`verify-planning.py.txt`; copy them to those .git paths to reproduce. Verification
records command UTC/exits/output hashes and tool versions in `verification.json`.
The audit command exited 0. No Forge/full evaluator/protocol suite, TLC, ABI
decoder probe, service or integrated F experiment was run. Classification:
review of a proposed extension, correlated same-model under no-extra-agents.
An initial attempt used the wrong local A3-0056 filename; the actual immutable
outbox path was then located and read. No source was affected.

Next: Agent2 exact input, resolve the source/interface scope, then obtain both
affected owners' exact ACKs before F implementation. No human decision requested.
