export const meta = {
  name: 'assess-sheets',
  description: 'Write, adversarially verify and (once) revise the written assessment of each comparison sheet in a batch, against the render that made it',
  phases: [
    { title: 'Write', detail: 'one writer per sheet: header from the record, both halves looked at, assessment_check must pass' },
    { title: 'Verify', detail: 'one sceptic per sheet: recompute figures, check visual claims against the images, check the verdict against the record' },
    { title: 'Revise', detail: 'a refuted assessment is rewritten once against the verdict, then verified again' },
  ],
}

const SLUGS = Array.isArray(args) ? args : (args && Array.isArray(args.slugs) ? args.slugs : [])
if (!SLUGS.length) return { error: 'pass the batch as args: ["slug", ...]' }

const SCRATCH = '/tmp/claude-0/-home-user-Map-New-York/acd234fa-9154-5ea7-ad61-034753232ccb/scratchpad/assess'

const HOUSE = `
You are writing one comparison-sheet assessment for the NYC 1:1 simulation project, repository /home/user/Map-New-York
(branch claude/nyc-1-to-1-drivable-sim-u0rmr7). Do NOT git commit or push. Do NOT run Blender or any renderer. Do not
modify any file other than docs/verification/comparison/<slug>/assessment.md. Scratch files go under ${SCRATCH}/ only.

WHAT AN ASSESSMENT IS. Each sheet pairs a reference photograph (left) with the simulation's render of the same
viewpoint (right). The assessment is the written judgement of that pairing, and it is evidence: it is read by people
deciding whether this build is a 1:1 model of New York. The project's brief says presenting approximated content as
real is the worst thing that can happen here, and its register of faults (docs/DEVIATIONS.md, J-numbered) records
two dozen cases of the same shape -- "a correct measurement of something other than the thing it stands for". Write
so that a reader can check every sentence.

THE THREE RULES THAT WERE PAID FOR:
1. **No figure that is not in that sheet's own record.** \`python3 tools/assessment_check.py <slug>\` rejects any number
   in the prose that does not appear in render.json / frame_stats.json / the generated header; historical values,
   city-wide medians and your own subtractions all fail. Either dissolve a comparison into words ("about a third",
   "half again as bright") or quote both operands as they stand in the record. Run the check until it prints \`ok\`.
2. **Look at both halves.** Four faults in this project were visible in the picture and invisible in the record. Read
   the pair image AND the full render.png AND the reference photograph with the Read tool before writing a word about
   what matches. Name what you see: the building's massing, its materials, the street, the crowd, the sky, the shadows.
3. **The record's verdicts are read against the picture, not instead of it.** \`sightline.subject_visible\` is "at least
   one of 13 rays lands on the subject" (J78) and publishes a fraction; a prop named as blocker is not a wall; a subject
   on the deck 100 m from the tower it names is J82. The lighting is metered (J83): the render's median is developed
   at middle grey, so DO NOT call a luminance ratio a fault of the city -- read \`lighting.development.stops\` (the
   physical statement: how many stops this scene needed to read as a picture; above +4 the record says under-lit) and
   frame_stats' \`exposure_offset_stops\` (how the photographer exposed relative to the same convention). A p05 gap
   under about 0.05 is the photographs' JPEG floor, not the render.

THE RHYTHM (run these, in this order):
   python3 tools/assessment_header.py <slug>      # the header block -- paste its bold paragraphs verbatim at the top;
                                                   # the indented lines under them are the record's facts to draw on
   python3 tools/sheet_brief.py <slug>            # everything quotable, in one screen
   python3 tools/sheet_pair.py <slug> 0.62 ${SCRATCH}/pair_<slug>.png   # then Read that image
   Read docs/verification/comparison/<slug>/render.png and docs/verification/reference/<slug>/<the photo file the
   header names>  -- at full size, so details are visible
   cat docs/verification/comparison/<slug>/render.json | python3 -m json.tool | less-equivalent: read the sightline,
   clearance, subject.height_probe, subject.plan_extent, lighting.development, scene.props/kit/agents blocks
   write docs/verification/comparison/<slug>/assessment.md
   python3 tools/assessment_check.py <slug>        # iterate until: ok    <slug>

IF THE SHEET WAS REFUSED (render.json status "rejected_unusable_frame": no render.png, a render_error.txt): the
assessment is of the refusal -- what the record still establishes (the height probe, the instant, the model's presence),
why the frame was refused (the camera against a slab, the metered stops at the clamp), and which J-row it is. If the
status is "not_renderable_interior": three short paragraphs saying the build models no interiors and this item is
declined, and stop.

THE SHAPE (house style, keep the headings):
# <Item name>
<the generated header: slug line, Reference, Camera, Sun, In the scene>
## Verdict — <one clause that is the honest headline>
<two to four paragraphs. Lead with what the pairing IS -- the same view or not, the subject in the frame or not,
what the record says and whether the picture agrees. Name the J-row for any known fault. Say what the reader must NOT
read into this sheet.>
## What matches
<bullets, each a concrete thing seen in both halves, with the record's figure where one exists>
## What does not match
<bullets, each a concrete gap, with figures; include the lighting as stops and exposure offset, never as "too dark">
## Cause of each gap
| gap | cause | class |
|---|---|---|
<one row per gap in the section above; class is one of: data, geometry, material, verification, performance,
reference, stated choice, or "— (not a gap)" ; a known fault carries "**DEVIATIONS Jnn**" in the class or cause>

VOICE. Direct, specific, unhedged; no praise as preamble; no filler; numbers in bold where they carry the sentence;
British-flavoured neutral English as in the exemplar. Never write "TODO" or leave a placeholder. 600 to 1,400 words.

THE J-ROWS YOU WILL MEET (docs/DEVIATIONS.md; read a row before citing it):
J57/J75/J82 subject coordinate off the thing it names · J60 photograph of somewhere else (GPS > 250 m) · J65 deck
viewpoints · J66 one material family per facade class (chroma) · J69 canopy-shaded street · J72 unknown subject height
· J74 height measured off the thing (43 rays) · J76/J78 sightline fan and fraction · J79 camera walk scores on the
subject · J80 chosen instant ("chosen, not measured") · J81 Barclays oculus corner · J83 metered development · I18
lens widened before tilt; tilt declared.

EXEMPLAR (the voice and shape to match; its numbers belong to an older render of its sheet and must not be reused):
---
## Verdict — the building is right, the frame is right, and the record's own verdict on it is wrong

**This is among the best landmark pairings in the set.** The Flatiron's wedge stands at the centre of both halves at
close to the same scale, tapering from its wide Fifth Avenue flank to the narrow prow at Twenty-third Street, with the
cornice reading as a cornice at the top and the two avenues falling away either side. Nothing about the camera is
assumed: the position is the photograph's own GPS, the heading is the bearing from that GPS to the building, and the
instant is the photograph's own EXIF, to the second.

**The measurement of the building agrees with its catalogue.** The height probe lands **17 of 17 rays** on built
fabric at the subject's coordinate and reads **85.35 m** above the ground there, off \`lm_flatiron.9\`; the catalogue
entry \`flatiron\`, 4.5 m away, publishes **86.9 m**. A metre and a half between a measured surface and a published
height, on a building whose top is a cornice rather than a point.

## What matches
* **The massing is the massing.** The triangular plan, the sharp prow, the flank running back along Fifth Avenue, the
  vertical proportion and the crowning cornice all read correctly, and at the same size in the frame as the photograph's.
* **The street furniture and fabric are right**: 5,343 kit pieces including **4,515 windows**, 356 storefronts, 70
  scaffold pieces, **52 cornices**, 67 pilasters, 51 string courses and 13 water towers — a Flatiron-district block face,
  not a bare extrusion.

## What does not match
* **The facade is a window grid where the photograph is carved stone.** The Flatiron's Renaissance-revival front
  carries a rusticated base, quoined corners, string courses, spandrel panels and a heavy modillioned cornice. The kit
  places 52 cornices, 67 pilasters and 51 string courses across the whole scene, and at this distance the building
  reads as a regular grid of openings.
* **A black SUV eight metres from the lens fills the lower left of the render.** It is a correctly placed simulated
  vehicle and it is where a car would be; it is also a third of the frame, and the photograph's foreground is open roadway.

## Cause of each gap
| gap | cause | class |
|---|---|---|
| a window grid where the photograph is carved stone | the shell is extruded from a footprint; rustication, quoins, spandrel panels and a modillioned cornice are not in the kit and the classifier has no source for them | geometry |
| a black SUV filling the lower left | a correctly placed simulated vehicle 8.0 m from the lens; placement is city-wide and the frame is not | verification |
---
`

