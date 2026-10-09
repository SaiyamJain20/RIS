# Subject routing/completion oracle preparation — 2026-10-09 UTC

Paper-derived HMBC2020 reconstruction, synthetic observations, compromised
configured relay stress outside paper secure isolation. This checkpoint adds a
pure independent checker; it does not collect or execute a release/completion,
complete a catalog case, prove ABE secrecy/delivery/durability, or pass gate E.

`evaluation/oracles/subject.py:check_subject_completion` consumes rechecked
pre-release facts and independently collected registered recipient/ciphertext
commitments. D35/A38 routes the symbolic response to grant.gid=Bob while native
grant.recipientKeyHash stays zero. Require distinct nonzero Alice/Bob keys,
original request reference/data/epoch, exact response/cache token commitment,
one fresh Bob intent/send, original expiry and event times, then Bob success and
Alice WRONG_SUBJECT. Whole native state/histories stay unchanged; both completion
observations also preserve the whole worker export. Alice's pending request is
never rewritten or assigned an invented Alice-bound outcome. Repaired-e is
excluded from this stage: its prior WRONG_SUBJECT rollback has no allowed release.

## Actual verification

- `red.json`: new87 tests fail/exit1 because checker is missing.
- `green.json`: same87 pass/exit0 in6.54s.
- `root-suite.json`: `.venv/bin/python -m pytest -q`,777 PASS/exit0 in117.25s.
- `suite-source-before.json` + `audit-final.json`:190 complete inherited
  runtime/config/fixture inputs plus evaluator Python inputs unchanged;303 selected
  owner blobs and15 frozen copies reverified. Frozen FREEZE f700292ec7e3b2c8f2b59c7a728a991cd7d6dea2e4a06cea71f6f6c97b9962a2.
- `mutants-result.json`: six deliberate in-memory removal controls (native state,
  Bob result, Alice error across two paper profiles) admit false observations
  while the real checker rejects them. No source mutation or owner vulnerability.
- `mutant-controls.json` retains script import-path failure1; corrected command
  `env PYTHONPATH=. .venv/bin/python .../mutants.py.txt` exits0. No failed raw
  record deleted or relabelled. A read-only initial peer filename typo (exit128)
  was corrected to the exact0058 owner path; this had no source effect.
- `communication-before/after.json`:174 newest file-changing communication paths,
  no incomparable content conflicts; exact peers e66eeb91caed0119c2c566f60621061699fc5063
  and96ebe16097a551c1f59f4554869e8b735787c738 unchanged. A1-0058 code correction and
  A2-0038 scoped historical replay review remain applicable; neither is a new
  execution-plan/report ACK. Exact worker source/hash in routing-source.json.

Commands, UTC timestamps, elapsed durations, exits and output SHA-256 are captured
by verify.py.txt. Python3.13.13, eth-account0.14.0, jsonschema4.26.0, pytest9.0.2,
Git2.54.0 in audit-final.json; no tool/ABI/dependency/frozen/custody change.
Synthetic observations use canonical hashes/addresses with simplified credential
facts; collector must still authenticate original requests/certificates/native
transactions and registration proofs using pinned public ABIs. The checker does
not authenticate RPC or userKeyRef invocation. Live completion cannot be inferred
from a fabricated successful response in these unit fixtures.

## Review, rulings and remaining work

Author whole-diff/ownership/source/schema review only, weaker than independent;
no extra agents or worktrees under explicit user instruction. Ruling: retain
existing checkout and self-review instead of skill-default worktree/reviewer;
there is a correlated-author blind-spot cost. No other material design choice,
shared interface change or deferred defect.

Public completion collector remains to be implemented: authenticated registered
key and record commitments, response only in memory with redacted commitments,
Bob and Alice calls using the same response and exact frozen key references,
block-anchored snapshots before/after operations, original lifetime preserved.
Run stress on fresh state separate from fresh legitimate Alice/Bob/wrong-admin
controls. Publish a complete revised source/tool/config/fixture execution plan
and FREEZE; BOTH new exact peer ACKs precede services. Old plans do not cover new
evaluator bytes.44 catalog comparisons remain; four paper crash classifications
BLOCKED/unproved. RemainingE01/E02/E03/mutants/revocation windows/RQ1 report and
all-three same-source report ACKs/every gateE criterion still precede F/G.
Historical recovery/expiry/duplicate/replay evidence including failed repaired
expiry remains unchanged. No live services/lease/new FREEZE/human blocker.

Scheduled exclusive mkdir guard and persistent guard PID1141016 plus separate
coordinator flock PID1141117 acquired before fetch; no stale recovery. Finally
cleanup/publication outcome recorded in automation memory/external run record.
Only exact reviewed owned paths on agent-3; preexisting scheduled-runs untouched.
