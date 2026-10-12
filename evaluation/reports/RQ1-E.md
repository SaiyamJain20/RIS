# RQ1 / E: authorization, trust-anchor freshness and audit correspondence in a paper-derived HMBC2020 reconstruction

> **Status: P4-2 report (A1-0082), written by agent 3 (proxy), final text for the P4-3 gate RESULT S3-0023.**
> The gate cells of §6, the gate summary (§5)
> and the ProVerif re-run block (§11) were filled by `fill_gate.py` (`evaluation/reports/fill_gate.py.txt`)
> from the finished gate run `E-gate-20261012` (FREEZE S3-0021, plan `c0086019..`), which agent 1 launched on
> agent 3 (proxy)'s FREEZE. The post-run reviews A1-0084 (ledger) and S2-0022 (protocol) found no discrepancy
> (§18). **Gate E is not yet adjudicated:** that needs the three same-source ACKs on the gate RESULT S3-0023
> (A1-0085, S2-0023 and agent 3 (proxy)'s sign-off S3-0024) and the GATES.md record (A1-0082 P4-3/P4-4).
> F and G stay locked. Historical slice runs are cited next to each row as history.

<!-- GATE-STATUS:BEGIN -->
> **Gate run:** `E-gate-20261012` finished with manifest status **PASS**: 56/56 rows PASS, ProVerif matched, 7 criteria VERIFIED and 2 PENDING by design (RQ1-report, three-matching-acks). Evidence: `evaluation/evidence/e3/gate-run-20261012/`. Run status is not gate E PASS: gate E is adjudicated by the GATES.md checklist and the three same-source ACKs (A1-0082 P4-3/P4-4).
<!-- GATE-STATUS:END -->

## Disclosure: correlated self-review

**Every review and every ACK in the solo phase is correlated self-review.** Agent 1, agent 2 (proxy) and
agent 3 (proxy) are the same model (human solo directive A1-0059). Nothing in this report has been reviewed
independently. The original agents 2 and 3 may re-review and overturn any of it on their return, including the
solo decisions D47, D48 and D49, the criterion 4 scoping (A1-0080) and the window decision (A1-0081).

**Source tags used below.** Text marked **[A1-Ln]** is merged from agent 1's
`communication/agent-1/solo/rq1-ledger-sections.md` (sections L1-L6). Text marked **[S2-…]** is merged from
agent 2 (proxy)'s `communication/agent-1/solo/agent-2-proxy/rq1-protocol-sections.md` (refreshed in 5c4c487).
Message IDs (A1-, S2-, S3-, A2-, A3-) refer to `communication/**`. Where an owner statement predates a later
decision, the report says so next to it and does not change the owner file.

## 0. Answer in brief

The gate run reproduced every row: 56/56 PASS, each with its frozen classification and error (§5, §6). The
answer below rests on the gate run [I]; the historical slice runs agree with it and are cited as history.

1. **What follows from HMBC's specified flow** (paper-strict and paper-minimal, as reconstructed under the
   recorded completions A01-A41; tested reconstruction results, not paper theorems):
   - an **identical** accepted request is not granted twice (REPLAY). This rests on our completion A25
     (deterministic grantId), not on a nonce;
   - a **duplicate outcome** is not recorded twice (REPLAY). "One outcome per request" is a reconstruction
     choice (A1-0042 E03-4);
   - a CA admin **cannot update another issuer's** trust list (UNAUTHORIZED_CALLER, code 16). This is a
     baseline caller restriction in every profile, **not a repair**;
   - a **dropped outcome** leaves the PBC request PENDING (FORWARDED, `outcomeLogId` 0) permanently. Only
     local durable worker evidence exists; reconciliation needs eventual delivery and an honest reporter.
2. **What depends on details the paper leaves open** (SPEC_GAP in both paper profiles):
   - E01: subject substitution, forged tuple, new-reference replay, wrong destination and the expiry
     boundary. The forwarded paper tuple carries no subject, source, destination, nonce or request-expiry
     binding the DBC can check;
   - E02: signed-list rollback (here it **un-revokes** a revoked credential), revocation after the request
     (the paper pre- and post-barrier rows are **one execution**), and an expired duty record (granted at the
     boundary instant);
   - E03: a fabricated outcome ("outcome without a grant"), and crash recovery of key release. The four paper
     crash rows are **frozen BLOCKED / decided SPEC_GAP, UNPROVED** (D47): the paper is silent on durability,
     so they are never a pass and never a finding.

   The relay-stress rows (subject substitution, forged tuple, new reference, wrong destination, fabricated
   outcome) use a compromised configured relay, which is **outside A01** (the paper's secure isolation). They
   show specification dependencies, **not HMBC exploits**.
3. **What the repaired-e extension enforces** (a project extension, not HMBC; tested reconstruction results):
   DV step 4 WRONG_SUBJECT; DV step 6 BAD_SIGNATURE; REPLAY from grant uniqueness (`KSSC.sol:180`) and, only
   in the same-nonce row, from the nonce guard (`KSSC.sol:181-183`); WRONG_DESTINATION at DV **step 1** (source
   binding) for the catalog recipe; EXPIRED at **equality** with the request expiry (DV step 9, `>=`);
   STALE_ANCHOR at `TMSC.sol:190`; STALE_STATE from the line 87 **sequence** cause after the revoking
   checkpoint; EXPIRED at DV step 13 for an expired duty record; WRONG_PROFILE on the unattested outcome path
   and receipt-binding WRONG_SUBJECT on the attested one (the binding rows use a deliberate witness deviation,
   A40; the receipt-signature controls and the receipt positive control are frozen as SUPPORTED controls of
   the same path); and bounded logical crash-recovery mechanics (identical cached response before expiry,
   EXPIRED after it).
   **Measured limits:** request TTL ≤ 30 s, with thin single-sample margins. In the gate run the repaired
   SL6 expired-duty consume came 7 s before the binding request expiry. The repaired SL7 expiry-boundary
   consume was at exactly `r.expiresAt`, and the witness's own DBC now + 30 was at least 1 s past
   `r.expiresAt`, so the request expiry bound the decision (§3.4); that is a margin between two expiry
   terms, not a window. Before the DBC accepts a revoking checkpoint, an older certificate is still
   accepted: that window is intentional. The owner measurement bounds it by
   W = min(time until the DBC accepts a post-revocation checkpoint, remaining request/decision TTL) ≤ 30 s
   (A1-0046); no window was measured by the integrated runner (A1-0081).
4. **What stays BLOCKED, unproved or not run:**
   - paper key-release durability (D47 above);
   - the integrated live mutant matrix: **not run**. Gate criterion 4 is "met on owner, formal and baseline
     evidence (human decision A1-0080); integrated live mutant matrix not run" (reason: safety-classifier
     stop, A1-0079);
   - the integrated revocation window: **not run** (A1-0081);
   - a kill of the destination-binding mutant by the catalog recipe: impossible, because step 1 fires first;
   - delivery to the recipient (unknown in every row), the hash-only log mode, TempACL rollback, acceptance at
     `expiresAt − 1`, witness or worker compromise (phase F), real encryption (no ABE), statistics (one trial
     per row) and independent review.

No count of "vulnerabilities" is given, because none is claimed.

## 1. Research question

**RQ1 (SPEC §1):** Which authorization, trust-anchor freshness and audit properties follow from HMBC's
specified access flow, which depend on missing details, and which explicit repairs enforce them in a
reconstruction?

**Required answer (SPEC §1):** a source-to-property table (§4); executable positive and negative traces for
three case families: E01 decision provenance and replay, E02 trust-anchor freshness, E03 audit correspondence
(§6-§9); repair comparisons (§7-§9, §12); and a bounded statement of what was proved or tested (§0, §15, §16).

**Paper:** V. Malamas, P. Kotzanikolaou, T. K. Dasaklis, M. Burmester, "A Hierarchical Multi Blockchain for
Fine Grained Access to Medical Data", IEEE Access 8 (2020) 134393-134412, DOI 10.1109/ACCESS.2020.3011201
(`references/HMBC2020.pdf`).

## 2. What this is and is not

- A **paper-derived reconstruction**, not the authors' implementation (no authors' code was available).
  Missing details are explicit choices (`interfaces/v1/assumptions.csv`, A01-A41), **not discovered
  vulnerabilities**.
- **HMBC only.** No JANUS code, claims or bug catalogue is used or claimed.
- **Synthetic fixtures only.** Authorities H1-H4; Alice (doctor at H1, on duty); Bob (registered, no doctor
  role); record `HMBC.data.P1.MHR`. All keys are TEST-ONLY and derivable from labels.

### 2.1 Result classes

| SPEC class | AGENTS.md vocabulary |
|---|---|
| SUPPORTED | paper-supported behaviour, *as reconstructed under recorded completions* (a tested reconstruction result) |
| SPEC_GAP | ambiguity |
| REPAIR_SUPPORTED | extension result |
| RECONSTRUCTION_FAILURE, REFUTED | tested reconstruction result |
| BLOCKED / UNPROVED | not tested or unproved |
| `mutant-*` outcomes, deviating-witness rows (A40) | deliberate mutation |

### 2.2 Evidence levels

| Level | Meaning |
|---|---|
| [I] | integrated two-chain run under a FREEZE with the exact ACKs (agent 3, or agent 3 (proxy) in the solo phase) |
| [R] | agent 1's owner rehearsal or owner measurement |
| [U] | module unit or process tests |
| [F] | symbolic ProVerif |

Only [I] answers a catalog row. The gate run is the [I] evidence for all 56 rows; each slice's historical [I]
run is cited next to it.

### 2.3 Must not claim

Merged from [A1-L1], [A1-L5], the [S2] "must not claim" checklist (items 1-15) and A1-0082:

- **No consensus.** Anvil with automining or interval mining on one host is not a consensus implementation,
  not PoS and not Byzantine-tolerant. The "safe ledger" assumption (correct execution, no reorg) is assumed,
  not tested [A1-L1].
- **No ABE, no real encryption, no secrecy or performance result,** and nothing about HMBC's cryptography.
  The adapter's crypto is symbolic [S2 P1]. A symbolic model is not a measured cryptographic implementation.
- **No claim about the authors' implementation.** The KSSC holds authorization state only; key material lives
  in agent 2's off-chain worker [A1-L1].
- **No delivery, receipt-by-user or exactly-once claim,** and no "atomic cross-chain logging" [S2 item 2].
- **No power-loss or OS-kill durability.** Crash evidence is two logical points via a TEST-ONLY hook [S2 item 3].
- **No HMBC vulnerability or exploit** from relay-stress rows. They are configured-relay stress outside A01
  [A1-L5 item 3; S2 item 5].
