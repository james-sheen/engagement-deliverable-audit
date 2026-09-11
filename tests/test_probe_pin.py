"""The pin probe: what it derives, what it refuses, and what it will not call a floor.

The probe's own failure mode is the one it exists to catch. It could report *every
release each pin claims passed* having installed nothing, because that sentence is
true of an empty set; it could read a version literal out of this file and keep
agreeing with itself after somebody raised the real one; and it could reduce a
sweep to a single boundary when the releases below the floor do not fail in order.
Each of those is a test here, and each fails if the probe is wrong rather than if
the pins change.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from packaging.specifiers import SpecifierSet
from packaging.version import Version

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "battery"))

import probe_pin  # noqa: E402


def _released(*texts: str):
    return lambda dist: sorted(Version(t) for t in texts)


# --- what it derives -------------------------------------------------------

def test_the_pins_are_read_from_the_file_that_declares_them() -> None:
    """Derived, not transcribed. The assertion is on the specifier's BEHAVIOUR at
    the floor rather than on its text, so raising the floor updates this test by
    making it fail rather than by leaving it agreeing with an old number."""
    pins = probe_pin.declared_pins()
    assert pins, "no pins were read at all, which every later check would pass over"
    core = pins["presence-audit"]
    assert core.contains("0.1.7") and not core.contains("0.1.6")
    assert "arbiter-engine" in pins, "the extras were dropped, and an extra is a pin"


def test_a_dependency_with_no_bound_is_refused(tmp_path, monkeypatch) -> None:
    """An unbounded dependency makes no claim, so there is nothing to probe and a
    clean exit would be asserting something about every release ever published."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["somepackage"]\n', encoding="utf-8")
    monkeypatch.setattr(probe_pin, "REPO_ROOT", tmp_path)
    with pytest.raises(probe_pin.CannotRun, match="no version specifier"):
        probe_pin.declared_pins()


def test_a_declaration_with_no_dependencies_is_refused(tmp_path, monkeypatch) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n', encoding="utf-8")
    monkeypatch.setattr(probe_pin, "REPO_ROOT", tmp_path)
    with pytest.raises(probe_pin.CannotRun, match="no dependencies"):
        probe_pin.declared_pins()


# --- what it refuses -------------------------------------------------------

def test_a_range_holding_no_releases_cannot_report_success(monkeypatch) -> None:
    """The empty-set trap, and the reason this is not theoretical: a typo in a
    distribution name, a yanked release, or a range written against a version line
    that never shipped all produce *every release in range passed* over nothing."""
    monkeypatch.setattr(probe_pin, "released", _released("0.1.0", "0.1.1"))
    with pytest.raises(probe_pin.CannotRun, match="matches none"):
        probe_pin.candidates("somepackage", SpecifierSet(">=0.2,<0.3"))


def test_the_release_below_the_floor_is_the_highest_one(monkeypatch) -> None:
    """Not merely *a* release below it. The floor is demonstrated by the release
    immediately under it; any older one failing says nothing about where the
    boundary is."""
    monkeypatch.setattr(probe_pin, "released",
                        _released("0.1.4", "0.1.6", "0.1.7", "0.1.8"))
    in_range, below = probe_pin.candidates("somepackage", SpecifierSet(">=0.1.7,<0.2"))
    assert [str(v) for v in in_range] == ["0.1.7", "0.1.8"]
    assert str(below) == "0.1.6"


def test_a_version_that_would_not_install_is_never_a_pass() -> None:
    """`pip` reports a resolver conflict on stderr and still exits 0, so the only
    honest answer when the environment does not hold the version asked for is that
    the probe could not run."""
    with pytest.raises(probe_pin.CannotRun, match="could-not-pin|asked for"):
        probe_pin.verdicts([{
            "dist": "somepackage", "pin": ">=0.1.7,<0.2",
            "in_range": [{"version": "0.1.7", "state": "could-not-pin",
                          "detail": "asked for 0.1.7, the environment reports 0.1.6"}],
            "below": None, "swept": []}])


# --- what it will not call a floor -----------------------------------------

def test_an_in_range_failure_refutes_and_a_below_floor_pass_does_not() -> None:
    """The two outcomes are not the same kind of thing. An in-range failure makes
    the declared range false. A below-floor pass leaves it true and says only that
    the number came from somewhere other than this probe -- lowering it needs a
    reason a person supplies, so it must not be reported as a refutation."""
    refutations, notes = probe_pin.verdicts([{
        "dist": "core", "pin": ">=0.1.7,<0.2",
        "in_range": [{"version": "0.1.7", "state": "fail", "detail": "1 failed"}],
        "below": {"version": "0.1.6", "state": "pass", "detail": "ok"},
        "swept": []}])
    assert len(refutations) == 1 and "claims 0.1.7 works and it does not" in refutations[0]
    assert any("floor-not-demonstrated" in note for note in notes)


def test_a_failing_release_below_the_floor_is_what_demonstrates_it() -> None:
    refutations, notes = probe_pin.verdicts([{
        "dist": "core", "pin": ">=0.1.7,<0.2",
        "in_range": [{"version": "0.1.7", "state": "pass", "detail": "ok"}],
        "below": {"version": "0.1.6", "state": "fail", "detail": "1 failed"},
        "swept": []}])
    assert refutations == []
    assert any("the floor holds" in note for note in notes)


def test_nothing_below_the_floor_is_reported_rather_than_read_as_agreement() -> None:
    """A floor at the first release ever published cannot be demonstrated by
    running anything, and that is a different state from a demonstrated one."""
    _, notes = probe_pin.verdicts([{
        "dist": "core", "pin": ">=0.1.0,<0.2",
        "in_range": [{"version": "0.1.0", "state": "pass", "detail": "ok"}],
        "below": None, "swept": []}])
    assert any("nothing is released below the floor" in note for note in notes)


def test_a_non_monotonic_sweep_is_named_rather_than_reduced_to_a_boundary() -> None:
    """Written while no sweep has produced this shape. The first real sweep found a
    clean boundary -- three releases passing above five failing -- which is exactly
    the condition under which this branch has never run. A sweep exists because the
    failure need not be monotonic in the version; if it is not, there is no single
    release to call the floor, and saying so is the only correct answer."""
    swept = [{"version": "0.1.9", "state": "fail", "detail": "1 failed"},
             {"version": "0.1.8", "state": "pass", "detail": "ok"}]
    _, notes = probe_pin.verdicts([{
        "dist": "core", "pin": ">=0.1.10,<0.2",
        "in_range": [{"version": "0.1.10", "state": "pass", "detail": "ok"}],
        "below": swept[0], "swept": swept}])
    assert any("NOT MONOTONIC" in note for note in notes)
    assert any("swept 2 release(s)" in note for note in notes)


def test_a_monotonic_sweep_is_not_reported_as_unordered() -> None:
    """The other half: the control that keeps the check above from firing on the
    shape every sweep so far has actually produced."""
    swept = [{"version": "0.1.9", "state": "pass", "detail": "ok"},
             {"version": "0.1.8", "state": "fail", "detail": "1 failed"}]
    _, notes = probe_pin.verdicts([{
        "dist": "core", "pin": ">=0.1.10,<0.2",
        "in_range": [{"version": "0.1.10", "state": "pass", "detail": "ok"}],
        "below": swept[0], "swept": swept}])
    assert not any("NOT MONOTONIC" in note for note in notes)
