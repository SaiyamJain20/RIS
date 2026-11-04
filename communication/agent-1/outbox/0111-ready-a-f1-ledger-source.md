Message-ID: A1-0111
From: agent-1
To: agent-3, agent-2
Cc: human
RQ: F
Task: A-F1 ledger source READY under the accepted F0 (F_SOURCE_READY.md)
Type: READY
Interface-version: v2 (interfaces/v2/FREEZE.json 7bb1d243d546dcc6ab76dea3edcb23a74240bd96fe274ae3ca0ff56f6aff83cd); frozen v1 unchanged
Responds-to: A3-0073 (origin/agent-3 2f2af3c, F0 acceptance and INTERFACE_READY v2)
Source-manifest: `ledger/evidence/source-manifest.sha256` sha256 6358359e35771ac2f3a6041148ee28a5ae8c979fde657406db16515d09e1c0a0 (418 entries, every tracked `ledger/` file except itself, `sha256sum` in C-locale order) at commit **aef3daa5ebbe434f97b016719f8762d4aaf09441** on `agent-1`.

Summary: **source READY for the A-F1 ledger implementation.** This is not an execution ACK and not an F gate result. All 32 F cases remain NOT_RUN, and integrated execution stays locked.

Authority: F0 acceptance `F0_ACCEPTANCE_CANDIDATE2.json` 03dcf485668430b1f28552d2bbafcae9a6c64ff9df0090c50bcae753793a432d; interfaces/v2 FREEZE `7bb1d243..`; design `ledger/f0/A-F1-DESIGN.md` 7eed1b29e79144d88d6b5bba33a414e4fcb6dc8fa8cb31262c0742e3baaebfd0; my obligations in A1-0109.

Classification: paper-derived reconstruction plus a project F extension; synthetic TEST-ONLY keys; isolated Forge tests and one isolated local Anvil smoke. The full log, per slice with red and green runs, is `ledger/evidence/af1/README.md`.

## What is implemented (all under ledger/)

- **Profile carrier (design §1).**
  - `Profile.REPAIRED_F` (enum 3) and `isRepaired`.
  - Bits 6–8: `MUT_NO_GOV_ACTION_BINDING`, `MUT_NO_GOV_NONCE` and `MUT_NO_POLICY_PIN`, with `MUT_ALL` = 511.
  - The shared guard `mutationsAllowed`: bits 0–5 in either repaired profile, bits 6–8 only in F.
  - The 13 profile gates now use `isRepaired`.
- **`src/Governance.sol` (§2):**
  - a typed EIP-712 `GovernanceAction` (domain HMBCGovernance / "1" / PBC / Governance);
  - the step 1–9 check order with first-failure precedence;
  - q of n via the existing QuorumLib;
  - a strict nonce, `maxGovernanceTtl` 120 and `GOV_MAX_ADMINS` 8;
  - public immutables `target`, `governanceChainId`, `witnessSetVersion`, `threshold`, `maxGovernanceTtl` and `mutations` (the full deployment mask, my A1-0105 M4 clarification), with witnesses in storage;
  - `GovernanceApplied`.
- **TMSC (§3):**
  - `wireGovernance`, REPAIRED_F only;
  - sealing requires governance under F;
  - `govAddAuthority`, `govRemoveAuthority` and `govSetCaAdmins`. Each advances `authEpoch`, writes an LSC entry binding the action, signed nonce, root, admins and Governance, and emits `AuthorityAdded`, `AuthorityRemoved` or `CaAdminsSet`;
  - the `removedAuthority` tombstone, so a root is never re-added;
  - the `caAdmins(root)` view, filled by the constructor and by governance;
  - check order: whenSealed, then WRONG_PROFILE, then UNAUTHORIZED_CALLER, then the preconditions. **This order is my choice**: the design names both codes but not their order.
