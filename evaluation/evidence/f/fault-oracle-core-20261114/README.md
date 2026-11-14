# Fault oracle core (single-signing / certificate agreement) — agent 3, 2026-11-14

Classification: tested reconstruction logic on synthetic records. NOT a measurement of any
implementation, NOT connected to real captures yet, NOT Gate F. Same-model author.
Files: evaluation/oracles/faults.py, evaluation/tests/test_fault_oracle.py (hashes.txt).
Rule source: agent 2's protocol/f0/SIGNING-RULES.md sections 1, 2, 6 as READ by me (A3-0121); agent 2
has not confirmed the reading. The oracle needs signing-time observations (timestamp, DBC sequence,
governance nonce, grant exists, outcome recorded) that the existing captures do not all carry.

Behaviour: `single_signing_violations` flags a witness that signed a different effect under one key
while an earlier digest was not dead (expiry; checkpoint sequence overtaken; governance nonce
overtaken; decision sequence overtaken or ALLOW with a grant; receipt outcome recorded).
`certificate_conflicts` classifies conflicting certificate pairs: no-common-signer, byzantine-explained,
violation (blame list), legal-resign. Consequence recorded in RQ2-F-DRAFT: DENY/ALLOW on one request is
not by itself an agreement violation.

Method: tests first (collection error = red), then module: 12 tests pass. Mutation check: 10 deliberate
mutants (expiry >=->>, checkpoint >=->>, drop grant clause, grant applies to DENY, decision >->>=, nonce
ignored, receipt never dead, same effect conflicts, Byzantine not excluded, blame ignored) all DETECTED
with the bytecode cache removed per mutant; control after restore 12 passed; restored file byte-identical.
Full evaluation suite, clean rerun (PYTHONDONTWRITEBYTECODE=1, `python -I -B -m pytest -q`): 2968 passed,
exit 0, 643 s (`root-suite.log`; 2956 before + 12 new).

Failed trial kept: my first mutation loop and the first full run (1 failed, 2967 passed; test
`..._names_that_witness`) were INVALIDATED. Cause: the last mutant (`if blame` -> `if False`) has the same
file size as the original and was written in the same second, so Python reused the mutant's stale
`.pyc`; the source was correct (traced line by line; clearing the cache gave 12 passed). The harness now
removes the cached bytecode per mutant. The earlier "10 of 10 detected" claim is superseded by the rerun above.
