# Third-party ontologies

The files in this directory are **not** part of VizBind and are **not** covered by this
repository's Apache-2.0 or CC BY 4.0 licences. They are published vocabularies,
redistributed here unmodified so that the evaluation in the accompanying paper is
reproducible from the exact bytes it was run against.

Each retains its original licence and copyright. All were retrieved on **2026-07-18**.

| File | Vocabulary | Source | Licence |
|---|---|---|---|
| `dcat.ttl` | Data Catalog Vocabulary (DCAT) 3 | <https://www.w3.org/TR/vocab-dcat-3/> | CC BY 4.0 — declared in the file itself: `dcterms:license <https://creativecommons.org/licenses/by/4.0/>` |
| `org.ttl` | The Organization Ontology | <https://www.w3.org/TR/vocab-org/> | ODC PDDL 1.0 — declared in the file itself: `dct:license <http://www.opendatacommons.org/licenses/pddl/1.0/>` |
| `foaf.rdf` | FOAF Vocabulary Specification 0.99 | <http://xmlns.com/foaf/spec/> | CC BY 1.0, per the specification: "This work is licensed under a Creative Commons Attribution License", <http://creativecommons.org/licenses/by/1.0/>. Copyright © 2000–2014 Dan Brickley and Libby Miller |
| `prov-o.ttl` | PROV-O: The PROV Ontology | <https://www.w3.org/TR/prov-o/> | W3C Recommendation; terms per the W3C licences — see note below |
| `skos.rdf` | SKOS Simple Knowledge Organization System Reference | <https://www.w3.org/TR/skos-reference/> | W3C Recommendation; terms per the W3C licences — see note below |

## Note on the W3C vocabularies

`prov-o.ttl` and `skos.rdf` carry no machine-readable licence triple, and the two source
Recommendations predate W3C's 2023 licence revision. Their terms are set by the W3C
document and software licences rather than by anything in the files themselves:

- W3C Software and Document License (2023): <https://www.w3.org/copyright/software-license/>
- W3C Document License: <https://www.w3.org/copyright/document-license/>

<!-- TODO(Marek): before the first public release, confirm on each Recommendation's own
     copyright footer which of the two W3C licences applies to that document's RDF, and
     replace the "see note below" cells above with the specific licence name and URL.
     Redistributing them is permitted under either; this is about naming them correctly. -->

## Alternative

If redistributing these files ever becomes awkward, `scripts/evaluate.py` could fetch
them at run time instead. That is deliberately **not** what this repository does: pinning
the exact bytes is what makes the reported numbers reproducible, and a fetched-at-run-time
vocabulary can change under you between the paper and the reader.
