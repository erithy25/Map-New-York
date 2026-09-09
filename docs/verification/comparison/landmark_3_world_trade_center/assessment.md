# 3 World Trade Center

`landmark_3_world_trade_center` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:3 World Trade Center 121.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2023-03-27 12:24:23, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:3_World_Trade_Center_121.jpg)

**Camera** — 40.710789, -74.010339 (NYC_TM -5064, 1260) at z 10.0 m NAVD88 | azimuth 277.9°, pitch +32.0° | 18 mm on 36 mm (73.7° horizontal, portrait) | 904x1206.

**Sun** — azimuth 165.2°, elevation 51.1° at 2023-03-27T12:24:23-04:00 (EXIF DateTimeOriginal); 891.9 W/m² direct normal, sky at strength 0.0319, Filmic, +1.93 stops.

**Subject** — 3 World Trade Center at 149.2 m.

**In the scene**, within 595.7 m of the camera and not all of it in frame — 4 building tiles (106,490 tris), 13 landmark models of which **2 can fall inside the 73.7° frame**, 22,813 pavement polygons (8,642 white, 4,350 sidewalk, 4,251 roadbed, 3,082 curb, 1,536 plaza, 574 crosswalk, 179 median, 158 yellow, 41 parking lot), 1325 props of the 3,967 in range, 5,603 kit pieces, 88 vehicles and 424 people; 4,500,244 triangles. Ground mesh 80,582 triangles, 0 holes. 20 city surfaces are dressed from the shared photographic catalogue.

## Verdict — the tower is modelled to its published height and the render walked away from it; the two halves are not the same picture

**The photograph is taken at the foot of 3 World Trade Center's east face, looking almost straight up it.** The bottom of the frame is the dark louvred glass and steel of the podium under a metal coping, above it the curtain wall rises in a regular grid with the sky reflected blue in it, a shadow from a neighbour cuts diagonally across the upper glazing, and down the right-hand edge runs the tower's defining feature, the external K-bracing of its load-sharing frame, catching the light in silver diagonals. There is no street, no person, no vehicle; the sky fills the top-left quarter of the frame, everything left of and above the tower's edge. The render is a street view: Church Street from a pavement, a bare linden in the left foreground, a queue of black sedans with a yellow taxi behind them in the carriageway, pedestrians on the kerb, a cobra-head lamp on the right, the white ribs of the Oculus just left of the axis, One World Trade Center and its spire at about two-thirds of the width, and a tall curtain-wall shell filling the left third, cut off by the left edge of the frame with its verticals converging. That shell is where the record puts the subject, at **149.2 m**; the photographer's camera is at its base.

**The record says how the two came apart.** The camera starts on the photograph's own EXIF GPS, **22 m** from the item's nominal viewpoint, with the heading **277.9°** the bearing from that GPS to the tower — position and heading both from the photograph. The clearance rule then found the view azimuth closed off **13 m** ahead (by something it does not name), decided that was less than the **54 m** this frame needs to show its subject, and moved the camera **70 m** onto the nearest sidewalk polygon, from which the azimuth is clear for **65 m**. The heading was not re-derived after the move, so the tower now sits at the frame's left edge. This is the J79 shape — a clearance the frame does not need optimised over the sightline it does — with the J79 repair in place: the walk scored its candidates on the subject's sightline (`scored_on_subject_sightline: true`) and accepted a position from which **1 of 13** rays reaches the subject, a visible fraction of **0.077** (J78). The photographer pointed the camera up the tower from its foot; the placement rule cannot do that and looked for open air instead.

**The tilt and the lens are declared, and the record itself says the frame is not comparable on proportion.** The top of `lm_b_wtc_site.238` stands **325 m** above a lens **108 m** away, **72°** above the horizon; the lens was widened from **35 mm** to the **18 mm** floor (**90°** vertical) and the axis tilted **+32.0°**, and the top is still cut off (I18). The photograph is tilted far more steeply, so the two frames do not share a projection either. A reader must not take this sheet as evidence for or against the tower's proportions, its street setting or its crowd: it shows that the model is present at the coordinate, and how the placement rule behaves when a photograph is taken from the foot of its subject.

