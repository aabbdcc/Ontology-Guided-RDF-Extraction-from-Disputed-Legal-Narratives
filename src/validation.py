"""SHACL validation, with labeled offline Core-subset fallback.

For authoritative SHACL benchmarking install and run pySHACL.
Fallback implements ONLY used: targetClass, path, min/maxCount, datatype,
class, minInclusive, sh:in, and RDFS subclass checking. No SPARQL shapes.
"""

from __future__ import annotations
from decimal import Decimal, InvalidOperation
from rdflib import Graph, Literal
from rdflib.collection import Collection
from rdflib.namespace import RDF, RDFS, SH, XSD

try:
    from pyshacl import validate as pyshacl_validate
except ImportError:
    pyshacl_validate = None


def validate_graph(graph: Graph, shapes: Graph, ontology: Graph, engine="auto"):
    if engine not in {"auto", "pyshacl", "offline_subset"}:
        raise ValueError("Unknown engine")
    if engine == "pyshacl" and pyshacl_validate is None:
        raise RuntimeError("pySHACL unavailable. Install requirements first.")
    if pyshacl_validate is not None and engine != "offline_subset":
        conforms, report_graph, report_text = pyshacl_validate(
            data_graph=graph,
            shacl_graph=shapes,
            ont_graph=ontology,
            inference="rdfs",
            abort_on_first=False,
            allow_infos=False,
            allow_warnings=False,
        )
        violations = sum(
            1 for _ in report_graph.subjects(RDF.type, SH.ValidationResult)
        )
        return {
            "conforms": bool(conforms),
            "violations": violations,
            "engine": "pyshacl",
            "details": report_text,
        }
    return _validate_offline(graph, shapes, ontology)


def _is_class(g, onto, obj, expected):
    if (obj, RDF.type, expected) in g:
        return True
    types = list(g.objects(obj, RDF.type))
    for t in types:
        frontier = [t]
        visited = set()
        while frontier:
            current = frontier.pop()
            if current == expected:
                return True
            if current in visited:
                continue
            visited.add(current)
            frontier.extend(onto.objects(current, RDFS.subClassOf))
            frontier.extend(g.objects(current, RDFS.subClassOf))
    return False


def _validate_offline(g, shapes, onto):
    errors = []
    for shape in shapes.subjects(RDF.type, SH.NodeShape):
        for target in shapes.objects(shape, SH.targetClass):
            for subj in g.subjects(RDF.type, target):
                for ps in shapes.objects(shape, SH.property):
                    path = shapes.value(ps, SH.path)
                    vals = list(g.objects(subj, path))
                    mn = shapes.value(ps, SH.minCount)
                    mx = shapes.value(ps, SH.maxCount)
                    if mn is not None and len(vals) < int(mn):
                        errors.append((subj, path, "minCount"))
                    if mx is not None and len(vals) > int(mx):
                        errors.append((subj, path, "maxCount"))
                    dtype = shapes.value(ps, SH.datatype)
                    klass = shapes.value(ps, SH["class"])
                    minval = shapes.value(ps, SH.minInclusive)
                    enum = shapes.value(ps, SH["in"])
                    accepted = (
                        set(Collection(shapes, enum)) if enum is not None else None
                    )
                    for v in vals:
                        if dtype is not None and (
                            not isinstance(v, Literal)
                            or v.datatype != dtype
                            and not (dtype == XSD.string and v.datatype is None)
                        ):
                            errors.append((subj, path, "datatype"))
                        if klass is not None and not _is_class(g, onto, v, klass):
                            errors.append((subj, path, "class"))
                        if accepted is not None and v not in accepted:
                            errors.append((subj, path, "in"))
                        if minval is not None:
                            try:
                                if Decimal(str(v)) < Decimal(str(minval)):
                                    errors.append((subj, path, "minInclusive"))
                            except (InvalidOperation, ValueError):
                                errors.append((subj, path, "minInclusive"))
    return {
        "conforms": not errors,
        "violations": len(errors),
        "engine": "offline_core_subset",
        "details": [
            {"node": str(s), "property": str(p), "constraint": str(c)}
            for s, p, c in errors
        ],
    }
