# American Museum of Natural History

`landmark_amnh` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:AmericanMuseumOfNaturalHistory2020FrontEntrance.jpg by DanielPenfield, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2020-01-01 11:24:55, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:AmericanMuseumOfNaturalHistory2020FrontEntrance.jpg)

**Camera** — 40.780672, -73.972842 (NYC_TM -1950, 8930) at z 28.3 m NAVD88 | azimuth 308.0°, pitch +4.0° | 35 mm on 36 mm (42.2° horizontal, portrait) | 904x1206.

**Sun** — azimuth 171.2°, elevation 25.7° at 2020-01-01T11:24:55-05:00 (EXIF DateTimeOriginal); 727.7 W/m² direct normal, sky at strength 0.0376, Filmic, +4.71 stops.

**Subject** — American Museum of Natural History (Central Park West entrance) at 118.9 m.

**In the scene**, within 619.6 m of the camera and not all of it in frame — 4 building tiles (276,676 tris), 5 landmark models of which **1 can fall inside the 42.2° frame**, 14,973 pavement polygons (4,547 sidewalk, 3,844 white, 3,789 roadbed, 1,959 curb, 411 median, 181 crosswalk, 121 parking lot, 104 yellow, 17 plaza), 5229 props of the 5,287 in range, 34 kit pieces, 84 vehicles and 181 people; 2,938,020 triangles. Ground mesh 83,198 triangles, 0 holes. 18 city surfaces are dressed from the shared photographic catalogue.

## Verdict — a slice of the museum's flank at twenty-six metres, passed as the entrance by a subject coordinate that is under the museum's own roof

**The two halves are of the same building and not of the same thing.** The photograph is the Theodore Roosevelt Memorial: four Ionic columns, the arch with the T. rex banner in it, the statue pylons, the inscribed attic, the equestrian statue on its plinth, the steps, the pavement and a crosswalk across Central Park West in the foreground, under a fifth of a frame of blue sky. The render is a wall: a pale speckled facade filling the top seven-tenths of the frame edge to edge, four round-arched openings along the ground storey (the right-hand one cut by the frame), a string course, three rows of rectangular windows in five bays with the top row cut by the frame's edge; below it a green verge, grey roadbed with one white marking, and one bare tree at two-fifths of the width. No column, no statue, no steps, no sky. The camera is the photograph's EXIF GPS, **38.3 m** from the item's recorded viewpoint; the heading is the bearing from that GPS to the subject coordinate, **308.0°**, against the item's own **288.3°**, **19.7°** away.

**The record says the subject is visible, 13 of 13, and every one of those rays stopped well short of it.** The subject coordinate is **118.9 m** from the placed camera (`subject_range_m` **119.2**); the sightline fan lands at **26.2 m** on `lm_c_american_museum_natural_history.1`, and the field that records this is `subject_rays_on_own_fabric_nearer_than_recorded`: **13**. J78's rule — one ray on the named model — passes it at a fraction of **1.0**. The height probe tells the rest: at the subject's coordinate **43 of 43** rays land on built fabric and read **32.09 m** above the ground there, off `lm_c_american_museum_natural_history.3`, **40.3 m** from the catalogue origin whose published height is **44.8 m**. A point named *Central Park West entrance* has thirty-two metres of building standing on it: the coordinate is inside the block, on the roof of the range, not on the memorial's face — the J57/J82 shape, a subject coordinate off the thing it names — and the camera was aimed, pitched (**+4.0°**) and walked on it.

**The camera walk did what J79 asked and it made the frame worse.** The GPS viewpoint was "boxed in: the view azimuth is closed off 18 m ahead, less than the 57 m this frame needs to show its subject", so the camera moved **36.0 m** to the left, ranked on the subject sightline (`scored_on_subject_sightline` true). No point within 80 m had 57 m of open air along the azimuth, so the frame is closed off at **26.2 m** by the museum's own fabric, the nearest built thing in it is `t_-2_8_park_park_ground_grass` at **15.4 m**, and no simulated agent stands within **20 m**. Thirty-six metres along Central Park West takes the lens off the memorial's axis onto the plain range beside it.

**What the reader must not read into this sheet:** that the model lacks the memorial. The catalogue entry says it carries the columns, the arch, the pylons and the **44.8 m** attic; none of that is in this frame, which cannot say whether it is right. Nor is the flatness a light fault of the city: the scene metered **+4.71** stops (the physical rule alone would have given **+0.75**), above the **4** a photographer recovers hand-held, and the record marks it under-lit and publishes it anyway.

