"""Detect *potentially competing assertions*, not adjudicated legal contradictions."""

from rdflib.namespace import RDF
from .rdf_utils import EX


def detect_conflicts(graph):
    claims = []
    for c in graph.subjects(RDF.type, EX.Claim):
        doc_id = str(c).split("claim_")[-1]
        claims.append(
            {
                "id": doc_id,
                "matter": graph.value(c, EX.concerns),
                "actor": graph.value(c, EX.assertedBy),
                "qualification": graph.value(c, EX.hasQualification),
                "kind": graph.value(c, EX.claimKind),
                "amount": graph.value(c, EX.claimAmount),
            }
        )
    output = []
    for i, a in enumerate(claims):
        for b in claims[i + 1 :]:
            if not a["matter"] or a["matter"] != b["matter"]:
                continue
            kind = None
            if (
                a["qualification"] is not None
                and b["qualification"] is not None
                and a["qualification"] != b["qualification"]
            ):
                kind = "competing_qualification"
            elif (
                a["actor"] == b["actor"]
                and a["kind"] is not None
                and a["kind"] == b["kind"]
                and a["amount"] is not None
                and b["amount"] is not None
                and a["amount"].toPython() != b["amount"].toPython()
            ):
                kind = "numeric_disagreement"
            if kind:
                x, y = sorted([a["id"], b["id"]])
                output.append({"a": x, "b": y, "type": kind})
    return sorted(output, key=lambda x: (x["a"], x["b"]))
