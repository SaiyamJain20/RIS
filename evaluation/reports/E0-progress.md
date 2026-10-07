# Phase 1 / E0 progress — 2026-10-07

**Status: E0 PARTIAL, E1 NOT UNLOCKED, gate E NOT RUN.** This report is a restartable progress record, not the RQ1 conclusion or an interface freeze. The user confirmed `/home/karma/Documents/RIS`, `SaiyamJain20/RIS`, branch `agent-3`, independent machines, and review of latest communication files across all branches.

## Source and choices

`evaluation/evidence/source-map.csv` maps 37 source/property rows; `assumptions.csv` separates 27 paper assumptions, ambiguities, reconstruction fills and deliberate deviations. PDF page 1 is journal page 134393. Source provenance hashes and visual checks of Figures 5/6 and Tables 2/3 are recorded in `evidence/e0/source-provenance.json`.

The source supports the six contract roles, GID possession, signed issuer-owned trust lists, long-term/temporal combinations, log-first access processing and isolated temporal key use. It does not give our EIP-712 wire formats, nonce/checkpoint rules, atomic cross-chain delivery logging or precise cryptographic split. The complete-details versus hash-only logging interpretations, optional System-mediated policy, wildcard issuer interpretation and majorityConsent placement remain explicit ambiguities. No JANUS finding/code is used.

A3-0002 proposes the conservative same-issuer emergency fixture, signature-authorized submission, issuer-scoped admin rules, paper latest-appended lists, shared paper-profile relay hop, repaired checkpoint/epoch equality, measured clock skew and expiry-bounded cached retries. A1-0007 ACKs the ledger items for D20-D22; agent-2 agreement is pending. A1-0008 revision 2 supersedes the old receipt proposal; agent 3 ACKs the exact RFC in A3-0005. D23 remains OPEN until agent-2 confirms capability/semantics. No receipt schema field migration or implementation is authorized yet.

## Original checkpoint evidence (unchanged historical scope)

| Check | Result | Scope |
|---|---|---|
| Evaluation suite | 57 passed, 0 failed | Schema/vector/oracle/preflight/evidence tests; no live protocol integration |
| Independent eth-account/eth-abi vector cross-check | 333 checks; 8 signed vectors; 70 mutations; 1 record-array vector; no mismatch | Encoding/signature recovery only; incomplete/empty packs rejected |
| Candidate schema fixture validation | 47 cases, no mismatch | Signed/bundle fields and numeric overflow/unknown-field negatives; exact count in schema-vector-check.json |
| Pinned agent-1 Forge suite | 151 passed, 0 failed | Ledger-only module evidence, source snapshot f643805 |
| Pinned Cast cross-check | 166 checks, no mismatch | Peer tool using independent Alloy encoding, reproduced locally |
| Pinned ledger mutant suites | 6/6 detected; expected property failures only | Deliberate check removals, not original-paper vulnerabilities |
| Pending E03 ledger control | exit 1, expected failure | Current repaired-e records an outcome without DBC grant evidence; repair pending |
| ProVerif 2.05 smoke | public token reachable; private token unreachable | Toolchain functionality only; not E correspondence/secrecy proof |
| Runner and gate preflight | exit 2/BLOCKED | Rejects missing freeze/services; no synthetic PASS |

The source/input/output hashes, exact commands, tool versions and failures are attached under `evaluation/evidence/e0/` and `toolchain.json`. The ledger READY manifest has 86 entries and SHA-256 `4d7802b70d731cf5ba3ac3b38fac32ffddaf0400d5b0e7fccfb9117815bfd577`; every entry still matches after local tests. Sample deployment traces remain agent-1 evidence. No integration services were started here.

The vector verifier's first attempt missed the AccessRequest domain dependence on sourceChainId/psc; both were corrected and rechecked. Initial missing-module/stub failures and later behavior RED logs are retained. ProVerif's first build failed at the optional GUI ocamlfind dependency; the command-line core was rebuilt successfully with `-nointeract native`. A Foundry signature-cache warning appeared on the first run; compilation/tests still passed. No failed experiment is labelled REFUTED or omitted.

## What remains mandatory

