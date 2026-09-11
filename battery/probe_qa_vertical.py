#!/usr/bin/env python3
"""Run this package's `qa-orchestrator` vertical and require every claim it makes.

Six legs, and the last three are the ones that make the other three mean anything:

1. **registration is reversible** -- `register()` then `unregister()` leaves the
   three registries as they were, AND changed them in between. A `register()` that
   quietly did nothing passes the first half of that perfectly.
2. **every scenario parses** -- `check` over all of them.
3. **every honest scenario passes** -- `run` over each, exit 0.
4. **the wrong-on-purpose scenario fails, with BOTH of its errors named.** Requiring
   only that it fails would be satisfied by a scenario broken some other way: an
   unknown verb, a missing config, a tier that would not start. Each of those
   proves nothing about whether anything is being compared.
5. **each of its two errors is independently load-bearing** -- repair one and
   exactly one mismatch remains, and repair the other and exactly the other
   remains. Two mismatches from one cause would look identical from leg 4.
6. **the tier and the referee grade against the SAME declaration** -- the tier reads
   the window out of a module-relative file and the referee reads it out of the
   scenario's `config`. Two files holding one number is how the two halves of this
   harness come to disagree about which deliverables are stalled, and neither side
   would go red.

    python3 battery/probe_qa_vertical.py

Exit 0 every leg held, 1 a leg failed, 2 the probe could not run.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCENARIOS = HERE / "scenarios"
PLUGIN = HERE / "qa_vertical.py"

HONEST = ("orphaned-deliverable", "orphaned-deliverable-detect",
          "reassigned", "status-bounced")
WRONG = "must-fail"

EXIT_CLEAN, EXIT_FAILED, EXIT_ERROR = 0, 1, 2


class CannotRun(Exception):
    """The probe could not reach a verdict. Never reported as a pass."""


def _orchestrate(*argv: str, scenario_text: str | None = None) -> subprocess.CompletedProcess:
    """Run the harness with this vertical loaded, as a person would."""
    command = [sys.executable, "-m", "qa_orchestrator.cli",
               "--plugin", str(PLUGIN), *argv]
    return subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True)


def leg_registration() -> tuple[bool, str]:
    sys.path.insert(0, str(HERE))
    sys.path.insert(0, str(ROOT / "src"))
    try:
        from qa_orchestrator import actions, referee, substrate
    except ImportError as missing:
        raise CannotRun(f"qa-orchestrator is not installed, so nothing registered "
                        f"and nothing was checked: {missing}") from missing
    import qa_vertical

    def snapshot():
        return (tuple(substrate.known()), tuple(referee.known_tools()),
                tuple(actions.known_verbs()))

    before = snapshot()
    qa_vertical.register()
    during = snapshot()
    qa_vertical.unregister()
    after = snapshot()

    if during == before:
        return False, "register() changed none of the three registries"
    if after != before:
        return False, f"unregister() left something behind: {set(after[0]) - set(before[0])}, " \
                      f"{set(after[1]) - set(before[1])}, {set(after[2]) - set(before[2])}"
    added = set(during[2]) - set(before[2])
    if added != {"orphan", "reassign", "slip", "bounce"}:
        return False, f"the verbs registered were {sorted(added)}"
    return True, f"registries restored, and {len(added)} verb(s) plus a tier and a " \
                 f"referee were added in between"


def leg_check() -> tuple[bool, str]:
    done = _orchestrate("check", *[str(p) for p in sorted(SCENARIOS.glob("*.yaml"))])
    count = len(list(SCENARIOS.glob("*.yaml")))
    if not count:
        raise CannotRun("there are no scenarios, so `check` passed over nothing")
    if done.returncode != 0:
        return False, f"check exited {done.returncode}: {done.stdout[-400:]}"
    return True, f"{count} scenario(s) parse"


def leg_honest_runs() -> tuple[bool, str]:
    for name in HONEST:
        path = SCENARIOS / f"{name}.yaml"
        if not path.exists():
            raise CannotRun(f"{path} is named here and is not on disk")
        done = _orchestrate("run", str(path))
        if done.returncode != 0:
            return False, (f"{name} exited {done.returncode}, and it is meant to "
                           f"pass:\n{done.stdout[-900:]}")
    return True, f"{len(HONEST)} scenario(s) ran green"


def _mismatches(done: subprocess.CompletedProcess) -> list[str]:
    """The harness's mismatch list, which is on STDERR, one per line.

    Measured, not assumed. Stdout carries the phase lines with every mismatch of a
    phase joined onto one `MISMATCH:` line by a semicolon; stderr carries them
    enumerated. Reading stdout gave this probe an empty list and two legs that
    failed for a reason that was about the probe.
    """
    return [line.strip()[2:].strip() for line in done.stderr.splitlines()
            if line.strip().startswith("- ")]


def leg_wrong_on_purpose() -> tuple[bool, str]:
    done = _orchestrate("run", str(SCENARIOS / f"{WRONG}.yaml"))
    if done.returncode == 0:
        return False, (f"{WRONG} passed. Either the comparator is not comparing, or "
                       f"somebody fixed the scenario that exists to be wrong")
    found = _mismatches(done)
    channels = {"referee": any("exit code" in m for m in found),
                "substrate": any("substrate state" in m for m in found)}
    if not all(channels.values()):
        silent = [name for name, seen in channels.items() if not seen]
        return False, (f"{WRONG} failed, but not in {' and '.join(silent)}: a run "
                       f"broken some other way would look the same. Mismatches "
                       f"reported: {found}")
    return True, f"failed with both channels named: {len(found)} mismatch(es)"


def leg_each_error_is_load_bearing() -> tuple[bool, str]:
    """Repair one deliberate error at a time and require exactly the other to remain.

    Two mismatches can come from one cause -- a tier that cannot start reports a
    failure in both channels. This is the check that separates them.
    """
    source = (SCENARIOS / f"{WRONG}.yaml").read_text(encoding="utf-8")
    repairs = (
        ("referee", re.sub(r"referee: \{exit: 0\}", "referee: {exit: 1}", source),
         "substrate state"),
        ("substrate", source.replace("D-2: reading", "D-2: disabled"),
         "exit code"),
    )
    scratch = SCENARIOS / "_probe-partial-repair.yaml"
    try:
        for repaired, text, must_remain in repairs:
            if text == source:
                raise CannotRun(f"the {repaired} repair changed nothing, so this leg "
                                f"is asserting over an unmodified scenario")
            scratch.write_text(text, encoding="utf-8")
            done = _orchestrate("run", str(scratch))
            found = _mismatches(done)
            if done.returncode == 0:
                return False, (f"repairing the {repaired} expectation made the whole "
                               f"scenario pass, so the other error was never doing "
                               f"any work")
            if len(found) != 1 or must_remain not in found[0]:
                return False, (f"with the {repaired} expectation repaired the "
                               f"remaining mismatch should be the {must_remain} one "
                               f"alone, got {found}")
    finally:
        scratch.unlink(missing_ok=True)
    return True, "each deliberate error fails on its own, so neither is carrying the other"


def leg_one_window() -> tuple[bool, str]:
    """The tier's declaration and every scenario's config are the same file."""
    sys.path.insert(0, str(HERE))
    import qa_vertical

    tier_reads = Path(qa_vertical.DECLARATION).resolve()
    if not tier_reads.exists():
        raise CannotRun(f"the tier grades against {tier_reads} and it is not there")
    seen = []
    for path in sorted(SCENARIOS.glob("*.yaml")):
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if not line.startswith("config:"):
                continue
            inline = line.split(":", 1)[1].strip()
            if inline:
                entries = [inline]
            else:
                # A detect scenario names TWO configs as a block list -- the
                # declaration and then the model. Reading only the inline form
                # resolved this leg to the scenario's own directory and reported a
                # disagreement that was about the parser.
                entries = []
                for following in lines[index + 1:]:
                    stripped = following.strip()
                    if stripped.startswith("- "):
                        entries.append(stripped[2:].strip())
                    elif stripped and not stripped.startswith("#"):
                        break
            if not entries:
                raise CannotRun(f"{path.name} names a config this probe cannot read")
            # THE FIRST config only. It is the declaration, and the declaration is
            # what carries the window the tier grades by; a second config is the
            # model, which the tier never reads.
            seen.append((path.name, (path.parent / entries[0]).resolve()))
    if not seen:
        raise CannotRun("no scenario names a config, so this leg compared nothing")
    wrong = [(name, str(named)) for name, named in seen if named != tier_reads]
    if wrong:
        return False, (f"the tier grades by {tier_reads} and these judge against "
                       f"something else, so the two halves can disagree about which "
                       f"deliverables are stalled with neither going red: {wrong}")
    return True, f"{len(seen)} scenario(s) judge against the file the tier reads"


LEGS = (("registration", leg_registration),
        ("check", leg_check),
        ("honest runs", leg_honest_runs),
        ("wrong on purpose", leg_wrong_on_purpose),
        ("each error load-bearing", leg_each_error_is_load_bearing),
        ("one window", leg_one_window))


def main() -> int:
    results, failed = [], False
    try:
        for name, leg in LEGS:
            held, note = leg()
            failed = failed or not held
            results.append({"leg": name, "held": held, "note": note})
            print(f"  {'ok  ' if held else 'FAIL'} {name}: {note}", file=sys.stderr)
    except CannotRun as error:
        print(f"\nprobe-qa-vertical: could not run -- {error}", file=sys.stderr)
        print(json.dumps({"code": EXIT_ERROR, "note": str(error)}, indent=2))
        return EXIT_ERROR

    code = EXIT_FAILED if failed else EXIT_CLEAN
    print(json.dumps({"code": code, "legs": results}, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
