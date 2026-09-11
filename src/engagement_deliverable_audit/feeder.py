"""Stage 2: feed the engine from a series of captures, and say exactly what was fed.

THE ENGINE IS IMPORTED INSIDE `run` AND NOWHERE ELSE, which is what lets every other
verb in this package work with it uninstalled. A bare install audits deliverables; the
engine is an extra.

Three things here are load-bearing.

**Every deliverable the capture presents is fed, not only the ones Stage 1 called
reading.** A sibling in this family feeds only what its Stage 1 saw reading, and that
is right for it: its faults are absence and silence, so a subject that is not reading
has nothing to say to a model. Here the opposite holds. The first invariant is
CONNECTIVITY over ownership, and an orphan is precisely a deliverable that is NOT
reading -- feeding only the reading ones would mean the one finding this model exists
for could never fire.

**The owner edge is fed only where the capture names an owner.** That is the whole
mechanism: an orphan is an entity with no edge, and the engine reports the missing
relationship. Inventing a placeholder owner to keep the graph tidy would silence the
finding.

**`transitions_per_week` is DERIVED here, and the derivation needs a clock.** A capture
carries the days since a deliverable's last transition; a reset of that number between
two captures IS a transition. So the series is the count of resets inside a trailing
week, one point per capture -- and every capture must carry `captured_at`, because a
derivation over a series has no reference date of its own. A reference date invented
here would be the defect this package already shipped once: a typed *now* made a real
corpus read as 100% stalled.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

WEEK = dt.timedelta(days=7)

#: The property this module derives. Named here so a reader of the model can find the
#: one indicator that is computed rather than read, and so the test that the model
#: declares nothing unfeedable has something to compare against.
DERIVED = "transitions_per_week"


class FeedError(ValueError):
    """Captures this module will not feed, and why."""


@dataclass(frozen=True)
class Fed:
    """What was put into the engine, so a report can say so rather than imply it."""

    deliverables: tuple[str, ...] = ()
    consultants: tuple[str, ...] = ()
    edges: tuple[tuple[str, str, str], ...] = ()
    series: Mapping[str, tuple[tuple[dt.datetime, float], ...]] = field(
        default_factory=dict)
    captures: int = 0
    #: Deliverables the capture presented with no owner. Fed as entities and given no
    #: edge, which is what makes them findable.
    unowned: tuple[str, ...] = ()

    def summary(self) -> str:
        return (f"{len(self.deliverables)} deliverable(s), {len(self.consultants)} "
                f"consultant(s), {len(self.edges)} ownership edge(s), "
                f"{len(self.series)} derived series over {self.captures} capture(s)")


def _moment(export: Any, which: int) -> dt.datetime:
    stamp = getattr(export, "captured_at", None)
    if not stamp:
        raise FeedError(
            f"capture {which + 1} carries no captured_at. The derived series is a "
            f"count inside a trailing week, so every capture has to say when it was "
            f"taken -- a reference date invented here would be a clock nobody set")
    try:
        return dt.datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError as error:
        raise FeedError(f"capture {which + 1} stamps itself {stamp!r}, which is not "
                        f"a date this module can read: {error}") from error


def _owner_id(owner: str) -> str:
    """A consultant's entity id. Opaque on purpose: an owner is a person."""
    return f"consultant:{owner}"


def transitions(readings: Sequence[tuple[dt.datetime, float | None]]) -> tuple[
        tuple[dt.datetime, float], ...]:
    """Resets inside a trailing week, one point per capture after the first.

    A capture says how many days since the last transition. If that number FELL
    between two captures, the deliverable moved. Counting the falls inside a week
    gives a quantity that is flat at zero for a deliverable nothing touches, which
    is what `expect_variation` asks about.

    The first capture is dropped rather than counted as zero: with nothing before it
    there is no interval to have moved in, and a zero there would be a transition
    count asserted over no elapsed time.
    """
    out: list[tuple[dt.datetime, float]] = []
    for index in range(1, len(readings)):
        moment, _ = readings[index]
        window_start = moment - WEEK
        count = 0
        for earlier in range(1, index + 1):
            then, now_value = readings[earlier]
            before_value = readings[earlier - 1][1]
            if then < window_start:
                continue
            if (isinstance(now_value, (int, float))
                    and isinstance(before_value, (int, float))
                    and now_value < before_value):
                count += 1
        out.append((moment, float(count)))
    return tuple(out)


