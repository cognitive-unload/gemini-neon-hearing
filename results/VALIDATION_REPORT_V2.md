# Validation Report v2 — Pitch 1: Gemini 4 Neon Audio Audit (With Round-2 Diagnostic Ablations)

- **Story:** Pitch 1 — *"Gemini 4 Neon: Can AI Finally Hear?"* (Cognitive Unload, Type 1)
- **Channel:** Cognitive Unload (`https://www.youtube.com/@Cognitive-Unload/`)
- **Pre-Registered Spec:** `EXAM_SPEC_V1.md`
- **Run Scope:** **163 primary v1 blinded runs** (`111` isolated `agy 1.5.12` + `51` `Qwen3-Omni-30B-A3B` + `1` deterministic `ffmpeg`/DSP) + **27 Round-2 diagnostic ablation runs** = **190 total isolated runs (`$0` spend)**.

## Executive Verdict: `Change direction`

Our double-blind exam + 27-run diagnostic follow-up gives a sharper, viewer-verified 4-act engineering story than the original *"Neon wins composite Perception by >= 15 pp"* framing:

> **Validated Thesis:** *"Gemini 4 Neon Can Finally Hear — Just Don't Trust Its Clock or Its Blind A/B Picks Without Code (1 Line of `ffprobe` Fixes the Clock, 50 Lines of DSP Catch What It Still Misses)."*

1. **Act 1 — Native Ear Leap (Single-Clip Perception R1 & R2 + Zero Hallucination):** Raw `gemini-4-neon-medium` beats `gemini-4-argon-medium` by **+18.5 pp** on non-speech sound scenes (`77.8% vs 59.3%`, where Argon hallucinated female pricing dialogue, laughter, a sneeze, and shattering glass on byte-verified 4.75 s wind-chime `r1_01` run 3), beats Argon by **+25.0 pp** on real AI creator voice failures (`83.3% vs 58.3%`), and crushes local `Qwen3-Omni-30B-A3B` (`25.0%` R2 — **0/9** voice flaws caught; **+49.69 pp** strict Composite Perception lead).
2. **Act 2 — The Judge Paradox (A2 `FAIL` + Solo vs Paired Proof):** Solo (`r3_single_clip`), Neon misses **9/9 (`0.0%`)** mix/EQ/splice flaws (rating every flawed clip clean `9/10`, giving `0/9` implied wins, `8/9` ties, `1/9` loss — even hallucinating a spoken voiceover on clean instrumental `r3_p3_x` runs 2–3). **With a reference, Neon hears what is wrong (`16/18 = 88.9%` flaw cause in paired v1 Round 3, vs Argon `61.1%`, `Qwen3-Omni` `16.7%`), but it often blames the wrong clip (`12/18 = 66.7%` correct picks, `15/18 = 83.3%` Clip-A bias, `3/9 = 33.3%` order-invariant)** — going **9/9 (100%)** when clean=A vs **3/9 (33.3%)** when clean=B (`r3_p2_fwd` `0/3` despite `6/6` `harsh_thin_eq`). That collapsed Neon's order-invariance below the `>= 80%` bar and narrowed Composite Perception over Argon to **+11.73 pp** strict / **+10.50 pp** lenient (below `>= +15 pp`), failing **A2**. **Production risk for Neon critics in `video-gauntlet-loop`:** under `"disagreement = reject"`, **6/9 v1 pairs would stall with no verdict** (and in Pair 2 `harsh_thin_eq`, Neon never once picked the clean clip when flawed came first), so Neon critics will often stall the loop unless paired with swapped-order verification + DSP/human guards.
3. **Act 3 — Gemini Has No Stopwatch; `Qwen3-Omni` Does (A3 `PASS` Across R4+R5, `4/5` Caveat on R4 Alone):** Internal clock distortion is **Gemini-specific here, not universal across audio AI**. On the exact same WAV files, local **`Qwen3-Omni-30B-A3B` kept an accurate real-time clock** (`0.8%` duration error, `121 s` vs `120.0 s`; `0.88–1.00 s` median onset error, `0.97x` median ratio) while failing audio perception/QA (`0/9` R2 flaws, `0/18` R3 picks, `0/15` R4 faults, `"telephone dial tone"` collapse on R5a). By contrast, **Gemini 4 compressed internal time** via `agy 1.5.12` (transcript WAVs verified byte-identical `120.000 s`; unanchored Neon placed `r5_01` cues at ~**0.38x** true time `[0.21, 0.38, 0.47]`, estimating 120.0 s as `28–55 s`, `63.6%` dur err, `32.09 s` med onset err, and Argon at ~**0.47x** `[0.29, 0.47, 0.81]`). **Ablation 2 (`gemini-4-neon-high`)** improved mean `r5_01` dur err (`24.86%`, med `12.10 s`), and **Run 3 hit `120.0 s` (`1.465 s` med) unanchored with zero hint**, proving the full audio duration reaches the model through `agy` — so the short clock is **most likely the model's reasoning, not `agy` cutting the audio; a direct API check was not run** (no Gemini API key is on record in `model-plans`). **Ablation 1 (`duration_only` — just `exact_duration_sec` from `ffprobe`)** cut Neon's clock error by **91.5%** on `r5_01` (`32.09 s -> 2.735 s` med, `[0.82, 1.06, 1.22]`) and **71.3%** on `r4_01` (`3.87 s -> 1.11 s` med, `10/15` hits all `<= 1.68 s`), yet micro-click recall stayed **1/6 (`83.3%` missed)**. Plainly for **A3**: deterministic `ffmpeg`/DSP passes **only when Rounds 4 and 5 are combined (`13/14 = 92.9%` at `<= 0.25 s` physical onset)** — on Round 4 planted faults alone, DSP found **`4/5 = 80.0%`** (below the 90% bar, missing the voiced `5.6x`-crest click at `84.331 s`), plus `6/6` R5a onsets (`0.005 s` med) and `3/3` R5b pulses (`0.002 s` med, vs Neon `4/9`, Argon `2/9`, `Qwen3-Omni` `0/9`).
4. **Act 4 — "DSP Finds *When*, Neon Says *What*" (A4 `PASS` With Honest Division of Labor):** On Round 4 (`r4_01`), **DSP deserves full credit for the `4/5` detection recall and `0.0645 s` timestamps** — in all 3 `hybrid_dsp_neon` runs, Neon echoed DSP's exact 4 candidates (`12.2, 21.95, 51.85, 66.0 s`) and missed the exact same `84.331 s` click (Neon's R4 contribution was merging DSP's two split clipping sub-spans cleanly, attaching spoken-word context, and keeping `0/3` false alarms on clean `r4_02`). Meanwhile, **Ablation 1 (`duration_only`)** shows Neon's genuine timeline self-calibration (`32.09 s -> 2.735 s` R5a; `3.87 s -> 1.11 s` R4) from one `ffprobe` scalar, and **Round 6 (`hybrid_dsp_neon`)** proves the real perceptual synergy on `r5_01`: pairing DSP's `0.005 s` onset anchors with Neon lifted strict sound-naming recall from **77.8% (14/18)** to **94.4% (17/18)** (`18/18` lenient).

