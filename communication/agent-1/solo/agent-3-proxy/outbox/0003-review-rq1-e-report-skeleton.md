Message-ID: S3-0003
From: agent-3 (proxy)
To: agent-1
Cc: agent-2 (proxy)
RQ: E
Task: P0 read-only preparation: skeleton of evaluation/reports/RQ1-E.md with the 12 completed E2 results filled in from evidence
Type: REVIEW
Interface-version: v1
Responds-to: A1-0059, S3-0001, S3-0002
Source-manifest: agent-1 HEAD 78cdd11c6a99ca0aaab57fc031ee0699b759ba0d; SPEC.md and PLAN.md (agent-3 8e5a6dd versions, merged); interfaces/v1/source-map.csv and assumptions.csv (frozen copies); evidence READMEs and catalog-coverage.json under evaluation/evidence/{e1,e2}/; communication/agent-1/outbox/0042 (ledger claim sheet), 0046 (revocation window owner result); ledger/E2_HANDOFF.md b770c825..

Summary: Below is the proposed skeleton of `evaluation/reports/RQ1-E.md`, for review before P2. It is **not the report** and **not a gate result**.

- Completed results are filled in only where integrated evidence exists: E1 9/9, the ProVerif slice and 12 of 56 catalog comparisons.
- Every other row is a `NOT_RUN` placeholder.
- Owner rehearsal and unit evidence are cited as [R]/[U] and never counted as integrated [I].

The file goes to `evaluation/reports/RQ1-E.md` in P4, after the gate run.

Evidence: read-only. The cited paths exist at HEAD 78cdd11. Same-model correlated review. Nothing executed.

Impact: fixes the report structure, so each P2 slice can fill its family section and the gate run can fill the hashes.

Action requested:
- **agent 1:** review the ledger-claim placement (sections 5-7 and 10) and the limitation list.
- **agent 2 (proxy):** review the protocol/key assumptions in section 10 and the worker/delivery wording in section 7.3.

Both may send REVIEWs now. Formal ACKs come only on the final report hash (S3-0002 section 3.2).

---

# RQ1 / E: authorization, trust-anchor freshness and audit correspondence in a paper-derived HMBC2020 reconstruction

> **Status:** DRAFT SKELETON (P0). Gate E: NOT_RUN. F/G locked. Rows marked NOT_RUN have no
> integrated result. Every review and ACK of this report in the solo phase comes from the same model
> as agent 1 (agent 1, agent 2 (proxy), agent 3 (proxy)). It is **correlated self-review, not
> independent review**. Agents 2 and 3 may re-review and overturn it on return.

## 0. Answer in brief (to be written last)

[PLACEHOLDER: write after the gate run. Allowed structure:

- (i) which properties the paper's specified flow supports, in our reconstruction under recorded completions;
- (ii) which depend on unspecified details (SPEC_GAP), with the profile that shows the dependency;
- (iii) which repaired-e extensions enforce them, with measured limits;
- (iv) what stays BLOCKED or unproved.

Do not state a count of "vulnerabilities". Do not describe a compromised-relay stress as an HMBC
exploit.]

## 1. Research question

**RQ1 (SPEC section 1):** Which authorization, trust-anchor freshness and audit properties follow from
HMBC's specified access flow, which depend on missing details, and which explicit repairs enforce
them in a reconstruction?

**Required answer (SPEC section 1):**

- a source-to-property table;
- executable positive/negative traces for three case families (E01 decision provenance and replay;
  E02 trust-anchor freshness; E03 audit correspondence);
- repair comparisons;
- a bounded statement of what was proved or tested.

**Paper:** V. Malamas, P. Kotzanikolaou, T. K. Dasaklis, M. Burmester, "A Hierarchical Multi
Blockchain for Fine Grained Access to Medical Data", IEEE Access 8 (2020) 134393-134412,
DOI 10.1109/ACCESS.2020.3011201 (`references/HMBC2020.pdf`).

## 2. What this is and is not

- A **paper-derived reconstruction**, not the authors' implementation. Missing details are explicit
  choices (`interfaces/v1/assumptions.csv`, A01-A41), not discovered vulnerabilities.
- **HMBC only.** No JANUS code, claims or bug catalogue.
- **Synthetic fixtures only.** H1-H4 authorities; Alice (doctor at H1, on duty); Bob (registered, no
  doctor role); record `HMBC.data.P1.MHR`.

### 2.1 Result classes

The SPEC section 2 classes map to the AGENTS.md evidence vocabulary as follows:

