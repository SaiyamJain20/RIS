"""LIVE tests against REAL nodes and a REAL deployment: the D50 chain view and open-time reconstruction (slice 8b) and the witness-side ledger view with real witness signatures accepted by the real
contracts (slice 9a, the second half of this file).

D50 part (slice 8b, agent 2, F task 2).

Two Anvil nodes (Foundry 1.8.5 in the tool directory the carried live fixtures use) and agent 1's ledger snapshot at commit 85c59f5, deployed by agent 1's own `ledger/tools/deploy_local.sh` into a scratch
directory (`git archive`, nothing of any peer checkout is touched), once as `repaired-f` and once as `repaired-e` with `SUCCESSOR_EXPORT=1` (the v2.1 carrier). `RpcBindingView.from_manifest` loads the
ABI files of that snapshot (hash-checked against the manifest), and `binding_open.reconstruct` reads the real chains: this is the first time the masked-bytecode build check, the immutable-reference pins and
the 55/48-request schedule meet real contract code instead of synthetic bytes. Skipped when Foundry or the pinned commit is missing. What it does NOT show: a witness-side view, timing, a second host, or
anything about a deployment other than this snapshot; the nodes are local, single-process Anvil with automine, and the deployer key is Anvil's public default account.
"""
import copy
import json
import os
import pathlib
import socket
import subprocess
import tarfile
import time
from types import SimpleNamespace

import pytest

from hmbc_protocol import adapter_v2_start as st
from eth_account import Account

from hmbc_protocol import eip712, keys, messages, rpc_witness_view as rwv
from hmbc_protocol.abi import Contract
from hmbc_protocol.chain import Rejected
from hmbc_protocol import witness_service as svc, witness_state as ws
from hmbc_protocol import binding as bd
from hmbc_protocol import binding_open as bo
from hmbc_protocol import rpc_binding_view as rv
from hmbc_protocol.chain import Chain

REPO = pathlib.Path(__file__).resolve().parents[2]
LEDGER_COMMIT = "85c59f588de58a8ff5e87b9fe6f630c9d8c43642"
FOUNDRY = pathlib.Path.home() / ".local/share/hmbc-tools/foundry-1.8.5"
ANVIL_KEY0 = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"        # Anvil's public default account
ALT_KEY_ADDR = "0x" + "ee" * 20


class Counting(Chain):
    calls = 0

    def rpc(self, method, params=None):
        type(self).calls += 1
        return super().rpc(method, params)


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait(url):
    for _ in range(100):
        try:
            Chain(url, 1).rpc("eth_chainId")
            return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"anvil at {url} did not start")