**What the record does establish is the building.** The height probe lands **43 of 43** rays on built fabric at the subject's coordinate and reads **329.92 m** above a ground at **5.08 m**, off `lm_b_wtc_site.238`; the catalogue's `b_wtc_site` origin is **149.5 m** away — past the **120 m** the old rule looked in, so the height is measured from the geometry (J74) — and publishes **329.2 m** for the same tower. Measured surface and published height agree to well under one storey. The plan extent of the probed object, **99.9 m** by **94.6 m**, is the axis-aligned box of a square tower standing at an angle to the grid, which is what 3 World Trade Center is.

## What matches

* **The tower is at the coordinate and at its published height**: **43 of 43** probe rays on built fabric, **329.92 m** measured against **329.2 m** catalogued.
* **The instant is the photograph's own**, 2023-03-27 12:24:23 from EXIF, Sun at azimuth **165.2°**, elevation **51.1°** — south and high. In both halves the east face is lit obliquely: a specular glint a third of the way down the render's near tower, sunlit upper glazing with a neighbour's shadow across it in the photograph.
* **The neighbours are the right neighbours.** The Oculus reads as the Oculus — a white ribbed ellipsoid presenting its end to Church Street — and One World Trade Center with its spire stands **343.7 m** from the placed camera (`scene.landmarks`, measured from `scene.centre_tm`), right of centre in the frame where it belongs. The header's cone table puts it at **331.6 m** and **26.3°** off axis, but that table measures from the `camera` block, which still holds the photograph's GPS the walk left **70 m** behind. Neither neighbour is in the photograph.
* **The development is ordinary daylight.** The scene needed **+1.93** stops to read at middle grey where the physical rule alone would have given **+0.00** — nowhere near the +4 that marks an under-lit frame (J83).

## What does not match

* **The view.** The photograph is a look-up from the base of the east face; the render is a street scene with the subject at its left edge, **149.2 m** off, and the sightline reaching it on **1 of 13** rays, blocked at **14.7 m** by `prop_tree_littleleaf_linden_medium_bare_45`. The one ray that counts lands on `lm_b_wtc_site.239` at **224.7 m**, a neighbouring object of the same site model, accepted under the J78 same-fabric rule.
* **The facade.** The photograph's east face is a curtain wall with a dark louvred podium and the external K-bracing running its full height on the right. The model is a prism on the OTI footprint with storey bands; the catalogue states the curtain-wall panes are not modelled and names no bracing. The render's near tower is a plain banded grid with a dark podium band at its foot.
* **The foreground.** The bottom fifth of the render is roadway and kerb, with **88** vehicles in the scene (44 sedans, 22 SUVs, 11 taxis), **424** people, a bare street tree and a lamp **12.1 m** away; the photograph's frame never reaches the ground.
* **Tone and colour.** Render mean **0.5203** against the photograph's **0.367**, median ratio **1.543**; the photograph is exposed **-1.094** stops from the metering convention and the render **0.226** above it, so the gap is first an exposure choice (J83). Chroma **0.0883** against **0.2206**, ratio **0.4**: the photograph is blue sky in blue glass, the render is grey-blue shells, grey road and white ribs. The p05 gap, **0.1889** against **0.0609**, is the photograph's black podium glass, not a shadow floor.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| a street scene where the photograph is a look-up from the tower's foot | the clearance walk read the azimuth as closed 13 m ahead and moved the camera 70 m to find 54 m of open air; the heading was not re-derived; scored on the subject sightline it accepted 1 of 13 rays | verification, **DEVIATIONS J79 / J78** |
| verticals converge and the top is cut off | lens widened to the 18 mm floor then tilted +32.0°, declared in the record | stated choice, **I18** |
| no K-bracing, a banded prism for a curtain wall | `b_wtc_site` builds 3 WTC as a prism with storey bands on its footprint; panes are stated as not modelled and the bracing is not in the build | geometry |
| the header's landmark cone measured from the wrong point | the cone table reads the `camera` block, which keeps the photograph's GPS after a clearance move; the placed camera is `scene.centre_tm` and `scene.landmarks` distances are measured from it | verification |
| vehicles, pedestrians, tree and lamp in the bottom fifth | the simulation's own weekday crowd and traffic at that hour; the photograph's frame contains no ground | — (not a gap) |
| mean 1.418x, median 1.543x, chroma 0.4x | metered development against a photograph exposed -1.094 stops from the same convention, over two frames whose content differs entirely | verification, **DEVIATIONS J83** |