- **No key secrecy.** TEST-ONLY keys are derivable from labels. No second deployment (D2, SL7's B) is a
  separately keyed authority [S2 item 6].
- **One trusted witness and a trusted worker.** No quorum, witness-fault, consensus or Byzantine property
  [S2 item 7].
- **Timing constants are project choices,** not paper numbers [S2 item 8].
- **No statistics.** One trial per row on one host; wall times are single samples.
- **No JANUS material.** F and G are not started.
- Owner [U]/[R] evidence is never counted as an integrated catalog row or as an integrated mutant kill
  [S2 item 11].
- The four paper crash rows are **frozen BLOCKED / decided SPEC_GAP, UNPROVED** (D47): never a pass, never a
  finding [S2 item 4].
- A31 is caller discipline, not an adapter guarantee; D49 is a runner recording rule, not an idle-worker
  export [S2 item 9]. The deviating-witness rows are a deliberate deviation (A40), not honest-witness
  behaviour [S2 item 10].
- Criterion 4 uses the A1-0080 wording (no integrated live mutant kill, nothing about adapter or relay
  mutants); the window uses the A1-0081 wording (no integrated window measurement) [S2 item 12].
- The PLAN B-E2 file names (`protocol/faults.py`, `state.py`, `test_{replay,freshness,recovery}.py`) are not
  claimed to exist as planned: the faults are runner transactions plus `testtools/*`; only
  `tests/test_recovery.py` exists (T2) [S2 item 13].

## 3. System, profiles and method

### 3.1 Ledger [A1-L1, A1-L2]

- **Six contracts on two Anvil chains:** PBC: RSC, TMSC, PSC, LSC; DBC: ACSC, KSSC. Solidity 0.8.37,
  Foundry 1.8.5, no external Solidity dependencies (`ledger/README.md`). Pin 933d2a7 (manifest c7b7dd51..,
  195 entries).
- **Profiles are fixed at deployment** (`ledger/README.md` "Profiles"; `TMSC.sol:30-45`):

  | Profile | Meaning |
  |---|---|
  | `paper-strict` | issuer-scoped CA-Admin caller, list signed by the issuer root key; latest appended list is current, with no version ordering or list expiry (paper silent) |
  | `paper-minimal` | as strict, but the list signature is not verified on chain |
  | `repaired-e` | **a project extension, not HMBC**: strict plus monotone list versions, list validity at use, typed witness decisions verified by the 13-step `DecisionVerifier`, `(gid, nonce)` consumption, a state-checkpoint barrier, destination binding and request/grant-correlated receipts |
  | `mutant-*` | repaired-e minus one check (bit). These exist only to show that tests and oracles are sensitive. They are never HMBC evidence |

- **DecisionVerifier check order** (`ledger/src/DecisionVerifier.sol` header) is fixed, so a multi-defect
  certificate always yields the same code [A1-L2]:

  | Step | Check | Code |
  |---|---|---|
  | 1 | source | WRONG_DESTINATION (3) |
  | 2 | destination | WRONG_DESTINATION (3) |
  | 3 | action | MALFORMED |
  | 4 | request binding | WRONG_SUBJECT (2) |
  | 5 | witness-set version | STALE_STATE (6) |
  | 6 | signatures | BAD_SIGNATURE (1) / quorum codes |
  | 7 | result | — |
  | 8 | credential binding | WRONG_SUBJECT |
  | 9 | request/decision expiry, `now >= expiresAt` | EXPIRED (7) |
  | 10 | checkpoint freshness | STALE_STATE |
  | 11 | auth/policy epoch | STALE_STATE |
  | 12 | key epoch | WRONG_EPOCH |
  | 13 | record validity at now | EXPIRED |

### 3.2 Protocol module, key custody and symbolic mode [S2 §3.x]

**What runs.** The protocol module (`protocol/`, pinned owner snapshot 0716a8e, manifest d16ddad8.., 108
entries) is one **JSON-lines adapter process per deployment**: `python -m hmbc_protocol.adapter --state-dir
<new 0700 dir> --deployment <file>`, with eight closed operations: `prepare_request`, `collect_checkpoint`,
`collect_decision`, `attest_grant`, `encrypt_record`, `release`, `finish_decryption`, and `rotate_epoch`
(which answers NOT_IMPLEMENTED_IN_PHASE).

**Option A: the adapter submits no transactions.** The runner submits every PBC/DBC transaction as the
configured relay or as an issuer-scoped CA admin. User, witness and worker keys resolve only inside the
adapter process (BOUNDARY.md; A36).

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

The P1-P16 table is copied verbatim from [S2 §3.x].

### 3.3 Catalog and execution discipline

- **Catalog:** the frozen `interfaces/v1/scenarios/e0_cases.json` (48 rows = 16 schedules × 3 profiles,
  sha256 438fa38d..) plus `e0_supplement_cases.json` (8 repaired-e rows, sha256 9ccade36..) = **56
  comparisons**. Positive controls are in `e_positive.json` (9). Expectations were frozen in E0 (FREEZE
  `f700292e..`) **before** any E2 observation. No frozen byte has changed.
- **Chains:** two local Anvil chains per row, PBC (chain ID 18545, port 18545) and DBC (chain ID 28545, port
  18546 in solo plans, D48). Foundry 1.8.5, solc 0.8.37. A fresh chain pair and fresh deployments for every
  row.
- **Per-row controls (D1):** wrong-admin (code 16) before the legitimate H2 update; Alice allowed, released,
  completed and one outcome; Bob policy-denied (code 9). The stress runs on a fresh second deployment D2 on
  the same chain pair (and a third deployment B for wrong destination).
- **Discipline:** a FREEZE with the exact plan SHA-256; exact solo ACKs (ledger and protocol scope) committed
  before services; owner snapshots materialized from Git blobs at the pins (ledger 933d2a7, protocol 0716a8e);
  source brackets before and after; oracles independent of the implementation's control flow; failed trials
  kept and never retried silently.

### 3.4 Clocks and measured margins [S2 "Witness timing"]

Rules (witness.py at the pin): **record lapse gives DENY, never ALLOW** (lines 133-134), so an expired-duty
ALLOW must be collected while the duty is valid at DBC now; **decision expiry** = `min(request.expiresAt,
checkpoint.expiresAt, DBC now + 30)` (line 140); **checkpoint** sequence = DBC current + 1, `expiresAt = DBC
now + 60` (lines 54-67); a freshness refusal is an exception, never a signature (lines 109-125).

Measured in the historical slice runs (DBC/chain seconds, single samples, 1 s granularity, two Anvil clocks
with uncorrected skew):

| Item | Value | Source |
|---|---|---|
| Which decision term binds | `request.expiresAt` in every repaired row where checked (SL6 ×3, SL7 expiry boundary). Witness DBC now + 30 exceeded it by 1-2 s in SL6 (1 s lower bound from cp expiry − 60; 2 s upper bound from the runner's later reading) and by ≥ 1 s in SL7 | S2-0018, S2-0020 |
| SL7 expiry boundary | consume at exactly `r.expiresAt`: decision `expiresAt` = request `expiresAt` = consume block timestamp = 1791727102; checkpoint 1791727133. The witness's own DBC now + 30 was at least 1 s past `r.expiresAt`, so the request expiry bound the decision. A structural margin between two expiry terms, not a window | S2-0020 |
| SL6 expired duty (repaired) | decision collected at DBC 1791704470, duty end 1791704490 (**20 s** before lapse, so ALLOW was correct); consume 1791704491 vs decision/request expiry 1791704498: **7 s** | S2-0018 |
| SL6 pre-/post-barrier (repaired) | consume 24 s / 23 s before decision expiry | timelines |
| SL6 post-barrier cp2 | sequence 2, authEpoch 4 (= revocation's after-epoch), source block 49 (= revocation block), collected after the revocation transaction | S2-0018 |
| SL2 same nonce | 24 s between the second consume and the earliest request expiry | S2-0010 |
| SL1 paper releases | 29 s, 28 s before grant expiry | S2-0005 |
| SL3 dropped-outcome releases | 29 s, 28 s (paper); 26 s (repaired, after checkpoint and decision) | S2-0012 |
| E2 recovery retries (repaired) | about 4 s before expiry | A1-0049 |

Measured in the gate run (`evaluation/evidence/e3/gate-run-20261012/thin-row-margins.json`, extracted from the published result files and
native records; same units and limits):

| Row | Value |
|---|---|
| SL7 expiry boundary, repaired-e | request 1791773414; consume = `r.expiresAt` = `d.expiresAt` = 1791773444; `firingStep` 9. The checkpoint expiry 1791773475 (= DBC now + 60) puts the checkpoint at DBC 1791773415, and the decision was collected after it (DBC read before the pin: 1791773416). So the witness's own DBC now + 30 was at least 1 s past `r.expiresAt`, and the request expiry bound the decision |
| SL6 expired duty, repaired-e | duty end 1791772820; consume 1791772821; request and decision expiry 1791772828: **7 s**; `expiredStep` 13 |
| Identical replay, repaired-e | grant 1791769486; replay 1791769487 and release 1791769489, 25 s and 23 s before `r.expiresAt` 1791769512 |
| Crash recovery, repaired-e | last send 23 s before the original expiry (1791769054 after intent, 1791769124 after send); the expired cached retry was observed at expiry + 1 and returned EXPIRED |
| Paper rows | recovery and identical replay: 27-29 s before the paper grant expiry (block + 30); SL6 expired duty granted at DBC time = duty end (8 s and 7 s before the request expiry); SL7 expiry boundary granted at exactly `r.expiresAt` |
| Every decision of the run (repaired-e rows: 66 = 48 D1 + 18 stress) | `d.expiresAt` = `request.expiresAt` < `checkpoint.expiresAt` in all 66. The checkpoint lower bound (cp − 60, the witness's DBC time at creation; witness.py:65) plus 30 exceeds the request expiry by 1-21 s (minimum 1 s), so the request term bound every decision, shown without the witness's private clock (agent 2 (proxy)'s post-run re-check S2-0022, item G) |

A1-0082 flagged the SL7 and SL6 margins as the thin ones for the gate run; both held, with the values above.
Every oracle refuses an overrun rather than passing it, so a miss is a visible failed trial, never a silent
pass [S2 "Witness timing"]. These margins are properties of this host, not of the protocol (A1-0074 point 6).

## 4. Source-to-property table

Built from `interfaces/v1/source-map.csv` (S-ids, PDF pages) and `assumptions.csv` (A-ids). "Observed" is
the class each row family showed in its historical slice run; the gate run showed the same class for every row,
and the gate column of §6 is authoritative.

| Property (family) | Paper source (PDF p., section) | What the paper specifies | What it leaves open (assumptions) | Paper profiles (observed) | repaired-e mechanism (observed) | Rows (§6) |
|---|---|---|---|---|---|---|
| Subject binding of the forwarded decision (E01) | S12 p.12 Fig. 6; S09 p.10-11 III-E1; S20 p.15 Table 3; S13 p.14 V-A1 | PSC validates credentials and forwards GID, verified attributes and data id; ACSC enforces policy; `policyEnf` actuator is the PSC | no nonce, EIP-712, destination binding or witness attestation format; no authenticated cross-chain actuator (A02, A14, A19, A25, A38, A41) | relay-asserted gid is granted: SPEC_GAP | DV step 4, WRONG_SUBJECT: REPAIR_SUPPORTED | 13-15 |
| Source authentication of the tuple (E01) | S12; S20; S13 | as above | as above; secure isolation assumed (A01) | `policyEnf` needs no PBC request: SPEC_GAP | DV step 6, BAD_SIGNATURE: REPAIR_SUPPORTED | 16-18 |
| Replay of an identical accepted request (E01) | S35 p.12 Fig. 6 | a transaction reference travels with the response | no duplicate-forward or nonce rule (A25) | deterministic grantId: REPLAY, SUPPORTED (rests on A25) | same guard: REPAIR_SUPPORTED | 10-12 |
| Replay under a new reference or a reused nonce (E01) | S35; S12 | as above | A25, A39 | new reference gives a second grant: SPEC_GAP | REPLAY (`KSSC.sol:180`; nonce guard `KSSC.sol:181-183` only in the same-nonce row): REPAIR_SUPPORTED | 19-22 |
| Destination binding (E01) | S12; S24 p.12 IV-A | two independent chains interact through APIs | tuple has no destination or source field (A14, A19) | A grants on B's tuple: SPEC_GAP | DV step 1 (source), WRONG_DESTINATION: REPAIR_SUPPORTED | 51-53 |
| Request expiry at the DBC (E01) | S34 p.12 Fig. 6 | synchronous `requestData` | no asynchronous grant lifetime or request-expiry check (A19, A20, A24) | granted at the request-expiry instant: SPEC_GAP | DV step 9 at equality (`>=`), EXPIRED: REPAIR_SUPPORTED | 54-56 |
| Issuer scoping of trust-list updates (E02) | S03 p.8 III-C5/C6; S17 p.15 Table 2 | lists belong to independent stakeholders and are signed; `updateTrustAnchors` actuator is the CA Admin | transport and verifier (A08) | UNAUTHORIZED_CALLER (16): SUPPORTED, baseline in every profile, **not a repair** | same | 36-38 |
| Trust-list freshness, rollback (E02) | S04 p.9 III-D1a/c | validation uses the latest list indices | "latest append is not anti-rollback" (A09) | old signed list re-accepted: SPEC_GAP | `TMSC.sol:190` STALE_ANCHOR: REPAIR_SUPPORTED | 39-41 |
| Revocation reaching the DBC (E02) | S15 p.16 V-A4 | mediation can stop new decryption requests after revocation | no recall; cross-chain finality/barrier unspecified (A17, A20, A22) | no barrier; tuple stays grantable: SPEC_GAP (one execution) | pre-barrier accept (intended); post-barrier STALE_STATE, line 87 sequence: REPAIR_SUPPORTED | 42-47 |
| Temporal record validity at use (E02) | S02 p.7 III-C4; S33 p.9 III-D1c | temporal roles with effective periods | validity check at use not stated (A07, A23) | granted at the boundary instant: SPEC_GAP | DV step 13, EXPIRED: REPAIR_SUPPORTED | 48-50 |
| Outcome correspondence (E03) | S06 p.15 Table 2, V-A5; S07 p.10 III-D3/D4; S19 p.15 Table 2 LSC; S26; S36 | requests are logged; the PSC returns the response and logs it | no atomic delivery, authenticated grant receipt or outcome method (A11, A12, A26) | duplicate REPLAY: SUPPORTED; dropped PENDING: SUPPORTED; fabricated recorded: SPEC_GAP | duplicate REPLAY; WRONG_PROFILE on the unattested path; receipt binding WRONG_SUBJECT: REPAIR_SUPPORTED | 7-9, 23-35 |
| Log content (E03) | S08 p.10 III-D4, V-B3 | detailed and hash-only logging both described | which one (A13) | complete details only were run; **hash-only NOT RUN** | same | – |
| Key-release durability and crash recovery (E03) | S10 p.11 III-E2/Fig. 5; S21 p.15 Table 3; S07 | KSSC partially decrypts and forwards | silent on durability, retry, recovery (A03, A12, A21, A37) | frozen BLOCKED / decided SPEC_GAP, UNPROVED (D47) | bounded logical mechanics: REPAIR_SUPPORTED | 1-6 |

## 5. The gate run (one command)

**Command** (S3-0021; run from the repository root after the committed FREEZE and both ACKs):

```
export PATH="$HOME/.foundry/bin:$PATH"
.venv/bin/python -m evaluation.e_gate \
  --plan evaluation/evidence/e3/gate-plan-20261012/integration-plan.json \
  --acks /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/gate-run/acks.json \
  --output /home/saiyamjain/.claude/jobs/aed51961/tmp/p3/gate-run/out
```

- **Launched by agent 1** on this host, detached, on agent 3 (proxy)'s FREEZE S3-0021: 2026-10-12T07:01:35+05:30
  at HEAD 21b37fb to 08:20:46+05:30, exit 0 (`run.meta`, `run.exit` in the published evidence).
- **Plan:** `evaluation/evidence/e3/gate-plan-20261012/integration-plan.json`, sha256
  `c00860192aaa69fd2e5f7baf132f5ebf10bf14ebba377edada31c1d9372b6bb9`, runId `E-gate-20261012`. It embeds the
  ten slice plans that the existing `e2.create_plan` slice flags produce; every row runs once through
  `evaluation.e2.run_row`, the P2 slice runner and its frozen row check. **No new oracle** (A1-0082 P4-1;
  checked in A1-0083 and S2-0021).
- **ACKs:** A1-0083 (ledger scope) and S2-0021 (protocol scope), both on the exact plan hash. Both are
  correlated self-review.
- **Stages:** 1 verify-freeze and versions; 2 source bracket (pre); 3 all 56 rows; 6 ProVerif re-run compared
  byte for byte with A3-0033 and `p3-proverif-20261012`; 7 source bracket (post), HEAD and `git status`
  unchanged, plan re-verified; 8 `manifest.json`; 9 `gate-evidence.json`.
- **Dropped stages:** 4 mutants (human decision A1-0080) and 5 window (human decision A1-0081).
- **Failure policy:** each row runs exactly once; a failed row is kept with its type and message, the run
  continues on a fresh chain pair, and any FAILED or NOT_RUN row makes the run FAILED. Re-running a failed row
  needs a new FREEZE (A1-0082).
- **Manifest status is not gate E PASS.** `evaluation/gate.py` stays fail-closed by design; gate E is the
  GATES.md checklist plus the three same-source ACKs (A1-0082 P4-3/P4-4).
- **Published evidence:** `evaluation/evidence/e3/gate-run-20261012/`, a selected copy of the raw output (selection, exclusions and the
  never-publish scan are in its README; INTEGRATION_RESULT S3-0022).

**Gate summary** (filled from the gate output by `fill_gate.py`):

<!-- GATE-SUMMARY:BEGIN -->
| Item | Value |
|---|---|
| Run ID / FREEZE | `E-gate-20261012` / S3-0021 |
| Plan sha256 | `c00860192aaa69fd2e5f7baf132f5ebf10bf14ebba377edada31c1d9372b6bb9` |
| Manifest status | **PASS** (run stages only; not gate E PASS) |
| Rows | 56 PASS, 0 FAILED, 0 NOT_RUN, 0 RUNNING (of 56) |
| ProVerif matched | True |
| sourceStable / worktreeUnchanged / planReverified | True / True / True |
| HEAD before / after | `21b37fbaf569ef37ddd679f0f1db1891fd8db75d` / `21b37fbaf569ef37ddd679f0f1db1891fd8db75d` |
| Started / ended (UTC) | 2026-10-12T01:31:36.460526+00:00 / 2026-10-12T02:50:45.957045+00:00 |
| Wall time | 4749 s (1.32 h) |
| MemAvailable before / after | 3805 MiB / 3751 MiB |
| MemFree before / after | 1109 MiB / 785 MiB |
| SwapFree before / after | 11657 MiB / 11661 MiB |
| Lowest MemAvailable at a row start | 3489 MiB |
| Published evidence | `evaluation/evidence/e3/gate-run-20261012/` |
| sha256 `manifest.json` | `908fd6156ac5c6c4f640686fbddade3f9720cf29fb1e579f7c3d01f0909205a2` |
| sha256 `gate-evidence.json` | `47e38dd369ce686d5298f909c43c79cdf4b7eff4d20d41988a57f80974538500` |
| sha256 `catalog-coverage-56.json` | `e57e49835a7addead3e7aa210ad12ea0604093342ad33961052c450dbebba8f4` |
| sha256 `proverif/summary.json` | `d8c4a946231593d7be4ef18734c21354ee5e491e469fb60c89a6edb0416faab7` |

| Stage | Status |
|---|---|
| verify-freeze-and-versions | PASS |
| source-bracket-pre | PASS |
| catalog-56 | PASS |
| proverif | PASS |
| source-bracket-post | PASS |
| gate-evidence | WRITTEN |
| manifest | WRITTEN |
| mutants (dropped) | not run: S3-0002 stage 4 dropped by the human decision A1-0080 (after the A1-0079 safety-classifier stop): criterion 4 rests on owner, formal and baseline evidence; the integrated live mutant matrix is not run and is never resumed |
| window (dropped) | not run: S3-0002 stage 5 dropped by the human decision A1-0081: no revocation window is measured by this run; the report cites the owner measurement A1-0046 and the SL6 ordering result |

| Slice | Status | Rows PASS | Row wall time (sum) |
|---|---|---|---|
| recovery-expiry | E2_RECOVERY_EXPIRY_SLICE_PASS | 6/6 | 399 s |
| duplicate-outcome | E2_DUPLICATE_OUTCOME_SLICE_PASS | 3/3 | 193 s |
| nonce-replay | E2_NONCE_REPLAY_SLICE_PASS | 3/3 | 189 s |
| sl1-subject | E2_SUBJECT_SUBSTITUTION_SLICE_PASS | 3/3 | 291 s |
| sl2-relay | E2_RELAY_STRESS_SLICE_PASS | 7/7 | 651 s |
| sl3-audit | E2_AUDIT_STRESS_SLICE_PASS | 6/6 | 493 s |
| sl4-receipt | E2_RECEIPT_STRESS_SLICE_PASS | 7/7 | 576 s |
| sl5-trust | E2_TRUST_STRESS_SLICE_PASS | 6/6 | 453 s |
| sl6-barrier | E2_BARRIER_STRESS_SLICE_PASS | 9/9 | 834 s |
| sl7-destination | E2_DESTINATION_STRESS_SLICE_PASS | 6/6 | 613 s |

| Criterion (`gate-evidence.json`) | Status |
|---|---|
| interface-and-source-review | VERIFIED |
| legitimate-and-denied-controls | VERIFIED |
| E01-E02-E03-classification | VERIFIED |
| repairs-and-mutants | VERIFIED (human-scoped, A1-0080) |
| real-two-chain-and-recovery | VERIFIED |
| proverif-and-negative-control | VERIFIED |
| RQ1-report | PENDING (by design: adjudicated after the run) |
| stable-hashed-input-output-tools | VERIFIED |
| three-matching-acks | PENDING (by design: adjudicated after the run) |
<!-- GATE-SUMMARY:END -->

## 6. Results: all 56 rows

Paths in the **Gate path** column are relative to the published gate evidence directory `evaluation/evidence/e3/gate-run-20261012/`
(raw output: `tmp/p3/gate-run/out/` in job tmp, never published unselected). The **GATE** column is the gate
run's row status, the classification reported by `catalog-coverage-56.json` and the observed error; the
**Historical run** column is the earlier slice run of the same recipe, cited as history. Rows marked
**(guard)** are the 8 guard rows of gate criterion 4 (§12). The four paper crash rows carry the D47 label.

<!-- row skeleton generated by agent 3 (proxy)'s scratch helper gen_rows.py (job tmp, not published) from the frozen catalog, the gate plan c0086019.. and the historical result.json files; GATE cells filled by fill_gate.py -->

#### E03 crash and recovery (6 rows): slice `recovery-expiry`

- Gate rows: `catalog/recovery-expiry/<case>/<profile>/`, primary proof `recovery/result.json` (also `expired-retry/result.json`).
- Historical run: `evaluation/evidence/e2/expiry-live-20261009/` (A3-0037 plan a76a291d..; ACKs A1-0050, A2-0030; 779.772 s, exit 0; result A3-0038); pre-solo, agent 3 host, strict mode; ledger reviews A1-0049 (recovery) and A1-0051 (expiry), protocol reviews by the original agent 2 (A2-0029, A2-0031). Also: recovery-only run `evaluation/evidence/e2/recovery-live-20261009/` (A3-0035 plan 4bceffc3..; A1-0048, A2-0028; 778.47 s, exit 0; A3-0036).

| # | Case ID | Profile | Frozen expectation (outcome · class · error) | Historical run (class · error) | GATE (status · class · error) | Gate path |
|---|---|---|---|---|---|---|
| 1 | `E03-crash-after-intent-paper-strict` | paper-strict | UNPROVED · BLOCKED · – → **frozen BLOCKED / decided SPEC_GAP, UNPROVED** (D47) | recovery ok=True; expired retry EXPIRED (ok=True); class recorded BLOCKED (pre-D47) | PASS (mechanics) · frozen BLOCKED / decided SPEC_GAP, UNPROVED · –; expired retry EXPIRED, 67 s | `catalog/recovery-expiry/paper-strict-after_intent/paper-strict/` |
| 2 | `E03-crash-after-send-paper-strict` | paper-strict | UNPROVED · BLOCKED · – → **frozen BLOCKED / decided SPEC_GAP, UNPROVED** (D47) | recovery ok=True; expired retry EXPIRED (ok=True); class recorded BLOCKED (pre-D47) | PASS (mechanics) · frozen BLOCKED / decided SPEC_GAP, UNPROVED · –; expired retry EXPIRED, 66 s | `catalog/recovery-expiry/paper-strict-after_send/paper-strict/` |
| 3 | `E03-crash-after-intent-paper-minimal` | paper-minimal | UNPROVED · BLOCKED · – → **frozen BLOCKED / decided SPEC_GAP, UNPROVED** (D47) | recovery ok=True; expired retry EXPIRED (ok=True); class recorded BLOCKED (pre-D47) | PASS (mechanics) · frozen BLOCKED / decided SPEC_GAP, UNPROVED · –; expired retry EXPIRED, 65 s | `catalog/recovery-expiry/paper-minimal-after_intent/paper-minimal/` |
| 4 | `E03-crash-after-send-paper-minimal` | paper-minimal | UNPROVED · BLOCKED · – → **frozen BLOCKED / decided SPEC_GAP, UNPROVED** (D47) | recovery ok=True; expired retry EXPIRED (ok=True); class recorded BLOCKED (pre-D47) | PASS (mechanics) · frozen BLOCKED / decided SPEC_GAP, UNPROVED · –; expired retry EXPIRED, 63 s | `catalog/recovery-expiry/paper-minimal-after_send/paper-minimal/` |
| 5 | `E03-crash-after-intent-repaired-e` | repaired-e | CONDITIONAL · REPAIR_SUPPORTED · – | recovery ok=True; expired retry EXPIRED (ok=True); class recorded REPAIR_SUPPORTED (bounded mechanics) | PASS · REPAIR_SUPPORTED · –; expired retry EXPIRED, 68 s | `catalog/recovery-expiry/repaired-e-after_intent/repaired-e/` |
| 6 | `E03-crash-after-send-repaired-e` | repaired-e | CONDITIONAL · REPAIR_SUPPORTED · – | recovery ok=True; expired retry EXPIRED (ok=True); class recorded REPAIR_SUPPORTED (bounded mechanics) | PASS · REPAIR_SUPPORTED · –; expired retry EXPIRED, 71 s | `catalog/recovery-expiry/repaired-e-after_send/repaired-e/` |

#### E03 duplicate outcome (3 rows): slice `duplicate-outcome`

- Gate rows: `catalog/duplicate-outcome/<case>/<profile>/`, primary proof `alice/duplicate-outcome/result.json`.
- Historical run: `evaluation/evidence/e2/duplicate-live-20261009/` (A3-0039 plan 5ef10dc6..; ACKs A1-0052, A2-0032; 365.374 s, exit 0; result A3-0040); pre-solo, agent 3 host, strict mode; ledger review A1-0053.

| # | Case ID | Profile | Frozen expectation (outcome · class · error) | Historical run (class · error) | GATE (status · class · error) | Gate path |
|---|---|---|---|---|---|---|
| 7 | `E03-duplicate-outcome-paper-strict` | paper-strict | NO_NEW_OUTCOME · SUPPORTED · REPLAY | SUPPORTED · REPLAY | PASS · SUPPORTED · REPLAY, 63 s | `catalog/duplicate-outcome/paper-strict-duplicate-outcome/paper-strict/` |
| 8 | `E03-duplicate-outcome-paper-minimal` | paper-minimal | NO_NEW_OUTCOME · SUPPORTED · REPLAY | SUPPORTED · REPLAY | PASS · SUPPORTED · REPLAY, 63 s | `catalog/duplicate-outcome/paper-minimal-duplicate-outcome/paper-minimal/` |
| 9 | `E03-duplicate-outcome-repaired-e` | repaired-e | NO_NEW_OUTCOME · REPAIR_SUPPORTED · REPLAY | REPAIR_SUPPORTED · REPLAY | PASS · REPAIR_SUPPORTED · REPLAY, 67 s | `catalog/duplicate-outcome/repaired-e-duplicate-outcome/repaired-e/` |

#### E01 identical accepted-request replay (3 rows): slice `nonce-replay`

- Gate rows: `catalog/nonce-replay/<case>/<profile>/`, primary proof `alice/nonce-replay/result.json`.
- Historical run: `evaluation/evidence/e2/grouped-replay-live-20261009/` (A3-0044 plan 1b3cf7cd..; ACKs A1-0056, A2-0037; 375.185 s, exit 0; result A3-0045); pre-solo, agent 3 host, strict mode; ledger review A1-0057. Also: earlier failed trial `evaluation/evidence/e2/nonce-replay-live-20261009/` (plan a7732650.., result A3-0042, 341.181 s, exit 2: repaired release EXPIRED; ledger review A1-0055), kept.

| # | Case ID | Profile | Frozen expectation (outcome · class · error) | Historical run (class · error) | GATE (status · class · error) | Gate path |
|---|---|---|---|---|---|---|
| 10 | `E01-nonce-replay-paper-strict` | paper-strict | NO_NEW_GRANT · SUPPORTED · REPLAY | SUPPORTED · REPLAY | PASS · SUPPORTED · REPLAY, 63 s | `catalog/nonce-replay/paper-strict-nonce-replay/paper-strict/` |
| 11 | `E01-nonce-replay-paper-minimal` | paper-minimal | NO_NEW_GRANT · SUPPORTED · REPLAY | SUPPORTED · REPLAY | PASS · SUPPORTED · REPLAY, 60 s | `catalog/nonce-replay/paper-minimal-nonce-replay/paper-minimal/` |
| 12 | `E01-nonce-replay-repaired-e` | repaired-e | NO_NEW_GRANT · REPAIR_SUPPORTED · REPLAY | REPAIR_SUPPORTED · REPLAY | PASS · REPAIR_SUPPORTED · REPLAY, 66 s | `catalog/nonce-replay/repaired-e-nonce-replay/repaired-e/` |

#### E01 subject substitution, SL1 (3 rows): slice `sl1-subject`

- Gate rows: `catalog/sl1-subject/<case>/<profile>/`, primary proof `subject-stress/subject-substitution/result.json` (paper rows also `subject-stress/subject-completion/result.json`).
- Historical run: `evaluation/evidence/e2/sl1-subject-live-20261010/` (S3-0005 plan 6fd5809b..; ACKs A1-0062, S2-0004; 255.73 s, exit 0; result S3-0006); reviews A1-0063 (ledger), S2-0005 (protocol).

| # | Case ID | Profile | Frozen expectation (outcome · class · error) | Historical run (class · error) | GATE (status · class · error) | Gate path |
|---|---|---|---|---|---|---|
| 13 | `E01-subject-substitution-paper-strict` | paper-strict | CONDITIONAL · SPEC_GAP · – | SPEC_GAP · – | PASS · SPEC_GAP · –, 93 s | `catalog/sl1-subject/paper-strict-subject-substitution/paper-strict/` |
| 14 | `E01-subject-substitution-paper-minimal` | paper-minimal | CONDITIONAL · SPEC_GAP · – | SPEC_GAP · – | PASS · SPEC_GAP · –, 94 s | `catalog/sl1-subject/paper-minimal-subject-substitution/paper-minimal/` |
| 15 | `E01-subject-substitution-repaired-e` | repaired-e | REJECT · REPAIR_SUPPORTED · WRONG_SUBJECT | REPAIR_SUPPORTED · WRONG_SUBJECT | PASS · REPAIR_SUPPORTED · WRONG_SUBJECT, 103 s | `catalog/sl1-subject/repaired-e-subject-substitution/repaired-e/` |

#### E01 relay stress, SL2 (7 rows): slice `sl2-relay`

- Gate rows: `catalog/sl2-relay/<case>/<profile>/`, primary proof `relay-stress/result.json`.
- Historical run: `evaluation/evidence/e2/sl2-relay-live-20261010/` (S3-0009 plan b3a02098..; ACKs A1-0066, S2-0009; 544.93 s, exit 0; result S3-0010); reviews A1-0067, S2-0010. Also: first run `evaluation/evidence/e2/sl2-relay-failed-20261010/` (S3-0007 plan d67f1786..; S3-0008; exit 2, 75 s, runner defect, 0/7 rows), kept.

| # | Case ID | Profile | Frozen expectation (outcome · class · error) | Historical run (class · error) | GATE (status · class · error) | Gate path |
|---|---|---|---|---|---|---|
| 16 | `E01-forged-tuple-paper-strict` | paper-strict | ACCEPT · SPEC_GAP · – | SPEC_GAP · – | PASS · SPEC_GAP · –, 87 s | `catalog/sl2-relay/paper-strict-forged-tuple/paper-strict/` |
| 17 | `E01-forged-tuple-paper-minimal` | paper-minimal | ACCEPT · SPEC_GAP · – | SPEC_GAP · – | PASS · SPEC_GAP · –, 85 s | `catalog/sl2-relay/paper-minimal-forged-tuple/paper-minimal/` |
| 18 | `E01-forged-tuple-repaired-e` | repaired-e | REJECT · REPAIR_SUPPORTED · BAD_SIGNATURE | REPAIR_SUPPORTED · BAD_SIGNATURE | PASS · REPAIR_SUPPORTED · BAD_SIGNATURE, 99 s | `catalog/sl2-relay/repaired-e-forged-tuple/repaired-e/` |
| 19 | `E01-new-reference-replay-paper-strict` | paper-strict | ACCEPT · SPEC_GAP · – | SPEC_GAP · – | PASS · SPEC_GAP · –, 90 s | `catalog/sl2-relay/paper-strict-new-reference-replay/paper-strict/` |
| 20 | `E01-new-reference-replay-paper-minimal` | paper-minimal | ACCEPT · SPEC_GAP · – | SPEC_GAP · – | PASS · SPEC_GAP · –, 91 s | `catalog/sl2-relay/paper-minimal-new-reference-replay/paper-minimal/` |
| 21 | `E01-new-reference-replay-repaired-e` | repaired-e | NO_NEW_GRANT · REPAIR_SUPPORTED · REPLAY | REPAIR_SUPPORTED · REPLAY | PASS · REPAIR_SUPPORTED · REPLAY, 100 s | `catalog/sl2-relay/repaired-e-new-reference-replay/repaired-e/` |
| 22 | `E01-same-nonce-distinct-digests-repaired-e` (guard) | repaired-e | NO_NEW_GRANT · REPAIR_SUPPORTED · REPLAY | REPAIR_SUPPORTED · REPLAY | PASS · REPAIR_SUPPORTED · REPLAY, 99 s | `catalog/sl2-relay/repaired-e-same-nonce-distinct-digests/repaired-e/` |

#### E03 dropped and fabricated outcome, SL3 (6 rows): slice `sl3-audit`

- Gate rows: `catalog/sl3-audit/<case>/<profile>/`, primary proof `audit-stress/result.json`.
- Historical run: `evaluation/evidence/e2/sl3-audit-live-20261010/` (S3-0011 plan d768463d..; ACKs A1-0068, S2-0011; 459.88 s, exit 0; result S3-0012); reviews A1-0069, S2-0012.

| # | Case ID | Profile | Frozen expectation (outcome · class · error) | Historical run (class · error) | GATE (status · class · error) | Gate path |
|---|---|---|---|---|---|---|
| 23 | `E03-dropped-outcome-paper-strict` | paper-strict | PENDING · SUPPORTED · – | SUPPORTED · – (PENDING) | PASS · SUPPORTED · – (PENDING), 91 s | `catalog/sl3-audit/paper-strict-dropped-outcome/paper-strict/` |
| 24 | `E03-dropped-outcome-paper-minimal` | paper-minimal | PENDING · SUPPORTED · – | SUPPORTED · – (PENDING) | PASS · SUPPORTED · – (PENDING), 88 s | `catalog/sl3-audit/paper-minimal-dropped-outcome/paper-minimal/` |
| 25 | `E03-dropped-outcome-repaired-e` | repaired-e | PENDING · REPAIR_SUPPORTED · – | REPAIR_SUPPORTED · – (PENDING) | PASS · REPAIR_SUPPORTED · – (PENDING), 82 s | `catalog/sl3-audit/repaired-e-dropped-outcome/repaired-e/` |
| 26 | `E03-fabricated-outcome-paper-strict` | paper-strict | CONDITIONAL · SPEC_GAP · – | SPEC_GAP · – | PASS · SPEC_GAP · –, 77 s | `catalog/sl3-audit/paper-strict-fabricated-outcome/paper-strict/` |
| 27 | `E03-fabricated-outcome-paper-minimal` | paper-minimal | CONDITIONAL · SPEC_GAP · – | SPEC_GAP · – | PASS · SPEC_GAP · –, 76 s | `catalog/sl3-audit/paper-minimal-fabricated-outcome/paper-minimal/` |
| 28 | `E03-fabricated-outcome-repaired-e` | repaired-e | REJECT · REPAIR_SUPPORTED · WRONG_PROFILE | REPAIR_SUPPORTED · WRONG_PROFILE | PASS · REPAIR_SUPPORTED · WRONG_PROFILE, 80 s | `catalog/sl3-audit/repaired-e-fabricated-outcome/repaired-e/` |

#### E03 receipt controls, SL4 (7 rows): slice `sl4-receipt`

- Gate rows: `catalog/sl4-receipt/<case>/<profile>/`, primary proof `receipt-stress/result.json`.
- Historical run: `evaluation/evidence/e2/sl4-receipt-live-20261010/` (S3-0013 plan 851896f3..; ACKs A1-0070, S2-0013; 601.60 s, exit 0; result S3-0014); reviews A1-0071, S2-0014.

| # | Case ID | Profile | Frozen expectation (outcome · class · error) | Historical run (class · error) | GATE (status · class · error) | Gate path |
|---|---|---|---|---|---|---|
| 29 | `E03-receipt-binding-control-requestDigest-repaired-e` (guard) | repaired-e | NO_NEW_OUTCOME · REPAIR_SUPPORTED · WRONG_SUBJECT | REPAIR_SUPPORTED · WRONG_SUBJECT (NO_NEW_OUTCOME) | PASS · REPAIR_SUPPORTED · WRONG_SUBJECT (NO_NEW_OUTCOME), 86 s | `catalog/sl4-receipt/repaired-e-receipt-binding-control-requestDigest/repaired-e/` |
| 30 | `E03-receipt-binding-control-gid-repaired-e` (guard) | repaired-e | NO_NEW_OUTCOME · REPAIR_SUPPORTED · WRONG_SUBJECT | REPAIR_SUPPORTED · WRONG_SUBJECT (NO_NEW_OUTCOME) | PASS · REPAIR_SUPPORTED · WRONG_SUBJECT (NO_NEW_OUTCOME), 81 s | `catalog/sl4-receipt/repaired-e-receipt-binding-control-gid/repaired-e/` |
| 31 | `E03-receipt-binding-control-dataId-repaired-e` (guard) | repaired-e | NO_NEW_OUTCOME · REPAIR_SUPPORTED · WRONG_SUBJECT | REPAIR_SUPPORTED · WRONG_SUBJECT (NO_NEW_OUTCOME) | PASS · REPAIR_SUPPORTED · WRONG_SUBJECT (NO_NEW_OUTCOME), 83 s | `catalog/sl4-receipt/repaired-e-receipt-binding-control-dataId/repaired-e/` |
| 32 | `E03-receipt-signature-control-requestDigest-repaired-e` | repaired-e | NO_NEW_OUTCOME · SUPPORTED · WRONG_SUBJECT | SUPPORTED · WRONG_SUBJECT (NO_NEW_OUTCOME) | PASS · SUPPORTED · WRONG_SUBJECT (NO_NEW_OUTCOME), 83 s | `catalog/sl4-receipt/repaired-e-receipt-signature-control-requestDigest/repaired-e/` |
| 33 | `E03-receipt-signature-control-gid-repaired-e` | repaired-e | NO_NEW_OUTCOME · SUPPORTED · WRONG_SUBJECT | SUPPORTED · WRONG_SUBJECT (NO_NEW_OUTCOME) | PASS · SUPPORTED · WRONG_SUBJECT (NO_NEW_OUTCOME), 83 s | `catalog/sl4-receipt/repaired-e-receipt-signature-control-gid/repaired-e/` |
| 34 | `E03-receipt-signature-control-dataId-repaired-e` | repaired-e | NO_NEW_OUTCOME · SUPPORTED · WRONG_SUBJECT | SUPPORTED · WRONG_SUBJECT (NO_NEW_OUTCOME) | PASS · SUPPORTED · WRONG_SUBJECT (NO_NEW_OUTCOME), 83 s | `catalog/sl4-receipt/repaired-e-receipt-signature-control-dataId/repaired-e/` |
| 35 | `E03-receipt-binding-positive-repaired-e` | repaired-e | ACCEPT · SUPPORTED · – | SUPPORTED · – (ACCEPT) | PASS · SUPPORTED · – (ACCEPT), 77 s | `catalog/sl4-receipt/repaired-e-receipt-binding-positive/repaired-e/` |

#### E02 wrong issuer and signed-list rollback, SL5 (6 rows): slice `sl5-trust`

- Gate rows: `catalog/sl5-trust/<case>/<profile>/`, primary proof `trust-stress/result.json`.
- Historical run: `evaluation/evidence/e2/sl5-trust-live-20261010/` (S3-0015 plan 9e14a148..; ACKs A1-0072, S2-0015; 531.40 s, exit 0; result S3-0016); reviews A1-0073, S2-0016.

| # | Case ID | Profile | Frozen expectation (outcome · class · error) | Historical run (class · error) | GATE (status · class · error) | Gate path |
|---|---|---|---|---|---|---|
| 36 | `E02-wrong-issuer-paper-strict` | paper-strict | REJECT · SUPPORTED · UNAUTHORIZED_CALLER | SUPPORTED · UNAUTHORIZED_CALLER (REJECT) | PASS · SUPPORTED · UNAUTHORIZED_CALLER (REJECT), 74 s | `catalog/sl5-trust/paper-strict-wrong-issuer/paper-strict/` |
| 37 | `E02-wrong-issuer-paper-minimal` | paper-minimal | REJECT · SUPPORTED · UNAUTHORIZED_CALLER | SUPPORTED · UNAUTHORIZED_CALLER (REJECT) | PASS · SUPPORTED · UNAUTHORIZED_CALLER (REJECT), 71 s | `catalog/sl5-trust/paper-minimal-wrong-issuer/paper-minimal/` |
| 38 | `E02-wrong-issuer-repaired-e` | repaired-e | REJECT · SUPPORTED · UNAUTHORIZED_CALLER | SUPPORTED · UNAUTHORIZED_CALLER (REJECT) | PASS · SUPPORTED · UNAUTHORIZED_CALLER (REJECT), 76 s | `catalog/sl5-trust/repaired-e-wrong-issuer/repaired-e/` |
| 39 | `E02-signed-list-rollback-paper-strict` | paper-strict | ACCEPT · SPEC_GAP · – | SPEC_GAP · – (ACCEPT) | PASS · SPEC_GAP · – (ACCEPT), 75 s | `catalog/sl5-trust/paper-strict-signed-list-rollback/paper-strict/` |
| 40 | `E02-signed-list-rollback-paper-minimal` | paper-minimal | ACCEPT · SPEC_GAP · – | SPEC_GAP · – (ACCEPT) | PASS · SPEC_GAP · – (ACCEPT), 72 s | `catalog/sl5-trust/paper-minimal-signed-list-rollback/paper-minimal/` |
| 41 | `E02-signed-list-rollback-repaired-e` (guard) | repaired-e | REJECT · REPAIR_SUPPORTED · STALE_ANCHOR | REPAIR_SUPPORTED · STALE_ANCHOR (REJECT) | PASS · REPAIR_SUPPORTED · STALE_ANCHOR (REJECT), 84 s | `catalog/sl5-trust/repaired-e-signed-list-rollback/repaired-e/` |

#### E02 revocation barrier and expired duty, SL6 (9 rows): slice `sl6-barrier`

- Gate rows: `catalog/sl6-barrier/<case>/<profile>/`, primary proof `barrier-stress/result.json`.
- Historical run: `evaluation/evidence/e2/sl6-barrier-live-20261011/` (S3-0017 plan 78d6ebfb..; ACKs A1-0074, S2-0017; 736.64 s, exit 0; result S3-0018); reviews A1-0075, S2-0018.

| # | Case ID | Profile | Frozen expectation (outcome · class · error) | Historical run (class · error) | GATE (status · class · error) | Gate path |
|---|---|---|---|---|---|---|
| 42 | `E02-pre-barrier-revocation-paper-strict` | paper-strict | ACCEPT · SPEC_GAP · – | SPEC_GAP · – (ACCEPT) | PASS · SPEC_GAP · – (ACCEPT), 88 s | `catalog/sl6-barrier/paper-strict-pre-barrier-revocation/paper-strict/` |
| 43 | `E02-pre-barrier-revocation-paper-minimal` | paper-minimal | ACCEPT · SPEC_GAP · – | SPEC_GAP · – (ACCEPT) | PASS · SPEC_GAP · – (ACCEPT), 89 s | `catalog/sl6-barrier/paper-minimal-pre-barrier-revocation/paper-minimal/` |
| 44 | `E02-pre-barrier-revocation-repaired-e` | repaired-e | ACCEPT · REPAIR_SUPPORTED · – | REPAIR_SUPPORTED · – (ACCEPT) | PASS · REPAIR_SUPPORTED · – (ACCEPT), 99 s | `catalog/sl6-barrier/repaired-e-pre-barrier-revocation/repaired-e/` |
| 45 | `E02-post-barrier-revocation-paper-strict` | paper-strict | CONDITIONAL · SPEC_GAP · – | SPEC_GAP · – (ACCEPT) | PASS · SPEC_GAP · – (ACCEPT), 89 s | `catalog/sl6-barrier/paper-strict-post-barrier-revocation/paper-strict/` |
| 46 | `E02-post-barrier-revocation-paper-minimal` | paper-minimal | CONDITIONAL · SPEC_GAP · – | SPEC_GAP · – (ACCEPT) | PASS · SPEC_GAP · – (ACCEPT), 91 s | `catalog/sl6-barrier/paper-minimal-post-barrier-revocation/paper-minimal/` |
| 47 | `E02-post-barrier-revocation-repaired-e` (guard) | repaired-e | REJECT · REPAIR_SUPPORTED · STALE_STATE | REPAIR_SUPPORTED · STALE_STATE (REJECT) | PASS · REPAIR_SUPPORTED · STALE_STATE (REJECT), 101 s | `catalog/sl6-barrier/repaired-e-post-barrier-revocation/repaired-e/` |
| 48 | `E02-expired-duty-paper-strict` | paper-strict | CONDITIONAL · SPEC_GAP · – | SPEC_GAP · – (ACCEPT) | PASS · SPEC_GAP · – (ACCEPT), 95 s | `catalog/sl6-barrier/paper-strict-expired-duty/paper-strict/` |
| 49 | `E02-expired-duty-paper-minimal` | paper-minimal | CONDITIONAL · SPEC_GAP · – | SPEC_GAP · – (ACCEPT) | PASS · SPEC_GAP · – (ACCEPT), 87 s | `catalog/sl6-barrier/paper-minimal-expired-duty/paper-minimal/` |
| 50 | `E02-expired-duty-repaired-e` (guard) | repaired-e | REJECT · REPAIR_SUPPORTED · EXPIRED | REPAIR_SUPPORTED · EXPIRED (REJECT) | PASS · REPAIR_SUPPORTED · EXPIRED (REJECT), 96 s | `catalog/sl6-barrier/repaired-e-expired-duty/repaired-e/` |

#### E01 wrong destination and expiry boundary, SL7 (6 rows): slice `sl7-destination`

- Gate rows: `catalog/sl7-destination/<case>/<profile>/`, primary proof `destination-stress/result.json`.
- Historical run: `evaluation/evidence/e2/sl7-destination-live-20261011/` (S3-0019 plan d4fa294e..; ACKs A1-0076, S2-0019; 602.24 s, exit 0; result S3-0020); reviews A1-0077, S2-0020.

| # | Case ID | Profile | Frozen expectation (outcome · class · error) | Historical run (class · error) | GATE (status · class · error) | Gate path |
|---|---|---|---|---|---|---|
| 51 | `E01-wrong-destination-paper-strict` | paper-strict | CONDITIONAL · SPEC_GAP · – | SPEC_GAP · – (ACCEPT) | PASS · SPEC_GAP · – (ACCEPT), 114 s | `catalog/sl7-destination/paper-strict-wrong-destination/paper-strict/` |
| 52 | `E01-wrong-destination-paper-minimal` | paper-minimal | CONDITIONAL · SPEC_GAP · – | SPEC_GAP · – (ACCEPT) | PASS · SPEC_GAP · – (ACCEPT), 112 s | `catalog/sl7-destination/paper-minimal-wrong-destination/paper-minimal/` |
| 53 | `E01-wrong-destination-repaired-e` (guard) | repaired-e | REJECT · REPAIR_SUPPORTED · WRONG_DESTINATION | REPAIR_SUPPORTED · WRONG_DESTINATION (REJECT), step 1 | PASS · REPAIR_SUPPORTED · WRONG_DESTINATION (REJECT), step 1, 121 s | `catalog/sl7-destination/repaired-e-wrong-destination/repaired-e/` |
| 54 | `E01-expiry-boundary-paper-strict` | paper-strict | CONDITIONAL · SPEC_GAP · – | SPEC_GAP · – (ACCEPT) | PASS · SPEC_GAP · – (ACCEPT), 83 s | `catalog/sl7-destination/paper-strict-expiry-boundary/paper-strict/` |
| 55 | `E01-expiry-boundary-paper-minimal` | paper-minimal | CONDITIONAL · SPEC_GAP · – | SPEC_GAP · – (ACCEPT) | PASS · SPEC_GAP · – (ACCEPT), 86 s | `catalog/sl7-destination/paper-minimal-expiry-boundary/paper-minimal/` |
| 56 | `E01-expiry-boundary-repaired-e` | repaired-e | REJECT · REPAIR_SUPPORTED · EXPIRED | REPAIR_SUPPORTED · EXPIRED (REJECT), step 9 | PASS · REPAIR_SUPPORTED · EXPIRED (REJECT), step 9, 97 s | `catalog/sl7-destination/repaired-e-expiry-boundary/repaired-e/` |

### 6.1 Protocol facts per slice (historical runs) [S2 "Protocol facts per slice"]

All 44 SL1-SL7 rows used the **production** `hmbc_protocol.adapter` for D1 and every stress deployment:
exit 0, empty stderr (e3b0c442..), no exchange failures, distinct state directories. No row used a
TEST-ONLY tool except SL4's three binding rows.

| Slice (rows) | Stress-adapter operations | `collect_decision`: paper rows | `collect_decision`: repaired-e rows |
|---|---|---|---|
| SL1 subject (3) | paper: `encrypt_record`, `prepare_request`, `release`, `finish_decryption` ×2; repaired: `encrypt_record`, `prepare_request`, `collect_checkpoint`, `collect_decision` | 0, 0 | 1 |
| SL2 relay (7) | forged tuple paper: **none**; new reference paper: `prepare_request`; repaired forged and new reference: request, checkpoint, decision; same nonce: `prepare_request` ×2, one `collect_checkpoint`, `collect_decision` ×2 | 0 ×4 | forged 1; new reference 1; same nonce **2, one per distinct request digest** |
| SL3 audit (6) | dropped: `encrypt_record` first, then request (+ checkpoint, decision in repaired), one `release`; fabricated: `prepare_request` (+ `attest_grant` → NOT_COMMITTED in repaired) | 0 ×4 | dropped 1; fabricated 0 |
| SL4 receipts (7, all repaired-e) | `prepare_request`, `collect_checkpoint`, `collect_decision`, `attest_grant` | – | 1 ×7 |
| SL5 trust (6) | rollback: `prepare_request` only; wrong issuer: **none** | 0 ×4 | 0 ×2 |
| SL6 barrier (9) | paper: `prepare_request`; repaired pre-barrier and expired duty: request, checkpoint, decision; repaired post-barrier: request, checkpoint, decision, **second checkpoint** | 0 ×6 | 1 ×3 |
| SL7 destination (6) | wrong destination: B serves `prepare_request` (+ checkpoint, decision in repaired), A serves none; expiry boundary: A serves `prepare_request` (+ checkpoint, decision in repaired) | 0 ×4 | 1 ×2 (B's; A's) |

**Totals:** 24 paper rows with 0 decisions; 20 repaired-e rows with 18 decisions (16 rows with one decision
for one request; SL2 same nonce with two decisions for two distinct requests; SL3 fabricated and both SL5
repaired rows with none). No request digest was decided twice. No stress adapter served `rotate_epoch`, and none served `release` outside SL1's paper rows and
SL3's dropped rows.

**Worker observations (D49) and never-publish scans** [S2, verbatim]:

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

The gate run re-ran these recipes. Its runner recorded **180** verified never-instantiated worker probes (the
same count as SL2-SL7), 689 owner command records (the 180 probes, which exit 1 by design, and 509 with exit 0)
and 51823 RPC calls, all exit 0 (`evaluation/evidence/e3/gate-run-20261012/live-result-audit.json`). The gate publication was scanned in
full for 18 TEST-ONLY label keys (a superset of agent 1's 13), the 3 frozen-vector keys (all equal to label
keys) and the 61 release tokens of the run: 0 hits (`evaluation/evidence/e3/gate-run-20261012/never-publish-scan.json`).

Agent 2 (proxy)'s post-run re-check **S2-0022** (the check promised in S2-0021; script and output in
`protocol/evidence/reviews/s2-0022-gate-run/`, `problems: []`) found **no discrepancy in protocol scope** on the
published copy:

- its seven slice review scripts pass unchanged on the gate rows;
- D1 and every stress adapter is the production adapter, except D1 in the 6 recovery rows, which is the crash
  hook (exit 86, then a production restart with one release per row);
- A31: **18** stress decisions, equal per slice to the slice reviews above, plus 48 D1 decisions; no request
  digest was decided twice;
- D49: **180** verified never-instantiated probes, equal per slice;
- all 152 prepared requests appear verbatim in exactly one relay `requestAccess` on their own PBC;
- its own never-publish scan (TEST-ONLY keys of 19 labels, a superset of the 18 above, and token-digest
  preimages over 18609 distinct 32-byte hex strings) found 0 hits. S2-0022 did not repeat the raw-token
  substring scan.

## 7. E01: decision provenance and replay

**Where enforced** [A1-L2]:

| Property | Paper profiles (ledger behaviour) | Repaired-e guard (source) |
|---|---|---|
| subject binding | `policyEnf` checks only gid != 0 and evaluates the **relay-supplied** records (`ACSC.sol:140-167`); grantId = H(pbcRequestId, KSSC, dbcChainId) (`ProtocolTypes.sol:447`), independent of gid | DV step 4: WRONG_SUBJECT |
| forged tuple | `policyEnf` needs no PBC request; caller = configured relay | DV step 6: BAD_SIGNATURE |
| identical replay | grant uniqueness `KSSC.sol:180`: REPLAY | same guard, checked before the nonce |
| new reference | a fresh pbcRequestId means a new grantId and a **second grant** | same request/certificate means the same grantId: REPLAY (`KSSC.sol:180`) |
| same nonce, distinct digests | not applicable | nonce guard `KSSC.sol:181-183`: REPLAY. The **only** row reaching it |
| expiry | paper grant TTL = policyEnf block + 30 s (`ACSC.sol:154`); no request expiry check. SL7: a grant mined at DBC time == request expiry, expiring 30 s later | grant expiry = min(decision.expiresAt, request.expiresAt) (`ACSC.sol:190`); DV step 9 (line 74, `>=`) rejects at equality. SL7: consume == request expiry == decision expiry → EXPIRED |
| wrong destination | the tuple has no destination (or source) field. SL7: A grants on B's tuple although A's PBC never saw the request | DV steps 1-2 (lines 60, 61-64). The catalog's second-deployment recipe fails at **step 1** (A1-0039). SL7 confirmed this on calldata, and the certificate was signed under B's domain |

### 7.1 Identical accepted-request replay (rows 10-12)

**As measured in the historical run** (`grouped-replay-live-20261009/`, agent 3 host): in each profile one
allowed grant existed; the relay resubmitted the **identical** accepted ACSC calldata (`policyEnf` in paper
profiles, `consumeDecision` in repaired-e) with a fresh transaction nonce; it was mined with status 0, decoded
Rejected(8), with no logs; the request, grant, nonce, access count, idle worker and both chains' histories
were unchanged; Alice's release, completion and one outcome, Bob's denial and wrong-admin 16 passed in all
three profiles. Probe wall times 7.07 s, 7.00 s, 7.00 s.

**Gate run** (row 12): replay block 1791769487, Rejected(8), 25 s before `r.expiresAt` 1791769512; the
legitimate release came 23 s before it (§3.4). The repaired release did not expire as in the first historical
trial below.

**Limits:** grant-id uniqueness (`KSSC.sol:180`, A25) fires **before** the nonce check, so this row does not
test `(gid, nonce)` consumption; only the same-nonce supplement does. Equal idle-worker snapshots are not
retry or idempotence evidence. Paper "SUPPORTED" rests on the A25 completion (deterministic grantId).

**Kept failed trial:** the first attempt (`nonce-replay-live-20261009/`, plan a7732650.., 341.181 s, exit 2,
A3-0042; ledger review A1-0055) completed the paper rows; in repaired-e the replay subcheck passed but the
first release then returned EXPIRED (probe 10.21 s, thin TTL margin). A runner-timing failure, not a protocol
finding; no TTL extension.

### 7.2 Subject substitution (rows 13-15; SL1)

[S2 §5] **Paper-strict and paper-minimal: SPEC_GAP (CONDITIONAL).** On a fresh D2 with its own adapter
process and 0700 state:

- the relay changed only the gid of Alice's forwarded tuple to registered Bob, and the DBC granted it (gid
  Bob, native recipient 0, TTL +30 s);
- one production release on that grant was bound to **Bob's** registered key (D35/A38): exactly one worker
  intent, one send attempt and one cache entry (delivery unknown);
- that same response completed for `keyref:user:bob` (decryptable) and was refused WRONG_SUBJECT for
  `keyref:user:alice`; completion changed nothing in the worker, and no outcome was reported;
- DBC clock at release: 29 s and 28 s before grant expiry.

**Repaired-e: REPAIR_SUPPORTED.** The substituted request with Alice's unchanged certificate was mined with
status 0 and Rejected(2) WRONG_SUBJECT. There was no release, and the D2 worker stayed idle.

**Ledger facts** (A1-0062, A1-0063): the logged grantId equals keccak256(abi.encode(pbcRequestId, KSSC,
28545)), independent of gid; Alice's PSC request stays FORWARDED and both subjects' nonces are unchanged. In
repaired-e only `gid` differs from the signed request, and the certificate's `requestDigest` equals the
original digest, so DV step 4 fails. Review limit: agent 1 re-derived values from raw calldata and block
timestamps but did not re-decode raw log topics (A1-0063).

**Interpretation:** a configured-relay stress outside A01. The paper tuple carries no subject binding, so the
symbolic response follows the relay-asserted subject. This is **not an HMBC exploit**, and not real
encryption. Owner test [U]: `protocol/tests/test_paper_release.py` (T1; S2-0006).

### 7.3 Forged tuple (rows 16-18; SL2)

- **Paper:** the relay's `policyEnf` alone, with a fixed synthetic pbcRequestId never sent to the PBC; the D2
  adapter served 0 exchanges. The grant has recipient 0, TTL `block.timestamp + 30`, and grantId =
  H(fabricated reference, KSSC, 28545) (A1-0065, A1-0067).
- **Repaired-e:** the honest decision from `collect_decision` was used **only** in an `eth_call`, never mined.
  The mined copy kept the decision bytes and replaced only the signature with a TEST-ONLY **relay** signature;
  no witness key was used by the runner. Decision digest 0x698b3a6e.. (domain `HMBCDecision` v1 on D2's KSSC)
  equals the runner's honest and forged digests; the honest signature recovers to the witness, the forged one
  to the relay. So BAD_SIGNATURE comes from the signer, not from a wrong digest [S2 §5; A1-0067].
- **Disclosed recipe difference** (A1-0065): the repaired-e row used a **real** forwarded Alice request, so a
  PBC request exists for it, unlike the frozen "without a PBC request/log" wording. The ledger outcome cannot
  depend on it: no DV step reads the PBC. The paper rows do use a reference the PBC never saw.

### 7.4 New-reference replay and same nonce (rows 19-22; SL2)

- **New reference, paper:** only `prepare_request` on D2; the replay differs **only** in pbcRequestId, which
  the PBC never saw, and yields a second distinct grant (TTL +30, recipient 0); the original grant is
  unchanged. Both paper rows report the same second grantId 0x1bf1f8ad..: a fixture-determinism artifact
  (fixed synthetic relay reference and identical D2 KSSC address on each fresh Anvil), not cross-row state
  (A1-0067 note 1; S2-0010).
- **New reference, repaired-e:** the identical granted calldata re-consumed gives REPLAY from `KSSC.sol:180`.
- **Same nonce, distinct digests (repaired-e only; guard row):** two `prepare_request` calls with nonce 1 and
  expiries e and e − 1 gave distinct digests (the adapter keeps no nonce state); **one** checkpoint after the
  second forward; **both** decisions before any consume (each saw `nonceConsumed == false`). The second,
  pre-collected certificate met the ledger nonce guard (`KSSC.sol:181-183`), not EXPIRED: second consume at
  1791595477, earliest expiry 1791595501 (24 s margin) [S2 §5; A1-0067].

### 7.5 Wrong destination (rows 51-53; SL7)

- **Setup** [S2 §5]: B is a third deployment on the same chain pair, contracts disjoint from A and D1, with
  its own production adapter, 0700 state, `--deployment` and D49 probe. B's request is bound to B's PSC, KSSC
  and chain ids; A's PBC has no `requestAccess`. B's checkpoint and decision recover to the witness under
  **B's** KSSC domain and not under A's. B and A derive the same label keys (P16), so the only defect at A is
  the destination.
- **Paper:** A grants on B's forwarded tuple and records (pbcRequestId = B's digest, A's PBC `getRequest`
  status 0). The grant references a request that does not exist on A's PBC: a chosen completion under
  compromised-relay stress, outside A01, so a SPEC_GAP, **not an HMBC exploit** (A1-0076 point 2).
- **Repaired-e:** Rejected(3) WRONG_DESTINATION at **DV step 1 (line 60, source PSC binding)**; step 2 also
  mismatches but is never reached (A1-0076 point 1; A1-0077).
- **Required wording (A1-0039):** the catalog recipe is rejected at step 1 (source PSC binding), not at the
  destination check. **This row cannot kill the destination-binding mutant (1).**

### 7.6 Expiry boundary (rows 54-56; SL7)

- **Paper:** the consume block timestamp equals the request expiry exactly (1791726931, 1791727014); the grant
  expires 30 s later. Paper `policyEnf` never sees the request expiry (A1-0076 point 4; A1-0077 note 4).
- **Repaired-e:** decision `expiresAt` = `request.expiresAt` = consume timestamp 1791727102; the request term
  bound (margin ≥ 1 s from the checkpoint lower bound). Rejected(7) EXPIRED at DV step 9 (line 74).
- **Gate run:** paper consume = `r.expiresAt` (1791773263, 1791773349), granted with expiry + 30 s; repaired
  consume = `r.expiresAt` = `d.expiresAt` = 1791773444, Rejected(7) at step 9; the request expiry bound the
  decision by at least 1 s (§3.4).
- **Equality at expiry rejects.** "Exactly at expiry" is a property of `>=`, consistent with every other
  ledger validity check (`TMSC.sol:298,325`; `DecisionVerifier.sol:93`). It is **not** a test of
  `expiresAt − 1`: that supplementary `eth_call` was skipped, so acceptance one second earlier is not shown in
  SL7. Other rows show acceptance well before expiry (A1-0076 point 3).
- **Clock:** the runner pinned only the DBC (`evm_setNextBlockTimestamp`, no `evm_mine`), with no adapter call
  between the pin and the consume (static reading of `destination_stress.py:133-139`); the consume block
  timestamp equals the pinned value. That no DBC block was mined in between is shown only indirectly
  [S2 "does not show"].

## 8. E02: trust-anchor freshness

**Where enforced** [A1-L2]:

| Property | Paper profiles (ledger behaviour) | Repaired-e guard (source) |
|---|---|---|
| rollback | latest appended list wins; an old signed list is re-accepted | strictly increasing version: STALE_ANCHOR (`TMSC.sol:190`) |
| wrong issuer | `UNAUTHORIZED_CALLER` (16) (`TMSC.sol:181`): **baseline caller restriction in every profile, not a repair** (D-record N-1) | same |
| revocation barrier | no barrier; a forwarded tuple stays grantable after revocation (pre- and post-barrier paper rows are the same execution) | a newer accepted checkpoint invalidates older decisions: DV line 87, **sequence** cause (`d.stateSequence != cp.sequence`). SL6 showed this, with the expiry clause on the same line not applying. Before that checkpoint, acceptance is the intended window |
| expired duty | no record-validity check at use. SL6: grants at DBC time == record validUntil (expired under the half-open convention, zero-second margin) | DV step 13 (lines 92-94): EXPIRED. SL6 showed `duty end <= consume < min(decision, request, checkpoint expiry)`, so the rejection is not step 9 |

### 8.1 Wrong issuer (rows 36-38; SL5)

The H1 CA-admin submitted an H2 list at version 2 whose signature recovers to the H2 root, so the list itself
is valid; status 0, Rejected(16), no logs; anchors, authEpoch, revocations, credentials and logs unchanged
(A1-0073). No adapter call at all; 3 D49 probes per row [S2 §6]. **Wrong issuer is not a repaired-e property
and is not counted as repair evidence** (A1-0072 point 1). The code 16 seen in every row's controls is the
same baseline restriction; this catalog row is credited only through its own frozen steps (A1-0061).

### 8.2 Signed-list rollback (rows 39-41; SL5)

- **Paper:** after an H1 CRL v2 revoking serial 101 (Alice), the bootstrap H1 CRL v1, byte-identical to the
  mined bootstrap transaction in the same PBC records, is re-accepted. Here v2 revoked Alice, so the rollback
  **un-revokes** her: a revoked credential becomes usable again. The general paper statement is "the latest
  appended list is current, with no version ordering or list expiry" (A1-0072 point 3).
- **Repaired-e:** Rejected(5) STALE_ANCHOR. **STALE_ANCHOR is line 190, not 192:** the replayed v1 list was
  still valid at the replay block, and the only other way TMSC returns code 5 is expiry (`TMSC.sol:192`),
  which did not apply (A1-0072 point 2; A1-0073 note 1).
- **Protocol** [S2 §6]: one `prepare_request` per row; on-chain request and signature equal the adapter output
  byte for byte. authEpoch signed = TMSC.authEpoch at the request block: 5, 5, 4. The adapter signed exactly
  what it was given (P14); the repaired request was then denied at the PSC (REVOKED, code 19).
- **CRL only.** TempACL rollback has the same `_checkFreshness` path (`TMSC.sol:155`) but **was not run**
  (A1-0072 point 4).
- The actor is an authorized issuer-scoped administrator, so these are tested reconstruction results, not
  HMBC exploits (A1-0073 note 3).

### 8.3 Revocation before and after the barrier (rows 42-47; SL6)

- **The paper pre- and post-barrier rows are the same execution.** Without a checkpoint there is no barrier
  step to run; the ACCEPT vs CONDITIONAL difference comes from the catalog's labelling, not from different
  observations. They are one paper behaviour, observed twice per profile, not independent findings.
  CONDITIONAL means acceptance depends on the configured relay forwarding the request-time records; the paper
  does not say how a revocation would reach the DBC (A1-0074 point 1; A1-0075 note 4).
- **Repaired pre-barrier: ACCEPT, REPAIR_SUPPORTED, intentional.** One decision on cp1 (sequence 1, authEpoch
  3, source block 48), collected **before** the revocation in PBC block 49; no other checkpoint accepted
  before consume; consume 24 s inside the decision expiry [S2 §6; A1-0075].
- **Repaired post-barrier: STALE_STATE, line 87, sequence cause.** The old certificate was collected before
  the revocation (decision 07:37:00.5Z, revocation 07:37:02.3Z, cp2 07:37:03.2Z); cp2 = sequence 2, authEpoch
  4, source block 49, current at consumption. Agent 1's replay of the verifier on the mined inputs fails first
  at line 87 on the sequence (decision 1 ≠ checkpoint 2); the expiry clause on the same line does not apply
  (d.expiresAt 1791704248 ≤ cp2.expiresAt 1791704283; consume 1791704225 below all expiries) (A1-0075).
- **The cross-clock 2 s is not a window.** `windowSeconds` compares the DBC consume time with the PBC
  revocation time on two separate Anvil clocks; the order comes from the runner's sequential steps. It is an
  approximate cross-clock number, **not the measured revocation window** (A1-0074 point 2).

### 8.4 Expired duty (rows 48-50; SL6)

- **Paper: granted at the boundary instant, not after it.** In both paper rows the consume block time equals
  the record validUntil (1791704326, 1791704403). Under the ledger's half-open convention `[validFrom,
  validUntil)` (`TMSC.sol:325`, `DecisionVerifier.sol:93`) the record **is** expired at that instant, so the
  SPEC_GAP reading holds; but the margin is zero seconds. "validUntil in the DBC's past" (S3-0018) should be
  read as "at or past". A grant strictly after the end would take the same path, because paper `policyEnf`
  never reads validUntil (A1-0075 note 2).
- **Repaired-e: EXPIRED at DV step 13.** Decision collected at DBC 1791704470 while the duty was valid (end
  1791704490), so ALLOW was right; consume 1791704491, 7 s before the binding request expiry 1791704498. The
  oracle requires `collectedDbcNow < dutyEnd <= consume < min(decision, request, checkpoint expiry)`, so the
  rejection is step 13, not step 9 [S2 §6; A1-0075 note 1].
- **Gate run:** paper consume at DBC time = duty end (1791772640, 1791772728), granted; repaired duty end
  1791772820, consume 1791772821, 7 s before the binding request and decision expiry 1791772828, Rejected(7)
  at step 13 (§3.4).
- **ADVANCE_CLOCK models elapsed time:** an explicit DBC timestamp jump, not a real delay; the PBC clock and
  state are untouched. The paper row shows the DBC accepts a record whose validUntil is at or past DBC now; it
  does not show that the PBC would have refused (A1-0074 point 4). **INSTALL_SHORT_DUTY** is recorded setup,
  not a catalog step (A1-0074 point 5).

### 8.5 Revocation window (human decision A1-0081)

The window is not a gate criterion. Under A1-0081 ("Use existing window evidence") this report carries the
following statements exactly.

**What RQ1-E.md may claim about the window (A1-0081):**

1. **Owner integrated measurement (A1-0046, `ledger/evidence/revocation-window/`):**
   - Setup: repaired-e on two Anvil chains with interval mining, agent 2's **unmodified production adapter**
     (8b7caf5 = E1 pin 465aff5) collecting checkpoints and decisions, and the owner runner and collector.
   - Barrier delay d = 0 / 5 / 10 / 20 s gives refusal in the barrier block itself (STALE_STATE), with
     W = 2 / 6 / 11 / 21 s.
   - With no barrier, refusal comes exactly at `request.expiresAt` (EXPIRED), W = 26 s, which is the TTL left
     at T0.
   - A new request after T0 is refused at the PSC at once (REVOKED).
   - **Paper-strict:** a pre-revocation tuple is still grantable at T0 + 5, + 35 and + 65 s.
2. **The integrated C-E2 runner, SL6:** this is an ordering result, not a measured window.
   - Before the DBC accepts the revoking checkpoint, the older certificate is accepted (pre-barrier,
     REPAIR_SUPPORTED, intentional).
   - After it, the older certificate is rejected with STALE_STATE from the line 87 sequence cause
     (post-barrier).
   - The 2 s SL6 value is a cross-clock difference and is **not** a window measurement (A1-0074 point 2).
3. **What W is:** W = min(time until the DBC accepts a post-revocation checkpoint, remaining request/decision
   TTL) ≤ 30 s. It is a runner/witness cadence parameter, not a ledger constant.

**What must not be claimed (A1-0081):**

- **No window measured by the integrated C-E2 runner.** D-P3-3 was not run; record it as not run, with the
  reason (A1-0079/A1-0081).
- **No statistics.** There was one trial per delay, on one host, with 1 s granularity.

**Protocol facts behind them** [S2 window]: the owner measurement used agent 2's production adapter at
8b7caf5, whose `hmbc_protocol/**` and `abi/**` are byte-identical to pin 0716a8e; it is still an owner
measurement with the owner runner. The adapter never pushes checkpoints (P8), so W is capped by the 30 s
request TTL and the decision rule `min(request, checkpoint, DBC now + 30)` (P7).

[A1-L4] records the same: no integrated window was measured (A1-0079/A1-0081). The frozen catalog
qualification "repaired acceptance within this measured window" refers to a window the integrated runner did
not measure; the gate run did not measure one either (stage 5 dropped).

## 9. E03: audit correspondence

**Where enforced** [A1-L2]:

| Property | Paper profiles (ledger behaviour) | Repaired-e guard (source) |
|---|---|---|
| outcome | paper `reportOutcome` accepts a relay report for a forwarded request, even with no DBC grant (fabricated). The relay must supply the public derived grantId = H(digest, KSSC, dbcChainId); any other value gives WRONG_DESTINATION (`PSC.sol:227-229`). A dropped outcome leaves the request FORWARDED with outcomeLogId 0 permanently, because the PSC has no time-based transition (SL3) | `reportOutcome`: WRONG_PROFILE; `reportAttestedOutcome` needs a witness receipt bound to (requestDigest, gid, dataId) (`PSC.sol:266-269`). The binding test precedes quorum, so binding and signature rows give the same code (SL4) |
| duplicate outcome | `PSC.sol:226` (paper) / `:250` (repaired) REPLAY. It is checked right after the unknown-request check (`:225`/`:249`, WRONG_SUBJECT) and before any binding or signature check | same |

**Required wording** [S2 §7.3]:

- **Delivery is unknown in every row.** `RELEASE_SENT` is a write-ahead record of an attempted send, never
  recipient delivery; the protocol has no recipient acknowledgement (worker.py:3-6, 158).
- A DBC grant or a GrantReceipt proves **authorization** (a past allowed grant), not delivery or decryption.
- Reconciliation needs eventual delivery and an honest reporter (A12).

### 9.1 Duplicate outcome (rows 7-9)

**As measured in the historical run** (`duplicate-live-20261009/`, agent 3 host): after a successful Alice
release, completion and one outcome, the relay resubmitted the identical outcome call (`reportOutcome` in paper
profiles, `reportAttestedOutcome` with the original receipt in repaired-e) with a fresh transaction nonce; it
was mined with status 0, Rejected(8), no logs; the PBC request, DBC grant, worker cache, events and attempts,
and both histories were unchanged. **Limit:** "one outcome per request" is a reconstruction choice (A1-0042
E03-4): a tested reconstruction result, not a paper theorem.

### 9.2 Dropped and fabricated outcome (rows 23-28; SL3)

- **Dropped outcome** [S2 §7.3; A1-0069]: each row includes the catalog's RELEASE. `encrypt_record` first,
  then the request (and checkpoint + one decision in repaired-e), then exactly one `release`. Worker: idle
  before; after = [RELEASE_INTENT, RELEASE_SENT], sendAttempts 1, completedAttempts 1, delivery `unknown`.
  Release bound to Alice's registered key; native grant recipient **0** in paper (D35/A38) and the signed
  recipient in repaired-e. Releases 29 s, 28 s and 26 s inside the grant lifetime. No DBC transaction after
  the grant (the release is off chain). The PBC request stayed FORWARDED (status 1, `outcomeLogId` 0).
- **PENDING is a ledger-permanent state.** The PSC has no time-based status transition (expiry is checked only
  in `requestAccess`, `PSC.sol:197`; late reconciliation is allowed, `PSC.sol:239`). "Reconciliation requires
  eventual delivery and an honest reporter" is a liveness assumption; the ledger enforces no deadline
  (A1-0068 point 2). Local durable logs do not imply PBC reconciliation.
- **The paper fabricated outcome is "outcome without a grant", not "arbitrary outcome".** The relay must supply
  the public, deterministic grantId = H(digest, KSSC, dbcChainId); with any other value the report reverts
  WRONG_DESTINATION (`PSC.sol:227-229`); `outcomeDigest` is opaque to the ledger. So the gap is that the PBC
  records a correctly *shaped* outcome for which no DBC grant exists (A1-0068 point 1). Observed: LSC OUTCOME
  log 7 with complete details, status 2, while the DBC had no grant at all (A1-0069).
- **Repaired fabricated outcome:** Rejected(21) WRONG_PROFILE, the first check at `PSC.sol:222`; besides that,
  the honest witness refused to attest the absent grant: `{ok: false, error.code: "NOT_COMMITTED"}`, no
  receipt and **no signature** (witness.py:153-154 raises before `_sign`) [S2 §7.3].
- **E0-era catalog text:** the dropped rows' frozen qualification still says "Current production owner still
  refuses paper grants". That sentence predates the paper release path used live by the E1 control and the
  duplicate rows and is **superseded** (A1-0068 point 3). The frozen catalog is not edited.
- Agent 1's owner rehearsal omitted RELEASE for the dropped rows (A1-0060 R2 correction), so it is not
  evidence for them.

### 9.3 Receipt controls (rows 29-35; SL4)

- **Honest receipts (7)** come from the production `attest_grant`, after FORWARD_OR_CONSUME and before any
  report. Each recovers to the witness under `HMBCReceipt` v1 on the PBC PSC (messages.py:52-53) [S2 §7.3].
- **Binding rows (3; guard rows) are a deliberate mutation.** The inconsistent receipt comes from
  `testtools.deviating_witness` (sha256 0511ba57.., re-hashed before every call): a **deliberate witness
  deviation (A40)**, outside the honest-witness assumption. They are defence-in-depth controls, **never an
  HMBC result** and never honest-witness behaviour (A1-0070 point 4; S2-0007; D-6 accepted in A1-0064). One
  call per binding row, exit 0, argv equal to the plan template; each artifact passed the three-way check
  (only the named field differs, the altered value equals the tool's `_altered`, the signature recovers to the
  witness, `testOnly` true).
- **Binding and signature rows give the same native result** (Rejected(2) WRONG_SUBJECT, before quorum). What
  separates them is signature evidence only: in binding rows the submitted signature recovers to the witness
  over the **altered** receipt; in signature rows it recovers to the witness only over the **honest** receipt
  (A1-0070 point 1; A1-0071). The signature controls therefore cannot kill the binding mutant [S2 §7.3].
- **Positive control:** the honest receipt submitted unchanged is recorded (status 1, LSC OUTCOME log 7,
  status 2): the repaired path is not deny-all.
- **`dbcBlockNumber`/`dbcBlockHash` are witness-attested only;** the PBC cannot check them. A receipt is
  evidence of DBC **authorization**, not of release or delivery (A1-0070 point 2).
- **No report deadline at the PBC** (late reconciliation, `PSC.sol:239`); `reportAfterGrantExpiry` is recorded,
  not required (A1-0070 point 3).
- **Not done:** the D-6 plan also allowed the tool against the no-receipt-binding mutant deployment. The live
  mutant matrix was not run (A1-0080), so the tool has never run against a `mutant-*` deployment in an
  integrated run; its mutant behaviour is owner evidence only [S2 §7.3]. R11 (non-strict JSON parsing in the
  tool) stays an unfixed hardening item.

### 9.4 Crash and recovery (rows 1-6): frozen BLOCKED / decided SPEC_GAP, UNPROVED (D47)

[S2 §7.2, replacement text]

| Row | paper-strict | paper-minimal | repaired-e |
|---|---|---|---|
| crash after durable intent | **frozen BLOCKED / decided SPEC_GAP, UNPROVED** (D47); mechanics PASS [I] | **frozen BLOCKED / decided SPEC_GAP, UNPROVED** (D47); mechanics PASS [I] | **REPAIR_SUPPORTED [I]**, bounded logical mechanics only |
| crash after send | **frozen BLOCKED / decided SPEC_GAP, UNPROVED** (D47); mechanics PASS [I] | **frozen BLOCKED / decided SPEC_GAP, UNPROVED** (D47); mechanics PASS [I] | **REPAIR_SUPPORTED [I]**, bounded |

**Mechanism (our chosen completion, not the paper's):** the worker commits one `RELEASE_INTENT` per grant
(with the response token) **before** anything is sent, then a write-ahead `RELEASE_SENT` per attempted send
**before** transmitting; a retry returns the stored token; delivery is always `unknown`; SQLite WAL with
`synchronous=FULL` (worker.py:59-60, 130-188). The crash is the TEST-ONLY hook `testtools.faulty_adapter`,
which ends the process with `os._exit(86)` at `after_intent` (no response line) or `after_send` (after the
response line is flushed). Restart uses the **production** adapter on the same state.

**As measured in the historical runs [I], all six rows:** the hook exits 86 with empty stderr; the production
restart on the same private state and deployment returned the **identical cached response** strictly before
the original grant expiry; worker counts:

| Point | At crash (sent / completed) | After retry (sent / completed) | Intents |
|---|---|---|---|
| after intent | 0 / 0 | 1 / 1 | 1 |
| after send | 1 / 0 | 2 / 1 | 1 |

One PBC outcome per row afterwards. In a separate step the DBC was advanced to max(latest + 1, original
expiry); the **identical** release envelope then returned EXPIRED, with the whole worker log, cache, attempts
and native state unchanged (A3-0038). Repaired-e retries landed about 4 s before expiry (A1-0049, agent 3
host, single samples). In the gate run (this host) the last sends came 23 s (repaired-e) and 27 s (paper)
before the original expiry, and every expired cached retry, observed at expiry + 1, returned EXPIRED (§3.4).

**Why the paper rows are SPEC_GAP (D47; S2-0002; paper figures checked in A1-0064):** HMBC specifies **no**
key-release durability, retry, idempotence or crash-recovery semantics (III-D3/D4; III-E2; IV-B/Fig. 8, where
a cache database holds *pending log sessions*: cite Fig. 8 as a pending-log-session cache, not as release-state
durability). Agent 1 read Fig. 5, 6 and 8 (pp. 11-13) as rendered images: no figure specifies crash, retry,
restart, durability or recovery semantics for key release; the only failure language (§IV-B, p. 13) concerns
batching log sessions into the PBC (A1-0064). The crash points exist **only because** this reconstruction
moved partial decryption into an off-chain worker (A03). The observed behaviour is a **tested reconstruction
result of our own completion** (A03, A12, A21, A37, D35/A38); it can neither establish nor refute a paper
property. The frozen label BLOCKED is shown because it was pre-registered before D35/A2-0012 made paper
releases run at all. This is a relabel of an ambiguity class: **not a pass, not a changed outcome, never a
finding.**

**Owner evidence [U], not catalog rows** (`protocol/evidence/p2-t1-t3/`; S2-0006): T2 (`test_recovery.py`, 3
profiles) shows a crash **before** the durable intent leaves no release row and nothing is sent; T3
(`test_faulty_adapter.py`, 3 × 2) shows the **first** production restart after the original expiry answers
EXPIRED with the worker log unchanged. Both were detected by deliberate mutants on a scratch copy (3/3).

**Limits:** two logical crash points via a TEST-ONLY hook; no power loss, no OS-level kill, no
fsync-of-directory claim; worker-side equality at the exact expiry second is owner evidence only
(`test_worker_hardening.py:27`); the first restart after expiry is owner evidence (T3), not an integrated row;
one trial per row. SL1-SL7 add **no** recovery evidence.

## 10. Legitimate controls

- **E1 9/9 [I]:** Alice allowed; Bob policy-denied (code 9); wrong-issuer admin (code 16); in each of the three
  profiles (`evaluation/evidence/e1/integrated-controls-20261008/`; A3-0029 plan 78e195f5..; A1-0038, A2-0019;
  356.061 s, exit 0).
- **Every catalog row runs the three controls first on D1** and the runner refuses the row otherwise
  (`e1._profile`); so every gate row PASS includes a passing Alice allow, release and one outcome, a Bob code 9
  and a wrong-admin code 16. This is the basis of gate criterion `legitimate-and-denied-controls`.
- **Fake implementations:** grant-all and deny-all fakes fail the oracle (unit level,
  `evaluation/tests/test_access_oracle.py`).
- Wrong-admin 16 is the baseline issuer restriction, not a repair (D-record N-1).

## 11. Formal correspondence (symbolic) [F]

**Models:** `evaluation/models/e/access.pv` (sha256 1ca65506..) and `access_mutant.pv` (1c6e1acc..), unchanged
since 4af11d3; ProVerif 2.05, declared local build bc2cd5ed.. (D48). Sources: A3-0033
(`evaluation/evidence/e2/formal-and-hook-review-20261009/`) and the P3 publication
(`evaluation/evidence/e2/p3-proverif-20261012/`, byte-identical outputs).

| Query | Full binding | Destination omitted from the certificate (deliberate abstraction mutant) |
|---|---|---|
| A grant agrees with a prior user request on all 8 fields | true | false (destination-substitution trace) |
| A grant agrees with a prior witness decision on all 8 fields | true | false (trace) |
| A grant agrees with a witness decision on the 7 non-destination fields, and that decision names the approved destination | true | true |
| `not event(AllowedGrant)` (an allowed grant is reachable, so the model is not vacuous) | false | false |
| `not event(DeniedGrant)` (a policy-denied grant is unreachable) | true | true |

<!-- GATE-PROVERIF:BEGIN -->
**Gate re-run (stage 6):** matched = **True**, tool sha256 `bc2cd5eddb8976fbab0194b6a10f6f05cf057287cf49dbbc97b37322b46af1cb` (declared local ProVerif 2.05 build).

| Model | Exit | stderr bytes | Verdicts | Expected | Byte-identical to A3-0033 / p3-proverif-20261012 |
|---|---|---|---|---|---|
| `evaluation/models/e/access.pv` | 0 | 0 | true, true, true, false, true | true, true, true, false, true | True / True |
| `evaluation/models/e/access_mutant.pv` | 0 | 0 | false, false, true, false, true | false, false, true, false, true | True / True |
<!-- GATE-PROVERIF:END -->

**Limits** (`evaluation/models/e/README.md`): non-injective queries, so replay is possible; one honest user,
one trusted witness, perfect symbolic signatures, atomic public names; not modelled: nonce consumption,
mutable trust or revocation state, timestamps or expiry, worker intent/send/recovery, audit reconciliation,
EIP-712 encoding, implementation correspondence, computational cryptography, ABE, quorum or consensus. The
model mutant is an abstraction mutation, not the deployed ledger mutant and not a paper vulnerability.

## 12. Mutants and gate criterion 4 (human decision A1-0080)

**Criterion 4 is stated as: "met on owner, formal and baseline evidence (human decision A1-0080); integrated
live mutant matrix not run".** Reason: the P3-mutants test-first work was stopped twice by a safety classifier
(A1-0079); the human chose to accept the existing evidence as a scoped claim (A1-0080). It is not
re-attempted.

**What criterion 4 rests on (A1-0080):**

1. **Owner ledger mutant suite on the real contracts** (`FOUNDRY_PROFILE=mutants forge test --root ledger`,
   checked by `ledger/tools/check_mutants.py`; `ledger/evidence/ae2-mutants.{json,txt}`). Re-run on the
   integrated tree on 2026-10-12 (`ledger/evidence/p3-mutant-suite-rerun/`, exit 0, 17 s): output
   byte-identical to the pinned evidence (`mutants.json` 60a30adc.., `mutants.txt` 7bcfca8e..): "ALL MUTANTS
   DETECTED BY THEIR EXPECTED TESTS".

   | Mutant (bit) | Detected by |
   |---|---|
   | no-destination-binding (1) | `test_E01_RequestFieldSubstitution`, `test_E01_RequestForOtherDestinationCertifiedHere` (contract `MutantNoDestinationBindingTest`) |
   | no-state-barrier (2) | `test_E02_RevocationBarrierBlocksOlderDecision` |
   | no-record-freshness (4) | `test_E02_DeliveryAfterOnDutyEntryEnds` |
   | no-nonce (8) | `test_E01_NonceReuseAcrossDifferentRequests`; the access-flow nonce-state assertion |
   | no-version-monotone (16) | `test_E02_EqualVersionDifferentContent`, `test_E02_StaleSignedCrlReplay`, `test_E02_StaleSignedTempAclReplay` |
   | no-receipt-binding (32) | `test_E03_ReceiptFieldSubstitution` |

2. **The ProVerif destination mutant** (§11): destination-substitution counterexamples, while agreement on the
   remaining fields holds.
3. **The baseline integrated catalog guard rows:** each guard rejects at exactly the check its mutant removes;
   agent 1's reviews replay this on calldata (A1-0067..A1-0077). In the gate run these are the 8 rows marked
   (guard) in §6:

   | Guard row (§6 #) | Expected error | Guard | Mutant it would kill |
   |---|---|---|---|
   | same nonce, distinct digests (22) | REPLAY | nonce guard `KSSC.sol:182` (181-183) | no-nonce (8) |
   | receipt binding × 3 (29-31) | WRONG_SUBJECT | receipt field binding before the quorum (`PSC.sol:266-269`) | no-receipt-binding (32) |
   | signed-list rollback (41) | STALE_ANCHOR | `TMSC.sol:190` | no-version-monotone (16) |
   | post-barrier revocation (47) | STALE_STATE | DV line 87, sequence cause | no-state-barrier (2) |
   | expired duty (50) | EXPIRED | DV step 13 | no-record-freshness (4) |
   | wrong destination (53) | WRONG_DESTINATION | DV step 1, line 60 | **none**: step 1 fires first; no-destination-binding (1) is detected only by the forge tests and the ProVerif mutant |

   These show that the integrated runner reaches each guard. **They do not show a mutant accepting in the
   integrated runner.**
4. **Positive controls:** legitimate Alice access succeeds in every row (§10), so the repaired profile is not
   deny-all.

**What must not be claimed (A1-0080):**

- **No integrated live mutant kill.** The evaluator never ran a `mutant-*` deployment.
- **No live accept-vs-reject kill of no-destination-binding** in any form (A1-0078 D-P3-2).
- The forge mutant suite is unit/integration-level on the ledger contracts. It does not cover the adapter, the
  relay or the two-chain runner.

**Owner rehearsal versus integrated baseline** [A1-L3] (owner evidence: `ledger/E2_HANDOFF.md`,
`ledger/evidence/ae2-mutants.*`). The "catalog row" column names the row whose guard each mutant removes. The
owner rehearsal ran live mutant probes (`ledger/tools/e2_rehearsal.py --mutants`, one fresh `mutant-*`
deployment each; `ledger/evidence/e2-full-rehearsal/summary.json` and `mutant-*/`): 5/6 were detected, and
no-destination-binding was not killed by the catalog recipe. This is owner evidence on agent 1's runner with
agent 2's faulty adapter. It is not the integrated evaluator, and it is **not** part of the A1-0080
criterion-4 basis. The integrated runner, including the gate run, ran only the **baseline** rows, where the
guard rejects; no mutant was ever deployed there (A1-0080).

| Mutant (bit) | Catalog row (guard) | Guard → mutant behaviour (owner rehearsal) |
|---|---|---|
| no-nonce (8) | E01-same-nonce-distinct-digests | REPLAY → second grant |
| no-receipt-binding (32) | E03-receipt-binding-control-* | WRONG_SUBJECT → inconsistent receipt recorded |
| no-state-barrier (2) | E02-post-barrier-revocation | STALE_STATE → grant after revocation |
| no-record-freshness (4) | E02-expired-duty | EXPIRED → grant after the duty ended |
| no-version-monotone (16) | E02-signed-list-rollback | STALE_ANCHOR → old list accepted |
| no-destination-binding (1) | **not killable by the catalog recipe** | the second-deployment request fails at step 1, which the mutant keeps |

The "mutant behaviour" column comes from the owner rehearsal; it was **not observed in any integrated run**.
Sensitivity for no-destination-binding comes from the forge contract `MutantNoDestinationBindingTest`
(`ledger/test-mutants/Mutants.t.sol:22`, which extends `DecisionBindingRepairedTest`:
`test_E01_RequestFieldSubstitution` and `test_E01_RequestForOtherDestinationCertifiedHere`) and from the
ProVerif destination mutant (A3-0033; re-run byte-identical in `p3-proverif-20261012` and in gate stage 6).
**No integrated destination kill is claimed** (A1-0061 G-3). A1-0077 note 2 also named a live code-separation
row for this mutant (from A1-0078 D-P3-2); A1-0080 supersedes that: no such row was run, and none is claimed.

**Protocol scope** [S2 §9/§10]: the A1-0080 basis contains **no protocol-module mutant**. The protocol owner
mutation checks (`protocol/evidence/mutation-check.json` 65/73 detected with 8 documented equivalents, the
original agent 2's run; `mutation-check-faulty-adapter.json` 9/9; T1-T3 3/3) show that the protocol module's
own tests are sensitive [U]; they are not a criterion-4 kill. The witness and worker gate on `profile == "2"`
and would serve `mutant-*` deployments (static reading); no integrated run ever deployed or served a mutant.

## 13. Ambiguities (paper silent or underspecified)

- **Relay-to-ACSC source authentication:** Fig. 6 forwards verified attributes with no binding specified (A02,
  A14, A25). All E01 paper SPEC_GAP rows depend on it.
- **Grant lifetime and recipient in paper profiles:** A24 (30 s from `policyEnf`), A38/D35 (response to
  `RSC.recipientKeyHash(grant.gid)`, native recipient zero); subject substitution routes the symbolic response
  to the substituted subject (SL1).
- **Trust-list "latest" semantics:** A09 (append vs monotone); the revocation barrier A17, A20, A22.
- **Key-release durability, retries and crash recovery:** the paper is silent (A1-0064 figure check); our
  worker choice is A03, A12, A21, A37. This is why the four paper crash rows are SPEC_GAP next to the frozen
  BLOCKED (D47).
- **Decision retry policy:** A31 is caller-side runner discipline, not an adapter guarantee (P9; A1-0064:
  ambiguity / stated trust assumption).
- **Record registration authenticity:** A41 (first-writer-wins payload commitment, trusted pre-registration).
- **Log detail mode:** hash-only vs complete details (A13). The runs used complete details; hash-only was not
  run.

## 14. Refuted hypotheses, failed trials and process errors

- **Refuted catalog expectations:** none in the historical slice runs and none in the gate run: every row
  matched its frozen classification and error. Frozen CONDITIONAL outcomes resolved to acceptance under the configured-relay
  recipes (subject substitution, wrong destination, expiry boundary, post-barrier, expired duty; the fabricated
  outcome was recorded); that is a resolution of CONDITIONAL, not a refutation.
- **Refuted runner assumption (SL2):** "the D2 worker can be exported in every row" was false: the pinned
  worker is created lazily. The first SL2 run failed visibly (exit 2, 75 s, 0/7 rows; S3-0008,
  `evaluation/evidence/e2/sl2-relay-failed-20261010/`). It was missed by all three same-model reviews (A1-0065,
  S2-0008, S3-0007), which is the correlated-review risk of A1-0059 showing up in practice (A1-0066). Fix:
  the D49 never-instantiated rule (S3-0009). A runner and review defect, not a protocol finding.
- **Failed trial:** repaired-e identical replay, first attempt: release after the original expiry (§7.1). Kept;
  re-run under a new FREEZE.
- **Evaluator error caught by review:** the subject oracle first used WRONG_SUBJECT = 3; the frozen code is 2
  (A1-0058, fixed in A3-0047). Not a research result.
- **Owner review-tool defects, fail-closed and fixed before any result:** SL3 event registry (A1-0069 note 1);
  SL5 ABI registry and record filter (A1-0073 disclosure). Evidence unchanged.
- **Wording corrections:** S3-0018 "validUntil in the DBC's past" → "at or past" (A1-0075 note 2); S2-0018 per-row
  probe counts (total right); S2-0019 cited line 49 for a check at line 52 [S2].
- **Owner rehearsal gap:** dropped-outcome rows without RELEASE (A1-0060 R2 correction).
- **Safety-classifier stops (P3):** the live mutant matrix and the integrated window were stopped, paused and
  not retried (A1-0079, A1-0081); a truncated test file was removed so the suite still collects. Both are
  recorded as NOT RUN with human decisions A1-0080 and A1-0081.

## 15. Limitations

- Paper-derived reconstruction; no access to the authors' implementation; omitted details are explicit choices
  (A01-A41).
- **Symbolic** crypto adapter in E: no ABE, no secrecy or performance claim; `rotate_epoch` not implemented
  (G is locked).
- **Safe-ledger** assumption: single-host Anvil, no consensus, finality or Byzantine validator. Grouped RPC
  reads cannot detect a transient reorg restored between checks. Status-0 codes are decoded from
  `debug_traceTransaction.returnValue` (selector `0xf73a052c`), an Anvil debug API, not a consensus-level
  guarantee [A1-L5 item 7].
- **Trusted worker** and **one trusted witness** (q = 1). A compromise of either breaks the repaired-e
  guarantees; the DBC verifies the witness signature, not that a PBC request exists [S2 §13]. Witness or worker
  compromise is F's subject, not tested here.
- **TEST-ONLY keys** are derivable from labels; custody is role separation, not secrecy; every adapter,
  including SL7's B, derives the same label keys [A1-L5 item 1; S2 P16].
- **Delivery unknown.** Logical process-death crash points only.
- **Compromised-relay stresses** are outside HMBC's secure-isolation assumption (A01): specification
  dependencies, not exploits [A1-L5 item 3].
- **Fixed synthetic policy:** doctor/onDuty TempACL and DATA_P1/P2; not a general ABAC engine [A1-L5 item 4].
- **Governance** (addCA/removeCA/root refresh, majorityConsent) is phase F and not implemented [A1-L5 item 5].
- **Gas and cost** are not an RQ1 metric; the relay deployer needs about 400 ETH per deployment on Anvil
  [A1-L5 item 6].
- **Clocks:** two Anvil chains with uncorrected skew; 1 s granularity; second-level cross-chain values are
  indicative only. Repaired-e request TTL ≤ 30 s with thin single-sample margins (§3.4).
- **Fingerprints** bind chain ids plus addresses: a state directory reused on a fresh chain with identical
  addresses would be accepted (no effect: new state directories were used). Fixed deploy sequences repeat
  grant ids and KSSC addresses across rows [S2 §13].
- **One trial per row.** SPEC §7's performance protocol (10 warm-up and 30 measured repetitions) was not
  applied; no statistics and no performance claim.
- **Not run:** integrated live mutant matrix (A1-0080), integrated window (A1-0081), hash-only log mode,
  TempACL rollback, acceptance at `expiresAt − 1`.
- **Host and toolchain:** one machine; Python 3.13.5 against the frozen 3.13.13 (`hostDifferences`); ProVerif
  2.05 as a declared local build (bc2cd5ed.. against the frozen c1087205.., source equal) (D48). The three
  pre-solo slices historically ran on agent 3's host in strict mode; the gate run re-ran them in solo mode on
  this host (12/12 PASS). Their historical raw logs are held only on agent 3's host. Host memory was low during
  the gate run (MemAvailable about 3.4-3.8 GiB; §5).
- **Correlated review:** all solo-phase reviews and ACKs come from one model; the original agents 2 and 3 have
  not reviewed results after A3-0049.

## 16. What the evidence does not show [S2 "does not show", A1 review exclusions]

- **The witness's own clock readings.** Which decision term bound, and that the expired-duty duty was valid at
  collection, are inferred from bounds and from the ALLOW result, not observed directly.
- **That no DBC block was mined between SL7's timestamp pin and the consume** (shown only indirectly).
- **Adapter internals** (purity of `prepare_request`, file-free witness operations, no caches): static reading
  at the pin.
- **Raw adapter transcripts:** published as canonical or redacted responses with hashes; not re-joined against
  the private raw transcripts.
- **Key-substring absence in the historical SL1-SL3 publications** (only token-preimage scans there; the gate
  publication, which re-ran those rows, was key- and token-scanned in full).
- **Any recovery or durability property beyond §9.4,** any delivery, any recipient-side decryption.
- **Any mutant accepting in the integrated runner** and **any integrated window value** (A1-0080, A1-0081).
- **Raw log topics** in SL1 were not re-decoded by agent 1 (A1-0063); agent 1's reviews use the same
  keccak/eth_abi/eth_keys libraries as the evaluator (A1-0067 note 4).
- **Independent review.** Every check is correlated self-review.

## 17. Reproduction and evidence index

| Item | Location |
|---|---|
| Gate plan, FREEZE, ACKs | `evaluation/evidence/e3/gate-plan-20261012/` (plan c0086019..); S3-0021; A1-0083; S2-0021; ACK index `tmp/p3/gate-run/acks.json` (job tmp) |
| Gate run evidence | `evaluation/evidence/e3/gate-run-20261012/`: selected copy of the raw output with README, `selected-manifest.json`, `external-public-inventory.json`, `live-result-audit.json`, `publication-check.json`, `thin-row-margins.json`, `never-publish-scan.json` and the selection script; INTEGRATION_RESULT S3-0022; hashes in §5 |
| Historical slice runs | `evaluation/evidence/e2/{recovery,expiry,duplicate,grouped-replay}-live-20261009/`, `sl1-subject-live-20261010/`, `sl2-relay-live-20261010/`, `sl3-audit-live-20261010/`, `sl4-receipt-live-20261010/`, `sl5-trust-live-20261010/`, `sl6-barrier-live-20261011/`, `sl7-destination-live-20261011/` |
| Kept failed trials | `evaluation/evidence/e2/nonce-replay-live-20261009/`, `evaluation/evidence/e2/sl2-relay-failed-20261010/` |
| E1 controls | `evaluation/evidence/e1/integrated-controls-20261008/` |
| ProVerif | `evaluation/evidence/e2/formal-and-hook-review-20261009/` (A3-0033); `evaluation/evidence/e2/p3-proverif-20261012/`; gate stage 6 `evaluation/evidence/e3/gate-run-20261012/proverif/` |
| Frozen interface | `interfaces/v1/FREEZE.json` (f700292e..), `interfaces/v1/scenarios/`, `source-map.csv`, `assumptions.csv` |
| Forge suite [A1-L6] | `forge test --root ledger` (166/0 at P1, `communication/agent-1/solo/evidence/p1-integrated-baseline/`) |
| Mutant suites, mutation smoke, cast crosscheck [A1-L6] | `ledger/evidence/` |
| Owner mutant suite re-run, criterion 4 basis [A1-L6] | `ledger/evidence/p3-mutant-suite-rerun/` (byte-identical to the pinned `ae2-mutants.*`; A1-0080) |
| Early-rows review tool, 12 pre-solo rows [A1-L6] | `ledger/evidence/early-rows-review/` (committed in 9682e54, before the gate FREEZE) |
| Gate run, independent ledger review [A1-L6] | 8 pre-registered tools (A1-0083): 56/56 rows pass on the raw output; the published-copy review is A1-0084 |
| Gate run post-run reviews and gate RESULT | A1-0084 (ledger; tool outputs `ledger/evidence/gate-e-review/`); S2-0022 (protocol; `protocol/evidence/reviews/s2-0022-gate-run/`); gate RESULT S3-0023 (§18.3) |
| Owner rehearsal of 56 rows [A1-L6] | `ledger/evidence/e2-full-rehearsal/` (dropped-outcome rows without RELEASE: A1-0060 R2 correction) |
| Revocation window (owner) | `ledger/evidence/revocation-window/` (A1-0046) |
| SL1-SL7 independent ledger reviews [A1-L6] | `ledger/evidence/sl{1-subject,2-relay,3-audit,4-receipt,5-trust,6-barrier,7-destination}-review/`; A1-0063, A1-0067, A1-0069, A1-0071, A1-0073, A1-0075, A1-0077 (SL6/SL7 tools committed before their runs) |
| Protocol pin manifest [S2] | `git show 0716a8e:protocol/evidence/source-manifest.sha256` (d16ddad8.., 108); current `protocol/evidence/source-manifest.sha256` (551e9f77.., 127) |
| Protocol owner suite and T1-T3 [S2] | `protocol/evidence/p2-t1-t3/` (1375 passed, 201 skipped, exit 0) |
| Protocol mutation checks [S2] | `protocol/evidence/mutation-check.json` (65/73, 8 equivalents); `mutation-check-faulty-adapter.json` (9/9) |
| Protocol slice reviews [S2] | `protocol/evidence/reviews/s2-0005-sl1/`, `s2-0010-sl2-r2/`, `s2-0012-sl3/`, `s2-0014-sl4/`, `s2-0016-sl5/`, `s2-0018-sl6/`, `s2-0020-sl7/`, `s2-0021-gate-freeze/` (every `review_*.out.json` has `problems: []`) |
| Decisions | `communication/DECISIONS.md` D35, D47, D48, D49; A1-0059, A1-0061, A1-0064, A1-0080, A1-0081, A1-0082 |

## 18. Review and ACK record

### 18.1 Agent 1's independent ledger review of the gate run (pre-registered in A1-0083)

Agent 1 committed eight review tools **before** the run and ran them on the gate output: first on the raw
output in job tmp, then on the published copy (A1-0084). Any tool failure is reported as a discrepancy, not
fixed silently (A1-0083).

| Tool | sha256 | Rows |
|---|---|---|
| review_early_rows_evidence.py | 199dd936.. (committed 9682e54) | recovery-expiry 6, duplicate 3, nonce replay 3 |
| review_subject_evidence.py | 3e180ac4.. | SL1 3 |
| review_relay_stress_evidence.py | 98a97c63.. | SL2 7 |
| review_audit_stress_evidence.py | f02cbec4.. | SL3 6 |
| review_receipt_stress_evidence.py | 5fa5a7c9.. | SL4 7 |
| review_trust_stress_evidence.py | 13c10d1d.. | SL5 6 |
| review_barrier_stress_evidence.py | 9edc3eb2.. | SL6 9 |
| review_destination_stress_evidence.py | 9e788ce9.. | SL7 6 |

**Results:** agent 1's eight pre-registered ledger review tools (A1-0083) pass 56/56 rows on the raw gate
output; the published-copy review is A1-0084.

**A1-0084** (`communication/agent-1/outbox/0084-review-e-gate-run-result.md`, sha256 580d9a12..; tool outputs
`ledger/evidence/gate-e-review/`). Verdict: **no discrepancy in the ledger-native evidence of the 56 gate
rows.**

- The eight tools, unchanged, pass 56/56 rows on the raw output and again on the published copy, with
  byte-identical JSON outputs. Every value is re-derived from the native records with the ledger ABIs.
- All 2092 published catalog files and the 7 top-level run files are byte-identical to the raw output, and
  agent 1's key scan (13 label keys plus the vector keys) found 0 hits.
- RQ1-E.md's ledger claims match agent 1's sections. This was a targeted check, not a line-by-line read: all
  21 distinct ledger `file:line` citations resolve at 933d2a7, criterion 4 has the A1-0080 wording, the window
  text is A1-0081's, the D47 labels are present, the Appendix A points are stated, and the must-not-claims
  appear only as negations.
- Not covered by A1-0084: the release-token scan, adapter and worker internals, and runner and oracle
  internals. It is correlated review, not a gate E decision.

Before publication, agent 3 (proxy) ran the same unchanged tools read-only on the published copy as a layout
check: each exited 0, 56 rows in total, and every output was byte-identical to the run on the raw output
(`evaluation/evidence/e3/gate-run-20261012/publication-check.json`). That check is not agent 1's review.

### 18.2 Agent 2 (proxy)'s protocol reviews

- Slice reviews, each with a script and output under `protocol/evidence/reviews/`: S2-0005 (SL1), S2-0010
  (SL2), S2-0012 (SL3), S2-0014 (SL4, first live deviating witness), S2-0016 (SL5), S2-0018 (SL6), S2-0020
  (SL7). Each found no discrepancy in protocol scope.
- Slice ACKs: S2-0004, S2-0008, S2-0009, S2-0011, S2-0013, S2-0015, S2-0017, S2-0019; owner tests T1-T3
  (S2-0006); D-6 and A31 (S2-0007, accepted in A1-0064).
- Gate FREEZE ACK S2-0021: same adapter, crash-hook, deviating-witness and B usage as the slices; timing risk
  stated; a post-run re-check of the protocol facts and the never-publish selection is promised before the
  P4-3 ACK.
- Post-run re-check **S2-0022** (`communication/agent-1/solo/agent-2-proxy/outbox/0022-review-e-gate-run-result.md`,
  sha256 f5a761cb..; script and output `protocol/evidence/reviews/s2-0022-gate-run/`, `problems: []`).
  Verdict: **no discrepancy in protocol scope across all 56 gate rows, and no objection to RQ1-E.md's
  protocol claims.** It found:
  - A31: 18 stress decisions, equal per slice to the slice reviews;
  - D49: 180 verified never-instantiated probes;
  - the crash hook in all 6 recovery rows, with a single release per row;
  - 66 decisions, all bound by the request expiry (§3.4);
  - all 152 prepared requests verbatim in the mined calldata;
  - 0 never-publish hits;
  - §3.2, the §6.1 tables and the §9.4 crash-count table verbatim;
  - the §3.4 SL7 rewording accepted.
  It did not read the private worker databases or repeat the raw-token substring scan (§6.1).

### 18.3 Same-source ACKs (A1-0082 P4-3)

**Status: pending.** The gate RESULT is **S3-0023**
(`communication/agent-1/solo/agent-3-proxy/outbox/0023-gate-result-e.md`). It names one manifest:

- the gate `manifest.json` and `gate-evidence.json` sha256;
- the sha256 of this report;
- the plan (c0086019..);
- the run HEAD 21b37fb and the evidence commit c2c81d5.

This report and S3-0023 are committed together in one agent-1 commit.

The three same-source ACKs follow S3-0023. Each names the same hashes and that commit, and each repeats the
correlated-review disclosure:

- **A1-0085**: agent 1, the ledger claims and every row;
- **S2-0023**: agent 2 (proxy), the protocol and key claims;
- **S3-0024**: agent 3 (proxy), sign-off of the evidence and model.

This report cannot carry its own hash or those ACKs. The final ACK record and the gate E decision live in
`communication/GATES.md` (A1-0082 P4-4).

## Appendix A. Points stated by agent 1's ACKs and reviews (A1-0062..A1-0077)

| Point | Source | Where in this report |
|---|---|---|
| Paper grantId is independent of gid; the substituted grant is to a relay-asserted gid (outside A01) | A1-0062, A1-0063 | §7.2 |
| A31 is runner discipline, not protocol enforcement; Fig. 8 is a pending-log-session cache | A1-0064 | §3.2 P9, §9.4, §13 |
| Forged-tuple repaired-e used a real forwarded request (disclosed recipe difference) | A1-0065 | §7.3 |
| SL2 review miss (lazy worker), correlated-review risk; D49 | A1-0066 | §14 |
| Shared paper replay grantId is a fixture artifact | A1-0067 | §7.4 |
| Fabricated outcome is "outcome without a grant"; PENDING is ledger-permanent; E0-era sentence superseded | A1-0068 | §9.2 |
| Binding and signature rows give the same native code; dbcBlock witness-attested only; no PBC report deadline; binding rows are A40 | A1-0070, A1-0071 | §9.3 |
| **Wrong issuer is not a repair** | A1-0072 point 1, A1-0073 | §0, §8.1 |
| **STALE_ANCHOR is `TMSC.sol:190`**, not 192 | A1-0072 point 2, A1-0073 note 1 | §8.2, §12 |
| Paper rollback un-revokes Alice; CRL only, TempACL not run | A1-0072 points 3-4 | §8.2 |
| **Paper pre- and post-barrier are the same execution** | A1-0074 point 1, A1-0075 note 4 | §8.3 |
| **The cross-clock 2 s is not a window** | A1-0074 point 2 | §8.3, §8.5 |
| Post-barrier STALE_STATE is the line 87 sequence cause; expired duty is step 13 | A1-0074 point 3, A1-0075 note 1 | §8.3, §8.4 |
| ADVANCE_CLOCK is a DBC-only jump; INSTALL_SHORT_DUTY is setup; margins are host properties | A1-0074 points 4-6 | §8.4, §3.4 |
| **The paper expired-duty grant is at the boundary instant** | A1-0075 note 2 | §8.4 |
| Repaired expired-duty margin 7 s | A1-0075 note 3 | §3.4, §8.4 |
| **SL7 step 1 cannot kill mutant 1** | A1-0076 point 1, A1-0077 note 2 | §7.5, §12 |
| Paper wrong destination references a request absent from A's PBC | A1-0076 point 2 | §7.5 |
| **Equality at expiry rejects (`>=`)**; `expiresAt − 1` not tested | A1-0076 point 3, A1-0077 note 4 | §7.6 |
| DBC-only clock pin; B is a third deployment | A1-0076 points 4-5 | §7.5, §7.6 |
