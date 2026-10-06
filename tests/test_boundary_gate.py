"""Where a bound fires is measured, not assumed -- and the two axioms differ."""

from __future__ import annotations

import math

import pytest


def _model(indicator):
    return {"domain": {"id": "t", "name": "t", "description": "t",
                       "entity_types": ["Response"], "relationship_types": [],
                       "indicators": {"Response": [indicator]}}}


from engagement_deliverable_audit.guards import boundary_gate as guard


def test_a_ceiling_declared_at_the_published_number_fails_a_compliant_subject() -> None:
    """The defect. *Shall not exceed forty pages* leaves forty compliant, and
    BOUNDEDNESS compares inclusively, so `critical: 40` reports a forty-page
    volume as critical."""
    model = _model({"name": "page_count", "type": "NUMERIC", "role": "count",
                    "critical": 40.0, "axioms": ["BOUNDEDNESS"]})
    found = guard.problems(model, [("Response", "page_count", "critical", 40.0)])
    assert len(found) == 1
    assert "itself is reported as a violation" in found[0].what


def test_the_repair_passes() -> None:
    """Declaring the next representable value makes the published number clean
    and the first non-compliant value fire. Nothing else changes."""
    model = _model({"name": "page_count", "type": "NUMERIC", "role": "count",
                    "critical": math.nextafter(40.0, math.inf),
                    "axioms": ["BOUNDEDNESS"]})
    assert guard.problems(model, [("Response", "page_count", "critical", 40.0)]) == ()


def test_the_guard_agrees_with_the_engine_about_the_other_axiom() -> None:
    """THE CONTROL: the guard probes rather than assumes, and this is what says so.

    It used to assert that RESPONSIVENESS is EXCLUSIVE -- `warning: 120` clean at
    120.0 and firing just past it -- which was measured and true when written.
    `arbiter-engine` 0.1.14 made the two axioms agree, inclusively, after this
    package's sibling reported that one engine holding both rules silently was
    the defect. So the remembered answer is now the wrong one, and a control
    pinned to it fails on a release that fixed the thing it exists to watch.

    What keeps the control honest is not WHICH way the axiom compares but that
    the guard says whatever the engine does. So this measures the engine and
    asserts the guard agrees -- true under either comparator, and still red if
    the guard ever starts assuming.
    """
    model = _model({"name": "turnaround_hours", "type": "NUMERIC", "role": "latency",
                    "warning": 120.0, "critical": 600.0,
                    "axioms": ["RESPONSIVENESS"]})
    fires_at_the_number = guard._fires(model, "Response", "turnaround_hours", 120.0)
    found = guard.problems(model,
                           [("Response", "turnaround_hours", "warning", 120.0)])
    if fires_at_the_number:
        assert len(found) == 1, (
            "the engine fires AT the declared number, so declaring the published "
            "limit reports a compliant subject and the guard must say so")
        assert "itself is reported as a violation" in found[0].what
    else:
        assert found == (), (
            "the engine is clean at the declared number, so the declaration is "
            "correct and the guard must not refuse it")


def test_a_bound_that_fires_nowhere_is_reported() -> None:
    """The other half of the assertion. A threshold on an indicator whose axiom
    never reads it produces no finding at any value, which reads exactly like a
    subject that complies."""
    model = _model({"name": "page_count", "type": "NUMERIC", "role": "count",
                    "critical": 40.0, "axioms": []})
    found = guard.problems(model, [("Response", "page_count", "critical", 40.0)])
    assert len(found) == 1 and "nothing fires just past" in found[0].what


def test_a_floor_is_probed_downwards() -> None:
    """`nextafter` has to be told which way is worse, and a floor crossed upwards
    would look clean forever."""
    model = _model({"name": "days_of_runway", "type": "NUMERIC", "role": "count",
                    "lower_critical": math.nextafter(24.0, -math.inf),
                    "axioms": ["BOUNDEDNESS"]})
    assert guard.problems(model,
                          [("Response", "days_of_runway", "lower_critical", 24.0)]) == ()


@pytest.mark.parametrize("line, limit, warning, critical", [
    (38.0, 40.0, "warning", "critical"),
    (5.0, 2.0, "lower_warning", "lower_critical"),
], ids=["a warning line under a ceiling", "a warning line over a floor"])
def test_two_bounds_on_one_indicator_are_each_judged_at_their_own_severity(line, limit, warning, critical) -> None:
    """The common shape, which the guard had never met: a warning line inside a limit. At the
    published limit the subject is past its warning line -- the engine says WARNING, correctly --
    and inside the limit, so the critical bound is clean there and fires just past it. Counting
    any finding read that warning as the critical bound firing at its own number."""
    away = math.inf if warning == "warning" else -math.inf
    model = _model({"name": "page_count", "type": "NUMERIC", "axioms": ["BOUNDEDNESS"],
                    warning: math.nextafter(line, away), critical: math.nextafter(limit, away)})
    assert guard.problems(model, [("Response", "page_count", warning, line),
                                  ("Response", "page_count", critical, limit)]) == ()
    model["domain"]["indicators"]["Response"][0][critical] = limit       # the defect, still caught
    found = guard.problems(model, [("Response", "page_count", critical, limit)])
    assert len(found) == 1 and "itself is reported as a violation" in found[0].what
