export const meta = {
  name: 'woodland-canopy',
  description: 'Stage 55: the Ramble and every other wood in the five boroughs is bare terrain -- fill the OSM woodland polygons the build already holds with declared-procedural canopy stems, put the park ground under the verification scene, and let far trees reach the frame as billboards',
  phases: [
    { title: 'Implement', detail: 'two implementers in parallel on disjoint files: the pipeline canopy rule (furniture) and the verification scene (park ground, far-tree billboards, per-dataset counts)' },
    { title: 'Verify', detail: 'three sceptics: numbers over the rebuilt tiles, code over every changed file, one render of Bethesda Terrace against the photograph' },
  ],
}

const SCRATCH = '/tmp/claude-0/-home-user-Map-New-York/acd234fa-9154-5ea7-ad61-034753232ccb/scratchpad/canopy'

const COMMON = `
Repository: /home/user/Map-New-York (branch claude/nyc-1-to-1-drivable-sim-u0rmr7). Python 3 with numpy, pandas,
pyarrow, shapely, geopandas; Blender is the 'bpy' module (python3 -c "import bpy"). Do NOT run
tools/render_all_sheets.py (a render pass may be running in the background under that runner: leave its state file
blender_out/render_all_state.json and its lock blender_out/.render_lock alone). Do NOT run the Unreal manifest stage
(python -m nycsim_pipeline.unreal.manifest) -- the orchestrator runs it once after every furniture change. Do NOT git
commit, push or change branches. Keep any single process under ~3 GB: a comparison render (7.7 GB) may be running in
the same 14.3 GB memory cgroup. Scratch only under ${SCRATCH}/.
Project discipline: docs/DEVIATIONS.md is the J-register (the next free row is J86; J85 is the Hudson Yards platform,
being written by another agent -- do not touch its row or the file's other rows beyond your own and D10). Every
constant carries its source. A rule the sources do not give is written as a rule, named in the build summary and in
the rows' attrs, never dressed as a measurement. The brief's rule (§12, "Real data only") is that anything
procedural is declared as such, in code, in data and in the report. The recurring fault shape in this project is
"a correct measurement of something other than the thing it stands for".
Your final message is consumed by a program: return exactly the structured output requested.
`

