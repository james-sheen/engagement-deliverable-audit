"""The vocabulary: all fifteen members, and the kit that cannot prove enough."""

from __future__ import annotations

import subprocess
import sys

import pytest

from engagement_deliverable_audit import capture
from engagement_deliverable_audit.vertical import AUDITED, KINDS, EngagementVocabulary


def test_the_conformance_kit_is_green() -> None:
    """Run as the core intends it to be run, in a fresh interpreter. Green means
    nothing reached past the contract; it does NOT mean the contract is enough
    for this domain, which is what the tests below and the end-to-end file are
    for."""
    done = subprocess.run(
        [sys.executable, "-m", "presence_audit.conformance",
         "engagement_deliverable_audit.vertical:register"],
        capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr


def test_every_member_the_core_declares_is_answered() -> None:
    """Derived from the core's own protocol rather than a list typed here, so a
    sixteenth member makes this fail on the day it lands."""
    from presence_audit.vocabulary import Vocabulary

    required = {m for m in dir(Vocabulary) if not m.startswith("_")}
    assert required, "the protocol yielded nothing; this check would pass over it"
    missing = sorted(m for m in required if not hasattr(EngagementVocabulary(), m))
    assert missing == [], f"unanswered: {missing}"


def test_the_optional_members_are_answered_too() -> None:
    """A report printing `point` for a deliverable is a report in somebody
    else's noun, and a count key printed under its own name is ugly by design."""
    v = EngagementVocabulary()
    assert v.noun == ("deliverable", "deliverables")
    assert set(v.count_labels()) == set(v.count_keys.values())
    assert "window" in v.report_sections()


def test_count_keys_name_only_kinds_that_exist() -> None:
    v = EngagementVocabulary()
    assert set(v.count_keys) <= set(KINDS)


@pytest.mark.parametrize("declared,kind", [
    ("deliverable", "deliverable"), ("milestone", "milestone"),
    ("ceremony", "ceremony"), ("assumption", "assumption"),
    ("workstream", "unrecognised"), (None, "unrecognised")])
def test_classification_is_three_valued_about_itself(declared, kind) -> None:
    assert EngagementVocabulary().classify(declared) == kind


def test_a_ceremony_can_never_be_absent() -> None:
    """Without this a weekly steering call would be reported as a missing
    deliverable on every single run."""
    v = EngagementVocabulary()
    assert v.is_expected_live("deliverable") is True
    assert v.is_expected_live("ceremony") is False
    assert v.is_expected_live("assumption") is False
    assert all(v.is_auditable(k) for k in AUDITED)


def test_peer_groups_is_a_claim_and_not_a_gap() -> None:
    """Two deliverables are two things. If a rule could derive the pairs it would
    not know them."""
    assert EngagementVocabulary().peer_groups(object()) == ()


def _export(points, **kw):
    return capture.load({"format": "engagement-deliverable-audit/capture/1",
                         "points": points, **kw}, stall_window_days=14)


def test_the_two_findings_only_this_domain_can_see() -> None:
    v = EngagementVocabulary()
    export = _export([
        {"name": "D-1", "state": "In Progress", "owner": "anon-1", "days_since_transition": 2},
        {"name": "D-2", "state": "In Progress", "owner": "anon-2", "days_since_transition": 40},
        {"name": "D-3", "state": "In Progress", "owner": None, "days_since_transition": 1}])
    found = {f.kind: f.point for f in v.capture_findings(export)}
    assert found == {"stalled_deliverable": "D-2", "orphaned_deliverable": "D-3"}


def test_an_orphan_is_reported_as_an_orphan_and_not_as_stalled() -> None:
    """Both are present-and-not-moving; only one of them has somebody to ask."""
    v = EngagementVocabulary()
    export = _export([{"name": "D-1", "state": "In Progress", "owner": None,
                       "days_since_transition": 99}])
    kinds = [f.kind for f in v.capture_findings(export)]
    assert kinds == ["orphaned_deliverable"]


def test_two_exports_from_different_exporters_are_skipped_not_compared() -> None:
    """False here means SKIPPED. A difference between two exporters is not a
    change in the engagement."""
    v = EngagementVocabulary()
    a = _export([], exporter={"export_sha256": "a" * 64})
    b = _export([], exporter={"export_sha256": "b" * 64})
    assert v.captures_comparable(a, a) is True
    assert v.captures_comparable(a, b) is False
    changed = [c.kind for c in v.capture_changes(a, b)]
    assert "exporter_changed" in changed


def test_a_moved_window_is_reported_as_a_change_of_rules() -> None:
    """Two verdicts reached under different windows are not comparable findings,
    and saying so is the difference between a regression and a re-definition."""
    v = EngagementVocabulary()
    narrow = capture.load({"format": "engagement-deliverable-audit/capture/1",
                           "points": []}, stall_window_days=7)
    wide = capture.load({"format": "engagement-deliverable-audit/capture/1",
                         "points": []}, stall_window_days=30)
    assert "window_changed" in [c.kind for c in v.capture_changes(narrow, wide)]
