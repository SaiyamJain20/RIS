"""TEST-ONLY registry and builder of the seven DELIBERATE source mutants M1..M7 of the F plan (agent 2, F phase; gap G3). PAPER-DERIVED RECONSTRUCTION. Not imported by any production module; not an adapter
operation; not in exports/adapter.json.

    python -m testtools.mutant_tree list
    python -m testtools.mutant_tree build M1 --dest /absolute/new/directory

`build` copies `hmbc_protocol` and `testtools` (and the data directories `abi` and `exports`, unchanged) of THIS checkout into DEST and applies exactly ONE registered mutant: every edit's anchor must match its file exactly once and the edit must change the text; DEST
must be an absolute path to a directory that does not exist or is empty (nothing is written into a refused one). A marker `MUTANT.json` records the mutant id and the sha256 of every edited file, so
`testtools.mutant_run` can refuse a tampered tree. The mutants are single-site edits, defined by the F plan (SOURCE-INTERFACE-PLAN, "experiment coverage"); they are not observed vulnerabilities, and the baseline
(unmutated) behaviour is what the F oracles must show the weakened one differs from:
  M1 no durable conflict record                       (F-12)        witness: the pin of a key is never written, so a second effect for a live key is signed too
  M2 emit signature before durable commit             (F-12, F-13)  witness: `sign` returns with the transaction still open and commits at the next request or never: a kill after the reply loses the record
  M3 declare expiry/re-sign from the host wall clock  (F-29)        witness: the expiry predicate reads the host clock instead of the ledger observation
  M4 skip all-field checkpoint validation             (FL-7, F-24)  witness: the checkpoint is not compared with the witness's own reads (block hash, key epoch, witness set, authEpoch, policyVersion)
  M5 collector forwards replies without recovery      (FL-5, F-22)  adapter: a reply is not checked to recover to the replying witness, so an invalid signature reaches the submission
  M6 receipt reference uses the DBC head              (FL-1)        witness: the receipt names the DBC head, not the block that contains the GrantIssued log
  M7 decision expiry retains the local-clock term     (FL-1)        witness: expiresAt = min(request, checkpoint, own DBC time + 30)
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from typing import NamedTuple

PROTO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
MARKER = "MUTANT.json"
PACKAGES = ("hmbc_protocol", "testtools")
DATA_DIRS = ("abi", "exports")            # read relative to the package (`ledger.ABI_DIR`, `export.ROOT`): copied unchanged so a tree behaves like the checkout


class MutantError(ValueError):
    """A refusal: the id, the destination, the anchors or the tree are not what a mutant build needs."""


class Mutant(NamedTuple):
    id: str
    rows: tuple
    role: str            # "witness": runs in a witness_main process; "adapter": runs in the adapter process
    what: str
    edits: tuple         # ((path relative to protocol/, old text, new text), ...): every `old` matches its file exactly once


_STATE, _SERVICE, _POOL = "hmbc_protocol/witness_state.py", "hmbc_protocol/witness_service.py", "hmbc_protocol/witness_pool.py"

MUTANTS = {m.id: m for m in (
    Mutant("M1", ("F-12",), "witness", "no durable conflict record: the pin of a key is never written",
           ((_STATE, '        if rec is None:\n            con.execute("INSERT INTO conflict (type, domain, wsv, key, effect, vhash) VALUES (?,?,?,?,?,?)", (*k, canonical_json(effect), vhash))\n',
             '        if rec is None:\n            pass                                                     # M1: the conflict record is never written\n'),)),
    Mutant("M2", ("F-12", "F-13"), "witness", "emit the signature before the durable commit: the transaction stays open until the next request",
           ((_STATE, '            self._con.execute("BEGIN IMMEDIATE")\n            pending = None',
             '            if self._con.in_transaction:\n                self._con.execute("COMMIT")                          # M2: the PREVIOUS reply\'s record is committed only now\n'
             '            self._con.execute("BEGIN IMMEDIATE")\n            pending = None'),
            (_STATE, '                    return self._stored\n                self._hook("before_commit")\n                self._con.execute("COMMIT")',
             '                    return self._stored\n                self._hook("before_commit")                        # M2: no COMMIT here, the reply leaves first'))),
    Mutant("M3", ("F-29",), "witness", "death of a digest by expiry is decided from the host wall clock",
           ((_STATE, 'int(obs["timestamp"]) >= max(int(r[1]) for r in live)', '__import__("time").time() >= max(int(r[1]) for r in live)'),)),
    Mutant("M4", ("FL-7", "F-24"), "witness", "the checkpoint is not compared with the witness's own reads",
           ((_SERVICE, '            if cp[f] != reads[f]:', '            if False:'),
            (_SERVICE, '            if cp[f] != head_reads[f]:', '            if False:'),
            (_SERVICE, '        if block["hash"] != cp["sourceBlockHash"]:', '        if False:'),
            (_SERVICE, '        if cp["keyEpoch"] != "0":', '        if False:'),
            (_SERVICE, '        if cp["witnessSetVersion"] != self._wsv or cp["witnessSetVersion"] != reads["witnessSetVersion"]:', '        if False:'))),
    Mutant("M5", ("FL-5", "F-22"), "adapter", "a reply is not checked to recover to the replying witness",
           ((_POOL, '        who = self._recover(m, sig)\n        if who is None:\n            return self._invalid(w, "signature does not verify over the recomputed digest")\n'
                    '        if who != self._w[w]:\n            return self._invalid(w, "signature does not recover to the replying witness")\n        c = _canon(m)\n',
             '        c = _canon(m)                                                # M5: no recovery, no filtering\n'),)),
    Mutant("M6", ("FL-1",), "witness", "the receipt names the DBC head instead of the block that contains the GrantIssued log",
           ((_SERVICE, '"dbcBlockNumber": str(int(logs[0]["block"])), "dbcBlockHash": logs[0]["hash"]}', '"dbcBlockNumber": str(int(head["blockNumber"])), "dbcBlockHash": head["blockHash"]}'),)),
    Mutant("M7", ("FL-1",), "witness", "decision expiry keeps a local-clock term",
           ((_SERVICE, '"expiresAt": str(min(int(request["expiresAt"]), int(cp["expiresAt"])))}', '"expiresAt": str(min(int(request["expiresAt"]), int(cp["expiresAt"]), dbc_now + 30))}'),)),
)}


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def build(mutant_id: str, dest: str) -> str:
    """Build the tree of ONE mutant in DEST (absolute; absent or empty) and return DEST."""
    if not isinstance(mutant_id, str) or mutant_id not in MUTANTS:
        raise MutantError("unknown mutant id")
    if not isinstance(dest, str) or not os.path.isabs(dest):
        raise MutantError("the destination must be an absolute path")
    if os.path.exists(dest) and (not os.path.isdir(dest) or os.listdir(dest)):
        raise MutantError("the destination exists and is not an empty directory")
    mu = MUTANTS[mutant_id]
    texts = {}
    for rel, old, new in mu.edits:                                                  # validate every anchor BEFORE anything is written
        text = texts.get(rel)
        if text is None:
            with open(os.path.join(PROTO, rel), encoding="utf-8") as f:
                text = f.read()
        if text.count(old) != 1:
            raise MutantError(f"an anchor of {mutant_id} matches {text.count(old)} times in {rel}")
        if old == new:
            raise MutantError(f"an edit of {mutant_id} changes nothing")
        texts[rel] = text.replace(old, new)
    os.makedirs(dest, exist_ok=True)
    for pkg in (*PACKAGES, *DATA_DIRS):
        shutil.copytree(os.path.join(PROTO, pkg), os.path.join(dest, pkg), ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    files = {}
    for rel, text in texts.items():
        data = text.encode("utf-8")
        with open(os.path.join(dest, rel), "wb") as f:
            f.write(data)
        files[rel] = _sha(data)
    with open(os.path.join(dest, MARKER), "w", encoding="utf-8") as f:
        json.dump({"id": mutant_id, "role": mu.role, "rows": list(mu.rows), "files": files, "note": "TEST-ONLY deliberate source mutant of the F plan; not a vulnerability finding"}, f, sort_keys=True, indent=1)
    return dest


def verify_tree(dest: str, mutant_id: str) -> dict:
    """Return the marker of DEST if it is a built tree of `mutant_id` whose edited files are untouched; raise MutantError otherwise."""
    if not isinstance(dest, str) or not os.path.isabs(dest) or not os.path.isdir(dest):
        raise MutantError("the tree is not an absolute path to a directory")
    try:
        with open(os.path.join(dest, MARKER), encoding="utf-8") as f:
            marker = json.load(f)
    except (OSError, ValueError):
        raise MutantError("the tree has no readable mutant marker") from None
    if not isinstance(marker, dict) or marker.get("id") != mutant_id or mutant_id not in MUTANTS:
        raise MutantError("the tree is not a tree of this mutant")
    expected = {rel for rel, _, _ in MUTANTS[mutant_id].edits}
    files = marker.get("files")
    if not isinstance(files, dict) or set(files) != expected:
        raise MutantError("the marker does not list the edited files of this mutant")
    for rel, digest in files.items():
        try:
            with open(os.path.join(dest, rel), "rb") as f:
                if _sha(f.read()) != digest:
                    raise MutantError("an edited file of the tree was changed after the build")
        except OSError:
            raise MutantError("an edited file of the tree is missing") from None
    return marker


def _main(argv) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="testtools.mutant_tree", add_help=False)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list")
    b = sub.add_parser("build")
    b.add_argument("mutant")
    b.add_argument("--dest", required=True)
    try:
        args = ap.parse_args(argv)
    except SystemExit:
        sys.stderr.write("refusing: usage: list | build ID --dest ABSOLUTE_DIR\n")
        return 2
    try:
        if args.cmd == "list":
            for mu in MUTANTS.values():
                print(json.dumps({"id": mu.id, "rows": list(mu.rows), "role": mu.role, "what": mu.what}, sort_keys=True))
            return 0
        if args.cmd == "build":
            build(args.mutant, args.dest)
            return 0
    except MutantError as e:
        sys.stderr.write(f"refusing: {e}\n")
        return 2
    sys.stderr.write("refusing: usage: list | build ID --dest ABSOLUTE_DIR\n")
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
