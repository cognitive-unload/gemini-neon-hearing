#!/usr/bin/env python3
"""Deterministic and audited scorer for Round-2 diagnostic ablations (ablation_v2)."""

from __future__ import annotations

import itertools
import json
import pathlib
import statistics
import sys
from typing import Any

BASE_DIR = pathlib.Path("<REPO_ROOT>")
sys.path.insert(0, str(BASE_DIR))

from score_exam import match_r4_optimal, match_r5a_label, sha256_file  # noqa: E402

ABLATION_DIR = BASE_DIR / "ablation_v2"
OUTPUTS_DIR = ABLATION_DIR / "outputs"
UNSEALED_DIR = BASE_DIR / "unsealed"


def load_runs(ablation_key: str, item_stem: str) -> list[tuple[int, dict[str, Any]]]:
    rows: list[tuple[int, dict[str, Any]]] = []
    for run in (1, 2, 3):
        p = OUTPUTS_DIR / ablation_key / item_stem / f"run_{run}.json"
        rec = json.loads(p.read_text(encoding="utf-8"))
        assert rec.get("status") == "SUCCESS" and rec.get("parse_ok") and rec.get("audit_clean"), f"Unclean run: {p}"
        rows.append((run, rec["parsed"]))
    return rows


def score_r5a_ablation(gt: dict[str, Any], ablation_key: str) -> dict[str, Any]:
    gt_file = gt["files"]["r5_01.wav"]
    true_dur = float(gt_file["duration_sec"])
    gt_cues = gt_file["cues"]
    gt_onsets = [float(c["onset_sec"]) for c in gt_cues]

    dur_errs: list[float] = []
    onset_errs: list[float] = []
    ratios: list[float] = []
    detected_events = 0
    strict_hits = 0
    lenient_hits = 0
    run_logs: list[dict[str, Any]] = []

    for run, parsed in load_runs(ablation_key, "r5_01"):
        est_dur = float(parsed["estimated_duration_sec"])
        d_err = abs(est_dur - true_dur) / true_dur * 100.0
        dur_errs.append(d_err)
        cues = parsed.get("cues", [])
        all_lbls = [str(c.get("sound", "")) for c in cues]

        if len(cues) == 6:
            pairs = [(i, i) for i in range(6)]
        elif len(cues) < 6:
            best_p: list[tuple[int, int]] = []
            best_cost = float("inf")
            for gt_combo in itertools.combinations(range(6), len(cues)):
                cost = sum(abs(float(cues[pi]["onset_sec"]) - gt_onsets[gi]) for pi, gi in enumerate(gt_combo))
                if cost < best_cost:
                    best_cost = cost
                    best_p = list(zip(range(len(cues)), gt_combo))
            pairs = best_p
        else:
            best_p = []
            best_cost = float("inf")
            for pred_combo in itertools.combinations(range(len(cues)), 6):
                cost = sum(abs(float(cues[pi]["onset_sec"]) - gt_onsets[gi]) for gi, pi in enumerate(pred_combo))
                if cost < best_cost:
                    best_cost = cost
                    best_p = list(zip(pred_combo, range(6)))
            pairs = best_p

        detected_events += len(pairs)
        cue_rows: list[dict[str, Any]] = []
        run_errs: list[float] = []
        run_ratios: list[float] = []
        for pi, gi in pairs:
            pred_t = float(cues[pi]["onset_sec"])
            true_t = gt_onsets[gi]
            err = abs(pred_t - true_t)
            ratio = pred_t / true_t
            onset_errs.append(err)
            ratios.append(ratio)
            run_errs.append(err)
            run_ratios.append(ratio)
            lbl = str(cues[pi].get("sound", ""))
            s_ok = match_r5a_label(gi, lbl, all_lbls, lenient=False)
            l_ok = match_r5a_label(gi, lbl, all_lbls, lenient=True)
            if s_ok:
                strict_hits += 1
            if l_ok:
                lenient_hits += 1
            cue_rows.append(
                {
                    "gt_idx": gi + 1,
                    "gt_sound": gt_cues[gi]["sound"],
                    "gt_onset_sec": true_t,
                    "pred_sound": lbl,
                    "pred_onset_sec": pred_t,
                    "abs_err_sec": round(err, 3),
                    "ratio_pred_over_true": round(ratio, 3),
                    "strict_label_match": s_ok,
                    "lenient_label_match": l_ok,
                }
            )
        run_logs.append(
            {
                "run": run,
                "est_dur_sec": est_dur,
                "dur_err_pct": round(d_err, 2),
                "n_cues_pred": len(cues),
                "median_onset_err_sec": round(statistics.median(run_errs), 3) if run_errs else None,
                "max_onset_err_sec": round(max(run_errs), 3) if run_errs else None,
                "ratio_min_med_max": [
                    round(min(run_ratios), 2),
                    round(statistics.median(run_ratios), 2),
                    round(max(run_ratios), 2),
                ]
                if run_ratios
                else None,
                "cues": cue_rows,
            }
        )

    return {
        "mean_dur_err_pct": round(statistics.mean(dur_errs), 2),
        "onset_events_detected": f"{detected_events}/18",
        "strict_labeled_recall": f"{strict_hits}/18",
        "strict_labeled_recall_pct": round(strict_hits / 18.0 * 100, 2),
        "lenient_labeled_recall": f"{lenient_hits}/18",
        "lenient_labeled_recall_pct": round(lenient_hits / 18.0 * 100, 2),
        "median_onset_err_sec": round(statistics.median(onset_errs), 4) if onset_errs else None,
        "max_onset_err_sec": round(max(onset_errs), 4) if onset_errs else None,
        "ratio_min_med_max": [
            round(min(ratios), 2),
            round(statistics.median(ratios), 2),
            round(max(ratios), 2),
        ]
        if ratios
        else None,
        "runs": run_logs,
    }