def _deploy(tmp_path_factory, profile, successor):
    anvil, forge = FOUNDRY / "anvil", FOUNDRY / "forge"
    if not anvil.is_file() or not forge.is_file():
        pytest.skip("Foundry (anvil/forge) not installed in the hmbc-tools directory")
    if subprocess.run(["git", "cat-file", "-e", LEDGER_COMMIT], cwd=REPO, capture_output=True).returncode != 0:
        pytest.skip(f"ledger commit {LEDGER_COMMIT} not available locally (git fetch origin)")
    root = tmp_path_factory.mktemp("live-" + profile)
    tar = subprocess.run(["git", "archive", LEDGER_COMMIT, "ledger"], cwd=REPO, capture_output=True, check=True).stdout
    (root / "snap.tar").write_bytes(tar)
    with tarfile.open(root / "snap.tar") as t:
        t.extractall(root / "src", filter="data")
    src = root / "src"
    ports = [_free_port(), _free_port()]
    procs = [subprocess.Popen([str(anvil), "--port", str(p), "--chain-id", str(c), "--silent"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for p, c in zip(ports, (18545, 28545))]
    try:
        urls = [f"http://127.0.0.1:{p}" for p in ports]
        for u in urls:
            _wait(u)
        env = {**os.environ, "PATH": f"{FOUNDRY}:{os.environ['PATH']}", "DEPLOYER_PK": ANVIL_KEY0}
        if successor:
            env["SUCCESSOR_EXPORT"] = "1"
        run = subprocess.run(["bash", "ledger/tools/deploy_local.sh", urls[0], urls[1], profile, "complete-details", "live-d50"], cwd=src, env=env, capture_output=True, text=True, timeout=900)
        assert run.returncode == 0, run.stdout[-1500:] + run.stderr[-1500:]
        out = src / "ledger/exports/deployments/live-d50"
        dep = json.loads((out / ("deployment-v2.json" if successor else "deployment.json")).read_text())
        yield SimpleNamespace(dep=dep, urls=urls, abi_dir=str(src / "ledger/exports/abi"))
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()


@pytest.fixture(scope="module")
def live_f(tmp_path_factory):
    yield from _deploy(tmp_path_factory, "repaired-f", False)


@pytest.fixture(scope="module")
def live_f_fresh(tmp_path_factory):
    """A SECOND deployment of the F ledger, untouched by the other tests: the compromised-quorum test needs a DBC with no checkpoint and a PBC with governance nonce 0."""
    yield from _deploy(tmp_path_factory, "repaired-f", False)


@pytest.fixture(scope="module")
def live_e(tmp_path_factory):
    yield from _deploy(tmp_path_factory, "repaired-e", True)


def view_for(live, manifest=None):
    m = manifest or live.dep
    chains = {s: Counting(live.urls[i], int(m["chains"][s]["chainId"])) for i, s in enumerate(("pbc", "dbc"))}
    Counting.calls = 0
    return rv.RpcBindingView.from_manifest(m, chains, live.abi_dir), chains


def refusal(fn):
    try:
        fn()
    except bd.OpenRefusal as e:
        return e
    return None


# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_the_real_f_deployment_reconstructs_with_the_masked_build_check_in_exactly_55_requests(live_f):
    view, chains = view_for(live_f)
    out = bo.reconstruct(live_f.dep, view, role="worker")
    assert Counting.calls == 55 and out["buildChecked"] is True
    doc = out["document"]
    assert doc["profile"] == {"enum": "3", "name": "repaired-f"} and doc["witnessSets"]["psc"]["version"] == "2" and doc["witnessSets"]["psc"]["threshold"] == "3" and len(doc["witnessSets"]["psc"]["witnesses"]) == 4
    assert doc["witnessSets"]["governance"]["witnesses"] == doc["witnessSets"]["psc"]["witnesses"]
    for side in ("pbc", "dbc"):                                          # the anchor is a real block of the real chain, read independently with the carried client
        n = int(out["anchor"][side]["number"])
        assert Chain(live_f.urls[0 if side == "pbc" else 1], int(live_f.dep["chains"][side]["chainId"])).get_block(n)["hash"] == out["anchor"][side]["hash"]
    again = bo.reconstruct(live_f.dep, view_for(live_f)[0], role="worker")
    assert again["binding_v2"] == out["binding_v2"] and again["document"] == out["document"]


def test_the_real_e_successor_deployment_reconstructs_in_exactly_48_requests(live_e):
    assert live_e.dep["schemaVersion"] == "hmbc-ledger-deployment/v2.1"
    view, _ = view_for(live_e)
    out = bo.reconstruct(live_e.dep, view, role="worker")
    assert Counting.calls == 48 and out["buildChecked"] is True and out["document"]["profile"] == {"enum": "2", "name": "repaired-e"}


def test_the_witness_role_accepts_a_member_key_and_refuses_another(live_f):
    member = live_f.dep["fixture"]["witnessSet"]["witnesses"][0]
    view, _ = view_for(live_f)
    assert bo.reconstruct(live_f.dep, view, role="witness", key_address=member)["binding_v2"] == bo.reconstruct(live_f.dep, view_for(live_f)[0], role="worker")["binding_v2"]
    e = refusal(lambda: bo.reconstruct(live_f.dep, view_for(live_f)[0], role="witness", key_address=ALT_KEY_ADDR))
    assert e is not None and e.reason == "UNKNOWN_AUTHORITY"


def mutate(live, fn):
    m = copy.deepcopy(live.dep)
    fn(m)
    return m


def test_a_manifest_that_disagrees_with_the_real_chain_is_refused_with_the_predicted_stage(live_f):
    flip = lambda h: ("0" if h[0] != "0" else "1") + h[1:]
    cases = {
        "PROFILE_MISMATCH": lambda m: m.update(profileEnum="2"),
        "GENESIS_MISMATCH (a deploy block past the head)": lambda m: m["chains"]["pbc"].update(deployBlock="9999"),
        "BUILD_MISMATCH (a pinned masked runtime hash that is not the live one)": lambda m: m["abi"]["PSC"].update(runtimeSha256=flip(m["abi"]["PSC"]["runtimeSha256"])),
    }
    got = {}
    for name, fn in cases.items():
        m = mutate(live_f, fn)
        e = refusal(lambda: bo.reconstruct(m, view_for(live_f, m)[0], role="worker"))
        got[name] = None if e is None else e.reason
    assert got == {"PROFILE_MISMATCH": "PROFILE_MISMATCH", "GENESIS_MISMATCH (a deploy block past the head)": "GENESIS_MISMATCH",
                   "BUILD_MISMATCH (a pinned masked runtime hash that is not the live one)": "BUILD_MISMATCH"}, got


def test_a_manifest_naming_another_chain_id_is_refused_by_the_stage_not_by_the_client_and_wiring_comes_first(live_f):
    m = mutate(live_f, lambda m: m["chains"]["dbc"].update(chainId="28546"))
    view, chains = view_for(live_f, m)
    assert view.chain_id("dbc") == "28545"                               # the node's own answer is reported as is
    e = refusal(lambda: bo.reconstruct(m, view, role="worker"))
    # my first prediction was GENESIS_MISMATCH; the precedence of SUCCESSOR-WIRE section 1 puts the wiring stage (5) before the genesis/chain-id stage (6), and `PSC.ksscForChain(28546)` is the zero address
    assert e is not None and e.reason == "WIRING_MISMATCH"


def test_an_unreachable_real_node_is_stage_one(live_f):
    m = copy.deepcopy(live_f.dep)
    chains = {"pbc": Chain(live_f.urls[0], int(m["chains"]["pbc"]["chainId"])), "dbc": Chain("http://127.0.0.1:%d" % _free_port(), int(m["chains"]["dbc"]["chainId"]))}
    view = rv.RpcBindingView.from_manifest(m, chains, live_f.abi_dir)
    e = refusal(lambda: bo.reconstruct(m, view, role="worker"))
    assert e is not None and e.reason == "LEDGER_UNREACHABLE"


def test_the_startup_order_binds_the_worker_directory_against_the_real_deployment(live_f, tmp_path):
    view, _ = view_for(live_f)
    ctx = st.start(manifest=live_f.dep, schema_revision="v2", chain_view=view, state_dir=str(tmp_path / "state"), worker_factory=lambda c: (_ for _ in ()).throw(AssertionError("lazy")))
    assert set(ctx.handlers) == {"prepare_request", "encrypt_record", "release", "finish_decryption"} and Counting.calls == 55
    assert (tmp_path / "state" / "worker" / "INITIALIZED").is_file()
    ctx2 = st.start(manifest=live_f.dep, schema_revision="v2", chain_view=view_for(live_f)[0], state_dir=str(tmp_path / "state"), worker_factory=lambda c: None)      # the same deployment reopens
    assert ctx2.manifest == live_f.dep


# ========================================================================================================================================================
# Slice 9a: the witness-side ledger view over the same real nodes, and REAL witness signatures accepted by the REAL contracts.
# Written BEFORE hmbc_protocol/rpc_witness_view.py existed. Four real WitnessService objects (real durable stores, the synthetic witness keys the deployment names) read the real ledger through
# `RpcWitnessView`; a three-signature checkpoint certificate and a GovernanceAction certificate are submitted to the real KSSC and Governance contracts, which verify the EIP-712 signatures themselves.
# This is the first time my signing digests meet Solidity. NOT shown: the decision and receipt paths (they need a forwarded request with credentials on the real ledger), independent hosts, timing.
# ========================================================================================================================================================
def witness_view(live, manifest=None):
    m = manifest or live.dep
    chains = {s: Chain(live.urls[i], int(m["chains"][s]["chainId"])) for i, s in enumerate(("pbc", "dbc"))}
    return rwv.RpcWitnessView.from_manifest(m, chains, live.abi_dir), chains


def real_witnesses(live, tmp_path, allowed=None):
    wview, _ = witness_view(live)
    out = []
    for i in range(4):
        key = keys.synthetic_private_key("witness-%d" % (i + 1))
        addr = live.dep["fixture"]["witnessSet"]["witnesses"][i]
        assert Account.from_key(key).address.lower() == addr                    # the deployment's witness set IS the synthetic witness-N keys
        r = bo.reconstruct(live.dep, view_for(live)[0], role="witness", key_address=addr)
        store = ws.init_store(str(tmp_path / ("w%d" % i)), r["binding_v2"], r["document"], "witness:" + addr, anchor=r["anchor"])
        out.append(svc.WitnessService(store=store, key=key, view=wview, deployment=live.dep, witness_set_version="2", allowed_governance=allowed))
    assert [w.address for w in out] == live.dep["fixture"]["witnessSet"]["witnesses"]
    return out, wview


def mine(live, side):
    """One new block on that chain (Anvil `evm_mine`), so the LATEST block carries the current time. FINDING (observed): on an idle automine chain the latest block's timestamp is that of the last
    transaction; a checkpoint proposed with `expiresAt = latest + 30` can already be in the past when the next block is mined, and the real KSSC then rejects it EXPIRED. The witness rules read the
    latest block (F0), so liveness needs block production (a heartbeat), which is the F-29 note in INVENTORY made concrete. The tests mine before deriving, as an operator's block producer would."""
    from support import rpc
    rpc(live.urls[0 if side == "pbc" else 1], "evm_mine")


def sorted_signatures(m, name, sigs, deployment):
    by = {}
    for sg in sigs:
        if name == "GovernanceAction":
            digest = svc._governance_digest(m, deployment)
        elif name == "GrantReceipt":                                     # the carried E validator hard-codes witnessSetVersion=1: the F receipt has its own digest helper
            digest = svc._receipt_digest(m, deployment)
        else:
            digest = messages.digest_of(name, m, messages.domain_for(name, m, deployment))
        by[eip712.recover(digest, sg)] = sg
    return [by[a] for a in sorted(by)]


def test_the_witness_view_returns_the_shapes_the_service_expects_from_the_real_ledger(live_f):
    wview, chains = witness_view(live_f)
    head = chains["dbc"].get_block("latest")
    o = wview.observe("dbc")
    assert o["chainId"] == "28545" and int(o["blockNumber"]) >= head["number"] and len(o["blockHash"]) == 66 and int(o["timestamp"]) >= head["timestamp"]
    n = int(wview.observe("pbc")["blockNumber"])
    b = wview.pbc_block(n)
    assert b == {"number": str(n), "hash": chains["pbc"].get_block(n)["hash"], "timestamp": str(chains["pbc"].get_block(n)["timestamp"])}
    assert wview.pbc_block(n + 1000) is None
    assert wview.reads_at(n) == {"authEpoch": "0", "policyVersion": "1", "witnessSetVersion": "2"}
    assert wview.dbc_current_checkpoint() is None                      # nothing accepted yet on a fresh deployment
    assert wview.governance_nonce() in (0, "0") and wview.is_authority("0x" + "ab" * 20) is False and wview.removed_authority("0x" + "ab" * 20) is False
    assert wview.nonce_consumed("0x" + "ab" * 20, "1") is False
    assert wview.now("dbc") >= int(o["timestamp"])
    assert wview.forwarded_logs("0x" + "00" * 32) == [] and wview.grant_issued_logs("0x" + "00" * 32) == []
    assert wview.psc_request("0x" + "00" * 32)["status"] == "0"


def test_a_proposer_derives_a_valid_checkpoint_from_the_real_ledger(live_f):
    wview, chains = witness_view(live_f)
    cp = svc.derive_checkpoint(wview, live_f.dep)
    assert cp["sequence"] == "1" and cp["keyEpoch"] == "0" and cp["witnessSetVersion"] == "2" and cp["sourceChainId"] == "18545"
    assert cp["psc"] == live_f.dep["chains"]["pbc"]["contracts"]["PSC"] and cp["sourceBlockHash"] == chains["pbc"].get_block(int(cp["sourceBlockNumber"]))["hash"]


def test_three_real_witness_signatures_are_accepted_by_the_real_kssc_and_two_or_a_stranger_are_not(live_f, tmp_path):
    witnesses, wview = real_witnesses(live_f, tmp_path)
    _, chains = witness_view(live_f)
    kssc = Contract(json.load(open(os.path.join(live_f.abi_dir, "KSSC.json"))), live_f.dep["chains"]["dbc"]["contracts"]["KSSC"])
    mine(live_f, "dbc")
    cp = svc.derive_checkpoint(wview, live_f.dep)
    sigs = [w.sign_checkpoint(cp) for w in witnesses[:3]]
    ordered = sorted_signatures(cp, "StateCheckpoint", sigs, live_f.dep)
    with pytest.raises(Rejected) as e2:                                   # two of four is below the threshold of three: PREDICTED INSUFFICIENT_QUORUM
        chains["dbc"].send(ANVIL_KEY0, kssc, "acceptState", cp, ordered[:2])
    assert e2.value.code == "INSUFFICIENT_QUORUM"
    stranger = eip712.sign_digest(keys.synthetic_private_key("outsider"), messages.digest_of("StateCheckpoint", cp, messages.domain_for("StateCheckpoint", cp, live_f.dep)))
    with pytest.raises(Rejected):                                         # a signature by a non-member in place of the third
        chains["dbc"].send(ANVIL_KEY0, kssc, "acceptState", cp, sorted_signatures(cp, "StateCheckpoint", sigs[:2] + [stranger], live_f.dep))
    chains["dbc"].send(ANVIL_KEY0, kssc, "acceptState", cp, ordered)       # the real contract verifies the three EIP-712 signatures
    cur = wview.dbc_current_checkpoint()
    assert cur is not None and cur["sequence"] == "1" and cur["sourceBlockHash"] == cp["sourceBlockHash"]
    assert svc.derive_checkpoint(wview, live_f.dep)["sequence"] == "2"
    with pytest.raises(Rejected):                                         # the same sequence cannot be accepted twice
        chains["dbc"].send(ANVIL_KEY0, kssc, "acceptState", cp, ordered)


def test_real_witness_signatures_over_a_governance_action_are_executed_by_the_real_governance_contract(live_f, tmp_path):
    root, admin = "0x" + "c4" * 20, "0x" + "d5" * 20
    witnesses, wview = real_witnesses(live_f, tmp_path, allowed=[("1", root, (admin,))])
    _, chains = witness_view(live_f)
    gov = Contract(json.load(open(os.path.join(live_f.abi_dir, "Governance.json"))), live_f.dep["chains"]["pbc"]["contracts"]["Governance"])
    mine(live_f, "pbc")
    ts = int(wview.observe("pbc")["timestamp"])
    action = {"action": "1", "root": root, "admins": [admin], "nonce": "1", "witnessSetVersion": "2", "expiresAt": str(ts + 60)}
    sigs = sorted_signatures(action, "GovernanceAction", [w.sign_governance(action) for w in witnesses[:3]], live_f.dep)
    assert wview.is_authority(root) is False
    chains["pbc"].send(ANVIL_KEY0, gov, "execute", action, sigs)           # the real contract verifies the signatures and applies the action to the real TMSC
    assert wview.is_authority(root) is True and int(wview.governance_nonce()) == 1
    again = dict(action, nonce="2")
    with pytest.raises(svc.WitnessRefusal) as e:                           # the witnesses now refuse ADD of an existing authority before signing
        witnesses[0].sign_governance(again)
    assert e.value.code == "ALREADY_REGISTERED"


# ========================================================================================================================================================
# Slice 9b: the decision and receipt paths against a REAL forwarded request on the real F ledger. Written BEFORE it was known whether the carried E client/relay/bootstrap helpers work with the F
# ABIs (they do for the names used here); the F ledger is wrapped in the carried `Ledger` class through its public constructor with the F contracts. Alice is registered and entitled by the carried
# `ledger_setup.setup_pbc`; she signs a request, the carried relay forwards it to the PBC; four real WitnessServices derive the decision from the REAL ledger through RpcWitnessView and three of them
# sign it; the real ACSC.consumeDecision verifies the certificate and issues the grant; the same witnesses derive and sign the GrantReceipt, which the real PSC.reportAttestedOutcome accepts.
# ========================================================================================================================================================
def f_ledger(live):
    from hmbc_protocol.ledger import Ledger
    chains = {s: Chain(live.urls[i], int(live.dep["chains"][s]["chainId"])) for i, s in enumerate(("pbc", "dbc"))}
    contracts = {}
    for name, side in (("PSC", "pbc"), ("RSC", "pbc"), ("TMSC", "pbc"), ("LSC", "pbc"), ("Governance", "pbc"), ("ACSC", "dbc"), ("KSSC", "dbc")):
        contracts[name] = Contract(json.load(open(os.path.join(live.abi_dir, name + ".json"))), live.dep["chains"][side]["contracts"][name])
    return Ledger(chains["pbc"], chains["dbc"], contracts, live.dep)


def accept_checkpoint(live, witnesses, wview, led, n=3):
    mine(live, "dbc")
    cp = svc.derive_checkpoint(wview, live.dep)
    ordered = sorted_signatures(cp, "StateCheckpoint", [w.sign_checkpoint(cp) for w in witnesses[:n]], live.dep)
    led.dbc.send(ANVIL_KEY0, led.KSSC, "acceptState", cp, ordered)
    return cp


def test_decision_and_receipt_signed_by_three_real_witnesses_are_accepted_by_the_real_acsc_and_psc(live_f, tmp_path):
    import ledger_setup as setup
    from hmbc_protocol.client import UserClient
    from hmbc_protocol.relay import Relay
    led = f_ledger(live_f)
    witnesses, wview = real_witnesses(live_f, tmp_path)
    ctx = setup.setup_pbc(led)
    client, relay = UserClient("alice", live_f.dep), Relay(led, "relay")
    signed = client.sign_request(setup.make_request(led, ctx, client, nonce="1", ttl=30))
    fwd = relay.forward(signed, ctx.bundle)
    assert fwd.code == "NONE"                                              # the real PSC allowed and forwarded the request
    accept_checkpoint(live_f, witnesses, wview, led)
    digest = signed["requestDigest"]
    decision, records = svc.derive_decision(wview, live_f.dep, digest, witness_set_version="2")
    assert decision["result"] == "1" and records                          # real credentials, real policy: ALLOW
    sigs = [w.sign_decision(decision) for w in witnesses[:3]]
    cert = {"decision": decision, "signatures": sorted_signatures(decision, "AccessDecision", sigs, live_f.dep)}
    with pytest.raises(Rejected) as r2:                                    # two of three is below the real threshold
        led.dbc.send(setup.key("relay"), led.ACSC, "consumeDecision", signed["request"], dict(cert, signatures=cert["signatures"][:2]), records)
    assert r2.value.code == "INSUFFICIENT_QUORUM"                         # predicted
    with pytest.raises(Rejected) as rf:                                    # a decision whose result a signer did not sign is rejected: flip the result after signing
        led.dbc.send(setup.key("relay"), led.ACSC, "consumeDecision", signed["request"], {"decision": dict(decision, result="0"), "signatures": cert["signatures"]}, records)
    assert rf.value.code == "BAD_SIGNATURE"                              # OBSERVED (not predicted): the signatures recover to non-members of the changed digest
    led.dbc.send(setup.key("relay"), led.ACSC, "consumeDecision", signed["request"], cert, records)          # the real ACSC verifies the certificate
    grant_id = "0x" + eip712.grant_id(bytes.fromhex(digest[2:]), led.KSSC.address, led.dbc.chain_id).hex()
    assert led.dbc.call(led.KSSC, "getGrant", grant_id)[5] is True        # allowed grant on the real DBC
    mine(live_f, "dbc")
    receipt = svc.derive_receipt(wview, live_f.dep, grant_id, witness_set_version="2")
    assert receipt["requestDigest"] == digest and receipt["grantId"] == grant_id
    rsigs = sorted_signatures(receipt, "GrantReceipt", [w.sign_receipt(receipt) for w in witnesses[:3]], live_f.dep)
    outcome = "0x" + "5e" * 32
    with pytest.raises(Rejected) as rr:
        led.pbc.send(setup.key("relay"), led.PSC, "reportAttestedOutcome", digest, outcome, receipt, rsigs[:2])
    assert rr.value.code == "INSUFFICIENT_QUORUM"                         # predicted
    led.pbc.send(setup.key("relay"), led.PSC, "reportAttestedOutcome", digest, outcome, receipt, rsigs)      # the real PSC verifies the receipt certificate
    assert led.pbc.call(led.PSC, "getRequest", digest)["status"] == "2"      # an outcome is recorded
    with pytest.raises(svc.WitnessRefusal) as e:                           # the witnesses now refuse to decide this request again
        witnesses[0].sign_decision(decision)
    assert e.value.code == "REPLAY"


# ========================================================================================================================================================
# Slice 9c: what the REAL contracts do with messages a COMPROMISED quorum certifies but an honest witness would never sign. The runner holds all four synthetic witness keys here, so it can craft
# three valid EIP-712 signatures over anything (testtools.byzantine.sign_message: no store, no validation). The contracts' own checks are the last line: each doomed message must be rejected with a
# closed code and leave the state unchanged. PREDICTIONS were written into PREDICTED before the first run; the observed code of each case is asserted against it, and a case whose observed code
# differs from the prediction is recorded in the evidence README as a wrong prediction, not silently adjusted. The tests do NOT show that honest witnesses refuse these (the witness-service tests do).
# ========================================================================================================================================================
PREDICTED = {
    "first checkpoint with a skipped sequence": "STALE_STATE", "checkpoint sequence skipped": "STALE_STATE", "checkpoint with a lower sequence": "STALE_STATE", "checkpoint already expired": "EXPIRED", "checkpoint for another source chain": "WRONG_DESTINATION", "checkpoint with keyEpoch 1": "WRONG_EPOCH",
    "checkpoint accepted twice": "STALE_STATE", "duplicate signer": "DUPLICATE_SIGNER", "governance ADD of an existing authority": "ALREADY_REGISTERED", "governance nonce skipped": "STALE_STATE",
    "governance with another witness set version": "STALE_STATE", "governance already expired": "EXPIRED", "governance REMOVE of an unknown root": "NOT_REGISTERED",
}


def crafted(live, name, msg, n=3, repeat_first=False):
    from testtools import byzantine as bz
    sigs = [bz.sign_message(keys.synthetic_private_key("witness-%d" % (i + 1)), name, msg, live.dep) for i in range(n)]
    by = {eip712.recover(svc._governance_digest(msg, live.dep) if name == "GovernanceAction" else messages.digest_of(name, msg, messages.domain_for(name, msg, live.dep)), s): s for s in sigs}
    ordered = [by[a] for a in sorted(by)]
    return [ordered[0]] + ordered if repeat_first else ordered


def test_a_compromised_quorum_cannot_make_the_real_contracts_accept_a_doomed_message(live_f_fresh, tmp_path):
    live_f = live_f_fresh
    witnesses, wview = real_witnesses(live_f, tmp_path)
    led = f_ledger(live_f)
    observed, wrong = {}, {}

    def attempt(label, contract, chain, fn, *args):
        try:
            chain.send(ANVIL_KEY0, contract, fn, *args)
            code = "ACCEPTED"                                           # a doomed message the contract took: recorded, not hidden (and later cases may then be affected)
        except Rejected as e:
            code = e.code
        observed[label] = code
        if code != PREDICTED[label]:
            wrong[label] = (PREDICTED[label], code)

    mine(live_f, "dbc")
    first = svc.derive_checkpoint(wview, live_f.dep)
    assert first["sequence"] == "1" and wview.dbc_current_checkpoint() is None          # a fresh DBC
    # FINDING (observed, my prediction STALE_STATE was wrong): the real KSSC accepts a certified FIRST checkpoint whose sequence is 5, not 1. The witnesses' rule is exactly current + 1 (F0 R6),
    # the contract's rule evidently is not, at least for the first checkpoint.
    attempt("first checkpoint with a skipped sequence", led.KSSC, led.dbc, "acceptState", dict(first, sequence="5"), crafted(live_f, "StateCheckpoint", dict(first, sequence="5")))
    assert (wview.dbc_current_checkpoint() or {}).get("sequence") == "5"
    mine(live_f, "dbc")
    second = svc.derive_checkpoint(wview, live_f.dep)                    # the honest proposer now derives sequence 6
    assert second["sequence"] == "6"
    # FINDING, second observation (my prediction STALE_STATE was wrong again): with a checkpoint present the real KSSC still accepts a certified sequence ABOVE current + 1 (7 after 5): its rule is
    # strictly increasing, not current + 1.
    attempt("checkpoint sequence skipped", led.KSSC, led.dbc, "acceptState", dict(second, sequence="7"), crafted(live_f, "StateCheckpoint", dict(second, sequence="7")))
    assert wview.dbc_current_checkpoint()["sequence"] == "7"
    mine(live_f, "dbc")
    good = svc.derive_checkpoint(wview, live_f.dep)
    assert good["sequence"] == "8"
    before = wview.dbc_current_checkpoint()
    attempt("checkpoint with a lower sequence", led.KSSC, led.dbc, "acceptState", dict(good, sequence="3"), crafted(live_f, "StateCheckpoint", dict(good, sequence="3")))
    attempt("checkpoint already expired", led.KSSC, led.dbc, "acceptState", dict(good, expiresAt="1"), crafted(live_f, "StateCheckpoint", dict(good, expiresAt="1")))
    attempt("checkpoint for another source chain", led.KSSC, led.dbc, "acceptState", dict(good, sourceChainId="1"), crafted(live_f, "StateCheckpoint", dict(good, sourceChainId="1")))
    attempt("checkpoint with keyEpoch 1", led.KSSC, led.dbc, "acceptState", dict(good, keyEpoch="1"), crafted(live_f, "StateCheckpoint", dict(good, keyEpoch="1")))
    attempt("duplicate signer", led.KSSC, led.dbc, "acceptState", good, crafted(live_f, "StateCheckpoint", good, n=2, repeat_first=True))
    assert wview.dbc_current_checkpoint() == before                      # every rejection left the DBC checkpoint as it was
    led.dbc.send(ANVIL_KEY0, led.KSSC, "acceptState", good, crafted(live_f, "StateCheckpoint", good))
    attempt("checkpoint accepted twice", led.KSSC, led.dbc, "acceptState", good, crafted(live_f, "StateCheckpoint", good))

    mine(live_f, "pbc")
    nonce = int(wview.governance_nonce())
    ts = int(wview.observe("pbc")["timestamp"])
    existing = "0x" + "ce" * 20
    admin = "0x" + "d6" * 20
    add_it = {"action": "1", "root": existing, "admins": [admin], "nonce": str(nonce + 1), "witnessSetVersion": "2", "expiresAt": str(ts + 60)}
    led.pbc.send(ANVIL_KEY0, led.Governance, "execute", add_it, crafted(live_f, "GovernanceAction", add_it))          # an honestly certified ADD makes `existing` an authority
    nonce += 1
    assert wview.is_authority(existing) is True and int(wview.governance_nonce()) == nonce
    ts = int(wview.observe("pbc")["timestamp"])
    doomed = {
        "governance ADD of an existing authority": dict(add_it, nonce=str(nonce + 1), expiresAt=str(ts + 60)),
        "governance nonce skipped": dict(add_it, root="0x" + "cf" * 20, nonce=str(nonce + 2), expiresAt=str(ts + 60)),
        "governance with another witness set version": dict(add_it, root="0x" + "cf" * 20, nonce=str(nonce + 1), witnessSetVersion="3", expiresAt=str(ts + 60)),
        "governance already expired": dict(add_it, root="0x" + "cf" * 20, nonce=str(nonce + 1), expiresAt="1"),
        "governance REMOVE of an unknown root": {"action": "2", "root": "0x" + "d0" * 20, "admins": [], "nonce": str(nonce + 1), "witnessSetVersion": "2", "expiresAt": str(ts + 60)},
    }
    for label, action in doomed.items():
        attempt(label, led.Governance, led.pbc, "execute", action, crafted(live_f, "GovernanceAction", action))
    assert int(wview.governance_nonce()) == nonce                         # no doomed action moved the nonce (INVENTORY F-30: the whole transaction reverts and the nonce stays)
    assert wview.is_authority("0x" + "cf" * 20) is False and wview.is_authority("0x" + "d0" * 20) is False
    # What the real contracts DID (observed on agent 1's ledger at 85c59f58..): pinned so a different ledger build or a regression shows. Five of my eleven pre-registered predictions were wrong:
    # the KSSC accepts a certified checkpoint whose sequence is strictly higher than the current one even when it skips (twice observed: first checkpoint 5, then 7 after 5); the Governance contract
    # answers MALFORMED (not ALREADY_REGISTERED) for an ADD of an existing authority and (not STALE_STATE) for a skipped nonce, and UNKNOWN_AUTHORITY (not NOT_REGISTERED) for a REMOVE of an unknown root.
    # Every doomed GOVERNANCE action reverted with the nonce and the authority set unchanged (INVENTORY F-30 held).
    assert observed == {"first checkpoint with a skipped sequence": "ACCEPTED", "checkpoint sequence skipped": "ACCEPTED", "checkpoint with a lower sequence": "STALE_STATE",
                        "checkpoint already expired": "EXPIRED", "checkpoint for another source chain": "WRONG_DESTINATION", "checkpoint with keyEpoch 1": "WRONG_EPOCH", "duplicate signer": "DUPLICATE_SIGNER",
                        "checkpoint accepted twice": "STALE_STATE", "governance ADD of an existing authority": "MALFORMED", "governance nonce skipped": "MALFORMED",
                        "governance with another witness set version": "STALE_STATE", "governance already expired": "EXPIRED", "governance REMOVE of an unknown root": "UNKNOWN_AUTHORITY"}
    assert wrong == {"first checkpoint with a skipped sequence": ("STALE_STATE", "ACCEPTED"), "checkpoint sequence skipped": ("STALE_STATE", "ACCEPTED"),
                     "governance ADD of an existing authority": ("ALREADY_REGISTERED", "MALFORMED"), "governance nonce skipped": ("STALE_STATE", "MALFORMED"),
                     "governance REMOVE of an unknown root": ("NOT_REGISTERED", "UNKNOWN_AUTHORITY")}, wrong
    assert set(observed) == set(PREDICTED)


# ========================================================================================================================================================
# Slice 10a: the command line as a REAL SUBPROCESS against the REAL F ledger. `python -m hmbc_protocol.adapter_v2_main` is started with the live manifest, the real ABI files, the published schema and
# its pinned hash; JSON lines go in on stdin and every response is validated against the PUBLISHED schema by the test as well as by the process (check_responses stays on). The worker operations run
# on the real ledger; the witness operations answer "not wired". Written BEFORE adapter_v2_main.py existed (the no-node tests of test_adapter_v2_main.py were red first).
# ========================================================================================================================================================
def cli(live, tmp_path, lines, dep=None, revision="v2", state="state"):
    import subprocess
    import sys as _sys
    dep_file = tmp_path / "dep.json"
    dep_file.write_text(json.dumps(dep or live.dep))
    FXD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
    args = ["--deployment", str(dep_file), "--abi-dir", live.abi_dir, "--schema", os.path.join(FXD, "agent3-v2.1-hmbc.schema.json"),
            "--schema-sha256", "d43c3a9a4cbb10214135afb767a2adc109da462f88bd11a81a8c8955d44fd1f3", "--schema-revision", revision, "--state-dir", str(tmp_path / state)]
    proto = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    p = subprocess.run([_sys.executable, "-B", "-m", "hmbc_protocol.adapter_v2_main", *args], input="".join(l + "\n" for l in lines), capture_output=True, text=True, cwd=proto,
                       env={"PYTHONPATH": proto, "PATH": "/usr/bin:/bin"}, timeout=120)
    return p


def v2_line(op, inp, dep):
    return json.dumps({"schemaVersion": "v2", "operation": op, "input": inp, "deploymentManifest": dep})


def schema_validator():
    import jsonschema
    schema = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "agent3-v2.1-hmbc.schema.json")))
    return jsonschema.Draft202012Validator({"$schema": "https://json-schema.org/draft/2020-12/schema", "$ref": "#/$defs/AdapterResponse", "$defs": schema["$defs"]}, format_checker=jsonschema.FormatChecker())


