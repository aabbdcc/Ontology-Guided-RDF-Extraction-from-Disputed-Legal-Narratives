"""Metrics report the observation unit and denominator explicitly."""

from collections import defaultdict
from decimal import Decimal
from rdflib import Literal
from rdflib.namespace import RDF
from .rdf_utils import EX, normalized_core_triples
from .conflict_detection import detect_conflicts


def _prf(tp, pred, gold):
    prec = tp / pred if pred else 0.0
    rec = tp / gold if gold else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "predicted": pred,
        "gold": gold,
    }


def evaluate(gold, predictions, rows, gold_conflicts):
    gset = normalized_core_triples(gold)
    pset = normalized_core_triples(predictions)
    triple = _prf(len(gset & pset), len(pset), len(gset))

    def semantic_values(graph, subj, pred):
        values = []
        for obj in graph.objects(subj, pred):
            if (
                isinstance(obj, Literal)
                and obj.datatype
                and str(obj.datatype).endswith("#decimal")
            ):
                values.append(("decimal", Decimal(str(obj))))
            else:
                values.append(("rdf", str(obj)))
        return sorted(values)

    num_claims = 0
    attrib_correct = 0
    unmatched_qual = 0
    recognized = 0
    recognized_by_category = defaultdict(lambda: {"correct": 0, "total": 0})
    for row in rows:
        doc = row["id"]
        cat = row["category"]
        ann = row["annotation"]
        sub = EX[("claim_" if ann["type"] == "claim" else "payment_") + doc]
        recognized_by_category[cat]["total"] += 1
        if (
            sub,
            RDF.type,
            EX.Claim if ann["type"] == "claim" else EX.Payment,
        ) in predictions:
            recognized += 1
            recognized_by_category[cat]["correct"] += 1
        if ann["type"] == "claim":
            num_claims += 1
            core_preds = [EX.assertedBy, EX.concerns]
            if ann.get("qualification"):
                core_preds.append(EX.hasQualification)
            if ann.get("kind"):
                core_preds.append(EX.claimKind)
            if ann.get("amount") is not None:
                core_preds.append(EX.claimAmount)
            if all(
                semantic_values(gold, sub, p) == semantic_values(predictions, sub, p)
                for p in core_preds
            ):
                attrib_correct += 1
    for c in predictions.subjects(RDF.type, EX.Claim):
        p_qual = predictions.value(c, EX.hasQualification)
        g_qual = gold.value(c, EX.hasQualification)
        if p_qual is not None and p_qual != g_qual:
            unmatched_qual += 1
    all_statements = set(predictions.subjects(RDF.type, EX.Claim)) | set(
        predictions.subjects(RDF.type, EX.ObservedFact)
    )
    source_text = {r["id"]: r["text"] for r in rows}
    with_trace = 0
    for subj in all_statements:
        doc = predictions.value(subj, EX.derivedFrom)
        quote = predictions.value(subj, EX.sourceText)
        if not doc or not quote:
            continue
        doc_id = str(doc).rsplit("doc_", 1)[-1]
        if doc_id in source_text and str(quote) in source_text[doc_id]:
            with_trace += 1
    pconf = detect_conflicts(predictions)
    gold_set = {(c["a"], c["b"], c["type"]) for c in gold_conflicts["pairs"]}
    pred_set = {(c["a"], c["b"], c["type"]) for c in pconf}
    cmetrics = _prf(len(pred_set & gold_set), len(pred_set), len(gold_set))
    return {
        "core_triple_micro": triple,
        "recognized_units": recognized,
        "total_units": len(rows),
        "recognized_by_category": dict(recognized_by_category),
        "claim_attribution": {
            "correct": attrib_correct,
            "total": num_claims,
            "gold_claim_recovery": (
                round(attrib_correct / num_claims, 4) if num_claims else 0
            ),
        },
        "provenance": {
            "grounded_statements": with_trace,
            "generated_statements": len(all_statements),
            "generated_coverage": (
                round(with_trace / len(all_statements), 4) if all_statements else 0
            ),
            "gold_coverage": round(with_trace / len(rows), 4) if rows else 0,
        },
        "unsupported_qualifications": unmatched_qual,
        "potential_conflicts": pconf,
        "conflict_pair": cmetrics,
    }
