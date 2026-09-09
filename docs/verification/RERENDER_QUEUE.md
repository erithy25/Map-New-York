# Sheets that must be re-rendered before the comparison set is final

A sheet lands here when something it depends on changed *after* it was rendered, so the published
frame is a picture of a state the repository no longer holds. The list exists so that a stale frame
is a tracked debt rather than a silent one; each entry names what changed and why the frame was not
simply re-rendered on the spot.

Nothing here is a claim about the city. A sheet in this list has an honest frame of an older build.

| sheet | what changed under it | why it waits |
|---|---|---|
| `drive_bronx_arthur_ave` | J80 — the assumed instant is now chosen to light the view instead of fixed at 09:30 | rendered before the change landed; the v15 pass does not revisit a sheet it has already done |
| `drive_bronx_grand_concourse` | J80 | as above |
| `drive_brooklyn_bed_stuy_stuyvesant_ave` | J80 | as above |
| `drive_brooklyn_park_slope_7th_ave` | J80 | as above |
| `drive_midtown_sixth_ave_45th` | J80 | as above; this one was refused at mean 0.037 and the new instant is the reason to expect a usable frame |
| `fifth_ave_42nd_north` | J80 | as above |
| `landmark_federal_hall` | J80 | as above; refused at mean 0.021, the darkest frame in the set |
| `landmark_nyse` | J80 | as above |
| `landmark_barclays_center` | J81 — the oculus canopy stood on the wrong corner of the arena and now stands on the entrance corner | the model was rebuilt while the pass was running; re-rendering a sheet the pass has already passed would race it |

**When**: after the v15 pass finishes, together with the J78 / J79 re-renders. Each sheet's assessment
is written or rewritten against the new frame, not the old one.
