# Midtown avenue at rush hour

`street_midtown_avenue_rush_hour` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:26th St 8th Av td (2018-11-27) 24 - Midtown Tennis Club.jpg by Tdorante10, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2018, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:26th_St_8th_Av_td_(2018-11-27)_24_-_Midtown_Tennis_Club.jpg) — the file's stored date is the year alone and its viewpoint confidence is **low**. Eighth Avenue at 26th Street on a low-sun afternoon: a yellow medallion cab filling the foreground with two more behind it, a black SUV, a pickup and a Shawnee Transportation box truck queued at the light, the Gristedes Megastore's blue fascia along the base of the Midtown Tennis Club, the club's white inflatable dome above it, a brick apartment slab beyond, a mast-arm signal carrying two vehicle heads and a pedestrian countdown, an OPEN 24 HRS banner on the corner, a continental crosswalk under the cars, and bare plane trees at the left.

**Camera** — 40.7576, -73.9866 (NYC_TM -3051, 6374) at z 16.646 m NAVD88, a 1.6 m standing eye over terrain read at 15.046 m — the 10th percentile of 113 samples within 12.0 m | azimuth 209.0°, pitch 0.0° | 35 mm on 36 mm (54.432° horizontal) | 1280x854. The camera stands on the item's recorded viewpoint, Seventh Avenue at West 44th Street, because the photograph's own GPS is **1,455 m** away — it is a picture of Eighth Avenue at 26th Street, and the item's note calls its own block a *"representative avenue"*. The walk then moved **44.5 m** onto a crosswalk polygon: *"boxed in: the view azimuth is closed off 10 m ahead"*. From there the view is clear for 60.0 m and the nearest built thing is `lm_c_times_square.38` **10.1 m** away at +27° yaw. `scored_on_subject_sightline` is **false** — this item names no subject, so there is no probe, no sightline and no visible fraction, and nothing weighed the move.

**Sun** — azimuth 203.8°, elevation **71.4°** at 2018-06-21T13:30:00-04:00. Not measured: *"photograph year only, 21 June assumed, and 13:30 **chosen**, not measured: of the hours that put the Sun above 20 deg it is the one whose bearing (204 deg) comes closest to the view azimuth (209 deg), 5 deg off"*. 940 W/m² direct normal, Nishita sky, Filmic, **+2.75 stops**. Metered: **2.747 stops** on a linear median of **0.02681** against a physical rule of **0.0** — the rule asks for no correction at all, because this is the **second-highest Sun of the 172 sheets** and a solstice noon needs none.

## Verdict — the date is in the photograph's own title, the hour contradicts the item's own name, and Times Square's shells left a canyon of blank slabs

**The photograph's title says 27 November 2018 and the render is 21 June.** The fetch stored `date_taken` as the year, so `photo_instant` took the 21 June fallback (J114); the full date has been sitting in the file's own name the whole time, in the same record, six characters from the year that was read. The cost is visible in both halves: the reference's trees are bare and its Sun is low and raking, and the render has full summer canopy under a Sun at **71.4°**, nearly overhead, which is the highest light any street sheet in the pass is given but one. **Two of the seventeen sheets that took this fallback carry a full date in the photograph's title, and four carry a month or a date.**

**And the hour contradicts the item's own name.** The sheet is called *Midtown avenue at rush hour*. The instant is **13:30**, and the crowd was simulated at `hour: 13` to match it. J80 chooses the hour to light the view — here it picked the one whose Sun bearing sits 5° from the view azimuth — and nothing in that rule knows the item asked for rush hour. So a sheet about an avenue at its busiest is rendered at lunchtime, and its traffic is lunchtime traffic.

**The frame is a canyon of blank grey slabs, and the number that explains it is 6,127.** That is how many kit pieces were **suppressed with landmark shells** on this sheet: the camera stands inside the Times Square composite, whose landmark models replace the tiled buildings for the whole block, so the windows, cornices, storefronts and string courses that would have been placed on those buildings are correctly withheld — and the shells that replace them carry no openings of their own (J51). Against 6,127 suppressed, 6,496 were drawn, and 6,108 of those are windows on buildings outside the composite. The great featureless plane filling the right half of the picture, ten metres from the lens, is `lm_c_times_square.38`.

**So the two halves have almost no colour in common.** Chroma is **0.255**: the photograph is yellow cabs, blue supermarket signage, a red banner and a blue sky, and the render is grey. Contrast follows at **0.815** and the render sits **0.797 stops** brighter with a p50 ratio of **1.296** — a solstice noon against a November afternoon.

**Sixty-one vehicles on a sheet named for rush hour.** The density table asked for 1,200 vehicles and 3,856 people over the simulated ring; 1,435 and 3,000 were produced; **4,137 were dropped**, of which **560 vehicles and 1,095 people went to the 1,125,000-triangle agent budget** and 762 vehicles and 1,313 people fell outside the radius. What survives is 61 vehicles and 237 people. The reference's foreground alone holds six vehicles across two lanes.

**The fourteen boro taxis are in a zone where they may not pick up.** The mix is 20 yellow medallion cabs, **14 green boro taxis**, 11 black cars, 9 SUVs, 3 sedans, 2 box trucks, an MTA bus and an NYPD car — and the camera is standing in Times Square, inside the street-hail exclusion zone the boro taxi was created to stay out of. Nearly a quarter of this frame's traffic is a class that is licensed not to be here (J105).

**No signal, on the sheet where the signal is the composition.** The photograph's most prominent object after the cab is a mast-arm carrying two vehicle heads and a pedestrian countdown on the near corner, with a second mast behind it. The render has none, and neither does any other sheet in the pass: 19,814 signalised nodes and 633,287 signs are exported and the verification renderer never reads them (J110). Nor is there a Gristedes fascia, an OPEN 24 HRS banner or any other lettering.

