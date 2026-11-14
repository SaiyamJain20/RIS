# Agent 1 handoff

## Current (2026-11-12, ~19:00): solo phase F closed (A1-0120); owners back; ledger unchanged at 85c59f5

- **Owners are back.** Agent 2 returned on 2026-11-09 (A2-0081) and agent 3 on 2026-11-12 (A3-0105). Both own their scopes again. A1-0120 closes solo phase F.
- **Proxies stood down.** Both proxies stopped on the account usage limit at about 23:00 on 2026-11-08 and wrote nothing (no S2-0024, no S3-0025). They will not be resumed.
- **No more peer merges.** The merges 84f46f9 and 7e51f5e stay. I merge no later peer commits; integration checkpoints are agent 3's.
- **Baseline on ca5a8e4 (2026-11-08), all exit 0:**
  - forge: 316 passed;
  - protocol: 2962 passed, 201 skipped;
  - root: 2944 passed.
- **New peer work read (2026-11-12):**
  - A2-0081: P0 inventory; claims G1/G2/G3.
  - A2-0082: G2 built. It is weaker than the inventory: no fork or reorg.
  - A2-0083: delta READY for G3/G1/G2 at 4893db1. No production, export or ABI byte changed since f026a50.
  - A3-0105: ACKs A2-0074 O1..O6. Decides A2-0077 F1 (`collect(anchors=...)` fixed on agent-3 04b7169), F2 option (a) with no `worker.py` change, and A2-0080 F1 (each checkpoint's own source block as `pbcHead`).
  - A3-0106: static scope check of A2-0083.
  - None of them asks anything of agent 1.

- **Read 2026-11-13 (~19:30):**
  - A3-0108: agent 3's consolidated isolated review of agent 2's runtime at 5e25b53. 195 focused tests passed, and 42 store plus 19 startup mutants were detected. A3-0096/97 close in that scope. One gap: the init-kill test was vacuous on agent 3's host (interrupted=0). Provenance correction: the A2-0076 manifest is published at 8b0a0b4, not at 7d97b90.
  - A2-0085: delta READY at 8ffd316. The kill schedule is now controlled by stage: interrupted >= 4, K1/K2 detected, E1 survives as designed. Full suite 3204 passed, 201 skipped. Test files only.
  - 1037517: executable hook reference for the runner (test_hook_reference.py, 20 starts).
  - None of them asks anything of agent 1.
- **Ledger-facing check that closes the open item in A1-0120 §4.** Agent 2's live tests deploy exactly the reviewed ledger. `protocol/tests/test_rpc_binding_view_live.py` pins `LEDGER_COMMIT = 85c59f58..` (line 38), then runs `git archive` of `ledger/` at that commit and agent 1's own `ledger/tools/deploy_local.sh` (profiles `repaired-f`, and `repaired-e` with `SUCCESSOR_EXPORT=1`). The new hook-reference test reuses those fixtures. I read this on origin/agent-2 1037517; I did not run it.

- **2026-11-13/14 reviews and reproductions (all correlated; no ledger byte changed):**

  | message | content |
  |---|---|
  | A1-0121 | DecisionQuorum model: the f0 cfg deadlocks under TLC defaults; independent enumeration |
  | A1-0122 | closed: TLC's distinct counts 108/81 equal mine |
  | A1-0123 | A3-0114 M1 gas, calldata and sizes reproduce exactly; my cold-storage hypothesis refuted; `--sizes` exits 1 only because of Forge scripts |
  | A1-0124 | receipt gas reproduces exactly |
  | A1-0125 | governance gas reproduces exactly; attribution checked against the source |
  | A1-0126 | RQ2-F draft review. The witness set is fixed at deployment (trust-matrix correction, accepted in A3-0120). Tested f=2 outcomes on the ledger (scratch DoubleCert, 4 of 4). Oracle keying question to agent 2 (open). |
  | A1-0127 | ledger-scope inventory of the 32 F cases; forge 316 of 316 and the mutant check both exit 0 on 2026-11-14 |

  The execution FREEZE must pin 85c59f5, not the matrix's `ledgerCommit` e4e992f (the F0-time ledger).
- **2026-11-14 afternoon, proxy-2 (A1-0130):**
  - S2-0024, S2-0025 and S2-0026 are committed. The K1 commit of record is 37ca31c, protocol subtree 7566f63d (A1-0131).
  - Agent 3 (A3-0129) accepted S2-0024's content but not proxy authority.
  - A1-0132 relays the human's words. **Pending:** if agent 3 does not accept, push the fallback commit d230c48 (local branch `agent2-fallback`; 9d44754 plus `protocol/` only, fast-forward) to `agent-2`. The human authorized this push.
- **Open with peers:**
  - agent 2: A3-0110 (K1 not deterministic) and the A1-0126 §4 question; silent since A2-0086.
  - agent 3: runner, oracle, execution FREEZE, 32 cases.

**Next:**
1. Ledger-scope ACK of agent 3's execution FREEZE when it is published.
2. Any ledger fix the runs expose, as a new commit plus a fresh READY.
3. The A1-0117 paragraph goes into the ledger findings at the next ledger revision.

## Previous (2026-11-08, ~23:00): solo phase F opened (A1-0119); proxies at P0; closed by A1-0120 without proxy output

- **Human directive (~22:50 IST):** agents 2 and 3 were at their usage limits, so I was to work as all three with proxy subagents. Recorded in A1-0119; plan in `communication/agent-1/solo/F-PLAN.md`.
- I merged origin/agent-3 6358f7c (84f46f9) and origin/agent-2 9d56d2c (7e51f5e) into agent-1 and pushed ca5a8e4.

## Previous (2026-11-08, ~05:00): A2-0076 ledger-facing check (A1-0118); ledger unchanged at 85c59f5

- Agent 2 published the **complete runtime source READY, A2-0076** (commit of record 7d97b90, manifest 7de8f334.., 549 entries). It asks nothing of agent 1.
  - Before it, agent 2 pushed three mutation-runner repairs (1f162b8, 9181d4f, 7d97b90) in `protocol/tools/` only.
- **A1-0118** records my ledger-facing check:
  - the 7 ABI copies and the two 85c59f5 deployment fixtures are byte copies of my reviewed files;
  - `worker.py` profile 3 in the repaired recipient branch matches PSC/ACSC;
  - the A2-0074 witness index/label layout matches the F base fixture.
- No `ledger/` edit.

**Next:**
1. Agent 3 reviews A2-0076 and ACKs A2-0074, then proposes the execution FREEZE, which I ACK on its exact bytes.
2. Integrated runs.

## Previous (2026-11-08, ~03:30): sequence-rule note (A1-0117); ledger unchanged at 85c59f5

- Caught up on A2-0063..0074 and A3-0083..0104. Only A2-0070 asked agent 1 something.
- **A2-0070** asked whether the strictly-greater checkpoint sequence rule is intended. **A1-0117** answers:
  - **Intended:** yes, `KSSC.sol:160`, design §9; the exact successor is witness-side (SIGNING-RULES §3).
  - **Already tested:** the poison tests (F0Powers/F0Quorum/Quorum).
  - **Still saturable by a compromised quorum under F:** `sequence`, `authEpoch` and `sourceBlockNumber`.
  - **Closed under F:** `keyEpoch` (must be 0) and `policyVersion` (pinned).
  - **Why no on-chain current + 1:** it would not close the class.
- No `ledger/` edit; carry the paragraph into the ledger findings at the next ledger revision.

**Next:**
1. Agent 2's full runtime READY (A2-0074's F start contract is BUILT plus PLANNED).
2. Agent 3's execution FREEZE, which I ACK on its exact bytes.
3. Integrated runs.

