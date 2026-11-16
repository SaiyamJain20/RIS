"""Retain synthetic executor examples only. No protocol/ledger/model execution."""

import copy
import json
from pathlib import Path
import sys
import tempfile

from evaluation.f_baselines import run_baselines
from evaluation.manifests import canonical_hash, sha256


def main():
    output = Path(__file__).resolve().parent / "sample"
    output.mkdir(exist_ok=False)
    with tempfile.TemporaryDirectory(prefix="ris-baseline-synthetic-") as scratch:
        root = Path(scratch)
        fixture = root / "fixture.txt"
        fixture.write_text("synthetic public fixture\n")
        recipe = {
            "schemaVersion": "hmbc-f-baselines/v1", "workspace": str(root),
            "sourceRoots": ["fixture.txt"], "sourceFiles": {"fixture.txt": sha256(fixture)},
            "runtimeFiles": {}, "tools": {"python": {"path": sys.executable, "sha256": sha256(sys.executable)}},
            "environment": {}, "commands": [],
        }
        def cmd(name, script, code=0, expected="CONTROL", timeout=2):
            return {"id": name, "tool": "python", "args": ["-c", script], "cwd": ".",
                    "timeoutSeconds": timeout, "maxOutputBytes": 1024 * 1024,
                    "expectedExitCode": code, "requiredOutput": [expected]}
        recipe["commands"] = [cmd("control", 'import sys; print("CONTROL"); print("STDERR",file=sys.stderr)'),
                              cmd("counterexample", 'import sys; print("SYNTHETIC COUNTEREXAMPLE"); sys.exit(12)', 12, "SYNTHETIC COUNTEREXAMPLE")]
        summaries = {}
        for name in ("controls", "wrong-source", "failed-command", "timeout"):
            candidate = copy.deepcopy(recipe)
            if name == "wrong-source": candidate["sourceFiles"]["fixture.txt"] = "0" * 64
            if name == "failed-command": candidate["commands"][0] = cmd("control", 'import sys; print("CONTROL"); sys.exit(7)')
            if name == "timeout": candidate["commands"][0] = cmd("control", 'import time; print("CONTROL",flush=True); time.sleep(30)', timeout=.2)
            recipe_path = output / (name + "-recipe.json")
            recipe_path.write_text(json.dumps(candidate, indent=2) + "\n")
            result = run_baselines(candidate, output / name, expected_recipe_sha256=canonical_hash(candidate))
            summaries[name] = {"status": result["status"], "commands": [r["status"] for r in result["commands"]]}
        assert summaries == {
            "controls": {"status": "PASS", "commands": ["PASS", "PASS"]},
            "wrong-source": {"status": "BLOCKED", "commands": []},
            "failed-command": {"status": "FAIL", "commands": ["FAIL", "NOT_RUN"]},
            "timeout": {"status": "FAIL", "commands": ["FAIL", "NOT_RUN"]},
        }
        (output / "summary.json").write_text(json.dumps(summaries, indent=2) + "\n")
    print(json.dumps(summaries, sort_keys=True))


if __name__ == "__main__":
    main()
