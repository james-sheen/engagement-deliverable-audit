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

import ast
import os
import sys
import time
from pathlib import Path

import pytest
from packaging.specifiers import SpecifierSet
from packaging.version import Version

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "battery"))

import probe_pin  # noqa: E402


@pytest.fixture(scope="module")
def probe_pin_source() -> str:
    return Path(probe_pin.__file__).read_text()


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
    assert core.contains("0.1.13") and not core.contains("0.1.12")
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


# --- the reaper: what a killed run leaves, and what is not ours to remove ----
#
# `finally` covers the exceptions. It does not cover SIGKILL, a timed-out CI step
# or a reboot, and a run that dies that way leaves one virtualenv per release with
# nothing alive to remove them. The reaper closes that, which means it deletes
# directories nobody asked it to -- so most of what follows is about what it must
# NOT touch. Every removal case is paired with a refusal, because a reaper that
# matched nothing at all would pass every refusal on its own.


def _work(root, name, *, age_hours=None, environments=False, other=False):
    """Build a directory in `root` and optionally age it. Ages via `os.utime`
    rather than by waiting, so the threshold is exercised rather than approximated."""
    made = root / name
    made.mkdir()
    if environments:
        (made / "in-1.0").mkdir()
        (made / "in-1.0" / "pyvenv.cfg").write_text("home = /usr\n")
    if other:
        (made / "notes.txt").write_text("somebody else's file\n")
    if age_hours is not None:
        when = time.time() - age_hours * 3600
        os.utime(made, (when, when))
    return made


@pytest.fixture()
def tmp_as_tempdir(tmp_path, monkeypatch):
    """Point the reaper at a directory of our own.

    The real one holds other people's work and this test deletes things."""
    monkeypatch.setattr(probe_pin.tempfile, "gettempdir", lambda: str(tmp_path))
    return tmp_path


def test_a_killed_runs_environments_are_reaped(tmp_as_tempdir) -> None:
    """The case the reaper exists for: old, ours, and full of virtualenvs."""
    left = _work(tmp_as_tempdir, probe_pin.WORK_PREFIX + "killed",
                 age_hours=24, environments=True)
    assert probe_pin.reap_abandoned() == [left.name]
    assert not left.exists()


def test_the_empty_shell_of_a_run_that_died_early_is_reaped(tmp_as_tempdir) -> None:
    """A run killed before it built anything leaves a directory with nothing in
    it. Reaped too, or the shells accumulate forever at one inode apiece."""
    left = _work(tmp_as_tempdir, probe_pin.WORK_PREFIX + "early", age_hours=24)
    assert probe_pin.reap_abandoned() == [left.name]
    assert not left.exists()


def test_a_probe_running_right_now_is_never_reaped(tmp_as_tempdir) -> None:
    """The age gate, and the reason there is one. A concurrent run's directory is
    indistinguishable from an abandoned one except by age, and reaping it would
    delete the environments out from under a live probe."""
    live = _work(tmp_as_tempdir, probe_pin.WORK_PREFIX + "live", environments=True)
    assert probe_pin.reap_abandoned() == []
    assert live.exists()


def test_the_age_gate_is_the_reason_and_not_a_reaper_that_matches_nothing(
        tmp_as_tempdir) -> None:
    """Both arms, on ONE directory. The test above passes just as well if the
    reaper is broken and matches nothing, so the same young directory is offered
    to a zero threshold here and must then be removed."""
    live = _work(tmp_as_tempdir, probe_pin.WORK_PREFIX + "live", environments=True)
    assert probe_pin.reap_abandoned() == []
    assert live.exists(), "the real threshold should have declined it"
    assert probe_pin.reap_abandoned(older_than=0) == [live.name]
    assert not live.exists(), "so the refusal above was the age and nothing else"


def test_a_directory_wearing_the_prefix_that_is_not_ours_is_left_alone(
        tmp_as_tempdir) -> None:
    """The prefix is a convention, not a proof of ownership. A directory holding
    files but no environments was made by something else."""
    theirs = _work(tmp_as_tempdir, probe_pin.WORK_PREFIX + "theirs",
                   age_hours=24, other=True)
    assert probe_pin.reap_abandoned(older_than=0) == []
    assert theirs.exists()


