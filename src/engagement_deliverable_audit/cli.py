"""The verbs, and the one line a machine reads.

`capture` prints exactly one `OUTCOME ...` line and everything else is prose.
That is a family rule with a reason: a caller parsing output needs one place to
look, and prose that might be the answer is prose that will be parsed wrongly.

A MALFORMED DOCUMENT IS ALWAYS 2, NEVER 1. A file that could not be read has
produced no verdict, and reporting it as findings would claim a judgment nobody
made. Exit 1 means this package compared two documents and found something.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from typing import Any, Sequence

from . import capture as capture_module
from . import declaration as declaration_module
from . import exit_contract, formats, qa_memory
from .exit_contract import CLEAN, FINDINGS, INCOMPLETE

MEANING = {CLEAN: "clean", FINDINGS: "findings", INCOMPLETE: "could-not-complete"}


def _out(line: str = "") -> None:
    print(line)


def _read(path: str) -> Any:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _digest(payload: Any) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(body).hexdigest()


def _refuse(what: str) -> int:
    _out(f"  {what}")
    _out(f"OUTCOME exit={INCOMPLETE} verdict={MEANING[INCOMPLETE]}")
    return INCOMPLETE


def _key_for(engagement: Any) -> dict:
    """`display_name` -> the declared id, for the subjects the core names.

    A finding the core raises about a declared point names it `D-4 steering
    sign-off`; one raised from the capture names `D-4`, because a captured point
    has no display name to reach for. Both used to appear as subjects in the same
    document, so anything joining rows by subject saw two deliverables where there
    is one -- and a grader matching subjects for equality cannot match either
    against the other.

    The prose still prints the declared title, because a person reading a list of
    findings is helped by it. The DOCUMENT carries one spelling, and it is the key,
    because that is the thing every other row and every other verb names.
    """
    return {point.display_name: point.name for point in engagement.points
            if point.display_name and point.display_name != point.name}


# --- declare ---------------------------------------------------------------

def cmd_declare(args: argparse.Namespace) -> int:
    """Say what the declaration claims, before anything is compared against it."""
    try:
        engagement = declaration_module.load(_read(args.declaration))
    except (OSError, ValueError) as problem:
        return _refuse(str(problem))

    kinds: dict[str, int] = {}
    for point in engagement.points:
        kinds[point.type or "(none)"] = kinds.get(point.type or "(none)", 0) + 1
    _out(f"  {len(engagement.points)} declared point(s): "
         + ", ".join(f"{n} {k}" for k, n in sorted(kinds.items())))
    _out(f"  stall window: {engagement.stall_window_days:g} day(s) -- a deliverable "
         f"reads when it has an owner and a transition inside it")
    _out(f"  change order: {engagement.change_order}"
         + (f", supersedes {engagement.supersedes}" if engagement.supersedes else ""))
    descoped = [p.name for p in engagement.points if p.disabled]
    _out(f"  descoped: {', '.join(descoped) if descoped else 'none'}")
    if not engagement.reviewed:
        _out("  NOT REVIEWED: no reviewed_by and reviewed_on, so no verb will act "
             "on this declaration until a person signs it")
        return _refuse("the declaration is a candidate and not a statement")
    _out(f"  reviewed by {engagement.reviewed_by} on {engagement.reviewed_on}")
    _out(f"OUTCOME exit={CLEAN} verdict={MEANING[CLEAN]}")
    return CLEAN


# --- capture ---------------------------------------------------------------

def cmd_capture(args: argparse.Namespace) -> int:
    """Produce an export, from a harness snapshot or a file already in our format."""
    scheme, _, rest = args.source.partition(":")
    if not rest:
        return _refuse(f"--source wants <scheme>:<path>, got {args.source!r}")
    try:
        raw = _read(rest)
    except (OSError, ValueError) as problem:
        return _refuse(str(problem))

    try:
        if scheme == "qa-memory":
            payload = qa_memory.as_capture(raw, captured_at=args.captured_at)
        elif scheme == "export":
            payload = dict(formats.require(raw, formats.CAPTURE))
        else:
            return _refuse(f"unknown source scheme {scheme!r}; known: qa-memory, export")
    except ValueError as problem:
        return _refuse(str(problem))

    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    _out(f"  {len(payload['points'])} point(s) written to {args.out}")
    if args.print_digest:
        _out(f"  {_digest(payload)}")
    _out(f"OUTCOME captured exit={CLEAN} verdict={MEANING[CLEAN]}")
    return CLEAN


# --- presence --------------------------------------------------------------

def cmd_presence(args: argparse.Namespace) -> int:
    """The three-valued answer, through the shared core's diff."""
    from presence_audit import diff

    from .vertical import register

    try:
        engagement = declaration_module.load(_read(args.declaration))
    except (OSError, ValueError) as problem:
        return _refuse(str(problem))
    if not engagement.reviewed:
        return _refuse("the declaration is unreviewed; sign it before judging "
                       "anything against it")
    try:
        export = capture_module.load(
            _read(args.capture), stall_window_days=engagement.stall_window_days)
    except (OSError, ValueError) as problem:
        return _refuse(str(problem))

    register()
    report = diff.compare(engagement, export)
    kinds = [f.kind for f in report.findings]
    stale = declaration_module.staleness(engagement, args.latest_change_order) \
        if args.latest_change_order is not None else ()
    kinds += [problem.where for problem in stale]

    code = exit_contract.code_for(kinds, require_complete=args.require_complete)
    counts = dict(report.counts())
    keys = _key_for(engagement)

    if args.json:
        print(json.dumps({
            "format": formats.PRESENCE,
            "window": {"stall_window_days": engagement.stall_window_days},
            "counts": counts,
            "findings": [{"kind": f.kind,
                          "deliverable": keys.get(f.sensor, f.sensor),
                          "detail": f.detail}
                         for f in report.findings]
                        + [{"kind": p.where, "deliverable": "(declaration)",
                            "detail": p.what} for p in stale],
            "floors": [{"kind": k, "floor": fl, "why": why}
                       for k, fl, why in exit_contract.reasons(kinds)],
            "unclassified": list(exit_contract.unclassified(kinds)),
            "exit_code": code, "verdict": MEANING[code],
        }, indent=2))
        return code

    _out(f"  {counts['declared']} deliverable(s) declared; {counts['reading']} moving, "
         f"{counts['present_not_reading']} present and not moving, "
         f"{counts['declared_absent']} absent")
    for label, key in (("ceremonies", "not_a_deliverable"),
                       ("assumptions", "counted_out_assumption"),
                       ("type unrecognised", "unrecognised_type")):
        if counts.get(key):
            _out(f"  {counts[key]} {label}, counted out and never reported absent")
    for finding in report.findings:
        _out(f"  {finding.kind}: {finding.sensor} -- {finding.detail}")
    for problem in stale:
        _out(f"  {problem.where}: {problem.what}")
    for kind in exit_contract.unclassified(kinds):
        _out(f"  {kind} has no row in this package's floor table, so this run "
             f"could not be scored")
    _out(f"OUTCOME exit={code} verdict={MEANING[code]}")
    return code


