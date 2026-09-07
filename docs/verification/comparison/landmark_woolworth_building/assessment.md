# Woolworth Building from City Hall Park

`landmark_woolworth_building` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Woolworth Building April 2022 007.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-04-30 13:17, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:Woolworth_Building_April_2022_007.jpg)

**Camera** — camera 40.71233, -74.00680 (NYC_TM -4799, 1371) z 13.7 m NAVD88 | azimuth 273.2deg pitch +0.0deg | 18 mm on 36 mm (73.7deg horizontal, 90.0deg vertical, portrait) | 904x1206. View direction: 273.2 deg, the bearing from this photograph's own GPS position to the Woolworth Building; heading and position both come from the photograph, which stands 44 m from the item's recorded viewpoint. Aim: level optical axis; the lens was widened from 35 mm to the 18 mm floor and the top of the subject is still cut off.

**Sun** — azimuth 193.0°, elevation 63.7° at 2022-04-30T13:17:00-04:00 (EXIF DateTimeOriginal).

**In frame** — 4/4 building tiles (82,358 tris), 10 landmark models, 2,231 pavement polygons, 746 props, 5,939 facade-kit pieces; 3,193,947 triangles; ground mesh 205² at 2.0 m near / 40.0 m far. The props were capped by the 1,257,391-triangle budget.

**Verdict — the two frames are not of the same thing. The reference is a tilted-up portrait of the Woolworth's Gothic crown filling the sky; the render's level axis cuts the building off 108 m below that crown, and half the frame is the empty grey plane of City Hall Park**

## What matches

* The building is in the right place and at the right width. Projecting the `woolworth` model's footprint through the recorded camera puts its four corners at 95–175 m and between −15.7 deg and +24.9 deg of the view axis, i.e. spanning pixel columns 282 to 732 of 904; the beige gridded mass in the render occupies almost exactly that band. Its base sits on the horizon line at y ≈ 620 of 1206, which is where the projection puts it.
* The horizontal proportions of the shaft are right. The model's tower rises out of a wider base block, and the step from base to tower falls at the same fraction of the building's width as in the photograph.
* The Sun is placed from the photograph's own timestamp, so the west face is in shade and the south face lit in both frames — the render's light/shade split down the tower's corner matches the photograph's.
* The ground under the camera is right: City Hall Park's plaza and path polygons are drawn from `data/processed/roads/pavement`, the camera stands on them in open air, and nothing was corrected (the clearance search left it where the photograph's GPS put it, with the nearest solid thing in the view cone further than 60 m).

## What does not match

* **The whole subject of the reference photograph is out of the render's frame.** The Woolworth model's published height is 241.4 m on an origin at 10.06 m NAVD88, so its crown stands 238 m above a lens at 13.7 m from 129 m away — 61.5 deg above the horizon. A level axis at the 18 mm floor sees 45 deg. Everything above 143 m NAVD88 is cut off: the top 108 m of the building, which is the flying buttresses, the pinnacled tourelles, the gabled setbacks and the green copper pyramid — the entire reason the photograph exists. The render's caption states this, and it is the honest consequence of the level-axis rule; it is also the reason this pair cannot be compared on the thing the photograph shows.
* **The Woolworth model has no Gothic detail.** What is in frame is a flat beige wall with a uniform grid of dark punched openings and a darker two-storey base. The photograph shows continuous vertical piers, recessed spandrels with tracery panels, arched heads to every window, string courses at the setbacks and a heavily modelled cornice. At 129 m none of that is present in the render.
* **The bottom half of the frame is a single featureless pale-grey plane.** The photograph has no foreground at all (it is aimed at the sky), so this is not a mismatch of content so much as a mismatch of framing — but it means half the render's pixels carry no information. The plaza reads as blank because pavement polygons carry a flat base colour with no paving pattern, no joints and no wear.
* **City Hall Park's trees are almost entirely missing, and the few that are there are black cones.** The reference's left and right thirds are filled with a spring ginkgo in leaf; the render has a handful of small dark conical crowns in shadow near the left edge and nothing else. The park's real canopy — a mature grove — is not in the frame.
* The park itself is not modelled: no paths, no fountain, no benches beyond one prop bench sitting on the plane, no railings, no lawn.
* No people, no vehicles, no traffic on Broadway — the standard gap.
* The sky is a clear Nishita gradient, pale near the horizon. The reference is a deep saturated blue with a slight haze. This is a view-transform and sky-model difference, not a Sun-position one.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the top 108 m of the Woolworth, including the whole crown, is outside the frame | the level-axis rule, held at the 18 mm floor: at 129 m the crown needs 61.5 deg of elevation and 18 mm gives 45 deg. Tilting would contain it but would skew the verticals and stop the two frames being comparable on proportion | camera/reference metadata |
| the Woolworth is a flat window grid with no piers, tracery or cornice | the `woolworth` landmark model is a massing model with a punched-window facade; no stage carves Gothic ornament | geometry |
| blank pale plaza over half the frame | pavement polygons carry a flat per-kind base colour with no paving texture, joints or wear | material |
| City Hall Park's canopy is absent and the few trees present are opaque dark cones | the park's trees are not in `props.parquet` at anything like their real density, and a leaf-card canopy in shade reads as a solid mass at this distance | data |
| no paths, fountain, railings or lawn in City Hall Park | park furniture and path geometry are neither buildings nor road polygons, so no stage produces them | geometry |
| no people, no vehicles | no stage places moving objects into a still verification frame | data |
| clear pale sky against a deep blue photograph | Nishita atmosphere with no aerosol tuning and no cloud layer; the reference's saturation is a camera and weather property | lighting |
