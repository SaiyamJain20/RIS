"""C-F1 fault oracle core: single-signing (pin-death) and certificate agreement, for the paper-derived F reconstruction.

Rule source (READ by agent 3, A3-0121; not a test of agent 2's store): protocol/f0/SIGNING-RULES.md sections 1, 2, 6.
A witness pins (type, key) to one effect. It may sign a DIFFERENT effect under the same key only when every earlier
digest under that key is dead, judged by an observation taken at the later signing. Death predicates:
  expiry (any record with expires_at): obs.timestamp >= expires_at
  StateCheckpoint: obs.sequence >= seq            GovernanceAction: obs.nonce >= seq
  AccessDecision: obs.sequence > seq, or (earlier result ALLOW and obs.grant_exists)
  GrantReceipt: obs.outcome_recorded
Input records are synthetic dicts: witness, t (signing order), type, key, effect, digest, expires_at, seq, result, obs.
This is an oracle over given observations: records that lack the needed observation fields must not be fed to it.
Tested reconstruction logic, not a measurement of any implementation, and not an agreement proof."""


def is_dead(prev, obs):
    exp = prev.get("expires_at")
    if exp is not None and obs["timestamp"] >= exp:
        return True
    t = prev["type"]
    if t == "StateCheckpoint":
        return obs["sequence"] >= prev["seq"]
    if t == "GovernanceAction":
        return obs["nonce"] >= prev["seq"]
    if t == "AccessDecision":
        return obs["sequence"] > prev["seq"] or (prev.get("result") == "ALLOW" and bool(obs["grant_exists"]))
    if t == "GrantReceipt":
        return bool(obs["outcome_recorded"])
    return False


def single_signing_violations(records):
    """Honest-signing rule per witness: returns one dict per breach (witness, key, earlier digest, later digest)."""
    out = []
    by = {}
    for r in sorted(records, key=lambda x: x["t"]):
        k = (r["witness"], r["type"], r["key"])
        for p in by.get(k, []):
            if p["effect"] != r["effect"] and not is_dead(p, r["obs"]):
                out.append({"witness": r["witness"], "type": r["type"], "key": r["key"],
                            "earlier": p["digest"], "later": r["digest"]})
        by.setdefault(k, []).append(r)
    return out


def certificate_conflicts(certs, records, byzantine):
    """For every pair of certificates under one (type, key) with different effects, classify:
    no-common-signer (quorum overlap broken), byzantine-explained (every common signer is declared Byzantine),
    violation (an honest common signer broke the rule; blame lists them), legal-resign (honest common signers followed it)."""
    breached = {(v["witness"], v["type"], v["key"]) for v in single_signing_violations(records)}
    out = []
    for i, a in enumerate(certs):
        for b in certs[i + 1:]:
            if (a["type"], a["key"]) != (b["type"], b["key"]) or a["effect"] == b["effect"]:
                continue
            common = set(a["signers"]) & set(b["signers"])
            base = {"type": a["type"], "key": a["key"], "effects": [a["effect"], b["effect"]]}
            if not common:
                out.append(dict(base, verdict="no-common-signer"))
                continue
            honest = sorted(common - set(byzantine))
            if not honest:
                out.append(dict(base, verdict="byzantine-explained"))
                continue
            blame = [w for w in honest if (w, a["type"], a["key"]) in breached]
            out.append(dict(base, verdict="violation", blame=blame) if blame else dict(base, verdict="legal-resign"))
    return out
