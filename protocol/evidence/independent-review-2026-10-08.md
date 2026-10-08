# Independent adversarial review of agent-2's protocol module (2026-10-08)

**Reviewer:** a separate read-only subagent (instructed not to edit the repository), launched at the user's explicit permission to fan out parallel agents.
The project's own instruction files say "do not launch extra agents"; the user overrode that for this session, so this review is **not** one of the three
persistent project agents and is **not** a peer review. It reviewed commit 2f9f0bb plus uncommitted working-tree edits, ran 36 hand-made mutants and 11
reproduction tests in a scratch copy, and reported 15 items. Its full output is not stored; this table records the disposition of each item.
Author self-review plus a same-session reviewer is still weaker than a review by another project agent: agent 1 independently reviewed `witness.py`
(A1-0017) and found one issue, which is item A below.

| # | Severity | Finding | Disposition | Where |
|---|---|---|---|---|
| 1 | HIGH | The per-request `deploymentManifest` was the trust root of the witness and worker (a runner could point RPC at a mock node and get a signed ALLOW). | **Fixed.** The adapter pins a deployment at startup (`--deployment`); any different manifest answers `WRONG_DESTINATION` before any connection; ledger operations are `ADAPTER_UNAVAILABLE` without one; worker state is bound to the deployment fingerprint. | `adapter.py`, `worker.py`; `test_adapter_hardening.py`, `test_worker_hardening.py` |
| 2 | MEDIUM | "Now" came from the latest block's timestamp, so an idle DBC wedged checkpoint signing. | **Fixed.** `Chain.now()` = max(latest, pending block); witness uses it. | `chain.py`, `witness.py`; `test_chain_hardening.py` |
| 3 | MEDIUM | Same clock in the worker: a 30 s grant stayed releasable after 5 idle minutes. | **Fixed** (same `now()`; adapter passes `led.dbc.now`). | `worker.py`/`adapter.py`; `test_worker_hardening.py` |
| 4 | MEDIUM | Witness signed ALLOW the DBC would revert: (A) records lapsed by DBC `now`, (B) nonce already consumed. | **Fixed.** (A) signs DENY with empty records; (B) refuses `REPLAY`. Plus policy-aware result (A1-0017). | `witness.py`; `test_witness_hardening.py`, `test_witness_policy.py` |
| 5 | MED/LOW | One invalid UTF-8 byte on stdin killed the adapter; unbounded line buffering. | **Fixed.** Binary bounded `readline`; one MALFORMED response; stream resynchronises. | `adapter.py`; `test_adapter_hardening.py` |
| 6 | LOW | `encrypt_record` select-then-insert race (27/150 raw `IntegrityError`). | **Fixed** (`begin immediate`; init serialised with a file lock, found by the new test). | `worker.py` |
| 7 | LOW | Loopback allowlist bypassable via redirects/proxy env; `Chain()` validated nothing. | **Fixed.** `Chain` validates the URL; opener has no proxies and no redirects. | `chain.py`, `ledger.py` |
| 8 | LOW | Raw exceptions: 4300-digit ints, `:99999` port, reply without `result`, non-hex revert data. | **Fixed** (length guard, `validate_url`, strict `_hex`, malformed-reply handling). | `eip712.py`, `chain.py` |
| 9 | LOW | Forwarding tx `to` not pinned to the PSC; destination chain/KSSC not checked. | **Fixed** (tx.to pinned; destination checked). Destination check is unreachable with the real PSC (documented equivalent mutant). | `witness.py` |
| 10 | LOW | `encrypt_record` has no caller authentication; first writer wins for a dataId's `payloadDigest`. | **Open, interface-level.** The ACSC pins owner and policy but not the payload commitment; authenticating the registrant needs an interface change (not made). Stated limit for E. | A2-0009 |
| 11 | LOW | Signature self-checks used `assert` (stripped by `python -O`). | **Fixed** (explicit errors in witness, client, adapter). | `witness.py`, `client.py`, `adapter.py` |
| 12 | LOW | Second worker transaction had no rollback. | **Fixed.** | `worker.py`; `test_worker_hardening.py` |
| 13 | tests | Guards no test exercised. | **Closed where reachable** (expired request, checkpoint expiry, status-2 REPLAY, attest after outcome, expiry boundary, recipient/keyEpoch noted as unreachable on repaired-e, loopback hostnames, state-dir permissions). Unreachable guards are listed as documented equivalent mutants in `protocol/tools/mutation_check.py`. | tests |
| 14 | flake | `ttl-too-long` (31 s) test and the 60 s session bound. | **Fixed** (45 s; setup/time from a fresh block; `now()` removes the 60 s bound). | tests |
| 15 | tests | Crash tests are in-process; pragmas and concurrency untested. | **Partly closed.** Pragmas and 8-thread release/registration concurrency are tested. Crash tests remain logical-commit-order evidence, not power-loss evidence (stated limit). | `test_worker_hardening.py` |

Additional defects found while fixing (not in the review): `chain.send` signed with a non-checksummed `to`; `setup_pbc` derived time from a stale head block (flaky
20 s duty window); two tests relied on a one-second difference to make digests differ.

A. (agent 1, A1-0017) the witness ignored the DBC policy; fixed test-first.
