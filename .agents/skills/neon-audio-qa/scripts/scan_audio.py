#!/usr/bin/env python3
"""Deterministic Audio QA Pre-Scanner for the neon-audio-qa Agent Skill.

Extracts exact ffprobe duration, K-weighted LUFS loudness, spectral centroid,
and physical DSP defect/event anchors (silence, clipping, impulse clicks,
raised high-band hiss, cue onsets, and rapid pulse bursts), then emits
ready-to-use anchored or swapped-order A/B prompts for Gemini 4 Neon.

Supports lossless WAV directly and transparently decodes MP3/M4A/FLAC/MP4/MOV
via ffmpeg into a temporary 48 kHz 16-bit PCM WAV when given non-WAV media.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import tempfile
from typing import Any

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter, sosfilt

# Calibrated defaults from Cognitive Unload blind audio exam (results/dsp_baseline_outputs.json)
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


def _ensure_pcm16_wav(src: pathlib.Path, tmp_dir: pathlib.Path) -> tuple[pathlib.Path, bool]:
    """Return a readable 16-bit PCM WAV path (converting non-WAV/non-PCM media via ffmpeg)."""
    if src.suffix.lower() == ".wav":
        try:
            sr, data = wavfile.read(str(src))
            if data.dtype == np.int16 and sr > 0:
                return src, False
        except Exception:
            pass
    out_wav = tmp_dir / f"{src.stem}_pcm16.wav"
    subprocess.run(
        [
            "ffmpeg", "-nostdin", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(src), "-vn", "-acodec", "pcm_s16le", "-ar", "48000", str(out_wav),
        ],
        check=True,
    )
    return out_wav, True


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


def _lufs(x: np.ndarray, sr: int) -> float | None:
    arr = x if x.ndim == 2 else x[:, None]
    blk, hop = int(0.4 * sr), int(0.1 * sr)
    if len(arr) <= blk:
        return None

    def kw(sig: np.ndarray) -> np.ndarray:
        f0, G, Q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
        K = np.tan(np.pi * f0 / sr)
        Vh = 10 ** (G / 20)
        Vb = Vh ** 0.4996667741545416
        a0 = 1 + K / Q + K * K
        sig = lfilter(
            [(Vh + Vb * K / Q + K * K) / a0, 2 * (K * K - Vh) / a0, (Vh - Vb * K / Q + K * K) / a0],
            [1, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0],
            sig,
        )
        f0, Q = 38.13547087602444, 0.5003270373238773
        K = np.tan(np.pi * f0 / sr)
        a0 = 1 + K / Q + K * K
        return lfilter([1, -2, 1], [1, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0], sig)

    w = np.stack([kw(arr[:, c]) for c in range(arr.shape[1])], axis=1)
    zs = np.array([np.sum(np.mean(w[i : i + blk] ** 2, axis=0)) for i in range(0, len(w) - blk, hop)])
    zs = zs[-0.691 + 10 * np.log10(zs + 1e-20) > -70]
    if not len(zs):
        return None
    rel = -0.691 + 10 * np.log10(np.mean(zs)) - 10
    zs = zs[-0.691 + 10 * np.log10(zs) > rel]
    if not len(zs):
        return None
    return round(float(-0.691 + 10 * np.log10(np.mean(zs))), 2)


def _centroid(mono: np.ndarray, sr: int) -> float:
    spec = np.abs(np.fft.rfft(mono))
    denom = float(np.sum(spec))
    if denom <= 0:
        return 0.0
    freqs = np.fft.rfftfreq(len(mono), 1.0 / sr)
    return round(float(np.sum(freqs * spec) / denom), 1)


def analyze_media(
    path: pathlib.Path,
    click_thr: float = DEFAULT_CLICK_SCORE_THR,
    hiss_db: float = DEFAULT_HISS_FLOOR_DBFS,
) -> dict[str, Any]:
    dur = ffprobe_duration_sec(path)
    with tempfile.TemporaryDirectory(prefix="neon_audio_qa_") as td:
        wav_path, decoded = _ensure_pcm16_wav(path, pathlib.Path(td))
        sr, raw = wavfile.read(str(wav_path))
        x = raw.astype(np.float64) / 32768.0
        mono = x.mean(axis=1) if x.ndim == 2 else x

        # 1. Silence >= 1.0 s below -60 dBFS (excluding 0.5 s head/tail margins)
        sil_run = subprocess.run(
            [
                "ffmpeg", "-nostdin", "-v", "info", "-i", str(wav_path),
                "-af", "silencedetect=noise=-60dB:d=1.0", "-f", "null", "-",
            ],
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

        # 3. Isolated impulse clicks (5 kHz high-pass 2nd diff > click_thr over 1 s neighborhood)
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

        # 4. Raised high-band hiss (>= 2.0 s above hiss_db on 4 kHz minimum-statistics floor)
        fr_h = _frames_rms(_hp(mono, 4000.0, sr), sr, 0.02)
        win, hop = 100, 25
        ft = np.array([
            float(_dbv(np.min(fr_h[i : i + win])))
            for i in range(0, max(1, len(fr_h) - win + 1), hop)
        ])
        h_spans = [[i * 0.5, i * 0.5 + 2.0] for i in np.flatnonzero(ft > hiss_db)]
        hiss_spans = [[round(a, 2), round(b, 2)] for a, b in _merge(h_spans, 1.0) if b - a >= 2.0]

        # 5. Discrete cue onsets (+15 dB above median, 1.5 s hold)
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

        # 6. Rapid pulse bursts (+20 dB above median, 40 ms pulse gap, 1.25 s burst gap)
        fr_p = _frames_rms(mono, sr, 0.01)
        e_p = _dbv(fr_p)
        p_idx = np.flatnonzero(e_p > float(np.median(e_p)) + 20.0)
        bursts: list[dict[str, Any]] = []
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
            bursts = [
                {"burst_index": i + 1, "onset_sec": round(b[0], 2), "pulse_count": len(b)}
                for i, b in enumerate(grouped)
            ]

        return {
            "file": path.name,
            "decoded_via_ffmpeg": decoded,
            "sample_rate_hz": int(sr),
            "channels": 1 if x.ndim == 1 else int(x.shape[1]),
            "exact_duration_sec": dur,
            "loudness_lufs": _lufs(x, sr),
            "spectral_centroid_hz": _centroid(mono, sr),
            "thresholds": {"click_score": click_thr, "hiss_floor_dbfs": hiss_db},
            "impulse_click_candidates_sec": click_hits,
            "clipping_spans_sec": clip_spans,
            "silence_spans_sec": silences,
            "hiss_spans_sec": hiss_spans,
            "onset_peaks_sec": onsets,
            "pulse_bursts": bursts,
        }


def build_voiceover_prompt(anchors: dict[str, Any]) -> str:
    subset = {
        k: anchors[k]
        for k in [
            "impulse_click_candidates_sec",
            "clipping_spans_sec",
            "silence_spans_sec",
            "hiss_spans_sec",
        ]
    }
    return (
        f"Audit {anchors['file']} (exact_duration_sec={anchors['exact_duration_sec']} from ffprobe).\n"
        f"Deterministic DSP candidate windows: {json.dumps(subset)}\n"
        "Listen to the full audio file using your audio input tool. For each DSP candidate window, "
        "confirm whether a real technical defect is audible and classify it "
        "(click_pop | clipping | silence_gap | hiss | false_positive). Also note any semantic speech "
        "errors (garbled syllables, mispronunciations, repeated words) that DSP cannot detect. "
        "Return strict JSON with exact timestamps anchored to the file duration."
    )


def build_timeline_prompt(anchors: dict[str, Any]) -> str:
    return (
        f"Identify every sound cue in {anchors['file']} "
        f"(exact_duration_sec={anchors['exact_duration_sec']} from ffprobe).\n"
        f"DSP onset peaks (sec): {json.dumps(anchors['onset_peaks_sec'])}\n"
        f"DSP rapid pulse bursts: {json.dumps(anchors['pulse_bursts'])}\n"
        "Listen to the full audio file and name the sound at each DSP onset peak without inventing "
        "unanchored timestamps or guessing pulse counts when DSP already measured them. Return strict JSON."
    )


def build_ab_prompts(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    lufs_a, lufs_b = a["loudness_lufs"], b["loudness_lufs"]
    diff = round(abs(lufs_a - lufs_b), 2) if (lufs_a is not None and lufs_b is not None) else None
    warning = None
    if diff is not None and diff > 1.0:
        warning = (
            f"Loudness mismatch ({diff} dB between {a['file']} [{lufs_a} LUFS] and "
            f"{b['file']} [{lufs_b} LUFS]). Loudness-match both clips within 1.0 dB before A/B judging."
        )
    shared = (
        "Compare clip_A and clip_B strictly on mix quality (vocal-to-music balance, vocal EQ warmth/harshness, "
        "and rhythmic/edit continuity). Return ONLY strict JSON: "
        '{"better": "A" | "B" | "tie", "flawed_clip": "A" | "B" | "none", '
        '"flaw_category": "vocal_buried" | "harsh_thin_eq" | "rhythm_or_splice_glitch" | "none" | "other", '
        '"explanation": string}.'
    )
    return {
        "loudness_lufs_diff_db": diff,
        "loudness_warning": warning,
        "pass_1_forward": {
            "clip_A": a["file"],
            "clip_B": b["file"],
            "prompt": f"Pass 1 (fresh isolated context). Attach clip_A={a['file']}, clip_B={b['file']}.\n{shared}",
        },
        "pass_2_reversed": {
            "clip_A": b["file"],
            "clip_B": a["file"],
            "prompt": f"Pass 2 (separate fresh isolated context). Attach clip_A={b['file']}, clip_B={a['file']}.\n{shared}",
        },
        "agreement_rule": (
            "Accept a winner/flaw ONLY if Pass 1 and Pass 2 point to the same underlying file. "
            "If both passes pick slot A, reject as Slot-A positional bias and escalate to human listen."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic DSP + ffprobe pre-scanner for neon-audio-qa")
    parser.add_argument("--audio", required=True, help="Primary audio/video file to scan")
    parser.add_argument("--audio-b", help="Optional second file for --mode ab-pair comparison")
    parser.add_argument(
        "--mode",
        choices=["voiceover", "timeline", "ab-pair"],
        default="voiceover",
        help="Prompt workflow mode (default: voiceover)",
    )
    parser.add_argument("--dsp-only", action="store_true", help="Emit raw JSON measurements without prompt templates")
    parser.add_argument("--click-thr", type=float, default=DEFAULT_CLICK_SCORE_THR, help="Click score threshold")
    parser.add_argument("--hiss-db", type=float, default=DEFAULT_HISS_FLOOR_DBFS, help="Hiss 4 kHz floor dBFS threshold")
    args = parser.parse_args()

    primary = analyze_media(pathlib.Path(args.audio), click_thr=args.click_thr, hiss_db=args.hiss_db)

    if args.mode == "ab-pair":
        if not args.audio_b:
            parser.error("--mode ab-pair requires --audio-b <second_file>")
        secondary = analyze_media(pathlib.Path(args.audio_b), click_thr=args.click_thr, hiss_db=args.hiss_db)
        out: dict[str, Any] = {"file_1": primary, "file_2": secondary}
        if not args.dsp_only:
            out["ab_protocol"] = build_ab_prompts(primary, secondary)
        print(json.dumps(out, indent=2))
        return

    if args.dsp_only:
        print(json.dumps(primary, indent=2))
        return

    prompt = build_timeline_prompt(primary) if args.mode == "timeline" else build_voiceover_prompt(primary)
    print(json.dumps({"anchors": primary, "gemini_4_neon_prompt": prompt}, indent=2))


if __name__ == "__main__":
    main()
