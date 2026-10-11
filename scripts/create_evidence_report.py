"""Summarize saved rule and paired LLM measurements for reports and CV use."""

import argparse
import json
from pathlib import Path

from rdflib import Graph
from rdflib.namespace import OWL, RDF, SH

from scripts.compare_llm_runs import load_repetitions, rates
from src.rdf_utils import ROOT, graph_for, load_jsonl, normalized_core_triples


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path)
    args = parser.parse_args(argv)
    development = load_jsonl(ROOT / "data/gold_annotations.jsonl")
    challenge = load_jsonl(ROOT / "data/challenge_24.jsonl")
    gold = Graph().parse(ROOT / "data/gold.ttl")
    ontology = Graph().parse(ROOT / "ontology/ontology.ttl")
    shapes = Graph().parse(ROOT / "ontology/shapes.ttl")
    validation = read_json(ROOT / "results/gold_validation.json")
    injected = read_json(ROOT / "results/injected_violations.json")
    rules = {
        name: read_json(ROOT / "results" / name / "metrics.json")["evaluation"][
            "core_triple_micro"
        ]
        for name in ("rule_naive", "rule_attributed")
    }
    challenge_scores = read_json(ROOT / "results/challenge/scores.json")
    info = {
        "publication_safety": "Synthetic passages; no personal case records",
        "gold_documents": len(development),
        "challenge_documents": len(challenge),
        "challenge_groups": {
            group: sum(row["group"] == group for row in challenge)
            for group in sorted({row["group"] for row in challenge})
        },
        "gold_claims": sum(row["annotation"]["type"] == "claim" for row in development),
        "gold_payments": sum(
            row["annotation"]["type"] == "payment" for row in development
        ),
        "gold_rdf_triples_all": len(gold),
        "gold_rdf_core_triples": len(normalized_core_triples(gold)),
        "challenge_core_triples": len(normalized_core_triples(graph_for(challenge))),
        "ontology_classes": len(set(ontology.subjects(RDF.type, OWL.Class))),
        "shacl_node_shapes": len(set(shapes.subjects(RDF.type, SH.NodeShape))),
        "shacl_property_shapes": len(set(shapes.objects(None, SH.property))),
        "preannotated_competing_claim_pairs": len(
            read_json(ROOT / "data/gold_conflicts.json")["pairs"]
        ),
        "gold_validation": {
            key: validation[key] for key in ("engine", "conforms", "violations")
        },
        "error_injection": {key: injected[key] for key in ("engine", "violations")},
        "rule_development": rules,
        "rule_challenge": {
            name: score["core_triples"] for name, score in challenge_scores.items()
        },
        "challenge_by_group": {
            name: score["groups"] for name, score in challenge_scores.items()
        },
        "llm_inference_measured": False,
        "standard_pyshacl_measured_in_this_environment": False,
        "claims_not_supported": [
            "generalized extraction accuracy",
            "ontology guidance improves extraction",
        ],
    }
    standard_path = ROOT / "results/standard_shacl_verification.json"
    if standard_path.exists():
        standard = read_json(standard_path)
        info["standard_pyshacl_measured_in_this_environment"] = (
            standard["engine"] == "pyshacl" and standard["gold"]["conforms"]
        )
        info["standard_shacl_verification"] = standard
    if args.run_dir:
        run = args.run_dir.resolve()
    else:
        completed = [
            path.parent
            for path in (ROOT / "results/llm_runs").glob("*/run_status.json")
            if read_json(path).get("status") == "complete"
        ]
        run = max(completed, key=lambda path: path.name) if completed else None

    llm_lines = ["No complete paired LLM results are available."]
    cv = [
        "- Developed a provenance-aware text-to-RDF extraction pipeline with a 10-class ontology, SHACL validation, potential claim-conflict detection, and rule-based RDF-to-text verbalisation.",
        "- Designed a reproducible benchmark of 48 synthetic legal passages, including a 24-document challenge set with 73 core gold triples, and evaluated extraction quality, claim attribution, and provenance.",
    ]
    if run:
        manifest = read_json(run / "manifest.json")
        if read_json(run / "run_status.json").get("status") != "complete":
            raise ValueError("The selected paired run is incomplete")
        rows = {"main": development, "challenge": challenge}[manifest["dataset"]]
        records = load_repetitions(run, rows, manifest["repetitions"])
        analysis = read_json(run / "paired_analysis.json")
        measured = []
        for index, record in enumerate(records, 1):
            arms = {arm: rates(record[arm]) for arm in ("baseline", "guided")}
            if arms != {arm: analysis["per_repeat"][index - 1][arm] for arm in arms}:
                raise ValueError(
                    "Paired analysis is stale; rerun scripts.compare_llm_runs"
                )
            measured.append(arms)
        info.update(
            llm_inference_measured=True,
            llm_run=run.relative_to(ROOT).as_posix(),
            llm_model=manifest["model"],
            llm_dataset=manifest["dataset"],
            llm_repetitions=manifest["repetitions"],
            llm_results=measured,
        )
        llm_lines = [
            f"Run directory: `{info['llm_run']}`. Model alias: `{manifest['model']}`; see the root `Modelfile` for the supplied model configuration.",
            f"Dataset: {manifest['dataset']}; {len(rows)} documents; {manifest['repetitions']} paired repetitions.",
            "",
            "| Arm | Precision | Recall | Micro-F1 | TP | FP | FN |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for index, arms in enumerate(measured, 1):
            for arm, score in arms.items():
                llm_lines.append(
                    f"| {arm} (repeat {index}) | {score['precision']:.4f} | {score['recall']:.4f} | {score['f1']:.4f} | {score['tp']} | {score['predicted'] - score['tp']} | {score['gold'] - score['tp']} |"
                )
        llm_lines += [
            "",
            "See [research_summary.md](research_summary.md) for full metrics, subgroups and error cases. One small paired run cannot establish the general effectiveness of guidance.",
        ]
        if manifest["dataset"] == "challenge" and len(measured) == 1:
            baseline, guided = measured[0]["baseline"], measured[0]["guided"]
            extra = (guided["predicted"] - guided["tp"]) - (
                baseline["predicted"] - baseline["tp"]
            )
            cv.append(
                f"- Compared baseline and ontology/SHACL-guided prompting in one paired run on the challenge set: {baseline['f1'] * 100:.1f}% vs. {guided['f1'] * 100:.1f}% core-triple micro-F1, with {extra} additional false-positive triples under guidance."
            )
    (ROOT / "results/cv_evidence.json").write_text(
        json.dumps(info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (ROOT / "results/CV_BULLETS.md").write_text(
        "# CV wording\n\n**Ontology-Guided RDF Extraction from Disputed Legal Narratives**\n\nPython · Qwen3.5-4B · RDF/OWL · SHACL · SPARQL · rdflib · pySHACL\n\n"
        + "\n".join(cv)
        + "\n\nModel alias: `legal-kg-qwen4b:latest`; the supplied Modelfile uses `qwen3.5:4b-q8_0`. This records the supplied configuration, not an archived model-weight digest.\n",
        encoding="utf-8",
    )
    lines = [
        "# Results and data scope",
        "",
        "Generated from saved measurements by `python -m scripts.create_evidence_report`.",
        "",
        "| Item | Count | Scope |",
        "|---|---:|---|",
        f"| Synthetic passages | {len(development) + len(challenge)} | 24 development + 24 challenge |",
        f"| Full gold RDF triples | {len(gold)} | Development, including types and provenance |",
        f"| Core semantic triples | {info['gold_rdf_core_triples']} / {info['challenge_core_triples']} | Development / challenge |",
        f"| Claim / Payment | {info['gold_claims']} / {info['gold_payments']} | Development |",
        f"| OWL classes / SHACL node shapes / property shapes | {info['ontology_classes']} / {info['shacl_node_shapes']} / {info['shacl_property_shapes']} | Ontology and shapes |",
        "",
        "## Paired LLM experiment",
        "",
        *llm_lines,
        "",
        "## Rule baselines",
        "",
        "| Dataset | Simple regex F1 | Attribution-aware regex F1 |",
        "|---|---:|---:|",
        f"| Development | {rules['rule_naive']['f1']:.4f} | {rules['rule_attributed']['f1']:.4f} |",
        f"| Challenge | {challenge_scores['rule_naive']['core_triples']['f1']:.4f} | {challenge_scores['rule_attributed']['core_triples']['f1']:.4f} |",
        "",
        "The expanded rules were written for development templates; development F1=1.0 is an in-template check. Both rules miss all eight challenge paraphrases.",
        "",
        "## SHACL",
        "",
        f"Gold validation engine: `{validation['engine']}`; {validation['violations']} findings. Five injected edits produce {injected['violations']} findings with `{injected['engine']}`.",
        "",
        "Structural conformance, exact quote matching and semantic correctness are measured separately. The challenge reuses development scenarios and has no blind evaluation or double annotation.",
    ]
    if info["standard_pyshacl_measured_in_this_environment"]:
        lines += [
            "",
            "Standard pySHACL was also run: gold conforms, and removing the mandatory payer produces a finding. See `standard_shacl_verification.json`.",
        ]
    (ROOT / "results/KEY_RESULTS.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    (ROOT / "results/RESULTS.md").write_text(
        "# Results index\n\nSee [KEY_RESULTS.md](KEY_RESULTS.md) for measured results, [research_summary.md](research_summary.md) for the research report, and [error_analysis.md](error_analysis.md) for error cases.\n",
        encoding="utf-8",
    )
    print("Updated evidence, results index and CV wording.")


if __name__ == "__main__":
    main()
