# Blind Audio Exam Specification v1 (Pre-Registered)

**Story:** Pitch 1 — *"Gemini 4 Neon: Can AI Finally Hear?"* (Cognitive Unload, Type 1: trending tool put to the test)  
**Channel:** Cognitive Unload (`https://www.youtube.com/@Cognitive-Unload/`)  
**Roles:** Validation Lead & Independent Exam Builder / Peer Reviewer  
**Pre-Registration Date:** 2026-11-20  

> **Pre-Registration Rule:** This specification, all pass thresholds (A1–A6), all verbatim blind prompts, all JSON schemas, and the SHA-256 hash of sealed `ground_truth.json` are locked BEFORE any model hears any exam clip.

---

## 1. Pre-Registered Assumptions & Viewer-Visible Pass Checks (A1–A6)

| ID | Assumption | Viewer-Visible Pass Check |
|---|---|---|
| **A1** | **Apples-to-apples audio route:** Raw `gemini-4-neon-medium` and raw `gemini-4-argon-medium` both receive real audio via `agy 1.5.12` `read_file` at the same fixed thinking level (`medium`, no Orchestrator grading itself, `$0` extra spend). | Speech-control clip transcribed verbatim by both models on the same harness. *(Passed smoke check on 20 Nov 2026 on `.mp3` and `.wav`.)* |
| **A2** | **Perception leap — Neon vs Argon & open model:** On Perception rounds (Rounds 1–3: non-speech sound scenes, real AI-creator voice flaws, swapped-order blind mix/timbre A/B), raw Neon clearly beats raw Argon and the audited open-weight audio model across 3 runs each. | Neon beats Argon by `>= 15` percentage points on composite Perception accuracy, achieves `>= 80%` order-invariant consistency on swapped A/B pairs, and beats the audited open audio model on Perception. |
| **A3** | **Precision limit — DSP vs raw Neon:** On Precision rounds (Rounds 4–5: planted micro-clicks, subtle hiss, clipping, dead-air silence, 120 s timed cues, pulse counting), plain `ffmpeg`/DSP beats raw Neon on deterministic signal faults and timing precision. | Plain `ffmpeg`/DSP catches `>= 90%` of deterministic signal faults with `<= 0.25 s` timestamp error, while raw Neon misses `>= 25%` of micro-clicks/hiss OR shows `> 2.0 s` median timestamp drift unanchored. *(If raw Neon passes precision too, record A3 Fail and evaluate Change direction: "Neon solved precision too".)* |
| **A4** | **Hybrid payoff — DSP-anchored + Neon checker:** Adding deterministic `ffmpeg`/DSP pre-scan metadata (duration, loudness/silence spans, impulse/clip candidates, onset peaks — zero ground truth) to Neon's prompt improves timing without sacrificing perception, validating the open-source companion repo tool. | On Round 4 + Round 5a, DSP-anchored Neon cuts median timestamp error by `>= 50%` vs unanchored Neon (or lands `<= 1.5 s`) while keeping `>= 80%` defect recall and `<= 1` false alarm on the clean control. |
| **A5** | **Audited open-weight audio baseline:** At least one credible open-weight general audio model passes `repo-demos-install-audit` (pinned version + lockfile + OSV check recorded in task) and completes the full blind exam cleanly (non-gibberish structured outputs). | Audit verdict `install` or `install only in a container` recorded prior to execution, and all 3 runs finish with valid parseable JSON across all rounds. |
| **A6** | **Shareable, rights-cleared exam kit:** 100% of audio clips are synthetic/DSP-generated, CC0/public-domain, or commercial-rights-cleared Cognitive Unload/ElevenLabs assets — strictly zero private recordings and zero uncleared commercial music. | Origin, license, and SHA-256 of all 17 WAV files documented in `exam_manifest_public.json`. |

---

## 2. Contestants & Run Protocol

