"""The real-process Byzantine witness (H1; gap G1) as a WITNESS VARIANT of the TEST-ONLY alternate adapter entry (agent 2, F phase). Written BEFORE `testtools.faulty_adapter_v2` gained it. PAPER-DERIVED
RECONSTRUCTION; deliberate adversary, synthetic TEST-ONLY keys.

    python -m testtools.faulty_adapter_v2 <the adapter flags> --witness-variant I=byz:SPEC [...]
    SPEC  withhold | garbage | repeat:N | equivocate | impersonate:J | poison:FIELD     (the grammar of `testtools.byzantine_witness`)

`I=byz:SPEC` makes witness I start as `python -B -m testtools.byzantine_witness --behavior SPEC` followed by the production witness's own arguments; every other witness keeps the production command byte for
byte. It combines with the other variants at OTHER indices (crash, delay, mutant). A malformed SPEC is the entry's one closed MALFORMED refusal before anything is created or spawned."""
import pytest

from test_faulty_adapter_v2 import base_flags, default_command, mods, one_refusal, restoring, run, args_for, F2


@pytest.mark.parametrize("spec", ["withhold", "garbage", "repeat:2", "repeat:8", "equivocate", "impersonate:0", "impersonate:3", "poison:sourceBlockNumber", "poison:expiresAt"])
def test_a_byzantine_variant_parses_to_exactly_its_parts(spec):
    fa, _, _ = mods()
    v = fa.parse_variant("2=byz:" + spec)
    assert (v.index, v.name, v.behavior) == (2, "byz", spec) and (v.point, v.delay_ms, v.only_kind, v.when, v.mutant) == (None, None, None, None, None)


@pytest.mark.parametrize("text", ["2=byz:", "2=byz", "2=byz:teleport", "2=byz:repeat", "2=byz:repeat:1", "2=byz:repeat:9", "2=byz:impersonate:4", "2=byz:poison", "2=byz:poison:nope", "2=byz:Withhold",
                                  "2=Byz:withhold", "2=byz: withhold", "2=byz:withhold:", "2=byz:garbage:x", "4=byz:withhold", "byz:withhold"])
def test_every_malformed_byzantine_variant_is_refused(text):
    fa, _, _ = mods()
    with pytest.raises(ValueError):
        fa.parse_variant(text)


def test_the_existing_variants_still_parse_with_the_new_field_defaulting_to_none():
    fa, _, _ = mods()
    for text in ("1=crash:after_commit", "1=delay:5", "1=mutant:M1"):
        assert fa.parse_variant(text).behavior is None


def test_command_for_starts_a_byzantine_witness_and_keeps_every_other_command():
    fa, _, wpt = mods()
    variants = {0: fa.parse_variant("0=byz:repeat:3"), 2: fa.parse_variant("2=crash:after_commit"), 3: fa.parse_variant("3=byz:poison:authEpoch")}
    cf = fa.command_for_variants(variants)
    d = [default_command(wpt, i, allow="/d/allow.json") for i in range(4)]
    assert cf(1, d[1]) == d[1]
    assert cf(0, d[0]) == ["/py", "-B", "-m", "testtools.byzantine_witness", "--behavior", "repeat:3", *d[0][4:]]
    assert cf(2, d[2]) == ["/py", "-B", "-m", "testtools.faulty_witness", "--crash-at", "after_commit", *d[2][4:]]
    assert cf(3, d[3]) == ["/py", "-B", "-m", "testtools.byzantine_witness", "--behavior", "poison:authEpoch", *d[3][4:]]
    assert cf(0, d[0])[-2:] == ["--allow-governance", "/d/allow.json"]                  # the production arguments, the approval list included, are carried over verbatim


def test_installed_byzantine_variants_reach_the_real_supervisors_effective_commands(tmp_path, monkeypatch):
    fa, am, wpt = mods()
    restoring(monkeypatch, am)
    fa.install({1: fa.parse_variant("1=byz:withhold"), 2: fa.parse_variant("2=byz:impersonate:0")}, None)
    ctx, sup = am.build_runtime(args_for(tmp_path), start=lambda **kw: "CONTEXT")
    cmds = sup._effective_commands()
    assert [c[c.index("-m") + 1] for c in cmds] == ["hmbc_protocol.witness_main", "testtools.byzantine_witness", "testtools.byzantine_witness", "hmbc_protocol.witness_main"]
    assert cmds[1][4:6] == ["--behavior", "withhold"] and cmds[2][4:6] == ["--behavior", "impersonate:0"]
    assert cmds[0] == sup.commands[0] and cmds[3] == sup.commands[3]
    for i, c in enumerate(cmds):
        assert c[c.index("--index") + 1] == str(i) and c[c.index("--deployment") + 1] == F2


def test_main_with_a_byzantine_variant_patches_then_delegates_with_only_the_adapter_flags(tmp_path, monkeypatch):
    fa, am, _ = mods()
    restoring(monkeypatch, am)
    runtime = am.build_runtime
    seen = {}
    monkeypatch.setattr(am, "main", lambda argv=None, stdin=None, stdout=None, stderr=None: seen.update(argv=argv, patched=am.build_runtime is not runtime) or 0)
    base = base_flags(tmp_path)
    assert fa.main(["--witness-variant", "1=byz:garbage"] + base) == 0 and seen["argv"] == base and seen["patched"] is True


@pytest.mark.parametrize("variant", ["3=byz:teleport", "3=byz:", "3=byz:repeat:1", "3=byz:poison:nope"])
def test_a_bad_byzantine_request_is_one_closed_refusal_before_anything_is_created_or_spawned(tmp_path, variant):
    fa, _, _ = mods()
    p = run(base_flags(tmp_path) + ["--witness-variant", variant])
    assert one_refusal(p, tmp_path) == fa.MSG_VARIANT


def test_the_documented_syntax_names_the_byzantine_variant():
    fa, _, _ = mods()
    assert "byz:SPEC" in fa.SYNTAX
