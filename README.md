# Gemini 4 Neon Audio Audit — Companion Reproduction Kit (`v1.1.0`)

Companion reproduction kit — including the ready-to-install **`neon-audio-qa` Agent Skill** — for the **Cognitive Unload** episode: ***"Gemini 4 Neon: Can AI Finally Hear?"*** ([Watch on YouTube](https://youtu.be/fg-zlj1Nvfo)).

> **Channel Verdict: KEEP — WITH CODE / SKIP RAW**  
> Keep **Gemini 4 Neon** as a **perception ear** paired with `ffprobe`, a **238-line Python DSP checker** (`harness/src/dsp.py`), and swapped-order A/B verification. Skip raw, unanchored Neon as a solo mix critic or timeline clock.

---

## Installable Agent Skill (`neon-audio-qa`)

This repository ships a ready-to-use agent skill at [`.agents/skills/neon-audio-qa/`](.agents/skills/neon-audio-qa/SKILL.md) that wraps the entire verified workflow (`ffprobe` duration anchor + DSP pre-scanner + swapped-order `(A, B)` / `(B, A)` mix gate + explicit `speech_present` solo rubric):

- **Antigravity / Codex / Cursor (auto-discovered on clone):** Clone this repo into your workspace — `.agents/skills/neon-audio-qa/SKILL.md` is discovered automatically.
- **Install via Skills CLI:**
  ```bash
  npx skills add cognitive-unload/gemini-neon-hearing --skill neon-audio-qa
  ```
- **Global install (Antigravity / Claude Code / Codex):**
  ```bash
  # Antigravity / generic agent skill folder
  cp -R .agents/skills/neon-audio-qa ~/.gemini/antigravity/skills/neon-audio-qa
  # Or Claude Code
  cp -R .agents/skills/neon-audio-qa ~/.claude/skills/neon-audio-qa
  ```

The skill bundles:
- `.agents/skills/neon-audio-qa/SKILL.md` — 4-step audio QA runbook & honest limit disclosures.
- `.agents/skills/neon-audio-qa/scripts/scan_audio.py` — standalone DSP + `ffprobe` + LUFS/centroid pre-scanner (`.wav`, `.mp3`, `.m4a`, `.flac`, `.mp4`, `.mov`) with `--mode voiceover|timeline|ab-pair`.
- `.agents/skills/neon-audio-qa/references/QA_PROMPTS.md` — copy-pasteable strict-JSON prompt templates grounded in all `238` blind runs.

---

## What 220 Isolated Blind Runs Found (+ 18-Run Solo-Rubric Follow-Up)

Across **163 primary v1 runs** (`111` isolated `Antigravity CLI` + `51` local `Qwen3-Omni-30B-A3B` + `1` deterministic `ffmpeg`/DSP baseline), **27 Round-2 diagnostic ablations**, plus **30 targeted `gemini-4-neon-xhigh` runs**:

| Metric / Round | `gemini-4-neon-medium` | `gemini-4-argon-medium` | `Qwen3-Omni-30B-A3B` (`Q8_0`) | Plain `dsp.py` (`238 lines`) | Hybrid (`dsp.py` + Neon) |
|---|---:|---:|---:|---:|---:|
| **R1 Non-Speech Scenes** | **77.8%** strict (`0/9` hallucinations*) | 59.3% (`1/9` speech hallucination on `r1_01` run 3) | 37.0% strict / 74.1% lenient | N/A | N/A |
| **R2 AI Creator Speech Flaws** | **83.3%** | 58.3% | 25.0% (`0/9` flaws caught) | N/A | N/A |
| **R3 Paired Judge (Cause / Correct Pick / Invariance)** | **88.9%** (`16/18`) / 66.7% / **33.3%** (`3/9`, 83.3% Slot-A bias) | 61.1% / 72.2% / 44.4% | 16.7% / 0.0% / 0.0% | N/A | Use swapped-order agreement |
| **R3 Solo Judge (`r3_single_clip`, 18 runs)** | **0/9 (`0.0%`)** flaws caught (every flawed clip rated `9/10` clean) | — | — | N/A | N/A |
| **R4 Voiceover Micro-Defects (`r4_01.wav`, 5 faults)** | 40.0% (`6/15` <= 5 s, `1/6` clicks, `3.87 s` med err, `1` clean FA) | 40.0% (`6/15`, `2.13 s` med err) | 0.0% (`0/15`) | **80.0% (`4/5`)**, `0.0595 s` med, `0` clean FA | **80.0% (`4/5`)**, `0.0645 s` med, `0/3` clean FA *(timestamps from DSP; both missed `84.331 s` voiced click)* |
| **R5a Stopwatch (`r5_01.wav`, `120.000 s`)** | `63.6%` dur err (`~0.38x`), `32.09 s` med err; **`14/18` (`77.8%`)** strict naming | `56.4%` dur err (`~0.47x`), `25.5 s` med err | **0.8% dur err (`121.0 s` = `1.008x`, `0.88-1.00 s` med err)** *(failed QA: `0/9` R2, `0/18` R3, `0/15` R4)* | `0.0%` err, `0.005 s` med (`6/6` unlabelled onsets) | `0.0%` err, `0.005 s` med; **strict cue naming `77.8% -> 94.4%` (`17/18`)** |
| **R5b Pulse Counting (`[9, 5, 8]` bursts)** | `4/9` (`44.4%`) exact | `2/9` (`22.2%`) | `0/9` (`0.0%`) | **3/3 (`100%`)** @ `0.002 s` med | — |
| **Combined R4+R5 Physical Timing (`<= 0.25 s`)** | — | — | — | **13/14 (`92.9%`)** | **13/14 (`92.9%`)** |
| **1-Line `ffprobe` (`duration_only`)** | Cut R5a error **91.5%** (`32.09 s -> 2.735 s` med) & R4 error **71.3%** (`3.87 s -> 1.11 s` med, `10/15`), clicks stayed `1/6` | — | — | — | — |

\* *Transparency note:* Primary R2–R6 were independently re-scored by our peer reviewer; R1's `0/9` hallucination tally comes from `results/scores_v1.json`. No direct Gemini API calls were run (all Gemini runs used `Antigravity CLI 1.5.12`); `gemini-4-neon-high` unanchored Run 3 hit `120.0 s` (`0.0%` dur err, `1.465 s` med err), showing Antigravity delivers the full audio file to the model.

### Targeted `gemini-4-neon-xhigh` Extension (`30` Runs — `results/XHIGH_REPORT.md` & `results/xhigh_scores.json`)

| Round | `gemini-4-neon-medium` | `gemini-4-neon-xhigh` | What Changed With Maximum Reasoning |
|---|---:|---:|---|
| **R3 Paired Judge** | 66.7% picks / 33.3% inv. (`0` ties) | **50.0% picks (`9/18`) / 11.1% inv. (`1/9`)** | **7 identical ties** on clear defect pairs; picked clean clip only **`1/9`** times when clean sat second (`A=10, B=1, tie=7`). |
| **R4 92 s Micro-Defects** | 40.0% (`6/15`, 1 FA on clean) | **73.3% (`11/15`, `0` clean FAs)** | Higher recall & clean specificity, yet `0/15` hits within `1.0 s` (`4.088 s` med err) and `0/3` on the `84.331 s` *"screen"* click. |
| **R5a Stopwatch (`120.0 s`)** | `28–55 s` (`63.6%` dur err) | **`~60 s` (`49.9%` dur err, `22.89 s` med err)** | Still cut the 2-minute track roughly in half unanchored (`83.3%` strict / `100%` lenient cue naming). |
| **R5b Pulse Counting** | `4/9` (`44.4%`) exact | **`5/9` (`55.6%`) exact** | Modest count lift (`[9, 5, 8]`), while plain `dsp.py` nailed `3/3` (`100%`). |

### Post-Exam Solo Explicit-Rubric Follow-Up (`18` Runs — `results/R3_SOLO_RUBRIC_REPORT.md` & `results/r3_solo_rubric_scores.json`)

To test whether Neon's `0/9` solo mix-judging miss was merely a short-prompt artifact, we re-ran all 6 Round 3 WAVs × 3 isolated blind runs (`18` runs total on `gemini-4-neon-medium`) with an explicit acoustic definition of *"clean"* plus an explicit `"speech_present"` gate:

| Flaw Type / Metric | Short Prompt (`ablation_v2/r3_single_clip`) | Explicit Acoustic Rubric (`r3_solo_rubric`) | Takeaway |
|---|---:|---:|---|
| **Flawed clips caught** | `0/9` (`0.0%`) | **`2/9` (`22.2%`)** | Only rescued internally self-referenced rhythmic splice (`r3_p3_y`) |
| **Buried vocals (`vocal_buried`, music +8 dB)** | `0/3` (all `9/10`) | **`0/3` (all `9/10`)** | Zero lift — still praised vocal clarity `3/3` |
| **Harsh/thin EQ (`harsh_thin_eq`, 450 Hz HP + 9 dB @ 3.2 kHz)** | `0/3` (all `9/10`) | **`0/3` (all `9/10`)** | Zero lift — echoed rubric words (*"good low-end warmth"*) `3/3` |
| **Rhythmic splice (`rhythm_or_splice_glitch`, 180 ms off-beat cut)** | `0/3` (all `9/10`) | **`2/3` (`4/10`, `9/10`, `4/10`)** | Real lift — localized exact 4th-bar seam around `10 s` |
| **Clean false positives / VO hallucinations** | `1/9` FP (plus instrumental VO hallucination) | **`0/9` (`0.0%`) / `0/6` VO hallucinations** | Explicit `speech_present` gating completely eliminated instrumental VO hallucinations |

---

## Known Limits Disclosed Up Front

1. **DSP & Hybrid Missed Fault 5 (`84.331 s` voiced click):** `r4_01.wav` contains a short click (`5.6x` crest factor) inside the spoken word *"screen"*. Simple 5 kHz high-pass impulse ratios missed it (`4/5 = 80.0%` on R4 alone; `13/14 = 92.9%` combined R4+R5).
2. **Solo & Unswapped Judging Failures:** Solo ratings miss `9/9` mix/EQ/splice flaws with a short prompt and still miss `6/6` buried-vocal / harsh-EQ flaws even with an explicit rubric (`2/9` overall, rescuing only rhythmic splices). Paired A/B picks suffer `83.3% (15/18)` Slot-A bias (`3/9` order-invariance). Always run both `(A, B)` and `(B, A)` against a loudness-matched clean reference and require agreement.
3. **Clock Compression Is Gemini-Specific Here:** Local `Qwen3-Omni-30B-A3B` kept real time (`121.0 s` for `120.0 s` = `1.008x`) on the exact same WAVs. Passing `exact_duration_sec` from `ffprobe` resolves `91.5%` of Neon's median onset drift.

---

## Repository Contents & Provenance

- `.agents/skills/neon-audio-qa/`: ready-to-install agent skill (`SKILL.md`, standalone `scripts/scan_audio.py`, and `references/QA_PROMPTS.md`).
- `exam/`: 17 rights-cleared lossless WAV files (`r1_01.wav`–`r5_02.wav`), `exam_manifest_public.json`, `ground_truth.json`. Synthesized and open-license local sources only (no proprietary or third-party private recordings). Spoken tracks were generated via **Kokoro-82M** (`mlx-community/Kokoro-82M-bf16`, rev `a71e4d38`, **Apache-2.0**); SFX, music stems, and planted defects were synthesized in `numpy` (**CC0-1.0**).
- `harness/`: pre-registered `EXAM_SPEC_V1.md`, **238-line deterministic DSP script** `harness/src/dsp.py` (exact pre-truth frozen SHA-256 `a8d62850...`), standalone `harness/hybrid_quickstart.py`, blind exam/ablation runners (`run_blind_exam.py`, `run_ablation_v2.py`, `run_r3_solo_rubric.py`), and deterministic scorers (`score_exam.py`, `score_ablation_v2.py`).
- `results/`: full `VALIDATION_REPORT_V2.md`, `XHIGH_REPORT.md`, `xhigh_scores.json`, `R3_SOLO_RUBRIC_REPORT.md`, `r3_solo_rubric_scores.json`, `scores_v1.json`, `ablation_v2_scores.json`, `dsp_baseline_outputs.json`, and `dsp_anchors.json`.
- `requirements.lock`: pip SHA-256 hash-pinned dependencies (`numpy==2.5.4`, `scipy==1.18.1`; 127 PyPI hashes, zero known OSV vulnerabilities).
- `SANITISATION.md` & `TESTED_HASHES.json`: exact path-scrubbing notes and cryptographic SHA-256 inventory.

---

## Reproducing Locally

### 1. Prerequisites
- Python `3.12+` and `ffmpeg` / `ffprobe` on `PATH`.
- Optional (only if re-running AI trials): `Antigravity CLI 1.5.12` and/or `llama.cpp` (`v1.0.0` b12359) serving `Qwen3-Omni-30B-A3B-Instruct` `Q8_0` (API token costs outside subscription/local inference: unknown / unmeasured here).

### 2. Clean-Room Install (Hash-Locked)
```bash
python3 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements.lock
```

### 3. Run the Skill Pre-Scanner or Hybrid Quickstart
```bash
# Inspect Round 4 voiceover defects via the skill scanner (reproduces 4/5 detection, 0 FAs on clean control r4_02.wav)
.venv/bin/python .agents/skills/neon-audio-qa/scripts/scan_audio.py --audio exam/wavs/r4_01.wav --mode voiceover
.venv/bin/python .agents/skills/neon-audio-qa/scripts/scan_audio.py --audio exam/wavs/r4_02.wav --dsp-only

# Check loudness parity & generate swapped (A, B) / (B, A) prompts for a mix pair
.venv/bin/python .agents/skills/neon-audio-qa/scripts/scan_audio.py --audio exam/wavs/r3_p2_y.wav --audio-b exam/wavs/r3_p2_x.wav --mode ab-pair

# Or run the standalone quickstart script on r5_01.wav (120.000 s cues)
.venv/bin/python harness/hybrid_quickstart.py --audio exam/wavs/r5_01.wav
```

---

## Reproducibility & Credits

- Built by **Cognitive Unload** (`https://www.youtube.com/@Cognitive-Unload/`).
- Audio test tracks: **Kokoro-82M** (Apache-2.0, see `LICENSES/KOKORO-82M-APACHE-2.0.txt`) + synthesized numpy audio (**CC0-1.0**, see `LICENSES/AUDIO-CC0-1.0.txt`).
- Repository code license: MIT (`LICENSE`).