1. **Plain `ffmpeg`/DSP (`dsp`):** 1 deterministic run (`$0`). Marks pure Perception semantic questions (`speech_present` content interpretation, vocal garble, room-reverb semantic judgment, perceptual mix quality) as `N/A (DSP blind)` where signal meters have no semantic detector, while outputting deterministic signal metrics in matching JSON schemas where applicable.
2. **Gemini 4 Neon — raw (`gemini-4-neon-medium`):** Invoked via `agy 1.5.12 --model gemini-4-neon-medium --output-format json --dangerously-skip-permissions --disable-slash-commands`. Fresh isolated session per clip/pair/run, executed inside a temporary blind directory containing ONLY the target WAV file(s). **3 independent runs** per prompt (handles Cloud docs `temperature = 1.0` fixed variance). `$0` extra API spend.
3. **Gemini 4 Argon — raw (`gemini-4-argon-medium`):** Identical `agy 1.5.12` harness, identical blind directory isolation, identical prompts, **3 independent runs** per prompt. `$0` extra API spend (no OpenCode Go credits needed for Argon).
4. **Audited Open-Weight Audio Model (`open_audio`):** 1 pinned open-weight general audio model passing `repo-demos-install-audit` (priority shortlist: Qwen3-Omni / Qwen2.5-Omni on a verified non-broken runtime, Voxtral Small 24B / Mini 3B, or Gemma 4 E4B/12B audio). **3 independent runs** on identical blind prompts. `$0` local.
5. **Hybrid DSP-Anchored Neon (`hybrid_dsp_neon` — Round 6):** `gemini-4-neon-medium` via `agy 1.5.12`, **3 independent runs** on `r4_01.wav`, `r4_02.wav`, and `r5_01.wav`, receiving the audio file plus the deterministic `DSP_PRECHECK` block from `dsp_anchors.json`.
6. **Optional Ablations (reported separately from the primary scoreboard):**
   - Targeted `gemini-4-neon-high` run on Round 4 / Round 5 if `medium` shows timing drift or misses micro-defects.
   - `gpt-audio-1.5` optional if separately budgeted (not run in this study).

---

## 3. Blind Exam Inventory & Format Rules

- **Format:** Lossless 16-bit PCM `.wav` (`24 kHz` or `44.1 kHz`, mono for voice/precision rounds, stereo for scenes/mixes), `<= 8 MB` per file, all metadata tags stripped (`ffmpeg -map_metadata -1`), anonymized filenames only.
- **Duration Leakage Rule:** Exact clip durations MUST NOT appear anywhere in `exam_manifest_public.json` or the blind folder for unanchored Rounds 1–5. Exact durations appear ONLY inside `dsp_anchors.json` (used exclusively in Round 6) and `dsp_baseline_outputs.json`.
- **Total Files:** **17 `.wav` files** representing **14 test items** across 5 rounds (**17 prompts/run** in Parts A + B, plus **3 prompts/run** in Part C = **20 prompts/run** for Neon):

### Part A — Perception (13 prompts/run across 3 rounds)

#### Round 1 — Non-Speech Sound Scenes & Foley (`r1_01.wav` – `r1_03.wav`, 3 clips, `speech_present: false`)
- `r1_01.wav` (2–5 s): Single non-speech chime / metallic wash texture (no speech).
- `r1_02.wav` (12–18 s): Indoor everyday scene with 3 sequential distinct non-speech events (e.g., water pour -> mug clink -> door latch).
- `r1_03.wav` (12–18 s): Outdoor ambient scene (2 steady background elements + 1 clear mid-clip event such as a distant siren or dog bark).

#### Round 2 — Real AI-Creator Voice Failures (`r2_01.wav` – `r2_04.wav`, 4 clips, 15–30 s each)
Randomized mapping from the 4 conditions below into `r2_01.wav`..`r2_04.wav` inside sealed `ground_truth.json`:
1. **Clean control** (`defect_type: "none"`): 0 defects.
2. **Mid-word splice cut** (`defect_type: "cut_word_splice"`): Clean 5 ms crossfaded cut mid-word at normal loudness (invisible to loudness/clipping meters).
3. **Garbled/warbled vocal artifact** (`defect_type: "garbled_vocal"`): Existing rejected Cognitive Unload TTS take with audible warble/mispronunciation, or a controlled 1–2 s vocal stutter/phase glitch.
4. **Overlapping speaker or abrupt room-reverb shift** (`defect_type: "overlap_or_reverb_jump"`): 2–3 s second-voice bleed OR mid-sentence jump into heavy room reverb.

