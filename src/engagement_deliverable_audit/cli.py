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
import datetime as dt
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
            # A harness snapshot has no clock of its own, and a capture made now IS
            # stamped now -- so defaulting to the present is recording when this ran,
            # not inventing a date. The opposite default is the one that hurts: with
            # no stamp at all, `detect` refuses the whole series, because an axiom
            # counting inside a trailing window has no reference to count from.
            # `--captured-at` remains for replaying a snapshot as of some other time.
            stamp = args.captured_at or dt.datetime.now(
                dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            payload = qa_memory.as_capture(raw, captured_at=stamp)
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


# --- detect ----------------------------------------------------------------

#: The engine reports a problem type with the indicator after a colon --
#: `frozen_series:transitions_per_week`. The floor table is keyed on the class, because
#: a floor is a decision about a kind of fault and not about which indicator happened
#: to carry it. Keyed on the whole string, every new indicator would fall to the
#: unclassified floor on the day it was declared.
def _class_of(problem_type: str) -> str:
    return str(problem_type or "").split(":", 1)[0]


def _decline_kind(decline: Any) -> str:
    """A decline's kind, which is its reason except for the one that means two things.

    `insufficient_samples` means *not yet* when the series will fill, and *never* when
    the collector is slower than the window can hold. The engine states which in the
    decline itself, so this is read rather than computed -- and the two floor at 0 and
    1, because warming ends and a cadence that can never present a floor does not.
    """
    reason = str(decline.get("reason") or "")
    if reason == "insufficient_samples" and decline.get("floor_unreachable_at_this_rate"):
        return "warmup_unreachable"
    return reason


def cmd_detect(args: argparse.Namespace) -> int:
    """Feed a series of captures to the engine and score what comes back."""
    from . import feeder

    try:
        engagement = declaration_module.load(_read(args.declaration))
    except (OSError, ValueError) as problem:
        return _refuse(str(problem))
    if not engagement.reviewed:
        return _refuse("the declaration is unreviewed; sign it before judging "
                       "anything against it")
    try:
        with open(args.model, encoding="utf-8") as handle:
            model_text = handle.read()
    except OSError as problem:
        return _refuse(f"cannot read the model {args.model}: {problem}")

    exports = []
    try:
        for path in args.capture:
            exports.append(capture_module.load(
                _read(path), stall_window_days=engagement.stall_window_days))
    except (OSError, ValueError) as problem:
        return _refuse(str(problem))

    try:
        envelope, fed = feeder.run(engagement, exports, model_text)
    except feeder.FeedError as problem:
        return _refuse(str(problem))
    except ImportError:
        return _refuse("detect needs the engine: pip install "
                       "'engagement-deliverable-audit[detect]'")

    findings = [{"kind": _class_of(f.get("problem_type")),
                 "deliverable": f.get("entity_id"),
                 "detail": f.get("reason") or f.get("problem_type")}
                for f in envelope.get("findings") or ()]
    declines = [{"kind": _decline_kind(d),
                 "deliverable": d.get("entity_id"),
                 "detail": d.get("detail") or d.get("reason"),
                 "axiom": d.get("axiom")}
                for d in envelope.get("not_checked") or ()]
    kinds = [row["kind"] for row in findings] + [row["kind"] for row in declines]
    code = exit_contract.code_for(kinds, require_complete=args.require_complete)

    if args.json:
        print(json.dumps({
            "format": formats.DETECT,
            "fed": {"deliverables": list(fed.deliverables),
                    "consultants": list(fed.consultants),
                    "ownership_edges": len(fed.edges),
                    "unowned": list(fed.unowned),
                    "derived_series": len(fed.series),
                    "captures": fed.captures},
            "findings": findings,
            "declines": declines,
            "floors": [{"kind": k, "floor": fl, "why": why}
                       for k, fl, why in exit_contract.reasons(kinds)],
            "unclassified": list(exit_contract.unclassified(kinds)),
            "exit_code": code, "verdict": MEANING[code],
        }, indent=2))
        return code

    _out(f"  fed: {fed.summary()}")
    if fed.unowned:
        _out(f"  {len(fed.unowned)} deliverable(s) fed with no owner, so the model "
             f"can see them as orphans")
    for finding in findings:
        _out(f"  {finding['kind']}: {finding['deliverable']} -- {finding['detail']}")
    for decline in declines:
        _out(f"  {decline['kind']}: {decline['deliverable']} "
             f"({decline['axiom']}) -- {decline['detail']}")
    for kind in exit_contract.unclassified(kinds):
        _out(f"  {kind} has no row in this package's floor table, so this run "
             f"could not be scored")
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

    det = verbs.add_parser("detect", help="feed a series of captures to the engine")
    det.add_argument("--declaration", required=True)
    det.add_argument("--model", required=True)
    # Repeatable, and that is the difference from `presence`. An axiom about a series
    # needs the series; one capture is a photograph. Oldest first.
    det.add_argument("--capture", required=True, action="append",
                     help="repeatable, oldest first: the history the axioms read")
    det.add_argument("--require-complete", action="store_true")
    det.add_argument("--json", action="store_true")
    det.set_defaults(run=cmd_detect)

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