def plan(engagement: Any, exports: Sequence[Any]) -> Fed:
    """What would be fed, without importing the engine.

    Separate from `run` so the decisions above are testable with nothing installed,
    and so a caller can print what is about to be fed before feeding it.
    """
    if not exports:
        raise FeedError("no captures were given, so there is nothing to feed and a "
                        "clean run would assert nothing")
    moments = [_moment(export, index) for index, export in enumerate(exports)]

    auditable = {point.name for point in engagement.points
                 if not point.disabled}
    readings: dict[str, list[tuple[dt.datetime, float | None]]] = {}
    owners: dict[str, str | None] = {}
    for moment, export in zip(moments, exports):
        for point in export.points:
            if point.name not in auditable:
                continue
            readings.setdefault(point.name, []).append((moment, point.reading))
            # THE LATEST CAPTURE IS THE STATE, including when the latest says nobody.
            # Recording an owner only when one is present made an owner who left
            # permanently owned: the name from an earlier capture stayed in the graph,
            # the edge was still fed, and the orphan the model exists to find could
            # not be seen. One capture has no history to go stale, so the real-data
            # run could not show this; the scenario that orphans a deliverable between
            # two captures found it on the first run.
            owners[point.name] = str(point.owner) if point.owner else None

    # A DELIVERABLE THE LATEST CAPTURE NO LONGER HOLDS IS NOT FED AT ALL.
    #
    # The rule above handles a point that is still there with `owner: null`. It does
    # NOT handle a point that has gone: nothing overwrites an entry for a name no
    # capture after it mentions, so a deliverable owned in capture 1 and absent from
    # capture 2 was fed as an owned entity with a live `owned_by` edge -- an edge to a
    # consultant, for something the tracker no longer shows. That is the phantom
    # topology the `dangling_relationship` floor exists to refuse, arrived at from the
    # other direction.
    #
    # Not fed rather than fed-as-an-orphan, and that is the decision. Feeding it with
    # no edge would report `missing_relationship`, which says *nobody owns this* about
    # something that is gone -- and Stage 1 already reports it as `declared_absent`,
    # with its own floor and the right word. Stage 2 judges the current state of things
    # that exist; absence is the other stage's finding.
    #
    # ONLY WHEN THE LATEST CAPTURE IS COMPLETE. A partial export withheld absence
    # rather than reporting it, so dropping a name missing from one would turn *we did
    # not look* into *it is gone*. With an incomplete latest capture the older state
    # stands, which is the conservative reading and the one Stage 1 takes.
    latest = exports[-1]
    if bool(getattr(latest, "complete", True)):
        present_now = {point.name for point in latest.points}
        for name in [n for n in readings if n not in present_now]:
            del readings[name]
            owners.pop(name, None)

    deliverables = tuple(sorted(readings))
    series = {name: transitions(points) for name, points in readings.items()}
    series = {name: points for name, points in series.items() if points}
    edges = tuple((name, "owned_by", _owner_id(owners[name]))
                  for name in deliverables if owners.get(name))
    consultants = tuple(sorted({_owner_id(owner) for owner in owners.values() if owner}))
    unowned = tuple(name for name in deliverables if not owners.get(name))
    return Fed(deliverables=deliverables, consultants=consultants, edges=edges,
               series=series, captures=len(exports), unowned=unowned)


@dataclass(frozen=True)
class Run:
    """One pass through the engine, and everything a caller might need from it.

    The session is kept because an attestation is built FROM it: the core's
    `build_attestation` asks the engine to attest each problem type, which needs the
    session that produced them. Returning only the envelope meant the attestation had
    to re-feed, and a second feed is a second chance to feed differently.
    """

    envelope: dict
    fed: Fed
    session: Any
    describe: dict


def run(engagement: Any, exports: Sequence[Any], model_text: str) -> Run:
    """Feed the engine and return its envelope beside a record of what went in.

    The envelope's `not_checked` is as much of the answer as its `findings`: an axiom
    that declined because the series is still short is a different fact from one that
    found nothing, and only the first is going to change with time.
    """
    from arbiter_engine.api import EngineSession, check, model_describe  # deferred

    fed = plan(engagement, exports)
    session = EngineSession()
    # EVERY WAY A MODEL CAN FAIL TO LOAD ARRIVES AS `FeedError`, so the CLI's exception
    # table stays in one place. `load_domain` calls `yaml.safe_load` unwrapped and
    # raises a bare `ValueError` for a non-mapping, and `yaml.YAMLError` does NOT
    # subclass `ValueError` -- so an unparseable model escaped `detect` as a traceback
    # and exited 1, which this package's contract reads as FINDINGS rather than as a
    # document it could not read. Caught here rather than in the CLI because the
    # engine is imported here and nowhere else, and the set of exceptions it can raise
    # is therefore this module's to know.
    try:
        session.load_model(model_text)
    except FeedError:
        raise
    except Exception as problem:                                  # noqa: BLE001
        raise FeedError(
            f"the engine would not load this model: {problem}") from problem
    for name in fed.deliverables:
        properties = {}
        points = fed.series.get(name)
        if points:
            properties[DERIVED] = points[-1][1]
        session.add_entity(name, "Deliverable", properties=properties)
    for consultant in fed.consultants:
        session.add_entity(consultant, "Consultant", properties={})
    for source, relation, target in fed.edges:
        session.add_relationship(source, relation, target)
    for name, points in fed.series.items():
        session.add_observations(name, DERIVED, list(points))

    envelope = check(session).to_dict()
    # From `model_describe` and not from `check`. The engine grew a dropped-declaration
    # leg on `check` after 0.1.10, and 0.1.10 is this package's own floor -- so a
    # reader that took it from there would have a silent hole on the oldest release it
    # claims to support. `model_describe` reports the same fact on every release in
    # the range, which is the surface a pin can rely on.
    described = model_describe(session).to_dict()
    envelope["model"] = described.get("model") or {}
    envelope["unread_properties"] = described.get("unread_properties") or []
    return Run(envelope=envelope, fed=fed, session=session, describe=described)
