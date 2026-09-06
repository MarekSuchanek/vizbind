#!/usr/bin/env python3
"""Build the published vocabulary site into ``_site/``.

The site is what https://w3id.org/vizbind redirects to. GitHub Pages cannot do
content negotiation, so w3id's .htaccess (see ``w3id/.htaccess``) decides which
of these files to hand back, and every one of them has to exist at a stable path:

    _site/index.html        human-readable documentation (pyLODE)
    _site/vizbind.ttl       Turtle          (text/turtle)
    _site/vizbind.rdf       RDF/XML         (application/rdf+xml)
    _site/vizbind.jsonld    JSON-LD         (application/ld+json)
    _site/vizbind-vowl.svg  the vocabulary drawn by VizBind itself

Usage:  python scripts/build_docs.py [--skip-diagram]
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOCAB = ROOT / "vocab" / "vizbind.ttl"
SITE = ROOT / "_site"

SERIALIZATIONS = [
    ("vizbind.ttl", "turtle"),
    ("vizbind.rdf", "xml"),
    ("vizbind.jsonld", "json-ld"),
]


def run(cmd: list[str]) -> None:
    print("  $", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True)


def build_serializations() -> None:
    from rdflib import Graph

    g = Graph()
    g.parse(VOCAB, format="turtle")
    print(f"  vocabulary: {len(g)} triples")
    for name, fmt in SERIALIZATIONS:
        out = SITE / name
        if fmt == "turtle":
            # Copy rather than re-serialize: the hand-written file is the
            # canonical one, and rdflib would reorder and reformat it.
            shutil.copyfile(VOCAB, out)
        else:
            g.serialize(destination=out, format=fmt)
        print(f"  wrote {out.relative_to(ROOT)}")


def build_docs() -> None:
    run([sys.executable, "-m", "pylode", str(VOCAB),
         "-o", str(SITE / "index.html"), "-c", "true", "-p", "ontpub"])


def build_diagram() -> bool:
    """Render the VizBind vocabulary through VizBind's own VOWL notation.

    Dogfooding, and it gives the documentation page the picture pyLODE has no
    way to produce. Needs Graphviz on PATH; skipped (with a warning) if absent.
    """
    if shutil.which("dot") is None:
        print("  ! Graphviz 'dot' not found - skipping the diagram")
        return False
    dot_path = SITE / "vizbind-vowl.dot"
    run([sys.executable, "-m", "vizbind", "render",
         "--model", str(VOCAB),
         "--notation", str(ROOT / "notations" / "vowl-subset.ttl"),
         "--backend", "graphviz", "--out", str(dot_path)])
    run(["dot", "-Tsvg", str(dot_path), "-o", str(SITE / "vizbind-vowl.svg")])
    dot_path.unlink()
    return True


FIGURE = """
<div style="margin:2em 0;padding:1em;border:1px solid #ccc;border-radius:4px">
  <img src="vizbind-vowl.svg" alt="The VizBind vocabulary rendered as a VOWL-style diagram"
       style="width:100%;height:auto">
  <p style="font-size:.9em;color:#555;margin:.6em 0 0">
    The VizBind vocabulary, rendered through VizBind's own VOWL-subset notation.
    Generated from <code>vocab/vizbind.ttl</code> by the engine this vocabulary defines.
  </p>
</div>
"""


def inject_diagram() -> None:
    """Put the diagram just above the Classes section of the pyLODE page."""
    page = SITE / "index.html"
    html = page.read_text(encoding="utf-8")
    anchor = "<h2>Classes</h2>"
    if anchor not in html:
        # pyLODE's markup is not a stable contract, so fail loudly rather than
        # publishing a page that silently lost its diagram.
        raise SystemExit(
            "could not find the Classes heading in the pyLODE output; "
            "the markup changed and scripts/build_docs.py needs updating"
        )
    page.write_text(html.replace(anchor, FIGURE + anchor, 1), encoding="utf-8")
    print("  injected the diagram into index.html")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-diagram", action="store_true",
                    help="do not render the self-diagram (no Graphviz needed)")
    args = ap.parse_args()

    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()

    print("Serializations:")
    build_serializations()
    print("Documentation:")
    build_docs()
    if not args.skip_diagram and build_diagram():
        inject_diagram()

    print(f"\nSite built in {SITE.relative_to(ROOT)}/:")
    for f in sorted(SITE.iterdir()):
        print(f"  {f.name:22} {f.stat().st_size:>8,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
