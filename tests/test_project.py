import json
from rdflib import Graph, Literal
from rdflib.namespace import RDF
from src.rdf_utils import ROOT, EX, graph_for, load_jsonl
from src.run_experiment import build_gold
from src.validation import validate_graph
from src.extractors import naive_rule, attribution_aware_rule
from src.conflict_detection import detect_conflicts
from src.verbalization import verbalize


def data():
    return load_jsonl(ROOT / "data/gold_annotations.jsonl")


def graphs():
    g = build_gold()
    s = Graph().parse(ROOT / "ontology/shapes.ttl")
    o = Graph().parse(ROOT / "ontology/ontology.ttl")
    return g, s, o


def test_dataset_is_24_and_all_synthetic():
    rows = data()
    assert len(rows) == 24
    assert sorted(set(x["category"] for x in rows)) == [
        "attributed_claim",
        "competing_qualification",
        "numeric_semantics",
        "simple_payment",
    ]
    assert sum(r["annotation"]["type"] == "claim" for r in rows) == 17


def test_gold_turtle_parses_and_conforms():
    g, s, o = graphs()
    assert len(g) > 100
    res = validate_graph(g, s, o, engine="offline_subset")
    assert res["conforms"], res["details"]


def test_claim_not_promoted_to_loan_fact():
    g, *_ = graphs()
    assert (EX.transfer_q, RDF.type, EX.loan) not in g
    assert (EX.claim_D13, EX.hasQualification, EX.loan) in g


def test_naive_payment():
    assert naive_rule(data()[0]["text"])["amount"] == 10000


def test_expanded_handles_passive_payment():
    assert attribution_aware_rule(data()[2]["text"])["payer"] == "Claire"


def test_no_legal_qualification_in_bank_record():
    ann = attribution_aware_rule(data()[23]["text"])
    assert ann["type"] == "payment" and "qualification" not in ann


def test_expected_potential_conflicts_only():
    g, *_ = graphs()
    observed = detect_conflicts(g)
    expected = json.loads((ROOT / "data/gold_conflicts.json").read_text())["pairs"]
    assert observed == sorted(expected, key=lambda x: (x["a"], x["b"]))
    assert not any("D19" in (x["a"], x["b"]) for x in observed)


def test_repeated_monetary_kind_matters():
    g, *_ = graphs()
    assert {"a": "D22", "b": "D23", "type": "numeric_disagreement"} in detect_conflicts(
        g
    )


def test_missing_payer_violates():
    g, s, o = graphs()
    p = next(g.objects(EX.payment_D01, EX.payer))
    g.remove((EX.payment_D01, EX.payer, p))
    res = validate_graph(g, s, o, engine="offline_subset")
    assert not res["conforms"]
    assert any(v["constraint"] == "minCount" for v in res["details"])


def test_string_amount_violates():
    g, s, o = graphs()
    amount = next(g.objects(EX.payment_D01, EX.amount))
    g.remove((EX.payment_D01, EX.amount, amount))
    g.add((EX.payment_D01, EX.amount, Literal("ten thousand")))
    assert not validate_graph(g, s, o, engine="offline_subset")["conforms"]


def test_payment_to_wrong_class_violates():
    g, s, o = graphs()
    p = next(g.objects(EX.payment_D01, EX.payer))
    g.set((EX.payment_D01, EX.payer, EX.loan))
    assert not validate_graph(g, s, o, engine="offline_subset")["conforms"]


def test_gold_verbalization_preserves_attribution():
    g, *_ = graphs()
    text = verbalize(g, EX.claim_D13)
    assert "Mira claims that" in text and "loan" in text
    assert verbalize(g, EX.claim_D14).startswith("Northstar ltd claims that")


def test_all_expanded_rules_on_small_synthetic():
    assert all(attribution_aware_rule(r["text"]) is not None for r in data())
