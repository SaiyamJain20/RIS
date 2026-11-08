"""Successor adapter startup order (agent 2, F task 2 slice 6c). Written BEFORE hmbc_protocol/adapter_v2_start.py existed.

`start(...)` composes what the other slices built, in the order D50 and SUCCESSOR-WIRE section 5 require, and returns the `adapter_v2.Context` the serving loop needs:
  0. cheap validation with no I/O (the explicit schema revision against the manifest marker; the wiring arguments are all-or-nothing),
  1. the D50 live reconstruction, stages 1 to 8, through the injected chain view (role `worker`: the adapter process holds no witness key),
  2. only then the worker store directory `<state_dir>/worker` is bound to the reconstructed deployment (the `INITIALIZED` marker is the last write),
  3. only then the handlers are installed and the Context is built.
Any refusal leaves NOTHING behind: no directory, no marker, no handler, no transport and no worker. The worker and the witness transport are made lazily by the injected factories, never at startup.
The chain view and every factory are INJECTED fakes here (the real chain view, the real worker factory and the witness processes are the integrated run's business); this file checks the ORDER and the
all-or-nothing behaviour, not the pieces, which have their own tests and mutants.
"""
import copy
import json
import os

import pytest

from hmbc_protocol import adapter_v2 as av2
from hmbc_protocol import adapter_v2_start as st
from hmbc_protocol import binding as bd
from hmbc_protocol import binding_open as bo
from hmbc_protocol import witness_state as ws
from hmbc_protocol import worker_binding as wb

from test_binding_open import ADDRS, FAULTS, Chains
from test_binding_open import make_manifest as _make_manifest


def make_manifest(family):
    m = _make_manifest(family)
    m["fixture"].update({"keyEpoch": "0", "policyVersion": "1"})          # the structural minimum the carried signer needs
    return m

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ADDRS4 = ["0x" + "%02x" % (0xB0 + i) * 20 for i in range(4)]
WORKER_FAULTS = [(r, f) for r, f in FAULTS if r != "UNKNOWN_AUTHORITY"]          # the witness-role check: an adapter process has no key


class Spy:
    def __init__(self):
        self.workers, self.transports = [], []

    def worker_factory(self, ctx):
        self.workers.append(ctx)
        raise AssertionError("the worker must not be made at startup")

    def transport_factory(self, kind):
        self.transports.append(kind)
        raise AssertionError("no transport at startup")


def go(tmp_path, family="F", manifest=None, chains=None, spy=None, witness=True, rev="v2", **over):
    m = manifest or make_manifest(family)
    ch = chains or Chains(m)
    spy = spy or Spy()
    kw = dict(manifest=m, schema_revision=rev, chain_view=ch, state_dir=str(tmp_path / "state"), worker_factory=spy.worker_factory)
    if witness:
        kw.update(witness_view=object(), witnesses=ADDRS4, transport_factory=spy.transport_factory)
    kw.update(over)
    return st.start(**kw), m, ch, spy


WORKER_OPS = {"prepare_request", "encrypt_record", "release", "finish_decryption"}
WITNESS_OPS = {"collect_checkpoint", "collect_decision", "attest_grant", "collect_governance"}


def test_an_honest_f_deployment_starts_binds_the_worker_directory_and_installs_all_eight_handlers(tmp_path):
    ctx, m, ch, spy = go(tmp_path)
    assert isinstance(ctx, av2.Context) and ctx.manifest == m and set(ctx.handlers) == WORKER_OPS | WITNESS_OPS
    assert len(ch.requests) == 55                                   # the F startup read schedule, nothing more
    d = str(tmp_path / "state" / "worker")
    assert os.path.exists(os.path.join(d, "INITIALIZED"))
    r = bo.reconstruct(m, Chains(m), role="worker")
    bound = wb.view_for_export(d)
    assert bound["owner"] == "worker" and bound["binding_v2"] == r["binding_v2"] and bound["document"] == r["document"] and bound["anchor"] == r["anchor"]
    assert spy.workers == [] and spy.transports == []


def test_without_the_witness_wiring_only_the_worker_operations_are_installed(tmp_path):
    ctx, *_ = go(tmp_path, witness=False)
    assert set(ctx.handlers) == WORKER_OPS


def test_an_e_deployment_starts_with_48_requests_and_the_worker_operations(tmp_path):
    ctx, m, ch, _ = go(tmp_path, family="E", rev="v2", witness=False)
    assert len(ch.requests) == 48 and set(ctx.handlers) == WORKER_OPS


@pytest.mark.parametrize("reason,fault", WORKER_FAULTS, ids=[r for r, _ in WORKER_FAULTS])
def test_every_open_refusal_leaves_nothing_behind_and_makes_nothing(tmp_path, reason, fault):
    m = make_manifest("F")
    ch = Chains(m)
    fault(m, ch)
    spy = Spy()
    with pytest.raises(bd.OpenRefusal) as e:
        go(tmp_path, manifest=m, chains=ch, spy=spy)
    assert e.value.reason == reason
    assert not os.path.exists(tmp_path / "state")                   # not even the directory
    assert spy.workers == [] and spy.transports == []


