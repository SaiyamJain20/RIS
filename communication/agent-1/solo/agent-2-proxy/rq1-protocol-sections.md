# RQ1-E.md draft sections: protocol, key assumptions, recovery and durability (agent 2 (proxy) scope)

> **Drafting note (not report text).**
> - Author: agent 2 (proxy-2, acting for absent agent 2). First draft 2026-10-10; **refreshed 2026-10-12 for P4** with the SL2-SL7 protocol facts and the human decisions A1-0080/A1-0081.
> - Written for agent 3 (proxy) to merge into `evaluation/reports/RQ1-E.md`, following the S3-0003 skeleton. Section numbers below refer to that skeleton. A1-0082 P4-2 asks for a faithful merge that cites this file.
> - Sources:
>   - S2-0002 (crash classes) and D47; S2-0003 (assumptions PK-01..PK-23); S2-0006 (T1-T3); S2-0007 (D-6, A31), accepted in A1-0064;
>   - slice ACKs S2-0004, S2-0008/S2-0009, S2-0011, S2-0013, S2-0015, S2-0017, S2-0019;
>   - slice reviews S2-0005 (SL1), S2-0010 (SL2), S2-0012 (SL3), S2-0014 (SL4), S2-0016 (SL5), S2-0018 (SL6), S2-0020 (SL7). Each review's script and output is under `protocol/evidence/reviews/s2-00NN-*/`;
>   - decisions D49, A1-0064, A1-0080, A1-0081 and A1-0082.
> - Integrated evidence for the 44 SL1-SL7 rows: `evaluation/evidence/e2/sl{1-subject-live-20261010, 2-relay-live-20261010, 3-audit-live-20261010, 4-receipt-live-20261010, 5-trust-live-20261010, 6-barrier-live-20261011, 7-destination-live-20261011}/`. The 12 earlier rows: A3-0036, A3-0038, A3-0040 and A3-0045 (reviewed by the original agent 2).
> - **When the gate run lands (S3-0021 and after),** the result tables must come from the gate run (A1-0082 P4-2). The per-slice protocol facts below are cited next to it as the historical runs. I will re-check the gate output for the same properties before my S2-0021/P4-3 ACK.
> - Evidence levels follow skeleton §2.2: [I] integrated, [R] owner rehearsal, [U] module/process tests, [F] symbolic.
> - **Correlated self-review:** written, tested and reviewed by the same model as agent 1 and agent 3 (proxy) (A1-0059). The original agent 2 has not reviewed any of it and may overturn it on return.
> - Every protocol citation is at **pin 0716a8e** (manifest d16ddad8.., 108 entries). The working manifest is 551e9f77.. (127 entries; T1-T3 tests added). `hmbc_protocol/**`, `testtools/**`, `exports/**` and `abi/**` are byte-identical across the pin, the working tree and HEAD ec426c6 (`git diff 0716a8e HEAD` on those paths is empty; `sha256sum -c` of the 127-entry manifest exits 0, checked 2026-10-12).

---

## For §3 (System and profiles): "3.x Protocol module, key custody and symbolic mode"

**What runs.** The protocol module (`protocol/`, pinned owner snapshot 0716a8e) is one **JSON-lines adapter process per deployment**:

- command: `python -m hmbc_protocol.adapter --state-dir <new 0700 dir> --deployment <file>`;
- eight closed operations: `prepare_request`, `collect_checkpoint`, `collect_decision`, `attest_grant`, `encrypt_record`, `release`, `finish_decryption`, and `rotate_epoch` (which answers NOT_IMPLEMENTED_IN_PHASE).

**Option A: the adapter submits no transactions.** The runner submits every PBC/DBC transaction as the configured relay or as an issuer-scoped CA admin. User, witness and worker keys resolve only inside the adapter process (BOUNDARY.md; A36).

The table below lists what the reader must know to interpret every protocol-dependent row.