# --- regression ------------------------------------------------------------

def cmd_regression(args: argparse.Namespace) -> int:
    """Two exports, compared directly. Skipped comparisons are said, not hidden."""
    from presence_audit.regression import compare_walks

    from .vertical import register

    try:
        before = capture_module.load(_read(args.before),
                                     stall_window_days=args.stall_window_days)
        after = capture_module.load(_read(args.after),
                                    stall_window_days=args.stall_window_days)
    except (OSError, ValueError) as problem:
        return _refuse(str(problem))

    register()
    report = compare_walks(before, after)
    changes = list(getattr(report, "changes", ()))
    code = FINDINGS if changes else CLEAN

    # The key is `findings` and not `changes`, and both verbs name it the same
    # thing. A regression's changes ARE its findings; `changes` stays the word
    # the prose uses. One generic name matters because a reader of this document
    # -- the grader included -- gets one key to look under for either verb, and
    # the alternative is a reader that finds none and reports agreement.
    if args.json:
        print(json.dumps({
            "format": formats.REGRESSION,
            "findings": [{"kind": c.kind, "deliverable": c.sensor, "detail": c.detail}
                         for c in changes],
            "exit_code": code, "verdict": MEANING[code],
        }, indent=2))
        return code

    if not changes:
        _out("  nothing changed between the two exports")
    for change in changes:
        _out(f"  {change.kind}: {change.sensor} -- {change.detail}")
    _out(f"OUTCOME exit={code} verdict={MEANING[code]}")
    return code


