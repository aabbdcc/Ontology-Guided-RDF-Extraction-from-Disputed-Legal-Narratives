"""Deliberately transparent rule baselines; no rule results are claimed as LLM results.

No ontology-guided LLM effect is measured by comparing these two regex parsers:
they have different handcrafted pattern coverage. They are pipeline smoke tests.
"""

from __future__ import annotations
import re
from datetime import datetime

DATE = "%d %B %Y"
AMT = r"[\d,]+"
QUAL = {
    "salary payment": "salary",
    "salary": "salary",
    "contractor fee": "contractor_fee",
    "capital contribution": "capital_contribution",
    "loan": "loan",
    "investment": "investment",
    "repayment": "repayment",
    "gift": "gift",
}


def payment(payer, recipient, amount, date):
    try:
        date = datetime.strptime(date, DATE).date().isoformat()
    except ValueError:
        return None
    return dict(
        type="payment",
        payer=payer,
        recipient=recipient,
        amount=int(amount.replace(",", "")),
        currency="EUR",
        date=date,
    )


def claim(actor, matter, qualification=None, kind=None, amount=None):
    out = dict(type="claim", asserted_by=actor, matter=matter.lower().replace(" ", "_"))
    if qualification:
        out["qualification"] = qualification
    if kind:
        out["kind"] = kind
    if amount is not None:
        out["amount"] = int(amount.replace(",", ""))
    return out


def naive_rule(text):
    m = re.fullmatch(
        rf"On (\d{{1,2}} \w+ \d{{4}}), (.*?) transferred EUR ({AMT}) to (.*?)\.", text
    )
    if m:
        d, p, a, r = m.groups()
        return payment(p, r, a, d)
    m = re.fullmatch(
        r"(.*?) claims that (?:transfer|payment|Transfer|Payment) (\w+) was (?:a |an )?(loan|investment|gift)\.",
        text,
    )
    if m:
        actor, key, qual = m.groups()
        word = "transfer" if "transfer" in text.lower() else "payment"
        return claim(actor, f"{word}_{key}", qualification=qual)
    return None


def attribution_aware_rule(text):
    if result := naive_rule(text):
        return result
    # Additional payment phrasings: purposefully domain-specific; no LLM here.
    patterns = [
        (rf"On (\d{{1,2}} \w+ \d{{4}}), (.*?) paid (.*?) EUR ({AMT})\.", "paid"),
        (
            rf"(.*?) received EUR ({AMT}) from (.*?) on (\d{{1,2}} \w+ \d{{4}})\.",
            "received",
        ),
        (
            rf"(?:A bank record shows that |A bank record documents that )(.*?) transferred EUR ({AMT}) to (.*?) on (\d{{1,2}} \w+ \d{{4}}),?(?: without specifying its legal nature)?\.",
            "bank",
        ),
        (rf"On (\d{{1,2}} \w+ \d{{4}}), (.*?) sent EUR ({AMT}) to (.*?)\.", "sent"),
    ]
    for pattern, kind in patterns:
        m = re.fullmatch(pattern, text)
        if not m:
            continue
        if kind in ("paid", "sent"):
            dt, p, r, a = (
                m.groups()
                if kind == "paid"
                else (m.group(1), m.group(2), m.group(4), m.group(3))
            )
        elif kind == "received":
            r, a, p, dt = m.groups()
        else:
            p, a, r, dt = m.groups()
        return payment(p, r, a, dt)
    # Attributed claim with explicit legal qualification.
    m = re.fullmatch(
        r"(.*?) (?:claims|maintains|alleges|asserts|argues) that (?:the )?(transfer|payment) (\w+) (?:was|represented) (?:a |an )?(.+?)\.",
        text,
        re.I,
    )
    if m:
        actor, word, key, phrase = m.groups()
        qual = QUAL.get(phrase.lower())
        if qual:
            return claim(actor, f"{word.lower()}_{key}", qualification=qual)
    # Numerical claims are never treated as observed payments.
    m = re.fullmatch(
        rf"(.*?) claims that .*? owes her EUR ({AMT}) as reimbursement for (Project \w+)\.",
        text,
    )
    if m:
        actor, amount, project = m.groups()
        return claim(actor, project, kind="claimed_reimbursement", amount=amount)
    m = re.fullmatch(
        rf"(.*?) states that she spent EUR ({AMT}) on (Project \w+)\.", text
    )
    if m:
        actor, amount, project = m.groups()
        return claim(actor, project, kind="total_expenditure", amount=amount)
    m = re.fullmatch(
        rf"(.*?) (?:says|states) that (?:her|his) planned contribution to (Project \w+) was EUR ({AMT})\.",
        text,
    )
    if m:
        actor, project, amount = m.groups()
        return claim(actor, project, kind="planned_contribution", amount=amount)
    return None
