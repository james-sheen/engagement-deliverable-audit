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

#: The functions in the writer that consume the elements. Named rather than
#: searched for: a walk over the whole module would also sweep up attribute
#: accesses on unrelated objects and quietly widen the requirement.
#:
#: TWO NAMES SINCE `presence-audit` 0.1.8, because the reading moved. The inline
#: comprehension inside `_as_json` became `_source_as_json`, a function whose
#: whole job is one element -- which is a BETTER anchor than the one this guard
#: started with, not a worse one. Both are named so the guard answers across the
#: whole range this package pins.
_WRITER_FUNCTIONS = ("_as_json", "_source_as_json")

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
              if isinstance(n, ast.FunctionDef) and n.name in _WRITER_FUNCTIONS]
    if not wanted:
        raise LookupError(
            f"{writer.__name__} has none of {list(_WRITER_FUNCTIONS)}; the "
            f"writer was renamed or restructured, and this guard is now asking "
            f"about nothing. Re-derive the name from the writer before trusting "
            f"it.")
    # A BARE ATTRIBUTE IS REQUIRED; A `getattr` WITH A DEFAULT IS NOT, and the
    # difference is the whole answer from 0.1.8 on. That release made the writer
    # read every member defensively, so an element answering NOTHING -- a plain
    # path, which is what the protocol's wording suggests -- goes through. The
    # requirement genuinely became empty, and a guard that cannot express *this
    # writer requires nothing* would report the fix as the writer disappearing.
    found = {
        node.attr
        for fn in wanted
        for node in ast.walk(fn)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == _ELEMENT
    }
    reached = _reached(wanted)
    if not reached:
        raise LookupError(
            f"{list(_WRITER_FUNCTIONS)} touch {_ELEMENT!r} nowhere at all. "
            f"Either the loop variable was renamed or the provenance block was "
            f"removed; either way this guard cannot see what it was written to "
            f"see.")
    return frozenset(found)


def _reached(functions) -> set[str]:
    """Every member the writer reaches for at all, however defensively.

    Separate from the required set so the two questions stay apart: *what must
    an element answer* and *does this guard still know where to look*. Collapsing
    them is how an empty requirement -- a correct answer from 0.1.8 -- would read
    as a guard that had lost its subject.
    """
    out = set()
    for fn in functions:
        for node in ast.walk(fn):
            if (isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Name)
                    and node.value.id == _ELEMENT):
                out.add(node.attr)
            elif (isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Name) and node.func.id == "getattr"
                  and node.args and isinstance(node.args[0], ast.Name)
                  and node.args[0].id == _ELEMENT
                  and len(node.args) > 1 and isinstance(node.args[1], ast.Constant)):
                out.add(str(node.args[1].value))
    return out


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