| SPEC class | AGENTS.md vocabulary |
|---|---|
| SUPPORTED | paper-supported behaviour, *as reconstructed under recorded completions* |
| SPEC_GAP | ambiguity |
| REPAIR_SUPPORTED | extension result |
| RECONSTRUCTION_FAILURE | tested reconstruction result |
| REFUTED | tested reconstruction result |
| BLOCKED | not tested / unproved |
| `mutant-*` outcomes | deliberate mutation |

### 2.2 Evidence levels

| Level | Meaning |
|---|---|
| [I] | agent 3's (or agent 3 (proxy)'s) integrated two-chain run under FREEZE plus two ACKs |
| [R] | agent 1's owner rehearsal |
| [U] | module unit tests |
| [F] | symbolic ProVerif |

Only [I] answers a catalog row.

## 3. System and profiles (method)

- **Chains:** two local Anvil chains, PBC (chain ID 18545) and DBC (chain ID 28545). Foundry 1.8.5,
  solc 0.8.37, hardfork cancun, automining. A fresh chain pair and fresh deployment for every
  comparison row.
- **Roles:**
  - PBC: RSC registration/GID, TMSC trust lists, PSC orchestration, LSC logs;
  - DBC: ACSC policy enforcement, KSSC authorization, nonce and receipt state;
  - KSSC holds no secrets.
- **Off-chain:** agent 2's adapter (client, relay operations, one trusted witness, key worker) over
  JSON lines. Adapter mode is **symbolic**: no ABE, no real decryption.
- **Profiles:**
  - `paper-strict`;
  - `paper-minimal`;
  - `repaired-e`: user-signed EIP-712 requests, a witness-signed decision bound to the request
    digest, destination, state checkpoint and nonce, `(gid, nonce)` consumption, monotone trust-list
    versions, and attested outcome receipts;
  - `mutant-*`: one repaired check removed each.
- **Catalog:** frozen `interfaces/v1/scenarios/e0_cases.json` (48 = 16 schedules × 3 profiles) plus
  `e0_supplement_cases.json` (8 repaired-e) = **56 comparisons**. Positive controls are in
  `e_positive.json` (9). Expectations were frozen in E0 (FREEZE `f700292e..`) **before** any E2
  observation.
- **Execution discipline:**
  - FREEZE with the exact plan SHA-256;
  - exact ACKs (ledger and protocol scope) before services;
  - pinned owner snapshots (ledger 933d2a7, protocol 0716a8e);
  - source brackets before and after;
  - the oracles are independent of the implementation's control flow;
  - failed trials are kept.
- **Per-row controls:** wrong-admin (code 16) before the legitimate H2 update; Alice allow, release,
  completion and outcome; Bob policy denial (code 9).

## 4. Source-to-property table

[PLACEHOLDER: one row per property, built from `interfaces/v1/source-map.csv`. Columns: property, HMBC passage (PDF page / section), what the paper specifies, what it leaves open (A-id), paper-strict / paper-minimal behaviour, repaired-e mechanism, result class, evidence level and path. Seed rows:]

| Property | Paper source (source-map) | Open detail (assumption) | Family |
|---|---|---|---|
| Decision provenance (relay tuple to DBC) | S09, S12 (Fig. 6), S13 (V-A1), S20 | A02, A14, A19, A25, A38 | E01 |
| Trust-list freshness, issuer scoping | S03, S04, S15, S17 | A08, A09, A17, A20, A22 | E02 |
| Audit correspondence, outcome logging | S06 (Table 2), S07, S08, S19, S21 | A03, A12, A13, A21, A24, A26 | E03 |

## 5. E01: decision provenance and replay

| Schedule | paper-strict | paper-minimal | repaired-e | Evidence |
|---|---|---|---|---|
| identical request replay | **SUPPORTED [I]**: mined status 0, Rejected(8) REPLAY, no logs, whole state unchanged | **SUPPORTED [I]** | **REPAIR_SUPPORTED [I]** | `evaluation/evidence/e2/grouped-replay-live-20261009/` (A3-0044 plan 1b3cf7cd..; A1-0056, A2-0037; 375.185 s, exit 0) |
| subject substitution | NOT_RUN (expected CONDITIONAL / SPEC_GAP) | NOT_RUN | NOT_RUN (expected WRONG_SUBJECT 2) | SL1 |
| expiry boundary | NOT_RUN (expected CONDITIONAL / SPEC_GAP) | NOT_RUN | NOT_RUN (expected EXPIRED 7) | SL7 |
| forged tuple | NOT_RUN (expected ACCEPT / SPEC_GAP) | NOT_RUN | NOT_RUN (expected BAD_SIGNATURE 1) | SL2 |
| wrong destination | NOT_RUN (expected CONDITIONAL / SPEC_GAP) | NOT_RUN | NOT_RUN (expected WRONG_DESTINATION 3) | SL7 |
| new-reference replay | NOT_RUN (expected ACCEPT / SPEC_GAP) | NOT_RUN | NOT_RUN (expected REPLAY 8) | SL2 |
| same nonce, distinct digests | – | – | NOT_RUN (expected REPLAY 8) | SL2 |

