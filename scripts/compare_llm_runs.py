"""Summarize completed paired runs with document-bootstrap intervals.

Usage:
    python -m scripts.compare_llm_runs --run-dir results/llm_runs/challenge_YYYYMMDDTHHMMSSZ

Requires two complete arms and uses saved per-document predictions.
The intervals describe the supplied documents, not a wider legal population.
"""

from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import random
from statistics import mean
from src.rdf_utils import ROOT, load_jsonl, graph_for, normalized_core_triples
from src.llm_protocol import prompt_hash

SPLITS = {"main": "data/gold_annotations.jsonl", "challenge": "data/challenge_24.jsonl"}
ARMS = ("baseline", "guided")


def tp_counts(row, pred):
    gold_set = normalized_core_triples(graph_for([row]))
    pred_set = normalized_core_triples(
        graph_for(
            [{**row, "predicted_annotation": pred}],
            annotations_key="predicted_annotation",
        )
    )
    return {
        "tp": len(gold_set & pred_set),
        "pred": len(pred_set),
        "gold": len(gold_set),
    }


def rates(counts):
    tp = sum(r["tp"] for r in counts)
    p = sum(r["pred"] for r in counts)
    g = sum(r["gold"] for r in counts)
    precision = tp / p if p else 0
    recall = tp / g if g else 0
    f1 = 2 * tp / (p + g) if p + g else None
    return {
        "precision": round(precision, 5),
        "recall": round(recall, 5),
        "f1": round(f1, 5) if f1 is not None else None,
        "tp": tp,
        "predicted": p,
        "gold": g,
    }


def quantile(vals, alpha):
    ordered = sorted(vals)
    x = (len(ordered) - 1) * alpha
    lower = int(x)
    upper = min(len(ordered) - 1, lower + 1)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - x) + ordered[upper] * (x - lower)


def load_repetitions(run_dir, dataset, reps):
    ids = [r["id"] for r in dataset]
    all_records = []
    for rep in range(1, reps + 1):
        arms = {}
        for arm in ARMS:
            folder = run_dir / f"repeat_{rep}" / arm
            status = json.loads((folder / "metrics.json").read_text(encoding="utf-8"))
            if status.get("status") != "complete" or status.get("n_documents") != len(
                dataset
            ):
                raise ValueError(f"Incomplete experiment: {folder}")
            data = load_jsonl(folder / "predictions.jsonl")
            if len(data) != len(ids) or [x["id"] for x in data] != ids:
                raise ValueError(f"Prediction IDs do not match gold order in {folder}")
            audit = load_jsonl(folder / "responses.jsonl")
            if len(audit) != len(ids) or [x["id"] for x in audit] != ids:
                raise ValueError(f"Response IDs do not match gold order in {folder}")
            for row, prediction, response in zip(dataset, data, audit):
                if response.get("status") != "ok":
                    raise ValueError(f'Failed response in {folder}: {row["id"]}')
                if response.get("source_sha256") != prompt_hash(row["text"]):
                    raise ValueError(f'Source changed since inference: {row["id"]}')
                if prediction["prediction"] != response["predicted_annotation"]:
                    raise ValueError(f'Prediction differs from response: {row["id"]}')
                if response.get("prompt_sha256") != status["prompt_sha256"]:
                    raise ValueError(f'Prompt hash mismatch: {row["id"]}')
            arms[arm] = [
                tp_counts(row, item["prediction"]) for row, item in zip(dataset, data)
            ]
        all_records.append(arms)
    return all_records


