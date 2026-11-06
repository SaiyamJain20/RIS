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
        digest = svc._governance_digest(m, deployment) if name == "GovernanceAction" else messages.digest_of(name, m, messages.domain_for(name, m, deployment))
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