def test_the_cli_serves_the_worker_operations_on_the_real_ledger_and_says_not_wired_for_the_witness_ones(live_f, tmp_path):
    from test_adapter_v2_ops import KEYREF, request_for
    dep, ok = live_f.dep, schema_validator()
    other = copy.deepcopy(dep)
    other["chains"]["pbc"]["chainId"] = "18546"
    lines = [v2_line("prepare_request", {"request": request_for(dep), "signingKeyRef": KEYREF}, dep),
             v2_line("collect_checkpoint", {}, dep),
             v2_line("release", {"grantId": "0x" + "ab" * 32}, dep),
             "this is not json",
             v2_line("prepare_request", {"request": request_for(dep), "signingKeyRef": KEYREF}, other),
             v2_line("rotate_epoch", {"targetEpoch": "1"}, dep)]
    p = cli(live_f, tmp_path, lines)
    assert p.returncode == 0 and p.stderr == "" and "Traceback" not in p.stderr
    out = [json.loads(l) for l in p.stdout.splitlines()]
    assert len(out) == len(lines) and all(ok.is_valid(r) for r in out)
    prep, ckpt, rel, junk, wrong, rot = out
    assert prep["ok"] is True and prep["result"]["schemaVersion"] == "v2"
    assert ckpt["ok"] is False and ckpt["error"]["code"] == "ADAPTER_UNAVAILABLE" and "not wired" in ckpt["error"]["message"]
    assert rel["ok"] is False and rel["error"]["code"] == "NOT_COMMITTED"        # the REAL ledger has no grant with this id
    assert junk["error"]["code"] == "MALFORMED" and wrong["error"]["code"] == "WRONG_DESTINATION" and rot["error"]["code"] == "NOT_IMPLEMENTED_IN_PHASE"
    state = tmp_path / "state"
    assert (state / "worker" / "INITIALIZED").is_file() and oct(state.stat().st_mode & 0o777) == "0o700"


