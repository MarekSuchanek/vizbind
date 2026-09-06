"""Template language used by binding rules.

A template is text interleaved with ``{expression}`` holes, e.g.::

    "{coalesce(?label, localName(?c))}"
    "{localName(?p)} : {localName(?range)}"

Grammar::

    template := (TEXT | '{' expr '}')*
    expr     := var | call | string
    var      := '?' NAME
    call     := NAME '(' [ expr (',' expr)* ] ')'
    string   := "'" ... "'"

An expression evaluates to a string or to ``None`` (unbound). A template
containing an unbound hole evaluates to ``None`` as a whole, which lets callers
distinguish "no value" from "empty string".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Union


class TemplateError(ValueError):
    """Raised when a template cannot be parsed."""


# --------------------------------------------------------------------------
# AST
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Text:
    value: str


@dataclass(frozen=True)
class Var:
    name: str


@dataclass(frozen=True)
class Str:
    value: str


@dataclass(frozen=True)
class Call:
    name: str
    args: Sequence["Expr"]


Expr = Union[Var, Str, Call]
Segment = Union[Text, Var, Str, Call]


# --------------------------------------------------------------------------
# Built-in functions
# --------------------------------------------------------------------------


def _local_name(value: Optional[str]) -> Optional[str]:
    """Strip an IRI down to its local part (after the last '#' or '/')."""
    if value is None:
        return None
    for sep in ("#", "/"):
        if sep in value:
            value = value.rsplit(sep, 1)[-1]
    return value or None


def _coalesce(*values: Optional[str]) -> Optional[str]:
    for value in values:
        if value is not None and value != "":
            return value
    return None


FUNCTIONS: Dict[str, Callable[..., Optional[str]]] = {
    "localName": _local_name,
    "coalesce": _coalesce,
    "lower": lambda v: v.lower() if v is not None else None,
    "upper": lambda v: v.upper() if v is not None else None,
}


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------


class _Parser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    def _peek(self) -> str:
        return self.text[self.pos] if self.pos < len(self.text) else ""

    def _skip_ws(self) -> None:
        while self.pos < len(self.text) and self.text[self.pos].isspace():
            self.pos += 1

    def parse_template(self) -> List[Segment]:
        segments: List[Segment] = []
        buffer: List[str] = []
        while self.pos < len(self.text):
            char = self.text[self.pos]
            if char == "{":
                if buffer:
                    segments.append(Text("".join(buffer)))
                    buffer = []
                self.pos += 1
                segments.append(self.parse_expr())
                self._skip_ws()
                if self._peek() != "}":
                    raise TemplateError(f"expected '}}' at {self.pos} in {self.text!r}")
                self.pos += 1
            else:
                buffer.append(char)
                self.pos += 1
        if buffer:
            segments.append(Text("".join(buffer)))
        return segments

    def parse_expr(self) -> Expr:
        self._skip_ws()
        char = self._peek()
        if char == "?":
            return self._parse_var()
        if char == "'":
            return self._parse_string()
        if char.isalpha() or char == "_":
            return self._parse_call()
        raise TemplateError(f"unexpected {char!r} at {self.pos} in {self.text!r}")

    def _parse_name(self) -> str:
        start = self.pos
        while self.pos < len(self.text) and (
            self.text[self.pos].isalnum() or self.text[self.pos] in "_-"
        ):
            self.pos += 1
        if start == self.pos:
            raise TemplateError(f"expected a name at {start} in {self.text!r}")
        return self.text[start : self.pos]

    def _parse_var(self) -> Var:
        self.pos += 1  # consume '?'
        return Var(self._parse_name())

    def _parse_string(self) -> Str:
        self.pos += 1  # consume opening quote
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos] != "'":
            self.pos += 1
        if self.pos >= len(self.text):
            raise TemplateError(f"unterminated string in {self.text!r}")
        value = self.text[start : self.pos]
        self.pos += 1  # consume closing quote
        return Str(value)

    def _parse_call(self) -> Call:
        name = self._parse_name()
        self._skip_ws()
        if self._peek() != "(":
            raise TemplateError(
                f"unknown bare word {name!r} in {self.text!r}; "
                "did you mean ?{name} or a function call?"
            )
        self.pos += 1
        args: List[Expr] = []
        self._skip_ws()
        if self._peek() == ")":
            self.pos += 1
            return Call(name, args)
        while True:
            args.append(self.parse_expr())
            self._skip_ws()
            char = self._peek()
            if char == ",":
                self.pos += 1
                continue
            if char == ")":
                self.pos += 1
                break
            raise TemplateError(f"expected ',' or ')' at {self.pos} in {self.text!r}")
        if name not in FUNCTIONS:
            raise TemplateError(f"unknown function {name!r} in {self.text!r}")
        return Call(name, args)


def parse(text: str) -> List[Segment]:
    """Parse a template into segments. Raises TemplateError on bad syntax."""
    return _Parser(text).parse_template()


# --------------------------------------------------------------------------
# Evaluation
# --------------------------------------------------------------------------


def _eval_expr(expr: Expr, bindings: Dict[str, Optional[str]]) -> Optional[str]:
    if isinstance(expr, Var):
        return bindings.get(expr.name)
    if isinstance(expr, Str):
        return expr.value
    if isinstance(expr, Call):
        args = [_eval_expr(a, bindings) for a in expr.args]
        return FUNCTIONS[expr.name](*args)
    raise TemplateError(f"cannot evaluate {expr!r}")


def render(text: str, bindings: Dict[str, Optional[str]]) -> Optional[str]:
    """Render ``text`` against ``bindings``.

    Returns ``None`` if any non-literal hole is unbound, so that callers can
    skip the attribute (or the whole construct) rather than emit "None".
    """
    out: List[str] = []
    for segment in parse(text):
        if isinstance(segment, Text):
            out.append(segment.value)
            continue
        value = _eval_expr(segment, bindings)
        if value is None:
            return None
        out.append(value)
    return "".join(out)
