"""The paths are right, a missing path is a defect, and the gate sees a live engine."""

from __future__ import annotations

import pytest

from engagement_deliverable_audit.guards import describe_gate as guard


def test_the_published_acceptance_shape_is_refused_rather_than_passed() -> None:
    """A payload with all three names at the TOP level is the shape the
    acceptance one-liner assumed. Two of them do not live there, so a gate that
    defaulted to empty would call this clean."""
    found = guard.problems({"unreachable_declarations": [], "unread_fields": [],
                            "unread_properties": []})
    missing = {p.where for p in found}
    assert missing == {"model.unreachable_declarations", "model.unread_fields"}
    for problem in found:
        assert "offered" in problem.what


def test_a_correct_and_silent_payload_passes() -> None:
    assert guard.problems({"model": {"unreachable_declarations": [],
                                     "unread_fields": []},
                           "unread_properties": []}) == ()


def test_a_non_empty_list_is_reported_at_the_right_nesting() -> None:
    found = guard.problems({"model": {"unreachable_declarations": [],
                                      "unread_fields": [{"field": "role"}]},
                            "unread_properties": []})
    assert len(found) == 1 and found[0].where == "model.unread_fields"


# --- against a real engine -------------------------------------------------

def _model(indicators):
    return {"domain": {"id": "t", "name": "t", "description": "t",
                       "entity_types": ["Engagement"], "relationship_types": [],
                       "indicators": {"Engagement": indicators}}}


def _session(model):
    from arbiter_engine.api import EngineSession

    session = EngineSession()
    session.load_model(model)
    return session


def test_the_live_gate_sees_a_field_no_declared_axiom_reads() -> None:
    """The measured case, and the one the acceptance would have failed on: an
    observation-only peer carrying a `role` that only CONSISTENCY and
    RESPONSIVENESS read. Both are legal on their own; together they are a field
    nobody reads."""
    found = guard.silence(_session(_model([
        {"name": "coverage_b", "type": "NUMERIC", "role": "ratio", "axioms": []}])))
    assert [p for p in found if p.where == "model.unread_fields"], \
        "the live gate did not see the unread role"


def test_the_live_gate_is_silent_on_a_model_with_nothing_unread() -> None:
    """CONTROL. Before believing the positive above, prove this gate can report
    nothing -- otherwise it might be reporting on every model alike.

    **The control used to declare no axiom at all, and so was silent for the wrong
    reason.** A model with `axioms: []` has nothing unread because it has nothing
    declared, which is the degenerate silence rather than the real one -- and that
    model is now itself refused, because a run against it can only come back clean.
    So the control declares an axiom and is silent because the engine read all of it,
    which is the state a real model is supposed to be in.
    """
    assert guard.silence(_session(_model([
        {"name": "coverage_b", "type": "NUMERIC", "axioms": ["STABILITY"],
         "expect_variation": True, "window": "30d"}]))) == ()


def test_a_model_that_declares_no_axiom_is_refused_by_the_live_gate() -> None:
    """A model the engine loads, reads entirely, and judges nothing with.

    `something: else` is a valid `DomainModel` to this engine: `is_domain_model` says
    True, there are no entity types and no indicators, and every silence list is
    honestly empty. So all three checks above pass and a `detect` run against it
    scores CLEAN, because no findings and no declines is the clean case. Pointing a
    verb at the wrong YAML file was a clean audit.
    """
    found = guard.silence(_session({"something": "else"}))
    assert [p for p in found if p.where == "model.declared_axioms"], (
        f"a model declaring no axiom has to be refused, and the gate said {found}")
