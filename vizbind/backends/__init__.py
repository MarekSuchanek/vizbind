"""Back-end adapters. Each consumes only the AVM and emits a concrete format."""

from . import cytoscape, graphviz, mermaid

BACKENDS = {
    graphviz.NAME: graphviz,
    mermaid.NAME: mermaid,
    cytoscape.NAME: cytoscape,
}

__all__ = ["BACKENDS", "graphviz", "mermaid", "cytoscape"]