## Current (2026-11-04, ~19:40): ledger fully reviewed at 85c59f5; waiting

- **A1-0111** (aef3daa) was reviewed by A3-0077.
- **A1-0115** (85c59f5, manifest 70f541cd..; v2.1 E carrier migration) was reviewed by A3-0080.
- Together they cover the exact 85c59f5 for isolated consumption. **Nothing is owed by agent 1.**

**Waiting on:**
- agent 2's source READY (tasks 2 and 3). Check its ledger-facing facts. So far the checkpoint, decision and receipt witness derivations match KSSC, DecisionVerifier and PSC, and `binding.py` matches my exports 7/7.
- agent 3's evaluator, oracle and model.
- then agent 3's execution FREEZE, which I ACK on its exact bytes.
- then integrated runs; any ledger fix goes by a new commit plus a fresh READY.

## Current (2026-11-04, ~15:30): A-F1 ledger source READY (A1-0111), RFC A1-0112

**F0 accepted** (A3-0073, 14:24): `F0_ACCEPTANCE_CANDIDATE2.json` 03dcf485.., `interfaces/v2/FREEZE.json` 7bb1d243.. (read via `git archive origin/agent-3 interfaces/v2`; not merged).

**A-F1** was implemented test-first in 7 slices. The log is `ledger/evidence/af1/README.md`.

| Slice | Commit | Content | Result |
|---|---|---|---|
| 1 | aeea5a2 | profile carrier | 8 of 8 |
| 2 | 3abe0cf | Governance and the TMSC hooks | 30 of 30 |
| 3 | 1f47782 | KSSC pin, `Quorum.t.sol` | 9 of 9 |
| 4 | e22946f | E reruns under F | 71 of 71, identical to E |
| 5 | 8d363cb | F mutants (predictions in 8f5206f) | 12 of 12 detected |
| 6 | d056940 | deploy, successor exports, governance vectors, Anvil smoke | all pass |
| 7 | aef3daa | controls, mapping receipt, READY set | controls 13 of 13 |

**READY:** A1-0111 at aef3daa, ledger manifest 6358359e.. (418 entries).
- Full suite: 316 of 316.
- Mutants: 12 of 12.
- Controls: A-F1 13 of 13; F0 12 of 12.
- v2 vector receipt: 26 of 26 (implemented HMBCHash).
- E parity: every baseline test passes; E vectors byte-identical; the default E manifest is v1-valid; only the TMSC ABI changed, additively.

**RFC A1-0112:** the closed v1/E `LedgerSourceHashes` cannot list `src/interfaces/IPolicyVersion.sol`, which KSSC imports.

**How to re-run:**
- `forge test --root ledger`
- `python3 -I ledger/tools/check_mutants.py`
- `ledger/tools/af1_controls.sh <empty dir>`
- `.venv/bin/python -I ledger/tools/check_successor_export.py --schema <interfaces/v2/hmbc.schema.json> [--live] <deployment.json>`
- The smoke script is `ledger/evidence/af1/slice6-smoke/smoke.sh.txt`. It needs `ANVIL_DEV_KEY` in the environment; never record the key.

**Next:**
1. Agent 3's review of the READY. Fix by a new commit plus a fresh READY; never rewrite reviewed bytes.
2. RFC A1-0112.
3. The later execution FREEZE ACK.

## Current (2026-11-04, ~13:45): F0 freeze request ACKed in ledger scope (A1-0110)

**Thread:**
- A2-0057 (ac624b4): agent 2's protocol mapping/layout ACK of candidate 2. Both mapping ACKs now exist.
- A3-0072 (f1fe7e7): the F0 freeze request, `communication/F0_FREEZE_CANDIDATE2.json` f9f0906f.. (`implementationAuthorized` false until both freeze ACKs and acceptance).

**A1-0110:** ledger-scope F0 design freeze ACK of f9f0906f.., verified by script against the blobs:
- the 14 candidate files equal the candidate-2 manifest;
- the 4 ACK message hashes match;
- the 52 protocol files equal agent 2's manifest at 52f3943;
- the design 7eed1b29.. is at 8a943a7;
- the numeric plan agrees with KSSC/FixtureConfig and design 2.2.

**Next:**
1. agent 2's freeze ACK;
2. agent 3's separate acceptance record;
3. then A-F1 test-first per design 2.2 and the A1-0109 obligations;
4. source READY manifest;
5. later, execution FREEZE.

## Previous (2026-11-04, ~13:00): v2 candidate 2 mapping-ACKed in ledger scope (A1-0109)

**A3-0071** (origin/agent-3 5b6bb9d): the complete successor v2 candidate 2.
- `interfaces/proposals/v2-candidate2/`, MANIFEST 0d1a2be4.. (14 payload files);
- OWNER-PINS: ledger design 7eed1b29.., ledger commit 8a943a7, agent 2's revision 9.

**A3-0070** ACKs EXPORT-LAYOUTS r9 and keeps the generation-order rule.

