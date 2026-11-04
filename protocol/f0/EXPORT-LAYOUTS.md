# Exact layouts of the read-only evidence exporters (agent 2) — for review

Author: agent 2. Date: 2026-11-04 (revision 8 of the F0 set; answers item 4 of A3-0066 and the layout part of A2-0054). **PROPOSAL, NOT ACKED, NOT IMPLEMENTED, NOT FROZEN.**
Paper-derived reconstruction, synthetic fixtures, symbolic payloads. Claim classes: **[prop]** proposal, **[src]** read from source, **[untested]** nothing here has run against a real store. `hmbc_protocol.witness_state` does not exist yet; these are the layouts its read-only commands must print.
The reference and checker are `vectors/export_layouts_reference.py`; the expectations are `vectors/test_export_layouts.py` (written first; 62 expectations after the mutation-driven hardening); the vectors are `vectors/export_layouts_vectors.json`; the mutation record is `evidence/export-layouts-mutants.txt` (24 of 24 detected, `vectors/run_export_layout_mutants.py`). **The digests and signatures in the vectors are well-formed placeholders, not recovered signatures**; the invariants below do not need recovery, and anything that does (a signature recovering to the witness) stays a runner obligation.

## 1. Commands and the output contract [prop]

| Command | Reads | Prints (section) |
|---|---|---|
| `python -m hmbc_protocol.worker_log --state-dir D --binding` | `<D>/worker/` | the binding export (2) |
| `python -m hmbc_protocol.witness_state --state-dir D --witness-index I --binding` | `<D>/witness-<I>/` | the binding export (2) |
| `python -m hmbc_protocol.witness_state --state-dir D --witness-index I --evidence` | `<D>/witness-<I>/` | the evidence document (3) |

