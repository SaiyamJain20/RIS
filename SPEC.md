# HMBC E/F/G research specification

Status: executable research design proposed on 2026-10-06. The user selected E/F/G, HMBC-only scope, three concurrent agents, sequential RQ completion and the main checkout. The implementation choices below are explicit project choices; they are not attributed to HMBC or presented as completed results.

## 1. Research questions and order

| Order | Direction / RQ | Answer the project must produce |
|---|---|---|
| 1 | **E / RQ1:** Which authorization, trust-anchor freshness and audit properties follow from HMBC's specified access flow, which depend on missing details, and which explicit repairs enforce them in a reconstruction? | A source-to-property table; executable positive/negative traces for three case families; repair comparisons; a bounded statement of what was proved or tested. |
| 2 | **F / RQ2:** With Byzantine stakeholders, relay and witnesses, which RQ1 guarantees survive under stated ledger/key-service assumptions, and what quorum and state rules are sufficient in our extension? | A component-by-component trust matrix; threshold boundary experiments; governance/decision state models; safety and availability results with explicit failure bounds. |
| 3 | **G / RQ3:** What confidentiality remains after revocation, joining and later key compromise, and which guarantees can an explicit epoch/ciphertext lifecycle provide? | A precise secrecy matrix, an implemented lifecycle and compatible cryptographic adapter, positive/negative decryption experiments, and qualified formal/measurement evidence. |

The old plan's DP RQ1–RQ3 are archived and do not apply. These are three new RQs for the selected E/F/G scope.

E provides the request identifiers, authorization checks and test harness used by F. F specifies whose approval may release a key, which G consumes. G comes last because correct lifecycle claims depend on actual ciphertext policies, retained keys and compromise timing. Starting G with `SA@epoch` alone would repeat the earlier unsupported guarantee.

Alternatives considered: G first blocks on cryptographic reconstruction before a usable harness exists; F first encourages building a consensus system before specifying the access decision it must protect. E → F → G offers the earliest independently reportable RQ.

## 2. Baseline and evidence discipline

Build a **paper-derived reconstruction**, not a claimed reproduction of unavailable original source. Extract each relevant passage into `evaluation/evidence/source-map.csv` with PDF page/section, paraphrase, property, ambiguity and implementing fixture. No JANUS source or finding is admissible as HMBC evidence.

Use separate configurations:

- `paper-strict`: honor the paper's named actuators, GID possession, signed own-authority trust updates, long-term-plus-temporal policy and secure-isolation assumption. Fill missing authentication details conservatively and record every fill.
- `paper-minimal`: a documented minimal completion of a particular missing detail. For example, an authorized relay forwards a tuple without cryptographic source-decision binding. Preserve specified caller restrictions; never make everything publicly callable merely to obtain a failure.
- `repaired-e`, then `repaired-f`, then `repaired-g`: cumulative project extensions. Keep the E report's frozen configuration runnable after F/G are added.
- `mutant-*`: a deliberate check removal used to show that the tests/model can detect a problem. A mutant failure is not evidence that HMBC implements that mutation.

Every result is one of `SUPPORTED`, `SPEC_GAP`, `RECONSTRUCTION_FAILURE`, `REPAIR_SUPPORTED`, `REFUTED`, `BLOCKED`. Record the profile and assumptions. Several profiles may be consistent with underspecified prose; report that dependency. A negative result can answer an RQ. Do not force a minimum number or severity of vulnerabilities.

## 3. Smallest useful system

Start with one PBC and one Hospital DBC on separate Anvil instances. Four synthetic hospital organizations H1–H4 each act as independent credential/ABE authorities and logical stakeholders. Alice is a doctor at H1; Bob has no doctor role; P1/P2 and their records are synthetic. Use cross-hospital data ownership where needed. This exercises one populated HMBC domain; it does not validate multi-domain scaling.

PBC roles: **RSC** registration/GID mapping; **TMSC** credentials, revocation and temporal status; **PSC** access orchestration; **LSC** request/outcome evidence. DBC roles: **ACSC** policy enforcement; **KSSC** key-service authorization and receipt state. Minimal implementations cover the selected access flow, not every paper feature.

An off-chain key worker holds secrets and performs the simulated/real partial-decryption step. Contracts hold commitments and authorization state, never production secrets. This is an explicitly different realization of HMBC's assumed isolated KSSC execution. A separate synthetic-storage experiment may demonstrate the consequence of relaxing that isolation; it cannot refute a theorem that assumes isolation.

Default stack: Solidity with Forge/Anvil; Python for client, relay, witnesses and experiments; ProVerif for E protocol correspondence; TLC for finite F/G state exploration; a separately isolated ABE backend for G. E/F can use an explicitly tagged symbolic decryptability adapter. **G cannot claim measured ABE secrecy/performance using that adapter.**

