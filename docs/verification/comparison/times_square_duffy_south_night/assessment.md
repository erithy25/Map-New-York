# Times Square centre: Duffy Square looking south, night

`times_square_duffy_south_night` · sheet: [`sheet.png`](sheet.png) · render record: [`render.json`](render.json)

**Reference** — File:Times Square, New York 02.jpg by Edward Charles Kendall, CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0), taken 2016-08-03 21:00:36, 1920x2560. [Commons page](https://commons.wikimedia.org/wiki/File:Times_Square,_New_York_02.jpg)

**Camera** — camera 40.75909, -73.98486 (NYC_TM -2943, 6562) z 21.5 m NAVD88 | azimuth 202.2deg pitch +0.0deg | 24 mm on 36 mm (58.7deg horizontal, 73.7deg vertical, portrait) | 904x1206. View direction: 202.2 deg, the bearing from this photograph's own GPS position to One Times Square; heading and position both come from the photograph.  The item's recorded azimuth is 203.2 deg, 1.0 deg away, and belongs to its nominal viewpoint. Aim: level optical axis (the subject is 346 m away; anything that far is photographed with a level camera).

**Sun** — azimuth 302.7°, elevation -9.5° at 2016-08-03T21:00:36-04:00 (EXIF DateTimeOriginal).

**In frame** — 6/6 building tiles (261,448 tris), 9 landmark models, 2,430 pavement polygons, 338 props, 14,635 facade-kit pieces; 4,500,039 triangles; ground mesh 215² at 2.0 m near / 40.0 m far.

**Verdict — the darkest possible verdict, and an honest one: at 21:00 on a August night Times Square renders as an unlit grey canyon with six street lamps in it. The world has almost no emissive content — no screens, no shopfront glow, no lit windows, no headlights — and this frame measures exactly how much**

## What matches

* The Sun is correctly below the horizon: elevation -9.5 deg at 2016-08-03 21:00:36 EDT from the photograph's own EXIF timestamp, direct normal irradiance 0 W/m2, so the frame is lit by sky and emissives only, which is physically what the reference is.
* Street lighting works and is the right kind. Six lamps are lit with visible beam cones on the pavement, the pole geometry (bishop's crook and cobra-head davit) is correct, and the dusk-to-dawn rule has switched them on for a night frame while the daylight frame has them off.
* The New York City flag on its 6.2 m pole is modelled, correctly proportioned and reads clearly against the dark — one of the very few objects in the frame with any character.
* The camera stands on the photograph's own EXIF GPS, 18 m from the item's nominal viewpoint, and looks along 202.2 deg, the bearing from there to One Times Square 346 m away.
* The scene is identical in content to the daylight frame (same 6/6 tiles, 2,430 pavement polygons, 338 props, 14,635 kit pieces), so the pair isolates the lighting difference cleanly.

## What does not match

* Not one window in the city is lit. The tile shells carry per-building _lit_seed_hi / _lit_seed_lo attributes at every LOD — the data for lit windows exists — but no shell material has any emission, so every tower is a dark solid. In the reference, lit windows are the second-largest light source after the screens.
* Not one sign is lit, because there are no signs. The reference is dominated by the Marriott Marquis LED wrap, the Toshiba and Coca-Cola boards, and at least twenty smaller screens; the render has none.
* No shopfront is lit. The facade kit places 14,635 pieces including 155 storefronts and 35 storefront interiors in this frame, and none of them emits, so the street-level band is black where the photograph is a continuous ribbon of light.
* No vehicle headlights or tail lights, no traffic-signal glow reaching the pavement, no police-vehicle strobes.
* No people. The reference is a crowd of several hundred filling the whole lower half of the frame; the render's plaza is empty.
* The Father Duffy memorial cross, which is the vertical anchor of the reference photograph's centre, is not modelled: props.parquet classes it as 'memorial' and there is no exported asset for that kind.
* The buildings that are visible are lit only by the Nishita night sky at 0.5 strength, which renders their upper faces as flat salmon and grey with no fall-off and no local light. Nothing about the tonality of the frame resembles a lit city.
* The exposure is opened +2.00 stops to make the frame legible; without that the render would be near-black. That is an honest compensation, not a fix — the underlying emitted radiance is one or two orders of magnitude below the real square.

## Cause of each gap

| gap | cause | class |
|---|---|---|
| no lit windows | the shells carry _lit_seed_hi/_lit_seed_lo per building but no stage authors a night facade material that consumes them; the verification stage does not invent one | material |
| no screens or billboards | no stage produces sign geometry or sign emission anywhere in the world | geometry |
| no lit shopfronts | the facade kit's storefront pieces carry no emissive material | material |
| no headlights, no traffic | no vehicle placement feeds the verification scene | data |
| no people | no crowd placement feeds the verification scene | data |
| no Father Duffy memorial | props.parquet kind 'memorial' has no exported asset (4 memorials unmapped in this frame) | data |
| frame legible only at +2 stops | consequence of the four gaps above; the world emits far less light than the real square | lighting |
