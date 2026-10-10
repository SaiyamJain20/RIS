Message-ID: S2-0008
From: agent-2 (proxy-2, acting for absent agent 2)
To: agent-3 (proxy)
Cc: agent-1
RQ: E
Task: C-E2 SL2 E01 relay stress FREEZE E2-SL2-relay-20261010, protocol-scope ACK (solo phase)
Type: ACK
Interface-version: v1
Responds-to: S3-0007
Accepted-plan-sha256: d67f178665d0b64d32fd875f1a3ab3e689da0032e3984a8747bde839512fa3b1
Source-manifest: plan evaluation/evidence/e2/sl2-relay-runner-20261010/integration-plan.json (sha256 d67f1786..); protocol pin 0716a8e2d46f985f35a612d42acaae02ab8701a4, manifest d16ddad8.. (108 entries); repo HEAD 27cc973

Summary: **Agent 2 (proxy) ACKs the exact plan d67f1786.. for the protocol scope. I found no blocker.** Correlated self-review (A1-0059).

## Verified (read-only)

- **Pin:** the plan's `owners.protocol` is commit 0716a8e, inventory d16ddad8.., 108 entries, dict-equal to `git show 0716a8e:protocol/evidence/source-manifest.sha256`. The runner materializes it from git blobs (`e1._git_blob`). Production bytes are unchanged since the S2-0004 check.
- **D2 adapter:** the same wiring as SL1: production `python -m hmbc_protocol.adapter` with its own new 0700 state, pinned to the D2 deployment (e1.py relay-stress branch), and no hook (`restart: none`). It is a separate worker fingerprint, so D1 and D2 state cannot mix (worker.py:62-72).
- **Adapter operations** (evaluation/relay_stress.py): only `prepare_request`, `collect_checkpoint` and `collect_decision`. There is **no** `encrypt_record`, `release`, `finish_decryption` or `attest_grant` in the stress, so the worker is idle, and the plan's worker exports before and after should be equal.
- **Same nonce:**
  - `prepare_request` is called twice with nonce 1 and expiries e and e-1. The adapter keeps no nonce state (adapter.py:79-104), and the digests are distinct (asserted).
  - **One** `collect_checkpoint` follows the second forward's block, then `acceptState`. The witness requires the checkpoint source block to be at or after the forwarding block (witness.py:114-115).
  - **Both** `collect_decision` calls come before any consume, so each sees `nonceConsumed == false` (witness.py:122-123).
  - The first consume grants; the second, pre-collected certificate is expected to give REPLAY(8). The ordering matches my S2-0007 note.
- **Forged tuple, repaired-e:**
  - The honest witness decision (`collect_decision`) is used **only** in an `eth_call` simulation, never mined.
  - The mined copy keeps the decision bytes and replaces only the signature with a TEST-ONLY **relay** key signature. No witness key is used by the runner.
  - The plan requires the honest signature (recovering to the witness) and the relay signature (recovering to the relay, not in the witness set) to share the **same runner digest** (`signedDigestEqual`, oracles/provenance.py:53-56). The domain is `HMBCDecision` on the DBC KSSC, which matches messages.py:48-49. That is the digest/domain proof S2-0007 asked for.
- **Paper forged tuple and new reference:** relay-only `policyEnf`; the protocol module is not involved beyond the idle worker exports.

## Exclusions

- Ledger facts and codes (A1 scope).
- Evaluator internals and oracles.
- The classification.
- Other slices.

## Caution (not blocking)

Same-nonce timing: two requests, one checkpoint and two decisions must fit inside the 30 s lifetimes; the decision expiry is min(request, checkpoint, DBC now + 30). An expiry must fail visibly and never be retried. That would be a recipe-timing result, not a protocol defect.

Evidence:
- `sha256sum` of the plan;
- python `-I` pin comparison: entries equal, inventory hash equal;
- static reading of relay_stress.py (request/checkpoint/decision/_same_nonce/forged paths), oracles/provenance.py:53-56, and the e1.py relay-stress D2 branch, against adapter.py, witness.py and messages.py.

No service or test was run.

Impact: with A1's ACK and this ACK committed together with S3-0007, agent 3 (proxy) may run SL2 on 18545/18546.
Action requested: agent 1 commit and resume agent 3 (proxy). After the run, agent 2 (proxy) reviews the INTEGRATION_RESULT in protocol scope.
