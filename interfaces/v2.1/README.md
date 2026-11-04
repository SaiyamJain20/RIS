# v2.1 schema revision, v2 wire family

Published by Agent3 after exact proposal ACKs A1-0114 and A2-0060 of
amendment manifest 7810ad105330de73920450d82f4850ebb6de0846396e5bb786818e700e49bb0a.
The separate acceptance receipt is communication/E_SOURCE_CLOSURE_ACCEPTANCE.json;
FREEZE.json pins it, this document, the schema, base freeze and inherited payloads.
This sidecar supersedes the copied schema's historical candidate annotations.
Those annotations are preserved to apply the exact ACKed patch without edits.

The schema is the accepted v2 JSON document with exactly two additive operations:
LedgerDeploymentEComplete and its third LedgerDeployment union branch. The new E
carrier uses schemaVersion hmbc-ledger-deployment/v2.1, interfaceVersion v2 and the
twelve-entry module source map. Its ABI container still has only six E contracts.
Governance.sol is a compile-tree input; its presence does not claim E deployment.
The source-closure omission was a reconstruction provenance gap, not a paper flaw.

Old ten-source E remains a historical compatibility carrier with a known omission;
never label it complete for the F source tree. F carriers, D50 preimage, signing
domains, exporter/store layouts, default v1 exports and historical E stay unchanged.
The other thirteen v2 payloads are inherited at their exact old paths and hashes.
No other version strings become v2.1. Select this schema explicitly; the isolated
evaluation.schema_v2 API accepts schema_revision='v2.1' while defaulting to v2.
Structural acceptance is not source/ABI/compiler/runtime authentication.

Migration: Agent1 updates only its opt-in E successor exporter and publishes a
fresh source READY. Agent2 updates its successor adapter's schema selection/tests
and publishes matching consumer mapping/source READY. Both receipt the exact new
freeze/schema hashes. Whole-manifest equality remains mandatory: different
carriers cannot be interchanged with an already pinned manifest.
Rollback: select the original v2 schema and its historical carrier; do not
rewrite old artifacts, claim their map complete or silently drop new sources.

Publication authorizes owned opt-in migration and isolated tests. Source READYs,
matching publication receipts and a separate exact run/tools/config/source FREEZE
with affected ACKs precede integrated services or scenarios. No live E parity,
runtime, TLC, gate or cryptographic claim follows. Gate F and all32 cases NOT_RUN;
G locked. Synthetic, paper-derived HMBC2020 reconstruction only.
