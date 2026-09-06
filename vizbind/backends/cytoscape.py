"""Cytoscape.js back-end adapter.

Emits Cytoscape.js ``elements`` plus a stylesheet. Unlike the DOT and Mermaid
adapters, this one targets an interactive, client-side rendering paradigm --
further evidence that the AVM is not tailored to a single engine.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from ..model import AVM

SHAPES = {
    "Circle": "ellipse",
    "Ellipse": "ellipse",
    "Rectangle": "rectangle",
    "RoundedRectangle": "round-rectangle",
    "Diamond": "diamond",
    "Hexagon": "hexagon",
    "Note": "round-rectangle",
    "Point": "ellipse",
}

ARROWS = {
    "NoArrow": "none",
    "OpenArrow": "vee",
    "FilledTriangle": "triangle",
    "HollowTriangle": "triangle-tee",
    "FilledDiamond": "diamond",
    "HollowDiamond": "diamond",
}

LINE_STYLES = {"Solid": "solid", "Dashed": "dashed", "Dotted": "dotted", "Bold": "solid"}

NAME = "cytoscape"
EXTENSION = "json"


def render(avm: AVM, indent: int = 2) -> str:
    elements: List[Dict[str, Any]] = []
    style: List[Dict[str, Any]] = []

    for node_id in sorted(avm.nodes):
        node = avm.nodes[node_id]
        label_parts = [node.label or node_id]
        for slot in sorted(node.compartments):
            label_parts.extend(node.compartments[slot])
        for decorator in node.decorators:
            label_parts.append(f"«{decorator.text}»")
        elements.append(
            {
                "group": "nodes",
                "data": {"id": node_id, "label": "\n".join(label_parts)},
            }
        )
        selector_style: Dict[str, Any] = {
            "shape": SHAPES.get(node.shape or "Rectangle", "rectangle"),
            "background-color": node.fill or "#FFFFFF",
            "label": "data(label)",
            "text-wrap": "wrap",
            "text-valign": "center",
        }
        if node.stroke:
            selector_style["border-color"] = node.stroke
            selector_style["border-width"] = 1
        if node.line_style and node.line_style != "Solid":
            selector_style["border-style"] = LINE_STYLES[node.line_style]
        if node.font_style == "Italic":
            selector_style["font-style"] = "italic"
        style.append({"selector": f'node[id = "{node_id}"]', "style": selector_style})

    for edge_id in sorted(avm.edges):
        edge = avm.edges[edge_id]
        label_parts = [p for p in [edge.label] if p]
        label_parts += [d.text for d in edge.decorators]
        elements.append(
            {
                "group": "edges",
                "data": {
                    "id": edge_id,
                    "source": edge.source,
                    "target": edge.target,
                    "label": " ".join(label_parts),
                },
            }
        )
        style.append(
            {
                "selector": f'edge[id = "{edge_id}"]',
                "style": {
                    "curve-style": "bezier",
                    "label": "data(label)",
                    "target-arrow-shape": ARROWS.get(edge.arrow_head or "FilledTriangle", "triangle"),
                    "line-style": LINE_STYLES.get(edge.line_style or "Solid", "solid"),
                    "line-color": edge.stroke or "#666666",
                    "font-size": 8,
                },
            }
        )

    return json.dumps({"elements": elements, "style": style}, indent=indent, ensure_ascii=False)
