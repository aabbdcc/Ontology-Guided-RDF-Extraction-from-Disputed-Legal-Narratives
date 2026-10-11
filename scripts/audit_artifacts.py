"""Recheck a saved paired run without contacting the model endpoint."""

import argparse
import json
from pathlib import Path

from rdflib import Graph
from rdflib.compare import isomorphic

from scripts.compare_llm_runs import SPLITS, load_repetitions
from src.llm_protocol import parse_prediction, prompt_hash, system_prompt
from src.quality_metrics import quality_metrics
from src.rdf_utils import ROOT, graph_for, load_jsonl
from src.validation import validate_graph


def audit_run(run):
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    state = json.loads((run / "run_status.json").read_text(encoding="utf-8"))
    if state.get("status") != "complete":
        raise ValueError("Only complete runs can be audited as paired experiments")
    rows = load_jsonl(ROOT / SPLITS[manifest["dataset"]])
    load_repetitions(run, rows, manifest["repetitions"])
    shapes = Graph().parse(ROOT / "ontology/shapes.ttl")
    ontology = Graph().parse(ROOT / "ontology/ontology.ttl")
    findings = []
    for repeat in range(1, manifest["repetitions"] + 1):
        for arm in ("baseline", "guided"):
            folder = run / f"repeat_{repeat}" / arm
            metrics = json.loads((folder / "metrics.json").read_text(encoding="utf-8"))
            if manifest[f"{arm}_prompt_sha256"] != prompt_hash(
                system_prompt(arm == "guided")
            ):
                raise ValueError(f"Current {arm} prompt differs from the archived hash")
            enriched = []
            for row, response in zip(rows, load_jsonl(folder / "responses.jsonl")):
                parsed, _ = parse_prediction(response["raw_response"], row["text"])
                if parsed != response["predicted_annotation"]:
                    raise ValueError(f"Raw-response parsing differs: {row['id']}")
                enriched.append({**row, "predicted_annotation": parsed})
            predicted = graph_for(enriched, annotations_key="predicted_annotation")
            # Turtle represents integral decimals as e.g. 10000.0. Round-trip
            # both graphs so equivalent numeric values have the same spelling.
            serialized = Graph().parse(
                data=predicted.serialize(format="turtle"), format="turtle"
            )
            if not isomorphic(serialized, Graph().parse(folder / "predicted.ttl")):
                raise ValueError(f"Saved RDF differs from predictions: {folder}")
            engine = (
                "pyshacl"
                if metrics["schema_validation_engine"] == "pyshacl"
                else "offline_subset"
            )
            validation = validate_graph(predicted, shapes, ontology, engine=engine)
            quality = quality_metrics(rows, enriched, predicted, validation)
            for key, value in quality.items():
                if metrics["quality"].get(key) != value:
                    raise ValueError(f"Saved metric differs: {folder}, {key}")
            findings.append(
                {
                    "repeat": repeat,
                    "arm": arm,
                    "documents": len(rows),
                    "quality": quality,
                    "validation_report": validation,
                }
            )
    return {
        "status": "verified",
        "run": run.relative_to(ROOT).as_posix(),
        "arms": findings,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    report = audit_run(args.run_dir.resolve())
    (ROOT / "results/artifact_audit.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        "Verified raw responses, source and prompt hashes, predictions, RDF and quality metrics."
    )


if __name__ == "__main__":
    main()
