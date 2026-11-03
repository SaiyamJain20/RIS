"""Expectations for the pool's recorded-value adoption rule (agent 2, F0 revision 5; answers A3-0061). Written BEFORE the reference exists.

Rule under test (SIGNING-RULES section 8, items 7-9): after a StateCheckpoint collection round in which witnesses refused CONFLICT_PINNED and returned the value they
recorded, the pool adopts a value M* iff EXACTLY ONE value has at least two distinct witnesses reporting it (valid signature, right sequence). Otherwise it adopts nothing.

PREDICTIONS (written first):
  A1  safety of adoption at f <= 1: over ALL assignments of three honest witnesses' recorded values (none, A, B) and ANY SUBSET of reports from the one Byzantine witness (A, B, FAKE,
      wrong-sequence value, invalid-signature FAKE), whenever a value is adopted at least one HONEST witness recorded it. (Exhaustive; the four witnesses are indices 0-3, the Byzantine one is
      each index in turn.)
  A2  positive: if two honest witnesses recorded the same value and no other value reaches two reports, that value is adopted.
  A3  ambiguity: two different values with two reports each adopt nothing.
  A4  control, outside the bound: with TWO Byzantine witnesses reporting the same FAKE value, FAKE is adopted (A1 is violated at f = 2; the check can fail).
  A5  one witness reporting the same value several times counts once.
  A6  reports for another sequence, and reports whose signature does not verify, are ignored.
  A7  adoption is a pure function of the reports: the order of reports does not matter.

    python3 -B -I protocol/f0/vectors/test_pool_adoption.py   (standard library only; exit 0 = all expectations hold)
"""
import importlib.util
import itertools
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pool_adoption", os.path.join(HERE, "pool_adoption.py"))
pa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pa)

FAILS = []


def check(name, cond):
    if not cond:
        FAILS.append(name)
    print(("ok   " if cond else "FAIL ") + name)


SEQ = 7
A, B, FAKE = ("7", "A"), ("7", "B"), ("7", "FAKE")
WRONG = ("8", "A")


def rep(w, value, valid=True):
    return {"witness": w, "message": value, "validSignature": valid}


# A1 exhaustive: 3 honest + 1 Byzantine, every position of the Byzantine witness
honest_choices = [None, A, B]
byz_pool = [A, B, FAKE, WRONG, ("7", "FAKE", "invalid")]          # what one Byzantine witness may send, in any combination
violations, cases, adopted_cases = [], 0, 0
for byz in range(4):
    honest = [i for i in range(4) if i != byz]
    for hv in itertools.product(honest_choices, repeat=3):
        for mask in range(1 << len(byz_pool)):
            reports = [rep(w, v) for w, v in zip(honest, hv) if v is not None]
            for j, bz in enumerate(byz_pool):
                if mask >> j & 1:
                    reports.append(rep(byz, bz[:2], valid=False) if len(bz) == 3 else rep(byz, bz))
            got = pa.adopt_recorded(reports, SEQ)
            cases += 1
            if got is not None:
                adopted_cases += 1
                if got not in [v for v in hv if v is not None]:
                    violations.append((byz, hv, mask, got))
check(f"A1 exhaustive f<=1 ({cases} assignments, {adopted_cases} adoptions): an adopted value was recorded by at least one honest witness", not violations)
check("A1 is not vacuous: some assignments adopt and some do not", 0 < adopted_cases < cases)

check("A2 positive: two honest witnesses recorded A, the others nothing, so A is adopted", pa.adopt_recorded([rep(0, A), rep(1, A)], SEQ) == A)
check("A2 positive with a Byzantine third reporter of B: A still adopted (B has one report)", pa.adopt_recorded([rep(0, A), rep(1, A), rep(3, B)], SEQ) == A)
check("A3 ambiguity: A and B each reported twice adopts nothing", pa.adopt_recorded([rep(0, A), rep(1, A), rep(2, B), rep(3, B)], SEQ) is None)
check("a single report adopts nothing", pa.adopt_recorded([rep(0, A)], SEQ) is None)
check("no reports adopts nothing", pa.adopt_recorded([], SEQ) is None)
check("A4 control outside the bound: two Byzantine witnesses reporting FAKE get FAKE adopted", pa.adopt_recorded([rep(0, FAKE), rep(1, FAKE)], SEQ) == FAKE)
check("A5 one witness repeating a value counts once", pa.adopt_recorded([rep(3, FAKE), rep(3, FAKE), rep(3, FAKE)], SEQ) is None)
check("A5 a witness reporting two different values counts once for EACH value: A has two distinct reporters (3 and 0), so A is adopted, and honest witness 0 recorded it", pa.adopt_recorded([rep(3, FAKE), rep(3, A), rep(0, A)], SEQ) == A)
check("A5 the same witness reporting FAKE twice and A once, with nobody else, adopts nothing", pa.adopt_recorded([rep(3, FAKE), rep(3, FAKE), rep(3, A)], SEQ) is None)
check("A6 other-sequence reports are ignored", pa.adopt_recorded([rep(0, WRONG), rep(1, WRONG)], SEQ) is None)
check("A6 invalid-signature reports are ignored", pa.adopt_recorded([rep(0, A, valid=False), rep(1, A, valid=False)], SEQ) is None)
check("A6 one valid plus one invalid report is not two reports", pa.adopt_recorded([rep(0, A), rep(1, A, valid=False)], SEQ) is None)
reports = [rep(0, A), rep(1, A), rep(2, B), rep(3, FAKE)]
check("A7 order independent", all(pa.adopt_recorded(list(p), SEQ) == pa.adopt_recorded(reports, SEQ) for p in itertools.permutations(reports)))
check("witness index outside 0..3 is refused", pa.refuses(lambda: pa.adopt_recorded([rep(4, A), rep(1, A)], SEQ)))
check("a non-boolean validSignature is refused", pa.refuses(lambda: pa.adopt_recorded([{"witness": 0, "message": A, "validSignature": "yes"}], SEQ)))

print("\nFAILED: %d" % len(FAILS) if FAILS else "\nall expectations hold")
sys.exit(1 if FAILS else 0)
