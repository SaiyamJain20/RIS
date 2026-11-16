"""Synthetic process controls; no owner package or F case runs in this file."""

import importlib
import json
from pathlib import Path
import subprocess
import sys
import time

import pytest

from evaluation.manifests import canonical_hash, sha256


@pytest.fixture
def api():
    try:
        return importlib.import_module("evaluation.f_baselines")
    except ModuleNotFoundError:
        pytest.fail("stage-3 baseline executor is not implemented")


@pytest.fixture
def recipe(tmp_path):
    root = tmp_path / "snapshot"
    root.mkdir()
    (root / "fixture.txt").write_text("synthetic source\n")
    return {
        "schemaVersion": "hmbc-f-baselines/v1",
        "workspace": str(root),
        "sourceRoots": ["fixture.txt"],
        "sourceFiles": {"fixture.txt": sha256(root / "fixture.txt")},
        "runtimeFiles": {},
        "tools": {"python": {"path": sys.executable, "sha256": sha256(sys.executable)}},
        "environment": {"CONTROL": "public-fixture"},
        "commands": [command("first", 'import sys; print("ok"); print("err", file=sys.stderr)')],
    }


def command(name, script, *, timeout=2, exit_code=0, required="ok"):
    return {"id": name, "tool": "python", "args": ["-c", script], "cwd": ".",
            "timeoutSeconds": timeout, "expectedExitCode": exit_code,
            "requiredOutput": [required], "maxOutputBytes": 1024 * 1024}


def run(api, recipe, tmp_path):
    return api.run_baselines(recipe, tmp_path / "result", expected_recipe_sha256=canonical_hash(recipe))


def test_records_separate_byte_streams_exit_environment_and_recipe(api, recipe, tmp_path):
    result = run(api, recipe, tmp_path)
    row = result["commands"][0]
    assert result["status"] == "PASS" and row["status"] == "PASS"
    assert row["exitCode"] == 0 and not row["timedOut"]
    assert (tmp_path / "result/first.stdout").read_bytes() == b"ok\n"
    assert (tmp_path / "result/first.stderr").read_bytes() == b"err\n"
    assert row["stdoutSha256"] == sha256(tmp_path / "result/first.stdout")
    assert row["stderrSha256"] == sha256(tmp_path / "result/first.stderr")
    assert row["environmentSha256"] == canonical_hash(recipe["environment"])
    assert result["recipeSha256"] == canonical_hash(recipe)
    assert result["executionAuthorized"] is False and result["gateF"] == "NOT_RUN"
    assert json.loads((tmp_path / "result/manifest.json").read_text()) == result


def test_order_and_expected_counterexample_exit(api, recipe, tmp_path):
    recipe["commands"] = [command("control", 'from pathlib import Path; Path("order").write_text("1"); print("ok")'),
                          command("counterexample", 'from pathlib import Path; import sys; assert Path("order").read_text()=="1"; print("Agreement violated"); sys.exit(12)', exit_code=12, required="Agreement violated")]
    result = run(api, recipe, tmp_path)
    assert [row["status"] for row in result["commands"]] == ["PASS", "PASS"]
    assert result["commands"][1]["exitCode"] == 12


@pytest.mark.parametrize("mutation", ["recipe", "source", "tool", "runtime", "extra-source"])
def test_pin_mismatches_block_before_any_command(api, recipe, tmp_path, mutation):
    root = Path(recipe["workspace"])
    recipe["sourceRoots"] = ["."]
    recipe["runtimeFiles"] = {str(tmp_path / "runtime.cfg"): "0" * 64}
    (tmp_path / "runtime.cfg").write_text("runtime")
    recipe["runtimeFiles"][str(tmp_path / "runtime.cfg")] = sha256(tmp_path / "runtime.cfg")
    expected = canonical_hash(recipe)
    if mutation == "recipe": recipe["commands"][0]["timeoutSeconds"] = 3
    if mutation == "source": (root / "fixture.txt").write_text("changed")
    if mutation == "tool": recipe["tools"]["python"]["sha256"] = "0" * 64
    if mutation == "runtime": (tmp_path / "runtime.cfg").write_text("changed")
    if mutation == "extra-source": (root / "injected.py").write_text("# unexpected import")
    if mutation == "tool": expected = canonical_hash(recipe)
    result = api.run_baselines(recipe, tmp_path / "result", expected_recipe_sha256=expected)
    assert result["status"] == "BLOCKED"
    assert result["commands"] == [] and result["blockers"]
    assert not list((tmp_path / "result").glob("*.stdout"))


@pytest.mark.parametrize("first", [command("bad-exit", 'import sys; print("ok"); sys.exit(4)'),
                                  command("missing-output", 'print("wrong")')])
