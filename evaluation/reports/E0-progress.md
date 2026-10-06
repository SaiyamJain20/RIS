# Phase 1 / E0 progress — 2026-10-07

**Status: E0 PARTIAL, E1 NOT UNLOCKED, gate E NOT RUN.** This report is a restartable progress record, not the RQ1 conclusion or an interface freeze. The user confirmed `/home/karma/Documents/RIS`, `SaiyamJain20/RIS`, branch `agent-3`, independent machines, and review of latest communication files across all branches.

## Source and choices

`evaluation/evidence/source-map.csv` maps 32 source/property rows; `assumptions.csv` separates 22 paper assumptions, ambiguities, reconstruction fills and deliberate deviations. PDF page 1 is journal page 134393. Source provenance hashes and visual checks of Figures 5/6 and Tables 2/3 are recorded in `evidence/e0/source-provenance.json`.

The source supports the six contract roles, GID possession, signed issuer-owned trust lists, long-term/temporal combinations, log-first access processing and isolated temporal key use. It does not give our EIP-712 wire formats, nonce/checkpoint rules, atomic cross-chain delivery logging or precise cryptographic split. The complete-details versus hash-only logging interpretations, optional System-mediated policy, wildcard issuer interpretation and majorityConsent placement remain explicit ambiguities. No JANUS finding/code is used.

A3-0002 proposes the conservative same-issuer emergency fixture, signature-authorized submission, issuer-scoped admin rules, paper latest-appended lists, shared paper-profile relay hop, repaired checkpoint/epoch equality, measured clock skew and expiry-bounded cached retries. D20-D22 are proposals pending peer ACK. A1-0005's GrantReceipt is an E03 extension; A3-0002 proposes a grant-only success path, separate denial handling and no claim of recipient delivery. D23 remains OPEN until agent-1 publishes an exact accepted revision and agent-2 confirms capability.

## Locally executed evidence

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

1. Agent 1 must review the exact schema/vector/source proposal and reply to A3-0002/A3-0003; candidate publication does not replace its ACK.
2. Agent 2 must publish `agent-2`, review source/key/credential flow, propose dependencies, reproduce digests/signatures/mutations and agree to exact schemas, clocks/retry rules and receipt capability.
3. Resolve operation-specific JSON-lines input/result/deployment schemas and ABI/error/retry ambiguities. The envelope's opaque result is explicitly not a fully validated internal record. Existing deployment metadata integer representation still needs explicit review against wire decimal-string rules.
4. Only after three exact ACKs and module smoke checks: freeze `interfaces/v1`, publish INTERFACE_READY, unlock E1 and implement the real adapter runner/service lifecycle against reviewed public exports.
5. Run Alice/Bob/wrong-issuer controls across actual two-chain services; then E2 case matrix/recovery, correspondence model and negative control, repaired receipts, RQ1 report and E3 freeze/ACK gate.

No F/G feature has been implemented. Phase 1 is not complete. Agent 3 has exhausted the currently independent E0 work identified here; the next normative step needs peer artifacts/ACKs. Hourly branch monitoring resumes on meaningful new support. Author self-review is recorded; no independent reviewer was launched because the project explicitly prohibits extra agents.
