#!/usr/bin/env python3
"""18-run isolated blind ablation: R3 solo clips with an explicit 'what clean means' QA rubric.

Direct apples-to-apples test vs ablation_v2/r3_single_clip (which caught 0/9 flawed clips
using the short category-only prompt). Changes ONLY the prompt to define 'clean' and list
explicit acoustic checks (balance, EQ warmth/tinniness, rhythmic/splice continuity, and
speech-presence check to avoid instrumental VO hallucinations).
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tarfile
import time
import uuid
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
HARNESS_DIR = REPO_ROOT / "harness"
EXAM_DIR = REPO_ROOT / "exam"
BLIND_DIR = EXAM_DIR / "wavs"
GT_PATH = EXAM_DIR / "ground_truth.json"
OUT_ROOT = pathlib.Path(os.environ.get("R3_RUBRIC_OUT_DIR", str(REPO_ROOT / "results" / "r3_solo_rubric_run")))

sys.path.insert(0, str(HARNESS_DIR))
import run_blind_exam as rbe  # noqa: E402

AGY_BIN = os.environ.get("AGY_BIN", "agy")
TARGET_MODEL = "gemini-4-neon-medium"

PROMPT_R3_SOLO_RUBRIC = (
    f"{rbe.SHARED_PREFIX}\n"
    '{"speech_present": boolean, "has_flaw": boolean, '
    '"flaw_category": "none" | "vocal_buried" | "harsh_thin_eq" | '
    '"rhythm_or_splice_glitch" | "other", '
    '"mix_quality_score_1_to_10": integer, "explanation": string}\n\n'
    "You are QA-checking a single podcast/video audio clip on its own before publishing. "
    "First decide whether actual human speech is present (\"speech_present\": true or false; "
    "some clips are pure instrumental music with no voiceover). Then check the clip against "
    "this explicit definition of a CLEAN audio master:\n"
    "1. Vocal-to-music balance (\"vocal_buried\"): ONLY if speech and music play together, "
    "the voice must sit clearly in front of the music and stay effortless to understand at "
    "normal listening volume. Flag \"vocal_buried\" if the background music competes with, "
    "masks, or overpowers the narrator. Never flag \"vocal_buried\" on an instrumental clip "
    "with no speech.\n"
    "2. Vocal tone & EQ (\"harsh_thin_eq\"): ONLY if speech is present, a clean voice sounds "
    "natural and balanced with normal low-end warmth/chest body and smooth upper-mids. Flag "
    "\"harsh_thin_eq\" if the voice sounds thin, tinny, hollowed-out, telephone/megaphone-like, "
    "stripped of bass warmth, or sharply harsh/piercing in the upper-mid frequencies.\n"
    "3. Rhythm, tempo & edit continuity (\"rhythm_or_splice_glitch\"): Music beds and phrasing "
    "must keep a steady beat, consistent bar timing, and smooth transitions from start to end. "
    "Flag \"rhythm_or_splice_glitch\" if you hear an off-beat cut, skipped/rushed beat, "
    "abrupt loop seam, hiccup, or jarring splice glitch in the music or edit.\n"
    "4. Other clear defect (\"other\"): Flag \"other\" only for another unmistakable technical "
    "defect (clipping, hiss, clicks, dead-air dropouts).\n\n"
    "Decision rule:\n"
    "- A clip is CLEAN (\"has_flaw\": false, \"flaw_category\": \"none\", score 8-10) ONLY if "
    "every applicable check above passes cleanly. Do NOT invent flaws on genuinely clean clips.\n"
    "- If ANY concrete flaw above is clearly audible, set \"has_flaw\": true, pick its exact "
    "\"flaw_category\", rate mix quality 1-6 (1 = severe, 6 = borderline), and explain what "
    "you heard (including approximate time in seconds if localized).\n\n"
    "Use read_file on {clip_path}."
)

R3_FILES = (
    "r3_p1_x.wav",
    "r3_p1_y.wav",
    "r3_p2_x.wav",
    "r3_p2_y.wav",
    "r3_p3_x.wav",
    "r3_p3_y.wav",
)


def run_attempt(job: dict[str, Any], eph_root: pathlib.Path, timeout_sec: int) -> dict[str, Any]:
    eph_dir = eph_root / uuid.uuid4().hex[:12]
    eph_dir.mkdir(parents=True, exist_ok=False)
    os.chmod(eph_dir, 0o700)
    try:
        pc = eph_dir / "clip.wav"
        shutil.copyfile(BLIND_DIR / job["source_file"], pc)
        prompt = PROMPT_R3_SOLO_RUBRIC.replace("{clip_path}", str(pc))
        cmd = [
            AGY_BIN,
            "--model",
            job["agy_model"],
            "--output-format",
            "stream-json",
            "--dangerously-skip-permissions",
            "--disable-slash-commands",
            "--add-dir",
            str(eph_dir),
            "--print-timeout",
            f"{timeout_sec}s",
            f"-p={prompt}",
        ]
        t0 = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(eph_dir),
                capture_output=True,
                text=True,
                timeout=timeout_sec + 30,
            )
            wall_sec = round(time.monotonic() - t0, 3)
            returncode = proc.returncode
            stdout_text = proc.stdout
            stderr_text = proc.stderr
        except subprocess.TimeoutExpired as exc:
            wall_sec = round(time.monotonic() - t0, 3)
            returncode = -1
            stdout_text = (
                exc.stdout.decode("utf-8", errors="replace")
                if isinstance(exc.stdout, bytes)
                else (exc.stdout or "")
            )
            stderr_text = f"TimeoutExpired after {timeout_sec + 30}s"

        init_model, tools_called, agy_payload = rbe.parse_stream_json(stdout_text)
        audit_clean, audit_notes = rbe.evaluate_audit(
            job["agy_model"], init_model, tools_called, [pc], eph_dir
        )

        raw_response = ""
        status = "ERROR"
        parse_ok = False
        parsed_json: Any = None
        parse_err: str | None = None

        if returncode == 0 and agy_payload:
            status = agy_payload.get("status", "UNKNOWN")
            raw_response = agy_payload.get("response", "")
            if status == "SUCCESS":
                parse_ok, parsed_json, parse_err = rbe.extract_json_payload(raw_response)
            else:
                parse_err = f"agy status={status}"
        elif returncode == 0:
            parse_err = "missing result event in stream-json"
        else:
            parse_err = f"rc={returncode} stderr={stderr_text.strip()[:400]}"

        return {
            "ablation_key": "r3_solo_rubric",
            "agy_model": job["agy_model"],
            "item_id": job["source_file"],
            "source_file": job["source_file"],
            "run_idx": job["run_idx"],
            "status": status,
            "parse_ok": parse_ok,
            "parse_error": parse_err,
            "audit_clean": audit_clean,
            "audit_notes": audit_notes,
            "init_model": init_model,
            "tools_called": tools_called,
            "parsed": parsed_json,
            "raw_response": raw_response,
            "conversation_id": agy_payload.get("conversation_id"),
            "duration_seconds": agy_payload.get("duration_seconds"),
            "wall_seconds": wall_sec,
            "usage": agy_payload.get("usage"),
            "returncode": returncode,
        }
    finally:
        shutil.rmtree(eph_dir, ignore_errors=True)


def run_one(job: dict[str, Any], out_dir: pathlib.Path, eph_root: pathlib.Path, timeout_sec: int = 180) -> tuple[str, bool, str]:
    safe_item = job["source_file"].replace(".wav", "")
    out_path = out_dir / job["agy_model"] / safe_item / f"run_{job['run_idx']}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    label = f"{job['agy_model']}/{safe_item}/run_{job['run_idx']}"

    if out_path.is_file():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            if existing.get("status") == "SUCCESS" and existing.get("parse_ok") and existing.get("audit_clean"):
                return label, True, "skipped (already done)"
        except Exception:
            pass

    last_rec: dict[str, Any] | None = None
    for attempt in range(1, 4):
        rec = run_attempt(job, eph_root, timeout_sec)
        rec["attempts"] = attempt
        last_rec = rec
        if rec["status"] == "SUCCESS" and rec["parse_ok"] and rec["audit_clean"]:
            break
        if attempt < 3:
            time.sleep(3)

    assert last_rec is not None
    out_path.write_text(json.dumps(last_rec, indent=2), encoding="utf-8")
    out_path.chmod(0o600)
    ok = bool(last_rec["status"] == "SUCCESS" and last_rec["parse_ok"] and last_rec["audit_clean"])
    info = f"ok ({last_rec['wall_seconds']}s)" if ok else f"FAIL ({last_rec['parse_error']} / {last_rec['audit_notes']})"
    return label, ok, info


def score_results(out_dir: pathlib.Path, model: str) -> dict[str, Any]:
    gt = json.loads(GT_PATH.read_text(encoding="utf-8"))["round3_pairs"]
    file_gt: dict[str, dict[str, Any]] = {}
    for pair_id, info in gt.items():
        file_gt[info["clean_file"]] = {"pair": pair_id, "is_clean": True, "flaw_category": "none"}
        file_gt[info["flawed_file"]] = {"pair": pair_id, "is_clean": False, "flaw_category": info["flaw_category"]}

    rows = []
    by_pair: dict[str, dict[str, Any]] = {}
    for fname in R3_FILES:
        safe = fname.replace(".wav", "")
        meta = file_gt[fname]
        pair = meta["pair"]
        by_pair.setdefault(
            pair,
            {
                "flaw_category": gt[pair]["flaw_category"],
                "clean_file": gt[pair]["clean_file"],
                "flawed_file": gt[pair]["flawed_file"],
                "clean_scores": [],
                "flawed_scores": [],
                "clean_fp": 0,
                "flawed_detected": 0,
                "flawed_exact_cat": 0,
            },
        )
        for r in (1, 2, 3):
            rec = json.loads((out_dir / model / safe / f"run_{r}.json").read_text(encoding="utf-8"))
            p = rec["parsed"]
            has_flaw = bool(p.get("has_flaw"))
            cat = p.get("flaw_category")
            score = p.get("mix_quality_score_1_to_10")
            sp = p.get("speech_present")
            expl = (p.get("explanation") or "").strip()
            exact_ok = (not has_flaw and cat == "none") if meta["is_clean"] else (has_flaw and cat == meta["flaw_category"])
            rows.append({
                "file": fname,
                "pair": pair,
                "gt_clean": meta["is_clean"],
                "gt_cat": meta["flaw_category"],
                "run": r,
                "speech_present": sp,
                "has_flaw": has_flaw,
                "pred_cat": cat,
                "score": score,
                "exact_ok": exact_ok,
                "explanation": expl,
            })
            bp = by_pair[pair]
            if meta["is_clean"]:
                bp["clean_scores"].append(score)
                if has_flaw:
                    bp["clean_fp"] += 1
            else:
                bp["flawed_scores"].append(score)
                if has_flaw:
                    bp["flawed_detected"] += 1
                if has_flaw and cat == meta["flaw_category"]:
                    bp["flawed_exact_cat"] += 1

    # Compute implied pairwise wins/ties/losses by run index (same metric as ablation_v2)
    tot_w = tot_t = tot_l = 0
    for pair, bp in by_pair.items():
        w = t = l = 0
        for cs, fs in zip(bp["clean_scores"], bp["flawed_scores"]):
            if cs > fs:
                w += 1
            elif cs == fs:
                t += 1
            else:
                l += 1
        bp["implied_wtl"] = [w, t, l]
        tot_w += w
        tot_t += t
        tot_l += l

    summary = {
        "model": model,
        "total_runs": len(rows),
        "flawed_detected": sum(bp["flawed_detected"] for bp in by_pair.values()),
        "flawed_exact_cat": sum(bp["flawed_exact_cat"] for bp in by_pair.values()),
        "flawed_total": 9,
        "clean_correct": 9 - sum(bp["clean_fp"] for bp in by_pair.values()),
        "clean_fp": sum(bp["clean_fp"] for bp in by_pair.values()),
        "clean_total": 9,
        "exact_classification": sum(1 for r in rows if r["exact_ok"]),
        "implied_pairwise_wtl": [tot_w, tot_t, tot_l],
        "by_pair": by_pair,
        "rows": rows,
    }
    return summary


def main() -> int:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    out_dir = OUT_ROOT / "outputs"
    eph_root = OUT_ROOT / "eph"
    out_dir.mkdir(parents=True, exist_ok=True)
    eph_root.mkdir(parents=True, exist_ok=True)
    os.chmod(eph_root, 0o700)
    os.chmod(out_dir, 0o700)

    rbe.verify_blind_pack(BLIND_DIR, EXAM_DIR)
    print("VERIFY OK: 17/17 WAV hashes match exam_manifest_public.json", flush=True)

    jobs = [
        {"agy_model": TARGET_MODEL, "source_file": f, "run_idx": r}
        for r in (1, 2, 3)
        for f in R3_FILES
    ]
    failures = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futs = [pool.submit(run_one, j, out_dir, eph_root, 180) for j in jobs]
        for fut in concurrent.futures.as_completed(futs):
            label, ok, info = fut.result()
            if not ok:
                failures += 1
            print(f"  [{'OK' if ok else 'ERR'}] {label}: {info}", flush=True)

    rem = list(eph_root.iterdir())
    if rem:
        raise RuntimeError(f"Ephemeral dir not empty: {rem}")
    if failures:
        return 1

    summary = score_results(out_dir, TARGET_MODEL)
    (OUT_ROOT / "r3_solo_rubric_scores.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Tarball raw outputs
    tar_path = OUT_ROOT / "r3_solo_rubric_outputs.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tf:
        for p in sorted(out_dir.rglob("*.json")):
            tf.add(p, arcname=str(p.relative_to(out_dir)))
    tar_sha = rbe.sha256_file(tar_path)
    print(f"TARBALL: {tar_path} sha256={tar_sha}", flush=True)
    print("=== SUMMARY ===", flush=True)
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2), flush=True)
    print("=== ROWS ===", flush=True)
    for row in summary["rows"]:
        tag = "CLEAN" if row["gt_clean"] else row["gt_cat"]
        print(
            f"  {row['file']} r{row['run']} (GT={tag:23s}) | sp={row['speech_present']} "
            f"flaw={row['has_flaw']} cat={row['pred_cat']:23s} score={row['score']}/10 | {row['explanation'][:130]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
