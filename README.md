# VizBind — Declarative, Notation-Independent Visualization of RDFS/OWL

[![CI](https://github.com/MarekSuchanek/vizbind/actions/workflows/ci.yml/badge.svg)](https://github.com/MarekSuchanek/vizbind/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Vocabulary: CC BY 4.0](https://img.shields.io/badge/Vocabulary-CC_BY_4.0-lightgrey.svg)](LICENSE-CC-BY-4.0.md)

<!-- TODO(Marek): after the first Zenodo-archived release, add the concept-DOI badge:
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
-->

Research artifact accompanying the KEOD 2026 paper *Binding Ontologies to Notation: A
Declarative RDF Vocabulary for Notation-Independent Visualisation of RDFS/OWL Models*.

> **Status: proof of concept (0.1.0).** The contribution is the *vocabulary*; the engine
> exists to show that the vocabulary is executable and engine-independent, not as a
> production tool. While the version stays below 1.0, the vocabulary and the engine API
> may change between releases. A fuller treatment is planned.

**Claim.** Existing OWL visualization tools (VOWL, Graffoo, OWLGrEd) each hard-code one
visual language. VizBind expresses the model→visual mapping *as RDF data*, so a notation
becomes a shareable configuration rather than tool code. The same ontology renders into
different notations by swapping one file; the same notation renders through different
engines.

## Layout

| Path | What it is |
|---|---|
| `vocab/vizbind.ttl` | **The contribution**: the binding metamodel (OWL ontology) |
| `notations/vowl-subset.ttl` | A subset of VOWL expressed as bindings |
| `notations/uml-style.ttl` | A contrasting UML-class-style notation |
| `examples/library.ttl` | Running example ontology |
| `examples/vendor/` | Third-party ontologies (FOAF, DCAT, ORG, SKOS, PROV-O) for evaluation |
| `vizbind/` | Reference engine (Python) |
| `vizbind/backends/` | Graphviz, Mermaid, Cytoscape.js adapters |
| `scripts/build_figures.py` | Regenerates the paper's figures |
| `scripts/evaluate.py` | Regenerates every number the paper reports |
| `scripts/build_docs.py` | Builds the published vocabulary site into `_site/` |
| `tests/` | Test suite (27 tests) |
| `w3id/.htaccess` | The w3id.org redirect rules (to be PR'd to perma-id/w3id.org) |

## Setup

```bash
python3 -m venv .venv
./.venv/bin/pip install -e ".[dev]"
brew install graphviz          # or: apt install graphviz
```

## Use

```bash
# Render the running example as VOWL, then as UML — only --notation changes.
./.venv/bin/python -m vizbind render \
    --model examples/library.ttl --notation notations/vowl-subset.ttl \
    --backend graphviz --out /tmp/vowl.dot
dot -Tpdf /tmp/vowl.dot -o /tmp/vowl.pdf

./.venv/bin/python -m vizbind render \
    --model examples/library.ttl --notation notations/uml-style.ttl \
    --backend graphviz --rankdir TB --out /tmp/uml.dot

# Same notation, different engines.
./.venv/bin/python -m vizbind render --model examples/library.ttl \
    --notation notations/uml-style.ttl --backend mermaid
./.venv/bin/python -m vizbind render --model examples/library.ttl \
    --notation notations/uml-style.ttl --backend cytoscape

# Inspect the engine-independent intermediate representation.
./.venv/bin/python -m vizbind avm --model examples/library.ttl \
    --notation notations/vowl-subset.ttl --digest
```

## How a binding works

A notation is a set of rules, each with three separated concerns:

```turtle
vowl:ClassBinding a vb:Binding ;
    vb:priority 10 ;
    vb:select  [ a vb:SparqlSelection ;                    # 1. SELECTION
                 vb:query "SELECT ?c WHERE { ?c a owl:Class . FILTER(isIRI(?c)) }" ] ;
    vb:produce [ a vb:Node ;                               # 2. MAPPING
                 vb:id "{?c}" ;
                 vb:labelTemplate "{coalesce(?label, localName(?c))}" ;
                 vb:nodeShape vb:Circle ;                  # 3. STYLING
                 vb:fill "#AACCFF" ] .
```

Selection is SPARQL over the subject model. Mapping targets an abstract construct
(`vb:Node`, `vb:Edge`, `vb:Compartment`, `vb:Decorator`). Styling is engine-agnostic and
resolved per back-end at render time. When bindings collide, the highest `vb:priority`
wins per attribute and non-conflicting attributes compose.

## Reproducing the paper's results

```bash
./.venv/bin/python -m pytest -q                 # 27 tests
./.venv/bin/python scripts/build_figures.py     # -> figures/*.pdf
./.venv/bin/python scripts/evaluate.py          # -> results/evaluation.json, results/tables.tex
```

`results/tables.tex` is `\input` by the paper's LaTeX source, so every reported number is
generated from this artifact and cannot drift from it. CI re-runs both scripts on every
push and fails if the committed `results/` and `figures/` differ from a fresh run.

## Namespace and published documentation

The vocabulary namespace is **`https://w3id.org/vizbind#`** — a permanent identifier, so
terms such as `vb:Binding` are `https://w3id.org/vizbind#Binding`.

Because it is a *hash* namespace, clients strip the fragment and only ever request
`https://w3id.org/vizbind`, which content-negotiates:

| You ask for | You get |
|---|---|
| `text/html` (a browser) | the rendered documentation |
| `text/turtle` | `vizbind.ttl` |
| `application/rdf+xml` | `vizbind.rdf` |
| `application/ld+json` | `vizbind.jsonld` |

The negotiation happens at w3id, not on GitHub Pages — Pages serves static files with
fixed content types and cannot negotiate. The redirect rules live in
[`w3id/.htaccess`](w3id/.htaccess), version-controlled here so they stay in step with the
published site, and must be contributed to
[perma-id/w3id.org](https://github.com/perma-id/w3id.org) to take effect.

<!-- TODO(Marek): open that PR (fork perma-id/w3id.org, add w3id/.htaccess as
     vizbind/.htaccess). Until it is merged, https://w3id.org/vizbind will not resolve —
     which is harmless, since an identifier does not have to resolve to be valid. -->

The documentation is generated by [pyLODE](https://github.com/RDFLib/pyLODE) and published
to GitHub Pages by [`.github/workflows/docs.yml`](.github/workflows/docs.yml). Build it
locally with:

```bash
./.venv/bin/pip install -e ".[docs]"
./.venv/bin/python scripts/build_docs.py       # -> _site/
```

The page includes the VizBind vocabulary rendered through VizBind's own VOWL-subset
notation — the metamodel drawn by the engine it defines.

## Citing

If you use VizBind, please cite the paper. GitHub's *Cite this repository* button reads
[`CITATION.cff`](CITATION.cff), which carries both the software entry and the paper as
the preferred citation.

## Licensing

- **Code and the repository as a whole**: [Apache License 2.0](LICENSE).
- **The vocabulary and notation documents** (`vocab/`, `notations/`,
  `examples/library.ttl`): additionally available under
  [CC BY 4.0](LICENSE-CC-BY-4.0.md), the customary licence for published vocabularies.
  Use whichever of the two suits your purpose.
- **Third-party ontologies** in `examples/vendor/` are redistributed unmodified under
  their own licences and are covered by neither of the above. See
  [`examples/vendor/NOTICE.md`](examples/vendor/NOTICE.md).
