import json
from pathlib import Path

import pytest

from evaluation.run import run


ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "evaluation/evidence/f/execution-plan-draft-20261114/plan-draft.json"


def test_f_preflight_blocks_draft_and_keeps_all_cases_unrun(tmp_path):
    output = tmp_path / "f-preflight"

    result = run("F", "repaired-f", output, integration_plan=PLAN)

    assert result["status"] == "BLOCKED"
    assert result["executionMode"] == "f-preflight-only"
    assert result["executionAuthorized"] is False
    assert result["servicesStarted"] == []
    assert result["stage1Pins"]["status"] == "BLOCKED"
    assert result["stage2SourceBracket"]["status"] == "RECORDED"
    assert len(result["caseResults"]) == 32
    assert {case["status"] for case in result["caseResults"]} == {"NOT_RUN"}
    bracket = result["stage2SourceBracket"]["sourceBracket"]
    assert len(bracket["head"]) == 40
    assert bracket["branch"] == "agent-3"
    assert bracket["agent3SourceFiles"]
    assert len(bracket["sha256"]) == 64
    coverage = result["stage1Pins"]["caseCoverage"]
    assert coverage["matrixCaseCount"] == 32
    assert coverage["coverageCasesNotInMatrix"] == []
    assert coverage["coverageCsvSha256"]
    assert json.loads((output / "manifest.json").read_text()) == result


def test_f_preflight_flags_plan_case_coverage_drift(tmp_path):
    plan = json.loads(PLAN.read_text())
    plan["families"]["F-compromise-and-residual-inventory"]["cases"].remove("F-26")
    plan_path = tmp_path / "changed-plan.json"
    plan_path.write_text(json.dumps(plan))

    result = run("F", "repaired-f", tmp_path / "f-preflight", integration_plan=plan_path)

    assert result["status"] == "BLOCKED"
    assert result["stage1Pins"]["caseCoverage"]["status"] == "MISMATCH"
    assert "F-26" in result["stage1Pins"]["caseCoverage"]["missing"]
    assert result["servicesStarted"] == []


def test_f_preflight_blocks_when_frozen_matrix_ids_drift(tmp_path, monkeypatch):
    import evaluation.f_preflight as f_preflight

    matrix = json.loads((ROOT / f_preflight.MATRIX_PATH).read_text())
    matrix["cases"][0]["id"] = "UNEXPECTED-CASE"
    matrix_path = tmp_path / "matrix.json"
    matrix_path.write_text(json.dumps(matrix))
    monkeypatch.setattr(f_preflight, "MATRIX_PATH", matrix_path)

    result = run("F", "repaired-f", tmp_path / "f-preflight", integration_plan=PLAN)

    coverage = result["stage1Pins"]["caseCoverage"]
    assert coverage["status"] == "MISMATCH"
    assert coverage["coverageCasesNotInMatrix"]
    assert any("pinned F matrix" in blocker for blocker in result["blockers"])


def test_f_preflight_refuses_to_overwrite_output(tmp_path):
    output = tmp_path / "f-preflight"
    output.mkdir()
    sentinel = output / "manifest.json"
    sentinel.write_text("preserve")

    with pytest.raises(FileExistsError):
        run("F", "repaired-f", output, integration_plan=PLAN)

    assert sentinel.read_text() == "preserve"


def test_f_preflight_records_candidate_snapshots_without_finalizing_them(tmp_path):
    result = run("F", "repaired-f", tmp_path / "f-preflight", integration_plan=PLAN)

    ledger = result["stage1Pins"]["ownerCandidates"]["ledger"]
    protocol = result["stage1Pins"]["ownerCandidates"]["protocol"]
    assert len(ledger["commit"]) == 40 and len(ledger["tree"]) == 40
    assert len(protocol["commit"]) == 40 and len(protocol["tree"]) == 40
    assert ledger["finalPin"] is False
    assert protocol["finalPin"] is False