---

## 1. Pre-Registered Assumptions Scorecard (A1–A6, Primary v1 Exam)

| ID | Threshold | Verdict | Observed Evidence |
|---|---|---|---|
| **A1** | Same `agy 1.5.12` `read_file` audio route at fixed `medium` effort (`$0`) | `pass` | `111/111` clean primary runs (`+27/27` Round-2 ablations); `36/36` R3, Argon `r1_01` run 3, `r5_01` run 1, and `27/27` ablation transcripts verified byte-exact against blind WAVs. |
| **A2** | Neon beats Argon by `>= +15 pp` composite Perception, `>= 80%` R3 order-invariance, and beats `open_audio` | `fail` | **Strict Composite Perception:** Neon `70.37%` vs Argon `58.64%` (`+11.73 pp`; lenient `70.37% vs 59.87%`, `+10.50 pp`) — missed `>= +15 pp`; vs `Qwen3-Omni` `20.68%` (`+49.69 pp`). **R3 invariance:** `33.33% (3/9)` — missed `>= 80%` due to `15/18 (83.3%)` Clip-A bias despite `16/18 (88.9%)` flaw-cause accuracy. |
| **A3** | Plain DSP catches `>= 90%` deterministic faults at `<= 0.25 s`, while raw Neon misses `>= 25%` clicks/hiss or drifts `> 2.0 s` | `pass` | **Combined R4+R5 (`13/14 = 92.9%` at `<= 0.25 s` physical onset):** DSP hit `6/6` R5a (`0.005 s`), `3/3` R5b (`0.002 s`), and **`4/5 (80.0%)` on R4 alone** *(below 90% standalone, missing `84.331 s` voiced click)*. Raw Neon missed `5/6 (83.3%)` R4 clicks, hallucinated 1 click on clean `r4_02` run 3, and drifted `3.87 s` med R4 (`4.284 s` unrestricted) / `32.09 s` med R5a (`63.6%` dur err). **Key finding:** `Qwen3-Omni` did *not* drift (`0.8%` dur err, `0.88–1.00 s` onset err) — time squash is specific to Gemini via `agy`, not all AI. |
| **A4** | Hybrid cuts R4+R5a median error `>= 50%` (or `<= 1.5 s`), keeps `>= 80%` R4 recall, `<= 1` `r4_02` FA | `pass` | **Thresholds met (`0.0645 s` R4 med, `80.0% = 12/15` R4 recall, `0/3` `r4_02` FA, `0.005 s` R5a med) — with explicit attribution:** on R4, `hybrid_dsp_neon` echoed DSP's 4 candidates verbatim (`12.2, 21.95, 51.85, 66.0 s`, still missing `84.331 s`), merging split clipping spans cleanly; Neon's genuine Hybrid value on R5a was lifting strict naming **`77.8% (14/18) -> 94.4% (17/18)`** on DSP's `0.005 s` clock *(while `duration_only` Ablation 1 cut Neon's own drift to `1.11 s` R4 / `2.735 s` R5a)*. |
| **A5** | Audited open-weight audio model passes `repo-demos-install-audit` & completes `3 x 17` valid JSONs | `pass` | `Qwen3-Omni-30B-A3B-Instruct` Q8_0 (`llama.cpp v1.0.0` b12359) audited `install` prior to execution and finished `51/51` clean JSONs (`$0` local). |
| **A6** | 100% rights-cleared audio (`0` private clips / `0` uncleared music) documented in manifest | `pass` | `17/17` lossless WAVs verified (Apache-2.0 Kokoro-82M voices + CC0-1.0 numpy synth, `$0`). |

