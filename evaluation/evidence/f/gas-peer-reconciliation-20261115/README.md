# M1 gas peer-reproduction reconciliation — 2026-11-15

Classification: tested reconstruction results with Agent 1 peer reproductions
reported in its addressed outbox. This is a read-only reconciliation of the
published messages against Agent 3's retained M1 tables and artifacts. Agent 3
did not execute Forge in this slice. After this reconciliation, Agent 1's
A1-0136 rerun attached raw logs and a rerun script at `origin/agent-1`
`f6f852789d2629cb3b0a846d55793cd27799441d` under
`communication/agent-1/outbox/0136-attachments/`; its addressed note reports
that the 12-entry checksum file verifies. This improves auditability, but Agent
3 has not independently run the script or verified those attachment checksums.

## Scope and source

The three notes cover the complete controlled gas table now summarized as M1,
M1b and M1c:

| Slice | Agent 1 message | Reported Agent 1 command/result | Exact values reported equal |
|---|---|---|---|
| M1 checkpoint + decision paths, and product runtime sizes | A1-0123, `origin/agent-1` commit `208a0b5`; corrected and freshly rerun in A1-0136 | `forge test --root ledger --match-path 'test/CertBench*.t.sol' -vvvv`; exit 0, **6/6 passed** (not 9/9). `forge build --root ledger --sizes`; exit 1 for the three oversized local scripts described below. | 6 gas/calldata rows; 7 product runtime sizes |
| M1b receipt path | A1-0124, `origin/agent-1` commit `0a3ae9a` | `forge test --root ledger --match-path test/CertBench.t.sol -vvvv`; exit 0, 9/9 passed | 3 gas/calldata rows; prior 6 remain unchanged |
| M1c governance actions | A1-0125, `origin/agent-1` commit `94c0003` | `forge test --root ledger --match-path test/CertBenchGov.t.sol --match-test test_gov_ -vvvv`; exit 0, 6/6 passed | 6 gas/calldata rows |

Agent 1 reports using a clean archive of ledger commit `85c59f5`, tree
`36a868305d67c8f546e6bde558ceb8e356962819`, Forge 1.8.5 (build
`51a52c59`) and solc 0.8.37. Its M1 harness was copied unmodified from Agent 3
commit `70a8bfe` (SHA-256
`840970d462c083b233218ccc43aafff6576aadb8b4a31b33f84f7ca7d2296424`). M1b's
harness is from `8152bcc` (SHA-256
`0b650e8246e8d360eb1c101edfea2c0d636ae48a727250ef5c3eff47464924b6`); M1c's
is from `674511f` (SHA-256
`24352dd3ba0e7b327e0b45c148c60be9a77da1ce5a88ac42ef30adc87f755f94`). The
commits and source-tree identity were checked locally. The peer's scratch copy
and execution environment were not available for inspection.

## Reconciliation result

All values in the peer tables match Agent 3's corresponding retained tables:

- M1: `KSSC.acceptState` — 208,290 / 548 B (1 signature), 231,260 / 868 B
  (3), 238,046 / 1,028 B (4); `ACSC.consumeDecision` — 324,323 / 1,380 B,
  342,261 / 1,700 B, 349,053 / 1,860 B.
- M1b: `PSC.reportAttestedOutcome` — 533,754 / 644 B (1 signature),
  553,488 / 964 B (3), 560,290 / 1,124 B (4).
- M1c: `Governance.execute` — AddAuthority 524,214 / 836 B (3 signatures),
  530,980 / 996 B (4); RemoveAuthority 424,421 / 804 B, 431,185 / 964 B;
  SetCaAdmins 446,934 / 836 B, 453,688 / 996 B.

A1-0123 reports all seven product runtime sizes matching: ACSC 12,370 B,
Governance 4,829 B, KSSC 7,767 B, LSC 3,724 B, PSC 12,516 B, RSC 4,174 B,
TMSC 16,127 B (8,449 B below EIP-170). It also refutes its earlier cold-storage
hypothesis: warming the witness-set read changed the 3- and 4-signature
checkpoint measurements by only one gas. The proposed attribution to the
policy-version call and four-entry witness-set scan is source-consistent but
was not split by measurement. The analogous fixed overhead for the receipt
path (about 6.1k gas) is also not decomposed. M1c's action-cost explanation is
qualitative source reading, not a gas breakdown.

`forge build --sizes` reportedly exits 1 because three local Forge scripts
exceed the runtime limit (Deploy 83,849 B; ExportGovernanceVectors 45,094 B;
ExportVectors 39,827 B). They are run as scripts, not deployed products. The
product rows remain below 24,576 B. This resolves the exit-code ambiguity and
does not establish deployed-size behavior beyond the product runtime figures.

## Retained Agent 3 artifact hashes

These hashes identify Agent 3's retained artifacts; A1-0136's newer peer logs
and their hashes are attached under `0136-attachments/` on the exact Agent 1 ref
above and are not duplicated here.

| Artifact | SHA-256 |
|---|---|
| Agent 3 `CertBench.t.sol` at the M1b receipt revision | `0b650e8246e8d360eb1c101edfea2c0d636ae48a727250ef5c3eff47464924b6` |
| Agent 3 `CertBenchGov.t.sol` | `24352dd3ba0e7b327e0b45c148c60be9a77da1ce5a88ac42ef30adc87f755f94` |
| retained initial M1 Forge log | `9b74e0a8369a462d37a9296e9bd78854d4d25176e85c811a2ce082e18e2931dd` |
| retained M1b Forge log | `d623e61d9e5f8516067847c5e3a1b435c0af12ea78be708bf262322a3081114e` |
| retained M1c Forge log | `56b2e01ad00b0d3e3584614de45d5ba70fa4a00eb1e17874a715302ee0eee2cc` |
| retained F runtime-size table | `96e17ab2eb7dcc25d660d28582f4775852eff5289fe5f0ad70fbf4c0f4d3be58` |

The addressed peer-message SHA-256 values at fetched Agent 1 tip
`2acb1962df795701d6751e4d022a1caeaec87a64` are: A1-0123
`f11cb8525e14884a3bb1aeb6224d0576270faa4a0a42241e3c1163d0cd653cec`,
A1-0124 `0d6d77efc5fcd6d86b23d8755351486022dc58795589291fe6b53c00b4643287`,
and A1-0125 `6b89bfcc31d402fec8b19bd0c541dfc7ebe698a408066ad2ca9005d10860e2cb`.

A1-0136 corrects A1-0123's M1 count from 9/9 to 6/6, attaches raw logs and
`run.sh` for a fresh four-command rerun, and reports that all 21 gas/calldata
values and seven runtime sizes match. Its fresh peer result remains correlated
and has not been rerun by Agent 3.

## Limits

The notes describe correlated same-model review on another host; they are not
an independent methodological review, fee estimate, production throughput
measurement, integrated F case, or gate result. The E baseline is the E
profile in the F commit, not historical E bytecode. Each row is a deterministic
fixture run, not a statistical sample. No service was started and no F case
was executed. Plan remains DRAFT; all 32 cases and Gate F remain NOT_RUN.
