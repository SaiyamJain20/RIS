#!/usr/bin/env python3
"""Export the six HMBC contracts' ABIs from Forge build artifacts (agent 1, ledger).

Usage (from the repository root, after `forge build --root ledger`):
    python3 -I ledger/tools/export_abi.py

Writes ledger/exports/abi/<Contract>.json (the compiler's ABI, unmodified) and
ledger/exports/abi/manifest.json with compiler settings, source/ABI SHA-256 and runtime sizes.
Standard library only. Never hand-edit an exported ABI; re-run this script instead.
"""
import hashlib
import json
import pathlib
import sys

CONTRACTS = ["LSC", "TMSC", "RSC", "PSC", "ACSC", "KSSC"]
LEDGER = pathlib.Path(__file__).resolve().parent.parent


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    out_dir = LEDGER / "exports" / "abi"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schemaVersion": "hmbc-ledger-abi/v0",
        "interfaceVersion": "v0 proposed",
        "producer": "agent-1 ledger/tools/export_abi.py",
        "contracts": {},
        "sources": {},
    }
    compiler = None
    for name in CONTRACTS:
        artifact_path = LEDGER / "out" / f"{name}.sol" / f"{name}.json"
        if not artifact_path.exists():
            print(f"missing build artifact {artifact_path}; run forge build --root ledger", file=sys.stderr)
            return 2
        artifact = json.loads(artifact_path.read_text())
        metadata = artifact.get("rawMetadata") or artifact.get("metadata")
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        settings = metadata["settings"]
        this_compiler = {
            "solc": metadata["compiler"]["version"],
            "evmVersion": settings.get("evmVersion"),
            "optimizer": settings.get("optimizer"),
            "viaIR": settings.get("viaIR", False),
        }
        if compiler is None:
            compiler = this_compiler
        elif compiler != this_compiler:
            print(f"compiler settings differ for {name}", file=sys.stderr)
            return 3
        abi_text = json.dumps(artifact["abi"], indent=2, sort_keys=False) + "\n"
        abi_path = out_dir / f"{name}.json"
        abi_path.write_text(abi_text)
        runtime = artifact["deployedBytecode"]["object"]
        runtime_hex = runtime[2:] if runtime.startswith("0x") else runtime
        manifest["contracts"][name] = {
            "abi": f"exports/abi/{name}.json",
            "abiSha256": sha256(abi_path),
            "runtimeBytes": len(runtime_hex) // 2,
            "runtimeSha256": hashlib.sha256(bytes.fromhex(runtime_hex)).hexdigest(),
            "source": f"src/{name}.sol",
        }
    for src in sorted((LEDGER / "src").rglob("*.sol")):
        manifest["sources"][str(src.relative_to(LEDGER))] = sha256(src)
    manifest["foundryTomlSha256"] = sha256(LEDGER / "foundry.toml")
    manifest["compiler"] = compiler
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: v["abiSha256"] for k, v in manifest["contracts"].items()}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
