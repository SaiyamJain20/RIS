import hashlib
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


def test_manifest_lists_all_eight_operations_and_only_symbolic_mode():
    m = json.loads((ROOT / "exports" / "adapter.json").read_text())
    assert [o["name"] for o in m["operations"]] == ["prepare_request", "collect_decision", "collect_checkpoint", "attest_grant", "release", "encrypt_record",
                                                    "finish_decryption", "rotate_epoch"]
    assert m["supportedAdapterModes"] == ["symbolic"] and m["adapterMode"] == "symbolic"
    assert m["startup"]["requiredEnvironmentVariables"] == []
    cmd = m["startup"]["command"]
    assert "--state-dir" in cmd and "--deployment" in cmd, "ledger-backed operations need a pinned deployment (A2-0009)"
    assert "pinned" in m["startup"]["deploymentPinning"].lower() and "never from a request" in m["startup"]["deploymentPinning"]
    statuses = {o["name"]: o["status"] for o in m["operations"]}
    assert statuses["prepare_request"] == "implemented-e0" and statuses["rotate_epoch"] == "not-implemented-in-phase"
    assert all(s == "candidate-b-e1-not-unlocked" for k, s in statuses.items() if k in {"collect_decision", "collect_checkpoint", "attest_grant", "release", "encrypt_record", "finish_decryption"})


FREEZE = ROOT / "tests" / "fixtures" / "freeze-a3-f7b8f3f-v1.json"
V1_DEPLOYMENT = ROOT / "tests" / "fixtures" / "deployment-agent1-91add8c-v1-repaired-e.json"


def test_manifest_carries_the_frozen_v1_label():
    """A3-0021 asks for a reviewed v1-labelled successor; the gate and BOUNDARY compare the label with exactly 'v1'."""
    m = json.loads((ROOT / "exports" / "adapter.json").read_text())
    assert m["interfaceVersion"] == "v1"


def test_manifest_names_the_exact_frozen_publication_it_maps_to():
    """The mapping reference is checked against a byte copy of FREEZE.json, so a wrong id/hash/commit cannot be typed in by hand."""
    m = json.loads((ROOT / "exports" / "adapter.json").read_text())
    raw = FREEZE.read_bytes()
    frozen = json.loads(raw)
    ref = m["freeze"]
    assert hashlib.sha256(raw).hexdigest() == ref["freezeJsonSha256"] == "f700292ec7e3b2c8f2b59c7a728a991cd7d6dea2e4a06cea71f6f6c97b9962a2"
    assert ref["freezeId"] == frozen["freezeId"] == "E0-v1-r6-20261008"
    assert ref["publicationCommit"] == "f7b8f3fd74ae3dd52e385cd013a6429415b519a2"
    assert ref["candidateRevision"] == frozen["candidateRevision"] == 6
    assert ref["reviewManifestSha256"] == frozen["reviewManifest"]["sha256"]
    assert frozen["interfaceVersion"] == m["interfaceVersion"]


def test_manifest_says_the_label_is_a_mapping_and_not_a_service_ready_or_unlock():
    """Labelling the export v1 must not read as integration approval: agent 3 excluded service READY until E1 is unlocked."""
    m = json.loads((ROOT / "exports" / "adapter.json").read_text())
    s = m["serviceStatus"]
    assert "CANDIDATE" in s and "no owner service READY" in s and "E1" in s and "never a research gate" in s
    frozen = json.loads(FREEZE.read_text())
    assert frozen["e1Unlocked"] is False and frozen["owners"]["protocol"]["serviceReadyForIntegration"] is False


def test_examples_embed_agent1s_v1_labelled_deployment_sample():
    """A v1 export must not carry legacy 'v0 proposed' deployments in its examples (BOUNDARY: an E1 run uses owner exports labelled v1)."""
    dep = json.loads(V1_DEPLOYMENT.read_text())
    assert dep["interfaceVersion"] == "v1"
    for op in adapter.OPERATIONS:
        doc = json.loads((ROOT / "exports" / "examples" / f"{op}.json").read_text())
        assert "deployment-agent1-91add8c-v1-repaired-e.json" in doc["deploymentFixture"]
        for case in doc["cases"]:
            assert case["request"]["deploymentManifest"] == dep, (op, case["case"])


def test_agent1s_v1_sample_loads_and_its_abi_hashes_equal_the_bundled_abis():
    """The v1 sample must be usable by the ledger loader unchanged (all six ABI hashes pinned to the bundled ABIs)."""
    from hmbc_protocol import ledger as ledger_mod
    led = ledger_mod.Ledger.from_deployment(json.loads(V1_DEPLOYMENT.read_text()))
    assert led.pbc.chain_id == 18545 and led.dbc.chain_id == 28545


def test_manifest_documents_the_worker_log_evidence_export_without_tokens():
    m = json.loads((ROOT / "exports" / "adapter.json").read_text())
    ev = m["evidence"]["workerLog"]
    assert ev["command"][:3] == ["python", "-m", "hmbc_protocol.worker_log"] and "--state-dir" in ev["command"]
    assert "redacted" in ev["tokens"].lower() and "RELEASE_SENT" in ev["semantics"] and "attempt" in ev["semantics"].lower()


def test_candidate_operations_are_declared_with_their_state_requirements():
    m = json.loads((ROOT / "exports" / "adapter.json").read_text())
    ops = {o["name"]: o for o in m["operations"]}
    for name in ("collect_decision", "collect_checkpoint", "attest_grant", "release", "encrypt_record", "finish_decryption"):
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