---

## 2. Cryptographic & Media Audit Verification

| Artifact / Audit Check | Result | SHA-256 / Verification |
|---|---|---|
| `ground_truth.json` | PASS | `11c254082fb7a5502a2aac8d6065dfeda5c195eb6ab8706cec144fd53b690852` |
| `open_audio_outputs.json` | PASS | `1dfedb6cc4230e0b90489cb75d03d183a9b6a7ac51fc1ccfd267574a37b17205` |
| `exam_manifest_public.json` | PASS | `1a59500441778a5fedbb3b7dc6d3dfeeafb78a6fced98f860098d9efe236a1da` |
| `dsp_baseline_outputs.json` | PASS | `97e2bdd9a9c17449ea2b01a4dcdd5127a8e1ef06a96ecef6e688524197057804` |
| `dsp_anchors.json` | PASS | `a51e6f8fabad038bfca59f8b44762fc9cc7c27fa2098bce1f4c0bd1f8c5df14c` |
| `blind_outputs_neon_argon_v1.tar.gz` | PASS | `dd4f322024eed62597c3a8440ceafcde5c063df79bb01dd9f63e3273580f6b08` |
| `blind_outputs_neon_argon_v1.md` | PASS | `6f4dbcd8645f0aa763dc13f7f06ecf45033260c1bf83700d7e276ea3c0d44ba1` |
| `unsealed/CROSSCHECK_V1.md` (Peer Reviewer v1 check) | PASS | `4b259e00ab449de590ea4ee38c51c941c8bb3a6887254b25ac19e793fd15d036` |
| `unsealed/CROSSCHECK_V2.md` (Peer Reviewer v2 ablation check) | PASS | `03da0e404186d404eeecfaab3b48a19c95707107a8c9a88a3ec3a618bac378f6` |
| `ablation_v2/ablation_v2_outputs.tar.gz` (27 runs) | PASS | `15576b8e90b42d4b7ff9fc566540a06b976da4d4b76f5a04ba2b8a5564f77b33` |
| `ablation_v2/ablation_v2_outputs.md` (inner JSON `eb977134...6927d`) | PASS | `aee6555749bf0a012e8db1957bcff506a26197c29905082ee429fc85e5207920` |
| `ablation_v2/ablation_v2_scores.json` | PASS | `54f293da8dcf929f00aa09e4b960a82e460930b2d0cd9e752565c512cbdf73fb` |
| Blind WAV pack (`blind/*.wav`) | PASS | `17/17` manifest SHA-256 matches |
| Primary R3 & Argon `r1_01` run 3 transcript media | PASS | `36/36` R3 pairs + Argon `r1_01` r3 byte-exact WAV SHA-256 |
| Round-2 ablation transcript media (`ablation_v2/`) | PASS | `27/27` byte-exact WAV SHA-256 matches (incl. `r5_01.wav` = `120.000 s`) |

**Physical Waveform Inspection (`r4_01.wav`):** Hard clipping (`+14 dB`, `782` full-scale samples) starts physically at **`21.9400 s`** (`[21.94–22.6163 s]` 715 samples + `[23.3878–23.4484 s]` 67 samples, vs `21.68 s` nominal ramp start). Click 1 (`12.217 s`, pause) has peak `-10.5 dBFS` over `-90.3 dBFS` surrounding (`9729x` crest -> DSP `0.000 s` err); Click 2 (`84.331 s`, voiced *"screen"*) has peak `-8.7 dBFS` over `-23.6 dBFS` active speech (`5.6x` crest -> missed by DSP, Neon, and Hybrid).

---

## 3. Primary v1 Scoreboard — Part A: Perception (Rounds 1–3)

| Contestant | R1 Strict | R1 Lenient | R1 Speech Halluc. | R2 Voice Flaws | R3 Pick Rate | R3 Order-Invariance | R3 Flaw Cause | R3 Composite | **Composite Perception (Strict / Lenient)** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `dsp` | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | **N/A (DSP blind)** |
| Gemini 4 Neon (`gemini-4-neon-medium`) | 77.8% | 77.8% | 0/9 | 83.3% | 66.7% (12/18) | 33.3% (3/9) | 88.9% (16/18) | 50.0% | **70.37% / 70.37%** |
| Gemini 4 Argon (`gemini-4-argon-medium`) | 59.3% | 63.0% | 1/9 | 58.3% | 72.2% (13/18) | 44.4% (4/9) | 61.1% (11/18) | 58.3% | **58.64% / 59.87%** |
| Qwen3-Omni-30B-A3B (`open_audio`) | 37.0% | 74.1% | 0/9 | 25.0% | 0.0% (0/18) | 0.0% (0/9) | 16.7% (3/18) | 0.0% | **20.68% / 33.02%** |

