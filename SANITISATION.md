# Sanitisation Log

This companion repository was audited before tagging `v1.0.0` and re-audited for public release `v1.1.0` under `cognitive-unload/gemini-neon-hearing`:

1. **Host Filesystem Paths & Internal Workflow References Scrubbed:**
   - Replaced workstation/VM workspace paths in `harness/run_blind_exam.py`, `harness/run_ablation_v2.py`, `harness/run_r3_solo_rubric.py`, `harness/score_exam.py`, `harness/score_ablation_v2.py`, `results/scores_v1.json`, and `results/R3_SOLO_RUBRIC_REPORT.md` with portable relative paths (`REPO_ROOT`) or placeholders (`<REPO_ROOT>`, `<SCRATCH_BLIND_DIR>`, `<AGENT_BRAIN_DIR>`, and CLI binary name `agy`).
   - Removed internal production tracker URLs, workspace identifiers, and personal names from `requirements.lock`, `harness/EXAM_SPEC_V1.md`, `harness/score_exam.py`, `results/VALIDATION_REPORT_V2.md`, and the `private_audio` metadata comment line in `exam/ground_truth.json`. *(Because that 1 metadata comment line in `exam/ground_truth.json` was scrubbed for public release, its public SHA-256 in `TESTED_HASHES.json` differs from the internal pre-registration seal hash `11c25408...` cited in `results/VALIDATION_REPORT_V2.md`; every ground-truth label, timestamp, coin-flip assignment, all 17 WAV files, `harness/src/dsp.py` `a8d62850...`, and all benchmark scores remain bit-for-bit unchanged.)*
   - `.agents/skills/neon-audio-qa/` contains strictly portable scripts and prompts with zero host paths or credentials.
2. **Zero Secrets or Credentials:**
   - No API keys, OAuth tokens, SSH keys, IP addresses, or email addresses exist in any tracked file or git commit.
3. **Zero Private Media:**
   - `exam/wavs/` contains strictly 17 synthetic WAVs (`Kokoro-82M` Apache-2.0 voices + `CC0-1.0` `numpy` synth) verified against `TESTED_HASHES.json` and `exam/exam_manifest_public.json`.
