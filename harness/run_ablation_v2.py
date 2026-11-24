#!/usr/bin/env python3
"""Isolated Round-2 diagnostic micro-ablations (27 runs, $0 spend) for Gemini 4 Neon audio validation."""

from __future__ import annotations

import argparse
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

BASE_DIR = pathlib.Path("<REPO_ROOT>")
sys.path.insert(0, str(BASE_DIR))

from run_blind_exam import (  # noqa: E402
    AGY_BIN,
    DEFAULT_EPH_ROOT,
    PROMPT_R4_BASE,
    PROMPT_R5A_BASE,
    SHARED_PREFIX,
    extract_json_payload,
    parse_stream_json,
    evaluate_audit,
    sha256_file,
    verify_blind_pack,
)

ABLATION_DIR = BASE_DIR / "ablation_v2"

DURATION_ANCHOR_SUFFIX = (
    "\n\nDURATION_ANCHOR (exact total file duration from ffprobe—contains NO event timestamps "
    "or defect candidates; use this exact total duration as your clock scale while listening):\n"
    "{anchor_json}"
)

PROMPT_R3_SINGLE = (
    f"{SHARED_PREFIX}\n"
    '{"has_flaw": boolean, "flaw_category": "none" | "vocal_buried" | "harsh_thin_eq" | '
    '"rhythm_or_splice_glitch" | "other", "mix_quality_score_1_to_10": integer, "explanation": string}\n\n'
    "You are QA-checking a single podcast/video audio clip on its own. Determine whether this clip is "
    "clean and well-balanced or has a clear mix/timbre/editing flaw (\"vocal_buried\", \"harsh_thin_eq\", "
    "\"rhythm_or_splice_glitch\", or \"other\"). Rate overall mix/audio quality from 1 (severe flaw) to "
    "10 (clean master). If clean, set \"has_flaw\": false and \"flaw_category\": \"none\".\n\n"
    "Use read_file on {clip_path}."
)


def build_ablation_jobs(runs: int = 3) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    # 1. duration_only (gemini-4-neon-medium, 6 runs)
    for fname, exact_dur, pk in (
        ("r5_01.wav", 120.0, "R5A_DUR"),
        ("r4_01.wav", 92.048, "R4_DUR"),
    ):
        for run_idx in range(1, runs + 1):
            jobs.append(
                {
                    "ablation_key": "duration_only",
                    "agy_model": "gemini-4-neon-medium",
                    "item_id": fname,
                    "source_file": fname,
                    "prompt_key": pk,
                    "exact_duration_sec": exact_dur,
                    "run_idx": run_idx,
                }
            )

    # 2. neon_high_r5_01 (gemini-4-neon-high unanchored, 3 runs)
    for run_idx in range(1, runs + 1):
        jobs.append(
            {
                "ablation_key": "neon_high_r5_01",
                "agy_model": "gemini-4-neon-high",
                "item_id": "r5_01.wav",
                "source_file": "r5_01.wav",
                "prompt_key": "R5A_RAW",
                "run_idx": run_idx,
            }
        )

    # 3. r3_single_clip (gemini-4-neon-medium, 18 runs)
    for fname in (
        "r3_p1_x.wav",
        "r3_p1_y.wav",
        "r3_p2_x.wav",
        "r3_p2_y.wav",
        "r3_p3_x.wav",
        "r3_p3_y.wav",
    ):
        for run_idx in range(1, runs + 1):
            jobs.append(
                {
                    "ablation_key": "r3_single_clip",
                    "agy_model": "gemini-4-neon-medium",
                    "item_id": fname,
                    "source_file": fname,
                    "prompt_key": "R3_SINGLE",
                    "run_idx": run_idx,
                }
            )
    return jobs


def format_ablation_prompt(job: dict[str, Any], clip_path: pathlib.Path) -> str:
    pk = job["prompt_key"]
    if pk == "R5A_RAW":
        return PROMPT_R5A_BASE.replace("{clip_path}", str(clip_path))
    if pk in ("R5A_DUR", "R4_DUR"):
        base = PROMPT_R5A_BASE if pk == "R5A_DUR" else PROMPT_R4_BASE
        base = base.replace("{clip_path}", str(clip_path))
        anchor_json = json.dumps({"exact_duration_sec": job["exact_duration_sec"]})
        return base + DURATION_ANCHOR_SUFFIX.replace("{anchor_json}", anchor_json)
    if pk == "R3_SINGLE":
        return PROMPT_R3_SINGLE.replace("{clip_path}", str(clip_path))
    raise ValueError(f"Unknown prompt_key: {pk}")


