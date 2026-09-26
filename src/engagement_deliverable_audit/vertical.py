"""This domain, offered to the shared core as a registered vertical.

All fifteen members of the core's `Vocabulary`, and the three optional ones are
answered rather than left to default: a report printing `point` for a deliverable
is a report in somebody else's noun.

TWO SUBJECT SPELLINGS IN ONE REPORT, which a downstream profile has to know.
A finding the core raises about a declared point names it by `display_name` --
`D-4 the pilot report` -- because a report printing the bare pairing key leaks
it. A finding THIS vertical raises from a capture names the ticket key alone,
because `capture_findings` is handed the capture and nothing else, and a captured
point has no display name to reach for. So `D-2` and `D-4 the pilot report` can
appear as subjects in the same artifact. A consumer asserting on subjects has to
match the key as a substring rather than for equality; asserting equality would
pass on this vertical's own findings and fail on the core's.

WHAT ONLY THIS DOMAIN CAN SEE, and why it needs its own channel. A deliverable
tracked with no owner, and one whose last transition is older than the window the
engagement declared, are both present and enabled by every structural test the
core applies. The core therefore reports neither. They arrive through
`capture_findings`, and because the core's exit code scores only its own
regression kinds, they are scored by this package's exit contract instead --
measured: a capture carrying one of these returns exit 0 from the core with the
finding present in the report.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

#: Every class a declared point can fall into. `unrecognised` is last and is not
#: a type anything declares: it is where a type this vocabulary does not know
#: goes, counted and reported and never asserted about.
KINDS = ("deliverable", "milestone", "ceremony", "assumption", "unrecognised")

#: The kinds the audit is about. A ceremony is a real thing a statement of work
#: names and an assumption is a real thing it records; neither is a deliverable,
#: and counting them out is said out loud rather than done by omission.
AUDITED = ("deliverable", "milestone")


class EngagementVocabulary:
    """The fifteen members, for deliverables on an engagement.

    **`capture_findings` NEEDS THE DECLARATION AND THE PROTOCOL HANDS IT THE CAPTURE.**
    The two findings below are derived from a tracker row alone, so until this argument
    existed they fired on ANY row whose name matched a declared one -- measured on the
    shipped fixture with one row added to the tracker, `presence` reported
    `orphaned_deliverable: C-1`, *nobody owns it, so nobody is going to move it*, about
    a weekly steering call. A ceremony cannot be owned or moved, and the 0.1.2 record
    asserted the opposite of this: that Stage 1 filters on `declared_type` where the
    feeder does not. It filters `declared_absent` on it. On the capture side neither
    stage did, which is why the same conflation sat in both and no test on either could
    fail.

    The upstream hook takes one argument while its own caller holds both the
    declaration and the capture, so no vertical can do this through the protocol; filed
    upstream. Until it lands, the types arrive here at registration, from the same
    `Engagement` the caller passes to `compare` -- and the default is empty, which means
    *no declaration was supplied, so nothing can be counted out*. That is the honest
    reading rather than a safe-looking one: a silent empty default cannot suppress a
    real finding, it can only leave the old behaviour, and a test asserts the CLI
    supplies them.
    """

    def __init__(self, declared_types: Mapping[str, str | None] | None = None) -> None:
        self._declared_types = dict(declared_types or {})

    kinds = KINDS
    count_keys = {"ceremony": "not_a_deliverable",
                  "assumption": "counted_out_assumption",
                  "unrecognised": "unrecognised_type"}
    noun = ("deliverable", "deliverables")

    def count_labels(self) -> Mapping[str, tuple[str, str]]:
        return {
            "not_a_deliverable": (
                "ceremonies", "status calls and reviews; real commitments, not "
                "things that get delivered"),
            "counted_out_assumption": (
                "assumptions", "what the engagement was priced on; a fact about "
                "the client, not a thing to deliver"),
            "unrecognised_type": (
                "type unrecognised", "not classified either way; NOT counted as absent"),
        }

    def classify(self, declared_type: str | None) -> str:
        return declared_type if declared_type in KINDS[:-1] else "unrecognised"

    def is_auditable(self, kind: str) -> bool:
        return kind in AUDITED

    def is_expected_live(self, declared_type: str | None) -> bool:
        """A ceremony and an assumption can never be absent, because neither is
        ever expected to appear in a tracker. Without this they would be reported
        as missing deliverables on every run."""
        return declared_type in AUDITED

    def template_pattern(self, declared_name: str):
        """Ticket keys are literal. Returning a matcher that wildcarded would let
        one declared deliverable satisfy itself against any ticket at all."""
        return None

    def same_point(self, old: Any, new: Any) -> bool:
        """The ticket key is the point. A deliverable legitimately changes title,
        owner, board and status across exports; if the key is the same it is the
        same commitment."""
        return getattr(old, "name", None) == getattr(new, "name", None)

    def captures_comparable(self, before: Any, after: Any) -> bool:
        """Only two complete exports from the same exporter compare.

        A difference between two exporters is not a change in the engagement, and
        reporting it as one would put the tooling's own churn in front of a
        partner. False here means SKIPPED, never ran-and-found-nothing.
        """
        return (bool(getattr(before, "complete", False))
                and bool(getattr(after, "complete", False))
                and getattr(before, "exporter", None) == getattr(after, "exporter", None))

    def point_changes(self, old: Any, new: Any, *, comparable: bool = False):
        from presence_audit.regression import Change  # deferred: optional extra

        if not comparable:
            return ()
        out = []
        if getattr(old, "owner", None) and not getattr(new, "owner", None):
            out.append(Change(kind="owner_removed", point=new.name,
                              detail=f"{old.owner} was the owner and now nobody is",
                              before_path=old.path, after_path=new.path))
        if getattr(old, "is_reading", None) and not getattr(new, "is_reading", None):
            out.append(Change(kind="stopped_moving", point=new.name,
                              detail=f"was moving, now {new.state}",
                              before_path=old.path, after_path=new.path))
        if (getattr(old, "state", None) != getattr(new, "state", None)
                and getattr(old, "is_reading", None) and getattr(new, "is_reading", None)):
            out.append(Change(kind="status_bounced", point=new.name,
                              detail=f"{old.state} -> {new.state}",
                              before_path=old.path, after_path=new.path))
        return tuple(out)

    def capture_changes(self, before: Any, after: Any):
        from presence_audit.regression import Change  # deferred: optional extra

        out = []
        if getattr(before, "exporter", None) != getattr(after, "exporter", None):
            out.append(Change(kind="exporter_changed", point="(export)",
                              detail="the two exports came from different exporter pins"))
        if getattr(before, "stall_window_days", None) != getattr(after, "stall_window_days", None):
            out.append(Change(kind="window_changed", point="(export)",
                              detail=f"the stall window moved from "
                                     f"{before.stall_window_days:g} to "
                                     f"{after.stall_window_days:g} day(s), so the "
                                     f"two verdicts were reached under different rules"))
        return tuple(out)

    @property
    def regression_kinds(self):
        """Which of this domain's OWN finding kinds mean something got worse.

        `capture_findings` below produces two the core cannot see, and until
        `presence-audit` 0.1.8 the core scored findings against a frozen set of
        its own kinds -- so a domain finding could sit in the report and compose
        a clean verdict. This package was not bitten, because `cmd_detect` scores
        with the floor table rather than with the core's code; a third party
        asking the CORE for a diff over this vertical was.

        DERIVED from that same floor table, not listed here. Two records of one
        decision drift, and the one that drifts is the copy nobody edits when the
        floor moves. What this answers is exactly the kinds this vocabulary emits
        that its own table floors at FINDINGS.
        """
        from .exit_contract import FINDINGS, FLOORS
        return tuple(sorted(
            kind for kind in ("orphaned_deliverable", "stalled_deliverable")
            if FLOORS.get(kind, (None,))[0] == FINDINGS))

    def capture_findings(self, capture: Any):
        from presence_audit.diff import Finding  # deferred: optional extra

        out = []
        for point in getattr(capture, "points", ()):
            # Declared, and declared as something a tracker was never going to carry.
            # Not silence: `cmd_presence` counts these out in its own line, the way the
            # absence side already says *counted out and never reported absent*.
            if point.name in self._declared_types and not self.is_expected_live(
                    self._declared_types[point.name]):
                continue
            if getattr(point, "owner", None) is None:
                out.append(Finding(
                    kind="orphaned_deliverable", point=point.name,
                    detail="tracked and nobody owns it, so nobody is going to move it",
                    live_path=point.path))
            elif not point.is_reading:
                since = point.reading
                out.append(Finding(
                    kind="stalled_deliverable", point=point.name,
                    detail=f"owned and not moving: last transition "
                           f"{'unknown' if since is None else format(since, 'g') + ' day(s)'} ago, "
                           f"against a declared window of "
                           f"{capture.stall_window_days:g} day(s)",
                    live_path=point.path))
        return tuple(out)

    def peer_groups(self, declaration: Any):
        """A CLAIM, not a gap. Two deliverables are two things: there is no pair
        here that measures one quantity twice, so there is nothing for the
        generator to pair and nothing an operator could declare redundant. If a
        rule could derive the pairs it would not know them."""
        return ()

    def report_sections(self):
        return {"window": lambda capture: {
            "stall_window_days": getattr(capture, "stall_window_days", None),
            "stalled": sum(1 for p in getattr(capture, "points", ())
                           if p.owner is not None and not p.is_reading),
            "orphaned": sum(1 for p in getattr(capture, "points", ())
                            if p.owner is None)}}


def register(engagement: Any = None) -> str:
    """Install this vocabulary. Pass the declaration when the caller has one.

    `regression` genuinely has none -- it compares two captures and never reads a
    declaration -- and that path does not reach `capture_findings` at all. `presence`
    always has one, and it is the only path that does.
    """
    from presence_audit import vocabulary as _vocabulary  # deferred: optional extra

    _vocabulary.register(EngagementVocabulary(
        {point.name: point.type for point in getattr(engagement, "points", ())}))
    return ("engagement: deliverable kinds, a declared stall window, and the two "
            "findings only a tracker export shows")
