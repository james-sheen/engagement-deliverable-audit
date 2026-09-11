"""The gate refuses what the engine answers silently, and permits what works."""

from __future__ import annotations

import pytest

from engagement_deliverable_audit.guards import model_gate as guard


def _model(indicator):
    return {"domain": {"id": "t", "name": "t", "description": "t",
                       "entity_types": ["Engagement"], "relationship_types": [],
                       "indicators": {"Engagement": [
                           dict(indicator),
                           {"name": "peer", "type": "NUMERIC", "axioms": []}]}}}


CONSISTENT = {"name": "coverage", "type": "NUMERIC", "role": "ratio",
              "axioms": ["CONSISTENCY"]}


@pytest.mark.parametrize("shape,why", [
    ({}, "no consistency block at all"),
    ({"consistency": {"tolerance": 0.02}}, "a block with no agrees_with"),
    ({"consistency": {"agrees_with": [], "tolerance": 0.02}}, "an empty agrees_with"),
])
def test_every_silent_shape_is_refused(shape, why) -> None:
    """All three behave identically in the engine: no finding, no decline, and a
    place in the denominator. A check asking whether the BLOCK is present would
    pass two of them."""
    found = guard.problems(_model({**CONSISTENT, **shape}))
    assert [p for p in found if "CONSISTENCY" in p.what], f"{why} was not refused"


def test_a_populated_agrees_with_is_accepted() -> None:
    found = guard.problems(_model({**CONSISTENT,
                                   "consistency": {"agrees_with": ["peer"],
                                                   "tolerance": 0.02}}))
    assert found == ()


def test_a_bare_monotonicity_is_deliberately_not_refused() -> None:
    """Measured: the reversal arm answers without a block, so refusing this
    would reject a declaration that works. The guard is allowed to be narrower
    than the list of axioms that take configuration."""
    found = guard.problems(_model({"name": "slip_days", "type": "NUMERIC",
                                   "role": "count", "axioms": ["MONOTONICITY"]}))
    assert found == ()


def test_a_boundedness_with_nothing_to_bound_is_refused() -> None:
    found = guard.problems(_model({"name": "utilisation", "type": "NUMERIC",
                                   "role": "ratio", "axioms": ["BOUNDEDNESS"]}))
    assert len(found) == 1 and "BOUNDEDNESS" in found[0].what


def test_the_gate_is_not_vacuous_over_a_clean_model() -> None:
    """NON-VACUITY in the other direction: a gate that refused everything would
    pass every test above and be useless."""
    clean = _model({**CONSISTENT, "consistency": {"agrees_with": ["peer"]}})
    clean["domain"]["indicators"]["Engagement"].append(
        {"name": "margin", "type": "NUMERIC", "role": "ratio",
         "axioms": ["HOMEOSTASIS"], "homeostasis": {"setpoint": 0.3,
                                                    "tolerance": 0.05}})
    assert guard.problems(clean) == ()


def test_a_basis_that_does_not_contain_its_number_is_refused() -> None:
    """A citation can name a real document and still be the author's invention.
    A statement of work that sets a due date does not publish a warning line
    three days before it."""
    found = guard.basis_problems([
        {"name": "page_count", "critical": 40,
         "basis": {"quote": "Volume II shall not exceed 40 pages"}},
        {"name": "hours_to_deadline", "lower_warning": 72,
         "basis": {"quote": "responses are due on the date shown"}},
    ])
    assert len(found) == 1
    assert found[0].where == "hours_to_deadline.lower_warning"
    assert "HOMEOSTASIS" in found[0].remedy