def test_a_file_wearing_the_prefix_is_not_removed(tmp_as_tempdir) -> None:
    """Not hypothetical: files named for this prefix have sat in /tmp alongside
    the work directories. The reaper removes trees, so a file it matched would be
    a file it deleted for no reason."""
    theirs = tmp_as_tempdir / (probe_pin.WORK_PREFIX + "ready.json")
    theirs.write_text("{}\n")
    os.utime(theirs, (time.time() - 24 * 3600,) * 2)
    assert probe_pin.reap_abandoned(older_than=0) == []
    assert theirs.exists()


def test_a_symlink_never_takes_the_reaper_outside_the_temporary_directory(
        tmp_as_tempdir) -> None:
    """The target is built to look EXACTLY reapable -- old, and holding
    environments -- so nothing but the link-ness saves it.

    This pins an OUTCOME and not the `is_symlink()` guard above it. Deleting that
    guard does not make this test red, because `shutil.rmtree` refuses a symbolic
    link on its own and the reaper swallows the error: the directory survives for
    a second reason. The guard stays because the refusal should be this tool's
    decision rather than a detail of the standard library that a later refactor
    could quietly step around -- but a test cannot claim to prove a guard whose
    removal changes nothing, so this one does not.
    """
    target = tmp_as_tempdir / "real-and-not-ours"
    target.mkdir()
    (target / "in-1.0").mkdir()
    (target / "in-1.0" / "pyvenv.cfg").write_text("home = /usr\n")
    when = time.time() - 24 * 3600
    os.utime(target, (when, when))
    link = tmp_as_tempdir / (probe_pin.WORK_PREFIX + "link")
    link.symlink_to(target)
    os.utime(link, (when, when), follow_symlinks=False)

    assert probe_pin.reap_abandoned() == []
    assert (target / "in-1.0" / "pyvenv.cfg").exists(), "reaped through the link"


def test_another_tools_directories_are_not_reaped(tmp_as_tempdir) -> None:
    """Several packages in this family run the same probe against the same /tmp.
    Each reaps only its own."""
    sibling = _work(tmp_as_tempdir, "some-other-tool-", age_hours=24,
                    environments=True)
    assert probe_pin.reap_abandoned(older_than=0) == []
    assert sibling.exists()


def test_the_prefix_has_one_definition(probe_pin_source) -> None:
    """The reaper matches on the prefix and `mkdtemp` writes it. Written twice the
    two drift, and a reaper that matches nothing reads exactly like a tool that
    never leaks -- the failure would be invisible in both directions."""
    calls = [node for node in ast.walk(ast.parse(probe_pin_source))
             if isinstance(node, ast.Call)
             and getattr(node.func, "attr", None) == "mkdtemp"]
    assert calls, "no mkdtemp call found; this check would pass over nothing"
    for call in calls:
        prefix = [kw.value for kw in call.keywords if kw.arg == "prefix"]
        assert prefix, "mkdtemp without a prefix cannot be reaped by prefix"
        assert "WORK_PREFIX" in ast.dump(prefix[0]), (
            "the prefix is written out at the mkdtemp rather than taken from "
            "WORK_PREFIX, so the reaper and the writer can disagree")


def test_the_reaper_is_actually_called(probe_pin_source) -> None:
    """Defined and never invoked is the shape this very change shipped in three
    of its five copies on the first pass: the function was present, the call site
    was not, and every test of the function still passed."""
    tree = ast.parse(probe_pin_source)
    mains = [node for node in ast.walk(tree)
             if isinstance(node, ast.FunctionDef) and node.name == "main"]
    assert mains, "no main() found; this check would pass over nothing"
    called = {getattr(node.func, "id", None)
              for main in mains for node in ast.walk(main)
              if isinstance(node, ast.Call)}
    assert "reap_abandoned" in called, (
        "main() never calls reap_abandoned, so nothing reaps and the tests above "
        "only prove the function would work if anything ran it")
