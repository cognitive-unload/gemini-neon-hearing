#!/usr/bin/env python3
"""Minimal Audio QA Kit: ffprobe duration + deterministic DSP anchors + swapped-order Gemini 4 Neon prompt templates.

Implements the verified workflow from Cognitive Unload ("Gemini 4 Neon: Can AI Finally Hear?"):
  1. Never let Gemini estimate audio timestamps unanchored — extract exact duration via ffprobe first.
  2. Never trust solo quality ratings (0/9 caught) or single-order A/B picks (83.3% Slot-A bias) — swap A/B twice and trust agreement.
  3. Scan waveforms with DSP first ("DSP finds when, Neon says what") and disclose speech-masked click limits.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

# Fixed defaults calibrated on clean Kokoro-82M speech in the published exam (results/dsp_baseline_outputs.json)
DEFAULT_CLICK_SCORE_THR = 131.4
DEFAULT_HISS_FLOOR_DBFS = -73.1


def ffprobe_duration_sec(path: pathlib.Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        text=True,
    ).strip()
    return round(float(out), 3)


def _hp(x: np.ndarray, freq: float, sr: int) -> np.ndarray:
    return sosfilt(butter(4, min(freq, sr / 2 * 0.8), "high", fs=sr, output="sos"), x)


def _frames_rms(x: np.ndarray, sr: int, win: float) -> np.ndarray:
    m = max(1, int(win * sr))
    k = len(x) // m
    if k == 0:
        return np.array([1e-10])
    return np.sqrt(np.mean(x[: k * m].reshape(k, m) ** 2, axis=1) + 1e-20)


def _dbv(v: np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(v, 1e-10))


def _merge(spans: list[list[float]], gap: float) -> list[list[float]]:
    out: list[list[float]] = []
    for a, b in sorted(spans):
        if out and a - out[-1][1] <= gap:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def analyze_wav(path: pathlib.Path, click_thr: float = DEFAULT_CLICK_SCORE_THR, hiss_db: float = DEFAULT_HISS_FLOOR_DBFS) -> dict:
    dur = ffprobe_duration_sec(path)
    sr, raw = wavfile.read(str(path))
    x = raw.astype(np.float64) / 32768.0
    mono = x.mean(axis=1) if x.ndim == 2 else x

    # 1. Silence >= 1.0 s below -60 dBFS via ffmpeg
    sil_run = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "info", "-i", str(path), "-af", "silencedetect=noise=-60dB:d=1.0", "-f", "null", "-"],
        capture_output=True, text=True, check=False,
    )
    starts = [float(v) for v in re.findall(r"silence_start: ([\d.]+)", sil_run.stderr)]
    ends = [float(v) for v in re.findall(r"silence_end: ([\d.]+)", sil_run.stderr)]
    silences = [[round(a, 3), round(b, 3)] for a, b in zip(starts, ends) if a > 0.5 and b < dur - 0.5]

    # 2. Hard clipping >= 3 consecutive samples >= 0.999 full scale
    clipped = np.abs(x if x.ndim == 1 else x.max(axis=1)) >= 0.999
    c_idx = np.flatnonzero(clipped)
    clip_spans: list[list[float]] = []
    if len(c_idx):
        for r in np.split(c_idx, np.flatnonzero(np.diff(c_idx) > 1) + 1):
            if len(r) >= 3:
                clip_spans.append([r[0] / sr, (r[-1] + 1) / sr])
    clip_spans = [[round(a, 3), round(b, 3)] for a, b in _merge(clip_spans, 0.25)]

    # 3. Isolated impulse clicks (> click_thr over 1 s neighborhood)
    d = np.abs(np.diff(_hp(mono, 5000.0, sr), 2))
    w = int(1.0 * sr)
    click_hits: list[float] = []
    for s in range(0, len(d), w):
        seg = d[max(0, s - w // 2) : s + w + w // 2]
        med = float(np.median(seg)) + 1e-9
        blk = d[s : s + w]
        for j in np.flatnonzero(blk > 8.0 * med):
            g = s + int(j)
            around = np.concatenate([
                d[max(0, g - int(0.01 * sr)) : max(0, g - int(0.002 * sr))],
                d[g + int(0.002 * sr) : g + int(0.01 * sr)],
            ])
            if len(around) and float(np.percentile(around, 90)) < 4.0 * med:
                if float(blk[j] / med) > click_thr:
                    t = g / sr
                    if not click_hits or t - click_hits[-1] > 0.05:
                        click_hits.append(round(t, 3))

    # 4. Raised high-band hiss (>= 2 s above hiss_db)
    fr_h = _frames_rms(_hp(mono, 4000.0, sr), sr, 0.02)
    win, hop = 100, 25
    ft = np.array([float(_dbv(np.min(fr_h[i : i + win]))) for i in range(0, max(1, len(fr_h) - win + 1), hop)])
    h_spans = [[i * 0.5, i * 0.5 + 2.0] for i in np.flatnonzero(ft > hiss_db)]
    hiss_spans = [[round(a, 2), round(b, 2)] for a, b in _merge(h_spans, 1.0) if b - a >= 2.0]

    # 5. Discrete cue onsets & rapid pulse bursts
    fr_on = _frames_rms(mono, sr, 0.05)
    e_on = _dbv(fr_on)
    thr_on = float(np.median(e_on)) + 15.0
    onsets: list[float] = []
    quiet_since = 1.5
    for i, val in enumerate(e_on):
        if val > thr_on:
            if quiet_since >= 1.5:
                onsets.append(round(i * 0.05, 2))
            quiet_since = 0.0
        else:
            quiet_since += 0.05

    fr_p = _frames_rms(mono, sr, 0.01)
    e_p = _dbv(fr_p)
    p_idx = np.flatnonzero(e_p > float(np.median(e_p)) + 20.0)
    bursts: list[dict] = []
    if len(p_idx):
        runs = np.split(p_idx, np.flatnonzero(np.diff(p_idx) > 4) + 1)
        starts_p = [float(r[0] * 0.01) for r in runs]
        cur = [starts_p[0]]
        grouped: list[list[float]] = []
        for a, b in zip(starts_p, starts_p[1:]):
            if b - a >= 1.25:
                grouped.append(cur)
                cur = [b]
            else:
                cur.append(b)
        grouped.append(cur)
        bursts = [{"burst_index": i + 1, "onset_sec": round(b[0], 2), "pulse_count": len(b)} for i, b in enumerate(grouped)]

    return {
        "file": path.name,
        "exact_duration_sec": dur,
        "thresholds": {"click_score": click_thr, "hiss_floor_dbfs": hiss_db},
        "impulse_click_candidates_sec": click_hits,
        "clipping_spans_sec": clip_spans,
        "silence_spans_sec": silences,
        "hiss_spans_sec": hiss_spans,
        "onset_peaks_sec": onsets,
        "pulse_bursts": bursts,
    }


def build_neon_anchored_prompt(anchors: dict) -> str:
    return (
        f"Inspect {anchors['file']} (exact_duration_sec={anchors['exact_duration_sec']} from ffprobe).\n"
        f"Physical DSP anchors detected: {json.dumps({k: anchors[k] for k in ['impulse_click_candidates_sec', 'clipping_spans_sec', 'silence_spans_sec', 'hiss_spans_sec', 'onset_peaks_sec']})}\n"
        "Listen to the full audio using read_file and verify/name each anchored window without inventing unanchored timestamps."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Cognitive Unload Hybrid Audio QA Quickstart")
    parser.add_argument("--audio", required=True, help="Path to WAV file to scan")
    parser.add_argument("--dsp-only", action="store_true", help="Print DSP + ffprobe anchors without Neon prompt wrapper")
    args = parser.parse_args()

    wav = pathlib.Path(args.audio)
    anchors = analyze_wav(wav)
    if args.dsp_only:
        print(json.dumps(anchors, indent=2))
    else:
        print(json.dumps({"anchors": anchors, "gemini_4_neon_prompt": build_neon_anchored_prompt(anchors)}, indent=2))


if __name__ == "__main__":
    main()
