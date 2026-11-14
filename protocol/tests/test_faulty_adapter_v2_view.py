"""The real-process divergent-view witness (H3; gap G2) as a WITNESS VARIANT of the TEST-ONLY alternate adapter entry. Written BEFORE `testtools.faulty_adapter_v2` gained it.

    python -m testtools.faulty_adapter_v2 <the adapter flags> --witness-variant I=view:SPEC [...]      SPEC: the grammar of `testtools.divergent_witness`

`I=view:SPEC` makes witness I start as `python -B -m testtools.divergent_witness --view SPEC` followed by the production witness's own arguments; every other witness keeps the production command by byte."""
import pytest

from test_faulty_adapter_v2 import base_flags, default_command, mods, one_refusal, restoring, run, args_for, F2


@pytest.mark.parametrize("spec", ["authEpoch:1", "policyVersion:50", "witnessSetVersion:3", "headLag:12"])
def test_a_view_variant_parses_to_exactly_its_parts(spec):
    fa, _, _ = mods()
    v = fa.parse_variant("1=view:" + spec)
    assert (v.index, v.name, v.view) == (1, "view", spec) and (v.point, v.delay_ms, v.only_kind, v.when, v.mutant, v.behavior) == (None,) * 6


@pytest.mark.parametrize("text", ["1=view:", "1=view", "1=view:authEpoch", "1=view:authEpoch:0", "1=view:authEpoch:51", "1=view:keyEpoch:1", "1=view:headLag:x", "1=View:headLag:1", "5=view:headLag:1", "view:headLag:1",
                                  "1=view:headLag:1:2"])
def test_every_malformed_view_variant_is_refused(text):
    fa, _, _ = mods()
    with pytest.raises(ValueError):
        fa.parse_variant(text)


def test_the_existing_variants_still_parse_with_the_new_field_defaulting_to_none():
    fa, _, _ = mods()
    for text in ("1=crash:after_commit", "1=delay:5", "1=mutant:M1", "1=byz:withhold"):
        assert fa.parse_variant(text).view is None


def test_command_for_starts_a_divergent_witness_and_keeps_every_other_command():
    fa, _, wpt = mods()
    variants = {0: fa.parse_variant("0=view:authEpoch:2"), 2: fa.parse_variant("2=byz:withhold"), 3: fa.parse_variant("3=view:headLag:5")}
    cf = fa.command_for_variants(variants)
    d = [default_command(wpt, i, allow="/d/allow.json") for i in range(4)]
    assert cf(1, d[1]) == d[1]
    assert cf(0, d[0]) == ["/py", "-B", "-m", "testtools.divergent_witness", "--view", "authEpoch:2", *d[0][4:]]
    assert cf(3, d[3]) == ["/py", "-B", "-m", "testtools.divergent_witness", "--view", "headLag:5", *d[3][4:]]
    assert cf(2, d[2])[3] == "testtools.byzantine_witness" and cf(0, d[0])[-2:] == ["--allow-governance", "/d/allow.json"]


def test_installed_view_variants_reach_the_real_supervisors_effective_commands(tmp_path, monkeypatch):
    fa, am, _ = mods()
    restoring(monkeypatch, am)
    fa.install({2: fa.parse_variant("2=view:policyVersion:1")}, None)
    ctx, sup = am.build_runtime(args_for(tmp_path), start=lambda **kw: "CONTEXT")
    cmds = sup._effective_commands()
    assert [c[c.index("-m") + 1] for c in cmds] == ["hmbc_protocol.witness_main", "hmbc_protocol.witness_main", "testtools.divergent_witness", "hmbc_protocol.witness_main"]
    assert cmds[2][4:6] == ["--view", "policyVersion:1"] and cmds[0] == sup.commands[0]
    for i, c in enumerate(cmds):
        assert c[c.index("--index") + 1] == str(i) and c[c.index("--deployment") + 1] == F2


@pytest.mark.parametrize("variant", ["3=view:", "3=view:authEpoch:0", "3=view:nonsense:1"])
def test_a_bad_view_request_is_one_closed_refusal_before_anything_is_created_or_spawned(tmp_path, variant):
    fa, _, _ = mods()
    p = run(base_flags(tmp_path) + ["--witness-variant", variant])
    assert one_refusal(p, tmp_path) == fa.MSG_VARIANT


def test_the_documented_syntax_names_the_view_variant():
    fa, _, _ = mods()
    assert "view:SPEC" in fa.SYNTAX
