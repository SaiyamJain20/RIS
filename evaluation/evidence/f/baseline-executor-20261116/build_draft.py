"""Build a review artifact from Git blobs and tool bytes; execute no baselines."""

import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from evaluation.f_baselines import build_owner_recipe
from evaluation.manifests import canonical_hash, sha256


def main():
    root = Path(__file__).resolve().parents[4]
    evidence = Path(__file__).resolve().parent
    parent = "0aac1cc0eb5000efa097e26195b0759f814f3060"
    sources = [
        ("85c59f588de58a8ff5e87b9fe6f630c9d8c43642", ["ledger"]),
        ("73fb2ce42d513ad3faf384500609e76d54aedbfb", ["protocol"]),
        (parent, ["interfaces", "evaluation/models/f", "pyproject.toml", "uv.lock"]),
    ]
    expected = {}
    provenance = []
    for commit, paths in sources:
        archive = subprocess.check_output(["git", "archive", commit, *paths], cwd=root)
        with tarfile.open(fileobj=io.BytesIO(archive)) as handle:
            for item in handle.getmembers():
                if item.isdir(): continue
                if not item.isfile(): raise ValueError("Source archive contains non-regular input")
                expected[item.name] = hashlib.sha256(handle.extractfile(item).read()).hexdigest()
        provenance.append({"commit": commit, "paths": paths,
                           "archiveSha256": hashlib.sha256(archive).hexdigest()})
    toolchain = json.loads((root / "evaluation/toolchain.json").read_text())
    tools = {**toolchain["foundry"]["binaryPaths"], "solc": toolchain["solc"]}
    tools = {name: {"path": data["path"], "sha256": data["sha256"]} for name, data in tools.items()}
    tools["python"] = {"path": sys.executable, "sha256": sha256(sys.executable)}
    for name in ("java", "git", "bash"):
        executable = shutil.which(name)
        if not executable: raise ValueError(f"Missing {name}")
        tools[name] = {"path": executable, "sha256": sha256(executable)}
    for name, data in tools.items():
        assert sha256(data["path"]) == data["sha256"], name
    jar = Path.home() / ".local/share/hmbc-tools/tlaplus-v1.7.4/tla2tools.jar"
    assert sha256(jar) == "936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88"
    runtime_files = {str(path): sha256(path) for path in (jar, root / ".venv/pyvenv.cfg", root / "uv.lock")}
    dirs = list(dict.fromkeys(str(Path(data["path"]).parent) for data in tools.values()))
    env = {"PATH": ":".join(dirs), "HOME": str(Path.home()),
           "HMBC_FOUNDRY_DIR": str(Path(tools["forge"]["path"]).parent),
           "HMBC_TEST_PORT_RANGE": "18545-18599", "FOUNDRY_SOLC": tools["solc"]["path"],
           "FOUNDRY_OFFLINE": "true", "PYTHONDONTWRITEBYTECODE": "1", "GIT_DIR": str(root / ".git")}
    recipe = build_owner_recipe(workspace=root / "evaluation/runs/f-stage3-proposed/snapshot",
        source_roots=[name for _, paths in sources for name in paths], source_files=dict(sorted(expected.items())),
        tools=tools, runtime_files=runtime_files, environment=env, tlc_jar=jar)
    recipe.update(status="DRAFT", authorizesExecution=False, sourceProvenance=provenance,
        blockers=["Exact execution FREEZE and owner ACKs absent; DO NOT EXECUTE",
                  "Snapshot not materialized or verified on disk; pinned Git objects must remain reachable for protocol test archives",
                  "Installed Python distributions, Java runtime libraries and transitive executable/configuration closure still need inventory",
                  "Owner recipes are content-checked only, never executed by this implementation receipt",
                  "Protocol live-binding tests can choose OS ephemeral ports beyond HMBC_TEST_PORT_RANGE (S2-0026 section 9)"])
    (evidence / "owner-recipe-draft.json").write_text(json.dumps(recipe, indent=2) + "\n")
    print(json.dumps({"sourceFiles": len(expected), "commands": len(recipe["commands"]),
                      "recipeSha256": canonical_hash(recipe), "status": "DRAFT", "executed": False}))


if __name__ == "__main__":
    main()