def bootstrap_ci(records, n, iterations, seed):
    rnd = random.Random(seed)
    diffs = []
    for _ in range(iterations):
        inds = [rnd.randrange(n) for _ in range(n)]
        sample_deltas = []
        for rep in records:
            base = rates([rep["baseline"][i] for i in inds])["f1"]
            guided = rates([rep["guided"][i] for i in inds])["f1"]
            if base is not None and guided is not None:
                sample_deltas.append(guided - base)
        if sample_deltas:
            diffs.append(mean(sample_deltas))
    return [round(quantile(diffs, q), 5) for q in (0.025, 0.975)] if diffs else None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--bootstrap", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=20261011)
    args = parser.parse_args(argv)
    if not 100 <= args.bootstrap <= 100000:
        raise ValueError("bootstrap iterations must be in 100..100000")
    path = args.run_dir.resolve()
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    state = json.loads((path / "run_status.json").read_text(encoding="utf-8"))
    if state.get("status") != "complete":
        raise ValueError("LLM run did not complete; no paired scores may be claimed")
    dataset_name = manifest["dataset"]
    if dataset_name not in SPLITS:
        raise ValueError("Unknown dataset")
    dataset = load_jsonl(ROOT / SPLITS[dataset_name])
    reps = manifest["repetitions"]
    records = load_repetitions(path, dataset, reps)
    rows = []
    for rep_id, r in enumerate(records, 1):
        a = rates(r["baseline"])
        b = rates(r["guided"])
        rows.append(
            {
                "repetition": rep_id,
                "baseline": a,
                "guided": b,
                "delta_f1": round(b["f1"] - a["f1"], 5),
            }
        )
    avg_delta = mean(x["delta_f1"] for x in rows)
    ci = bootstrap_ci(records, len(dataset), args.bootstrap, args.seed)
    groups = {}
    for group in sorted(
        {r.get("group", r.get("category", "unknown")) for r in dataset}
    ):
        idx = [
            i
            for i, r in enumerate(dataset)
            if r.get("group", r.get("category", "unknown")) == group
        ]
        groups[group] = {"n": len(idx), "per_repeat": []}
        for repeat in records:
            a = rates([repeat["baseline"][i] for i in idx])
            b = rates([repeat["guided"][i] for i in idx])
            groups[group]["per_repeat"].append(
                {
                    "baseline": a,
                    "guided": b,
                    "delta_f1": (
                        round(b["f1"] - a["f1"], 5)
                        if a["f1"] is not None and b["f1"] is not None
                        else None
                    ),
                }
            )
    report = {
        "dataset": dataset_name,
        "n_documents": len(dataset),
        "model": manifest["model"],
        "repetitions": reps,
        "protocol_version": manifest["protocol_version"],
        "primary_outcome": "micro core-triple F1; guided minus baseline",
        "per_repeat": rows,
        "mean_delta_f1": round(avg_delta, 5),
        "paired_document_bootstrap_ci95": ci,
        "bootstrap_iterations": args.bootstrap,
        "subgroups": groups,
        "limits": [
            "Synthetic manually authored passages are not a representative legal corpus.",
            "The 24-item challenge set contains paraphrases of development cases.",
            "CI measures sampling variability over these 24 fixed document units, not real-world generalization.",
            "Model randomness can remain even at temperature zero.",
            "Guided arm adds explanatory semantic constraints AND ontology AND SHACL: cannot attribute any change to ontology alone.",
            "Both arms produce JSON annotations converted deterministically into RDF.",
        ],
    }
    (path / "paired_analysis.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    with (path / "paired_per_document.csv").open(
        "w", newline="", encoding="utf-8"
    ) as file:
        wr = csv.writer(file)
        wr.writerow(
            [
                "repeat",
                "id",
                "group",
                "baseline_tp",
                "baseline_pred",
                "baseline_gold",
                "guided_tp",
                "guided_pred",
                "guided_gold",
            ]
        )
        for i, rep in enumerate(records, 1):
            for row, a, b in zip(dataset, rep["baseline"], rep["guided"]):
                wr.writerow(
                    [
                        i,
                        row["id"],
                        row.get("group", row.get("category", "unknown")),
                        a["tp"],
                        a["pred"],
                        a["gold"],
                        b["tp"],
                        b["pred"],
                        b["gold"],
                    ]
                )
    exact_deltas = [
        2 * row["guided"]["tp"] / (row["guided"]["predicted"] + row["guided"]["gold"])
        - 2
        * row["baseline"]["tp"]
        / (row["baseline"]["predicted"] + row["baseline"]["gold"])
        for row in rows
    ]
    delta = round(mean(exact_deltas) * 100, 2)
    ci_str = f"{ci[0]*100:+.2f} to {ci[1]*100:+.2f} pp" if ci else "n/a"
    lines = [
        f'# Paired LLM Benchmark — {manifest["model"]}',
        "",
        f"- Dataset: `{dataset_name}` ({len(dataset)} synthetic documents).",
        f"- Arms: same model, identical JSON schema; baseline vs ontology/SHACL-guided prompt.",
        f"- Repeats: {reps}.",
        f"- Mean guided minus baseline micro-triple F1: **{delta:+.2f} percentage points**.",
        f"- Paired document-bootstrap 95% interval: **{ci_str}** (descriptive; small synthetic sample).",
        "",
        "| Repeat | Baseline F1 | Guided F1 | Delta (pp) |",
        "|---|---:|---:|---:|",
    ]
    for r, exact_delta in zip(rows, exact_deltas):
        lines.append(
            f'| {r["repetition"]} | {r["baseline"]["f1"]:.5f} | {r["guided"]["f1"]:.5f} | {exact_delta*100:+.2f} |'
        )
    lines.extend(
        ["", "## Interpretation limits", ""] + ["- " + x for x in report["limits"]]
    )
    (path / "paired_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:9]))
    print("Saved:", path / "paired_analysis.md")


if __name__ == "__main__":
    main()
