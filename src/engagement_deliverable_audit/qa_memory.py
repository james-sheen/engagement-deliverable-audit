"""Read a harness snapshot as a tracker export.

WHY THIS SOURCE EXISTS. A scenario has to be able to make a deliverable stall,
lose its owner, or vanish, and do it the same way twice. A real tracker cannot be
asked for that, so the harness writes a `qa-memory/1` snapshot and this reads it
as though it were an export. The battery and the grader both drive this path;
nothing about it is a fixture for the tests alone.

THE MAPPING IS CHOSEN SO THE BUILT-IN VERBS ALREADY MEAN SOMETHING. An entity's
`value` is DAYS SINCE THE LAST TRANSITION, not the owner. That way `remove` makes
a deliverable absent, `drive` walks one from moving to stalled across captures,
and `set` moves it back -- three of the harness's own verbs, with no custom verb
needed to exercise the three states. Losing an owner is the one thing the
built-ins cannot say, so it is the verb a scenario adds.

`value: null` is *no transition recorded*, which is not the same as a transition
at zero. A missing number means the export did not carry one, and reporting that
as fresh would turn a gap in the data into a healthy deliverable.
"""

from __future__ import annotations

from typing import Any, Mapping

from . import formats

MEMORY = "qa-memory/1"


class SnapshotError(ValueError):
    """A snapshot this reader will not read, and why."""


def as_capture(snapshot: Mapping[str, Any], *, captured_at: str | None = None,
               exporter: str | None = None) -> dict:
    """Turn a `qa-memory/1` snapshot into an `…/capture/1` payload.

    Produces the payload rather than an `Export` so the result can be written to
    a file and validated by the same reader a real export goes through. A source
    that bypassed the format would be exercising a path nothing else takes.
    """
    if not isinstance(snapshot, Mapping):
        raise SnapshotError(f"expected a mapping, got {type(snapshot).__name__}")
    declared = snapshot.get("format")
    if declared != MEMORY:
        raise SnapshotError(f"this reader reads {MEMORY} and the snapshot "
                            f"declares {declared!r}")
    entities = snapshot.get("entities")
    if not isinstance(entities, Mapping):
        raise SnapshotError("the snapshot carries no entities mapping. An empty "
                            "substrate would make every declared deliverable "
                            "absent and every phase pass")

    points = []
    for name, record in entities.items():
        record = record if isinstance(record, Mapping) else {"value": record}
        value = record.get("value")
        # `owner` defaults to present. A snapshot that says nothing about owners
        # is describing a tracker where everything is owned, which is the
        # ordinary case; a scenario that wants an orphan says so explicitly.
        owner = record.get("owner", "anon")
        points.append({
            "name": str(name),
            "path": str(record.get("path") or f"qa-memory://{name}"),
            "state": record.get("state") or "In Progress",
            "owner": owner,
            "days_since_transition": value if isinstance(value, (int, float)) else None,
        })

    errors = snapshot.get("errors") or {}
    return {
        "format": formats.CAPTURE,
        "captured_at": captured_at,
        # `id`, not `export_sha256`: this value identifies the exporter and is
        # only compared for equality, and nothing here computes a hash.
        "exporter": {"id": exporter} if exporter else {},
        "complete": not errors,
        "points": points,
        "errors": [[str(where), str(what)] for where, what in errors.items()],
    }
