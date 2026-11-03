# F0 key, state and correlation inventory (agent 2) — for review

Author: agent 2. Date: 2026-11-03. **PROPOSAL / INVENTORY, NOT ACKED, NOT FROZEN.** Answers the agent-2 half of PLAN section 6 F0 and A3-0054..0057.
Claim classes: **[src]** read from source (not executed here), **[prop]** proposal, **[model]** bounded design check, **[gap]** something the code or paper does not provide.
Current protocol bytes are unchanged: origin/agent-2 376347d (= common F0 baseline), manifest `005c8448..`.

## 1. Keys [src unless marked]

All E keys are **TEST-ONLY and derivable from a public label**: `privateKey = keccak256("hmbc-e0-synthetic-key:" || label)` (`keys.py:27-28`). The labels are written in the deployment manifest
(`fixture.witnessSet.keyLabels`, `fixture.authorities[*].rootKeyLabel/caAdminKeyLabel`, `fixture.relay.keyLabel`). So **"the adapter keeps the key" is a process convention, not custody**:
anyone holding the manifest can sign as any identity. That makes the harness-level compromise of any key a free action (the runner already does it), and it makes F-25 / F-24 tell us nothing about
secrecy. It is a reconstruction limit, stated here once.

| # | Key (role) | Label / handle | Process that holds it today | Signs | Held by a faulty hospital Hx? |
|---|---|---|---|---|---|
| K1 | witness-1 (E, q=1) | `witness-1` | adapter process (`Witness.__init__`, `witness.py:35`) | StateCheckpoint, AccessDecision, GrantReceipt | n/a in E |
| K1' | witness-1..4 (F, proposed) | `witness-1..4` (A1-0088 C0.2) | one process each (proposal, §5) | the same three types plus GovernanceAction | **its own witness only** (1 of 4) |
| K2 | user / GID | `keyref:user:<label>` handle (`keys.parse`) | adapter, inside `prepare_request` only; the runner passes a handle, never a key | AccessRequest, Registration | Hx's controlled GIDs |
| K3 | authority root | `H1-root`..`H4-root` | runner / bootstrap producer (agent 1 script or my `testtools/bootstrap_fixture.py`), **never the adapter** | RoleCertificate, anchors | Hx's own root |
| K4 | CA-admin | `H1-ca-admin`.. | same | RevocationList, TemporalAcl | Hx's scoped admin |
| K5 | relay | `relay` | the **runner** plays relay in integrated runs (Option A: the runner submits all transactions); `relay.py` is agent 2's own-test relay | no typed message; it is a transaction sender and the PSC/ACSC-authorised relay address | none |
| K6 | deployer | ledger scripts | runner / ledger scripts; sealed after bootstrap | no typed message | none after seal |
| K7 | worker | **none**. There is no worker signing key in E. The `worker` role exists in the `keyref` grammar but no code signs with it (`keys.py:14`, `adapter.py`) | n/a | n/a | n/a |

Worker "secrets" in symbolic mode: a per-release random 32-byte token (`os.urandom`, `worker.py:155`) stored in `worker.sqlite`, plus the `records` and `releases` tables. They are TEST-ONLY handles with no
cryptographic confidentiality (`worker.py` module docstring). The recipient commitment is `keccak("HMBC.recipient-key." || label)`, a label hash, not a key hash.

