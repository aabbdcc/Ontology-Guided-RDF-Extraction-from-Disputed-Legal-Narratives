"""Cross-dataset quality statistics. Annotation accuracy != adjudicated truth."""

from __future__ import annotations
from rdflib.namespace import RDF
from .rdf_utils import graph_for, normalized_core_triples, EX


def quality_metrics(rows, enriched, predicted_graph, validation=None):
    gold = graph_for(rows)
    g = normalized_core_triples(gold)
    p = normalized_core_triples(predicted_graph)
    tp = len(g & p)
    pre = tp / len(p) if p else 0.0
    rec = tp / len(g) if g else 0.0
    f1 = 2 * pre * rec / (pre + rec) if pre + rec else 0.0
    true_claims = [r for r in rows if r["annotation"]["type"] == "claim"]
    correct_claims = 0
    claimed_false_fact = 0
    quote_ok = 0
    extracted = 0
    negative_fp = 0
    correct_type = 0
    matched_fields = 0
    gold_fields = 0
    structural = [
        "payer",
        "recipient",
        "amount",
        "currency",
        "date",
        "asserted_by",
        "matter",
        "qualification",
        "kind",
    ]
    for orig, pr in zip(rows, enriched):
        gold_ann = orig["annotation"]
        ann = pr.get("predicted_annotation") or {"type": "none"}
        gt = gold_ann["type"]
        pt = ann["type"]
        correct_type += gt == pt
        if gt == "none" and pt != "none":
            negative_fp += 1
        if gt == "claim" and pt == "payment":
            claimed_false_fact += 1
        if pt != "none":
            extracted += 1
            quote = ann.get("source_quote", "")
            if isinstance(quote, str) and quote and quote in orig["text"]:
                quote_ok += 1
        if gt == "claim" and pt == "claim":
            expected_fields = [
                f
                for f in ("asserted_by", "matter", "qualification", "kind", "amount")
                if f in gold_ann
            ]
            if all(ann.get(f) == gold_ann[f] for f in expected_fields) and all(
                f not in ann
                for f in ("qualification", "kind", "amount")
                if f not in gold_ann
            ):
                correct_claims += 1
        for field in structural:
            if field in gold_ann:
                gold_fields += 1
                if pt == gt and ann.get(field) == gold_ann.get(field):
                    matched_fields += 1
    return {
        "documents": len(rows),
        "triple": {
            "tp": tp,
            "predicted": len(p),
            "gold": len(g),
            "precision": round(pre, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
        },
        "type_accuracy": round(correct_type / len(rows), 4) if rows else 0,
        "claim_attribution": {
            "correct": correct_claims,
            "total": len(true_claims),
            "recall": (
                round(correct_claims / len(true_claims), 4) if true_claims else None
            ),
        },
        "per_field": {
            "correct": matched_fields,
            "total": gold_fields,
            "recall": round(matched_fields / gold_fields, 4) if gold_fields else None,
        },
        "negative_false_positive_count": negative_fp,
        "claim_to_observed_payment_errors": claimed_false_fact,
        "provenance": {
            "exact_quote_count": quote_ok,
            "extracted_units": extracted,
            "exact_quote_coverage": round(quote_ok / extracted, 4) if extracted else 0,
        },
        "schema_validation": (
            {
                "engine": validation["engine"],
                "conforms": validation["conforms"],
                "violations": validation["violations"],
            }
            if validation
            else None
        ),
    }
