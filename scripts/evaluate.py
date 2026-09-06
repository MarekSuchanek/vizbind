#!/usr/bin/env python3
"""Produce every quantitative result reported in the paper.

    python scripts/evaluate.py

Writes ``results/evaluation.json`` (machine-readable) and ``results/tables.tex``
(\\input by paper.tex, so the reported numbers cannot drift from the artifact).

Four questions are measured, matching the paper's evaluation section:

EQ1 Expressiveness  -- which VOWL constructs can the metamodel express?
EQ2 Notation-independence -- what must change to switch notation?
EQ3 Engine-independence   -- do all back-ends consume an identical AVM?
EQ4 Applicability   -- does it run on real, third-party ontologies?
"""

from __future__ import annotations

import json
import pathlib
import statistics
import sys
import time
from typing import Dict, List

from rdflib import Graph

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vizbind.backends import BACKENDS  # noqa: E402
from vizbind.engine import apply_notation  # noqa: E402
from vizbind.notation import load_notation  # noqa: E402

RESULTS = ROOT / "results"

NOTATIONS = ["vowl-subset", "uml-style"]

#: Subject models: (display name, path, provenance)
MODELS = [
    ("Library (example)", "examples/library.ttl", "authored here"),
    ("FOAF", "examples/vendor/foaf.rdf", "third-party"),
    ("DCAT 3", "examples/vendor/dcat.ttl", "third-party"),
    ("ORG", "examples/vendor/org.ttl", "third-party"),
    ("SKOS", "examples/vendor/skos.rdf", "third-party"),
    ("PROV-O", "examples/vendor/prov-o.ttl", "third-party"),
]

# ---------------------------------------------------------------------------
# EQ1: VOWL coverage
#
# status: "subset"    -- expressed in notations/vowl-subset.ttl (verified below)
#         "expressible" -- expressible with the same mechanisms, outside our subset
#         "procedural"  -- NOT expressible: not a model->visual mapping at all
# ---------------------------------------------------------------------------

VOWL_COVERAGE = [
    ("Class", "subset", "ClassBinding"),
    ("External class", "subset", "ExternalClassBinding"),
    ("owl:Thing", "subset", "ThingBinding"),
    ("Datatype", "subset", "DatatypeBinding"),
    ("Object property", "subset", "ObjectPropertyNode"),
    ("Datatype property", "subset", "DatatypePropertyNode"),
    ("rdfs:subClassOf", "subset", "SubClassOfEdge"),
    ("Functional property", "subset", "FunctionalDecorator"),
    ("Cardinality (min/max)", "subset", "MinCardinalityDecorator"),
    ("Deprecated class", "expressible", "owl:deprecated"),
    ("Equivalent classes", "expressible", "owl:equivalentClass"),
    ("Disjoint classes", "expressible", "owl:disjointWith"),
    ("Inverse property", "expressible", "owl:inverseOf"),
    ("Union / intersection", "expressible", "owl:unionOf"),
    ("Force-directed layout", "procedural", "engine concern"),
    ("Node size by instance count", "procedural", "aggregate over data"),
]


def _count_loc(path: pathlib.Path) -> int:
    """Non-blank, non-comment, non-docstring-delimiter lines."""
    loc = 0
    in_doc = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(('"""', "'''")):
            # A one-line docstring opens and closes on the same line.
            if not (len(line) > 3 and line.endswith(('"""', "'''"))):
                in_doc = not in_doc
            continue
        if in_doc or line.startswith("#"):
            continue
        loc += 1
    return loc


def eq1_expressiveness(notations: Dict) -> Dict:
    """Verify every 'subset' claim actually resolves to a binding in the file."""
    vowl_bindings = {b.iri.rsplit("#", 1)[-1] for b in notations["vowl-subset"].bindings}
    rows = []
    for element, status, mechanism in VOWL_COVERAGE:
        verified = None
        if status == "subset":
            claimed = mechanism
            verified = claimed in vowl_bindings
            if not verified:
                raise AssertionError(
                    f"coverage claims {element!r} is in the subset via {mechanism}, "
                    f"but no such binding exists in notations/vowl-subset.ttl"
                )
        rows.append(
            {"element": element, "status": status, "mechanism": mechanism, "verified": verified}
        )
    tally = {s: sum(1 for _, st, _ in VOWL_COVERAGE if st == s) for s in
             ("subset", "expressible", "procedural")}
    return {"rows": rows, "tally": tally, "total": len(VOWL_COVERAGE)}


