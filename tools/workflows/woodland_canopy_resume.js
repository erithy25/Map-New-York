export const meta = {
  name: 'woodland-canopy-resume',
  description: 'Stage 55, continued: two implementers finish the canopy rule and the verification scene where the first run stopped (session limit), then three sceptics verify',
  phases: [
    { title: 'Finish', detail: 'two implementers in parallel on disjoint files, each continuing a half-done piece of work already in the tree' },
    { title: 'Verify', detail: 'a numbers sceptic, a code sceptic, and one render of Bethesda Terrace against the photograph' },
  ],
}

const SCRATCH = '/tmp/claude-0/-home-user-Map-New-York/acd234fa-9154-5ea7-ad61-034753232ccb/scratchpad/canopy'

const COMMON = `
Repository: /home/user/Map-New-York (branch claude/nyc-1-to-1-drivable-sim-u0rmr7). Python 3 with numpy, pandas,
pyarrow, shapely, geopandas; Blender is the 'bpy' module (python3 -c "import bpy"). Do NOT run
tools/render_all_sheets.py. Do NOT run the Unreal manifest stage (python -m nycsim_pipeline.unreal.manifest) -- the
orchestrator runs it once after every furniture change. Do NOT git commit, push, stash, checkout or change branches:
the working tree holds uncommitted work from two other stages (J85 platform: terrain/*, three reference meta.json,
DECISIONS/STATE/DATA_CONTRACTS section 3 and the J85 row) that must stay exactly as it is. Keep any single process
under ~3 GB. Scratch only under ${SCRATCH}/.
Project discipline: docs/DEVIATIONS.md is the J-register (J85 is taken by the platform; the canopy row is J86).
Every constant carries its source. A rule the sources do not give is written as a rule, named in the build summary
and in the rows' attrs, never dressed as a measurement. The brief's rule (section 12, "Real data only") is that
anything procedural is declared as such, in code, in data and in the report. The recurring fault shape in this
project is "a correct measurement of something other than the thing it stands for".
Your final message is consumed by a program: return exactly the structured output requested.
`

const HISTORY = `
WHAT HAPPENED: a first run of this stage was cut off by a session limit with both halves part-done and left in the
working tree (uncommitted). Read what is there before writing anything; continue it, do not start over.
The finding it addresses (measured): the build's only tree sources are point inventories (census: 0 rows in Central
Park; OSM natural=tree: 1,472 in the park, 7 inside its 41.91 ha of wood polygons); the woodland COVERAGE is on disk
in data/processed/osm/landuse_leisure.parquet (five boroughs: wood 2,144 / forest 365 / scrub 1,426 polygons,
union 5,557.1 ha; 94.5 % hold zero trees) and nothing reads it; no canopy raster or LiDAR is held, so the polygon
extent is the only real claim and every stem, its count, species and height are inferred and declared so. The
verification scene loaded no park ground and drew far trees only at LOD0; every tree glb has a 6-triangle LOD1.
`

const PIPELINE_REPORT = { type: 'object', properties: {
  changed_files: { type: 'array', items: { type: 'string' } },
  what_changed: { type: 'string' },
  rule_text: { type: 'string', description: 'the exact rule strings written into build_summary.json rules / props_catalog.json for the canopy, verbatim' },
  measurements: { type: 'array', items: { type: 'object', properties: { claim: { type: 'string' }, before: { type: 'string' }, after: { type: 'string' }, source: { type: 'string' } }, required: ['claim', 'before', 'after', 'source'] } },
  stems: { type: 'object', properties: { total: { type: 'integer' }, wood_forest: { type: 'integer' }, scrub: { type: 'integer' }, central_park: { type: 'integer' }, ramble_bbox: { type: 'integer' }, prospect_park: { type: 'integer' }, suppressed_near_dataset_tree: { type: 'integer' }, excluded_paved_or_water: { type: 'integer' }, tiles_rewritten: { type: 'integer' }, per_ha_wood_forest: { type: 'number' }, per_ha_scrub: { type: 'number' } }, required: ['total', 'wood_forest', 'scrub', 'central_park', 'ramble_bbox', 'prospect_park', 'suppressed_near_dataset_tree', 'excluded_paved_or_water', 'tiles_rewritten', 'per_ha_wood_forest', 'per_ha_scrub'] },
  commands_run: { type: 'array', items: { type: 'string' } },
  tests_run: { type: 'string' },
  deviations_entry: { type: 'string' },
  not_done: { type: 'array', items: { type: 'string' } },
}, required: ['changed_files', 'what_changed', 'rule_text', 'measurements', 'stems', 'commands_run', 'tests_run', 'deviations_entry', 'not_done'] }