const DIAGNOSIS = `
THE FINDING (measured by a scoping agent; every number below is from the repository on disk):
* The build's only tree sources are point inventories: the 2015 Street Tree Census (zero rows inside Central Park)
  and OSM natural=tree nodes (D10: 49,175 placed city-wide; 1,472 inside Central Park, of which 7 fall inside the
  park's 41.91 ha of natural=wood/landuse=forest polygons and 3 inside the Ramble's bounding box).
* The woodland COVERAGE is already extracted and read by nothing: data/processed/osm/landuse_leisure.parquet holds
  natural=wood 6,521 / landuse=forest 390 / natural=scrub 2,196 polygons (within the five boroughs: wood 2,144 /
  3,783.7 ha, forest 365 / 549.3 ha, scrub 1,426 / 1,227.2 ha, union 5,557.1 ha; Central Park 145 polygons / 41.91 ha;
  the Ramble bbox NYC_TM (-1984,8384)-(-1519,8829): 76 polygons / 11.04 ha, holding 3 OSM tree nodes and 8 placed
  tree instances; note there is no OSM polygon named "The Ramble" in Central Park -- the two rows with that name
  are in New Jersey). furniture/build.py reads only the census and osm/trees.parquet;
  parks/surfaces.py has no woodland class. 94.5 % of the five boroughs' wood/forest/scrub polygons hold zero trees.
* No canopy raster, LiDAR point cloud, canopy-change polygons or Conservancy map is held or registered
  (pipeline/nycsim_pipeline/sources.py: the only vegetation source is street_trees_2015). So the polygon extent is
  the only real claim; every stem position, the count, the species (unless from a tag or a mapped neighbour) and
  the height are inferred and must be declared so.
* A planted Ramble reaches the Bethesda sheet's prop disc but not its triangle budget (a sceptic corrected the
  scoping agent's "376 m" here): render_sheets.py RADIUS_OVERRIDES gives bethesda_terrace_fountain prop_r 300 m
  (342.67 m after the spare); the nearest Ramble-bbox wood polygon is 83.4 m from the camera at its edge (way
  1429681680, centroid 132.8 m), 27 of the bbox's 76 polygons (4.71 ha) lie inside the prop radius and 3.17 ha of
  wood lies in the 65.5 deg cone (azimuth 20.4) within it; the bbox's far corner is 674.8 m away and 15.86 ha of
  wood lies in the cone within 1,200 m. About 1,580 Ramble stems at LOD0 (3,676-9,564 triangles each) would be
  5.8-15 M triangles against add_props' 900,000 budget, and the 76 trees already in that frame account for most of
  its 673,140. scene.py add_props instances LOD0 only (lib.get(..., max_lod=0)). Every tree glb carries a LOD1 of
  6 triangles (three crossed billboards with a 512 px impostor, catalogue lod suffix): the far ring is for the
  budget, and the wider canopy radius is for the far shore, not for reaching the near wood at all.
* The verification scene loads no park ground at all (blender/verify/scene.py has add_buildings, add_landmarks,
  add_pavement, add_structures, add_props, add_kit -- no parkground), and blender/parks/build_parkground.py has
  been run for the 43 first-drive tiles only (blender_out/tiles/*/tile_parkground.glb: 43 files, 44 MB). So in
  every park sheet the ground is the grey terrain: Bethesda's assessment calls it "a bare, faceted grey hillside".
  The 23 sheets this stage touches are listed in docs/verification/render_pass_last.txt (lines 8-30); the 91
  tiles those sheets can reach (1,200 m) that hold a park surface and have no park ground yet are: t_-1_-2 t_-1_-3
  t_-1_-4 t_-1_-5 t_-1_-6 t_-1_10 t_-1_11 t_-1_12 t_-1_6 t_-1_7 t_-1_8 t_-1_9 t_-2_-2 t_-2_-3 t_-2_-4 t_-2_-5 t_-2_-6
  t_-2_10 t_-2_11 t_-2_12 t_-2_8 t_-2_9 t_-3_-2 t_-3_-3 t_-3_-4 t_-3_-5 t_-3_-6 t_-3_10 t_-3_11 t_-3_12 t_-3_8 t_-3_9
  t_-4_-2 t_-4_8 t_-4_9 t_-5_-2 t_-5_-3 t_-6_-2 t_-6_-3 t_-7_-2 t_0_10 t_0_11 t_0_12 t_0_13 t_0_14 t_0_15 t_0_16 t_0_7
  t_0_8 t_0_9 t_10_10 t_10_11 t_10_12 t_10_13 t_10_3 t_10_4 t_10_5 t_11_10 t_11_12 t_11_13 t_1_13 t_1_14 t_1_15
  t_1_16 t_2_13 t_2_14 t_2_15 t_2_16 t_3_13 t_3_14 t_3_15 t_7_3 t_7_4 t_7_5 t_7_6 t_8_10 t_8_11 t_8_12 t_8_13 t_8_3
  t_8_4 t_8_5 t_8_6 t_9_10 t_9_11 t_9_12 t_9_13 t_9_3 t_9_4 t_9_5 t_9_6 (about 1 MB each; the disk has ~1.7 GB free
  and a render pass needs 700 MB of it, so build these 91 and no more; the city-wide park ground stays a named
  remainder).
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
  scene_contract: { type: 'string', description: 'the new render.json fields and their meaning: scene.parkground.*, scene.props.per_dataset, scene.props.canopy.* (radius, billboard count, lod0 count)' },
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

phase('Implement')
const [pipe, scene] = await parallel([
  () => agent(`${COMMON}${DIAGNOSIS}
TASK (pipeline half; another agent is editing blender/verify/scene.py, blender/parks/build_parkground.py and
blender_out/ at the same time -- do not touch those): build the canopy rule in the main tree.
1. New pipeline/nycsim_pipeline/furniture/canopy.py, the same shape as rules.py's lamp/manhole/steam rules
   (source = SOURCE_RULE, dataset_id "rule:woodland_canopy", kind 0 tree, attrs {"rule":"woodland_canopy",
   "wood_osm_id":..., "wood_value": wood|forest|scrub, "leaf_type":..., "species_from": tag|neighbour|census_pool|fallback,
   "height_source":...}). Inputs, all on disk: landuse_leisure.parquet polygons with value in {wood, forest, scrub}
   clipped to the five boroughs (data/raw/nyc_opendata/borough_boundaries.geojson) and to the tile grid; the
   dataset trees already in cols (census + OSM) for suppression; parks/surfaces.parquet paved kinds (court, pool,
   track, rink, ...) and the tiles' pavement polygons (data/processed/pavement or roads: find the table
   build_pavement.py reads) and the water polygons (hydrography.parquet) for exclusion; the terrain sampler for z
   (the same one furniture/elevation.py or the ground model uses); furniture/trees.py CensusHeights for heights;
   blender_out/props/props_asset_catalog.json nominal_size_m for crown widths (read it; do not hard-code).
