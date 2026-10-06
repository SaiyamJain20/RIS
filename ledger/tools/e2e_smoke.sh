#!/usr/bin/env bash
# Ledger-only two-chain smoke of the legitimate Alice flow against a deployment made by
# tools/deploy_local.sh. Signs as user/witness/relay inside Forge (TEST-ONLY keys); it checks
# contracts, ABI and chain bindings, not agent 2's services, and is not the integration run.
# Usage (repository root): ledger/tools/e2e_smoke.sh <pbc-rpc> <dbc-rpc> <deployment.json> <nonce>
set -euo pipefail
if [ "$#" -ne 4 ]; then sed -n '2,5p' "$0" >&2; exit 2; fi
PBC_RPC="$1"; DBC_RPC="$2"; MANIFEST="$3"; export NONCE="$4"
LEDGER="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
get() { python3 -I -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["chains"][sys.argv[2]]["contracts"][sys.argv[3]])' "$MANIFEST" "$1" "$2"; }
export TMSC RSC PSC ACSC KSSC LSC
TMSC="$(get pbc TMSC)"; RSC="$(get pbc RSC)"; PSC="$(get pbc PSC)"; LSC="$(get pbc LSC)"
ACSC="$(get dbc ACSC)"; KSSC="$(get dbc KSSC)"
RUN_DIR="$(python3 -I -c 'import os,sys; print(os.path.relpath(os.path.dirname(os.path.abspath(sys.argv[1])), sys.argv[2]))' "$MANIFEST" "$LEDGER")"
export OUT_DIR="$RUN_DIR/smoke-nonce-$NONCE"
mkdir -p "$LEDGER/$OUT_DIR"
run() { STAGE="$1" forge script "$LEDGER/script/E2ESmoke.s.sol:E2ESmoke" --root "$LEDGER" --rpc-url "$2" --broadcast --slow >"$LEDGER/$OUT_DIR/$1.log" 2>&1 || { tail -40 "$LEDGER/$OUT_DIR/$1.log"; exit 1; }; echo "stage $1: ok"; }
if [ "$(cast call "$TMSC" 'authEpoch()(uint64)' --rpc-url "$PBC_RPC")" = "0" ]; then run pbc-setup "$PBC_RPC"; fi
run pbc-request "$PBC_RPC"
run dbc-deliver "$DBC_RPC"
run pbc-outcome "$PBC_RPC"
DIGEST_GRANT="$(cast abi-decode 'f()(bytes32,bytes32)' "$(cat "$LEDGER/$OUT_DIR/grant.hex")")"
DIGEST="$(echo "$DIGEST_GRANT" | sed -n 1p)"; GRANT="$(echo "$DIGEST_GRANT" | sed -n 2p)"
{
  echo "requestDigest=$DIGEST"
  echo "grantId=$GRANT"
  echo "pbc.requestLogId=$(cast call "$LSC" 'firstRequestLogId(bytes32)(uint256)' "$DIGEST" --rpc-url "$PBC_RPC")"
  echo "pbc.outcomeLogId=$(cast call "$LSC" 'outcomeLogId(bytes32)(uint256)' "$DIGEST" --rpc-url "$PBC_RPC")"
  echo "pbc.lscLogCount=$(cast call "$LSC" 'logCount()(uint256)' --rpc-url "$PBC_RPC")"
  echo "dbc.getGrant=$(cast call "$KSSC" 'getGrant(bytes32)(bytes32,bytes32,address,uint64,uint64,bool)' "$GRANT" --rpc-url "$DBC_RPC" | tr '\n' ' ' | sed 's/ *$//')"
  echo "dbc.accessLogCount=$(cast call "$ACSC" 'accessLogCount()(uint256)' --rpc-url "$DBC_RPC")"
} | tee "$LEDGER/$OUT_DIR/summary.txt"
