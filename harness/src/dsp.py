"""Plain DSP baseline + Round 6 anchors (EXAM_SPEC_V1.md).

usage: <python with numpy+scipy> -I dsp.py BLIND_DIR OUT_DIR CALIB_DIR
CALIB_DIR holds clean speech that is not part of the exam. The click and hiss
thresholds are set from it (1.5x the worst clean click score; worst clean
2 s minimum noise floor + 6 dB) before any exam file is read.
Reads only the WAV files. Never reads ground truth. Thresholds are fixed and
general (listed in THRESHOLDS); none was tuned per file.
Silence uses ffmpeg silencedetect; everything else is numpy/scipy.
"""
import json, re, subprocess, sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

BLIND, OUT, CALIB = sys.argv[1], sys.argv[2], sys.argv[3]
THRESHOLDS = {
    "silence": "ffmpeg silencedetect noise=-60dB d=1.0",
    "clipping": ">= 3 consecutive samples at >= 0.999 full scale; spans merged within 0.25 s",
    "click": "5 kHz highpass, 2nd difference; score = sample / median of its 1 s neighbourhood; isolated (90th pct of the 2-10 ms around it < 4x median); score above the calibrated threshold; merged within 0.05 s",
    "hiss": "minimum statistics: 4 kHz highpass, quietest 20 ms frame in each 2 s window (hop 0.5 s); floor above the calibrated dBFS level; merged within 1 s; spans >= 2 s",
    "onsets": "50 ms RMS envelope; rise above (median + 15 dB); new onset only after 1.5 s below that level",
    "pulses": "10 ms RMS envelope above (median + 20 dB); pulses split by gaps >= 40 ms; bursts split by gaps >= 1.0 s",
}

def load(fn):
    sr, x = wavfile.read(f"{BLIND}/{fn}")
    x = x.astype(np.float64) / 32768.0
    mono = x.mean(axis=1) if x.ndim == 2 else x
    return sr, x, mono

def hp(x, f, sr):
    return sosfilt(butter(4, f, "high", fs=sr, output="sos"), x)

def frames_rms(x, sr, win):
    m = max(1, int(win * sr)); k = len(x) // m
    return np.sqrt(np.mean(x[:k * m].reshape(k, m) ** 2, axis=1) + 1e-20), m

def dbv(v):
    return 20 * np.log10(np.maximum(v, 1e-10))

def merge(spans, gap):
    out = []
    for a, b in sorted(spans):
        if out and a - out[-1][1] <= gap:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out

