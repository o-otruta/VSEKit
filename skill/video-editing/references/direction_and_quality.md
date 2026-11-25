# Direction and quality — how to make the edit good, not just correct

The rest of the skill makes an edit *technically* right (fps, loudness, safe zones). This file is about
making it *worth watching*, and about being honest on what was actually checked. Read it before planning
any piece where motion, pacing or graphics carry the video: intros, trailers, title/end cards, Shorts hooks,
explainers, product/UI demos, motion pieces. For a plain talking-head cut, sections 2 (lightly) and 3 still
apply; section 1's camera rules mostly don't.

> Credit: the three-pillar structure (quality defaults → direction before build → mandatory iteration with
> honest statuses) is adapted from the **vizavi_motion** skill v1.6.1, shown in
> https://www.youtube.com/watch?v=L4MM8BQ9dTM. Ideas paraphrased and reworked for Blender VSE + VSEKit;
> no text copied (the original has no licence). Its HTML-first stack and image/3D provider notes are not
> carried over.

The user's brief always wins over these defaults (length, silence, style, "keep it simple"). Make the
reversible creative calls yourself — don't send the user a questionnaire — but never invent facts about a
real product, price, stat or the user's preferences.

---

## 1. Quality defaults (what "good" looks like before anyone asks)

**Motion has intent and physics.**
- Things that move have weight: anticipation → action → contact/overshoot → settle. A card that slides in
  and stops dead on a linear key reads as cheap. Use `vse.key(..., interp="BACK"/"EXPO", easing=...)`, and a
  small overshoot + settle on landings.
- Don't put an ease-in-out to zero speed on every keyframe of a camera/scale move — chained moves should
  flow through accents (speed waves), and slow to a calm drift only where the viewer must read.
- One main accent at a time; secondary layers react slightly later (offset 2–4 frames), not all at once.
- **No flash/strobe as a substitute for energy.** A white flash on every beat is the easiest way to look
  amateur (we did exactly that in early devlog builds). Vary the tool: punch-in, whip, mask reveal, hard cut,
  hold. Fast repeated full-frame luminance flips are also a photosensitivity risk — avoid them.

**Depth, not flat zooms** (where the piece has space — 3D scenes, layered stills, game footage):
- Foreground / midground / background move at different rates (parallax). One linear zoom on a flat image
  is not "camera movement".
- In Blender scene strips: EEVEE motion blur on fast moves, depth of field on close/spatial shots (focus
  follows the meaningful detail; text and hero stay readable). Zoom/radial blur (`fx.whip`, DBlur) is a
  stylised accent for transitions — not a replacement for DOF or motion blur, and never on the whole video.
- Light, contact shadow and overlap sell form; grain, glow and particles don't fix a weak composition.

**Typography acts.** Design the readable final layout first, then how words/letters get there (build,
mask, weight/width change, interaction with an object). Every effect needs a job. Check the font actually
has the glyphs (Cyrillic! — Russo One/Rubik in `assets/fonts` do) and give text its reading window
(≈ 0.3 s per word + 0.5 s, more on busy frames).

**Sound is part of the direction from the start** (unless the brief says silent): music with an actual
arc (intro → build → peak → resolve), and SFX tied to motion, contact and transitions — not the same
whoosh on every cut, not an impact doubled on every drum hit. A pile of whooshes is not a soundtrack.
`vsekit.audio` can synthesise both; licensed tracks are often better — say which you used.

**Sync to accents, not to every beat.** Periodically land a cut, a reveal, a contact or a settle on a
real accent of the *actual* track (a hit, a phrase change, a drop, a sudden pause). See §2 accent map.

---

## 2. Direction before build

Before writing `build.py`:

1. **Extract the brief**: goal, viewer, the one idea, mandatory text, format/aspect, length, sound/voice,
   allowed assets, deliverables. Unknown real-world facts stay unknown; creative gaps you fill yourself.
2. **One thread.** What acts, what changes, what the ending proves. A sequence of unrelated pretty shots is
   not a video. Don't reuse the previous video's structure under a new title (e.g. every devlog starting
   with the same 3D title).
3. **3–5 genuinely different options per scene** — different action, composition/space, metaphor or
   transition (a new colour or font is not a new option). Pick the strongest for the whole; show the user
   the pick and a one-line reason, not the whole deliberation. Skip this for mechanical scenes (a jump-cut
   talking head, a credits card) — spend it where the video lives or dies: hook, key reveal, ending.
4. **Shot card per scene** — this is the storyboard `config.py` should encode:

| Field | Fix down |
|---|---|
| Time + role | interval, the one accent, what this scene does for the story |
| Action | state before → trigger → change → result |
| Space | composition, fg/mid/bg layers, light |
| Text | exact words, how they move, reading window |
| Camera | path, target, speed shape, framing; blur/DOF if any |
| In / out | how we enter from the previous scene and what carries us into the next |
| Sound | music moment, SFX, sync event — or "silent" |
| Risk | the riskiest thing here and how you'll check it |

Design transitions together with both scenes. A match cut needs matching silhouette, scale, orientation
and direction of motion; a mask transition needs the next scene genuinely inside the mask, not an overlay
slapped on after the cut.

