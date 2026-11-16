#!/usr/bin/env python3
"""A-E2: run the mutant-* deployment suites and verify each is detected by the expected tests.

Usage (repository root): python3 -I ledger/tools/check_mutants.py [report.json]

Each `test-mutants/` suite deploys REPAIRED_E or REPAIRED_F with exactly one check removed (or, for
mutant-f-q2, threshold 2 instead of 3). Detection means the
listed repaired-e property tests FAIL against that mutant. Every other test in the suite should still
pass (otherwise the mutant breaks something unrelated). Unmutated base suites, compiled in the same
run, must have no failures. Exit 0 only if all of that holds. Standard library only; needs forge.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

LEDGER = pathlib.Path(__file__).resolve().parent.parent

EXPECTED = {
    "MutantNoDestinationBindingTest": {"test_E01_RequestForOtherDestinationCertifiedHere",
                                       "test_E01_RequestFieldSubstitution"},
    "MutantNoStateBarrierTest": {"test_E02_RevocationBarrierBlocksOlderDecision"},
    "MutantNoRecordFreshnessTest": {"test_E02_DeliveryAfterOnDutyEntryEnds"},
    "MutantNoNonceDecisionBindingTest": {"test_E01_NonceReuseAcrossDifferentRequests"},
    "MutantNoNonceAccessFlowTest": {"test_AliceRegisteredDoctorOnDutyGetsGrant"},
    "MutantNoVersionMonotoneTest": {"test_E02_StaleSignedTempAclReplay", "test_E02_StaleSignedCrlReplay",
                                    "test_E02_EqualVersionDifferentContent"},
    "MutantNoReceiptBindingTest": {"test_E03_ReceiptFieldSubstitution"},
    # A-F1 (design 2.2 section 6), REPAIRED_F. Pre-registered before the first mutant run.
    "MutantNoGovActionBindingTest": {"test_AF1G_SetCertificateSubmittedAsRemoveIsBadSignature"},
    "MutantNoGovNonceTest": {"test_AF1G_ReplayedSetIsReplayWithNoSecondEffect", "test_AF1G_NonceReplayAndGap",
                             "test_AF1G_CheckOrderStructureNonceExpirySignatures",
                             "test_AF1G_AddAuthorityByQuorum", "test_AF1G_RemovedRootCannotBeReAdded",
                             "test_AF1G_ExpiryBounds"},
    "MutantNoPolicyPinTest": {"test_AF1Q_PolicyPinRejectsAForeignPolicyVersion"},
    # mutant-f-q2 (F-18): a configuration, threshold 2 in PSC, KSSC and Governance, mask 0, no code bit.
    "MutantFQ2QuorumTest": {"test_AF1Q_CheckpointRejectsBadQuorumLists", "test_AF1Q_DecisionRejectsBadQuorumLists",
                            "test_AF1Q_ReceiptRejectsBadQuorumLists"},
    "MutantFQ2GovernanceTest": {"test_AF1G_QuorumFailures"},
}


def main(argv) -> int:
    env = dict(os.environ, FOUNDRY_PROFILE="mutants")
    proc = subprocess.run([shutil.which("forge") or "forge", "test", "--root", str(LEDGER)],
                          capture_output=True, text=True, env=env)
    out = proc.stdout + proc.stderr
    failing = {}
    suite = None
    for line in out.splitlines():
        if line.startswith("Failing tests:"):
            break  # forge repeats every failure in a trailing summary; per-suite sections are above
        m = re.match(r"Ran \d+ tests? for (\S+):(\w+)", line)
        if m:
            suite = m.group(2)
            failing.setdefault(suite, set())
            continue
        m = re.match(r"\[FAIL[^\]]*\] (test\w+)\(", line)
        if m and suite:
            failing[suite].add(m.group(1))
    ok = True
    report = {"command": "FOUNDRY_PROFILE=mutants forge test --root ledger", "forgeExit": proc.returncode, "suites": {}}
    for name, want in EXPECTED.items():
        got = failing.get(name)
        if got is None:
            print(f"MISSING  {name}: suite did not run")
            ok = False
            continue
        missed = sorted(want - got)
        extra = sorted(got - want)
        detected = not missed and not extra
        ok = ok and detected
        report["suites"][name] = {"expectedFailing": sorted(want), "failing": sorted(got), "missed": missed,
                                  "unexpected": extra, "detected": detected}
        print(f"{'DETECTED' if detected else 'MISMATCH'} {name}: failing={sorted(got)} missed={missed} unexpected={extra}")
    for name, got in failing.items():
        if name not in EXPECTED and got:
            print(f"BASE-SUITE FAILURE {name}: {sorted(got)}")
            report["suites"][name] = {"unexpectedBaseFailures": sorted(got)}
            ok = False
    if len(argv) > 1:
        pathlib.Path(argv[1]).write_text(json.dumps(report, indent=2) + "\n")
    print("ALL MUTANTS DETECTED BY THEIR EXPECTED TESTS" if ok else "MUTANT CHECK FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
