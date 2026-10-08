import json
import pathlib
import subprocess
import sys

from hmbc_protocol import adapter, export

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_committed_exports_equal_regeneration():
    """adapter.json and every example are produced by running the adapter; hand edits or drift fail here."""
    r = subprocess.run([sys.executable, "-m", "hmbc_protocol.export", "--check"], cwd=ROOT,
                       env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_manifest_lists_all_six_operations_and_only_symbolic_mode():
    m = json.loads((ROOT / "exports" / "adapter.json").read_text())
    assert [o["name"] for o in m["operations"]] == ["prepare_request", "collect_decision", "release", "encrypt_record", "finish_decryption", "rotate_epoch"]
    assert m["supportedAdapterModes"] == ["symbolic"] and m["adapterMode"] == "symbolic"
    assert m["startup"]["requiredEnvironmentVariables"] == []
    statuses = {o["name"]: o["status"] for o in m["operations"]}
    assert statuses["prepare_request"] == "implemented-e0" and statuses["rotate_epoch"] == "not-implemented-in-phase"
    assert all(s == "candidate-b-e1-not-unlocked" for k, s in statuses.items() if k in {"collect_decision", "release", "encrypt_record", "finish_decryption"})


def test_candidate_operations_are_declared_with_their_state_requirements():
    m = json.loads((ROOT / "exports" / "adapter.json").read_text())
    ops = {o["name"]: o for o in m["operations"]}
    for name in ("collect_decision", "release", "encrypt_record", "finish_decryption"):
        note = ops[name]["draftNote"] if "draftNote" in ops[name] else ops[name].get("candidateNote", "")
        assert "CANDIDATE" in note and "E1 is not unlocked" in note and "--state-dir" in note, name


def test_every_example_has_exactly_one_of_result_or_error_and_unbuilt_ops_never_succeed():
    for op in adapter.OPERATIONS:
        doc = json.loads((ROOT / "exports" / "examples" / f"{op}.json").read_text())
        for case in doc["cases"]:
            resp = case["response"]
            assert (resp["result"] is None) != (resp["error"] is None)
            if adapter.OPERATIONS[op]["status"] != "implemented-e0":
                assert resp["ok"] is False
    ok = json.loads((ROOT / "exports" / "examples" / "prepare_request.json").read_text())["cases"][0]["response"]
    assert ok["ok"] and ok["result"]["signature"].startswith("0x")


def test_no_private_key_in_any_export():
    blob = "".join(p.read_text() for p in (ROOT / "exports").rglob("*.json"))
    assert "0x5ae9decb17555998c229f97e1846cd52b643a4b10efd2bbbc09c89c6ba1f76db" not in blob
    assert "5ae9decb1755" not in blob


def test_prepare_request_example_verifies_with_eth_account_alone():
    """Independent of hmbc_protocol's encoder and recovery: eth_account encodes, hashes and recovers."""
    from eth_account import Account
    from eth_account.messages import _hash_eip191_message, encode_typed_data
    case = json.loads((ROOT / "exports" / "examples" / "prepare_request.json").read_text())["cases"][0]
    res, dep = case["response"]["result"], case["request"]["deploymentManifest"]
    req = res["request"]
    msg = {k: (int(v) if k in {"sourceChainId", "destinationChainId", "action", "policyVersion", "authEpoch", "keyEpoch", "nonce", "expiresAt"} else v)
           for k, v in req.items()}
    full = {"types": {"EIP712Domain": [{"name": "name", "type": "string"}, {"name": "version", "type": "string"},
                                       {"name": "chainId", "type": "uint256"}, {"name": "verifyingContract", "type": "address"}],
                      "AccessRequest": adapter.messages.TYPES["AccessRequest"]},
            "primaryType": "AccessRequest",
            "domain": {"name": "HMBCRequest", "version": "1", "chainId": int(req["sourceChainId"]), "verifyingContract": req["psc"]},
            "message": msg}
    signable = encode_typed_data(full_message=full)
    assert "0x" + _hash_eip191_message(signable).hex() == res["requestDigest"]
    assert Account.recover_message(signable, signature=res["signature"]).lower() == res["signer"] == req["gid"]
    assert req["psc"] == dep["chains"]["pbc"]["contracts"]["PSC"]
