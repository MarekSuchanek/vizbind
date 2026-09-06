#!/usr/bin/env python3
"""Regenerate every figure used in the paper.

    python scripts/build_figures.py

Layout engine and rank direction are rendering concerns, not notation
concerns: the same AVM is handed to Graphviz in each case, and only the
layout invocation differs. This is why they live here and not in a notation.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

from rdflib import Graph

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vizbind.backends import cytoscape, graphviz, mermaid  # noqa: E402
from vizbind.engine import apply_notation  # noqa: E402
from vizbind.notation import load_notation  # noqa: E402

FIGURES = ROOT / "figures"

#: (name, notation, rankdir, layout engine, extra layout flags)
#:
#: The VOWL subset yields ~2.5x the nodes of the UML style on the same input, so
#: it is compressed to a wide aspect that stays legible when scaled to the
#: two-column width of the paper. This is a typesetting choice, not a notation
#: one: the DOT (and the AVM behind it) is identical either way.
JOBS = [
    ("library-vowl-subset", "vowl-subset", "LR", "dot", ["-Gratio=compress", "-Gsize=6.7,3.0"]),
    ("library-uml-style", "uml-style", "TB", "dot", []),
]


def build() -> int:
    FIGURES.mkdir(exist_ok=True)
    model = Graph()
    model.parse(ROOT / "examples" / "library.ttl", format="turtle")

    for name, notation_name, rankdir, engine, flags in JOBS:
        notation = load_notation(str(ROOT / "notations" / f"{notation_name}.ttl"))
        avm = apply_notation(model, notation)
        for warning in avm.warnings:
            print(f"warning [{name}]: {warning}", file=sys.stderr)

        dot_path = FIGURES / f"{name}.dot"
        dot_path.write_text(graphviz.render(avm, rankdir=rankdir), encoding="utf-8")

        pdf_path = FIGURES / f"{name}.pdf"
        subprocess.run(
            [engine, *flags, "-Tpdf", str(dot_path), "-o", str(pdf_path)],
            check=True,
        )
        print(f"{pdf_path.relative_to(ROOT)}  ({len(avm.nodes)} nodes, {len(avm.edges)} edges)")

        # The other back-ends are emitted from the identical AVM as evidence for
        # the engine-independence claim; they are not used in the figures.
        (FIGURES / f"{name}.mmd").write_text(mermaid.render(avm), encoding="utf-8")
        (FIGURES / f"{name}.cyto.json").write_text(cytoscape.render(avm), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(build())
