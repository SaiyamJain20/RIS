"""Pinned, ordered isolated controls. This API cannot authorize an F run.

Caller supplies a closed, disposable snapshot, exact input inventory and public
environment. This is process isolation, not a sandbox against malicious commands.
Snapshot completeness/provenance and execution FREEZE/ACK verification belong to
the future coordinator. No services or cases are started by the recipe builder.
"""

import copy
import json
import math
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import time

from evaluation.manifests import canonical_hash, now, sha256


_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,79}\Z")


def _inside(root, relative):
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Snapshot path must be relative without parent traversal")
    result = root / path
    if not result.resolve().is_relative_to(root):
        raise ValueError("Snapshot path escapes root")
    return result


def _inventory(root, roots):
    files = {}
    for name in roots:
        path = _inside(root, name)
        if path.is_symlink():
            raise ValueError(f"Source root symlink is not a closed input: {name}")
        if not path.exists():
            raise ValueError(f"Missing source root: {name}")
        candidates = [path] if path.is_file() else path.rglob("*")
        for item in candidates:
            rel = item.relative_to(root)
            # Only known generated outputs are excluded. Everything else in the
            # selected roots (including untracked files) participates in the pin.
            if any(part in {"__pycache__", ".pytest_cache"} for part in rel.parts):
                continue
            if rel.parts[:2] in {("ledger", "out"), ("ledger", "cache")}:
                continue
            if item.is_symlink():
                raise ValueError(f"Source symlink is not a closed input: {rel}")
            if item.is_file():
                files[rel.as_posix()] = sha256(item)
    return dict(sorted(files.items()))


def _validate(recipe, output):
    if recipe.get("schemaVersion") != "hmbc-f-baselines/v1":
        raise ValueError("Unknown baseline recipe schema")
    raw_root = Path(recipe["workspace"])
    if not raw_root.is_absolute() or not raw_root.is_dir():
        raise ValueError("Workspace must be an existing absolute snapshot directory")
    root = raw_root.resolve()
    if output.resolve().is_relative_to(root):
        raise ValueError("Evidence output must be outside the snapshot")
    if not recipe["sourceRoots"] or not recipe["sourceFiles"]:
        raise ValueError("Nonempty closed source inventory required")
    for name, digest in recipe["sourceFiles"].items():
        _inside(root, name)
        if not _SHA.fullmatch(digest):
            raise ValueError("Source pin must be a full SHA-256")
    for name in recipe["sourceRoots"]:
        _inside(root, name)
    for tool in recipe["tools"].values():
        # Do NOT resolve: venv launch semantics depend on the lexical path.
        if not Path(tool["path"]).is_absolute() or not _SHA.fullmatch(tool["sha256"]):
            raise ValueError("Tool requires an absolute lexical path and exact hash")
    for name, digest in recipe["runtimeFiles"].items():
        if not Path(name).is_absolute() or not _SHA.fullmatch(digest):
            raise ValueError("Runtime file requires an absolute path and exact hash")
    if not isinstance(recipe["environment"], dict) or any(
        not isinstance(k, str) or not isinstance(v, str) or "=" in k or not k or "\0" in k + v
        for k, v in recipe["environment"].items()
    ):
        raise ValueError("An explicit process environment is required")
    commands = recipe["commands"]
    if not commands or len({row["id"] for row in commands}) != len(commands):
        raise ValueError("Commands must be nonempty with unique IDs")
    for row in commands:
        if not _ID.fullmatch(row["id"]) or row["tool"] not in recipe["tools"]:
            raise ValueError("Command ID/tool is invalid")
        if not _inside(root, row["cwd"]).is_dir():
            raise ValueError("Command cwd is not an existing snapshot directory")
        timeout = row["timeoutSeconds"]
        if isinstance(timeout, bool) or not math.isfinite(timeout) or not 0 < timeout <= 3600:
            raise ValueError("Finite positive timeout <=3600s required")
        if not isinstance(row["maxOutputBytes"], int) or row["maxOutputBytes"] <= 0:
            raise ValueError("Positive output budget required")
        if type(row["expectedExitCode"]) is not int or not 0 <= row["expectedExitCode"] <= 255:
            raise ValueError("Expected exit code must be 0..255")
        if not isinstance(row["args"], list) or any(not isinstance(v, str) or "\0" in v for v in row["args"]):
            raise ValueError("Command arguments must be strings")
        for value in row["args"]:
            if value.startswith("@OUTPUT@/"):
                _inside(output.resolve(), value[len("@OUTPUT@/"):])
        if not row["requiredOutput"] or any(not isinstance(v, str) or not v for v in row["requiredOutput"]):
            raise ValueError("Nonempty output assertions required")
    return root


