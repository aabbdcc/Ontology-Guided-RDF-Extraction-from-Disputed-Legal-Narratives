# Research report: ontology guidance and semantic fidelity

## Question and design

Does adding an ontology and SHACL constraints to a structured extraction prompt improve the resulting RDF? This prototype focuses on reported payments and attributed claims, where a legal qualification must remain attached to its speaker.

The development set contains 24 synthetic passages, 17 claims, 7 payment events and 98 core gold triples. The challenge set has 24 passages and 73 core gold triples, divided equally between paraphrases, template positives and abstention controls. The full development graph has 247 triples. Ten ontology classes and three SHACL node shapes define the target representation.

A completed paired experiment used the local model alias `legal-kg-qwen4b:latest`. The supplied Modelfile names `qwen3.5:4b-q8_0`; the run did not archive a weight digest. Both conditions used temperature 0, seed 42, JSON output, no reasoning and a 512-token output limit. Guidance added semantic definitions, ontology Turtle and SHACL Turtle to the common extraction prompt. The experiment has one repetition, with 48 successful calls in total.

## Results

| Measure | Baseline | Guided |
|---|---:|---:|
| Precision | 0.85185 | 0.77528 |
| Recall | 0.94521 | 0.94521 |
| Core-triple micro-F1 | 0.89610 | 0.85185 |
| TP / FP / FN | 69 / 12 / 4 | 69 / 20 / 4 |
| Correct claims / gold claims | 4 / 9 | 3 / 9 |
| Correct output type / documents | 20 / 24 | 19 / 24 |
| Correct gold fields / gold fields | 62 / 66 | 62 / 66 |
| Claim promoted to payment | 0 | 0 |
| False-positive abstention documents | 4 / 8 | 5 / 8 |
| Exact quotations / extracted units | 20 / 20 | 20 / 21 |
| pySHACL findings | 1 | 2 |
| Prompt tokens | 6,578 | 39,338 |
| Completion tokens | 1,050 | 1,129 |
| Total logged call latency | 33.7 s | 53.3 s |

The main difference is lower precision under guidance. True positives remain at 69, while false positives increase by eight. Seven of the net additional false-positive triples occur in the abstention subgroup. Guidance improves the paraphrase subgroup slightly but loses one true positive in the template subgroup.

| Challenge subgroup | Documents | Baseline F1 | Guided F1 | Baseline FP | Guided FP |
|---|---:|---:|---:|---:|---:|
| Paraphrases | 8 | 0.92958 | 0.94444 | 2 | 2 |
| Template positives | 8 | 0.98630 | 0.95890 | 0 | 1 |
| Abstention controls | 8 | 0.00000 | 0.00000 | 10 | 17 |

F1 on the abstention subgroup is uninformative here because there are no positive gold triples; false-positive counts carry the useful information. Across the full set, the guided-minus-baseline difference is −4.43 percentage points. A paired document bootstrap with 3,000 samples gives a descriptive 95% interval of −10.85 to +0.80 points. It spans zero, and only reflects variation across this small authored set.

## Interpretation

The findings do not support an extraction improvement from the full guidance package in this run. More ontology context appears to encourage some out-of-scope assertions, particularly on negated or uncertain material. This is an interpretation of the observed examples, not a proven mechanism. The experiment combines ontology, SHACL and explanatory instructions, so it cannot identify which component caused the change.

Quote coverage and structural validity give complementary evidence. Baseline has an exact quotation for every emitted unit, yet it still has twelve false-positive triples. Guided has one missing valid quote and two SHACL findings. Neither quote matching nor SHACL conformance establishes that an assertion follows from the source.

The claim metric is stricter than finding an `assertedBy` relation: it requires the correct speaker, matter, expected qualification/kind/amount, and absence of unsupported optional claim fields. This explains why claim recovery is substantially lower than triple recall. The canonical document and entity identifiers make evaluation tractable; unrestricted entity linking is outside the benchmark.

## Rule and validation checks

Simple and attribution-aware regex baselines score 0.3934 and 1.0000 on development, and 0.2195 and 0.6727 on challenge. The attribution-aware rules were written for the development templates. Both rules fail on all eight deliberately rewritten challenge passages.

The project-specific offline SHACL subset reports zero gold violations and six findings from five injected edits. A separate standard pySHACL check confirms the gold graph and detects a removed mandatory payer. The LLM metrics use pySHACL, not the subset. The saved-run audit reconstructs predictions from raw responses and verifies hashes, RDF and every quality metric without further inference.

## Limitations and next experiment

All passages and gold annotations were authored for this project, without independent double annotation. Challenge paraphrases reuse development scenarios, and the positive controls share template syntax. There is only one paired repetition. Requests ran baseline first and guided second; prompt length and processing time differ substantially. The model configuration is supplied, but its weight identity and server environment are not archived.

The output schema supports one event or claim per passage. Long narratives, multiple claims, nested sources and open-domain entity linking need a different annotation protocol. RDF-to-text is rule-based and has only been checked as a grounded example; it is not a measured LLM verbalisation task. Collaborative co-editing and synchronization remain future work.

For the Inria topic, the strongest current contribution is an inspectable extraction-and-validation experiment with a documented negative result. Next steps are a blind independently annotated set, guidance ablations, explicit quote-entailment judgments, and a repair condition evaluated separately from detection.

## Evidence

- [Paired analysis](llm_runs/challenge_20261011T181352Z/paired_analysis.json) and [per-document counts](llm_runs/challenge_20261011T181352Z/paired_per_document.csv).
- [Baseline metrics](llm_runs/challenge_20261011T181352Z/repeat_1/baseline/metrics.json) and [guided metrics](llm_runs/challenge_20261011T181352Z/repeat_1/guided/metrics.json).
- [Error cases](error_analysis.md), [artifact audit](artifact_audit.json), and [standard SHACL check](standard_shacl_verification.json).
