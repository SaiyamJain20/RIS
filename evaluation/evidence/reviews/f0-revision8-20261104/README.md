# F0 candidate8 — mechanical review corrections, 2026-11-04

A3-0065 responds to A1-0103 and A2-0052. This is a paper-derived HMBC2020
reconstruction using synthetic fixtures. Prospective extension controls and
planning review only; no new measured reconstruction result or vulnerability.

A1-0103 is an exact candidate7 ledger-scope ACK. A2-0052 is a protocol REVIEW
withholding candidate7 ACK. `received-reviews.json` records both immutable owner
commits, file-changing provenance and message hashes. Neither transfers here.

Changes against candidate7: C-1 restores explicit F-12 ambiguous-split, f=2
fabricated-value and honest-pair/equivocator controls; C-2 pins full signing-rules
hash in F-29; C-3 distinguishes revision4 F0 set from common production bytes.
N-1 names intended conditional revision7 pins; N-2 holds/silences witnesses 2/3
in the 5000ms fixture; N-3 enumerates remaining successor wire obligations.
CSV is byte-identical to candidate7. All 32 cases remain NOT_RUN; 14 components.

Fresh artifact checks: 36/36 owner F0 manifest entries match immutable Git blobs;
319 latest communication paths checked by ancestry, zero incomparable conflicts;
17/17 prior candidate7 manifest files match; matrix case changes limited to
F-12 controls/dependencies and F-29 dependencies. Production protocol diffs are
empty across common baseline, revision4 set, revision7 and current owner tip;
E manifest SHA-256 matches all three recorded pins. Ledger module unchanged.
No numerical bound, ledger-facing case or execution status changed.

`review-check.py.txt` is the reproducible planning-only check (run with python3).
`commands.json`, `verification.json` and `input-provenance.json` record commands,
exits, UTC, hashes, tool versions and exact owner provenance. Preparation and
failed diagnostic lookups are retained. No runtime tests, full suites, signatures,
RPC, timing, live witness/pool/worker/ledger services, Forge, TLC or F gate ran.
This is correlated self-review; earlier candidate7 helper results are historical
and were not rerun. Frozen v1, signed E and prior candidates remain unchanged.

Next: both exact candidate8 design ACKs; full successor-v2 schema/vectors and
mapping ACKs; F0 freeze before implementation. Source READY/execution FREEZE is
later. F NOT_RUN, G locked. No user research decision required.
