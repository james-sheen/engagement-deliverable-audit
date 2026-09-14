"""The derived requirement is exactly right, proven in both directions."""

from __future__ import annotations

import json
import types

import pytest

from engagement_deliverable_audit.guards import source_contract as guard


class _Source:
    """An element answering every member the writer reads, and nothing more."""

    def __init__(self, members):
        for name in members:
            setattr(self, name, None)
        # The one that is called rather than read.
        self.provenance_line = lambda: "from a fixture, disclosed"
        self.supplied = ()


def test_the_guard_still_knows_where_to_look() -> None:
    """NON-VACUITY, asked of the thing that can actually go vacuous.

    It used to assert the REQUIREMENT was non-empty, which stopped being the
    right question at `presence-audit` 0.1.8: that release made the writer read
    every member defensively, so an element answering nothing goes through and
    the requirement is legitimately empty. Asserting otherwise would report the
    fix as a regression.

    What must never be empty is what the guard can SEE. A writer it cannot find,
    or one it finds and reads nothing off, makes every check below pass over
    nothing -- and that is indistinguishable from a clean tree.
    """
    import ast
    import inspect

    from presence_audit import report

    tree = ast.parse(inspect.getsource(report))
    functions = [n for n in ast.walk(tree)
                 if isinstance(n, ast.FunctionDef)
                 and n.name in guard._WRITER_FUNCTIONS]
    assert functions, "the guard names no function the writer has"
    assert len(guard._reached(functions)) >= 2, (
        "the guard can see fewer than two members being reached for, so it has "
        "lost its subject rather than found a writer that requires nothing")


def test_an_object_answering_the_derived_set_survives_the_real_writer() -> None:
    """The strong form: the derived set is SUFFICIENT, checked by writing JSON.

    This is what the conformance kit cannot do -- it never reaches the writer --
    so a vertical can be green there and die here.
    """
    from presence_audit import diff, report, vocabulary

    _register_minimal_vocabulary(vocabulary)
    declaration = _declaration(sources=(_Source(guard.required_members()),))
    built = diff.compare(declaration, _capture())
    payload = json.loads(report.as_json(built, target="a fixture"))
    assert payload["declaration_sources"], "the provenance block was not written"


def test_dropping_one_member_breaks_the_real_writer() -> None:
    """And NECESSARY: each derived member is one the writer truly reaches for.

    Without this the set could be too wide and nothing would notice, because a
    too-wide requirement only ever refuses things that would have worked.
    """
    from presence_audit import diff, report, vocabulary

    _register_minimal_vocabulary(vocabulary)
    members = sorted(guard.required_members())
    for dropped in members:
        element = _Source(m for m in members if m != dropped)
        if dropped == "provenance_line":
            del element.provenance_line
        if dropped == "supplied":
            del element.supplied
        built = diff.compare(_declaration(sources=(element,)), _capture())
        with pytest.raises(AttributeError):
            report.as_json(built, target="a fixture")


def test_a_path_string_is_judged_by_the_writer_that_is_installed() -> None:
    """The shape the protocol's wording suggests, the conformance kit's own
    stand-in supplies, and the one shipped non-BMC vertical returns.

    BOTH ARMS ASSERT, because the answer legitimately differs across the range
    this package pins. Below `presence-audit` 0.1.8 the writer reads the members
    bare and a path is refused, naming the first one it would break on. From
    0.1.8 the writer reads them defensively -- reported upstream and fixed there
    -- so a path goes through and refusing it would be this guard enforcing a
    contract the core has dropped.
    """
    required = guard.required_members()
    found = guard.problems(("register.yaml",))
    if required:
        assert len(found) == 1
        assert "str" in found[0].where
        assert "kind" in found[0].what
    else:
        assert found == (), (
            "the installed writer requires nothing off an element, so a path "
            "string is not a problem; this guard reported one anyway")


def test_an_empty_sources_tuple_is_accepted() -> None:
    """Carrying no provenance is a decision a vertical is allowed to make; what
    it is not allowed to do is carry something the writer cannot read."""
    assert guard.problems(()) == ()


def test_a_writer_without_the_function_is_refused_loudly() -> None:
    """If the writer is renamed, this guard must say so rather than require
    nothing. A LookupError is the only honest answer to *I cannot see*."""
    empty = types.ModuleType("empty")
    empty.__name__ = "empty"
    source = "def something_else():\n    return 1\n"
    empty.__file__ = "<string>"
    import inspect

    original = inspect.getsource
    inspect.getsource = lambda obj: source if obj is empty else original(obj)
    try:
        with pytest.raises(LookupError):
            guard.required_members(empty)
    finally:
        inspect.getsource = original


# --- fixtures, deliberately tiny -------------------------------------------

def _register_minimal_vocabulary(vocabulary) -> None:
    class _V:
        kinds = ("deliverable", "unrecognised")
        count_keys = {"unrecognised": "unrecognised_type"}

        def classify(self, declared_type):
            return declared_type if declared_type == "deliverable" else "unrecognised"

        def is_auditable(self, kind):
            return kind == "deliverable"

        def is_expected_live(self, declared_type):
            return declared_type == "deliverable"

        def template_pattern(self, declared_name):
            return None

        def same_point(self, old, new):
            return True

        def captures_comparable(self, before, after):
            return False

        def point_changes(self, old, new, *, comparable=False):
            return ()

        def capture_changes(self, before, after):
            return ()

        def capture_findings(self, capture):
            return ()

        def peer_groups(self, declaration):
            return ()

    vocabulary.reset()
    vocabulary.register(_V())


class _Declared:
    name = "D-1"
    type = "deliverable"
    display_name = "D-1 a deliverable"
    source = "a fixture"
    expects_reading = None
    disabled = False
    is_templated = False
    thresholds = ()


def _declaration(sources):
    return types.SimpleNamespace(points=(_Declared(),), sources=sources,
                                 anomalies=(), unreadable=())


def _capture():
    live = types.SimpleNamespace(name="D-1", path="tracker://D-1", reading=1.0,
                                 is_reading=True, state=None, thresholds={},
                                 units=None, is_enabled=True)
    return types.SimpleNamespace(points=(live,), captured_at=None, complete=True,
                                 errors=())
