"""The three answers, demonstrated end to end through the shared core.

This is the claim the package is for, so it is asserted against the real
`diff.compare` with the real vocabulary registered, not against a stub.
"""

from __future__ import annotations

import pytest

from engagement_deliverable_audit import capture, declaration, exit_contract
from engagement_deliverable_audit.vertical import register


@pytest.fixture(autouse=True)
def _registered():
    from presence_audit import vocabulary

    vocabulary.reset()
    register()
    yield
    vocabulary.reset()


DECLARED = {
    "format": "engagement-deliverable-audit/declaration/1",
    "engagement": "E-1", "stall_window_days": 14,
    "reviewed_by": "an engagement manager", "reviewed_on": "2026-09-11",
    "change_order": 2,
    "sources": [{"path": "sow.pdf", "derived_from": "the signed statement of work"}],
    "points": [
        {"id": "D-1", "declared_type": "deliverable", "text": "the migration plan"},
        {"id": "D-2", "declared_type": "deliverable", "text": "the data model"},
        {"id": "D-3", "declared_type": "deliverable", "text": "the cutover runbook"},
        {"id": "D-4", "declared_type": "deliverable", "text": "the pilot report",
         "descoped": True},
        {"id": "C-1", "declared_type": "ceremony", "text": "weekly steering call"},
        {"id": "A-1", "declared_type": "assumption", "text": "the client staffs two analysts"},
    ],
}

EXPORTED = {
    "format": "engagement-deliverable-audit/capture/1",
    "captured_at": "2026-09-11T00:00:00Z",
    "exporter": {"export_sha256": "a" * 64},
    "points": [
        {"name": "D-1", "path": "tracker://PROJ-11", "state": "In Progress",
         "owner": "anon-3", "days_since_transition": 2},
        {"name": "D-2", "path": "tracker://PROJ-12", "state": "In Progress",
         "owner": "anon-5", "days_since_transition": 40},
        {"name": "D-4", "path": "tracker://PROJ-14", "state": "In Progress",
         "owner": "anon-3", "days_since_transition": 1},
        {"name": "X-9", "path": "tracker://PROJ-99", "state": "In Progress",
         "owner": "anon-7", "days_since_transition": 1},
    ],
}


def _compare():
    from presence_audit import diff

    engagement = declaration.load(DECLARED)
    export = capture.load(EXPORTED, stall_window_days=engagement.stall_window_days)
    return diff.compare(engagement, export), engagement, export


def test_the_three_answers_are_three_answers() -> None:
    report, _, _ = _compare()
    counts = report.counts()
    # D-1 moving; D-2 stalled; D-4 descoped and still moving -- all three matched.
    assert counts["reading"] == 2, counts
    assert counts["present_not_reading"] == 1, counts
    # D-3 is declared and the tracker has never heard of it.
    assert counts["declared_absent"] == 1, counts
    # A ceremony and an assumption are counted out, not reported absent.
    assert counts["not_a_deliverable"] == 1 and counts["counted_out_assumption"] == 1
    assert counts["declared"] == 4, "the denominator must exclude what is counted out"


def test_a_stalled_deliverable_is_named_with_its_window() -> None:
    report, _, export = _compare()
    stalled = [f for f in report.findings if f.kind == "stalled_deliverable"]
    assert [f.sensor for f in stalled] == ["D-2"], "capture-side findings use the key"
    assert "14 day(s)" in stalled[0].detail and "40 day(s)" in stalled[0].detail


def test_a_descoped_deliverable_still_moving_is_reported() -> None:
    report, _, _ = _compare()
    kinds = {f.kind: f.sensor for f in report.findings}
    # Asserted as a prefix, not an equality, and that is the convention rather
    # than laziness: a finding the CORE raises names the declared point by its
    # display name, while one this vertical raises from a capture names the
    # ticket key, because `capture_findings` never sees a display name. See the
    # note in `vertical.py`.
    assert kinds.get("disabled_in_config_but_live", "").startswith("D-4")


def test_work_the_statement_of_work_does_not_name_is_reported_and_not_scored() -> None:
    report, _, _ = _compare()
    kinds = [f.kind for f in report.findings]
    assert "undeclared_present" in kinds
    assert exit_contract.floor("undeclared_present") == exit_contract.CLEAN


def test_the_two_scorings_agree_about_a_domain_only_defect() -> None:
    """THE REASON the exit code is computed here, and the reason has moved.

    It used to be that the core scored only its OWN regression kinds, so a
    capture whose single defect is one this domain alone can see came back clean
    from it -- reported upstream, and this assertion pinned the limitation with
    a message saying what to do when it lifted.

    It lifted. `presence-audit` 0.1.8 lets a vocabulary name which of its own
    kinds are regressions, and this package's does. So the two scorings now
    AGREE on this capture, which is the stronger claim, and it is what this
    asserts. Below that release the core cannot know, and the package's own
    scoring is the only one that answers -- so both arms assert rather than one
    of them skipping.
    """
    from presence_audit import diff

    engagement = declaration.load(DECLARED)
    only_orphan = dict(EXPORTED, points=[
        {"name": "D-1", "path": "t://1", "state": "In Progress", "owner": None,
         "days_since_transition": 1}])
    export = capture.load(only_orphan, stall_window_days=engagement.stall_window_days)
    trimmed = declaration.Engagement(
        points=tuple(p for p in engagement.points if p.name == "D-1"),
        sources=engagement.sources, stall_window_days=engagement.stall_window_days,
        reviewed_by="a name", reviewed_on="2026-09-11")
    report = diff.compare(trimmed, export)
    kinds = [f.kind for f in report.findings]
    assert kinds == ["orphaned_deliverable"]
    assert exit_contract.code_for(kinds) == exit_contract.FINDINGS, (
        "this package's own floor table stopped scoring its own finding")
    from presence_audit import vocabulary as _core_vocabulary

    if hasattr(_core_vocabulary, "regression_kinds"):
        assert report.exit_code == exit_contract.FINDINGS, (
            "the core reads `regression_kinds` from this release on and this "
            "vertical declares `orphaned_deliverable`, so the two scorings must "
            "agree rather than this package quietly carrying the verdict alone")
    else:
        assert report.exit_code == 0, (
            "the installed core cannot score a domain's own kinds, which is why "
            "this package computes its own code -- but it answered something "
            "other than clean, so neither explanation holds")


def test_an_incomplete_export_withholds_absence() -> None:
    from presence_audit import diff

    engagement = declaration.load(DECLARED)
    partial = dict(EXPORTED, complete=False,
                   errors=[["board/2", "the export stopped at 50 rows"]])
    export = capture.load(partial, stall_window_days=engagement.stall_window_days)
    report = diff.compare(engagement, export)
    kinds = [f.kind for f in report.findings]
    assert "walk_incomplete" in kinds
    assert "declared_absent" not in kinds, "absence must be withheld, not reported"
    assert exit_contract.code_for(kinds) == exit_contract.FINDINGS
    assert exit_contract.code_for(kinds, require_complete=True) == exit_contract.INCOMPLETE