All three are **read-only** (SUCCESSOR-WIRE section 5: one read transaction through a WAL-aware `mode=ro` connection, never `immutable=1`; the committed state is main file plus `-wal` plus the `INITIALIZED` marker), make **no RPC** (D50 section 3, "Other commands"), print **no key material**, and are **not adapter operations** (not in `adapter.json`). `worker_log` without `--binding` is unchanged byte for byte. `--witness-index` is `0..3` (`0` only for a carried E deployment).
- **Success:** exit 0; stdout is **one line**: the canonical JSON of the document (`json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=True)`) followed by exactly one LF; stderr empty.
- **Refusal:** exit 3; stdout empty; stderr is one line, the canonical JSON of `{code, message, reason}` (the successor `Error` members) followed by one LF. An exporter reads the store only, so it can refuse only: `STORE_MISSING` (no database and no marker, or a database without the `INITIALIZED` marker and without rows: initialisation never completed), `STORE_CORRUPT` (failed `integrity_check`, rows without the marker, a marker whose `binding_v2` or `owner` differs from the database's, or missing binding rows next to a marker), `LEGACY_STATE` (a database with rows and no binding rows: an unbound E store). Codes: `ADAPTER_UNAVAILABLE`, `ADAPTER_UNAVAILABLE`, `WRONG_DESTINATION` (the table of SUCCESSOR-WIRE section 1). Any other reason is a defect of the exporter. Usage errors are exit 2 (argparse).

## 2. The `--binding` export [prop]

Exactly four members and nothing else (D50 section 5, "old-state migration and refusal"): `{owner, binding_v2, document, anchor}`.

| Member | Value | Rule |
|---|---|---|
| `owner` | `"worker"` or `"witness:0x<40 lowercase hex>"` | one store, one role; outside `B` |
| `binding_v2` | 64 lowercase hex, no `0x` | **equals** `sha256("hmbc-deployment-binding/v2\n" ‖ canonical_json(document))` |
| `document` | `B`, the D50 closed binding document | valid under the D50 reference (`d50_reference.validate`, revision 5) |
| `anchor` | `{pbc: {number, hash}, dbc: {number, hash}}`, closed | `number` a decimal string, `hash` `0x` + 64 lowercase hex: the pinned block at which the live fields were read, so an observer can recompute at the same block; not part of `B`; `anchor.<chain>.number >= document.chains.<chain>.deployBlock.number` |

## 3. The `--evidence` document (witness stores only) [prop]

Top level, closed, in this set of members: `schemaVersion` (`"hmbc-witness-evidence/v2"`), `owner` (`"witness:0x…"`, never `"worker"`), `binding` (`{binding_v2, document}`, same rules as section 2), `marker` (`{binding_v2, owner, schema}`, the `INITIALIZED` marker content; must equal the binding, the owner and `schema` `"2"`), `observations`, `faulted`, `faultLog`, `conflicts`, `superseded`, `evidenceSha256`.
- **`observation`** (everywhere): `{chainId, blockNumber, blockHash, timestamp}`, decimal strings and a `0x` hash (SIGNING-RULES section 6). **`observations`** is the **last stored observation per chain**: one per chain, ascending numeric `chainId`, only the chains of the binding; it must contain the target chain of every recorded type.
- **`conflicts`**: the live record for each conflict key `K = (type, domainSeparator, witnessSetVersion, keyField)`, **sorted** by (type order `AccessDecision`, `StateCheckpoint`, `GrantReceipt`, `GovernanceAction`; `domainSeparator`; numeric `witnessSetVersion`; key, numerically for decimal keys), at most one per `K`. A record is `{type, domainSeparator, witnessSetVersion, keyField, effect, vHash, digests}`.
  - `keyField`: decimal for `StateCheckpoint` (`sequence`) and `GovernanceAction` (`nonce`); `0x` + 64 hex for `AccessDecision` and `GrantReceipt` (`requestDigest`).
  - `effect` is **V**, closed per type: every signed field **except the key field and the liveness field** (SIGNING-RULES section 1; for the receipt row, "all fields" is read as all fields but the key). `StateCheckpoint`: `authEpoch, policyVersion, keyEpoch, witnessSetVersion, sourceChainId, psc, sourceBlockNumber, sourceBlockHash`. `AccessDecision`: `result, credentialDigest, stateSequence, witnessSetVersion, sourceBlockNumber, sourceBlockHash`. `GrantReceipt`: `grantId, gid, dataId, keyEpoch, grantExpiresAt, witnessSetVersion, dbcChainId, kssc, dbcBlockNumber, dbcBlockHash`. `GovernanceAction`: `action, root, admins, witnessSetVersion`. Value types are those of the v1 message definitions; `effect.witnessSetVersion` must equal the record's `witnessSetVersion`.
  - `vHash` = lowercase `sha256` of the canonical JSON of `effect`.
  - `digests`: at least one, sorted by (`expiresAt`, `digest`); each `{digest, signature, observation}` plus **`expiresAt`** (decimal) for every type with a liveness field and **absent** for `GrantReceipt`. `digest` is `0x` + 64 hex, `signature` is `0x` + 130 hex (the signature the witness already issued, deterministic RFC 6979), `observation` is the one taken when it signed, **of the target ledger of the type** (DBC for decision and checkpoint, PBC for governance and receipt).
- **`superseded`**: the append-only history, numbered `seq` `"1".."n"` in append order, each a record **plus** `seq` and `death`. `death` is `{kind, observation}` plus **`observed`** (decimal) **exactly** for the three numeric kinds. Kinds and what the checker verifies (SIGNING-RULES section 6):

| `kind` | type | `observed` | verified |
|---|---|---|---|
| `expiry` | decision, checkpoint, governance | absent | `observation.timestamp >=` the latest `expiresAt` of **every** digest of the record |
| `overtaken-checkpoint` | checkpoint | `DBC current.sequence` | `observed >= keyField` |
| `overtaken-governance` | governance | `governanceNonce` | `observed >= keyField` |
| `overtaken-decision-sequence` | decision | `DBC current.sequence` | `observed > effect.stateSequence` |
| `overtaken-decision-grant` | decision (ALLOW only) | absent | the type only: that a grant exists is a ledger fact the layout cannot show |
| `executed-receipt` | receipt | absent | the type only: that the PSC request is `OUTCOME_RECORDED` is a ledger fact |

  The death `observation` is of the target ledger of the type. **A superseded effect must differ from the live effect for the same `K`** (otherwise it is not a supersession).
- A **digest occurs once in the whole store** (live and superseded).
- **`faulted`**: `null`, or `{reason, previous, observed}` with `reason` in `number-regression` (`observed.blockNumber < previous.blockNumber`), `timestamp-regression` (`observed.timestamp < previous.timestamp`), `hash-changed` (same `blockNumber`, different `blockHash`); `previous` and `observed` are of one chain, and `previous` **equals the stored last observation** of that chain (a regression is not adopted).
- **`faultLog`**: the append-only clears, numbered `"1".."n"`, each `{seq, fault, clearedAgainst, note}`: `fault` as above, `clearedAgainst` an observation of the same chain as `fault.observed` and not later than the stored last observation of that chain (it became the new baseline), `note` a non-empty string. **A clear never deletes or rewrites `conflicts` or `superseded`** (SUCCESSOR-WIRE section 4).
- **Monotonicity.** When the store has **no** fault and **no** fault-log row, no recorded observation (in any digest or death) may exceed the stored last observation of its chain in number or timestamp, and an equal number needs an equal hash. A store with a fault or a clear is **explicitly outside the safe-ledger assumption for that interval** and the rule is not applied; the evidence must still say so, and a consumer must label the run.
- **`evidenceSha256`**: lowercase `sha256` of the canonical JSON of the document **without** this member. It is a **fingerprint for before/after comparison of the evidence** (a refusal must leave it unchanged); it is **not authentication**, and it is not the logical-snapshot hash of SUCCESSOR-WIRE section 5, which the test harness computes over the SQLite rows and marker bytes.

**New storage obligations this layout implies (the witness would have to record them; please read this as part of the proposal, not as an accepted fact):** the `observed` value of the numeric death kinds and the per-digest observation, which SIGNING-RULES section 2 already requires for the observation and section 6 implies for the death. Nothing here asks the witness to store a wall-clock time.

## 4. What the layouts do not claim, and what stays a runner obligation

- No signature is recovered here. That each `signature` recovers to the owner over the HMBC domain, that `digest` is the EIP-712 digest of the stated message, that the `observation`s match the chain, and that `death` facts are true on the ledger are **runner obligations**, as in BOUNDARY.
- The checker is internal consistency of one document and ordering/uniqueness rules; it cannot show that the store holds nothing else, and a consistent document can still come from a wrong store. The evaluator joins the document with anchored observations; it does not trust `evidenceSha256` or `binding_v2`.
- The vectors are synthetic. Nothing here ran against a real SQLite store, a real chain or a real witness, and `witness_state` does not exist.
- The successor schema must carry these layouts as separate closed definitions (the two documents are not adapter responses); a JSON Schema cannot express the sorting, uniqueness, hash and death rules, which stay here and in the checker.