- **R3 Pick Distribution (`A / B / tie` across 18 runs):** Neon `A=15, B=3, tie=0` (`83.3%` A-bias) | Argon `A=8, B=9, tie=1` | `open_audio` `A=0, B=3, tie=15` (`83.3%` ties).

---

## 4. Primary v1 Scoreboard — Parts B & C: Precision & Hybrid (Rounds 4–6)

### Round 4 & Round 6 — 92 s Micro-Defects (`r4_01.wav` 5 faults + `r4_02.wav` clean control)

| Contestant | Recall (`<=5s`) | Recall (Unrestricted) | Strict `<=1.0s` Hits | Click/Pop (`<=5s`) | Med Err (`<=5s` / Unrestr.) | Unmatched `r4_01` | Clean `r4_02` FA |
|---|---:|---:|---:|---:|---:|---:|---:|
| Plain ffmpeg/DSP (`dsp`) | 80.0% (4/5) | 80.0% (4/5) | 80.0% (4/5) | 1/2 | 0.0595s / 0.0595s | 1 | 0/1 |
| Hybrid DSP + Neon (`hybrid_dsp_neon`) | 80.0% (12/15) | 80.0% (12/15) | 80.0% (12/15) | 3/6 | 0.0645s / 0.0645s | 0 | 0/3 |
| Gemini 4 Neon (`gemini-4-neon-medium`) | 40.0% (6/15) | 66.7% (10/15) | 6.7% (1/15) | 1/6 | 3.87s / 4.284s | 4 | 1/3 |
| Gemini 4 Argon (`gemini-4-argon-medium`) | 40.0% (6/15) | 80.0% (12/15) | 0.0% (0/15) | 2/6 | 2.13s / 4.384s | 6 | 0/3 |
| Qwen3-Omni-30B-A3B (`open_audio`) | 0.0% (0/15) | 0.0% (0/15) | 0.0% (0/15) | 0/6 | N/A | 0 | 0/3 |

*Note: `hybrid_dsp_neon` inherited its `4/5` detection set and `0.0645 s` timestamps directly from DSP (`dsp_anchors.json`) in 3/3 runs while merging DSP's 2 split clipping bursts (`unmatched=0`) and keeping `0/3` false alarms on `r4_02`.*

### Round 5a, 5b & Round 6 — Stopwatch Cues (`r5_01.wav`, 120.0 s) & Pulse Counting (`r5_02.wav` `[9, 5, 8]`)

| Contestant | R5a Dur Err | R5a Onset Ratio (`pred/true` min/med/max) | R5a Strict Labels | R5a Lenient Labels | R5a Med / Max Onset Err | R5b Exact Bursts | R5b MAE | R5b Med Onset Err |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| Plain ffmpeg/DSP (`dsp`) | 0.0% | [1.00, 1.00, 1.00] | 0.0% (0/6) | 0.0% (0/6) | 0.005s / 0.03s | 100.0% (3/3) | 0 | 0.002s |
| Hybrid DSP + Neon (`hybrid_dsp_neon`) | 0.0% | [1.00, 1.00, 1.00] | 94.4% (17/18) | 100.0% (18/18) | 0.005s / 0.03s | N/A | N/A | N/A |
| Gemini 4 Neon (`gemini-4-neon-medium`) | 63.6% | [0.21, 0.38, 0.47] | 77.8% (14/18) | 88.9% (16/18) | 32.09s / 83.38s | 44.4% (4/9) | 0.78 | 2.046s |
| Gemini 4 Argon (`gemini-4-argon-medium`) | 56.4% | [0.29, 0.47, 0.81] | 77.8% (14/18) | 77.8% (14/18) | 25.5s / 77.08s | 22.2% (2/9) (1 seg err) | 0.83 *(3-burst)* | 2.046s |
| Qwen3-Omni-30B-A3B (`open_audio`) | 0.8% | [0.90, 0.97, 0.99] *(order-idx: [0.93, 0.99, 1.28])* | 0.0% (0/18) | 22.2% (4/18) | 0.88s / 10.88s | 0.0% (0/9) | 3.67 | 0.209s |

*Note on Argon `r5_02` MAE: across runs 1–2 (`3` bursts), MAE = `0.83`; across all 3 runs using the peer reviewer's 3-slot index match (`CROSSCHECK_V1.md`), MAE = `1.78` due to run 3 splitting burst 1 into 4 bursts `[3, 6, 4, 7]`.*

---

## 5. Transparent Open-Text Audit Tables (Primary v1 Round 1 & Round 5a)

### Round 1 Per-Run Semantic Judgments

