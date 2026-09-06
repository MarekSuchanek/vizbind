"""Loading a notation (a set of binding rules) from an RDF graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from rdflib import Graph, Namespace, RDF, URIRef
from rdflib.term import Node as RDFNode

VB = Namespace("https://w3id.org/vizbind#")

#: Attributes carried by a produced visual construct, keyed by the vb: predicate.
#: The value is the AVM attribute name.
STYLE_ATTRS: Dict[URIRef, str] = {
    VB.labelTemplate: "label",
    VB.nodeShape: "shape",
    VB.fill: "fill",
    VB.stroke: "stroke",
    VB.lineStyle: "line_style",
    VB.fontStyle: "font_style",
    VB.arrowHead: "arrow_head",
    VB.arrowTail: "arrow_tail",
}

#: Structural attributes: templates that must resolve, or the construct is skipped.
STRUCTURAL_ATTRS: Dict[URIRef, str] = {
    VB.id: "id",
    VB["from"]: "source",
    VB.to: "target",
    VB.owner: "owner",
    VB.slot: "slot",
    VB.target: "decorator_target",
    VB.entryTemplate: "entry",
    VB.textTemplate: "text",
    VB.position: "position",
}

CONSTRUCT_KINDS = {
    VB.Node: "node",
    VB.Edge: "edge",
    VB.Compartment: "compartment",
    VB.Decorator: "decorator",
}


class NotationError(ValueError):
    """Raised when a notation graph is malformed."""


@dataclass
class Produce:
    """The visual-construct template of a binding."""

    kind: str
    #: Template strings keyed by AVM attribute name.
    templates: Dict[str, str] = field(default_factory=dict)


@dataclass
class Binding:
    iri: str
    query: str
    produce: Produce
    priority: int = 0
    comment: Optional[str] = None


@dataclass
class Notation:
    iri: str
    label: Optional[str]
    bindings: List[Binding] = field(default_factory=list)
    #: Number of triples in the notation document (reported in the evaluation).
    triple_count: int = 0


def _shorten(term: RDFNode) -> str:
    """Render an enumerated style individual (e.g. vb:Circle) as a bare name."""
    text = str(term)
    return text.rsplit("#", 1)[-1] if "#" in text else text


def load_notation(path: str) -> Notation:
    """Load a notation from a Turtle document.

    ``vb:extends`` is resolved by loading the parent document relative to
    ``path`` and prepending its bindings, so that a child's higher-priority
    bindings can override inherited ones.
    """
    import os

    graph = Graph()
    graph.parse(path, format="turtle")

    notations = list(graph.subjects(RDF.type, VB.Notation))
    if len(notations) != 1:
        raise NotationError(f"{path}: expected exactly one vb:Notation, found {len(notations)}")
    notation_iri = notations[0]

    bindings: List[Binding] = []

    for parent in graph.objects(notation_iri, VB.extends):
        parent_path = os.path.join(os.path.dirname(path), os.path.basename(str(parent)))
        if os.path.exists(parent_path):
            bindings.extend(load_notation(parent_path).bindings)

    for binding_iri in graph.objects(notation_iri, VB.hasBinding):
        bindings.append(_load_binding(graph, binding_iri, path))

    # Deterministic order: priority descending, then IRI. The engine relies on
    # this for reproducible conflict resolution.
    bindings.sort(key=lambda b: (-b.priority, b.iri))

    label = graph.value(notation_iri, URIRef("http://www.w3.org/2000/01/rdf-schema#label"))
    return Notation(
        iri=str(notation_iri),
        label=str(label) if label else None,
        bindings=bindings,
        triple_count=len(graph),
    )


def _load_binding(graph: Graph, binding_iri: RDFNode, path: str) -> Binding:
    selection = graph.value(binding_iri, VB.select)
    if selection is None:
        raise NotationError(f"{path}: binding {binding_iri} has no vb:select")

    query = graph.value(selection, VB.query)
    if query is None:
        raise NotationError(
            f"{path}: selection of {binding_iri} has no vb:query "
            "(only vb:SparqlSelection is supported by this engine)"
        )

    produce_node = graph.value(binding_iri, VB.produce)
    if produce_node is None:
        raise NotationError(f"{path}: binding {binding_iri} has no vb:produce")

    kind = None
    for type_iri in graph.objects(produce_node, RDF.type):
        if type_iri in CONSTRUCT_KINDS:
            kind = CONSTRUCT_KINDS[type_iri]
            break
    if kind is None:
        raise NotationError(f"{path}: produce of {binding_iri} has no known vb: construct type")

    templates: Dict[str, str] = {}
    for predicate, attr in {**STRUCTURAL_ATTRS, **STYLE_ATTRS}.items():
        value = graph.value(produce_node, predicate)
        if value is None:
            continue
        # Object-valued style properties (shapes, arrow heads, ...) are enumerated
        # individuals, not templates; reduce them to their local name.
        templates[attr] = _shorten(value) if isinstance(value, URIRef) else str(value)

    priority = graph.value(binding_iri, VB.priority)
    comment = graph.value(binding_iri, URIRef("http://www.w3.org/2000/01/rdf-schema#comment"))

    return Binding(
        iri=str(binding_iri),
        query=str(query),
        produce=Produce(kind=kind, templates=templates),
        priority=int(priority) if priority is not None else 0,
        comment=str(comment) if comment else None,
    )
