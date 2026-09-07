# Williamsburg Bridge from Domino Park

`landmark_williamsburg_bridge` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Williamsburg Bridge June 2022 003.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-06-28 13:38:05, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Williamsburg_Bridge_June_2022_003.jpg)

**Camera** — camera 40.71318, -73.96827 (NYC_TM -1544, 1464) z 5.3 m NAVD88 | azimuth 202.5deg pitch -0.2deg | 35 mm on 36 mm (54.4deg horizontal) | 1208x906. The camera now stands on **this photograph's own EXIF GPS**, 389 m from the item's recorded viewpoint. Heading 202.5 deg, the bearing from that position to the Brooklyn tower; heading and position come from the same measurement.

**Sun** — azimuth 208.0°, elevation 70.7° at 2022-06-28T13:38:05-04:00 (EXIF DateTimeOriginal).

**In frame** — 5/5 building tiles (166,404 tris), 2 landmark models, 868 pavement polygons, 451 props, 4,089 facade-kit pieces; 2,137,334 triangles; ground mesh 205² at 2.0 m near / 40.0 m far, 17,254 quads on the flattened East River surface. Frame mean 0.523, sd 0.205; **83.4 %** of pixels differ from the shipped render by more than 8/255.

**Verdict — re-rendered 2026-09-07 from where the photograph was actually taken. The camera has come 389 m forward, from the far end of Domino Park to 118 m from the Brooklyn tower, and the render is now the same *situation* as the reference — under the approach viaduct, beside a warehouse, looking south along the deck. It is not yet the same *picture*: the tower the sheet names as its subject rises 39.8 deg above a level 35 mm frame that reaches 21.1 deg, so it is out of shot above the top edge, and the lens rule did not widen because it could not find the bridge model to measure**

## Why the camera moved 389 m

The old camera stood on the item's nominal viewpoint, **506.5 m** from the Brooklyn tower, and the
photograph's own GPS — **117.5 m** from it — was thrown away by a rule that measured the wrong
distance. `PHOTO_GPS_SANITY_M` asked how far the photograph's GPS was from the *recorded viewpoint*
(389 m, past 250 m) and rejected it as mis-tagged, which is to say it preferred an estimate to a
measurement on the strength of their disagreement.

The rule now asks what defines the view (`docs/verification/comparison/REPORT.md` §2.9 and §1). This
item is a view **of** a point subject, so its viewpoint is only an estimate of where such a photograph
is taken from: the catalogue *generates* it as a bearing and a distance from the subject. A photograph
that stands **nearer the subject** than that estimate and **on the same side of it** — 117.5 m against
506.5 m, 3.0 deg apart in bearing — is the same view of the same thing, and its own GPS is the better
position however far it is from the estimate. An item that is a view **from** somewhere keeps the
250 m radius, which is why the Staten Island Ferry, whose photograph's GPS is also nearer the aim
point, is unaffected: from a moving vessel the recorded position *is* the view.

Measured across all 57 rendered subjects, this is the **only** camera the change moves.

## What matches

* **The camera is where the picture was taken.** 118 m from the Brooklyn tower, under the approach
  viaduct on the Brooklyn side, which is what the reference photograph shows: a brick warehouse on the
  left, the deck overhead, the ground falling away to the right.
* **The approach viaduct is modelled and it is overhead where the photograph has it overhead.** The
  through-truss deck and its piers cross the top of the frame, and the reference's deck crosses the
  same part of its frame at the same slope.
* The Sun is placed from the photograph's own timestamp — 70.7 deg elevation, almost overhead, 208 deg azimuth. The camera looks 202 deg, i.e. within 6 deg of the Sun's azimuth, so everything in frame is back-lit in both the render and the photograph.
* The East River is in the right place and its surface is flat and level (17,254 water quads).
* 5 of 5 building tiles loaded, no LOD substitution, no triangle cap on props or kit.

## What does not match

* **The Brooklyn tower — the subject the sheet names — is above the top of the frame.** At 118 m its
  103.2 m top stands **39.8 deg** above a 5.3 m eye, and a level 35 mm frame at this aspect reaches
  **21.1 deg**. The lens rule exists for exactly this and did not fire, because `subject_top` looks for
  a landmark model within 120 m of the item's recorded subject coordinate and `b_williamsburg_bridge`'s
  origin is **320.9 m** from it — the model's origin is at the middle of a 1,978 m span, not at the
  tower. With no model found it fell back to a nominal 10 m subject, which a level 35 mm lens contains
  easily, so it stayed at 35 mm. **This is the next thing to fix on this sheet**: the search radius is
  measured from an origin that, for a bridge, is nowhere near the thing being photographed. Moving the
  camera to the right place has made the framing fault visible rather than caused it — at 507 m the
  same tower needed only 11 deg and fitted.
* **The bottom half of the frame is an unbroken pale-grey plane.** The camera now stands on the street
  under the approach rather than in Domino Park, and the ground it stands on is pavement polygons with
  a flat per-kind colour: no kerb detail, no markings, no texture. The reference has cobbles, a kerb, a
  fence and a brick wall in the same area.
* **The street trees along the far edge render as opaque black cones.** Measured against the assets: each tree is 4,000–7,000 triangles of `bark_*` branches plus 800–2,300 alpha-masked `LEAF_*` cards, and the six-polygon `IMPOSTOR_*` billboard is correctly dropped (12 cards dropped in this scene). So this is not the impostor defect. It is what a dense cone of leaf cards looks like at 200 m, back-lit and in shade: a smooth, hard-edged dark triangle with no branch structure and no light coming through. The same assets read correctly — irregular, translucent, leafy — at 30–60 m in sunlight in the Washington Square Arch frame.
* The left half of the frame is a plain pale-grey block — a tile shell of the warehouse the photograph
  shows in red brick with window openings, a cornice and a downpipe. The shell has the right mass and
  none of the surface.
* The street trees that filled the old frame are gone with the camera; nothing in this frame tests them.
* The sky is a clear Nishita gradient. The photograph has strong cumulus across the whole upper half, which is most of its visual character.
* No people, no vehicles, no traffic on the bridge, no boats.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| ~~the camera stands 500 m from where the photograph was taken~~ | **fixed**: the sanity radius now applies only to a view *from* a place; a view *of* a subject accepts a photograph's GPS that is nearer the subject and on the same side of it | camera/reference metadata |
| the tower is above the top of the frame | the lens rule looks for a landmark model within 120 m of the recorded subject to measure the subject's height; `b_williamsburg_bridge`'s origin is 320.9 m away at mid-span, so it found none and used a nominal 10 m | camera/reference metadata |
| the ground is a flat grey plane | pavement polygons carry a per-kind base colour and no texture | material |
| flat glass slabs on the Domino site | building shells carry a per-material base colour with no glass BSDF and no reflection | material |
| clear sky against a cumulus photograph | Nishita atmosphere with no cloud layer | lighting |
| no people, vehicles, traffic or boats | no stage places moving objects into a still verification frame | data |
