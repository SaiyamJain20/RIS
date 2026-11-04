"""Production D50 binding module (agent 2, F task 2 slice 2). Written BEFORE hmbc_protocol/binding.py existed.

`binding.py` is the PRODUCTION port of the pinned specification reference `protocol/f0/vectors/d50_reference.py` (D50 revision 5, 8ed6f1a4..). These expectations make the two equivalent: the
pinned vector (three binding documents, the masked-build vector, the object-list vector, 14 manifest-profile cases) and a differential over the corruption corpus (every single-key deletion, key
addition and leaf corruption of the E, F and mutant documents plus the structural cases): same verdict on every case, and the same binding hash wherever both accept. The reference stays the
specification; if they ever differ, the pin wins and the production code is wrong.
"""
import copy
import hashlib
import importlib.util
import json
import os

import pytest

from hmbc_protocol import binding as bd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
V = os.path.join(ROOT, "protocol", "f0", "vectors")
spec = importlib.util.spec_from_file_location("d50_reference", os.path.join(V, "d50_reference.py"))
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)
VEC = json.load(open(os.path.join(V, "d50_binding_vector.json")))


def verdict(mod, doc):
    try:
        return ("ok", mod.binding_v2(doc))
    except ValueError:
        return ("refused", None)
    except Exception as e:  # noqa: BLE001 - anything but a documented refusal is a defect
        return ("CRASH", type(e).__name__)


def test_the_pinned_documents_hash_and_canonicalise_exactly_like_the_vector():
    for name, entry in VEC["documents"].items():
        assert bd.canonical_json(entry["document"]) == entry["canonicalJson"], name
        assert bd.binding_v2(entry["document"]) == entry["bindingV2"], name
    assert bd.binding_v2(VEC["documents"]["repaired-e"]["document"]).startswith("242f7ca6977e22c9")
    assert bd.binding_v2(VEC["documents"]["repaired-f"]["document"]).startswith("798f7d722b2c3a5d")
    assert bd.PREFIX == b"hmbc-deployment-binding/v2\n"


def test_the_masked_build_and_object_list_vectors():
    m = VEC["maskedBuild"]
    assert bd.masked_runtime_sha256(m["liveRuntimeHex"], m["ranges"], m["runtimeBytes"]) == m["maskedSha256"]
    r = VEC["immutableRefs"]
    assert bd.immutable_refs_canonical_json(r["objectList"], r["runtimeBytes"]) == r["canonicalJson"]
    assert bd.immutable_refs_sha256(r["objectList"], r["runtimeBytes"]) == r["immutableRefsSha256"]
    assert bd.immutable_refs_sha256([], "128") == hashlib.sha256(b"[]").hexdigest()


def test_the_manifest_profile_cases_of_the_vector():
    assert set(bd.PROFILE_TABLE) == set(VEC["profileTable"]) and len(VEC["manifestProfileCases"]) == 14
    for case in VEC["manifestProfileCases"]:
        args = tuple(case["input"])
        if "expectedProfile" in case:
            assert bd.profile_from_manifest(*args) == case["expectedProfile"]
        else:
            with pytest.raises(bd.OpenRefusal) as e:
                bd.profile_from_manifest(*args)
            assert e.value.reason == case["expectedRefusal"]


def _paths(x, p=()):
    yield p, x
    if isinstance(x, dict):
        for k, v in x.items():
            yield from _paths(v, p + (k,))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from _paths(v, p + (i,))


def _get(d, p):
    for k in p:
        d = d[k]
    return d


