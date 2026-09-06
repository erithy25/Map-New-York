# New York City Hall

`landmark_city_hall` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Cherry blossom at City Hall Park, May 1st 2024, Manhattan 03.jpg by Deans Charbal, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2024-05-01 12:33:28, 1920x1440. [Commons page](https://commons.wikimedia.org/wiki/File:Cherry_blossom_at_City_Hall_Park,_May_1st_2024,_Manhattan_03.jpg)

**Camera** — camera 40.71195, -74.00700 (NYC_TM -4817, 1329) z 13.1 m NAVD88 | azimuth 42.1deg pitch +8.0deg | 35 mm on 36 mm (54.4deg horizontal) | 1208x906. View direction: 42.1 deg, the bearing from this photograph's own GPS position to New York City Hall; heading and position both come from the photograph.  The item's recorded azimuth is 45.9 deg, 3.8 deg away, and belongs to its nominal viewpoint. Aim: aimed at New York City Hall 127 m away, at its mid-height (the city_hall model's 37 m height); +8.0 deg from horizontal.

**Sun** — azimuth 169.1°, elevation 64.3° at 2024-05-01T12:33:28-04:00 (EXIF DateTimeOriginal).

**In frame** — 4/4 building tiles (82,358 tris), 11 landmark models, 2,160 pavement polygons, 728 props, 11,513 facade-kit pieces; 4,331,761 triangles; ground mesh 205² at 2.0 m near / 40.0 m far.

**Verdict — one of the best landmark models in the set: City Hall's portico, colonnade, arcaded wings and green cupola are all present and correctly proportioned, with the Woolworth Building beside it — set on a park that is a blank grey plane where the photograph is entirely blossom, benches and people**

## What matches

* New York City Hall is recognisably itself. The central portico with its columns and pediment, the arcaded ground floor running the width of both wings, the balustraded parapet and the domed cupola with its cornice and green copper roof are all modelled and correctly proportioned against the 37 m published height.
* The Woolworth Building stands beside it at the right distance, at the right height, with its gold-brown terracotta and its dense window grid legible — the strongest facade in the frame and one of the few with real fenestration.
* The camera stands on the photograph's own EXIF GPS, 51 m from the item's nominal viewpoint, and the heading (42.1 deg) is the bearing from there to City Hall 127 m away. The aim rule tilted +8.0 deg to centre it, exactly at the limit.
* 11 landmark models are in range with their shells suppressed, so nothing is drawn twice, and the block behind City Hall reads at the right height.
* 2,160 pavement polygons, 728 props and 11,513 kit pieces are placed, and the kerb line and paving pattern read across the plaza.

## What does not match

* City Hall Park does not exist. The reference is a spring park: cherry and redbud in blossom, mature planes, iron benches, the Delacorte fountain, railings, planting beds and forty people. The render's park is one flat grey plane with a single tree and a bench on it.
* The stone has no surface: City Hall's marble and brownstone read as one uniform grey, without joints, tonal variation or weathering.
* There is no glass in any of City Hall's openings, and the windows behind the arcade are dark rectangles.
* No people anywhere, no vehicles on Park Row, no fountain, no flagpoles in front of the building.
* The foreground half of the frame is bare paving with no texture and visible facets from the graded terrain grid.
* Props were capped by the triangle budget at 728 placed.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no park: no planting, blossom, benches, fountain or railings | park planting and furniture are in no dataset the verification scene reads; props.parquet is the street-tree census | data |
| no stone surface | the landmark model carries a flat base colour per material with no texture | material |
| no glazing | neither the landmark model nor the kit supplies glass | material |
| no people or vehicles | no crowd or traffic placement feeds the verification scene | data |
| bare, faceted foreground | the pavement material is a flat colour and the terrain grid is 2 m here | material |
