# Round 3 Solo Mix Judging — Explicit "What Clean Means" Rubric Ablation (`18` Isolated Blind Runs)

**Model:** `gemini-4-neon-medium` via `agy` (`18/18` runs `SUCCESS`, `parse_ok=True`, `audit_clean=True`, `read_file`-only on ephemeral `clip.wav`).
**Artifacts:** `results/r3_solo_rubric_scores.json` (raw archive `r3_solo_rubric_outputs.tar.gz` (`sha256: 589d7041a2d6dfa14ed83b6ca87c9e3319fd64afdd9b0f881e8ced04f69146cf`), script `harness/run_r3_solo_rubric.py`.

## Apples-to-Apples Comparison (`gemini-4-neon-medium`, same 6 R3 WAVs × 3 runs)

| Metric | Short Prompt (`ablation_v2/r3_single_clip`) | Explicit Acoustic Rubric (`r3_solo_rubric`) | Delta / Takeaway |
|---|---:|---:|---|
| **Flawed clips caught** | `0/9` (`0.0%`) | **`2/9` (`22.2%`)** | Only rescued self-referenced rhythmic splice (`r3_p3_y`) |
| **Pair 1: `vocal_buried`** (`r3_p1_y`, music +8 dB) | `0/3` (all `9/10`) | **`0/3` (all `9/10`)** | Zero change — still called voice *"sits clearly in front of the background music"* `3/3` |
| **Pair 2: `harsh_thin_eq`** (`r3_p2_x`, 450 Hz HP + 9 dB @ 3.2 kHz) | `0/3` (all `9/10`) | **`0/3` (all `9/10`)** | Zero change — echoed rubric words (*"good low-end warmth and smooth upper-mids"*) `3/3` on a bass-stripped tinny voice |
| **Pair 3: `rhythm_or_splice_glitch`** (`r3_p3_y`, 180 ms off-beat cut @ 10.50 s) | `0/3` (all `9/10`) | **`2/3` (`4/10`, `9/10`, `4/10`)** | Real lift — Run 3 located the exact 4th-bar seam (*"Around 10 seconds, at the end of the fourth bar"*) |
| **Clean false positives** | `1/9` (`r3_p3_x` r2 `3/10` `vocal_buried`; r3 `9/10` hallucinated VO) | **`0/9` (`0.0%`)** | Explicit `speech_present` check eliminated instrumental VO hallucinations (`6/6` `speech_present=false`) |
| **Exact classification** | `8/18` (`44.4%`) | **`11/18` (`61.1%`)** | `+3/18` (`+1` clean FP fixed, `+2` splice detections) |
| **Implied pairwise `W / T / L`** | `0W / 8T / 1L` | **`2W / 7T / 0L`** | Still `7/9` ties; `0/6` on tonal/balance flaws |

## Key Acoustic Insight

1. **What explicit prompting DOES fix:**
   - Adding an explicit `speech_present` check eliminated the instrumental voiceover hallucination (`0/6` hallucinations on pure instrumental `r3_p3_x`/`r3_p3_y`; `0/9` clean false alarms).
   - Explicitly defining beat/bar continuity helped Neon detect an **internally self-referenced** temporal discontinuity (`r3_p3_y`: bars 1–3 set the tempo, bar 4 breaks it — caught `2/3` times at `4/10`).
2. **What explicit prompting STILL CANNOT fix solo (`0/6`):**
   - **Global tonal and mix-balance calibration (`vocal_buried` `0/3`, `harsh_thin_eq` `0/3`):** Every flawed clip was still rated `9/10` clean, and Neon parroted the rubric's own descriptors back (*"warm low-end body"*, *"effortless to understand"*) even when the voice had everything below 450 Hz cut out or sat under a +8 dB music bed.
   - Reliable mix/EQ judging still requires a **known-clean reference clip** beside the test track with **swapped-order `(A, B)` + `(B, A)` agreement**.

## Exact Rubric Prompt Tested

```text
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
