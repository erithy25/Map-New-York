export const meta = {
  name: 'kerb-headings',
  description: 'J84: every dataset-placed kerb-side prop faces north — give bus shelters, LinkNYC kiosks, newsstands, bike shelters, bus stop signs and bike racks the heading of the kerb they stand on, from the road network, with the facing side taken from which side of the centreline the point lies',
  phases: [
    { title: 'Scope', detail: 'read the loaders, the Citi Bike axis code, the consumers, and each asset\'s facing convention' },
    { title: 'Implement', detail: 'one implementer in the main tree; furniture stage rebuilt; no Unreal manifest run' },
    { title: 'Verify', detail: 'two sceptics re-measure the headings from the rebuilt tiles' },
  ],
}

const COMMON = `
Repository: /home/user/Map-New-York (branch claude/nyc-1-to-1-drivable-sim-u0rmr7). Python 3 with numpy, pandas,
pyarrow, shapely, geopandas; Blender is the 'bpy' module. Do NOT run blender/verify/render_sheets.py or
tools/render_all_sheets.py. Do NOT run the Unreal manifest stage (python -m nycsim_pipeline.unreal.manifest) -- it is
run once by the orchestrator after every furniture change. Do NOT git commit, push or change branches. Keep any
single process under ~3 GB. Scratch only under /tmp/claude-0/-home-user-Map-New-York/acd234fa-9154-5ea7-ad61-034753232ccb/scratchpad/kerb/.
Project discipline: docs/DEVIATIONS.md is the J-register; every constant carries its source; a rule the sources do
not give is written as a rule, named in the build summary and in the rows' attrs, never dressed as a measurement.
The recurring fault shape is "a correct measurement of something other than the thing it stands for".

THE FINDING, already in the register as J84 (read the row): heading is NaN on 3,380 of 3,380 bus_shelter, 9,864 of
9,864 bike_rack, 2,251 of 2,251 linknyc, 360 of 360 newsstand, 13,341 of 13,341 bus_stop_sign and 17 of 17
bike_shelter rows in the 1,648 tile props.parquet files, because the loaders in
pipeline/nycsim_pipeline/furniture/datasets.py never write cols["heading"]; both consumers
(blender/verify/scene.py and the Unreal build_levels.py) turn NaN into yaw 0, so every shelter, kiosk and newsstand
stands square to north whatever its street runs.

WHAT ALREADY EXISTS AND MUST BE REUSED: pipeline/nycsim_pipeline/furniture/citibike.py station_axes() -- the local
bearing of the nearest CSCL centreline (roads/segments.parquet) within 25 m, reduced mod 180, the same tangent
rules._densify uses -- and the convention written into DATA_CONTRACTS §8.1 (heading = axis - 90; NaN where no
segment is within reach). One thing the Citi Bike code declared it could not know -- which side of the kerb the
station stands on -- IS in the data: the sign of the cross product of the segment's local tangent with the vector
from the projected point to the prop says whether the point lies left or right of the centreline, and the roadway
is toward the centreline. That is geometry read from two sources, not a rule. Use it for the facing, and record it
(attrs.side = left|right, attrs.facing = toward_roadway|away_from_roadway|along_kerb).
Your final message is consumed by a program: return exactly the structured output requested.
`

const PLAN = { type: 'object', properties: {
  loaders: { type: 'string', description: 'file:line of each loader for bus_shelter, linknyc, newsstand, bike_shelter, bus_stop_sign, bike_rack and where heading is (not) set; where in build.py the step goes (after dedupe, beside citibike.apply)' },
  facing_per_kind: { type: 'array', items: { type: 'object', properties: { kind: { type: 'string' }, asset_front_axis: { type: 'string' }, facing: { type: 'string' }, source_or_rule: { type: 'string' } }, required: ['kind', 'asset_front_axis', 'facing', 'source_or_rule'] }, description: 'for each kind: which local axis of the asset is its front (read blender/props/*.py PropSpec docstrings and the mesh builders), which way it faces relative to the kerb, and whether that is a sourced fact (an MTA/DOT standard, the asset\'s own docstring) or a declared rule' },
  consumers: { type: 'string', description: 'how scene.py and build_levels.py turn heading into yaw (heading_to_yaw), and whether the Citi Bike convention heading = axis - 90 puts the dock front toward the kerb under that mapping -- verify with the actual code' },
  side_of_centreline: { type: 'string', description: 'the exact computation and its sign convention, with a worked example' },
  plan: { type: 'array', items: { type: 'object', properties: { step: { type: 'string' }, files: { type: 'array', items: { type: 'string' } }, detail: { type: 'string' } }, required: ['step', 'files', 'detail'] } },
  rebuild: { type: 'string', description: 'the exact furniture rebuild command, expected tiles rewritten (build_summary tiles_rewritten / tiles_changed.txt) and time' },
  verification: { type: 'array', items: { type: 'string' } },
  risks: { type: 'array', items: { type: 'string' } },
}, required: ['loaders', 'facing_per_kind', 'consumers', 'side_of_centreline', 'plan', 'rebuild', 'verification', 'risks'] }

const REPORT = { type: 'object', properties: {
  changed_files: { type: 'array', items: { type: 'string' } },
  what_changed: { type: 'string' },
  measurements: { type: 'array', items: { type: 'object', properties: { claim: { type: 'string' }, before: { type: 'string' }, after: { type: 'string' }, source: { type: 'string' } }, required: ['claim', 'before', 'after', 'source'] } },
  commands_run: { type: 'array', items: { type: 'string' } },
  tests_run: { type: 'string' },
  deviations_entry: { type: 'string' },
  not_done: { type: 'array', items: { type: 'string' } },
}, required: ['changed_files', 'what_changed', 'measurements', 'commands_run', 'tests_run', 'deviations_entry', 'not_done'] }