const SCENE_REPORT = { type: 'object', properties: {
  changed_files: { type: 'array', items: { type: 'string' } },
  what_changed: { type: 'string' },
  parkground_tiles_built: { type: 'integer' },
  parkground_bytes: { type: 'integer' },
  parkground_failures: { type: 'array', items: { type: 'string' } },
  scene_contract: { type: 'string', description: 'the render.json fields and their meaning: scene.parkground.*, scene.props.per_dataset, scene.props.canopy.*' },
  measurements: { type: 'array', items: { type: 'object', properties: { claim: { type: 'string' }, value: { type: 'string' }, source: { type: 'string' } }, required: ['claim', 'value', 'source'] } },
  commands_run: { type: 'array', items: { type: 'string' } },
  tests_run: { type: 'string' },
  not_done: { type: 'array', items: { type: 'string' } },
}, required: ['changed_files', 'what_changed', 'parkground_tiles_built', 'parkground_bytes', 'parkground_failures', 'scene_contract', 'measurements', 'commands_run', 'tests_run', 'not_done'] }

const VERDICT = { type: 'object', properties: {
  refuted: { type: 'boolean' }, reasoning: { type: 'string' },
  defects: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, problem: { type: 'string' }, evidence: { type: 'string' } }, required: ['file', 'problem', 'evidence'] } },
  measurements: { type: 'array', items: { type: 'string' } },
}, required: ['refuted', 'reasoning', 'defects', 'measurements'] }