**A1-0109:** exact mapping/layout ACK of 0d1a2be4.., ledger producer/consumer scope only.
- M1–M4 and N1/N2/N4 are verified on the bytes.
- The v1-named ledger definitions are byte-identical to frozen v1, except the `LedgerDeployment` union (note A: v2 envelopes carry only v2 carriers).
- The E mappings equal `make_manifest.py`.
- The vectors are identical to candidate 1, and the Solidity check re-run on the c2 directory gives 26/26.
- The owner copies are identical (`cmp`).
- The death kinds and effects are ledger-true, and the schema has the ALLOW guard.

**A-F1 obligations accepted (after the freeze only):**
- Governance with public immutables, full mask, `MAX_ADMINS` 8, TTL 120 and the native events;
- IPolicyVersion and the design §§1–4 changes plus the §7 test edits;
- the opt-in successor exporter (deployment/v2 E and F, V2 entries with immutables, `fixture.governance`, the F `mutantNote`, q2 config, witness sets in fixture order); the default E export stays byte-identical.

**Next:** agent 2's protocol mapping ACK, then agent 3's separate F0 freeze record (my exact ACK), then A-F1 test-first.

## Previous (2026-11-04, ~12:20): EXPORT-LAYOUTS revision 9 re-ACKed in ledger-facing scope (A1-0108)

**A2-0056** (origin/agent-2 52f3943): revision 9, manifest 8496c7f3...
- Only EXPORT-LAYOUTS changed (b0b801ba.. → 53bbf7e0..).
- D50 8ed6f1a4.., SUCCESSOR-WIRE 3f1db2ca.., SIGNING-RULES and INVENTORY are byte-identical.
- The change: L1 per-generation supersession (A→B→A legal), L2 `overtaken-decision-grant` requires result "1", and a new generation-order rule (agent 3 decides whether it stays).

**A1-0108:** ledger-facing ACK of 53bbf7e0...
- The DENY fact holds in F too (design line 188).
- The generation-order premise holds: same target chain, monotone mined blocks, equality allowed.
- The A1-0106 scope for D50 and SUCCESSOR-WIRE stands.

**Next:** agent 3's candidate 2, then my exact mapping ACK, then the F0 freeze, then A-F1.

## Previous (2026-11-04, ~11:45): ledger facts for the EXPORT-LAYOUTS fix (A1-0107)

**A3-0068** ACKs D50 r5 (8ed6f1a4..) and the SUCCESSOR-WIRE r8 rules (3f1db2ca..). **A3-0069** withholds the EXPORT-LAYOUTS (b0b801ba..) ACK:
- **L1:** the checker rejects a legal A→B→A supersession.
- **L2:** the checker accepts a DENY under `overtaken-decision-grant`.

**A1-0107** supports both from the ledger:
- **DENY:** a valid DENY is logged and returns, with no replay guard (ACSC:185–187). It stays acceptable after a grant exists; its deaths are only expiry and sequence.
- **ALLOW:** only ALLOW hits the grant REPLAY (KSSC:179–180).
- **A→B→A:** legal on the ledger for an unexecuted governance nonce.

My A1-0106 is unchanged, and it does not transfer to the amended bytes.

**Next:** agent 2's EXPORT-LAYOUTS amendment (my ledger-facing re-ACK), then agent 3's candidate 2 (my mapping ACK), then the F0 freeze, then A-F1.

## Previous (2026-11-04, ~11:00): agent 2's revision 8 ACKed in ledger-facing scope (A1-0106)

**Thread:**
- A2-0054 (9ced19a): agent 2 agrees with M1–M4.
- A3-0067 (4fc3882): a prospective schema with M1–M3 and N1, accepting M4. Candidate 2 waits for revision 8.
- A2-0055 (64ec86a): revision 8 (manifest 19220e0f..):
  - D50 r5 8ed6f1a4..;
  - SUCCESSOR-WIRE 3f1db2ca..;
  - EXPORT-LAYOUTS b0b801ba.. (new);
  - SIGNING-RULES unchanged.

**A1-0106:** ACK of those exact files in ledger-facing scope. Checked:
- the table equals `make_manifest.py` (AST compare);
- the profile/mutations holders are exactly TMSC/PSC/KSSC/ACSC, plus Governance's mask in F;
- the paper profiles' mask 0 is enforced on chain;
- the thresholds 1..n and unique witnesses are constructor rules;
- all 3 bindings were recomputed with my encoder;
- each death kind was checked against the code: KSSC:148/153/179–180, DecisionVerifier:74/86–87, PSC:250, and design §2 for Governance.

Note: under bit 1 and bit 5, "overtaken-decision-sequence" and "executed-receipt" are false on the ledger, so that evidence must be labelled mutant.

**Next:** agent 3's candidate 2 (M1–M4 plus the revision-8 layouts), then my exact mapping ACK (with the `LedgerAbiContracts` naming note), then the F0 freeze, then A-F1.

## Previous (2026-11-04, ~10:30): interface-v2 candidate 1 reviewed in ledger scope (A1-0105)

**A3-0066** (origin/agent-3 4de6274):
- both candidate-8 ACKs recorded;
- `A-F1-DESIGN.md` pinned as 7eed1b29..;
- interface-v2 candidate 1: `interfaces/proposals/v2/`, MANIFEST 6acceadf.., review-manifest fd4b037c...

**A1-0105:** REVIEW, not a mapping ACK yet.

Verified:
- **Signing vectors:** all six, in Solidity, with `HMBCHash` and QuorumLib. The governance type hash, domain, struct hash and digest match, and each vector passes at q3: 26/26. Two sensitivity controls fail as expected.
- **Immutable ranges and masked build:** recomputed.
- **Schema:** the ledger definitions, read and diffed against v1.

Corrections:
- **M1:** add `fixture.governance {maxGovernanceTtl "120", maxAdmins "8"}`, which design §8 lists.
- **M2:** the v2 E carrier keeps `schemaVersion` "hmbc-ledger-deployment/v0" with a changed entry shape. Use v2 and rename the entry.
- **M3:** `mutantNote` is a fixed disclaimer (`make_manifest.py:52`). Classify by mask + threshold only, and forbid q2 combined with bits.
- **M4:** BOUNDARY must state the equalities: all five contracts' `mutations()` equal the mask, and all three witness sets equal the fixture.
  - Clarification, not a design revision: "non-F bit" means a bit outside `MUT_ALL`. Governance stores the full mask, and its config values are public immutables.

Answers:
- **Item 1:** accepted, subject to M3/M4.
- **Item 2:** accepted. The runner must sort the q2 signatures by address.

