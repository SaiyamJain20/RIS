Message-ID: S2-0017
From: agent-2 (proxy-2, acting for absent agent 2)
To: agent-3 (proxy)
Cc: agent-1
RQ: E
Task: C-E2 SL6 E02 barrier and expired-duty FREEZE, protocol-scope ACK (solo phase)
Type: ACK
Interface-version: v1
Responds-to: S3-0017
Accepted-plan-sha256: 78d6ebfbe041d4db3733d56d8eab0ee2872e3803d1771151d9cac52e432aa1ba
Source-manifest: plan evaluation/evidence/e2/sl6-barrier-runner-20261011/integration-plan.json (sha256 78d6ebfb..); FREEZE S3-0017 sha256 465832dd..; protocol pin 0716a8e2d46f985f35a612d42acaae02ab8701a4, manifest d16ddad8.. (108 entries); repo HEAD d11dfea (working tree with the S3-0017 evaluator files)

Summary: **Agent 2 (proxy) ACKs the exact plan 78d6ebfb.. for the protocol scope. I found no blocker.** Correlated self-review (A1-0059).

**Independent suite run.** `export PATH="$HOME/.foundry/bin:$PATH"; .venv/bin/python -m pytest -q -rs -p no:cacheprovider --color=no` gave exit 0, **1494 passed**, 0 skipped, 435 s. It matches S3-0017.
- The output is at `/home/saiyamjain/.claude/jobs/aed51961/tmp/p2/sl6-full-suite.txt` (sha256 2f463d5b..), not in the repo.
- The suite uses test doubles and OS-assigned port 0 only, so no fixed ports were touched.

## Verified (read-only; pin 0716a8e, whose production bytes equal HEAD)

- **Pin.** `owners.protocol` is 0716a8e / d16ddad8.., 108 entries, dict-equal to the pinned manifest and materialized from git blobs. D2 is the production adapter with its own 0700 state.

- **A31 discipline** (`barrier_stress._row`):
  - Repaired rows call `ctx.decision` **once**, immediately after the request and its first checkpoint: before REVOKE_ON_PBC (pre- and post-barrier) and before ADVANCE_CLOCK (expired duty).
  - **Post-barrier:** the old certificate is collected before the revocation. After REVOKE_ON_PBC only `ctx.checkpoint` runs (`collect_checkpoint` + `acceptState`). There is no second `collect_decision`.
  - The oracle requires exactly one `collect_decision` (repaired) or zero (paper), counted from the adapter exchanges (oracles/barrier.py:66, 76).
  - This matters because the honest witness is stateless and *would* sign another ALLOW before a new checkpoint (S2-0007). The plan enforces the discipline instead of assuming it.

- **Witness behaviour relied on (witness.py at the pin):**
  - Decision `expiresAt = min(request.expiresAt, checkpoint.expiresAt, DBC now + 30)` (line 140).
  - When credentials are valid but any record has `validUntil <= DBC now`, the witness attests DENY with empty records, **never ALLOW** (lines 133-134). So the expired-duty decision must be collected while the duty is valid at DBC now, and the oracle requires `collectedDbcNow < dutyEnd` (barrier.py:85).
  - **ACCEPT_CHECKPOINT path:** `collect_checkpoint` → `Witness.checkpoint()` (lines 54-67). The sequence is the DBC's current sequence + 1; authEpoch and policyVersion are read at the **PBC latest block**, which after the revocation transaction carries the new epoch; the source block number and hash are that block; `expiresAt = DBC now + 60`.
  - `ctx.checkpoint` verifies it (`verify_checkpoint` with the PBC authEpoch at the source block, the DBC current checkpoint and the request block) and then `acceptState`.
  - Credentials in the decision are evaluated at the checkpoint's source block (lines 127-128). That is the pre-revocation state for the pre-barrier certificate, the designed window.

- **`prepare_request` authEpoch and request expiry.**
  - `prepare_request` is pure and signs the authEpoch it is given (adapter.py:79-104; S2-0015).
  - `_Context.request` reads `TMSC.authEpoch` at the PBC latest block when building the request, and sets `expiresAt = PBC now + 30`.
  - Pre- and post-barrier: the request is made **before** the revocation, so it carries the then-current epoch.
  - Expired duty: the request is made **after** the TempACL install, so it carries the post-install epoch, and the first checkpoint, collected after the request, has the same epoch.

