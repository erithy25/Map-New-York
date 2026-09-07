# Reference photography — stage report

Stage: **reference** (project brief §12.3 and §13; ARCHITECTURE.md §14; ADR-012).
Run: 2026-09-06. Producer: `pipeline/nycsim_pipeline/reference/fetch_photos.py`.

Real, openly licensed photographs of every verification subject, with the licence, author, date,
camera GPS and an estimated photographer viewpoint recorded per photo, so that Cycles renders of the
generated city can be put beside a photograph of the same place from the same position.

## 1. What was built

| File | What it is |
|---|---|
| `pipeline/nycsim_pipeline/reference/fetch_photos.py` | the fetcher: catalogue of 172 subjects, Commons search/geosearch/imageinfo client, licence and content filters, downloader, viewpoint estimator, index/licence/summary writers, CLI |
| `pipeline/tests/test_reference_fetch_photos.py` | 22 pytest tests (pure functions, catalogue consistency, selection rules, viewpoint estimation, an offline end-to-end run against a fake client) |
| `docs/verification/reference/<slug>/1..n.jpg` | 519 photographs, ≤ 1,920 px wide, 426.0 MB |
| `docs/verification/reference/<slug>/meta.json` | per subject: viewpoint, subject, queries, candidate/rejection counts; per photo: title, Commons page URL, file URL, download URL, author, credit, licence name + URL + template, date taken and its source, camera GPS, original and stored pixel size, bytes, sha256, mean luminance, description, categories, provenance, score, estimated viewpoint with its explanation, and a ready-made attribution line |
| `docs/verification/reference/INDEX.md` | one row per subject: group, photo count, licences, year range, viewpoint lat/lon, azimuth, confidence, status |
| `docs/verification/reference/LICENSES.md` | every one of the 519 files with author, licence, licence URL, date and camera GPS — the attribution list |
| `docs/verification/reference/summary.json` | machine-readable totals, per-item counts and rejection histograms |

Re-runnable and resumable: `python -m nycsim_pipeline.reference.fetch_photos` skips any subject whose
`meta.json` is complete and whose files are present at the recorded size. `--revalidate` re-tests the
stored photographs against the current selection rules and re-fetches only the subjects that now fail;
`--index-only` regenerates the three index files with no network access.

## 2. Coverage

172 subjects, **every one with at least one photograph**; 519 photographs, mean 3.0 per subject.

| group | subjects | photos | MB |
|---|---|---|---|
| viewpoint (the 7 mandated views; Times Square day + night, Fifth Ave both directions) | 9 | 34 | 31.6 |
| drive_through (the 5 mandated areas, 2 blocks each) | 10 | 30 | 25.7 |
| landmark (every structure named in `docs/LANDMARKS.md`) | 133 | 394 | 320.8 |
| streetscape | 16 | 45 | 36.8 |
| vehicle | 4 | 16 | 11.1 |
| **total** | **172** | **519** | **426.0** |

**The seven mandated viewpoints** — Brooklyn Heights Promenade → Lower Manhattan (4 photos), Top of the
Rock looking south (4), Duffy Square looking south by day (4) and by night (4), Fifth Avenue at 42nd
Street north (3) and south (3), Bethesda Terrace and Fountain (4), Staten Island Ferry deck → Lower
Manhattan (4), Washington Street in DUMBO with the Manhattan Bridge (4).

**The five drive-through areas** — Midtown (Sixth Ave at 45th St), Lower Manhattan (Broadway at Wall St;
Stone St), a Brooklyn brownstone block (Park Slope Seventh Ave; Bed-Stuy Stuyvesant Ave), a Queens
two-family residential street (Forest Hills Gardens; Jackson Heights; Bayside), the Bronx Grand
Concourse (plus Arthur Ave). Three photographs each.

**Landmarks** — all 133 subjects carry 2–4 photographs (minimum 2). Every structure named in
`docs/LANDMARKS.md` groups A, B and C is present; the test
`test_every_landmark_in_docs_landmarks_md_has_a_subject` asserts the mapping for 132 named structures.

**Streetscapes and vehicles** — tenement with fire escapes, SoHo cast-iron block, NYCHA tower campus,
Queens vinyl-sided houses, Staten Island houses, two elevated-subway streets (Roosevelt Ave under the 7,
Broadway under the J), a Midtown avenue at rush hour, wet-night Times Square, snow on a Brooklyn street,
street-name signs, traffic and pedestrian signals, hydrant, LinkNYC kiosk, newsstand, sidewalk shed,
yellow cab, MTA bus, NYPD car, FDNY engine.

## 3. Licence and quality profile