#### Round 3 — Swapped-Order Blind Mix & Timbre A/B (`r3_p1_{x,y}.wav` – `r3_p3_{x,y}.wav`, 3 pairs × 2 orders = 6 prompts/run, 15–25 s each)
Coin-flipped assignment of clean master vs flawed copy to `_x.wav` and `_y.wav` inside sealed `ground_truth.json`. Every pair MUST be evaluated in BOTH orders (`fwd`: `clip_A = _x, clip_B = _y`; `rev`: `clip_A = _y, clip_B = _x`) in separate isolated sessions:
- **Pair 1 (`r3_p1` — Vocal balance, `flaw_category: "vocal_buried"`):** Clean balanced voice + music bed vs voice buried under `+8 dB` louder music bed.
- **Pair 2 (`r3_p2` — Voice timbre/EQ defect, `flaw_category: "harsh_thin_eq"`):** Clean warm narrator vs harsh/tinny EQ (`highpass 450 Hz` + `+9 dB @ 3.2 kHz`), matched to identical integrated LUFS so a loudness meter sees `0 dB` difference.
- **Pair 3 (`r3_p3` — Music rhythm/splice edit flaw, `flaw_category: "rhythm_or_splice_glitch"`):** Smooth instrumental bed (or voice+bed) vs RMS-matched copy with an off-beat bar splice cut.

### Part B — Precision (4 prompts/run across 2 rounds)

#### Round 4 — Planted Micro-Defects in Long Voice Track (`r4_01.wav` – `r4_02.wav`, 2 clips)
- `r4_01.wav` (90–120 s continuous voice track): 5 planted defects at secret timestamps:
  - `2x` sharp micro-clicks/pops (`2–4 ms` impulse, audible on headphones)
  - `1x` subtle low-level hiss segment (`8–10 s` at `-36 dBFS` floor)
  - `1x` brief digital clipping burst (`1.5–2 s` hard-clipped at `0 dBFS`)
  - `1x` dead-air silence gap (`2.2 s`)
- `r4_02.wav` (45–60 s clean voice control, same speaker, `0` planted defects).

#### Round 5 — Stopwatch & Counting Precision (`r5_01.wav` – `r5_02.wav`, 2 clips)
- `r5_01.wav` (120 s audio with **6 distinct recognizable sound cues** placed at irregular secret timestamps spanning `0:08`–`1:54`).
- `r5_02.wav` (15–20 s pulse/alert-pattern counting clip: **3 distinct tone/alert bursts** separated by `~2 s` pauses, each with an exact secret pulse count between `3` and `9`).

### Part C — Hybrid DSP-Anchored Neon (3 prompts/run)

#### Round 6 — DSP-Anchored Precision (`r4_01.wav`, `r4_02.wav`, `r5_01.wav`)
Same audio files as Rounds 4 and 5a, run on `gemini-4-neon-medium` (3 runs each) with the deterministic `DSP_PRECHECK` JSON block from `dsp_anchors.json` appended to the prompt.

---

## 4. Verbatim Blind Prompt Templates & Strict JSON Schemas

Every prompt begins with the shared isolation rule:
> `Listen ONLY to the attached audio file(s) using your native audio reader. Do NOT run shell commands, ffmpeg, python, or external speech-to-text tools. Do NOT inspect any other files. Return ONLY valid JSON matching the exact schema below—no markdown fences or extra commentary.`

### Round 1 (`r1_01.wav`, `r1_02.wav`, `r1_03.wav`)
```text
Listen ONLY to the attached audio file using your native audio reader. Do NOT run shell commands, ffmpeg, python, or external speech-to-text tools. Do NOT inspect any other files. Return ONLY valid JSON matching this exact schema—no markdown fences or extra commentary:
{"speech_present": boolean, "speech_transcript": string or null, "events_in_order": [{"label": string, "approx_start_sec": number, "approx_end_sec": number}], "scene_summary": string}

Describe every distinct sound event you hear in chronological order. Set "speech_present" to true ONLY if actual human spoken words are audible; otherwise set it to false and "speech_transcript" to null.
```