**Completed result (identical replay), as measured:**

- In each profile, one allowed grant existed.
- The relay resubmitted the **identical** accepted ACSC calldata (`policyEnf` in paper profiles,
  `consumeDecision` in repaired-e) with a fresh transaction nonce.
- The transaction was mined with status 0, decoded Rejected(8), and no logs.
- The request, grant, nonce, access count, idle worker and both chains' histories were unchanged.
- The original Alice release, completion and one outcome, Bob's denial and wrong-admin 16 all passed
  in all three profiles.
- Probe wall times: 7.07 s, 7.00 s, 7.00 s.

**Limits:**

- Grant-id uniqueness (`KSSC.sol:180`, A25) fires **before** the nonce check. This row therefore
  does not test `(gid, nonce)` consumption; only the same-nonce supplement does.
- Equal idle-worker snapshots are not retry/idempotence evidence.
- Paper "SUPPORTED" rests on the A25 completion (deterministic grantId).

**Retained failed trial:** the first attempt (`evaluation/evidence/e2/nonce-replay-live-20261009/`,
plan a7732650.., 341.181 s, exit 2) failed:

- the paper rows were complete;
- in repaired-e, the replay subcheck passed but the first release then returned EXPIRED (probe
  10.21 s, thin TTL margin).

This was a runner-timing failure, not a protocol finding. It was kept; there was no TTL extension.

[PLACEHOLDER: the other rows, with the paper-vs-repaired distinction, observed traces and per-row
qualifications. **Required wording for wrong destination (repaired):** the catalog recipe is
rejected at DecisionVerifier step 1 (source PSC binding), not at the destination check (A1-0039).]

## 6. E02: trust-anchor freshness

| Schedule | paper-strict | paper-minimal | repaired-e | Evidence |
|---|---|---|---|---|
| wrong issuer (H1 admin, H2 list) | exercised [I] in every E1/E2 row (code 16 plus rollback), not yet credited as a catalog row | same | same (baseline, not a repair) | `evaluation/evidence/e1/integrated-controls-20261008/` (A3-0030) and every E2 row. Catalog credit: SL5 |
| signed-list rollback | NOT_RUN (expected ACCEPT / SPEC_GAP) | NOT_RUN | NOT_RUN (expected STALE_ANCHOR 5) | SL5 |
| pre-barrier revocation | NOT_RUN (expected ACCEPT / SPEC_GAP) | NOT_RUN | NOT_RUN (expected ACCEPT, designed window) | SL6 |
| post-barrier revocation | NOT_RUN (expected CONDITIONAL / SPEC_GAP) | NOT_RUN | NOT_RUN (expected STALE_STATE 6) | SL6 |
| expired duty | NOT_RUN (expected CONDITIONAL / SPEC_GAP) | NOT_RUN | NOT_RUN (expected EXPIRED 7) | SL6 |

**Revocation window:**

- Integrated measurement: NOT_RUN.
- Owner measurement [R] (A1-0046, `ledger/evidence/revocation-window/`):
  - repaired-e: W = min(barrier acceptance, remaining request TTL) ≤ 30 s, with 2/6/11/21 s for
    barrier delays 0/5/10/20 s and 26 s at expiry without a barrier;
  - paper-strict: no ledger bound (a pre-revocation tuple is still grantable at +65 s).
- [PLACEHOLDER: integrated values and comparison.]

## 7. E03: audit correspondence

### 7.1 Duplicate outcome (completed)

| Profile | Result | Evidence |
|---|---|---|
| paper-strict | **SUPPORTED [I]** | `evaluation/evidence/e2/duplicate-live-20261009/` (A3-0039 plan 5ef10dc6..; A1-0052, A2-0032; 365.374 s, exit 0) |
| paper-minimal | **SUPPORTED [I]** | same |
| repaired-e | **REPAIR_SUPPORTED [I]** | same |

**As measured:**

- After a successful Alice release, completion and one outcome, the relay resubmitted the identical
  outcome call (`reportOutcome` in paper profiles, `reportAttestedOutcome` with the original receipt
  in repaired-e) with a fresh transaction nonce.
- It was mined with status 0, Rejected(8), and no logs.
- The PBC request, DBC grant, worker cache, events and attempts, and both histories were unchanged.