**Implementation commitments recorded in A1-0105, for A-F1 after the freeze:**
- Governance stores the full mask, with public immutables;
- an opt-in successor export mode (default E export byte-identical) carrying `fixture.governance` and the F `mutantNote` text.

**Next:** candidate 2, then my exact mapping ACK, then the F0 freeze, then A-F1.

## Previous (2026-11-04, ~08:40): candidate 8 ACKed in ledger scope (A1-0104)

**Thread:**
- A2-0052 (e0f25ef): agent 2 withheld its candidate-7 ACK pending C-1 (F-12 controls), C-2 (F-29 SIGNING-RULES hash) and C-3 (revision-4 F0 set label).
- A3-0065 (731833c): candidate 8 adopts C-1..C-3 and N-1..N-3.
- A2-0053 (de12537): agent 2's exact protocol-scope ACK of candidate 8.

**A1-0104:** ACK of the exact candidate-8 hashes, ledger scope:
- plan 76069506..;
- f_matrix 2230daf3..;
- CSV 5bf01f05.. (byte-identical to candidate 7);
- review-manifest 1388af02...

Checked:
- Only F-12 (controls, dependencies) and F-29 (dependencies) changed among the 32 cases. No ledger line of the plan changed (task 1, K1, K2, K4, F-18).
- The f=2 control's "no certificate forms" has a ledger backstop: q3 rejects two signatures (`test_F0Q_TwoOfFourInsufficient`, re-run 9/9, exit 0). That holds only while every honest witness refuses, because three signers can poison (L8).
- Note for the freeze: record `A-F1-DESIGN.md` sha256 `7eed1b29e79144d88d6b5bba33a414e4fcb6dc8fa8cb31262c0742e3baaebfd0`. "Design 2.2" alone also names `45004b72..` (3de2ee6).

**Next:** the full successor v2 schema and vectors from agent 3. For my mapping ACK, I review:
- the export fields (`runtimeBytes`, `immutableReferences`, `immutableRefsSha256`);
- the Governance ABI and `GovernanceAction` type;
- repaired-f and `profileEnum` 3;
- the four-witness fixture with set version 2;
- the mutation names for bits 6–8 and `mutant-f-q2`.

Then the F0 freeze, then A-F1.

## Previous (2026-11-04, ~07:40): candidate 7 ACKed in ledger scope (A1-0103)

**Pool-retry thread (agent 2 / agent 3):**
- A2-0049: revision 6, answering R4/R5.
- A2-0050: protocol ACK of candidate 6.
- A3-0063: raised R6 (selection versus action, the 2 s gate, the hard stop).
- A2-0051: revision 7, answering R6.
- A3-0064: candidate 7, with revision 7 adopted.

None of this touches ledger semantics.

**A1-0103:** ACK of the exact candidate-7 hashes, ledger scope:
- plan 04d6c67f..;
- f_matrix 114dfa06..;
- CSV 5bf01f05..;
- review-manifest 20048e64...

Checked: K4 is retained (plan line 134); the FL-1 clockPolicy and F-32 concurrency are retained in the matrix; the ledger rows are unchanged.

**Next:** the full successor v2 schema and vectors from agent 3. For my mapping ACK, I review:
- the export fields (`runtimeBytes`, `immutableReferences`, `immutableRefsSha256`);
- the Governance ABI and `GovernanceAction` type;
- repaired-f and `profileEnum` 3;
- the four-witness fixture with set version 2;
- the mutation names for bits 6–8 and `mutant-f-q2`.

Then the F0 freeze, then A-F1.

## Previous (2026-11-04, ~04:20): candidate 6 ACKed in ledger scope (A1-0102)

**A3-0062** (origin/agent-3 6fd26d3), candidate 6:
- plan df510108..;
- f_matrix 5c917c2d..;
- CSV e3cf2a1e..;
- review-manifest 82da3758...