| Model | Clip | Run | Speech? | Labels Emitted | Strict | Lenient | Notes |
|---|---|---:|---|---|---:|---:|---|
| `gemini-4-neon-medium` | `r1_01` | 1 | no | high-pitched metallic chimes ringing; resonant bell and chime cluster; sustained metallic chime overtones fading out | 1.00 | 1.00 | strict miss: none |
| `gemini-4-neon-medium` | `r1_01` | 2 | no | bright metallic chimes/bells ringing; sustained metallic chime resonance fading out | 1.00 | 1.00 | strict miss: none |
| `gemini-4-neon-medium` | `r1_01` | 3 | no | metallic wind chimes begin ringing with bright overlapping bell-like tones; dense cascade of shimmering metallic wind chimes clinking and resonating together; additional softer metallic chime strikes over sustained ringing overtones; sustained metallic chime resonance gradually decaying into silence | 1.00 | 1.00 | strict miss: none |
| `gemini-4-neon-medium` | `r1_02` | 1 | no | three knocks on a wooden door; rising high-pitched tea kettle whistle; two-tone ding-dong doorbell chime | 0.67 | 0.67 | strict miss: glass clinks |
| `gemini-4-neon-medium` | `r1_02` | 2 | no | three rapid knocks on a hollow wooden surface (door knocking); high-pitched breathy whistling sound (like a tea kettle or steam whistle); two-tone descending doorbell chime (ding-dong) | 0.67 | 0.67 | strict miss: glass clinks |
| `gemini-4-neon-medium` | `r1_02` | 3 | no | wooden knocking; tea kettle whistle; two-tone metallic bell chime | 0.67 | 0.67 | strict miss: glass clinks |
| `gemini-4-neon-medium` | `r1_03` | 1 | no | continuous heavy rain or rushing water noise; wailing emergency vehicle siren fading in and out | 0.67 | 0.67 | strict miss: wind |
| `gemini-4-neon-medium` | `r1_03` | 2 | no | heavy rain or rushing water noise; wailing emergency siren | 0.67 | 0.67 | strict miss: wind |
| `gemini-4-neon-medium` | `r1_03` | 3 | no | continuous heavy rain; wailing emergency siren | 0.67 | 0.67 | strict miss: wind |
| `gemini-4-argon-medium` | `r1_01` | 1 | no | ascending glockenspiel or chime glissando (magical sparkle chime); sustained metallic bell chime resonance decaying to silence | 1.00 | 1.00 | strict miss: none |
| `gemini-4-argon-medium` | `r1_01` | 2 | no | ascending glockenspiel / chime musical flourish; sustained metallic chime resonance and decay | 1.00 | 1.00 | strict miss: none |
| `gemini-4-argon-medium` | `r1_01` | 3 | YES (-0.5) | human speech (female voice speaking a sentence); laughter / giggle (two bursts of female laughter); sneeze; glass breaking / shattering | 0.00 | 0.00 | strict miss: wind-chime/bell cluster |
| `gemini-4-argon-medium` | `r1_02` | 1 | no | three rapid knocking or wooden tapping sounds; rising-pitch whistle or frequency sweep; high-pitched metallic bell chime or ding | 0.67 | 0.67 | strict miss: glass clinks |
| `gemini-4-argon-medium` | `r1_02` | 2 | no | ambient background hiss; three short percussive taps or clicks; rising frequency sweep tone; two high-pitched bell chimes | 0.00 | 0.33 | strict miss: door knocks, kettle whistle, glass clinks |
| `gemini-4-argon-medium` | `r1_02` | 3 | no | three hollow wooden knocking or tapping sounds; rising-pitch whistle or whistling kettle sound; two metallic bell chimes or dings | 0.67 | 0.67 | strict miss: glass clinks |
| `gemini-4-argon-medium` | `r1_03` | 1 | no | heavy rain and static noise; wailing emergency siren | 0.67 | 0.67 | strict miss: wind |
| `gemini-4-argon-medium` | `r1_03` | 2 | no | heavy rain and downpour; thunder; wailing emergency vehicle siren | 0.67 | 0.67 | strict miss: wind |
| `gemini-4-argon-medium` | `r1_03` | 3 | no | heavy rain and downpour noise; wailing emergency vehicle siren | 0.67 | 0.67 | strict miss: wind |
| `open_audio` | `r1_01` | 1 | no | doorbell | 0.00 | 1.00 | strict miss: wind-chime/bell cluster |
| `open_audio` | `r1_01` | 2 | no | doorbell | 0.00 | 1.00 | strict miss: wind-chime/bell cluster |
| `open_audio` | `r1_01` | 3 | no | doorbell | 0.00 | 1.00 | strict miss: wind-chime/bell cluster |
| `open_audio` | `r1_02` | 1 | no | knocking; steam whistle; bell | 0.67 | 0.67 | strict miss: glass clinks |
| `open_audio` | `r1_02` | 2 | no | tap; whistle; bell | 0.33 | 0.67 | strict miss: door knocks, glass clinks |
| `open_audio` | `r1_02` | 3 | no | knocking; whistling; buzzer | 0.67 | 0.67 | strict miss: glass clinks |
| `open_audio` | `r1_03` | 1 | no | rain; siren | 0.67 | 0.67 | strict miss: wind |
| `open_audio` | `r1_03` | 2 | no | static; siren | 0.33 | 0.33 | strict miss: rain, wind |
| `open_audio` | `r1_03` | 3 | no | rain; siren | 0.67 | 0.67 | strict miss: wind |

