# Error analysis

This analysis refers to the completed `challenge_20261011T181352Z` paired run. Core-triple counts are reconstructed from saved predictions; no additional model calls are involved.

## Where the eight extra false positives arise

| Document | Error | Baseline FP | Guided FP | Net change |
|---|---|---:|---:|---:|
| P05 | Baseline uses `capital investment` instead of gold `investment`; guidance fixes it | 1 | 0 | −1 |
| P07 | Guidance adds an unsupported `loan` qualification | 0 | 1 | +1 |
| H15 | Guidance substitutes `loan` for explicit `salary` | 0 | 1 | +1 |
| H19 | Guidance extracts a claim from a discussion of a transfer that never occurred | 0 | 3 | +3 |
| H22 | Guidance adds `loan` and `planned_contribution` to an uncertain statement | 2 | 4 | +2 |
| H23 | Guidance adds `loan` and `planned_contribution` where the court has not decided | 2 | 4 | +2 |
| Other documents | No change in false-positive triple count | 7 | 7 | 0 |
| Total | | 12 | 20 | +8 |

This is a net difference in triple counts, not eight additional erroneous documents. False extractions on the eight abstention controls increase from four documents to five. H19 is the additional document; H22 and H23 already have false extractions in both conditions but acquire extra unsupported properties under guidance.

## Negation and uncertainty

H17 says Alice denies that Transfer V was a loan. Both conditions encode a positive loan claim. Their supporting quotations match the source exactly, but the extracted assertion reverses its meaning.

H18 asks whether EUR 3,000 might have been a loan. Both conditions invent a claim about `transfer_q` without an identified speaker. This also produces a mandatory `assertedBy` SHACL finding in each graph.

H19 says a possible transfer was discussed and the payment never occurred. Baseline abstains; guided emits a claim based on a partial quotation. A source substring can be valid while omitting the context needed to interpret it.

H22 expresses uncertainty between salary and gift, and H23 states that the court has not decided. The schema requires abstention for both. Guidance nevertheless introduces `loan` and `planned_contribution`, neither of which appears in the passages.

## Monetary roles and legal qualification

P06 and H16 report expenditure, but both conditions omit `kind=total_expenditure`. Baseline also omits `kind=claimed_reimbursement` in P07. Guided retains the omission and adds `qualification=loan`. P08 receives an unsupported loan qualification in both conditions despite correctly identifying a planned contribution.

P05 illustrates a small benefit from guidance: `capital investment` is mapped to the gold concept `investment`. H15 illustrates the opposite: an explicit salary claim becomes a loan. Overall true positives stay at 69, with four missed triples in each condition, but the identities of the errors differ.

## Quote and claim metrics

Baseline emits 20 units with 20 valid exact quotations. Guided emits 21 units with 20 valid quotations; H14 supplies no quotation and consequently lacks RDF `sourceText`, producing the second guided SHACL finding. These counts measure string matching, not entailment.

Fully correct claims are 4/9 for baseline and 3/9 for guided. This metric checks all expected speaker/matter/qualification/kind/amount fields and rejects extra optional qualification, kind or amount keys. The existing protocol counts an extra `amount: null` key as a mismatch, even though it contributes no RDF amount triple. In P05, guidance fixes the qualification but still fails the full-claim check for this reason. The published scores retain this original metric definition; future evaluation should decide explicitly whether null and absent fields are equivalent.

## Rule baselines and validation controls

The simple development regex emits 6/24 target units and recovers 24/98 core triples. The expanded regex recovers 98/98 and all four annotated potential-conflict pairs because it was written for these templates. Both systems recover 0/36 core triples on the eight adversarial paraphrases. Their challenge F1 values are 0.2195 and 0.6727 respectively.

Development documents D19–D21 concern reimbursement, expenditure and planned contribution with different amounts. They do not trigger a conflict because the monetary roles differ. D22/D23 have the same speaker, matter and claim kind but different amounts, so they are flagged as a potential numeric disagreement.

Five injected development-graph edits remove a payer, replace a decimal amount with text, use an unsupported currency, replace a recipient with an unrelated concept, and remove a claim speaker. The offline subset detects six findings because the text amount violates two constraints. Separately, standard pySHACL confirms the gold graph and detects a removed payer. Rule outputs with few or no statements can conform vacuously, so validation cannot replace recall.

## Follow-up

Prioritize negation and uncertainty controls in a new blind set. Review whether quotations entail each emitted property, test a shorter schema-only condition, and evaluate validation/repair separately. Multiple claims and independent gold annotation would make the next benchmark more informative.
