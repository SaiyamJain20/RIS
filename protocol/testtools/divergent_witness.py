"""TEST-ONLY real-PROCESS divergent ledger view (H3 as a supervised child; agent 2, F phase; gap G2). PAPER-DERIVED RECONSTRUCTION; synthetic TEST-ONLY keys. Not imported by any production module; not an
adapter operation; not in exports/adapter.json.

    python -m testtools.divergent_witness --view SPEC <the production witness's own arguments>
    SPEC  authEpoch:N | policyVersion:N | witnessSetVersion:N | headLag:N        (N a canonical decimal 1..50)

Serves the PRODUCTION witness process (`hmbc_protocol.witness_main`: same arguments, wire, start-up, durable store, exit codes) with ONE difference inside this process: the `RpcWitnessView` it reads the
real chains through is wrapped so that its reads DIVERGE from the real ledger:
  authEpoch:N, policyVersion:N, witnessSetVersion:N   `reads_at(n)` returns the real value + N for that field (a value that is not a canonical decimal is left alone);
  headLag:N                                           the PBC this witness sees is N blocks behind: `observe("pbc")` reports block head-N (clamped at genesis) and `pbc_block(n)` is None above it.
Every other read is delegated to the real view unchanged. D50 start-up uses the real, unwrapped binding view, so the process starts and binds its store exactly as the production witness does. This breaks the
safe-ledger assumption BY DESIGN (INVENTORY H3) and is for the conditional rows only (F-16, F-17, F-18, F-31). How, without editing any existing file: `install()` replaces `RpcWitnessView.from_manifest`
IN THIS PROCESS ONLY with a wrapper that returns a `DivergentView` around what the original builds. Refuses (non-zero exit, empty stdout, `refusing:` on stderr, nothing created) unless `--view` is a valid
SPEC and the deployment declares TEST-ONLY synthetic keys. Not claimed: that any oracle accepts what it produces; anything about clocks, reorgs or independent hosts.
"""
from __future__ import annotations

import argparse
import re
import sys

from hmbc_protocol import adapter
from hmbc_protocol import rpc_witness_view as rwv
from hmbc_protocol import witness_main

from testtools.bootstrap_fixture import require_test_only

READ_FIELDS = ("authEpoch", "policyVersion", "witnessSetVersion")
_SPEC = re.compile(r"(authEpoch|policyVersion|witnessSetVersion|headLag):([1-9][0-9]?)")
_DEC = re.compile(r"0|[1-9][0-9]*")
MAX_N = 50
SYNTAX = "authEpoch:N | policyVersion:N | witnessSetVersion:N | headLag:N with N in 1..50"


def parse_spec(text):
    """`FIELD:N` exactly (N a canonical decimal 1..50); anything else is a ValueError. Returns the text unchanged."""
    m = _SPEC.fullmatch(text) if isinstance(text, str) else None
    if m is None or not 1 <= int(m.group(2)) <= MAX_N:
        raise ValueError("malformed view spec")
    return text


class DivergentView:
    def __init__(self, inner, spec):
        self._inner = inner
        self.field, n = parse_spec(spec).split(":")
        self.n = int(n)

    def __getattr__(self, name):                                               # everything not overridden below is the real view's, unchanged
        return getattr(self._inner, name)

    def reads_at(self, number):
        out = dict(self._inner.reads_at(number))
        if self.field in READ_FIELDS and isinstance(out.get(self.field), str) and _DEC.fullmatch(out[self.field]):
            out[self.field] = str(int(out[self.field]) + self.n)
        return out

    def _lagged_head(self):
        head = int(self._inner.observe("pbc")["blockNumber"])
        return max(head - self.n, 0)

    def observe(self, chain):
        real = self._inner.observe(chain)
        if self.field != "headLag" or chain != "pbc":
            return real
        n = self._lagged_head()
        block = self._inner.pbc_block(n)
        return {"chainId": real["chainId"], "blockNumber": str(n), "blockHash": block["hash"], "timestamp": block["timestamp"]}

    def pbc_block(self, number):
        if self.field == "headLag" and number > self._lagged_head():
            return None
        return self._inner.pbc_block(number)


def install(spec):
    """Make every `RpcWitnessView` this process builds from a manifest a `DivergentView` of `spec` (call once, before the witness starts)."""
    parse_spec(spec)
    original = rwv.RpcWitnessView.from_manifest.__func__

    def from_manifest(cls, *args, **kwargs):
        return DivergentView(original(cls, *args, **kwargs), spec)
    rwv.RpcWitnessView.from_manifest = classmethod(from_manifest)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    ap.add_argument("--view")
    ap.add_argument("--deployment")
    args, rest = ap.parse_known_args(argv)
    try:
        parse_spec(args.view)
    except ValueError:
        raise SystemExit(f"refusing: --view must be {SYNTAX}") from None
    if args.deployment is None:
        raise SystemExit("refusing: --deployment is required")
    try:
        with open(args.deployment, "rb") as f:
            deployment = adapter.strict_loads(f.read().decode("utf-8"))
        require_test_only(deployment)
    except (OSError, ValueError, adapter.AdapterError) as e:
        raise SystemExit(f"refusing: {type(e).__name__}: {e}") from None
    install(args.view)
    return witness_main.main(["--deployment", args.deployment, *rest])


if __name__ == "__main__":
    sys.exit(main())