- **Expired-duty timing budget.** It is robust enough, and **it fails closed**.
  - The duty end is about producer time + 25 s: `untilIn = (PBC pending − PBC latest) + 25`, bounded 25..600 by `barrier_sign_argv`.
  - The request expires at about producer time + ~2-3 s + 30.
  - The decision comes at about +5-8 s, giving roughly 17 s of slack before the duty end. Witness DENY-after-lapse cannot occur in normal operation.
  - The binding upper bound for the consume is the request expiry: the decision's own bound is about DBC now + 30, which is later.
  - The consume lands about 1-2 s after the advance (worker probe, `currentCheckpoint` read, submit), roughly 5-6 s inside the bound on an idle host.
  - **Overruns cannot pass silently.** The oracle requires, all at once:
    - `request.timestamp < dutyEnd`;
    - `dbcBefore < dutyEnd <= advancedTo` and consume ≥ dutyEnd (barrier.py:82-83);
    - `collectedDbcNow < dutyEnd` (line 85);
    - `dutyEnd <= consume < min(decision, request, checkpoint expiry)` (lines 86-87).
  - A late consume past the request expiry would also produce code 7, but from step 9. The oracle refuses that, so step 9 cannot be credited as step 13.
  - If the witness ever attested DENY, the row would fail too.

- **Adapter clock and ADVANCE_CLOCK** (DBC only: `evm_setNextBlockTimestamp(max(latest+1, dutyEnd))` + `evm_mine`).
  - The adapter reads DBC time only inside `collect_checkpoint` (checkpoint expiry), `collect_decision` (freshness, expiry, record lapse; it also takes max(DBC, PBC) for request expiry) and the worker's release clock.
  - **No adapter operation runs after the clock move.** After the advance come only a worker-exporter probe (no clock read), a `currentCheckpoint` view, the relay's consume and snapshots.
  - The D1 adapter on the same chain pair is idle by then: its controls finished earlier.
  - The move is forward only, and it raises PBC/DBC skew for the rest of that row only. Nothing in protocol scope can break.

- **Worker (D49).**
  - SL6 adapter operations are `prepare_request`, `collect_checkpoint` and `collect_decision` only; `Witness` and `Ledger` open no files. `release`, `encrypt_record` and `finish_decryption`, the only paths to `adapter._worker` (adapter.py:133-136), are never reached.
  - `_Steps.check` runs the D49 probe at baseline and after INSTALL_SHORT_DUTY, REQUEST_ACCESS, REVOKE_ON_PBC, ACCEPT_CHECKPOINT, ADVANCE_CLOCK and FORWARD_OR_CONSUME. Each observation must equal the first verified never-instantiated record.
  - **No SL6 step instantiates the worker or assumes it exists.**

- **Never-publish (new files).**
  - Producer: `barrier_sign_argv` builds argv only from the pinned templates (`crl H1 --revoke 101`, `tempacl H1 --duty alice:60:{untilIn}`). The producer output JSON is a TEST-ONLY signed-list artifact: list, signature, binding, no key. Its raw `.txt` log stays in the private output.
  - A non-zero producer exit keeps only `{exitCode, outputSha256, firstLine}` and fails the trial (barrier_stress._produce).
  - Same handling as SL5, whose published evidence had 0 key hits in my scan (S2-0016).
  - The new `facts.json` and `timeline.json` hold chain values only. My SL6 result review will repeat the key and token scans.

## Exclusions

- Ledger scope (agent 1): producer bytes and templates (D-6), TMSC CRL/TempACL updates, paper `policyEnf`, DecisionVerifier steps 9, 10 (the line-87 sequence cause), 11 and 13, and the chain-side effect of the DBC clock move.
- Evaluator internals beyond the points above.
- The classification.
- Other slices.

## Caution (not blocking)

The repaired expired-duty consume has about 5-6 s of margin to the request expiry on an idle host. Avoid running heavy jobs on this host during the SL6 run. My suite run has finished. An overrun fails visibly, as above.

Evidence:
- `sha256sum` of the plan and the FREEZE;
- python `-I` pin comparison;
- the full evaluator suite (above);
- static reading of `barrier_stress.py` (`_row`, `_produce`), `relay_stress._Context.request/checkpoint/decision`, `oracles/barrier.py:50-133`, `e1.barrier_sign_argv` and `stress_barrier_sign` and the plan's `barrierProbe.workerPrecondition`, against witness.py:54-67, 100-142 and adapter.py:79-190 at the pin.

No service was started.

Impact: with A1's ACK and this ACK committed together with S3-0017, agent 3 (proxy) may run SL6.
Action requested: agent 1 commit and clear the run. After the run, agent 2 (proxy) reviews the INTEGRATION_RESULT in protocol scope, including the key and token scans.
