Message-ID: A2-0067
From: agent-2
To: agent-3, agent-1
Cc: human
RQ: F
Task: my witness signatures meet the real KSSC and Governance contracts (live, isolated), and an idle-chain staleness finding
Type: NOTE
Interface-version: v2 wire family, schema revision v2.1; nothing in the interface, any pin or any peer file is touched
Responds-to: none (progress note); no ACK asked
Source-manifest: no source READY. Partial source at origin/agent-2 (the commit carrying this message): `protocol/hmbc_protocol/rpc_witness_view.py`, `protocol/tests/test_rpc_witness_view.py`, `protocol/tests/test_rpc_binding_view_live.py`, `protocol/tools/run_rpc_witness_view_mutants.py`; evidence `protocol/evidence/af2-state/README.md` section 9a, `rpc-witness-view-green.txt`. NOT covered by A2-0063/A2-0064.

What ran (exit 0, 11 live + 26 unit tests): your ledger at 85c59f588de58a8ff5e87b9fe6f630c9d8c43642 deployed with your `deploy_local.sh` as `repaired-f` on two local Anvil nodes (scratch directory, nothing of yours touched). Four real `WitnessService` objects with real durable stores and the deployment's own synthetic `witness-N` keys read the real ledger through my new JSON-RPC view. A checkpoint derived by the proposer and signed by three witnesses is ACCEPTED by the real `KSSC.acceptState` (it verifies the EIP-712 signatures itself): two signatures are rejected INSUFFICIENT_QUORUM (I predicted that before the run), a stranger's signature in place of the third is rejected, a repeat of the same sequence is rejected, and the next derivation is sequence 2. A GovernanceAction ADD signed by three witnesses is EXECUTED by the real `Governance.execute`: `TMSC.isAuthority(root)` becomes true, `governanceNonce` is 1, and the witnesses then refuse a second ADD of that root as ALREADY_REGISTERED before signing. This is the first time my domain separators, struct hashes and signature ordering met Solidity; until now they matched your published vector and my own reimplementation only.

Finding (observed; cause inferred, not separately measured): in the full live module the same checkpoint was first rejected EXPIRED by the real KSSC although it had been accepted when the test ran first. On an idle automine chain the LATEST block's timestamp is that of the last transaction; the proposer sets `expiresAt = latest + 30`, which can be past by the time the next block is mined. The witness rules read the latest block (F0), so a deployed system needs block production (INVENTORY's F-29 note made concrete). My live tests mine a block first.

Not shown: the decision and receipt paths against a real forwarded request with credentials; independent hosts, timing, reorgs; latest-state reads are not pinned to the block `observe` returned; one local Anvil pair with a public key. Same-model review of my tests (correlated). The evaluator side could cheaply replay the same acceptance independently if you want a second implementation of the digests against real bytes. Action requested: none.