def test_f_preflight_does_not_treat_prefix_pins_as_exact(tmp_path):
    plan = json.loads(PLAN.read_text())
    plan["pins"]["f_matrix"] = "2230daf3da1eda11"
    plan["pins"]["interfaces/v2.1/FREEZE.json"] = "sha256 232b84bb7f997b68"
    plan_path = tmp_path / "prefix-plan.json"
    plan_path.write_text(json.dumps(plan))

    result = run("F", "repaired-f", tmp_path / "f-preflight", integration_plan=plan_path)

    pins = result["stage1Pins"]["pinChecks"]
    assert pins["fMatrix"]["status"] == "PREFIX_MATCH"
    assert pins["fMatrix"]["exactPin"] is False
    assert pins["fMatrix"]["actualSha256"] == "2230daf3da1eda11e7fd51a0c84f846711c2e1f1b3b2b5a82c33d3c262411b64"
    assert pins["interfaceV21Freeze"]["status"] == "PREFIX_MATCH"
    assert pins["interfaceV21Freeze"]["exactPin"] is False


def test_f_preflight_accepts_only_full_hashes_for_reviewed_artifacts(tmp_path):
    result = run("F", "repaired-f", tmp_path / "f-preflight", integration_plan=PLAN)

    pins = result["stage1Pins"]["pinChecks"]
    for name in (
        "interfaceFreeze",
        "interfaceV21Freeze",
        "interfaceV21Schema",
        "fMatrix",
        "coverageMap",
        "toolchainManifest",
        "tlcJar",
        "ledgerManifest",
        "ledgerCommit",
        "protocolCommit",
    ):
        assert pins[name]["status"] == "EXACT_MATCH"
        assert pins[name]["exactPin"] is True
    assert pins["ledgerManifest"]["sourceCommit"] == result["stage1Pins"]["ownerCandidates"]["ledger"]["commit"]
    assert result["stage1Pins"]["ownerCandidates"]["ledger"]["finalPin"] is False
    assert result["stage1Pins"]["ownerCandidates"]["protocol"]["finalPin"] is False


def test_f_preflight_checks_reviewed_v21_and_owner_artifact_pins(tmp_path):
    result = run("F", "repaired-f", tmp_path / "f-preflight", integration_plan=PLAN)

    pins = result["stage1Pins"]["pinChecks"]
    for name in (
        "interfaceV21Freeze",
        "interfaceV21Schema",
        "fMatrix",
        "coverageMap",
        "toolchainManifest",
        "tlcJar",
        "ledgerManifest",
    ):
        assert pins[name]["status"] == "EXACT_MATCH"
        assert pins[name]["exactPin"] is True
    assert pins["ledgerManifest"]["sourceCommit"] == result["stage1Pins"]["ownerCandidates"]["ledger"]["commit"]


def test_execution_draft_encodes_a1_0129_ledger_run_constraints():
    plan = json.loads(PLAN.read_text())

    deployment = plan["deployment"]
    assert deployment["script"] == "ledger/tools/deploy_local.sh"
    assert deployment["scratchArchive"] == "git archive <ledgerCommit> ledger"
    assert deployment["chainIds"] == {"pbc": 18545, "dbc": 28545}
    assert deployment["logMode"] == "complete-details"
    assert deployment["fProfile"] == "repaired-f"
    assert deployment["f18Profile"] == "mutant-f-q2"
    assert plan["oracleRules"]["ledgerRevert"] == "F-31 is outside the monotone safe-ledger assumption after evm_revert"
    assert plan["families"]["A-quorum-availability-and-signature-lists"]["rejectionCodes"]


def test_f_preflight_cli_returns_blocked_and_writes_manifest(tmp_path, monkeypatch):
    from evaluation.run import main
    import sys

    output = tmp_path / "f-cli"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "evaluation.run",
            "--rq",
            "F",
            "--profile",
            "repaired-f",
            "--integration-plan",
            str(PLAN),
            "--output",
            str(output),
        ],
    )

    assert main() == 2
    assert json.loads((output / "manifest.json").read_text())["status"] == "BLOCKED"
