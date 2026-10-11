Message-ID: S2-0019
From: agent-2 (proxy-2, acting for absent agent 2)
To: agent-3 (proxy)
Cc: agent-1
RQ: E
Task: C-E2 SL7 E01 wrong destination and expiry boundary FREEZE, protocol-scope ACK (solo phase)
Type: ACK
Interface-version: v1
Responds-to: S3-0019
Accepted-plan-sha256: d4fa294edd954a137abbb62e34ebfffee2119a87eb6490b81777a555daeb5908
Source-manifest: plan evaluation/evidence/e2/sl7-destination-runner-20261011/integration-plan.json (sha256 d4fa294e..); FREEZE S3-0019 sha256 4489d25b..; evaluation/destination_stress.py bc5cc0f4..; protocol pin 0716a8e2d46f985f35a612d42acaae02ab8701a4, manifest d16ddad8.. (108 entries); repo HEAD bf2d2b9

Summary: **Agent 2 (proxy) ACKs the exact plan d4fa294e.. for the protocol scope. I found no blocker.** Correlated self-review (A1-0059).

**Independent suite run** (not re-run for this message). `export PATH="$HOME/.foundry/bin:$PATH"; .venv/bin/python -m pytest -q -rs -p no:cacheprovider --color=no` at HEAD bf2d2b9 gave exit 0, **1596 passed**, 0 skipped, 453.57 s. It matches S3-0019. The output is at `/home/saiyamjain/.claude/jobs/aed51961/tmp/p2/sl7-full-suite.txt` (sha256 9adfaed7..), outside the repo; only test doubles and port 0 were used.

## Verified (read-only; pin 0716a8e, whose production bytes equal HEAD)

- **Pin.** `owners.protocol` is 0716a8e / d16ddad8.., 108 entries, dict-equal to the pinned manifest and materialized from git blobs.

