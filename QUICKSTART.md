# Quick start

The project includes a completed paired challenge experiment: 24 synthetic passages, 73 core gold triples, 89.6% baseline and 85.2% guided micro-F1. Both conditions recover 69 triples; false positives increase from 12 to 20 under guidance. The challenge reuses development scenarios and is not a blind external test.

Read the [README](README.md), [research report](results/research_summary.md), and [measured results](results/KEY_RESULTS.md).

## Windows setup

Run in the project root. If `.venv` exists, use its interpreter directly. Otherwise:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

## Verify saved results

These commands do not contact a model endpoint:

```powershell
.\.venv\Scripts\python.exe -m scripts.audit_artifacts --run-dir results/llm_runs/challenge_20261011T181352Z
.\.venv\Scripts\python.exe -m scripts.verify_standard_shacl
.\.venv\Scripts\python.exe -m scripts.compare_llm_runs --run-dir results/llm_runs/challenge_20261011T181352Z
.\.venv\Scripts\python.exe -m scripts.create_evidence_report --run-dir results/llm_runs/challenge_20261011T181352Z
```

Rule checks are available through `scripts.run_offline`, `scripts.run_challenge`, and `scripts.robustness_probe`. See [LOCAL_EXPERIMENT.md](LOCAL_EXPERIMENT.md) to run new inference, and [PUBLISHING.md](PUBLISHING.md) for the initial GitHub import.
