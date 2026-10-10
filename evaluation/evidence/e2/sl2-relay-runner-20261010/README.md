# SL2: E01 relay-stress runner and plan (no services yet)

Paper-derived HMBC2020 reconstruction. Synthetic only. E/RQ1 is active; gate E is NOT_RUN; F and G
are locked.

Author: agent 3 (proxy), solo phase (A1-0059, A1-0061, A1-0064). **Correlated self-review.**

**Status:** runner implemented test-first and unit-verified; plan frozen as S3-0007. No service,
chain, adapter or worker has run. **No catalog row is completed by this checkpoint.**

## Rows and frozen expectations, checked against the pinned ledger source (933d2a7)

| Row | Frozen expected | Ledger fact (pin) | Agreement |
|---|---|---|---|
| E01-forged-tuple-paper-strict / -paper-minimal | ACCEPT / SPEC_GAP | `ACSC.policyEnf` (ACSC.sol:140-167) grants any relay tuple whose records satisfy the policy; TTL `ts+30`, recipient 0 | yes |
| E01-forged-tuple-repaired-e | REJECT / REPAIR_SUPPORTED / BAD_SIGNATURE | DecisionVerifier step 6 → `QuorumLib.verify`; signer not in the witness set gives BAD_SIGNATURE (SigLib.sol:47) | yes |
| E01-new-reference-replay-paper-strict / -paper-minimal | ACCEPT / SPEC_GAP | `policyEnf` under a fresh `pbcRequestId` gives a new grant id, so a second grant (A25) | yes |
| E01-new-reference-replay-repaired-e | NO_NEW_GRANT / REPAIR_SUPPORTED / REPLAY | `KSSC.requestData` grant exists gives REPLAY (KSSC.sol:180), **before** the nonce check | yes (nonce guard not reached) |
| E01-same-nonce-distinct-digests-repaired-e | NO_NEW_GRANT / REPAIR_SUPPORTED / REPLAY | distinct digest gives a distinct grant id; the nonce is consumed, giving REPLAY (KSSC.sol:182, lines 181-183) | yes |

**No disagreement between the catalog and the ledger was found.**

## Recipe (`integration-plan.json` sha256 d67f1786..)

Each of the 7 rows runs on a fresh chain pair: PBC port 18545, DBC port 18546, chain IDs
18545/28545. D1 runs the controls (wrong-admin 16; Alice allow with release and one outcome; Bob
policy denial 9). D2 is a fresh second deployment on the same chain pair, with its own bootstrap,
production adapter and 0700 state. This is the SL1 path, generalized as `kind=relay`; the SL1 subject
names are unchanged.

**Collector** `evaluation/relay_stress.py`; **oracles** `evaluation/oracles/provenance.py`.

**Forged tuple, paper.**

- A fixed synthetic reference `keccak("HMBC.E01.forged-tuple.pbcRequestId.v1")`. It is never sent to
  the PBC.
- Uses Alice's gid with credential records from the public `TMSC.checkCredentials` view.
- **Choice (ambiguity):** the owner rehearsal used an unregistered gid; both choices give ACCEPT.
- Expected: one `GrantIssued` plus one `AccessLog`. The PBC request status stays 0, and the PBC
  history is unchanged.

**Forged tuple, repaired-e.**

1. A real Alice request, checkpoint and honest certificate.
2. The honest witness signature and the TEST-ONLY relay signature both recover under the **same
   runner EIP-712 digest and DBC/KSSC domain** (A1-0064). This is recorded in
   `forged-certificate.json`.
3. An `eth_call` simulation of the honest certificate must return the derived grant id. It is never
   mined.
4. The relay-signed copy is mined: `Rejected(1)`, and nothing changes.

DecisionVerifier steps 1-5 pass because the request and decision bytes are the honest ones.

**New-reference replay.**

- **Paper:** the original forwarded tuple is granted, then the same verified tuple under the fixed
  fresh reference `keccak("HMBC.E01.new-reference.pbcRequestId.v1")`. Expected: a second grant and
  no second PBC request.
- **Repaired-e:** the original signed request and certificate are re-consumed with identical
  calldata. Expected: `Rejected(8)` with nothing changed.

**Same nonce, distinct digests (repaired-e).**

1. Two Alice requests: nonce 1, expiry `e` and `e-1`.
2. One checkpoint after both forwards.
3. Both ALLOW certificates collected before any consume.
4. Consume the first, giving a grant and a consumed nonce.
5. Consume the second pre-collected certificate, giving `Rejected(8)`.

The pre- and post-states are read **afterwards** at explicit DBC blocks `second-1` and `second`
(D-5c, new pinned `read_group(block=...)`). Every chain timestamp is recorded against both 30 s
lifetimes in `timeline.json` (A1-0064). An EXPIRED or other code would mask the nonce guard, and the
oracle refuses it.

**Worker:** must stay idle in every SL2 stress, since there is no release.

## Verification (`manifest.json`)

**RED first (true test-first order this time).**

1. All tests were written before any SL2 code: **130 failed**
   (`red-before-implementation.txt`; all missing-feature errors).
2. The A1-0064 additions were tested before their code: 4 failed, 102 passed
   (`red-a1-0064-additions.txt`).

**GREEN.**

- SL2 unit tests: 114.
- Plan tests: 63.
- Full suite `.venv/bin/python -m pytest -q -rs`: exit 0, **987 passed, 0 failed, 0 skipped**,
  286 s. The bracket of 2114 files was stable.

**Negative controls each fail for the intended reason** (a scratch reason probe printed every
message):

- paper deny;
- grant-all;
- reverted honest simulation;
- a moving worker;
- the original tuple not granted;
- another replay code;
- the no-nonce mutant behaviour (second grant);
- an EXPIRED second consume;
- an unsupported variant or profile.

**Collector double.** The tests use a TEST-ONLY stateful two-chain world that mirrors the pinned
ledger semantics. It is not ledger evidence; the live run is.

## Limits

- **Live paths not yet exercised:** the D2 relay wiring, the pinned historical reads and the
  `eth_call` simulation on Anvil. All are unit-tested only.
- **Repaired-e timing:** the same-nonce row puts 2 requests, a checkpoint, 2 decisions and 2
  consumes inside the 30 s TTL (agent 2 (proxy) estimated about 29 s under the old per-call
  hashing). SL1's repaired stress took 7.9 s with checkpoint hashing.
- **Expiry behaviour:** any expiry fails visibly and is kept as it is. There is no TTL change.
- **Assumptions:** delivery unknown; symbolic adapter; safe-ledger, trusted-worker and
  one-trusted-witness assumptions; configured-relay stress outside A01.
- **Do not touch these files before the run.** All 92 `agent3Sources` are frozen, including every
  `evaluation/**/*.py`. Store helper scripts only as `.py.txt`.
