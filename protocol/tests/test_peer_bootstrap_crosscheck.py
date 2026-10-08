"""Cross-implementation check of agent 1's ledger-owned bootstrap producer (A1-0029/A1-0030) against agent 2's independent one.

Two producers written independently (agent 1: a read-only Foundry script; agent 2: Python over the EIP-712 encoder in hmbc_protocol) must agree on every signed byte
when they are given the same deployment and the same clock, because RFC 6979 signatures are deterministic. This test also pushes the PEER's output through agent 2's
adapter PROCESS (the witness recovers the runner-passed bundle from calldata) and answers the two points A1-0029 asked agent 2 to confirm.

The peer tool is taken from a `git archive` of the pinned commit, never from this checkout; nothing of agent 1's is edited. The runner role is played by the test
with ONLY the relay and CA-admin TEST keys. Nothing here is an E1 result.
"""
import json
import os
import pathlib
import subprocess
import tarfile

import pytest

from hmbc_protocol import keys
from hmbc_protocol.chain import Rejected
from hmbc_protocol.ledger import Ledger
from support import foundry
import ledger_setup as setup
from test_bootstrap_fixture import assert_alice_flow, assert_bob_denial

REPO = pathlib.Path(__file__).resolve().parents[2]
PEER_COMMIT = "9d6911d9a35c7d20b3e0226400f8f0fcc99ef256"       # origin/agent-1, A1-0030 (READY: ledger TEST-ONLY bootstrap producer)
PROFILES = ["ledger", "ledger_paper", "ledger_paper_minimal"]


@pytest.fixture(scope="session")
def peer_root(tmp_path_factory):
    if not foundry("forge"):
        pytest.skip("Foundry not installed")
    if subprocess.run(["git", "cat-file", "-e", PEER_COMMIT], cwd=REPO, capture_output=True).returncode != 0:
        pytest.skip(f"peer commit {PEER_COMMIT} not available locally (git fetch origin)")
    root = tmp_path_factory.mktemp("peer-bootstrap")
    tar = root / "snap.tar"
    tar.write_bytes(subprocess.run(["git", "archive", PEER_COMMIT], cwd=REPO, capture_output=True, check=True).stdout)
    with tarfile.open(tar) as t:
        t.extractall(root / "src", filter="data")
    return root / "src"


def peer_output(peer_root, led, tmp_path):
    dep = tmp_path / "peer-deployment.json"
    dep.write_text(json.dumps(led.deployment))
    out = tmp_path / "peer-out.json"
    env = {**os.environ, "PATH": f"{pathlib.Path(foundry('forge')).parent}:{os.environ['PATH']}"}
    p = subprocess.run(["bash", "ledger/tools/bootstrap_fixture.sh", led.pbc.url, str(dep), str(out)], cwd=peer_root, env=env, capture_output=True, text=True, timeout=600)
    assert p.returncode == 0, p.stdout[-1500:] + p.stderr[-1500:]
    return json.loads(out.read_text())


def mine_for_clock(led, now):
    from testtools import bootstrap_fixture
    return bootstrap_fixture.build_plan(led, now)


@pytest.mark.parametrize("fixture_name", PROFILES)
def test_identities_and_every_signed_artifact_equal_the_independent_producer_for_the_same_clock(request, fixture_name, peer_root, tmp_path):
    chains = request.getfixturevalue(fixture_name)
    led = Ledger.from_deployment(chains.deployment)
    peer = peer_output(peer_root, led, tmp_path)
    assert peer["schemaVersion"] == "hmbc-ledger-bootstrap/v0" and peer["testOnly"] is True
    mine = mine_for_clock(led, int(peer["binding"]["blockTimestamp"]))
    # A1-0029 point 2: keyref:user:alice/bob are the same GIDs, and the recipient hashes follow the A35 convention
    for label in ("alice", "bob"):
        assert peer["users"][label]["gid"] == mine["identities"][label]["gid"] == setup.addr(label)
        assert peer["users"][label]["recipientKeyHash"] == mine["identities"][label]["recipientKeyHash"] == keys.recipient_key_hash(f"keyref:user:{label}")
    steps = {s["id"]: s["args"] for s in mine["steps"]}
    for entry, step_id, key in zip(peer["trustLists"], ("h1-revocation-list", "h1-temporal-acl", "h2-revocation-list"), ("list", "acl", "list")):
        assert entry["list"] == steps[step_id][key], step_id
        assert entry["signature"] == steps[step_id]["issuerSignature"], step_id
    for label in ("alice", "bob"):
        a, u = steps[f"register-{label}"], peer["users"][label]
        assert u["registration"] == a["reg"] and u["possessionSignature"] == a["possessionSignature"] and u["certificate"] == a["cert"], label
        assert u["bundle"] == mine["credentialBundles"][label], label


