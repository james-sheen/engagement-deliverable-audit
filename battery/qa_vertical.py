#!/usr/bin/env python3
"""`engagement-deliverable-audit` as a `qa-orchestrator` vertical: a tier and a referee.

**Why this is in `battery/` and not in `src/`.** It is verification apparatus. A
shipped module would make `qa-orchestrator` a dependency of a package whose job is
auditing deliverables, for the benefit of the people testing it. The core's plugin
loader takes a file, so this needs no entry point and no extra:

    qa-orchestrator --plugin battery/qa_vertical.py check battery/scenarios/orphaned-deliverable.yaml
    qa-orchestrator --plugin battery/qa_vertical.py run   battery/scenarios/orphaned-deliverable.yaml

**Every signature below was read off the installed wheel before it was written**,
and measuring changed four things a plausible reading would have got wrong:

* `presence --capture` takes ONE path, not a list. The harness hands `judge_argv`
  every capture so far; passing them all makes argparse keep the last silently, so
  this passes `captures[-1]` deliberately and says so.
* `regression` REQUIRES `--stall-window-days` and takes no declaration, so the
  window is read out of the config here. There is no second copy of the number.
* `ReportSchema.findings` is a single key, and it is read with a plain `.get()` --
  no dotted path. This tool keeps findings at the top level, so it is reachable;
  a sibling in this family keeps them nested and is not (`qa-orchestrator` #1).
* `regression --json` used to print its document and then a prose OUTCOME line.
  The harness parses the WHOLE of stdout, catches the decode error and carries on
  with NO report -- so every expectation naming an absence would have passed over
  nothing. Fixed in the tool; `tests/test_cli.py` holds the guard.

**Four verbs are registered, and the count is measured rather than assumed.** The
core ships `disable`, `drive`, `fail`, `remove`, `set` and the alias `drift`. An
entity's `value` is days since the last transition, so `remove` makes a deliverable
absent and `set` moves one back inside the window with no help from here. What the
built-ins cannot say is anything about an OWNER or a STATUS, which is where this
domain's faults live -- so `orphan`, `reassign`, `slip` and `bounce` are added, and
`register_verb` refuses a name already taken rather than shadowing it.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence

from qa_orchestrator.actions import Verb, one_of, register_verb, unregister_verb
from qa_orchestrator.substrates.memory import MemorySubstrate
from qa_orchestrator.vocabulary import (ABSENT, DISABLED, READING, ScenarioError,
                                        SubstrateUnavailable)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# Installed normally in CI and in any working env; the fallback is for a clone
# where nobody has installed it yet, so a scenario fails on its own terms rather
# than on an import.
try:
    from engagement_deliverable_audit import capture as capture_module
    from engagement_deliverable_audit import qa_memory
except ImportError:                                         # pragma: no cover
    sys.path.insert(0, str(ROOT / "src"))
    from engagement_deliverable_audit import capture as capture_module
    from engagement_deliverable_audit import qa_memory

#: The declaration the referee judges against, and the one place the window lives.
#: Module-relative on purpose: the core resolves a scenario's `config` against the
#: scenario file but passes `setup` through untouched, so a relative path in setup
#: would resolve against whoever ran the harness. `probe_qa_vertical.py` asserts
#: that each scenario's config IS this file, because the tier grades by this
#: window and the referee grades by the config's -- two files, one number.
DECLARATION = ROOT / "examples" / "engagement.fixture.json"


def _needs(condition: bool, message: str) -> None:
    if not condition:
        raise ScenarioError(message)


class EngagementSubstrate(MemorySubstrate):
    """A tracker, as a snapshot this class mutates.

    Inherits the memory tier because the faults of this domain are presence, owner
    and status -- no server to run. What it overrides is `state`, because the base
    tier calls anything with a number `reading`, and in this domain a deliverable
    with a number from six months ago is the *stalled* case this package exists to
    tell apart from the other two.
    """

    NAME = "engagement"
    name = NAME

    def __init__(self, setup: dict) -> None:
        super().__init__(setup)
        path = Path(str(setup.get("declaration") or DECLARATION))
        if not path.is_absolute():
            # Against this file, never the working directory. See DECLARATION.
            path = (ROOT / path).resolve()
        try:
            declaration = json.loads(path.read_text(encoding="utf-8"))
        except OSError as error:
            raise SubstrateUnavailable(
                f"this tier grades against the declaration's window and cannot read "
                f"{path}: {error}") from error
        window = declaration.get("stall_window_days")
        if not isinstance(window, (int, float)) or window <= 0:
            raise SubstrateUnavailable(
                f"{path} declares stall_window_days {window!r}. This tier grades a "
                f"deliverable as reading only inside that window, so it cannot "
                f"default one: a window nobody decided would make every phase here "
                f"pass for a reason nobody chose")
        self._window = float(window)
        self._declaration = path

    # ------------------------------------------------------- this domain's verbs
    def orphan(self, entity: str) -> None:
        """The owner goes away and the deliverable stays. `null`, not absent."""
        self.record(entity)["owner"] = None

    def reassign(self, entity: str, to: str) -> None:
        self.record(entity)["owner"] = to

    def slip(self, entity: str, days: float) -> None:
        """Age the last transition by `days`. Refuses a record with no transition.

        `value: null` is *no transition recorded*, which is not a transition at
        zero. Adding days to it would invent one and turn a gap in the export into
        a deliverable with a history.
        """
        record = self.record(entity)
        current = record.get("value")
        if not isinstance(current, (int, float)):
            raise SubstrateUnavailable(
                f"{entity} has no recorded transition, so it cannot slip by "
                f"{days}. A missing number is not a transition at zero")
        record["value"] = float(current) + float(days)

    def bounce(self, entity: str, to: str) -> None:
        """The ticket goes back to an earlier status, still owned and still moving."""
        self.record(entity)["state"] = to

    # ------------------------------------------------------------- observation
    def state(self, entity: str) -> str:
        """What the tracker looks like NOW, in the core's three words.

        Graded by THIS TOOL'S OWN reader rather than by a rule copied here. A
        second opinion about what counts as moving is a second thing to keep in
        step, and the copy that drifts is the one nobody runs.
        """
        if entity not in self._entities:
            known = ", ".join(sorted(self._entities)) or "(none)"
            raise SubstrateUnavailable(
                f"{self.NAME} serves the deliverables this engagement declares and "
                f"{entity!r} is not one of them: {known}. That is not `absent` -- "
                f"absent means declared and not in the tracker. This scenario is "
                f"asking about something else, another vertical's entity or a typo")
        if entity in self._gone:
            return ABSENT
        export = capture_module.load(
            qa_memory.as_capture(json.loads(Path(self.start()).read_text(
                encoding="utf-8"))),
            stall_window_days=self._window)
        for point in export.points:
            if point.name == entity:
                return READING if point.is_reading else DISABLED
        return ABSENT


# ----------------------------------------------------------------------- verbs
def _v_entity(payload: Any, where: str, captures: int) -> str:
    _needs(isinstance(payload, str) and bool(payload.strip()),
           f"{where}: orphan takes a deliverable name, got {payload!r}")
    return payload


def _v_to(verb: str):
    def validate(payload: Any, where: str, captures: int) -> dict:
        _, entity = one_of(payload, ("entity", "deliverable"), where, verb)
        _needs("to" in payload, f"{where}: {verb} needs an entity and a `to`")
        unknown = set(payload) - {"entity", "deliverable", "to"}
        _needs(not unknown, f"{where}: {verb} does not take {', '.join(sorted(unknown))}")
        return {"entity": str(entity), "to": str(payload["to"])}
    return validate


def _v_slip(payload: Any, where: str, captures: int) -> dict:
    _, entity = one_of(payload, ("entity", "deliverable"), where, "slip")
    _needs("days" in payload, f"{where}: slip needs an entity and days")
    try:
        days = float(payload["days"])
    except (TypeError, ValueError):
        raise ScenarioError(f"{where}: slip needs a number of days, got "
                            f"{payload['days']!r}") from None
    _needs(days > 0, f"{where}: slip takes a positive number of days, got {days}")
    return {"entity": str(entity), "days": days}


def _reaches(target: Any, method: str, cannot: str):
    found = getattr(target, method, None)
    if found is None:
        raise SubstrateUnavailable(f"this tier cannot {cannot}")
    return found


ORPHAN = Verb("orphan", "the owner goes away and the deliverable stays",
              _v_entity,
              apply=lambda target, payload: _reaches(
                  target, "orphan", "take the owner off a deliverable")(payload))
REASSIGN = Verb("reassign", "the deliverable moves to a different owner",
                _v_to("reassign"),
                apply=lambda target, payload: _reaches(
                    target, "reassign", "move a deliverable to another owner")(
                        payload["entity"], payload["to"]))
SLIP = Verb("slip", "the last transition ages by a number of days",
            _v_slip,
            apply=lambda target, payload: _reaches(
                target, "slip", "age a deliverable's last transition")(
                    payload["entity"], payload["days"]))
BOUNCE = Verb("bounce", "the ticket goes back to an earlier status",
              _v_to("bounce"),
              apply=lambda target, payload: _reaches(
                  target, "bounce", "change a deliverable's status")(
                      payload["entity"], payload["to"]))

VERBS = (ORPHAN, REASSIGN, SLIP, BOUNCE)


# --------------------------------------------------------------------- referee
def _capture_argv(handle: str, out: Path) -> tuple[str, ...]:
    """`capture --source qa-memory:<snapshot> --out W --print-digest`.

    The memory tier's handle is the path of the snapshot it just wrote, which is
    exactly what this tool's `qa-memory:` source reads.
    """
    return ("capture", "--source", f"qa-memory:{handle}", "--out", str(out),
            "--print-digest")


def _window_in(config: str) -> str:
    """The window, out of the declaration the referee is already judging against.

    `regression` takes no declaration and requires the window on the command line.
    Reading it here rather than writing it into the profile keeps one copy of the
    number: the declaration's.
    """
    try:
        declared = json.loads(Path(config).read_text(encoding="utf-8"))
    except OSError as error:
        raise ScenarioError(f"cannot read the config {config} to find the window "
                            f"regression needs: {error}") from None
    window = declared.get("stall_window_days")
    if not isinstance(window, (int, float)) or window <= 0:
        raise ScenarioError(
            f"{config} declares stall_window_days {window!r}, and regression "
            f"cannot run without a positive window")
    return f"{window:g}"


def _judge_argv(mode: str, configs: Sequence[str],
                captures: Sequence[Path]) -> tuple[str, ...]:
    if not configs:
        raise ScenarioError(f"{mode} needs the declaration as its config")
    if mode == "regression":
        if len(captures) < 2:
            raise ScenarioError(
                "regression compares two exports and this phase has "
                f"{len(captures)}; give the phase before it a capture too")
        return ("regression", "--before", str(captures[-2]),
                "--after", str(captures[-1]),
                "--stall-window-days", _window_in(str(configs[0])))
    # ONE capture, the latest. `--capture` is a single-value option: argparse
    # keeps the last of a repeated one without a word, so passing every capture
    # would look like a run over all of them and be a run over one.
    if not captures:
        raise ScenarioError(f"{mode} needs a capture and this phase has none")
    return (mode, "--declaration", str(configs[0]), "--capture", str(captures[-1]))


def _schema(referee):
    """DERIVED from reports this tool wrote, never from plausible names.

    Read off `presence --json` and `regression --json`:

    * `findings` -- top level in both, since the regression document was renamed
      from `changes` to match its sibling. One key is all the schema has.
    * `subject` -- `deliverable` in both. The Python objects spell it `sensor` and
      the CLI renames it on the way out; a schema written from the objects would
      name a key no document carries.
    * `text` -- `detail` first, then `kind`, both this tool's own words. Never a
      core headline: *did not finish* is the prose report's heading and appears in
      no document, so an expectation matching it would match nothing and pass.
    * `declines` -- None, measured. This tool emits no `not_checked` list at all,
      and a list-shaped field pointed at a missing key reads as *no declines* for
      ever.
    * `checked` -- None, and deliberately. The diff's `counts` has no such key, and
      adding one to a published document to satisfy a harness field would be
      changing the tool for the convenience of its grader.
    """
    return referee.ReportSchema(
        findings="findings",
        subject=("deliverable",),
        text=("detail", "kind"),
        declines=None,
        checked=None)


def _tool(referee):
    return referee.Tool(
        name="engagement-deliverable-audit",
        executable="engagement-deliverable-audit",
        install_hint="pip install 'engagement-deliverable-audit[detect]'",
        modes=("presence", "regression"),
        capture_argv=_capture_argv,
        validate_argv=lambda path: ("validate-capture", str(path)),
        judge_argv=_judge_argv,
        json_argv=lambda mode: ("--json",),
        report=_schema(referee),
        digest_pattern=r"\bsha256:[0-9a-f]{64}\b",
        configs_are_paths=True)


def register() -> str:
    from qa_orchestrator import referee, substrate

    substrate.register(EngagementSubstrate.NAME, EngagementSubstrate)
    for verb in VERBS:
        register_verb(verb)
    referee.register_tool(_tool(referee))
    return (f"referee engagement-deliverable-audit (modes presence, regression); "
            f"tier {EngagementSubstrate.NAME}; verbs "
            f"{', '.join(v.name for v in VERBS)}")


def unregister() -> None:
    from qa_orchestrator import referee, substrate

    substrate.unregister(EngagementSubstrate.NAME)
    for verb in VERBS:
        unregister_verb(verb.name)
    referee.unregister_tool("engagement-deliverable-audit")
