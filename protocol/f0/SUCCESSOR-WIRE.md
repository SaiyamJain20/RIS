# F0 successor wire, error and store-lifecycle definitions (agent 2) — for review

Author: agent 2. Date: 2026-11-04 (revision 3 input, answers A3-0058 items 2 and 3). **PROPOSAL, NOT ACKED, NOT IMPLEMENTED, NOT FROZEN.**
The frozen v1 files, the E pins and `exports/adapter.json` (7146495b..) are untouched. Agent 3 owns the successor schema; this document is what I propose it contains for the protocol side.
Claim classes: **[prop]** proposal, **[src]** read from source, **[untested]** nothing here has run. Every example below is **illustrative**, not output of a run.

## 1. Error vocabulary: reasons on existing codes (option E1, recommended) [prop]

v1 `Error` is closed: `{code, message}` with 21 codes (`hmbc.schema.json` `$defs/Error`). `CONFLICT` and `QUORUM_UNAVAILABLE` (named in SIGNING-RULES) are **internal reasons**, not new codes:

- **E1 (recommended):** the successor `Error` gains two optional members, `reason` (a closed enum) and, for collection failures only, `collection` (section 3). `code` stays one of the 21 v1 values; consumers that ignore `reason` keep working.
- **E2 (alternative):** new top-level codes. This widens the shared vocabulary that the ledger's `ErrorCode` enum also uses, and either leaves the two enums inconsistent or forces a ledger change. Not recommended.

