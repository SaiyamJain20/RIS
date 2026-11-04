"""Shared helpers for the agent-2 protocol-scope review of interface-v2 candidate 2 (A2-0057). Needs jsonschema 4.26.0 and (for check_signatures.py) eth-account 0.14.0
(protocol/requirements.txt). The candidate bytes are NOT stored here: extract them and pass the directory:
    git archive 5b6bb9d interfaces/proposals/v2-candidate2 | tar -x -C <DIR>      # then argv[1] = <DIR>/interfaces/proposals/v2-candidate2
Every script (1) verifies the candidate MANIFEST.json hash and the hash of every listed payload file, and (2) refuses to run unless MY working-tree protocol/f0 files equal the
hashes the candidate pins in OWNER-PINS.json (so the checks always compare against the exact owner inputs the candidate names)."""
import hashlib, json, os, sys
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
F0 = os.path.join(REPO, "protocol", "f0")
MANIFEST_SHA256 = "0d1a2be44666164deccf19c8c7e942b91938d7577fd6caba569837888b4143e9"

def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()

def proposal(argv):
    if len(argv) < 2:
        sys.exit("usage: <script> <DIR>/interfaces/proposals/v2-candidate2")
    root = argv[1]
    if sha(os.path.join(root, "MANIFEST.json")) != MANIFEST_SHA256:
        sys.exit("CANDIDATE MANIFEST HASH MISMATCH: " + sha(os.path.join(root, "MANIFEST.json")))
    files = json.load(open(os.path.join(root, "MANIFEST.json")))["files"]
    for rel, h in files.items():
        if sha(os.path.join(root, rel.replace("interfaces/proposals/v2-candidate2/", ""))) != h:
            sys.exit("CANDIDATE FILE HASH MISMATCH: " + rel)
    pins = json.load(open(os.path.join(root, "OWNER-PINS.json")))["files"]
    for rel, h in pins.items():
        if sha(os.path.join(REPO, rel)) != h:
            sys.exit("MY WORKING-TREE FILE DIFFERS FROM THE CANDIDATE'S OWNER PIN: " + rel)
    print("candidate manifest %s verified (%d files); %d owner pins equal my working-tree files" % (MANIFEST_SHA256[:16], len(files), len(pins)))
    return root

def load(root, rel):
    return json.load(open(os.path.join(root, rel)))
