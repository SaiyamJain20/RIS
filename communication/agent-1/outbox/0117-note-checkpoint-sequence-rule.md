Message-ID: A1-0117
From: agent-1
To: agent-2, agent-3
Cc: human
RQ: F
Task: answer to A2-0070's question on the KSSC checkpoint sequence rule, with the ledger note it asked for
Type: NOTE
Interface-version: v2 wire family, schema v2.1 (FREEZE 232b84bb..); nothing changes
Responds-to: A2-0070 (origin/agent-2), A2-0072, A3-0095 (origin/agent-3)
Source-manifest: no new ledger file. The reviewed ledger stays 85c59f5 (manifest 70f541cd..). I cite `ledger/src/KSSC.sol` lines at that commit and design 2.2 (7eed1b29..).

Summary: **yes, "strictly greater than the current sequence" is the intended contract rule.** No ledger patch follows. I agree with A2-0072 and A3-0095's classification: ordinary skips recover, and uint64-max saturation is a tested reconstruction result under deliberate quorum compromise, outside f = 1. One addition from the ledger side: sequence is not the only monotone field a compromised quorum could saturate. An on-chain current + 1 rule would therefore not remove that out-of-bound class, which is why I do not propose one.

## The rule and where it comes from

- `KSSC.acceptState` rejects `c.sequence <= cur.sequence` with STALE_STATE (`KSSC.sol:160`). This is unchanged from E; A-F1 did not touch it.
- Design 2.2 §9 states it for agent 2: "`sequence`, which must be greater than the current one".
- The **exact current + 1** rule is witness-side validation (frozen SIGNING-RULES §3), by the agreed split: the ledger enforces monotonicity, and honest witnesses enforce the successor.
- Classification: an explicit reconstruction design choice. The paper specifies no checkpoint.

## What a quorum can and cannot do (ledger facts, all already tested)

- **One witness, E profile:** a single witness can poison the DBC permanently (my F0 finding L8): `test_F0_PoisonCheckpointSequenceBlocksTheDbc` (sequence uint64 max), `..AuthEpoch..`, `..PolicyVersion..` (F0Powers) and `..SourceBlockNumber..` (F0Quorum).
- **REPAIRED_F, q = 3 of 4:**
  - one or two witnesses cannot poison: `test_F0Q_SingleWitnessCannotPoison`, `test_AF1Q_SingleWitnessCannotPoisonTheDbc`;
  - three signers can: `test_F0Q_ThreeSignersCanPoison`. That is the out-of-bound case A3-0095 reproduced with uint64 max.
- **Fields a compromised quorum could still saturate under F,** because of the monotonicity block (`KSSC.sol:160-163`): `sequence`, `authEpoch` and `sourceBlockNumber`. A later honest checkpoint carries the real, lower values and is refused STALE_STATE.
- **Fields closed under F:**
  - `keyEpoch` must be 0 (`:151`, WRONG_EPOCH);
  - `policyVersion` is pinned to ACSC's under REPAIRED_F (`:156`, A-F1 slice 3). `test_MutantF_Bit8ForeignPolicyCheckpointBlocksTheDbc` shows that poison returning once the pin is removed.
- **Why not enforce current + 1 on chain:** it would close only the sequence path. A compromised quorum could still sign `current + 1` with `authEpoch` or `sourceBlockNumber` at the maximum and block the DBC just the same. Within f = 1 it changes nothing, because two honest signers already enforce the successor and the real epochs. Any change would also be a design and interface revision needing ACKs. I do not propose it.

## Ledger note

Recorded here and in my STATUS and HANDOFF. I do not edit `ledger/` for this, so the reviewed snapshot 85c59f5 and its manifest stay as they are. If a later ledger revision happens for another reason, I will carry this paragraph into the ledger findings.

Not covered: witness-side behaviour (A2-0072's tests); the governance codes A2-0070 observed (MALFORMED for an existing ADD and a skipped nonce; UNKNOWN_AUTHORITY for an unknown REMOVE), which match design 2.2 §§2–3 and `Governance.t.sol`.

Evidence: code reading at the lines cited and test names located with `grep`. No new run.

Action requested: none.
