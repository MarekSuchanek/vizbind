"""Graphviz (DOT) back-end adapter.

Resolves the engine-agnostic style vocabulary of the AVM into DOT attributes.
The adapter reads *only* the AVM -- it never sees the notation or the model.
"""

from __future__ import annotations

from typing import List, Optional

from ..model import AVM, Edge, Node

SHAPES = {
    "Circle": "circle",
    "Ellipse": "ellipse",
    "Rectangle": "box",
    "RoundedRectangle": "box",
    "Diamond": "diamond",
    "Hexagon": "hexagon",
    "Note": "note",
    "Point": "point",
}

ARROWS = {
    "NoArrow": "none",
    "OpenArrow": "vee",
    "FilledTriangle": "normal",
    "HollowTriangle": "empty",
    "FilledDiamond": "diamond",
    "HollowDiamond": "odiamond",
}

LINE_STYLES = {"Solid": "solid", "Dashed": "dashed", "Dotted": "dotted", "Bold": "bold"}

NAME = "graphviz"
EXTENSION = "dot"


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _escape_record(text: str) -> str:
    out = _escape(text)
    for char in "{}|<>":
        out = out.replace(char, "\\" + char)
    return out


def _node_id(node_id: str) -> str:
    return f'"{_escape(node_id)}"'


def _node_label(node: Node, rankdir: str = "LR") -> str:
    """Build a DOT label; nodes with compartments become record labels.

    Each line is escaped before the DOT newline separator is inserted, so that
    the separator itself survives escaping.

    Graphviz lays record fields out along the rank direction, so the brace
    nesting needed to stack compartments vertically depends on ``rankdir``:
    under TB a single ``{}`` stacks, under LR it takes a second one.
    """
    lines = [f"«{d.text}»" for d in node.decorators] + [node.label or ""]

    if not node.compartments:
        return 'label="' + "\\n".join(_escape(line) for line in lines) + '"'

    sections: List[str] = ["\\n".join(_escape_record(line) for line in lines)]
    for slot in sorted(node.compartments):
        entries = node.compartments[slot]
        if not entries:
            continue
        sections.append("".join(f"{_escape_record(e)}\\l" for e in entries))
    body = "{" + "|".join(sections) + "}"
    if rankdir.upper() in ("LR", "RL"):
        body = "{" + body + "}"
    return f'shape=record, label="{body}"'


def _node_attrs(node: Node, rankdir: str = "LR") -> str:
    attrs: List[str] = []
    if node.compartments:
        attrs.append(_node_label(node, rankdir))  # includes shape=record
    else:
        attrs.append(_node_label(node, rankdir))
        attrs.append(f'shape={SHAPES.get(node.shape or "Rectangle", "box")}')
    styles = ["filled"]
    if node.line_style and node.line_style != "Solid":
        styles.append(LINE_STYLES[node.line_style])
    attrs.append(f'style="{",".join(styles)}"')
    attrs.append(f'fillcolor="{node.fill or "#FFFFFF"}"')
    if node.stroke:
        attrs.append(f'color="{node.stroke}"')
    if node.font_style == "Italic":
        attrs.append('fontname="Times-Italic"')
    elif node.font_style == "BoldFont":
        attrs.append('fontname="Times-Bold"')
    return ", ".join(attrs)


def _edge_attrs(edge: Edge) -> str:
    attrs: List[str] = []
    if edge.label:
        attrs.append(f'label="{_escape(edge.label)}"')
    attrs.append(f'arrowhead={ARROWS.get(edge.arrow_head or "FilledTriangle", "normal")}')
    if edge.arrow_tail and edge.arrow_tail != "NoArrow":
        attrs.append(f'dir=both, arrowtail={ARROWS[edge.arrow_tail]}')
    if edge.line_style and edge.line_style != "Solid":
        attrs.append(f'style={LINE_STYLES[edge.line_style]}')
    if edge.stroke:
        attrs.append(f'color="{edge.stroke}"')
    for decorator in edge.decorators:
        if decorator.position == "AtTarget":
            attrs.append(f'headlabel="{_escape(decorator.text)}"')
        elif decorator.position == "AtSource":
            attrs.append(f'taillabel="{_escape(decorator.text)}"')
        else:
            attrs.append(f'xlabel="{_escape(decorator.text)}"')
    return ", ".join(attrs)


def render(avm: AVM, rankdir: str = "LR", title: Optional[str] = None) -> str:
    lines: List[str] = ["digraph G {"]
    lines.append(f'  rankdir={rankdir};')
    lines.append('  graph [fontname="Times", splines=true, overlap=false, nodesep=0.35];')
    lines.append('  node  [fontname="Times", fontsize=10];')
    lines.append('  edge  [fontname="Times", fontsize=9, labeldistance=1.6];')
    if title:
        lines.append(f'  label="{_escape(title)}"; labelloc=t;')
    for node_id in sorted(avm.nodes):
        lines.append(f"  {_node_id(node_id)} [{_node_attrs(avm.nodes[node_id], rankdir)}];")
    for edge_id in sorted(avm.edges):
        edge = avm.edges[edge_id]
        lines.append(
            f"  {_node_id(edge.source)} -> {_node_id(edge.target)} [{_edge_attrs(edge)}];"
        )
    lines.append("}")
    return "\n".join(lines) + "\n"
