#!/usr/bin/env python3
"""Install every release a pin claims, and run this package against each one.

A version range is a claim about every release inside it. `presence-audit>=0.1.7,<0.2`
says this package works on 0.1.7 and on everything released under 0.2 after it. No test
suite can check that, because a suite runs against the one version the resolver picked
-- by default the newest, which is the release the claim is least likely to be wrong
about. The floor is the interesting end and it is the end nothing exercises.

So this installs each in-range release into its own throwaway environment, installs this
package from the repository beside it, and runs the suite there. It also installs the
highest release *below* the floor, because a floor that nothing below it breaks is a
floor nobody measured -- the number came from a design note rather than a run.

    python3 battery/probe_pin.py                      # every pin this package declares
    python3 battery/probe_pin.py --dist presence-audit
    python3 battery/probe_pin.py --keep               # leave the environments behind

Exit 0 every in-range release passed, 1 a declared claim is false, 2 the probe could
not run -- including when a range turns out to hold no releases at all, because
*every release passed* is true of an empty set and means nothing.

WHAT THIS DELIBERATELY DOES NOT DECIDE: whether a passing below-floor release means the
floor should drop. The pin is still true either way; `floor-not-demonstrated` says only
that this probe is not where the number came from. Lowering it needs a reason a person
supplies, so that outcome is reported loudly and exits 0.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

REPO_ROOT = Path(__file__).resolve().parents[1]

EXIT_CLEAN, EXIT_REFUTED, EXIT_ERROR = 0, 1, 2

INDEX = "https://pypi.org/pypi/{dist}/json"


class CannotRun(Exception):
    """The probe could not reach a verdict. Never reported as a pass."""


def declared_pins() -> dict[str, SpecifierSet]:
    """The pins this package declares, read out of its own `pyproject.toml`.

    Derived rather than transcribed: a second copy of `>=0.1.7` in this file would
    go on passing after somebody raised the real one.
    """
    try:
        import tomllib as toml_reader
    except ModuleNotFoundError:
        try:
            import tomli as toml_reader  # type: ignore[no-redef]
        except ModuleNotFoundError as error:
            raise CannotRun(
                "no TOML reader: tomllib arrived in 3.11, and tomli is not installed, "
                "so the pins cannot be read from the file that declares them") from error

    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        project = toml_reader.load(handle).get("project", {})

    strings: list[str] = list(project.get("dependencies", ()))
    for extra in (project.get("optional-dependencies") or {}).values():
        strings.extend(extra)
    if not strings:
        raise CannotRun("pyproject.toml declares no dependencies, so there is no pin "
                        "to probe and nothing this probe could have found")

    pins: dict[str, SpecifierSet] = {}
    for text in strings:
        requirement = Requirement(text)
        if not requirement.specifier:
            raise CannotRun(f"{requirement.name} is declared with no version specifier; "
                            "an unbounded dependency makes no claim to probe")
        pins[requirement.name] = requirement.specifier
    return pins


def declared_extras() -> tuple[str, ...]:
    """Every extra this package declares, read from the file that declares them.

    The environments below install all of them. A hardcoded list here would go on
    installing yesterday's extras, and the suite would fail in every probed
    environment for a reason that is about this probe -- which reads, from the
    outside, exactly like a floor that does not hold.
    """
    try:
        import tomllib as toml_reader
    except ModuleNotFoundError:
        import tomli as toml_reader  # type: ignore[no-redef]
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        project = toml_reader.load(handle).get("project", {})
    return tuple(sorted(project.get("optional-dependencies") or {}))


def released(dist: str) -> list[Version]:
    """Every version the index serves for `dist`, oldest first."""
    request = urllib.request.Request(
        INDEX.format(dist=dist), headers={"Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as error:
        raise CannotRun(f"cannot read the index for {dist}: {error}") from error

    versions = []
    for text in payload.get("releases", {}):
        try:
            versions.append(Version(text))
        except InvalidVersion:
            continue
    return sorted(versions)


def candidates(dist: str, pin: SpecifierSet) -> tuple[list[Version], Version | None]:
    """The in-range releases, and the highest release below the range.

    The second is what makes the floor a measurement. Without it the probe can only
    confirm the releases somebody already chose.
    """
    every = released(dist)
    in_range = [version for version in every if pin.contains(version, prereleases=False)]
    if not in_range:
        raise CannotRun(
            f"{dist}{pin} matches none of the {len(every)} released versions, so there "
            "is no release to run and a clean exit here would assert nothing")
    below = [version for version in every if version < min(in_range)]
    return in_range, (max(below) if below else None)


def _run(argv: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True)


def exercise(dist: str, version: Version, root: Path) -> dict[str, object]:
    """Install `dist==version`, install this package beside it, run the suite."""
    home = root / f"{dist}-{version}"
    made = _run([sys.executable, "-m", "virtualenv", "-q", str(home)])
    if made.returncode != 0:
        raise CannotRun(f"cannot create an environment for {dist} {version}: "
                        f"{made.stderr.strip()[:300]}")
    python = home / "bin" / "python"

    # This package, as a consumer installs it, with every extra it declares --
    # the guards need one and the grader vertical needs another, and the suite
    # imports both.
    extras = ",".join(declared_extras())
    built = _run([str(python), "-m", "pip", "install", "-q",
                  f".[{extras}]" if extras else ".", "pytest"], cwd=REPO_ROOT)
    if built.returncode != 0:
        raise CannotRun(f"cannot install this package for {dist} {version}: "
                        f"{built.stderr.strip()[-400:]}")

    # Then pin the one dependency under test. Resolution above takes the newest in
    # range, which is the case already covered; this is the whole point of the probe.
    _run([str(python), "-m", "pip", "install", "-q", f"{dist}=={version}"])

    # Assert the mutation applied. pip reports a resolver conflict on stderr and still
    # exits 0, so the only trustworthy answer is what the environment now reports.
    seen = _run([str(python), "-c",
                 f"import importlib.metadata as m; print(m.version('{dist}'))"])
    installed = seen.stdout.strip()
    if installed != str(version):
        return {"version": str(version), "state": "could-not-pin",
                "detail": f"asked for {version}, the environment reports "
                          f"{installed or 'nothing'}"}

    suite = _run([str(python), "-m", "pytest", "tests/", "-q", "--no-header",
                  "-p", "no:cacheprovider"], cwd=REPO_ROOT)
    tail = [line for line in suite.stdout.splitlines() if line.strip()][-1:]
    failed = [line for line in suite.stdout.splitlines()
              if line.startswith("FAILED") or line.startswith("ERROR")]
    return {"version": str(version),
            "state": "pass" if suite.returncode == 0 else "fail",
            "detail": (tail[0] if tail else "no output"),
            "failures": failed[:10]}


def probe(dist: str, pin: SpecifierSet, root: Path,
          sweep_below: bool = False) -> dict[str, object]:
    in_range, below = candidates(dist, pin)
    print(f"\n{dist}{pin}")
    print(f"  in range : {', '.join(str(v) for v in in_range)}")
    print(f"  below    : {below if below else '(nothing released below the floor)'}")
    if len(in_range) == 1:
        print("  note     : the range holds one release today, so *every release in "
              "range* is a claim about one")

    results = []
    for version in in_range:
        outcome = exercise(dist, version, root)
        results.append(outcome)
        print(f"  in  {version}: {outcome['state']} -- {outcome['detail']}")
        for line in outcome.get("failures") or ():
            print(f"        {line}")

    under = None
    swept: list[dict[str, object]] = []
    if below is not None:
        beneath = [v for v in released(dist) if v < min(in_range)]
        for version in (sorted(beneath, reverse=True) if sweep_below else [below]):
            outcome = exercise(dist, version, root)
            swept.append(outcome)
            print(f"  under {version}: {outcome['state']} -- {outcome['detail']}")
            for line in outcome.get("failures") or ():
                print(f"        {line}")
        under = swept[0]

    return {"dist": dist, "pin": str(pin), "in_range": results,
            "below": under, "swept": swept}


def verdicts(found: list[dict[str, object]]) -> tuple[list[str], list[str]]:
    """Return (refutations, notes)."""
    refutations, notes = [], []
    for report in found:
        dist, pin = report["dist"], report["pin"]
        for outcome in report["in_range"]:  # type: ignore[union-attr]
            if outcome["state"] == "could-not-pin":
                raise CannotRun(f"{dist} {outcome['version']}: {outcome['detail']}")
            if outcome["state"] != "pass":
                refutations.append(
                    f"{dist}{pin} claims {outcome['version']} works and it does not: "
                    f"{outcome['detail']}")
        under = report["below"]
        if under is None:
            notes.append(f"{dist}: nothing is released below the floor, so the floor "
                         "cannot be demonstrated by running anything")
        elif under["state"] == "could-not-pin":  # type: ignore[index]
            notes.append(f"{dist}: the release below the floor could not be installed, "
                         "so the floor is undemonstrated rather than wrong")
        elif under["state"] == "pass":  # type: ignore[index]
            notes.append(
                f"{dist}: floor-not-demonstrated -- {under['version']} is below the "  # type: ignore[index]
                f"declared floor and the suite passes on it, so this probe is not "
                "where that number came from")
        else:
            notes.append(
                f"{dist}: the floor holds -- {under['version']} fails and the floor "  # type: ignore[index]
                "is the first release that does not")
    for report in found:
        swept = report.get("swept") or []
        if len(swept) > 1:
            states = {str(o["version"]): o["state"] for o in swept}
            passing = [v for v, state in states.items() if state == "pass"]
            failing = [v for v, state in states.items() if state == "fail"]
            notes.append(
                f"{report['dist']}: swept {len(swept)} release(s) below the floor -- "
                f"{len(passing)} pass, {len(failing)} fail")
            ordered = [o["state"] for o in swept]          # newest first
            if "pass" in ordered and "fail" in ordered and \
                    ordered.index("pass") > ordered.index("fail"):
                notes.append(
                    f"{report['dist']}: NOT MONOTONIC -- a release fails above one "
                    "that passes, so there is no single boundary to call the floor")
    return refutations, notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dist", action="append", default=None,
                        help="probe only this distribution; repeatable")
    parser.add_argument("--keep", action="store_true",
                        help="leave the environments on disk for inspection")
    parser.add_argument("--sweep-below", action="store_true",
                        help="run every release below the floor, not just the highest. "
                             "Sweeps rather than bisects: a bisection assumes the "
                             "failure is monotonic in the version, which is the "
                             "assumption a floor is supposed to be measuring")
    args = parser.parse_args(argv)

    root = Path(tempfile.mkdtemp(prefix="probe-pin-"))
    try:
        pins = declared_pins()
        wanted = args.dist or sorted(pins)
        missing = [name for name in wanted if name not in pins]
        if missing:
            raise CannotRun(f"this package declares no pin for {', '.join(missing)}")

        found = [probe(name, pins[name], root, args.sweep_below) for name in wanted]
        refutations, notes = verdicts(found)

        print(f"\n{len(found)} pin(s) probed, "
              f"{sum(len(r['in_range']) for r in found)} in-range release(s) run")
        for note in notes:
            print(f"  note: {note}")
        for refutation in refutations:
            print(f"  REFUTED: {refutation}")
        if refutations:
            return EXIT_REFUTED
        print("  every release each pin claims was installed and passed")
        return EXIT_CLEAN
    except CannotRun as error:
        print(f"\nprobe-pin: could not run -- {error}", file=sys.stderr)
        return EXIT_ERROR
    finally:
        if args.keep:
            print(f"\nenvironments left in {root}")
        else:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