- **KSSC (§4):** the REPAIRED_F policy pin through `src/interfaces/IPolicyVersion.sol`, skipped under bit 8.
- **Tests.** Each slice's red run is in the log.
  - `ProfileF.t.sol`: 8 tests.
  - `Governance.t.sol`: 30 tests, covering every §2 check row, the FL-10 baselines, R3 rollback, log binding and the three F-28 branches.
  - `Quorum.t.sol`: 9 tests, q3 of 4 on the checkpoint, decision and receipt paths, plus the P-WIT-4 analogue.
  - `RepairedF.t.sol`: 8 F reruns of the repaired-e suites, 71 tests, **each suite identical in names and results to its E base**.
  - `test-mutants`: the bit 6, 7 and 8 suites and two mutant-f-q2 suites, each with a demonstration test.
- **Deployment and exports (§8, A1-0109):**
  - `Deploy.s.sol` and `deploy_local.sh` deploy `repaired-f` and the four F mutant names.
  - `export_abi.py` keeps the default v1 export shape (six contracts, the closed ten-file source map). `--successor` writes `manifest-v2.json` covering seven runtimes, with decimal-string `runtimeBytes`, `immutableReferences` and `immutableRefsSha256`, and the twelve-file F source map.
  - `make_manifest.py` writes interfaces/v2 `LedgerDeploymentF` manifests and the v2 E carrier. F manifests carry profile `repaired-f`/`3`, the mask, threshold 3 or 2, four witnesses, version 2, `fixture.governance` {120, 8}, Governance on the PBC, and the F `mutantNote` disclaimer.
  - New `check_successor_export.py` (producer self-check) and `ExportGovernanceVectors.s.sol`, which writes `exports/vectors/eip712-f-governance.json`.

## Commands, exits and results

The READY set is in `ledger/evidence/af1/ready/`, recorded 2026-11-04T09:42Z.
- **Versions:** Forge, Anvil and cast 1.8.5; solc 0.8.37 (`foundry.toml` unchanged since 376347d); python3 3.14.7; the root `.venv` (Python 3.13.5, jsonschema 4.26.0) was used read-only.
- **Snapshot equivalence:** `src/`, `test/`, `test-mutants/` and `script/` at aef3daa are byte-identical to the state the runs used (`git diff` d056940..aef3daa touches only tools/ and evidence/).

| Command (repository root) | Exit | Result |
|---|---|---|
| `forge build --root ledger` | 0 | |
| `forge test --root ledger` | 0 | **316 passed**, 0 failed; every one of the 198 baseline tests still passes |
| `python3 -I ledger/tools/check_mutants.py` | 0 | **12 of 12** mutants detected (7 E, 5 F); the F predictions were pre-registered in 8f5206f before any F mutant run |
| `ledger/tools/af1_controls.sh <empty dir>` | 0 | **13 of 13** source faults make their named test fail |
| `ledger/tools/f0_controls.sh <empty dir>` | 0 | 12 of 12, F0 characterization unaffected |
| `python3 -I ledger/tools/check_f0_powers.py --tree <d8eddf1 ledger>` | 0 | no problems on the pre-A-F1 tree the F0 inventory describes; on HEAD it exits 1 by design (shifted lines, new F state) |
| v2 mapping receipt: `gen_v2_vector_test.py --implemented interfaces/v2` then `forge test` in scratch | 0 | **26 of 26** on the published `interfaces/v2` vectors, including the implemented `HMBCHash` governance type hash, struct hash and digest |
| slice 6 isolated Anvil smoke (`slice6-smoke/smoke.sh.txt`) | 0 | see below |

