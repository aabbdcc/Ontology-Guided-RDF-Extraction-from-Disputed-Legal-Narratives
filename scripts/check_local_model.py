"""Two-call local Ollama preflight: REAL baseline and guided inference on one example.

No invented scores: checks availability, verifies JSON and supporting-quote policy,
logs timings and raw model output. Results are a smoke test, not a benchmark.

Usage:
  python -m scripts.check_local_model --model legal-kg-qwen4b
"""

from __future__ import annotations
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from src.llm_protocol import system_prompt, parse_prediction
from src.rdf_utils import ROOT, load_jsonl


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", default="legal-kg-qwen4b")
    p.add_argument("--dataset", choices=["main", "challenge"], default="challenge")
    p.add_argument("--index", type=int, default=0, help="0-based sample index")
    p.add_argument(
        "--output", type=Path, default=ROOT / "results" / "local_model_smoke.json"
    )
    opts = p.parse_args(argv)
    base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    api_key = os.getenv("OPENAI_API_KEY", "ollama")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "Missing OpenAI SDK. Install dependencies: python -m pip install -r requirements.txt"
        ) from exc
    client = OpenAI(base_url=base_url, api_key=api_key, timeout=240, max_retries=0)
    print(f"Checking endpoint: {base_url}")
    names = [m.id for m in client.models.list().data]
    if opts.model not in names:
        raise RuntimeError(
            f"Model {opts.model!r} not found. Available: {names}. Run `ollama list`."
        )
    samples = load_jsonl(
        ROOT
        / (
            "data/challenge_24.jsonl"
            if opts.dataset == "challenge"
            else "data/gold_annotations.jsonl"
        )
    )
    if not 0 <= opts.index < len(samples):
        raise ValueError("Sample index out of range")
    row = samples[opts.index]
    print("Sample ID:", row["id"], "Text:", row["text"])
    from scripts.run_paired_llm import call_model

    readings = []
    for arm in ("baseline", "guided"):
        prompt = system_prompt(arm == "guided")
        raw, seconds, usage, actual = call_model(
            client, opts.model, prompt, row["text"], seed=42, json_mode=True
        )
        try:
            predicted, parse_info = parse_prediction(raw, row["text"])
            status = "parsed"
        except (ValueError, json.JSONDecodeError, TypeError) as exc:
            predicted = None
            parse_info = {"error": f"{type(exc).__name__}: {exc}"}
            status = "parse_error"
        entry = {
            "arm": arm,
            "seconds": round(seconds, 2),
            "tokens": usage,
            "model_returned": actual,
            "raw_response": raw,
            "predicted_annotation": predicted,
            "parse_info": parse_info,
            "status": status,
        }
        readings.append(entry)
        print(
            f'{arm}: {seconds:.1f}s; {status}; quote_valid={parse_info.get("source_quote_valid")}; raw={raw[:400]}'
        )
    result = {
        "status": "smoke_only_not_benchmark",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model": opts.model,
        "endpoint": base_url,
        "sample_id": row["id"],
        "input": row["text"],
        "results": readings,
        "note": "Do not report single-sample scores in a CV. Run paired benchmark on all 24 items.",
    }
    opts.output.parent.mkdir(parents=True, exist_ok=True)
    opts.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("Saved:", opts.output)
    if any(x["status"] != "parsed" for x in readings):
        raise RuntimeError("Smoke test returned non-JSON; see saved raw responses")
    print("Preflight succeeded. Ready for --dataset challenge benchmark.")


if __name__ == "__main__":
    main()
