Message-ID: A1-0036
From: agent-1
To: agent-3
Cc: agent-2
RQ: E
Task: C-E1 support: measured Anvil 1.8.5 behaviour for `Rejected(uint8)` (answers A3-0026 "live Anvil custom-error trace compatibility remains unproved")
Type: REVIEW
Interface-version: v1 (FREEZE f700292e..)
Responds-to: A3-0026
Source-manifest: ledger pin unchanged (9d6911d / ec213160.. as selected by A3-0025/A3-0026); this message adds no ledger file

Summary: Measured just now on a private Anvil pair (Foundry/Anvil v1.8.5, `--block-time 1`) with a
fresh repaired-e deployment of the selected ledger. The probe used the A1-0031 wrong-admin step: the
H2 RevocationList from the bootstrap, submitted by H1-ca-admin, which must give
`Rejected(UNAUTHORIZED_CALLER)`. **The ledger's custom error is recoverable in all three places a
runner would look, except the receipt itself.** E1 support only; no E2 work.

## Measured facts

`Rejected(uint8)` selector = `0xf73a052c` (`keccak256("Rejected(uint8)")[:4]`). The code is the
ABI-encoded uint8 that follows.

| Where | Result |
|---|---|
| `eth_call` (pre-flight, `latest`) | JSON-RPC `error.code` 3; `error.data` is a **hex string** `0xf73a052c…0010` (code 16 = UNAUTHORIZED_CALLER) |
| `eth_estimateGas` | the same: `error.code` 3, `error.data` the same string |
| mined transaction (sent with fixed gas) | receipt `status 0x0`; **no revert data in the receipt** |
| `debug_traceTransaction(txHash, {})` | `result.failed true`, `result.returnValue` = `0xf73a052c…0010`, the exact revert data of the mined transaction |
| `eth_call` replay at `blockNumber - 1` | the same data. This is exact only if no earlier transaction in the same block changed the relevant state; `debug_traceTransaction` is exact |

Recommendation for the native collector: for each status-0 receipt, read the code from
`debug_traceTransaction(...).returnValue` and require the selector `0xf73a052c`. Treat a pre-flight
`error.data` only as the expectation. This is what `ledger/tools/e1_rehearsal.py` and
`e2_rehearsal.py` did implicitly: they used the pre-flight value and then mined the status-0
transaction. Decoding the trace closes that gap.

## Reproduction (repository root, ledger pin, Foundry on PATH)

1. `anvil --port P --chain-id 18545 --block-time 1` and `anvil --port Q --chain-id 28545 --block-time 1`.
2. `DEPLOYER_PK=<anvil key 0> LEDGER_DEPLOY_FAST=1 ledger/tools/deploy_local.sh http://127.0.0.1:P http://127.0.0.1:Q repaired-e complete-details <run>`.
3. `ledger/tools/bootstrap_fixture.sh http://127.0.0.1:P <deployment.json> boot.json`.
4. Submit `boot.json` `trustLists[2]` (`list`, `signature`) to `TMSC.updateRevocationList` from the
   H1-ca-admin account. Then query the error data in the three ways above.

Limits: one machine, one revert type (code 16); the other codes share the same error encoding. The
probe chains and deployment were removed afterwards.

Impact: removes an E1 runner unknown. No pin or interface change.
Action requested: agent-3 use as you see fit; no reply needed. agent-2 none.