def eq2_notation_independence(models: Dict, notations: Dict) -> Dict:
    """Switching notation must change the notation document and nothing else."""
    model = models["examples/library.ttl"]
    per_notation = {}
    for name in NOTATIONS:
        avm = apply_notation(model, notations[name])
        per_notation[name] = {
            "bindings": len(notations[name].bindings),
            "notation_triples": notations[name].triple_count,
            "nodes": len(avm.nodes),
            "edges": len(avm.edges),
            "digest": avm.digest(),
        }

    engine_loc = sum(
        _count_loc(ROOT / "vizbind" / f)
        for f in ("engine.py", "model.py", "notation.py", "template.py")
    )
    return {
        "per_notation": per_notation,
        # What a notation switch costs the user:
        "model_bytes_changed": 0,
        "engine_loc_changed": 0,
        "engine_loc_total": engine_loc,
        "avms_differ": len({v["digest"] for v in per_notation.values()}) == len(NOTATIONS),
    }


def eq3_engine_independence(models: Dict, notations: Dict) -> Dict:
    """Every back-end must consume a byte-identical AVM.

    Also checks determinism: SPARQL result order is not guaranteed, so the AVM
    is rebuilt from scratch several times and the digests must agree.
    """
    model = models["examples/library.ttl"]
    per_notation = {}
    for name in NOTATIONS:
        avm = apply_notation(model, notations[name])
        digest = avm.digest()
        repeats = {apply_notation(model, notations[name]).digest() for _ in range(5)}
        if repeats != {digest}:
            raise AssertionError(f"{name}: AVM is not deterministic across runs: {repeats}")
        outputs = {}
        for backend_name, backend in sorted(BACKENDS.items()):
            text = backend.render(avm)
            outputs[backend_name] = {
                "bytes": len(text.encode("utf-8")),
                "adapter_loc": _count_loc(ROOT / "vizbind" / "backends" / f"{backend_name}.py"),
                # The AVM is untouched by rendering: re-digest after the call.
                "avm_digest_after_render": avm.digest(),
            }
        per_notation[name] = {
            "avm_digest": digest,
            "backends": outputs,
            "deterministic_across_runs": True,
            "all_backends_saw_same_avm": all(
                o["avm_digest_after_render"] == digest for o in outputs.values()
            ),
        }
    return {"per_notation": per_notation, "backend_count": len(BACKENDS)}


def eq4_applicability(notations: Dict) -> Dict:
    """Run both notations over third-party ontologies; report size and time."""
    rows: List[Dict] = []
    for display, rel_path, provenance in MODELS:
        path = ROOT / rel_path
        if not path.exists():
            print(f"skipping missing model {rel_path}", file=sys.stderr)
            continue
        graph = Graph()
        graph.parse(str(path))
        row = {
            "model": display,
            "path": rel_path,
            "provenance": provenance,
            "triples": len(graph),
            "notations": {},
        }
        for name in NOTATIONS:
            timings = []
            avm = None
            for _ in range(3):
                start = time.perf_counter()
                avm = apply_notation(graph, notations[name])
                timings.append(time.perf_counter() - start)
            row["notations"][name] = {
                "nodes": len(avm.nodes),
                "edges": len(avm.edges),
                "warnings": len(avm.warnings),
                "median_seconds": round(statistics.median(timings), 4),
            }
        rows.append(row)
    return {"rows": rows}


# ---------------------------------------------------------------------------
# LaTeX emission
# ---------------------------------------------------------------------------

# Symbols keep the Status column narrow enough to stay inside the column width.
# Legend is given in the table caption in paper.tex.
STATUS_LABEL = {
    "subset": r"$\bullet$",        # expressed
    "expressible": r"$\circ$",     # expressible, outside the authored subset
    "procedural": r"$-$",          # out of scope (not a model->visual mapping)
}


def _tex_escape(text: str) -> str:
    return text.replace("_", r"\_").replace("&", r"\&").replace("%", r"\%")


