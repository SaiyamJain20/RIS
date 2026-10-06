#!/usr/bin/env python3
"""A-E1 test-sensitivity check: remove one ledger check at a time and require named tests to fail.

Usage (repository root): python3 -I ledger/tools/mutation_smoke.py [report.json]

These are throwaway source edits in a temporary copy of ledger/, used only to show that the A-E1
suite is not vacuous (deny-all and grant-all both fail it). They are NOT the A-E2 `mutant-*`
deployment profiles and say nothing about HMBC. Each edit must match its source text exactly once.
Exit 0 only if every mutant is detected by all of its expected tests and the unmutated copy passes.
Standard library only; requires `forge` on PATH.
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

LEDGER = pathlib.Path(__file__).resolve().parent.parent

# (id, file, original, replacement, tests that must FAIL)
MUTANTS = [
    ("grant-all-policy", "src/ACSC.sol",
     "DataEntry storage d = _data[dataId];\n        if (!d.exists) return false;",
     "DataEntry storage d = _data[dataId];\n        if (d.exists) return true;",
     ["test_BobWithoutDoctorRoleIsDeniedAndGetsNoGrant", "test_TemporalRoleWithoutLongTermDoctorIsDenied"]),
    ("deny-all-policy", "src/ACSC.sol",
     "if (!d.exists) return false;",
     "if (d.exists || !d.exists) return false;",
     ["test_AliceRegisteredDoctorOnDutyGetsGrant"]),
    ("unscoped-ca-admin", "src/TMSC.sol",
     "if (!isCaAdmin[authority][msg.sender])",
     "if (false && !isCaAdmin[authority][msg.sender])",
     ["test_H1AdminCannotReplaceH2TemporalAcl", "test_H1AdminCannotReplaceH2RevocationList",
      "test_NonAdminCannotUpdateEvenWithIssuerSignature"]),
    ("no-list-signature", "src/TMSC.sol",
     "if (profile != Profile.PAPER_MINIMAL && !SigLib.isValid(digest, issuerSignature, authority))",
     "if (false && !SigLib.isValid(digest, issuerSignature, authority))",
     ["test_ListNotSignedByIssuerRootKey"]),
    ("no-crl-check", "src/TMSC.sol",
     "if (st.published && _revoked[keccak256(abi.encode(c.issuer, st.generation, c.serial))])",
     "if (false && _revoked[keccak256(abi.encode(c.issuer, st.generation, c.serial))])",
     ["test_CrlRevocationTakesEffectAtPbc"]),
    ("no-gid-possession", "src/RSC.sol",
     "if (!SigLib.isValid(digest, possessionSignature, reg.gid))",
     "if (false && !SigLib.isValid(digest, possessionSignature, reg.gid))",
     ["test_RegistrationWithoutGidPossessionFails"]),
    ("no-user-signature", "src/PSC.sol",
     "if (!SigLib.isValid(requestDigest, userSignature, r.gid)) return ErrorCode.BAD_SIGNATURE;",
     "if (false) return ErrorCode.BAD_SIGNATURE;",
     ["test_RequestSignedByAnotherKeyIsDenied"]),
    ("request-expiry-off-by-one", "src/PSC.sol",
     "if (block.timestamp >= r.expiresAt) return ErrorCode.EXPIRED;",
     "if (block.timestamp > r.expiresAt) return ErrorCode.EXPIRED;",
     ["test_RequestAtExactExpiryIsDenied"]),
    ("no-pbc-destination-check", "src/PSC.sol",
     "if (r.kssc == address(0) || ksscForChain[r.destinationChainId] != r.kssc) return ErrorCode.WRONG_DESTINATION;",
     "if (false) return ErrorCode.WRONG_DESTINATION;",
     ["test_WrongDestinationRequestIsDenied"]),
    ("no-pbc-replay-check", "src/PSC.sol",
     "if (_requests[requestDigest].status != RequestStatus.NONE) return ErrorCode.REPLAY;",
     "if (false) return ErrorCode.REPLAY;",
     ["test_DuplicateForwardedRequestIsReplayAndBothAreLogged"]),
    ("denial-reverts-log", "src/PSC.sol",
     "denialCount[requestDigest] += 1;",
     "revert Rejected(code);",
     ["test_UnregisteredUserIsDeniedAtPbcButRequestIsLogged"]),
    ("unauthenticated-outcome", "src/PSC.sol",
     "if (msg.sender != relay) revert Rejected(ErrorCode.UNAUTHORIZED_CALLER);",
     "if (false) revert Rejected(ErrorCode.UNAUTHORIZED_CALLER);",
     ["test_OutcomeRequiresRelayForwardedRequestAndMatchingGrant"]),
    ("unauthenticated-relay", "src/ACSC.sol",
     "if (msg.sender != pscRelay) revert Rejected(ErrorCode.UNAUTHORIZED_CALLER);",
     "if (false) revert Rejected(ErrorCode.UNAUTHORIZED_CALLER);",
     ["test_TableActuatorRestrictions"]),
    ("no-witness-quorum", "src/DecisionVerifier.sol",
     "if (code != ErrorCode.NONE) return (code, requestDigest);",
     "if (false) return (code, requestDigest);",
     ["test_RejectedCertificateChangesNoState"]),
    ("no-nonce-consumption", "src/KSSC.sol",
     "nonceConsumed[p.gid][p.nonce] = true;",
     "p.nonce;",
     ["test_AliceRegisteredDoctorOnDutyGetsGrant"]),
]


def run_forge(root: pathlib.Path):
    proc = subprocess.run(
        [shutil.which("forge") or "forge", "test", "--root", str(root)],
        capture_output=True, text=True,
    )
    failing = sorted(set(re.findall(r"\[FAIL[^\]]*\] (test\w+)\(", proc.stdout + proc.stderr)))
    summary = re.findall(r"(\d+) tests passed, (\d+) failed", proc.stdout)
    compiled = "Compiler run successful" in proc.stdout or "No files changed" in proc.stdout or bool(summary)
    return proc.returncode, failing, summary[-1] if summary else None, compiled


def copy_ledger(dst: pathlib.Path):
    for part in ("src", "test", "script"):
        shutil.copytree(LEDGER / part, dst / part)
    shutil.copy2(LEDGER / "foundry.toml", dst / "foundry.toml")
    (dst / "exports").mkdir()


def main(argv) -> int:
    report = {"tool": "ledger/tools/mutation_smoke.py", "mutants": []}
    ok = True
    with tempfile.TemporaryDirectory(prefix="hmbc-ledger-mutants-") as tmp:
        base = pathlib.Path(tmp) / "baseline"
        copy_ledger(base)
        code, failing, summary, _ = run_forge(base)
        report["baseline"] = {"exit": code, "failing": failing, "passedFailed": summary}
        print(f"baseline: exit={code} passed/failed={summary}")
        if code != 0:
            ok = False
        for mid, rel, original, replacement, expected in MUTANTS:
            root = pathlib.Path(tmp) / mid
            copy_ledger(root)
            path = root / rel
            text = path.read_text()
            count = text.count(original)
            if count != 1:
                print(f"ERROR {mid}: original text found {count} times in {rel}")
                report["mutants"].append({"id": mid, "error": f"match count {count}"})
                ok = False
                continue
            path.write_text(text.replace(original, replacement))
            code, failing, summary, _ = run_forge(root)
            missed = [t for t in expected if t not in failing]
            detected = code != 0 and not missed
            ok = ok and detected
            report["mutants"].append({
                "id": mid, "file": rel, "exit": code, "passedFailed": summary,
                "expectedFailing": expected, "failing": failing, "detected": detected,
            })
            print(f"{'DETECTED' if detected else 'MISSED  '} {mid}: exit={code} failing={len(failing)} missed={missed}")
    if len(argv) > 1:
        pathlib.Path(argv[1]).write_text(json.dumps(report, indent=2) + "\n")
    print("ALL MUTANTS DETECTED" if ok else "SOME MUTANTS MISSED OR BASELINE FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