2. Placement: inside each polygon minus a 2 m edge inset, minus the exclusions, a deterministic Poisson-disc
   (blue-noise) sample seeded from (wood osm_id, cell index) in the style of coordinate_uniform() / SplitMix64
   so a re-run is bit-identical and independent of row order; a stem is suppressed within 6 m of any dataset tree
   (the 5.0 m cross-source radius plus a metre; cite it) so every mapped tree keeps its place and the rule fills
   gaps only, exactly the lamp/manhole convention.
3. Density: the repository holds no stem inventory of any NYC woodland, so the density is a MODELLING CONSEQUENCE
   of what the tag asserts (ground covered by tree crowns): stems are placed until the projected crown area
   (pi/4 * nominal_size_m[0]^2 per placed asset) reaches the polygon's area (closed canopy), with a minimum
   spacing of max(4 m, 0.6 * crown width); scrub draws only the small size band with 3 m spacing. State the
   resulting stems/ha in the summary as a consequence, never as a measurement. Species: (a) if any mapped OSM tree
   inside the same polygon carries species/genus, draw from those taxa; (b) else broadleaved/mixed/untagged -> the
   catalogue's species weighted by the 2015 census species counts in the same borough (state that this is a
   street-population proxy); needleleaved -> no conifer asset exists: record the tag's genus in attrs, place the
   broadleaf fallback, flag species_substituted. Heights: CensusHeights.draw conditioned on the taxon (reuse the
   OSM-tree path, height_source 4). variant 3 (condition unknown), as D10 does.
4. Hook: furniture/build.py appends the canopy rows to the rule parts after the OSM ingest and before dedupe, and
   dedupe.py's cross-source rules make a rule stem lose to any dataset tree within 6 m; catalog.py kind 0 lists the
   rule in its datasets and description; the build summary gets a "canopy" block (stems by value, by borough,
   Central Park / Prospect Park / Ramble-bbox counts, suppressed, excluded, per-ha consequence, rules text);
   props_catalog.json counts follow. DATA_CONTRACTS.md gets a §8.2 for the rule.
5. Rebuild the furniture stage: cd pipeline && python3 -m nycsim_pipeline furniture (about 90 s before this
   stage; measure it). Then re-measure over the written tiles: total rule:woodland_canopy rows, by wood value,
   Central Park (parks_properties signname), the Ramble bbox NYC_TM (-1984,8384)-(-1519,8829), Prospect Park,
   suppressed and excluded counts, stems/ha for wood/forest and scrub, tiles rewritten (build_summary
   tiles_rewritten / furniture/tiles_changed.txt), and that no kind other than tree changed row counts
   (compare counts_by_kind before/after).
6. Tests in pipeline/tests/test_furniture.py: determinism (two runs over one polygon are identical), the edge
   inset, exclusion of a paved polygon, suppression next to a dataset tree, crown-closure density on a synthetic
   1 ha square (the count is within the rule's own bound), needleleaved substitution is flagged, and the register
   test that every rule row carries attrs.rule. Run pipeline/tests/test_furniture.py and tests/test_props.py.
   If tests/test_world_integration.py's tile-index count test fails after the rebuild, run
   cd pipeline && python3 -m nycsim_pipeline.terrain.index --counts and re-run it.
7. DEVIATIONS.md: a new row J86 in the register's house style (finding in bold, measured numbers, why it was
   missed, what was done with numbers, what remains: the city-wide count is a consequence of crown closure, not a
   measurement; the LiDAR crown segmentation is the eventual per-tree answer), and amend D10's third column with
   one sentence pointing at J86. Do not commit. Return a PIPELINE_REPORT.`,
    { label: 'implement:canopy-pipeline', phase: 'Implement', schema: PIPELINE_REPORT, effort: 'high' }),
  () => agent(`${COMMON}${DIAGNOSIS}
