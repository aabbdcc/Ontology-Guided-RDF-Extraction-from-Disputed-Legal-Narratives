# Local paired experiment on Windows

The saved complete experiment uses the alias `legal-kg-qwen4b:latest`. The supplied Modelfile selects `qwen3.5:4b-q8_0` and an 8192-token context. The challenge scores are 89.6% baseline and 85.2% guided core-triple micro-F1. The following commands create a new run; to inspect saved results, use [QUICKSTART.md](QUICKSTART.md).

## Environment

Install Python and [Ollama](https://ollama.com/download/windows). In the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
ollama --version
ollama pull qwen3.5:4b-q8_0
ollama create legal-kg-qwen4b -f Modelfile
ollama list
```

Skip environment creation if it already exists. Keep Ollama running in the background; if necessary, run `ollama serve` in a separate terminal. Model downloads require network access. Check disk and memory requirements locally.

## Run both conditions

```powershell
$env:OPENAI_BASE_URL = 'http://localhost:11434/v1'
$env:OPENAI_API_KEY = 'ollama'
.\.venv\Scripts\python.exe -m scripts.check_local_model --model legal-kg-qwen4b:latest
.\.venv\Scripts\python.exe -m scripts.run_paired_llm --model legal-kg-qwen4b:latest --dataset challenge --repetitions 1 --seed 42 --dry-run
.\.venv\Scripts\python.exe -m scripts.run_paired_llm --model legal-kg-qwen4b:latest --dataset challenge --repetitions 1 --seed 42
```

The smoke test checks one passage and is not part of the benchmark. A complete repetition makes 48 model calls. Replace `<RUN_DIRECTORY>` below with the new directory printed by the runner:

```powershell
.\.venv\Scripts\python.exe -m scripts.compare_llm_runs --run-dir '<RUN_DIRECTORY>'
.\.venv\Scripts\python.exe -m scripts.audit_artifacts --run-dir '<RUN_DIRECTORY>'
.\.venv\Scripts\python.exe -m scripts.create_evidence_report --run-dir '<RUN_DIRECTORY>'
```

Both arms share the passages, JSON schema, temperature 0 and seed. The guided arm adds semantic instructions, ontology and SHACL. Requests disable reasoning and allow 512 output tokens. Endpoint support for these options must be checked. A fixed seed does not guarantee identical outputs across hardware or model versions.

## Outputs and interpretation

Each complete run contains a manifest, raw responses, predictions, RDF, metrics, summary and paired analysis. API or parsing failures mark the run incomplete and exclude it from paired reporting. Smoke tests and partial runs are not benchmark evidence.

Report core-triple micro-F1 differences in percentage points. Also inspect claim recovery, exact quote coverage, SHACL findings and abstention false positives. The saved run does not support an improvement from guidance; see the [research report](results/research_summary.md). Standard validation is available through `scripts.verify_standard_shacl`.

## Troubleshooting

- Missing model: check `ollama list` and the `:latest` suffix.
- Connection failure: check the Ollama background service and `http://localhost:11434/api/tags`.
- Timeout or JSON failure: inspect `FAILED.txt` and `responses.jsonl` in the new run.
- Missing dependencies: use the `.venv` interpreter.
- Insufficient memory: inspect `ollama ps`. If changing the model or quantization, create a new alias and record the configuration; do not reuse the saved run's model label.

For future experiments, archive the Ollama version, model digest, dependency versions, hardware and decoding configuration. These records are incomplete for the historical run.