def score_r4_ablation(gt: dict[str, Any], ablation_key: str) -> dict[str, Any]:
    gt_defects = gt["files"]["r4_01.wav"]["defects"]
    runs_data = load_runs(ablation_key, "r4_01")
    out: dict[str, Any] = {}
    for mname, tol in (("tol_5s", 5.0), ("unrestricted", None)):
        errs: list[float] = []
        hits = 0
        s1 = 0
        unm = 0
        by_subtype = {"click_pop": 0, "clipping": 0, "silence_gap": 0, "hiss": 0}
        run_logs: list[dict[str, Any]] = []
        for run, parsed in runs_data:
            preds = parsed.get("defects", [])
            matched, unmatched = match_r4_optimal(gt_defects, preds, tol=tol)
            hits += len(matched)
            unm += len(unmatched)
            for m in matched:
                e = m["abs_err_sec"]
                errs.append(e)
                by_subtype[m["type"]] += 1
                if e <= 1.0:
                    s1 += 1
            run_logs.append(
                {
                    "run": run,
                    "has_defects": parsed.get("has_defects"),
                    "n_pred": len(preds),
                    "matched": matched,
                    "unmatched": [{"type": u.get("type"), "start_sec": u.get("start_sec"), "note": u.get("note")} for u in unmatched],
                }
            )
        out[mname] = {
            "recall": f"{hits}/15",
            "recall_pct": round(hits / 15.0 * 100, 2),
            "strict_1s": f"{s1}/15",
            "strict_1s_pct": round(s1 / 15.0 * 100, 2),
            "click_recall": f"{by_subtype['click_pop']}/6",
            "by_subtype_hits": by_subtype,
            "median_err_sec": round(statistics.median(errs), 4) if errs else None,
            "max_err_sec": round(max(errs), 4) if errs else None,
            "unmatched_r4_01": unm,
            "runs": run_logs,
        }
    return out