E0 records exact tool/library/compiler versions and lockfiles after a compatibility smoke test. The inspected host has Python 3.13.13, Node 24.15.0 and Java 21; Forge, Anvil and ProVerif were absent. These observations do not establish compatibility or resource availability. No fixed RAM, cloud access, team deadline or eight-week promise is assumed.

## 4. E: properties and first case families

| Case | Property / fixture | Baseline distinction and repair target |
|---|---|---|
| **E01 Decision provenance and replay** | Each grant must bind the same subject, data, destination, action, policy version, nonce and decision approved at the PBC. Try valid relay, forged tuple, wrong subject/data/chain/contract, replay and expiration. | Fig. 6 forwards verified attributes; complete source authentication is unspecified. Compare strict/minimal completions. Repair with user signatures, independently checked decision attestations, destination binding and durable nonce consumption. |
| **E02 Trust-anchor freshness** | Replay an older correctly signed CRL/TempACL after a newer one; try wrong-issuer updates, expired duty, and delayed decision delivery across revocation. | The paper specifies signed trust lists and latest references. Version/expiry/finality details require a chosen completion. Repair with monotone authority versions, bounded validity and epoch checks at consumption. |
| **E03 Audit correspondence** | Successful release has a preceding DBC authorization record tied to the same request. Drop/duplicate/reorder the PBC outcome receipt; retry after a crash. | Preserve Table 2's request logging. Run hash-only and complete-details interpretations; neither automatically proves delivery. Repair by durable intent, DBC grant evidence and explicit pending reconciliation. |

E uses one named honest decision witness; it is a trusted-service assumption, not decentralized assurance. F replaces that profile with four witnesses. E tests relay/user attacks; witness/host compromise is a labelled stress experiment for F.

Define these events distinctly: `REQUEST_LOGGED`, `PBC_DECIDED`, `DBC_AUTHORIZED`, `RELEASE_INTENT`, `RELEASE_SENT`, `OUTCOME_RECORDED`. A ledger grant means permission to release, not proof of actual delivery. Key-worker intent is durable before transmission. Retries return the same cached response for the same authorized operation, rather than generating a second capability. A crash can leave an intent whose delivery is unknown; report that state honestly.

For an untrusted relay that drops outcomes, only **local durable evidence** is unconditional under the trusted-worker assumption. Eventual PBC reconciliation requires eventual delivery and an honest reconciler. Do not promise instantaneous atomic logging across chains and an off-chain network send.

## 5. F: extend the fault model after E closes

Use **four application decision witnesses, threshold q=3, fault bound f=1**. Each represents one logical hospital and signs with its own off-chain key after independently checking the same accepted PBC decision and current state. The relay has no witness key. The certificate contains distinct signers, a witness-set version and action/request/state bindings.

This layer authenticates decisions; it is not a newly implemented consensus protocol. The core experiment assumes safety of the source/destination ledgers and reports that assumption. Anvil is a deterministic local execution environment. A later four-validator Besu/QBFT experiment is optional and must be identified as a different consensus choice from HMBC's unspecified PoS.

Required fault cases: relay forgery; one equivocating witness; one refusing witness; duplicate signatures; stale certificate; stale witness set; reordered trust updates; a split/replayed decision view; compromised key-worker host; and thresholds outside the promised bound. With f=1, three honest witnesses can proceed after eventual message delivery. With two unavailable witnesses, availability may fail. With two Byzantine witnesses, the one-fault safety proof no longer applies; include an explicit divergent-view certificate experiment to expose that boundary.

An honest witness signs at most one conflicting decision for a `(requestDigest, witnessSetVersion)` key and persists that choice before returning its signature. Honest witnesses must check policy/state themselves; blindly countersigning the relay's proposal defeats the threshold argument.

Authority membership changes require an action-specific q=3 authorization under the **old** witness set. In the first implementation the four witness identities stay fixed; removing a credential authority is not removing a validator. Dynamic witness rotation, if later included, requires an explicit joint/overlap transition protocol and a separate decision. Do not implement it by silently resetting the set.

The trust matrix must include PBC ledger, DBC ledger, relay, witness keys, credential authority, key worker, client and data store. A compromised key worker/authority may bypass key-release policy despite correct quorums; demonstrate or classify the residual. Retaining this explicit trusted component is a valid research limitation. No threshold ABE, DKG, TEE or claim of host-compromise confidentiality is smuggled into F.

## 6. G: meanings of secrecy and the lifecycle to test

Do not use “forward/backward secrecy” without the following qualifier:

