"""Offline reproducible engineering checks; NOT an LLM benchmark."""

from pathlib import Path
import json
import csv
from rdflib import Graph, Literal
from rdflib.namespace import RDF, XSD
from src.run_experiment import build_gold, save_verbalizations, run
from src.rdf_utils import ROOT, EX, load_jsonl
from src.validation import validate_graph


def main():
    gold = build_gold()
    save_verbalizations(gold)
    reports = [
        run(mode, validation_engine="offline_subset")
        for mode in ("rule_naive", "rule_attributed")
    ]
    shapes = Graph().parse(ROOT / "ontology/shapes.ttl")
    ontology = Graph().parse(ROOT / "ontology/ontology.ttl")
    gold_val = validate_graph(gold, shapes, ontology, engine="offline_subset")
    (ROOT / "results/gold_validation.json").write_text(
        json.dumps(gold_val, indent=2), encoding="utf-8"
    )
    # Deliberately injected constraints: missing payer, wrong amount datatype,
    # unsupported currency, claim without assertedBy and invalid class.
    invalid = Graph()
    for t in gold:
        invalid.add(t)
    node = EX.payment_D01
    for p in list(invalid.objects(node, EX.payer)):
        invalid.remove((node, EX.payer, p))
    for p in list(invalid.objects(node, EX.amount)):
        invalid.remove((node, EX.amount, p))
    invalid.add((node, EX.amount, Literal("ten thousand")))
    invalid.set((node, EX.currency, Literal("USD")))
    claim = EX.claim_D13
    for p in list(invalid.objects(claim, EX.assertedBy)):
        invalid.remove((claim, EX.assertedBy, p))
    invalid.set((EX.payment_D02, EX.recipient, EX.loan))
    injected = validate_graph(invalid, shapes, ontology, engine="offline_subset")
    (ROOT / "results/injected_violations.json").write_text(
        json.dumps(injected, indent=2), encoding="utf-8"
    )
    fieldnames = [
        "method",
        "is_llm",
        "documents",
        "predicted_core_triples",
        "gold_core_triples",
        "triple_precision",
        "triple_recall",
        "triple_f1",
        "correct_claims",
        "total_claims",
        "gold_claim_recovery",
        "generated_provenance_coverage",
        "gold_provenance_coverage",
        "conflict_precision",
        "conflict_recall",
        "conflict_f1",
        "shacl_violations",
        "validation_engine",
    ]
    with (ROOT / "results/metrics.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in reports:
            v = r["evaluation"]
            tri = v["core_triple_micro"]
            conflict = v["conflict_pair"]
            writer.writerow(
                {
                    "method": r["mode"],
                    "is_llm": False,
                    "documents": r["n_documents"],
                    "predicted_core_triples": tri["predicted"],
                    "gold_core_triples": tri["gold"],
                    "triple_precision": tri["precision"],
                    "triple_recall": tri["recall"],
                    "triple_f1": tri["f1"],
                    "correct_claims": v["claim_attribution"]["correct"],
                    "total_claims": v["claim_attribution"]["total"],
                    "gold_claim_recovery": v["claim_attribution"][
                        "gold_claim_recovery"
                    ],
                    "generated_provenance_coverage": v["provenance"][
                        "generated_coverage"
                    ],
                    "gold_provenance_coverage": v["provenance"]["gold_coverage"],
                    "conflict_precision": conflict["precision"],
                    "conflict_recall": conflict["recall"],
                    "conflict_f1": conflict["f1"],
                    "shacl_violations": r["validation"]["violations"],
                    "validation_engine": r["validation"]["engine"],
                }
            )
    print("gold:", gold_val["conforms"], "violations", gold_val["violations"])
    print(
        "injected:",
        injected["conforms"],
        "violations",
        injected["violations"],
        [e["constraint"] for e in injected["details"]],
    )
    for r in reports:
        e = r["evaluation"]
        print(
            r["mode"],
            "triple",
            e["core_triple_micro"],
            "claim",
            e["claim_attribution"],
            "conflict",
            e["conflict_pair"],
            "schema violations",
            r["validation"]["violations"],
        )


if __name__ == "__main__":
    main()
