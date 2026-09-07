# Williamsburg Bridge from Domino Park

`landmark_williamsburg_bridge` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Williamsburg Bridge June 2022 003.jpg by Kidfly182, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2022-06-28 13:38:05, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Williamsburg_Bridge_June_2022_003.jpg)

**Camera** — camera 40.71650, -73.96680 (NYC_TM -1420, 1832) z 4.3 m NAVD88 | azimuth 199.4deg pitch +0.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1208x906. The camera stands on the item's recorded viewpoint: this photograph's own EXIF GPS is 389 m away, past the 250 m at which it could still be the same view, so it was rejected as mis-tagged. Heading 199.4 deg as recorded, which agrees with the bearing from that position to the Brooklyn tower (199.5 deg) to 0.1 deg. Aim: level optical axis (the subject is 507 m away).

**Sun** — azimuth 208.0°, elevation 70.7° at 2022-06-28T13:38:05-04:00 (EXIF DateTimeOriginal).

**In frame** — 10/10 building tiles (235,926 tris), 2 landmark models, 2,184 pavement polygons, 326 props, 3,936 facade-kit pieces; 2,076,582 triangles; ground mesh 235² at 2.0 m near / 40.0 m far, 19,424 quads on the flattened East River surface.

**Verdict — the bridge model itself is the best-modelled thing in any of these five frames, and it is also 500 m too far away to be the picture: the photograph was taken from directly under the Brooklyn tower and the render stands at the far end of Domino Park, because the rejection rule threw away a camera GPS that was in fact correct. What is left is a small correct bridge behind a two-metre flagpole**

## What matches

* **The bridge is modelled properly and it renders properly.** The Brooklyn tower is a steel lattice with X-braced panels and a cross-braced portal; the main cables sag between the towers with individual suspenders hanging from them; the deck is a through-truss with a visible Warren web running the full span; the approach viaduct carries on past the tower. Every one of those is legible at 500 m. Nothing else in this pass is modelled to that level.
* The bridge's silhouette against the sky matches the photograph's proportions: the tower's height above the deck, the deck's depth relative to the tower, and the cable's sag are all in the right ratio.
* The Sun is placed from the photograph's own timestamp — 70.7 deg elevation, almost overhead, 208 deg azimuth. The camera looks 199 deg, i.e. within 9 deg of the Sun's azimuth, so everything in frame is back-lit in both the render and the photograph. That is why the render's steelwork is a pale silhouette and the trees are dark.
* The East River is in the right place and its surface is flat and level (19,424 water quads on the tile's flattened water surface).
* 10 of 10 building tiles loaded, no LOD substitution, no triangle cap on props or kit.

## What does not match

* **The camera is 500 m from where the photograph was taken, and the rejection rule is why.** This photograph's EXIF GPS is 40.71318, -73.96827, which is 117 m from the item's recorded subject (the Brooklyn tower) and directly beneath the bridge deck — exactly where the photograph, which is aimed steeply up at the underside of the deck from beside a brick pump house, was plainly taken. The item's *nominal* viewpoint is at the north end of Domino Park, 506 m from the tower, and does not correspond to this photograph at all. The 250 m rule assumes the nominal viewpoint is the reliable one and the camera GPS the suspect one; here it is the other way round, and a correct GPS was discarded as "mis-tagged". This is the single largest error in the sheet, and it is a rule error, not a world error.
* **A flagpole 2.3 m from the lens runs the full height of the frame down the middle.** `prop_flag_nyc_pole_0` is recorded as the nearest obstruction in the view cone at 2.3 m; the clearance check did not treat it as a block because it stands only 2.3 m from a camera that still has 150 m of clear view past it. It splits the frame in two and hides part of the bridge. A second, rusted standard stands a few metres to its right. A photographer standing on that pier would simply take a step.
* **The bottom 55 % of the frame is an unbroken pale-grey plane.** Domino Park itself — its raised walkway, the sugar-crane trestle, the elevated catwalk, the seating, the syrup tanks — is not modelled. The pavement polygons that are drawn carry a flat per-kind colour, and the only park furniture in shot is three bike hoops and a lamp standard.
* **The street trees along the far edge render as opaque black cones.** Measured against the assets: each tree is 4,000–7,000 triangles of `bark_*` branches plus 800–2,300 alpha-masked `LEAF_*` cards, and the six-polygon `IMPOSTOR_*` billboard is correctly dropped (12 cards dropped in this scene). So this is not the impostor defect. It is what a dense cone of leaf cards looks like at 200 m, back-lit and in shade: a smooth, hard-edged dark triangle with no branch structure and no light coming through. The same assets read correctly — irregular, translucent, leafy — at 30–60 m in sunlight in the Washington Square Arch frame.
* The left half of the frame is two tall flat slabs: a blue-grey glass mass with sparse dashed window rows and a cream tower behind it. These are the new Domino-site residential buildings as tile shells; in the photograph the equivalent quadrant is the red brick pump house and the bridge's masonry anchorage, both of which the photograph shows at close range and this camera cannot see.
* The Domino Sugar Refinery landmark model is in the scene at 233 m and projects across pixel columns 164–929 with its top at 76–258 px, but it is hidden behind those tile shells and does not appear in the frame.
* The sky is a clear Nishita gradient. The photograph has strong cumulus across the whole upper half, which is most of its visual character.
* No people, no vehicles, no traffic on the bridge, no boats.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| the camera stands 500 m from where the photograph was taken | the photograph's own EXIF GPS was rejected as mis-tagged by the 250 m rule, but it is the correct position and the item's nominal viewpoint is the wrong one. The rule has no way to tell which of the two is wrong; it should prefer the GPS when the GPS is closer to the recorded subject than the nominal viewpoint is, as it is here (117 m against 506 m) | camera/reference metadata |
| a 2.3 m flagpole splits the frame | the clearance test only rejects an eye point when something is inside 1 m of the lens or the view closes off; a thin prop 2.3 m away with 150 m of street behind it passes both | camera/reference metadata |
| no Domino Park: no walkway, crane trestle, catwalk, seating or tanks | park structures are neither buildings nor road polygons, so no stage produces them | geometry |
| street trees as opaque black cones | a dense cone of alpha leaf cards at 200 m, back-lit and in shade, has no resolvable structure; the assets themselves are correct and their impostor cards are dropped | material |
| flat glass slabs on the Domino site | building shells carry a per-material base colour with no glass BSDF and no reflection | material |
| clear sky against a cumulus photograph | Nishita atmosphere with no cloud layer | lighting |
| no people, vehicles, traffic or boats | no stage places moving objects into a still verification frame | data |