phase('Finish')
const [pipe, scene] = await parallel([
  () => agent(`${COMMON}${HISTORY}
TASK (pipeline half; another agent is finishing blender/verify/scene.py, blender/verify/render_sheets.py,
tests/test_parkground.py, tests/test_comparison.py and blender_out/ at the same time -- do not touch those).
ALREADY DONE by the first run, in the tree: pipeline/nycsim_pipeline/furniture/canopy.py (907 lines: the rule,
Poisson-disc placement seeded per (wood osm_id, cell), edge inset, exclusions, 6 m suppression next to dataset
trees, crown-closure density from props_asset_catalog.json nominal_size_m, species and height rules, needleleaved
substitution flag) and ten tests appended to pipeline/tests/test_furniture.py (test_canopy_* and
test_every_canopy_row_in_the_tiles_carries_the_rule_in_its_attrs) -- 'cd pipeline && python3 -m pytest
tests/test_furniture.py -q -k canopy' passes 10 of 10 as of now. Read canopy.py in full first and check its docstring
and rule text say the density is a modelling consequence of crown closure, never a measurement; fix what is not
right rather than rewriting.
STILL TO DO: (1) the hook -- furniture/build.py appends the canopy rows to the rule parts after the OSM ingest and
before dedupe (read how park_lamps / citibike / kerb are hooked and how rules are timed into timings_s), and
dedupe.py's cross-source rules make a rule stem lose to any dataset tree within 6 m (cite the 5.0 m cross-source
radius plus a metre); catalog.py kind 0 lists "rule:woodland_canopy" in its datasets and description; the build
summary gets a "canopy" block (stems by wood value, by borough, Central Park / Prospect Park / Ramble-bbox counts,
suppressed, excluded, per-ha consequence, rules text); props_catalog.json counts follow. (2) DATA_CONTRACTS.md: a
new subsection for the rule under section 8 -- sections 8.1 (Citi Bike) and 8.2 (kerb facing) exist, so use the
next free number; do not edit any other section (section 3 carries uncommitted J85 text). (3) Rebuild the
furniture stage: cd pipeline && python3 -m nycsim_pipeline furniture (76 s before this stage; measure it; props
tile writes are atomic). Then re-measure over the written tiles: total rule:woodland_canopy rows, by wood value,
Central Park (parks_properties signname), the Ramble bbox NYC_TM (-1984,8384)-(-1519,8829), Prospect Park,
suppressed and excluded counts, stems/ha for wood/forest and scrub, tiles rewritten (build_summary
tiles_rewritten / furniture/tiles_changed.txt), and that no kind other than tree changed row counts (compare
counts_by_kind before/after; take the before from the current build_summary.json BEFORE you rebuild). (4) Run
pipeline/tests/test_furniture.py, tests/test_props.py; then cd pipeline && python3 -m nycsim_pipeline.terrain.index
--counts and PYTHONPATH=pipeline python3 -m pytest tests/test_world_integration.py -q -k "tile_index or props or
kerb or citibike" (the manifest-staleness test is expected red until the orchestrator re-runs the manifest; say
so, do not touch props.json). (5) DEVIATIONS.md: a new row J86 in the register's house style (finding in bold with
the measured numbers, why it was missed, what was done with numbers, what remains: the city-wide count is a
consequence of crown closure not a measurement; the LiDAR crown segmentation is the eventual per-tree answer), and
one sentence in D10's third column pointing at J86 -- touch no other row. Return a PIPELINE_REPORT.`,
    { label: 'finish:canopy-pipeline', phase: 'Finish', schema: PIPELINE_REPORT, effort: 'high' }),
  () => agent(`${COMMON}${HISTORY}
TASK (scene half; another agent is finishing pipeline/nycsim_pipeline/furniture/* (build.py hook, canopy.py,
catalog.py, dedupe.py), pipeline/tests/test_furniture.py, docs/DEVIATIONS.md (J86, D10) and docs/DATA_CONTRACTS.md
and will rebuild data/processed/tiles/*/props.parquet during your work -- do not touch those files, and never assert
props.parquet counts). ALREADY DONE by the first run, in the tree (uncommitted; read 'git diff blender/verify/scene.py
blender/verify/render_sheets.py tests/test_comparison.py' and tests/test_parkground.py in full first):
blender/verify/scene.py gained PARKGROUND_GLB/dress_parkground_materials/_cut_faces_inside/add_parkground and a
canopy path in add_props (CANOPY_RADIUS_M 1500, CANOPY_DATASET_ID, LOD1 impostor cards beyond a near radius,
per_dataset counts, a canopy block in the report), AssetLibrary.get grew for LOD1; build_scene wires both;
render_sheets.py prints the park-ground and tree lines in the caption and the gaps; tests/test_parkground.py (9 pass)
and two tests in tests/test_comparison.py (test_the_park_ground_lands_on_its_tile_origin_at_its_own_height,
test_a_far_tree_and_a_procedural_stem_are_cards_and_a_near_surveyed_tree_is_branches) were written; park ground was
built for the 91 listed tiles (${SCRATCH}/parkground_build.log, 91/91) and the orchestrator rebuilt t_-5_5 and
t_-5_6 on the J85 terrain (133 tile_parkground.glb files exist now). The first run died while checking how the
verify scene's graded terrain sits against the imported park ground around Bethesda (fraction of park-ground
samples under/over the terrain) and while running the tests.
STILL TO DO: (1) finish that terrain-vs-parkground check and act on it: the park ground is draped on the
LandscapeSampler grid and the verify scene grades its own terrain mesh, so where the two disagree the ground either
z-fights or the park mesh sinks; measure over t_-2_8 around (-1777, 8205) and state the rule the scene uses (the
pavement path already solves the same problem: read how add_pavement handles it and use the same convention), and
put the measurement in scene.parkground; (2) run and make green: python3 -m pytest tests/test_parkground.py -q and
python3 -m pytest tests/test_comparison.py -q (the whole file; it is slow, use timeout 1500); (3) re-read your diff
adversarially: the near-lens LOD0 impostor strip must still apply (it fixed the cone-tree fault), the triangle
budget must count the cards, per_dataset must sum to placed, add_parkground must place a tile's mesh with exactly
the tile-local X/Y + absolute Z convention add_pavement uses, and every flat park material must carry a reason in
the record; (4) DEVIATIONS.md J38: ONE sentence in its third column updating the park-ground count (43 -> 133
tiles, bytes) -- the only row you touch, and re-read the file before editing because another agent edits it too;
(5) do NOT run render_sheets.py: the render sceptic does that once. Return a SCENE_REPORT.`,
    { label: 'finish:canopy-scene', phase: 'Finish', schema: SCENE_REPORT, effort: 'high' }),
])
if (!pipe || !scene) return { pipe, scene, error: 'an implementer returned nothing' }
log(`pipeline: ${pipe.stems.total} stems, ${pipe.stems.tiles_rewritten} tiles rewritten, ${pipe.not_done.length} not done; scene: ${scene.parkground_tiles_built} park-ground tiles, ${scene.not_done.length} not done`)

