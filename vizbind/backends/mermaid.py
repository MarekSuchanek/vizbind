"""Mermaid back-end adapter.

Mermaid is a text-based diagramming engine with a rendering model quite unlike
Graphviz's: it has no record shapes and a fixed set of node forms. It is
included precisely because it stresses the engine-agnostic claim -- the same AVM
must survive translation to a renderer with different primitives.
"""

from __future__ import annotations

from typing import Dict, List

from ..model import AVM

#: Mermaid node delimiters per abstract shape.
SHAPE_DELIMS: Dict[str, tuple] = {
    "Circle": ("((", "))"),
    "Ellipse": ("([", "])"),
    "Rectangle": ("[", "]"),
    "RoundedRectangle": ("(", ")"),
    "Diamond": ("{", "}"),
    "Hexagon": ("{{", "}}"),
    "Note": ("[/", "/]"),
    "Point": ("((", "))"),
}

ARROWS = {
    "NoArrow": "---",
    "OpenArrow": "-->",
    "FilledTriangle": "-->",
    "HollowTriangle": "-.->",
    "FilledDiamond": "-->",
    "HollowDiamond": "-->",
}

NAME = "mermaid"
EXTENSION = "mmd"


def _safe_id(raw: str, table: Dict[str, str]) -> str:
    """Mermaid identifiers cannot contain IRI punctuation; assign stable aliases."""
    if raw not in table:
        table[raw] = f"n{len(table)}"
    return table[raw]


def _escape(text: str) -> str:
    return text.replace('"', "&quot;").replace("\n", " ")


def render(avm: AVM) -> str:
    ids: Dict[str, str] = {}
    lines: List[str] = ["graph LR"]

    for node_id in sorted(avm.nodes):
        node = avm.nodes[node_id]
        open_delim, close_delim = SHAPE_DELIMS.get(node.shape or "Rectangle", ("[", "]"))
        label_parts = [node.label or node_id]
        # Mermaid has no compartments: fold them into the label, which is the
        # honest degradation for an engine lacking the primitive.
        for slot in sorted(node.compartments):
            for entry in node.compartments[slot]:
                label_parts.append(entry)
        for decorator in node.decorators:
            label_parts.append(f"«{decorator.text}»")
        label = _escape("<br/>".join(label_parts))
        alias = _safe_id(node_id, ids)
        lines.append(f'  {alias}{open_delim}"{label}"{close_delim}')
        if node.fill:
            lines.append(f"  style {alias} fill:{node.fill}")

    for edge_id in sorted(avm.edges):
        edge = avm.edges[edge_id]
        source = _safe_id(edge.source, ids)
        target = _safe_id(edge.target, ids)
        arrow = ARROWS.get(edge.arrow_head or "FilledTriangle", "-->")
        label_parts = [p for p in [edge.label] if p]
        label_parts += [d.text for d in edge.decorators]
        label = _escape(" ".join(label_parts))
        if label:
            lines.append(f'  {source} {arrow}|"{label}"| {target}')
        else:
            lines.append(f"  {source} {arrow} {target}")

    return "\n".join(lines) + "\n"