const VERDICT = { type: 'object', properties: {
  refuted: { type: 'boolean' }, reasoning: { type: 'string' },
  defects: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, problem: { type: 'string' }, evidence: { type: 'string' } }, required: ['file', 'problem', 'evidence'] } },
  measurements: { type: 'array', items: { type: 'string' } },
}, required: ['refuted', 'reasoning', 'defects', 'measurements'] }

phase('Scope')
const plan = await agent(`${COMMON}
TASK (read-only): scope the fix. Read pipeline/nycsim_pipeline/furniture/{datasets.py,build.py,citibike.py,rules.py,
catalog.py,schema.py}, the PropSpecs and mesh builders for the six kinds in blender/props/*.py (which way is the
front of a bus shelter, a LinkNYC kiosk, a newsstand, a bike shelter, a bus stop sign, a bike rack -- in the asset's
own frame), blender/verify/scene.py and unreal/.../build_levels.py heading_to_yaw, docs/DATA_CONTRACTS.md §8/§8.1,
docs/DEVIATIONS.md J56 J58 J84, and the existing tests in pipeline/tests/test_furniture.py (test_kerb_kinds_carry_no_heading
pins the fault; it will need to become its inverse). Measure over the tiles: for each of the six kinds, how many
rows have a CSCL segment within 25 m (citibike.station_axes) and the distance distribution. Produce the PLAN.`,
  { label: 'scope:kerb', phase: 'Scope', schema: PLAN, effort: 'high' })
if (!plan) return { error: 'scope returned nothing' }
log(`scope: ${plan.plan.length} steps, ${plan.facing_per_kind.length} kinds`)

phase('Implement')
const report = await agent(`${COMMON}
TASK: implement the plan below in the main tree (deviate only where the code proves it wrong, and say so):
${JSON.stringify(plan, null, 1)}
Requirements: (1) one shared step in build.py after dedupe (beside citibike.apply) that writes heading for the six
kinds from citibike.station_axes and the side-of-centreline facing, with each kind's facing rule named in the row's
attrs and the build summary; rows with no segment within 25 m keep NaN and attrs.axis_source = none; an OSM
direction tag, where present, wins over the derived heading and is recorded as such; (2) apply the same
side-of-centreline facing to the Citi Bike parts (kiosk front and dock fronts toward the sidewalk, i.e. away from the
roadway, unless the asset docstring says otherwise) and update citibike.RULES and DATA_CONTRACTS §8.1 to say the side
is now read from the geometry, not a rule; (3) rebuild the furniture stage (python3 -m nycsim_pipeline furniture,
~90 s); (4) re-measure over the written tiles: per kind, heading NaN count, and for 200 random rows per kind the
angle between (heading + the kind's facing offset) and the nearest segment's bearing -- it must be within 1 deg mod
180, and the facing sign must match the side; (5) turn test_kerb_kinds_carry_no_heading into its inverse, add a unit
test for the side-of-centreline sign with a worked example, run pipeline/tests/test_furniture.py and tests/test_props.py;
(6) DEVIATIONS.md: close J84 in its third column with the before/after numbers. Do not run the Unreal manifest.
Do not commit. Return a REPORT.`,
  { label: 'implement:kerb', phase: 'Implement', schema: REPORT, effort: 'high' })
if (!report) return { plan, error: 'implementer returned nothing' }
log(`implemented: ${report.changed_files.length} files, ${report.not_done.length} not done`)

phase('Verify')
const verdicts = (await parallel([
  () => agent(`${COMMON}
Sceptic, NUMBERS lens: re-measure every before/after claim in this REPORT from the rebuilt tiles (data/processed/tiles/*/props.parquet),
roads/segments.parquet and build_summary.json: per-kind NaN counts, the heading-vs-segment angle on your own random
sample, the side/facing sign on at least 20 rows you project yourself, and that no kind outside the six plus
citibike_dock changed (compare counts_by_kind and a byte compare of tiles not in tiles_changed.txt against git HEAD's
content is impossible -- data/processed is untracked -- so compare row counts per kind and a checksum of the
non-heading columns for 30 random tiles against the build summary's before numbers). Default refuted=true on any
wrong load-bearing number. Do not modify files. REPORT:\n${JSON.stringify(report, null, 1)}`,
    { label: 'verify:numbers', phase: 'Verify', schema: VERDICT, effort: 'high' }),
  () => agent(`${COMMON}
Sceptic, CODE lens: read every changed file in full; check the facing conventions against the assets' own frames
(open the PropSpec/builder for each kind) and the consumers' heading_to_yaw; check the side-of-centreline sign with
your own worked example; run 'cd pipeline && python3 -m pytest tests/test_furniture.py -q' and 'python3 -m pytest
tests/test_props.py -q'. Default refuted=true if uncertain. Do not modify files. REPORT:\n${JSON.stringify(report, null, 1)}`,
    { label: 'verify:code', phase: 'Verify', schema: VERDICT, effort: 'high' }),
])).filter(Boolean)
log(`verify: ${verdicts.filter(v => v.refuted).length}/${verdicts.length} refute`)
return { plan, report, verdicts }