### Round 5a Per-Run Semantic Cue-Label Judgments (`r5_01.wav`)

| Model | Run | Aligned Cue Labels & Onsets (Strict / Lenient) | Strict | Lenient |
|---|---:|---|---:|---:|
| `gemini-4-neon-medium` | 1 | #1 5.2s `door knock` [OK], #2 12.2s `electric buzzer` [LEN], #3 18.1s `water droplets` [OK], #4 24.6s `bell chime` [OK], #5 33.8s `whistle` [OK], #6 42.8s `electronic ring` [MISS] | 4/6 | 5/6 |
| `gemini-4-neon-medium` | 2 | #1 5.2s `door knocking` [OK], #2 13.5s `buzzing vibration` [MISS], #3 20.5s `water droplets` [OK], #4 27.5s `bell chime` [OK], #5 38.0s `whistle` [OK], #6 48.5s `car horn` [OK] | 5/6 | 5/6 |
| `gemini-4-neon-medium` | 3 | #1 3.0s `wooden knocking / tapping` [OK], #2 7.8s `vibrating buzzer / electronic trill` [LEN], #3 11.4s `rapid popping / water droplets` [OK], #4 15.1s `metallic bell chime` [OK], #5 20.6s `high-pitched whistle` [OK], #6 25.5s `low horn / buzzer` [OK] | 5/6 | 6/6 |
| `gemini-4-argon-medium` | 1 | #1 11.4s `three short low beeps / knocking tones` [OK], #2 22.8s `telephone ringtone / warbling electronic alert` [OK], #3 30.8s `four water droplet / popping clicks` [OK], #4 39.8s `chime / bell ding` [OK], #5 53.6s `rising whistle / firework screech` [OK], #6 66.8s `dual-tone electronic beep / phone tone` [MISS] | 5/6 | 5/6 |
| `gemini-4-argon-medium` | 2 | #1 6.1s `door knock` [OK], #2 16.1s `phone ringing` [OK], #3 22.3s `water dripping` [OK], #4 29.8s `bell chime` [OK], #5 37.5s `whistle` [OK], #6 44.6s `beep` [MISS] | 5/6 | 5/6 |
| `gemini-4-argon-medium` | 3 | #1 4.2s `three knocks` [OK], #2 10.6s `alarm beep` [MISS], #3 15.0s `water drips` [OK], #4 19.6s `bell chime` [OK], #5 26.8s `whistle` [OK], #6 31.8s `phone ring` [MISS] | 4/6 | 4/6 |
| `open_audio` | 1 | #1 13.0s `telephone dial tone` [MISS], #2 32.0s `telephone dial tone` [LEN], #3 44.0s `telephone dial tone` [MISS], #4 58.0s `telephone dial tone` [MISS], #6 98.0s `telephone dial tone` [MISS] | 0/6 | 1/6 |
| `open_audio` | 2 | #1 13.0s `telephone dial tone` [MISS], #2 31.0s `telephone dial tone` [LEN], #3 43.0s `beep` [MISS], #4 58.0s `telephone bell ringing` [LEN], #6 108.0s `telephone bell ringing` [MISS] | 0/6 | 2/6 |
| `open_audio` | 3 | #1 13.0s `telephone dial tone` [MISS], #2 32.0s `telephone dial tone` [LEN], #3 44.0s `telephone dial tone` [MISS], #4 58.0s `telephone dial tone` [MISS], #6 99.0s `telephone dial tone` [MISS] | 0/6 | 1/6 |
| `hybrid_dsp_neon` | 1 | #1 14.0s `door knock` [OK], #2 32.85s `telephone ring` [OK], #3 44.5s `water drops` [OK], #4 58.55s `bell chime` [OK], #5 84.45s `whistle` [OK], #6 108.85s `car horn` [OK] | 6/6 | 6/6 |
| `hybrid_dsp_neon` | 2 | #1 14.0s `wood knocking` [OK], #2 32.85s `electric buzzer` [LEN], #3 44.5s `water droplets` [OK], #4 58.55s `bell chime` [OK], #5 84.45s `whistle` [OK], #6 108.85s `car horn` [OK] | 5/6 | 6/6 |
| `hybrid_dsp_neon` | 3 | #1 14.0s `door knock` [OK], #2 32.85s `telephone ring` [OK], #3 44.5s `water drops` [OK], #4 58.55s `bell chime` [OK], #5 84.45s `referee whistle` [OK], #6 108.85s `car horn` [OK] | 6/6 | 6/6 |

---

## 6. Round-2 Diagnostic Micro-Ablations (27 Isolated `$0` Runs — Separate From Primary A1–A6)

