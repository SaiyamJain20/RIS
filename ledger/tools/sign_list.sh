#!/usr/bin/env bash
# TEST-ONLY signed trust-list producer for E2 schedules (A1-0034). READ-ONLY: it sends no transaction.
# Signs one RevocationList (crl) or TemporalAcl (tempacl) with an authority root key, bound to a pinned PBC
# deployment and the PBC latest timestamp t. The output item has the same shape as a bootstrap trustLists entry.
#
# Usage (from the repository root):
#   ledger/tools/sign_list.sh <pbc-rpc-url> <deployment.json> <out.json> <crl|tempacl> <H1|H2|H3|H4> \
#       [--version N] [--valid-for SECONDS] [--revoke S1,S2,...] [--duty LABEL:FROM_AGO:UNTIL_IN]...
#   --version   default: on-chain version + 1; any other value is used as given (e.g. an equal or older one)
#   --valid-for list validity from t (default 86400)
#   --revoke    crl serials, strictly ascending (TMSC rejects others with MALFORMED)
#   --duty      tempacl OnDuty entry [t - FROM_AGO, t + UNTIL_IN] for a fixture label (alice, bob); give
#               entries in ascending gid order (TMSC rejects others with MALFORMED)
# Exit non-zero, with no output file, on a chain id or address mismatch or an unknown authority.
set -euo pipefail

if [ "$#" -lt 5 ]; then
  sed -n '2,14p' "$0" >&2
  exit 2
fi
PBC_RPC="$1"; DEPLOYMENT="$2"; DEST="$3"; LIST_KIND="$4"; LIST_AUTHORITY="$5"; shift 5
LIST_VERSION=0; LIST_VALID_FOR=86400; REVOKED=""; DUTY_GIDS=""; DUTY_FROM_AGO=""; DUTY_UNTIL_IN=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --version) LIST_VERSION="$2"; shift 2 ;;
    --valid-for) LIST_VALID_FOR="$2"; shift 2 ;;
    --revoke) REVOKED="$2"; shift 2 ;;
    --duty)
      IFS=: read -r g a u <<<"$2"
      DUTY_GIDS="${DUTY_GIDS:+$DUTY_GIDS,}$g"; DUTY_FROM_AGO="${DUTY_FROM_AGO:+$DUTY_FROM_AGO,}$a"
      DUTY_UNTIL_IN="${DUTY_UNTIL_IN:+$DUTY_UNTIL_IN,}$u"; shift 2 ;;
    *) echo "unknown option $1" >&2; exit 2 ;;
  esac
done
case "$LIST_KIND" in crl|tempacl) ;; *) echo "kind must be crl or tempacl" >&2; exit 2 ;; esac
LEDGER="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ -f "$DEPLOYMENT" ] || { echo "no deployment file: $DEPLOYMENT" >&2; exit 2; }

read -r EXPECT_CHAIN_ID TMSC RSC < <(python3 -I -c '
import json, sys
d = json.load(open(sys.argv[1]))
p = d["chains"]["pbc"]
print(p["chainId"], p["contracts"]["TMSC"], p["contracts"]["RSC"])' "$DEPLOYMENT")
DEPLOYMENT_SHA256="$(python3 -I -c 'import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$DEPLOYMENT")"

TMP_REL="exports/.signed-list-$$-$RANDOM.json"
trap 'rm -f "$LEDGER/$TMP_REL"' EXIT
export TMSC RSC EXPECT_CHAIN_ID DEPLOYMENT_SHA256 OUT="$TMP_REL" LIST_KIND LIST_AUTHORITY LIST_VERSION LIST_VALID_FOR
[ -n "$REVOKED" ] && export REVOKED
[ -n "$DUTY_GIDS" ] && export DUTY_GIDS DUTY_FROM_AGO DUTY_UNTIL_IN
LOG="$(mktemp)"
if ! forge script "$LEDGER/script/SignList.s.sol:SignList" --sig "sign()" --root "$LEDGER" --rpc-url "$PBC_RPC" >"$LOG" 2>&1; then
  tail -20 "$LOG" >&2; rm -f "$LOG"; exit 1
fi
rm -f "$LOG"
python3 -I -c 'import json, sys; json.load(open(sys.argv[1]))' "$LEDGER/$TMP_REL"
mv "$LEDGER/$TMP_REL" "$DEST"
echo "signed list: $DEST"
