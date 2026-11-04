"""Shared helpers for the agent-2 protocol-scope review of interface-v2 candidate 1 (A2-0054). Standard library + jsonschema 4.26.0 + eth-account 0.14.0
(protocol/requirements.txt). The candidate bytes are NOT stored here: extract them with
    git archive 4de6274 interfaces/proposals/v2 | tar -x -C <DIR>
and pass <DIR>/interfaces/proposals/v2 as argv[1]. Every script first verifies the candidate MANIFEST.json hash and every listed file hash."""
import hashlib, json, os, sys
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
F0 = os.path.join(REPO, "protocol", "f0")
MANIFEST_SHA256 = "6acceadf35b9f01833642f61ca7ae7bc05158e5499fb3e06c1d66fb2bbde3aee"

def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()

def proposal(argv):
    if len(argv) < 2:
        sys.exit("usage: <script> <DIR>/interfaces/proposals/v2")
    root = argv[1]
    m = os.path.join(root, "MANIFEST.json")
    if sha(m) != MANIFEST_SHA256:
        sys.exit("CANDIDATE MANIFEST HASH MISMATCH: " + sha(m))
    files = json.load(open(m))["files"]
    for rel, h in files.items():
        if sha(os.path.join(root, rel.replace("interfaces/proposals/v2/", ""))) != h:
            sys.exit("CANDIDATE FILE HASH MISMATCH: " + rel)
    print("candidate manifest %s verified (%d files)" % (MANIFEST_SHA256[:16], len(files)))
    return root

def load(root, rel):
    return json.load(open(os.path.join(root, rel)))