def _check_pins(recipe, root):
    if _inventory(root, recipe["sourceRoots"]) != recipe["sourceFiles"]:
        raise ValueError("Source inventory pin mismatch")
    for name, tool in recipe["tools"].items():
        if sha256(tool["path"]) != tool["sha256"]:
            raise ValueError(f"Tool pin mismatch: {name}")
    for name, expected in recipe["runtimeFiles"].items():
        if sha256(name) != expected:
            raise ValueError(f"Runtime pin mismatch: {name}")


def _stop_group(process):
    # The direct child has not been reaped. Its PID cannot be reused while we
    # terminate the fresh process group we own, including normal-exit stragglers.
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass
        if sig == signal.SIGTERM:
            time.sleep(.05)
    process.wait(timeout=5)


def _execute(row, recipe, root, output):
    stdout = output / (row["id"] + ".stdout")
    stderr = output / (row["id"] + ".stderr")
    args = [str(output / value[len("@OUTPUT@/"):]) if value.startswith("@OUTPUT@/") else value
            for value in row["args"]]
    argv = [recipe["tools"][row["tool"]]["path"], *args]
    result = {"id": row["id"], "status": "FAIL", "argv": argv,
              "cwd": str(_inside(root, row["cwd"])), "startedAt": now(),
              "environmentSha256": canonical_hash(recipe["environment"]),
              "timedOut": False, "outputLimitExceeded": False, "reaped": False,
              "pid": None, "processGroup": None, "exitCode": None}
    began = time.monotonic()
    process = None
    with stdout.open("xb") as out, stderr.open("xb") as err:
        try:
            process = subprocess.Popen(argv, cwd=result["cwd"], env=recipe["environment"],
                                       stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                       start_new_session=True)
            result["pid"] = result["processGroup"] = process.pid
            while True:
                # WNOWAIT prevents premature reaping/PID reuse before cleanup.
                exited = os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
                result["outputLimitExceeded"] = stdout.stat().st_size + stderr.stat().st_size > row["maxOutputBytes"]
                if exited is not None or result["outputLimitExceeded"]:
                    break
                if time.monotonic() - began >= row["timeoutSeconds"]:
                    result["timedOut"] = True
                    break
                time.sleep(.01)
        except OSError as error:
            result["error"] = str(error)
        finally:
            if process is not None:
                _stop_group(process)
                result["exitCode"] = process.returncode
                result["reaped"] = True
    result.update(endedAt=now(), elapsedSeconds=time.monotonic() - began,
                  stdoutSha256=sha256(stdout), stderrSha256=sha256(stderr))
    # A budget is a monitored stop threshold, not a strict disk quota: a child
    # may overshoot between polls. Never accept that output as a successful run.
    result["outputLimitExceeded"] |= stdout.stat().st_size + stderr.stat().st_size > row["maxOutputBytes"]
    if not result["outputLimitExceeded"]:
        content = stdout.read_bytes() + stderr.read_bytes()
        result["missingOutput"] = [s for s in row["requiredOutput"] if s.encode() not in content]
    else:
        result["missingOutput"] = list(row["requiredOutput"])
    if (result["exitCode"] == row["expectedExitCode"] and not result["timedOut"]
            and not result["outputLimitExceeded"] and not result["missingOutput"]
            and "error" not in result):
        result["status"] = "PASS"
    return result


