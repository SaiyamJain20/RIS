"""Re-run fault-oracle mutation controls against the unchanged WitnessStore grid.

Usage: python3 -I oracle_mutant_discrimination.py <protocol-root> <output.json>

This is an offline synthetic harness. It imports the existing 180-case oracle/store
differential driver and changes only the oracle predicate under test; each run gets
fresh temporary SQLite stores. It does not start services or run an F case.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import runpy
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from evaluation.oracles import faults  # noqa: E402


def mutant(name: str):
    def is_dead(prev: dict, obs: dict) -> bool:
        exp = prev.get("expires_at")
        typ = prev["type"]
        if name == "expiry-strict" and exp is not None and obs["timestamp"] > exp:
            return True
        if name != "expiry-strict" and exp is not None and obs["timestamp"] >= exp:
            return True
        if typ == "StateCheckpoint":
            op = obs["sequence"] > prev["seq"] if name == "checkpoint-strict" else obs["sequence"] >= prev["seq"]
            return op
        if typ == "GovernanceAction":
            op = obs["nonce"] > prev["seq"] if name == "governance-strict" else obs["nonce"] >= prev["seq"]
            return op
        if typ == "AccessDecision":
            sequence_dead = obs["sequence"] >= prev["seq"] if name == "decision-inclusive" else obs["sequence"] > prev["seq"]
            grant_dead = bool(obs["grant_exists"])
            if name == "drop-grant-death":
                grant_dead = False
            elif name == "grant-kills-deny":
                grant_dead = bool(obs["grant_exists"])
            else:
                grant_dead = prev.get("result") == "ALLOW" and grant_dead
            return sequence_dead or grant_dead
        if typ == "GrantReceipt":
            return False if name == "receipt-never-dead" else bool(obs["outcome_recorded"])
        return False

    return is_dead


def run_grid(protocol_root: str, output_path: Path) -> dict:
    sys.argv = ["oracle_store_diff.py", protocol_root, str(output_path)]
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        runpy.run_path(str(ROOT / "evaluation/measurements/oracle_store_diff.py"), run_name="__main__")
    result = json.loads(output_path.read_text(encoding="utf-8"))
    result["stdout"] = stdout.getvalue()
    return result


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    protocol_root = os.path.abspath(sys.argv[1])
    output = Path(sys.argv[2])
    baseline = run_grid(protocol_root, output.with_suffix(".baseline.json"))
    expected = {
        "expiry-strict": 20,
        "receipt-never-dead": 18,
        "decision-inclusive": 6,
        "drop-grant-death": 4,
        "grant-kills-deny": 4,
        "checkpoint-strict": 4,
        "governance-strict": 4,
    }
    controls = []
    original = faults.is_dead
    try:
        for name, expected_disagreements in expected.items():
            faults.is_dead = mutant(name)
            with tempfile.TemporaryDirectory(prefix="ris-oracle-mutant-") as temp:
                result = run_grid(protocol_root, Path(temp) / "mutant.json")
            summary = result["summary"]
            controls.append({
                "mutant": name,
                "cases": summary["cases"],
                "oracle_store_agree": summary["agree"],
                "disagreements": summary["disagree"],
                "expected_disagreements_from_prior_receipt": expected_disagreements,
                "matches_prior_count": summary["disagree"] == expected_disagreements,
            })
    finally:
        faults.is_dead = original
    report = {
        "classification": "tested reconstruction result on synthetic offline fixtures",
        "scope": "oracle mutation sensitivity against the existing 180-case SQLite WitnessStore grid; not Gate F",
        "baseline": baseline["summary"],
        "controls": controls,
        "all_controls_detected": all(row["disagreements"] > 0 for row in controls),
        "all_prior_counts_reproduced": all(row["matches_prior_count"] for row in controls),
        "mutants": [row["mutant"] for row in controls],
        "limitations": [
            "same-model oracle and store; synthetic keys and observations",
            "one earlier digest per key; grant and executed-receipt facts are caller-asserted",
            "no native ledger reachability, process transcript, quorum, or integrated F case",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"baseline": report["baseline"], "controls": controls,
                      "all_controls_detected": report["all_controls_detected"],
                      "all_prior_counts_reproduced": report["all_prior_counts_reproduced"]}, indent=2))
    return 0 if report["baseline"].get("disagree") == 0 and report["all_controls_detected"] and report["all_prior_counts_reproduced"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
