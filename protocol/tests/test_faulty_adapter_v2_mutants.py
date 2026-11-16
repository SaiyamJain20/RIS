"""The F-plan source mutants M1..M7 as WITNESS VARIANTS of the TEST-ONLY alternate adapter entry (agent 2, F phase; gap G3). Written BEFORE `testtools.faulty_adapter_v2` gained them. PAPER-DERIVED
RECONSTRUCTION; deliberate mutants, not observed vulnerabilities.

    python -m testtools.faulty_adapter_v2 <the adapter flags> --witness-variant I=mutant:ID --mutant-tree ID=/absolute/built/tree [...]

`I=mutant:ID` (ID one of the WITNESS-role mutants M1 M2 M3 M4 M6 M7) makes witness I start through `testtools.mutant_run` from the built tree of that mutant (`testtools.mutant_tree`), with the production witness's own
arguments after `--`; every other witness keeps the production command byte for byte. `--mutant-tree ID=DIR` (repeatable, once per id, an absolute directory) names the tree; each variant needs its tree and each tree
needs a variant, and every tree is verified (an untampered build of that very mutant) BEFORE anything is created or spawned. M5 (an ADAPTER-role mutant) is not a witness variant: it runs the whole adapter from its
tree (`testtools.mutant_run --module testtools.faulty_adapter_v2`), see the live tests. A refusal is the entry's one closed MALFORMED line, exit 2, nothing created, nothing spawned, no path echoed."""
import json
import os
import sys

import pytest

from test_faulty_adapter_v2 import ABI_DIR, F2, args_for, base_flags, default_command, mods, one_refusal, restoring, run

IDS = ["M1", "M2", "M3", "M4", "M6", "M7"]


def mt():
    mods()
    from testtools import mutant_tree
    return mutant_tree


def tree_of(tmp_path, mid, name=None):
    dest = str(tmp_path / (name or "tree-" + mid))
    mt().build(mid, dest)
    return dest


# ---- the variant syntax ----------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("mid", IDS)
def test_a_mutant_variant_parses_to_exactly_its_parts(mid):
    fa, _, _ = mods()
    v = fa.parse_variant("3=mutant:" + mid)
    assert (v.index, v.name, v.mutant) == (3, "mutant", mid) and (v.point, v.delay_ms, v.only_kind, v.when) == (None, None, None, None)


@pytest.mark.parametrize("text", ["3=mutant:M5", "3=mutant:M8", "3=mutant:M0", "3=mutant:", "3=mutant:m1", "3=mutant:M1:x", "3=mutant :M1", "3=Mutant:M1", "4=mutant:M1", "3=mutant:M10", "3=mutant:M١", "mutant:M1",
                                  "3=mutant"])
def test_every_malformed_or_non_witness_mutant_variant_is_refused(text):
    fa, _, _ = mods()
    with pytest.raises(ValueError):
        fa.parse_variant(text)


def test_the_existing_variants_still_parse_with_the_new_field_defaulting_to_none():
    fa, _, _ = mods()
    assert fa.parse_variant("1=crash:after_commit").mutant is None and fa.parse_variant("1=delay:5").mutant is None


# ---- the tree flag ---------------------------------------------------------------------------------------------------------------------------------------

def test_split_arguments_collects_the_trees_and_keeps_the_adapter_flags(tmp_path):
    fa, _, _ = mods()
    base = base_flags(tmp_path)
    parsed = fa.split_arguments(["--witness-variant", "3=mutant:M1", "--mutant-tree", "M1=/abs/t1", "--witness-variant", "2=mutant:M2", "--mutant-tree", "M2=/abs/t2"] + base)
    assert parsed.base == base and dict(parsed.trees) == {"M1": "/abs/t1", "M2": "/abs/t2"}
    assert [(v.index, v.mutant) for v in parsed.variants] == [(3, "M1"), (2, "M2")]
    assert fa.split_arguments(base).trees == [] or dict(fa.split_arguments(base).trees) == {}


@pytest.mark.parametrize("flag", ["M1", "M1=", "=/abs", "M5=/abs/t", "M8=/abs/t", "m1=/abs/t", "M1=relative/t", "M1=/abs/t=x", ""])
def test_a_malformed_tree_flag_is_refused(flag, tmp_path):
    fa, _, _ = mods()
    with pytest.raises(ValueError):
        fa.split_arguments(["--witness-variant", "3=mutant:M1", "--mutant-tree", flag] + base_flags(tmp_path))


def test_a_repeated_tree_id_is_refused(tmp_path):
    fa, _, _ = mods()
    with pytest.raises(ValueError):
        fa.split_arguments(["--witness-variant", "3=mutant:M1", "--mutant-tree", "M1=/abs/a", "--mutant-tree", "M1=/abs/b"] + base_flags(tmp_path))


# ---- the command seam ------------------------------------------------------------------------------------------------------------------------------------