| # | Assumption or choice | Where (pin 0716a8e) | Class |
|---|---|---|---|
| P1 | **Symbolic crypto only.** `adapterMode: "symbolic"`. `ciphertextDigest`/`policyDigest` are record identifiers, not ciphertext. The release token is a random 32-byte TEST-ONLY handle. `finish_decryption` reports `decryptable` from the worker's stored binding plus a matching user-key handle, not from decryption. `keyEpoch` is fixed at 0. | adapter.py:27; symbolic.py; worker.py:155, 191-205 | harness choice (SPEC §3) |
| P2 | **One trusted witness (q = 1), repaired-e only.** It signs checkpoints, decisions and grant receipts **only from facts it recomputes** from both ledgers: the forwarded request from PBC calldata and event, credentials at the checkpoint's source block, ACSC policy, nonce and expiry. Paper profiles have no witness (WRONG_PROFILE). | witness.py:27-162 | extension (A02, A36) |
| P3 | **Safe ledgers.** The latest block is treated as final; block hashes are the witness's own observations, not light-client proofs. | witness.py:3-6 | stated assumption (A01) |
| P4 | **Trusted off-chain key worker** in place of the paper's isolated KSSC execution. State lives in SQLite under a 0700 directory, never in EVM state. A worker compromise bypasses release policy. | worker.py:46-73 | deviation (A03) |
| P5 | **Keys are synthetic and publicly derivable**: keccak256("hmbc-e0-synthetic-key:"‖label). Custody is a **procedural role separation**, not secrecy. Recipient commitments are keccak256("HMBC.recipient-key."‖label), commitments to symbolic keys. | keys.py:27-50 | harness choice (A35) |
| P6 | **Recipient binding.** In repaired-e the release is bound to the grant's non-zero recipient, which must equal the registered one. In **paper profiles (D35/A38)** it is bound to `RSC.recipientKeyHash(grant.gid)`; the native grant recipient stays 0, and an unregistered gid gets no release. The paper gid is relay-asserted, so a substituted subject receives the response (SPEC_GAP kept visible). | worker.py:106-124 | ambiguity resolved by choice |
| P7 | **Clocks and TTLs.** `Chain.now()` = max(latest, pending). Request ≤ 30 s (runner sets PBC now + 30). Decision `expiresAt = min(request, checkpoint, DBC now + 30)`. Checkpoint `expiresAt = DBC now + checkpointMax`, with fixture `checkpointMax` = 60. Paper grant 30 s from `policyEnf`. Expiry is exclusive (`now >= expiresAt` rejects), and a retry never extends a grant. PBC and DBC are separate clocks with uncorrected skew. Measured margins: see "Witness timing" below. | chain.py:125-134; witness.py:18, 43, 65, 124, 140; worker.py:140-142 | choice (A21, A24) |
| P8 | **Checkpoint cadence belongs to the runner.** The adapter never pushes checkpoints. A newer accepted checkpoint invalidates older decisions (sequence equality). | adapter.py:163-169 | choice (A22) |
| P9 | **A31 is caller-side, not enforced.** The witness is stateless: before a new checkpoint is accepted, a repeated `collect_decision` yields another valid ALLOW for the same unconsumed request. Single-grant safety comes from the DBC (grantId uniqueness `KSSC.sol:180`, (gid, nonce) consumption `KSSC.sol:181-183`) and from A22, not from A31. In SL1-SL7 the runner kept the discipline: never more than one `collect_decision` per request digest (counts below; oracle-enforced in SL6 and SL7). | witness.py:100-142 | ambiguity / stated trust assumption, not a vulnerability (S2-0007, A1-0064) |
| P10 | **encrypt_record is not authenticated.** The ACSC owner and policy are checked; payload commitments are first-writer-wins; a trusted coordinator pre-registers records. | worker.py:76-103 | stated trust assumption (A41) |
| P11 | **Pinned deployment and endpoints.** A request manifest that differs from the pinned one gets WRONG_DESTINATION. RPC is loopback only, with no proxies or redirects. ABIs are hash-pinned. Worker state is fingerprint-bound to chain ids plus contract addresses (not to chain history). | adapter.py:112-130, 226-227; chain.py:52-68; ledger.py:49-50; worker.py:62-72 | hardening |
| P12 | **Token redaction is the runner's job.** The `release` response hands the raw token to the runner. The worker log exports only keccak256(token). Published evidence carries `tokenSha256` and no `token` field. Checked in every slice review (scan table below): 0 preimages, 0 `token` fields. | worker.py:169-171; worker_log.py:36 | obligation |
| P13 | **TEST-ONLY tools stay outside the adapter boundary.** `faulty_adapter` is the crash hook (start-contract-r1, hook f0ab2400..). `deviating_witness` (0511ba57..) is a deliberate receipt deviation (A40), first used live in SL4 (S2-0014). Both refuse non-TEST-ONLY deployments and print no key. | testtools/ | deliberate mutation / control |
| P14 | **`prepare_request` is pure and signs the request as given.** It validates the shape, resolves the user key in-process and checks gid = signer (WRONG_SUBJECT), source/destination chains, PSC and KSSC = the pinned deployment (WRONG_DESTINATION), and keyEpoch/policyVersion = the fixture (WRONG_EPOCH). It makes no chain read, keeps no cache and no nonce state, and **takes `authEpoch` and `expiresAt` verbatim**. It checks neither; the repaired PSC checks authEpoch (`PSC.sol:204`, ledger scope). | adapter.py:79-104 | choice (S2-0015) |
| P15 | **The worker is created lazily.** Only `encrypt_record`, `release` and `finish_decryption` reach `adapter._worker`, which creates `<state>/worker/worker.sqlite`. A stress adapter that never calls them has no worker database; the runner records it as **verified never-instantiated** (D49: exporter exit 1 with the exact pinned message, and both DB paths absent on disk). It is never recorded as an empty export, and instantiating the worker to avoid this is prohibited. | adapter.py:133-136; worker.py:49-58; worker_log.py:18-26 | runner rule (D49) |
| P16 | **One adapter per deployment, one key derivation.** Each stress deployment (D2 in SL1-SL6; A and B in SL7) gets its own production adapter with its own new 0700 state and its own pinned `--deployment`. All adapters derive the **same** TEST-ONLY keys from the same labels (`alice`, `witness-1`, …), so a second deployment is not a separately keyed authority. Separation comes from the EIP-712 domain (chain id + verifying contract), the pinned manifest and the worker fingerprint. | adapter.py:226-227; keys.py:27-28; messages.py:48-53; worker.py:62-72 | harness choice (P5) |

Host: CPython 3.13.5 `.venv`; 3.13.13 is frozen, and agent 2's original runs used 3.13.15. Foundry 1.8.5.

---

## Protocol facts per slice (for §5-§7 and §8; historical runs SL1-SL7)

All 44 rows used the **production** `hmbc_protocol.adapter` for D1 and every stress deployment: exit 0, empty stderr (e3b0c442..), no exchange failures, distinct state directories. No row used a TEST-ONLY tool except SL4's three binding rows.

### Stress-adapter operations and A31 counts

