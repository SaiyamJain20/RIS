"""Independent review of agent 3's revision-5 boundary proposal (A3-0012), pinned at origin/agent-3 3e0300a.

`hmbc_protocol.wire` boundary validators were written from BOUNDARY.md prose, not from agent 3's schema code.
ScenarioResult (100 cases) is agent 3's/agent 1's to judge and is reported as skipped, never counted as agreed.
"""
import copy
import hashlib
import json
import pathlib

import pytest

from hmbc_protocol import wire

FIX = pathlib.Path(__file__).parent / "fixtures"
CASES_FILE = FIX / "boundary-cases-a3-3e0300a.json"
SCHEMA_FILE = FIX / "hmbc-schema-candidate-a3-3e0300a.json"
CASES = json.loads(CASES_FILE.read_text())["cases"]
NOT_AGENT2 = {"ScenarioResult", "WorkerExpectation"}


def test_pins():
    assert hashlib.sha256(CASES_FILE.read_bytes()).hexdigest() == "fce967f87cce9b453ae23d7450bcb6a199f3c0f6ad5d933b378b8f90e5a42210"
    assert hashlib.sha256(SCHEMA_FILE.read_bytes()).hexdigest() == "df44c418cdb9dba34f30678c2a777c1c52e074cb25de99dd44e3aeb7ac78f027"
    assert len(CASES) == 497


@pytest.mark.parametrize("i", range(len(CASES)), ids=lambda i: f"{i:03d}-{CASES[i]['schema']}-{'ok' if CASES[i]['valid'] else 'bad'}")
def test_verdict_agrees_with_agent3(i):
    c = CASES[i]
    if c["schema"] in NOT_AGENT2:
        pytest.skip("ScenarioResult is not agent-2's scope")
    if c["valid"]:
        wire.validate(c["schema"], c["input"])
    else:
        with pytest.raises(wire.WireError):
            wire.validate(c["schema"], c["input"])


VALID = {c["schema"]: c["input"] for c in CASES if c["valid"]}
TRIED: dict = {}


def rejects(name, value):
    with pytest.raises(wire.WireError):
        wire.validate(name, value)


def test_policy_rules_beyond_the_fixtures():
    pol = VALID["SymbolicPolicy"]
    first = pol["clauses"][0][0]
    wire.validate("SymbolicPolicy", pol)
    rejects("SymbolicPolicy", {"clauses": pol["clauses"] + [[{**first, "issuerMode": "2"}]]})   # first position of a LATER clause
    rejects("SymbolicPolicy", {"clauses": []})
    rejects("SymbolicPolicy", {"clauses": pol["clauses"] + [[]]})
    for bad in ({"kind": "3"}, {"kind": "0"}, {"kind": 1}, {"issuerMode": "3"}, {"issuerMode": 2}):
        rejects("SymbolicPolicy", {"clauses": [[{**first, **bad}]]})


def test_result_rules_beyond_the_fixtures():
    cdr = VALID["CollectDecisionResult"]
    rejects("CollectDecisionResult", {**cdr, "signatures": []})
    rejects("CollectDecisionResult", {**cdr, "signatures": cdr["signatures"] * 2})
    rejects("CollectDecisionResult", {**cdr, "credentialRecords": cdr["credentialRecords"] * 2})
    rejects("CollectDecisionResult", {**cdr, "credentialRecords": [{**r, "kind": "2", "serial": "5"} for r in cdr["credentialRecords"]]})
    fdr = VALID["FinishDecryptionResult"]
    for bad in ("true", 1, None):
        rejects("FinishDecryptionResult", {**fdr, "decryptable": bad})
    rel = VALID["ReleaseResult"]
    rejects("ReleaseResult", {**rel, "keyEpoch": "1"})
    rejects("ReleaseResult", {**rel, "adapterMode": "abe-real"})
    rejects("ReleaseResult", {**rel, "responseEnvelope": {**rel["responseEnvelope"], "kind": "symbolic-partial/v2"}})
    rejects("CollectDecisionInput", {**VALID["CollectDecisionInput"], "witnessSetVersion": "2"})
    rejects("CollectDecisionInput", {**VALID["CollectDecisionInput"], "witnessSetVersion": 1})
    rejects("RotateEpochInput", {"targetEpoch": "-1"})


