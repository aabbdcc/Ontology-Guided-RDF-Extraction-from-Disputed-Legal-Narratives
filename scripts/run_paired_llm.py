"""Run an actual, audited same-model A/B inference benchmark.

Usage:
  python -m scripts.run_paired_llm --model MODEL --dataset main --dry-run
  OPENAI_API_KEY=... python -m scripts.run_paired_llm --model MODEL --dataset main --repetitions 3
  OPENAI_BASE_URL=http://localhost:11434/v1 OPENAI_API_KEY=ollama \\
    python -m scripts.run_paired_llm --model qwen3:8b --dataset challenge

Requires a reachable OpenAI-compatible chat endpoint. Completed experiments
are stored separately from the rule-based measurements.
"""

from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import time
from rdflib import Graph
from src.rdf_utils import ROOT, load_jsonl, graph_for, save_graph
from src.validation import validate_graph
from src.evaluation import evaluate
from src.llm_protocol import (
    system_prompt,
    prompt_hash,
    parse_prediction,
    describe_config,
    PROMPT_VERSION,
)
from src.quality_metrics import quality_metrics

DATASETS = {
    "main": "data/gold_annotations.jsonl",
    "challenge": "data/challenge_24.jsonl",
}


def call_model(client, model, system, source, seed=None, json_mode=True):
    kwargs = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": source},
        ],
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    if seed is not None:
        kwargs["seed"] = seed
    start = time.perf_counter()

    kwargs["reasoning_effort"] = "none"
    kwargs["max_tokens"] = 512
    response = client.chat.completions.create(**kwargs)
    elapsed = time.perf_counter() - start
    choice = response.choices[0]
    content = choice.message.content
    if not isinstance(content, str):
        raise ValueError("No text completion returned")
    usage = getattr(response, "usage", None)
    counts = {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
    }
    return content, elapsed, counts, getattr(response, "model", model)


