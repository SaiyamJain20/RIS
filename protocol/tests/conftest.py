"""Live-ledger fixtures: two Anvil nodes + agent-1's exact ledger snapshot deployed in repaired-e.

Everything is created in a temp dir from `git archive <pinned commit>`; no peer file in this repository is touched, and only
the two Anvil processes this fixture starts are ever stopped. Tests that need it skip when Foundry or the pinned commit is missing.
"""
import hashlib
import json
import os
import pathlib
import socket
import subprocess
import tarfile
import time
from types import SimpleNamespace

import pytest

from support import foundry, rpc

REPO = pathlib.Path(__file__).resolve().parents[2]
LEDGER_COMMIT = "33a7a5dbb040bce61caf357673722a68ae464cb3"           # origin/agent-1, A1-0014 + A1-0015
ABI_MANIFEST_SHA256 = hashlib.sha256((pathlib.Path(__file__).resolve().parents[1] / "abi/manifest.json").read_bytes()).hexdigest()
ANVIL_KEY0 = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"   # Anvil's public default account 0 (test-only)
PBC_ID, DBC_ID = 18545, 28545


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait(url: str):
    for _ in range(100):
        try:
            rpc(url, "eth_chainId")
            return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"anvil at {url} did not start")


def _deploy_profile(tmp_path_factory, profile: str):
    """Start two Anvil nodes and deploy agent-1's pinned ledger in `profile` ('repaired-e', 'paper-strict', 'mutant-no-nonce', ...). Generator: yields the
    deployment namespace, then stops ONLY the two processes it started."""
    anvil, forge = foundry("anvil"), foundry("forge")
    if not anvil or not forge:
        pytest.skip("Foundry (anvil/forge) not installed")
    if subprocess.run(["git", "cat-file", "-e", LEDGER_COMMIT], cwd=REPO, capture_output=True).returncode != 0:
        pytest.skip(f"pinned ledger commit {LEDGER_COMMIT} not available locally (git fetch origin)")
    root = tmp_path_factory.mktemp(f"ledger-snapshot-{profile}")
    tar = subprocess.run(["git", "archive", LEDGER_COMMIT], cwd=REPO, capture_output=True, check=True).stdout
    tmp_tar = root / "snap.tar"
    tmp_tar.write_bytes(tar)
    with tarfile.open(tmp_tar) as t:
        t.extractall(root / "src", filter="data")
    src = root / "src"
    assert hashlib.sha256((src / "ledger/exports/abi/manifest.json").read_bytes()).hexdigest() == ABI_MANIFEST_SHA256, "ABI fixtures differ from the pinned commit"
    ports = (_free_port(), _free_port())
    procs = [subprocess.Popen([anvil, "--port", str(p), "--chain-id", str(cid), "--silent"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
             for p, cid in zip(ports, (PBC_ID, DBC_ID))]
    try:
        urls = [f"http://127.0.0.1:{p}" for p in ports]
        for u in urls:
            _wait(u)
        env = {**os.environ, "PATH": f"{pathlib.Path(forge).parent}:{os.environ['PATH']}", "DEPLOYER_PK": ANVIL_KEY0}
        run = subprocess.run(["bash", "ledger/tools/deploy_local.sh", urls[0], urls[1], profile, "complete-details", "protocol-tests"],
                             cwd=src, env=env, capture_output=True, text=True, timeout=600)
        assert run.returncode == 0, run.stdout[-1500:] + run.stderr[-1500:]
        dep = json.loads((src / "ledger/exports/deployments/protocol-tests/deployment.json").read_text())
        yield SimpleNamespace(deployment=dep, pbc_url=urls[0], dbc_url=urls[1], root=src, profile=profile)
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()


@pytest.fixture(scope="session")
def ledger_chains(tmp_path_factory):
    yield from _deploy_profile(tmp_path_factory, "repaired-e")


@pytest.fixture(scope="session")
def ledger_chains_paper(tmp_path_factory):
    yield from _deploy_profile(tmp_path_factory, "paper-strict")


@pytest.fixture(scope="session")
def ledger_chains_paper_minimal(tmp_path_factory):
    yield from _deploy_profile(tmp_path_factory, "paper-minimal")


@pytest.fixture(scope="session")
def ledger_chains_no_nonce(tmp_path_factory):
    yield from _deploy_profile(tmp_path_factory, "mutant-no-nonce")


@pytest.fixture(scope="session")
def ledger_chains_no_receipt_binding(tmp_path_factory):
    yield from _deploy_profile(tmp_path_factory, "mutant-no-receipt-binding")


def _isolated(chains):
    ids = [rpc(u, "evm_snapshot") for u in (chains.pbc_url, chains.dbc_url)]
    yield chains
    for u, i in zip((chains.pbc_url, chains.dbc_url), ids):
        assert rpc(u, "evm_revert", [i]) is True


@pytest.fixture
def ledger(ledger_chains):
    """Per-test isolation: revert both chains to the freshly-deployed state afterwards (snapshot ids are single-use)."""
    ids = [rpc(u, "evm_snapshot") for u in (ledger_chains.pbc_url, ledger_chains.dbc_url)]
    yield ledger_chains
    for u, i in zip((ledger_chains.pbc_url, ledger_chains.dbc_url), ids):
        assert rpc(u, "evm_revert", [i]) is True


@pytest.fixture
def world(ledger):
    """(Ledger view, authority context) after the PBC fixture setup: CRLs, Alice on duty, Alice registered."""
    from hmbc_protocol import ledger as ledger_mod
    import ledger_setup
    led = ledger_mod.Ledger.from_deployment(ledger.deployment)
    return led, ledger_setup.setup_pbc(led)


def _world(chains):
    from hmbc_protocol import ledger as ledger_mod
    import ledger_setup
    led = ledger_mod.Ledger.from_deployment(chains.deployment)
    return led, ledger_setup.setup_pbc(led)


@pytest.fixture
def ledger_paper(ledger_chains_paper):
    yield from _isolated(ledger_chains_paper)


@pytest.fixture
def world_paper(ledger_paper):
    return _world(ledger_paper)


@pytest.fixture
def ledger_no_nonce(ledger_chains_no_nonce):
    yield from _isolated(ledger_chains_no_nonce)


@pytest.fixture
def world_no_nonce(ledger_no_nonce):
    return _world(ledger_no_nonce)


@pytest.fixture
def ledger_no_receipt_binding(ledger_chains_no_receipt_binding):
    yield from _isolated(ledger_chains_no_receipt_binding)


@pytest.fixture
def world_no_receipt_binding(ledger_no_receipt_binding):
    return _world(ledger_no_receipt_binding)


@pytest.fixture
def ledger_paper_minimal(ledger_chains_paper_minimal):
    yield from _isolated(ledger_chains_paper_minimal)


@pytest.fixture
def world_paper_minimal(ledger_paper_minimal):
    return _world(ledger_paper_minimal)
