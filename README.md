# Timing Attacks (Semester Project)

Flask web lab for demonstrating a timing side-channel during naive HMAC tag comparison and comparing it against a constant-time comparison.

Implements the required parts from the assignment:

- HMAC-SHA256 tag, naive byte-by-byte early-exit compare (vulnerable), constant-time compare (`hmac.compare_digest`).
- Noise profiles: none (baseline), jitter (random delay), cpu load (background threads).
- Attack simulator: adaptive byte recovery with statistical decision (t-test or KS-test) and `alpha` threshold.
- Exports: `runs/<run_id>/result.json`, `runs/<run_id>/results.csv`, plus plots.

## Quick start (Windows)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open:

- http://127.0.0.1:5000/

Artifacts are written under `runs/<run_id>/`.

## Notes

- The verify API returns the same response text regardless of correctness (no content oracle). The attack uses only time measurements.
- For faster demos, start with `tag_len=4..8`, `byte_delay_us=800..1500`, noise=`none`.


