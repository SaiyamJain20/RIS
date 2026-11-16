#!/usr/bin/env python3
"""Export the HMBC contracts' ABIs from Forge build artifacts (agent 1, ledger).

Usage (from the repository root, after `forge build --root ledger`):
    python3 -I ledger/tools/export_abi.py                # default (interface v1) export, unchanged shape
    python3 -I ledger/tools/export_abi.py --successor    # interface-v2 export (A-F1, interfaces/v2)

Default: writes ledger/exports/abi/<Contract>.json (the compiler's ABI, unmodified) for the six E
contracts and ledger/exports/abi/manifest.json with compiler settings, source/ABI SHA-256 and runtime
sizes. Its source map is the frozen v1 set (closed at ten files); compile inputs outside that set are
reported on stderr, not hidden.

--successor: also writes Governance.json and ledger/exports/abi/manifest-v2.json for the seven
runtimes, each with decimal-string `runtimeBytes`, `immutableReferences` ([{start, length}], decimal
strings, sorted, disjoint, length 32, in bounds) and `immutableRefsSha256` (SHA-256 of the canonical
JSON of that object list), plus the twelve-file F source map (design 2.2 section 8, interfaces/v2).
Standard library only. Never hand-edit an exported ABI; re-run this script instead.
"""
import hashlib
import json
import pathlib
import sys

CONTRACTS = ["LSC", "TMSC", "RSC", "PSC", "ACSC", "KSSC"]
F_CONTRACTS = CONTRACTS + ["Governance"]
# interfaces/v1 LedgerSourceHashes (also the v2 E carrier) is closed at exactly these files.
V1_SOURCES = [
    "src/ACSC.sol", "src/DecisionVerifier.sol", "src/KSSC.sol", "src/LSC.sol", "src/PSC.sol", "src/RSC.sol",
    "src/TMSC.sol", "src/lib/Bootstrapped.sol", "src/lib/SigLib.sol", "src/types/ProtocolTypes.sol",
]
# interfaces/v2 LedgerSourceHashesF.
F_SOURCES = V1_SOURCES + ["src/Governance.sol", "src/interfaces/IPolicyVersion.sol"]
LEDGER = pathlib.Path(__file__).resolve().parent.parent


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def immutable_ranges(deployed: dict, runtime_bytes: int):
    """The artifact's immutable ranges as the v2 object list, or None if they break the export rule."""
    ranges = sorted((r["start"], r["length"]) for refs in deployed.get("immutableReferences", {}).values() for r in refs)
    end = 0
    for start, length in ranges:
        if start < end or length != 32 or start + length > runtime_bytes:
            return None
        end = start + length
    return [{"start": str(s), "length": str(n)} for s, n in ranges]


def main(argv) -> int:
    successor = argv[1:] == ["--successor"]
    if argv[1:] and not successor:
        print(__doc__, file=sys.stderr)
        return 2
    out_dir = LEDGER / "exports" / "abi"
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schemaVersion": "hmbc-ledger-abi/v0",
        "interfaceVersion": "v1",
        "producer": "agent-1 ledger/tools/export_abi.py",
        "contracts": {},
        "sources": {},
    }
    v2 = {
        "schemaVersion": "hmbc-ledger-abi/v2",
        "interfaceVersion": "v2",
        "producer": "agent-1 ledger/tools/export_abi.py --successor",
        "contracts": {},
        "sources": {},
    }
    compiler = None
    for name in F_CONTRACTS if successor else CONTRACTS:
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
        runtime_bytes = len(runtime_hex) // 2
        entry = {
            "abi": f"exports/abi/{name}.json",
            "abiSha256": sha256(abi_path),
            "runtimeBytes": runtime_bytes,
            "runtimeSha256": hashlib.sha256(bytes.fromhex(runtime_hex)).hexdigest(),
            "source": f"src/{name}.sol",
        }
        if name in CONTRACTS:
            manifest["contracts"][name] = entry
        if successor:
            refs = immutable_ranges(artifact["deployedBytecode"], runtime_bytes)
            if refs is None:
                print(f"{name}: immutable ranges break the export rule (sorted, disjoint, 32 bytes, in bounds)",
                      file=sys.stderr)
                return 4
            v2["contracts"][name] = dict(entry, runtimeBytes=str(runtime_bytes), immutableReferences=refs,
                                         immutableRefsSha256=hashlib.sha256(canonical(refs)).hexdigest())
    all_sources = sorted(str(p.relative_to(LEDGER)) for p in (LEDGER / "src").rglob("*.sol"))
    for rel in V1_SOURCES:
        manifest["sources"][rel] = sha256(LEDGER / rel)
    outside = [rel for rel in all_sources if rel not in V1_SOURCES]
    if outside:
        print(f"note: compile inputs outside the closed v1 source map: {outside}", file=sys.stderr)
    manifest["foundryTomlSha256"] = sha256(LEDGER / "foundry.toml")
    manifest["compiler"] = compiler
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if successor:
        missing = [rel for rel in F_SOURCES if rel not in all_sources]
        extra = [rel for rel in all_sources if rel not in F_SOURCES]
        if missing or extra:
            print(f"F source map mismatch: missing={missing} extra={extra}", file=sys.stderr)
            return 5
        for rel in F_SOURCES:
            v2["sources"][rel] = sha256(LEDGER / rel)
        v2["foundryTomlSha256"] = manifest["foundryTomlSha256"]
        v2["compiler"] = compiler
        (out_dir / "manifest-v2.json").write_text(json.dumps(v2, indent=2) + "\n")
    print(json.dumps({k: v["abiSha256"] for k, v in (v2 if successor else manifest)["contracts"].items()}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
