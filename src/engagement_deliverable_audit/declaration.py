"""A statement of work, read as the declaration of what should exist.

THE WINDOW IS A SPECIFICATION AND IT IS REQUIRED. A deliverable reads when it is
tracked with an owner and a transition inside a window, so the window is what
decides which deliverables count as stalled. It is declared per engagement,
because a two-week sprint and a nine-month build do not stall at the same rate,
and this module refuses a declaration that omits it rather than choosing a
default. A default here would be a number nobody decided, inherited by every
engagement after the first.

ONE SIGNATURE, RECORDED AS A CHOICE. The review gate takes a single
`reviewed_by` with a `reviewed_on`, matching who actually reads a statement of
work. A sibling in this family takes two, because a settlement batch is checked
by four eyes as a matter of regulation; an engagement is not, and requiring a
second name that nobody is accountable for produces a signature rather than a
review. What is NOT optional is that a person signs at all: an unreviewed
declaration is refused by every verb that would act on it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from . import formats
from .guards import source_contract


@dataclass(frozen=True)
class Source:
    """One document the declaration was derived from.

    Answers the members the core's report writer reads off each element of
    `sources`. Two of them -- `platform` and `firmware` -- are another domain's
    nouns that reached the shared schema, and there is no vocabulary hook to
    rename them, so they are answered with `None` DELIBERATELY rather than
    pressed into service. Mapping `firmware` onto a change-order number would put
    a word in the published artifact that means something else to every reader of
    it. The honest provenance is in `derived_from` and `provenance_line`.
    """

    path: str
    derived_from: str
    reviewed_by: str | None = None
    reviewed_on: str | None = None
    captured_at: str | None = None
    supplied: Sequence[str] = ()

    kind = formats.DECLARATION
    platform = None
    firmware = None
    is_downgrade = False

    def provenance_line(self) -> str:
        who = self.reviewed_by or "nobody yet"
        when = self.reviewed_on or "no date"
        return (f"{self.path}, derived from {self.derived_from}, "
                f"reviewed by {who} on {when}")


@dataclass(frozen=True)
class Deliverable:
    """One thing the statement of work says should exist. A `DeclaredPoint`."""

    name: str
    type: str | None
    display_name: str
    source: str
    disabled: bool = False
    expects_reading: bool | None = None
    is_templated: bool = False
    thresholds: Sequence[Any] = ()


@dataclass(frozen=True)
class Engagement:
    """A `DeclarationSource`, plus the window only this document can publish."""

    points: Sequence[Deliverable]
    sources: Sequence[Source]
    stall_window_days: float
    anomalies: Sequence[Any] = ()
    unreadable: Sequence[tuple[str, str]] = ()
    reviewed_by: str | None = None
    reviewed_on: str | None = None
    supersedes: str | None = None
    change_order: int = 0

    @property
    def reviewed(self) -> bool:
        return bool(self.reviewed_by) and bool(self.reviewed_on)


class DeclarationError(ValueError):
    """A declaration this package will not act on, and why."""


def load(payload: Mapping[str, Any]) -> Engagement:
    """Read an `engagement-deliverable-audit/declaration/1` document.

    Refuses rather than records, for the two things that cannot be repaired
    downstream: a missing window, because every three-valued answer depends on
    it, and a declared type outside the enumeration, because a type nobody
    recognises would be counted out silently and leave the denominator wrong.
    """
    formats.require(payload, formats.DECLARATION)
    window = payload.get("stall_window_days")
    if window is None:
        raise DeclarationError(
            "this declaration names no stall_window_days. A deliverable reads "
            "when it has an owner and a transition inside that window, so "
            "omitting it leaves every three-valued answer undefined. There is "
            "no default: a window nobody decided would be inherited by every "
            "engagement after the first")
    if not isinstance(window, (int, float)) or window <= 0:
        raise DeclarationError(
            f"stall_window_days is {window!r}; it has to be a positive number of days")

    points, source_path = [], payload.get("engagement") or "(unnamed engagement)"
    for entry in payload.get("points") or ():
        declared_type = entry.get("declared_type")
        if declared_type not in formats.DECLARED_TYPES:
            raise DeclarationError(
                f"{entry.get('id')!r} declares type {declared_type!r}, which is "
                f"not one of {', '.join(formats.DECLARED_TYPES)}. An unrecognised "
                f"type would be counted out rather than audited, so it is refused "
                f"here instead of quietly narrowing the denominator")
        text = str(entry.get("text") or "")
        points.append(Deliverable(
            name=str(entry["id"]),
            type=declared_type,
            display_name=f"{entry['id']} {text[:60]}".strip(),
            source=source_path,
            disabled=bool(entry.get("descoped")),
        ))

    sources = tuple(Source(
        path=str(s.get("path") or source_path),
        derived_from=str(s.get("derived_from") or "a statement of work"),
        reviewed_by=payload.get("reviewed_by"),
        reviewed_on=payload.get("reviewed_on"),
        captured_at=s.get("captured_at"),
        supplied=tuple(s.get("supplied") or ()),
    ) for s in payload.get("sources") or ())

    engagement = Engagement(
        points=tuple(points), sources=sources, stall_window_days=float(window),
        reviewed_by=payload.get("reviewed_by"),
        reviewed_on=payload.get("reviewed_on"),
        supersedes=payload.get("supersedes"),
        change_order=int(payload.get("change_order") or 0),
        unreadable=tuple(tuple(u) for u in payload.get("unreadable") or ()),
    )
    return engagement


def check_sources(engagement: Engagement) -> tuple[Any, ...]:
    """Ask the guard whether these sources can survive the core's JSON writer.

    NOT called by `load`, and that is the point. The guard derives its
    requirement by reading the core, so calling it here would make reading a
    statement of work depend on the core -- and Stage 1 declaring no
    dependencies is a claim this package asserts rather than describes. The
    contract only matters where the core's writer is actually used, so the check
    lives at that boundary and in the suite, not on the path a dependency-free
    Stage 1 takes.
    """
    return source_contract.problems(engagement.sources)


def staleness(engagement: Engagement, latest_change_order: int) -> tuple[Any, ...]:
    """Is this declaration the current statement of work?

    The reshaped form of a problem the sibling document verticals have a harder
    version of. Where both sides of an audit are extractions of prose, the risk is
    that a commitment nobody extracted silently leaves the denominator. Here the
    declaration is a person reading a signed contract, so that risk is a human
    omission rather than a blind spot in an instrument -- and the live risk is
    instead STALENESS: a change order signed and not yet reflected, which makes
    every verdict in the run correct against commitments that no longer hold.

    Cheap to ask, and it is asked rather than assumed.
    """
    from .guards.problem import Problem

    if latest_change_order > engagement.change_order:
        return (Problem(
            where="declaration_stale",
            what=f"this declaration is at change order {engagement.change_order} "
                 f"and the engagement is at {latest_change_order}",
            remedy="re-derive the declaration from the current statement of work "
                   "and have it signed; until then every verdict here is about "
                   "commitments that have been superseded"),)
    return ()
