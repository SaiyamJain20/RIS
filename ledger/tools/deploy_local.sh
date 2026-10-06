#!/usr/bin/env bash
# Deploy the six HMBC roles to two ALREADY RUNNING EVM nodes and write a deployment manifest.
# This script never starts or stops chains; the integration runner (agent 3) owns them.
#
# Usage (from the repository root):
#   DEPLOYER_PK=0x... ledger/tools/deploy_local.sh <pbc-rpc-url> <dbc-rpc-url> <profile> <log-mode> <run-id>
#     profile:  paper-strict | paper-minimal | repaired-e
#     log-mode: hash-only | complete-details
# Output: ledger/exports/deployments/<run-id>/{pbc-stage,dbc-stage,deployment}.json
# Chain ids default to 18545 (PBC) and 28545 (DBC); override with PBC_CHAIN_ID / DBC_CHAIN_ID.
set -euo pipefail

if [ "$#" -ne 5 ]; then
  sed -n '2,11p' "$0" >&2
  exit 2
fi
PBC_RPC="$1"; DBC_RPC="$2"; PROFILE_NAME="$3"; LOG_NAME="$4"; RUN_ID="$5"
: "${DEPLOYER_PK:?set DEPLOYER_PK to a funded key on both chains}"
case "$PROFILE_NAME" in
  paper-strict) PROFILE=0 ;; paper-minimal) PROFILE=1 ;; repaired-e) PROFILE=2 ;;
  *) echo "unknown profile $PROFILE_NAME" >&2; exit 2 ;;
esac
case "$LOG_NAME" in
  hash-only) LOG_MODE=0 ;; complete-details) LOG_MODE=1 ;;
  *) echo "unknown log mode $LOG_NAME" >&2; exit 2 ;;
esac
case "$RUN_ID" in
  *[!A-Za-z0-9._-]*|"") echo "run-id must match [A-Za-z0-9._-]+" >&2; exit 2 ;;
esac

LEDGER="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PBC_CHAIN_ID="${PBC_CHAIN_ID:-18545}" DBC_CHAIN_ID="${DBC_CHAIN_ID:-28545}"
export PROFILE LOG_MODE DEPLOYER_PK
export OUT_DIR="exports/deployments/$RUN_ID"
mkdir -p "$LEDGER/$OUT_DIR"

field() { python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' "$1" "$2"; }

forge build --root "$LEDGER" >/dev/null
python3 -I "$LEDGER/tools/export_abi.py" >/dev/null

STAGE=pbc forge script "$LEDGER/script/Deploy.s.sol:Deploy" --root "$LEDGER" --rpc-url "$PBC_RPC" --broadcast --slow
export PSC LSC TMSC RSC
PSC="$(field "$LEDGER/$OUT_DIR/pbc-stage.json" psc)"
LSC="$(field "$LEDGER/$OUT_DIR/pbc-stage.json" lsc)"
TMSC="$(field "$LEDGER/$OUT_DIR/pbc-stage.json" tmsc)"
RSC="$(field "$LEDGER/$OUT_DIR/pbc-stage.json" rsc)"

STAGE=dbc forge script "$LEDGER/script/Deploy.s.sol:Deploy" --root "$LEDGER" --rpc-url "$DBC_RPC" --broadcast --slow
export KSSC
KSSC="$(field "$LEDGER/$OUT_DIR/dbc-stage.json" kssc)"

STAGE=finalize forge script "$LEDGER/script/Deploy.s.sol:Deploy" --root "$LEDGER" --rpc-url "$PBC_RPC" --broadcast --slow

python3 -I "$LEDGER/tools/make_manifest.py" "$LEDGER/$OUT_DIR" "$PROFILE_NAME" "$LOG_NAME" \
  "$PBC_CHAIN_ID" "$DBC_CHAIN_ID" "$PBC_RPC" "$DBC_RPC"