### Round 2 (`r2_01.wav`, `r2_02.wav`, `r2_03.wav`, `r2_04.wav`)
```text
Listen ONLY to the attached audio file using your native audio reader. Do NOT run shell commands, ffmpeg, python, or external speech-to-text tools. Do NOT inspect any other files. Return ONLY valid JSON matching this exact schema—no markdown fences or extra commentary:
{"has_defect": boolean, "defect_type": "none" | "cut_word_splice" | "garbled_vocal" | "overlap_or_reverb_jump" | "other", "approx_time_sec": number or null, "explanation": string}

You are QA-checking a creator voiceover take. Determine whether the recording is clean or contains a clear editing/vocal/recording flaw ("cut_word_splice", "garbled_vocal", "overlap_or_reverb_jump", or "other"). If clean, set "has_defect": false, "defect_type": "none", and "approx_time_sec": null.
```

### Round 3 (`r3_p{1..3}` — `fwd` and `rev` runs)
```text
Listen ONLY to the two attached audio files ("clip_A" and "clip_B") using your native audio reader. Do NOT run shell commands, ffmpeg, python, or external speech-to-text tools. Do NOT inspect any other files. Return ONLY valid JSON matching this exact schema—no markdown fences or extra commentary:
{"better": "A" | "B" | "tie", "flawed_clip": "A" | "B" | "none", "flaw_category": "vocal_buried" | "harsh_thin_eq" | "rhythm_or_splice_glitch" | "other", "explanation": string}

Compare clip_A and clip_B as a podcast/video mix QA reviewer. Pick which version is cleaner and better balanced ("A", "B", or "tie"), identify which clip has the flaw, and classify the main flaw in the losing clip.
```

### Round 4 (`r4_01.wav`, `r4_02.wav`)
```text
Listen ONLY to the attached audio file using your native audio reader. Do NOT run shell commands, ffmpeg, python, or external speech-to-text tools. Do NOT inspect any other files. Return ONLY valid JSON matching this exact schema—no markdown fences or extra commentary:
{"has_defects": boolean, "defects": [{"type": "click_pop" | "hiss" | "clipping" | "silence_gap" | "other", "start_sec": number, "end_sec": number, "confidence": "low" | "medium" | "high", "note": string}]}

Inspect this voiceover recording carefully from start to end for technical audio defects: sharp clicks/pops, background hiss segments, digital clipping/distortion, or unnatural dead-air silence gaps. Report every defect you hear with timestamps in seconds. If the recording has no defects, return {"has_defects": false, "defects": []}.
```

### Round 5a (`r5_01.wav`)
```text
Listen ONLY to the attached audio file using your native audio reader. Do NOT run shell commands, ffmpeg, python, or external speech-to-text tools. Do NOT inspect any other files. Return ONLY valid JSON matching this exact schema—no markdown fences or extra commentary:
{"estimated_duration_sec": number, "cues": [{"sound": string, "onset_sec": number}]}

Estimate the total clip duration in seconds and list every distinct sound cue or event in chronological order with its exact onset timestamp in seconds.
```

### Round 5b (`r5_02.wav`)
```text
Listen ONLY to the attached audio file using your native audio reader. Do NOT run shell commands, ffmpeg, python, or external speech-to-text tools. Do NOT inspect any other files. Return ONLY valid JSON matching this exact schema—no markdown fences or extra commentary:
{"bursts": [{"burst_index": integer, "onset_sec": number, "pulse_count": integer, "description": string}]}

Count the exact number of individual tone/alert pulses inside each distinct burst separated by pauses. List each burst in order (1-indexed) with its onset time in seconds, exact integer pulse count, and brief description.
```

### Round 6 (`r4_01.wav`, `r4_02.wav`, `r5_01.wav` — Hybrid DSP-Anchored Neon)
Uses the exact same instructions and JSON schema as Round 4 (for `r4_01.wav`, `r4_02.wav`) and Round 5a (for `r5_01.wav`), with one deterministic pre-scan block appended:
```text
DSP_PRECHECK (deterministic ffmpeg/Python signal measurements for the file above—contains NO human labels; use these timestamps and candidates as your exact clock anchor while you verify by listening):
<JSON block for this filename from dsp_anchors.json>
```

---

## 5. Double-Blind Sealing & Delivery Schema (Exam Builder -> Validation Lead)