const WRITE_RESULT = {
  type: 'object',
  properties: {
    slug: { type: 'string' },
    check_output: { type: 'string', description: 'the last line(s) of tools/assessment_check.py for this slug' },
    ok: { type: 'boolean' },
    headline: { type: 'string', description: 'the Verdict heading you wrote' },
    images_read: { type: 'array', items: { type: 'string' }, description: 'the image files you actually opened with Read' },
    word_count: { type: 'integer' },
    notes: { type: 'string', description: 'anything the orchestrator must know: a record field that contradicts the picture, a J-row that seems to apply but is not in the register, a figure you wanted and could not source' },
  },
  required: ['slug', 'check_output', 'ok', 'headline', 'images_read', 'word_count', 'notes'],
}

const VERDICT = {
  type: 'object',
  properties: {
    slug: { type: 'string' },
    refuted: { type: 'boolean' },
    figures_checked: { type: 'array', items: { type: 'object', properties: { quoted: { type: 'string' }, recomputed: { type: 'string' }, source: { type: 'string' }, agrees: { type: 'boolean' } }, required: ['quoted', 'recomputed', 'source', 'agrees'] } },
    visual_claims_checked: { type: 'array', items: { type: 'object', properties: { claim: { type: 'string' }, what_the_image_shows: { type: 'string' }, agrees: { type: 'boolean' } }, required: ['claim', 'what_the_image_shows', 'agrees'] } },
    verdict_direction_ok: { type: 'boolean', description: 'the Verdict heading and paragraphs agree with the record (subject_visible + fraction, metered stops, status) and with the picture' },
    style_ok: { type: 'boolean', description: 'headings present, cause table complete with a class per row, no placeholder, no luminance ratio presented as a fault without the exposure offset, 600-1400 words' },
    check_ok: { type: 'boolean', description: 'tools/assessment_check.py prints ok' },
    problems: { type: 'array', items: { type: 'string' }, description: 'each problem precisely enough that a writer can fix it without re-deriving' },
  },
  required: ['slug', 'refuted', 'figures_checked', 'visual_claims_checked', 'verdict_direction_ok', 'style_ok', 'check_ok', 'problems'],
}

