# RQ1-E.md draft sections: protocol, key assumptions, recovery and durability (agent 2 (proxy) scope)

> **Drafting note (not report text).**
> - Author: agent 2 (proxy-2, acting for absent agent 2), 2026-10-10.
> - Written for agent 3 (proxy) to merge into `evaluation/reports/RQ1-E.md`, following the S3-0003 skeleton. Section numbers below refer to that skeleton.
> - Sources: S2-0002 (crash classes) and D47; S2-0003 (assumptions PK-01..PK-23); S2-0005 (SL1 review); S2-0006 (T1-T3); S2-0007 (D-6, A31).
> - Integrated evidence: A3-0036 (`evaluation/evidence/e2/recovery-live-20261009/`), A3-0038 (`…/expiry-live-20261009/`), S3-0006 (`…/sl1-subject-live-20261010/`).
> - Evidence levels follow skeleton §2.2: [I] integrated, [R] owner rehearsal, [U] module/process tests, [F] symbolic.
> - **Correlated self-review:** written, tested and reviewed by the same model as agent 1 and agent 3 (proxy). The original agent 2 has not reviewed it.
> - Placeholders `[…]` are for values that arrive with later slices or the gate run.

---

## For §3 (System and profiles): "3.x Protocol module, key custody and symbolic mode"

**What runs.** The protocol module (`protocol/`, pinned owner snapshot 0716a8e, manifest d16ddad8.., 108 entries) is one **JSON-lines adapter process per deployment**:

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
| P7 | **Clocks and TTLs.** `Chain.now()` = max(latest, pending). Request ≤ 30 s, decision `min(request, checkpoint, DBC now + 30)`, checkpoint ≤ 60 s, paper grant 30 s from `policyEnf`. Expiry is exclusive (`now >= expiresAt` rejects), and a retry never extends a grant. PBC and DBC are separate clocks with uncorrected skew. | chain.py:125-134; witness.py:18, 43, 124, 140; worker.py:140-142 | choice (A21, A24) |
| P8 | **Checkpoint cadence belongs to the runner.** The adapter never pushes checkpoints. A newer accepted checkpoint invalidates older decisions (sequence equality). | adapter.py:163-169 | choice (A22) |
| P9 | **A31 is caller-side, not enforced.** The witness is stateless: before a new checkpoint is accepted, a repeated `collect_decision` yields another valid ALLOW for the same unconsumed request. Single-grant safety comes from the DBC (grantId and (gid, nonce) consumption) and from A22, not from A31. Pre-barrier "no re-collection" is runner discipline, checked from exchange logs. | witness.py:100-142 | correction to A31 (S2-0007) |
| P10 | **encrypt_record is not authenticated.** The ACSC owner and policy are checked; payload commitments are first-writer-wins; a trusted coordinator pre-registers records. | worker.py:76-103 | stated trust assumption (A41) |
| P11 | **Pinned deployment and endpoints.** A request manifest that differs from the pinned one gets WRONG_DESTINATION. RPC is loopback only, with no proxies or redirects. ABIs are hash-pinned. Worker state is fingerprint-bound to chain ids plus contract addresses (not to chain history). | adapter.py:112-130, 226-227; chain.py:52-68; ledger.py:49-50; worker.py:62-72 | hardening |
| P12 | **Token redaction is the runner's job.** The `release` response hands the raw token to the runner. The worker log exports only keccak256(token). Published evidence carries `tokenSha256` and no `token` field. SL1 check: 0 preimages among 790 hex strings (S2-0005). | worker.py:169-171; worker_log.py:36 | obligation |
| P13 | **TEST-ONLY tools stay outside the adapter boundary.** `faulty_adapter` is the crash hook (start-contract-r1, hook f0ab2400..). `deviating_witness` is a deliberate receipt deviation (A40; S2-0007). Both refuse non-TEST-ONLY deployments and print no key. | testtools/ | deliberate mutation / control |

