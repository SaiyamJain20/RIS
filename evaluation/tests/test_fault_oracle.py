"""Tests for evaluation.oracles.faults (C-F1 agreement/single-signing oracle). Synthetic records only.
Rule source: protocol/f0/SIGNING-RULES.md sections 1, 2, 6 as READ by agent 3 (A3-0121); not a test of agent 2's store."""
from evaluation.oracles import faults as F


def rec(w, t, typ, key, eff, digest, *, exp=None, seq=None, result=None, **obs):
    o = {"timestamp": 100, "sequence": 0, "nonce": 0, "grant_exists": False, "outcome_recorded": False}
    o.update(obs)
    return {"witness": w, "t": t, "type": typ, "key": key, "effect": eff, "digest": digest,
            "expires_at": exp, "seq": seq, "result": result, "obs": o}


def test_same_effect_resigned_is_fine_even_with_another_expiry():
    rs = [rec(0, 1, "AccessDecision", "r1", "E1", "d1", exp=500, seq=4, result="ALLOW"),
          rec(0, 2, "AccessDecision", "r1", "E1", "d2", exp=600, seq=4, result="ALLOW")]
    assert F.single_signing_violations(rs) == []


def test_different_effect_while_earlier_is_live_is_a_violation():
    rs = [rec(0, 1, "StateCheckpoint", "7", "A", "d1", exp=500, seq=7),
          rec(0, 2, "StateCheckpoint", "7", "B", "d2", exp=500, seq=7, timestamp=200, sequence=6)]
    v = F.single_signing_violations(rs)
    assert [(x["witness"], x["key"]) for x in v] == [(0, "7")]


def test_expiry_kills_the_earlier_digest():
    rs = [rec(0, 1, "StateCheckpoint", "7", "A", "d1", exp=150, seq=7),
          rec(0, 2, "StateCheckpoint", "7", "B", "d2", exp=900, seq=7, timestamp=150, sequence=6)]
    assert F.single_signing_violations(rs) == []
    rs[1]["obs"]["timestamp"] = 149
    assert len(F.single_signing_violations(rs)) == 1


def test_overtaken_checkpoint_sequence_kills_a_checkpoint():
    rs = [rec(1, 1, "StateCheckpoint", "7", "A", "d1", exp=900, seq=7),
          rec(1, 2, "StateCheckpoint", "7", "B", "d2", exp=900, seq=7, sequence=7)]
    assert F.single_signing_violations(rs) == []


def test_decision_deny_then_allow_needs_the_sequence_overtaken():
    deny = rec(2, 1, "AccessDecision", "r1", "DENY", "d1", exp=900, seq=4, result="DENY")
    alive = rec(2, 2, "AccessDecision", "r1", "ALLOW", "d2", exp=900, seq=4, result="ALLOW", sequence=4)
    assert len(F.single_signing_violations([deny, alive])) == 1
    overtaken = rec(2, 2, "AccessDecision", "r1", "ALLOW", "d2", exp=900, seq=5, result="ALLOW", sequence=5)
    assert F.single_signing_violations([deny, overtaken]) == []


def test_decision_allow_then_deny_is_legal_only_after_a_grant_exists():
    allow = rec(2, 1, "AccessDecision", "r1", "ALLOW", "d1", exp=900, seq=4, result="ALLOW")
    deny_no_grant = rec(2, 2, "AccessDecision", "r1", "DENY", "d2", exp=900, seq=4, result="DENY", sequence=4)
    assert len(F.single_signing_violations([allow, deny_no_grant])) == 1
    deny_after_grant = rec(2, 2, "AccessDecision", "r1", "DENY", "d2", exp=900, seq=4, result="DENY", sequence=4, grant_exists=True)
    assert F.single_signing_violations([allow, deny_after_grant]) == []
    # a DENY is never killed by a grant (only by sequence or expiry)
    deny = rec(2, 1, "AccessDecision", "r1", "DENY", "d1", exp=900, seq=4, result="DENY")
    allow_with_grant_flag = rec(2, 2, "AccessDecision", "r1", "ALLOW", "d2", exp=900, seq=4, result="ALLOW", sequence=4, grant_exists=True)
    assert len(F.single_signing_violations([deny, allow_with_grant_flag])) == 1