def silence_spans(fn):
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "info", "-i", f"{BLIND}/{fn}", "-af", "silencedetect=noise=-60dB:d=1.0", "-f", "null", "-"],
                       capture_output=True, text=True)
    st = [float(v) for v in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    en = [float(v) for v in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return [[round(a, 3), round(b, 3)] for a, b in zip(st, en)]

def clipping_spans(x, sr):
    a = np.abs(x if x.ndim == 1 else x.max(axis=1)) >= 0.999
    spans, i, n = [], 0, len(a)
    idx = np.flatnonzero(a)
    if not len(idx):
        return []
    runs = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
    for r in runs:
        if len(r) >= 3:
            spans.append([r[0] / sr, (r[-1] + 1) / sr])
    return [[round(a, 3), round(b, 3)] for a, b in merge(spans, 0.25)]

def click_scores(mono, sr):
    d = np.abs(np.diff(hp(mono, min(5000, sr / 2 * 0.8), sr), 2))
    w = int(1.0 * sr)
    out = []
    for s in range(0, len(d), w):
        seg = d[max(0, s - w // 2):s + w + w // 2]
        med = np.median(seg) + 1e-9
        blk = d[s:s + w]
        for j in np.flatnonzero(blk > 8 * med):
            g = s + j
            around = np.concatenate([d[max(0, g - int(0.01 * sr)):max(0, g - int(0.002 * sr))], d[g + int(0.002 * sr):g + int(0.01 * sr)]])
            if len(around) and np.percentile(around, 90) < 4 * med:
                out.append((g / sr, float(blk[j] / med)))
    return out

CLICK_THR = None
def click_candidates(mono, sr):
    hits = sorted(t for t, sc in click_scores(mono, sr) if sc > CLICK_THR)
    out = []
    for t in hits:
        if not out or t - out[-1] > 0.05:
            out.append(t)
    return [round(t, 3) for t in out]

def floor_track(mono, sr):
    """Minimum-statistics noise floor: quietest 20 ms frame (4 kHz highpass) in each 2 s window, hop 0.5 s, in dBFS."""
    h = hp(mono, 4000, sr)
    fr, m = frames_rms(h, sr, 0.02)
    win, hop = 100, 25
    return np.array([dbv(np.min(fr[i:i + win])) for i in range(0, max(1, len(fr) - win + 1), hop)])

HISS_DB = None
def hiss_spans(mono, sr):
    ft = floor_track(mono, sr)
    spans = [[i * 0.5, i * 0.5 + 2.0] for i in np.flatnonzero(ft > HISS_DB)]
    return [[round(a, 2), round(b, 2)] for a, b in merge(spans, 1.0) if b - a >= 2.0]

def onsets(mono, sr, rise_db=15.0, hold=1.5):
    fr, m = frames_rms(mono, sr, 0.05)
    e = dbv(fr)
    thr = np.median(e) + rise_db
    out, quiet_since = [], hold
    for i, v in enumerate(e):
        t = i * 0.05
        if v > thr:
            if quiet_since >= hold:
                out.append(round(t, 2))
            quiet_since = 0
        else:
            quiet_since += 0.05
    return out

def events(mono, sr):
    fr, m = frames_rms(mono, sr, 0.05)
    e = dbv(fr); thr = np.median(e) + 12
    spans = [[i * 0.05, (i + 1) * 0.05] for i in np.flatnonzero(e > thr)]
    return [[round(a, 2), round(b, 2)] for a, b in merge(spans, 0.6)]

def pulses(mono, sr):
    fr, m = frames_rms(mono, sr, 0.01)
    e = dbv(fr); on = e > np.median(e) + 20
    idx = np.flatnonzero(on)
    if not len(idx):
        return []
    runs = np.split(idx, np.flatnonzero(np.diff(idx) > 4) + 1)          # >= 40 ms gap splits pulses
    starts = [r[0] * 0.01 for r in runs]
    bursts, cur = [], [starts[0]]
    for a, b in zip(starts, starts[1:]):
        if b - a >= 1.0 + 0.25:   # the gap between pulse starts includes the pulse itself
            bursts.append(cur); cur = [b]
        else:
            cur.append(b)
    bursts.append(cur)
    return bursts

def lufs(x, sr):
    from scipy.signal import lfilter
    x = x if x.ndim == 2 else x[:, None]
    def kw(sig):
        f0 = 1681.974450955533; G = 3.999843853973347; Q = 0.7071752369554196
        K = np.tan(np.pi * f0 / sr); Vh = 10 ** (G / 20); Vb = Vh ** 0.4996667741545416; a0 = 1 + K / Q + K * K
        sig = lfilter([(Vh + Vb * K / Q + K * K) / a0, 2 * (K * K - Vh) / a0, (Vh - Vb * K / Q + K * K) / a0], [1, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0], sig)
        f0 = 38.13547087602444; Q = 0.5003270373238773; K = np.tan(np.pi * f0 / sr)
        return lfilter([1, -2, 1], [1, 2 * (K * K - 1) / (1 + K / Q + K * K), (1 - K / Q + K * K) / (1 + K / Q + K * K)], sig)
    w = np.stack([kw(x[:, c]) for c in range(x.shape[1])], axis=1)
    blk, hop = int(0.4 * sr), int(0.1 * sr)
    zs = np.array([np.sum(np.mean(w[i:i + blk] ** 2, axis=0)) for i in range(0, len(w) - blk, hop)])
    zs = zs[-0.691 + 10 * np.log10(zs + 1e-20) > -70]
    rel = -0.691 + 10 * np.log10(np.mean(zs)) - 10
    zs = zs[-0.691 + 10 * np.log10(zs) > rel]
    return round(float(-0.691 + 10 * np.log10(np.mean(zs))), 2)

def centroid(mono, sr):
    s = np.abs(np.fft.rfft(mono)); f = np.fft.rfftfreq(len(mono), 1 / sr)
    return round(float(np.sum(f * s) / np.sum(s)), 1)

import os
cal_click, cal_hiss = [], []
for f in sorted(os.listdir(CALIB)):
    sr_c, xc = wavfile.read(f"{CALIB}/{f}"); xc = xc.astype(np.float64) / 32768.0
    cal_click += [sc for t, sc in click_scores(xc, sr_c)]
    cal_hiss.append(float(np.max(floor_track(xc, sr_c))))
CLICK_THR = 1.5 * max(cal_click + [8.0])
HISS_DB = max(cal_hiss) + 6.0
THRESHOLDS["calibrated"] = {"click_score_threshold": round(CLICK_THR, 1), "hiss_floor_dbfs": round(HISS_DB, 1),
                            "calibration_files": sorted(os.listdir(CALIB))}

NA = "N/A (DSP blind)"
res = {"_about": {"contestant": "dsp", "thresholds": THRESHOLDS, "note": "Semantic fields are N/A: signal meters cannot name sounds, judge voices or pick a better mix."}}
anchors = {}

for fn in ["r1_01.wav", "r1_02.wav", "r1_03.wav"]:
    sr, x, mono = load(fn)
    res[fn] = {"speech_present": NA, "speech_transcript": None,
               "events_in_order": [{"label": "unlabelled energy event", "approx_start_sec": a, "approx_end_sec": b} for a, b in events(mono, sr)],
               "scene_summary": NA}

for fn in ["r2_01.wav", "r2_02.wav", "r2_03.wav", "r2_04.wav"]:
    sr, x, mono = load(fn)
    found = []
    for a, b in clipping_spans(x, sr): found.append(("clipping", a))
    for a, b in silence_spans(fn):
        if a > 0.5 and b < len(mono) / sr - 0.5: found.append(("silence_gap", a))
    for t in click_candidates(mono, sr): found.append(("click_pop", t))
    res[fn] = {"has_defect": bool(found), "defect_type": "other" if found else "none",
               "approx_time_sec": found[0][1] if found else None,
               "explanation": ("signal faults: " + ", ".join(f"{k} at {t} s" for k, t in found)) if found else
                              "no clipping, dead air or isolated clicks found; splice, garble and overlap are " + NA}

for p in (1, 2, 3):
    m = {}
    for s in ("x", "y"):
        sr, x, mono = load(f"r3_p{p}_{s}.wav")
        m[s] = {"lufs": lufs(x, sr), "spectral_centroid_hz": centroid(mono, sr), "clipping_spans": clipping_spans(x, sr)}
    for order, (A, B) in {"fwd": ("x", "y"), "rev": ("y", "x")}.items():
        res[f"r3_p{p}_{order}"] = {"better": NA, "flawed_clip": NA, "flaw_category": NA,
                                   "explanation": f"measurements only: clip_A {m[A]}, clip_B {m[B]}"}

for fn in ["r4_01.wav", "r4_02.wav"]:
    sr, x, mono = load(fn)
    d = []
    for t in click_candidates(mono, sr): d.append({"type": "click_pop", "start_sec": t, "end_sec": round(t + 0.005, 3), "confidence": "high", "note": "isolated impulse"})
    for a, b in hiss_spans(mono, sr): d.append({"type": "hiss", "start_sec": a, "end_sec": b, "confidence": "medium", "note": "high-band noise floor raised"})
    for a, b in clipping_spans(x, sr): d.append({"type": "clipping", "start_sec": a, "end_sec": b, "confidence": "high", "note": "samples at full scale"})
    for a, b in silence_spans(fn):
        if a > 0.5 and b < len(mono) / sr - 0.5: d.append({"type": "silence_gap", "start_sec": a, "end_sec": b, "confidence": "high", "note": "below -60 dBFS for over 1 s"})
    d.sort(key=lambda r: r["start_sec"])
    res[fn] = {"has_defects": bool(d), "defects": d}

sr, x, mono = load("r5_01.wav")
res["r5_01.wav"] = {"estimated_duration_sec": round(len(mono) / sr, 3), "cues": [{"sound": "unlabelled onset", "onset_sec": t} for t in onsets(mono, sr)]}
sr, x, mono = load("r5_02.wav")
res["r5_02.wav"] = {"bursts": [{"burst_index": i + 1, "onset_sec": round(b[0], 2), "pulse_count": len(b), "description": "tone burst (unlabelled)"} for i, b in enumerate(pulses(mono, sr))]}

for fn in ["r4_01.wav", "r4_02.wav", "r5_01.wav"]:
    sr, x, mono = load(fn)
    fr, m = frames_rms(mono, sr, 2.0)
    anchors[fn] = {"exact_duration_sec": round(len(mono) / sr, 3),
                   "rms_dbfs_2s_bins": [round(float(v), 1) for v in dbv(fr)],
                   "silence_spans": silence_spans(fn),
                   "impulse_click_candidates_sec": click_candidates(mono, sr),
                   "clipping_spans_sec": clipping_spans(x, sr),
                   "raised_noise_floor_spans_sec": hiss_spans(mono, sr),
                   "onset_peaks_sec": onsets(mono, sr)}
anchors["_about"] = {"note": "Deterministic signal measurements only. No human labels, no ground truth. 'rms_dbfs_2s_bins' is plain RMS in dBFS per 2 s bin (the spec name rms_lufs_2s_bins was not used because these are not LUFS).", "thresholds": THRESHOLDS}

json.dump(res, open(f"{OUT}/dsp_baseline_outputs.json", "w"), indent=1)
json.dump(anchors, open(f"{OUT}/dsp_anchors.json", "w"), indent=1)
print("ok")
