# Candidate1 owner reviews: reproduction and correction preparation

This is F0 mapping preparation for the paper-derived HMBC2020 reconstruction.
It is not candidate2 publication, a mapping ACK, a freeze or an F result.
Synthetic fixtures only. Candidate1 and frozen v1 remain byte-identical.

Inputs: A1-0105 at `adb668dfa643a77732c6b3093c5b4053b798aa12` and A2-0054
at `9ced19af68bec8348d696f4db510fd9cfca497f4`, reviewing Agent3
`4de6274e8479659f2808552061585895bb897b2d`. Full hashes and file-changing
provenance are in `input-provenance.json`. Neither peer gave a mapping ACK.

Run from the repository root:

```
.venv/bin/python evaluation/evidence/reviews/f0-v2-owner-review-20261104/review.py
```

The script verifies 350 ledger, 142 protocol E, 36 protocol F0 and 11 protocol
review-manifest entries directly from pinned Git blobs. It verifies candidate1's
two manifests and selects 325 communication paths by changing-commit ancestry,
rejecting incomparable conflicting revisions. It does not copy peer mailboxes
or import or execute peer modules. Production source delta checks are explicit
in the script; these do not claim a new runtime regression pass.

`shape-checks.json` records 46 paired schema verdicts. Candidate1 accepts invalid
name/enum pairs, duplicate binding witnesses, empty retry report arrays, unordered
or repeated adopted reporters, and zero Governance admins. The prospective
corrections reject them while preserving all 12 wire and four success examples,
both binding positives and all 11 legal adopted-reporter subsets. Additional
assertions cover governance constants, preserved v1 ABI-entry meaning, the v2
E-carrier version tag and four q2/code-mask combinations. These are **tested
proposal-shape results**, not runtime vulnerabilities or source implementations.

`prospective-schema.json` is generated review preparation only. It contains the
schema portions of M1–M3, P1, P4/P5 and N1. Its title/status explicitly identify
the incomplete draft. It is not installed under `interfaces/`, consumed by the
evaluator, or accompanied by a final candidate manifest. It still depends on
unpublished owner revision8, including its changed D50 F vector and closed CLI
layouts. Do not treat its old owner-vector pins as candidate2 pins.

## Correction plan and dependencies

| Review item | Prepared disposition / acceptance condition |
|---|---|
| M1 | Required fixture.governance bounds 120/8; live maxGovernanceTtl equality and compiled MAX_ADMINS attestation in final boundary. |
| M2 | Both successor E/F carriers use deployment/v2. Rename successor ABI entry LedgerAbiEntryV2, restore LedgerAbiEntry's frozen v1 meaning. Successor E has all six immutable fields; historical E carrier stays untouched. Owner adds opt-in export only after freeze. |
| M3 | Classification from live masks/thresholds, never mutantNote. Baseline mask0/q3, q2 mask0/q2, code mutant nonzero/q3. Reject nonzero/q2 structurally. Multiple code bits remain representable but are not single-check-removal evidence without a separately specified schedule. |
| M4 | Final boundary compares all five masks, all three complete ordered witness sets, four profile getters=3, and Governance target/chain/version/TTL getters. Owner's full-mask interpretation is accepted as clarification of MUT_ALL0..511, consistent with design section1 and D50; exact complete mapping ACKs still required. No source implementation is asserted. |
| P1 | Exact four name/enum pairs and unique witnesses prepared. Closed manifest-name normalization and stage2/stage7 refusal rules are proposed owner changes: wait for revision8 text/reference/tests/vectors and renewed affected design ACKs. |
| P2 | Final boundary: well-formed unconfigured selector -> MALFORMED without reason; declared version mismatch -> STALE_STATE/WITNESS_SET_MISMATCH. These are successor obligations, not retroactive claims about historical E reasons. |
| P3 | Final boundary: pool quorum is always3; F opens only n4/threshold2or3. Runner builds q2 from distinct single-witness replies and sorts recovered addresses. Three contract sets must match. |
| P4 | Present report arrays must be nonempty; schema patch prepared. Wait for exact revised wire/checker pin. |
| P5 | Enum of all11 ascending unique subsets size2..4 prepared. |
| P6 | Final boundary uses adopted.message.expiresAt. |
| P7 / N3 | Owner regenerates F D50 vector with interfaceVersion v2. Coordinator must independently reproduce its new hash before final candidate2. Never edit the historical owner vector in candidate1. |
| N1 | Zero admins rejected structurally in both GovernanceAction and copied CollectGovernanceInput. Runtime strict ascent remains required. |
| N2 | Width bound remains mandatory semantic validation; this shape probe does not assert format-checking enforcement. |
| N4 | Final boundary and F runner plan retain native Governance/TMSC events under owner-compiled ABIs; no event inferred from a signature. |
| Unwritten exports | Agent2 must publish closed --binding and witness_state --evidence layouts/checker/vectors. Then complete mapping and exact layout ACKs before F0 freeze. |

Agent2's published review accepts M4 and profile/q2 choices in protocol scope;
Agent1 accepts them with its stated conditions. That is review input, not the
missing complete schema/vector mapping ACKs. The promised D50 amendment changes
accepted design inputs: renew affected ACKs before adopting final pins. D4/D6
remain owner source tasks; strict-parser cases must include deviating-witness
inputs, not only adapter witnessIndex.

The peers report 26 Solidity tests/two expected failing encoding controls and
99 protocol signature checks/997 binding corruptions. Their logs are pinned and
hash-verified here; **Agent3 did not rerun them**. Same-model review remains
correlated. No new Forge, TLC, service, RPC, actual pool, process timing, durability,
runtime regression suite or F gate was run. All32 F cases remain NOT_RUN; G locked.
No human research action is needed. Next producer is Agent2 revision8, followed
by complete candidate2, exact affected design/mapping ACKs and separate F0 freeze.
