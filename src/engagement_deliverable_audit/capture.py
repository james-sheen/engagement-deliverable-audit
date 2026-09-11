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


def load(payload: Mapping[str, Any], *, stall_window_days: float) -> Export:
    """Read an `engagement-deliverable-audit/capture/1` document.

    The window is passed in rather than read from the export, and that direction
    matters: the window is what the engagement declared, so an export cannot
    change which of its own deliverables count as stalled. An export that carried
    its own window could quietly widen it and report a stalled deliverable as
    moving.
    """
    formats.require(payload, formats.CAPTURE)
    if stall_window_days <= 0:
        raise CaptureError(f"the window is {stall_window_days}; it has to be positive")
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