1. Agent 1 supplied the scoped non-receipt candidate ACK (A1-0009) and corrected READY (A1-0010), now reproduced as described below. Complete receipt/adapter/operation/result/deployment schema agreement and any new exact revision ACKs remain required; this is not a whole-interface freeze.
2. Agent 2 must publish `agent-2`, review source/key/credential flow, propose dependencies, reproduce digests/signatures/mutations and agree to exact schemas, clocks/retry rules and receipt capability.
3. Resolve operation-specific JSON-lines input/result/deployment schemas and ABI/error/retry ambiguities. The envelope's opaque result is explicitly not a fully validated internal record. Agent 3 agrees with A1-0007 that deployment ABI unsigned values stay decimal strings; agent-2 and the full deployment schema review remain pending.
4. Only after three exact ACKs and module smoke checks: freeze `interfaces/v1`, publish INTERFACE_READY, unlock E1 and implement the real adapter runner/service lifecycle against reviewed public exports.
5. Run Alice/Bob/wrong-issuer controls across actual two-chain services; then E2 case matrix/recovery, correspondence model and negative control, repaired receipts, RQ1 report and E3 freeze/ACK gate.

No F/G feature has been implemented. Phase 1 is not complete. Agent 3 has exhausted the currently independent E0 work identified here; the next normative step needs peer artifacts/ACKs. Hourly branch monitoring resumes on meaningful new support. Author self-review is recorded; no independent reviewer was launched because the project explicitly prohibits extra agents.

## A1-0007 review follow-up

Reviewed owner messages from file-changing commit 589a05331a1a9a9cfe99eee2da70b980a44e5317. A1-0007 SHA-256 7489f8ec3b5b196573bb1748ed43faa208802eb9048c384bd878e992d8f61e49; A1-0008 SHA-256 c42d064ce31a6c482f26640e67d1c541e3681db7239b89147b10e6b2e35aefea. The full across-branch provenance snapshot and peer manifest inspection are under evaluation/evidence/e0/review-a1-0007/. No new agent-2 branch was present.

S-1: explicit EIP-712 encodeType annotations and RoleCertificate property order match owner vectors; S-2: empty CredentialBundle is MALFORMED; S-3: direct/nested zero-GID temporal entries are MALFORMED. Ten regression cases failed before fixes and passed afterward (31 schema tests). S-4 is an owner-side change reported as 154 ledger tests; this count is not independently reproduced for the newer unready revision. Historical 151-test evidence remains tied to f643805.

M-1 corrects implemented E validation/update/registration functions. M-2 adds explicit certificate-time, paper-grant lifetime/recipient, partial replay and log-variable fills. M-3 fixes signed CRL wording and ACSC page 10–11. M-4 records registration attempt/success logging-order ambiguity. Rows S33–S37 and assumptions A23–A27 are gap fills/ambiguities, not discovered paper vulnerabilities.

No integration or formal correspondence claim follows from these revisions. Author self-review only; receipt revision 2 and complete interface freeze still need agent-2 support. Final owned verification and the revised candidate hash are recorded by the subsequent READY message A3-0006.

Current follow-up verification: full owned suite 67 passed; independent vector checks333/0; schema fixtures53 (10 valid/43 invalid), zero mismatches; prompt/diff checks exit0; runner/gate expected2/BLOCKED. Checks SHA-256 08a26fa290feed61f024dac17f18a751841f126ca60502d9eb49c9ef6ce0a10e. Revised 16-file candidate manifest SHA-256 e2dde1994fb1146e0df979a955cc2c2ada7ce05e88eb55bf26c26fdf91a815c7. Packaging metadata is added after stable command inputs; no runtime/fixture changes follow verification.

## Corrected ledger READY and scoped candidate ACK

A1-0009/A1-0010 from file-changing commit e351be5 resolve the prior metadata blocker. A1-0009 ACKs exact candidate e2dde199.. for non-receipt ledger semantics only; its stated exclusions remain open. A1-0010 pins ledger589a053/hash1c4f4fc8.. (87 files), superseding A1-0006. Agent3 now independently reproduced ledger154/0, Cast166/0 and six mutant suites; owned67/0/vector333/0; source/peer hashes stable. E03 pending test still exits1, runner/gate2 BLOCKED, PV trivial smoke only. All ten expected outcomes match, checks SHA-256 1b9283db8d6b08d80234e60eacad3067aaa0a981cce7f7e8e93af3a1c795cf8c under evaluation/evidence/e0/ready-a1-0010/. No15-edit source mutation smoke, current deployments, E correspondence or real integration was rerun. Candidate bytes remain unchanged; no full freeze. Missing agent2 and complete schema/receipt agreement still prevent E0 completion/E1 entry.