//: What the sceptics faulted most in the first eighteen sheets, distilled so a first draft does not repeat it.
//: Every line here cost a revision round (about 250 k tokens and forty minutes a sheet).
const PREFLIGHT = `
BEFORE YOU WRITE, and again before you return -- the faults the sceptics found in the first sheets:
* Positions in a picture are fractions of its width and height, read off the image at full size, not
  impressions: "in the right fifth, two-thirds of the way from the axis to the edge", never "just right of
  centre" for something at x 1050 of 1280.  Count people, vehicles and trees at full size before you write
  a number of them; a "two pedestrians" that is four is a refutation.
* Light is measured, not inferred from the Sun's bearing.  Before saying a face is "in full sun" or "in
  shade", sample it: python3 -c with PIL over render.png, display luminance on the face's pixels, and say
  which surfaces exceed 0.7 and where the cast shadows fall.  A wall the Sun "should" light is often the one
  in shade.
* A figure is only in the prose if it is in render.json, frame_stats.json, meta.json, tools/sheet_facts.py
  output or your own PIL measurement (say so), with its source.  No distance to a thing the record holds no
  distance to; the nearest agent is the one clearance.nearest_agent names, at its recorded metres and angle
  (positive yaw is to the right).  assessment_check passing is necessary, not sufficient: it cannot see a
  figure that coincides with another field.
* The body from "## Verdict" through the end of the cause table is 600-1,400 words by \`wc -w\`; measure it.
* The record's own wording for choices: a Sun instant that was "chosen" is chosen, not measured; a
  direction "not derived from the image" is the item's heading, and the two halves need not face the same
  way -- say so in the first paragraph when it is so.
`

function writerPrompt(slug, revision) {
  return `${HOUSE}${PREFLIGHT}
YOUR SHEET: ${slug}
${revision ? `THIS IS A REVISION. A sceptic refuted the previous draft; every problem below must be fixed, and nothing
else may get worse. Read the existing assessment.md first, then the images again, then rewrite the file.
SCEPTIC'S VERDICT:
${JSON.stringify(revision, null, 1)}
` : ''}
When the file is written and assessment_check prints ok, return a WRITE_RESULT object.`
}

