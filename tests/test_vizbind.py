"""Tests for the VizBind reference engine.

    python -m pytest tests/ -q
"""

from __future__ import annotations

import pathlib
import sys

import pytest
from rdflib import Graph

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vizbind import template  # noqa: E402
from vizbind.backends import BACKENDS  # noqa: E402
from vizbind.engine import apply_notation  # noqa: E402
from vizbind.notation import load_notation  # noqa: E402


@pytest.fixture(scope="module")
def library() -> Graph:
    graph = Graph()
    graph.parse(str(ROOT / "examples" / "library.ttl"), format="turtle")
    return graph


@pytest.fixture(scope="module")
def vowl():
    return load_notation(str(ROOT / "notations" / "vowl-subset.ttl"))


@pytest.fixture(scope="module")
def uml():
    return load_notation(str(ROOT / "notations" / "uml-style.ttl"))


# -- template language ------------------------------------------------------


def test_template_plain_text():
    assert template.render("hello", {}) == "hello"


def test_template_variable_substitution():
    assert template.render("{?x}", {"x": "value"}) == "value"


def test_template_unbound_variable_yields_none():
    assert template.render("{?x}", {"x": None}) is None
    assert template.render("a{?missing}b", {}) is None


def test_template_local_name_strips_iri():
    assert template.render("{localName(?c)}", {"c": "https://e.org/o#Book"}) == "Book"
    assert template.render("{localName(?c)}", {"c": "https://e.org/path/Book"}) == "Book"


def test_template_coalesce_falls_back():
    bindings = {"label": None, "c": "https://e.org/o#Book"}
    assert template.render("{coalesce(?label, localName(?c))}", bindings) == "Book"
    bindings["label"] = "A Book"
    assert template.render("{coalesce(?label, localName(?c))}", bindings) == "A Book"


def test_template_mixed_segments():
    bindings = {"p": "https://e.org/o#isbn", "r": "http://www.w3.org/2001/XMLSchema#string"}
    assert template.render("{localName(?p)} : {localName(?r)}", bindings) == "isbn : string"


def test_template_rejects_unknown_function():
    with pytest.raises(template.TemplateError):
        template.render("{bogus(?x)}", {"x": "v"})


def test_template_rejects_unterminated_hole():
    with pytest.raises(template.TemplateError):
        template.render("{?x", {"x": "v"})


# -- notation loading -------------------------------------------------------


def test_notation_loads_bindings(vowl, uml):
    assert vowl.bindings, "VOWL subset should declare bindings"
    assert uml.bindings, "UML style should declare bindings"


def test_bindings_sorted_by_descending_priority(vowl):
    priorities = [b.priority for b in vowl.bindings]
    assert priorities == sorted(priorities, reverse=True)


# -- engine -----------------------------------------------------------------


def test_vowl_renders_object_property_as_node(library, vowl):
    """The defining structural feature of VOWL: a property IS a node."""
    avm = apply_notation(library, vowl)
    assert "https://example.org/library#hasAuthor" in avm.nodes


def test_uml_renders_object_property_as_edge(library, uml):
    """The same construct is an edge, not a node, under the UML notation."""
    avm = apply_notation(library, uml)
    assert "https://example.org/library#hasAuthor" not in avm.nodes
    assert "https://example.org/library#hasAuthor" in avm.edges


def test_uml_renders_datatype_property_as_compartment(library, uml):
    avm = apply_notation(library, uml)
    book = avm.nodes["https://example.org/library#Book"]
    assert "isbn : string" in book.compartments["attributes"]


def test_uml_draws_no_datatype_nodes(library, uml):
    avm = apply_notation(library, uml)
    assert not [n for n in avm.nodes if "XMLSchema" in n]


def test_vowl_draws_datatype_nodes(library, vowl):
    avm = apply_notation(library, vowl)
    assert [n for n in avm.nodes if "XMLSchema" in n]


def test_notations_produce_different_avms(library, vowl, uml):
    """Notation-independence: same model, same engine, different diagrams."""
    assert apply_notation(library, vowl).digest() != apply_notation(library, uml).digest()


def test_cardinality_decorator_is_applied(library, uml):
    avm = apply_notation(library, uml)
    texts = [d.text for d in avm.edges["https://example.org/library#hasAuthor"].decorators]
    assert "1..*" in texts


def test_functional_property_decorated(library, vowl):
    avm = apply_notation(library, vowl)
    texts = [d.text for d in avm.nodes["https://example.org/library#heldBy"].decorators]
    assert "functional" in texts


def test_no_warnings_on_running_example(library, vowl, uml):
    assert apply_notation(library, vowl).warnings == []
    assert apply_notation(library, uml).warnings == []


def test_engine_is_deterministic(library, vowl):
    """SPARQL result order is unspecified; the AVM must not depend on it."""
    digests = {apply_notation(library, vowl).digest() for _ in range(5)}
    assert len(digests) == 1


def test_higher_priority_binding_wins(library, vowl):
    """ExternalClassBinding (priority 5) must not override ClassBinding (10)."""
    avm = apply_notation(library, vowl)
    # Every library class is declared locally, so all keep the standard fill.
    assert avm.nodes["https://example.org/library#Book"].fill == "#AACCFF"


# -- back-ends --------------------------------------------------------------


@pytest.mark.parametrize("backend_name", sorted(BACKENDS))
def test_backend_produces_output_without_mutating_avm(library, uml, backend_name):
    avm = apply_notation(library, uml)
    before = avm.digest()
    output = BACKENDS[backend_name].render(avm)
    assert output.strip(), f"{backend_name} produced empty output"
    assert avm.digest() == before, f"{backend_name} mutated the AVM"


def test_graphviz_emits_record_for_compartments(library, uml):
    dot = BACKENDS["graphviz"].render(avm=apply_notation(library, uml), rankdir="TB")
    assert "shape=record" in dot
    assert "isbn : string" in dot


def test_graphviz_escapes_quotes_in_labels(library, uml):
    dot = BACKENDS["graphviz"].render(apply_notation(library, uml))
    # Balanced quoting: every attribute list must terminate.
    assert dot.count("[") == dot.count("]")


def test_cytoscape_emits_valid_json(library, uml):
    import json

    payload = json.loads(BACKENDS["cytoscape"].render(apply_notation(library, uml)))
    assert payload["elements"]
    assert payload["style"]
