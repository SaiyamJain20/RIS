"""D50 live-read reconstruction at open (agent 2, F task 2, slice 5a). Written BEFORE hmbc_protocol/binding_open.py existed.

`binding_open.reconstruct(manifest, view, role, key_address)` is the startup read schedule S0 and the open-time checks of D50 section 3 (stages 1 to 8 of the SUCCESSOR-WIRE precedence; stage 9, the store
itself, is `witness_state.open_store`): read every value of the binding document B live through an INJECTED chain view, all at ONE pinned anchor block per chain, compare the manifest-asserted values, and
return B, its hash and the anchor, or refuse with the reason of the FIRST failing stage. It reads nothing from a store and never touches one. Standard library only.

What these tests establish, and what they do not:
  * The request count of S0 equals the number D50 section 3 derives (48 for an E deployment, 55 for F), with every read after the anchor pinned to that anchor.
  * B equals a document built independently in the test from the same manifest and fake state (same author: correlated), validates under the closed shape, and is sensitive to each live fact.
  * Every refusal has its reason and its code (the code table is checked against SUCCESSOR-WIRE section 1) and the precedence is checked on ALL pairs of simultaneous faults.
  * Against the real store: a refusal at stages 1 to 8 leaves the state directory byte-identical; stage 9 is the store's own.
  * The CHAIN IS A FAKE. Nothing here is a measured ledger, an Anvil, a Forge build or an RPC; the synthetic runtime bytes make the masked-build check meaningful but they are not compiled contracts.
Explicit choices where D50 does not say (recorded, not discovered): a chain id that differs from the manifest's, or a deploy block the chain does not have, is GENESIS_MISMATCH (the identity of the chain);
an `immutableRefsSha256` that is not the hash of the pinned object list, or a missing one under repaired-f, is BUILD_PIN_INVALID; a manifest that is not even shaped like a deployment raises ValueError
(it is outside the reason table); the F witness set must hold 4 witnesses with threshold 2 or 3 (SUCCESSOR-WIRE section 2) and every set equals the manifest's.
"""
import ast
import copy
import hashlib
import importlib.util
import json
import os
import re
import subprocess

import pytest

from hmbc_protocol import binding as bd
from hmbc_protocol import binding_open as bo
from hmbc_protocol import witness_state as ws
from testtools import state_oracle

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
V = os.path.join(ROOT, "protocol", "f0", "vectors")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def addr(tag):
    return "0x" + ("%02x" % tag) * 20


def bhash(label):
    return "0x" + sha(label.encode())


PBC_E, DBC_E = ("LSC", "TMSC", "RSC", "PSC"), ("ACSC", "KSSC")
N_BYTES = 160
REFS = [{"start": "20", "length": "32"}, {"start": "100", "length": "32"}]
PAIRS = bd.pairs_from_object_list(REFS)
WITNESSES_F = [addr(0xB0 + i) for i in range(4)]
WITNESS_E = [addr(0xB0)]
RELAY = addr(0xC0)
ADDRS = {n: addr(0x10 + i) for i, n in enumerate(("LSC", "TMSC", "RSC", "PSC", "Governance", "ACSC", "KSSC"))}