def run_baselines(recipe, output, *, expected_recipe_sha256):
    """Run exact local commands only; PASS means this recipe's controls passed.

    The caller must already have execution authority. This low-level API does
    not parse or accept ACKs and cannot move a research gate or start case work.
    Synthetic tests can exercise it independently of the execution FREEZE.
    """
    if os.name != "posix" or not hasattr(os, "WNOWAIT"):
        raise ValueError("Owned process cleanup requires POSIX waitid/WNOWAIT")
    recipe = copy.deepcopy(recipe)
    output = Path(output).absolute()
    root = _validate(recipe, output)
    if not _SHA.fullmatch(expected_recipe_sha256):
        raise ValueError("Exact recipe SHA-256 required")
    output.mkdir(parents=True, exist_ok=False)
    result = {"schemaVersion": "hmbc-f-baseline-result/v1", "startedAt": now(),
              "recipeSha256": canonical_hash(recipe), "status": "BLOCKED",
              "executionAuthorized": False, "gateF": "NOT_RUN", "commands": [], "blockers": [],
              "inputPins": {key: recipe[key] for key in ("workspace", "sourceRoots", "sourceFiles", "runtimeFiles", "tools")},
              "expectedCommands": recipe["commands"],
              "environmentSha256": canonical_hash(recipe["environment"])}
    try:
        if result["recipeSha256"] != expected_recipe_sha256:
            raise ValueError("Recipe pin mismatch")
        if ("status" in recipe or "authorizesExecution" in recipe) and (
                recipe.get("status") != "FROZEN" or recipe.get("authorizesExecution") is not True):
            raise ValueError("DRAFT recipe does not authorize owner baseline execution")
        if recipe.get("blockers"):
            raise ValueError("Recipe still declares execution blockers")
        _check_pins(recipe, root)
    except (OSError, ValueError) as error:
        result["blockers"].append(str(error))
    if not result["blockers"]:
        result["status"] = "PASS"
        for row in recipe["commands"]:
            if result["status"] != "PASS":
                result["commands"].append({"id": row["id"], "status": "NOT_RUN"})
                continue
            try:
                _check_pins(recipe, root)
                completed = _execute(row, recipe, root, output)
                result["commands"].append(completed)
                _check_pins(recipe, root)
            except (OSError, ValueError) as error:
                if not result["commands"] or result["commands"][-1]["id"] != row["id"]:
                    completed = {"id": row["id"], "status": "FAIL"}
                    result["commands"].append(completed)
                completed.update(status="FAIL", error=str(error))
            if completed["status"] != "PASS":
                result["status"] = "FAIL"
    result["endedAt"] = now()
    (output / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def build_owner_recipe(*, workspace, source_roots, source_files, tools, runtime_files,
                       environment, tlc_jar):
    """Build, never execute, proposed stage-3 commands for review/FREEZE.

    Caller must pin the closed snapshot's ledger/protocol/interfaces/models and
    dependency inputs plus interpreter environment/runtime files. The supplied
    hashes are expected pins, never inferred permission or owner provenance.
    """
    jar = str(Path(tlc_jar).absolute())
    if jar not in runtime_files or not {"python", "forge", "solc", "java"} <= tools.keys():
        raise ValueError("Python/Forge/solc/Java and pinned TLC jar required")
    port_match = re.fullmatch(r"([0-9]+)-([0-9]+)", environment.get("HMBC_TEST_PORT_RANGE", ""))
    forge_dir = str(Path(tools["forge"]["path"]).parent)
    if (not port_match or not 1024 <= int(port_match[1]) < int(port_match[2]) <= 65535
            or environment.get("HMBC_FOUNDRY_DIR") != forge_dir
            or shutil.which(Path(tools["forge"]["path"]).name, path=environment.get("PATH", "")) != tools["forge"]["path"]):
        raise ValueError("Explicit Foundry PATH/directory and port-range environment required")
    def cmd(name, tool, args, code, output, timeout):
        return {"id": name, "tool": tool, "args": args, "cwd": ".",
                "expectedExitCode": code, "requiredOutput": output,
                "timeoutSeconds": timeout, "maxOutputBytes": 64 * 1024 * 1024}
    commands = [
        cmd("ledger-tests", "forge", ["test", "--root", "ledger", "--offline", "--use", tools["solc"]["path"]],
            0, ["316 tests passed, 0 failed, 0 skipped"], 600),
        cmd("ledger-mutants", "python", ["-I", "ledger/tools/check_mutants.py"],
            0, ["ALL MUTANTS DETECTED BY THEIR EXPECTED TESTS"], 600),
        cmd("protocol-tests", "python", ["-m", "pytest", "protocol/tests", "-c", "protocol/pytest.ini",
            "--rootdir", "protocol", "-p", "no:cacheprovider", "-rs", "-q"],
            0, ["3226 passed, 201 skipped"], 3600),
    ]
    for suffix, code in [("", 0), ("-f0", 0), ("-weak-q2", 12), ("-f2", 12), ("-no-persist", 12)]:
        name = "tlc" + (suffix or "-f1")
        commands.append(cmd(name, "java", ["-cp", jar, "tlc2.TLC", "-metadir", "@OUTPUT@/" + name,
            "-config", f"evaluation/models/f/DecisionQuorum{suffix}.cfg", "evaluation/models/f/DecisionQuorum.tla"],
            code, ["Agreement is violated" if code else "Model checking completed. No error has been found."], 120))
    return copy.deepcopy({"schemaVersion": "hmbc-f-baselines/v1", "status": "DRAFT",
        "authorizesExecution": False, "workspace": str(workspace),
        "sourceRoots": source_roots, "sourceFiles": source_files, "tools": tools,
        "runtimeFiles": runtime_files, "environment": environment, "commands": commands})
