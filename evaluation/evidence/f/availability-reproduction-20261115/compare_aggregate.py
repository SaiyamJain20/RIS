#!/usr/bin/env python3
"""Compare M2 result fields while excluding host-dependent wall timings."""
import json
import sys

fresh, previous = (json.load(open(path, encoding="utf-8")) for path in sys.argv[1:3])
fields = ("muted", "ok", "virtual_finish_ms", "signatures", "runs")
errors = []
for index, (new_row, old_row) in enumerate(
    zip(fresh["muted_sweep"], previous["muted_sweep"])
):
    for field in fields:
        if new_row.get(field) != old_row.get(field):
            errors.append((index, field, new_row.get(field), old_row.get(field)))
if len(fresh["muted_sweep"]) != len(previous["muted_sweep"]):
    errors.append(("row_count", len(fresh["muted_sweep"]), len(previous["muted_sweep"])))
if fresh["delay_order"] != previous["delay_order"]:
    errors.append(("delay_order", fresh["delay_order"], previous["delay_order"]))

print(
    "outcome_fields_match=",
    not errors,
    "subset_rows=",
    len(fresh["muted_sweep"]),
    "trials=",
    sum(row["runs"] for row in fresh["muted_sweep"]),
    "delay_order_match=",
    fresh["delay_order"] == previous["delay_order"],
)
for error in errors:
    print("MISMATCH", error)
sys.exit(bool(errors))
