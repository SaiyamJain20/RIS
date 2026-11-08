# C-F1 deployment context slice

Implements the accepted candidate2 D50 reconstruction/fixture checks in
interfaces/v2/BOUNDARY.md §§Deployment exports and D50. F0 acceptance is
03dcf485668430b1f28552d2bbafcae9a6c64ff9df0090c50bcae753793a432d.

1. Tests first: independent synthetic successor E/F deployments, raw code and
   per-read block labels; controls for wrong chain/build/getters/wiring/fixture,
   missing observations and a self-consistent forged export. Observe RED.
2. Add evaluation-only pure reconstruction and export comparison. Explicit
   successor carrier selection; no existing consumer changes. Observe GREEN.
3. Review scope/negative controls, run focused and root tests with input hashes,
   refresh exact peer communication, publish only reviewed owned paths.

Pre-flight: schema_v2 supplies declared shape/width semantics; this slice supplies
independent observed-value joins. certificates_v2 requires caller context but is
not switched to this API yet. Exporter history/WAL/native-effect joins and the
fault oracle/model remain separate unfinished C-F1 tasks.

Ruling: use normalized read records with an explicit anchor per code/getter row
and a confirming chain anchor, supplied by the future collector. This is an
internal evaluator API, not a shared wire revision. No RPC collector, source
attestation, persistent store, gate or timing claim follows; a fabricated but
consistent observation remains undetectable without independent acquisition.
MAX_ADMINS is a separately supplied pinned compiled attestation (Governance has
no getter), while maxGovernanceTtl/governanceChainId are observed getters.

Review ruling: contract addresses are namespaced by chain. An initial extra
global uniqueness assertion rejected valid repeated addresses on distinct
chains. Added the positive namespace test first (1 RED/97 PASS), then removed
that unsupported assertion. No shared contract or expected behavior changed.

User prohibits extra agents/worktrees: work inline in agent-3, with correlated
author review. No new shared fields, dependency, peer writes, services or main
push. Preserve all historical evidence and publication bytes.