def test_a_second_start_on_the_same_directory_opens_it_unchanged(tmp_path):
    go(tmp_path)
    marker = tmp_path / "state" / "worker" / "INITIALIZED"
    before = marker.read_bytes()
    ctx, *_ = go(tmp_path)
    assert set(ctx.handlers) == WORKER_OPS | WITNESS_OPS and marker.read_bytes() == before


def test_a_directory_bound_to_another_deployment_is_refused_and_no_context_is_built(tmp_path):
    go(tmp_path)
    other = make_manifest("F")
    other["chains"]["pbc"]["chainId"] = "18546"                     # an honest but different deployment
    with pytest.raises(ws.StoreError) as e:
        go(tmp_path, manifest=other)
    assert e.value.code == "WRONG_DESTINATION" and e.value.reason == "BINDING_MISMATCH"


def test_a_schema_revision_that_does_not_match_the_manifest_is_refused_before_any_chain_read(tmp_path):
    m = make_manifest("F")
    m["schemaVersion"] = "hmbc-ledger-deployment/v2.1"
    ch = Chains(m)
    with pytest.raises(ValueError):
        go(tmp_path, manifest=m, chains=ch, rev="v2")
    assert ch.requests == [] and not os.path.exists(tmp_path / "state")


@pytest.mark.parametrize("drop", ["witness_view", "witnesses", "transport_factory"])
def test_the_witness_wiring_is_all_or_nothing_and_refused_before_any_chain_read(tmp_path, drop):
    m = make_manifest("F")
    ch = Chains(m)
    spy = Spy()
    kw = dict(manifest=m, schema_revision="v2", chain_view=ch, state_dir=str(tmp_path / "state"), worker_factory=spy.worker_factory,
              witness_view=object(), witnesses=ADDRS4, transport_factory=spy.transport_factory)
    del kw[drop]
    with pytest.raises(ValueError):
        st.start(**kw)
    assert ch.requests == [] and not os.path.exists(tmp_path / "state")


def test_the_witness_addresses_are_validated_before_any_chain_read(tmp_path):
    m = make_manifest("F")
    ch = Chains(m)
    with pytest.raises(ValueError):
        go(tmp_path, manifest=m, chains=ch, witnesses=ADDRS4[:3])
    assert ch.requests == []


@pytest.mark.parametrize("bad", [None, 5, "x"])
def test_the_worker_factory_must_be_callable_and_is_checked_first(tmp_path, bad):
    m = make_manifest("F")
    ch = Chains(m)
    with pytest.raises(ValueError):
        go(tmp_path, manifest=m, chains=ch, worker_factory=bad)
    assert ch.requests == []


def test_the_state_directory_must_be_a_non_empty_string(tmp_path):
    for bad in (None, "", 5):
        m = make_manifest("F")
        ch = Chains(m)
        with pytest.raises(ValueError):
            go(tmp_path, manifest=m, chains=ch, state_dir=bad)
        assert ch.requests == []


def test_the_witness_handlers_are_wired_to_the_given_view_and_transport_factory_and_the_worker_ones_to_the_worker_factory(tmp_path):
    class View:
        def dbc_current_checkpoint(self):
            raise LookupError("the witness view was reached")

    spy = Spy()
    ctx, *_ = go(tmp_path, spy=spy, witness_view=View())
    with pytest.raises(LookupError):                              # the proposer derives from the witness view the caller injected
        ctx.handlers["collect_checkpoint"]({}, ctx)
    with pytest.raises(AssertionError, match="worker must not"):  # the worker comes from the worker factory, called with the Context, and only when an operation runs
        ctx.handlers["release"]({"grantId": "0x" + "00" * 32}, ctx)
    assert spy.workers == [ctx]


def test_the_module_reads_no_clock_no_thread_no_socket_and_no_environment():
    src = open(os.path.join(ROOT, "protocol", "hmbc_protocol", "adapter_v2_start.py")).read()
    for banned in ("import time", "from time", "datetime", "import threading", "import socket", "import random", "import asyncio", "subprocess", "os.environ"):
        assert banned not in src, banned


def test_a_published_schema_is_applied_to_the_manifest_before_any_chain_read(tmp_path):
    schema = json.load(open(os.path.join(ROOT, "protocol", "tests", "fixtures", "agent3-v2.1-hmbc.schema.json")))
    m = make_manifest("F")                                          # a synthetic manifest: far from a full LedgerDeployment
    ch = Chains(m)
    with pytest.raises(ValueError):
        go(tmp_path, manifest=m, chains=ch, schema=schema)
    assert ch.requests == [] and not os.path.exists(tmp_path / "state")