K4 is fixed. Revision 5 pool-retry is not adopted, pending R4/R5 (agent 2's).

**A1-0102:** ACK of the exact candidate-6 hashes, ledger scope only.

**Excluded:** protocol internals, revision 5, the evaluator and model, the v2 schema mapping, the freeze and execution.

**Observation:** in F-32, concurrent deployments with identical chain ids and addresses have identical EIP-712 domains. Do not cross-submit artifacts.

**Next:** any candidate 7 after R4/R5 (I review the changed bytes), then the v2 schema and vectors (my mapping ACK), then the F0 freeze, then A-F1 implementation.

## Previous (2026-11-04, ~03:20): candidate 5 reviewed in ledger scope (A1-0101)

**A3-0061** (origin/agent-3 00588a7), candidate 5:
- plan cd174284..;
- f_matrix 582f8739.. (32 cases, with new F-31/F-32);
- CSV fed0d757...

K2/K3 are adopted exactly.

**A1-0101:** not an ACK yet. The only correction is **K4**: owner task 1 names `src/lib/QuorumLib.sol`. That file does not exist; it should be "QuorumLib in src/lib/SigLib.sol".
- M7 fixture: ledger-feasible, with the PBC leading the DBC by at least 20 s. Every boundary check is satisfied.
- F-28 note: the separate branches are harmless, but the check order (verify before KSSC) already prevents masking.

**Next:** candidate 6 (K4 plus agent 2's revision-5 pool-retry amendment), which I ACK in ledger scope. Then v2 schema/vectors, then the F0 freeze.

## Previous (2026-11-04, ~02:30): candidate 4 reviewed in ledger scope (A1-0100)

**A3-0060** (origin/agent-3 096a9f3), candidate 4:
- plan 7852b7a0..;
- f_matrix 673ef239..;
- fault-model e06280c1...

K1 is pinned and agent 2's E-1..E-5 are folded in.

**A1-0100:** whole-document review (plan, CSV and all 30 cases with every array). Not an ACK yet.
- **K2:** FL-10 should pre-register:
  - the SET([])→REMOVE baseline BAD_SIGNATURE;
  - the bit 6 mutant;
  - the SET replay baseline REPLAY;
  - the bit 7 mutant;
  - EXPIRED and nonce-gap MALFORMED;
  - before/after state evidence.
- **K3:** F-28 should require the PBC UNKNOWN_AUTHORITY, the DBC pre-barrier grant and the DBC post-barrier STALE_STATE.
- Everything else is accepted in ledger scope.

**Next:** candidate 5 with K2/K3, which I ACK in ledger scope. Then v2 schema and vectors (mapping ACK), then the F0 freeze, then A-F1.

## Previous (2026-11-04, ~01:50): agent 2's revision 4 ACKed in ledger scope (A1-0099)

**A2-0044** (origin/agent-2 c3a0538):
- manifest 30051bc5.., D50 b178e0a8..;
- the five immutable cross-checks, so S0 is 48 (E) / 55 (F);
- object-list `immutableRefsSha256` in decimal strings (K1-compatible).

**A2-0045:** agent 2's scoped ACK of candidate 3, conditional on E-1..E-5 for agent 3.

**A1-0099:** ACK of the ledger-facing deltas only.
- Evidence `crosscheck-a2-reference.txt`: agent 2's reference equals my `immutable_refs_digest.py` on all six real E lists, and my encoder reproduces its vector 69b614b0...

**Next:** agent 3's next candidate with K1 and E-1..E-5, which I ACK in ledger scope. Then v2 schema and vectors, then the F0 freeze.

## Previous (2026-11-04, ~01:30): candidate-3 plan reviewed in ledger scope (A1-0098)

**A3-0059** (origin/agent-3 05c239e):
- SOURCE-INTERFACE-PLAN 5ae2740f..;
- f_matrix 25690ec1.. (30 cases);
- fault-model e06280c1...

**A1-0098:** not an ACK yet. One correction:
- **K1:** state the number form of `start` and `length` in the hashed `immutableReferences` list. Decimal strings are recommended.

Everything else is accepted in ledger scope: the scope itself, Governance, error mapping E1, the export rule, task 1, F-30 and the numeric candidate.

**Feasibility note:** worst case about 25 s of the 30 s request TTL. The pre-FREEZE measurements decide it.

**New:**
- `ledger/tools/immutable_refs_digest.py`;
- `ledger/evidence/f0-d50-masked/immutable-refs-digests.txt`: reference digests for the six E contracts; `runtimeSha256` and `runtimeBytes` equal the published export.

**Next:** agent 3's next candidate with K1 pinned, which I ACK in ledger scope. Then the v2 schema and vectors for the mapping ACK, then the F0 freeze, then A-F1 implementation.

## Previous (2026-11-04, ~01:00): agent 2's revision 3 ACKed in ledger scope (A1-0097)

**A2-0043** (origin/agent-2 d4d5ff0, manifest 22e88c23..):

| File | sha256 |
|---|---|
| D50-DEPLOYMENT-BINDING.md | 73e6493a.. |
| SIGNING-RULES.md | c982ec8a.. |
| SUCCESSOR-WIRE.md | 54abfaa2.. |
| INVENTORY.md | ca65e530.. |
| vectors/d50_binding_vector.json | edd8d633.. |

**A1-0097:** ACK scoped to the ledger-facing items:
- the masked-build contract;
- the Governance contract-set rules;
- the wiring and sealed checks;
- the ledger-code mapping of the reason table.

It does not cover protocol internals or vector values.

**My side:**
- `check_masked_runtime.py` hardened: concatenation after validation. `offline-replay-hardened.txt` gives exit 0 and is identical; the negative control still exits 1.
- Design 2.2 §8: successor numbers are decimal strings.

**All F0 inputs are reviewed:**
- matrix rev 2 (A1-0091);
- design 2.2;
- A2 rev 3 (A1-0097).

**Next:** agent 3's final source/interface plan and exact ACK request.

## Previous (2026-11-04, later): design 2.2 export rule and offline replay (A1-0096)

**A3-0058** (origin/agent-3 0ed33c5) reviewed agent 2's input:
- it gave agent 2 five more amendments;
- it recorded A1-0095;
- it asked agent 1 for the immutable ranges and byte length.

**A1-0096:**
- `ledger/f0/A-F1-DESIGN.md` revision 2.2 §8: the exact `immutableReferences` rule and the masked-check acceptance conditions. Attestation scope: all 35 immutables are public, so the masked check plus the getters attest the constructor values; E CA-Admin sets are the exception.
- `ledger/tools/check_masked_runtime.py` gained `--save-code` and `--code-dir` and range validation.
- `ledger/evidence/f0-d50-masked/`:
  - `replay/` holds the raw code and deployment manifests;
  - `offline-replay.txt`: 18/18 match, equal to the online run;
  - `offline-negative-control.txt`: a flipped byte is detected.

**Not changed:** production and interfaces.

**Next:** review agent 2's next amended revision separately, then agent 3's final plan.

## Previous (2026-11-04): agent 2's revision 2 ACKed in ledger scope (A1-0095)

**A2-0042** (origin/agent-2 09dbb5b): manifest b606a335.., SIGNING-RULES 85887e38.., D50 cff58c3e.., INVENTORY 659ed463...
- C1–C4 verified in the diff.
- `TMSC.governance()` confirmed as a public view in design 2.1 §3.

**A1-0095:** ACK scoped to the ledger-facing items. It is not a freeze, choice, migration or protocol-internals ACK.

**All F0 inputs are now published:**
- matrix revision 2 (aded280a.., A1-0091);
- A-F1 design 2.1 (0d66f89a..);
- A2 F0 revision 2 (b606a335.., A1-0095).

**Next:** agent 3's final source/interface plan and exact ACK request. A-F1 code only after the F0 freeze.

## Previous (2026-11-03, late night): agent 2's F0 input reviewed (A1-0094)

**A2-0040/0041** (origin/agent-2 39af20f):

| File | sha256 |
|---|---|
| INVENTORY.md | 6210006e.. |
| SIGNING-RULES.md | 3d5ca717.. |
| D50-DEPLOYMENT-BINDING.md | f615e0f9.. |
| MANIFEST.sha256 | 2d9395aa.. |

**A1-0094:** not an ACK yet.
- Confirmed against the code: the §3 validation duties, the §5 receipt block rule, the §6 death predicates, F-30, and the D50 views for six contracts plus Governance per design 2.1.
- Corrections:
  - **C1:** min(request, checkpoint) is effect-equivalent, not "largest acceptable".
  - **C2:** monotone timestamps apply to the live ledger, not to `vm.warp`.
  - **C3:** add the storage wiring views `TMSC.psc/rsc`, `LSC.rsc/tmsc/psc`, and under F `TMSC.governance` and `Governance.target`.
  - **C4:** require `configured() == true`.
- Provenance: commit 39af20f is authored as `karma-skz`. Raised for the record, not as a finding.

**New tool:** `ledger/tools/check_masked_runtime.py`.

**New evidence:** `ledger/evidence/f0-d50-masked/`:
- masked live code equals the compiled runtime 18/18;
- on fresh chains the addresses are the same across repaired-e, paper-strict and mutant-no-nonce, but the raw code differs for TMSC, PSC, ACSC and KSSC;
- the Anvil chains were my own processes, stopped afterwards; the deployment outputs were kept out of the repository.

**Agreed:** the `immutableReferences` export for the successor schema (sorted `{start, length}`).

**Next:**
- agent 2's revision with C1–C4, which I will ACK;
- agent 3's final source/interface plan.

## Previous (2026-11-03, night): design revision 2.1 (A1-0093) after A3-0056

**A3-0056** (origin/agent-3 393d5ae):
- A1-0091 recorded as a scoped ledger ACK of revision 2 (aded280a..);
- design revision 2 reviewed: R1/R2/R3/R5 addressed, R4's core resolved.

**A1-0093 (revision 2.1)** changes two things:
- **Calldata claim:** authorization binds the decoded values; raw calldata is not canonical, trailing bytes are not rejected; no canonical-calldata claim.
- **Bit 7 control:** uses a repeatable SET_CA_ADMINS action. The baseline gives REPLAY with no repeated effects; the mutant repeats the effects; both have positive controls.

**Not changed:** source, tests and ABI.

**Waiting for:**
- agent 2's inventory, R6 and D50 for seven runtimes;
- then agent 3's final source/interface plan and the exact ACK request.

## Previous (2026-11-03, later): matrix revision 2 ACKed in ledger scope (A1-0091); design revision 2 (A1-0092)

**A3-0055** (origin/agent-3 80439e9):
- matrix revision 2, manifest aded280a.., with 29 scenarios;
- DESIGN-REVIEW.md, R1–R6.

**A1-0091:** a scoped ACK, covering ledger scope and revision 2's exact hashes.
- f_matrix.json 73b892ef..;
- fault-model.csv 6df6d357..;
- DESIGN-REVIEW.md 62a12dcd...
- It is not a freeze, choice or migration ACK.

**A1-0092:** `ledger/f0/A-F1-DESIGN.md` revision 2 (dda3914b..):

| Review item | Answer |
|---|---|
| R1 | Exact assertion-preserving E test edits: 8 `virtual`, 9 `isRepaired`, fixture parameters, q-aware signing of `witnessPk` |
| R2 | Tombstone: a removed root can never be re-added |
| R3 | Mutators take the signed nonce; nonce is set before the call; log binding; full events and getters; `IPolicyVersion` path |
| R4 | Typed `GovernanceAction` struct with `address[] admins`; no bytes payload; full precedence; bit 6 control signed over action=0; vector list |
| R5 | Interface v2 successor; seven runtimes for D-f |

**Not changed:** source, tests and ABI.

**Next:**
- agent 3's response and its exact source/interface plan;
- agent 2's R6, D50 and inventory, which are still missing.

## Previous (2026-11-03, evening): A3-0054 matrix reviewed; A-F1 design for review (A1-0090)

**A3-0054:** agent 3's F0 draft, at origin/agent-3 91062fd:
- `evaluation/evidence/fault-model.csv` has 14 components;
- `evaluation/scenarios/f_matrix.json` has 27 cases, all NOT_RUN;
- it accepts A1-0089.

**A1-0090:** my review. Not an ACK. It requests 7 changes:
1. evidence for F-14;
2. evidence for F-15;
3. evidence for F-21;
4. F-18 as a `mutant-f-q2` configuration;
5. F-24 split by e1;
6. new row F-28: authority removal across the barrier;
7. new row F-29: governance nonce after expiry, depending on the clock bound.

**`ledger/f0/A-F1-DESIGN.md`:** exact design for review only, not implemented:
- REPAIRED_F profile sites;
- `Governance.sol` type, payloads, nonce and expiry, check order and codes;
- TMSC governance mutators plus a `caAdmins` view;
- the KSSC policyVersion pin, through `IPolicyVersion` with no ABI change;
- mutation bits 6–8;
- vectors and the manifest;
- the E regression plan;
- conflict keys built on the domain separator. This withdraws the `(chainId, nonce)` shorthand.

**No code, test or ABI changed.**

**Next:** agent 3's revised matrix and design comments, and agent 2's D50 RFC and key inventory, which are still the gating input.

## Previous (2026-11-03): F0 quorum characterization addendum (A1-0089)

**What changed:**
- `ledger/test/F0Quorum.t.sol` adds 10 tests: 9 measure the **existing** QuorumLib with a test-only 4-witness KSSC at q=3, and 1 covers `sourceBlockNumber` poison.
- `ledger/tools/f0_controls.sh` now runs 12 controls.
- `ledger/f0/README.md`:
  - L8 and L12 are now tested;
  - the FL table has a column for the E test that measures each row;
  - the decision summary is corrected to defer to A1-0088.
- `actor-powers.csv` A05 evidence is updated.
- Successor manifest 96c9909d.. (301 entries).

**Commands and results:**

| Command | Result |
|---|---|
| `forge test --root ledger --match-path test/F0Quorum.t.sol` | exit 0, 10 passed. The first attempt failed to compile because of a test type bug; that output is kept. |
| `forge test --root ledger` | exit 0, 198 passed |
| `ledger/tools/f0_controls.sh <empty dir>` | exit 0, 12/12 sensitive |
| `python3 -I ledger/tools/check_f0_powers.py` | exit 0, `problems: []` |

**Not changed:** production ledger bytes (933d2a7), interfaces and gates.

**Waiting for:**
- agent 3's choices on A1-0088;
- agent 2's key-control enumeration and D50 RFC.

Neither has pushed since 2026-10-13.

## Previous (2026-10-14): grouped F0 RFC published (A1-0088); ledger F0 input accepted (A3-0053)

**A3-0053:** agent 3 accepted A1-0087 as reviewed F0 input.
- It ran on an exact snapshot: Forge 188 passed, the AST checker returned `problems: []`, and the manifest verified 296 of 296 entries.
- It did not re-run the 7 controls; it read them.
- It requested a grouped RFC.

**A1-0088 (RFC)** contains:
- C0, the common carrier:
  - a new `Profile.REPAIRED_F = 3`, with E profiles unchanged;
  - a 4-witness fixture with q=3 and set version 2;
  - F mutant bits;
  - keeping `QuorumLib`.
- D-a: governance actions, with a candidate `GovernanceAction` EIP-712 type.
- D-b: governance signers.
- D-c: global authEpoch.
- D-d: user-signature check on the DBC.
- D-e: poison checkpoints (pin policyVersion; recovery).
- D-f: what the ledger can expose to D50. Two things are not exposed today:
  - CA-Admin sets cannot be enumerated;
  - the exported `runtimeSha256` hashes compiled code with immutables zeroed, so it does not equal the on-chain code.

**Status of the choices:**
- Every choice in A1-0088 is UNRESOLVED; my recommendations are not approved scope.
- No source, test, ABI or interface changed.

**Next:** agent 3's choices and exact ACK requests. Then agent 2's D50 formula, which I ACK. A-F1 code starts only after the F0 freeze ACKs.

## Previous (2026-10-13): F0 ledger power matrix READY (A1-0087)

**Task:** F0, PLAN.md section 6, first bullet (agent 1 part), assigned in A3-0052. Base: common baseline 376347d (D51).

**Exported artifacts** (`ledger/f0/`, which README.md explains):

| File | Content |
|---|---|
| `ledger-state.csv` | 29 rows covering all 70 state variables |
| `entry-points.csv` | All 33 constructors and state-changing or placeholder entry points |
| `actor-powers.csv` | 12 actors |

**Consumers:**
- agent 3 for `fault-model.csv` and `f_matrix.json`;
- agent 2 for the B-F1 honest-witness checks and the D50 RFC.

**Commands and results** (repository root, Foundry 1.8.5, solc 0.8.37 hash 5de843c2..):

| Command | Result |
|---|---|
| `forge test --root ledger --match-path test/F0Powers.t.sol` | exit 0, 22 passed, expectations written before the first run |
| `forge test --root ledger` | exit 0, 188 passed |
| `ledger/tools/f0_controls.sh <empty scratch dir>` | exit 0, 7/7 sensitive. The first run matched no tests and is kept as `controls-run1-no-match.txt` |
| `python3 -I ledger/tools/check_f0_powers.py` | exit 0, `problems: []`. A negative control catches 3 injected errors |

**Evidence:** `ledger/evidence/f0-powers/`.

**Source manifest:** 186e28fb.. (296 entries). It only adds entries to 5b32e2c4... Production ledger bytes are unchanged since 933d2a7.

**Open decisions** (README D-a..D-f; agent 3 coordinates):

| Ref | Decision |
|---|---|
| D-a | Governance actions in core F |
| D-b | Old-set q=3 witness signers |
| D-c | Global authEpoch (L5) |
| D-d | User-signature check in `consumeDecision` (ABI change, needs an RFC) |
| D-e | Poison-checkpoint mitigation (L8) |
| D-f | Deployment verification, folded into D50 |

**Limits:**
- tests run in a single EVM with the E fixture (q=1);
- pre-seal deployer powers, ledger-operator powers, `sourceBlockNumber` poison and QuorumLib at n=4 are read, not tested;
- the checker proves coverage and citations, not the power claims;
- all review is correlated.

**Next action for the receiving agent:** read A1-0087 and `ledger/f0/README.md`. Agent 3 then folds the rows into the F0 matrix and asks for any RFCs it wants. A-F1 starts only after the F0 freeze ACKs.

## Previous (2026-10-12): gate E PASS (solo phase), board at F0

- **Decision recorded in `communication/GATES.md`:** "gate E PASS: solo phase, correlated review, criterion 4
  human-scoped (A1-0080), window cited from owner evidence (A1-0081), integrated mutants and window not run".
- **Three same-source ACKs**, each naming manifest 908fd615.., gate-evidence 47e38dd3.., RQ1-E.md 69dabfba.. and
  HEAD 871e218:
  - A1-0085 (agent 1);
  - S2-0023 (agent 2 (proxy));
  - S3-0024 (agent 3 (proxy)).
- **Gate run:** `evaluation/evidence/e3/gate-run-20261012/` (FREEZE S3-0021, plan c0086019.., exit 0, 56/56 rows,
  ProVerif matched).
- **Agent 1's independent review:** `ledger/evidence/gate-e-review/`. The eight tools in `ledger/tools/review_*.py`
  were committed before the FREEZE and pass 56/56 on the raw and the published copy (A1-0084).
- **Ledger code:** ledger pin 933d2a7 (c7b7dd51..) for every E2 and gate run. No ledger source change in the
  solo phase. New tools and evidence are review-only:
  - `ledger/tools/review_*.py`;
  - `ledger/evidence/sl*-review/`, `early-rows-review/`, `gate-e-review/`, `p3-mutant-suite-rerun/`.
- **Limits:**
  - all solo reviews are correlated self-review (A1-0059);
  - the integrated live mutant matrix and the integrated window were not run (A1-0079/A1-0080/A1-0081);
  - D47 paper crash rows;
  - single host, one trial per row, symbolic adapter.
- **Not done and not authorized:**
  - F work; it needs its own plan and the human's go-ahead;
  - pushing `main`, which is the human's decision.

The sections below are the earlier E0/E1 handoff snapshot, kept for history.

Status (2026-10-08 snapshot): **READY FOR INTEGRATION; not DONE.** Interface **v1 FROZEN** (E0-v1-r6-20261008, FREEZE.json
f700292e.. at agent-3 f7b8f3f); E0 closed and E1 unlocked by A3-0023; agent-1 mapping ACK A1-0027, A-E1 READY
A1-0028. Ledger READY items: A1-0030 (bootstrap producer, E1), **A1-0039 (E2 handoff: `ledger/E2_HANDOFF.md`, sign_list.sh, mutant kill map)**.
Latest inventory **A1-0046** (manifest 5b32e2c4.., 232 entries); contract code unchanged since 91add8c. Owner rehearsals (not C-E1/C-E2
results): E1 9/9 frozen controls with agent 2's adapter (A1-0033; agent 2 cross-ran 9/9), E2 47/47 rehearsable catalog
cases (A1-0035). **C-E1 COMPLETE: agent 3's actual integration 9/9 (A3-0030) under plan 78e195f5.. (A1-0038 ACK).** E2/E3 unlocked.

- **RQ/task and interface version:** E / sprint E0 close -> E1 integration (A1-0023). The ledger has: E0 deliverables, an A-E1
  draft, and A-E2 suites prepared before E1 integration, including the E03 GrantReceipt repair
  (A1-0008 revision 2, ACKed by agent 3 in A3-0005 and agent 2 in A2-0002, implemented in A1-0011).
- **Changed owned files and source manifest:** `ledger/**` (232 files) with SHA-256 in
  `ledger/evidence/source-manifest.sha256` (232 entries; file sha256
  5b32e2c47bc234192dc2bb98732ad1f00c9dfb81acc7f020d44806c2511c7ca7). Solidity sources, tests,
  scripts, foundry.toml and vectors are byte-identical to e6cf4ff (A1-0014). A1-0024 changes only the
  export label "v0 proposed" -> "v1" and regenerates the samples (`ledger/evidence/v1-export-run.txt`).
  A1-0026 adds the opt-in fast deploy (`tools/deploy_local.sh`). A1-0030 adds the TEST-ONLY bootstrap producer
  (`script/BootstrapFixture.s.sol`, `tools/bootstrap_fixture.sh`, `tools/check_bootstrap.py`; evidence
  `bootstrap-check.txt`). A1-0033 adds `tools/e1_rehearsal.py` and `evidence/e1-rehearsal/` (owner rehearsal,
  9/9 frozen E1 controls with agent 2's adapter). A1-0034 adds `script/SignList.s.sol`, `tools/sign_list.sh`, `tools/check_sign_list.py` and
  `evidence/signed-list-check/`. A1-0035 adds `tools/e2_rehearsal.py` and `evidence/e2-rehearsal/` (47/47 rehearsable catalog cases). A1-0039 adds `E2_HANDOFF.md`, live mutant probes in `e2_rehearsal.py` and `evidence/e2-ready/`. A1-0043 adds crash cases to `e2_rehearsal.py` and `evidence/e2-full-rehearsal/` (56/56 catalog). A1-0046 adds `tools/revocation_window.py` and `evidence/revocation-window/` (measured revocation window). Messages A1-0001..A1-0046.
- **Exported artifacts and consumers:**
  - ABIs: `ledger/exports/abi/*.json` + `manifest.json` (cea42704.., label v1; ABI JSON unchanged since 54262c2).
  - Vectors: `ledger/exports/vectors/eip712-v0-ledger.json` (6aa399e0..; 9 signed types incl.
    GrantReceipt, plus credentialDigest) + `typed/*.json`.
  - Samples: `ledger/exports/deployments/sample-{paper-strict,paper-minimal,repaired-e,mutant-no-receipt-binding}/`
    (labelled `interfaceVersion: "v1"`, valid against revision-6 `LedgerDeployment`; machine-local RPC/addresses).
  - Tools: `ledger/tools/deploy_local.sh` and `e2e_smoke.sh`.
  - Consumers: agent 2 (relay, witness, worker), agent 3 (runner, schema).
- **Exact commands, exit codes, evidence** (repository root, Foundry v1.8.5, solc 0.8.37):
  - `forge test --root ledger` -> exit 0, 166 passed / 0 failed (`ledger/evidence/forge-test.txt`)
  - policy test-first run -> 2 expected failures before the ACSC change (`policy-first-run.txt`)
  - receipt test-first run against a stub -> 11 expected failures (`receipt-first-run.txt`);
    A-E2 first run -> 63/63 matched pre-written expectations (`ae2-first-run.txt`)
  - `python3 -I ledger/tools/check_mutants.py ledger/evidence/ae2-mutants.json` -> exit 0, 7/7 mutant suites detected
  - `python3 -I ledger/tools/mutation_smoke.py ledger/evidence/ae1-mutation-smoke.json` -> exit 0, 17/17 detected (baseline 166/0)
  - `python3 -I ledger/tools/crosscheck_cast.py` -> exit 0, 196 checks / 0 failures
  - `forge build --root ledger && python3 -I ledger/tools/export_abi.py` -> exit 0
  - `DEPLOYER_PK=<anvil key 0> ledger/tools/deploy_local.sh <pbc-rpc> <dbc-rpc> <profile> complete-details sample-<profile>`
    then `ledger/tools/e2e_smoke.sh <pbc-rpc> <dbc-rpc> <deployment.json> 1` -> exit 0 for all 4 samples
    (Anvil `--block-time 1`, 5 stages including `dbc-receipt`)
  - historical `TMSC.checkCredentials` read across a revocation (`historical-read-check.txt`)
  - independent reproduction by peers: agent 3 (A3-0008) re-ran 162/0, 196/0, 7 mutants and 33
    export checks at 54262c2; agent 2 (A2-0003) reproduced all 9 signed vectors including GrantReceipt
- **Valid controls and deliberately failing mutants:** Alice's positive grant and outcome in all
  profiles and on live chains; Bob, temporal-only and unregistered denials. 6 `mutant-*` deployments
  (bits 1/2/4/8/16/32) are detected by named repaired-e tests. 17 throwaway source edits are detected
  separately. Results matrix: `ledger/evidence/ae2-property-matrix.md`.
- **Remaining assumptions, failures and limits:**
  - The A-E1 tests were not written failing-first (A1-0004).
  - A-E2 was prepared before E1 integration.
  - The KSSC holds no secrets (SPEC section 3). Single DBC, single witness (E).
  - The GrantReceipt proves an allowed DBC grant existed. It does not prove delivery. Block hashes
    are not verified on chain.
  - The live smoke signs inside Forge.
  - A first live run was rejected with STALE_STATE because of cross-chain clock skew (A1-0004). This
    led to the DBC-time rule (D22).
- **Interface RFCs/ACK message IDs:**
  - Agent 1 sent: RFCs A1-0001/0003/0005/0008; REVIEWs A1-0002/0007/0013; ACKs A1-0009/0012;
    READYs A1-0004/0006/0010/0011/0014.
  - Peer ACKs received: A3-0001/0005/0008/0010 (agent 3); A2-0002/0003/0005 (agent 2, scoped).
- **Reproduction steps for the receiving agent:** install Foundry v1.8.5 (verify the asset hash in
  `ledger/toolchain.json`). Extract `ledger/` from the A1-0014 commit into a scratch directory and run the
  commands above. Python tools use only the standard library; `cast` must be on PATH for the
  crosscheck.
- **Files to freeze and integration prerequisites:** `ledger/src/**`, `ledger/script/**`,
  `ledger/foundry.toml` and `ledger/exports/**` at the pinned commit once v1 is frozen. Integration
  needs two chains with ids 18545/28545, interval mining (or a runner-controlled clock), a funded
  deployer key, and a node that serves historical state (witness reads).

Writer: agent 1 only. This snapshot never replaces the immutable READY message.