TASK (scene half; another agent is editing pipeline/nycsim_pipeline/furniture/*, docs/DEVIATIONS.md,
docs/DATA_CONTRACTS.md and rebuilding data/processed/tiles/*/props.parquet at the same time -- do not touch those,
and expect props.parquet files to change under you: read them only for measurements, never assert their counts).
1. blender/verify/scene.py: a new add_parkground(cx, cy, radius_m, ...) that imports blender_out/tiles/{tile}/
   tile_parkground.glb for every tile within the radius that has one (the same tile-local X/Y + absolute Z convention
   as add_pavement / add_structures -- read how they place a tile's mesh), dresses each material from the shared
   photographic catalogue the way add_pavement / the NYCSIM_* dressing does (which catalogue entry is grass, which
   is dirt/forest floor, which is sand: read blender/common/texture_catalog.json and the parkground builder's
   material names; if a surface class has no catalogue texture, say so in the record with the reason, exactly as
   the buildings' 'stayed flat' reasons are recorded), and reports scene.parkground {tiles, tiles_missing,
   surfaces, triangles, by_kind, dressed, flat_with_reason} in render.json. Wire it into render_sheets.py's scene
   build where the other add_* calls are, with the same radius as the pavement.
2. blender/verify/scene.py add_props: a canopy path. Instances whose dataset_id is "rule:woodland_canopy" OR kind
   tree beyond a near radius (~120 m, a constant with its reason) are placed from the asset's LOD1 (the crossed
   billboards; lib.get(..., max_lod=1) and pick the lod1 mesh, see how add_landmarks does it) with a gather radius
   of its own, canopy_radius_m ~1,500 m (constant with reason: the Ramble's far edge is 681 m from the Bethesda
   camera), billboard-only beyond the near radius, LOD0 within it; the existing 'strip billboard cards near the
   lens' rule stays for LOD0 instances (it fixed the cone-tree fault; find it and keep it). The triangle budget
   accounting must count billboards. render.json scene.props gains per_dataset counts (rows placed per dataset_id,
   so a sheet can say 'N measured trees, M procedural canopy stems') and a canopy block {near_radius_m, radius_m,
   lod0, billboards, triangles, dropped_for_budget}. Read the existing props code in full before changing it.
3. Park ground for the 91 tiles listed above: python3 blender/parks/build_parkground.py --tile ... one process at a
   time or --workers 1 (a comparison render may be running beside you; keep under 3 GB), after checking how the
   builder finds the tile's pavement to subtract (tile_pavement.glb exists for 546 tiles; if a listed tile has no
   pavement export, read what the builder does and report it). Record bytes written, failures with their reason,
   and update the parkground total in DEVIATIONS.md J38's third column with one sentence (the only row you touch).
4. Tests: tests/test_comparison.py or tests/test_verify_scene.py (whichever holds the scene tests) gets: a
   synthetic parkground glb placed at the right absolute position; a canopy instance beyond the near radius is a
   6-triangle billboard and one inside it is LOD0; per_dataset counts sum to placed. Run the test file(s) you
   changed. Do NOT run render_sheets.py yourself: the render verifier does that once, after both halves land.
Return a SCENE_REPORT.`,
    { label: 'implement:canopy-scene', phase: 'Implement', schema: SCENE_REPORT, effort: 'high' }),
])
if (!pipe || !scene) return { pipe, scene, error: 'an implementer returned nothing' }
log(`pipeline: ${pipe.stems.total} stems, ${pipe.stems.tiles_rewritten} tiles rewritten, ${pipe.not_done.length} not done; scene: ${scene.parkground_tiles_built} park-ground tiles, ${scene.not_done.length} not done`)

phase('Verify')
const verdicts = (await parallel([
  () => agent(`${COMMON}
