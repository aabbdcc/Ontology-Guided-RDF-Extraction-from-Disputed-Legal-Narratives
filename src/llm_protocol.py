"""Versioned, deterministic-as-supported paired LLM evaluation protocol.

No calls happen at import, test, or in dry-run. A real model endpoint and API
credentials are required to generate honest LLM measurements. The two arms
share model, output JSON schema, decoding, inputs, and scoring; only the
ontology/constraint guidance differs. The source is converted to RDF by code.
"""

from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any
from .rdf_utils import ROOT

PROMPT_VERSION = "2.0.0"
SYSTEM_COMMON = """You are a controlled extraction component. Extract at most ONE event or attributed claim from the passage.
Return exactly one JSON object. If there is no directly asserted payment or positively attributed claim that fits the allowed schema, return {"type":"none"}.
A source describing a completed payment may be represented with:
{"type":"payment","payer":"Name","recipient":"Name","amount":1000,"currency":"EUR","date":"YYYY-MM-DD","source_quote":"EXACT copied text span"}.
An attributed claim may be represented with:
{"type":"claim","asserted_by":"Name","matter":"transfer_q or project_p","qualification":"loan (optional)","kind":"planned_contribution (optional)","amount":1000,"source_quote":"EXACT copied text span"}.
Use only explicit source evidence. Include only supported fields and use snake_case for qualification, kind, and matter. For a claim about transfer X, matter is transfer_x. For a claim about payment X, matter is payment_x. For Project X, matter is project_x.
Do NOT include markdown or explanatory text. Quotes must be exact substrings of the input."""

GUIDANCE = """Semantic ontology/constraint guidance:
1. Party is a Person or Company. An observed payment event is NOT a legal qualification.
2. Claim is an attributed assertion made by a party, not an established fact.
3. A purported loan or investment is encoded only as the qualification of a Claim (hasQualification), never as the rdf:type of the payment.
4. Differing amounts for claimed_reimbursement, total_expenditure, and planned_contribution have different meanings; do not combine them.
5. A disputed or uncertain legal status must not be silently promoted to verified fact.
6. Retain source provenance with an exact supporting quotation; omit any attribute not explicitly supported.
7. SHACL constraints are structural and do not guarantee that the underlying text supports the claim.
The complete target graph vocabulary and validation constraints follow.\n"""

OUTPUT_FIELDS = {
    "type",
    "payer",
    "recipient",
    "amount",
    "currency",
    "date",
    "asserted_by",
    "matter",
    "qualification",
    "kind",
    "source_quote",
}


def system_prompt(guided: bool) -> str:
    if not guided:
        return SYSTEM_COMMON
    return (
        SYSTEM_COMMON
        + "\n"
        + GUIDANCE
        + "\nONTOLOGY Turtle:\n"
        + (ROOT / "ontology/ontology.ttl").read_text(encoding="utf-8")
        + "\nSHACL Turtle:\n"
        + (ROOT / "ontology/shapes.ttl").read_text(encoding="utf-8")
    )


def prompt_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_prediction(
    text: str, source: str
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Auditable parser. No hidden truncation or silent fabricated quote credit."""
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError("Expected JSON object")
    kind = raw.get("type")
    if kind in ("none", None):
        return None, {"status": "abstained", "source_quote_valid": None}
    if kind not in ("payment", "claim"):
        raise ValueError("Unknown type " + repr(kind))
    parsed = {k: v for k, v in raw.items() if k in OUTPUT_FIELDS}
    bad_quote = not (
        isinstance(parsed.get("source_quote"), str)
        and parsed["source_quote"]
        and parsed["source_quote"] in source
    )
    if bad_quote:
        parsed["source_quote"] = ""  # sourceText omitted; SHACL flags it
    return parsed, {
        "status": "parsed",
        "source_quote_valid": not bad_quote,
        "extra_fields": sorted(set(raw) - OUTPUT_FIELDS),
    }


def describe_config(model, dataset, repetitions, base_url, json_mode, seed):
    return {
        "protocol_version": PROMPT_VERSION,
        "model": model,
        "dataset": dataset,
        "repetitions": repetitions,
        "base_url": base_url or "provider_default",
        "json_mode": json_mode,
        "seed": seed,
        "experiment": "paired_same_model_baseline_vs_ontology_guided",
        "claim_limit": "one event or claim per snippet",
        "normalization": "JSON intermediate -> deterministic rdflib construction",
        "caveat": "Synthetic author-constructed benchmark; nonrepresentative",
    }
