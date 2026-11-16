Message-ID: A1-0121
From: agent-1
To: agent-3
Cc: agent-2, human
RQ: F
Task: C-F1 review of the DecisionQuorum model text (A3-0111) in agent 1's review focus (duplicate signers, quorum threshold). Finding: the f=0 control deadlocks under TLC defaults. Independent state enumeration.
Type: REVIEW
Interface-version: v2 wire family, schema v2.1; nothing changes
Responds-to: A3-0111 (origin/agent-3 af30e65: `evaluation/models/f/DecisionQuorum.tla`, five `.cfg` files, `README.md`)
Source-manifest: model files read with `git show af30e65:<path>`. Ledger rule read at agent-1 d4269d5: `ledger/src/lib/SigLib.sol` `QuorumLib.verify`, which is byte-identical to the reviewed 85c59f5. The enumeration script is given in full below; it was run with `python3 -I` (Python 3.13.5), and its sha256 is 6f4684c1cfc9dbf020ea43a0cb5aad8cf48452b15abc3b015a0026e695b9ac41.

Summary: **one defect in a control config. Every other prediction in the README is confirmed by an independent enumeration. The certificate rule matches the ledger.**

- **Not TLC.** I did not run TLC. I have no jar, and I will not download and run the jar that your session's classifier refused. What follows is a separate explicit-state enumeration that I wrote, mirroring the module's Init, Next and invariants literally.
- **Correlated review.** It comes from the same model family as you, so it is correlated review, not independent.

## 1. Finding: `DecisionQuorum-f0.cfg` deadlocks

**Classification:** tested reconstruction result about the model or config. It is not a protocol or ledger finding.

**Why it deadlocks.** With `Byz = {}` and `Persist = TRUE`:
- Once every witness has signed one value, `HonestSign` is disabled (it needs `signed[w] = {}`) and `ByzSign` is disabled (no Byzantine witness exists).
- The enumeration finds **16 states with no successor**: each of the four witnesses has signed `a` or `b`, so 2^4 = 16.
- TLC checks for deadlock by default. It will therefore stop with "Deadlock reached" and a nonzero exit, so the f=0 positive control would read as an error, not as "holds".

**Why only f0 deadlocks.**
- In `DecisionQuorum.cfg`, `-weak-q2` and `-f2`, a Byzantine witness can always re-sign a value it already holds. That is a self-loop, which counts as a successor.
- In `-no-persist`, honest witnesses can always re-sign.

**Suggested fix (your call).**
- **Option 1 (my recommendation): change the spec.** Add a terminal stuttering disjunct to `Next` (for example `\/ UNCHANGED vars`). All five configs then behave the same, and the README command needs no flag. It adds no new distinct states.
- **Option 2: change the command.** Run f0 with TLC's `-deadlock` option, which disables the deadlock check, and record that flag in the evidence.

## 2. Predictions confirmed by enumeration (distinct reachable states)

| config | ASSUME | reachable states | Agreement-violating states | HonestSingle violations | states with no successor | README prediction |
|---|---|---|---|---|---|---|
| `DecisionQuorum.cfg` (Byz {w1}, Q 3) | true | 108 | 0 | 0 | 0 | holds: **confirmed** |
| `-f0` (Byz {}, Q 3) | true | 81 | 0 | 0 | **16** | holds: **confirmed for the invariants, but TLC reports a deadlock (§1)** |
| `-weak-q2` (Byz {w1}, Q 2) | true | 108 | 18 | 0 | 0 | violated: **confirmed** |
| `-f2` (Byz {w1,w2}, Q 3) | true | 144 | 2 | 0 | 0 | violated: **confirmed** |
| `-no-persist` (Byz {}, Q 3, Persist FALSE) | true | 256 | 25 | 0 | 0 | violated, HonestSingle vacuous: **confirmed** |

These counts give you something to compare against when TLC does run.
- **"Distinct states found"** should equal 108, 81, 108, 144 and 256 for a complete run. With the stuttering fix, f0 stays at 81.
- **Violated configs:** TLC stops at the first violation, so expect a counterexample trace rather than a full count.

## 3. Correspondence with the ledger rule (agent 1's scope)

- **Accepted certificates are certified.** `QuorumLib.verify` (`ledger/src/lib/SigLib.sol:37`) returns `NONE` only if every signature recovers to a member of the fixed witness set, the recovered signers are strictly increasing, and the count reaches `threshold`. Otherwise it returns `BAD_SIGNATURE`, `DUPLICATE_SIGNER`, `MALFORMED` or `INSUFFICIENT_QUORUM`. F uses 3 of 4 (`DecisionVerifier.sol`). So any certificate the ledger accepts has at least Q distinct witness signers, which is exactly the model's `Certified(v)` over the set `Signers(v)`.
- **So Agreement carries over to the ledger.** With f ≤ 1, model Agreement implies that the ledger cannot accept two certificates for conflicting values of the same decision, in the counting dimension.
- **The ledger is stricter than the model:**
  - it rejects a duplicate signature instead of counting it once;
  - it rejects a certificate that contains any non-member signature, even if three valid ones are present.

  Neither weakens the implication.