function verifierPrompt(slug, wrote) {
  return `You are a sceptic verifying one comparison-sheet assessment in /home/user/Map-New-York (read-only: do not modify
any file; scratch under ${SCRATCH}/ only; no git, no Blender). The assessment is
docs/verification/comparison/${slug}/assessment.md; its record is render.json and frame_stats.json beside it; the
sheet is sheet.png (or a render_error.txt if the frame was refused); the reference photograph is in
docs/verification/reference/${slug}/ (the header names the file). The writer reported: ${JSON.stringify(wrote)}.

Do all of this, and default to refuted=true if any load-bearing item fails:
1. Run \`python3 tools/assessment_check.py ${slug}\` -- it must print ok.
2. Recompute at least three of the figures the assessment quotes from render.json / frame_stats.json (e.g. the
   height probe, the metered stops, the sightline fraction, a scene count, a frame statistic) and say whether each
   agrees exactly.
3. Read the images: \`python3 tools/sheet_pair.py ${slug} 0.62 ${SCRATCH}/verify_pair_${slug}.png\` then Read it, and
   Read render.png and the reference photograph at full size. Check at least three of the assessment's visual claims
   ("the tower is at the left edge", "the render's sky is a clear gradient", "the crowd gathers at the same place")
   against what the images actually show.
4. Check the Verdict's direction against the record: subject_visible and subject_visible_fraction (J78 semantics: at
   least one of 13 rays), lighting.development.stops (metered; 'under-lit' above +4), status. An assessment that calls
   a metered luminance ratio a fault of the city without citing the exposure offset is refuted. An assessment that
   says the subject is absent when the record's fraction is > 0 and the picture shows it, or vice versa, is refuted.
5. Style: the five headings; a cause table with a class on every row; no placeholders; 600-1,400 words; the header's
   bold paragraphs present; J-rows cited where the register has them (spot-check one in docs/DEVIATIONS.md).
6. A figure that is not in the record is refuting whatever its weight -- an "off-axis 1.6 deg" that no field holds
   and that assessment_check passes only because 1.6 is the eye height is the exact fault this project keeps
   finding, "a correct measurement of something other than the thing it stands for". So is a visual claim the
   images contradict, and a description of the measuring method (how the 13 rays are laid out, what the probe
   rings are) that camera.py does not support. Any of these sets refuted=true; nothing goes in 'problems' that
   does not also refute.
Return a VERDICT object. Be precise in 'problems': quote the sentence and say what is wrong and what the right
statement is, with its source.`
}

phase('Write')
const results = await pipeline(
  SLUGS,
  slug => agent(writerPrompt(slug, null), { label: `write:${slug}`, phase: 'Write', schema: WRITE_RESULT, effort: 'high' }),
  async (wrote, slug) => {
    if (!wrote) return { slug, status: 'writer-failed' }
    let verdict = await agent(verifierPrompt(slug, wrote), { label: `verify:${slug}`, phase: 'Verify', schema: VERDICT, effort: 'medium' })
    if (!verdict) return { slug, status: 'verifier-failed', wrote }
    // A sceptic who lists a problem, or a figure or picture that disagrees, has refuted the draft whatever it
    // put in the boolean: the pilot's Flatiron verifier passed an invented "1.6 deg off-axis" as not load-bearing.
    const refuted = v => !!v && (v.refuted || (v.problems || []).length > 0
      || (v.figures_checked || []).some(f => f.agrees === false)
      || (v.visual_claims_checked || []).some(c => c.agrees === false))
    if (!refuted(verdict)) return { slug, status: 'accepted', wrote, verdict }
    const rewrote = await agent(writerPrompt(slug, verdict), { label: `revise:${slug}`, phase: 'Revise', schema: WRITE_RESULT, effort: 'high' })
    if (!rewrote) return { slug, status: 'revision-failed', wrote, verdict }
    const again = await agent(verifierPrompt(slug, rewrote) + `
THIS IS THE SECOND VERIFICATION, of a revision.  The previous verdict was:
${JSON.stringify(verdict.problems || [], null, 1)}
Check first that each of those problems is gone and nothing new was introduced in the sentences that changed
(compare against the problems' quoted text); then the three most load-bearing figures and three visual claims.
Do not re-derive the whole sheet.`, { label: `reverify:${slug}`, phase: 'Revise', schema: VERDICT, effort: 'medium' })
    return { slug, status: again && !refuted(again) ? 'accepted-after-revision' : 'still-refuted', wrote: rewrote, verdict: again || verdict, first_verdict: verdict }
  },
)

const out = results.filter(Boolean)
const tally = {}
for (const r of out) tally[r.status] = (tally[r.status] || 0) + 1
log(`assessments: ${JSON.stringify(tally)}`)
return { tally, results: out }