Host: CPython 3.13.5 `.venv`; 3.13.13 is frozen, and agent 2's original runs used 3.13.15. Foundry 1.8.5.

---

## For §5 (E01), the subject-substitution row: protocol-side text (completed [I], SL1)

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

---

## For §7.2 (Crash and recovery): replacement text

### 7.2 Crash and recovery (mechanics completed [I]; paper rows SPEC_GAP under D47)

| Row | paper-strict | paper-minimal | repaired-e |
|---|---|---|---|
| crash after durable intent | **SPEC_GAP / UNPROVED** (frozen label: BLOCKED; D47); mechanics PASS [I] | **SPEC_GAP / UNPROVED** (frozen BLOCKED; D47); mechanics PASS [I] | **REPAIR_SUPPORTED [I]**, bounded logical mechanics only |
| crash after send | **SPEC_GAP / UNPROVED** (frozen BLOCKED; D47); mechanics PASS [I] | **SPEC_GAP / UNPROVED** (frozen BLOCKED; D47); mechanics PASS [I] | **REPAIR_SUPPORTED [I]**, bounded |

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

**Why the paper rows are SPEC_GAP (D47; S2-0002):**

- HMBC specifies **no** key-release durability, retry, idempotence or crash-recovery semantics:
  - III-D3/D4: the PSC returns the DBC response to the user and logs it; the LSC caches pending requests;
  - III-E2: the KSSC partially decrypts and forwards;
  - IV-B/Fig. 8: a cache database holds *pending log sessions*, not release state.
- The crash points exist **only because** this reconstruction moved partial decryption into an off-chain worker (A03).
- The observed behaviour is therefore a **tested reconstruction result of our own completion** (A03, A12, A21, A37, D35/A38). It can neither establish nor refute a paper property.
- The frozen label BLOCKED is shown because it was pre-registered. It was set before D35/A2-0012 made paper releases run at all.
- This is a relabel of an ambiguity class: **not a pass, not a changed outcome, never a finding.**
- Caveat: the "silent" reading rests on the text extraction plus figures 5, 6 and 8 [PLACEHOLDER: confirm against the PDF figures].

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

---

## For §7.3 (Remaining E03 rows): required protocol wording

- **Delivery is unknown in every row.**
  - `RELEASE_SENT` is a write-ahead record of an attempted send, never recipient delivery.
  - The protocol has no recipient acknowledgement (worker.py:3-6, 158).
  - A DBC grant or a GrantReceipt proves **authorization** (a past allowed grant), not delivery or decryption.
- **Dropped outcome:** each row must include the catalog's RELEASE. The evidence is a local intent and send in the worker log while the PBC request stays FORWARDED. Local durable logs do not imply PBC reconciliation, which needs eventual delivery and an honest reporter (A12).
  - Note: agent 1's owner rehearsal omitted RELEASE for these rows (A1-0060 R2 correction), so it is not evidence for them.
- **Receipt-binding controls (SL4):**
  - The inconsistent receipt comes from `testtools.deviating_witness`, a **deliberate witness deviation** (A40) outside the honest-witness assumption. Report it as a defence-in-depth control: never an HMBC attack, never honest-witness behaviour (S2-0007).
  - The receipt-signature controls edit one bound field and keep the honest signature. Binding precedes quorum in repaired-e, so they cannot kill the binding mutant.
- **Fabricated outcome (repaired-e):** besides WRONG_PROFILE on the unattested path, the honest witness refuses to attest a grant that does not exist (NOT_COMMITTED; witness.py:151-154).

---

## For §11 (Ambiguities): protocol items

- **Key-release durability, retries and crash recovery:** the paper is silent. Our worker choice is A03, A12, A21 and A37. The four paper crash rows are SPEC_GAP under D47, next to the frozen BLOCKED.
- **Response recipient in paper profiles:** the paper tuple has no recipient binding. We bind to `RSC.recipientKeyHash(grant.gid)` (D35/A38), so subject substitution routes the symbolic response to the substituted subject (SL1).
- **Decision retry policy:** A31 is caller-side, not an adapter guarantee (P9).
- **Record registration authenticity:** A41 (first-writer-wins payload commitment, trusted pre-registration).

