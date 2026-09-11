"""What a declaration's `sources` elements must answer, derived from the reader.

THE DEFECT THIS EXISTS FOR. `presence_audit.protocols` documents
`DeclarationSource.sources` as one member and says nothing about its elements.
`diff` copies them verbatim onto the report, and the core's JSON writer then
reads eleven members off each one. A vertical that fills `sources` with paths --
which is what the protocol's wording suggests, what the conformance kit's own
stand-in does, and what the one shipped non-BMC vertical does -- passes the
conformance kit and then dies with `AttributeError: 'str' object has no
attribute 'kind'` the first time anything asks for JSON. The text writer accepts
the string happily, so the report a person reads is clean while the report a
harness parses does not run at all.

WHY THE LIST IS DERIVED AND NOT TYPED. A transcribed list of eleven names is
correct on the day it is written and silently wrong after the writer gains a
twelfth. So the list is read out of the writer itself, by walking its syntax
tree for attribute accesses on the loop variable. If the writer starts reading
something new, this guard starts requiring it, in the same release, with no edit
here.
"""

from __future__ import annotations

import ast
import inspect
from typing import Any, Iterable

from .problem import Problem

#: The function in the writer that consumes the elements. Named rather than
#: searched for: a walk over the whole module would also sweep up attribute
#: accesses on unrelated objects and quietly widen the requirement.
_WRITER_FUNCTION = "_as_json"

#: The loop variable the writer binds each element to.
_ELEMENT = "source"


def required_members(writer: Any = None) -> frozenset[str]:
    """Every member the writer reads off one element of `sources`.

    Raises rather than returning an empty set when it cannot find the function
    or the accesses: an empty requirement would make `missing()` below pass over
    everything, which is the failure this whole module is about.
    """
    if writer is None:
        from presence_audit import report as writer  # deferred: optional extra
    tree = ast.parse(inspect.getsource(writer))
    wanted = [n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == _WRITER_FUNCTION]
    if not wanted:
        raise LookupError(
            f"{writer.__name__} has no {_WRITER_FUNCTION!r}; the writer was "
            f"renamed or restructured, and this guard is now asking about "
            f"nothing. Re-derive the name from the writer before trusting it.")
    found = {
        node.attr
        for fn in wanted
        for node in ast.walk(fn)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == _ELEMENT
    }
    if not found:
        raise LookupError(
            f"{_WRITER_FUNCTION} reads nothing off {_ELEMENT!r}. Either the "
            f"loop variable was renamed or the provenance block was removed; "
            f"either way this guard cannot see what it was written to see.")
    return frozenset(found)


def missing(element: Any, writer: Any = None) -> tuple[str, ...]:
    """Members the writer will reach for and this element does not answer."""
    return tuple(sorted(m for m in required_members(writer)
                        if not hasattr(element, m)))


def problems(sources: Iterable[Any], writer: Any = None) -> tuple[Problem, ...]:
    """Every element of a declaration's `sources` that the writer would break on."""
    out = []
    for index, element in enumerate(sources):
        gaps = missing(element, writer)
        if gaps:
            out.append(Problem(
                where=f"sources[{index}] ({type(element).__name__})",
                what=f"does not answer {', '.join(gaps)}, which the report "
                     f"writer reads off every element",
                remedy="supply an object carrying those members, or return an "
                       "empty sources tuple and say in the docstring that this "
                       "package writes its own provenance block"))
    return tuple(out)
