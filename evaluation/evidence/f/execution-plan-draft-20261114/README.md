# F execution plan DRAFT — agent 3, 2026-11-14

DRAFT. Authorizes nothing: no service, no integrated run, no FREEZE. Gate F NOT_RUN; all 32 cases NOT_RUN;
G locked. This is my proposal after the E gate precedent (`evidence/e3/gate-plan-20261012`) and the merged
case coverage map (`case-coverage-map-20261114`). Grouping into families is a planning choice, not a protocol result.

`plan-draft.json` holds the machine-readable form: pins, six case families (8+6+4+8+3+3 = 32, each case once),
stages, preconditions and non-goals. Key points:
- Ledger pin is 85c59f5, not the e4e992f named in f_matrix.json (A1-0127; matrix not edited).
- The protocol pin is NOT final: candidate 55f180e, blocked on K1 (A3-0110, ~72% per-run detection, not
  deterministic) and on agent 2 confirming the signing-rule reading (A3-0121). Agent 2 has been silent since A2-0086.
- Family B uses the fault oracle (`oracles/faults.py`); the oracle needs signing-time observations that current
  captures do not all carry. That gap must be closed by the runner before family B can produce verdicts.
- F-25 and F-26 are residual-inventory analysis items and are NOT_EXECUTED by design; F-17, F-18, F-24, F-19 are
  outside-bound or mutation cases and are expected to show violations or trust assumptions, reported as such.
- Stages mirror the E gate: verify pins, source bracket, isolated baselines as controls, per-family integrated runs
  with positive controls first, result classification, post bracket, manifest and E regression, then RQ2-F.md.
Update 2026-11-14 (A3-0128, incorporating ledger review A1-0129): the test-first runner preflight for stages 1–2 now exists in
`evaluation/f_preflight.py`. It verifies the draft's 32 IDs against the exact frozen revision-8
matrix at `evaluation/evidence/reviews/f0-revision8-20261104/f_matrix.json`; coverage matches
32/32 with no missing, extra or duplicate IDs. The first preflight mistakenly used the current
29-row scenario matrix; that artifact is explicitly invalidated and must not be cited.

The draft now carries exact commit/tree candidates for both owner sources, the ledger source
manifest digest, v2 and v2.1 freeze hashes, v2.1 schema hash, matrix and coverage hashes, the frozen
root toolchain-manifest hash, and the F-only TLC jar hash. Preflight reads the ledger manifest blob
from the exact candidate commit. It treats the root toolchain as the frozen E manifest and records
TLC separately as an F-only tool; this avoids changing the E-frozen toolchain file.

The final r4 preflight exits 2 with `BLOCKED`, starts no service and records all 32 cases as
`NOT_RUN`. Every declared source/blob hash matches exactly. The owner commits are not execution
ACKs. Agent 1's A1-0129 review is a scoped review, not a FREEZE ACK; agent 2 has not ACKed. Protocol
K1 and A3-0121 questions remain open.

A1-0129's ledger-scope details are now explicit in the machine-readable plan: v2.1/schema and
ledger-manifest pins; scratch-archive deployment; profiles, complete-details log mode and chain
IDs; secret exclusion; fresh chain pair per case; exact quorum rejection precedence; FL-6 stale
witness-set result; F-24 poison deployment isolation; F-31 `evm_revert` outside the monotone
safe-ledger assumption; and the F-commit `repaired-e` regression choice. This is still a DRAFT,
not an execution authorization.

Next: obtain required owner ACKs before services; close the signing-time capture gap; implement
and verify the remaining runner stages without changing this draft into authorization. Then start
with positive controls and family A, preserving the staged gate sequence. Honest size: the
integrated runner and six families are the bulk of F. Detailed final preflight output and limits:
`../preflight-20261114-r4/README.md`.
