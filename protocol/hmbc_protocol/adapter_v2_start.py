"""Successor adapter startup order (HMBC2020 successor, F task 2 slice 6c): `start` composes the pieces in the order D50 and SUCCESSOR-WIRE section 5 require and returns the `adapter_v2.Context`.

PAPER-DERIVED RECONSTRUCTION. The order, and why:
  0. validation with NO I/O: the explicit schema revision against the manifest marker (a dry `Context`), the factories being callable, the state directory being a non-empty string, and the witness
     wiring being all-or-nothing (and its addresses well formed). A caller bug is refused before the chain is asked anything.
  1. the D50 live reconstruction, stages 1 to 8 (`binding_open.reconstruct`, role `worker`: the adapter process holds no witness key), through the injected chain view. The first failing stage refuses.
  2. only then `worker_binding.bind_worker_dir(<state_dir>/worker, ...)`: the directory is created, or an existing one is compared; the INITIALIZED marker is the last write. A directory bound to
     another deployment is refused (`StoreError` BINDING_MISMATCH).
  3. only then the handlers are installed (`prepare_request` and the three key-worker operations; the four witness operations when the witness wiring is given) and the Context is built.
A refusal at any step leaves nothing behind: no directory, no marker, no handler, no transport and no worker. The worker and the witness transport are made lazily, per call, by the injected factories;
startup never calls them. The chain view, the worker factory, the witness view and the transport factory are INJECTED: the real ones (JSON-RPC views of both chains, a `Worker` over the real ledger, supervised
witness channels) belong to the integrated run and are NOT here. This module does not parse a command line and reads no clock, environment or file by itself.
"""
from __future__ import annotations

import os

from . import adapter_v2 as av2
from . import adapter_v2_ops as ops
from . import adapter_v2_witness as aw
from . import binding_open as bo
from . import worker_binding as wb

WORKER_SUBDIR = "worker"


def start(*, manifest, schema_revision, chain_view, state_dir, worker_factory, witness_view=None, witnesses=None, transport_factory=None, schema=None):
    """Returns the Context, or raises: ValueError for a caller bug (nothing was read), `binding.OpenRefusal` for a deployment that does not verify (stage reason in `.reason`), `witness_state.StoreError`
    for a worker directory that is corrupt, legacy or bound to another deployment."""
    av2.Context(manifest=manifest, schema_revision=schema_revision, handlers={}, schema=schema)          # step 0: the revision and the manifest marker agree (no I/O)
    if not callable(worker_factory):
        raise ValueError("worker_factory must be callable")
    if not isinstance(state_dir, str) or not state_dir:
        raise ValueError("state_dir must be a non-empty string")
    wiring = (witness_view, witnesses, transport_factory)
    if any(x is not None for x in wiring) and any(x is None for x in wiring):
        raise ValueError("the witness wiring is witness_view, witnesses and transport_factory together, or none of them")
    witness_ops = {} if witness_view is None else aw.witness_handlers(view=witness_view, witnesses=witnesses, transport_factory=transport_factory)
    r = bo.reconstruct(manifest, chain_view, role="worker")                                              # step 1: stages 1 to 8
    wb.bind_worker_dir(os.path.join(state_dir, WORKER_SUBDIR), r["binding_v2"], r["document"], r["anchor"])      # step 2: the store identity
    handlers = {"prepare_request": ops.prepare_request, **ops.worker_handlers(worker_factory), **witness_ops}   # step 3
    return av2.Context(manifest=manifest, schema_revision=schema_revision, handlers=handlers, schema=schema)
