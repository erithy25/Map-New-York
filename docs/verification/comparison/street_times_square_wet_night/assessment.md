# Times Square on a wet night

`street_times_square_wet_night` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:THANK YOU NYC.jpg by Jorge Jaramillo, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2020, 1920x1281. [Commons page](https://commons.wikimedia.org/wiki/File:THANK_YOU_NYC.jpg) — camera GPS on the file, viewpoint confidence **medium**. Times Square in the 2020 lockdown, after rain: a wall of advertising screens fills the upper half — a blue American Eagle THANK YOU, a red Coca-Cola sign, a musical's marquee, the news ticker, blue screens carrying Covid-19 study data and a message to essential workers — and the roadway below is standing water reflecting every one of them, upside down, across the bottom **45 per cent** of the picture. One person crosses the empty street under an umbrella. There is no traffic at all.

**Camera** — 40.758488, -73.9851 (NYC_TM -2964, 6496) at z 16.005 m NAVD88, a 1.6 m standing eye over terrain read at 14.405 m — the 10th percentile of 113 samples within 12.0 m | azimuth 29.0°, pitch 0.0° | 35 mm on 36 mm (54.432° horizontal) | 1280x854. The camera stands on *"this photograph's own EXIF camera GPS (40.75849, -73.98510), 209 m from the item's recorded viewpoint -- the position the picture was taken from"*, inside the 250 m radius at which a fix can still be the same view. It was **not moved**: 150 m of clear azimuth, the nearest built thing `prop_lamp_cobra_davit_5` **12.1 m** away and the nearest agent a yellow cab at 11.2 m. Level axis, no subject, no probe, no sightline.

**Sun** — azimuth 318.6°, elevation **-13.7°** at 2020-06-21T22:00:00-04:00: *"a night item, given an hour after civil dusk on every date of the year in New York, so the Sun is down and nothing but the city's own emissive content lights the frame."* Direct normal irradiance **0.0**, background 0.5, Filmic, **-1.25 stops** — and `metered` is **false**. A night frame is not metered, by design (J83): it takes the physical rule's -1.25 stops, because there is no daylight median to place at middle grey. The emissive note reads *"night frame: every emissive material left as the kit authored it"*, with 0 lamps switched off and 0 light cones hidden.

## Verdict — the frame is dark because Times Square's light is its advertising and this build has none, and the roadway is a mirror the renderer cannot make

**One hundred and forty-four billboards, all blank.** That is the whole verdict in a number. The kit places `billboard` **144 times** in this frame and every one is an unlit rectangle, so the square's own light source is absent and the render falls back on what is left: **129 cobra-head street lamps** casting cones onto an empty roadway, a yellow cab and a dark SUV under them, and a crowd standing in near-darkness. The Duffy Square night sheet says the same thing with 249 billboards. This one says it with the reference beside it in which the screens *are* the picture.

**And the roadway is not wet.** Half of the reference is a reflection: the Coca-Cola red and the American Eagle blue, inverted, in standing water across the foreground. The render's asphalt is dry and matte. The snapshot request carries x, y, heading, hour, day type, seed and headlights and no weather, so `rain_mm_h` is 0.00 on every one of the 172 sheets (J97) — and even with rain there is no wet-surface state on the roadway material to switch. Two of the three things this sheet's title names, *wet* and *night*, are a weather state and a light source, and the build has neither.

**Every luminance number agrees, and every one of them is measuring the wrong thing.** The exposure gap is **-0.234 stops**; the medians are within **9 per cent** (p50 **0.908**), the means within 15 per cent, and the contrast within 6 per cent (sd **0.939**). Two dark frames of the same darkness. The one ratio that separates them is **chroma, 0.158** — the render carries a sixth of the photograph's colour, the fourth lowest of the 171 measured sheets. The render's 95th percentile is even **brighter** than the photograph's, 0.6462 against 0.5865, because a lamp cone on wet-free asphalt is a hot highlight. So this sheet is the clearest case in the pass for reading the four ratios together rather than the exposure gap alone: on the number a reader looks at first, it is one of the closest matches in the set.

**The reference is a lockdown photograph and the simulation has no lockdown.** The photograph's street is empty because it was taken when Times Square was empty; the render draws **65 vehicles and 239 people** for a normal Sunday at 22:00 — 26 yellow cabs, 12 boro taxis, 12 sedans, 10 black cars, 4 SUVs and a box truck. Neither half is wrong about its own night. They are two different nights.

**Twelve boro taxis in Times Square.** The street-hail exclusion zone is the reason the green cab exists, and a ninth of this frame's traffic is a class licensed not to pick up in it (J105).

**The kit was cut to under three per cent.** **109,115 kit records were in range and 3,162 were drawn** — 2.9 per cent, the **third smallest share of any sheet in the pass** — against a 611,825-triangle cap, with a further 1,054 suppressed where the landmark composites replace the tiled buildings. Of what survived, 2,850 are windows and 144 are the blank billboards. Props went the same way: 991 placed and **3,943 dropped**, four in five, including 2,437 tree rows.

**What the scene does get right.** **37,646 pavement polygons with 18,885 white markings, 1,531 plaza, 839 crosswalk and 6,321 sidewalk, none dropped** — the bowtie's geometry is fully surfaced and it is the largest pavement count read this round. **13 landmark models placed with 4 inside the frame cone.** 21 LinkNYC kiosks, 15 subway entrances, 12 newsstands, 7 steam vents and 38 vent grates, which is the right street-furniture vocabulary for this square. Building tiles complete: 6 of 6, 332,446 triangles, none missing.

**And the record is honest about the one thing it could have hidden.** It does not meter a night frame and says so, it prints -1.25 stops as a physical rule rather than a measurement, and it records that no lamp was switched off and no cone hidden to flatter the picture.

## What matches

* **The luminance statistics agree**: a 0.234-stop gap, medians within 9 per cent, contrast within 6 per cent.
* **The pavement is complete and fully marked**: 37,646 polygons, none dropped, with the bowtie's plaza surfaced.
* **The street-furniture vocabulary is the square's**: LinkNYC kiosks, newsstands, steam vents, subway entrances and vent grates.
* **The camera stands on the photographer's own GPS fix** and needed no correction.
* **13 landmark models placed, 4 inside the frame.**
* **Building tiles complete**: 6 of 6, none missing, none LOD-substituted.
* **The night rule is declared, not smoothed**: not metered, -1.25 stops from the physical rule, no lamp switched off, no cone hidden.

## What does not match

* **144 billboards, every one blank**, so the square's own light source is missing and the frame is dark.
* **No wet roadway and no reflection**, on a sheet titled for a wet night; half the reference's picture is that reflection (J97).
* **Chroma 0.158**: a sixth of the photograph's colour, the fourth lowest of the 171 measured sheets.
* **The render's brightest highlights are street lamps** at a 95th percentile of 0.6462 against the photograph's 0.5865, so it is not that the render is too dark but that it is bright in the wrong places.
* **Sixty-five vehicles and 239 people against an empty lockdown street** — two different nights, neither wrong about its own.
* **Twelve boro taxis inside the street-hail exclusion zone** (J105).
* **2.9 per cent of the kit drawn**: 3,162 of 109,115 records, plus 1,054 suppressed.
* **Four in five props dropped**, 3,943 of them, including 2,437 tree rows.
* **No text anywhere**: no marquee, no ticker, no logo, no lettering, and none of the city's 633,287 signs (J110).
* **Five of the six structures tiles have no file**, leaving 21,408 triangles from one.
* **The instant is an assumed 21 June** because the photograph carries only a year (J114); for a night frame this costs only the date, since 22:00 is after civil dusk on every day of the year.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| 3,162 kit pieces drawn of 109,115 in range is 2.9 per cent, the third smallest share in the pass | the sum of the record's `scene.kit.per_category` against its `records_in_range`, ranked over every record in the pass that reports both |
| the chroma ratio of 0.158 is the fourth lowest of the 171 measured sheets | the `render_over_reference.chroma` of every `frame_stats.json` in the pass, ranked |
| the reflection fills the bottom 45 per cent of the reference | reading the reference half of `sheet.png`, where the waterline runs across the frame a little below its middle |
| 633,287 signs exist and none is drawn | DEVIATIONS J110, whose measurement this is |
| 21 June is an assumed date, not the photograph's | the record's own `sun.time_source`, and DEVIATIONS J114 for the seventeen sheets that take that fallback |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| 144 blank billboards, and so a dark square | the emissive slots exist and carry no video; the square's advertising is its light source and no content pipeline fills it | **content — open, and the largest single gap on this sheet** |
| no wet roadway, no reflection | the snapshot request carries no weather at all (J97), and the roadway material has no wet state to switch even if it did | **verification and content — open** |
| chroma 0.158 | screens and their reflections against grey asphalt under sodium-neutral lamp cones | consequent on the two above |
| an empty street against 65 vehicles | the photograph is of the 2020 lockdown and the simulation models a normal Sunday night | reference — the pairing, not the render |
| twelve boro taxis in the exclusion zone | `TrafficSim::sampleClass` splits the taxi share 70/30 with no geography (J105) | **runtime — open** |
| 2.9 per cent of the kit drawn | a 611,825-triangle cap against 109,115 kit records in the densest facade block in the city | performance — declared |
| four in five props dropped | a 911,955-triangle prop cap against the same block | performance — declared |
| no text anywhere | the verification renderer never reads the sign or signal export, and no lettering exists on any surface in this build (J110) | **verification — open** |
| five of six structures tiles have no file | the B13 remainder | data — open |