def test_failure_blocks_later_command(api, recipe, tmp_path, first):
    recipe["commands"] = [first, command("later", 'print("ok")')]
    result = run(api, recipe, tmp_path)
    assert result["status"] == "FAIL"
    assert [row["status"] for row in result["commands"]] == ["FAIL", "NOT_RUN"]
    assert not (tmp_path / "result/later.stdout").exists()


def test_source_changed_by_successful_command_invalidates_result(api, recipe, tmp_path):
    recipe["commands"] = [command("change", 'from pathlib import Path; Path("fixture.txt").write_text("changed"); print("ok")'), command("later", 'print("ok")')]
    result = run(api, recipe, tmp_path)
    assert result["status"] == "FAIL"
    assert result["commands"][0]["status"] == "FAIL"
    assert "pin" in result["commands"][0]["error"].lower()
    assert result["commands"][1]["status"] == "NOT_RUN"


@pytest.mark.parametrize("exit_parent", [False, True])
def test_timeout_or_normal_exit_cleans_owned_descendant(api, recipe, tmp_path, exit_parent):
    script = ('import subprocess,sys,time; from pathlib import Path; '
              'p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"]); '
              'Path("descendant.pid").write_text(str(p.pid)); print("ok",flush=True); ' +
              ('sys.exit(0)' if exit_parent else 'time.sleep(30)'))
    recipe["commands"] = [command("child", script, timeout=.4)]
    began = time.monotonic()
    result = run(api, recipe, tmp_path)
    assert time.monotonic() - began < 5
    row = result["commands"][0]
    assert row["timedOut"] is (not exit_parent)
    assert row["status"] == ("PASS" if exit_parent else "FAIL")
    child = int((Path(recipe["workspace"]) / "descendant.pid").read_text())
    state_path = Path(f"/proc/{child}/stat")
    assert not state_path.exists() or state_path.read_text().split(") ")[1][0] == "Z"
    assert row["pid"] == row["processGroup"] and row["reaped"] is True


def test_output_limit_fails_closed(api, recipe, tmp_path):
    recipe["commands"] = [command("flood", 'import os,time; os.write(1,b"x"*10000); time.sleep(30)')]
    recipe["commands"][0]["maxOutputBytes"] = 1024
    result = run(api, recipe, tmp_path)
    assert result["status"] == "FAIL" and result["commands"][0]["outputLimitExceeded"]


@pytest.mark.parametrize("mutation", ["cwd", "tool-path", "nan-timeout", "empty-commands", "duplicate-id", "source-prefix", "output-in-source"])
def test_malformed_recipe_never_launches(api, recipe, tmp_path, mutation):
    output = tmp_path / "result"
    if mutation == "cwd": recipe["commands"][0]["cwd"] = "../"
    if mutation == "tool-path": recipe["tools"]["python"]["path"] = "python3"
    if mutation == "nan-timeout": recipe["commands"][0]["timeoutSeconds"] = float("nan")
    if mutation == "empty-commands": recipe["commands"] = []
    if mutation == "duplicate-id": recipe["commands"] *= 2
    if mutation == "source-prefix": recipe["sourceFiles"]["fixture.txt"] = "abc"
    if mutation == "output-in-source": output = Path(recipe["workspace"]) / "evidence"
    with pytest.raises(ValueError):
        api.run_baselines(recipe, output, expected_recipe_sha256=canonical_hash(recipe))
    assert not output.exists()


def test_preserves_lexical_venv_interpreter_and_explicit_environment(api, recipe, tmp_path):
    # Resolving this symlink loses pyvenv.cfg lookup; the path is part of the recipe.
    bindir = tmp_path / "venv/bin"
    bindir.mkdir(parents=True)
    interpreter = bindir / "python"
    interpreter.symlink_to(sys.executable)
    recipe["tools"]["python"]["path"] = str(interpreter)
    recipe["commands"] = [command("lexical", 'import os,sys; print(sys.executable); print(os.environ.get("CONTROL")); assert "HOME" not in os.environ', required=str(interpreter))]
    result = run(api, recipe, tmp_path)
    assert result["status"] == "PASS"
    assert result["commands"][0]["argv"][0] == str(interpreter)