## For §13 (Limitations): protocol items

- Symbolic adapter: no ABE, no ciphertext secrecy, no performance claim. `rotate_epoch` is not implemented (G is locked).
- One trusted witness (q = 1) and a trusted worker. A compromise of either breaks the repaired-e guarantees. The DBC verifies the witness signature, not that a PBC request exists.
- Synthetic, publicly derivable keys. Custody is procedural.
- Logical crash points only; delivery unknown.
- Fingerprints bind chain ids plus addresses: a state directory reused on a fresh chain with identical addresses would be accepted. The runs used new state directories, so there was no effect (S2-0005).
- Clocks: two Anvil chains with uncorrected skew. Second-level cross-chain values are indicative only.
- Margins:
  - repaired-e release and retry margins were thin (3-4 s in the replay/recovery slices);
  - paper releases in SL1 had 28-29 s;
  - all single samples.
- Python 3.13.5 on this host (3.13.13 frozen).

## "Must not claim" checklist (protocol scope; proxy-2 will check the merged report against it before ACK)

1. No ABE, confidentiality, secrecy or performance result, and nothing about HMBC's cryptography (P1).
2. No delivery, receipt-by-user or exactly-once claim. Not "atomic cross-chain logging" (P8, §7.3).
3. No power-loss or OS-kill durability. Crash evidence is two logical points via a TEST-ONLY hook (§7.2).
4. The paper crash rows are **SPEC_GAP / UNPROVED** with the frozen BLOCKED shown (D47). They are never a pass and never a finding.
5. No HMBC vulnerability or exploit from relay-stress rows (subject substitution, forged tuple, wrong destination, new reference, fabricated outcome). They show specification dependencies under configured-relay stress outside A01.
6. No claim that any key is secret (P5), and no quorum, witness-fault or consensus property (P2, P3).
7. Timing constants are project choices, not paper numbers (P7). The revocation window is bounded by them (P8).
8. A31 is described as caller discipline, not an adapter guarantee (P9).
9. The deviating-witness rows are a deliberate deviation (A40), not honest-witness behaviour (§7.3).
10. Owner [U]/[R] evidence (T1-T3, rehearsals) is never counted as an integrated [I] catalog row.
11. The PLAN B-E2 file names (`protocol/faults.py`, `state.py`, `test_{replay,freshness,recovery}.py`) are not claimed to exist as planned. The faults are runner transactions plus `testtools/*`. Only `tests/test_recovery.py` now exists (T2).
12. No JANUS material. F and G are not started.

## Protocol evidence index (for §14)

| Item | Path |
|---|---|
| Protocol pin manifest (E2 runs) | `git show 0716a8e:protocol/evidence/source-manifest.sha256` (d16ddad8.., 108) |
| Current protocol manifest (T1-T3 added) | `protocol/evidence/source-manifest.sha256` (551e9f77.., 127) |
| Owner suite on this host | `protocol/evidence/p2-t1-t3/green-full-suite.txt` (1375 passed, 201 skipped, exit 0) |
| T1-T3 mutants and RED/GREEN | `protocol/evidence/p2-t1-t3/mutation-check-p2-t1-t3.json`; `…/red-green/` |
| Earlier production mutation check | `protocol/evidence/mutation-check.json` (65/73 detected, 8 documented equivalents; agent 2's run) |
| Crash-hook mutation check | `protocol/evidence/mutation-check-faulty-adapter.json` (9/9) |
| SL1 protocol review | `protocol/evidence/reviews/s2-0005-sl1/` |
| Messages | S2-0001..S2-0007; A2-0020..A2-0038 (original agent 2) |