**Limit:** "one outcome per request" is a reconstruction choice (A1-0042 E03-4). This is a tested
reconstruction result, not a paper theorem.

### 7.2 Crash and recovery (completed mechanics; paper classification BLOCKED)

| Row | paper-strict | paper-minimal | repaired-e |
|---|---|---|---|
| crash after durable intent | mechanics PASS [I]; **class BLOCKED / unproved** | mechanics PASS [I]; **BLOCKED** | **REPAIR_SUPPORTED [I]**, bounded logical mechanics only |
| crash after send | mechanics PASS [I]; **BLOCKED** | mechanics PASS [I]; **BLOCKED** | **REPAIR_SUPPORTED [I]**, bounded |

**Evidence:**

- `evaluation/evidence/e2/recovery-live-20261009/` (A3-0035 plan 4bceffc3..; A1-0048, A2-0028;
  778.47 s, exit 0; 24 process records: 18 exit 0, 6 intentional exit 86);
- `evaluation/evidence/e2/expiry-live-20261009/` (A3-0037 plan a76a291d..; A1-0050, A2-0030;
  779.772 s, exit 0; `catalog-coverage.json`).

**As measured:**

- The TEST-ONLY hook `testtools.faulty_adapter` exited naturally with code 86 and empty stderr:
  - `after_intent`: empty EOF;
  - `after_send`: one validated response frame, then EOF.
- The production adapter restarted on the **same** private state and deployment. The retry ran
  strictly before the original grant expiry and returned the identical cached response.
- Worker counts:

  | Point | Intent | Send attempts | Completed |
  |---|---|---|---|
  | after intent | 1 | 1 | 1 |
  | after send | 1 | 2 | 1 |

- One later PBC outcome.
- A separate cached retry after the original expiry returned EXPIRED, with the worker log, cache,
  attempts and all native state unchanged.

**Why the paper rows stay BLOCKED (G-4):** HMBC is silent on worker durability. The crash mechanics
belong to *our* chosen worker (A37). They cannot establish or refute a paper property. This is an
**ambiguity**, never a finding.

**Limits:** no first restart at expiry, no exact clock equality, no power-loss or OS-kill.

### 7.3 Remaining E03 rows

| Schedule | paper-strict | paper-minimal | repaired-e | Slice |
|---|---|---|---|---|
| dropped outcome | NOT_RUN (expected PENDING / SUPPORTED) | NOT_RUN | NOT_RUN (expected PENDING / REPAIR_SUPPORTED) | SL3 |
| fabricated outcome | NOT_RUN (expected CONDITIONAL / SPEC_GAP) | NOT_RUN | NOT_RUN (expected WRONG_PROFILE 21) | SL3 |
| receipt binding × 3 fields | – | – | NOT_RUN (expected WRONG_SUBJECT 2) | SL4 |
| receipt signature × 3 fields | – | – | NOT_RUN (expected WRONG_SUBJECT 2) | SL4 |
| receipt positive | – | – | NOT_RUN (expected ACCEPT) | SL4 |

**Required wording:**

- **Delivery is unknown in every row.** `RELEASE_SENT` records an attempted send, not recipient
  delivery.
- A DBC grant or receipt proves authorization, not delivery.
- Reconciliation needs eventual delivery and an honest reporter.

## 8. Legitimate controls

**E1 9/9 [I]:**

- Alice allowed; Bob policy-denied (code 9); wrong-issuer admin (code 16); in each of the 3 profiles.
- `evaluation/evidence/e1/integrated-controls-20261008/` (A3-0029 plan 78e195f5..; A1-0038,
  A2-0019; 356.061 s, exit 0).

**Grant-all and deny-all fake implementations** fail the oracle (unit level,
`evaluation/tests/test_access_oracle.py`). Every E2 row re-ran the three controls.

[PLACEHOLDER: gate-run control counts.]

## 9. Formal correspondence (symbolic) [F]

**Source:** A3-0033, `evaluation/evidence/e2/formal-and-hook-review-20261009/`; models
`evaluation/models/e/access.pv` and `access_mutant.pv` (unchanged since 4af11d3); ProVerif 2.05.

| Query | Full binding | Destination omitted (deliberate mutant) |
|---|---|---|
| A grant agrees with the prior user request on all 8 fields | true | false (trace) |
| A grant agrees with the prior witness decision on all 8 fields | true | false (trace) |
| Agreement excluding destination | true | true |
| An allowed grant is reachable | yes (not vacuous) | yes |
| A policy-denied grant is reachable | no | no |

**Limits:**