phase('Verify')
const verdicts = (await parallel([
  () => agent(`${COMMON}
Sceptic, NUMBERS + CODE lens, in one pass: (a) re-measure every number in these two REPORTS from the rebuilt tiles
(data/processed/tiles/*/props.parquet), data/processed/furniture/build_summary.json, landuse_leisure.parquet,
parks_properties.geojson and blender_out/tiles/*/tile_parkground.glb: total canopy rows and by wood value; Central
Park, Ramble bbox and Prospect Park counts (project the polygons yourself); the stems/ha consequence against the
crown-closure rule (30 random polygons: sum pi/4*crown^2 of the placed assets from props_asset_catalog.json
nominal_size_m against polygon area); no stem within 6 m of a dataset tree (kd-tree, 5 random tiles); none on a
paved or water polygon (30 random tiles); every canopy row carries attrs.rule and source = 1; no kind other than
tree changed counts; park-ground files: count, bytes, each listed tile present. (b) read every changed file in
full (both reports' changed_files, plus git diff of scene.py / render_sheets.py): the density is written as a
modelling consequence everywhere and never as a measurement; the seed is deterministic and row-order independent;
the scene's card path picks the LOD1 mesh and keeps the near-lens LOD0 strip; per_dataset sums to placed;
add_parkground uses add_pavement's placement convention. Run: cd pipeline && python3 -m pytest tests/test_furniture.py
-q; python3 -m pytest tests/test_props.py -q; python3 -m pytest tests/test_parkground.py -q. Default refuted=true on
any wrong load-bearing number or if uncertain. Do not modify files.
PIPELINE_REPORT:\n${JSON.stringify(pipe, null, 1)}\nSCENE_REPORT:\n${JSON.stringify(scene, null, 1)}`,
    { label: 'verify:numbers-and-code', phase: 'Verify', schema: VERDICT, effort: 'high' }),
  () => agent(`${COMMON}
Sceptic, RENDER lens -- the one agent allowed to render, once: run
  cd /home/user/Map-New-York && python3 blender/verify/render_sheets.py --slugs bethesda_terrace_fountain
(5-10 minutes; nothing else renders now). Then read docs/verification/comparison/bethesda_terrace_fountain/render.json:
scene.parkground (tiles, surfaces, dressed, the terrain-vs-parkground measurement), scene.props.per_dataset (the
canopy count), scene.props.canopy (billboards, lod0, radius), triangle totals against the budgets,
lighting.development.stops, sightline.subject_visible_fraction (must still be > 0: the fountain must not be hidden
by a stem -- if a canopy stem stands on the terrace's plaza or the lower plaza, that is an exclusion fault, name
it). Then LOOK: python3 tools/sheet_pair.py bethesda_terrace_fountain 0.62 ${SCRATCH}/bethesda_pair.png and Read it,
and Read render.png at full size and the reference photograph in docs/verification/reference/bethesda_terrace_fountain/.
The far shore behind the Lake (the Ramble) must now carry a wooded hillside where the photograph has one, and the
ground under the terrace and along the Lake must read as lawn/park ground rather than grey terrain; the cards must
not read as flat cut-outs edge-on at the frame's distances (say what they look like). Report what the picture
shows, with crops if needed (PIL, under ${SCRATCH}/). Confirm the previous record (git show HEAD:docs/verification/
comparison/bethesda_terrace_fountain/render.json) had no parkground block and 76 trees, for the before/after.
Default refuted=true if the canopy is not in the picture, the ground is still grey, or the fountain is hidden. Do
not modify source files.
PIPELINE_REPORT:\n${JSON.stringify(pipe, null, 1)}\nSCENE_REPORT:\n${JSON.stringify(scene, null, 1)}`,
    { label: 'verify:render', phase: 'Verify', schema: VERDICT, effort: 'high' }),
])).filter(Boolean)
log(`verify: ${verdicts.filter(v => v.refuted).length}/${verdicts.length} refute`)
return { pipe, scene, verdicts }