Why `INSUFFICIENT_QUORUM` is **not** reused for "the collector never obtained three signatures": that code means *the ledger rejected a submitted certificate* (it is already listed in `collect_decision`'s errors and in `QuorumLib`). A collector timeout means *no certificate was ever submitted*. An oracle must tell FL-3 (two witnesses down, nothing submitted) from a ledger rejection (FL-4/FL-5/F-23), so the timeout is `ADAPTER_UNAVAILABLE` with reason `QUORUM_UNAVAILABLE` and the per-witness evidence. A missing quorum is therefore never `POLICY_DENIED` and never a success.

| `reason` | `code` | Meaning |
|---|---|---|
| `CONFLICT_PINNED` | `STALE_STATE` | the witness's record for the conflict key holds a different effect value that is not yet dead (SIGNING-RULES section 2) |
| `PROPOSAL_MISMATCH` | `STALE_STATE` | the proposal differs from the witness's own derivation; the message names the field |
| `QUORUM_UNAVAILABLE` | `ADAPTER_UNAVAILABLE` | the collection deadline passed with fewer than q distinct valid signers; carries `collection` |
| `WITNESS_FAULTED` | `ADAPTER_UNAVAILABLE` | the witness's tripwire is set (section 4) |
| `LEDGER_UNREACHABLE` | `ADAPTER_UNAVAILABLE` | RPC failure while reading the ledger (today's behaviour, now named) |
| `STORE_MISSING`, `STORE_CORRUPT` | `ADAPTER_UNAVAILABLE` | the store is missing next to its marker, or fails its integrity check |
| `PROFILE_MISMATCH` | `WRONG_PROFILE` | manifest profile/enum differs from the contracts' `profile()` |
| `UNSEALED`, `WIRING_MISMATCH`, `GENESIS_MISMATCH`, `CODE_MISMATCH`, `MUTATIONS_MISMATCH`, `BUILD_MISMATCH` | `WRONG_DESTINATION` | D50 identity/build/wiring checks (D50 section 3) |
| `LEGACY_STATE`, `BINDING_MISMATCH`, `OWNER_MISMATCH` | `WRONG_DESTINATION` | the store belongs to another deployment, role or key, or is an unbound E store with rows |
| `BUILD_PIN_INVALID` | `MALFORMED` | the trusted build pins (immutable ranges, runtime length) are themselves malformed |
| `WITNESS_SET_MISMATCH` | `STALE_STATE` | set, threshold or version differs from the manifest, or PSC/KSSC/Governance disagree |

A key that is not a member of the sets stays `UNKNOWN_AUTHORITY` (`witness.py:39`, no reason). Validation refusals that already have a v1 code (`EXPIRED`, `REPLAY`, `WRONG_EPOCH`, ...) are unchanged and need no reason.

**Precedence at open (first failing wins).** Steps 1-8 read the ledger only and **touch no store**; step 9 uses a read-only connection and the marker file:
1 `LEDGER_UNREACHABLE`; 2 `PROFILE_MISMATCH`; 3 `BUILD_PIN_INVALID`; 4 `UNSEALED`; 5 `WIRING_MISMATCH`; 6 `GENESIS_MISMATCH`; 7 `CODE_MISMATCH`, `MUTATIONS_MISMATCH`, `BUILD_MISMATCH`; 8 `WITNESS_SET_MISMATCH`, then `UNKNOWN_AUTHORITY` (witness stores only);
9 `STORE_MISSING`, `STORE_CORRUPT`, `LEGACY_STATE`, `BINDING_MISMATCH`, `OWNER_MISMATCH`, then `WITNESS_FAULTED`. The checks that need no store run first so that a refusal before step 9 cannot have modified one.

## 2. Operations (successor shapes) [prop]

Envelope: as v1 with `schemaVersion: "v2"`; `ok`, `result`, `error` unchanged. Integers are decimal strings, as in v1. `adapterMode` stays `"symbolic"`.

| Operation | v2 change |
|---|---|
| `collect_checkpoint`, `collect_decision`, `attest_grant` | input gains optional `witnessIndex` (`"0".."3"`). Without it the adapter runs the **pool collection** and returns q signatures plus `collection`. With it, one witness answers (single-witness mode, for the runner's crafted certificates FL-4, FL-5, FL-6, F-23). `witnessSetVersion` is `"2"` under repaired-f. The caller still never supplies a sequence, timestamp or source block: unknown fields reject |
| `collect_governance` (new) | input is the **whole proposed action**, because a governance action comes from an operator decision, not from ledger state: `{action, root, admins, nonce, witnessSetVersion, expiresAt, witnessIndex?}`. Output: `{governanceAction, signatures, collection}` |
| `prepare_request`, `release`, `encrypt_record`, `finish_decryption`, `rotate_epoch` | unchanged |

Pool-mode success (witness 2 returned an invalid signature and was filtered; the certificate holds exactly q = 3 signatures sorted by signer address):

```json
{"schemaVersion":"v2","ok":true,"result":{"schemaVersion":"v2","adapterMode":"symbolic","checkpoint":{"sequence":"4","authEpoch":"3","policyVersion":"1","keyEpoch":"0","witnessSetVersion":"2","sourceChainId":"18545","psc":"0x1613beb3b2c4f22ee086b2b38c1476a3ce7f78e8","sourceBlockNumber":"250","sourceBlockHash":"0x5555555555555555555555555555555555555555555555555555555555555555","expiresAt":"1791521500"},"signatures":["0xaaaa","0xbbbb","0xcccc"],"collection":{"quorum":"3","witnessSetVersion":"2","outcomes":[{"witnessIndex":"0","witness":"0x1000000000000000000000000000000000000001","status":"signed","replies":"1"},{"witnessIndex":"1","witness":"0x2000000000000000000000000000000000000002","status":"signed","replies":"1"},{"witnessIndex":"2","witness":"0x3000000000000000000000000000000000000003","status":"invalid","replies":"1","detail":"signature does not recover to the replying witness"},{"witnessIndex":"3","witness":"0x4000000000000000000000000000000000000004","status":"signed","replies":"2"}],"submittedSigners":["0x1000000000000000000000000000000000000001","0x2000000000000000000000000000000000000002","0x4000000000000000000000000000000000000004"]}},"error":null}
```

Collection failure (two witnesses refused or silent; **no certificate was submitted**):

```json
{"schemaVersion":"v2","ok":false,"result":null,"error":{"code":"ADAPTER_UNAVAILABLE","reason":"QUORUM_UNAVAILABLE","message":"2 of 3 required distinct valid signatures before the deadline","collection":{"quorum":"3","witnessSetVersion":"2","outcomes":[{"witnessIndex":"0","witness":"0x1000000000000000000000000000000000000001","status":"signed","replies":"1"},{"witnessIndex":"1","witness":"0x2000000000000000000000000000000000000002","status":"refused","replies":"1","code":"STALE_STATE","reason":"CONFLICT_PINNED"},{"witnessIndex":"2","witness":"0x3000000000000000000000000000000000000003","status":"signed","replies":"1"},{"witnessIndex":"3","witness":"0x4000000000000000000000000000000000000004","status":"silent","replies":"0"}],"submittedSigners":[]}}}
```

Single-witness refusal (tripwire set):

```json
{"schemaVersion":"v2","ok":false,"result":null,"error":{"code":"ADAPTER_UNAVAILABLE","reason":"WITNESS_FAULTED","message":"witness 1 refuses to sign: ledger clock regression observed"}}
```

Open refusal (a mutant deployment on addresses an honest store was created for):

```json
{"schemaVersion":"v2","ok":false,"result":null,"error":{"code":"WRONG_DESTINATION","reason":"BINDING_MISMATCH","message":"this store was bound to a different deployment"}}
```

`collection` rules: `outcomes` has exactly one entry per witness index, in index order. `status` is one of `signed`, `refused`, `invalid`, `silent`, `dissent`, `duplicate-only` (no valid first reply). `replies` counts every reply received from that witness; duplicates never add to the count of signers. A `refused` entry carries `code` and, when one exists, `reason`. `submittedSigners` is empty on failure and has exactly `quorum` addresses on success. The collection deadline and the per-witness reply timeout are **start-contract parameters with no default proposed here**: finite budgets belong to agent 3's numeric plan (A3-0058). A deadline can only be shorter than the proposal's remaining validity; eventual delivery after expiry does not rescue the operation.

Where `witnessIndex` lives (production boundary or only a TEST-ONLY wrapper) is agent 3's decision. It exposes one witness's signature, which the pool already produces internally; under public synthetic keys it grants nothing that the harness cannot already do.

## 3. Evidence export for witness stores [prop]

Like `worker_log` for the worker: `python -m hmbc_protocol.witness_state --state-dir D --evidence` opens the store **read-only** and prints the conflict records, digests, `superseded` history with its death evidence, the last observation per chain, the fault log and the binding (`--binding` as in D50). It is not an adapter operation and not listed in `adapter.json`. Raw signatures are not secrets; no key material is ever printed.

## 4. Tripwire: FAULTED response and recovery [prop]

Entered when, for a chain a signing operation reads, `latest.number` or `latest.timestamp` is **lower** than the last stored observation, or the hash stored for the last observed number changed (SIGNING-RULES section 6).

- **Persisted first.** The witness writes `faulted = {reason, previous observation, new observation}` to its store before answering; a restart stays FAULTED. If that write fails it still refuses.
- **Response.** Every signing operation answers `ADAPTER_UNAVAILABLE` / `WITNESS_FAULTED` until cleared. Read-only evidence export keeps working.
- **Clear.** An explicit operator command, `python -m hmbc_protocol.witness_service --state-dir D --clear-fault --note TEXT`. It **never deletes or rewrites signing history**: conflict records, digests and `superseded` rows stay; it appends a row to an append-only `fault_log` (old fault, the observation it was cleared against, the note) and sets the new observation baseline to the chain's current `latest`.
- **Scope of the claim.** A run that contains a clear is **outside the safe-ledger assumption for the interval it covers**. Evidence must say so; a clear does not turn a regression or reorganisation into an in-scope safety result, and digests recorded before the fault keep their earlier expiries (they are dead only by the ordinary rule, observed on the new baseline).

## 5. Store lifecycle and crash ordering [prop]

Two stores, two owners (D50 section 3): the worker store (`<state-dir>/worker/`, `owner = "worker"`, **no key and no membership check**) and each witness store (`<state-dir>/witness-<i>/`, `owner = "witness:0x<address>"`, membership in PSC, KSSC and Governance required).

**Initialisation (fresh directory), in this order; signing is allowed only after step 5:**
1. create the directory (mode 0700) and take `flock` on `.init.lock`;
2. compute and verify the binding (section 1, steps 1-8) **before creating any file**;
3. create the database, schema and `meta` rows (`binding_v2`, `binding_v2_doc`, `owner`, `schema`) in one transaction; commit (`synchronous=FULL`);
4. write `INITIALIZED.tmp` containing `{binding_v2, owner, schema}`, fsync, rename to `INITIALIZED`, fsync the directory;
5. release the lock.

**Crash points and what a restart does:**
| Crash after | State on disk | Restart |
|---|---|---|
| 1 or 2 | no database, no marker | initialise again |
| 3 | database with binding rows and **no** record rows, no marker | complete step 4 (nothing can have been signed: signing needs the marker) |
| 4 before the rename | as above plus `INITIALIZED.tmp` | delete the temp file, complete step 4 |
| the rename | marker present | normal open |
| any, but record rows exist and the marker is missing | impossible by the ordering | `STORE_CORRUPT`, refuse |

**Open of an existing store:** steps 1-8, then read the marker file and open the database **read-only** (`mode=ro`, as `worker_log.py` does) to check `integrity_check`, `binding_v2`, `owner`, `schema` and the legacy rule; only after every check passes is a read-write connection opened. **A refused open leaves the bytes of the database file and of the marker unchanged**; SQLite's side files (`-wal`, `-shm`) may appear and are not state. Controls compare the sha256 of the database and the marker before and after every refusal.

## 6. Controls this adds (test-first, none exists) [untested]

Lifecycle: kill at each of the five crash points above and check the restart column; refuse signing before the marker exists; a refused open leaves database and marker bytes identical (every reason in the precedence list); a successful reopen of the worker and of each witness; a witness store opened as another witness or as the worker; a worker store opened by a witness process; an E store with rows (`LEGACY_STATE`); a missing store next to a marker (`STORE_MISSING`); a corrupted page (`STORE_CORRUPT`).
Tripwire: regression of number, of timestamp, a changed hash; FAULTED survives restart; a clear keeps every conflict and `superseded` row and writes one `fault_log` row; a run containing a clear is labelled out of assumption in the evidence export.
Collection: invalid, duplicate, dissenting, silent and refusing witnesses (each of `signed`, `refused`, `invalid`, `silent`, `dissent`, `duplicate-only`); exactly q signatures submitted; failure submits nothing.
Source-edit mutants for `tools/mutation_check.py`: a refusal that writes the store; marker written before the database commit; signing allowed before the marker; clear that deletes history; collector that forwards an invalid signature; collector that counts a duplicate.

## 7. Open points for agent 3

E1 or E2; whether `witnessIndex` is in the boundary or a TEST-ONLY wrapper; the collection deadline and reply timeout (numbers); whether the evidence export is consumed by the evaluator; the successor schema encoding of `reason` and `collection`.