### Step A: Seal Before Delivery (Exam Builder)
1. Generate the 17 `.wav` files and `ground_truth.json` (containing exact condition mappings, coin-flip A/B assignments, planted defect types and start/end seconds, Round 5a cue onsets, Round 5b exact pulse counts, and clip origins/licenses).
2. Compute `sha256sum ground_truth.json` and post **ONLY the SHA-256 hex digest** in the pre-registration seal log. **Do NOT share `ground_truth.json` until blind runs are hashed.**
3. Deliver these 4 public/blind artifacts to the blind runner:
   - `blind_exam_v1.tar.gz` — contains ONLY the 17 stripped `.wav` files (`r1_01.wav`..`r5_02.wav`).
   - `exam_manifest_public.json` — array/map of `{filename, round, sha256, license, rights_source}`. **MUST NOT contain clip duration or defect/condition hints.**
   - `dsp_baseline_outputs.json` — plain `ffmpeg`/DSP detections per clip in the exact Round 1–5 JSON schemas (plus `N/A (DSP blind)` markers for semantic Perception fields).
   - `dsp_anchors.json` — deterministic pre-scan for `r4_01.wav`, `r4_02.wav`, and `r5_01.wav` ONLY, containing `{exact_duration_sec, rms_lufs_2s_bins, silence_spans, impulse_click_candidates_sec, clipping_spans_sec, onset_peaks_sec}` (zero ground-truth labels).

### Step B: Execute & Seal Outputs (Validation Lead)
1. Run `gemini-4-neon-medium` (Parts A, B, C × 3 runs) and `gemini-4-argon-medium` (Parts A, B × 3 runs) in fresh isolated sessions.
2. Bundle all raw JSON model responses into `blind_outputs_neon_argon_v1.tar.gz` and post its SHA-256 digest in the pre-registration seal log.

### Step C: Unseal & Score
1. Exam Builder releases `ground_truth.json` (verified against the pre-registered SHA-256 digest from Step A).
2. Both sides compute and cross-check all pre-registered metrics below.

---

## 6. Pre-Registered Scoring Rules

- **Round 1 (Non-Speech Scenes):** `event_recall` = fraction of ground-truth events named accurately in chronological order (`0.0–1.0` per clip), minus a `0.5` penalty per clip if `speech_present: true` is hallucinated (clamped `>= 0.0`).
- **Round 2 (AI Voice Failures):** 1 point per clip (`4` max per run -> `%`): clean control requires `has_defect == false`; defective clips require `has_defect == true` AND exact `defect_type` match (or `0.5` credit if `has_defect == true` + timestamp within `+/- 3.0 s` but category `"other"` with accurate prose).
- **Round 3 (Swapped-Order A/B):**
  - `correct_pick_rate`: fraction of the `6` individual A/B runs picking the true clean clip (`better` matches un-flawed side).
  - `order_invariance_rate`: fraction of the `3` pairs where `fwd` and `rev` both pick the same underlying audio file.
  - `cause_accuracy`: fraction of runs with exact `flaw_category` match.
  - Round 3 composite score = mean of `correct_pick_rate` and `order_invariance_rate` (with `cause_accuracy` reported alongside).
- **Composite Perception Score (Tests A2):** Mean of Round 1, Round 2, and Round 3 accuracy across 3 runs per model.
- **Round 4 (Micro-Defects Precision):**
  - Match each predicted defect to a planted defect of compatible subtype within `+/- 5.0 s` tolerance for attribution; also compute strict hit rate at `<= 1.0 s` error.
  - Report: recall by subtype (`click_pop`, `hiss`, `clipping`, `silence_gap`), overall recall (`x/5`), false-alarm count (`r4_02.wav` clean control + unmatched detections on `r4_01.wav`), and median & max absolute timestamp error (`s`) on matched detections.
- **Round 5a (Stopwatch Cues):** Cue recall (`x/6` matched by sound description + chronological alignment), median & max absolute onset error (`s`), and wall-clock duration estimate error (`|est - true| / true * 100%`).
- **Round 5b (Pulse Counting):** Exact integer `pulse_count` match rate (`x/3` bursts), mean absolute pulse count error (`|pred - true|`), and onset timestamp error (`s`).
- **Round 6 (Tests A4 — Hybrid Delta):** Direct comparison against unanchored `gemini-4-neon-medium` on Round 4 and Round 5a for: (a) median timestamp error reduction (`%` and `s`), (b) defect/cue recall change, and (c) false alarms on `r4_02.wav`.
