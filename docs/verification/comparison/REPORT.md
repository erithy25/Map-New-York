# Visual comparison — renders against licensed photographs

Stage: **comparison** (`blender/verify/`). This is condition 3 of `docs/DEFINITION_OF_DONE.md`:
*"Screenshots from the seven standard viewpoints compared with real photographs."*

Every sheet in this directory puts one licensed photograph beside a Cycles render taken from the
photograph's own recorded viewpoint, with a caption strip that states the camera, the Sun, the
licence, and exactly which pieces of world data were in the frame. `INDEX.md` lists every subject
and its status. Each rendered subject has its own `assessment.md` with the judgement written down.

This report is written from the sheets, not from the code. Where the simulation falls short the
gap is named and attributed to one of four causes: **missing data**, **missing geometry**,
**missing material detail**, **lighting**.

---

## 1. How a sheet is made

`blender/verify/` is three modules, run as `python3 blender/verify/render_sheets.py --slugs <slug>`.

**`scene.py` — assemble the world around a point.**

| layer | source | how it is placed |
|---|---|---|
| terrain | `data/processed/tiles/{tile}/terrain.png` + `.json` (16-bit, 501x501 at 2 m, `z = z_min_m + v*z_scale_m`) | displaced regular grid over the scene square; PNG row 0 is the north edge so the array is flipped before sampling; quads whose four corners sit on a tile's flattened water surface get a separate water material |
| building shells | `blender_out/tiles/{tile}/tile_buildings.glb` | translated by the tile origin (`tx*1000, ty*1000`). Each glb carries LOD0/LOD1/LOD2 as sibling objects; exactly one LOD is kept per tile (LOD0 inside 1.2 km, LOD1 beyond) and the rest deleted, otherwise every shell would be drawn two or three times over |
| landmarks | `blender_out/landmarks/catalog/*.json` | translated to `origin_tm`; the model axes are already parallel to NYC_TM ("no rotation to apply on import"). Two catalogue shapes are handled: `glb` + `bounds_local_m` for the towers, and a `lods` map with `path` + `bounds` for the bridges and monuments |
| props | `data/processed/tiles/{tile}/props.parquet` (§8) | instanced against `blender_out/props/props_asset_catalog.json`, matched on `kind` -> `dataset_kind`; trees matched on the census species (`Styphnolobium japonicum` -> `tree_sophora_*`) and size class. Yaw is the negated compass heading, because every prop asset is authored facing +Y |
| facade kit | `data/processed/tiles/{tile}/kit_placements.bin` (§6, 40-byte records) | instanced against the tile's own `kit_placements.json` header, which carries the `kit_id -> glb` map the placements were written with. Yaw is `yaw_deg + 90` deg (the record holds the wall's outward normal as an angle CCW from east; every kit piece is authored with its wall plane at y=0 and `into_building = +Y`, so its outward direction is local -Y). `scale` is applied to local X only — it is the along-run stretch, not a uniform scale, so a 12x cornice must not become 12x tall |

Instancing shares one mesh datablock across every placement, so 7,000 kit pieces cost 7,000 object
headers and one copy of the geometry. Everything is capped by a triangle budget (3 M by default,
allocated buildings -> landmarks -> props -> kit) and every cap is recorded in `render.json` and
printed on the sheet, so a frame never silently omits content.

**`camera.py` — put the camera where the photographer stood.**

