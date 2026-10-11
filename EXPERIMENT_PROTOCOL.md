# Paired extraction protocol

The completed Qwen3.5-4B challenge run scores 89.6% baseline versus 85.2% guided core-triple micro-F1, with eight additional false-positive triples under guidance. Results and limitations are documented in [research_summary.md](results/research_summary.md).

Baseline uses common structured extraction instructions. Guided adds semantic explanations, ontology Turtle and SHACL Turtle. Both return JSON annotations, then use the same RDF builder. This comparison evaluates the complete guidance package, rather than isolating ontology or SHACL effects.

Recheck the saved run without contacting a model:

```powershell
.\.venv\Scripts\python.exe -m scripts.audit_artifacts --run-dir results/llm_runs/challenge_20261011T181352Z
```

See [LOCAL_EXPERIMENT.md](LOCAL_EXPERIMENT.md) for new inference. Future work should include independently annotated blind data, guidance ablations, quote-entailment review and a separate validation-and-repair condition. Repeated runs on the same small set test stability, not generalization.