def _corpus():
    docs = {k: v["document"] for k, v in VEC["documents"].items()}
    for name, base in docs.items():
        yield name, "base", base
        for p, v in _paths(base):
            if not p:
                continue
            if isinstance(_get(base, p[:-1]), dict):
                d = copy.deepcopy(base)
                del _get(d, p[:-1])[p[-1]]
                yield name, "delete " + ".".join(map(str, p)), d
            if isinstance(v, dict):
                d = copy.deepcopy(base)
                _get(d, p)["zz"] = "0"
                yield name, "add-key " + ".".join(map(str, p)), d
            if isinstance(v, str):
                for tag, nv in (("empty", ""), ("suffix", v + "A"), ("int", 5), ("null", None), ("upper", v.upper()), ("leading-zero", "0" + v if v.isdigit() else v)):
                    if nv != v:
                        d = copy.deepcopy(base)
                        _get(d, p[:-1])[p[-1]] = nv
                        yield name, f"leaf-{tag} " + ".".join(map(str, p)), d

        def add(tag, fn):
            d = copy.deepcopy(base)
            fn(d)
            return name, tag, d
        yield add("profile.name=mutant", lambda d: d["profile"].__setitem__("name", "mutant-no-nonce"))
        yield add("profile.enum=4", lambda d: d["profile"].__setitem__("enum", "4"))
        yield add("profile disagree", lambda d: d["profile"].__setitem__("enum", "3" if base["profile"]["name"] == "repaired-e" else "2"))
        yield add("iface v1", lambda d: d.__setitem__("interfaceVersion", "v1"))
        yield add("iface v2", lambda d: d.__setitem__("interfaceVersion", "v2"))
        yield add("iface v", lambda d: d.__setitem__("interfaceVersion", "v"))
        for ws in base["witnessSets"]:
            yield add(ws + " duplicate", lambda d, ws=ws: d["witnessSets"][ws]["witnesses"].append(d["witnessSets"][ws]["witnesses"][0]))
            yield add(ws + " threshold 0", lambda d, ws=ws: d["witnessSets"][ws].__setitem__("threshold", "0"))
            yield add(ws + " threshold above", lambda d, ws=ws: d["witnessSets"][ws].__setitem__("threshold", str(len(d["witnessSets"][ws]["witnesses"]) + 1)))
            yield add(ws + " reversed", lambda d, ws=ws: d["witnessSets"][ws]["witnesses"].reverse())
            yield add(ws + " empty", lambda d, ws=ws: d["witnessSets"][ws].__setitem__("witnesses", []))
        for side in ("pbc", "dbc"):
            for cn, row in base["chains"][side]["contracts"].items():
                if "immutableRefsSha256" in row:
                    yield add(f"drop refs on {cn}", lambda d, side=side, cn=cn: d["chains"][side]["contracts"][cn].pop("immutableRefsSha256"))

        def drop_all(d):
            for s in ("pbc", "dbc"):
                for r in d["chains"][s]["contracts"].values():
                    r.pop("immutableRefsSha256", None)
        yield add("drop refs on all", drop_all)


def test_differential_over_the_corruption_corpus():
    n = disagree = crashes = 0
    seen_ok = seen_refused = 0
    first = []
    for name, tag, doc in _corpus():
        a, b = verdict(bd, doc), verdict(ref, doc)
        n += 1
        if a[0] == "CRASH" or b[0] == "CRASH":
            crashes += 1
            first.append((name, tag, a, b))
        elif a != b:
            disagree += 1
            first.append((name, tag, a, b))
        seen_ok += a[0] == "ok"
        seen_refused += a[0] == "refused"
    assert n > 1300 and seen_ok > 10 and seen_refused > 1000        # the corpus really exercises both verdicts
    assert crashes == 0 and disagree == 0, first[:5]


def test_masked_build_and_ranges_agree_with_the_reference_on_valid_and_invalid_inputs():
    code = bytes(range(128))
    live = bytearray(code); live[8:40] = b"\xaa" * 32; live[64:96] = b"\xbb" * 32
    hx = "0x" + live.hex()
    cases = [
        (hx, [["8", "32"], ["64", "32"]], "128"), ("0x" + code.hex(), [], "128"), (hx, [["8", "32"], ["40", "32"]], "128"), (hx, [["96", "32"]], "128"),
        (hx, [["64", "32"], ["8", "32"]], "128"), (hx, [["8", "32"], ["39", "32"]], "128"), (hx, [["8", "31"]], "128"), (hx, [["8", "0"]], "128"), (hx, [["100", "32"]], "128"),
        (hx, [["8", "32"]], "127"), (hx, [["8", "32"]], "129"), (hx, [["8", "32"]], 128), (hx, [[8, 32]], "128"), (hx, [["08", "32"]], "128"), (hx, "x", "128"), (hx, [["8"]], "128"),
        ("0x" + code.hex().upper(), [], "128"), ("0x" + code.hex()[:-1], [], "128"), (code.hex(), [], "128"), (hx, [["8", "32", "1"]], "128"), (hx, [["4294967296", "32"]], "128"),
    ]
    for c in cases:
        def run(mod):
            try:
                return mod.masked_runtime_sha256(*c)
            except ValueError:
                return "refused"
        assert run(bd) == run(ref), c
    objs = [[], [{"start": "8", "length": "32"}], [{"start": "8", "length": "32"}, {"start": "64", "length": "32"}], [{"start": "64", "length": "32"}, {"start": "8", "length": "32"}],
            [{"start": "8", "length": "31"}], [{"start": 100, "length": 32}], [{"start": "100", "length": "32"}], [{"start": 8, "length": 32}], [["8", "32"]], [{"start": "8"}], [{"start": "8", "length": "32", "id": "1"}], "x", [{"length": "32", "start": "8"}]]
    for o in objs:
        def run(mod):
            try:
                return mod.immutable_refs_sha256(o, "128")
            except ValueError:
                return "refused"
        assert run(bd) == run(ref), o