- **Not covered by the model.** The README says so already; I add the ledger-side items:
  - the digest binding (chain id, KSSC address, action and payload);
  - sequence and epoch replay across instances;
  - the governance nonce and expiry;
  - the witness-set version.

  These are covered by the A-F1 Forge tests (FL-4, FL-6, F-24 and the governance cases), not by this single-slot model. The model checks quorum-overlap combinatorics for one decision slot only.

## 4. Wording nit

The `-f2` row and the module comment say the counterexample is "conditional on that modeled source-view failure". The model has no source view. The f2 violation comes from two Byzantine witnesses each signing both values, which is outside f = 1.

Suggested wording: "conditional on two Byzantine witnesses (f = 2 > 1), outside the fault bound". That keeps PLAN §6's "not a measured break of safe Anvil consensus" intact.

## 5. Script (complete; `python3 -I dq_enum.py`)

```python
"""Independent explicit-state enumeration of agent 3's DecisionQuorum.tla (af30e65), written by agent 1.
Mirrors Init/Next/invariants literally; reports reachable states, invariant violations and states with
no successor (what TLC reports as 'Deadlock reached' unless deadlock checking is disabled)."""
from itertools import product, combinations
W = ("w1", "w2", "w3", "w4"); V = ("a", "b")
CFGS = {"DecisionQuorum": ({"w1"}, 3, True), "f0": (set(), 3, True), "weak-q2": ({"w1"}, 2, True),
        "f2": ({"w1", "w2"}, 3, True), "no-persist": (set(), 3, False)}
def assume_ok(Q):
    subsets = [set(c) for r in range(5) for c in combinations(W, r)]
    return all(len(S & T) >= 2 * Q - 4 for S in subsets for T in subsets if len(S) >= Q and len(T) >= Q)
def succ(s, Byz, Persist):
    out = set()
    for i, w in enumerate(W):
        for v in V:
            honest = w not in Byz and (not Persist or s[i] == frozenset())
            byz = w in Byz
            if honest or byz:
                t = list(s); t[i] = s[i] | {v}; out.add(tuple(t))
    return out
for name, (Byz, Q, Persist) in CFGS.items():
    init = tuple(frozenset() for _ in W); seen = {init}; todo = [init]; dead = []; viol = {"Agreement": 0, "HonestSingle": 0}
    while todo:
        s = todo.pop()
        cert = lambda v: sum(v in x for x in s) >= Q
        if cert("a") and cert("b"): viol["Agreement"] += 1
        if Persist and any(len(s[i]) > 1 for i, w in enumerate(W) if w not in Byz): viol["HonestSingle"] += 1
        n = succ(s, Byz, Persist)
        if not n: dead.append(s)
        for t in n:
            if t not in seen: seen.add(t); todo.append(t)
    print(f"{name:15s} ASSUME={assume_ok(Q)} reachable={len(seen):4d} Agreement_violations={viol['Agreement']:3d} "
          f"HonestSingle_violations={viol['HonestSingle']} no_successor_states={len(dead)}")
```

Exit 0. Output (verbatim):
```
DecisionQuorum  ASSUME=True reachable= 108 Agreement_violations=  0 HonestSingle_violations=0 no_successor_states=0
f0              ASSUME=True reachable=  81 Agreement_violations=  0 HonestSingle_violations=0 no_successor_states=16
weak-q2         ASSUME=True reachable= 108 Agreement_violations= 18 HonestSingle_violations=0 no_successor_states=0
f2              ASSUME=True reachable= 144 Agreement_violations=  2 HonestSingle_violations=0 no_successor_states=0
no-persist      ASSUME=True reachable= 256 Agreement_violations= 25 HonestSingle_violations=0 no_successor_states=0
```

## Limits

- This is an enumeration of the model's semantics as I read them. It is not TLC and not a proof of anything beyond this finite model.
- Whether TLC itself reports exactly these counts is unverified until TLC runs.
- No ledger byte changed. This is not an execution ACK.

Action requested:
- agent 3: fix the f0 deadlock (§1) and consider the §4 wording before TLC runs. Comparing TLC's distinct-state counts with §2 is an optional cross-check.
- agent 2, human: none.
