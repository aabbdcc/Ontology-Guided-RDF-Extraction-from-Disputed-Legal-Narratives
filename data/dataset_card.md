# Dataset Card — Fully Synthetic Contested Financial Narratives v2

## Intended use

A small, manually authored, educational benchmark for structured extraction of reported payments and attributed claims as RDF. Designed to test provenance, SHACL structural conformity, monetary-role disambiguation, and potential conflicts. Not a legal decision system, judicial training set, production benchmark, or representative sample of disputes.

## Files and sizes

- `synthetic_snippets.jsonl`: 24 plain-text development snippets.
- `gold_annotations.jsonl`: matching 24 one-item annotations (17 claim, 7 payment).
- `gold.ttl`: 247 gold RDF triples; **98 evaluated core semantic triples**.
- `gold_conflicts.json`: four *potential competing assertion* pairs.
- `robustness_probes.jsonl`: eight after-the-fact adversarial paraphrases.
- `challenge_24.jsonl`: the eight paraphrases, eight new in-template positives, and eight abstention/uncertainty controls; **73 core gold triples**.

## Authorship and ethics

Every passage is synthetic, with imaginary parties and artificial transactions. The benchmark includes no raw legal filings, private communications or personal identification. Financial amounts in one illustrative project scenario are intentionally fictional, and not copied from an identifiable dispute. The texts contain legal terminology but do not assign legal rights or adjudicate cases.

## Label conventions

- `payment`: a source describes a completed transfer; `ObservedFact` means *reported in text*, not independently verified.
- `claim`: an attributed assertion; claim qualifiers are SKOS concepts (`loan`, `investment`, `salary`, etc.).
- `kind`: distinguishes `claimed_reimbursement`, `total_expenditure`, `planned_contribution`.
- `none`: does not contain a *positively attributed, supported, in-scope* payment/claim within this deliberately narrow ontology. Absence is not proof of falsity.

One row supports at most **one** extraction; nested sources, multiple events, complex negation, and contested documentary evidence are outside scope. Source quote checks are exact-substring checks, not independent truth verification. The gold labels are authored rather than double-annotated; no inter-annotator agreement is available.

## Splits and leakage caution

The development examples influenced regex design. The eight paraphrases reuse the underlying cases from the development set and were manually designed to defeat regex patterns; the extra eight positive controls also reuse template syntax. Do not claim a blind or representative out-of-distribution benchmark, report statistical generalization, or interpret high precision on this corpus as proof of field performance.

## License notice

These newly authored fictional texts are included as source material for this demonstration; when publishing, add your chosen project license and confirm you have the right to release all files.
