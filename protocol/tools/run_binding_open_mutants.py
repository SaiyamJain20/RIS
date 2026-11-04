"""Mutation check of the D50 live-read reconstruction at open (agent 2, F task 2 slice 5a). Standard library only. Same method as the other runners: one text replacement per mutant (it must match exactly once
and change the file), run the UNCHANGED tests/test_binding_open.py in a temporary copy that keeps the repository layout, count a mutant DETECTED only when the tests ran and failed; a crash or
timeout is NOT detection; the unmutated copy runs first as a control. binding.py and witness_state.py are NOT mutated here (their own runners do that).

Usage (repository root):   python3 -B -I protocol/tools/run_binding_open_mutants.py        (needs pytest and the E dependencies: protocol/requirements.txt)
Exit 0 only when every mutant is detected.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROTO = os.path.abspath(os.path.join(HERE, ".."))
SRC = open(os.path.join(PROTO, "hmbc_protocol", "binding_open.py")).read()

M = [
    ("O1 the configured() reads are not made", [('R["configured"][n] = call(n, "configured")', 'R["configured"][n] = True')]),
    ("O2 the view calls are not pinned to the anchor", [("return view.call(s, addr(n), fn, list(args), at[s])", "return view.call(s, addr(n), fn, list(args), at[s] - 1)")]),
    ("O3 the code reads are not pinned to the anchor", [("R[\"code\"][n] = view.code(s, addr(n), at[s])", "R[\"code\"][n] = view.code(s, addr(n), at[s] + 1)")]),
    ("O4 the genesis is read from block 1", [("R[\"genesis\"][side] = view.block(side, 0)", "R[\"genesis\"][side] = view.block(side, 1)")]),
    ("O5 the deploy block is read one block late", [('R["deploy"][side] = view.block(side, int(ch[side]["deployBlock"]))', 'R["deploy"][side] = view.block(side, int(ch[side]["deployBlock"]) + 1)')]),
    ("O6 eth_chainId is requested twice", [('R["chain"][side] = view.chain_id(side)', 'R["chain"][side] = (view.chain_id(side), view.chain_id(side))[0]')]),
    ("O7 an unreachable chain escapes as a raw exception", [("    except LedgerUnreachable as e:\n        _refuse(\"LEDGER_UNREACHABLE\"", "    except KeyError as e:\n        _refuse(\"LEDGER_UNREACHABLE\"")]),
    ("O8 the profile is not compared", [("    profile = _profile_stage(p, R)\n", "    profile = {\"name\": bd.BASE_NAME[int(p[\"enum\"])], \"enum\": p[\"enum\"]}\n")]),
    ("O9 only one holder's live profile is compared", [("    for n in HOLDERS:\n        result = bd.profile_from_manifest(", "    for n in HOLDERS[:1]:\n        result = bd.profile_from_manifest(")]),
    ("O10 the pin pair rule is not checked", [('        if has_refs != has_sha:\n            _refuse("BUILD_PIN_INVALID"', '        if False:\n            _refuse("BUILD_PIN_INVALID"')]),
    ("O11 the pinned hash is not compared with the object list", [('            if good != a["refsSha256"]:', "            if False:")]),
    ("O12 repaired-f does not require the pins everywhere", [('    if p["family"] == "F" and not all(pinned):', "    if False:")]),
    ("O13 E pins on only some contracts are accepted", [("    if any(pinned) and not all(pinned):", "    if False:")]),
    ("O14 an unsealed deployment is accepted", [("        if v is not True:", "        if False:")]),
    ("O15 the governance wiring is not compared", [('    if p["family"] == "F":\n        want += [', '    if False:\n        want += [')]),
    ("O16 the relay is not compared", [('("ACSC.pscRelay", w["pscRelay"], p["relay"])', '("ACSC.pscRelay", w["pscRelay"], w["pscRelay"])')]),
    ("O17 the last immutable cross-check is not compared", [('("RSC.lsc", R["cross"]["RSC"]["lsc"], A["LSC"])', '("RSC.lsc", A["LSC"], A["LSC"])')]),
    ("O18 the first immutable cross-check is not compared", [('("PSC.rsc", R["cross"]["PSC"]["rsc"], A["RSC"])', '("PSC.rsc", A["RSC"], A["RSC"])')]),
    ("O19 the chain id is not compared", [('        if R["chain"][side] != p["chains"][side]["chainId"]:', "        if False:")]),
    ("O20 a missing genesis block is accepted", [("        if g is None or d is None or int(", "        if d is None or int(")]),
    ("O21 a missing deploy block is accepted", [("        if g is None or d is None or int(", "        if g is None or int(")]),
    ("O22 a deploy block after the anchor is accepted", [('d is None or int(p["chains"][side]["deployBlock"]) > int(a["number"]):', "d is None:")]),
    ("O23 empty code is not recognised", [('        if not isinstance(code, str) or code in ("", "0x"):', "        if False:")]),
    ("O24 the live mutations are not compared", [('    bd.profile_from_manifest(p["profile"], p["enum"], p["mutations"], R["profile"]["TMSC"], R["mutations"])', "    pass")]),
    ("O25 the live code length is not checked", [(' or len(code) != 2 + 2 * int(runtime_bytes):', ":")]),
    ("O26 the masked hash is not compared", [('            if masked != a["runtimeSha256"]:', "            if False:")]),
    ("O27 the masked check never runs", [("        if pinned:\n            try:\n                masked", "        if False:\n            try:\n                masked")]),
    ("O28 the masked check masks nothing", [('bd.masked_runtime_sha256(code, bd.pairs_from_object_list(a["refs"]), a["runtimeBytes"])', 'bd.masked_runtime_sha256(code, [], a["runtimeBytes"])')]),
    ("O29 the code hash is over a truncated code", [("digests[n] = hashlib.sha256(raw).hexdigest()", "digests[n] = hashlib.sha256(raw[:-1]).hexdigest()")]),
    ("O30 the F set size and threshold rule is not applied", [('    if p["family"] == "F" and (len(w["witnesses"]) != 4 or w["threshold"] not in ("2", "3")):', "    if False:")]),
    ("O31 the live threshold is not compared", [(' or s["threshold"] != w["threshold"] or s["version"]', " or s[\"version\"]")]),
    ("O32 the live version is not compared", [(' or s["version"] != w["version"]:', ":")]),
    ("O33 the live members are not compared", [('        if s["witnesses"] != w["witnesses"] or s["threshold"]', '        if s["threshold"]')]),
    ("O34 the KSSC set is not read", [('        for n in ("PSC", "KSSC") + (("Governance",) if p["family"] == "F" else ()):\n            R["sets"][n]', '        for n in ("PSC",) + (("Governance",) if p["family"] == "F" else ()):\n            R["sets"][n]')]),
    ("O35 the witness key need not be a member", [('    if role == "witness" and key not in w["witnesses"]:', "    if False:")]),
    ("O36 a witness may open without a key address", [('    if role == "witness" and (not isinstance(key_address, str) or _ADDR.fullmatch(key_address) is None):', "    if False:")]),
    ("O37 any role is accepted", [('    if role not in ("worker", "witness"):', "    if False:")]),
    ("O38 the pin hash is put into B even when there is no pin", [("            if pinned:\n                row[\"immutableRefsSha256\"]", "            if True:\n                row[\"immutableRefsSha256\"]")]),
    ("O39 B names the deploy block's hash as the genesis hash", [('"genesisHash": R["genesis"][side]["hash"]', '"genesisHash": R["deploy"][side]["hash"]')]),
    ("O40 B names the genesis hash as the deploy block's hash", [('"hash": R["deploy"][side]["hash"]}', '"hash": R["genesis"][side]["hash"]}')]),
    ("O41 the anchor carries the genesis hash", [('"hash": R["anchor"][s]["hash"]} for s in ("pbc", "dbc")}', '"hash": R["genesis"][s]["hash"]} for s in ("pbc", "dbc")}')]),
    ("O42 buildChecked is always true", [('"buildChecked": pinned}', '"buildChecked": True}')]),
    ("O43 the store owner is the worker", [('    owner = "witness:" + key_address', '    owner = "worker"')]),
    ("O44 the anchor is not persisted at init", [("owner, anchor=r[\"anchor\"])", "owner, anchor=None)")]),
    ("O45 a missing store is created on open", [("    if init:\n        return ws.init_store", "    if True:\n        return ws.init_store")]),
    ("O46 PROFILE_MISMATCH maps to WRONG_DESTINATION", [('"PROFILE_MISMATCH": "WRONG_PROFILE"', '"PROFILE_MISMATCH": "WRONG_DESTINATION"')]),
    ("O47 every manifest is read as an E manifest", [('    family = "F" if m["profile"] == "repaired-f" else "E"', '    family = "E"')]),
    ("O48 the contract set of a chain is not checked", [("            if not isinstance(contracts, dict) or set(contracts) != set(want[side]):", "            if not isinstance(contracts, dict):")]),
    ("O49 the manifest chain id need not be a decimal string", [('"chainId": _dec(c["chainId"], "chainId")', '"chainId": c["chainId"]')]),
    ("O50 the sealed check runs before the profile check", [("    profile = _profile_stage(p, R)\n    pinned = _pins_stage(p)\n    _sealed_stage(R)\n", "    _sealed_stage(R)\n    profile = _profile_stage(p, R)\n    pinned = _pins_stage(p)\n")]),
    ("O51 the wiring check runs before the sealed check", [("    _sealed_stage(R)\n    _wiring_stage(p, R)\n", "    _wiring_stage(p, R)\n    _sealed_stage(R)\n")]),
    ("O52 the sets are judged before the genesis", [("    _genesis_stage(p, R)\n    digests = _code_stage(p, R, pinned)\n    _sets_stage(p, R, role, key_address)\n", "    _sets_stage(p, R, role, key_address)\n    _genesis_stage(p, R)\n    digests = _code_stage(p, R, pinned)\n")]),
]


def validate_anchors():
    bad = [(name, SRC.count(old)) for name, edits in M for old, _ in edits if SRC.count(old) != 1]
    if bad:
        print("INVALID anchors (nothing was run):", bad)
        return False
    return True


def run_in_copy(text):
    d = tempfile.mkdtemp(prefix="bopen-mutant-")
    try:
        p = os.path.join(d, "protocol")
        for sub in ("hmbc_protocol", "tests", "testtools", os.path.join("f0", "vectors")):
            os.makedirs(os.path.join(p, sub), exist_ok=True)
        tt = os.path.join(PROTO, "testtools")
        for name in os.listdir(tt):
            if name.endswith(".py"):
                shutil.copy(os.path.join(tt, name), os.path.join(p, "testtools", name))
        pkg = os.path.join(PROTO, "hmbc_protocol")
        for name in os.listdir(pkg):
            if name.endswith(".py") and name != "binding_open.py":
                shutil.copy(os.path.join(pkg, name), os.path.join(p, "hmbc_protocol", name))
        for rel in ("pytest.ini", os.path.join("tests", "test_binding_open.py"), os.path.join("f0", "SUCCESSOR-WIRE.md")):
            shutil.copy(os.path.join(PROTO, rel), os.path.join(p, rel))
        with open(os.path.join(p, "hmbc_protocol", "binding_open.py"), "w") as f:
            f.write(text)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            r = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_binding_open.py"], cwd=p, capture_output=True, text=True, timeout=300, env=env)
        except subprocess.TimeoutExpired:
            return "timeout", None
        m = re.search(r"(\d+) failed", r.stdout)
        if r.returncode == 0:
            return "pass", 0
        if r.returncode == 1 and m:
            return "fail", int(m.group(1))
        return "crash", None
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    if not validate_anchors():
        return 2
    status, _ = run_in_copy(SRC)
    if status != "pass":
        print("CONTROL FAILED: the unmutated module does not pass its own tests (%s); nothing reported" % status)
        return 2
    print("control: unmutated module passes all tests")
    detected = 0
    for name, edits in M:
        text = SRC
        for old, new in edits:
            if text.count(old) != 1:
                print("INVALID %s | anchor matches %d times: %r" % (name, text.count(old), old[:70]))
                return 2
            text = text.replace(old, new)
        if text == SRC:
            print("INVALID %s | the mutation changed nothing" % name)
            return 2
        status, n = run_in_copy(text)
        if status == "fail":
            detected += 1
            print("DETECTED %s | failed tests: %d" % (name, n))
        else:
            print("NOT-DETECTED(%s) %s" % (status, name))
    print("detected %d of %d" % (detected, len(M)))
    return 0 if detected == len(M) else 1


if __name__ == "__main__":
    sys.exit(main())
