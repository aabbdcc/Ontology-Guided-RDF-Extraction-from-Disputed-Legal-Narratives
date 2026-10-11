"""Canonical event/attribution RDF representation and normalized triple evaluation.

Document references come from ingestion. Predicted sourceText must come from
the extractor; filling in a missing quote would inflate grounding scores.
"""

from __future__ import annotations
from decimal import Decimal
from pathlib import Path
import json
import re
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, XSD, SKOS

EX = Namespace("https://example.org/legal-kg/")
ROOT = Path(__file__).resolve().parents[1]
CORE_PROPS = {
    EX.payer,
    EX.recipient,
    EX.amount,
    EX.currency,
    EX.date,
    EX.assertedBy,
    EX.concerns,
    EX.hasQualification,
    EX.claimKind,
    EX.claimAmount,
}


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).casefold()).strip("_")


def person_or_company(name: str):
    return (
        EX.Company
        if ("company " in name.lower() or name.lower().endswith(" ltd"))
        else EX.Person
    )


def load_jsonl(path):
    return [
        json.loads(row)
        for row in Path(path).read_text(encoding="utf-8").splitlines()
        if row.strip()
    ]


def graph_for(records, *, annotations_key="annotation") -> Graph:
    """Create graph from annotated rows. Predicted source spans must be explicit and exact."""
    g = Graph()
    g.bind("ex", EX)
    g.bind("xsd", XSD)
    g.bind("skos", SKOS)
    for rec in records:
        ann = rec.get(annotations_key)
        if not ann or ann.get("type") == "none":
            continue
        doc = EX["doc_" + rec["id"]]
        g.add((doc, RDF.type, EX.Document))
        source = rec["text"]
        if ann["type"] == "payment":
            payment = EX["payment_" + rec["id"]]
            statement = EX["fact_" + rec["id"]]
            g.add((payment, RDF.type, EX.Payment))
            for prop, name in (
                (EX.payer, ann.get("payer")),
                (EX.recipient, ann.get("recipient")),
            ):
                if name:
                    party = EX[slug(name)]
                    g.add((party, RDF.type, person_or_company(name)))
                    g.add((payment, prop, party))
            if ann.get("amount") is not None:
                try:
                    g.add(
                        (
                            payment,
                            EX.amount,
                            Literal(Decimal(str(ann["amount"])), datatype=XSD.decimal),
                        )
                    )
                except Exception:
                    g.add((payment, EX.amount, Literal(str(ann["amount"]))))
            if ann.get("currency"):
                g.add((payment, EX.currency, Literal(str(ann["currency"]))))
            if ann.get("date"):
                g.add((payment, EX.date, Literal(str(ann["date"]), datatype=XSD.date)))
            g.add((statement, RDF.type, EX.ObservedFact))
            g.add((statement, EX.concerns, payment))
        elif ann["type"] == "claim":
            claim = EX["claim_" + rec["id"]]
            g.add((claim, RDF.type, EX.Claim))
            if ann.get("asserted_by"):
                who = str(ann["asserted_by"])
                party = EX[slug(who)]
                g.add((party, RDF.type, person_or_company(who)))
                g.add((claim, EX.assertedBy, party))
            if ann.get("matter"):
                matter = EX[slug(ann["matter"])]
                g.add((matter, RDF.type, EX.DisputeMatter))
                g.add((claim, EX.concerns, matter))
            if ann.get("qualification"):
                qualification = EX[slug(ann["qualification"])]
                g.add((qualification, RDF.type, SKOS.Concept))
                g.add((claim, EX.hasQualification, qualification))
            if ann.get("kind"):
                kind = EX[slug(ann["kind"])]
                g.add((kind, RDF.type, SKOS.Concept))
                g.add((claim, EX.claimKind, kind))
            if ann.get("amount") is not None:
                try:
                    g.add(
                        (
                            claim,
                            EX.claimAmount,
                            Literal(Decimal(str(ann["amount"])), datatype=XSD.decimal),
                        )
                    )
                except Exception:
                    g.add((claim, EX.claimAmount, Literal(str(ann["amount"]))))
            statement = claim
        else:
            raise ValueError(f'Unknown annotation type {ann["type"]}')
        # The source document identity is known by the ingestion pipeline even if
        # the model did not produce a valid source quote. Do NOT conflate these.
        g.add((statement, EX.derivedFrom, doc))
        quote = ann.get(
            "source_quote", source if annotations_key == "annotation" else ""
        )
        if isinstance(quote, str) and quote and quote in source:
            g.add((statement, EX.sourceText, Literal(quote)))
    return g


def save_graph(g, filepath):
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(filepath), format="turtle")


def normalized_core_triples(graph):
    """Semantic triples only (not RDF serialization/scaffolding).

    Synthetic corpus uses canonical IDs assigned by document ID. This is NOT a
    general RDF graph alignment benchmark. Entities are normalized by slug.
    """
    triples = set()
    for s, p, o in graph:
        if p not in CORE_PROPS:
            continue
        if isinstance(o, Literal) and o.datatype == XSD.decimal:
            ov = f"dec:{str(Decimal(str(o)).normalize())}"
        else:
            ov = str(o)
        triples.add((str(s), str(p), ov))
    return triples