### Ablation 1 & 2 — Clock Anchor (`exact_duration_sec` only) & `gemini-4-neon-high` on `r5_01.wav` (`120.0 s`) + `r4_01.wav` (`92.048 s`)

| Condition | Target | Model | Dur Err | `r5_01` Onset Ratio (`[min, med, max]`) | Med / Max Err | Strict Labels (`R5a`) or Recall (`R4`) |
|---|---|---|---:|---|---:|---|
| Primary v1 Unanchored (baseline) | `r5_01` | `neon-medium` | 63.6% | [0.21, 0.38, 0.47] | 32.09s / 83.38s | Strict 14/18 (`77.8%`) |
| **Ablation 2 Unanchored (`high`)** | `r5_01` | `neon-high` | 24.9% | [0.57, 0.66, 1.06] | 12.1s / 46.88s | Strict 15/18 (83.3%), Lenient 17/18 |
| **Ablation 1 `duration_only` (`ffprobe` 1 number)** | `r5_01` | `neon-medium` | 0.0% | [0.82, 1.06, 1.22] | **2.735s** / 12.95s | Strict 14/18 (77.8%), Lenient 15/18 |
| Primary v1 Full DSP Anchors (`R6`) | `r5_01` | `hybrid_dsp_neon` | 0.0% | [1.00, 1.00, 1.00] | 0.005s / 0.03s | Strict 17/18 (`94.4%`), Lenient `18/18` |
| Primary v1 Unanchored (baseline) | `r4_01` | `neon-medium` | — | — | 3.87s (`<=5s`) / 4.284s (unrestr.) | Recall `6/15 (40.0%)` `<=5s`, `<=1s`: `1/15 (6.7%)`, Clicks `1/6` |
| **Ablation 1 `duration_only` (`92.048 s`)** | `r4_01` | `neon-medium` | — | — | **1.11s** (max 1.68s) | Recall **10/15 (66.7%)** `<=5s` & unrestr., `<=1s`: **5/15 (33.3%)**, **Clicks `1/6`**, Unmatched `0` |

**Per-Run Breakdown (`duration_only` & `neon-high`):**
- `duration_only` `r5_01` run 1: `est_dur=120.0 s` (`0.0%` err), med err `4.595 s`, ratios `[1.0, 1.14, 1.22]` -> #1 16.5s (2.5s err, `knocking on wood`), #2 36.0s (3.15s err, `electric buzzing`), #3 53.5s (8.97s err, `rapid clicking and popping sounds`), #4 71.5s (12.95s err, `metallic bell chime`), #5 90.5s (6.04s err, `whistle`), #6 108.5s (0.38s err, `sustained horn or alarm tone`)
- `duration_only` `r5_01` run 2: `est_dur=120.0 s` (`0.0%` err), med err `2.095 s`, ratios `[0.99, 1.04, 1.09]` -> #1 14.0s (0.0s err, `three wooden knocks`), #2 35.0s (2.15s err, `electronic trill / buzzer`), #3 48.5s (3.97s err, `four rapid high-pitched blips / pops`), #4 61.8s (3.25s err, `resonant bell chime`), #5 86.5s (2.04s err, `whistle`), #6 107.5s (1.38s err, `harsh electronic horn / alarm tone`)
- `duration_only` `r5_01` run 3: `est_dur=120.0 s` (`0.0%` err), med err `2.735 s`, ratios `[0.82, 0.99, 1.08]` -> #1 11.5s (2.5s err, `wooden door knock`), #2 31.0s (1.85s err, `telephone ring`), #3 47.5s (2.97s err, `water drops`), #4 63.5s (4.95s err, `metallic bell chime`), #5 86.0s (1.54s err, `referee whistle`), #6 105.5s (3.38s err, `car horn`)
- `neon-high` `r5_01` run 1: `est_dur=70.5 s` (`41.25%` err), med err `18.29 s`, ratios `[0.57, 0.62, 0.65]` -> #1 9.0s (5.0s err, `door knocking`), #2 20.0s (12.85s err, `buzzer`), #3 29.0s (15.53s err, `water dripping`), #4 37.5s (21.05s err, `bell chime`), #5 50.5s (33.96s err, `whistle`), #6 62.0s (46.88s err, `car horn`)
- `neon-high` `r5_01` run 2: `est_dur=80.0 s` (`33.33%` err), med err `16.29 s`, ratios `[0.61, 0.66, 0.68]` -> #1 8.5s (5.5s err, `double wood knock`), #2 21.5s (11.35s err, `rapid buzzing vibration`), #3 30.5s (14.03s err, `water droplets`), #4 40.0s (18.55s err, `bell chime`), #5 56.0s (28.46s err, `whistle`), #6 71.0s (37.88s err, `buzzer horn`)
- `neon-high` `r5_01` run 3: `est_dur=120.0 s` (`0.0%` err), med err `1.465 s`, ratios `[0.96, 1.0, 1.06]` -> #1 14.0s (0.0s err, `three wooden knocks`), #2 33.0s (0.15s err, `electric buzzer`), #3 47.0s (2.47s err, `water droplets`), #4 62.0s (3.45s err, `metallic bell chime`), #5 84.0s (0.46s err, `whistle`), #6 105.0s (3.88s err, `electronic horn beep`)
- `duration_only` `r4_01` run 1: `3/5` matched, `0` unmatched -> clipping @ 20.2s (GT 21.68s, err 1.48s), silence_gap @ 50.5s (GT 51.86s, err 1.36s), hiss @ 65.5s (GT 65.888s, err 0.388s)
- `duration_only` `r4_01` run 2: `3/5` matched, `0` unmatched -> clipping @ 21.2s (GT 21.68s, err 0.48s), silence_gap @ 51.0s (GT 51.86s, err 0.86s), hiss @ 67.5s (GT 65.888s, err 1.612s)
- `duration_only` `r4_01` run 3: `4/5` matched, `0` unmatched -> click_pop @ 11.4s (GT 12.217s, err 0.817s), clipping @ 20.0s (GT 21.68s, err 1.68s), silence_gap @ 50.5s (GT 51.86s, err 1.36s), hiss @ 65.5s (GT 65.888s, err 0.388s)