* Position: the `viewpoint` lat/lon from `meta.json` through `nycsim_pipeline.crs.lonlat_to_tm`.
* Heading: that entry's `azimuth_deg` (compass, 0 = north, clockwise).
* Height: the heightmap surface plus an eye height read from the viewpoint note — 1.60 m for a
  standing observer, and an explicit entry with its published source where the note names a
  structure (Top of the Rock's 70th-floor deck at 259.1 m, the TKTS steps at 4.6 m, a Staten
  Island Ferry's upper deck at 6.4 m above the waterline).
* The ground under the camera is read from a *neighbourhood*, not one sample: the median inside
  5 m where the note names the raised surface the photographer stood on, and the 10th percentile
  inside 12 m where the note says roadway or sidewalk — the 1 m DEM carries building grades and
  raised plinths that would otherwise lift a street camera onto the terrace beside it.
* Lens: 35 mm on a 36 mm sensor (54.4 deg horizontal) by default; per-slug overrides with a written
  reason where the reference framing needs a wider lens (24 mm for the Top of the Rock panorama
  and the Duffy Square bowtie, 28 mm for the promenade, the ferry deck, Washington Street and
  Bethesda Terrace). A portrait reference is rendered with the lens fitted to the *vertical* axis,
  because that is where a turned camera's 36 mm dimension lies.
* The optical axis is level. A level axis keeps vertical building edges vertical, which is the
  only way a render and a photograph can be compared on proportion; the one exception is a subject
  inside 250 m that needs less than 8 deg of tilt to centre.

**`render_sheets.py` — light it, render it, compose it.**

* The Sun is put where it actually was at the instant the reference photograph was taken: the EXIF
  `DateTimeOriginal`, in America/New_York, through `services/nycsim_live/astronomy.py` — the same
  SPA implementation the live-services stage uses. Where only a date or a year is recorded the
  fallback is 09:30 local and the sheet says so.
* Sun strength follows the direct normal irradiance for that elevation (1361 W/m2 at the top of
  the atmosphere, Kasten-Young air mass, 0.7 transmittance per air mass) scaled by one calibration
  constant, measured with test renders, that puts a 0.26-albedo sunlit ground at about 150/255
  through the Filmic view transform — where a correctly exposed photograph of concrete sits. The
  view exposure then opens by up to three stops as the light falls off, the way a photographer
  would, and never stops down.
* Sky: Nishita at the true Sun elevation and azimuth.
* In a daylight frame the prop kit's modelled light cones are made transparent and the street-lamp
  lenses are switched off (NYC street lighting is dusk-to-dawn); traffic-signal and shopfront
  emissives are left on. In a night frame nothing is touched, so the frame shows exactly how much
  emissive content the world actually has.
* Cycles CPU, 64 samples with adaptive sampling (threshold 0.03) and denoising, 2 light bounces.
* Composition with Pillow: reference left, render right, caption strip below naming the subject,
  the viewpoint and its note, the photograph's title/author/licence/date and Commons URL, the
  camera parameters, the Sun, what was in the frame, and every gap and cap.

Sheets that embed a CC BY-SA photograph are derivative works and carry the same licence; the sheet
says so in its own caption.

### Resolution

Renders are 1280 px wide for any reference at 3:2 or wider. A quarter of the reference photographs
(137 of 519) are portrait, some as tall as 1:2.2; at 1280 px wide those cost three times the
samples of a landscape frame for the same content, so their width is reduced to hold every frame to
the same pixel budget as a 1280x853 landscape frame. The angle of view is unchanged — only the
sampling density. Each sheet states its own resolution.

---

## 2. A finding that affects every viewpoint: recorded viewpoints inside buildings

The reference viewpoints are recorded to five decimal places of latitude but they are *nominal*
positions, and a third of them are on the wrong side of a facade. Testing every recorded viewpoint
against the real footprints in `data/processed/tiles/{tile}/buildings.parquet`:

**52 of 171 recorded viewpoints (30 %) fall inside a real building footprint**, up to 52 m from the
nearest wall. Among them are three of the seven mandated viewpoints — Brooklyn Heights Promenade
(16.5 m tall shell, BIN 3001515), Washington Street in DUMBO (BIN 3000088) and Bethesda Terrace
(BIN 1091041) — and two of the five drive-through areas (Broadway at Wall Street, inside BIN
1001024, a 99.6 m tower; Stone Street, inside BIN 1000836).

Left alone this renders a black frame: the first Brooklyn Heights Promenade render was uniformly
black (mean pixel 0.08/255) because the eye point sat inside `t_-5_-1_roof_membrane`, 14 m below
that shell's roof.

`camera.py` now detects it — a ray straight up from the eye point that hits a building shell or a
landmark means the eye is inside it — and walks the camera radially outward in 2 m steps to the
nearest point in open air, re-measuring the eye height from the heightmap there. Every sheet whose
camera was moved states the distance, the direction and the shell it was moved out of. A second
rule covers rooftop viewpoints: an eye point standing on a roof is walked forward along the view
azimuth to the parapet, because a deck's viewpoint is recorded as one lat/lon for the whole slab
and the photographs are taken at the edge — without it the Top of the Rock frame is a picture of
the 30 Rockefeller Plaza roof slab, which is exactly what the first attempt produced.

This is a defect in the reference metadata, not in the world. It should be fixed at source by
snapping each viewpoint to the nearest point outside a footprint.

---

## 3. Coverage, verdict and ranked gaps

See section 4 onward, `INDEX.md` for the per-subject table, and each subject's `assessment.md`.