## What matches

* **The instant, the sun and the season.** Sun azimuth **171.2°**, elevation **25.7°**, from the photograph's own EXIF, on a Wednesday drawn as a weekday. Bare trees in both. Sampled with PIL on `render.png`, the direct light comes from behind-left as in the photograph: the right-hand jamb of every window is the lit one, the branch shadows on the upper-right stone fall to the right, and the upper stone at the left edge is the brightest surface in the frame, above seven-tenths display luminance over nearly all of it, while the openings sit under two-fifths.
* **The material family.** Pale speckled stone over asphalt in both halves; chroma ratio **0.879** (**0.0707** against **0.0804**).
* **The building's plan is measured, not looked up.** The object under the coordinate is **264.7 m** by **190.7 m** in plan, a museum-sized thing, **43 of 43** probe rays on built fabric.
* **The frame is empty of agents because the walk left them behind, not because the crowd failed.** **181** pedestrians and **84** vehicles were placed in the ring; the nearest-agent probe finds none within **20 m**.

## What does not match

* **The subject.** The photograph's subject is the memorial arch, centred at about half the width with the equestrian statue at three-fifths; the render's is a four-arch, five-bay slice of range wall at **26.2 m**, and the coordinate both are supposed to share has **32.09 m** of building on top of it.
* **The scale of the view.** The photograph holds the whole memorial with sky above it; the render's **42.2°** lens spans roughly twenty metres of wall at **26.2 m** and the frame top cuts the third row of windows.
* **The people and the vehicles.** Counted at full size, the photograph has 24 people along the steps and pavement (ten by the left pylon, one crossing the middle, thirteen by the plinth and right pylon), a white Ford Edge and the tail of a yellow taxi at the kerb, and pigeons on the plinth. The render has no person, no vehicle, no bird.
* **The tone range.** Render p05 **0.2942** against the photograph's **0.102**; sd **0.1478** against **0.2379** (ratio **0.621**); p95 **0.7425** against **0.8254**. The photograph's darks — portico, bronze, winter coats — are outside the render's frame. The photographer exposed at **-0.044** stops against the middle-grey convention and the render sits at **0.24**; the **0.284**-stop ratio is that, and the mean ratio of **1.181** follows from it.
* **The stops.** **+4.71** metered, and the record's own note calls the scene under-lit: **727.7 W/m²** direct normal with the sun at **25.7°** onto a facade seen from behind-left, and the linear median still came out at **0.006858**. That is the number to read the frame by.
* **Nothing carved.** The photograph's memorial carries statues in niches, a frieze of animals along the base, inscriptions and a bronze; the render's storey is `tower_tier` fenestration, **14** window pieces and **17** parapet pieces in the whole scene, and the catalogue itself declares the frieze, inscriptions and the statue's figures not modelled.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| a range wall at 26.2 m, not the memorial at 118.9 m | the subject coordinate sits under 32.09 m of the museum's own roof, 40.3 m from the model origin; the sightline lands on own fabric at 26.2 m of 119.2 m and J78's rule counts it as the subject — the J57/J82 shape, not yet a row of its own | verification (**DEVIATIONS J57 / J82 / J78**) |
| the lens off the memorial's axis on the plain range | the walk moved 36.0 m left to open the azimuth to a coordinate inside the block (**DEVIATIONS J79**); the heading is the bearing to that coordinate, 19.7° from the item's own | verification |
| twenty metres of wall, no sky | the frame is closed off at 26.2 m; at that range a 42.2° lens cannot hold a 44.8 m building | verification |
| no people, vehicles or pigeons against 24 people, two cars and a flock | the walk placed the lens where no agent stands within 20 m; pigeons are not simulated | — (not a gap) |
| p05 0.2942 against 0.102, sd ratio 0.621 | the photograph's darks are outside the render's frame; the metered development is not the cause (**DEVIATIONS J83**) | verification |
| +4.71 stops needed, physical rule +0.75, record says under-lit | metered development on a frame that is one lit wall and a road (**DEVIATIONS J83**); the record publishes the number | stated choice |
| a window grid where the photograph is carved limestone | the range is `tower_tier` fenestration; frieze, inscriptions and statue figures are declared not modelled in the catalogue entry | geometry |