- **B's adapter** (e1.py `source_instance`).
  - B is a third deployment on the same chain pair, made with the pinned owner commands and checked as same chain ids with contracts distinct from D1 and A.
  - It gets **its own** production `python -m hmbc_protocol.adapter --state-dir <source-instance/private-adapter-state, mkdir 0700> --deployment <B's deployment.json>`, cwd = the pinned protocol snapshot, and its own D49 probe (`probe_b`).
  - B's `prepare_request`, `collect_checkpoint` and `collect_decision` therefore run against B's pinned deployment. A's and B's adapters cannot serve each other's manifests (WRONG_DESTINATION on a different manifest, adapter.py:226-227), and their worker states are fingerprint-separated (worker.py:62-72).
  - **Shared keys, and why they do not change the result.** Both adapters derive the same TEST-ONLY keys from the same labels (`alice`, `witness-1`; keys.py:27-28). That is the intended recipe: B's request is genuinely Alice's for B, and B's certificate is genuinely the configured witness's, signed under **B's** KSSC domain (messages.py:48-49).
  - So the only thing wrong at A is the destination. The frozen code 3 comes from DecisionVerifier step 1 (request.psc / source chain ≠ A's source PSC), before any signature check. Even if a signature step were reached, B's domain-bound signature would not recover to the witness under A's domain.
  - No adapter state is shared.

- **A31.** `_decisions(a, b)` counts `collect_decision` over **both** adapters' exchanges, and the oracle requires exactly 1 for repaired rows and 0 for paper (oracles/destination.py `_decision`, line 49, and 86/114).
  - Wrong destination: B's single decision (A collects none).
  - Expiry boundary: A's single decision.
  - The certificate is collected once, right after the request and B's or A's first checkpoint (`_certificate`).

- **Expiry boundary: the decision expiry equals `request.expiresAt`, robustly, and fails closed.**
  - The witness sets `expiresAt = min(request, checkpoint, DBC now + 30)` (witness.py:140).
  - `request.expiresAt = PBC now + 30` at request build. The checkpoint TTL is DBC now + 60, so it never binds.
  - The decision is collected about 2 s after the request (request mined, then checkpoint accept), so `DBC now + 30 ≈ request.expiresAt + 2`, and the request binds.
  - SL6 measured exactly this: binding = request in all 3 repaired rows, with `collectedDbcNow + 30 − request.expiresAt = 2` (S2-0018). It would only fail if the DBC clock lagged the PBC by more than about 2 s at collection; both are fresh automining Anvils on wall-clock pending time.
  - **If it ever fails, it fails visibly.** The oracle requires `d.expiresAt == r.expiresAt` and `cp.expiresAt > r.expiresAt` (destination.py:106-107), and it requires the decision to be live when collected (line 55).

- **DBC clock pin** (destination_stress.py:133-139).
  - The runner first requires `DBC latest < r.expiresAt`, so a refused overrun is visible.
  - It then calls `evm_setNextBlockTimestamp(r.expiresAt)`, with **no** `evm_mine`.
  - **Between the pin and the consume there is no adapter call.** Only two things run:
    - `steps.check('ADVANCE_CLOCK')`: the `hmbc_protocol.worker_log` exporter, a read-only filesystem/SQLite open that makes no RPC (worker_log.py:29-48);
    - `_save('public-call')`.
  - The adapters never submit transactions under Option A, so no adapter can mine a block. The witness and worker read DBC time only inside `collect_*` and `release`, and none is called in this window.
  - The runner's own submit pipeline does RPC reads and the cast checkpoint, but no mining. The consume is therefore the next mined block, and the oracle **verifies** its timestamp equals `r.expiresAt` exactly (destination.py:101-102). Otherwise the row is refused.

- **D49.** SL7 adapter operations are `prepare_request`, `collect_checkpoint` and `collect_decision` only (`Witness`, no files). `release`, `encrypt_record` and `finish_decryption` are never reached.
  - `_Steps.check` probes **both** A and B (wrong destination) or A (expiry boundary) at baseline and after REQUEST_ACCESS, SUBSTITUTE_DESTINATION or ADVANCE_CLOCK, and FORWARD_OR_CONSUME.
  - Each observation must equal that deployment's first verified never-instantiated record. **No SL7 step instantiates either worker or assumes one exists.**

- **Never-publish (B's material).**
  - B's adapter state (`source-instance/private-adapter-state`) is private, like D2's.
  - B's deployment and bootstrap outputs contain contract addresses, signed certificates, registrations and possession signatures, never a key: the same producer outputs that scanned clean in SL1-SL6.
  - B's adapter `process.json` carries only hashes. Any B worker-probe log is the exporter's refusal message (a path only).
  - My SL7 result review will extend the key and token scan to all `source-instance/` files.

## Exclusions

- Ledger scope (agent 1): DecisionVerifier steps 1, 2 and 9, paper `policyEnf` and its TTL fill, the third deployment's owner commands and funding, and the chain-side effect of the timestamp pin.
- Evaluator internals beyond the points above.
- The classification.
- The P3 destination-binding mutant: not killable by this recipe, as the plan states.

## Caution (not blocking)

The expiry-boundary decision has about 2 s of structural margin between DBC now + 30 and the request expiry. The oracle refuses any other outcome, so a miss is visible, never a silent pass.

Evidence:
- `sha256sum` of the plan, the FREEZE and destination_stress.py;
- python `-I` pin comparison;
- the full suite (above);
- static reading of destination_stress.py:37-152, e1.py `source_instance`/`probe_b`, oracles/destination.py:48-119 and the plan's `destinationProbe.workerPrecondition`, against witness.py:54-67, 100-142, adapter.py:79-190 and 226-227, worker_log.py and messages.py at the pin.

No service was started.

Impact: with A1's ACK and this ACK committed together with S3-0019, agent 3 (proxy) may run SL7. That completes the catalog at 56/56 once run and reviewed.
Action requested: agent 1 commit and clear the run. After the run, agent 2 (proxy) reviews the INTEGRATION_RESULT in protocol scope, including B's material in the key and token scan.
