# Targeted `gemini-4-neon-xhigh` Blind Check Report (30 Isolated Runs)

- **Model:** `gemini-4-neon-xhigh` via `Antigravity CLI` (`1.5.12`)
- **Transcript Byte-Exact Media Audit:** `30/30` verified (`18/18` R3 pairs, `3/3` R5a `120.000 s` WAVs, `init_model == gemini-4-neon-xhigh`)
- **Artifacts:**
  - `xhigh_outputs_v1.tar.gz` sha256 `aaee2fddfd0e23f32a9219f5cda79b42577b73a28a075aaa2378290dd1ccfbb4`
  - `xhigh_outputs_v1.md` sha256 `1f45a2bd0cca6fb53ba5605b2216d05b2d6c3b22420636615c59da3cd9397fab`

## 1. Round 3 — Paired Blind A/B Mix Judge (`18` Runs)

| Model | Correct Picks | Order-Invariant Pairs | Flaw Cause | Pick Dist (`A/B/tie`) | Clean=A | Clean=B | Composite |
|---|---:|---:|---:|---|---:|---:|---:|
| `gemini-4-neon-xhigh` | **50.0% (9/18)** | **11.11% (1/9)** | 61.11% (11/18) | `A=10, B=1, tie=7` | 8/9 | 1/9 | 30.56% |
| `gemini-4-neon-medium` | 66.67% (12/18) | 33.33% (3/9) | 88.89% (16/18) | `A=15, B=3, tie=0` | 9/9 | 3/9 | 50.0% |
| `gemini-4-argon-medium` | 72.22% (13/18) | 44.44% (4/9) | 61.11% (11/18) | `A=8, B=9, tie=1` | — | — | 58.33% |
| `Qwen3-Omni-30B-A3B` | 0.0% (0/18) | 0.0% (0/9) | 16.67% (3/18) | `A=0, B=3, tie=15` | — | — | 0.0% |

### Per-Pair `xhigh` Breakdown
- `r3_p1` (`vocal_buried`): fwd `2/3`, rev `0/3`, order-invariant `0/3`, flaw cause `3/6`
- `r3_p2` (`harsh_thin_eq`): fwd `0/3`, rev `3/3`, order-invariant `0/3`, flaw cause `4/6`
- `r3_p3` (`rhythm_or_splice_glitch`): fwd `3/3`, rev `1/3`, order-invariant `1/3`, flaw cause `4/6`

## 2. Round 5a — Unanchored 120.0 s Stopwatch Cues (`r5_01.wav`, 3 Runs)

| Model | Mean Dur Err | Ratio `[min, med, max]` | Med / Max Onset Err | Strict Cue Labels | Lenient Cue Labels |
|---|---:|---|---:|---:|---:|
| **`gemini-4-neon-xhigh`** | **49.86%** | `[0.49, 0.53, 0.58]` | **22.89s / 55.88s** | 83.33% (15/18) | 100.0% (18/18) |
| `gemini-4-neon-high` | 24.86% | `[0.57, 0.66, 1.06]` | 12.1s / 46.88s | 83.33% (15/18) | 94.44% (17/18) |
| `gemini-4-neon-medium` | 63.61% | `[0.21, 0.38, 0.47]` | 32.09s / 83.38s | 77.78% (14/18) | 88.89% (16/18) |
| `Qwen3-Omni-30B-A3B` | 0.83% | `[0.9, 0.97, 0.99]` | 0.88s / 10.88s | 0.0% (0/18) | 22.22% (4/18) |
| `hybrid_dsp_neon` | 0.0% | `[1.0, 1.0, 1.0]` | 0.005s / 0.03s | 94.44% (17/18) | 100.0% (18/18) |
| `dsp` | 0.0% | `[1.0, 1.0, 1.0]` | 0.005s / 0.03s | 0.0% (0/6) | 0.0% (0/6) |

