#!/usr/bin/env python3
"""Validate M2 trial records and compare their aggregate to the prior receipt."""
import itertools, json, sys
fresh = json.load(open(sys.argv[1], encoding="utf-8"))
prior = json.load(open(sys.argv[2], encoding="utf-8"))
fields = ("muted", "ok", "virtual_finish_ms", "signatures", "runs")
errors = []
for index, (new, old) in enumerate(zip(fresh["muted_sweep"], prior["muted_sweep"])):
    for field in fields:
        if new.get(field) != old.get(field): errors.append(("aggregate", index, field, new.get(field), old.get(field)))
if len(fresh["muted_sweep"]) != len(prior["muted_sweep"]): errors.append(("aggregate_row_count", len(fresh["muted_sweep"]), len(prior["muted_sweep"])))
if fresh["delay_order"] != prior["delay_order"]: errors.append(("delay_order", fresh["delay_order"], prior["delay_order"]))
expected = [list(s) for n in range(5) for s in itertools.combinations(range(4), n)]
rows = {tuple(r["muted"]): r for r in fresh["muted_sweep"]}
if list(rows) != [tuple(s) for s in expected]: errors.append(("subset_grid", list(rows)))
trials = fresh.get("muted_trials")
if not isinstance(trials, list) or len(trials) != 80: errors.append(("trial_record_count", None if not isinstance(trials, list) else len(trials), 80))
else:
    grouped = {}
    for record in trials: grouped.setdefault(tuple(record.get("muted", [])), []).append(record)
    if list(grouped) != [tuple(s) for s in expected]: errors.append(("trial_subset_grid", list(grouped)))
    for subset in expected:
        key = tuple(subset); records = grouped.get(key, [])
        if [r.get("trial") for r in records] != [1, 2, 3, 4, 5]: errors.append(("trial_numbers", subset)); continue
        aggregate = rows.get(key)
        checks = {"ok": sorted({r["ok"] for r in records}), "virtual_finish_ms": sorted({r["virtual_finish_ms"] for r in records}), "signatures": sorted({r["signatures"] for r in records})}
        if aggregate is None or any(aggregate.get(k) != v for k, v in checks.items()): errors.append(("aggregate_vs_trials", subset, checks, aggregate))
print("aggregate_fields_match=", not any(e[0].startswith("aggregate") or e[0] == "delay_order" for e in errors), "subset_rows=", len(fresh["muted_sweep"]), "trial_records=", 0 if not isinstance(trials, list) else len(trials), "trial_aggregates_consistent=", not any(e[0] in ("subset_grid", "trial_record_count", "trial_subset_grid", "trial_numbers", "aggregate_vs_trials") for e in errors), "delay_order_match=", fresh["delay_order"] == prior["delay_order"])
for error in errors: print("MISMATCH", error)
sys.exit(bool(errors))