| | |
|---|---|
| Licences | CC BY-SA 4.0 × 337, CC BY 4.0 × 53, CC BY 2.0 × 44, CC0 × 27, CC BY-SA 3.0 × 21, CC BY 3.0 × 16, CC BY-SA 2.0 × 13, public domain × 8 |
| Non-free files accepted | **0** — every stored file passes `licence_ok` (CC0 / CC BY / CC BY-SA / public domain only), re-checked after the run |
| Taken 2015 or later | 491 of 519 (94.6 %); none undated; oldest kept 2010, with per-subject `min_year` raised for new buildings (2019 for Hudson Yards, 2021 for Moynihan Train Hall, 2022 for TSX Broadway) |
| Camera GPS present | 474 of 519 (91 %) |
| Stored width | 960–1,920 px (the standard Commons rendition widths at or below the 2,000 px limit) |
| Daylight vs night | enforced twice: night words reject a daylight subject and the reverse, then the decoded image's mean luminance must fall inside the subject's band |

Attribution: `LICENSES.md` carries the line for every file, and each `meta.json` photo record has a
ready-made `attribution` string. CC BY-SA files require share-alike, so a side-by-side comparison sheet
built from them must itself carry CC BY-SA and the author credits.

## 4. Viewpoint estimates

Every photograph records an estimated photographer position (WGS84) and camera azimuth with a sentence
saying how it was derived:

| method | photos | how |
|---|---|---|
| `camera_gps_to_subject` (high confidence) | 377 | the file's own camera GPS; azimuth = initial great-circle bearing from it to the subject |
| `standard_viewpoint` and its variants (medium) | 93 | no usable GPS, or GPS on the subject rather than the camera, or GPS beyond the subject's plausibility limit → the catalogued photographer position and its bearing to the subject |
| representative (low) | 49 | generic subjects (a hydrant, a cab): the position is where such a photograph is typically taken, and the explanation says so |

Two classes of bad metadata are handled explicitly rather than silently:

* **Wrong place.** A candidate whose camera GPS is more than 100 km from the subject is rejected
  (`wrong_place`). This caught a photograph of *Daqing* Times Square in China and one of Dülmen,
  Germany — both had passed the text filters.
* **Missing hemisphere sign.** A longitude written `+73.98550` instead of `-73.98550` is corrected when
  flipping the sign puts the camera at the subject, and the correction is stated in that photo's
  `estimated_viewpoint.explanation`.

Every `viewpoint_note` was checked against the geometry it describes: the compass word in
"looking &lt;direction&gt;" and in "&lt;direction&gt; of the building" must agree with the computed
azimuth to within 1.5 compass points (test `test_viewpoint_notes_agree_with_the_computed_geometry`).
Four notes were corrected to match the numbers (Lincoln Center, the Municipal Building, Trinity Church,
the Apollo Theater).

## 5. How it was verified

```
$ PYTHONPATH=pipeline python3 -m pytest pipeline/tests/test_reference_fetch_photos.py -q
22 passed
```

```
$ python -m nycsim_pipeline.reference.fetch_photos --index-only --revalidate
revalidate: 0 item(s) dropped for re-fetch
items 172 / 172, photos 519, bytes 425,961,932, items_without_photo []
items_partial [sheep_meadow 2/3, lincoln_tunnel_portal 2/3, kosciuszko_bridge 2/3,
               35_hudson_yards 2/3, two_times_square 2/3, traffic_signals 3/4, newsstand 2/3]
```

Independent integrity sweep over all 519 files — bytes, sha256, decoded size and format, licence,
viewpoint inside the NYC bounding box, azimuth in range, non-empty explanation and attribution, camera
GPS plausible: **0 failures**; widths 960–1,920 px; 426.0 MB; no stray files; 172 subject directories
matching the catalogue exactly.

Photographs were opened and looked at, not only counted. Spot checks confirmed the mandated views are
the views claimed: the Promenade frame shows Lower Manhattan across the East River (2024); Duffy Square
at night shows the Father Duffy statue with the bowtie behind it; Bethesda Terrace shows the fountain
from the upper terrace with the Lake behind; the ferry frame shows the Lower Manhattan skyline from the
water; the DUMBO frame is the Manhattan Bridge tower arch framing the Empire State Building. A
title/description sweep for scans, drawings, postcards, construction shots and similar non-photographs
across all 519 files returned 4 hits; all four were removed by tightening the rules and re-fetching,
and the sweep is now clean.

## 6. Gaps and what could not be reached

1. **`street_staten_island_ranch_houses` — 1 photograph, not 2–4.** Commons has essentially no freely
   licensed street photography of ordinary Staten Island tract housing. A borough-wide title and
   category search returns parks, stations, churches and civic buildings, and
   `incategory:"Houses in Staten Island"` returns nothing at all. The single on-target file (*Typical
   house in Dongan Hills (built in 1960)*, CC BY-SA 4.0) is kept and the subject's `want` is set to 1,
   with the reason in a code comment, rather than padding the subject with photographs of something
   else. This is the only subject below the two-photograph floor.