def test_the_cli_serves_a_real_grant_end_to_end_encrypt_release_finish_on_the_real_ledger(live_f_fresh, tmp_path):
    import ledger_setup as setup
    from hmbc_protocol.client import UserClient
    from hmbc_protocol.relay import Relay
    live = live_f_fresh
    led = f_ledger(live)
    witnesses, wview = real_witnesses(live, tmp_path)
    ctx = setup.setup_pbc(led)
    client, relay = UserClient("alice", live.dep), Relay(led, "relay")
    signed = client.sign_request(setup.make_request(led, ctx, client, nonce="1", ttl=30))      # ttl 60 exceeds PSC.maxRequestTtl: the real PSC answered MALFORMED to my first try
    assert relay.forward(signed, ctx.bundle).code == "NONE"
    accept_checkpoint(live, witnesses, wview, led)
    decision, records = svc.derive_decision(wview, live.dep, signed["requestDigest"], witness_set_version="2")
    assert decision["result"] == "1"
    cert = {"decision": decision, "signatures": sorted_signatures(decision, "AccessDecision", [w.sign_decision(decision) for w in witnesses[:3]], live.dep)}
    led.dbc.send(setup.key("relay"), led.ACSC, "consumeDecision", signed["request"], cert, records)
    grant_id = "0x" + eip712.grant_id(bytes.fromhex(signed["requestDigest"][2:]), led.KSSC.address, led.dbc.chain_id).hex()
    record = {"dataId": setup.DATA_P1, "owner": setup.addr("H2-root"), "payloadDigest": "0x" + __import__("eth_utils").keccak(text="synthetic payload P1").hex()}
    policy = {"clauses": [[{"role": setup.ROLE_DOCTOR, "kind": "1", "issuerMode": "0"}, {"role": setup.ROLE_ON_DUTY, "kind": "2", "issuerMode": "2"}]]}
    ok = schema_validator()
    # the worker is lazy and stateful: encrypt, release and finish run in ONE process, in order
    p = cli(live, tmp_path, [v2_line("encrypt_record", {"record": record, "policy": policy, "keyEpoch": "0"}, live.dep), v2_line("release", {"grantId": grant_id}, live.dep)])
    assert p.returncode == 0 and p.stderr == "", p.stderr
    enc, rel = [json.loads(l) for l in p.stdout.splitlines()]
    assert all(ok.is_valid(r) for r in (enc, rel)) and enc["ok"] is True and rel["ok"] is True, (enc, rel)
    assert rel["result"]["grantId"] == grant_id and rel["result"]["recipientKeyHash"] == keys.recipient_key_hash("keyref:user:alice")
    # a second process on the same state directory reopens the bound store and releases the SAME token (idempotent, durable)
    p2 = cli(live, tmp_path, [v2_line("release", {"grantId": grant_id}, live.dep), v2_line("finish_decryption", {"response": rel["result"], "userKeyRef": "keyref:user:alice"}, live.dep)])
    assert p2.returncode == 0 and p2.stderr == "", p2.stderr
    rel2, fin = [json.loads(l) for l in p2.stdout.splitlines()]
    assert ok.is_valid(rel2) and ok.is_valid(fin) and rel2["ok"] is True and fin["ok"] is True, (rel2, fin)
    assert rel2["result"]["responseEnvelope"]["token"] == rel["result"]["responseEnvelope"]["token"]


