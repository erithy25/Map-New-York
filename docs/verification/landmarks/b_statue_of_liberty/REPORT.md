# Statue of Liberty

Script: `blender/landmarks/b_statue_of_liberty.py` · agent B · generated 2026-09-06 14:10 UTC

## Placement

Fort Wood's real OSM ring (way 32965412), centroid NYC_TM (-7994.2, -1180.5); statue confirmed by OSM way 433053921 (height 93 m = the published 305 ft 1 in).

## Published dimensions

* **Ground level to the tip of the torch: 305 ft 1 in = 92.99 m**, made up of
  **65 ft = 19.81 m** foundation / Fort Wood star, **89 ft = 27.13 m** pedestal and
  **151 ft 1 in = 46.05 m** statue (the "46 m figure" of the build brief).
* Statue detail [NPS]: heel to top of head **111 ft 1 in = 33.86 m**; head from chin to cranium
  **17 ft 3 in = 5.26 m**; right arm **42 ft = 12.80 m** long; hand **16 ft 5 in = 5.00 m**; index finger
  **8 ft = 2.44 m**; the tablet **23 ft 7 in x 13 ft 7 in x 2 ft = 7.19 x 4.14 x 0.61 m**, inscribed JULY IV
  MDCCLXXVI; the crown carries **7 rays**; the copper skin is **3/32 in = 2.4 mm** thick (repousse over Eiffel's
  iron armature).
* **Pedestal** (Hunt): **62 ft = 18.90 m square at the base**, **40 ft = 12.19 m square at the top**, 89 ft tall,
  Stony Creek granite over concrete, with the Doric loggia and the four corner projections.
* **Fort Wood**: an **eleven-pointed star** built 1808-1811; its real plan is OSM way ``32965412`` (97 x 97 m).

## Honesty statement

The figure is a stylised sculpt, not a scan or a photogrammetric model.**  It is built from 38 metaball elements
(legs and drapery, torso, both arms, neck, head) meshed at a 0.80 m metaball resolution and then smoothed with one
level of Catmull-Clark subdivision, exactly as the build brief specifies.  The published proportions above set the
positions and radii of those metaballs, so the silhouette and the overall dimensions are right, but **the drapery
folds, the face, the sandal, the broken chains at the feet and the repousse surface are not reproduced** — anyone
comparing this model with a photograph will see a correct silhouette and an invented surface.

## Verification renders

Three verification renders, each framed to answer one question.

    1. ``from_the_ferry`` — 420 m out on a bearing of 170 deg, which is where the Statue Cruises ferry passes and
       where the statue's front-right (torch arm and tablet) faces the camera.  Question: is the 92.99 m
       ground-to-torch composition right — a 19.81 m star fort, a 27.13 m pedestal and a 46.05 m figure — and does
       the silhouette read as the Statue of Liberty?
    2. ``from_the_island`` — 105 m out at eye height on the same bearing.  Question: does the pedestal's batter
       (18.90 m square down to 12.19 m) and its Doric loggia read, and is Fort Wood's eleven-pointed plan visible?
    3. ``figure`` — a long lens level with the statue's waist.  Question: is the figure's posture right — the
       raised right arm with the torch, the tablet in the lowered left arm, the seven-ray crown — and is it
       recognisably a *sculpt*, not a scan (see the honesty statement in the docstring)?

## Not modelled

the interior spiral stair and Eiffel's armature, the museum inside the pedestal, the drapery folds,
the face and crown detail beyond the seven rays, the broken chains at the feet, the flame's gilded texture (an
emissive gold material is used), and the island's landscaping and buildings (a separate landmark would carry them).

## Polycounts / outputs

* `blender_out/landmarks/b_statue_of_liberty.glb` — 19,812 triangles, 0.47 MB, bounds min ['-45.3', '-58.6', '-2.0'] max ['51.7', '38.3', '96.0']
* `blender_out/landmarks/b_statue_of_liberty_lod1.glb` — 1,704 triangles, 0.09 MB, bounds min ['-45.3', '-58.6', '-2.0'] max ['51.7', '38.3', '96.0']
