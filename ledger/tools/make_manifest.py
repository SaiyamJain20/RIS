#!/usr/bin/env python3
"""Build the ledger deployment manifest from the Deploy.s.sol stage outputs (agent 1).

Usage: python3 -I ledger/tools/make_manifest.py [--successor] <out_dir> <profile> <log_mode> <pbc_chain_id> \
           <dbc_chain_id> <pbc_rpc> <dbc_rpc>
<out_dir> holds pbc-stage.json and dbc-stage.json; the manifest is written to <out_dir>/deployment.json.

E profiles (paper-*, repaired-e, mutant-no-*): the interface-v1 manifest, unchanged; it needs
exports/abi/manifest.json (tools/export_abi.py). With --successor, also <out_dir>/deployment-v2.json,
the source-complete successor E carrier of interfaces/v2.1 (A3-0079): schemaVersion
"hmbc-ledger-deployment/v2.1", interfaceVersion "v2", the six V2 ABI entries and the twelve-file source map of
this tree (needs exports/abi/manifest-v2.json, export_abi.py --successor). The earlier ten-file v2 E carrier
omitted src/interfaces/IPolicyVersion.sol (a KSSC import) and is no longer produced.

F profiles (A-F1): repaired-f, mutant-f-no-gov-action-binding, mutant-f-no-gov-nonce,
mutant-f-no-policy-pin, mutant-f-q2. deployment.json is the interfaces/v2 LedgerDeploymentF manifest:
profile "repaired-f", profileEnum "3"; the mutant is identified only by `mutations` and the witness-set
`threshold`, never by `mutantNote` (interfaces/v2 BOUNDARY). Needs exports/abi/manifest-v2.json.
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
# F deploy names -> (mask, threshold); every one is recorded as profile "repaired-f" (D50 revision 5 table).
F_PROFILES = {"repaired-f": (0, 3), "mutant-f-no-gov-action-binding": (64, 3), "mutant-f-no-gov-nonce": (128, 3),
              "mutant-f-no-policy-pin": (256, 3), "mutant-f-q2": (0, 2)}
LOG_MODES = {"hash-only": 0, "complete-details": 1}
E_NOTE = "non-zero only for mutant-* deployments: a deliberate check removal, never HMBC evidence"
F_NOTE = ("non-zero mutations or threshold 2 only for mutant deployments: a deliberate check removal or "
          "weakened quorum, never HMBC evidence")
ERROR_CODES = [
    "NONE", "BAD_SIGNATURE", "WRONG_SUBJECT", "WRONG_DESTINATION", "UNKNOWN_AUTHORITY", "STALE_ANCHOR",
    "STALE_STATE", "EXPIRED", "REPLAY", "POLICY_DENIED", "INSUFFICIENT_QUORUM", "DUPLICATE_SIGNER",
    "WRONG_EPOCH", "NOT_COMMITTED", "ADAPTER_UNAVAILABLE", "NOT_IMPLEMENTED_IN_PHASE", "UNAUTHORIZED_CALLER",
    "NOT_REGISTERED", "ALREADY_REGISTERED", "REVOKED", "MALFORMED", "WRONG_PROFILE",
]


def main(argv):
    successor = len(argv) > 1 and argv[1] == "--successor"
    if successor:
        argv = argv[:1] + argv[2:]
    if len(argv) != 8:
        print(__doc__, file=sys.stderr)
        return 2
    out_dir, profile, log_mode, pbc_id, dbc_id, pbc_rpc, dbc_rpc = argv[1:]
    if (profile not in PROFILES and profile not in F_PROFILES) or log_mode not in LOG_MODES:
        print("bad profile/log mode", file=sys.stderr)
        return 2
    out = pathlib.Path(out_dir)
    pbc = json.loads((out / "pbc-stage.json").read_text())
    dbc = json.loads((out / "dbc-stage.json").read_text())
    if profile in F_PROFILES:
        manifest = f_manifest(profile, log_mode, pbc_id, dbc_id, pbc_rpc, dbc_rpc, pbc, dbc)
        if manifest is None:
            return 3
        return write(out / "deployment.json", manifest)
    abi = json.loads((LEDGER / "exports" / "abi" / "manifest.json").read_text())
    manifest = e_manifest(profile, log_mode, pbc_id, dbc_id, pbc_rpc, dbc_rpc, pbc, dbc, abi)
    code = write(out / "deployment.json", manifest)
    if successor and code == 0:
        v2 = json.loads((LEDGER / "exports" / "abi" / "manifest-v2.json").read_text())
        carrier = dict(manifest, schemaVersion="hmbc-ledger-deployment/v2.1", interfaceVersion="v2",
                       abi={k: v2["contracts"][k] for k in manifest["abi"]}, sources=v2["sources"])
        code = write(out / "deployment-v2.json", carrier)
    return code


def write(path, manifest):
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{path} sha256={hashlib.sha256(path.read_bytes()).hexdigest()}")
    return 0


def e_manifest(profile, log_mode, pbc_id, dbc_id, pbc_rpc, dbc_rpc, pbc, dbc, abi):
    low = str.lower
    manifest = {
        "schemaVersion": "hmbc-ledger-deployment/v0",
        "interfaceVersion": "v1",
        "producer": "agent-1 ledger/tools/deploy_local.sh",
        "createdAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "profile": profile,
        "profileEnum": str(PROFILES[profile]),
        "mutations": str(MUTATIONS.get(profile, 0)),
        "mutantNote": E_NOTE,
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
    return manifest


def f_manifest(profile, log_mode, pbc_id, dbc_id, pbc_rpc, dbc_rpc, pbc, dbc):
    """interfaces/v2 LedgerDeploymentF from the E fields plus the F witness set, Governance and bounds."""
    mask, threshold = F_PROFILES[profile]
    v2 = json.loads((LEDGER / "exports" / "abi" / "manifest-v2.json").read_text())
    low = str.lower
    witnesses = [low(w) for w in dbc["witnesses"]]
    if (pbc.get("threshold"), dbc.get("threshold")) != (str(threshold), str(threshold)) or \
            [low(w) for w in pbc["witnesses"]] != witnesses or len(witnesses) != 4:
        print(f"stage outputs do not match {profile}: threshold or witness set differs", file=sys.stderr)
        return None
    m = e_manifest("repaired-e", log_mode, pbc_id, dbc_id, pbc_rpc, dbc_rpc, pbc, dbc,
                   {"contracts": {}, "compiler": v2["compiler"], "foundryTomlSha256": v2["foundryTomlSha256"],
                    "sources": v2["sources"]})
    m.update(schemaVersion="hmbc-ledger-deployment/v2", interfaceVersion="v2", profile="repaired-f",
             profileEnum="3", mutations=str(mask), mutantNote=F_NOTE, abi=v2["contracts"])
    m["chains"]["pbc"]["contracts"]["Governance"] = low(pbc["governance"])
    m["fixture"]["witnessSet"] = {"version": "2", "threshold": str(threshold), "witnesses": witnesses,
                                  "keyLabels": [f"witness-{i}" for i in range(1, 5)], "usedBy": "repaired-f only"}
    m["fixture"]["governance"] = {"maxGovernanceTtl": "120", "maxAdmins": "8"}
    return m


if __name__ == "__main__":
    sys.exit(main(sys.argv))