**What the scene does hold.** 6 of 6 building tiles with none missing and none LOD-substituted, 315,108 triangles; **27,305 pavement polygons with 11,601 white markings, 1,161 plaza and 526 crosswalk, none dropped**; 2,088 props with none dropped, among them **6 steam vents, 33 subway vent grates, 14 subway entrances, 2 subway emergency exits and 6 newsstands** — the Midtown street-furniture vocabulary, correctly dense; 40 billboards, all blank; 4 landmark models placed with 1 inside the frame cone.

**And 755 of the 1,620 trees are the wrong species** — 47 per cent, well above the pass-wide 39.19 per cent (J108).

**No park ground within 150 m at all.** The near band has **0 samples**; the mid band's 113 samples all clear; beyond 400 m a quarter of 1,197 sit under the terrain.

## What matches

* **The street-furniture vocabulary is Midtown's**: steam vents, subway vent grates, subway entrances, emergency exits, newsstands and LinkNYC kiosks, all placed from the datasets.
* **The pavement is fully marked**: 27,305 polygons with 11,601 white markings and 526 crosswalk, none dropped.
* **Building tiles complete**: 6 of 6, 315,108 triangles, none missing, none LOD-substituted.
* **The suppression is correct**: the kit is withheld exactly where a landmark composite replaces the tiled buildings, and the record says how much.
* **The record declares its own limits** — no subject, a low-confidence heading, a reference 1,455 m away, and the instruction to compare fabric rather than composition.
* **The instant is labelled as chosen, not measured**, with the reasoning printed in full.
* **Nothing dropped from the props budget.**

## What does not match

* **21 June against a photograph whose own title says 27 November** — full canopy and a 71.4° Sun against bare trees and a low one (J114).
* **13:30 on a sheet named for rush hour**, with the crowd simulated at hour 13 to match.
* **A canyon of blank slabs**: 6,127 kit pieces suppressed under landmark shells that carry no openings of their own (J51).
* **Chroma 0.255**: a quarter of the photograph's colour, because the reference is cabs and signage and the render is grey concrete.
* **Sixty-one vehicles**, after 560 were dropped to the triangle budget, on the sheet that exists to show an avenue full of them.
* **Fourteen boro taxis inside the street-hail exclusion zone** (J105).
* **No traffic signal, no pedestrian countdown, no fascia, no banner, no lettering of any kind** (J110), on a photograph whose subject after the cab is a signal mast.
* **The reference is Eighth Avenue at 26th Street and the render is Seventh Avenue at 44th**, 1,455 m apart; the item calls both representative and the sheet compares them on fabric alone.
* **47 per cent of the trees are the wrong species** (J108).
* **Five of the six structures tiles have no file**, leaving 21,408 triangles from one.
* **No park-ground samples within 150 m**, so nothing local was measured.

## Measured for this assessment

| figure | where it comes from |
|---|---|
| two of the seventeen sheets that fell back to 21 June carry a full date in the photograph's own title, and four carry a month or a date | matching a date or month pattern against the `reference_photo.title` of every record whose `sun.time_source` reads "photograph year only" |
| this is the second-highest Sun of the 172 sheets | the `sun.elevation_deg` of every record, ranked; the Bronx County Courthouse is higher at 72.22 deg |
| 6,496 kit pieces drawn against 6,127 suppressed | the sum of the record's `scene.kit.per_category`, whose `total` is null, against its `suppressed_with_landmark_shells` |
| 755 of 1,620 trees substituted is 47 per cent, against a pass-wide 39.19 per cent | the record's `props.tree_species_substituted` and its tree count, with the pass-wide figure from DEVIATIONS J108 |
| 19,814 signalised nodes and 633,287 signs are exported and never read | DEVIATIONS J110, whose measurement this is |
| the canopy is ten species against the 132 the 2015 street-tree census counts | DEVIATIONS J108, whose measurement this is |
| the fourteen boro taxis stand inside the street-hail exclusion zone | the camera's coordinate against the zone `fleet_mix.py` documents, and DEVIATIONS J105 |

## Cause of each gap

| gap | cause | class |
|---|---|---|
| 21 June against a title that says 27 November | `photo_instant` reads the normalised `date_taken` and `year` fields and never the title or description beside them (J114) | **verification — open, and mechanical: the date is in the string the record already prints** |
| 13:30 on a rush-hour sheet | J80 chooses the hour to light the view; nothing reads the item's own name or note for a time of day | **verification — open** |
| a canyon of blank slabs | the landmark composite correctly suppresses the tiled buildings' kit, and its own shells have no window, door or storefront openings (J51, measured at +48 GB and declared impossible in this container) | content — declared impossible here |
| sixty-one vehicles at rush hour | a 1,125,000-triangle agent budget against 1,435 simulated vehicles, plus an hour that is not rush hour | performance and verification — declared, and compounded |
| fourteen boro taxis in the exclusion zone | `TrafficSim::sampleClass` splits the taxi share 70/30 with no geography (J105) | **runtime — open** |
| no signal, no signage, no lettering | the verification renderer never reads the sign or signal export, and its props catalogue has no kind for either (J110) | **verification — open** |
| the reference is 1,455 m away | `pick_reference_photo`'s distance band applies only to the drive-through group; a streetscape item takes the best-lit, best-clocked photograph wherever it was taken (J60's stated judgement, measured in J112) | verification — declared for this group |
| 47 per cent of trees the wrong species | ten species with two appearances each against the 132 the 2015 census counts (J108) | content — open |
| five of six structures tiles have no file | the B13 remainder | data — open |
| no park ground within 150 m | there is no open-space polygon within 150 m of Seventh Avenue at 44th Street, which is correct | not a gap |
