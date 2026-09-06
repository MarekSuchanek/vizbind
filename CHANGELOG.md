# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

While the version stays below `1.0.0`, the binding vocabulary and the engine API are
explicitly **not** stable: terms may be renamed, added or withdrawn between minor
versions. A `1.0.0` release will follow the planned journal treatment, once the
vocabulary has been exercised against notations and adapters the authors did not write
themselves.

## [Unreleased]

## [0.1.0] — 2026-09-11

Initial public release: the proof-of-concept artifact as evaluated in the KEOD 2026
paper *Binding Ontologies to Notation: A Declarative RDF Vocabulary for
Notation-Independent Visualisation of RDFS/OWL Models*.

### Added

- `vocab/vizbind.ttl` — the binding metamodel, in the permanent namespace
  `https://w3id.org/vizbind#`: `vb:Binding`, `vb:Notation`, the
  four abstract visual constructs (`vb:Node`, `vb:Edge`, `vb:Compartment`,
  `vb:Decorator`), `vb:SparqlSelection`, engine-agnostic styling vocabularies and
  priority-based conflict resolution.
- `notations/vowl-subset.ttl` — a subset of VOWL expressed as bindings
  (14 bindings, 9 of 16 assessed VOWL constructs).
- `notations/uml-style.ttl` — a structurally contrasting UML-class-style notation
  (8 bindings).
- `vizbind/` — proof-of-concept engine over `rdflib`, producing an Abstract Visual
  Model (AVM) with an SHA-256 canonical digest.
- `vizbind/backends/` — Graphviz (DOT), Mermaid and Cytoscape.js adapters, each
  consuming only the AVM.
- `examples/library.ttl` — the running example (63 triples), and five third-party
  vocabularies under `examples/vendor/` for the applicability evaluation.
- `scripts/build_figures.py` and `scripts/evaluate.py` — regenerate every figure
  and every number the paper reports.
- `tests/` — 27 tests at fixture and integration level.

### Known limitations

- Layout is deliberately out of scope and delegated to the rendering engine, so
  notations whose identity is partly procedural (VOWL's force-directed dynamics)
  are reproduced in their static conventions only.
- Selections run over the *asserted* graph: no import closure, no RDFS or OWL
  entailment. Reasoning, where wanted, is a preprocessing step on the input.
- The binding vocabulary offers no scale functions or computed visual attributes,
  so aggregate-derived styling such as VOWL's instance-count node sizing is an
  extension point rather than an implemented feature.
- The `https://w3id.org/vizbind` redirect is pending review at
  [perma-id/w3id.org](https://github.com/perma-id/w3id.org); until it is merged the
  IRI does not resolve, though it is already the canonical identifier.

[Unreleased]: https://github.com/MarekSuchanek/vizbind/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/MarekSuchanek/vizbind/releases/tag/v0.1.0