### Ablation 3 — Solo Single-Clip Round 3 Judging (`r3_single_clip`, 18 Isolated Runs on `gemini-4-neon-medium`)

| Pair | Condition | Clean Scores (r1, r2, r3) | Flawed Scores (r1, r2, r3) | Standalone Exact Class. | Flawed Detected | Implied Pairwise (`W / T / L`) | Paired v1 Result |
|---|---|---|---|---:|---:|---|---|
| `r3_p1` | `vocal_buried` | [9, 9, 9] (mean 9.0) | [9, 9, 9] (mean 9.0) | 3/6 (clean 3/3, flaw 0/3) | **0/3** (`9/10`, `none`) | `0 / 3 / 0` | `pick=4/6`, `cause=4/6` |
| `r3_p2` | `harsh_thin_eq` | [9, 9, 9] (mean 9.0) | [9, 9, 9] (mean 9.0) | 3/6 (clean 3/3, flaw 0/3) | **0/3** (`9/10`, `none`) | `0 / 3 / 0` | `pick=3/6`, `cause=6/6` |
| `r3_p3` | `rhythm_or_splice_glitch` | [9, 3, 9] (mean 7.0) | [9, 9, 9] (mean 9.0) | 2/6 (clean 2/3, flaw 0/3) | **0/3** (`9/10`, `none`) | `0 / 2 / 1` | `pick=5/6`, `cause=6/6` |
| **TOTAL** | All 3 Pairs | Mean 8.33/10 | Mean 9.00/10 | **8/18 (44.44%)** *(clean FP 1/9)* | **0/9 (`0.0%`)** | **`0/9` win, `8/9` tie, `1/9` loss** | `pick=12/18`, `inv=3/9`, `cause=16/18` |

*Note on clean false positive (`r3_p3_x` runs 2 & 3):* on instrumental-only `r3_p3_x.wav`, run 2 scored `3/10` and hallucinated `vocal_buried` (*"background music track is mixed far too loud relative to the spoken voiceover"*), and run 3 scored `9/10` (`has_flaw=false`) while also claiming *"spoken voice sits clearly and intelligibly above the background music."* Meanwhile, every single flawed clip across all 9 runs (`vocal_buried`, `harsh_thin_eq`, `rhythm_or_splice_glitch`) was rated `9/10` clean!

---

## 7. Editorial & Production Decision Options (`Change direction`)

**Known Production Risk for Requested Neon Critics (`video-gauntlet-loop`):** Under `"disagreement = reject"`, **`6/9` v1 Round 3 pairs would stall with no verdict** (and in Pair 2 `harsh_thin_eq`, Neon never once picked the clean clip when the flawed clip came first). Solo judging also fails (`0/9` flawed clips detected). So Neon audio critics will often stall the gauntlet loop unless paired with swapped-order `fwd` + `rev` checks plus DSP click/timing checks (or DSP + human ear on Sound QA).

- **Option A (`Change direction` -> Reframed 4-Act Story + Swapped-Order Neon Critics + DSP Click/Timing Check — Recommended):** Keeps Neon makers and Neon critics (running swapped-order `fwd` + `rev` blind pairs) while adding deterministic `ffmpeg`/DSP checks for clicks, clipping, silence, and timestamps, framed around the validated 4-act thesis (*"Gemini 4 Neon Can Finally Hear — Just Don't Trust Its Clock or Its Blind A/B Picks Without Code"*).
- **Option B (`Change direction` -> Reframed 4-Act Story + DSP & Human Ear on Sound QA Instead of Neon Audio Critics):** Uses the same validated 4-act script, but avoids gauntlet-loop critic stalls by scoring Sound QA with DSP + human listening rather than Neon audio critics.
- **Option C (`Drop`):** Shelve Pitch 1 if A2's failure and two-clip position bias make the story unsuitable.
