"""A tracker export, read as what is actually there.

THE THREE-VALUED ANSWER LIVES IN `is_reading`, AND THE CORE'S FINDING DOES NOT.
Measured against the shared core: a point whose `reading` is a number and whose
`is_reading` is false moves the `present_not_reading` COUNT and produces no
finding at all; only `reading is None` produces `declared_unreadable`. The two
can even disagree -- a point with `reading: None` and `is_reading: True` is
counted as reading and reported unreadable in the same report.

So this adapter keeps the number. `reading` carries days since the last
transition whatever the verdict, because that number is the evidence a reader
acts on, and throwing it away to make a shared finding fire would trade evidence
for a kind name. The verdict is carried by `is_reading`, the reason by `state`,
and the findings this domain owns are emitted through `capture_findings` in the
vocabulary and scored by this package's own exit contract -- which it has to be
anyway, because the core does not score a vertical's own findings.

`is_enabled` is always true. Nothing in a tracker is administratively switched
off; a descoped deliverable is a change to the DECLARATION, not to the export.
The protocol says a domain where nothing can be switched off answers true, and
answering anything else here would report a change order as a tracker fault.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from . import formats


@dataclass(frozen=True)
class Tracked:
    """One deliverable as the tracker has it. A `CapturedPoint`."""

    name: str
    path: str
    reading: float | None
    is_reading: bool
    state: str | None
    owner: str | None = None
    thresholds: Mapping[Any, float] = field(default_factory=dict)
    units: str | None = "days"
    is_enabled: bool = True


@dataclass(frozen=True)
class Export:
    """One pass over the tracker. A `Capture`, plus the window it was judged against."""

    points: Sequence[Tracked]
    stall_window_days: float
    captured_at: str | None = None
    complete: bool = True
    errors: Sequence[tuple[str, str]] = ()
    exporter: str | None = None


class CaptureError(ValueError):
    """An export this package will not read, and why."""


#: WHY AN EMPTY EXPORT IS REFUSED, in one sentence every reader of one shares.
#: Judged against a declaration, a tracker that held nothing makes every declared
#: deliverable absent; compared against another export, it makes nothing change;
#: fed to the engine, it gives the engine nothing to judge. The first is a finding
#: about the engagement and the other two are clean, and all three are really a
#: fact about the EXPORT -- which is the one thing none of those answers says.
EMPTY_EXPORT = ("holds no points. A tracker export that carries nothing is one "
                "that did not run, not an engagement with no work in it, and every "
                "answer read from it would describe the engagement instead")


def problems(payload: Mapping[str, Any], *, allow_empty: bool = False) -> list[str]:
    """Why this export cannot be read as one; empty when it can.

    The structural half of `load`, asked without a window so `validate-capture`
    and `capture` put the same questions to a document that the verbs judging it
    do. A point is keyed on its `name`: one without a name was a KeyError here,
    which exits 1, and this package's contract reads 1 as findings. Refused BY
    POSITION rather than dropped, because dropping it would make the export
    smaller than the tracker and say nothing.
    """
    points = payload.get("points")
    if not isinstance(points, list):
        return [f"this export carries no points list; `points` is "
                f"{type(points).__name__}"]
    found = []
    if not points and not allow_empty:
        found.append(f"this export {EMPTY_EXPORT}")
    shapeless = [i for i, entry in enumerate(points) if not isinstance(entry, Mapping)]
    unnamed = [i for i, entry in enumerate(points) if isinstance(entry, Mapping)
               and (entry.get("name") is None or not str(entry["name"]).strip())]
    if shapeless:
        found.append(f"{_positions(shapeless, 'is not a point', 'are not points')}: "
                     f"an entry of `points` has to be a mapping carrying a name")
    if unnamed:
        found.append(f"{_positions(unnamed, 'has no name', 'have no name')}. A "
                     f"point with no name can be matched to nothing declared, and "
                     f"dropping one would make the export smaller than the tracker")
    # AN INCOMPLETE EXPORT SAYS WHAT DID NOT FINISH. `complete: false` is how an
    # export withholds absence -- a page failed, so a deliverable missing from it
    # may only be unread -- and the shared core names the first failure when it
    # reports that. One declaring itself incomplete and naming no failure reached
    # the core as an IndexError, and there is no honest reading of it: it cannot
    # say which part of the tracker went unread.
    errors = payload.get("errors") or []
    if not isinstance(errors, list):
        found.append(f"`errors` is {type(errors).__name__}; it has to be a list of "
                     f"[where, what] pairs")
        errors = []
    malformed = [i for i, error in enumerate(errors)
                 if not (isinstance(error, (list, tuple)) and len(error) == 2)]
    if malformed:
        found.append(f"errors[{malformed[0]}] is not a [where, what] pair, so the "
                     f"failure it records cannot be named")
    if not bool(payload.get("complete", True)) and not errors:
        found.append("this export says it did not finish and records no error, so "
                     "nothing says which part of the tracker went unread -- an "
                     "incomplete export has to name what failed")
    return found


def _positions(indices: Sequence[int], one: str, many: str) -> str:
    """`points[3] has no name`, or `points[3] and 9 more have no name`."""
    if len(indices) == 1:
        return f"points[{indices[0]}] {one}"
    return f"points[{indices[0]}] and {len(indices) - 1} more {many}"


def load(payload: Mapping[str, Any], *, stall_window_days: float,
         allow_empty: bool = False) -> Export:
    """Read an `engagement-deliverable-audit/capture/1` document.

    The window is passed in rather than read from the export, and that direction
    matters: the window is what the engagement declared, so an export cannot
    change which of its own deliverables count as stalled. An export that carried
    its own window could quietly widen it and report a stalled deliverable as
    moving.

    `allow_empty` is for the one reader that produces rather than judges: `draft`
    proposes a declaration from an export, and of an empty one it proposes nothing
    and says so. Every verb that judges refuses an empty export instead.
    """
    formats.require(payload, formats.CAPTURE)
    if stall_window_days <= 0:
        raise CaptureError(f"the window is {stall_window_days}; it has to be positive")
    found = problems(payload, allow_empty=allow_empty)
    if found:
        raise CaptureError("; ".join(found))
    points = []
    for entry in payload.get("points") or ():
        owner = entry.get("owner") or None
        since = entry.get("days_since_transition")
        fresh = isinstance(since, (int, float)) and float(since) <= stall_window_days
        if owner and fresh:
            state = entry.get("state")
        elif not owner:
            state = "no owner"
        else:
            state = f"no transition in {stall_window_days:g} day(s)"
        points.append(Tracked(
            name=str(entry["name"]),
            path=str(entry.get("path") or entry["name"]),
            reading=float(since) if isinstance(since, (int, float)) else None,
            is_reading=bool(owner and fresh),
            state=state,
            owner=owner,
        ))
    return Export(
        points=tuple(points),
        stall_window_days=float(stall_window_days),
        captured_at=payload.get("captured_at"),
        complete=bool(payload.get("complete", True)),
        errors=tuple(tuple(e) for e in payload.get("errors") or ()),
        exporter=_exporter_identity(payload.get("exporter") or {}),
    )


def _exporter_identity(exporter: Mapping[str, Any]) -> Any:
    """Whatever identifies the exporter, under either key.

    This value is only ever compared for EQUALITY, to decide whether two exports came
    from the same exporter and may be compared at all. It was read from
    `export_sha256` alone, and the committed Jira corpus carried sixty-four `z`
    characters there -- a field named as a digest holding a placeholder, in published
    evidence. `id` is the honest key for an identity that is not a hash; the digest key
    is still read, because it is the right name when the value really is one and
    because a capture written by 0.1.0 has to keep loading.

    Worth recording why this is not simply a content hash: two captures of the same
    engagement differ in content by design, so digesting the points would make every
    pair incomparable and turn every regression into a SKIP. The identity is of the
    EXPORTER, not of the export.
    """
    for key in ("id", "export_sha256"):
        value = exporter.get(key)
        if value:
            return value
    return None
