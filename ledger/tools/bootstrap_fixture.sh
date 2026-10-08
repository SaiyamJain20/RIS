#!/usr/bin/env bash
# TEST-ONLY bootstrap producer for the C-E1 runner (A1-0029). READ-ONLY: it sends no transaction.
# Signs, with the synthetic fixture keys, the public artifacts the runner submits after deploying:
# trust lists (H1 CRL, H1 TemporalAcl, H2 CRL), role certificates, GID-possession registrations and
# credential bundles for Alice (Doctor + OnDuty) and Bob (Researcher; registered, policy-denied).
# No private key appears in the output. Every leaf uses a frozen v1 wire shape.
#
# Usage (from the repository root):
#   ledger/tools/bootstrap_fixture.sh <pbc-rpc-url> <deployment.json> <out.json>
# Output: <out.json> (schemaVersion hmbc-ledger-bootstrap/v0). Exit non-zero, with no output file,
# if the RPC chain id or the TMSC/RSC addresses do not match deployment.json.
set -euo pipefail

if [ "$#" -ne 3 ]; then
  sed -n '2,10p' "$0" >&2
  exit 2
fi
PBC_RPC="$1"; DEPLOYMENT="$2"; DEST="$3"
LEDGER="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ -f "$DEPLOYMENT" ] || { echo "no deployment file: $DEPLOYMENT" >&2; exit 2; }

read -r EXPECT_CHAIN_ID TMSC RSC < <(python3 -I -c '
import json, sys
d = json.load(open(sys.argv[1]))
p = d["chains"]["pbc"]
print(p["chainId"], p["contracts"]["TMSC"], p["contracts"]["RSC"])' "$DEPLOYMENT")
DEPLOYMENT_SHA256="$(python3 -I -c 'import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$DEPLOYMENT")"

# forge may write only under ledger/exports (foundry.toml fs_permissions): use a private temp file there.
TMP_REL="exports/.bootstrap-$$-$RANDOM.json"
trap 'rm -f "$LEDGER/$TMP_REL"' EXIT
export TMSC RSC EXPECT_CHAIN_ID DEPLOYMENT_SHA256 OUT="$TMP_REL"
LOG="$(mktemp)"
if ! forge script "$LEDGER/script/BootstrapFixture.s.sol:BootstrapFixture" --root "$LEDGER" --rpc-url "$PBC_RPC" >"$LOG" 2>&1; then
  tail -20 "$LOG" >&2; rm -f "$LOG"; exit 1
fi
rm -f "$LOG"
python3 -I -c 'import json, sys; json.load(open(sys.argv[1]))' "$LEDGER/$TMP_REL"
mv "$LEDGER/$TMP_REL" "$DEST"
echo "bootstrap fixture: $DEST"
