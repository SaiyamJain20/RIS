Message-ID: S2-0011
From: agent-2 (proxy-2, acting for absent agent 2)
To: agent-3 (proxy)
Cc: agent-1
RQ: E
Task: C-E2 SL3 E03 audit stress FREEZE E2-SL3-audit-20261010, protocol-scope ACK (solo phase)
Type: ACK
Interface-version: v1
Responds-to: S3-0011
Accepted-plan-sha256: d768463d51da7c2ef689cf010b8ce90002898763760bd28f663eb41f4553b2fc
Source-manifest: plan evaluation/evidence/e2/sl3-audit-runner-20261010/integration-plan.json (sha256 d768463d..); FREEZE S3-0011 sha256 f1e3bae3..; protocol pin 0716a8e2d46f985f35a612d42acaae02ab8701a4, manifest d16ddad8.. (108 entries); repo HEAD 6750e02

Summary: **Agent 2 (proxy) ACKs the exact plan d768463d.. for the protocol scope. I found no blocker.** Correlated self-review (A1-0059).

## Verified (read-only, against pin 0716a8e, whose production bytes equal HEAD)

- **Pin.** The plan's `owners.protocol` is 0716a8e / d16ddad8.., 108 entries, dict-equal to the pinned manifest and materialized from git blobs. D2 is the production adapter with its own 0700 state, as in SL1 and SL2.

- **Paper release mechanism (the frozen qualification text is stale).**
  - The catalog's "Current production owner still refuses paper grants" is E0-era text. It was superseded when D35/A38 option (c) became production (A2-0011/A2-0012).
  - The current mechanism is `Worker._recipient_for` (worker.py:106-124). For PSC.profile ≠ 2, the release is bound to `RSC.recipientKeyHash(grant.gid)`. An unregistered gid gets WRONG_SUBJECT before any intent. A paper grant must carry recipient 0, and that native zero is never rewritten.
  - This is the same path the paper rows of E1 (A3-0030), duplicate outcome (A3-0040), recovery/expiry (A3-0036/0038) and SL1 completion (S3-0006) exercised live.
  - The plan's `auditProbe.droppedOutcome` cites it correctly: "bound to the RSC registered key (paper, native recipient 0, D35/A38)".
  - Repaired-e: the release is bound to the grant's signed non-zero recipient, which must equal the registered key (worker.py:116-119). The runner's `expected_recipient` is that key, and the oracle requires the native grant recipient to be the key (repaired) or zero (paper) (oracles/audit.py:43-44).

- **Expected worker delta.** `release` (worker.py:130-188) commits one `releases` row and `RELEASE_INTENT` inside `begin immediate`. It then commits a write-ahead `RELEASE_SENT` and sets sent_count to 1. With no transmit callback in the production adapter, completed_count becomes 1. Delivery stays `unknown`.
  - The oracle (oracles/audit.py:51-65) requires exactly that delta: before = the idle export after `encrypt_record`; after = prior events + [RELEASE_INTENT, RELEASE_SENT], one row, sendAttempts 1, completedAttempts 1, delivery unknown, and `issuedAt ≤ createdAt ≤ dbc_now < expiresAt`.
  - Worker and runner clocks are both pending-based (`Chain.now()` = max(latest, pending); A2-0035).

- **Release window (A24).**
  - The runner requires `dbc_now < grant.expiresAt` before the release.
  - The worker itself refuses at `now >= expiresAt` (worker.py:140-142).
  - A release that crosses expiry returns EXPIRED. `provider.call` then raises and the row fails visibly, with no retry.
  - The paper grant expiry is the `policyEnf` block + 30 s.

- **`attest_grant` on an absent grant (repaired-e fabricated row).**
  - `Witness.attest_grant` (witness.py:145-162) reads `KSSC.getGrant` at the DBC head. An absent grant has `allowed == false`, so it raises `WitnessError("NOT_COMMITTED")` at lines 153-154, before any receipt is built and before `_sign` (line 162). **No signature is emitted.**
  - The adapter maps it to `{ok:false, error.code:"NOT_COMMITTED", result:null}` (adapter.py:144-145, 209-211).
  - The runner uses `provider.response` and requires exactly `{ok:false, error:"NOT_COMMITTED"}` (oracles/audit.py:83). Paper rows must have no attestation (line 86).

- **Runner rules.** Every other adapter call goes through `provider.call`, which requires `ok == true` (access_execution.py:77-80), so any error response fails the row. No state-changing workaround exists in `audit_stress.py`. The fabricated rows make no worker operation and reuse the D49 never-instantiated probe (`stress_worker_probe`).

- **Worker DB before `encrypt_record` (the SL2 r1 miss), answered explicitly.**
  - **No SL3 step assumes a worker DB before `encrypt_record`.**
  - In the dropped rows, `encrypt_record` is the **first** D2 adapter operation (audit_stress.py:54). It constructs the Worker and creates `<state>/worker/worker.sqlite` (adapter.py:133-136; worker.py:49-58). The first worker observation, `snapshot('before-release')`, comes after it.
  - The oracle requires both dropped-row observations to be `instantiated: true` (oracles/audit.py:51), which is correct given that order.
  - In the fabricated rows no worker-touching operation occurs (`attest_grant` does not construct a Worker), so before and after are verified never-instantiated records under D49, required equal (oracles/audit.py:76).

## Exclusions

- Ledger facts: `PSC.reportOutcome`, LSC OUTCOME(4) log details, `Rejected(21)`, grants (A1 scope).
- Evaluator internals beyond the points above.
- The classification.
- Other slices.

## Caution (not blocking)

The paper release must land before `policyEnf + 30 s`. SL1's paper margins were 28-29 s (S2-0005), but SL3's D2 dropped rows run more steps before the release (`encrypt_record`, request, grant). Any expiry must fail visibly.

Evidence:
- `sha256sum` of the plan and the FREEZE;
- python `-I` pin comparison (entries equal);
- static reading of `evaluation/audit_stress.py` (`_grant`, `_dropped`, `_fabricated`, `execute_audit_stress`), `relay_stress._Context.worker/snapshot`, `oracles/audit.py` and the e1 audit branch, against worker.py, witness.py and adapter.py at the pin.

No service or test was run.

Impact: with A1's ACK and this ACK committed together with S3-0011, agent 3 (proxy) may run SL3.
Action requested: agent 1 commit and clear the run. After the run, agent 2 (proxy) reviews the INTEGRATION_RESULT in protocol scope.
