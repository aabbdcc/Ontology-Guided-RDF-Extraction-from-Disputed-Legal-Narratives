"""Rebuild author-constructed challenge corpus; NEVER used to tune regex extractors.

The challenge set contains 8 post-hoc adversarial paraphrases from v0.1, eight
in-template positive controls, and eight abstention/uncertainty controls. It is
not a random sample of production data or a statistically blind test set.
"""

import json
from src.rdf_utils import ROOT, load_jsonl


def main():
    old = load_jsonl(ROOT / "data/robustness_probes.jsonl")
    positive = [
        (
            "H09",
            "On 15 February 2025, Lucy transferred EUR 2,700 to Company J.",
            dict(
                type="payment",
                payer="Lucy",
                recipient="Company J",
                amount=2700,
                currency="EUR",
                date="2025-02-15",
            ),
        ),
        (
            "H10",
            "On 18 February 2025, Marcel paid Company K EUR 3,600.",
            dict(
                type="payment",
                payer="Marcel",
                recipient="Company K",
                amount=3600,
                currency="EUR",
                date="2025-02-18",
            ),
        ),
        (
            "H11",
            "Company L received EUR 9,100 from Nia on 3 March 2025.",
            dict(
                type="payment",
                payer="Nia",
                recipient="Company L",
                amount=9100,
                currency="EUR",
                date="2025-03-03",
            ),
        ),
        (
            "H12",
            "A bank record shows that Oliver transferred EUR 7,700 to Company M on 4 April 2025.",
            dict(
                type="payment",
                payer="Oliver",
                recipient="Company M",
                amount=7700,
                currency="EUR",
                date="2025-04-04",
            ),
        ),
        (
            "H13",
            "Pia claims that transfer V was a loan.",
            dict(
                type="claim",
                asserted_by="Pia",
                matter="transfer_v",
                qualification="loan",
            ),
        ),
        (
            "H14",
            "Company N maintains that transfer W was an investment.",
            dict(
                type="claim",
                asserted_by="Company N",
                matter="transfer_w",
                qualification="investment",
            ),
        ),
        (
            "H15",
            "Quinn alleges that payment Z represented salary.",
            dict(
                type="claim",
                asserted_by="Quinn",
                matter="payment_z",
                qualification="salary",
            ),
        ),
        (
            "H16",
            "Rita states that she spent EUR 17,000 on Project T.",
            dict(
                type="claim",
                asserted_by="Rita",
                matter="project_t",
                kind="total_expenditure",
                amount=17000,
            ),
        ),
    ]
    controls = [
        ("H17", "Alice denies that Transfer V was a loan."),
        ("H18", "The email asks whether EUR 3,000 might have been a loan."),
        (
            "H19",
            "The parties discussed a possible transfer of EUR 11,000, but the payment never occurred.",
        ),
        (
            "H20",
            "A draft memo lists EUR 30,000 and EUR 70,000 without identifying their roles.",
        ),
        (
            "H21",
            "The unsigned contract described a potential investment but no completed transaction.",
        ),
        (
            "H22",
            "One participant said they were unsure whether the receipt was a salary or a gift.",
        ),
        (
            "H23",
            "The court has not decided whether Transfer X represented salary or repayment.",
        ),
        (
            "H24",
            "The file contains an invoice, but no text identifies who paid it or when.",
        ),
    ]
    corpus = [{**r, "group": "paraphrase_out_of_template"} for r in old]
    corpus += [
        dict(
            id=id,
            category="challenge",
            group="in_template_positive",
            scenario=id.lower(),
            text=text,
            annotation=ann,
        )
        for id, text, ann in positive
    ]
    corpus += [
        dict(
            id=id,
            category="challenge",
            group="abstention_controls",
            scenario=id.lower(),
            text=text,
            annotation={"type": "none"},
        )
        for id, text in controls
    ]
    path = ROOT / "data/challenge_24.jsonl"
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in corpus),
        encoding="utf-8",
    )
    print("wrote", path, "n", len(corpus))


if __name__ == "__main__":
    main()
