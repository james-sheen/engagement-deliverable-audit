"""The two artifacts: what they refuse, and the one number they must carry."""

from __future__ import annotations

import pytest

from engagement_deliverable_audit import capture, declaration, formats

GOOD = {
    "format": "engagement-deliverable-audit/declaration/1",
    "engagement": "E-1", "stall_window_days": 14,
    "reviewed_by": "a name", "reviewed_on": "2026-09-11",
    "sources": [{"path": "sow.pdf", "derived_from": "the signed statement of work"}],
    "points": [{"id": "D-1", "declared_type": "deliverable", "text": "a thing"}],
}


def test_a_declaration_with_no_window_is_refused_not_defaulted() -> None:
    """The window decides which deliverables count as stalled, so a default would
    be a number nobody decided, inherited by every engagement after the first."""
    payload = {k: v for k, v in GOOD.items() if k != "stall_window_days"}
    with pytest.raises(declaration.DeclarationError) as raised:
        declaration.load(payload)
    assert "no default" in str(raised.value)


@pytest.mark.parametrize("window", [0, -1, "fourteen", None])
def test_a_window_that_is_not_a_positive_number_is_refused(window) -> None:
    with pytest.raises(declaration.DeclarationError):
        declaration.load(dict(GOOD, stall_window_days=window))


def test_an_unknown_declared_type_is_refused_rather_than_counted_out() -> None:
    """A type nobody recognises would be classified as `unrecognised` and counted
    out, which narrows the denominator silently. Refusing says so."""
    with pytest.raises(declaration.DeclarationError) as raised:
        declaration.load(dict(GOOD, points=[
            {"id": "D-9", "declared_type": "workstream", "text": "a thing"}]))
    assert "workstream" in str(raised.value)


def test_the_wrong_format_is_refused_naming_both() -> None:
    with pytest.raises(formats.FormatError) as raised:
        declaration.load(dict(GOOD, format="engagement-deliverable-audit/declaration/2"))
    assert "/1" in str(raised.value) and "/2" in str(raised.value)


def test_a_document_with_no_format_is_not_treated_as_an_earlier_one() -> None:
    with pytest.raises(formats.FormatError) as raised:
        declaration.load({k: v for k, v in GOOD.items() if k != "format"})
    assert "nobody versioned" in str(raised.value)


def test_the_review_gate_reads_both_a_name_and_a_date() -> None:
    assert declaration.load(GOOD).reviewed is True
    for missing in ("reviewed_by", "reviewed_on"):
        payload = dict(GOOD)
        payload[missing] = None
        assert declaration.load(payload).reviewed is False, missing


def test_the_sources_answer_what_the_report_writer_reads() -> None:
    """The guard, run against the real thing this package builds rather than
    against a fixture of it."""
    assert declaration.check_sources(declaration.load(GOOD)) == ()


def test_staleness_is_asked_rather_than_assumed() -> None:
    engagement = declaration.load(dict(GOOD, change_order=2))
    assert declaration.staleness(engagement, 2) == ()
    stale = declaration.staleness(engagement, 3)
    assert len(stale) == 1 and stale[0].where == "declaration_stale"


# --- the capture side ------------------------------------------------------

EXPORT = {
    "format": "engagement-deliverable-audit/capture/1",
    "points": [
        {"name": "D-1", "state": "In Progress", "owner": "anon-1",
         "days_since_transition": 3},
        {"name": "D-2", "state": "In Progress", "owner": "anon-2",
         "days_since_transition": 40},
        {"name": "D-3", "state": "In Progress", "owner": None,
         "days_since_transition": 1},
        {"name": "D-4", "state": "In Progress", "owner": "anon-4"},
    ],
}


def test_the_window_decides_which_are_moving() -> None:
    export = capture.load(EXPORT, stall_window_days=14)
    verdicts = {p.name: p.is_reading for p in export.points}
    assert verdicts == {"D-1": True, "D-2": False, "D-3": False, "D-4": False}


def test_the_same_export_gives_a_different_answer_under_a_different_window() -> None:
    """The window is a specification, so it is the lever. Asserting this keeps it
    visible: an export does not carry its own verdict."""
    wide = capture.load(EXPORT, stall_window_days=60)
    assert {p.name for p in wide.points if p.is_reading} == {"D-1", "D-2"}


def test_the_number_survives_the_verdict() -> None:
    """A stalled deliverable keeps its days-since-transition. Blanking it to make
    a shared finding fire would trade the evidence a reader acts on for a kind."""
    export = capture.load(EXPORT, stall_window_days=14)
    stalled = next(p for p in export.points if p.name == "D-2")
    assert stalled.reading == 40.0 and stalled.is_reading is False


def test_a_missing_transition_is_not_a_transition_at_zero() -> None:
    export = capture.load(EXPORT, stall_window_days=14)
    unknown = next(p for p in export.points if p.name == "D-4")
    assert unknown.reading is None and unknown.is_reading is False


def test_nothing_in_a_tracker_is_administratively_switched_off() -> None:
    """A descoped deliverable is a change to the declaration, not to the export.
    Answering anything but true here would report a change order as a fault."""
    export = capture.load(EXPORT, stall_window_days=14)
    assert all(p.is_enabled for p in export.points)
