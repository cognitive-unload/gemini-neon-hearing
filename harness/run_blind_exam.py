#!/usr/bin/env python3
"""Isolated blind audio exam runner for Gemini 4 Neon / Argon validation (EXAM_SPEC_V1.md)."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile
import time
import uuid
from typing import Any

DEFAULT_ROOT = pathlib.Path("<REPO_ROOT>")
DEFAULT_EPH_ROOT = pathlib.Path("<SCRATCH_BLIND_DIR>")
AGY_BIN = "agy"

SHARED_PREFIX = (
    "Listen ONLY to the attached audio file(s) using your native audio reader. "
    "Do NOT run shell commands, ffmpeg, python, or external speech-to-text tools. "
    "Do NOT inspect any other files. Return ONLY valid JSON matching this exact "
    "schema—no markdown fences or extra commentary:"
)

PROMPT_R1 = (
    f"{SHARED_PREFIX}\n"
    '{"speech_present": boolean, "speech_transcript": string or null, '
    '"events_in_order": [{"label": string, "approx_start_sec": number, '
    '"approx_end_sec": number}], "scene_summary": string}\n\n'
    "Describe every distinct sound event you hear in chronological order. "
    'Set "speech_present" to true ONLY if actual human spoken words are audible; '
    'otherwise set it to false and "speech_transcript" to null.\n\n'
    "Use read_file on {clip_path}."
)

PROMPT_R2 = (
    f"{SHARED_PREFIX}\n"
    '{"has_defect": boolean, "defect_type": "none" | "cut_word_splice" | '
    '"garbled_vocal" | "overlap_or_reverb_jump" | "other", '
    '"approx_time_sec": number or null, "explanation": string}\n\n'
    "You are QA-checking a creator voiceover take. Determine whether the recording is clean "
    'or contains a clear editing/vocal/recording flaw ("cut_word_splice", "garbled_vocal", '
    '"overlap_or_reverb_jump", or "other"). If clean, set "has_defect": false, '
    '"defect_type": "none", and "approx_time_sec": null.\n\n'
    "Use read_file on {clip_path}."
)

PROMPT_R3 = (
    'Listen ONLY to the two attached audio files ("clip_A" and "clip_B") using your native audio reader. '
    "Do NOT run shell commands, ffmpeg, python, or external speech-to-text tools. "
    "Do NOT inspect any other files. Return ONLY valid JSON matching this exact "
    "schema—no markdown fences or extra commentary:\n"
    '{"better": "A" | "B" | "tie", "flawed_clip": "A" | "B" | "none", '
    '"flaw_category": "vocal_buried" | "harsh_thin_eq" | "rhythm_or_splice_glitch" | "other", '
    '"explanation": string}\n\n'
    "Compare clip_A and clip_B as a podcast/video mix QA reviewer. Pick which version is cleaner "
    'and better balanced ("A", "B", or "tie"), identify which clip has the flaw, and classify '
    "the main flaw in the losing clip.\n\n"
    "Use read_file on BOTH {clip_a_path} (as clip_A) and {clip_b_path} (as clip_B)."
)

PROMPT_R4_BASE = (
    f"{SHARED_PREFIX}\n"
    '{"has_defects": boolean, "defects": [{"type": "click_pop" | "hiss" | '
    '"clipping" | "silence_gap" | "other", "start_sec": number, "end_sec": number, '
    '"confidence": "low" | "medium" | "high", "note": string}]}\n\n'
    "Inspect this voiceover recording carefully from start to end for technical audio defects: "
    "sharp clicks/pops, background hiss segments, digital clipping/distortion, or unnatural "
    "dead-air silence gaps. Report every defect you hear with timestamps in seconds. "
    'If the recording has no defects, return {"has_defects": false, "defects": []}.\n\n'
    "Use read_file on {clip_path}."
)

PROMPT_R5A_BASE = (
    f"{SHARED_PREFIX}\n"
    '{"estimated_duration_sec": number, "cues": [{"sound": string, "onset_sec": number}]}\n\n'
    "Estimate the total clip duration in seconds and list every distinct sound cue or event "
    "in chronological order with its exact onset timestamp in seconds.\n\n"
    "Use read_file on {clip_path}."
)

PROMPT_R5B = (
    f"{SHARED_PREFIX}\n"
    '{"bursts": [{"burst_index": integer, "onset_sec": number, "pulse_count": integer, '
    '"description": string}]}\n\n'
    "Count the exact number of individual tone/alert pulses inside each distinct burst separated "
    "by pauses. List each burst in order (1-indexed) with its onset time in seconds, exact integer "
    "pulse count, and brief description.\n\n"
    "Use read_file on {clip_path}."
)

DSP_PRECHECK_SUFFIX = (
    "\n\nDSP_PRECHECK (deterministic ffmpeg/Python signal measurements for the file above—"
    "contains NO human labels; use these timestamps and candidates as your exact clock anchor "
    "while you verify by listening):\n{dsp_json}"
)


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_blind_pack(blind_dir: pathlib.Path, pack_dir: pathlib.Path) -> list[dict[str, Any]]:
    manifest_path = pack_dir / "exam_manifest_public.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.get("files", [])
    if len(files) != 17:
        raise ValueError(f"Expected 17 files in manifest, got {len(files)}")

    errors: list[str] = []
    for entry in files:
        fname = entry["filename"]
        expected = entry["sha256"]
        fpath = blind_dir / fname
        if not fpath.is_file():
            errors.append(f"MISSING: {fpath}")
            continue
        actual = sha256_file(fpath)
        if actual != expected:
            errors.append(f"HASH MISMATCH {fname}: expected={expected} actual={actual}")

    if errors:
        raise RuntimeError("\n".join(errors))
    return files


def extract_json_payload(raw_text: str) -> tuple[bool, Any, str | None]:
    text = raw_text.strip()
    if not text:
        return False, None, "empty response"

    candidates = [text]
    fenced = re.findall(r"```(?:json)?\s*\r?\n?(.*?)\r?\n?```", text, flags=re.DOTALL | re.IGNORECASE)
    candidates.extend(fenced)

    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidates.append(text[first_brace : last_brace + 1])

    for cand in candidates:
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict):
                return True, obj, None
        except json.JSONDecodeError:
            continue
    return False, None, "failed to parse JSON object from response"


def build_tasks(include_round6: bool, models: list[str], runs: int) -> list[dict[str, Any]]:
    base_items: list[dict[str, Any]] = [
        {"item_id": "r1_01.wav", "round": "R1", "kind": "single", "files": ["r1_01.wav"], "prompt_key": "R1"},
        {"item_id": "r1_02.wav", "round": "R1", "kind": "single", "files": ["r1_02.wav"], "prompt_key": "R1"},
        {"item_id": "r1_03.wav", "round": "R1", "kind": "single", "files": ["r1_03.wav"], "prompt_key": "R1"},
        {"item_id": "r2_01.wav", "round": "R2", "kind": "single", "files": ["r2_01.wav"], "prompt_key": "R2"},
        {"item_id": "r2_02.wav", "round": "R2", "kind": "single", "files": ["r2_02.wav"], "prompt_key": "R2"},
        {"item_id": "r2_03.wav", "round": "R2", "kind": "single", "files": ["r2_03.wav"], "prompt_key": "R2"},
        {"item_id": "r2_04.wav", "round": "R2", "kind": "single", "files": ["r2_04.wav"], "prompt_key": "R2"},
        {"item_id": "r3_p1_fwd", "round": "R3", "kind": "pair", "files": ["r3_p1_x.wav", "r3_p1_y.wav"], "prompt_key": "R3"},
        {"item_id": "r3_p1_rev", "round": "R3", "kind": "pair", "files": ["r3_p1_y.wav", "r3_p1_x.wav"], "prompt_key": "R3"},
        {"item_id": "r3_p2_fwd", "round": "R3", "kind": "pair", "files": ["r3_p2_x.wav", "r3_p2_y.wav"], "prompt_key": "R3"},
        {"item_id": "r3_p2_rev", "round": "R3", "kind": "pair", "files": ["r3_p2_y.wav", "r3_p2_x.wav"], "prompt_key": "R3"},
        {"item_id": "r3_p3_fwd", "round": "R3", "kind": "pair", "files": ["r3_p3_x.wav", "r3_p3_y.wav"], "prompt_key": "R3"},
        {"item_id": "r3_p3_rev", "round": "R3", "kind": "pair", "files": ["r3_p3_y.wav", "r3_p3_x.wav"], "prompt_key": "R3"},
        {"item_id": "r4_01.wav", "round": "R4", "kind": "single", "files": ["r4_01.wav"], "prompt_key": "R4"},
        {"item_id": "r4_02.wav", "round": "R4", "kind": "single", "files": ["r4_02.wav"], "prompt_key": "R4"},
        {"item_id": "r5_01.wav", "round": "R5a", "kind": "single", "files": ["r5_01.wav"], "prompt_key": "R5A"},
        {"item_id": "r5_02.wav", "round": "R5b", "kind": "single", "files": ["r5_02.wav"], "prompt_key": "R5B"},
    ]

    r6_items: list[dict[str, Any]] = [
        {"item_id": "r6_r4_01", "round": "R6", "kind": "single_dsp", "files": ["r4_01.wav"], "prompt_key": "R4_DSP"},
        {"item_id": "r6_r4_02", "round": "R6", "kind": "single_dsp", "files": ["r4_02.wav"], "prompt_key": "R4_DSP"},
        {"item_id": "r6_r5_01", "round": "R6", "kind": "single_dsp", "files": ["r5_01.wav"], "prompt_key": "R5A_DSP"},
    ]

    jobs: list[dict[str, Any]] = []
    for run_idx in range(1, runs + 1):
        for item in base_items:
            for model in models:
                jobs.append({"model_key": model, "agy_model": model, "run_idx": run_idx, **item})
        if include_round6:
            for item in r6_items:
                jobs.append({
                    "model_key": "hybrid_dsp_neon",
                    "agy_model": "gemini-4-neon-medium",
                    "run_idx": run_idx,
                    **item,
                })
    return jobs


def format_prompt(
    task: dict[str, Any],
    eph_dir: pathlib.Path,
    dsp_anchors: dict[str, Any] | None,
) -> str:
    pk = task["prompt_key"]
    if pk == "R1":
        return PROMPT_R1.replace("{clip_path}", str(eph_dir / "clip.wav"))
    if pk == "R2":
        return PROMPT_R2.replace("{clip_path}", str(eph_dir / "clip.wav"))
    if pk == "R3":
        return (
            PROMPT_R3.replace("{clip_a_path}", str(eph_dir / "clip_A.wav"))
            .replace("{clip_b_path}", str(eph_dir / "clip_B.wav"))
        )
    if pk == "R4":
        return PROMPT_R4_BASE.replace("{clip_path}", str(eph_dir / "clip.wav"))
    if pk == "R5A":
        return PROMPT_R5A_BASE.replace("{clip_path}", str(eph_dir / "clip.wav"))
    if pk == "R5B":
        return PROMPT_R5B.replace("{clip_path}", str(eph_dir / "clip.wav"))
    if pk in ("R4_DSP", "R5A_DSP"):
        assert dsp_anchors is not None
        src_name = task["files"][0]
        if src_name not in dsp_anchors:
            raise KeyError(f"Missing {src_name} in dsp_anchors.json")
        base = PROMPT_R4_BASE if pk == "R4_DSP" else PROMPT_R5A_BASE
        base = base.replace("{clip_path}", str(eph_dir / "clip.wav"))
        dsp_json = json.dumps(dsp_anchors[src_name], indent=2)
        return base + DSP_PRECHECK_SUFFIX.replace("{dsp_json}", dsp_json)
    raise ValueError(f"Unknown prompt_key: {pk}")


def parse_stream_json(stdout_text: str) -> tuple[str | None, list[dict[str, Any]], dict[str, Any]]:
    init_model: str | None = None
    tool_steps: dict[Any, dict[str, Any]] = {}
    fallback_seq = 0
    result_payload: dict[str, Any] = {}

    for line in stdout_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        etype = ev.get("event")
        if etype == "init":
            init_obj = ev.get("init") or {}
            init_model = init_obj.get("model")
        elif etype == "step_update":
            su = ev.get("step_update") or {}
            if su.get("step_type") == "tool":
                step_idx = su.get("step_index")
                key = step_idx if step_idx is not None else f"_anon_{fallback_seq}"
                if step_idx is None:
                    fallback_seq += 1
                tool_info = su.get("tool_info") or {}
                tool_name = su.get("tool_name") or tool_info.get("name")
                params = tool_info.get("parameters") or {}
                state = su.get("state")
                prev = tool_steps.get(key)
                if prev is None or state == "DONE" or (params and not prev.get("parameters")):
                    tool_steps[key] = {
                        "step_index": step_idx,
                        "tool_name": tool_name,
                        "parameters": params,
                        "state": state,
                    }
        elif etype == "result":
            result_payload = ev.get("result") or {}

    tools_called = [
        {
            "step_index": v["step_index"],
            "tool_name": v["tool_name"],
            "parameters": v["parameters"],
        }
        for v in tool_steps.values()
    ]
    return init_model, tools_called, result_payload


def evaluate_audit(
    expected_agy_model: str,
    init_model: str | None,
    tools_called: list[dict[str, Any]],
    expected_paths: list[pathlib.Path],
    eph_dir: pathlib.Path,
) -> tuple[bool, list[str]]:
    notes: list[str] = []
    if init_model != expected_agy_model:
        notes.append(f"init_model mismatch: expected={expected_agy_model!r} got={init_model!r}")

    eph_resolved = eph_dir.resolve()
    expected_resolved = {p.resolve() for p in expected_paths}
    read_resolved: set[pathlib.Path] = set()

    if not tools_called:
        notes.append("no tool calls observed")

    for tc in tools_called:
        tname = tc.get("tool_name")
        if tname != "read_file":
            notes.append(f"disallowed tool called: {tname!r}")
            continue
        params = tc.get("parameters") or {}
        raw_path = params.get("Path") or params.get("path")
        if not raw_path or not isinstance(raw_path, str):
            notes.append(f"read_file missing Path parameter: {params!r}")
            continue
        p_res = pathlib.Path(raw_path).resolve()
        if not p_res.is_relative_to(eph_resolved):
            notes.append(f"read_file escaped ephemeral dir: {raw_path!r}")
            continue
        if p_res not in expected_resolved:
            notes.append(f"read_file targeted unexpected file: {raw_path!r}")
            continue
        read_resolved.add(p_res)

    missing = sorted(str(p.name) for p in (expected_resolved - read_resolved))
    if missing:
        notes.append(f"expected blind file(s) not read: {missing}")

    return len(notes) == 0, notes


def run_attempt(
    job: dict[str, Any],
    blind_dir: pathlib.Path,
    eph_root: pathlib.Path,
    dsp_anchors: dict[str, Any] | None,
    timeout_sec: int,
) -> dict[str, Any]:
    eph_dir = eph_root / uuid.uuid4().hex[:12]
    eph_dir.mkdir(parents=True, exist_ok=False)
    os.chmod(eph_dir, 0o700)

    try:
        expected_paths: list[pathlib.Path] = []
        if job["kind"] == "pair":
            pa = eph_dir / "clip_A.wav"
            pb = eph_dir / "clip_B.wav"
            shutil.copyfile(blind_dir / job["files"][0], pa)
            shutil.copyfile(blind_dir / job["files"][1], pb)
            expected_paths = [pa, pb]
        else:
            pc = eph_dir / "clip.wav"
            shutil.copyfile(blind_dir / job["files"][0], pc)
            expected_paths = [pc]

        prompt = format_prompt(job, eph_dir, dsp_anchors)
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
            "model_key": job["model_key"],
            "agy_model": job["agy_model"],
            "round": job["round"],
            "item_id": job["item_id"],
            "source_files": job["files"],
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
    dsp_anchors: dict[str, Any] | None,
    timeout_sec: int,
    max_attempts: int = 3,
) -> tuple[str, bool, str]:
    safe_item = job["item_id"].replace(".wav", "")
    out_path = out_dir / job["model_key"] / safe_item / f"run_{job['run_idx']}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    label = f"{job['model_key']}/{safe_item}/run_{job['run_idx']}"

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
        rec = run_attempt(job, blind_dir, eph_root, dsp_anchors, timeout_sec)
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
    if ok:
        info = f"ok ({last_record['wall_seconds']}s, attempts={last_record['attempts']})"
    else:
        info = (
            f"FAIL (status={last_record['status']} parse_ok={last_record['parse_ok']} "
            f"audit_clean={last_record['audit_clean']} err={last_record['parse_error']} "
            f"audit={last_record['audit_notes']})"
        )
    return label, ok, info


def bundle_outputs(out_dir: pathlib.Path, bundle_path: pathlib.Path) -> tuple[str, str, str, dict[str, Any]]:
    if not out_dir.is_dir():
        raise FileNotFoundError(f"Missing outputs dir: {out_dir}")
    files = sorted(p for p in out_dir.rglob("*.json") if p.is_file())
    if not files:
        raise RuntimeError(f"No JSON outputs found under {out_dir}")

    with tarfile.open(bundle_path, "w:gz") as tf:
        for p in files:
            arcname = str(p.relative_to(out_dir))
            tf.add(p, arcname=arcname)
    bundle_path.chmod(0o600)
    tar_sha = sha256_file(bundle_path)

    structured: dict[str, dict[str, dict[str, Any]]] = {}
    stats: dict[str, dict[str, int]] = {}
    overall = {"total": 0, "success": 0, "parse_ok": 0, "audit_clean": 0, "clean_pass": 0, "failures": 0}

    for p in files:
        rec = json.loads(p.read_text(encoding="utf-8"))
        mkey = rec["model_key"]
        item_id = rec["item_id"]
        run_key = str(rec["run_idx"])
        structured.setdefault(mkey, {}).setdefault(item_id, {})[run_key] = {
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
            mkey, {"total": 0, "success": 0, "parse_ok": 0, "audit_clean": 0, "clean_pass": 0, "failures": 0}
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

    md_path = bundle_path.parent / "blind_outputs_neon_argon_v1.md"
    lines = [
        "# Blind Exam Pack v1 — Neon & Argon Outputs",
        "",
        f"- **Tarball (`blind_outputs_neon_argon_v1.tar.gz`) SHA-256:** `{tar_sha}`",
        f"- **Inner JSON SHA-256:** `{inner_json_sha}`",
        "",
        "## Run Summary",
        "",
        "| Model Key | Total | SUCCESS | parse_ok | audit_clean | Clean Pass | Failures |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for mkey in sorted(stats):
        s = stats[mkey]
        lines.append(
            f"| `{mkey}` | {s['total']} | {s['success']} | {s['parse_ok']} | "
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

    return tar_sha, md_sha, inner_json_sha, {"overall": overall, "by_model": stats}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run isolated blind audio exam via agy 1.5.12.")
    ap.add_argument("--blind-dir", type=pathlib.Path, default=DEFAULT_ROOT / "blind")
    ap.add_argument("--pack-dir", type=pathlib.Path, default=DEFAULT_ROOT / "pack")
    ap.add_argument("--out-dir", type=pathlib.Path, default=DEFAULT_ROOT / "outputs")
    ap.add_argument("--eph-root", type=pathlib.Path, default=DEFAULT_EPH_ROOT)
    ap.add_argument("--verify-only", action="store_true", help="Verify all 17 blind WAVs against manifest and exit.")
    ap.add_argument("--models", default="gemini-4-neon-medium,gemini-4-argon-medium")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--timeout-sec", type=int, default=180)
    ap.add_argument("--limit", type=int, default=0, help="If > 0, run only first N jobs.")
    ap.add_argument("--include-round6", action="store_true", help="Also run Round 6 DSP-anchored Neon.")
    ap.add_argument("--bundle", action="store_true", help="Create tarball + md bundle and print SHA-256 digests.")
    ap.add_argument("--bundle-path", type=pathlib.Path, default=None)
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.bundle and not args.verify_only:
        bpath = args.bundle_path or (args.out_dir.parent / "blind_outputs_neon_argon_v1.tar.gz")
        tar_sha, md_sha, inner_sha, summary = bundle_outputs(args.out_dir, bpath)
        print(f"TARBALL: {bpath} sha256={tar_sha}")
        print(f"MARKDOWN: {bpath.parent / 'blind_outputs_neon_argon_v1.md'} sha256={md_sha}")
        print(f"INNER_JSON_SHA256: {inner_sha}")
        print(f"SUMMARY: {json.dumps(summary)}")
        return 0

    try:
        files = verify_blind_pack(args.blind_dir, args.pack_dir)
    except Exception as exc:
        print(f"VERIFY FAILED:\n{exc}", file=sys.stderr)
        return 1

    print(f"VERIFY OK: {len(files)}/17 WAV files match exam_manifest_public.json")
    if args.verify_only:
        return 0

    dsp_anchors: dict[str, Any] | None = None
    if args.include_round6:
        anchors_path = args.pack_dir / "dsp_anchors.json"
        if not anchors_path.is_file():
            print(f"Missing dsp_anchors.json at {anchors_path}", file=sys.stderr)
            return 1
        dsp_anchors = json.loads(anchors_path.read_text(encoding="utf-8"))

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    jobs = build_tasks(args.include_round6, models, args.runs)
    if args.limit > 0:
        jobs = jobs[: args.limit]

    args.eph_root.mkdir(parents=True, exist_ok=True)
    os.chmod(args.eph_root, 0o700)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(args.out_dir, 0o700)

    print(f"Starting {len(jobs)} isolated agy runs (workers={args.workers})...")
    failures = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(
                run_one,
                job,
                args.blind_dir,
                args.out_dir,
                args.eph_root,
                dsp_anchors,
                args.timeout_sec,
            )
            for job in jobs
        ]
        for fut in concurrent.futures.as_completed(futures):
            label, ok, info = fut.result()
            if not ok:
                failures += 1
            print(f"  [{'OK' if ok else 'ERR'}] {label}: {info}", flush=True)

    print(f"Finished {len(jobs)} jobs with {failures} failures.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