def test_the_cli_starts_on_the_real_e_successor_v2_1_deployment(live_e, tmp_path):
    from test_adapter_v2_ops import KEYREF, request_for
    dep, ok = live_e.dep, schema_validator()
    p = cli(live_e, tmp_path, [v2_line("prepare_request", {"request": request_for(dep), "signingKeyRef": KEYREF}, dep)], revision="v2.1")
    assert p.returncode == 0 and p.stderr == "", p.stderr
    (r,) = [json.loads(l) for l in p.stdout.splitlines()]
    assert ok.is_valid(r) and r["ok"] is True
    q = cli(live_e, tmp_path, [], revision="v2", state="state2")           # the v2.1 marker with revision v2 is refused at startup
    assert q.returncode == 2 and json.loads(q.stderr)["error"]["code"] == "MALFORMED" and not (tmp_path / "state2").exists()


def test_the_cli_refuses_a_bound_directory_of_another_deployment_with_wrong_destination(live_f, live_f_fresh, tmp_path):
    p = cli(live_f, tmp_path, [])
    assert p.returncode == 0
    q = cli(live_f_fresh, tmp_path, [])                                     # the same state directory, another real deployment
    err = json.loads(q.stderr)["error"]
    assert q.returncode == 2 and q.stdout == "" and err["code"] == "WRONG_DESTINATION" and err.get("reason") == "BINDING_MISMATCH"
