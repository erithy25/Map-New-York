# Lower Manhattan drive-through: Broadway at Wall Street

`drive_lower_manhattan_broadway_wall_st` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** - File:Wall Street sign & US Flag (May 2023).JPG by Benoît Prieur, CC0
(http://creativecommons.org/publicdomain/zero/1.0/deed.en), taken 2023-05-21 13:00:40, 1920x1693.
[Commons page](https://commons.wikimedia.org/wiki/File:Wall_Street_sign_%26_US_Flag_(May_2023).JPG)

**Camera** - 40.70783, -74.01166 (NYC_TM -5210, 871), z 12.334 m NAVD88 on a 10.734 m street surface,
1.6 m eye height | azimuth 200.0 deg, pitch +0.0 deg | 35 mm on 36 mm (54.4 deg horizontal) |
1112x980. The position is the photograph's own EXIF GPS, 56.2 m from the item's recorded viewpoint;
the heading is not. 200.0 deg is the street bearing recorded in `meta.json`, because the item names
no subject and the photograph's direction was never derived from the image (confidence: medium). The
lens is the default 35 mm equivalent and the axis is level for the same reason: nothing is named to
aim at.

**Sun** - azimuth 185.36 deg, elevation 69.46 deg at 2023-05-21T13:00:40-04:00, from the
photograph's EXIF DateTimeOriginal rather than an assumed hour; direct normal irradiance 937.5 W/m².

**In frame** - 4 of 4 building tiles, none missing or LOD-substituted, 106,490 triangles between
them; 14 landmark models, 0 skipped, Trinity Church the nearest at 52.8 m; 2,634 pavement polygons
(1,177 curb, 596 crosswalk, 451 roadbed, 242 sidewalk, 87 median, 70 plaza, 11 parking lot), none
dropped; 505 props of 1,074 rows in range; 4,044 facade-kit pieces of 15,836 in range, 3,732 of them
windows; 89 vehicles and 212 people; terrain 87,288 triangles at 2 m near and 40 m far, 0 holes;
**4,500,126 triangles** total. Three budgets bind: props at 1,198,584 triangles, the kit at
1,140,528, and the agent budget, which dropped 1,292 further pedestrians and 69 further vehicles the
simulation had in range. A separate 4,898 kit pieces were suppressed under landmark shells, and 83
curb ramps are counted as built elsewhere - in the pavement mesh, not as props.

**Verdict - the strongest street-level frame in the set and the one that can be scored least: the kerb ramps are cut, the crossing is painted, the axle spheres are gone and 301 agents are on the street, but the reference is a close-up of a street sign and shares no content with it, so this pairing should be re-chosen before anyone reads a fidelity number off it.**

## What matches

* The canyon reads as a street. Broadway runs away from the lens between unbroken block faces, the
  roadbed and both pavements hold their widths, and the view stays open for the 59.3 m the clearance
  probe measured.
* **The curb ramps are visible, and this is the first sheet that could show them.** On the left kerb
  at the crossing ahead the dark kerb band tapers to nothing and the pavement runs down flush to the
  carriageway. 83 ramps are recorded as built into the pavement mesh rather than placed as props,
  which is J21 closed and legible at eye height.
* **No vehicle carries a sphere at its rear axle.** The dark sedan in mid-frame sits on its four
  wheels on the roadbed with clean tail lights and mirrors, and nothing untextured hangs beneath it -
  J44, closed and confirmed in the picture rather than in a test.
* Two subway entrances stand on the left pavement with green railings and **legible SUBWAY
  lettering**, a third on the right; 23 subway entrance props are placed.
* The ground-floor shopfront on the right is real: thin mullions, dark glazed panels between them,
  and a lit white fascia band above, from the 156 storefront and 10 storefront-interior kit pieces.
* The near left wall's windows are genuine openings - deep reveals with projecting hoods casting hard
  shadows - not painted rectangles. Whether a window reads as an opening depends on the facade class,
  and this frame holds both cases: the right-hand tower's windows are shallow horizontal bands.
* The crowd is dense where a Financial District lunchtime would be: 212 people, 186 of them at LOD2,
  with rucksacks, hi-vis vests and summer clothing, on both pavements.
* The light is right and, unusually for this set, so is the exposure. A 69.5 deg May sun almost down
  the canyon (azimuth 185.4 deg, from the photograph's own EXIF instant) leaves the near left wall in
  its own deep shade while the carriageway stays the brightest large surface in the frame, with a
  bright wedge at the vanishing point. The frame mean is 0.4062 and the render record marks the frame
  usable, so I16 - which bites hardest on shaded frames - barely bites here.
* Small furniture is visible and correct: a green litter basket, red hydrants on both pavements, a
  manhole cover in the roadbed, a cobra-head mast down the right kerb.

## What does not match

* **The two halves are not of the same thing.** The photograph is a tight study of a black Wall St
  sign and a US flag against a pale limestone Beaux-Arts block; the render is a level view down
  Broadway. There is no shared object, no shared framing and no way to score composition. The
  reference chooser still establishes no view direction (I12).
* The render contains no street-name sign and no flag, which between them are the entire subject of
  the photograph. Three flagpole props are placed within 250 m and none appears in frame.
* Material is the one comparison the caption invites, and it fails. The reference facade is cream
  limestone with rusticated bands, a canted corner bay, arched openings with keystones, stone
  balustrades and a heavy cornice; the render's nearest wall is dark grey with a vertical streak and
  no cornice, string course, balustrade or carving anywhere on it.
* The two sides of the street disagree about whether glass exists. The near left facade's windows are
  unglazed voids all the way up and its ground floor is blank dark grey down to the pavement, carrying
  no shopfront anywhere in frame; the right-hand building carries a mullioned, glazed shopfront under
  a lit fascia.
* The lit fascia band is blank white. No wording, no blade sign, no roundel.
* The lamp standards are the right pattern and the wrong finish: bishop's-crook posts with ovoid
  globes, carrying a mottled white-and-rust shaft rather than painted dark cast iron.
* The crossing ahead is one solid painted slab spanning the carriageway kerb to kerb, not the
  continental bars a New York crossing carries, and no other marking - centre line, lane line, stop
  bar - appears on any of the 451 roadbed polygons in frame. 596 crosswalk polygons are in range and
  none of them is a bar pattern (J52, open).
* No tree canopy appears anywhere in the frame although 117 tree props are placed within 250 m, and
  112 of them are species substitutions.
* 4,044 kit pieces of 15,836 records in range means roughly three quarters of the facade detail
  within 120 m is not drawn.
* 14 prop rows in range resolve to no asset at all - 7 memorials, 5 artworks, 2 drinking fountains
  (J23).
* The camera stands in the carriageway with 89 simulated vehicles on it (I14), and the clearance
  record calls `prop_lamp_bishops_crook_9` at 14.2 m "the nearest solid thing in the frame" while
  counting built fabric only; it carries no `nearest_agent` reading, so it predates the J49 fix.
* One figure in the nearest group on the left pavement wears nothing but dark briefs, which is a
  clothing variant the hour and the neighbourhood do not support.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the two halves show different subjects | the chooser matches a photograph to a place, never to a direction, and this item names no subject | reference |
| no street-name sign, no flag in the render | no stage produces street-name signage, and flagpoles carry no flag geometry | data |
| dark grey wall against cream limestone; no cornice, balustrade or carving | facade material and trim are inferred from a rule table, not observed (A2), and the shell carries massing plus a kit, not mouldings | material |
| unglazed voids on the left facade, a glazed shopfront on the right | the kit supplies openings without glazing for the left wall's facade class, while the storefront piece placed on the right carries its own glass | geometry |
| blank fascia band | fascia geometry ships lit but this frame's storefronts carry no resolved wording (B15, B4) | data |
| lamp shaft finish reads as corroded metal | the prop's texture is a generic weathered metal rather than the painted standard | material |
| one solid crosswalk slab and no other road marking | the pavement stage builds seven surface kinds and no markings at all, and a crossing is a single 3.66 m rectangle (`pavement.CROSSWALK_DEPTH_M`) rather than a bar pattern (J52) | geometry |
| no tree canopy in frame | trees are placed within 250 m but none falls in this 54.4 deg wedge | camera |
| three quarters of the facade kit undrawn | the 1,140,528-triangle kit budget is spent before the records in range are | budget |
| 14 prop rows resolve to no asset | memorials, artworks and drinking fountains have no modelled asset (J23) | data |
| camera in live traffic | the camera search has no rule about what a photographer can stand on (I14) | verification |
| clearance note claims the frame and measures the built city only | this render predates the J49 probe and caption fix | reporting |
| a figure on the left pavement in nothing but dark briefs | garment choice is not conditioned on the hour, the weather or the neighbourhood, and the CC0 wardrobe it draws from is thin (E4) | data |