What a faulty hospital Hx controls (answers PLAN F0 "agent 2 enumerates ... keys it controls"): its root key (K3), its scoped CA-admin (K4), the GIDs it creates (K2), and **one** witness key (K1').
It does not control the relay, another hospital's witness, the deployer after seal, or the worker. Correlation of these keys is organisational (FM-07), not cryptographic.

## 2. Durable and volatile state [src unless marked]

| # | State | Location | Written by | Notes |
|---|---|---|---|---|
| S1 | worker store: `records`, `releases`, `meta`, `events` | `<state-dir>/worker/worker.sqlite`, WAL, `synchronous=FULL`, dir mode 0700 | key worker | the only durable agent-2 state in E. Intent and send attempt are committed before transmission. `meta.deployment` = fingerprint of chain ids and four addresses (the weak binding, D-2) |
| S2 | witness signing store | none in E. **[prop]** `<state-dir>/witness-<i>/signing.sqlite`: `conflict`, `digests`, `superseded`, `observed`, `meta` | witness i | `SIGNING-RULES.md` sections 2 and 6 |
| S3 | witness init marker **[prop]** | `<state-dir>/witness-<i>/INITIALIZED` | witness i, created atomically with S2 | a missing S2 next to an existing marker is refused, never silently re-created |
| S4 | adapter memory | process | adapter | `_PINNED` deployment, `_LEDGER` clients. Lost on restart; nothing durable depends on it |
| S5 | relay state | none: the transaction nonce is read from the chain (`eth_getTransactionCount pending`, `chain.py:173`) | | a relay restart loses nothing |
| S6 | client state | none (`prepare_request` is a pure function of its input); the application nonce is chosen by the runner | | |
| S7 | ledger state | two Anvil instances; in-memory unless the runner dumps state | ledger | outside agent 2 |
| S8 | data store / ciphertext | **none exists**. Symbolic mode carries digests only (`ciphertextDigest`, `policyDigest`); there are no ciphertext bytes anywhere | | matrix F-26, see section 4 |

## 3. Correlation domains in the local harness [src/prop]

- Both ledgers, the runner (relay, deployer, authorities, users), the adapter, the worker and (proposed) four witnesses run as processes of **one OS user on one host**. They share a filesystem and the host clock.
  Separate keys and separate state directories do not make separate failure domains: a host or user compromise exposes S1 and every S2 (matrix FM-13), and any process can read any label-derived key anyway.
- The two chain clocks are not corrected against each other (E README). Death and expiry rules in `SIGNING-RULES.md` section 6 use only each target ledger's own clock, so skew does not affect agreement, only availability.
- One adapter `--state-dir` holds the worker today; proposed witness directories sit beside it. Two processes given the **same key and different state directories** are two independent signers for the
  same identity, i.e. an equivocation capability created by operator error; a local check cannot detect it (`meta.owner` binds a directory to one key but cannot see a second directory). It belongs to FM-13/FM-14.

## 4. Review of the F0 matrix, protocol side (A3-0054 / A3-0055 request)

I read `evaluation/scenarios/f_matrix.json` revision 2 and `fault-model.csv` (origin/agent-3 143619f). Nothing below changes a recorded result; every row stays NOT_RUN.

**Matrix rows my input answers or corrects**

| Row | Pending item in the CSV | Answer |
|---|---|---|
| FM-03 relay | key/state confirmation | confirmed: no witness key, no durable state (S5); relay is a transaction sender. The runner is the relay in integrated runs |
| FM-04 one witness | conflict keys / state / expiry / F-29 | `SIGNING-RULES.md` sections 1, 2, 4, 6 |
| FM-05/07 authority, faulty hospital | key enumeration | section 1 above |
| FM-08 worker | synthetic compromise mechanism | the worker has no signing key; the residual is "symbolic release without a ledger-committed grant". Mechanism **[prop]**: a TEST-ONLY worker variant that skips the committed-grant check, outside the adapter (like `testtools/faulty_adapter.py`). Symbolic only; no secrecy conclusion |
| FM-09 client | key material | handles only (`keyref:user:<label>`); recipient material is a label hash |
| **FM-10 data store / F-26** | storage fixture | **[gap] no data store exists in symbolic mode (S8).** Withholding or corrupting "stored bytes" has nothing to act on; the only observable is the runner dropping a response or altering `ciphertextDigest`, which exercises `finish_decryption`'s digest comparison, not a storage. Recommendation: mark F-26 analysis-only, or have agent 3 define a minimal synthetic storage object. I will not invent one inside the protocol module |
| FM-11 bootstrap | D50 fingerprint | `D50-DEPLOYMENT-BINDING.md` |
| **FM-13 common host / F-25** | placement | keys are derivable from public labels (section 1), so "common host compromise" needs no host access in the harness. F-25 is true by construction here; keep it as an analysis row |
| FM-14 database / F-27 | custody and rollback rule | `SIGNING-RULES.md` and this section: an `INITIALIZED` marker plus `PRAGMA integrity_check`/`quick_check` at open plus identity binding make **corruption, deletion and wrong-deployment** fail closed. A **consistent rollback to an older valid copy is not detectable locally** (the model shows the resulting equivocation, P9). Expected F-27 result: equivocation possible, classified as an assumption violation |

**Per-scenario protocol feasibility and the hooks each needs** (TEST-ONLY unless stated; none is a production operation)

| Hook | Behaviour | Scenarios |
|---|---|---|
| H1 `byzantine` witness variants | withhold; delay; equivocate (sign two values); signature that does not recover to the sender; signature by a non-member; repeated replies; sign on a stale view; sign a poisoned checkpoint | FL-2, FL-4, FL-5, F-12, F-16, F-22, FL-7, F-24 |
| H2 per-witness signature op | the runner can obtain one witness's signature for one proposal and assemble or craft certificates itself | FL-4, FL-5, FL-6, FL-10, F-23 |
| H3 per-witness RPC override | a witness is pointed at a different (divergent) ledger view. **Breaks the safe-ledger assumption by design**; only for the conditional rows | F-16, F-17, F-18 |
| H4 witness crash points | after commit and before reply; before commit | F-13 |
| H5 compromised-worker variant | see FM-08 | F-19 |
| H6 delay injection | per-operation delay in a witness or in the runner's transport | F-20 |
| H7 state-dir copy/restore | the runner's own file copy, plus the witness refusing corrupt or missing state | F-27 |

Rows needing **no protocol code**: FL-1, FL-3 (stop two witness processes), FL-8, FL-9, FL-11, F-15, F-21 (the E independent-validation tests at q=3), F-25 (see above), F-28 (ledger plus checkpoint cadence).

**Suggested additions and corrections to the matrix** (proposals for agent 3, not edits)

1. **F-29 expectation.** Under the proposed rule the prediction can be sharper than "no recovery guarantee": *a pinned key is released by the first mined target-ledger block whose timestamp is at or after the old expiry; without block production it stays pinned.* Safety is unaffected. [model P2/P5 are an abstraction; untested on the implementation]
2. **New row F-30: a certified governance action that fails a TMSC precondition** (e.g. ADD of an existing root). The whole transaction reverts, the nonce stays, and without witness-side pre-validation the key is pinned until expiry. Expected: honest witnesses refuse such a proposal before signing. Agent 1 (A1-0094) confirms the check is exact (every TMSC precondition is written only by governance and nonces are strictly sequential) and that F-30 is outside the honest-validation assumption, like F-24: a doomed action cannot reach q = 3 while two honest witnesses pre-validate at f = 1. [prop; untested]
3. **Protocol-side mutants for sensitivity** (source-edit mutants in my `tools/mutation_check.py`, as in E): M1 no durable record; M2 record written after the signature (crash window); M3 wall-clock re-signing; M4 skipped all-field checkpoint validation; M5 collector without filtering; M6 receipt block taken from the head; M7 decision expiry with the local-clock term. Each should flip exactly the scenario named: M1 or M2 to F-12/F-13, M3 to F-29, M4 to FL-7/F-24, M5 to FL-5/F-22, M6 and M7 to the equality of three witnesses' digests. None exists yet.
4. **F-13 detail.** "Restart after first signature" is the first mutant pair (M2). A real process kill between commit and reply needs hook H4.
5. **E witness is not a valid q=3 signer** (stateless, clock-dependent fields, section 0 of SIGNING-RULES). That is a source reading, not a measured E result, and it is why B-F1 is a rewrite of the witness, not a configuration change.

## 5. Process layout, source and interface plan (protocol scope) [prop]

**Layout choice for agent 3 (O6).**
- **a. Pool and four witness objects in one adapter process**, one state directory each. Smallest start-contract change; one crash takes all four; the runner cannot withhold one witness without a hook.
- **b. Four witness processes, supervised by the adapter** (stdin/stdout JSON lines, same strict wire layer), state directories `<state-dir>/witness-<i>/`, pids written to `<state-dir>/witness-<i>/pid`. Matches PLAN's "four independent witness workers" and gives FL-2/FL-3/F-13 a real process to stop. The runner still starts **one** adapter command. Recommended.
- Either way: one key and one state directory per witness, an exclusive `flock` per state directory, and the D50 binding on every store.

**Files** (paths differ from PLAN's `protocol/witness_pool.py` etc. because the code lives in the `hmbc_protocol` package; a PLAN file-list deviation for agent 3 to approve, like A1's QuorumLib reuse):
`hmbc_protocol/witness_state.py` (conflict store, observation/tripwire, D50 binding), `hmbc_protocol/witness_service.py` (one witness), `hmbc_protocol/witness_pool.py` (collector, section 8 of SIGNING-RULES), changes to `witness.py` (profile 3, validation rules, deterministic fields), `testtools/byzantine.py` (H1, H3, H4, H5, H6, TEST-ONLY), tests `tests/test_witness_state.py`, `tests/test_witness_pool.py`, `tests/test_byzantine.py` (+ live q=3 fixture tests), `tools/mutation_check.py` (M1-M7), vectors for the Governance type produced by agent 1 and reproduced byte-exactly here.

**Interface impact (candidate v2, needs exact ACKs, nothing changes before):** profile `repaired-f` (enum 3), Governance contract entry, four witness labels and q=3 in the deployment manifest (agent 1's R5 schema work); adapter input/output additions (witness identifier per call for H2, a `collection` evidence object in the certificate reply, a governance collection operation) with their exact error reasons, envelopes and store lifecycle in `SUCCESSOR-WIRE.md`; `exports/adapter.json` successor; the D50 binding export option (`D50-DEPLOYMENT-BINDING.md`). The frozen v1 files, the E pins and `exports/adapter.json` 7146495b.. stay untouched.

**Dependencies:** none expected. SQLite, `fcntl`, `json` are standard library; signing uses the existing `eth-account`; Foundry/Anvil unchanged. No root lock change is requested.

**Order of work after ACKs (not started):** failing tests first for the conflict store and the collector (property: no two different values signed per key; restart keeps the first choice; invalid replies never reach the certificate); then the witness rewrite; then the live q=3 fixture; then mutants; then Byzantine variants.

## 6. ACK map

| Item | Needs ACK from |
|---|---|
| This inventory and the matrix corrections (section 4) | agent 3 (owner of the matrix), agent 1 for the ledger-facing rows |
| `SIGNING-RULES.md` (conflict keys, validation duties, death predicates, numeric defaults) | agent 1 (it pins ledger fields: `KSSC.sol:153`, `DecisionVerifier` gap, Governance steps), agent 3 (model, oracle, numeric plan) |
| Layout O6 and the interface additions | agent 3 |
| D50 binding | agent 1 (D-f inputs), agent 3 (evaluator impact) |

Silence is not agreement. No code, interface or production byte is changed by this document.
