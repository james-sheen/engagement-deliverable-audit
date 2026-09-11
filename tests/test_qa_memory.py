"""The harness source, including the rule the module states and nothing tested.

This file exists because a mutation pass found it: changing `as_capture` to read a
missing number as a transition at zero left all 147 other tests green. The module
documented the rule; nothing held it.
"""

from __future__ import annotations

import pytest

from engagement_deliverable_audit import capture, qa_memory


def _snapshot(entities, errors=None):
    return {"format": "qa-memory/1", "entities": entities, "errors": errors or {}}


def _export(entities, window=14.0, errors=None):
    return capture.load(qa_memory.as_capture(_snapshot(entities, errors)),
                        stall_window_days=window)


def test_a_missing_number_is_not_a_transition_at_zero() -> None:
    """The rule the module states, asserted. A snapshot that carried no number is
    a gap in the data; reporting it as fresh would turn that gap into a healthy
    deliverable, which is the most expensive kind of wrong answer this package can
    give."""
    export = _export({"D-1": {"value": None}})
    point = export.points[0]
    assert point.reading is None, "a missing number became a number"
    assert point.is_reading is False, "a gap in the data read as moving"


def test_a_transition_at_zero_really_is_fresh() -> None:
    """CONTROL. Without this the check above would also pass if zero were being
    rejected, which would be a different defect wearing the same result."""
    point = _export({"D-1": {"value": 0}}).points[0]
    assert point.reading == 0.0 and point.is_reading is True


def test_the_three_states_arrive_through_three_of_the_harness_own_verbs() -> None:
    """`remove` makes a deliverable absent, `drive`/`set` walk it across the
    window. Only losing an owner needs a verb of this domain's own."""
    export = _export({"D-1": {"value": 2}, "D-2": {"value": 40}})
    verdicts = {p.name: p.is_reading for p in export.points}
    assert verdicts == {"D-1": True, "D-2": False}
    assert "D-3" not in verdicts, "an entity the snapshot omits must simply be absent"


def test_an_owner_set_to_null_is_an_orphan_and_not_a_stall() -> None:
    export = _export({"D-1": {"value": 1, "owner": None}})
    assert export.points[0].owner is None
    assert export.points[0].state == "no owner"


def test_a_snapshot_with_no_owner_key_describes_an_owned_tracker() -> None:
    """The ordinary case. A snapshot silent about owners is not a tracker full of
    orphans; a scenario that wants one says so."""
    assert _export({"D-1": {"value": 1}}).points[0].owner == "anon"


def test_errors_make_the_export_incomplete() -> None:
    export = _export({"D-1": {"value": 1}}, errors={"board/2": "truncated at 50 rows"})
    assert export.complete is False
    assert export.errors and export.errors[0][0] == "board/2"


def test_a_snapshot_with_no_entities_is_refused() -> None:
    """An empty substrate would make every declared deliverable absent and every
    phase pass, which is the shape of a harness that silently stopped working."""
    with pytest.raises(qa_memory.SnapshotError) as raised:
        qa_memory.as_capture({"format": "qa-memory/1"})
    assert "every phase pass" in str(raised.value)


def test_the_wrong_format_is_refused_naming_both() -> None:
    with pytest.raises(qa_memory.SnapshotError) as raised:
        qa_memory.as_capture({"format": "qa-memory/2", "entities": {}})
    assert "qa-memory/1" in str(raised.value) and "qa-memory/2" in str(raised.value)


def test_the_result_goes_through_the_same_reader_a_real_export_does() -> None:
    """The source produces a payload in the published format rather than an object,
    so nothing reaches a path a real export would not take."""
    payload = qa_memory.as_capture(_snapshot({"D-1": {"value": 1}}))
    assert payload["format"] == "engagement-deliverable-audit/capture/1"
    assert capture.load(payload, stall_window_days=14).points[0].name == "D-1"
