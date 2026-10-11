# Results and data scope

Generated from saved measurements by `python -m scripts.create_evidence_report`.

| Item | Count | Scope |
|---|---:|---|
| Synthetic passages | 48 | 24 development + 24 challenge |
| Full gold RDF triples | 247 | Development, including types and provenance |
| Core semantic triples | 98 / 73 | Development / challenge |
| Claim / Payment | 17 / 7 | Development |
| OWL classes / SHACL node shapes / property shapes | 10 / 3 / 15 | Ontology and shapes |

## Paired LLM experiment

Run directory: `results/llm_runs/challenge_20261011T181352Z`. Model alias: `legal-kg-qwen4b:latest`; see the root `Modelfile` for the supplied model configuration.
Dataset: challenge; 24 documents; 1 paired repetitions.

| Arm | Precision | Recall | Micro-F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| baseline (repeat 1) | 0.8518 | 0.9452 | 0.8961 | 69 | 12 | 4 |
| guided (repeat 1) | 0.7753 | 0.9452 | 0.8518 | 69 | 20 | 4 |

See [research_summary.md](research_summary.md) for full metrics, subgroups and error cases. One small paired run cannot establish the general effectiveness of guidance.

## Rule baselines

| Dataset | Simple regex F1 | Attribution-aware regex F1 |
|---|---:|---:|
| Development | 0.3934 | 1.0000 |
| Challenge | 0.2195 | 0.6727 |

The expanded rules were written for development templates; development F1=1.0 is an in-template check. Both rules miss all eight challenge paraphrases.

## SHACL

Gold validation engine: `offline_core_subset`; 0 findings. Five injected edits produce 6 findings with `offline_core_subset`.

Structural conformance, exact quote matching and semantic correctness are measured separately. The challenge reuses development scenarios and has no blind evaluation or double annotation.

Standard pySHACL was also run: gold conforms, and removing the mandatory payer produces a finding. See `standard_shacl_verification.json`.
