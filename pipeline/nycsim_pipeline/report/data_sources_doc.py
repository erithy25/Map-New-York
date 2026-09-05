"""Generate docs/DATA_SOURCES.md from the source registry and the download manifest."""
from __future__ import annotations
import json
from ..manifest import DOWNLOADS
from ..paths import DOCS
from ..sources import SOURCES


def main(argv=None) -> int:
    dl = json.load(open(DOWNLOADS))["entries"] if DOWNLOADS.exists() else {}
    lines = ["# Data sources", "", "Generated from `pipeline/nycsim_pipeline/sources.py` and `data/manifest/downloads.json`. Dynamic sources registered by stages (USGS tiles, NJ footprints, textures, photos) are listed in their stage reports and in the manifest.", "",
             "| id | description | format | licence | attribution | downloaded | bytes | sha256 |", "|---|---|---|---|---|---|---|---|"]
    for s in SOURCES.values():
        e = dl.get(s.id)
        lines.append(f"| `{s.id}` | {s.description} | {s.fmt} | {s.license} | {s.attribution} | {e['downloaded_at'] if e else '—'} | {e['bytes'] if e else '—'} | `{e['sha256'][:16]}…` |" if e else f"| `{s.id}` | {s.description} | {s.fmt} | {s.license} | {s.attribution} | — | — | — |")
    extra = [k for k in dl if k not in SOURCES]
    if extra:
        lines += ["", "## Dynamically registered downloads", "", "| id | url | licence | bytes |", "|---|---|---|---|"]
        for k in sorted(extra):
            e = dl[k]
            lines.append(f"| `{k}` | {e['url']} | {e['license']} | {e['bytes']} |")
    (DOCS / "DATA_SOURCES.md").write_text("\n".join(lines) + "\n")
    print(f"wrote {DOCS / 'DATA_SOURCES.md'} ({len(SOURCES)} registry sources, {len(extra)} dynamic)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