def test_refusals_are_valueerrors_not_other_exceptions():
    for bad in (None, [], "x", 5, {}, {"interfaceVersion": "v2"}):
        with pytest.raises(ValueError):
            bd.binding_v2(bad)
    for args in (("repaired-e", "2", "0", "2", None), (None, "2", "0", "2", {}), ("repaired-e", None, None, None, None)):
        with pytest.raises(bd.OpenRefusal):
            bd.profile_from_manifest(*args)


def test_the_module_imports_nothing_from_the_specification_tree_and_reads_no_clock():
    import ast
    tree = ast.parse(open(bd.__file__).read())
    imported = {n.names[0].name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)} | {(n.module or "").split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert imported <= {"hashlib", "json", "re", "__future__"}                                                  # the standard library only: no clock, no randomness, no network, no chain client
    strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) < 200]
    assert not any("d50_reference" in x or "export_layouts_reference" in x or "vectors" in x for x in strings)   # it does not load the specification tree at run time


def test_profile_from_manifest_agrees_with_the_reference_over_a_full_matrix():
    """Not only the 14 vector cases: names, enums, masks, live enums and every shape of the live-mask report, 50,000 calls, same result or same refusal reason."""
    names = list(ref.PROFILE_TABLE) + ["mutant-no-such", None, 5]
    enums = ["0", "1", "2", "3", "4", "02", 2, None]
    muts = ["0", "1", "8", "32", "64", "511", "512", "-1", 0, None]
    E4, F5 = ("TMSC", "PSC", "KSSC", "ACSC"), ("TMSC", "PSC", "KSSC", "ACSC", "Governance")

    def lives(m):
        mm = m if isinstance(m, str) and m.isdigit() else "0"
        other = "0" if mm != "0" else "1"
        return [{n: mm for n in E4}, {n: mm for n in F5}, {**{n: mm for n in E4}, "KSSC": other}, {n: mm for n in E4[:3]}, {**{n: mm for n in F5}, "Governance": other}, None, {n: int(mm) for n in E4}]

    def run(mod, *a):
        try:
            return ("ok", mod.profile_from_manifest(*a))
        except mod.OpenRefusal as e:
            return ("refused", e.reason)
        except Exception as e:  # noqa: BLE001
            return ("CRASH", type(e).__name__)
    calls = bad = 0
    first = []
    for nm in names:
        for en in enums:
            for mu in muts:
                for le in enums:
                    for lv in lives(mu):
                        a, b = run(bd, nm, en, mu, le, lv), run(ref, nm, en, mu, le, lv)
                        calls += 1
                        if a != b or a[0] == "CRASH":
                            bad += 1
                            first.append((nm, en, mu, le, lv, a, b))
    assert calls > 40000 and bad == 0, first[:3]


def test_the_canonical_form_does_not_depend_on_key_order():
    def shuffle(x):
        if isinstance(x, dict):
            return {k: shuffle(x[k]) for k in sorted(x, reverse=True)}
        if isinstance(x, list):
            return [shuffle(i) for i in x]
        return x
    for name, entry in VEC["documents"].items():
        doc = shuffle(entry["document"])
        assert list(doc) != sorted(doc) and bd.binding_v2(doc) == entry["bindingV2"] and bd.canonical_json(doc) == entry["canonicalJson"]


def test_the_primary_check_refuses_with_its_own_reason_not_a_backstop():
    code = bytes(range(128))
    for pin in ("127", "129"):
        with pytest.raises(ValueError, match="pin says"):
            bd.masked_runtime_sha256("0x" + code.hex(), [], pin)
    with pytest.raises(ValueError, match="past the"):
        bd.immutable_refs_sha256([{"start": "100", "length": "32"}], "128")
    with pytest.raises(ValueError, match="base profile name"):
        bd.binding_v2({**VEC["documents"]["repaired-e"]["document"], "profile": {"name": "mutant-no-nonce", "enum": "2"}})
    with pytest.raises(ValueError, match="length must be 32"):
        bd.immutable_refs_sha256([{"start": "8", "length": "31"}], "128")
