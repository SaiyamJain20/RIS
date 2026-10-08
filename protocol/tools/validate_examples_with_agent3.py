#!/usr/bin/env python3
"""Validate agent-2's generated example requests/responses with agent 3's own revision-4 validators.

Usage: python protocol/tools/validate_examples_with_agent3.py <extracted agent-3 snapshot root> [--out FILE]
For each example case: the request line must satisfy agent 3's AdapterRequest iff agent-2's adapter did NOT answer MALFORMED for it,
and the response must satisfy validate_response(operation, response). Disagreements are reported and make the exit code 1.
"""
import importlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
snap = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(snap))
a3 = importlib.import_module("evaluation.schema")
rows, bad = [], []
for path in sorted((ROOT / "protocol/exports/examples").glob("*.json")):
    doc = json.loads(path.read_text())
    for case in doc["cases"]:
        line = json.dumps(case["request"])
        resp = case["response"]
        try:
            a3.validate_json_line("AdapterRequest", line)
            req_ok = True
        except Exception as e:  # noqa: BLE001
            req_ok = False
        try:
            a3.validate_response(doc["operation"], resp)
            resp_ok = True
        except Exception as e:  # noqa: BLE001
            resp_ok = False
        malformed = (not resp["ok"]) and resp["error"]["code"] == "MALFORMED"
        row = {"operation": doc["operation"], "case": case["case"], "a3RequestValid": req_ok, "a3ResponseValid": resp_ok,
               "agent2ResponseCode": None if resp["ok"] else resp["error"]["code"]}
        rows.append(row)
        # A request agent 3 accepts must not be MALFORMED here; one it rejects must be MALFORMED (or fail before dispatch) here.
        if not resp_ok or req_ok == malformed:
            bad.append(row)
report = {"snapshot": str(snap), "cases": rows, "disagreements": bad}
print(json.dumps(report, indent=1))
if "--out" in sys.argv:
    pathlib.Path(sys.argv[sys.argv.index("--out") + 1]).write_text(json.dumps(report, indent=1) + "\n")
raise SystemExit(1 if bad else 0)
