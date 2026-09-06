"""The Abstract Visual Model (AVM).

The AVM is the engine-independent intermediate representation produced by
applying a notation to a subject model. Back-end adapters consume *only* the
AVM, which is what makes a notation portable across rendering engines.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Decorator:
    text: str
    position: str = "Middle"

    def to_dict(self) -> Dict[str, Any]:
        return {"text": self.text, "position": self.position}


@dataclass
class Node:
    id: str
    label: Optional[str] = None
    shape: Optional[str] = None
    fill: Optional[str] = None
    stroke: Optional[str] = None
    line_style: Optional[str] = None
    font_style: Optional[str] = None
    compartments: Dict[str, List[str]] = field(default_factory=dict)
    decorators: List[Decorator] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "shape": self.shape,
            "fill": self.fill,
            "stroke": self.stroke,
            "lineStyle": self.line_style,
            "fontStyle": self.font_style,
            "compartments": {k: list(v) for k, v in sorted(self.compartments.items())},
            "decorators": [d.to_dict() for d in self.decorators],
        }


@dataclass
class Edge:
    id: str
    source: str
    target: str
    label: Optional[str] = None
    stroke: Optional[str] = None
    line_style: Optional[str] = None
    font_style: Optional[str] = None
    arrow_head: Optional[str] = None
    arrow_tail: Optional[str] = None
    decorators: List[Decorator] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from": self.source,
            "to": self.target,
            "label": self.label,
            "stroke": self.stroke,
            "lineStyle": self.line_style,
            "fontStyle": self.font_style,
            "arrowHead": self.arrow_head,
            "arrowTail": self.arrow_tail,
            "decorators": [d.to_dict() for d in self.decorators],
        }


@dataclass
class AVM:
    nodes: Dict[str, Node] = field(default_factory=dict)
    edges: Dict[str, Edge] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [self.nodes[k].to_dict() for k in sorted(self.nodes)],
            "edges": [self.edges[k].to_dict() for k in sorted(self.edges)],
        }

    def to_json(self, indent: Optional[int] = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True, ensure_ascii=False)

    def digest(self) -> str:
        """Stable SHA-256 over the canonical AVM.

        Used to demonstrate that every back-end consumes an identical AVM.
        """
        canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
