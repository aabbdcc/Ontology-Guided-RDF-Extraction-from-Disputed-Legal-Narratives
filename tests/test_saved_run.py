"""Regression checks for reporting saved inference without hiding stale inputs."""

import json
import shutil

import pytest

from scripts.audit_artifacts import audit_run
from scripts.compare_llm_runs import load_repetitions
from src.rdf_utils import ROOT, load_jsonl

RUN = ROOT / "results/llm_runs/challenge_20261011T181352Z"


def test_completed_run_reproduces_saved_quality():
    pytest.importorskip("pyshacl")
    report = audit_run(RUN)
    assert report["status"] == "verified"
    baseline, guided = [arm["quality"]["triple"] for arm in report["arms"]]
    assert baseline["tp"] == guided["tp"] == 69
    assert baseline["predicted"] == 81
    assert guided["predicted"] == 89


def test_changed_source_is_rejected():
    rows = load_jsonl(ROOT / "data/challenge_24.jsonl")
    rows[0]["text"] += " Changed after inference."
    with pytest.raises(ValueError, match="Source changed"):
        load_repetitions(RUN, rows, 1)


def test_prediction_edit_is_rejected(tmp_path):
    copy = tmp_path / "run"
    shutil.copytree(RUN, copy)
    path = copy / "repeat_1/baseline/predictions.jsonl"
    predictions = load_jsonl(path)
    predictions[0]["prediction"]["amount"] = 1
    path.write_text(
        "\n".join(json.dumps(row) for row in predictions) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="Prediction differs"):
        load_repetitions(copy, load_jsonl(ROOT / "data/challenge_24.jsonl"), 1)
