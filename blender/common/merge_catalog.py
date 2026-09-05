"""Merge per-asset catalog JSONs into one catalog file. Usage: python merge_catalog.py <dir> <out.json>"""
import json, sys, pathlib
d = pathlib.Path(sys.argv[1]); out = pathlib.Path(sys.argv[2])
entries = [json.load(open(p)) for p in sorted(d.glob("*.json"))]
ids = [e["id"] for e in entries]
dups = {i for i in ids if ids.count(i) > 1}
if dups:
    raise SystemExit(f"duplicate catalog ids: {sorted(dups)}")
json.dump({"schema_version": 1, "count": len(entries), "entries": entries}, open(out, "w"), indent=1, sort_keys=True)
print(f"merged {len(entries)} entries -> {out}")
