"""Generate protocol/exports/adapter.json and protocol/exports/examples/*.json by RUNNING the adapter.

Usage (repo root): PYTHONPATH=protocol python -m hmbc_protocol.export [--check]
`--check` regenerates in memory and fails if the committed files differ, so examples cannot drift from behaviour
or be hand-written. Example requests use the pinned agent-1 sample deployment fixture and TEST-ONLY synthetic keys.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

from . import adapter

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "exports"
DEPLOYMENT = ROOT / "tests" / "fixtures" / "deployment-agent1-54262c2-repaired-e.json"
SOURCES = ["hmbc_protocol/adapter.py", "hmbc_protocol/eip712.py", "hmbc_protocol/keys.py", "hmbc_protocol/messages.py", "hmbc_protocol/wire.py"]

CANDIDATE_NOTE = ("CANDIDATE B-E1 code: implemented while E1 is not unlocked and NOT offered for integration or claimed as an E1 result. It needs a "
                  "configured --state-dir and a reachable loopback ledger (rpcUrl in the deployment manifest); otherwise it answers ADAPTER_UNAVAILABLE. "
                  "The examples below are generated with no ledger running, so they show the refusal paths only; successful runs are recorded as "
                  "evidence from live-ledger tests, never invented here.")
OPS = {
    "prepare_request": {
        "inputFields": {"request": "AccessRequest (wire form, decimal-string uints)", "signingKeyRef": "keyref:user:<label>"},
        "resultFields": ["schemaVersion", "adapterMode", "request", "requestDigest", "signature", "signer"],
        "errors": ["MALFORMED", "WRONG_SUBJECT", "WRONG_DESTINATION", "WRONG_EPOCH", "ADAPTER_UNAVAILABLE"],
        "behaviour": "Signs the EIP-712 AccessRequest only if gid equals the referenced user key's address and the chains/contracts/keyEpoch/policyVersion equal the deployment manifest. Does not check expiry or authEpoch (the PSC and clock rules own those).",
    },
    "collect_decision": {
        "inputFields": {"requestDigest": "bytes32", "witnessSetVersion": "optional, E: \"1\""},
        "draftResultFields": ["schemaVersion", "adapterMode", "decision (AccessDecision)", "signatures (sorted by signer)", "credentialRecords (CredentialRecord[])"],
        "errors": ["ADAPTER_UNAVAILABLE", "STALE_STATE", "EXPIRED", "POLICY_DENIED", "REVOKED", "WRONG_SUBJECT", "NOT_REGISTERED", "INSUFFICIENT_QUORUM"],
        "behaviour": "Requires the DBC's CURRENT checkpoint (unexpired, describing the PBC state the witness verifies, not older than the request). Witness recomputes the decision from PBC state at the decision's block (checkCredentials at that block tag and its timestamp, A1-0011); relays never supply attributes. At most one re-collection per newly accepted checkpoint while the request is unexpired (D24).",
    },
    "collect_checkpoint": {
        "inputFields": {"witnessSetVersion": "optional, E: \"1\" ({} is valid); a sequence, block or timestamp is never accepted from the caller"},
        "draftResultFields": ["schemaVersion", "adapterMode", "checkpoint (StateCheckpoint)", "signatures (exactly one)"],
        "errors": ["ADAPTER_UNAVAILABLE", "MALFORMED", "STALE_STATE", "WRONG_DESTINATION"],
        "behaviour": "Witness signs a StateCheckpoint of the latest PBC block it treats as final (authEpoch, policyVersion, source block number/hash read from the PBC), with sequence = the DBC's current sequence + 1 read from the DBC, keyEpoch 0, expiresAt = the DBC clock (pending block) + 60. The RUNNER submits KSSC.acceptState (A2-0008 Option A, accepted in A3-0012).",
    },
    "attest_grant": {
        "inputFields": {"grantId": "bytes32"},
        "draftResultFields": ["schemaVersion", "adapterMode", "receipt (GrantReceipt)", "signatures (exactly one)"],
        "errors": ["ADAPTER_UNAVAILABLE", "MALFORMED", "NOT_COMMITTED", "WRONG_SUBJECT"],
        "behaviour": "Witness signs a GrantReceipt only for an ALLOWED grant it reads from the DBC at the latest block (grant id re-derived, cross-checked against the PBC's FORWARDED record); NOT_COMMITTED for a missing/denied grant, WRONG_SUBJECT once an outcome is recorded. A receipt is grant evidence, never delivery evidence. The RUNNER submits PSC.reportAttestedOutcome (only the configured relay may).",
    },
    "release": {
        "inputFields": {"grantId": "bytes32"},
        "draftResultFields": ["schemaVersion", "adapterMode", "requestDigest", "grantId", "dataId", "keyEpoch", "ciphertextDigest", "recipientKeyHash", "responseEnvelope"],
        "errors": ["ADAPTER_UNAVAILABLE", "NOT_COMMITTED", "EXPIRED", "WRONG_SUBJECT", "REPLAY (never: a retry returns the cached response)"],
        "behaviour": "Loads the committed grant from the DBC, persists release intent before sending, returns the same cached response on retry while the original grant is unexpired, and fails EXPIRED on the first call after expiry. Grant, send and reconciled outcome are separate recorded events.",
    },
    "encrypt_record": {
        "inputFields": {"record": "SymbolicRecord {dataId, owner, payloadDigest}", "policy": "SymbolicPolicy {clauses: PolicyRequirement[][]}", "keyEpoch": "\"0\""},
        "draftResultFields": ["schemaVersion", "adapterMode=symbolic", "dataId", "keyEpoch", "ciphertextDigest", "policyDigest"],
        "errors": ["ADAPTER_UNAVAILABLE", "WRONG_EPOCH", "MALFORMED"],
        "behaviour": "Symbolic token only. A result asserts modeled decryptability, never ABE confidentiality. Inputs follow candidate revision 4 SymbolicRecord/SymbolicPolicy (SAME_AS_FIRST cannot be a clause's first requirement).",
    },
    "finish_decryption": {
        "inputFields": {"response": "ReleaseResult", "userKeyRef": "keyref:user:<label>"},
        "draftResultFields": ["schemaVersion", "adapterMode=symbolic", "decryptable (boolean, modeled)", "dataId", "ciphertextDigest"],
        "errors": ["ADAPTER_UNAVAILABLE", "WRONG_SUBJECT", "MALFORMED"],
        "behaviour": "Symbolic two-step completion: the response must equal what this worker issued (token compared in constant time) and the user key handle must hash to the grant's recipientKeyHash; never returns decryptable=false in E (a refusal is an error).",
    },
    "rotate_epoch": {
        "inputFields": {"targetEpoch": "decimal string"},
        "draftResultFields": [],
        "errors": ["NOT_IMPLEMENTED_IN_PHASE"],
        "behaviour": "Always NOT_IMPLEMENTED_IN_PHASE before G; no fake rotation.",
    },
}


_h = lambda n: "0x" + format(n, "064x")  # noqa: E731  (constructed example values, not issued capabilities)


def _dep() -> dict:
    return json.loads(DEPLOYMENT.read_text())


def _pbc_request(**over) -> dict:
    dep = _dep()
    pbc, dbc = dep["chains"]["pbc"], dep["chains"]["dbc"]
    msg = {"sourceChainId": pbc["chainId"], "destinationChainId": dbc["chainId"], "psc": pbc["contracts"]["PSC"],
           "kssc": dbc["contracts"]["KSSC"], "gid": "0xc4ff0022e776c3471e39abf6c69ce679440c956d",
           "dataId": "0x" + "ab" * 32, "action": "1", "policyVersion": "1", "authEpoch": "3", "keyEpoch": "0",
           "nonce": "1", "expiresAt": "1800000030",
           "recipientKeyHash": "0x98d796e3229ebf5c50610744cf35aece58511751e387e8eef569a0117bb07e5d"}
    msg.update(over)
    return msg


def _example_cases() -> dict[str, list[tuple[str, dict]]]:
    dep = _dep()
    return {
        "prepare_request": [
            ("success", {"request": _pbc_request(), "signingKeyRef": "keyref:user:alice"}),
            ("refused: gid is not the referenced key's address", {"request": _pbc_request(gid="0x" + "11" * 20), "signingKeyRef": "keyref:user:alice"}),
            ("refused: wrong destination KSSC", {"request": _pbc_request(kssc="0x" + "11" * 20), "signingKeyRef": "keyref:user:alice"}),
            ("refused: JSON number instead of decimal string", {"request": _pbc_request(nonce=1), "signingKeyRef": "keyref:user:alice"}),
        ],
        "collect_checkpoint": [("well-formed request, no ledger running", {}), ("well-formed with the optional version", {"witnessSetVersion": "1"}),
                               ("refused: a relay-supplied sequence is never accepted", {"sequence": "9"})],
        "attest_grant": [("well-formed request, no ledger running", {"grantId": _h(2)}), ("refused: empty input is MALFORMED", {})],
        "collect_decision": [("well-formed request, no ledger running", {"requestDigest": _h(1)}),
                             ("refused: empty input is MALFORMED, not unavailable", {})],
        "release": [("well-formed request, no ledger running", {"grantId": _h(2)})],
        "encrypt_record": [("well-formed request, no ledger running", {
            "record": {"dataId": _h(3), "owner": "0x" + "44" * 20, "payloadDigest": _h(5)},
            "policy": {"clauses": [[{"role": _h(6), "kind": "1", "issuerMode": "0"}, {"role": _h(7), "kind": "2", "issuerMode": "2"}]]},
            "keyEpoch": "0"}),
            ("refused: SAME_AS_FIRST as a clause's first requirement", {
                "record": {"dataId": _h(3), "owner": "0x" + "44" * 20, "payloadDigest": _h(5)},
                "policy": {"clauses": [[{"role": _h(6), "kind": "1", "issuerMode": "2"}]]}, "keyEpoch": "0"})],
        "finish_decryption": [("well-formed request, no ledger running", {
            "response": {"schemaVersion": "v1", "adapterMode": "symbolic", "requestDigest": _h(1), "grantId": _h(2), "dataId": _h(3),
                         "ciphertextDigest": _h(8), "recipientKeyHash": _h(9), "keyEpoch": "0",
                         "responseEnvelope": {"kind": "symbolic-partial/v1", "token": _h(10)}},
            "userKeyRef": "keyref:user:alice"})],
        "rotate_epoch": [("G-phase op, well-formed request", {"targetEpoch": "1"})],
    }, dep


def build_examples() -> dict[str, dict]:
    cases, dep = _example_cases()
    out = {}
    for op, items in cases.items():
        entries = []
        for label, inp in items:
            req = {"schemaVersion": adapter.SCHEMA_VERSION, "operation": op, "input": inp, "deploymentManifest": dep}
            entries.append({"case": label, "request": req, "response": adapter.handle_line(json.dumps(req))})
        out[op] = {"operation": op, "generatedBy": "python -m hmbc_protocol.export (runs the adapter; not hand-written)",
                   "deploymentFixture": "tests/fixtures/deployment-agent1-54262c2-repaired-e.json (byte copy of agent-1 54262c2 sample-repaired-e; machine-local RPC URLs)",
                   "cases": entries}
    return out


def build_manifest() -> dict:
    ops = []
    for name, spec in OPS.items():
        entry = {"name": name, "status": adapter.OPERATIONS[name]["status"], "example": f"examples/{name}.json", **spec}
        if name in ("collect_decision", "collect_checkpoint", "attest_grant", "release", "encrypt_record", "finish_decryption"):
            entry["draftNote"] = CANDIDATE_NOTE
        ops.append(entry)
    return {
        "schemaVersion": "hmbc-protocol-adapter/v0",
        "interfaceVersion": "candidate v1 revision 3 (NOT frozen)",
        "producer": "agent-2 protocol/hmbc_protocol/export.py",
        "adapterMode": adapter.ADAPTER_MODE,
        "supportedAdapterModes": ["symbolic"],
        "note": "Paper-derived reconstruction. symbolic = modeled decryptability only; no real ABE and no performance claim.",
        "startup": {"command": ["python", "-m", "hmbc_protocol.adapter", "--state-dir", "<private directory, mode 0700>", "--deployment", "<deployment.json to pin>"],
                    "deploymentPinning": "The deployment given at startup is PINNED: RPC URLs, contract addresses and the witness key label come only from it, never from a request. A request whose deploymentManifest differs answers WRONG_DESTINATION before any connection is made; without --deployment the ledger-backed operations answer ADAPTER_UNAVAILABLE.",
                    "workingDirectory": "protocol (or set PYTHONPATH to it)", "requiredEnvironmentVariables": [],
                    "python": ">=3.13,<3.14", "requirements": "protocol/requirements.txt"},
        "transport": {"format": "JSON lines over stdin/stdout, UTF-8, one request object per line, one response per request line, max 1048576 bytes per line",
                      "request": ["schemaVersion", "operation", "input", "deploymentManifest"],
                      "response": ["schemaVersion", "ok", "result", "error"], "schemaVersionValue": adapter.SCHEMA_VERSION,
                      "strictness": "duplicate JSON keys, NaN/Infinity, unknown or missing fields, JSON-number integers, non-lowercase hex and trailing newlines all answer MALFORMED"},
        "keyHandles": {"pattern": "keyref:<user|witness|worker|authority>:<label [a-z0-9-]{1,64}>",
                       "resolution": "inside the adapter process only; E0/E1 keys are TEST-ONLY synthetic keys derived like agent 1's fixtures",
                       "neverReturned": ["private keys", "temporal key material", "master secrets", "plaintext keys"]},
        "errorChoices": ["No error class exists for a wrong SOURCE chain/PSC; the signer reports WRONG_DESTINATION for any chain/contract mismatch with the deployment manifest (agent-2 choice, RFC if agent 3 prefers another class).",
                         "Unknown operation, bad envelope and every wire-format violation answer MALFORMED (no dedicated code in the v0 list).",
                         "An unbuilt E operation answers ADAPTER_UNAVAILABLE, not NOT_IMPLEMENTED_IN_PHASE, because the limit is E1 not being unlocked, not a later phase."],
        "evidence": {"workerLog": {
            "command": ["python", "-m", "hmbc_protocol.worker_log", "--state-dir", "<the adapter's state directory>"],
            "output": "JSON: append-only worker events (RELEASE_INTENT / RELEASE_SENT with requestDigest, grantId, gid, dataId, timestamp), one row per release with sendAttempts/completedAttempts/delivery/tokenDigest, and counts {releaseIntentCount, releaseSentCount}",
            "tokens": "The symbolic capability is REDACTED: only keccak256(token) is exported, so a collector can check 'same cached response' without holding it.",
            "semantics": "RELEASE_SENT is a write-ahead record of an ATTEMPTED send (durable before the response can leave); delivery is never acknowledged and stays 'unknown'. Opened read-only; safe to run while the adapter is up."}},
        "operations": ops,
        "sourceSha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES},
    }


def render(obj: dict) -> str:
    return json.dumps(obj, indent=2, sort_keys=False) + "\n"


def main(argv: list[str]) -> int:
    check = "--check" in argv
    want = {EXPORTS / "adapter.json": render(build_manifest())}
    want.update({EXPORTS / "examples" / f"{op}.json": render(doc) for op, doc in build_examples().items()})
    bad = []
    for path, text in want.items():
        if check:
            if not path.exists() or path.read_text() != text:
                bad.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
    if bad:
        print("stale exports (run without --check):", *bad, sep="\n  ")
        return 1
    print(("exports match" if check else "wrote") + f" {len(want)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
