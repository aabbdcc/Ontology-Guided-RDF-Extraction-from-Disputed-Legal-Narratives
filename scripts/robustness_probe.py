"""Out-of-template adversarial paraphrases: not blind and not statistically representative."""

import json
from src.rdf_utils import ROOT, load_jsonl, graph_for, normalized_core_triples
from src.extractors import naive_rule, attribution_aware_rule


def main():
    rows = load_jsonl(ROOT / "data/robustness_probes.jsonl")
    gold = graph_for(rows)
    gset = normalized_core_triples(gold)
    output = {
        "n_paraphrases": len(rows),
        "gold_core_triples": len(gset),
        "selection": "manually adversarial, after rule design",
        "methods": {},
    }
    for name, fn in [
        ("rule_naive", naive_rule),
        ("rule_attributed", attribution_aware_rule),
    ]:
        preds = [{**r, "prediction": fn(r["text"])} for r in rows]
        extracted = graph_for(preds, annotations_key="prediction")
        pset = normalized_core_triples(extracted)
        output["methods"][name] = {
            "recognized_units": sum(1 for p in preds if p["prediction"] is not None),
            "triple_recall": round(len(pset & gset) / len(gset), 4),
            "triple_correct": len(pset & gset),
            "triple_predicted": len(pset),
        }
    (ROOT / "results/robustness.json").write_text(
        json.dumps(output, indent=2), encoding="utf-8"
    )
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
