# Bundled ledger ABIs

Byte copies of agent-1's `ledger/exports/abi/{ACSC,KSSC,LSC,PSC,RSC,TMSC}.json` at origin/agent-1
`33a7a5dbb040bce61caf357673722a68ae464cb3` (A1-0014/A1-0015; ABI JSON unchanged since 54262c2) and of `manifest.json` at origin/agent-1
`91add8cc6000d1413bad2ed0aa119a5f26e8c776` (A1-0026, the E1 ledger pin of A3-0023). The six ABI files are byte-identical at 91add8c; `manifest.json`
differs from the 33a7a5d copy ONLY in its `interfaceVersion` label ("v0 proposed" -> "v1"). Only the test fixture reads `manifest.json`; no production code does. They are DATA owned by agent 1; agent 2 never edits them.
`hmbc_protocol.ledger.Ledger` refuses a deployment manifest whose `abi.<Contract>.abiSha256` differs from the bundled file, so a ledger built
from different sources is rejected instead of driven with the wrong encoding. Refresh by copying a newer owner export and updating the pin in `tests/conftest.py`.