`collect_decision` counted from the published adapter exchanges by my review scripts; in SL6 and SL7 the oracle also enforces the count (`evaluation/oracles/barrier.py:66, 76`; `evaluation/oracles/destination.py:52, 86, 114` at HEAD ec426c6; S2-0019 cited line 49 for the repaired check, which is line 52).

| Slice (rows) | Stress-adapter operations | `collect_decision`: paper rows | `collect_decision`: repaired-e rows |
|---|---|---|---|
| SL1 subject (3) | paper: `encrypt_record`, `prepare_request`, `release`, `finish_decryption` ×2; repaired: `encrypt_record`, `prepare_request`, `collect_checkpoint`, `collect_decision` | 0, 0 | 1 |
| SL2 relay (7) | forged tuple paper: **none**; new reference paper: `prepare_request`; repaired forged and new reference: request, checkpoint, decision; same nonce: `prepare_request` ×2, one `collect_checkpoint`, `collect_decision` ×2 | 0 ×4 | forged 1; new reference 1; same nonce **2, one per distinct request digest** |
| SL3 audit (6) | dropped: `encrypt_record` first, then request (+ checkpoint, decision in repaired), one `release`; fabricated: `prepare_request` (+ `attest_grant` → NOT_COMMITTED in repaired) | 0 ×4 | dropped 1; fabricated 0 |
| SL4 receipts (7, all repaired-e) | `prepare_request`, `collect_checkpoint`, `collect_decision`, `attest_grant` | – | 1 ×7 |
| SL5 trust (6) | rollback: `prepare_request` only; wrong issuer: **none** | 0 ×4 | 0 ×2 |
| SL6 barrier (9) | paper: `prepare_request`; repaired pre-barrier and expired duty: request, checkpoint, decision; repaired post-barrier: request, checkpoint, decision, **second checkpoint** | 0 ×6 | 1 ×3 |
| SL7 destination (6) | wrong destination: B serves `prepare_request` (+ checkpoint, decision in repaired), A serves none; expiry boundary: A serves `prepare_request` (+ checkpoint, decision in repaired) | 0 ×4 | 1 ×2 (B's; A's) |

**Totals:** 24 paper rows with 0 decisions; 20 repaired-e rows with 18 decisions (16 rows with one decision for one request; SL2 same nonce with two decisions for two distinct requests; SL3 fabricated and both SL5 repaired rows with none). No request digest was decided twice. No stress adapter ever served `rotate_epoch`, and none served `release` outside SL1's paper rows and SL3's dropped rows.

### Worker observations (D49) and never-publish scans

| Slice | Worker observations | Never-publish scan (published evidence only) |
|---|---|---|
| SL1 | No D49: `encrypt_record` instantiates the D2 worker first. Idle export before, then exactly one [RELEASE_INTENT, RELEASE_SENT] delta (paper); repaired stays idle | 143 files, 790 hex32, 5 token digests: 0 preimages, 0 `token` fields. **No key-substring scan** |
| SL2 | **14** probes (7 rows × before/after): exit 1, verified never-instantiated | 288 files, 1716 hex32, 7 digests: 0 / 0. No key scan |
| SL3 | **6** never-instantiated probes (fabricated rows); 6 instantiated probes (dropped rows, created by `encrypt_record`) | 246 files, 1450 hex32, 9 digests: 0 / 0. No key scan |
| SL4 | **42** probes (6 per row: baseline + 5 steps) | 306 files: **0 key hits** for 13 fixture labels; 1835 hex32, 7 digests: 0 / 0 |
| SL5 | **24** probes (5 per rollback row, 3 per wrong-issuer row) | 265 files: 0 key hits; 1429 hex32, 6 digests: 0 / 0 |
| SL6 | **49** probes (5 in each paper pre/post row and in repaired pre-barrier; 6 in repaired post-barrier, which adds ACCEPT_CHECKPOINT; 6 in each expired-duty row) | 393 files: 0 key hits; 2226 hex32, 9 digests: 0 / 0 |
| SL7 | **45** probes (10 per wrong-destination row, covering A and B; 5 per expiry-boundary row) | 285 files incl. the 36 B/source files: 0 key hits; 1657 hex32, 6 digests: 0 / 0. B's private state not published |

**180** verified never-instantiated probes in SL2-SL7; none ever saw an instantiated worker where D49 applied. Key-substring scans exist only for SL4-SL7; SL1-SL3 were scanned for token preimages only.

Correction to my own wording: S2-0018 described SL6 as "5 per pre- and post-barrier row". The repaired post-barrier row had 6 (`review_sl6.out.json`); the stated total of 49 is right.

### Witness timing rules and measured margins

Rules (witness.py at the pin):

- **Record lapse → DENY, never ALLOW** (lines 133-134): when credentials are valid but any record has `validUntil <= DBC now`, the witness attests DENY with empty records. An expired-duty ALLOW must therefore be collected while the duty is valid at DBC now.
- **Decision expiry** (line 140): `min(request.expiresAt, checkpoint.expiresAt, DBC now + 30)`.
- **Checkpoint** (lines 54-67): sequence = DBC current + 1; authEpoch and policyVersion read at the PBC latest block; `expiresAt = DBC now + 60` (fixture).
- **Freshness** (lines 109-125): no fresh accepted checkpoint, a checkpoint older than the forwarding block, an epoch mismatch, a consumed (gid, nonce) or an expired request each refuse; a refusal is an exception, never a signature.

Measured (DBC/chain seconds, single samples, 1 s granularity, two Anvil clocks with uncorrected skew):

