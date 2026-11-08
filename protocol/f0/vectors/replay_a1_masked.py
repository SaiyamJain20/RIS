"""Replay agent 1's published masked-runtime evidence (A1-0096) through agent 2's STRICT masked check (agent 2, F0 revision 3).

Inputs are READ from an extracted copy of origin/agent-1's `ledger/evidence/f0-d50-masked/` (put it in scratch space; this script never writes there and the raw bytes are
not copied into this repository): per profile `replay/f0-masked-fresh-<profile>-tmp/{deployment.json,<Contract>.hex}` (raw eth_getCode, no 0x) and
`replay/online-check-<profile>.json` (agent 1's measured immutable ranges and hashes). Ranges come from agent 1's output, i.e. they are the pins; nothing is taken from RPC.

PREDICTIONS (written before the first run):
  R1  all 18 instances (3 profiles x 6 contracts): d50_reference.masked_runtime_sha256 equals the manifest runtimeSha256 AND agent 1's maskedLiveSha256.
  R2  my recomputed raw live sha256 equals agent 1's rawLiveSha256 for every instance (the published bytes are the measured bytes).
  R3  every published range has length 32, so the strict length rule of A1-0096 section 8 accepts all of them (if not, my rule or agent 1's claim is wrong).
  R4  flipping one byte INSIDE an immutable range does not change the masked hash; flipping one byte OUTSIDE every range does (per contract, 18 controls each).
  R5  perturbed pins are refused or mismatch: shifting one range start by +1 (still sorted) must not reproduce the manifest hash; two ranges merged into an overlap is refused.
  R6  raw live hashes differ across the three profiles for TMSC, PSC, ACSC and KSSC and are identical for LSC and RSC (agent 1's reading).
  R7  the PBC/DBC contract addresses are identical across the three profiles (D-2: addresses repeat on fresh chains).

    python3 -B -I replay_a1_masked.py <extracted-dir> > result.json
"""
import hashlib
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("d50_reference", os.path.join(HERE, "d50_reference.py"))
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)

PROFILES = ("repaired-e", "paper-strict", "mutant-no-nonce")
CONTRACTS = ("LSC", "TMSC", "RSC", "PSC", "ACSC", "KSSC")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main(root):
    base = os.path.join(root, "ledger", "evidence", "f0-d50-masked", "replay")
    out = {"inputs": {}, "instances": [], "controls": {}, "summary": {}}
    raw_by = {c: {} for c in CONTRACTS}
    addr_by = {c: {} for c in CONTRACTS}
    r1 = r2 = r3 = 0
    inside_ok = outside_ok = shifted_ok = merged_ok = 0
    n = 0
    for prof in PROFILES:
        run = os.path.join(base, f"f0-masked-fresh-{prof}-tmp")
        dep_bytes = open(os.path.join(run, "deployment.json"), "rb").read()
        dep = json.loads(dep_bytes)
        online = json.load(open(os.path.join(base, f"online-check-{prof}.json")))
        rows = {r["contract"]: r for r in online["results"][0]["contracts"]}
        out["inputs"][prof] = {"deployment.json": sha(dep_bytes), "online-check": sha(open(os.path.join(base, f"online-check-{prof}.json"), "rb").read())}
        for c in CONTRACTS:
            raw = open(os.path.join(run, f"{c}.hex"), "rb").read().strip().decode("ascii")
            out["inputs"][prof][f"{c}.hex"] = sha(raw.encode("ascii"))
            code_hex = "0x" + raw
            code = bytes.fromhex(raw)
            row = rows[c]
            ranges = [[str(r["start"]), str(r["length"])] for r in row["immutableRanges"]]
            n_bytes = str(dep["abi"][c]["runtimeBytes"])
            manifest_sha = dep["abi"][c]["runtimeSha256"]
            try:
                masked = ref.masked_runtime_sha256(code_hex, ranges, n_bytes)
                accepted = True
            except ValueError as e:
                masked, accepted = f"REFUSED: {e}", False
            n += 1
            ok1 = accepted and masked == manifest_sha == row["maskedLiveSha256"]
            ok2 = sha(code) == row["rawLiveSha256"]
            ok3 = all(r["length"] == 32 for r in row["immutableRanges"]) and accepted
            r1 += ok1; r2 += ok2; r3 += ok3
            raw_by[c][prof] = sha(code)
            addr_by[c][prof] = row["address"]
            # R4 controls
            if accepted and row["immutableRanges"]:
                s0, ln = row["immutableRanges"][0]["start"], row["immutableRanges"][0]["length"]
                a = bytearray(code); a[s0] ^= 0xFF
                inside_ok += ref.masked_runtime_sha256("0x" + a.hex(), ranges, n_bytes) == manifest_sha
                covered = set()
                for r in row["immutableRanges"]:
                    covered.update(range(r["start"], r["start"] + r["length"]))
                free = next(i for i in range(len(code)) if i not in covered)
                b = bytearray(code); b[free] ^= 0x01
                outside_ok += ref.masked_runtime_sha256("0x" + b.hex(), ranges, n_bytes) != manifest_sha
                # R5 controls
                sh = [list(r) for r in ranges]; sh[0][0] = str(int(sh[0][0]) + 1)
                try:
                    shifted_ok += ref.masked_runtime_sha256(code_hex, sh, n_bytes) != manifest_sha
                except ValueError:
                    shifted_ok += 1
                if len(ranges) >= 2:
                    mg = [list(r) for r in ranges]; mg[1][0] = str(int(mg[0][0]) + 1)
                    try:
                        ref.masked_runtime_sha256(code_hex, mg, n_bytes)
                    except ValueError:
                        merged_ok += 1
                else:
                    merged_ok += 1
            else:
                inside_ok += 1; outside_ok += 1; shifted_ok += 1; merged_ok += 1
            out["instances"].append({"profile": prof, "contract": c, "address": row["address"], "liveBytes": len(code), "ranges": len(ranges),
                                     "strictMaskedSha256": masked, "equalsManifestRuntimeSha256": masked == manifest_sha, "equalsAgent1Masked": masked == row["maskedLiveSha256"],
                                     "rawMatchesAgent1": ok2})
    sep = {c: len(set(v.values())) for c, v in raw_by.items()}
    same_addr = all(len(set(v.values())) == 1 for v in addr_by.values())
    out["controls"] = {"R4_inside_slot_flip_keeps_masked_hash": f"{inside_ok}/{n}", "R4_outside_slot_flip_changes_masked_hash": f"{outside_ok}/{n}",
                       "R5_shifted_range_does_not_reproduce": f"{shifted_ok}/{n}", "R5_overlapping_ranges_refused": f"{merged_ok}/{n}"}
    out["summary"] = {"instances": n, "R1_strict_masked_equals_manifest_and_agent1": f"{r1}/{n}", "R2_raw_hash_equals_agent1": f"{r2}/{n}",
                      "R3_all_ranges_length_32_and_accepted": f"{r3}/{n}", "R6_distinct_raw_hashes_per_contract_across_3_profiles": sep,
                      "R7_addresses_identical_across_profiles": same_addr,
                      "all_predictions_hold": r1 == r2 == r3 == inside_ok == outside_ok == shifted_ok == merged_ok == n
                      and sep == {"LSC": 1, "TMSC": 3, "RSC": 1, "PSC": 3, "ACSC": 3, "KSSC": 3} and same_addr}
    json.dump(out, sys.stdout, indent=1, sort_keys=True)
    print()
    return 0 if out["summary"]["all_predictions_hold"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