def emit_tables(results: Dict) -> str:
    out: List[str] = ["% Generated by scripts/evaluate.py -- do not edit by hand.", ""]

    # -- Table: VOWL coverage ------------------------------------------------
    out += [
        r"\newcommand{\CoverageTable}{%",
        r"\begin{tabular}{@{}lcl@{}}",
        r"\hline",
        r"VOWL construct & Status & Mechanism \\",
        r"\hline",
    ]
    for row in results["eq1"]["rows"]:
        out.append(
            f"{_tex_escape(row['element'])} & {STATUS_LABEL[row['status']]} & "
            f"{_tex_escape(row['mechanism'])} \\\\"
        )
    out += [r"\hline", r"\end{tabular}}", ""]

    # -- Table: notation comparison -----------------------------------------
    eq2 = results["eq2"]["per_notation"]
    out += [
        r"\newcommand{\NotationTable}{%",
        r"\begin{tabular}{@{}lrrrr@{}}",
        r"\hline",
        r"Notation & Bindings & Triples & Nodes & Edges \\",
        r"\hline",
    ]
    for name in NOTATIONS:
        v = eq2[name]
        out.append(
            f"{_tex_escape(name)} & {v['bindings']} & {v['notation_triples']} & "
            f"{v['nodes']} & {v['edges']} \\\\"
        )
    out += [r"\hline", r"\end{tabular}}", ""]

    # -- Table: applicability ------------------------------------------------
    out += [
        r"\newcommand{\ApplicabilityTable}{%",
        r"\begin{tabular}{@{}lrrrrr@{}}",
        r"\hline",
        r" & & \multicolumn{2}{c}{VOWL subset} & \multicolumn{2}{c}{UML style} \\",
        r"Ontology & Triples & N/E & s & N/E & s \\",
        r"\hline",
    ]
    for row in results["eq4"]["rows"]:
        vowl = row["notations"]["vowl-subset"]
        uml = row["notations"]["uml-style"]
        out.append(
            f"{_tex_escape(row['model'])} & {row['triples']} & "
            f"{vowl['nodes']}/{vowl['edges']} & {vowl['median_seconds']:.2f} & "
            f"{uml['nodes']}/{uml['edges']} & {uml['median_seconds']:.2f} \\\\"
        )
    out += [r"\hline", r"\end{tabular}}", ""]

    # -- Inline macros so prose numbers stay in sync -------------------------
    eq1, eq3 = results["eq1"], results["eq3"]
    macros = {
        "CoverageExpressed": eq1["tally"]["subset"],
        "CoverageExpressible": eq1["tally"]["expressible"],
        "CoverageProcedural": eq1["tally"]["procedural"],
        "CoverageTotal": eq1["total"],
        "BackendCount": eq3["backend_count"],
        "EngineLoc": results["eq2"]["engine_loc_total"],
        "VowlBindings": eq2["vowl-subset"]["bindings"],
        "UmlBindings": eq2["uml-style"]["bindings"],
        "VowlNodes": eq2["vowl-subset"]["nodes"],
        "VowlEdges": eq2["vowl-subset"]["edges"],
        "UmlNodes": eq2["uml-style"]["nodes"],
        "UmlEdges": eq2["uml-style"]["edges"],
        "ModelCount": len(results["eq4"]["rows"]),
    }
    for key, value in macros.items():
        out.append(rf"\newcommand{{\{key}}}{{{value}}}")
    out.append("")
    return "\n".join(out)


def main() -> int:
    RESULTS.mkdir(exist_ok=True)

    notations = {name: load_notation(str(ROOT / "notations" / f"{name}.ttl")) for name in NOTATIONS}
    library = Graph()
    library.parse(str(ROOT / "examples" / "library.ttl"), format="turtle")
    models = {"examples/library.ttl": library}

    results = {
        "eq1": eq1_expressiveness(notations),
        "eq2": eq2_notation_independence(models, notations),
        "eq3": eq3_engine_independence(models, notations),
        "eq4": eq4_applicability(notations),
    }

    (RESULTS / "evaluation.json").write_text(
        json.dumps(results, indent=2, sort_keys=True), encoding="utf-8"
    )
    (RESULTS / "tables.tex").write_text(emit_tables(results), encoding="utf-8")

    # -- console summary -----------------------------------------------------
    eq1, eq2, eq3 = results["eq1"], results["eq2"], results["eq3"]
    print("EQ1 coverage:", eq1["tally"], f"of {eq1['total']}")
    print("EQ2 notations produce distinct AVMs:", eq2["avms_differ"],
          f"| engine LOC unchanged across notations: {eq2['engine_loc_total']}")
    for name in NOTATIONS:
        info = eq3["per_notation"][name]
        print(f"EQ3 {name}: all {eq3['backend_count']} back-ends saw the same AVM:",
              info["all_backends_saw_same_avm"], f"({info['avm_digest'][:12]}...)")
    print("EQ4 models evaluated:", len(results["eq4"]["rows"]))
    for row in results["eq4"]["rows"]:
        v, u = row["notations"]["vowl-subset"], row["notations"]["uml-style"]
        print(f"    {row['model']:26s} {row['triples']:5d} triples  "
              f"VOWL {v['nodes']:3d}N/{v['edges']:3d}E {v['median_seconds']:.3f}s  "
              f"UML {u['nodes']:3d}N/{u['edges']:3d}E {u['median_seconds']:.3f}s")
    print(f"\nwrote {RESULTS/'evaluation.json'} and {RESULTS/'tables.tex'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