def run_one(
    client,
    rows,
    arm,
    model,
    iteration,
    seed,
    json_mode,
    output,
    shapes,
    ontology,
    gold_conflicts,
):
    prompt = system_prompt(arm == "guided")
    enriched = []
    audit = []
    errors = []
    file = output / "responses.jsonl"
    for row in rows:
        source = row["text"]
        doc_id = row["id"]
        path_key = f"{iteration}/{arm}/{doc_id}"
        try:
            raw, elapsed, usage, actual_model = call_model(
                client, model, prompt, source, seed, json_mode
            )
            parsed, info = parse_prediction(raw, source)
            entry = {
                "id": doc_id,
                "model_requested": model,
                "model_returned": actual_model,
                "arm": arm,
                "repeat": iteration,
                "prompt_sha256": prompt_hash(prompt),
                "source_sha256": prompt_hash(source),
                "raw_response": raw,
                "predicted_annotation": parsed,
                "parse_info": info,
                "latency_s": round(elapsed, 4),
                "tokens": usage,
                "status": "ok",
            }
        except Exception as exc:
            entry = {
                "id": doc_id,
                "arm": arm,
                "repeat": iteration,
                "prompt_sha256": prompt_hash(prompt),
                "source_sha256": prompt_hash(source),
                "status": "failed",
                "error_type": type(exc).__name__,
                "error": str(exc)[:500],
            }
            errors.append(entry)
            audit.append(entry)
            (output / "responses.jsonl").write_text(
                "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in audit),
                encoding="utf-8",
            )
            break  # never silently count a network or parse failure as an abstention
        audit.append(entry)
        enriched.append({**row, "predicted_annotation": parsed})
        file.write_text(
            "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in audit),
            encoding="utf-8",
        )
    if errors:
        (output / "FAILED.txt").write_text(
            "Incomplete inference! No numerical result is valid.\n"
            + errors[0]["error"],
            encoding="utf-8",
        )
        return {
            "status": "failed",
            "arm": arm,
            "iteration": iteration,
            "completed": len(enriched),
            "expected": len(rows),
        }
    pred = graph_for(enriched, annotations_key="predicted_annotation")
    save_graph(pred, output / "predicted.ttl")
    (output / "predictions.jsonl").write_text(
        "".join(
            json.dumps(
                {"id": r["id"], "prediction": r["predicted_annotation"]},
                ensure_ascii=False,
            )
            + "\n"
            for r in enriched
        ),
        encoding="utf-8",
    )
    val = validate_graph(pred, shapes, ontology, engine="auto")
    (output / "validation_report.json").write_text(
        json.dumps(val, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    quality = quality_metrics(rows, enriched, pred, val)
    if all(r["annotation"]["type"] in ("payment", "claim") for r in rows):
        gold = graph_for(rows)
        eval_original = evaluate(gold, pred, rows, gold_conflicts)
        quality["conflict_pair"] = eval_original["conflict_pair"]
    metrics = {
        "status": "complete",
        "model": model,
        "arm": arm,
        "iteration": iteration,
        "n_documents": len(rows),
        "prompt_sha256": prompt_hash(prompt),
        "quality": quality,
        "schema_validation_engine": val["engine"],
        "shacl_conforms": val["conforms"],
        "shacl_violations": val["violations"],
        "total_prompt_tokens": sum(a["tokens"]["prompt_tokens"] or 0 for a in audit),
        "total_completion_tokens": sum(
            a["tokens"]["completion_tokens"] or 0 for a in audit
        ),
        "total_latency_s": round(sum(a["latency_s"] for a in audit), 2),
    }
    (output / "metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return metrics


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", required=True)
    p.add_argument("--dataset", choices=["main", "challenge"], default="main")
    p.add_argument("--repetitions", type=int, default=3)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--json-mode", choices=["on", "off"], default="on")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--output-dir", type=Path, default=None)
    opts = p.parse_args(argv)
    if not 1 <= opts.repetitions <= 10:
        raise ValueError("Repetitions must be 1..10")
    rows = load_jsonl(ROOT / DATASETS[opts.dataset])
    model = opts.model
    config = describe_config(
        model,
        opts.dataset,
        opts.repetitions,
        os.getenv("OPENAI_BASE_URL"),
        opts.json_mode,
        opts.seed,
    )
    config.update(
        n_documents=len(rows),
        baseline_prompt_sha256=prompt_hash(system_prompt(False)),
        guided_prompt_sha256=prompt_hash(system_prompt(True)),
        temperature=0,
        reasoning_effort="none",
        max_tokens=512,
    )
    if opts.dry_run:
        print(
            json.dumps(
                {
                    **config,
                    "status": "DRY_RUN_NO_INFERENCE",
                    "planned_api_calls": len(rows) * 2 * opts.repetitions,
                },
                indent=2,
            )
        )
        return
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "Missing OPENAI_API_KEY. A real API/local endpoint is necessary. No LLM scores generated."
        )
    from openai import OpenAI

    client = OpenAI(
        base_url=os.getenv("OPENAI_BASE_URL") or None, timeout=300, max_retries=0
    )
    runstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = opts.output_dir or ROOT / "results/llm_runs" / f"{opts.dataset}_{runstamp}"
    output.mkdir(parents=True, exist_ok=False)
    (output / "manifest.json").write_text(
        json.dumps({**config, "created_at_utc": runstamp}, indent=2), encoding="utf-8"
    )
    shapes = Graph().parse(ROOT / "ontology/shapes.ttl")
    ontology = Graph().parse(ROOT / "ontology/ontology.ttl")
    conflicts = (
        json.loads((ROOT / "data/gold_conflicts.json").read_text(encoding="utf-8"))
        if opts.dataset == "main"
        else {"pairs": []}
    )
    reports = []
    for trial in range(1, opts.repetitions + 1):
        for arm in ("baseline", "guided"):
            dest = output / f"repeat_{trial}" / arm
            dest.mkdir(parents=True, exist_ok=True)
            report = run_one(
                client,
                rows,
                arm,
                model,
                trial,
                opts.seed,
                opts.json_mode == "on",
                dest,
                shapes,
                ontology,
                conflicts,
            )
            reports.append(report)
            print(trial, arm, report["status"])
            if report["status"] == "failed":
                (output / "run_status.json").write_text(
                    json.dumps({"status": "incomplete", "reports": reports}, indent=2),
                    encoding="utf-8",
                )
                raise RuntimeError(
                    f"Incomplete run; see {dest} . No paired scores may be claimed."
                )
    (output / "run_status.json").write_text(
        json.dumps({"status": "complete", "reports": reports}, indent=2),
        encoding="utf-8",
    )
    with (output / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        fields = [
            "model",
            "iteration",
            "arm",
            "n_documents",
            "triple_precision",
            "triple_recall",
            "triple_f1",
            "claim_recovery",
            "quote_coverage",
            "negative_false_positive_count",
            "shacl_violations",
            "schema_validation_engine",
            "prompt_tokens",
            "completion_tokens",
            "latency_s",
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for result in reports:
            q = result["quality"]
            t = q["triple"]
            writer.writerow(
                {
                    "model": model,
                    "iteration": result["iteration"],
                    "arm": result["arm"],
                    "n_documents": result["n_documents"],
                    "triple_precision": t["precision"],
                    "triple_recall": t["recall"],
                    "triple_f1": t["f1"],
                    "claim_recovery": q["claim_attribution"]["recall"],
                    "quote_coverage": q["provenance"]["exact_quote_coverage"],
                    "negative_false_positive_count": q["negative_false_positive_count"],
                    "shacl_violations": result["shacl_violations"],
                    "schema_validation_engine": result["schema_validation_engine"],
                    "prompt_tokens": result["total_prompt_tokens"],
                    "completion_tokens": result["total_completion_tokens"],
                    "latency_s": result["total_latency_s"],
                }
            )
    print("Complete. Paired experiment output:", output)


if __name__ == "__main__":
    main()
