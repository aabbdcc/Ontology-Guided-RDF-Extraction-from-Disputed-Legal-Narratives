"""Run a second nonrepresentative held-out-style challenge without tuning regex.

This is a designed robustness suite, not a model/ontology causality experiment.
"""

from collections import defaultdict
from pathlib import Path
import json
import csv
from src.rdf_utils import ROOT, load_jsonl, graph_for, normalized_core_triples
from src.extractors import naive_rule, attribution_aware_rule
from src.validation import validate_graph
from rdflib import Graph


def score(rows, fn):
    predicted = []
    units = []
    for row in rows:
        ann = fn(row["text"])
        if ann:
            ann = {**ann, "source_quote": row["text"]}
        predicted.append({**row, "predicted_annotation": ann})
        expected = row["annotation"]
        etype = expected["type"]
        ptype = ann["type"] if ann else "none"
        units.append(
            dict(
                id=row["id"],
                group=row["group"],
                expected=etype,
                predicted=ptype,
                type_correct=etype == ptype,
                abstain_correct=etype == "none" and ptype == "none",
            )
        )
    gold = graph_for(rows)
    predicted_graph = graph_for(predicted, annotations_key="predicted_annotation")
    gold_core = normalized_core_triples(gold)
    pred_core = normalized_core_triples(predicted_graph)
    tp = len(gold_core & pred_core)
    pp = len(pred_core)
    gg = len(gold_core)
    p = tp / pp if pp else 0
    r = tp / gg if gg else 0
    f = 2 * p * r / (p + r) if p + r else 0
    subtotals = {}
    for group in sorted({r["group"] for r in rows}):
        sub = [u for u in units if u["group"] == group]
        subtotals[group] = {
            "n": len(sub),
            "type_correct": sum(u["type_correct"] for u in sub),
            "detected": sum(u["predicted"] != "none" for u in sub),
        }
    n_pos = sum(r["annotation"]["type"] != "none" for r in rows)
    n_neg = sum(r["annotation"]["type"] == "none" for r in rows)
    val = validate_graph(
        predicted_graph,
        Graph().parse(ROOT / "ontology/shapes.ttl"),
        Graph().parse(ROOT / "ontology/ontology.ttl"),
        engine="offline_subset",
    )
    return {
        "n": len(rows),
        "positive_gold": n_pos,
        "negative_gold": n_neg,
        "positive_detected": sum(
            u["predicted"] != "none" and u["expected"] != "none" for u in units
        ),
        "correct_abstentions": sum(u["abstain_correct"] for u in units),
        "false_positive_abstentions": sum(
            u["expected"] == "none" and u["predicted"] != "none" for u in units
        ),
        "type_accuracy": round(sum(u["type_correct"] for u in units) / len(units), 4),
        "core_triples": {
            "tp": tp,
            "predicted": pp,
            "gold": gg,
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f, 4),
        },
        "groups": subtotals,
        "shacl_subset": {
            "engine": val["engine"],
            "conforms": val["conforms"],
            "violations": val["violations"],
        },
        "per_record": units,
    }


def main():
    rows = load_jsonl(ROOT / "data/challenge_24.jsonl")
    out = ROOT / "results/challenge"
    out.mkdir(exist_ok=True, parents=True)
    results = {
        name: score(rows, fn)
        for name, fn in [
            ("rule_naive", naive_rule),
            ("rule_attributed", attribution_aware_rule),
        ]
    }
    (out / "scores.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    with (out / "per_record.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "method",
                "id",
                "group",
                "expected",
                "predicted",
                "type_correct",
                "abstain_correct",
            ],
        )
        w.writeheader()
        for name, result in results.items():
            for record in result["per_record"]:
                w.writerow({"method": name, **record})
    for name, r in results.items():
        print(
            name,
            "type accuracy",
            r["type_accuracy"],
            "positives",
            r["positive_detected"],
            "/",
            r["positive_gold"],
            "abstentions",
            r["correct_abstentions"],
            "/",
            r["negative_gold"],
            "core F1",
            r["core_triples"]["f1"],
        )
    return results


if __name__ == "__main__":
    main()
