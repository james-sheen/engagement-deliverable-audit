"""Where a bound fires is measured, not assumed -- and the two axioms differ."""

from __future__ import annotations

import math


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


def test_the_exclusive_axiom_is_not_false_positived() -> None:
    """RESPONSIVENESS compares the other way: `warning: 120` is clean at 120.0
    and fires just past it. A guard that had hardcoded *inclusive* would refuse
    this correct declaration, so this is the control that keeps the guard honest
    about probing rather than assuming."""
    model = _model({"name": "turnaround_hours", "type": "NUMERIC", "role": "latency",
                    "warning": 120.0, "critical": 600.0,
                    "axioms": ["RESPONSIVENESS"]})
    assert guard.problems(model,
                          [("Response", "turnaround_hours", "warning", 120.0)]) == ()


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