- Non-injective queries, so replay is possible.
- One fixed honest GID and names; perfect signatures; one trusted witness.
- Not modelled: nonce storage, mutable trust, clocks, worker recovery, EIP-712 encoding,
  implementation equivalence, ABE, quorum or consensus.
- The model mutant is an abstraction mutation, not the deployed ledger mutant.

**Re-run at the gate:** [PLACEHOLDER: done, or "not re-run on this host (ProVerif not installed);
outputs hash-checked", per G-2.]

## 10. Mutants and oracle sensitivity

| Mutant (bit) | Killing case | Integrated [I] | Owner [R] / [U] |
|---|---|---|---|
| no-nonce (8) | same-nonce, distinct digests | NOT_RUN | detected [R], [U] |
| no-receipt-binding (32) | receipt-binding controls | NOT_RUN | detected [R], [U] |
| no-state-barrier (2) | post-barrier revocation | NOT_RUN | detected [R], [U] |
| no-record-freshness (4) | expired duty | NOT_RUN | detected [R], [U] |
| no-version-monotone (16) | signed-list rollback | NOT_RUN | detected [R], [U] |
| no-destination-binding (1) | **none in the catalog**: the wrong-destination recipe fails at DV step 1, which the mutant keeps (A1-0039) | NOT_RUN; at most a code-level distinction from a non-catalog kssc rewrite (extension) | killed only by [U] (`RequestForOtherDestinationCertifiedHere`) and by the [F] abstraction |

Every mutant row also needs the legitimate Alice control passing on the mutant deployment.

## 11. Ambiguities (paper silent or underspecified)

Seed list, finalized per family:

- **Relay-to-ACSC source authentication** (Fig. 6 forwards verified attributes; no binding
  specified): A02, A14, A25.
- **Grant lifetime and recipient in paper profiles:** A24 (30 s from `policyEnf`), A38/D35 (response
  to `RSC.recipientKeyHash(grant.gid)`, native recipient zero).
- **Trust-list "latest" semantics:** A09 (append vs monotone); the revocation barrier A17, A20, A22.
- **Worker durability and delivery semantics:** A12, A21, A37. This is why the four paper crash
  rows are BLOCKED.
- **Log detail mode:** hash-only vs complete details (A13). Runs used complete details.

## 12. Refuted hypotheses, failed trials and process errors

- **Failed trial:** repaired-e identical replay, first attempt. The release came after the original
  expiry (section 5). It was kept and re-run under a new FREEZE.
- **Evaluator error caught by review:** the subject oracle first used WRONG_SUBJECT = 3. The frozen
  code is 2 (A1-0058, fixed in A3-0047). This is not a research result.
- **Refuted:** [PLACEHOLDER: any hypothesis refuted by a completed run. None so far.]

## 13. Limitations

- Paper-derived reconstruction; no access to the authors' implementation; omitted details are
  explicit choices (A01-A41).
- **Symbolic** crypto adapter in E: no ABE, no secrecy or performance claim.
- **Safe-ledger** assumption: single-host Anvil with automining. There is no consensus, finality or
  Byzantine validator. Grouped RPC reads cannot detect a transient reorg restored between checks.
- **Trusted worker** and **one trusted witness** (threshold 1). A witness or worker compromise is
  F's subject, not tested here. The DBC grant implies a PBC log only through the witness (A1-0042
  E01-6).
- **Delivery unknown.** Logical process-death crash points only. No power-loss or OS-kill.
- Compromised-relay stresses are outside HMBC's secure-isolation assumption (A01). They show
  specification dependencies, not exploits of the paper's model.
- One trial per comparison. Wall times are single samples, not distributions.
- Repaired-e request TTL ≤ 30 s, with thin measured margins (3-4 s).
- Host and toolchain:
  - single machine, synthetic fixtures;
  - Python 3.13.5 on this host vs 3.13.13 recorded in the frozen toolchain;
  - ProVerif [PLACEHOLDER].
- **Correlated review:** in the solo phase, all three ACKs come from the same model. The original
  agents 2 and 3 have not reviewed results after A3-0049.
- Raw logs of agent 3's E2 slices are held only on agent 3's host. This host has the selected
  public evidence.

## 14. Reproduction and evidence index

[PLACEHOLDER: the gate command, plan SHA-256, ACK index, run-manifest SHA-256,
`catalog-coverage-56.json` hash, tool versions, and a per-row evidence path table.]

## 15. Review and ACK record

[PLACEHOLDER, all of the following:

- the A1 report ACK (ledger claims);
- the S2 report ACK (protocol and key assumptions);
- the S3 report ACK (evidence and model);
- the same report and manifest hashes;
- the correlated-review disclosure repeated.]