| Property | Required experiment / permitted conclusion |
|---|---|
| **Future-data exclusion after revocation** | A user revoked before epoch e+1 cannot decrypt freshly encrypted e+1 data using all retained e credentials, ciphertexts and partial decryptions. |
| **History exclusion for a new member** | A user joining at e+1 cannot obtain/decrypt e data under the project's explicit no-history policy, without credentials/outputs obtained before joining. This is a project policy, not a requirement inferred from HMBC. |
| **Past-data confidentiality after later key compromise** | Test each exposed key class separately. If a retained authority master secret or logged partial decryption recovers old data, report failure. Do not label ordinary revocation as cryptographic forward secrecy. |
| **Cached plaintext / previously usable decryption output** | Expected to remain usable. Cryptography cannot recall plaintext already learned. This negative control must pass. |

First reproduce a source-mapped static LW-style policy and HMBC's two-step decryptability using a reviewed reference adapter. G0 must identify the exact scheme, group parameters, GID binding, key ownership, output format and composition argument. Do not assume any library named “MA-ABE” implements that protocol. Do not implement new pairing algebra from prose to meet a deadline.

Proposed repair experiment: fresh per-record data-encryption keys, authenticated payload encryption, and an ABE wrapper with an explicit epoch-qualified mediating attribute conjoined with the ordinary policy. **Fresh ciphertexts and their policy/wrapper change for new epochs.** Old wrappers remain old; changing an attribute name alone is not an update operation. The attribute authority for each leaf is recorded, including the data custodian's mediating attribute. Avoid a branch that a single unintended authority can satisfy alone.

G0 selects the exact adapter and writes `protocol/crypto/DESIGN.md` with source passages and working vectors before this construction is implemented. If the primitive cannot support the selected composition, the proposed repair is BLOCKED; implement a documented alternative only after an interface/design revision. E/F reports remain complete. A toy adapter or a boolean policy check cannot close G's real-cryptography gate.

Lifecycle: `ACTIVE(e)` → `PREPARING(e+1)` → `COMMITTED(e+1)` → `RETIRED(e)`. Preparation creates fresh key material and a public commitment off chain. Commitment binds key/policy/auth epochs using F's decision authorization. No new-epoch release before commitment. Requests with stale epochs fail closed; partial rollout causes unavailability, not fallback to old authorization. Key-worker recovery is durable and idempotent. The G experiment uses explicit retention/erasure configurations for old material. Deleting an application file is not proof of physical erasure or absence from backups.

No retroactive re-encryption of all history is required for the first future-data experiment. If historical ciphertext migration is evaluated, it is a separate measured operation with an explicit source/destination policy and integrity binding. Do not promise revocation of already obtained ciphertext plus sufficient old keys.

## 7. Common experiment rules

- Configuration is explicit: fixture identities, policies, authority ownership, profile, versions, epochs, fault schedule and adapter mode. No hidden environment default affects an experiment.
- Correctness suites are deterministic. Performance: 10 warmup operations and 30 measured repetitions per case, seeds 0–29 for synthetic schedules; report failures/timeouts as well as successful latencies. Timings do not use deterministic production cryptographic randomness.
- Measure success/denial classification, replay count, stale-state rejection, audit reconciliation, gas, encoded message bytes and per-stage wall time. G additionally measures encryption, partial/final decryption, rotation cost and retained material. No throughput or production resilience claim follows from cohosted local processes.
- Gate reports contain the source/version, exact command, input hash, tool versions, output hash, exit code and commit plus dirty-tree/source manifest. A commit hash alone misses concurrent uncommitted changes.
- Security invariants need meaningful mutants and legitimate controls. A repaired implementation that denies every request fails.
- Source excerpts, formal model limits and measurements stay separate. Model success with bounded state space or ideal cryptography is scoped accordingly.
- Formal checks must include negative controls: a weakened binding or quorum should falsify the claimed invariant. A vacuous model with no grant path fails the gate.

## 8. Interfaces, ownership and completion

The normative v0 contract is [interfaces/README.md](interfaces/README.md). It becomes v1 only after all three agents acknowledge identical vectors and field definitions in E0. Cross-module imports must use that contract, not another module's internals.

Each module can be tested with contract-conforming stubs. Each RQ then receives a real integration run controlled by agent 3. Stub-only success cannot close a gate. `communication/GATES.md` records exact evidence and all three agents' acknowledgements. A task marked BLOCKED cannot silently become passed when another agent finishes.

Core F/RQ2 makes conditional claims about decision/governance behavior under safe ledgers and a stated key-service trust boundary. Core G/RQ3 requires actual compatible cryptography for its implemented secrecy experiments. Both limits must appear in their final answers.