5. **Accent map** (whenever music matters): after the track is chosen, list its real accents with
   `beats.analyze()` (onsets/downbeats/energy) + `beats.strongest()`, then pair the ones you'll use with
   visual events as frames (`round(t * fps)`), accounting for the strip's start offset. BPM grids and the
   start of an SFX file are not the accent — the perceived peak may be later. After any retiming/speed
   ramp or track trim, recompute the map. If a sync point fights readability, speech or the story, drop the
   sync, not the meaning.
6. **Probe the main risk before the full build**: render just the risky scene/transition at real quality
   (`vsekit/preview.py` for stills, a short `-s/-e` frame-range render for motion) and look at it. A probe
   doesn't replace the storyboard or the review in §3.

---

## 3. Mandatory iteration after the first build

**The first full render is an internal draft.** Don't hand it over as final. Review it, fix causes, re-check.

**Review pass** — whole video first, then each scene and every boundary:
- Is the thread readable? Any dead holds or boring stretches? Does it develop?
- Do camera, framing and layers direct attention? Are speeds and joins smooth?
- Can every mandatory word be read without pausing? Does the typography do something?
- Artefacts: wrong crops, layer conflicts, black frames, text over faces/UI, safe-zone violations.
- Blur/focus matching the motion and not hiding what matters.
- Sound: sync points land, no clicks/cut-offs, music ends rather than stops, mix balance (→ user listens).
- Brief: format, length, fps, silent/offline and other explicit requirements.

Write issues as **interval → observation → cause → fix → re-check**, fix the *cause*, re-check the changed
part with its neighbours, then the whole again. Don't fake iterations: if nothing is wrong, say what you
checked. When simplifying, compare with the brief — "cleaner" is not acceptable if required characters,
text or actions disappeared. Stop when the required things are done and checked and only taste-level
alternatives remain.

**Tools for looking (you can't watch real-time playback — use these):**

| Question | Tool |
|---|---|
| Compositions, layout, overall rhythm of shots | `media.contact_sheet(video, png, every_s=0.5)` |
| What happens across a cut / transition / sync point | `media.boundary_strip(video, t, png, before=3, after=3)` — consecutive frames in one row |
| A specific frame (overlay placement, freeze frame) | `media.frame_at(video, t, png)` |
| Before rendering | `vsekit/preview.py` on the `.blend` |
| The deliverable is technically right | `media.verify_export(mp4, fps=, duration=, width=, height=)` + `media.loudness()` |

Check the **decoded final file**, not the `.blend` or the PNG frames: its first and last frames, both
sides of every scene boundary, the fastest moment and the longest text hold. At 20 s × 60 fps expect 1200
frames (0…1199); `verify_export` counts them. Don't trim with `-shortest` blindly — it can cut the music
tail or the last line.

**Honest status words** — use them in the hand-over, per property:

| Status | Means |
|---|---|
| implemented | it's in the build script / `.blend` |
| rendered | the file exists and `verify_export` passes |
| seen in frames | you looked at contact sheets / frames |
| checked across boundaries | you looked at `boundary_strip`s at the cuts/sync points |
| **watched in motion** | real-time playback — **only the user can do this** |
| **listened** | audio quality, mix, sync feel — **only the user can do this** |

So a typical honest hand-over: "rendered, verified (1080×1920, 60 fps, 1560 frames, −14.0 LUFS), seen in
frames and checked at all 9 cuts; not watched in motion or listened — please check the drop at 0:07 and
the music ending." Never mark something checked because the parameter is set in code, and never claim
sync is "perfect" from numbers alone.

---

## Extras — only when the job needs them

**Analysing references** (`python -m vsekit.analyze`): work from real frames and audio, never from a
title or thumbnail. Separate **observed (interval) → principle → our own decision**. When combining
several references, decide which property comes from which (e.g. composition from A, typography from B,
rhythm from C) and build one system, not three fragments. Analysing a technique gives no right to reuse
the footage, music or fonts.

**UI / product demos** (app screens, game menus, store pages):
- One believable app with consistent data and states across scenes, not a new decorative card per scene.
- The cursor drives the action: approach → hover reaction → press (slight squash) → visible state change →
  readable result. Hit-test with the arrow tip, not the sprite centre; the cursor never covers the label
  or the number being shown. Typical move 0.6–0.9 s on a slight arc.
- States are causal: hover → pressed → processing → success; no success before the process ends.
  Shortened waits are fine, but don't present them as real product speed.
- Drag: keep the grab offset, card lifts and follows on an arc, target highlights, drop settles into the slot.
- Flat UI → 2.5D (same flat panels separated in depth, parallax) → 3D (real thickness, edges, side faces,
  light) are different things; don't fake 3D with drop shadows.
- Don't present demo numbers as real metrics of a real service.

**Stills and characters across shots**: keep identity/proportions/light consistent; three poses are a
discrete series, not a rotation; parallax of one image is not a new angle. Transparency means a real alpha
PNG — check edges on dark and light backgrounds (halos, premultiplied alpha).