def test_response_rules_beyond_the_fixtures():
    cdr = VALID["CollectDecisionResult"]
    ok = {"schemaVersion": "v1", "ok": True, "result": cdr, "error": None}
    wire.validate("AdapterResponse", ok)
    wire.validate("CollectDecisionResponse", ok)
    rejects("PrepareRequestResponse", ok)                                  # result type must match the pending operation
    rejects("AdapterResponse", {**ok, "error": {"code": "MALFORMED", "message": "x"}})
    rejects("AdapterResponse", {**ok, "ok": "true"})
    rejects("AdapterResponse", {**ok, "result": {**cdr, "x": 1}})
    rejects("AdapterResponse", {**ok, "result": {}})
    err = {"schemaVersion": "v1", "ok": False, "result": None, "error": {"code": "ADAPTER_UNAVAILABLE", "message": "m"}}
    wire.validate("AdapterResponse", err)
    for bad in ({"code": "NOPE", "message": "m"}, {"code": "MALFORMED", "message": 5}, {"code": "MALFORMED"}):
        rejects("AdapterResponse", {**err, "error": bad})
    rejects("AdapterResponse", {**err, "result": cdr})
    rejects("RotateEpochResponse", ok)                                     # rotate_epoch has no success in E


@pytest.mark.parametrize("name", sorted(n for n in VALID if n in wire.VALIDATORS and n not in NOT_AGENT2))
def test_scalar_noncanonical_forms_rejected_for_every_valid_boundary_case(name):
    """Trailing LF / leading space / upper-case hex / JSON number / leading zero on every string scalar."""
    base = VALID[name]

    def leaves(o, p=()):
        if isinstance(o, dict):
            for k, v in o.items():
                yield from leaves(v, p + (k,))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                yield from leaves(v, p + (i,))
        else:
            yield p, o

    tried = 0
    for path, val in leaves(base):
        if not isinstance(val, str) or "/" in val and not val.startswith("0x") and not val.startswith("keyref"):
            continue
        if name.endswith(("Request",)) and path[:1] == ("deploymentManifest",):
            continue                                                         # deployment is agent 1/3's schema
        variants = [val + "\n", " " + val]
        if val.startswith("0x") and any(ch.isalpha() for ch in val[2:]):
            variants.append("0x" + val[2:].upper())
        if val.isdigit():
            variants += [int(val), val + ".0", ("0" + val) if val != "0" else "00"]
        for bad in variants:
            mutated = copy.deepcopy(base) if path else bad
            if path:
                t = mutated
                for k in path[:-1]:
                    t = t[k]
                t[path[-1]] = bad
            if path and path[-1] in ("kind", "schemaVersion", "adapterMode", "operation", "type", "message", "scenarioId"):
                continue                                                      # free text / enum labels have their own tests
            rejects(name, mutated)
            tried += 1
    TRIED[name] = tried


def test_scalar_mutation_sweep_was_not_vacuous():
    """Runs after the parametrized sweep (file order): every executed schema tried mutations, and the total is large."""
    assert TRIED, "sweep did not run (run the whole file, not -k)"
    assert sum(TRIED.values()) >= 150, TRIED
    assert all(n > 0 for name, n in TRIED.items() if name not in {"UserKeyRef", "SymbolicEnvelope", "RotateEpochInput", "CollectCheckpointInput"}), TRIED


@pytest.mark.parametrize("name", ["CollectCheckpointResult", "AttestGrantResult"])
def test_new_witness_results_carry_exactly_one_canonical_signature(name):
    """Agent 3's pack has no zero/two-signature case for the two revision-5 results: E is q = 1 of 1 (A3-0012 'signatures[1]')."""
    base = VALID[name]
    wire.validate(name, base)
    for bad in ([], base["signatures"] * 2, ["0x" + "00" * 65], [base["signatures"][0] + "\n"], [base["signatures"][0].upper().replace("0X", "0x")], [1], None, "sig"):
        with pytest.raises(wire.WireError):
            wire.validate(name, {**base, "signatures": bad})
    for field in ("checkpoint", "receipt"):
        if field in base:
            with pytest.raises(wire.WireError):
                wire.validate(name, {**base, field: {**base[field], "extra": "1"}})
