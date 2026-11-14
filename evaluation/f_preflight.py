"""Fail-closed F setup preflight; this module never runs services or F cases."""

import csv
import hashlib
import json
import platform
import re
import subprocess
from pathlib import Path

from evaluation.manifests import canonical_hash, now, sha256, source_manifest


ROOT = Path(__file__).resolve().parents[1]
COVERAGE_PATH = Path("evaluation/evidence/f/case-coverage-map-20261114/coverage.csv")
MATRIX_PATH = Path("evaluation/evidence/reviews/f0-revision8-20261104/f_matrix.json")
INTERFACE_FREEZE_PATH = Path("interfaces/v2/FREEZE.json")
TOOLCHAIN_PATH = Path("evaluation/toolchain.json")
TLC_EVIDENCE_README = Path("evaluation/evidence/f/decision-quorum-tlc-20261113/README.md")
LEDGER_MANIFEST_PATH = "ledger/evidence/source-manifest.sha256"


def _git(root, *args):
    completed = subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, timeout=10
    )
    if completed.returncode:
        raise ValueError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def _case_inventory(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    cases = [row.get("case", "") for row in rows]
    if not cases or any(not case for case in cases) or len(cases) != len(set(cases)):
        raise ValueError("F case coverage inventory must contain unique non-empty case IDs")
    return cases


def _planned_case_ids(plan):
    families = plan.get("families")
    if not isinstance(families, dict):
        return []
    cases = []
    for family in families.values():
        if not isinstance(family, dict) or not isinstance(family.get("cases"), list):
            return []
        cases.extend(case for case in family["cases"] if isinstance(case, str))
    return cases


def _resolve_owner_candidate(root, label, description, remote_ref):
    matches = re.findall(r"(?<![0-9a-f])[0-9a-f]{7,40}(?![0-9a-f])", str(description))
    if not matches:
        return {"requested": str(description), "available": False, "finalPin": False}
    requested = matches[0]
    try:
        commit = _git(root, "rev-parse", "--verify", requested + "^{commit}")
        tree = _git(root, "rev-parse", "--verify", commit + "^{tree}")
        branch_exists = subprocess.run(
            ["git", "rev-parse", "--verify", remote_ref],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=10,
        ).returncode == 0
        ancestor = False
        if branch_exists:
            ancestor = subprocess.run(
                ["git", "merge-base", "--is-ancestor", commit, remote_ref],
                cwd=root,
                timeout=10,
            ).returncode == 0
        return {
            "requested": requested,
            "commit": commit,
            "tree": tree,
            "remoteRef": remote_ref,
            "remoteRefExists": branch_exists,
            "isAncestorOfOwnerHead": ancestor,
            "available": True,
            "finalPin": False,
        }
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        return {
            "requested": requested,
            "remoteRef": remote_ref,
            "available": False,
            "finalPin": False,
            "error": str(error),
        }


def _check_hash_pin(root, path, description):
    actual = sha256(root / path)
    matches = re.findall(r"(?<![0-9a-f])[0-9a-f]{7,64}(?![0-9a-f])", str(description))
    if not matches:
        return {"path": str(path), "status": "UNPINNED", "actualSha256": actual, "exactPin": False}
    requested = matches[0]
    matches_actual = actual == requested if len(requested) == 64 else actual.startswith(requested)
    status = ("EXACT_MATCH" if len(requested) == 64 else "PREFIX_MATCH") if matches_actual else "MISMATCH"
    return {
        "path": str(path),
        "requested": requested,
        "requestedLength": len(requested),
        "actualSha256": actual,
        "status": status,
        "exactPin": len(requested) == 64 and matches_actual,
    }


def _commit_pin(description, candidate):
    matches = re.findall(r"(?<![0-9a-f])[0-9a-f]{7,40}(?![0-9a-f])", str(description))
    requested = matches[0] if matches else ""
    matched = bool(candidate.get("available") and candidate.get("commit", "").startswith(requested))
    return {
        "requestedLength": len(requested),
        "resolvedCommit": candidate.get("commit"),
        "resolvedTree": candidate.get("tree"),
        "status": "PREFIX_RESOLVED" if matched and len(requested) < 40 else "EXACT_MATCH" if matched else "MISMATCH",
        "exactPin": matched and len(requested) == 40,
    }


def _check_owner_blob_hash(root, commit, path, description):
    matches = re.findall(r"(?<![0-9a-f])[0-9a-f]{7,64}(?![0-9a-f])", str(description))
    requested = matches[0] if matches else ""
    try:
        completed = subprocess.run(
            ["git", "show", f"{commit}:{path}"],
            cwd=root,
            capture_output=True,
            timeout=10,
            check=True,
        )
        actual = hashlib.sha256(completed.stdout).hexdigest()
    except (OSError, subprocess.SubprocessError):
        actual = None
    exact = len(requested) == 64 and actual == requested
    return {
        "path": path,
        "sourceCommit": commit,
        "requested": requested or None,
        "requestedLength": len(requested),
        "actualSha256": actual,
        "status": "EXACT_MATCH" if exact else "MISMATCH" if actual else "UNAVAILABLE",
        "exactPin": exact,
    }


def _toolchain_observations(root, plan):
    toolchain = json.loads((root / TOOLCHAIN_PATH).read_text(encoding="utf-8"))
    binaries = {}
    expected_tools = {
        **toolchain.get("foundry", {}).get("binaryPaths", {}),
        "solc": toolchain.get("solc", {}),
    }
    for name, expected in expected_tools.items():
        path = Path(expected.get("path", ""))
        exists = path.is_file()
        observed_hash = sha256(path) if exists else None
        try:
            result = subprocess.run(
                [str(path), "--version"], capture_output=True, text=True, timeout=5
            ) if exists else None
            version_output = ((result.stdout or "") + (result.stderr or "")).strip() if result else None
            exit_code = result.returncode if result else None
        except (OSError, subprocess.SubprocessError) as error:
            version_output, exit_code = str(error), None
        binaries[name] = {
            "path": str(path),
            "exists": exists,
            "expectedSha256": expected.get("sha256"),
            "observedSha256": observed_hash,
            "hashMatches": exists and observed_hash == expected.get("sha256"),
            "versionCommandExitCode": exit_code,
            "versionOutput": version_output,
        }

    evidence = (root / TLC_EVIDENCE_README).read_text(encoding="utf-8")
    match = re.search(
        r"tla2tools\.jar sha256 ([0-9a-f]{64})\s*\(path ([^)]+)\)", evidence
    )
    if match:
        expected_tlc_hash, directory = match.groups()
        jar = Path(directory.strip()).expanduser() / "tla2tools.jar"
        exists = jar.is_file()
        observed = sha256(jar) if exists else None
        tlc = {
            "path": str(jar),
            "expectedSha256": expected_tlc_hash,
            "observedSha256": observed,
            "hashMatches": exists and observed == expected_tlc_hash,
            "versionClaim": "TLC 2.19 (pinned prior evidence)",
        }
    else:
        tlc = {"available": False, "error": "TLC jar pin not found in prior evidence"}

    expected_lock = toolchain.get("pythonLock", {}).get("sha256")
    lock_path = root / "uv.lock"
    observed_lock = sha256(lock_path) if lock_path.is_file() else None
    planned_tlc_hash = plan.get("pins", {}).get("tlcJarSha256", "")
    actual_tlc = tlc.get("observedSha256")
    root_tlc_status = toolchain.get("tlc")
    return {
        "pythonVersion": platform.python_version(),
        "expectedPythonVersion": toolchain.get("hostPython"),
        "pythonVersionMatches": platform.python_version() == toolchain.get("hostPython"),
        "rootLock": {
            "path": "uv.lock",
            "expectedSha256": expected_lock,
            "observedSha256": observed_lock,
            "hashMatches": observed_lock == expected_lock,
        },
        "binaries": binaries,
        "tlc": tlc,
        "tlcPlanSha256": planned_tlc_hash,
        "tlcPlanPinMatches": bool(len(planned_tlc_hash) == 64 and actual_tlc == planned_tlc_hash),
        "rootToolchainTlcStatus": toolchain.get("tlc"),
        "tlcScopeNote": "F-only TLC is pinned separately; the frozen root/E toolchain excludes F/G tools"
        if root_tlc_status == "NOT INSTALLED: F/G locked"
        else "Root toolchain TLC status requires review",
    }


def _source_bracket(root, owner_candidates, pin_checks, toolchain):
    files = source_manifest(root)
    head = _git(root, "rev-parse", "HEAD")
    branch = _git(root, "branch", "--show-current")
    dirty = _git(root, "status", "--porcelain", "--untracked-files=all").splitlines()
    payload = {
        "head": head,
        "branch": branch,
        "dirtyPaths": dirty,
        "agent3SourceFiles": files,
        "ownerCandidates": owner_candidates,
        "pinChecks": pin_checks,
        "toolchain": toolchain,
    }
    payload["sha256"] = canonical_hash(payload)
    return payload


def _case_coverage(plan, expected_cases, matrix_cases, coverage_path):
    planned = _planned_case_ids(plan)
    duplicates = sorted({case for case in planned if planned.count(case) > 1})
    planned_set = set(planned)
    expected_set = set(expected_cases)
    missing = sorted(expected_set - planned_set)
    extra = sorted(planned_set - expected_set)
    matrix_missing = sorted(expected_set - set(matrix_cases))
    matrix_extra = sorted(set(matrix_cases) - expected_set)
    matrix_duplicates = sorted({case for case in matrix_cases if matrix_cases.count(case) > 1})
    return {
        "status": "MATCH" if not (duplicates or missing or extra or matrix_missing or matrix_extra or matrix_duplicates) else "MISMATCH",
        "expectedCount": len(expected_cases),
        "plannedCount": len(planned),
        "missing": missing,
        "extra": extra,
        "duplicates": duplicates,
        "coverageCsvSha256": sha256(coverage_path),
        "matrixCaseCount": len(matrix_cases),
        "coverageCasesNotInMatrix": matrix_missing,
        "matrixCasesNotInCoverage": matrix_extra,
        "duplicateMatrixCases": matrix_duplicates,
        "planCasesSha256": hashlib.sha256("\n".join(sorted(planned)).encode()).hexdigest(),
    }


def preflight(plan_path, output, *, root=ROOT, profile="repaired-f", provided_acks=None):
    """Record F stages 1-2 only. No execution or ACK can authorize services here."""
    root = Path(root).resolve()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    plan_path = Path(plan_path)
    raw = plan_path.read_bytes()
    plan = json.loads(raw)

    expected_cases = _case_inventory(root / COVERAGE_PATH)
    matrix = json.loads((root / MATRIX_PATH).read_text(encoding="utf-8"))
    matrix_cases = [item["id"] for item in matrix.get("cases", []) if isinstance(item, dict) and isinstance(item.get("id"), str)]
    coverage = _case_coverage(plan, expected_cases, matrix_cases, root / COVERAGE_PATH)
    pins = plan.get("pins", {})
    candidates = {
        "ledger": _resolve_owner_candidate(root, "ledger", pins.get("ledger", ""), "origin/agent-1"),
        "protocol": _resolve_owner_candidate(root, "protocol", pins.get("protocolSourceCandidate", ""), "origin/agent-2"),
    }
    versions = _toolchain_observations(root, plan)
    pin_checks = {
        "ledgerCommit": _commit_pin(pins.get("ledger", ""), candidates["ledger"]),
        "protocolCommit": _commit_pin(pins.get("protocolSourceCandidate", ""), candidates["protocol"]),
        "interfaceFreeze": _check_hash_pin(root, INTERFACE_FREEZE_PATH, pins.get(str(INTERFACE_FREEZE_PATH), "")),
        "interfaceV21Freeze": _check_hash_pin(root, Path("interfaces/v2.1/FREEZE.json"), pins.get("interfaces/v2.1/FREEZE.json", "")),
        "interfaceV21Schema": _check_hash_pin(root, Path("interfaces/v2.1/hmbc.schema.json"), pins.get("interfaces/v2.1/hmbc.schema.json", "")),
        "fMatrix": _check_hash_pin(root, MATRIX_PATH, pins.get("f_matrix", "")),
        "coverageMap": _check_hash_pin(root, COVERAGE_PATH, pins.get("coverageMapSha256", "")),
        "toolchainManifest": _check_hash_pin(root, TOOLCHAIN_PATH, pins.get("toolchainManifestSha256", "")),
        "tlcJar": {
            "status": "EXACT_MATCH" if versions["tlc"].get("hashMatches") and versions["tlcPlanPinMatches"] else "MISMATCH",
            "requested": versions.get("tlcPlanSha256") or None,
            "requestedLength": len(versions.get("tlcPlanSha256") or ""),
            "actualSha256": versions["tlc"].get("observedSha256"),
            "exactPin": bool(versions["tlc"].get("hashMatches") and versions["tlcPlanPinMatches"]),
        },
        "ledgerManifest": _check_owner_blob_hash(
            root,
            candidates["ledger"].get("commit", ""),
            LEDGER_MANIFEST_PATH,
            pins.get("ledgerManifestSha256", ""),
        ),
    }
    bracket = _source_bracket(root, candidates, pin_checks, versions)

    blockers = []
    if plan.get("status") != "FROZEN" or plan.get("authorizesExecution") is not True:
        blockers.append("Execution plan is DRAFT and does not authorize execution.")
    if coverage["status"] != "MATCH":
        blockers.append("Execution plan case list differs from the 32-case coverage inventory.")
    if coverage["matrixCaseCount"] != coverage["expectedCount"]:
        blockers.append("The pinned F matrix has fewer cases than the 32-case coverage inventory; the final plan must pin and explain the supplemental rows.")
    if (
        coverage["coverageCasesNotInMatrix"]
        or coverage["matrixCasesNotInCoverage"]
        or coverage["duplicateMatrixCases"]
    ):
        blockers.append("The pinned F matrix case IDs differ from the 32-case coverage inventory.")
    for label, candidate in candidates.items():
        if not candidate.get("available") or not candidate.get("remoteRefExists") or not candidate.get("isAncestorOfOwnerHead"):
            blockers.append(f"{label} candidate source commit is not verified against the fetched owner branch.")
    if not candidates["protocol"].get("finalPin"):
        blockers.append("Protocol source is only a candidate; K1 and the A3-0121 signing-rule question remain open.")
    if not versions["tlc"].get("hashMatches") or not versions["tlcPlanPinMatches"]:
        blockers.append("The F-only TLC jar does not match the exact artifact pinned in the draft plan.")
    for name in (
        "ledgerCommit",
        "protocolCommit",
        "interfaceFreeze",
        "interfaceV21Freeze",
        "interfaceV21Schema",
        "fMatrix",
        "coverageMap",
        "toolchainManifest",
        "tlcJar",
        "ledgerManifest",
    ):
        if not pin_checks[name]["exactPin"]:
            blockers.append(f"{name} is not bound by a complete exact pin in the draft plan.")
    if (
        not versions["pythonVersionMatches"]
        or not versions["rootLock"]["hashMatches"]
        or any(not item["hashMatches"] or item["versionCommandExitCode"] != 0 for item in versions["binaries"].values())
    ):
        blockers.append("A local toolchain executable, Python version, or dependency lock does not match the recorded root toolchain.")
    blockers.append("Only preflight stages 1-2 are implemented; isolated baselines, integrated cases, post-bracket and gate execution are not available.")
    if provided_acks is not None:
        blockers.append("An ACK path was supplied, but this preflight does not parse or accept execution ACKs.")

    case_results = [{"case": case, "status": "NOT_RUN"} for case in expected_cases]
    manifest = {
        "schemaVersion": "hmbc-f-preflight/v1",
        "runId": output.name,
        "rq": "F",
        "profile": profile,
        "executionMode": "f-preflight-only",
        "status": "BLOCKED",
        "executionAuthorized": False,
        "servicesStarted": [],
        "planPath": str(plan_path.resolve()),
        "planSha256": hashlib.sha256(raw).hexdigest(),
        "planStatus": plan.get("status"),
        "stage1Pins": {
            "status": "BLOCKED",
            "caseCoverage": coverage,
            "pinChecks": pin_checks,
            "ownerCandidates": candidates,
            "toolchain": versions,
        },
        "stage2SourceBracket": {"status": "RECORDED", "sourceBracket": bracket},
        "caseResults": case_results,
        "blockers": blockers,
        "startedAt": now(),
        "endedAt": now(),
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
