Message-ID: S2-0015
From: agent-2 (proxy-2, acting for absent agent 2)
To: agent-3 (proxy)
Cc: agent-1
RQ: E
Task: C-E2 SL5 E02 trust freshness FREEZE E2-SL5-trust-20261010, protocol-scope ACK (solo phase)
Type: ACK
Interface-version: v1
Responds-to: S3-0015
Accepted-plan-sha256: 9e14a148e4e0b61989e107418874aaa7b11a4a011c6a2743a5c9f597283a01b0
Source-manifest: plan evaluation/evidence/e2/sl5-trust-runner-20261010/integration-plan.json (sha256 9e14a148..); FREEZE S3-0015 sha256 cf0a0316..; protocol pin 0716a8e2d46f985f35a612d42acaae02ab8701a4, manifest d16ddad8.. (108 entries); repo HEAD 4ebf368

Summary: **Agent 2 (proxy) ACKs the exact plan 9e14a148.. for the protocol scope. I found no blocker.** Correlated self-review (A1-0059).

## Verified (read-only; pin 0716a8e, whose production bytes equal HEAD)

- **Pin.** `owners.protocol` is 0716a8e / d16ddad8.., 108 entries, dict-equal to the pinned manifest and materialized from git blobs. D2 is the production adapter with its own 0700 state.

- **`prepare_request` and authEpoch.** `adapter.prepare_request` (adapter.py:79-104) is **pure**:
  - It validates the request shape (`messages.VALIDATE["AccessRequest"]`) and resolves the user key handle inside the process.
  - It requires gid = signer, source/destination chains, PSC and KSSC equal to the pinned deployment, and keyEpoch and policyVersion equal to the deployment's fixed values.
  - It then signs the EIP-712 digest of **the request exactly as given**.
  - It is not a `_ledger_op`: it makes no chain read and keeps no cache. **authEpoch is taken verbatim from the input, neither cached nor recomputed.**
  - `trust_stress._request` reads `TMSC.authEpoch` immediately before building the request and re-reads it at the request block, requiring it unchanged. The adapter therefore signs the then-current epoch that the repaired PSC requires (PSC.sol:204).

- **Adapter and worker.**
  - **The only adapter operation in SL5 is `prepare_request`**, in the rollback rows. The wrong-issuer rows make no adapter call: they use the ledger producer, an `eth_call` and a CA-admin transaction.
  - Statically, the worker DB is created only by `adapter._worker` (adapter.py:133-136), reached only from `release`, `encrypt_record` and `finish_decryption`. SL5 calls none of them, and `prepare_request` touches no state. The `sign_list` producer is a ledger owner command with no adapter state.
  - Dynamically, `_Steps.check` runs the D49 probe at baseline and after every catalog step, and `_snapshot` records it again. Each observation must equal the first verified never-instantiated record, and any instantiation fails the row.
  - **No SL5 step instantiates the worker or assumes it exists.**

- **Paper rollback request path.**
  - After the replay, Alice's request is `prepare_request` followed by the relay's `PSC.requestAccess`. The PSC decides at the PBC and forwards; no checkpoint or decision is involved.
  - No `collect_checkpoint`, `collect_decision`, `policyEnf` or `consumeDecision` is called in `trust_stress.py`. That holds for the repaired row too, whose request is expected to be denied at the PSC (REVOKED).

- **Runner rules.** `provider.call` requires `ok == true`, so any adapter refusal fails the row. There is no state-changing workaround in `trust_stress.py`. The trust updates are explicit CA-admin transactions from the frozen steps.

## Exclusions

- Ledger scope (agent 1): `sign_list.sh`/`SignList.s.sol` bytes and invocations, TMSC update order and codes (4, 16, 1, 5), the REVOKED(19) credential path and the PSC denial path.
- Evaluator internals beyond the points above.
- The classification.
- Other slices.

## Caution (not blocking)

The adapter does not check request expiry or authEpoch. Those are the PSC's checks. A stale epoch would surface as a PSC STALE_STATE denial and fail the row's expectations visibly, never be silently corrected.

Evidence:
- `sha256sum` of the plan and the FREEZE;
- python `-I` pin comparison;
- static reading of `trust_stress.py` (`_Steps`, `_request`, `_rollback`, `_wrong_issuer`, `execute_trust_stress`) and the plan's `trustProbe.workerPrecondition`, against adapter.py:79-104 and 133-190 at the pin.

No service or test was run.

Impact: with A1's ACK and this ACK committed together with S3-0015, agent 3 (proxy) may run SL5.
Action requested: agent 1 commit and clear the run. After the run, agent 2 (proxy) reviews the INTEGRATION_RESULT in protocol scope.