def test_command_for_starts_a_mutant_witness_through_the_launcher_and_keeps_every_other_command():
    fa, _, wpt = mods()
    variants = {1: fa.parse_variant("1=mutant:M2"), 2: fa.parse_variant("2=crash:after_commit"), 3: fa.parse_variant("3=mutant:M6")}
    cf = fa.command_for_variants(variants, {"M2": "/abs/t2", "M6": "/abs/t6"})
    d = [default_command(wpt, i, allow="/d/allow.json") for i in range(4)]
    assert cf(0, d[0]) == d[0]
    assert cf(1, d[1]) == ["/py", "-B", "-m", "testtools.mutant_run", "--tree", "/abs/t2", "--mutant", "M2", "--module", "hmbc_protocol.witness_main", "--", *d[1][4:]]
    assert cf(2, d[2]) == ["/py", "-B", "-m", "testtools.faulty_witness", "--crash-at", "after_commit", *d[2][4:]]
    assert cf(3, d[3]) == ["/py", "-B", "-m", "testtools.mutant_run", "--tree", "/abs/t6", "--mutant", "M6", "--module", "hmbc_protocol.witness_main", "--", *d[3][4:]]
    assert cf(1, d[1])[-2:] == ["--allow-governance", "/d/allow.json"]                  # the production arguments, the approval list included, are carried over verbatim


def test_command_for_without_a_tree_for_a_mutant_variant_is_a_value_error():
    fa, _, wpt = mods()
    cf = fa.command_for_variants({1: fa.parse_variant("1=mutant:M1")}, {})
    with pytest.raises(ValueError):
        cf(1, default_command(wpt, 1))


def test_installed_mutant_variants_reach_the_real_supervisors_effective_commands(tmp_path, monkeypatch):
    fa, am, wpt = mods()
    restoring(monkeypatch, am)
    fa.install({3: fa.parse_variant("3=mutant:M1")}, None, {"M1": "/abs/t1"})
    ctx, sup = am.build_runtime(args_for(tmp_path), start=lambda **kw: "CONTEXT")
    assert ctx == "CONTEXT" and isinstance(sup, wpt.WitnessSupervisor) and not sup.children
    cmds = sup._effective_commands()
    assert [c[c.index("-m") + 1] for c in cmds] == ["hmbc_protocol.witness_main"] * 3 + ["testtools.mutant_run"]
    assert cmds[3][4:10] == ["--tree", "/abs/t1", "--mutant", "M1", "--module", "hmbc_protocol.witness_main"] and cmds[3][10] == "--"
    for i, c in enumerate(cmds):
        assert c[c.index("--index") + 1] == str(i) and c[c.index("--deployment") + 1] == F2
    assert cmds[0] == sup.commands[0] and cmds[1] == sup.commands[1] and cmds[2] == sup.commands[2]


def test_main_with_a_mutant_variant_verifies_the_tree_patches_then_delegates_with_only_the_adapter_flags(tmp_path, monkeypatch):
    fa, am, _ = mods()
    restoring(monkeypatch, am)
    runtime = am.build_runtime
    seen = {}
    monkeypatch.setattr(am, "main", lambda argv=None, stdin=None, stdout=None, stderr=None: seen.update(argv=argv, patched=am.build_runtime is not runtime) or 0)
    tree = tree_of(tmp_path, "M2")
    base = base_flags(tmp_path)
    assert fa.main(["--witness-variant", "3=mutant:M2", "--mutant-tree", "M2=" + tree] + base) == 0
    assert seen["argv"] == base and seen["patched"] is True


# ---- refusals as real processes: one closed line, nothing created, nothing spawned -----------------------------------------------------------------------------------

def refusal_cases(tmp_path):
    good = tree_of(tmp_path, "M1")
    other = tree_of(tmp_path, "M2")
    tampered = tree_of(tmp_path, "M3")
    open(os.path.join(tampered, "hmbc_protocol", "witness_state.py"), "a").write("\n# tampered\n")
    return {
        "variant-without-tree": ["--witness-variant", "3=mutant:M1"],
        "tree-without-variant": ["--mutant-tree", "M1=" + good],
        "tree-of-another-mutant": ["--witness-variant", "3=mutant:M1", "--mutant-tree", "M1=" + other],
        "tampered-tree": ["--witness-variant", "3=mutant:M3", "--mutant-tree", "M3=" + tampered],
        "missing-tree-directory": ["--witness-variant", "3=mutant:M1", "--mutant-tree", "M1=" + str(tmp_path / "nope")],
        "relative-tree": ["--witness-variant", "3=mutant:M1", "--mutant-tree", "M1=relative/tree"],
        "adapter-role-mutant": ["--witness-variant", "3=mutant:M5", "--mutant-tree", "M5=" + good],
    }


@pytest.mark.parametrize("name", ["variant-without-tree", "tree-without-variant", "tree-of-another-mutant", "tampered-tree", "missing-tree-directory", "relative-tree", "adapter-role-mutant"])
def test_a_bad_mutant_request_is_one_closed_refusal_before_anything_is_created_or_spawned(tmp_path, name):
    fa, _, _ = mods()
    cases = refusal_cases(tmp_path)
    p = run(base_flags(tmp_path) + cases[name])
    msg = one_refusal(p, tmp_path)
    assert msg in (fa.MSG_MUTANT, fa.MSG_VARIANT, fa.MSG_FLAGS), msg
    assert str(tmp_path) not in p.stderr


def test_the_documented_syntax_names_the_mutant_variant():
    fa, _, _ = mods()
    assert "mutant:ID" in fa.SYNTAX and "--mutant-tree" in fa.MSG_MUTANT
