"""Safety and measurement integrity tests for the v2 benchmark."""

import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from rdflib import Graph, Literal
from rdflib.namespace import RDF, XSD
from src.rdf_utils import ROOT, EX, graph_for, load_jsonl, normalized_core_triples
from src.quality_metrics import quality_metrics
from src.llm_protocol import system_prompt, parse_prediction
from scripts.run_challenge import score
from src.extractors import naive_rule, attribution_aware_rule
from src.validation import validate_graph
from src.run_experiment import build_gold


def test_gold_is_reproducible_against_file():
    generated = graph_for(load_jsonl(ROOT / "data/gold_annotations.jsonl"))
    saved = Graph().parse(ROOT / "data/gold.ttl")

    # rdflib may roundtrip 4500 -> 4500.0 for xsd:decimal; compare value-level semantics.
    def nondecimal(graph):
        return {
            (s, p, o)
            for s, p, o in graph
            if not (isinstance(o, Literal) and o.datatype == XSD.decimal)
        }

    assert nondecimal(generated) == nondecimal(saved)
    assert normalized_core_triples(generated) == normalized_core_triples(saved)


def test_missing_predicted_quote_is_not_credited():
    row = load_jsonl(ROOT / "data/gold_annotations.jsonl")[6]
    predicted = {
        **row,
        "predicted_annotation": {
            "type": "claim",
            "asserted_by": "Alma",
            "matter": "transfer_p7",
            "qualification": "loan",
        },
    }
    g = graph_for([predicted], annotations_key="predicted_annotation")
    assert (EX.claim_D07, EX.derivedFrom, EX.doc_D07) in g
    assert list(g.objects(EX.claim_D07, EX.sourceText)) == []


def test_exact_predicted_quote_is_credited():
    row = load_jsonl(ROOT / "data/gold_annotations.jsonl")[6]
    predicted = {
        **row,
        "predicted_annotation": {
            "type": "claim",
            "asserted_by": "Alma",
            "matter": "transfer_p7",
            "qualification": "loan",
            "source_quote": row["text"],
        },
    }
    g = graph_for([predicted], annotations_key="predicted_annotation")
    assert str(g.value(EX.claim_D07, EX.sourceText)) == row["text"]


def test_llm_parser_prevents_fabricated_quote_credit():
    out, audit = parse_prediction(
        json.dumps(
            {
                "type": "claim",
                "asserted_by": "Alma",
                "matter": "transfer_p7",
                "qualification": "loan",
                "source_quote": "unrelated fabrication",
            }
        ),
        "Alma claims transfer P7 was a loan.",
    )
    assert out["source_quote"] == ""
    assert audit["source_quote_valid"] is False


def test_no_promoted_claim_to_loan_fact():
    g = build_gold()
    assert (EX.transfer_q, RDF.type, EX.loan) not in g
    assert (EX.claim_D13, EX.hasQualification, EX.loan) in g


def test_challenge_has_exactly_24_and_balanced_groups():
    rows = load_jsonl(ROOT / "data/challenge_24.jsonl")
    assert len(rows) == 24
    assert {
        g: sum(r["group"] == g for r in rows) for g in set(r["group"] for r in rows)
    } == {
        "paraphrase_out_of_template": 8,
        "in_template_positive": 8,
        "abstention_controls": 8,
    }
    assert sum(r["annotation"]["type"] == "none" for r in rows) == 8


def test_challenge_score_is_reproducible():
    rows = load_jsonl(ROOT / "data/challenge_24.jsonl")
    res = score(rows, attribution_aware_rule)
    assert res["positive_detected"] == 8 and res["correct_abstentions"] == 8
    assert res["core_triples"]["gold"] == 73


def test_quality_uses_grounded_quote_and_claim_gold():
    row = load_jsonl(ROOT / "data/gold_annotations.jsonl")[6]
    annotation = row["annotation"]
    pred = [{**row, "predicted_annotation": {**annotation, "source_quote": "WRONG"}}]
    graph = graph_for(pred, annotations_key="predicted_annotation")
    result = quality_metrics([row], pred, graph)
    assert result["claim_attribution"]["correct"] == 1
    assert result["provenance"]["exact_quote_count"] == 0
    assert result["triple"]["f1"] == 1


