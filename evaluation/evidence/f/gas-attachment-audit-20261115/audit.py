"""Read-only reconciliation of pinned peer gas attachments and retained logs."""
from collections import Counter
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys

PEER = "f6f852789d2629cb3b0a846d55793cd27799441d"
PREFIX = "communication/agent-1/outbox/0136-attachments/"
RETAINED = "evaluation/evidence/f/measurements-20261114/"
ROOT = Path(__file__).resolve().parents[4]


def blob(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def events(text):
    pattern = r'emit Measure\(name: "([^"]+)", sigs: (\d+), gas: (\d+)(?: \[[^\]]+\])?, calldataBytes: (\d+)\)'
    return [(name, int(sigs), int(gas), int(size)) for name, sigs, gas, size in re.findall(pattern, text)]


def sizes(text):
    return {name: int(size.replace(",", "")) for name, size in
            re.findall(r"^\|\s*(\w+)\s*\|\s*([\d,]+)\s*\|", text, re.MULTILINE)}


def main():
    hashes = {}
    manifest = blob(PEER, PREFIX + "SHA256SUMS")
    hashes[PREFIX + "SHA256SUMS"] = digest(manifest)
    attachments = {}
    for line in manifest.decode().splitlines():
        expected, path = line.split(None, 1)
        require(path.startswith(PREFIX) and path not in attachments, f"Unexpected manifest path: {path}")
        data = blob(PEER, path)
        require(digest(data) == expected, f"Attachment digest mismatch: {path}")
        attachments[path] = data
        hashes[path] = expected
    expected_names = {"harness-sha256.txt", "m1b.exit", "m1b-forge-log.txt", "m1c.exit",
                      "m1c-forge-log.txt", "m1.exit", "m1-forge-log.txt", "measurements.tsv",
                      "run.sh", "sizes.exit", "sizes-forge-log.txt", "versions.txt"}
    require(set(attachments) == {PREFIX + name for name in expected_names}, "Incomplete attachment manifest")
    get = lambda name: attachments[PREFIX + name].decode()
    table = list(csv.DictReader(io.StringIO(get("measurements.tsv")), delimiter="\t"))
    results = {}
    all_rows = []
    for run, expected_count, retained_name in (
        ("m1", 6, "certbench.log.gz"),
        ("m1b", 9, "certbench-with-receipt.log.gz"),
        ("m1c", 6, "certbench-governance.log.gz"),
    ):
        text = get(run + "-forge-log.txt")
        rows = events(text)
        require(len(rows) == expected_count, f"Event count mismatch: {run}")
        table_rows = [(r["call"], int(r["sigs"]), int(r["gas"]), int(r["calldataBytes"]))
                      for r in table if r["run"] == run]
        require(Counter(rows) == Counter(table_rows), f"Peer table mismatch: {run}")
        retained = (ROOT / RETAINED / retained_name).read_bytes()
        hashes[RETAINED + retained_name] = digest(retained)
        require(Counter(rows) == Counter(events(gzip.decompress(retained).decode())), f"Retained log mismatch: {run}")
        summary = re.findall(r"(\d+) tests passed, (\d+) failed, (\d+) skipped \((\d+) total tests\)", text)
        require(summary == [(str(expected_count), "0", "0", str(expected_count))], f"Suite summary mismatch: {run}")
        require(get(run + ".exit").strip() == "0", f"Peer exit mismatch: {run}")
        results[run] = {"measure_events": len(rows), "peer_recorded_tests_passed": expected_count,
                        "peer_recorded_exit": 0, "matches_tsv_and_retained_log": True}
        all_rows.extend(rows)
    require(len(table) == len(all_rows) == 21 and len(set(all_rows)) == 15, "Unexpected total row count")
    retained_path = RETAINED + "runtime-sizes-F-85c59f5.txt"
    retained_sizes = (ROOT / retained_path).read_bytes()
    hashes[retained_path] = digest(retained_sizes)
    expected_sizes = sizes(retained_sizes.decode())
    actual_sizes = sizes(get("sizes-forge-log.txt"))
    require(set(expected_sizes) == {"ACSC", "Governance", "KSSC", "LSC", "PSC", "RSC", "TMSC"}, "Product set mismatch")
    require(all(actual_sizes.get(name) == size for name, size in expected_sizes.items()), "Product size mismatch")
    require(all(size < 24576 for size in expected_sizes.values()), "Product exceeds EIP-170")
    oversized = {name: size for name, size in actual_sizes.items() if size > 24576}
    require(oversized == {"Deploy": 83849, "ExportGovernanceVectors": 45094, "ExportVectors": 39827}, "Oversized script set mismatch")
    require(get("sizes.exit").strip() == "1", "Size command recorded exit mismatch")
    require("some contracts exceed the runtime size limit" in get("sizes-forge-log.txt"), "Size error missing")
    harnesses = [("70a8bfe", "CertBench.t.sol"), ("8152bcc", "CertBench.t.sol"), ("674511f", "CertBenchGov.t.sol")]
    harness_checks = []
    for line, (revision, name) in zip(get("harness-sha256.txt").splitlines(), harnesses, strict=True):
        expected, _ = line.split(None, 1)
        path = "evaluation/measurements/" + name
        actual = digest(blob(revision, path))
        require(actual == expected, f"Harness hash mismatch: {revision}")
        full_revision = subprocess.check_output(["git", "rev-parse", revision], cwd=ROOT, text=True).strip()
        harness_checks.append({"commit": full_revision, "path": path, "sha256": actual})
    commit_tree = subprocess.check_output(["git", "rev-parse", "85c59f5^{tree}"], cwd=ROOT, text=True).strip()
    ledger_subtree = subprocess.check_output(["git", "rev-parse", "85c59f5:ledger"], cwd=ROOT, text=True).strip()
    require(commit_tree == "36a868305d67c8f546e6bde558ceb8e356962819", "Commit tree mismatch")
    require(ledger_subtree == "5749ccb70442bbc93725174950809a10668acb87", "Ledger subtree mismatch")
    return {"classification": "artifact consistency audit of peer-reported reconstruction measurements",
            "peer_publication_commit": PEER, "commit_tree": commit_tree, "ledger_subtree": ledger_subtree,
            "attachments_verified": len(attachments), "runs": results, "measure_events": len(all_rows),
            "distinct_measurement_rows": len(set(all_rows)), "repeated_m1_rows": 6,
            "product_runtime_bytes": expected_sizes, "oversized_local_scripts": oversized,
            "peer_recorded_size_exit": 1, "harnesses_verified": harness_checks,
            "forge_executed_by_this_audit": False, "python_version": sys.version,
            "git_version": subprocess.check_output(["git", "--version"], cwd=ROOT, text=True).strip(),
            "input_sha256": hashes}


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, sort_keys=True))
