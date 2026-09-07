# Fifth Avenue at 42nd Street (NYPL), street view looking north

`fifth_ave_42nd_north` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:43rd St 5th Av td (2018-05-18) 21.jpg by Tdorante10, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2018, 1920x1280. [Commons page](https://commons.wikimedia.org/wiki/File:43rd_St_5th_Av_td_(2018-05-18)_21.jpg)

**Camera** — camera 40.75416, -73.98056 (NYC_TM -2581, 6014) z 22.2 m NAVD88 | azimuth 29.0deg pitch +0.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1280x854. View direction: 29.0 deg as recorded in meta.json — the avenue's uptown heading. Aim: level optical axis.

**Sun** — azimuth 95.4°, elevation 43.5° at 2018-06-21T09:30:00-04:00 (photograph year only; 21 June 09:30 assumed).

**In frame** — 6/6 building tiles (338,848 tris), 9 landmark models, 2,218 pavement polygons, 384 props, 12,460 facade-kit pieces; 4,500,107 triangles; ground mesh 209² at 2.0 m near / 40.0 m far; kit capped by the triangle budget (22,690 in range, 12,460 placed). Frame mean 0.224, sd 0.173.

**Verdict — this sheet now compares two views of the same street in the same direction, which it did not before. Both halves look north up Fifth Avenue from the west side near 43rd Street: the avenue recedes between towers on the right and a continuous wall on the left in both. What the render still cannot show is what makes the photograph a photograph — no vehicles, no people, no markings, no shopfronts — and it is far too dark, because the file records only a year and the Sun falls back to a June morning that puts the whole canyon in shadow**

## What changed, and why

Every one of the three photographs this item shipped with was of the **New York Public Library's
facade, looking west**; the item is a view **along** Fifth Avenue, looking north. Its own assessment
said so, and the assessment of `fifth_ave_42nd_south` said the same of that sheet. Two of the nine
viewpoints brief §12 condition 3 names could therefore not be judged at all.

They passed the chooser for two reasons, both now fixed
(`pipeline/nycsim_pipeline/reference/fetch_photos.py`):

* the item's second keyword group listed `"public library"` and `"nypl"` beside the cross-street
  numbers, and the *category* "5th Avenue (Manhattan)" sits on every photograph of a building on the
  avenue — so a library facade satisfied the test that was meant to find the street. The subject test
  is now matched against a photograph's **title and description only**, never its categories, because
  a category records where a photograph *is* and not what it is *of*;
* nothing rejected a photograph whose own title announces a different subject. `not_of` does: a title
  naming the library, Bryant Park, the Empire State Building or St Patrick's is a photograph of that
  building, whatever else it mentions.

Two further rules came out of the re-fetch, and both are general rather than about this item:

* **"325 Fifth Avenue" is a building, not the avenue.** The first re-fetch picked a telephoto frame of
  a tower top titled with a street address, which satisfied `"fifth avenue"`. A required term now only
  counts where it is not preceded by a house number.
* **A Library of Congress control number marks an archival scan.** "Fifth avenue from 42nd street,
  looking north LCCN2003680996" is a c.1900 photochrom whose only recorded date is its digitisation
  date, so `min_year = 2010` could not see it.

After all four, the item's three photographs are `43rd St 5th Av td (2018-05-18)` numbers 21, 08 and
09 — street-level views along the avenue at 43rd Street. The pool is thinner than before (66 search
seeds, 5 eligible), which is the honest cost: Commons has few free photographs looking up Fifth Avenue
and many of the library beside it.

## What matches

* **Both halves face the same way**, which is the point of the change: the photograph looks north up
  Fifth Avenue from the corner of 43rd Street and the render looks north up Fifth Avenue on the
  recorded 29.0 deg uptown heading. They can now be compared on street width, storey height, kerb line
  and massing, which is what this sheet is for.
* The camera stands on the photograph's own EXIF GPS, 187 m from the item's nominal viewpoint, at 22.2 m NAVD88.
* The street section is right. Fifth Avenue's roadbed width, the west and east sidewalk widths, the kerb reveal and the crosswalk positions all match the photograph's foreground where the two overlap.
* Storey heights and setback lines up the avenue are plausible: the block faces step from six to twelve storeys with the right rhythm and the towers behind them are at the right distance.
* The New York Public Library model is placed and 81.6 m from the camera, along with seven other landmark models (One Vanderbilt at 259 m, Grand Central at 368 m, the Chrysler Building at 538 m, the Empire State Building at 582 m). The earlier report that the library was missing no longer holds.
* Real street furniture in real places: 383 props including 49 hydrants, 79 manhole covers, 22 bus-stop signs, 9 bus shelters and 17 flagpoles; 11,520 facade-kit pieces including 188 storefronts and 52 scaffold bays.
* The Sun is placed from the photograph's own EXIF instant (2017-02-16 16:24:37 EST, elevation 11.2 deg, azimuth 243.3 deg) and the low winter light and long shadows in the render match the reference's.

## What does not match

* **The render is much too dark** — frame mean 0.224 against a photograph taken in flat daylight. The
  file records only the year 2018, so the Sun falls back to 21 June at 09:30, azimuth 95.4 deg: an
  early-morning sun almost due east, with a north-facing avenue between 100 m towers entirely in
  shadow. The photograph was taken in May in the middle of the day. This is a lighting mismatch caused
  by missing EXIF, not by the world, and the sheet states the fallback.
* **The heading is still assumed, not measured.** The item names no subject, so the azimuth is the
  avenue's own uptown heading rather than anything derived from the image (deviation I7). It happens to
  agree here; nothing in the metadata proves it.
* No people. The reference has about forty, including a group crossing the frame at 8 m; the render has none, so the near-foreground crosswalk reads as empty grey.
* No vehicles anywhere on the avenue.
* No road markings. The crosswalk in the reference is a broad zebra with a stop bar and lane lines; the render's crosswalk polygons are flat light-grey rectangles with no stripes.
* The bare street trees are still near-solid dark cones. The opaque impostor cards are dropped (12 in this frame) but the branch geometry itself reads as a mass rather than as winter branches, and there are eleven of them lining the avenue.
* A street lamp column stands about 1.5 m from the lens and runs the full height of the frame. That is where props.parquet puts a lamp and where the photograph's own GPS puts the camera, but a photographer would have stepped around it.
* The buildings have unglazed window dashes and no cornice, sill or reveal shadow — the storefront band on the right is a flat green stripe with no glass, no lettering and no awning.
* The bottom 40 % of the frame is bare grey sidewalk and roadbed with no texture, no expansion joints, no gratings, no litter and no tonal variation.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| ~~the two halves face different ways~~ | **fixed**: the chooser now requires the photograph's own title or description to name the street, rejects one titled after a building on it, rejects a street address as a street name, and rejects archival scans | reference |
| the render is too dark to compare on tone | the file records only a year, so the Sun falls back to 21 June 09:30 and a north-facing canyon is in shadow | lighting |
| no people, no vehicles | no crowd or traffic placement feeds the verification scene | data |
| no road markings | pavement polygons carry a kind but no stripe geometry and no texture | material |
| trees read as solid cones | the leaf-off branch model is dense and untextured | material |
| a lamp column across the lens | the photograph's GPS puts the camera within 1.5 m of a real lamp post; nothing moves an unblocked camera off one | camera |
| flat facades, no glass or lettering | shells carry a per-material base colour and the kit supplies openings without glazing, mullions or signage | material |
| featureless pavement | the pavement material is a flat base colour per kind with no texture map | material |