def test_governance_nonce_overtaken_and_receipt_outcome_recorded():
    g = [rec(3, 1, "GovernanceAction", "5", "A", "d1", exp=900, seq=5),
         rec(3, 2, "GovernanceAction", "5", "B", "d2", exp=900, seq=5, nonce=5)]
    assert F.single_signing_violations(g) == []
    g[1]["obs"]["nonce"] = 4
    assert len(F.single_signing_violations(g)) == 1
    r = [rec(0, 1, "GrantReceipt", "r1", "A", "d1"), rec(0, 2, "GrantReceipt", "r1", "B", "d2")]
    assert len(F.single_signing_violations(r)) == 1
    r[1]["obs"]["outcome_recorded"] = True
    assert F.single_signing_violations(r) == []


def test_different_keys_never_conflict():
    rs = [rec(0, 1, "StateCheckpoint", "7", "A", "d1", exp=900, seq=7),
          rec(0, 2, "StateCheckpoint", "8", "B", "d2", exp=900, seq=8)]
    assert F.single_signing_violations(rs) == []


def test_certificate_pair_with_honest_common_signer_following_the_rule_is_a_legal_resign():
    recs = [rec(1, 1, "AccessDecision", "r1", "ALLOW", "d1", exp=900, seq=4, result="ALLOW"),
            rec(1, 2, "AccessDecision", "r1", "DENY", "d2", exp=900, seq=4, result="DENY", sequence=4, grant_exists=True)]
    certs = [{"type": "AccessDecision", "key": "r1", "effect": "ALLOW", "signers": {0, 1, 2}},
             {"type": "AccessDecision", "key": "r1", "effect": "DENY", "signers": {1, 2, 3}}]
    out = F.certificate_conflicts(certs, recs, byzantine=set())
    assert [x["verdict"] for x in out] == ["legal-resign"]


def test_certificate_pair_whose_common_signer_broke_the_rule_names_that_witness():
    recs = [rec(1, 1, "StateCheckpoint", "7", "A", "d1", exp=900, seq=7),
            rec(1, 2, "StateCheckpoint", "7", "B", "d2", exp=900, seq=7, sequence=6)]
    certs = [{"type": "StateCheckpoint", "key": "7", "effect": "A", "signers": {0, 1, 2}},
             {"type": "StateCheckpoint", "key": "7", "effect": "B", "signers": {1, 2, 3}}]
    out = F.certificate_conflicts(certs, recs, byzantine=set())
    assert out[0]["verdict"] == "violation" and out[0]["blame"] == [1]
    # a declared-Byzantine common signer is excluded from blame; with no honest common signer the pair is explained by f
    out2 = F.certificate_conflicts(certs, recs, byzantine={1, 2})
    assert out2[0]["verdict"] == "byzantine-explained"


def test_disjoint_signers_of_conflicting_certificates_break_quorum_overlap():
    certs = [{"type": "StateCheckpoint", "key": "7", "effect": "A", "signers": {0, 1}},
             {"type": "StateCheckpoint", "key": "7", "effect": "B", "signers": {2, 3}}]
    out = F.certificate_conflicts(certs, [], byzantine=set())
    assert out[0]["verdict"] == "no-common-signer"


def test_same_effect_certificates_are_not_a_conflict():
    certs = [{"type": "StateCheckpoint", "key": "7", "effect": "A", "signers": {0, 1, 2}},
             {"type": "StateCheckpoint", "key": "7", "effect": "A", "signers": {1, 2, 3}}]
    assert F.certificate_conflicts(certs, [], byzantine=set()) == []
