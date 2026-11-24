# Verified Audio QA Prompt Templates

All templates below come from the **Cognitive Unload** blind exam (`220` primary runs + `18` solo-rubric follow-up runs on `gemini-4-neon-medium` / `gemini-4-neon-xhigh`). Keep every audit turn **isolated** (no prior hints, neutral filenames like `clip.wav` or `clip_a.wav`/`clip_b.wav`, and strict JSON output).

---

## Anchored Voiceover QA {#anchored-voiceover-qa}

Use after running `scripts/scan_audio.py --audio <file> --mode voiceover`. Pairs exact `ffprobe` duration + DSP defect windows with Neon's semantic ear (`4/5` faults caught at `0.0645 s` median error, `0/3` clean false alarms; still disclose speech-masked clicks).

```text
Return ONLY a single valid JSON object matching this exact schema (no markdown fences, no commentary):
{
  "has_defects": boolean,
  "defects": [
    {
      "type": "click_pop" | "clipping" | "silence_gap" | "hiss" | "speech_glitch" | "other",
      "start_sec": number,
      "end_sec": number,
      "confidence": "high" | "medium" | "low",
      "note": string
    }
  ]
}

You are auditing a single voiceover or rough-cut audio track before publishing.
Exact file duration from ffprobe: <EXACT_DURATION_SEC> seconds.
Deterministic DSP pre-scan windows:
- impulse_click_candidates_sec: <CLICKS_JSON>
- clipping_spans_sec: <CLIPPING_JSON>
- silence_spans_sec: <SILENCE_JSON>
- hiss_spans_sec: <HISS_JSON>

Listen to the entire audio file.
1. Inspect every DSP window above and confirm whether a real audible defect occurs there (omit confirmed false positives).
2. Also flag any unmistakable speech defects DSP cannot see (stutter, garbled words, broken phrasing, dropped words) using the exact duration above to calibrate timestamps.
3. If the track is genuinely clean, return {"has_defects": false, "defects": []}. Do not invent flaws.
```

---

## Anchored Timeline Cues {#anchored-timeline-cues}

Use after running `scripts/scan_audio.py --audio <file> --mode timeline`. Lifted strict cue naming on 2-minute audio from `77.8%` to **`94.4%` (`17/18`)** at `0.005 s` median timing error.

```text
Return ONLY a single valid JSON object matching this exact schema (no markdown fences, no commentary):
{
  "exact_duration_sec": number,
  "cues": [
    {
      "onset_sec": number,
      "sound": string,
      "note": string
    }
  ]
}

Exact file duration from ffprobe: <EXACT_DURATION_SEC> seconds.
Deterministic DSP onset timestamps (seconds): <ONSETS_JSON>

Listen to the entire audio file and name the exact sound event beginning at each DSP onset timestamp above. Keep timestamps anchored to the DSP values unless an audible transition clearly starts nearby. Do not skip events or compress the timeline.
```

---

## Swapped-Order A/B Mix Check {#swapped-ab-mix-check}

Use after running `scripts/scan_audio.py --audio <ref> --audio-b <candidate> --mode ab-pair` (verify `|lufs_diff_db| <= 1.0 dB` first).

Run **twice in two separate fresh sessions**:
- **Pass 1 (forward):** rename/attach `clip_a.wav` = reference, `clip_b.wav` = candidate.
- **Pass 2 (reversed):** rename/attach `clip_a.wav` = candidate, `clip_b.wav` = reference.

```text
Return ONLY a single valid JSON object matching this exact schema (no markdown fences, no commentary):
{
  "better": "A" | "B" | "tie",
  "flawed_clip": "A" | "B" | "none",
  "flaw_category": "vocal_buried" | "harsh_thin_eq" | "rhythm_or_splice_glitch" | "none" | "other",
  "explanation": string
}

Listen to both clip_a and clip_b in full. Both clips are matched in overall loudness.
Compare them strictly on technical mix quality:
1. Vocal-to-music balance ("vocal_buried"): does the voice stay effortless to hear above the bed?
2. Vocal EQ & tone ("harsh_thin_eq"): does the voice retain natural low-end body and smooth upper-mids rather than sounding thin, tinny, or piercing?
3. Rhythm & edit continuity ("rhythm_or_splice_glitch"): are beats, loops, and edit seams smooth?

Pick the cleaner clip ("A", "B", or "tie" ONLY if truly indistinguishable) and identify which clip has the flaw.
```

**Agreement rule:** Trust the decision **only** when Pass 1 and Pass 2 select the same underlying file. If both passes pick `"A"` (Slot-A positional bias) or disagree, treat the verdict as inconclusive and verify by human ear.

---

## Solo Explicit-Rubric Check (Limited Scope) {#solo-explicit-rubric}

Use **only** when no clean reference clip exists. Verified across `18` blind runs: eliminates instrumental voiceover hallucinations (`0/6`, `0/9` clean false alarms) and catches rhythmic splices (`2/3`), **but still scores `0/6` on buried vocals and harsh/thin EQ**. Never rely on this prompt alone to sign off vocal balance or EQ.

```text
Return ONLY a single valid JSON object matching this exact schema (no markdown fences, no commentary):
{
  "speech_present": boolean,
  "has_flaw": boolean,
  "flaw_category": "none" | "vocal_buried" | "harsh_thin_eq" | "rhythm_or_splice_glitch" | "other",
  "mix_quality_score_1_to_10": integer,
  "explanation": string
}

You are QA-checking a single podcast/video audio clip on its own before publishing.
First decide whether actual human speech is present ("speech_present": true or false; some clips are pure instrumental music with no voiceover).
Then check the clip against this explicit definition of a CLEAN audio master:
1. Vocal-to-music balance ("vocal_buried"): ONLY if speech and music play together, the voice must sit clearly in front of the music and stay effortless to understand at normal listening volume. Flag "vocal_buried" if the background music competes with, masks, or overpowers the narrator. Never flag "vocal_buried" on an instrumental clip with no speech.
2. Vocal tone & EQ ("harsh_thin_eq"): ONLY if speech is present, a clean voice sounds natural and balanced with normal low-end warmth/chest body and smooth upper-mids. Flag "harsh_thin_eq" if the voice sounds thin, tinny, hollowed-out, telephone/megaphone-like, stripped of bass warmth, or sharply harsh/piercing in the upper-mid frequencies.
3. Rhythm, tempo & edit continuity ("rhythm_or_splice_glitch"): Music beds and phrasing must keep a steady beat, consistent bar timing, and smooth transitions from start to end. Flag "rhythm_or_splice_glitch" if you hear an off-beat cut, skipped/rushed beat, abrupt loop seam, hiccup, or jarring splice glitch in the music or edit.
4. Other clear defect ("other"): Flag "other" only for another unmistakable technical defect (clipping, hiss, clicks, dead-air dropouts).

Decision rule:
- A clip is CLEAN ("has_flaw": false, "flaw_category": "none", score 8-10) ONLY if every applicable check above passes cleanly. Do NOT invent flaws on genuinely clean clips.
- If ANY concrete flaw above is clearly audible, set "has_flaw": true, pick its exact "flaw_category", rate mix quality 1-6 (1 = severe, 6 = borderline), and explain what you heard (including approximate time in seconds if localized).
```
