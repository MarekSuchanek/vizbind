"""The binding engine: subject model + notation -> Abstract Visual Model.

The engine implements the three stages of the metamodel in order:

1. **Selection** -- each binding's SPARQL query is evaluated over the subject
   model, yielding one variable assignment per result row.
2. **Mapping** -- each row instantiates the binding's visual-construct template.
3. **Styling & conflict resolution** -- attribute assignments from all bindings
   are reduced; the highest-priority assignment wins per attribute, and
   non-conflicting attributes from different bindings compose.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from rdflib import Graph, Namespace

from . import template
from .model import AVM, Decorator, Edge, Node
from .notation import Binding, Notation

#: Prefixes made available to every selection query, so that notation documents
#: stay readable and need not repeat boilerplate PREFIX blocks.
DEFAULT_PREFIXES = {
    "rdf": Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
    "rdfs": Namespace("http://www.w3.org/2000/01/rdf-schema#"),
    "owl": Namespace("http://www.w3.org/2002/07/owl#"),
    "xsd": Namespace("http://www.w3.org/2001/XMLSchema#"),
    "skos": Namespace("http://www.w3.org/2004/02/skos/core#"),
    "sh": Namespace("http://www.w3.org/ns/shacl#"),
    "dct": Namespace("http://purl.org/dc/terms/"),
}

STYLE_ATTR_NAMES = (
    "label",
    "shape",
    "fill",
    "stroke",
    "line_style",
    "font_style",
    "arrow_head",
    "arrow_tail",
)


@dataclass(frozen=True)
class _Assignment:
    priority: int
    binding_iri: str
    value: str


class Engine:
    def __init__(self, model: Graph, notation: Notation) -> None:
        self.model = model
        self.notation = notation
        self._ns = dict(DEFAULT_PREFIXES)
        # Prefixes declared by the subject model itself take part too, so a
        # notation may refer to domain vocabulary by prefix.
        for prefix, uri in model.namespaces():
            if prefix:
                self._ns.setdefault(prefix, Namespace(str(uri)))

    # -- stage 1: selection -------------------------------------------------

    def _select(self, binding: Binding) -> List[Dict[str, Optional[str]]]:
        result = self.model.query(binding.query, initNs=self._ns)
        rows: List[Dict[str, Optional[str]]] = []
        for row in result:
            assignment: Dict[str, Optional[str]] = {}
            for var in result.vars or []:
                value = row[var]
                assignment[str(var)] = None if value is None else str(value)
            rows.append(assignment)
        return rows

    # -- stages 2 & 3 -------------------------------------------------------

    def run(self) -> AVM:
        avm = AVM()

        # (kind, id, attr) -> assignments, reduced after all bindings are applied.
        style: Dict[Tuple[str, str, str], List[_Assignment]] = defaultdict(list)
        node_ids: List[str] = []
        edges: Dict[str, Tuple[str, str]] = {}
        compartments: List[Tuple[str, str, str]] = []      # owner, slot, entry
        decorators: List[Tuple[str, str, str]] = []        # target, text, position

        for binding in self.notation.bindings:
            produce = binding.produce
            for row in self._select(binding):

                def resolve(attr: str) -> Optional[str]:
                    text = produce.templates.get(attr)
                    return None if text is None else template.render(text, row)

                if produce.kind == "node":
                    node_id = resolve("id")
                    if node_id is None:
                        continue
                    if node_id not in node_ids:
                        node_ids.append(node_id)
                    self._collect_style(style, "node", node_id, produce, row, binding)

                elif produce.kind == "edge":
                    source, target = resolve("source"), resolve("target")
                    if source is None or target is None:
                        continue
                    edge_id = resolve("id") or f"{source}->{target}"
                    edges.setdefault(edge_id, (source, target))
                    self._collect_style(style, "edge", edge_id, produce, row, binding)

                elif produce.kind == "compartment":
                    owner, slot, entry = resolve("owner"), resolve("slot"), resolve("entry")
                    if owner is None or slot is None or entry is None:
                        continue
                    compartments.append((owner, slot, entry))

                elif produce.kind == "decorator":
                    target_id, text = resolve("decorator_target"), resolve("text")
                    if target_id is None or text is None:
                        continue
                    decorators.append((target_id, text, resolve("position") or "Middle"))

        for node_id in node_ids:
            avm.nodes[node_id] = Node(id=node_id, **self._reduce(style, "node", node_id, avm))
        for edge_id, (source, target) in edges.items():
            avm.edges[edge_id] = Edge(
                id=edge_id, source=source, target=target,
                **self._reduce(style, "edge", edge_id, avm),
            )

        self._attach_compartments(avm, compartments)
        self._attach_decorators(avm, decorators)
        self._check_dangling_edges(avm)
        return avm

    def _collect_style(
        self,
        style: Dict[Tuple[str, str, str], List[_Assignment]],
        kind: str,
        construct_id: str,
        produce,
        row: Dict[str, Optional[str]],
        binding: Binding,
    ) -> None:
        for attr in STYLE_ATTR_NAMES:
            text = produce.templates.get(attr)
            if text is None:
                continue
            value = template.render(text, row)
            if value is None:
                continue
            style[(kind, construct_id, attr)].append(
                _Assignment(binding.priority, binding.iri, value)
            )

    def _reduce(
        self,
        style: Dict[Tuple[str, str, str], List[_Assignment]],
        kind: str,
        construct_id: str,
        avm: AVM,
    ) -> Dict[str, str]:
        """Pick the winning value per attribute; record ties as warnings."""
        resolved: Dict[str, str] = {}
        for attr in STYLE_ATTR_NAMES:
            candidates = style.get((kind, construct_id, attr))
            if not candidates:
                continue
            top = max(c.priority for c in candidates)
            # Sort on the value as well as the binding: two *rows* of the same
            # binding can assign the same attribute (e.g. a label available in
            # several languages), and SPARQL result order is not guaranteed, so
            # binding IRI alone would not make the outcome reproducible.
            winners = sorted(
                (c for c in candidates if c.priority == top),
                key=lambda c: (c.binding_iri, c.value),
            )
            distinct = {c.value for c in winners}
            if len(distinct) > 1:
                sources = sorted({c.binding_iri for c in winners})
                avm.warnings.append(
                    f"tie on {kind} {construct_id!r} attribute {attr!r} at priority {top} "
                    f"between {len(distinct)} values from {sources}; "
                    f"chose {winners[0].value!r} deterministically"
                )
            resolved[attr] = winners[0].value
        return resolved

    def _attach_compartments(self, avm: AVM, entries: List[Tuple[str, str, str]]) -> None:
        for owner, slot, entry in entries:
            node = avm.nodes.get(owner)
            if node is None:
                avm.warnings.append(
                    f"compartment entry {entry!r} skipped: owner node {owner!r} not produced"
                )
                continue
            node.compartments.setdefault(slot, []).append(entry)
        for node in avm.nodes.values():
            for slot in node.compartments:
                node.compartments[slot].sort()

    def _attach_decorators(self, avm: AVM, items: List[Tuple[str, str, str]]) -> None:
        for target_id, text, position in items:
            holder = avm.nodes.get(target_id) or avm.edges.get(target_id)
            if holder is None:
                avm.warnings.append(
                    f"decorator {text!r} skipped: target {target_id!r} not produced"
                )
                continue
            holder.decorators.append(Decorator(text=text, position=position))
        for holder in list(avm.nodes.values()) + list(avm.edges.values()):
            holder.decorators.sort(key=lambda d: (d.position, d.text))

    def _check_dangling_edges(self, avm: AVM) -> None:
        for edge in list(avm.edges.values()):
            for end, node_id in (("from", edge.source), ("to", edge.target)):
                if node_id not in avm.nodes:
                    avm.warnings.append(
                        f"edge {edge.id!r} has dangling {end} endpoint {node_id!r}; "
                        "the notation produced no node for it"
                    )


def apply_notation(model: Graph, notation: Notation) -> AVM:
    """Convenience wrapper: apply ``notation`` to ``model``, returning the AVM."""
    return Engine(model, notation).run()
