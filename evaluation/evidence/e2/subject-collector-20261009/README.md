# Subject pre-release public collector —2026-10-09 UTC

Paper-derived HMBC2020 reconstruction, synthetic fixtures, compromised configured
relay stress outside the paper secure-isolation assumption. No live trial or full
catalog/gate result. The existing independent oracle/classifications are unchanged.

## Changes and actual verification

`evaluation/subject_substitution.py` consumes the public ABI/native executor and
read-only worker exporter. `execute_access(subject_substitution=<Bob GID>)` runs
its already checked Alice request, historical credentials/policy and repaired
checkpoint/ALLOW certificate, then stops at this collector before any release.
Only forwarded gid changes. Original signature/body/bundle/credentials/certificate
remain. Collector repeats user/witness signature recovery; matches the original
mined request and substituted ACSC transaction against exact calldata, contract,
relay and native block. Whole request/grant/nonces(Alice and Bob)/access count/worker
and decoded all-deployment histories use explicit block-anchored read groups.

Paper expected one Bob grant under the original derived grantId, zero native
recipient and30s native TTL; repaired expected mined status0/Rejected2/no receipt
logs/full rollback. Both retained in synthetic tests; these are classifier checks,
not findings. Invalid same-GID, malformed-address, Bob-control, crash, nonce-replay
and duplicate-outcome selections refuse before request/adapter side effects.

Commands, argv, UTC, elapsed time, exit codes and stdout/stderr hashes are in each
named JSON sidecar. Raw outputs, including failures, are preserved:

| Check | Exit / result |
|---|---|
| `red`: new collector tests before code |1 /12 failed, missing option |
| `green-initial` |1 /11 passed,1 fixture lookup collision |
| `green-corrected`: collector+oracle+access tests |0 /104 passed |
| `bundle-red` → `bundle-green` |1 /2 failed12 passed →0 /14 passed |
| `selection-red` → `selection-green` |1 /6 failed14 passed →0 /20 passed |
| `suite`: `.venv/bin/python -m pytest -q` |0 /690 passed110.48s;65 Python inputs |
| `suite-complete-bracket` |−15 /aborted22.33s; not a result |
| `suite-final`: same root command |0 /690 passed109.90s;124 complete inputs |
| `complete-audit` |0 /124 unchanged,303 owner blobs,15 frozen copies |
| `publication-fetch` |0 /peer tips unchanged |

Initial fixture reused hashes across chains, allowing DBC checkpoint calldata to
overwrite a PBC request in a shared lookup. Fixed fixture lookup to `(chain,hash)`;
no decoder workaround. Review detected missing original credential-bundle join and
late invalid-selection checks; RED/GREEN controls prove both fixes. Initial full
suite passed but its manifest covered65 Python files only; widened to124 source,
fixture, interface and config inputs. The first widening command used system
Python and failed importing eth_utils; aborted only owned pytest1114811 and saved
exit−15, then generated the inventory with `.venv/bin/python` before the final
suite. `bracket-setup-failure.json` and `progress.md` retain this mistake. A later
wrapper label `audit-final` collided with its existing output and refused before
execution; preserved original as `audit-initial.json`, ran `complete-audit` instead.
No source changed across final suite; no later code edit. Documentation-only
checkpoint writes follow verification; no unnecessary full rerun after prose.

## Source, tool, fixture and peer evidence

`audit-final.json` records Python3.13.13, eth-account0.14.0, jsonschema4.26.0,
pytest9.0.2 and Git2.54.0; exact source and fixture hashes in
`suite-source-before.json`, output hashes in command records. Frozen
FREEZE SHA-256 f700292ec7e3b2c8f2b59c7a728a991cd7d6dea2e4a06cea71f6f6c97b9962a2.
Owner inventories remain ledger933d2a7/c7b7dd51..195 and
protocol0716a8e/d16ddad8..108; all303 immutable selected Git blobs verified.
Frozen WRONG_SUBJECT2/WRONG_DESTINATION3 independently checked. No peer source,
ABI, interface, custody, dependency or tool change; no external deployment.

`communication-publication.json` records173 newest file-changing revisions across
all three fetched branches/no incomparable differing content. Owner messages read
through A1-0058/e66eeb91/1e3644dd.. and A2-0038/96ebe160/e02ca3d8.. unchanged;
exact copied reviews retained. These are not plan/report/gate ACKs. The initial
unlogged fetch command yielded a session without retained output; a separately
awaited fetch completed0 and the abandoned owned fetch processes were terminated.
No source movement/publication occurred in that interval. Final logged fetch0
rechecked peer tips. Branch agent-3/base fbebab747ca4b6b9e41e346f412ba6038f7074d7.

## Limits, review and continuation

Full subject cases remain NOT_RUN. Collector stops before release; `releaseTested`
is false. Next: registered Bob response routing, unchanged zero native recipient,
Bob symbolic completion/Alice WRONG_SUBJECT, original expiry, no Alice-bound audit
fabrication; separate fresh chains/state for legitimate Alice/Bob/wrong-admin
controls, complete revised execution-plan inventory and BOTH NEW exact peer ACKs
before services. Source review of pinned worker routing is in
`next-routing-source.json`; it is not measured release evidence. Old plan ACKs
cannot authorize changed collector bytes.44 comparisons, live mutants/windows,
RQ1 report/all3same-source ACKs/every gateE criterion remain; F/Glocked. Four paper
crash classifications remain BLOCKED/unproved. No ABE, actual encrypted delivery,
provider integrity, consensus, authors-implementation or power-loss claim.

Rulings: confirmed checkout and author review honor the human ban on worktrees/
extra agents (cost: correlated review blind spots); coherent pre-release checkpoint
leaves full case unproved (cost: later execution still required); existing normal
agent-3 push authorization applies (cost: branch checkpoint only, no main/PR).
No unresolved material review finding within this bounded stage; review in
`author-review.json`. No service/freeze/lease active. Exclusive scheduled guard
PID1093836 and separate coordinator flock held before fetch through publication;
finally cleanup/remote SHA recorded in automation memory/external run. Preexisting
untracked scheduled-run evidence preserved unstaged. No stale lock recovery.
