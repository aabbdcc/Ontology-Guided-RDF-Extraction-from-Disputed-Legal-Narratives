# Paired LLM Benchmark — legal-kg-qwen4b:latest

- Dataset: `challenge` (24 synthetic documents).
- Arms: same model, identical JSON schema; baseline vs ontology/SHACL-guided prompt.
- Repeats: 1.
- Mean guided minus baseline micro-triple F1: **-4.43 percentage points**.
- Paired document-bootstrap 95% interval: **-10.85 to +0.80 pp** (descriptive; small synthetic sample).

| Repeat | Baseline F1 | Guided F1 | Delta (pp) |
|---|---:|---:|---:|
| 1 | 0.89610 | 0.85185 | -4.43 |

## Interpretation limits

- Synthetic manually authored passages are not a representative legal corpus.
- The 24-item challenge set contains paraphrases of development cases.
- CI measures sampling variability over these 24 fixed document units, not real-world generalization.
- Model randomness can remain even at temperature zero.
- Guided arm adds explanatory semantic constraints AND ontology AND SHACL: cannot attribute any change to ontology alone.
- Both arms produce JSON annotations converted deterministically into RDF.