def score_r3_single_clip(gt: dict[str, Any]) -> dict[str, Any]:
    pairs = gt["round3_pairs"]
    gt_role: dict[str, dict[str, Any]] = {}
    for pid, g in pairs.items():
        clean_stem = g["clean_file"].replace(".wav", "")
        flawed_stem = g["flawed_file"].replace(".wav", "")
        gt_role[clean_stem] = {"pair": pid, "is_clean": True, "gt_flaw": "none"}
        gt_role[flawed_stem] = {"pair": pid, "is_clean": False, "gt_flaw": g["flaw_category"]}

    per_run_rows: list[dict[str, Any]] = []
    exact_cls = 0
    clean_fp = 0
    flawed_has_flaw = 0
    flawed_exact_cause = 0

    by_stem_run: dict[tuple[str, int], dict[str, Any]] = {}
    for stem in ("r3_p1_x", "r3_p1_y", "r3_p2_x", "r3_p2_y", "r3_p3_x", "r3_p3_y"):
        info = gt_role[stem]
        for run, parsed in load_runs("r3_single_clip", stem):
            hf = bool(parsed.get("has_flaw"))
            fc = str(parsed.get("flaw_category"))
            q = float(parsed["mix_quality_score_1_to_10"])
            expl = str(parsed.get("explanation", ""))
            if info["is_clean"]:
                is_exact = (hf is False) and (fc == "none")
                if hf:
                    clean_fp += 1
            else:
                if hf:
                    flawed_has_flaw += 1
                is_exact = (hf is True) and (fc == info["gt_flaw"])
                if is_exact:
                    flawed_exact_cause += 1
            if is_exact:
                exact_cls += 1
            row = {
                "item": stem,
                "pair": info["pair"],
                "run": run,
                "gt_clean": info["is_clean"],
                "gt_flaw": info["gt_flaw"],
                "has_flaw": hf,
                "flaw_category": fc,
                "score": q,
                "exact_cls": is_exact,
                "explanation": expl,
            }
            per_run_rows.append(row)
            by_stem_run[(stem, run)] = row

    pair_wins = 0
    pair_ties = 0
    pair_losses = 0
    tiebreak_wins = 0
    pair_summaries: list[dict[str, Any]] = []
    for pid, g in pairs.items():
        clean_stem = g["clean_file"].replace(".wav", "")
        flawed_stem = g["flawed_file"].replace(".wav", "")
        c_scores: list[float] = []
        f_scores: list[float] = []
        run_outcomes: list[dict[str, Any]] = []
        for run in (1, 2, 3):
            cr = by_stem_run[(clean_stem, run)]
            fr = by_stem_run[(flawed_stem, run)]
            c_scores.append(cr["score"])
            f_scores.append(fr["score"])
            if cr["score"] > fr["score"]:
                outcome = "win"
                pair_wins += 1
                tb_win = True
            elif cr["score"] == fr["score"]:
                outcome = "tie"
                pair_ties += 1
                # Tie-break: clean predicted has_flaw=False over flawed has_flaw=True
                tb_win = (cr["has_flaw"] is False) and (fr["has_flaw"] is True)
            else:
                outcome = "loss"
                pair_losses += 1
                tb_win = False
            if tb_win:
                tiebreak_wins += 1
            run_outcomes.append(
                {
                    "run": run,
                    "clean_score": cr["score"],
                    "clean_has_flaw": cr["has_flaw"],
                    "clean_cat": cr["flaw_category"],
                    "flawed_score": fr["score"],
                    "flawed_has_flaw": fr["has_flaw"],
                    "flawed_cat": fr["flaw_category"],
                    "outcome": outcome,
                    "tiebreak_win": tb_win,
                }
            )
        pair_summaries.append(
            {
                "pair": pid,
                "flaw_category": g["flaw_category"],
                "mean_clean_score": round(statistics.mean(c_scores), 2),
                "mean_flawed_score": round(statistics.mean(f_scores), 2),
                "runs": run_outcomes,
            }
        )

    return {
        "standalone_exact_cls": f"{exact_cls}/18",
        "standalone_exact_cls_pct": round(exact_cls / 18.0 * 100, 2),
        "clean_false_positives": f"{clean_fp}/9",
        "flawed_detected_rate": f"{flawed_has_flaw}/9",
        "flawed_exact_cause_rate": f"{flawed_exact_cause}/9",
        "implied_pairwise_wins": f"{pair_wins}/9",
        "implied_pairwise_win_pct": round(pair_wins / 9.0 * 100, 2),
        "implied_pairwise_ties": f"{pair_ties}/9",
        "implied_pairwise_losses": f"{pair_losses}/9",
        "tiebroken_pairwise_wins": f"{tiebreak_wins}/9",
        "tiebroken_pairwise_win_pct": round(tiebreak_wins / 9.0 * 100, 2),
        "per_pair": pair_summaries,
        "per_run": per_run_rows,
    }