### R5a Per-Run Breakdown (`gemini-4-neon-xhigh`)
- Run 1: `est_dur=59.5 s` (`50.42%` err), med err `23.29 s`, ratios `[0.49, 0.54, 0.55]` -> #1 7.4s (6.6s err) `door knock`, #2 18.2s (14.65s err) `electric buzzer`, #3 24.6s (19.93s err) `bubbling water droplets`, #4 31.9s (26.65s err) `bell chime`, #5 43.3s (41.16s err) `referee whistle`, #6 53.1s (55.78s err) `car horn`
- Run 2: `est_dur=60.0 s` (`50.0%` err), med err `24.14 s`, ratios `[0.49, 0.51, 0.53]` -> #1 7.0s (7.0s err) `door knock`, #2 17.0s (15.85s err) `electric buzzer`, #3 23.8s (20.73s err) `water droplets / bubble pops`, #4 31.0s (27.55s err) `bell chime`, #5 43.0s (41.46s err) `whistle`, #6 53.0s (55.88s err) `car horn`
- Run 3: `est_dur=61.0 s` (`49.17%` err), med err `21.79 s`, ratios `[0.51, 0.55, 0.58]` -> #1 7.5s (6.5s err) `door knock`, #2 18.2s (14.65s err) `electric buzzer`, #3 26.0s (18.53s err) `water drops`, #4 33.5s (25.05s err) `bell chime`, #5 45.5s (38.96s err) `referee whistle`, #6 55.0s (53.88s err) `car horn`

## 3. Round 5b — Rapid Pulse Counting (`r5_02.wav` `[9, 5, 8]`, 3 Runs)

| Model | Exact Bursts | MAE (3-burst) | Med Onset Err | Seg Errors |
|---|---:|---:|---:|---:|
| **`gemini-4-neon-xhigh`** | **55.56% (5/9)** | 0.56 | 2.046s | 0 |
| `gemini-4-neon-medium` | 44.44% (4/9) | 0.78 | 2.046s | 0 |
| `dsp` | 100.0% (3/3) | 0 | 0.002s | 0 |

- Run 1: `counts=[11, 6, 8]` (errs=[2, 1, 0], onsets=[0.8, 3.8, 6.4])
- Run 2: `counts=[9, 5, 7]` (errs=[0, 0, 1], onsets=[0.6, 3.2, 5.4])
- Run 3: `counts=[9, 5, 7]` (errs=[0, 0, 1], onsets=[0.5, 3.2, 5.5])

## 4. Round 4 — 92 s Micro-Defects (`r4_01.wav` + `r4_02.wav` Clean Control, 6 Runs)

| Model | Recall (`<=5s`) | Recall (Unrestr.) | `<=1.0s` Hits | Clicks (`<=5s`) | `12.217s` Click | `84.331s` Click | Med Err (`<=5s` / Unr.) | Unmatched `r4_01` | `r4_02` FA |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`gemini-4-neon-xhigh`** | **73.33% (11/15)** | 73.33% (11/15) | 0.0% (0/15) | 2/6 | 2/3 | 0/3 | 4.088s / 4.088s | 0 | 0/3 |
| `gemini-4-neon-medium` | 40.0% (6/15) | 66.67% (10/15) | 6.67% (1/15) | 1/6 | — | — | 3.87s / 4.284s | 4 | 1/3 |
| `hybrid_dsp_neon` | 80.0% (12/15) | 80.0% (12/15) | 80.0% (12/15) | 3/6 | 3/3 | 0/3 | 0.0645s / 0.0645s | 0 | 0/3 |
| `dsp` | 80.0% (4/5) | 80.0% (4/5) | 80.0% (4/5) | 1/2 | 1/1 | 0/1 | 0.0595s / 0.0595s | 1 | 0/1 |

### R4 Per-Run Matched & Unmatched (`gemini-4-neon-xhigh`, Unrestricted)
- Run 1: matched=[click_pop@11.0s (gt 12.217s, err 1.217s), clipping@19.4s (gt 21.68s, err 2.28s), silence_gap@47.7s (gt 51.86s, err 4.16s), hiss@61.8s (gt 65.888s, err 4.088s)] | unmatched_r4_01=[none] | r4_02_FA=0
- Run 2: matched=[clipping@19.4s (gt 21.68s, err 2.28s), silence_gap@47.7s (gt 51.86s, err 4.16s), hiss@61.5s (gt 65.888s, err 4.388s)] | unmatched_r4_01=[none] | r4_02_FA=0
- Run 3: matched=[click_pop@10.8s (gt 12.217s, err 1.417s), clipping@19.3s (gt 21.68s, err 2.38s), silence_gap@47.5s (gt 51.86s, err 4.36s), hiss@61.3s (gt 65.888s, err 4.588s)] | unmatched_r4_01=[none] | r4_02_FA=0
