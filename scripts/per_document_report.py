"""Readable audit trail showing which synthetic documents each extractor recognized."""

import csv
import json
from src.rdf_utils import ROOT, load_jsonl


def main():
    records = load_jsonl(ROOT / "data/gold_annotations.jsonl")
    extracted = {}
    for mode in ["rule_naive", "rule_attributed"]:
        p = ROOT / "results" / mode / "predictions.jsonl"
        extracted[mode] = {o["id"]: o["prediction"] for o in load_jsonl(p)}
    out = ROOT / "results/per_document.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "doc_id",
                "category",
                "text",
                "gold_type",
                "naive_recognized",
                "expanded_recognized",
            ],
        )
        writer.writeheader()
        for row in records:
            writer.writerow(
                {
                    "doc_id": row["id"],
                    "category": row["category"],
                    "text": row["text"],
                    "gold_type": row["annotation"]["type"],
                    "naive_recognized": extracted["rule_naive"][row["id"]] is not None,
                    "expanded_recognized": extracted["rule_attributed"][row["id"]]
                    is not None,
                }
            )
    print(out)


if __name__ == "__main__":
    main()
