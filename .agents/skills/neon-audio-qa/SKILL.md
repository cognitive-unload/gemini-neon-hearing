---
name: neon-audio-qa
description: Audits video, voiceover, or podcast audio tracks with Gemini 4 Neon (or similar multimodal audio models) using deterministic ffprobe timing, a Python DSP pre-scanner, and swapped-order A/B mix verification. Use when QA-checking rough cuts, voiceovers, mixes, sound effects, or timestamps before publishing.
---

# Neon Audio QA

Use this workflow when auditing audio with **Gemini 4 Neon** (or comparable multimodal audio models). It turns a strong perception ear into a reliable audio QA pipeline by putting three deterministic guardrails around the model's documented failure modes.

## Verified Guardrails (Why Raw Listening Fails)

From **238 isolated blind runs** (`220` primary + `18` solo-rubric follow-up; see repo `results/`):

| Failure Mode (Raw) | Measured Behavior | Required Guardrail |
|---|---|---|
| **Timeline compression** | Unanchored Neon shrinks 2-minute audio to `28–60 s` (`~0.38x–0.50x`, `22.9–32.1 s` median onset error) | Always extract `exact_duration_sec` via `ffprobe` and physical timestamps via `scripts/scan_audio.py` first |
| **Slot-A positional bias** | On paired A/B mix checks, Neon Medium picked Slot A `15/18` (`83.3%`) times (`3/9` order-invariant); `xhigh` dropped to `50%` (`7` ties, `1/9` when clean sat second) | Always run **both** `(A, B)` and swapped `(B, A)` in isolated turns and trust only verdicts that agree |
| **Solo tonal/balance blindness** | Solo checks missed `9/9` flaws with a short prompt and still missed `6/6` buried-vocal & harsh-EQ flaws (`9/10` clean) even with an explicit rubric | Never judge vocal balance or EQ solo — always compare against a loudness-matched known-clean reference |
| **Instrumental VO hallucination** | Unconstrained solo prompts hallucinated voiceover praise on pure instrumental tracks | Always gate solo prompts with explicit `"speech_present": true/false` first |

## Step 1: Run Deterministic Pre-Scan First

Never ask the model to guess durations or timestamps blind. Run `scripts/scan_audio.py` on the target audio or video file (`.wav`, `.mp3`, `.m4a`, `.flac`, `.mp4`, `.mov`):

```bash
# Single voiceover, rough cut, or SFX timeline (prints ffprobe duration + DSP anchors + anchored prompt)
python3 .agents/skills/neon-audio-qa/scripts/scan_audio.py --audio path/to/rough_cut.mp4 --mode voiceover

# Pure JSON anchors only (zero prompt wrapper)
python3 .agents/skills/neon-audio-qa/scripts/scan_audio.py --audio path/to/voiceover.wav --dsp-only

# Pairwise mix check: measures loudness/centroid parity + generates BOTH (A, B) and (B, A) prompts
python3 .agents/skills/neon-audio-qa/scripts/scan_audio.py --audio path/to/reference_clean.wav --audio-b path/to/candidate_mix.wav --mode ab-pair
```

If using this repository's hash-locked environment, invoke `.venv/bin/python` instead of `python3`.

## Step 2: Voiceover & Long-Track Defect Audit ("DSP Finds When, Neon Says What")

1. Run `scan_audio.py --audio <file> --mode voiceover` (or `--mode timeline` for sound-event cue sheets).
2. Read the returned JSON anchors:
   - `exact_duration_sec` — exact `ffprobe` file length.
   - `clipping_spans_sec` — `>= 3` consecutive samples at `>= 0.999` full scale.
   - `silence_spans_sec` — dead air `>= 1.0 s` below `-60 dBFS` (excluding 0.5 s head/tail margins).
   - `impulse_click_candidates_sec` — isolated 5 kHz high-pass impulse spikes above calibrated threshold (`131.4` default).
   - `hiss_spans_sec` — raised 4 kHz minimum-statistics noise floor `>= 2.0 s` above `-73.1 dBFS` default.
   - `onset_peaks_sec` & `pulse_bursts` — discrete cue onsets and rapid burst counts (`100%` exact vs `44–56%` raw Neon).
3. Pass `exact_duration_sec` + the anchor window list to Gemini 4 Neon using the **Anchored Voiceover QA** or **Anchored Timeline Cues** template in `references/QA_PROMPTS.md`.
4. Instruct the model to listen to the full audio (`read_file` or native audio attachment) and classify/explain **each anchored window** (plus note any semantic glitches like garbled syllables, repeated words, or mispronunciations that waveform math cannot see).

## Step 3: Mix & EQ Verification (Swapped-Order A/B Gate)

Do **not** ask Neon to rate a single track's vocal balance or EQ in isolation — even an explicit rubric yields `0/6` detection on buried vocals and thin/harsh EQ.

1. Pick a **known-clean reference clip** from the same voice/show/format.
2. Run `scan_audio.py --audio <ref> --audio-b <candidate> --mode ab-pair`.
   - Check `lufs_diff_db`: if `|lufs_diff_db| > 1.0 dB`, loudness-match both clips first (e.g., `ffmpeg` `loudnorm`) so volume does not bias the comparison.
3. Run **Pass 1 (`forward`)**: attach `clip_A = ref`, `clip_B = candidate` in a fresh context using `references/QA_PROMPTS.md#swapped-ab-mix-check`.
4. Run **Pass 2 (`reversed`)**: attach `clip_A = candidate`, `clip_B = ref` in a **separate fresh context** (neutral filenames like `clip_a.wav` / `clip_b.wav` so filenames do not leak which clip is reference).
5. Apply the **Agreement Gate**:
   - **PASS / CLEAN:** Both passes agree the candidate matches or beats the reference (or neither flags a concrete defect on the candidate).
   - **FAIL / FIX:** Both passes identify the **same underlying track** as flawed and name the defect.
   - **INCONCLUSIVE (Slot-A flip or tie):** Pass 1 picks `clip_A` and Pass 2 also picks `clip_A` (classic Slot-A bias) -> escalate to a human listen or inspect DSP spectral centroid / LUFS metrics.

## Step 4: Solo Sanity Check (Limited Scope Only)

If no clean reference clip exists:
1. Run `references/QA_PROMPTS.md#solo-explicit-rubric` with explicit `"speech_present"` gating.
2. Interpret results honestly:
   - **Useful for:** detecting rhythmic/loop splices (`2/3` caught) and preventing instrumental VO hallucinations (`0/6` hallucinations, `0/9` clean false alarms).
   - **NOT reliable for:** vocal-to-music balance (`0/3` caught solo) or harsh/thin vocal EQ (`0/3` caught solo). Never stamp mix balance or EQ "clean" from a solo run alone.

## Known Limits & Release Honesty

1. **Speech-masked micro-clicks (`~84 s` blind spot):** A short click tucked directly inside a voiced word (e.g., `5.6x` crest inside speech) can slip past **both** 5 kHz high-pass DSP and raw Neon (`4/5` caught on R4 voiceover defects). Spot-check critical intros, hooks, and sponsor reads with human ears.
2. **Calibration thresholds:** Default click (`131.4`) and hiss (`-73.1 dBFS`) thresholds were calibrated on clean synthetic speech (`Kokoro-82M`). For noisier live room recordings, pass `--click-thr` and `--hiss-db` (or run `harness/src/dsp.py` against your own clean room calibration clips) to avoid false alarms.
3. **Human sign-off & disclosure:** AI + DSP catches most gross technical defects cheaply, but never claim a human listened when only an agent checked the audio.
