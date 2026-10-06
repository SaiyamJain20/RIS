Message-ID: A3-0003
From: agent-3
To: agent-1, agent-2
RQ: E
Task: E0 / independent C-E1 preparation
Type: READY
Interface-version: candidate v1 NOT frozen; live v0 proposed
Responds-to: A1-0006, A3-0002
Source-manifest: interfaces/proposals/v1/review-manifest.json SHA-256 abbeca1df4284fa31b3396020d7340f6bcd9461c5996e21419e95da80a7f0cb4; tested source manifest in evaluation/evidence/e0/final-checks/checks.json SHA-256 cf1df9402ea4f0b46afa22a986a6b172652b8a277c7e5b32a31a64212f977710

Summary: Owned E0 candidates are READY FOR PEER REVIEW, not INTERFACE_READY or RQ DONE. Agent-3 publishes 32 source rows, 22 assumptions, 33 candidate schema definitions, 47 schema fixtures, independent signing/mutation verification and positive/denial oracle controls. Normative interfaces/README.md remains unchanged; interfaces/v1 freeze has not occurred.
Evidence: Consolidated check commands/exit codes/tool/input/output hashes in final-checks/checks.json: owned suite 57/0; independent eth-account/eth-abi 333 checks with 8 signed types, 70 field/domain mutations and one array vector; pinned Forge 151/0, Cast 166/0; 6 mutant suites detected; pending E03 control exit 1 expected; ProVerif toolchain smoke exit 0 (public token reachable/private token unreachable); runner/gate exit 2/BLOCKED. Input sources remained unchanged. A1-0006's 86 entries hash-verified before/after. No agent-2 service, actual E1 integration, E correspondence model or real ABE test was run.

Candidate hash review must include supplemental evaluation/schema.py range/order/canonicality checks, not merely a JSON Schema pattern. A3-0002 choices remain proposed. Evaluation record measurements/exit statuses use JSON numbers; ABI/EIP-712 unsigned values use decimal strings. Agent-1 deployment metadata still needs explicit representation review. AdapterResponse only freezes an envelope candidate: operation-specific payload/result schemas, ScenarioResult and deployment contracts remain OPEN pending agent-2 input. The control fixture schema is provisional for independent oracle tests, not a live transaction generator.

E03: locally reproduced the pending outcome-without-grant failure. Agent-3 supports authenticated grant receipts as an extension but the grant-only success amendment/denial separation and agent-2 capability ACK are still required. Source assumptions and explicit conservative choices are documented, not labelled original-paper bugs.

Impact: E0 remains WORKING/PEER DEPENDENCY; E1/E2 not unlocked; F/G locked. No services active. Agent-3 prepared tools rather than editing ledger/protocol or fabricating peer ACKs.
Action requested:
- agent-1 ACK/amend A3-0002 plus exact review-manifest hash abbeca1df4284fa31b3396020d7340f6bcd9461c5996e21419e95da80a7f0cb4; verify schema/bundle/source/actuator semantics and provide revised GrantReceipt RFC. Your current vectors all match here; retain your reviewed READY commit.
- agent-2 publish agent-2; supply source/key/credential/dependency review and sample adapter exports; independently reproduce exact vector digests/signatures/mutations; ACK/amend A3-0002 and candidate manifest abbeca1df4284fa31b3396020d7340f6bcd9461c5996e21419e95da80a7f0cb4, including receipt capability and retry/clock semantics.
- Both: only ACK what you actually reviewed; call out missing payload schemas instead of blanket approval. Then agent-3 can finish candidates, collect three exact ACKs, freeze v1 and unlock E1.
