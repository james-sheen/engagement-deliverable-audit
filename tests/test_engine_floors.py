"""The measured floors: that they ship, that they describe the engine installed now.

`battery/probe_engine.py` measures the engine and writes these numbers. Nothing here
re-measures -- a probe that fails is indistinguishable from an engine that changed, and
on a pin change the first thing anybody wants is the new numbers rather than a red
test. What these do is the two things a measurement needs beside it: that it travels
with the wheel, and that it is about the version actually resolved.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import engagement_deliverable_audit as package

FLOORS = Path(package.__file__).parent / "engine_floors.json"
BURN_IN = Path(__file__).resolve().parents[1] / "docs" / "burn-in.md"


@pytest.fixture(scope="module")
def measured() -> dict:
    assert FLOORS.exists(), (
        f"{FLOORS} is missing. It has to live INSIDE the package: a floor this "
        f"collector's cadence can never present is a different class from one it has "
        f"not reached yet, and an installed tool without these numbers cannot tell "
        f"them apart. A sibling in this family shipped a wheel without them and lost "
        f"that class silently")
    return json.loads(FLOORS.read_text(encoding="utf-8"))


def test_the_floors_describe_an_engine_this_package_supports(measured) -> None:
    """THE TRIPWIRE: the record names a version inside the declared pin.

    NOT equality with the engine installed right now, and that is measured rather
    than relaxed. `battery/probe_pin.py` installs every release the pin claims and
    runs this suite inside each one, so a test demanding equality fails in an
    environment built on purpose to exercise the floor -- which is what it did, in
    CI, on the commit that added it.

    The claim worth pinning is that these numbers describe an engine this package
    says it supports. Whether they still REPRODUCE is a behaviour question, and the
    grader job re-runs the probe and compares every measurement against this record
    in the declared environment. That is strictly stronger than comparing a version
    string, and it is the check that goes red on a pin change.
    """
    import sys
    from pathlib import Path as _Path

    from packaging.specifiers import SpecifierSet

    sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / "battery"))
    import probe_pin

    pin = probe_pin.declared_pins()["arbiter-engine"]
    recorded = measured["engine_version"]
    assert recorded, "the record names no engine version at all"
    assert SpecifierSet(str(pin)).contains(recorded), (
        f"the floors were measured against {recorded}, which this package's own pin "
        f"{pin} does not admit. Either the pin moved under the record or the record "
        f"is about an engine no consumer will install")


def test_every_floor_carries_a_reason(measured) -> None:
    """A number with no reason beside it is a preference. The same rule the
    declaration format applies to a threshold applies to a measurement."""
    thin = [name for name, floor in measured["floors"].items()
            if len(floor.get("note") or "") < 20]
    assert thin == [], f"these floors have no reason recorded: {thin}"


def test_what_was_not_measured_is_named(measured) -> None:
    """An unmeasured arm is not handled and not unhandled. Naming the ones left out
    is the only thing that keeps the difference visible, so an empty list here would
    read as full coverage."""
    assert measured["not_measured"], "no axiom is named as unmeasured, which would claim all of them"
    for entry in measured["not_measured"]:
        assert "--" in entry, f"{entry!r} names an axiom without saying why it is absent"


def test_the_probe_recorded_where_it_ran(measured) -> None:
    for key in ("measured_on", "engine_module", "python", "probes"):
        assert measured.get(key), f"the record carries no {key}"


def test_no_floor_carries_a_key_whose_unit_is_ambiguous(measured) -> None:
    """`captures` is banned from this record, and the ban is the fix.

    The word cost this package an off-by-one that reached three documents and a test:
    every floor was written under `captures`, holding whichever of two different units
    the probe happened to measure. Adding `observations` and
    `captures_through_the_feeder` beside it corrected the test and left the ambiguous key
    in the data file, which is where the next reader looks -- and by then `captures` meant
    three things in one record: an observation count, a real capture count, and a dict of
    cadence-to-count.

    Asserted over every floor rather than over STABILITY, because the key was ambiguous
    everywhere and only STABILITY was wrong by accident of which unit it held.
    """
    assert measured["floors"], "no floors in the record; this would check nothing"
    offenders = sorted(name for name, floor in measured["floors"].items()
                       if "captures" in floor)
    assert offenders == [], (
        f"{offenders} carry a key named `captures`, whose unit a reader has to guess. "
        f"Name the unit: `observations` for what the engine needs, "
        f"`captures_through_the_feeder` for what a collector must take")

    # And the positive half: every floor states at least one unit-named count, so the
    # ban above cannot be satisfied by a record that says nothing at all.
    for name, floor in measured["floors"].items():
        named = [k for k in floor
                 if k.startswith(("observations", "captures_through_the_feeder"))]
        assert named, f"{name} records no count under a unit-named key"


def test_a_derived_quantity_needs_one_more_capture_than_observation(measured) -> None:
    """The relationship between the two units, per floor, rather than once for STABILITY.

    A quantity the feeder DERIVES costs one capture more than the engine needs
    observations, because the first capture has no predecessor. One that is READ costs
    the same. Pinning the rule per floor is what stops a new indicator being recorded
    with the wrong pairing.
    """
    for name, floor in measured["floors"].items():
        if "observations" not in floor or "captures_through_the_feeder" not in floor:
            continue
        gap = floor["captures_through_the_feeder"] - floor["observations"]
        assert gap in (0, 1), (
            f"{name} claims {gap} captures of difference; the feeder either derives a "
            f"quantity (one more) or reads it (the same), and nothing else")


def test_the_burn_in_document_agrees_with_the_measurement(measured) -> None:
    """The seam between a number and the prose explaining it.

    Derived from the record rather than typed here, so raising the engine's floor
    fails this by making the document wrong rather than by leaving it agreeing with
    a number nothing holds any more.

    **IT PINNED THE PROBE'S NUMBER, NOT THE TOOL'S.** The probe feeds the engine
    observations directly and reaches the floor at ten; the tool feeds captures and
    derives one point each, dropping the first, so it reaches the floor at eleven. This
    asserted `capture 10` and the document said `capture 10`, and both were wrong about
    the thing a reader sizing a burn-in needs. The record now carries both numbers and
    this asserts the one the document is about.
    """
    text = BURN_IN.read_text(encoding="utf-8")
    stability = measured["floors"]["STABILITY"]["captures_through_the_feeder"]
    assert f"capture {stability}" in text, (
        f"the record says STABILITY answers from {stability} captures through the "
        f"feeder and the burn-in document does not say so")
    observations = measured["floors"]["STABILITY"]["observations"]
    assert stability == observations + 1, (
        "the feeder drops the first capture, so the tool's floor is the engine's plus "
        "one; if that stops holding, the derivation changed and this document is about "
        "a different number")
    learned = measured["floors"]["HOMEOSTASIS_learned"]["by_cadence"]
    assert learned["daily"]["unreachable at this rate"] is True, (
        "the document's central claim is that a daily collector cannot reach the "
        "learned baseline; the record no longer says that")
    # Pinned to the engine's own field name rather than to a turn of phrase. The
    # document is allowed to be rewritten; what it may not do is stop naming the
    # mechanism its central claim rests on. An earlier version of this asserted a
    # sentence, and reorganising the document broke it while every claim survived.
    assert "floor_unreachable_at_this_rate" in text, (
        "the document no longer names the field the engine reports this with, so a "
        "reader cannot check the claim against a run")