2. **Seven subjects at 2 or 3 photographs instead of 3–4** (Sheep Meadow, the Lincoln Tunnel portal,
   the Kosciuszko Bridge, 35 Hudson Yards, Two Times Square, traffic signals, the newsstand). The
   candidate pool was exhausted after licence, date and content filtering; each `meta.json` records
   `"exhausted": true` and the rejection histogram showing why.
3. **2 World Trade Center is absent by intent.** `docs/LANDMARKS.md` lists "2/3/4/7 WTC"; 2 WTC has
   never been built above its podium, so there is nothing to photograph. 3, 4 and 7 WTC are present.
4. **Two Times Square was located from its street address** (714 Seventh Avenue) because it has no
   Wikipedia coordinate; the other landmark coordinates come from Wikipedia/Wikidata or are well-known
   fixed points. Its two photographs show the correct wedge at the north end of the bowtie.
5. **Street-axis subjects carry the subject's azimuth, not the photograph's.** For a "looking north up
   Fifth Avenue" subject nothing in the file metadata gives the camera heading, so the recorded azimuth
   is the street heading of the reference view, and every such explanation says exactly that ("not
   derived from the photo"). Where such a photograph looks across the street rather than along it, the
   numeric azimuth still describes the reference view, not that frame.
6. **Originals are never downloaded.** upload.wikimedia.org now answers original-resolution requests
   from unauthenticated clients with HTTP 429 and `Retry-After: 600`, and renders only a fixed set of
   thumbnail widths (250/500/960/1280/1920 — any other width is HTTP 400 "Use thumbnail sizes listed on
   https://w.wiki/GHai"). The fetcher therefore takes the largest standard rendition ≤ `--max-width`,
   which is why stored widths are 960–1,920 px rather than exactly 2,000. A file whose original is
   between 900 and 960 px wide has no usable rendition; for those the fetcher makes one polite attempt
   at the original and otherwise moves on to the next candidate.

## 7. API etiquette actually observed

* User-Agent `NYCSim-reference-fetch/1.0 (<project URL>) python-requests/<version>` — a project URL,
  never a personal address; overridable with `NYCSIM_CONTACT`.
* At most 2 requests/second by construction (`--min-interval`, floor 0.5 s; the full pass ran at 1.1 s,
  ≈ 0.9 req/s), `maxlag=5`, exponential back-off honouring `Retry-After` on 429 and 5xx.
* One generator request per search returns both the search results and their `imageinfo`
  (`generator=search` / `generator=geosearch` with `prop=imageinfo`), which cut API calls per subject
  from 7 to 3.
* 1,532 HTTP requests in total for 519 photographs across all passes; 6,717 s of wall clock, most of it
  spent in rate-limit back-off rather than transfer.
* Resumed rather than re-fetched throughout: the rule-tightening passes re-downloaded only the subjects
  that failed revalidation.

## 8. What the next agent needs to know

* **Where the ground truth is.** For a subject `<slug>`, `docs/verification/reference/<slug>/meta.json`
  gives `viewpoint.lat/lon/azimuth_deg` — the camera to place in Blender — and, per photograph,
  `estimated_viewpoint.lat/lon/azimuth_deg` for that specific frame. Use the per-photo estimate when its
  `confidence` is `high` (377 of 519); otherwise use the subject-level `viewpoint`.
* **Camera height is not recorded.** Commons files carry no reliable altitude. Assume eye level
  (≈ 1.6 m above ground) for street subjects, and the published observation-deck height for
  `top_of_the_rock_south` (70th floor of 30 Rockefeller Plaza).
* **Field of view is not recorded either.** Focal length is outside the extmetadata subset requested, so
  frame the render on the subject rather than trying to match the lens. The DUMBO and skyline frames in
  particular are long-lens shots.
* **Licences propagate.** A side-by-side sheet containing a CC BY-SA photograph is a derivative: publish
  the sheet CC BY-SA and carry the author line from `LICENSES.md`.
* **Size.** 426 MB of JPEG under `docs/`. Every file's source URL and sha256 are in `meta.json`, so the
  set is exactly re-fetchable; if the orchestrator prefers the texture treatment (git-ignored,
  re-fetchable), ignore `docs/verification/reference/**/*.jpg` and keep the `.md`/`.json` files, which
  total 1.4 MB.
* **Adding a subject** is one `_it(...)` or `_lmk(...)` entry in `CATALOGUE` plus a re-run; existing
  subjects are skipped. `_lmk` places the photographer at a bearing and distance from the subject, so
  the prose note and the azimuth cannot drift apart.