@pytest.mark.parametrize("fixture_name", PROFILES)
def test_the_peers_bootstrap_registers_both_users_on_every_profile_through_the_runner_path(request, fixture_name, peer_root, tmp_path):
    chains = request.getfixturevalue(fixture_name)
    led = Ledger.from_deployment(chains.deployment)
    peer = peer_output(peer_root, led, tmp_path)
    submit_peer(led, peer)
    for label in ("alice", "bob"):
        assert led.pbc.call(led.RSC, "isRegistered", peer["users"][label]["gid"]) is True
        assert led.pbc.call(led.RSC, "recipientKeyHash", peer["users"][label]["gid"]) == peer["users"][label]["recipientKeyHash"]


def submit_peer(led, peer):
    """The runner's steps 3-4 from A1-0030, with ONLY relay/CA-admin TEST keys."""
    for t in peer["trustLists"]:
        contract_name, fn = t["call"].split(".")
        assert t["submitterRole"] in {"H1-ca-admin", "H2-ca-admin"}
        led.pbc.send(keys.synthetic_private_key(t["submitterRole"]), getattr(led, contract_name), fn, t["list"], t["signature"])
    for label in ("alice", "bob"):
        u = peer["users"][label]
        led.pbc.send(keys.synthetic_private_key("relay"), led.RSC, "register", u["registration"], u["possessionSignature"], u["certificate"])


def test_alice_completes_the_flow_through_the_adapter_process_with_the_peers_bundle(ledger, peer_root, tmp_path):
    """A1-0029 point 1: the runner-passed bundle is what the witness recovers from requestAccess calldata (here: an ALLOW for Alice)."""
    led = Ledger.from_deployment(ledger.deployment)
    peer = peer_output(peer_root, led, tmp_path)
    submit_peer(led, peer)
    assert_alice_flow(led, peer["users"]["alice"]["bundle"], peer["users"]["alice"]["recipientKeyHash"], tmp_path / "adapter-state")


def test_bob_reaches_the_native_denial_with_the_peers_bundle(ledger, peer_root, tmp_path):
    led = Ledger.from_deployment(ledger.deployment)
    peer = peer_output(peer_root, led, tmp_path)
    submit_peer(led, peer)
    assert_bob_denial(led, peer["users"]["bob"]["bundle"], peer["users"]["bob"]["gid"], tmp_path / "adapter-state")


def test_the_peers_own_h2_list_doubles_as_the_wrong_issuer_admin_control_if_sent_first_from_h1(ledger, peer_root, tmp_path):
    """No extra artifact is needed for the frozen WrongIssuerAdmin control: submit the produced H2 list from H1-ca-admin BEFORE the legitimate submission."""
    led = Ledger.from_deployment(ledger.deployment)
    peer = peer_output(peer_root, led, tmp_path)
    h2 = peer["trustLists"][2]
    assert h2["submitterRole"] == "H2-ca-admin"
    epoch = led.pbc.call(led.TMSC, "authEpoch")
    with pytest.raises(Rejected) as e:
        led.pbc.send(keys.synthetic_private_key("H1-ca-admin"), led.TMSC, "updateRevocationList", h2["list"], h2["signature"])
    assert e.value.code == "UNAUTHORIZED_CALLER"
    assert led.pbc.call(led.TMSC, "authEpoch") == epoch
    led.pbc.send(keys.synthetic_private_key("H2-ca-admin"), led.TMSC, "updateRevocationList", h2["list"], h2["signature"])        # the rightful admin may submit the same artifact
    assert led.pbc.call(led.TMSC, "authEpoch") != epoch