Sceptic, NUMBERS lens: re-measure every number in these two REPORTS from the rebuilt tiles
(data/processed/tiles/*/props.parquet), data/processed/furniture/build_summary.json, landuse_leisure.parquet,
parks_properties.geojson and blender_out/tiles/*/tile_parkground.glb: total canopy rows and by wood value; Central
Park, Ramble bbox and Prospect Park counts (project the polygons yourself); the stems/ha consequence against the
crown-closure rule (take 30 random polygons, sum pi/4*crown^2 of the placed assets from props_asset_catalog.json
nominal_size_m, compare with the polygon area); that no stem stands within 6 m of a dataset tree (kd-tree over 5
random tiles); that none stands on a paved or water polygon (30 random tiles); that every canopy row carries
attrs.rule and source = 1; that no kind other than tree changed counts; that a second furniture run would be
byte-identical (do NOT run it -- compare tiles_changed.txt and the summary's determinism statement, and run the
determinism unit test); park-ground files: count, bytes, each listed tile present. Default refuted=true on any
wrong load-bearing number. Do not modify files.
PIPELINE_REPORT:\n${JSON.stringify(pipe, null, 1)}\nSCENE_REPORT:\n${JSON.stringify(scene, null, 1)}`,
    { label: 'verify:numbers', phase: 'Verify', schema: VERDICT, effort: 'high' }),
  () => agent(`${COMMON}
Sceptic, CODE lens: read every changed file in full (both reports' changed_files). Check: the density is written
and named as a modelling consequence everywhere it appears (code docstring, build summary, catalogue, J86,
DATA_CONTRACTS) and never as a measurement; the seed is deterministic and row-order independent; the exclusions
and the suppression are the ones claimed; the species rule's census-proxy statement; the scene's billboard path
picks the LOD1 mesh and keeps the near-lens LOD0 strip; per_dataset counts sum to placed; add_parkground places
the tile mesh at the same absolute position convention as add_pavement (read both); materials dressed from the
catalogue with a recorded reason where flat. Run: cd pipeline && python3 -m pytest tests/test_furniture.py -q;
python3 -m pytest tests/test_props.py -q; and the scene test file(s) the scene report names. Default refuted=true
if uncertain. Do not modify files.
PIPELINE_REPORT:\n${JSON.stringify(pipe, null, 1)}\nSCENE_REPORT:\n${JSON.stringify(scene, null, 1)}`,
    { label: 'verify:code', phase: 'Verify', schema: VERDICT, effort: 'high' }),
  () => agent(`${COMMON}
Sceptic, RENDER lens -- the one agent allowed to render, once: run
  cd /home/user/Map-New-York && python3 blender/verify/render_sheets.py --slugs bethesda_terrace_fountain
(it takes the inter-process render lock itself; 5-10 minutes; if a pass is rendering it waits for the lock). Then
read docs/verification/comparison/bethesda_terrace_fountain/render.json: scene.parkground (tiles, surfaces,
dressed), scene.props.per_dataset (the canopy count), scene.props.canopy (billboards, lod0, radius), the triangle
totals against the budgets, lighting.development.stops, sightline.subject_visible_fraction (must still be > 0:
the fountain must not be hidden by a stem -- if a canopy stem stands inside the terrace's plaza or on the lower
plaza, that is an exclusion fault, name it). Then LOOK: python3 tools/sheet_pair.py bethesda_terrace_fountain
0.62 ${SCRATCH}/bethesda_pair.png and Read it, and Read render.png at full size and the reference photograph in
docs/verification/reference/bethesda_terrace_fountain/. The far shore behind the Lake (the Ramble) must now carry
a wooded hillside where the photograph has one, and the ground under the terrace and along the Lake must read as
lawn/park ground rather than the grey terrain. Report what the picture shows, with crops if needed
(PIL, under ${SCRATCH}/). Also confirm the render.json of the previous sheet (git show HEAD:docs/verification/
comparison/bethesda_terrace_fountain/render.json) had no parkground block and 76 trees, for the before/after.
Default refuted=true if the canopy is not in the picture or the fountain is hidden. Do not modify source files.
PIPELINE_REPORT:\n${JSON.stringify(pipe, null, 1)}\nSCENE_REPORT:\n${JSON.stringify(scene, null, 1)}`,
    { label: 'verify:render', phase: 'Verify', schema: VERDICT, effort: 'high' }),
])).filter(Boolean)
log(`verify: ${verdicts.filter(v => v.refuted).length}/${verdicts.length} refute`)
return { pipe, scene, verdicts }
