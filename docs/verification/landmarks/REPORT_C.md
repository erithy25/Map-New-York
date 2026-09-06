# Landmarks, agent C — verification report

**Lane:** Hudson Yards, Billionaires' Row, Times Square, the midtown modernists, the museums and cultural buildings,
the stadiums and the outer-borough icons — 39 landmark ids, `blender/landmarks/c_*.py`,
`blender_out/landmarks/`, `docs/verification/landmarks/`, `tests/test_landmarks_c.py`.

**Shared module used:** `blender/landmarks/common.py` (agent A). Every C script builds with A's `MeshBuilder`,
`Fenestration`/`tower_tier`/`facade_grid`/`cornice`/`column`/`pediment`/`arched_opening`/`punched_wall` builders, its
documented `PALETTE` (which now resolves CC0 PBR maps through `blender/common/textures.py` itself), and its
`finish`/`render_check` verification path. `blender/landmarks/c_common.py` was rewritten from a self-contained
duplicate into a thin layer over that module and now contains **only** what is specific to lane C: the registry, a
working footprint reader, the `curtain` helper, the Times Square screen slots and thin `finish`/`render` wrappers.