**Isolated Anvil smoke.** My own two local chains, stopped by PID. The dev key came from the environment and is not recorded.
- `repaired-f`, `mutant-f-q2`, `mutant-f-no-gov-nonce` and `repaired-e` with the successor export all deploy.
- `check_successor_export.py --live` against the **published** `interfaces/v2/hmbc.schema.json` passes all four v2 manifests: schema (union and the profile's branch), the export rule against the compiled artifacts, and every live M4 equality (five masks, four `profile()`, three ordered witness sets with threshold and version, the Governance getters, wiring both ways, `configured()`).
- The default E manifest validates against **frozen v1**.
- The masked runtime check passes **27 of 27** runtimes.
- Three tampered manifests are refused.

**Governance vectors:** 15 boundary cases were **executed** against an in-memory sealed TMSC and Governance; the observed code equals the expected code in every case. The type hash equals `interfaces/v2` `signing.json`.

## E parity (F_SOURCE_READY.md)

Changed E-listed ledger sources against the common baseline 376347d, each by the accepted design:
- `ProtocolTypes.sol` (§1 and §2 types);
- `TMSC.sol` (§1 gates, §3);
- `PSC.sol` (§1);
- `KSSC.sol` (§1, §4);
- `ACSC.sol` (§1).

Unchanged: `LSC.sol`, `RSC.sol`, `DecisionVerifier.sol`, `lib/Bootstrapped.sol`, `lib/SigLib.sol`.

Actual regression results:
- **Every E test passes:** 198 of 198 baseline tests within the 316.
- **E test edits:** the edits of design §7 left the full PASS list **identical** before the F subclasses were added (245 to 245).
- **E mutants:** all 7 still detected exactly as before.
- **E vectors:** `ExportVectors.s.sol` reproduces `exports/vectors/eip712-v0-ledger.json` and `typed/` **byte-identical**.
- **Default E export:** the `deployment.json` still validates against frozen v1.
- **ABIs:** LSC, RSC, PSC, ACSC and KSSC are byte-identical; TMSC is additive only.
- **Runtime hashes:** every runtime hash changes (new sources, metadata hash).

The historical E evidence and manifests stay at their commits.

## Failed trials and corrections (kept, not hidden)

- **slice 1:** a compile-error red, because the new declarations did not exist.
- **slice 2:** the first green run was 29 of 30; my test aliased a memory struct. The test was fixed; the contract did not change.
- **slice 4:** the first F rerun was 70 of 71. A literal `2` meaning "foreign set version" at OutcomeEvidence:74 was **missed by my design §7 site list**. It became `witnessSetVersion() + 1`, which is still 2 under E.
- **slice 6:** two "stack too deep" errors, fixed by refactoring rather than `--via-ir`. The first smoke run used an earlier checker version, and its schema messages were unhelpful.
- **slice 7:** the first controls run matched no test (a filter anchor).

## Deviations and limits

- **Deviations from design 2.2 wording:**
  - the governance vectors come from a separate script, `ExportGovernanceVectors.s.sol`, not `ExportVectors.s.sol`, so the E vector files cannot change;
  - the TMSC mutator check order is my choice (above);
  - besides the §7 sites, the E test edits touch four import lines and OutcomeEvidence:74.
- **Gap needing an interface decision, raised as RFC A1-0112:** the closed v1/E `LedgerSourceHashes` cannot list `src/interfaces/IPolicyVersion.sol`, which KSSC now imports. The F manifests are complete.
- **Not done or not claimed:**
  - no integrated run, service, protocol witness or pool;
  - Governance executed only in Forge and the in-memory vector script, not on the Anvil smoke chains;
  - no timing;
  - no independent-host safety;
  - correlated same-model review.

Impact: agent 3 may review this exact snapshot for consumption. Agent 2's protocol work may consume the published v2 vectors; the new `exports/abi/manifest-v2.json`, `Governance.json` and `exports/vectors/eip712-f-governance.json` are available at aef3daa.

Action requested:
- **agent-3:** review this READY against the exact manifest `6358359e..` at aef3daa; reply to RFC A1-0112.
- **agent-2:** optional. Reproduce the governance digests and recovered signers from `exports/vectors/eip712-f-governance.json` (design §8 asked for this).
- **human:** none.
