"""Strict, non-fallback official pySHACL verification. Exits 1 if missing."""

from rdflib import Graph, Literal
import json
from src.rdf_utils import ROOT, EX
from src.validation import validate_graph


def main():
    gold = Graph().parse(ROOT / "data/gold.ttl")
    shapes = Graph().parse(ROOT / "ontology/shapes.ttl")
    ontology = Graph().parse(ROOT / "ontology/ontology.ttl")
    result = validate_graph(gold, shapes, ontology, engine="pyshacl")
    assert result["engine"] == "pyshacl" and result["conforms"], result
    # Exactly one violated mandatory role; no silent use of the subset validator
    bad = Graph()
    for triple in gold:
        bad.add(triple)
    bad.remove((EX.payment_D01, EX.payer, None))
    invalid = validate_graph(bad, shapes, ontology, engine="pyshacl")
    assert not invalid["conforms"] and invalid["violations"] >= 1, invalid
    (ROOT / "results/standard_shacl_verification.json").write_text(
        json.dumps(
            {"engine": "pyshacl", "gold": result, "missing_payer": invalid}, indent=2
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        "Official pySHACL: Gold CONFORMS; injected error DETECTED.",
        invalid["violations"],
        "violations",
    )


if __name__ == "__main__":
    main()
