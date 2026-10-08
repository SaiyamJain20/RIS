#!/usr/bin/env python3
"""Build the ledger deployment manifest from the Deploy.s.sol stage outputs (agent 1).

Usage: python3 -I ledger/tools/make_manifest.py <out_dir> <profile> <log_mode> <pbc_chain_id> \
           <dbc_chain_id> <pbc_rpc> <dbc_rpc>
<out_dir> holds pbc-stage.json and dbc-stage.json; the manifest is written to
<out_dir>/deployment.json. Requires exports/abi/manifest.json (tools/export_abi.py).
Standard library only. Addresses are lowercase; unsigned integers are decimal strings.
"""
import datetime
import hashlib
import json
import pathlib
import sys

LEDGER = pathlib.Path(__file__).resolve().parent.parent
PROFILES = {"paper-strict": 0, "paper-minimal": 1, "repaired-e": 2,
            "mutant-no-destination-binding": 2, "mutant-no-state-barrier": 2, "mutant-no-record-freshness": 2,
            "mutant-no-nonce": 2, "mutant-no-version-monotone": 2, "mutant-no-receipt-binding": 2}
MUTATIONS = {"mutant-no-destination-binding": 1, "mutant-no-state-barrier": 2, "mutant-no-record-freshness": 4,
             "mutant-no-nonce": 8, "mutant-no-version-monotone": 16, "mutant-no-receipt-binding": 32}
LOG_MODES = {"hash-only": 0, "complete-details": 1}
ERROR_CODES = [
    "NONE", "BAD_SIGNATURE", "WRONG_SUBJECT", "WRONG_DESTINATION", "UNKNOWN_AUTHORITY", "STALE_ANCHOR",
    "STALE_STATE", "EXPIRED", "REPLAY", "POLICY_DENIED", "INSUFFICIENT_QUORUM", "DUPLICATE_SIGNER",
    "WRONG_EPOCH", "NOT_COMMITTED", "ADAPTER_UNAVAILABLE", "NOT_IMPLEMENTED_IN_PHASE", "UNAUTHORIZED_CALLER",
    "NOT_REGISTERED", "ALREADY_REGISTERED", "REVOKED", "MALFORMED", "WRONG_PROFILE",
]


def main(argv):
    if len(argv) != 8:
        print(__doc__, file=sys.stderr)
        return 2
    out_dir, profile, log_mode, pbc_id, dbc_id, pbc_rpc, dbc_rpc = argv[1:]
    if profile not in PROFILES or log_mode not in LOG_MODES:
        print("bad profile/log mode", file=sys.stderr)
        return 2
    out = pathlib.Path(out_dir)
    pbc = json.loads((out / "pbc-stage.json").read_text())
    dbc = json.loads((out / "dbc-stage.json").read_text())
    abi = json.loads((LEDGER / "exports" / "abi" / "manifest.json").read_text())
    low = str.lower
    manifest = {
        "schemaVersion": "hmbc-ledger-deployment/v0",
        "interfaceVersion": "v1",
        "producer": "agent-1 ledger/tools/deploy_local.sh",
        "createdAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "profile": profile,
        "profileEnum": str(PROFILES[profile]),
        "mutations": str(MUTATIONS.get(profile, 0)),
        "mutantNote": "non-zero only for mutant-* deployments: a deliberate check removal, never HMBC evidence",
        "logDetailMode": log_mode,
        "chains": {
            "pbc": {
                "chainId": pbc_id,
                "rpcUrl": pbc_rpc,
                "deployBlock": pbc["blockNumber"],
                "contracts": {k.upper(): low(pbc[k]) for k in ("lsc", "tmsc", "rsc", "psc")},
            },
            "dbc": {
                "chainId": dbc_id,
                "rpcUrl": dbc_rpc,
                "deployBlock": dbc["blockNumber"],
                "contracts": {k.upper(): low(dbc[k]) for k in ("acsc", "kssc")},
            },
        },
        "fixture": {
            "keyDerivation": "TEST-ONLY privateKey = keccak256('hmbc-e0-synthetic-key:' || label)",
            "authorities": [
                {"id": a["id"], "root": low(a["root"]), "caAdmins": [low(x) for x in a["caAdmins"]],
                 "rootKeyLabel": f"{a['id']}-root", "caAdminKeyLabel": f"{a['id']}-ca-admin"}
                for a in pbc["authorities"]
            ],
            "relay": {"address": low(pbc["relay"]), "keyLabel": "relay",
                      "roles": ["ACSC.policyEnf caller (paper profiles)", "PSC.reportOutcome caller"]},
            "witnessSet": {"version": "1", "threshold": "1", "witnesses": [low(w) for w in dbc["witnesses"]],
                           "keyLabels": ["witness-1"], "usedBy": "repaired-e only"},
            "policyVersion": "1",
            "keyEpoch": "0",
            "ttlSeconds": {"requestMax": "30", "decision": "30", "checkpointMax": "60", "paperGrant": "30"},
            "roles": {
                "Doctor": "keccak256('HMBC.role.Doctor')",
                "OnDuty": "keccak256('HMBC.role.OnDuty')",
                "Researcher": "keccak256('HMBC.role.Researcher')",
            },
            "data": [{"dataId": "keccak256('HMBC.data.P1.MHR')", "owner": low(dbc["dataOwner"]), "ownerId": "H2",
                      "policy": "emergency: Doctor(LONG_TERM, any issuer) AND OnDuty(TEMPORAL, same issuer as Doctor)"}],
        },
        "abi": abi["contracts"],
        "compiler": abi["compiler"],
        "foundryTomlSha256": abi["foundryTomlSha256"],
        "sources": abi["sources"],
        "errorCodes": {str(i): name for i, name in enumerate(ERROR_CODES)},
        "errorEncoding": "custom error Rejected(uint8 code); selector = bytes4(keccak256('Rejected(uint8)'))",
    }
    path = out / "deployment.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{path} sha256={hashlib.sha256(path.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
