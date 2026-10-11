"""Deterministic RDF-to-text baseline; no language model is used here."""

from rdflib.namespace import RDF
from .rdf_utils import EX


def display(node):
    return str(node).rsplit("/", 1)[-1].replace("_", " ")


def verbalize(graph, node):
    if (node, RDF.type, EX.Claim) in graph:
        actor = graph.value(node, EX.assertedBy)
        matter = graph.value(node, EX.concerns)
        if actor is None or matter is None:
            return None
        kval = graph.value(node, EX.hasQualification)
        kind = graph.value(node, EX.claimKind)
        amount = graph.value(node, EX.claimAmount)
        if kval:
            return f"{display(actor).capitalize()} claims that {display(matter)} was characterized as {display(kval)}."
        if kind and amount is not None:
            return f"{display(actor).capitalize()} asserts a {display(kind)} amount of EUR {amount} concerning {display(matter)}."
    if (node, RDF.type, EX.Payment) in graph:
        payer = graph.value(node, EX.payer)
        recipient = graph.value(node, EX.recipient)
        amount = graph.value(node, EX.amount)
        date = graph.value(node, EX.date)
        currency = graph.value(node, EX.currency)
        if any(value is None for value in (payer, recipient, amount, date, currency)):
            return None
        return f"The source reports that {display(payer)} transferred {currency} {amount} to {display(recipient)} on {date}."
    return None
