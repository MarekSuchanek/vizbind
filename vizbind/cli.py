"""Command-line interface.

    python -m vizbind render --model examples/library.ttl \
        --notation notations/vowl-subset.ttl --backend graphviz --out out.dot
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from rdflib import Graph

from .backends import BACKENDS
from .engine import apply_notation
from .notation import load_notation


def _load_model(paths: List[str]) -> Graph:
    graph = Graph()
    for path in paths:
        graph.parse(path)
    return graph


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="vizbind", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    render = sub.add_parser("render", help="render a model through a notation")
    render.add_argument("--model", required=True, nargs="+", help="subject model (Turtle/RDF)")
    render.add_argument("--notation", required=True, help="notation document (Turtle)")
    render.add_argument("--backend", default="graphviz", choices=sorted(BACKENDS))
    render.add_argument("--out", help="output file (default: stdout)")
    render.add_argument("--rankdir", default="LR", help="Graphviz rank direction")
    render.add_argument("--quiet", action="store_true", help="suppress warnings")

    avm_cmd = sub.add_parser("avm", help="dump the Abstract Visual Model as JSON")
    avm_cmd.add_argument("--model", required=True, nargs="+")
    avm_cmd.add_argument("--notation", required=True)
    avm_cmd.add_argument("--out")
    avm_cmd.add_argument("--digest", action="store_true", help="print the AVM digest only")
    avm_cmd.add_argument("--quiet", action="store_true", help="suppress warnings")

    args = parser.parse_args(argv)

    model = _load_model(args.model)
    notation = load_notation(args.notation)
    avm = apply_notation(model, notation)

    if not getattr(args, "quiet", False):
        for warning in avm.warnings:
            print(f"warning: {warning}", file=sys.stderr)

    if args.command == "avm":
        output = avm.digest() if args.digest else avm.to_json()
    else:
        backend = BACKENDS[args.backend]
        if backend.NAME == "graphviz":
            output = backend.render(avm, rankdir=args.rankdir)
        else:
            output = backend.render(avm)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(output if output.endswith("\n") else output + "\n")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
