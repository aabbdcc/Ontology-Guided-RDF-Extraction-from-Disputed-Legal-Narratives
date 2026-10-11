"""Numeric and output edge cases outside the original sentence templates."""

from rdflib import Graph, Literal
from rdflib.namespace import RDF, XSD

from scripts.compare_llm_runs import quantile
from src.conflict_detection import detect_conflicts
from src.rdf_utils import EX
from src.verbalization import verbalize


def test_zero_payment_is_verbalized_with_graph_currency():
    graph = Graph()
    node = EX.payment_zero
    for predicate, value in (
        (RDF.type, EX.Payment),
        (EX.payer, EX.alice),
        (EX.recipient, EX.bob),
        (EX.amount, Literal("0", datatype=XSD.decimal)),
        (EX.currency, Literal("USD")),
        (EX.date, Literal("2026-01-01", datatype=XSD.date)),
    ):
        graph.add((node, predicate, value))
    assert "USD 0" in verbalize(graph, node)


def test_equal_decimal_values_do_not_create_conflict():
    graph = Graph()
    for node, amount in ((EX.claim_A, "100"), (EX.claim_B, "100.0")):
        graph.add((node, RDF.type, EX.Claim))
        graph.add((node, EX.assertedBy, EX.alice))
        graph.add((node, EX.concerns, EX.project_p))
        graph.add((node, EX.claimKind, EX.total_expenditure))
        graph.add((node, EX.claimAmount, Literal(amount, datatype=XSD.decimal)))
    assert detect_conflicts(graph) == []


def test_quantile_includes_upper_endpoint():
    assert quantile([2, 4, 6], 1) == 6
    assert quantile([4], 0.5) == 4