def synthetic_code(name, flip=None):
    raw = bytearray((hashlib.sha256(name.encode() + bytes([i // 32])).digest()[i % 32]) for i in range(N_BYTES))
    if flip is not None:
        raw[flip] ^= 0xFF
    return "0x" + bytes(raw).hex()


def make_manifest(family):
    f = family == "F"
    names_pbc = PBC_E + (("Governance",) if f else ())
    abi = {}
    for n in names_pbc + DBC_E:
        abi[n] = {"abi": "exports/abi/%s.json" % n, "abiSha256": sha(("abi" + n).encode()), "runtimeBytes": str(N_BYTES), "runtimeSha256": bd.masked_runtime_sha256(synthetic_code(n), PAIRS, str(N_BYTES)),
                  "source": "src/%s.sol" % n, "immutableReferences": copy.deepcopy(REFS), "immutableRefsSha256": bd.immutable_refs_sha256(REFS, str(N_BYTES))}
    return {"schemaVersion": "hmbc-ledger-deployment/v2", "interfaceVersion": "v2", "profile": "repaired-f" if f else "repaired-e", "profileEnum": "3" if f else "2", "mutations": "0",
            "chains": {"pbc": {"chainId": "18545", "rpcUrl": "http://127.0.0.1:1", "deployBlock": "25", "contracts": {n: ADDRS[n] for n in names_pbc}},
                       "dbc": {"chainId": "28545", "rpcUrl": "http://127.0.0.1:2", "deployBlock": "32", "contracts": {n: ADDRS[n] for n in DBC_E}}},
            "fixture": {"relay": {"address": RELAY, "keyLabel": "relay"}, "witnessSet": {"version": "2" if f else "1", "threshold": "3" if f else "1", "witnesses": list(WITNESSES_F if f else WITNESS_E),
                                                                                     "keyLabels": ["witness-%d" % (i + 1) for i in range(4 if f else 1)]}},
            "abi": abi}


class Chains:
    """An INJECTED fake chain pair that answers from the manifest (an honest deployment), counts every request, and can be corrupted fault by fault."""

    def __init__(self, manifest):
        self.m = manifest
        self.f = manifest["profile"] == "repaired-f"
        self.requests = []
        self.unreachable = None            # a predicate over the request key, or None
        self.head = {"pbc": 300, "dbc": 400}
        self.genesis = {"pbc": bhash("genesis:pbc"), "dbc": bhash("genesis:dbc")}
        self.chain = {"pbc": manifest["chains"]["pbc"]["chainId"], "dbc": manifest["chains"]["dbc"]["chainId"]}
        self.missing_block = set()
        self.code_override, self.value_override = {}, {}
        e = int(manifest["profileEnum"])
        self.names = {a: n for side in ("pbc", "dbc") for n, a in manifest["chains"][side]["contracts"].items()}
        ws_ = manifest["fixture"]["witnessSet"]
        ex = {"profile": str(e), "mutations": manifest["mutations"], "configured": True, "witnesses": list(ws_["witnesses"]), "threshold": ws_["threshold"], "witnessSetVersion": ws_["version"]}
        A = ADDRS
        self.values = {("TMSC", "profile"): ex["profile"], ("PSC", "profile"): ex["profile"], ("KSSC", "profile"): ex["profile"], ("ACSC", "profile"): ex["profile"],
                       ("TMSC", "mutations"): ex["mutations"], ("PSC", "mutations"): ex["mutations"], ("KSSC", "mutations"): ex["mutations"], ("ACSC", "mutations"): ex["mutations"],
                       ("PSC", "witnesses"): ex["witnesses"], ("KSSC", "witnesses"): ex["witnesses"], ("PSC", "threshold"): ex["threshold"], ("KSSC", "threshold"): ex["threshold"],
                       ("PSC", "witnessSetVersion"): ex["witnessSetVersion"], ("KSSC", "witnessSetVersion"): ex["witnessSetVersion"],
                       ("PSC", "ksscForChain"): A["KSSC"], ("KSSC", "acsc"): A["ACSC"], ("ACSC", "kssc"): A["KSSC"], ("ACSC", "pscRelay"): RELAY,
                       ("TMSC", "psc"): A["PSC"], ("TMSC", "rsc"): A["RSC"], ("LSC", "rsc"): A["RSC"], ("LSC", "tmsc"): A["TMSC"], ("LSC", "psc"): A["PSC"],
                       ("PSC", "rsc"): A["RSC"], ("PSC", "tmsc"): A["TMSC"], ("PSC", "lsc"): A["LSC"], ("RSC", "tmsc"): A["TMSC"], ("RSC", "lsc"): A["LSC"]}
        for n in ("LSC", "TMSC", "RSC", "PSC", "ACSC", "KSSC"):
            self.values[(n, "configured")] = True
        if self.f:
            self.values.update({("Governance", "mutations"): ex["mutations"], ("Governance", "witnesses"): ex["witnesses"], ("Governance", "threshold"): ex["threshold"],
                                ("Governance", "witnessSetVersion"): ex["witnessSetVersion"], ("TMSC", "governance"): A["Governance"], ("Governance", "target"): A["TMSC"]})

    def _req(self, key):
        self.requests.append(key)
        if self.unreachable is not None and self.unreachable(key):
            raise bo.LedgerUnreachable(str(key))

    def chain_id(self, chain):
        self._req(("chain_id", chain))
        return self.chain[chain]

    def latest(self, chain):
        self._req(("latest", chain))
        return {"number": str(self.head[chain]), "hash": bhash("%s:%d" % (chain, self.head[chain]))}

    def block(self, chain, number):
        self._req(("block", chain, int(number)))
        n = int(number)
        if (chain, n) in self.missing_block or (n > self.head[chain] and not getattr(self, "lenient_blocks", False)):
            return None
        return {"number": str(n), "hash": self.genesis[chain] if n == 0 else bhash("%s:%d" % (chain, n))}

    def code(self, chain, address, at):
        self._req(("code", chain, address, int(at)))
        name = self.names[address]
        return self.code_override.get(name, synthetic_code(name))

    def call(self, chain, address, fn, args, at):
        self._req(("call", chain, address, fn, int(at)))
        name = self.names[address]
        if (name, fn) in self.value_override:
            return self.value_override[(name, fn)]
        return self.values[(name, fn)]


def expected_document(m, ch):
    """B built independently of the module (same author: correlated), from the manifest and the fake's honest state."""
    f = m["profile"] == "repaired-f"
    names = {"pbc": PBC_E + (("Governance",) if f else ()), "dbc": DBC_E}
    chains = {}
    for side in ("pbc", "dbc"):
        c = m["chains"][side]
        contracts = {}
        for n in names[side]:
            a = m["abi"][n]
            contracts[n] = {"address": c["contracts"][n], "codeSha256": sha(bytes.fromhex(synthetic_code(n)[2:])), "abiSha256": a["abiSha256"], "runtimeSha256": a["runtimeSha256"],
                            "runtimeBytes": a["runtimeBytes"], "immutableRefsSha256": a["immutableRefsSha256"]}
        chains[side] = {"chainId": c["chainId"], "genesisHash": ch.genesis[side], "deployBlock": {"number": c["deployBlock"], "hash": bhash("%s:%s" % (side, c["deployBlock"]))}, "contracts": contracts}
    e = m["profileEnum"]
    im = {n: {"profile": e, "mutations": m["mutations"]} for n in ("TMSC", "PSC", "KSSC", "ACSC")}
    w = m["fixture"]["witnessSet"]
    wset = {"version": w["version"], "threshold": w["threshold"], "witnesses": list(w["witnesses"])}
    wsets = {"psc": dict(wset), "kssc": dict(wset)}
    A = ADDRS
    wiring = {"ksscForChain": A["KSSC"], "acsc": A["ACSC"], "kssc": A["KSSC"], "pscRelay": RELAY, "tmsc": {"psc": A["PSC"], "rsc": A["RSC"]}, "lsc": {"rsc": A["RSC"], "tmsc": A["TMSC"], "psc": A["PSC"]}}
    if f:
        im["Governance"] = {"mutations": m["mutations"]}
        wsets["governance"] = dict(wset)
        wiring["governance"] = {"tmsc": A["Governance"], "target": A["TMSC"]}
    return {"interfaceVersion": m["interfaceVersion"], "profile": {"name": "repaired-f" if f else "repaired-e", "enum": e}, "chains": chains, "immutables": im, "witnessSets": wsets, "wiring": wiring}


def refusal(fn):
    try:
        fn()
    except bd.OpenRefusal as e:
        return e
    return None


@pytest.fixture(params=["E", "F"])
def fam(request):
    m = make_manifest(request.param)
    return request.param, m, Chains(m)


def reconstruct(m, ch, role="witness", key=WITNESSES_F[0]):
    return bo.reconstruct(m, ch, role=role, key_address=key if role == "witness" else None)


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the honest deployment
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_an_honest_deployment_yields_the_document_built_independently_and_its_hash(fam):
    family, m, ch = fam
    key = m["fixture"]["witnessSet"]["witnesses"][0]
    r = reconstruct(m, ch, key=key)
    want = expected_document(m, ch)
    assert r["document"] == want
    assert bd.validate(r["document"]) is (family == "F")
    assert r["binding_v2"] == bd.binding_v2(want)
    assert r["anchor"] == {"pbc": {"number": "300", "hash": bhash("pbc:300")}, "dbc": {"number": "400", "hash": bhash("dbc:400")}}


def test_the_startup_schedule_makes_exactly_the_requests_d50_derives_and_pins_every_read_to_one_anchor(fam):
    family, m, ch = fam
    reconstruct(m, ch, key=m["fixture"]["witnessSet"]["witnesses"][0])
    assert len(ch.requests) == (55 if family == "F" else 48)
    kinds = {}
    for r in ch.requests:
        kinds[r[0]] = kinds.get(r[0], 0) + 1
    n_contracts = 7 if family == "F" else 6
    assert kinds["chain_id"] == 2 and kinds["latest"] == 2 and kinds["block"] == 4 and kinds["code"] == n_contracts
    assert kinds["call"] == (55 if family == "F" else 48) - 8 - n_contracts
    for r in ch.requests:
        if r[0] == "code":
            assert r[3] == ch.head[r[1]]                                                         # one pinned block per chain
        if r[0] == "call":
            assert r[4] == ch.head[r[1]]
    blocks = sorted(r[1:] for r in ch.requests if r[0] == "block")
    assert blocks == [("dbc", 0), ("dbc", 32), ("pbc", 0), ("pbc", 25)]                          # genesis and deploy block of each chain


def test_the_worker_role_has_no_key_check_and_the_same_binding(fam):
    family, m, ch = fam
    w = reconstruct(m, ch, role="worker")
    k = reconstruct(m, Chains(m), key=m["fixture"]["witnessSet"]["witnesses"][0])
    assert w["binding_v2"] == k["binding_v2"] and w["document"] == k["document"]               # one binding per deployment, whoever opens it


def test_the_binding_is_sensitive_to_each_live_fact(fam):
    family, m, ch = fam
    base = reconstruct(m, ch, role="worker")["binding_v2"]
    for mut in (lambda c: c.genesis.update(pbc=bhash("other-genesis")), lambda c: c.genesis.update(dbc=bhash("other-genesis")),
                lambda c: c.code_override.update(TMSC=synthetic_code("TMSC", flip=0)), lambda c: c.code_override.update(KSSC=synthetic_code("KSSC", flip=1))):
        c2 = Chains(m)
        mut(c2)
        got = refusal(lambda: reconstruct(m, c2, role="worker"))
        if got is None:                                                                          # a change of genesis or of an immutable slot's content is not a refusal: it is a different binding
            assert reconstruct(m, c2, role="worker")["binding_v2"] != base
        else:
            assert got.reason in ("BUILD_MISMATCH", "CODE_MISMATCH")                              # a byte outside every slot is caught by the masked check
    m2 = copy.deepcopy(m)
    m2["abi"]["PSC"]["abiSha256"] = sha(b"another abi")
    assert reconstruct(m2, Chains(m2), role="worker")["binding_v2"] != base


def test_a_changed_immutable_slot_changes_the_binding_but_passes_the_masked_check(fam):
    family, m, ch = fam
    base = reconstruct(m, ch, role="worker")
    c2 = Chains(m)
    c2.code_override["PSC"] = synthetic_code("PSC", flip=25)                                     # inside the first pinned slot [20, 52)
    r = reconstruct(m, c2, role="worker")
    assert r["binding_v2"] != base["binding_v2"] and r["document"]["chains"]["pbc"]["contracts"]["PSC"]["codeSha256"] != base["document"]["chains"]["pbc"]["contracts"]["PSC"]["codeSha256"]


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the refusals, one per reason
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def fault_unreachable(m, c):
    c.unreachable = lambda k: k[0] == "call" and k[3] == "configured"


def fault_profile(m, c):
    c.value_override[("KSSC", "profile")] = "0"


def fault_pin(m, c):
    m["abi"]["TMSC"]["immutableReferences"] = [{"start": "20", "length": "32"}, {"start": "40", "length": "32"}]      # overlapping ranges


def fault_unsealed(m, c):
    c.value_override[("RSC", "configured")] = False


def fault_wiring(m, c):
    c.value_override[("LSC", "psc")] = addr(0x99)


def fault_genesis(m, c):
    c.missing_block.add(("dbc", 32))                                                              # the DBC does not have the deploy block: a restarted chain


def fault_code(m, c):
    c.code_override["LSC"] = "0x"


def fault_mutations(m, c):
    c.value_override[("PSC", "mutations")] = "4"


def fault_build(m, c):
    c.code_override["ACSC"] = synthetic_code("ACSC", flip=70)                                     # a byte outside every immutable slot


def fault_set(m, c):
    c.value_override[("KSSC", "threshold")] = "2" if m["profile"] == "repaired-f" else "1"
    if m["profile"] == "repaired-e":
        c.value_override[("KSSC", "witnessSetVersion")] = "9"


def fault_unknown(m, c):
    m["_key"] = addr(0x77)


FAULTS = [("LEDGER_UNREACHABLE", fault_unreachable), ("PROFILE_MISMATCH", fault_profile), ("BUILD_PIN_INVALID", fault_pin), ("UNSEALED", fault_unsealed),
          ("WIRING_MISMATCH", fault_wiring), ("GENESIS_MISMATCH", fault_genesis), ("CODE_MISMATCH", fault_code), ("MUTATIONS_MISMATCH", fault_mutations),
          ("BUILD_MISMATCH", fault_build), ("WITNESS_SET_MISMATCH", fault_set), ("UNKNOWN_AUTHORITY", fault_unknown)]
ORDER = [r for r, _ in FAULTS]                                                                    # the precedence of SUCCESSOR-WIRE section 1


def run_faults(family, names):
    m = make_manifest(family)
    c = Chains(m)
    m["_key"] = m["fixture"]["witnessSet"]["witnesses"][0]
    for n in names:
        dict(FAULTS)[n](m, c)
    key = m.pop("_key")
    return refusal(lambda: bo.reconstruct(m, c, role="witness", key_address=key))


@pytest.mark.parametrize("family", ["E", "F"])
@pytest.mark.parametrize("reason", ORDER)
def test_each_fault_alone_is_refused_with_its_reason(family, reason):
    r = run_faults(family, [reason])
    assert r is not None and r.reason == reason, (reason, getattr(r, "reason", None))


@pytest.mark.parametrize("family", ["E", "F"])
def test_the_precedence_holds_for_every_pair_of_simultaneous_faults(family):
    n = 0
    for i, a in enumerate(ORDER):
        for b in ORDER[i + 1:]:
            r = run_faults(family, [b, a])
            assert r is not None and r.reason == a, (a, b, getattr(r, "reason", None))              # the earlier stage wins whatever the order they were applied in
            n += 1
    assert n == 55


def test_the_f_only_wiring_governance_and_set_faults_are_refused():
    cases = [("WIRING_MISMATCH", lambda m, c: c.value_override.update({("TMSC", "governance"): addr(0x98)})), ("WIRING_MISMATCH", lambda m, c: c.value_override.update({("Governance", "target"): addr(0x98)})),
             ("WITNESS_SET_MISMATCH", lambda m, c: c.value_override.update({("Governance", "witnesses"): list(reversed(WITNESSES_F))})),
             ("WITNESS_SET_MISMATCH", lambda m, c: c.value_override.update({("Governance", "witnessSetVersion"): "3"})),
             ("MUTATIONS_MISMATCH", lambda m, c: c.value_override.update({("Governance", "mutations"): "1"})), ("CODE_MISMATCH", lambda m, c: c.code_override.update({"Governance": "0x"})),
             ("BUILD_MISMATCH", lambda m, c: c.code_override.update({"Governance": synthetic_code("Governance", flip=70)}))]
    for reason, mutate in cases:
        m = make_manifest("F")
        c = Chains(m)
        mutate(m, c)
        r = refusal(lambda: reconstruct(m, c, key=WITNESSES_F[0]))
        assert r is not None and r.reason == reason, (reason, getattr(r, "reason", None))


def test_the_set_rules_of_f_size_four_threshold_two_or_three_and_equal_everywhere():
    for mut in (lambda m: m["fixture"]["witnessSet"].update(threshold="4"), lambda m: m["fixture"]["witnessSet"].update(threshold="1"), lambda m: m["fixture"]["witnessSet"].update(witnesses=WITNESSES_F[:3])):
        m = make_manifest("F")
        mut(m)
        c = Chains(m)
        r = refusal(lambda: reconstruct(m, c, key=WITNESSES_F[0]))
        assert r is not None and r.reason == "WITNESS_SET_MISMATCH"
    m = make_manifest("F")
    m["fixture"]["witnessSet"]["threshold"] = "2"
    c = Chains(m)
    assert reconstruct(m, c, key=WITNESSES_F[0])["document"]["witnessSets"]["psc"]["threshold"] == "2"        # the q2 control configuration is allowed


def test_a_live_set_that_differs_from_the_manifest_in_membership_or_order_is_refused(fam):
    family, m, ch = fam
    for contract in ("PSC", "KSSC"):
        c = Chains(m)
        c.value_override[(contract, "witnesses")] = list(reversed(m["fixture"]["witnessSet"]["witnesses"])) if family == "F" else [addr(0x55)]
        r = refusal(lambda: reconstruct(m, c, key=m["fixture"]["witnessSet"]["witnesses"][0]))
        assert r is not None and r.reason == "WITNESS_SET_MISMATCH"


def test_a_witness_key_must_belong_to_every_set_and_a_worker_needs_none(fam):
    family, m, ch = fam
    r = refusal(lambda: reconstruct(m, ch, key=addr(0x77)))
    assert r is not None and r.reason == "UNKNOWN_AUTHORITY"
    assert reconstruct(m, Chains(m), role="worker")["binding_v2"]


def test_a_witness_without_a_key_address_is_a_caller_bug(fam):
    family, m, ch = fam
    for kw in (dict(role="witness", key_address=None), dict(role="witness", key_address=WITNESSES_F[0].upper()), dict(role="oracle", key_address=None)):
        with pytest.raises(ValueError) as e:
            bo.reconstruct(m, ch, **kw)
        assert not isinstance(e.value, bd.OpenRefusal), kw                                       # OpenRefusal is itself a ValueError: a caller bug must not look like a refusal


WIRING_OVERRIDES = [("PSC", "ksscForChain"), ("KSSC", "acsc"), ("ACSC", "kssc"), ("ACSC", "pscRelay"), ("TMSC", "psc"), ("TMSC", "rsc"), ("LSC", "rsc"), ("LSC", "tmsc"), ("LSC", "psc"),
                    ("PSC", "rsc"), ("PSC", "tmsc"), ("PSC", "lsc"), ("RSC", "tmsc"), ("RSC", "lsc")]


@pytest.mark.parametrize("contract,fn", WIRING_OVERRIDES + [("TMSC", "governance"), ("Governance", "target")])
def test_every_wiring_view_and_immutable_cross_check_is_compared_with_the_manifest(contract, fn):
    family = "F" if contract == "Governance" or fn == "governance" else "E"
    for fam_ in ([family] if family == "F" else ["E", "F"]):
        m = make_manifest(fam_)
        c = Chains(m)
        c.value_override[(contract, fn)] = addr(0x99)
        r = refusal(lambda: reconstruct(m, c, key=m["fixture"]["witnessSet"]["witnesses"][0]))
        assert r is not None and r.reason == "WIRING_MISMATCH", (contract, fn, fam_)


@pytest.mark.parametrize("contract", ["TMSC", "PSC", "KSSC", "ACSC"])
def test_the_live_profile_of_each_of_the_four_holders_is_compared(fam, contract):
    family, m, ch = fam
    ch.value_override[(contract, "profile")] = "0"
    r = refusal(lambda: reconstruct(m, ch, key=m["fixture"]["witnessSet"]["witnesses"][0]))
    assert r is not None and r.reason == "PROFILE_MISMATCH"


@pytest.mark.parametrize("contract", ["TMSC", "PSC", "KSSC", "ACSC"])
def test_the_live_mutations_of_each_holder_are_compared(fam, contract):
    family, m, ch = fam
    ch.value_override[(contract, "mutations")] = "1"
    r = refusal(lambda: reconstruct(m, ch, key=m["fixture"]["witnessSet"]["witnesses"][0]))
    assert r is not None and r.reason == "MUTATIONS_MISMATCH"


@pytest.mark.parametrize("contract", ["PSC", "KSSC"])
@pytest.mark.parametrize("what", ["witnesses", "threshold", "witnessSetVersion"])
def test_each_member_of_each_live_set_is_compared(fam, contract, what):
    family, m, ch = fam
    w = m["fixture"]["witnessSet"]
    ch.value_override[(contract, what)] = {"witnesses": list(reversed(w["witnesses"])) if len(w["witnesses"]) > 1 else [addr(0x55)], "threshold": "2" if w["threshold"] != "2" else "3",
                                           "witnessSetVersion": "9"}[what]
    r = refusal(lambda: reconstruct(m, ch, key=w["witnesses"][0]))
    assert r is not None and r.reason == "WITNESS_SET_MISMATCH"


def test_the_profile_is_judged_before_the_mutations_and_the_mutations_before_the_build(fam):
    family, m, ch = fam
    c = Chains(m)
    c.value_override[("TMSC", "profile")] = "0"
    c.value_override[("TMSC", "mutations")] = "7"
    assert refusal(lambda: reconstruct(m, c, key=m["fixture"]["witnessSet"]["witnesses"][0])).reason == "PROFILE_MISMATCH"


def test_a_mutant_manifest_binds_under_its_base_name_with_its_live_mask():
    m = make_manifest("E")
    m["profile"], m["mutations"] = "mutant-no-nonce", "8"
    c = Chains(m)
    r = reconstruct(m, c, key=WITNESS_E[0])
    assert r["document"]["profile"] == {"name": "repaired-e", "enum": "2"} and r["document"]["immutables"]["TMSC"]["mutations"] == "8"
    m["mutations"] = "16"                                                                      # the manifest says another mask than the live contracts
    assert refusal(lambda: reconstruct(m, c, key=WITNESS_E[0])).reason == "MUTATIONS_MISMATCH"


def test_a_missing_or_inconsistent_object_list_pin_is_a_build_pin_defect():
    for mut in (lambda m: m["abi"]["TMSC"].pop("immutableRefsSha256"), lambda m: m["abi"]["TMSC"].update(immutableRefsSha256=sha(b"x")),
                lambda m: m["abi"]["TMSC"].update(immutableReferences=[{"start": "20", "length": "31"}]), lambda m: m["abi"]["TMSC"].update(immutableReferences=[{"start": "150", "length": "32"}])):
        m = make_manifest("F")
        mut(m)
        r = refusal(lambda: reconstruct(m, Chains(m), key=WITNESSES_F[0]))
        assert r is not None and r.reason == "BUILD_PIN_INVALID"


def test_the_pin_rules_each_have_their_own_reason_text():
    m = make_manifest("E")
    m["abi"]["TMSC"].pop("immutableRefsSha256")                                                    # the list without its hash
    r = refusal(lambda: reconstruct(m, Chains(m), key=WITNESS_E[0]))
    assert r.reason == "BUILD_PIN_INVALID" and "together" in str(r)
    m = make_manifest("E")
    m["abi"]["TMSC"].pop("immutableReferences")                                                    # the hash without its list
    assert "together" in str(refusal(lambda: reconstruct(m, Chains(m), key=WITNESS_E[0])))
    m = make_manifest("E")
    m["abi"]["TMSC"].update(immutableRefsSha256=sha(b"x"))
    assert "not the hash" in str(refusal(lambda: reconstruct(m, Chains(m), key=WITNESS_E[0])))
    m = make_manifest("E")                                                                         # pins on only some E contracts
    m["abi"]["TMSC"].pop("immutableReferences")
    m["abi"]["TMSC"].pop("immutableRefsSha256")
    r = refusal(lambda: reconstruct(m, Chains(m), key=WITNESS_E[0]))
    assert r.reason == "BUILD_PIN_INVALID" and "every contract or on none" in str(r)
    m = make_manifest("F")                                                                         # repaired-f with NO pins at all
    for n in m["abi"]:
        m["abi"][n].pop("immutableReferences")
        m["abi"][n].pop("immutableRefsSha256")
    r = refusal(lambda: reconstruct(m, Chains(m), key=WITNESSES_F[0]))
    assert r.reason == "BUILD_PIN_INVALID" and "repaired-f requires" in str(r)


def test_a_missing_genesis_block_and_a_deploy_block_after_the_anchor_are_each_a_genesis_mismatch(fam):
    family, m, ch = fam
    key = m["fixture"]["witnessSet"]["witnesses"][0]
    ch.missing_block.add(("pbc", 0))
    r = refusal(lambda: reconstruct(m, ch, key=key))
    assert r is not None and r.reason == "GENESIS_MISMATCH" and "genesis" in str(r)
    m2 = copy.deepcopy(m)
    c2 = Chains(m2)
    c2.lenient_blocks = True                                                                       # a view that answers for a block after its own anchor
    m2["chains"]["dbc"]["deployBlock"] = "500"                                                     # anchor 400
    r2 = refusal(lambda: reconstruct(m2, c2, key=key))
    assert r2 is not None and r2.reason == "GENESIS_MISMATCH"
    m3 = copy.deepcopy(m)
    c3 = Chains(m3)
    c3.lenient_blocks = True
    m3["chains"]["dbc"]["deployBlock"] = "400"                                                     # the deploy block IS the anchor: allowed
    assert reconstruct(m3, c3, key=key)["binding_v2"]


def test_an_e_manifest_without_immutable_pins_binds_without_a_build_check_and_says_so():
    m = make_manifest("E")
    for n in m["abi"]:
        m["abi"][n].pop("immutableRefsSha256")
        m["abi"][n].pop("immutableReferences")
    c = Chains(m)
    c.code_override["ACSC"] = synthetic_code("ACSC", flip=70)                                    # a deviating build cannot be seen without the pins
    r = reconstruct(m, c, key=WITNESS_E[0])
    c2 = Chains(m)
    c2.code_override["ACSC"] = "0x" + "ab" * (N_BYTES - 1)                                       # the LENGTH is still checked without pins
    assert refusal(lambda: reconstruct(m, c2, key=WITNESS_E[0])).reason == "BUILD_MISMATCH"
    assert r["buildChecked"] is False and all("immutableRefsSha256" not in row for side in r["document"]["chains"].values() for row in side["contracts"].values())
    assert make_checked(make_manifest("E"))["buildChecked"] is True


def make_checked(m):
    return reconstruct(m, Chains(m), key=m["fixture"]["witnessSet"]["witnesses"][0])


def test_live_code_that_is_not_canonical_hex_or_not_the_pinned_length_is_a_build_mismatch(fam):
    family, m, ch = fam
    m = copy.deepcopy(m)
    m["abi"]["TMSC"]["runtimeBytes"] = "159"                                                      # the pin says another length than the live code has (the ranges still fit)
    c0 = Chains(m)
    r0 = refusal(lambda: reconstruct(m, c0, key=m["fixture"]["witnessSet"]["witnesses"][0]))
    assert r0 is not None and r0.reason == "BUILD_MISMATCH"
    m = make_manifest(family)
    for bad in ("0x" + "ab" * (N_BYTES - 1), "0x" + "ab" * (N_BYTES + 1), "0x" + "AB" * N_BYTES, "ab" * N_BYTES, "0xzz"):
        c = Chains(m)
        c.code_override["PSC"] = bad
        r = refusal(lambda: reconstruct(m, c, key=m["fixture"]["witnessSet"]["witnesses"][0]))
        assert r is not None and r.reason == "BUILD_MISMATCH", bad


def test_a_chain_id_that_differs_from_the_manifests_is_a_genesis_mismatch(fam):
    family, m, ch = fam
    ch.chain["pbc"] = "1"
    r = refusal(lambda: reconstruct(m, ch, key=m["fixture"]["witnessSet"]["witnesses"][0]))
    assert r is not None and r.reason == "GENESIS_MISMATCH"


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# reasons, codes, shape
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_every_reason_maps_to_the_code_of_the_successor_wire_table():
    text = open(os.path.join(ROOT, "protocol", "f0", "SUCCESSOR-WIRE.md"), encoding="utf-8").read()
    table = {}
    for line in text.splitlines():
        m = re.match(r"\|\s*((?:`[A-Z_]+`(?:,\s*)?)+)\s*\|\s*`([A-Z_]+)`\s*\|", line)
        if m:
            for r in re.findall(r"`([A-Z_]+)`", m.group(1)):
                table[r] = m.group(2)
    assert set(ORDER) - {"UNKNOWN_AUTHORITY"} <= set(table)
    for reason in ORDER:
        if reason == "UNKNOWN_AUTHORITY":
            assert bo.OPEN_REASON_CODE[reason] == "UNKNOWN_AUTHORITY"                         # a key outside the sets stays UNKNOWN_AUTHORITY with no reason
        else:
            assert bo.OPEN_REASON_CODE[reason] == table[reason], reason


def test_a_manifest_that_is_not_shaped_like_a_deployment_is_a_value_error_not_a_reason():
    m = make_manifest("F")
    for mut in (lambda d: d.pop("chains"), lambda d: d["chains"]["pbc"].pop("contracts"), lambda d: d.pop("abi"), lambda d: d["abi"].pop("PSC"), lambda d: d["fixture"].pop("witnessSet"),
                lambda d: d.update(profileEnum=3), lambda d: d["chains"]["pbc"].update(chainId=18545)):
        d = copy.deepcopy(m)
        mut(d)
        with pytest.raises(ValueError) as e:
            bo.reconstruct(d, Chains(m), role="worker", key_address=None)
        assert not isinstance(e.value, bd.OpenRefusal)


def test_an_f_manifest_must_name_governance_and_an_e_manifest_must_not():
    m = make_manifest("F")
    m["chains"]["pbc"]["contracts"].pop("Governance")
    with pytest.raises(ValueError):
        bo.reconstruct(m, Chains(make_manifest("F")), role="worker", key_address=None)
    e = make_manifest("E")
    e["chains"]["pbc"]["contracts"]["Governance"] = ADDRS["Governance"]
    with pytest.raises(ValueError):
        bo.reconstruct(e, Chains(make_manifest("E")), role="worker", key_address=None)


def test_the_module_reads_no_clock_no_network_and_no_store():
    src = open(os.path.join(ROOT, "protocol", "hmbc_protocol", "binding_open.py")).read()
    mods = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            mods.add((node.module or "").split(".")[0])
    assert not mods & {"time", "datetime", "random", "socket", "subprocess", "urllib", "http", "sqlite3", "os"}, mods


# --------------------------------------------------------------------------------------------------------------------------------------------------------
# the real manifest shape, and the real store
# --------------------------------------------------------------------------------------------------------------------------------------------------------
def test_the_manifest_reader_accepts_the_shape_of_agent_1s_real_manifests():
    got = 0
    for path in ("ledger/evidence/af1/migration-v2.1/f-base/deployment.json", "ledger/evidence/af1/migration-v2.1/e-successor/deployment-v2.json", "ledger/evidence/af1/migration-v2.1/f-q2/deployment.json"):
        try:
            blob = subprocess.check_output(["git", "-C", ROOT, "show", "85c59f5:" + path], stderr=subprocess.DEVNULL)
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            pytest.skip("agent 1's blob is not reachable from here (a disposable copy has no repository)")
        d = json.loads(blob)
        pins = bo.read_manifest(d)
        assert pins["family"] == ("F" if d["profile"] == "repaired-f" else "E") and set(pins["abi"]) == set(d["abi"])
        got += 1
    assert got == 3


def tree_hash(path):
    h = hashlib.sha256()
    for dp, dn, fn in sorted(os.walk(path)):
        for f in sorted(fn):
            p = os.path.join(dp, f)
            h.update(p.encode() + b"\0" + open(p, "rb").read())
    return h.hexdigest()


def test_a_refusal_at_stages_1_to_8_leaves_the_real_store_directory_byte_identical_and_stage_9_is_the_stores(tmp_path):
    m = make_manifest("F")
    ch = Chains(m)
    d = str(tmp_path / "w0")
    st = bo.open_witness_store(m, ch, d, WITNESSES_F[0], init=True)
    st.close()
    before = tree_hash(d)
    for reason, fault in FAULTS:
        if reason == "UNKNOWN_AUTHORITY":
            continue
        m2, c2 = make_manifest("F"), None
        c2 = Chains(m2)
        fault(m2, c2)
        with pytest.raises(bd.OpenRefusal) as e:
            bo.open_witness_store(m2, c2, d, WITNESSES_F[0])
        assert e.value.reason == reason and tree_hash(d) == before, reason
    reopened = bo.open_witness_store(make_manifest("F"), Chains(make_manifest("F")), d, WITNESSES_F[0])      # a positive control: the honest deployment reopens
    reopened.close()
    logical = state_oracle.logical_snapshot(d)                                                    # stage 9 is the store's own contract: the WAL-aware logical snapshot, not raw bytes
    other = make_manifest("F")
    c3 = Chains(other)
    c3.genesis["pbc"] = bhash("a restarted chain")                                                # passes stages 1 to 8, changes the binding: the STORE refuses (stage 9)
    with pytest.raises(ws.StoreError) as e:
        bo.open_witness_store(other, c3, d, WITNESSES_F[0])
    assert e.value.reason == "BINDING_MISMATCH" and state_oracle.logical_snapshot(d) == logical


def test_the_store_is_created_only_on_request_and_is_owned_by_the_witness_key(tmp_path):
    m = make_manifest("F")
    d = str(tmp_path / "w1")
    with pytest.raises(ws.StoreError) as e:
        bo.open_witness_store(m, Chains(m), d, WITNESSES_F[1])                                    # no silent creation of a replacement store
    assert e.value.reason == "STORE_MISSING"
    st = bo.open_witness_store(m, Chains(m), d, WITNESSES_F[1], init=True)
    assert st.owner == "witness:" + WITNESSES_F[1]
    st.close()
    with pytest.raises(ws.StoreError) as e:
        bo.open_witness_store(m, Chains(m), d, WITNESSES_F[2])                                    # witness 2's key on witness 1's store
    assert e.value.reason == "OWNER_MISMATCH"


def test_the_anchor_is_persisted_in_the_store_at_init(tmp_path):
    m = make_manifest("F")
    d = str(tmp_path / "w2")
    r = reconstruct(m, Chains(m), key=WITNESSES_F[0])
    st = bo.open_witness_store(m, Chains(m), d, WITNESSES_F[0], init=True)
    st.close()
    view = ws.view_for_export(d)
    assert view.anchor == r["anchor"] and view.binding_v2 == r["binding_v2"] and view.document == r["document"]