def test_owner_recipe_uses_explicit_pytest_config_toolchain_and_tlc_controls(api, recipe, tmp_path):
    tools = {name: recipe["tools"]["python"] for name in ("python", "forge", "solc", "java")}
    jar = tmp_path / "tlc.jar"
    jar.write_bytes(b"synthetic jar; never executed")
    built = api.build_owner_recipe(workspace=Path(recipe["workspace"]),
        source_roots=["fixture.txt"], source_files=recipe["sourceFiles"],
        tools=tools, runtime_files={str(jar): sha256(jar)},
        environment={"PATH": str(Path(sys.executable).parent),
                     "HMBC_FOUNDRY_DIR": str(Path(sys.executable).parent),
                     "HMBC_TEST_PORT_RANGE": "18545-18599"}, tlc_jar=jar)
    commands = built["commands"]
    assert [row["id"] for row in commands[:3]] == ["ledger-tests", "ledger-mutants", "protocol-tests"]
    assert commands[0]["args"][:3] == ["test", "--root", "ledger"]
    assert "--use" in commands[0]["args"] and "--offline" in commands[0]["args"]
    assert commands[1]["args"] == ["-I", "ledger/tools/check_mutants.py"]
    assert commands[2]["args"] == ["-m", "pytest", "protocol/tests", "-c", "protocol/pytest.ini", "--rootdir", "protocol", "-p", "no:cacheprovider", "-rs", "-q"]
    assert [row["expectedExitCode"] for row in commands[3:]] == [0, 0, 12, 12, 12]
    assert all(row["args"][0:3] == ["-cp", str(jar), "tlc2.TLC"] for row in commands[3:])
    assert all("-metadir" in row["args"] for row in commands[3:])
    assert all("Agreement is violated" in row["requiredOutput"] for row in commands[5:])
    assert commands[1]["requiredOutput"] == ["ALL MUTANTS DETECTED BY THEIR EXPECTED TESTS"]
    assert built["status"] == "DRAFT" and built["authorizesExecution"] is False


def test_owner_recipe_refuses_missing_foundry_and_port_environment(api, recipe, tmp_path):
    jar = tmp_path / "jar"
    jar.write_bytes(b"synthetic")
    with pytest.raises(ValueError, match="environment"):
        api.build_owner_recipe(workspace=Path(recipe["workspace"]), source_roots=["fixture.txt"],
            source_files=recipe["sourceFiles"],
            tools={name: recipe["tools"]["python"] for name in ("python", "forge", "solc", "java")},
            runtime_files={str(jar): sha256(jar)}, environment={}, tlc_jar=jar)


def test_existing_output_is_never_overwritten(api, recipe, tmp_path):
    output = tmp_path / "result"
    output.mkdir()
    (output / "manifest.json").write_text("previous evidence")
    with pytest.raises(FileExistsError): run(api, recipe, tmp_path)
    assert (output / "manifest.json").read_text() == "previous evidence"


def test_launch_error_retains_failure_and_blocks_later_commands(api, recipe, tmp_path):
    bad_tool = tmp_path / "not-executable"
    bad_tool.write_text("not an executable")
    recipe["tools"]["python"] = {"path": str(bad_tool), "sha256": sha256(bad_tool)}
    recipe["commands"].append(command("later", 'print("ok")'))
    result = run(api, recipe, tmp_path)
    assert result["status"] == "FAIL"
    first, later = result["commands"]
    assert first["exitCode"] is None and first["pid"] is None and first["error"]
    assert first["stdoutSha256"] == sha256(tmp_path / "result/first.stdout")
    assert later["status"] == "NOT_RUN"


@pytest.mark.parametrize("kind", ["runtime", "tool"])
def test_post_command_runtime_and_tool_changes_invalidate_success(api, recipe, tmp_path, kind):
    dependency = tmp_path / "dependency"
    dependency.write_text("original")
    if kind == "runtime": recipe["runtimeFiles"][str(dependency)] = sha256(dependency)
    else: recipe["tools"]["unused"] = {"path": str(dependency), "sha256": sha256(dependency)}
    recipe["commands"] = [command("change", f'from pathlib import Path; Path({str(dependency)!r}).write_text("changed"); print("ok")')]
    result = run(api, recipe, tmp_path)
    assert result["status"] == "FAIL"
    assert "pin mismatch" in result["commands"][0]["error"]


def test_timeout_leaves_unrelated_process_alive(api, recipe, tmp_path):
    unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        recipe["commands"] = [command("timeout", 'import time; time.sleep(30)', timeout=.1)]
        result = run(api, recipe, tmp_path)
        assert result["commands"][0]["timedOut"]
        assert unrelated.poll() is None
    finally:
        unrelated.terminate()
        unrelated.wait(timeout=5)


def test_source_symlink_is_not_accepted_as_closed_inventory(api, recipe, tmp_path):
    root = Path(recipe["workspace"])
    (root / "alias").symlink_to(root / "fixture.txt")
    recipe["sourceRoots"].append("alias")
    result = run(api, recipe, tmp_path)
    assert result["status"] == "BLOCKED" and result["commands"] == []
    assert "symlink" in result["blockers"][0]


def test_output_argument_cannot_escape_evidence_directory(api, recipe, tmp_path):
    recipe["commands"][0]["args"].append("@OUTPUT@/../outside")
    with pytest.raises(ValueError, match="traversal"):
        run(api, recipe, tmp_path)
    assert not (tmp_path / "result").exists()


def test_declared_draft_recipe_cannot_execute_even_with_matching_hash(api, recipe, tmp_path):
    recipe.update(status="DRAFT", authorizesExecution=False)
    result = run(api, recipe, tmp_path)
    assert result["status"] == "BLOCKED" and result["commands"] == []
    assert "DRAFT" in result["blockers"][0]
