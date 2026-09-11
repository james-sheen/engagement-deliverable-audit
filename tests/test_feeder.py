"""The feeder: what it derives, what it feeds, and what it refuses to invent.

Stage 2's answers are only as good as what went in, and every rule here was a
decision rather than an implementation detail. Each is asserted in both directions
where both directions exist, because *the orphan was reported* and *the orphan was
fed as an entity with no edge* are different claims and only the second is this
module's.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from engagement_deliverable_audit import capture as capture_module
from engagement_deliverable_audit import declaration as declaration_module
from engagement_deliverable_audit import feeder, qa_memory

ROOT = Path(__file__).resolve().parents[1]
DECL = ROOT / "examples" / "engagement.fixture.json"
MODEL = ROOT / "examples" / "engagement.model.yaml"
WINDOW = 14.0


def _engagement():
    return declaration_module.load(json.loads(DECL.read_text(encoding="utf-8")))


def _export(entities: dict, *, stamp: dt.datetime | None):
    payload = qa_memory.as_capture(
        {"format": "qa-memory/1", "entities": entities, "errors": {}},
        captured_at=stamp.strftime("%Y-%m-%dT%H:%M:%SZ") if stamp else None)
    return capture_module.load(payload, stall_window_days=WINDOW)


def _series(days: int = 12, moving: bool = True):
    """A recent series, dated from the real clock.

    Recent on purpose. The engine counts observations inside the declared window
    measured backwards from the moment of the run, so a series that stops a month ago
    falls outside a 30-day window however many captures it holds -- which is a clock
    property of the engine and not of the data.
    """
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    out = []
    for day in range(days):
        value = (day % 3) if moving else day
        out.append(_export({"D-1": {"value": value, "owner": "ana"}},
                           stamp=now - dt.timedelta(days=days - 1 - day)))
    return out


# --- the derivation --------------------------------------------------------

def test_a_reset_between_two_captures_is_a_transition() -> None:
    now = dt.datetime.now(dt.timezone.utc)
    readings = [(now - dt.timedelta(days=3 - i), float(v))
                for i, v in enumerate([2.0, 0.0, 1.0])]
    derived = feeder.transitions(readings)
    assert [value for _, value in derived] == [1.0, 1.0]


def test_the_first_capture_is_dropped_rather_than_counted_as_zero() -> None:
    """With nothing before it there is no interval to have moved in, and a zero there
    would be a transition count asserted over no elapsed time."""
    now = dt.datetime.now(dt.timezone.utc)
    assert feeder.transitions([(now, 5.0)]) == ()


def test_a_deliverable_that_never_moves_derives_a_flat_zero() -> None:
    """Which is what `expect_variation` is for: the series is a measurement that has
    stopped being one."""
    now = dt.datetime.now(dt.timezone.utc)
    readings = [(now - dt.timedelta(days=9 - i), float(i)) for i in range(10)]
    assert {value for _, value in feeder.transitions(readings)} == {0.0}


def test_a_missing_reading_is_not_treated_as_a_fall() -> None:
    """`None` is *no transition recorded*, and comparing it with a number would make
    a gap in the export look like movement."""
    now = dt.datetime.now(dt.timezone.utc)
    readings = [(now - dt.timedelta(days=2), 5.0), (now - dt.timedelta(days=1), None),
                (now, 1.0)]
    counted = [value for _, value in feeder.transitions(readings)]
    assert counted == [0.0, 0.0]


# --- what is fed -----------------------------------------------------------

def test_an_unowned_deliverable_is_fed_as_an_entity_with_no_edge() -> None:
    """THE MECHANISM of the first invariant, and the opposite of a sibling's rule.

    A sibling feeds only what its Stage 1 saw reading, which is right for a domain
    whose faults are absence and silence. Here the first invariant is ownership and an
    orphan is exactly a deliverable that is NOT reading -- so feeding only the reading
    ones would mean the one finding this model exists for could never fire.
    """
    now = dt.datetime.now(dt.timezone.utc)
    fed = feeder.plan(_engagement(), [
        _export({"D-1": {"value": 1, "owner": "ana"},
                 "D-2": {"value": 1, "owner": None}}, stamp=now)])
    assert "D-2" in fed.deliverables
    assert fed.unowned == ("D-2",)
    assert [edge[0] for edge in fed.edges] == ["D-1"]


def test_a_descoped_deliverable_is_not_fed_at_all() -> None:
    """Removed by change order. The tracker may still carry it and Stage 1 reports
    that separately; the model is about what is in scope."""
    now = dt.datetime.now(dt.timezone.utc)
    fed = feeder.plan(_engagement(), [
        _export({"D-1": {"value": 1, "owner": "ana"},
                 "D-5": {"value": 1, "owner": "ben"}}, stamp=now)])
    assert "D-5" not in fed.deliverables
    assert "D-1" in fed.deliverables, "nothing was fed, so this checked nothing"


def test_a_capture_with_no_clock_is_refused_rather_than_stamped() -> None:
    """The derived series is a count inside a trailing week, so every capture has to
    say when it was taken. This package has already shipped a typed reference date
    once, and it made a real corpus read as entirely stalled."""
    with pytest.raises(feeder.FeedError, match="captured_at"):
        feeder.plan(_engagement(), [_export({"D-1": {"value": 1}}, stamp=None)])


def test_no_captures_is_refused(tmp_path) -> None:
    with pytest.raises(feeder.FeedError, match="nothing to feed"):
        feeder.plan(_engagement(), [])


# --- through the engine ----------------------------------------------------

def test_a_frozen_deliverable_fires_and_a_moving_one_does_not() -> None:
    """Both halves in one assertion, because either alone is satisfied by a blind run.

    Twelve captures: one deliverable whose transition count never changes, and the
    same shape where it changes every third day. The first is a finding and the second
    must be silence.
    """
    engagement = _engagement()
    text = MODEL.read_text(encoding="utf-8")

    frozen = feeder.run(engagement, _series(moving=False), text).envelope
    moving = feeder.run(engagement, _series(moving=True), text).envelope

    def kinds(envelope):
        return {str(f.get("problem_type") or "").split(":", 1)[0]
                for f in envelope.get("findings") or ()}

    assert "frozen_series" in kinds(frozen)
    assert "frozen_series" not in kinds(moving)


def test_the_burn_in_is_measured_through_the_feeder_and_not_off_the_engine() -> None:
    """How many CAPTURES the history axiom needs, swept rather than transcribed.

    The engine's floor is ten OBSERVATIONS, and every probe in `battery/` feeds it
    observations directly. The tool feeds captures: `transitions` derives one point per
    capture and drops the first, so N captures are N-1 observations and the floor
    arrives one capture later. The burn-in document and the README both published the
    engine's ten as the number of daily captures to collect.

    Swept across the boundary, not bisected, and asserted on BOTH sides: the last
    capture count that still declines and the first that answers. Asserting only the
    answering end would pass against a floor of one.

    The series is anchored to the real clock deliberately -- the window is a ceiling
    measured backwards from the run, so a series dated a month ago falls outside a
    30-day window at any length. A first attempt at this sweep used a fixed start date
    and reported that fourteen captures still declined.
    """
    engagement, text = _engagement(), MODEL.read_text(encoding="utf-8")
    record = json.loads(
        (ROOT / "src" / "engagement_deliverable_audit" / "engine_floors.json")
        .read_text(encoding="utf-8"))
    floor = record["floors"]["STABILITY"]["captures_through_the_feeder"]

    def declines_at(count: int) -> bool:
        envelope = feeder.run(engagement, _series(days=count, moving=False), text).envelope
        return "insufficient_samples" in {
            d.get("reason") for d in envelope.get("not_checked") or ()
            if d.get("axiom") == "STABILITY"}

    assert declines_at(floor - 1), (
        f"{floor - 1} captures is {floor - 2} derived points, which is below the "
        f"engine's floor, so STABILITY has to still be warming")
    assert not declines_at(floor), (
        f"the record says the tool reaches the floor at {floor} captures and it did "
        f"not; the derivation or the engine's floor has moved")


def test_one_capture_answers_connectivity_and_warms_the_rest() -> None:
    """The criterion's answer, executable. CONNECTIVITY needs no history and the series
    axiom says it is warming rather than finding nothing."""
    now = dt.datetime.now(dt.timezone.utc)
    passed = feeder.run(
        _engagement(),
        [_export({"D-1": {"value": 1, "owner": None},
                  "D-2": {"value": 1, "owner": "ana"}}, stamp=now)],
        MODEL.read_text(encoding="utf-8"))
    envelope, fed = passed.envelope, passed.fed
    assert fed.series == {}, "one capture cannot derive a series"
    problems = {str(f.get("problem_type") or "").split(":", 1)[0]
                for f in envelope["findings"]}
    assert "missing_relationship" in problems
    assert "insufficient_samples" in {d.get("reason") for d in envelope["not_checked"]}


def test_an_engagement_where_nobody_owns_anything_goes_quiet_and_cannot_read_clean() -> None:
    """MEASURED, and the shape is the dangerous one: the check is quietest when the
    failure is total.

    CONNECTIVITY needs an entity of the target type to have been OBSERVED. With four
    owners among nineteen deliverables, the fifteen orphans all fire. With no owner at
    all there is no Consultant in the graph, so the axiom declines
    `missing_entity_type` and reports no orphan -- the worse the engagement, the
    quieter the model.

    What stops that reading as a pass is the floor: `missing_entity_type` is a model or
    feed defect and floors at 2, so a run where the axiom could not be evaluated exits
    could-not-complete rather than clean. This asserts the decline AND the floor,
    because the decline alone would be satisfied by a run nobody scored.
    """
    from engagement_deliverable_audit import exit_contract

    now = dt.datetime.now(dt.timezone.utc)
    passed = feeder.run(
        _engagement(),
        [_export({"D-1": {"value": 1, "owner": None},
                  "D-2": {"value": 1, "owner": None}}, stamp=now)],
        MODEL.read_text(encoding="utf-8"))
    envelope, fed = passed.envelope, passed.fed
    assert fed.consultants == (), "an owner was fed, so this is not the shape described"
    assert envelope["findings"] == [], "an orphan fired, and the point here is that none does"
    reasons = {d.get("reason") for d in envelope["not_checked"]}
    assert "missing_entity_type" in reasons
    assert exit_contract.code_for(reasons) == exit_contract.INCOMPLETE


def test_nothing_in_the_model_goes_unread_when_fed() -> None:
    """The model is read from `model_describe` rather than `check`, because the engine
    grew a dropped-declaration leg on `check` after 0.1.10 -- and 0.1.10 is this
    package's own floor, so a reader taking it from there has a silent hole on the
    oldest release it claims to support."""
    envelope = feeder.run(_engagement(), _series(),
                          MODEL.read_text(encoding="utf-8")).envelope
    assert envelope["model"].get("unread_fields") == []
    assert envelope["model"].get("unreachable_declarations") == []


def test_an_owner_who_leaves_is_forgotten() -> None:
    """The latest capture is the state, including when the latest says nobody.

    Recording an owner only when one was present made an owner who left permanently
    owned: the name from an earlier capture stayed in the graph, the edge was still
    fed, and the orphan the model exists to find could not be seen. One capture has no
    history to go stale, so the real-data run could not show it -- the scenario that
    orphans a deliverable between two captures found it on its first run.
    """
    now = dt.datetime.now(dt.timezone.utc)
    fed = feeder.plan(_engagement(), [
        _export({"D-1": {"value": 1, "owner": "ana"}}, stamp=now - dt.timedelta(days=1)),
        _export({"D-1": {"value": 1, "owner": None}}, stamp=now)])
    assert fed.unowned == ("D-1",)
    assert fed.edges == ()
    assert fed.consultants == ()


def test_a_deliverable_that_vanishes_is_not_fed_as_an_owned_one() -> None:
    """THE N=2 CASE THE SIBLING TEST ABOVE CANNOT REACH.

    That test keeps the point present and takes its owner away. This one removes the
    point. Nothing overwrote an entry for a name no later capture mentioned, so the
    deliverable kept its owner AND its `owned_by` edge -- the graph asserted a
    consultant owns something the tracker no longer holds.

    It needed two captures and a disappearance to exist at all: with one capture there
    is no earlier state to go stale, and the real-data runs both use a single capture.
    Stage 1 reports the absence as `declared_absent`; Stage 2 says nothing, which is
    the decision rather than an omission.
    """
    now = dt.datetime.now(dt.timezone.utc)
    fed = feeder.plan(_engagement(), [
        _export({"D-1": {"value": 1, "owner": "ana"},
                 "D-2": {"value": 1, "owner": "bo"}}, stamp=now - dt.timedelta(days=1)),
        _export({"D-2": {"value": 1, "owner": "bo"}}, stamp=now)])

    assert "D-1" not in fed.deliverables, (
        "a deliverable the latest capture does not hold is not part of the current "
        "state, so Stage 2 has nothing to judge about it")
    assert not any(edge[0] == "D-1" for edge in fed.edges), (
        "the vanished deliverable still carries an ownership edge")
    assert "D-1" not in fed.unowned, (
        "reporting it as an orphan says nobody owns it, about something that is gone; "
        "Stage 1 reports the absence with the right word")
    assert fed.deliverables == ("D-2",) and fed.edges == (
        ("D-2", "owned_by", "consultant:bo"),), (
        "the deliverable that is still there must be unaffected")


def test_an_incomplete_latest_capture_does_not_turn_absence_into_departure() -> None:
    """The guard on the rule above, and the reason it is a guard and not an exception.

    A partial export WITHHELD absence rather than reporting it. Dropping a name missing
    from one would read *we did not look* as *it is gone* -- the same inversion Stage 1
    keeps `walk_incomplete` separate from `declared_absent` to avoid. So with an
    incomplete latest capture the older state stands.
    """
    now = dt.datetime.now(dt.timezone.utc)
    full = _export({"D-1": {"value": 1, "owner": "ana"},
                    "D-2": {"value": 1, "owner": "bo"}},
                   stamp=now - dt.timedelta(days=1))
    partial = _export({"D-2": {"value": 1, "owner": "bo"}}, stamp=now)
    object.__setattr__(partial, "complete", False)

    fed = feeder.plan(_engagement(), [full, partial])
    assert "D-1" in fed.deliverables, (
        "absence from an incomplete export is not evidence of departure")
    assert any(edge[0] == "D-1" for edge in fed.edges)


def test_an_owner_who_arrives_is_seen() -> None:
    """The other direction, so the rule above is not satisfied by a feeder that simply
    never records an owner at all."""
    now = dt.datetime.now(dt.timezone.utc)
    fed = feeder.plan(_engagement(), [
        _export({"D-1": {"value": 1, "owner": None}}, stamp=now - dt.timedelta(days=1)),
        _export({"D-1": {"value": 1, "owner": "ana"}}, stamp=now)])
    assert fed.unowned == ()
    assert [edge[0] for edge in fed.edges] == ["D-1"]
