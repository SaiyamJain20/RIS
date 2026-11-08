# HMBC2020 v2 candidate 1 — mapping review only

**NOT FROZEN. No mapping ACK, F0 freeze, implementation or execution authorization.**
This is a paper-derived reconstruction and a proposed F extension, using synthetic
fixtures and symbolic payload processing. Frozen `interfaces/v1/**` is unchanged.

Agent 1 A1-0104 and Agent 2 A2-0053 ACK the exact candidate8 *design*, in their
respective scopes. The receipt and file-changing Git provenance are in
`evaluation/evidence/reviews/f0-v2-candidate1-20261104/input-provenance.json`.
Those ACKs do not approve this proposal. Intended design inputs are:

| Owner input | SHA-256 |
|---|---|
| ledger/f0/A-F1-DESIGN.md | 7eed1b29e79144d88d6b5bba33a414e4fcb6dc8fa8cb31262c0742e3baaebfd0 |
| protocol/f0/D50-DEPLOYMENT-BINDING.md | b178e0a8942dc1d4c99165a4b526c30813efc17dbbeb216492b9be6940247a18 |
| protocol/f0/SIGNING-RULES.md | 23a88159c869e767d4305236c089c6682a5a6be070afa43756e24b5f3f7919fb |
| protocol/f0/SUCCESSOR-WIRE.md | 065c46db8f3308e531b6b83db4bbf23cbe26f861a983a0af39ac3e86d505aa58 |
| protocol/f0/MANIFEST.sha256 | 097d8ed8a8d4e094195f620f53b9c7839a2426210538c75ed06ad16c5f9fa6a0 |

The JSON Schema is a complete candidate document derived from frozen v1, with
new definitions and operation associations. It is accompanied by mandatory
semantic rules in BOUNDARY.md; JSON Schema alone cannot enforce signature
recovery, numeric ordering, expiry, source truth, timing or durable state.
No running consumer is switched to this file. Carried Scenario/RunManifest/E0
definitions remain E definitions; the prospective F matrix is a separate planning
artifact, not a fabricated F result schema or execution result.

The review bundle contains schema, reason/code table, four-witness mapping,
six real synthetic signing vectors (including three governance actions), four
pool success responses, twelve re-encoded owner wire examples, and the exact
owner D50 vectors. E typed-message encodings are retained; only the successor
carrier and F witness-set value change. Governance vectors use two independent
Python encodings, not a run of the proposed Solidity implementation.

The manifest covers exact proposal bytes. Reproduce the planning audit and
vectors using the existing environment, without services or installations:

```
python3 evaluation/evidence/reviews/f0-v2-candidate1-20261104/prepare.py
.venv/bin/python evaluation/evidence/reviews/f0-v2-candidate1-20261104/vectors.py
.venv/bin/python evaluation/evidence/reviews/f0-v2-candidate1-20261104/verify.py
```

The preparation script pins the fetched owner revisions and original Agent3
base. Its Git provenance capture is a historical audit, so rerunning it from a
later HEAD changes that capture. Schema/vector bytes are deterministic for those
inputs. The verifier checks proposal syntax and illustrative relationships. It
does not implement or prove the future adapter's mandatory semantic checks.

Two coordinator mapping choices need explicit owner review:

1. F deployment manifests use base `profile="repaired-f"`, enum `"3"`; mutation
   bits and `mutantNote` identify source mutants. `mutant-f-q2` is the experiment
   label, with threshold 2 in all three sets, rather than a fifth D50 base profile.
   This matches D50's four-name closed vocabulary. Baseline is mutations 0/q3;
   F bits 6/7/8 are named exactly as Agent1 design §6, and combinations remain
   representable up to bit 8. It is a new *mapping proposal*, not an owner ACK.
2. The q2 control assembles two single-witness responses in the runner; the
   baseline pool Collection remains q3. If owners intend the production pool to
   emit q2 Collection responses, this schema needs an exact revised mapping.

Agent2 must also settle the pre-existing E mutant-profile spelling versus D50's
base-name vocabulary before v2 E-mutant consumers are implemented: current E
manifests carry `mutant-no-*` names, whereas D50 says `B.profile.name` copies
`manifest.profile` but its reference rejects those names. Historical v1 E stays
reproducible. This is a design mapping ambiguity, not a measured vulnerability.

Review these choices and BOUNDARY.md against exact manifest hashes. Resolve
any changes with a new candidate; obtain both owners' exact mapping ACKs, then
publish the separately ACKed F0 freeze. Source READY and execution FREEZE remain
later gates. All 32 F cases remain NOT_RUN; G remains locked.