def test_guided_prompt_is_distinct_but_common_schema_preserved():
    base = system_prompt(False)
    guided = system_prompt(True)
    assert guided.startswith(base)
    assert "SHACL Turtle:" in guided
    assert "SHACL Turtle:" not in base


def test_oracle_vs_abstention_detected_by_metrics():
    rows = load_jsonl(ROOT / "data/gold_annotations.jsonl")
    pred_oracle = [
        {
            **row,
            "predicted_annotation": {**row["annotation"], "source_quote": row["text"]},
        }
        for row in rows
    ]
    pred_none = [{**row, "predicted_annotation": None} for row in rows]
    good = quality_metrics(
        rows,
        pred_oracle,
        graph_for(pred_oracle, annotations_key="predicted_annotation"),
    )
    bad = quality_metrics(
        rows, pred_none, graph_for(pred_none, annotations_key="predicted_annotation")
    )
    assert good["triple"]["f1"] == 1
    assert bad["triple"]["f1"] == 0


def test_gold_and_bad_shape_with_offline_engine():
    g = build_gold()
    shapes = Graph().parse(ROOT / "ontology/shapes.ttl")
    ontology = Graph().parse(ROOT / "ontology/ontology.ttl")
    ok = validate_graph(g, shapes, ontology, engine="offline_subset")
    assert ok["conforms"]
    g.remove((EX.claim_D07, EX.assertedBy, None))
    fail = validate_graph(g, shapes, ontology, engine="offline_subset")
    assert fail["violations"] >= 1


def test_standard_pyshacl_if_dependency_available():
    pytest.importorskip("pyshacl")
    g = build_gold()
    shapes = Graph().parse(ROOT / "ontology/shapes.ttl")
    ontology = Graph().parse(ROOT / "ontology/ontology.ttl")
    res = validate_graph(g, shapes, ontology, engine="pyshacl")
    assert res["conforms"] and res["engine"] == "pyshacl"
    g.remove((EX.payment_D01, EX.payer, None))
    assert not validate_graph(g, shapes, ontology, engine="pyshacl")["conforms"]


def test_api_model_protocol_without_network(tmp_path):
    """Fake response checks experiment wiring, NOT model accuracy."""
    from scripts.run_paired_llm import run_one
    from types import SimpleNamespace

    row = load_jsonl(ROOT / "data/gold_annotations.jsonl")[0]
    gold_ann = row["annotation"]
    raw = {k: v for k, v in gold_ann.items() if k != "id"}
    raw["source_quote"] = row["text"]

    class Fake:
        def __init__(self):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        def create(self, **kwargs):
            return SimpleNamespace(
                model=kwargs["model"],
                usage=SimpleNamespace(prompt_tokens=50, completion_tokens=25),
                choices=[
                    SimpleNamespace(message=SimpleNamespace(content=json.dumps(raw)))
                ],
            )

    destination = tmp_path / "mock_trial"
    destination.mkdir()
    s = Graph().parse(ROOT / "ontology/shapes.ttl")
    onto = Graph().parse(ROOT / "ontology/ontology.ttl")
    out = run_one(
        Fake(),
        [row],
        "baseline",
        "FAKE_MODEL_NOT_LLM",
        1,
        None,
        True,
        destination,
        s,
        onto,
        {"pairs": []},
    )
    assert out["status"] == "complete"
    assert out["quality"]["triple"]["f1"] == 1
    assert out["quality"]["provenance"]["exact_quote_coverage"] == 1
    assert json.loads((destination / "responses.jsonl").read_text().splitlines()[0])[
        "raw_response"
    ] == json.dumps(raw)


def test_sparql_qualified_claims_query_executes():
    g = Graph().parse(ROOT / "data/gold.ttl")
    query = (ROOT / "ontology/queries.sparql").read_text(encoding="utf-8")
    matches = list(g.query(query))
    assert len(matches) == 12
    assert all(
        str(row[0]).endswith(
            (
                "claim_D07",
                "claim_D08",
                "claim_D09",
                "claim_D10",
                "claim_D11",
                "claim_D12",
                "claim_D13",
                "claim_D14",
                "claim_D15",
                "claim_D16",
                "claim_D17",
                "claim_D18",
            )
        )
        for row in matches
    )