def main() -> int:
    gt = json.loads((UNSEALED_DIR / "ground_truth.json").read_text(encoding="utf-8"))

    res = {
        "duration_only_r5_01": score_r5a_ablation(gt, "duration_only"),
        "duration_only_r4_01": score_r4_ablation(gt, "duration_only"),
        "neon_high_r5_01": score_r5a_ablation(gt, "neon_high_r5_01"),
        "r3_single_clip": score_r3_single_clip(gt),
    }

    # Verify bundle hashes if present
    for fn in ("ablation_v2_outputs.md", "ablation_v2_outputs.tar.gz"):
        fp = ABLATION_DIR / fn
        if fp.is_file():
            res.setdefault("artifacts", {})[fn] = sha256_file(fp)

    scores_path = ABLATION_DIR / "ablation_v2_scores.json"
    scores_path.write_text(json.dumps(res, indent=2), encoding="utf-8")
    scores_path.chmod(0o600)

    print("=== 1. DURATION-ONLY R5_01 (gemini-4-neon-medium + exact_duration_sec=120.0) ===")
    r5d = res["duration_only_r5_01"]
    print(f"Summary: dur_err={r5d['mean_dur_err_pct']}% med_err={r5d['median_onset_err_sec']}s max_err={r5d['max_onset_err_sec']}s ratios={r5d['ratio_min_med_max']} strict_labels={r5d['strict_labeled_recall']} lenient={r5d['lenient_labeled_recall']}")
    for r in r5d["runs"]:
        print(f"  run{r['run']}: est_dur={r['est_dur_sec']} ({r['dur_err_pct']}%) med={r['median_onset_err_sec']}s ratios={r['ratio_min_med_max']} cues={[(c['pred_onset_sec'], c['abs_err_sec'], c['pred_sound'], c['strict_label_match']) for c in r['cues']]}")

    print("\n=== 2. DURATION-ONLY R4_01 (gemini-4-neon-medium + exact_duration_sec=92.048) ===")
    r4d = res["duration_only_r4_01"]
    for mode in ("tol_5s", "unrestricted"):
        m = r4d[mode]
        print(f"  [{mode}] recall={m['recall']} ({m['recall_pct']}%) <=1s={m['strict_1s']} clicks={m['click_recall']} med={m['median_err_sec']}s max={m['max_err_sec']}s unm={m['unmatched_r4_01']} sub={m['by_subtype_hits']}")
    for r in r4d["unrestricted"]["runs"]:
        print(f"  run{r['run']} matched={[(x['type'], x['pred_start_sec'], x['gt_start_sec'], x['abs_err_sec']) for x in r['matched']]} unmatched={[(x['type'], x['start_sec']) for x in r['unmatched']]}")

    print("\n=== 3. NEON HIGH R5_01 (gemini-4-neon-high unanchored) ===")
    r5h = res["neon_high_r5_01"]
    print(f"Summary: dur_err={r5h['mean_dur_err_pct']}% med_err={r5h['median_onset_err_sec']}s max_err={r5h['max_onset_err_sec']}s ratios={r5h['ratio_min_med_max']} strict_labels={r5h['strict_labeled_recall']} lenient={r5h['lenient_labeled_recall']}")
    for r in r5h["runs"]:
        print(f"  run{r['run']}: est_dur={r['est_dur_sec']} ({r['dur_err_pct']}%) med={r['median_onset_err_sec']}s ratios={r['ratio_min_med_max']} cues={[(c['pred_onset_sec'], c['abs_err_sec'], c['pred_sound'], c['strict_label_match']) for c in r['cues']]}")

    print("\n=== 4. R3 SINGLE-CLIP ISOLATED (gemini-4-neon-medium, 18 runs) ===")
    r3s = res["r3_single_clip"]
    print(f"Summary: exact_cls={r3s['standalone_exact_cls']} ({r3s['standalone_exact_cls_pct']}%) clean_FP={r3s['clean_false_positives']} flawed_det={r3s['flawed_detected_rate']} flawed_cause={r3s['flawed_exact_cause_rate']}")
    print(f"Pairwise implied: wins={r3s['implied_pairwise_wins']} ({r3s['implied_pairwise_win_pct']}%) ties={r3s['implied_pairwise_ties']} losses={r3s['implied_pairwise_losses']} | tiebroken_wins={r3s['tiebroken_pairwise_wins']} ({r3s['tiebroken_pairwise_win_pct']}%)")
    for p in r3s["per_pair"]:
        print(f"  {p['pair']} ({p['flaw_category']}): mean_clean={p['mean_clean_score']} vs mean_flawed={p['mean_flawed_score']} | outcomes={[(x['run'], x['clean_score'], x['flawed_score'], x['outcome'], x['tiebreak_win']) for x in p['runs']]}")
    for row in r3s["per_run"]:
        print(f"    {row['item']} r{row['run']} (GT {'clean' if row['gt_clean'] else row['gt_flaw']}): has={row['has_flaw']} cat={row['flaw_category']} score={row['score']} | {row['explanation'][:100]}")

    print(f"\nWritten {scores_path} sha256={sha256_file(scores_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
