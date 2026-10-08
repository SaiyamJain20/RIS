# Bundled ledger ABIs

Byte copies of agent-1's `ledger/exports/abi/{ACSC,KSSC,LSC,PSC,RSC,TMSC}.json` and `manifest.json` at origin/agent-1
`33a7a5dbb040bce61caf357673722a68ae464cb3` (A1-0014/A1-0015; ABI JSON unchanged since 54262c2). They are DATA owned by agent 1; agent 2 never edits them.
`hmbc_protocol.ledger.Ledger` refuses a deployment manifest whose `abi.<Contract>.abiSha256` differs from the bundled file, so a ledger built
from different sources is rejected instead of driven with the wrong encoding. Refresh by copying a newer owner export and updating the pin in `tests/conftest.py`.
