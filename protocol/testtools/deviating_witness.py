"""TEST-ONLY deviating witness: signs a DELIBERATELY inconsistent GrantReceipt so a mutation/defence-in-depth control can run (A3-0016, A1-0020).

This is a mutation fixture, not an HMBC attack and not an honest-witness behaviour: the honest witness (hmbc_protocol.witness) never signs such a receipt and
cross-checks the PBC record. The tool exists because the runner must not hold the witness key (Option A custody), yet the receipt-binding control needs a
validly-signed receipt whose request digest / gid / dataId disagree with the forwarded request.

    python -m testtools.deviating_witness --deployment deployment.json receipt --grant-id 0x.. --field requestDigest|gid|dataId [--value V]

Prints ONE JSON object {schemaVersion, testOnly, deviation:{field, original, altered}, receipt, signatures:[sig]} and nothing else; the runner receives only the signed
artifact, never a key. The receipt is built AT RUN TIME from the real grant (KSSC.getGrant at the DBC head), the real PSC/chain EIP-712 domain and the real grant
expiry; exactly ONE field differs from the consistent receipt. It refuses unless the deployment declares TEST-ONLY synthetic keys, refuses a grant that does not
exist/is not allowed, and refuses every field except the three the PSC binds to its forwarded record.
"""
from __future__ import annotations

import argparse
import json
import sys

from eth_utils import keccak, to_checksum_address

from hmbc_protocol import eip712, keys, messages, wire
from hmbc_protocol.ledger import Ledger

BOUND_FIELDS = ("requestDigest", "gid", "dataId")


def _altered(field: str, original: str) -> str:
    h = keccak(b"hmbc-test-deviation:" + field.encode() + b":" + bytes.fromhex(original[2:]))
    return "0x" + (h[:20] if field == "gid" else h).hex()


def deviating_receipt(led: Ledger, grant_id: str, field: str, value: str | None = None) -> dict:
    if "TEST-ONLY" not in str(led.deployment.get("fixture", {}).get("keyDerivation", "")):
        raise SystemExit("refusing: the deployment does not declare TEST-ONLY synthetic keys")
    if field not in BOUND_FIELDS:
        raise SystemExit(f"refusing: --field must be one of {BOUND_FIELDS} (the fields the PSC binds to its forwarded record)")
    wire.hash32(grant_id)
    head = led.dbc.get_block("latest")
    digest, data_id, gid, key_epoch, expires, allowed = led.dbc.call(led.KSSC, "getGrant", grant_id, block=head["number"])
    if not allowed:
        raise SystemExit("refusing: no allowed grant with this id exists on the DBC")
    receipt = {"requestDigest": digest, "grantId": grant_id, "gid": gid, "dataId": data_id, "keyEpoch": key_epoch, "grantExpiresAt": expires,
               "witnessSetVersion": led.pbc.call(led.PSC, "witnessSetVersion"), "dbcChainId": str(led.dbc.chain_id), "kssc": led.KSSC.address,
               "dbcBlockNumber": str(head["number"]), "dbcBlockHash": head["hash"]}
    original = receipt[field]
    altered = value if value is not None else _altered(field, original)
    if altered == original:
        raise SystemExit("refusing: the altered value equals the original (no deviation)")
    receipt[field] = altered
    wire.grant_receipt(receipt)
    key = keys.synthetic_private_key(led.deployment["fixture"]["witnessSet"]["keyLabels"][0])
    dig = messages.digest_of("GrantReceipt", receipt, messages.domain_for("GrantReceipt", receipt, led.deployment))
    sig = eip712.sign_digest(key, dig)
    return {"schemaVersion": "hmbc-test-deviating-witness/v0", "testOnly": True,
            "deviation": {"field": field, "original": original, "altered": altered}, "receipt": receipt, "signatures": [sig]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--deployment", required=True, help="the deployment JSON the runner pinned the adapter with")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("receipt")
    r.add_argument("--grant-id", required=True)
    r.add_argument("--field", required=True)
    r.add_argument("--value")
    args = ap.parse_args(argv)
    with open(args.deployment, "rb") as f:
        dep = json.loads(f.read().decode("utf-8"))
    try:
        led = Ledger.from_deployment(dep)
        out = deviating_receipt(led, args.grant_id, args.field, args.value)
    except (wire.WireError, ValueError, KeyError) as e:
        raise SystemExit(f"refusing: {type(e).__name__}: {e}") from None
    sys.stdout.write(json.dumps(out) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