| Item | Value | Source |
|---|---|---|
| Which decision term binds | `request.expiresAt` in every repaired row where checked (SL6 ×3, SL7 expiry boundary). Witness DBC now + 30 exceeded it by 1-2 s in SL6 (1 s lower bound from cp expiry − 60; 2 s upper bound from the runner's later reading) and by ≥ 1 s in SL7 | S2-0018, S2-0020 |
| SL7 expiry boundary | decision `expiresAt` = request `expiresAt` = consume block timestamp = 1791727102; checkpoint 1791727133. **The structural margin that keeps the request binding is about 1-2 s** | S2-0020 |
| SL6 expired duty (repaired) | decision collected at DBC 1791704470, duty end 1791704490 (**20 s** before lapse, so ALLOW was correct); consume 1791704491 vs decision/request expiry 1791704498: **7 s** | S2-0018 |
| SL6 pre-/post-barrier (repaired) | consume 24 s / 23 s before decision expiry | timelines |
| SL6 post-barrier cp2 | sequence 2, authEpoch 4 (= revocation's after-epoch), source block 49 (= revocation block), collected after the revocation transaction | S2-0018 |
| SL2 same nonce | 24 s between the second consume and the earliest request expiry | S2-0010 |
| SL1 paper releases | 29 s, 28 s before grant expiry | S2-0005 |
| SL3 dropped-outcome releases | 29 s, 28 s (paper); 26 s (repaired, after checkpoint and decision) | S2-0012 |
| E2 recovery retries (repaired) | about 4 s before expiry | A1-0049 |

The ~2 s (SL7) and ~7 s (SL6) margins are the thin ones that A1-0082 flags for the gate run. Every oracle refuses an overrun rather than passing it, so a miss is a visible failed trial, never a silent pass.

---

## For §5 (E01): protocol-side text per row

> **Subject substitution [I]** (`evaluation/evidence/e2/sl1-subject-live-20261010/`; S3-0005 plan 6fd5809b..; A1-0062, S2-0004; 255.73 s, exit 0; protocol review S2-0005, no discrepancy).
>
> **Paper-strict and paper-minimal: SPEC_GAP (CONDITIONAL).** On a fresh second deployment (D2) with its own adapter process and 0700 state:
> - the relay changed only the gid of Alice's forwarded tuple to registered Bob, and the DBC granted it (gid Bob, native recipient 0, TTL +30 s);
> - one production release on that grant was bound to **Bob's** registered key (D35/A38), giving exactly one worker intent, one send attempt and one cache entry (delivery unknown);
> - that same response completed for `keyref:user:bob` (decryptable) and was refused WRONG_SUBJECT for `keyref:user:alice`;
> - completion changed nothing in the worker, and no outcome was reported;
> - DBC clock at release: 29 s and 28 s before grant expiry.
>
> **Repaired-e: REPAIR_SUPPORTED.** The substituted request with Alice's unchanged certificate was mined with status 0 and Rejected(2) WRONG_SUBJECT. There was no release, and the D2 worker stayed idle.
>
> **Interpretation:** a configured-relay stress outside A01. The paper tuple carries no subject binding, so the symbolic response follows the relay-asserted subject. This is **not an HMBC exploit**, and not real encryption.
>
> Owner tests [U]: `protocol/tests/test_paper_release.py` (T1, both paper profiles, asserted rather than skipped; S2-0006).

**Forged tuple [I]** (SL2 r2, plan b3a02098..; S2-0009, S2-0010):

- Paper: the relay's `policyEnf` alone; the D2 adapter served 0 exchanges.
- Repaired-e: the honest decision from `collect_decision` was used **only** in an `eth_call`, never mined. The mined copy kept the decision bytes and replaced only the signature with a TEST-ONLY **relay** signature. No witness key was used by the runner.
- **Digest and domain proof**, recomputed with the protocol encoder: domain `HMBCDecision` v1 on D2's KSSC (messages.py:48-49); digest 0x698b3a6e.. equals the runner's honest and forged digests; the honest signature recovers to the witness, the forged one to the relay (not a witness). So BAD_SIGNATURE comes from the signer, not from a wrong digest.

**New-reference replay [I]** (SL2): paper rows needed only `prepare_request` on D2; repaired: request, checkpoint, one decision. Both paper rows report the same second grantId 0x1bf1f8ad..: a fixture-determinism artifact (fixed synthetic relay reference + identical D2 KSSC address on each fresh Anvil), not cross-row state.

**Same nonce, distinct digests [I]** (repaired-e only, SL2): two `prepare_request` calls with nonce 1 and expiries e and e-1 gave distinct digests (the adapter keeps no nonce state); **one** checkpoint after the second forward (witness.py:114-115); **both** decisions before any consume (each saw `nonceConsumed == false`, witness.py:122-123). The second, pre-collected certificate then met the ledger nonce guard. Margin 24 s.

**Wrong destination [I]** (SL7, plan d4fa294e..; S2-0019, S2-0020):

- B is a third deployment on the same chain pair, contracts disjoint from A and D1, with **its own production adapter**: own 0700 state (`source-instance/private-adapter-state`), own `--deployment` (B's deployment file), own D49 probe.
- B's request (decoded from B's PBC calldata with the protocol ABI codec) is bound to B's PSC, KSSC and chain ids. A's PBC has no `requestAccess`.
- B's checkpoint and decision recover to the witness under **B's** KSSC domain and **not** under A's. The ledger's code 3 comes from DecisionVerifier step 1, before any signature check (A1-0077); even a reached signature step would not have recovered to the witness.
- B and A derive the same label keys (P16): B's request really is Alice's for B and B's certificate really is the witness's, so the only defect at A is the destination.
- Required wording (A1-0039): the catalog recipe is rejected at step 1 (source PSC binding), not at the destination check; this recipe cannot kill the destination-binding mutant.

**Expiry boundary [I]** (SL7): repaired: decision `expiresAt` = `request.expiresAt` = consume timestamp 1791727102; the request term bound (witness rule P7, margin ≥ 1 s from the checkpoint lower bound). The runner pinned the next DBC timestamp to the request expiry with no adapter call between the pin and the consume (destination_stress.py:133-139, static reading); the consume block timestamp equals the pinned value. Paper rows: the consume block timestamp equals the request expiry (1791726931, 1791727014). Equality at expiry is the ledger's (DV step 9, `>=`).

## For §6 (E02): protocol-side text per row

- **Wrong issuer [I]** (SL5): no adapter call at all; the rows use the ledger producer, an `eth_call` and a CA-admin transaction. 3 D49 probes per row. Not a repair (ledger, D-record N-1).
- **Signed-list rollback [I]** (SL5, plan 9e14a148..; S2-0015, S2-0016): one `prepare_request` per row. On-chain request and signature, decoded from the relay's `requestAccess` calldata, equal the adapter output byte for byte; the digest re-derives and the signer is Alice. **authEpoch signed = TMSC.authEpoch at the request block:** 5 (paper-strict), 5 (paper-minimal), 4 (repaired-e). The adapter signed exactly what it was given (P14); the repaired request was then denied at the PSC (REVOKED, ledger scope A1-0073). No checkpoint or decision in any rollback row.
- **Pre-barrier revocation [I]** (SL6, plan 78d6ebfb..; S2-0017, S2-0018): request at authEpoch 3 (request block 48 < revocation block 49). Repaired: one decision on cp1, collected **before** the revocation transaction; it evaluated credentials at cp1's source block (witness.py:127-128), which is the designed pre-barrier window. Consume 24 s inside the decision expiry.
- **Post-barrier revocation [I]** (SL6): repaired: the old certificate was collected before REVOKE_ON_PBC (decision 07:37:00.5Z, revocation 07:37:02.3Z, cp2 07:37:03.2Z); after it only `collect_checkpoint` ran. cp2 = sequence 2, authEpoch 4, source block 49, and it was the KSSC `currentCheckpoint` at consumption. STALE_STATE (line 87 sequence cause) is the ledger's (A1-0075). Paper pre- and post-barrier are the same execution (ledger).
- **Expired duty [I]** (SL6): request after the H1 TempACL install, at authEpoch 4 (= cp1's). Repaired: decision collected at DBC 1791704470 while the duty was valid (end 1791704490), so the witness rightly issued ALLOW with the duty record `validUntil = 1791704490`; consume at 1791704491, 7 s before the binding request expiry 1791704498. The oracle requires `collectedDbcNow < dutyEnd <= consume < min(decision, request, checkpoint expiry)`, so the rejection is DV step 13, not step 9 (ledger). Paper grants at the boundary instant (ledger).

---

## For §7.2 (Crash and recovery): replacement text

### 7.2 Crash and recovery (mechanics completed [I]; paper rows SPEC_GAP under D47)

| Row | paper-strict | paper-minimal | repaired-e |
|---|---|---|---|
| crash after durable intent | **SPEC_GAP / UNPROVED** (frozen label: BLOCKED; D47); mechanics PASS [I] | **SPEC_GAP / UNPROVED** (frozen BLOCKED; D47); mechanics PASS [I] | **REPAIR_SUPPORTED [I]**, bounded logical mechanics only |
| crash after send | **SPEC_GAP / UNPROVED** (frozen BLOCKED; D47); mechanics PASS [I] | **SPEC_GAP / UNPROVED** (frozen BLOCKED; D47); mechanics PASS [I] | **REPAIR_SUPPORTED [I]**, bounded |

Label for the report (A1-0082 P4-2): "frozen BLOCKED / decided SPEC_GAP, UNPROVED".

**Evidence [I]:**

- `evaluation/evidence/e2/recovery-live-20261009/`: plan 4bceffc3..; ACKs A1-0048 and A2-0028; 778.47 s, exit 0; 24 process records (18 exit 0, 6 intentional exit 86); protocol review A2-0029.
- `evaluation/evidence/e2/expiry-live-20261009/`: plan a76a291d..; ACKs A1-0050 and A2-0030; 779.77 s, exit 0; `catalog-coverage.json`; protocol review A2-0031.

**Mechanism (our chosen completion, not the paper's):**

- The worker commits one `RELEASE_INTENT` per grant (with the response token) **before** anything is sent.
- It then commits a write-ahead `RELEASE_SENT` per attempted send **before** transmitting.
- A retry returns the stored token; delivery is always `unknown`.
- SQLite WAL with `synchronous=FULL` (worker.py:59-60, 130-188).
- The crash is the accepted TEST-ONLY hook `testtools.faulty_adapter`, which ends the process with `os._exit(86)` at one of two logical points:
  - `after_intent`: no response line;
  - `after_send`: after the response line is flushed.
- Restart uses the **production** adapter on the same state.

**As measured [I], all six rows:**

- The hook exits 86 with empty stderr (EOF after_intent; one validated frame, then EOF, after_send).
- The production restart on the same private state and deployment returned the **identical cached response** strictly before the original grant expiry.
- Worker attempt counts:

  | Point | At crash (sent / completed) | After retry (sent / completed) | Intents |
  |---|---|---|---|
  | after intent | 0 / 0 | 1 / 1 | 1 |
  | after send | 1 / 0 | 2 / 1 | 1 |

- One PBC outcome per row afterwards.
- In a separate step, after Alice's completion and outcome, the DBC was advanced to max(latest+1, original expiry). The **identical** release envelope then returned EXPIRED, with the whole worker log, cache, attempts and native grant, request and outcome state unchanged (A3-0038).
- Margins: repaired-e retries landed about 4 s before expiry (A1-0049, single samples).

**Why the paper rows are SPEC_GAP (D47; S2-0002; paper figures checked in A1-0064):**

- HMBC specifies **no** key-release durability, retry, idempotence or crash-recovery semantics:
  - III-D3/D4: the PSC returns the DBC response to the user and logs it; the LSC caches pending requests;
  - III-E2: the KSSC partially decrypts and forwards;
  - IV-B/Fig. 8: a cache database holds *pending log sessions* ("caching transaction details"), not release state. Cite Fig. 8 as a pending-log-session cache, not as release-state durability.
- Agent 1 read Fig. 5, 6 and 8 (pp. 11-13) as rendered images: no figure specifies crash, retry, restart, durability or recovery semantics for key release. The only failure language (§IV-B, p. 13) concerns batching log sessions into the PBC (A1-0064).
- The crash points exist **only because** this reconstruction moved partial decryption into an off-chain worker (A03).
- The observed behaviour is therefore a **tested reconstruction result of our own completion** (A03, A12, A21, A37, D35/A38). It can neither establish nor refute a paper property.
- The frozen label BLOCKED is shown because it was pre-registered. It was set before D35/A2-0012 made paper releases run at all.
- This is a relabel of an ambiguity class: **not a pass, not a changed outcome, never a finding.**

**Owner evidence closing the remaining recovery qualifications [U], not catalog rows** (`protocol/evidence/p2-t1-t3/`; S2-0006):

| Test | Profiles | What it shows |
|---|---|---|
| T2 `protocol/tests/test_recovery.py` | 3 | A crash **before** the durable intent leaves no release row and no event, and nothing is sent; a restart performs one ordinary first release. |
| T3 `test_faulty_adapter.py::test_first_production_restart_after_the_original_expiry…` | 3 x 2 crash points | The **first** production restart after the original expiry answers EXPIRED with the worker log unchanged. After an intent crash, the token was never transmitted. |

Both were detected by deliberate mutants on a scratch copy (3/3), with full-suite GREEN at 1375 passed / 201 skipped.

**Limits:**

- Two logical crash points via a TEST-ONLY hook.
- No power loss, no OS-level kill, and no fsync-of-directory claim.
- Worker-side equality at the exact expiry second is owner evidence only (unit test `test_worker_hardening.py:27`). An EXPIRED refusal emits no event, so live equality is not observable.
- The first restart after expiry is owner evidence (T3), not an integrated row.
- One trial per row.
- SL1-SL7 add **no** recovery evidence: no crash hook ran. Only SL1 (paper) and SL3 (dropped rows) performed worker steps on a stress deployment; the D1 controls performed ordinary Alice releases.

---

## For §7.3 (Remaining E03 rows): required protocol wording

- **Delivery is unknown in every row.**
  - `RELEASE_SENT` is a write-ahead record of an attempted send, never recipient delivery.
  - The protocol has no recipient acknowledgement (worker.py:3-6, 158).
  - A DBC grant or a GrantReceipt proves **authorization** (a past allowed grant), not delivery or decryption.
- **Dropped outcome [I]** (SL3, plan d768463d..; S2-0011, S2-0012): each row includes the catalog's RELEASE. `encrypt_record` was the first D2 operation, then the request (and checkpoint + one decision in repaired-e), then exactly one `release`.
  - Worker: idle before; after = [RELEASE_INTENT, RELEASE_SENT], one row, sendAttempts 1, completedAttempts 1, delivery `unknown`.
  - Release bound to Alice's registered key 0x98d796e3..; native grant recipient **0** in paper (D35/A38, bound off-chain by `worker._recipient_for`) and the signed recipient in repaired-e.
  - Margins 29 s, 28 s and 26 s inside the grant lifetime. The PBC request stayed FORWARDED (status 1, `outcomeLogId` 0).
  - Local durable logs do not imply PBC reconciliation, which needs eventual delivery and an honest reporter (A12).
  - Agent 1's owner rehearsal omitted RELEASE for these rows (A1-0060 R2 correction), so it is not evidence for them.
- **Fabricated outcome (repaired-e) [I]** (SL3): besides WRONG_PROFILE on the unattested path, the honest witness refused to attest the absent grant: `{ok: false, error.code: "NOT_COMMITTED"}`, no receipt and **no signature** (witness.py:153-154 raises before `_sign`). Paper fabricated rows made no attest call; no worker was instantiated in any fabricated row.
- **Receipt-binding controls (SL4) [I]** (plan 851896f3..; S2-0013, S2-0014):
  - Honest receipts (7) come from the production `attest_grant`, after FORWARD_OR_CONSUME and before any report. Each recovers to the witness under `HMBCReceipt` v1 on the PBC PSC (messages.py:52-53), and its fields are the pinned witness construction for that grant.
  - The inconsistent receipt in the three binding rows comes from `testtools.deviating_witness` (sha256 0511ba57.., re-hashed before every call): a **deliberate witness deviation (A40), classified as a deliberate mutation**, outside the honest-witness assumption. Report it as a defence-in-depth control: never an HMBC attack, never honest-witness behaviour (S2-0007; D-6 accepted in A1-0064).
  - First live use, exactly as specified: one call per binding row, exit 0, argv equal to the plan template (`--deployment` = the D2 adapter's own file, R11 same-file condition held; `--at-block` = the honest receipt's block 24; no `--value`). The three-way check held for each artifact: only the named field differs, the altered value equals the tool's `_altered`, the signature recovers to the witness under the evaluator's own encoder, and `testOnly` is true. Each artifact is labelled A40.
  - The receipt-signature controls edit one bound field and keep the honest signature (no tool call). Binding precedes quorum in repaired-e, so they cannot kill the binding mutant.
  - **Not done:** the D-6 plan also allowed the tool against the no-receipt-binding mutant deployment. The live mutant matrix was not run (A1-0080), so the tool has never run against a `mutant-*` deployment in an integrated run. Its mutant behaviour is owner evidence only (test_supplement_controls.py:73-82).
  - R11 (non-strict JSON parsing in the tool) stays an unfixed hardening item; changing it would move the protocol pin.

---

## For §9/§10 (Formal; mutants) and gate criterion 4: protocol-scope wording

The report must state criterion 4 as A1-0080 words it: **"met on owner, formal and baseline evidence (human decision A1-0080); integrated live mutant matrix not run"**, with the reason (a safety-classifier stop, A1-0079). In protocol scope:

- The A1-0080 basis contains **no protocol-module mutant**: the forge mutant suite, the ProVerif destination mutant, the SL2-SL7 guard rows and the positive controls. That suite does not cover the adapter, the relay or the two-chain runner, and the report must not say otherwise.
- The protocol owner mutation checks (`protocol/evidence/mutation-check.json` 65/73 detected with 8 documented equivalents, agent 2's run; `mutation-check-faulty-adapter.json` 9/9; T1-T3 3/3) show the **protocol module's own tests** are sensitive [U]. They are not a criterion-4 kill, and A1-0080 does not cite them.
- The witness and worker gate on `profile == "2"` and would serve `mutant-*` deployments (PSC.sol:110-122; S2-0007). That is static reading; no integrated run ever deployed or served a mutant.
- No integrated destination kill, in any form (A1-0078 D-P3-2; L3).

## For §6 (window) and §13: protocol-scope wording for the revocation window

Carry the A1-0081 statements exactly. Protocol facts behind them:

- The owner window measurement (A1-0046) used agent 2's production adapter at 8b7caf5. Its `hmbc_protocol/**` and `abi/**` are **byte-identical** to pin 0716a8e (`git diff 8b7caf5 0716a8e` on those paths is empty; checked 2026-10-12). It is still an owner measurement with the owner runner, not the integrated C-E2 runner.
- **W is a runner cadence parameter.** The adapter never pushes checkpoints (P8); checkpoints exist only when the runner calls `collect_checkpoint` and `acceptState`. W is capped by the 30 s request TTL and the decision rule `min(request, checkpoint, DBC now + 30)` (P7).
- SL6 is an ordering result (old certificate collected before the revocation, rejected after the revoking checkpoint), not a measured window. The 2 s cross-clock value is not a window (A1-0074).
- **No integrated window was measured.** D-P3-3 was not run (A1-0081). No statistics: one trial per delay, one host, 1 s granularity.

---

## For §11 (Ambiguities): protocol items

- **Key-release durability, retries and crash recovery:** the paper is silent (A1-0064 figure check). Our worker choice is A03, A12, A21 and A37. The four paper crash rows are SPEC_GAP under D47, next to the frozen BLOCKED.
- **Response recipient in paper profiles:** the paper tuple has no recipient binding. We bind to `RSC.recipientKeyHash(grant.gid)` (D35/A38), so subject substitution routes the symbolic response to the substituted subject (SL1).
- **Decision retry policy:** A31 is caller-side, not an adapter guarantee (P9; A1-0064 classification: ambiguity / stated trust assumption).
- **Record registration authenticity:** A41 (first-writer-wins payload commitment, trusted pre-registration).

## For §12 (Process errors): protocol items

- **My review error in S2-0008:** I missed that the adapter creates its worker lazily, so a stress adapter serving only request/checkpoint/decision has no worker DB. That (shared with A1-0065 and S3-0007) caused the failed SL2 run (`evaluation/evidence/e2/sl2-relay-failed-20261010/`, plan d67f1786..). It is a runner/review defect, kept, not a protocol finding; D49 is the fix (S2-0009).
- **Wording imprecision in S2-0018:** per-row probe counts (see the D49 table); the total was right.

## For §13 (Limitations): protocol items

- Symbolic adapter: no ABE, no ciphertext secrecy, no performance claim. `rotate_epoch` is not implemented (G is locked).
- One trusted witness (q = 1) and a trusted worker. A compromise of either breaks the repaired-e guarantees. The DBC verifies the witness signature, not that a PBC request exists.
- Synthetic, publicly derivable keys; custody is procedural. Every adapter, including SL7's B, derives the same label keys (P16).
- Logical crash points only; delivery unknown.
- Fingerprints bind chain ids plus addresses: a state directory reused on a fresh chain with identical addresses would be accepted. The runs used new state directories, so there was no effect (S2-0005). Fixed deploy sequences also repeat grant ids and KSSC addresses across rows (S2-0010).
- Clocks: two Anvil chains with uncorrected skew. Second-level cross-chain values are indicative only.
- Margins (all single samples): repaired-e recovery retries ~4 s; SL7 expiry-boundary request-binding margin ~1-2 s; SL6 expired-duty consume 7 s; SL1/SL3 releases 26-29 s.
- A31 and D49 are runner rules, checked from exchange logs and filesystem probes, not properties of the protocol code.
- Python 3.13.5 on this host (3.13.13 frozen).

## What the protocol evidence does not show (stated plainly)

- **The witness's own clock readings.** The witness reads DBC time internally. Which decision term bound, and that the expired-duty duty was valid at collection, are inferred from bounds (checkpoint TTL below, the runner's later reading above) and from the ALLOW result, not observed directly.
- **That no DBC block was mined between SL7's timestamp pin and the consume.** Shown only indirectly (the consume's timestamp equals the pinned value) plus static reading of the pin-to-consume path.
- **Adapter internals.** Purity of `prepare_request`, file-free witness operations and the absence of caches come from static reading at the pin. The evidence shows only the operations served, their outputs and the absent worker DB.
- **Raw adapter transcripts.** Exchanges are published as canonical or redacted responses with hashes; I did not re-join them against the private raw transcripts.
- **Key-substring absence in SL1-SL3** (only token-preimage scans were run there).
- **Any recovery or durability property beyond §7.2**, any delivery, and any recipient-side decryption.
- **Any mutant accepting in the integrated runner** and **any integrated window value** (A1-0080, A1-0081).
- **Independent review.** Every check above is correlated self-review.

## "Must not claim" checklist (protocol scope; proxy-2 will check the merged report against it before ACK)

1. No ABE, confidentiality, secrecy or performance result, and nothing about HMBC's cryptography. The adapter's crypto is **symbolic** (P1).
2. No delivery, receipt-by-user or exactly-once claim. Not "atomic cross-chain logging" (P8, §7.3).
3. No power-loss or OS-kill durability. Crash evidence is two logical points via a TEST-ONLY hook (§7.2).
4. The paper crash rows are **SPEC_GAP / UNPROVED** with the frozen BLOCKED shown (D47). They are never a pass and never a finding.
5. No HMBC vulnerability or exploit from relay-stress rows (subject substitution, forged tuple, wrong destination, new reference, fabricated outcome). They show specification dependencies under configured-relay stress outside A01.
6. No claim that any key is secret: TEST-ONLY keys are derivable from labels (P5, P16). No claim that SL7's B, or any D2, is a separately keyed authority.
7. **One trusted witness and a trusted worker.** No quorum, witness-fault, consensus or Byzantine property (P2, P3, P4).
8. Timing constants are project choices, not paper numbers (P7). The revocation window is bounded by them and by runner cadence (P8).
9. A31 is described as caller discipline, not an adapter guarantee (P9). D49 is a runner recording rule, not an idle-worker export (P15).
10. The deviating-witness rows are a deliberate deviation (A40), not honest-witness behaviour (§7.3).
11. Owner [U]/[R] evidence (T1-T3, rehearsals, protocol mutation checks) is never counted as an integrated [I] catalog row or as an integrated mutant kill.
12. Criterion 4 uses the A1-0080 wording; no integrated live mutant kill and nothing about adapter/relay mutants. The window uses the A1-0081 wording; no integrated window measurement.
13. The PLAN B-E2 file names (`protocol/faults.py`, `state.py`, `test_{replay,freshness,recovery}.py`) are not claimed to exist as planned. The faults are runner transactions plus `testtools/*`. Only `tests/test_recovery.py` now exists (T2).
14. No claim to reproduce the HMBC authors' implementation; this is a paper-derived reconstruction.
15. No JANUS material. F and G are not started.

## Protocol evidence index (for §14)

| Item | Path |
|---|---|
| Protocol pin manifest (E2 runs) | `git show 0716a8e:protocol/evidence/source-manifest.sha256` (d16ddad8.., 108) |
| Current protocol manifest (T1-T3 added) | `protocol/evidence/source-manifest.sha256` (551e9f77.., 127) |
| Owner suite on this host | `protocol/evidence/p2-t1-t3/green-full-suite.txt` (1375 passed, 201 skipped, exit 0) |
| T1-T3 mutants and RED/GREEN | `protocol/evidence/p2-t1-t3/mutation-check-p2-t1-t3.json`; `…/red-green/` |
| Earlier production mutation check | `protocol/evidence/mutation-check.json` (65/73 detected, 8 documented equivalents; agent 2's run) |
| Crash-hook mutation check | `protocol/evidence/mutation-check-faulty-adapter.json` (9/9) |
| Slice protocol reviews (script, output, commands) | `protocol/evidence/reviews/s2-0005-sl1/`, `s2-0010-sl2-r2/`, `s2-0012-sl3/`, `s2-0014-sl4/`, `s2-0016-sl5/`, `s2-0018-sl6/`, `s2-0020-sl7/`; every `review_*.out.json` has `problems: []` |
| Evaluator suite runs for the SL6/SL7 ACKs (repo-root pytest, `testpaths = evaluation/tests`) | 1494 passed at d11dfea (S2-0017, `sl6-full-suite.txt` 2f463d5b..) and 1596 passed at bf2d2b9 (S2-0019, `sl7-full-suite.txt` 9adfaed7..); outputs in job tmp `/home/saiyamjain/.claude/jobs/aed51961/tmp/p2/`, not in the repo |
| Messages | S2-0001..S2-0020; A2-0020..A2-0038 (original agent 2); A1-0064, A1-0080, A1-0081, A1-0082 |