# --- validate --------------------------------------------------------------

def cmd_validate_capture(args: argparse.Namespace) -> int:
    """A recipient-side check. No declaration, no core, no judgment."""
    try:
        raw = _read(args.capture)
        formats.require(raw, formats.CAPTURE)
    except (OSError, ValueError) as problem:
        return _refuse(str(problem))
    points = raw.get("points")
    if not isinstance(points, list):
        return _refuse("this export carries no points list")
    complete = bool(raw.get("complete", True))
    _out(f"  {len(points)} point(s), complete={complete}")
    if args.print_digest:
        _out(f"  {_digest(raw)}")
    if args.require_complete and not complete:
        return _refuse("the export did not finish and --require-complete was asked for")
    _out(f"OUTCOME exit={CLEAN} verdict={MEANING[CLEAN]}")
    return CLEAN


def build_parser() -> argparse.ArgumentParser:
    from . import __version__

    parser = argparse.ArgumentParser(
        prog="engagement-deliverable-audit",
        description="Of the deliverables a statement of work declares, which are "
                    "moving, which are tracked and stalled, and which are absent.")
    parser.add_argument("--version", action="version",
                        version=f"engagement-deliverable-audit {__version__}")
    verbs = parser.add_subparsers(dest="verb", required=True)

    declare = verbs.add_parser("declare", help="what the declaration claims")
    declare.add_argument("--declaration", required=True)
    declare.set_defaults(run=cmd_declare)

    cap = verbs.add_parser("capture", help="produce an export")
    cap.add_argument("--source", required=True,
                     help="qa-memory:<path> or export:<path>")
    cap.add_argument("--out", required=True)
    cap.add_argument("--captured-at", default=None)
    cap.add_argument("--print-digest", action="store_true")
    cap.set_defaults(run=cmd_capture)

    pres = verbs.add_parser("presence", help="the three-valued answer")
    pres.add_argument("--declaration", required=True)
    pres.add_argument("--capture", required=True)
    pres.add_argument("--latest-change-order", type=int, default=None,
                      help="if given, report this declaration as stale when the "
                           "engagement has moved past it")
    pres.add_argument("--require-complete", action="store_true")
    pres.add_argument("--json", action="store_true")
    pres.set_defaults(run=cmd_presence)

    reg = verbs.add_parser("regression", help="two exports, compared directly")
    reg.add_argument("--before", required=True)
    reg.add_argument("--after", required=True)
    reg.add_argument("--stall-window-days", type=float, required=True,
                     help="required rather than defaulted: the window is what "
                          "decides which deliverables are stalled, and two "
                          "exports judged under different windows are not "
                          "comparable")
    reg.add_argument("--json", action="store_true")
    reg.set_defaults(run=cmd_regression)

    val = verbs.add_parser("validate-capture", help="recipient-side check")
    val.add_argument("capture")
    val.add_argument("--require-complete", action="store_true")
    val.add_argument("--print-digest", action="store_true")
    val.set_defaults(run=cmd_validate_capture)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