def run_attempt(
    job: dict[str, Any],
    blind_dir: pathlib.Path,
    eph_root: pathlib.Path,
    timeout_sec: int,
) -> dict[str, Any]:
    eph_dir = eph_root / uuid.uuid4().hex[:12]
    eph_dir.mkdir(parents=True, exist_ok=False)
    os.chmod(eph_dir, 0o700)

    try:
        clip_path = eph_dir / "clip.wav"
        shutil.copyfile(blind_dir / job["source_file"], clip_path)
        expected_paths = [clip_path]
        prompt = format_ablation_prompt(job, clip_path)

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
            stdout_text = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr_text = f"TimeoutExpired after {timeout_sec + 30}s"

        init_model, tools_called, agy_payload = parse_stream_json(stdout_text)
        audit_clean, audit_notes = evaluate_audit(
            job["agy_model"], init_model, tools_called, expected_paths, eph_dir
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
                parse_ok, parsed_json, parse_err = extract_json_payload(raw_response)
            else:
                parse_err = f"agy status={status}"
        elif returncode == 0:
            parse_err = "missing result event in stream-json"
        else:
            parse_err = f"rc={returncode} stderr={stderr_text.strip()[:400]}"

        return {
            "ablation_key": job["ablation_key"],
            "agy_model": job["agy_model"],
            "item_id": job["item_id"],
            "source_files": [job["source_file"]],
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


def run_one(
    job: dict[str, Any],
    blind_dir: pathlib.Path,
    out_dir: pathlib.Path,
    eph_root: pathlib.Path,
    timeout_sec: int,
    max_attempts: int = 3,
) -> tuple[str, bool, str]:
    safe_item = job["item_id"].replace(".wav", "")
    out_path = out_dir / job["ablation_key"] / safe_item / f"run_{job['run_idx']}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    label = f"{job['ablation_key']}/{safe_item}/run_{job['run_idx']}"

    if out_path.is_file():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            if (
                existing.get("status") == "SUCCESS"
                and existing.get("parse_ok") is True
                and existing.get("audit_clean") is True
            ):
                return label, True, "skipped (already done)"
        except Exception:
            pass

    last_record: dict[str, Any] | None = None
    for attempt in range(1, max_attempts + 1):
        rec = run_attempt(job, blind_dir, eph_root, timeout_sec)
        rec["attempts"] = attempt
        last_record = rec
        if rec["status"] == "SUCCESS" and rec["parse_ok"] and rec["audit_clean"]:
            break
        if attempt < max_attempts:
            time.sleep(3)

    assert last_record is not None
    out_path.write_text(json.dumps(last_record, indent=2), encoding="utf-8")
    out_path.chmod(0o600)

    ok = bool(
        last_record["status"] == "SUCCESS"
        and last_record["parse_ok"]
        and last_record["audit_clean"]
    )
    info = (
        f"ok ({last_record['wall_seconds']}s, attempts={last_record['attempts']})"
        if ok
        else (
            f"FAIL (status={last_record['status']} parse_ok={last_record['parse_ok']} "
            f"audit_clean={last_record['audit_clean']} err={last_record['parse_error']} "
            f"audit={last_record['audit_notes']})"
        )
    )
    return label, ok, info


def bundle_ablation_outputs(out_dir: pathlib.Path, ablation_dir: pathlib.Path) -> tuple[str, str, str, dict[str, Any]]:
    files = sorted(p for p in out_dir.rglob("*.json") if p.is_file())
    if not files:
        raise RuntimeError(f"No JSON outputs found under {out_dir}")

    tar_path = ablation_dir / "ablation_v2_outputs.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tf:
        for p in files:
            tf.add(p, arcname=str(p.relative_to(out_dir)))
    tar_path.chmod(0o600)
    tar_sha = sha256_file(tar_path)

    structured: dict[str, dict[str, dict[str, Any]]] = {}
    stats: dict[str, dict[str, int]] = {}
    overall = {"total": 0, "success": 0, "parse_ok": 0, "audit_clean": 0, "clean_pass": 0, "failures": 0}

    for p in files:
        rec = json.loads(p.read_text(encoding="utf-8"))
        akey = rec["ablation_key"]
        item_id = rec["item_id"]
        run_key = str(rec["run_idx"])
        structured.setdefault(akey, {}).setdefault(item_id, {})[run_key] = {
            "agy_model": rec.get("agy_model"),
            "status": rec.get("status"),
            "parse_ok": rec.get("parse_ok"),
            "audit_clean": rec.get("audit_clean"),
            "init_model": rec.get("init_model"),
            "tools_called_names": [t.get("tool_name") for t in (rec.get("tools_called") or [])],
            "attempts": rec.get("attempts"),
            "duration_seconds": rec.get("duration_seconds"),
            "usage": rec.get("usage"),
            "conversation_id": rec.get("conversation_id"),
            "parsed": rec.get("parsed"),
            "raw_response": rec.get("raw_response"),
        }

        s = stats.setdefault(
            akey, {"total": 0, "success": 0, "parse_ok": 0, "audit_clean": 0, "clean_pass": 0, "failures": 0}
        )
        is_success = rec.get("status") == "SUCCESS"
        is_parse = rec.get("parse_ok") is True
        is_audit = rec.get("audit_clean") is True
        is_clean = is_success and is_parse and is_audit

        for bucket in (s, overall):
            bucket["total"] += 1
            if is_success:
                bucket["success"] += 1
            if is_parse:
                bucket["parse_ok"] += 1
            if is_audit:
                bucket["audit_clean"] += 1
            if is_clean:
                bucket["clean_pass"] += 1
            else:
                bucket["failures"] += 1

    inner_json_str = json.dumps(structured, indent=2, sort_keys=True)
    inner_json_sha = hashlib.sha256(inner_json_str.encode("utf-8")).hexdigest()

    md_path = ablation_dir / "ablation_v2_outputs.md"
    lines = [
        "# Round-2 Diagnostic Ablation v2 — Raw Isolated Outputs (27 Runs)",
        "",
        f"- **Tarball (`ablation_v2_outputs.tar.gz`) SHA-256:** `{tar_sha}`",
        f"- **Inner JSON SHA-256:** `{inner_json_sha}`",
        "",
        "## Run Summary",
        "",
        "| Ablation Key | Total | SUCCESS | parse_ok | audit_clean | Clean Pass | Failures |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for akey in sorted(stats):
        s = stats[akey]
        lines.append(
            f"| `{akey}` | {s['total']} | {s['success']} | {s['parse_ok']} | "
            f"{s['audit_clean']} | {s['clean_pass']} | {s['failures']} |"
        )
    lines.append(
        f"| **TOTAL** | **{overall['total']}** | **{overall['success']}** | **{overall['parse_ok']}** | "
        f"**{overall['audit_clean']}** | **{overall['clean_pass']}** | **{overall['failures']}** |"
    )
    lines.extend(["", "```json", inner_json_str, "```", ""])

    md_text = "\n".join(lines).replace("\x00", "")
    md_path.write_text(md_text, encoding="utf-8")
    md_path.chmod(0o600)
    md_sha = sha256_file(md_path)
    return tar_sha, md_sha, inner_json_sha, {"overall": overall, "by_ablation": stats}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run Round-2 diagnostic ablations via agy 1.5.12.")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--timeout-sec", type=int, default=180)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--bundle", action="store_true", help="Only bundle existing ablation_v2/outputs/.")
    args = ap.parse_args(argv)

    blind_dir = BASE_DIR / "blind"
    pack_dir = BASE_DIR / "pack"
    out_dir = ABLATION_DIR / "outputs"
    eph_root = DEFAULT_EPH_ROOT

    ABLATION_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(ABLATION_DIR, 0o700)

    if not args.bundle:
        files = verify_blind_pack(blind_dir, pack_dir)
        print(f"VERIFY OK: {len(files)}/17 WAV files match exam_manifest_public.json")

        eph_root.mkdir(parents=True, exist_ok=True)
        os.chmod(eph_root, 0o700)
        out_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(out_dir, 0o700)

        jobs = build_ablation_jobs(runs=args.runs)
        print(f"Starting {len(jobs)} isolated ablation runs (workers={args.workers})...")
        failures = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [
                pool.submit(run_one, job, blind_dir, out_dir, eph_root, args.timeout_sec)
                for job in jobs
            ]
            for fut in concurrent.futures.as_completed(futures):
                label, ok, info = fut.result()
                if not ok:
                    failures += 1
                print(f"  [{'OK' if ok else 'ERR'}] {label}: {info}", flush=True)

        remaining_eph = list(eph_root.iterdir()) if eph_root.exists() else []
        print(f"Finished {len(jobs)} ablation jobs with {failures} failures; eph_remaining={len(remaining_eph)}")
        if remaining_eph:
            raise RuntimeError(f"Ephemeral dir not empty: {remaining_eph}")
        if failures:
            return 1

    tar_sha, md_sha, inner_sha, summary = bundle_ablation_outputs(out_dir, ABLATION_DIR)
    print(f"TARBALL: {ABLATION_DIR / 'ablation_v2_outputs.tar.gz'} sha256={tar_sha}")
    print(f"MARKDOWN: {ABLATION_DIR / 'ablation_v2_outputs.md'} sha256={md_sha}")
    print(f"INNER_JSON_SHA256: {inner_sha}")
    print(f"SUMMARY: {json.dumps(summary)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
