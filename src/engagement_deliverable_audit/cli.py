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
    # DISCLOSED AS, not REVIEWED BY, when the signature says of itself that nobody
    # signed it. Both are admitted; only the wording differs, and the wording is the
    # whole point -- a derived corpus has to fill these fields to be usable, and
    # printing `reviewed by` over one made a fixture read like a statement of work.
    if engagement.disclosure:
        _out(f"  NOT SIGNED, disclosed as {engagement.disclosure}: "
             f"{engagement.reviewed_by}")
        _out(f"  derived on {engagement.reviewed_on}")
    else:
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

    # THE DECLARATION, because `capture_findings` derives two findings from a tracker
    # row alone and the protocol hands it only the capture. Without this, a declared
    # ceremony present in the tracker came back as `orphaned_deliverable` -- see
    # `vertical.EngagementVocabulary`.
    register(engagement)
    report = diff.compare(engagement, export)

    # Counted out, and SAID. Derived from the declaration and the export directly rather
    # than from the vocabulary, so this line is a claim about the same two inputs the
    # findings are and cannot agree with a vocabulary that was registered wrong. The
    # absence side already says *counted out and never reported absent*; omitting the
    # capture side would be the silent omission this package refuses everywhere else.
    vocabulary = _vertical_vocabulary()
    counted_out = tuple(sorted(
        f"{point.name} ({point.type})" for point in engagement.points
        if not vocabulary.is_expected_live(point.type)
        and point.name in {tracked.name for tracked in export.points}))

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
            # Present in the tracker, declared as something a tracker was never
            # going to carry, and therefore not judged from its row. Stated, because
            # a consumer cannot otherwise tell this from a clean row.
            "counted_out_of_capture_findings": list(counted_out),
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
    if counted_out:
        _out(f"  {len(counted_out)} tracked and counted out of the capture findings: "
             f"{', '.join(counted_out)} -- declared as something a tracker was never "
             f"going to carry, so its row is not judged for an owner or a transition")
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


def _vertical_vocabulary():
    """This package's vocabulary, for a predicate rather than for registration."""
    from .vertical import EngagementVocabulary

    return EngagementVocabulary()


def _report_unfed(fed: Any, engagement: Any) -> None:
    """Name what the engine was not given, and say why not -- in the right noun.

    **NOT FEEDING SOMETHING IS A DECISION, and this verb used to keep it to itself.**
    A deliverable that disappears from the tracker between two captures is dropped from
    the feed -- correctly, because asserting a stale ownership edge for something the
    tracker no longer holds is a phantom topology. But the run then named it nowhere:
    measured over two captures, `detect` exited 0 and printed no line about it, so a
    `detect`-only pipeline reported CLEAN over a vanished commitment.

    **BOTH LINES SAID *DELIVERABLE* AND NEITHER SET WAS ALL DELIVERABLES.** Measured on
    the shipped fixture, `never_seen` was `A-1, C-1, D-4` -- an assumption, a ceremony
    and a milestone -- and this printed *3 declared deliverable(s) in no capture at
    all*, which is three wrong words about three names. The feed now asks Stage 1's
    `is_expected_live` which declared types a tracker was ever going to carry, so the
    ceremony and the assumption are out of the population entirely; but a MILESTONE is
    in it, and it is still not a deliverable. Filtering alone would have printed *1
    declared deliverable(s) ... D-4* and left the defect in place with a smaller
    denominator, which is why the noun is fixed here as well as the population there.

    So each name carries its declared type and the head uses `commitment`, which is
    this package's word for a thing a statement of work names whatever its kind.

    **NEITHER LINE CARRIES A FLOOR, and the reason is not the one the 0.1.2 record
    gave.** That reason was that Stage 2 fed types Stage 1 filtered out, so scoring the
    set would call a steering call a missing deliverable. True then, and the filter
    above has now removed it. The standing reason is narrower and survives: `presence`
    reports absence as `declared_absent`, with its own floor and its own word, over the
    same population. Scoring it here as well would score one fact twice and let a
    `detect` run and a `presence` run disagree about how bad the same absence is.
    """
    kinds = {point.name: point.type for point in engagement.points}

    def named(names) -> str:
        return ", ".join(f"{name} ({kinds.get(name) or 'type undeclared'})"
                         for name in names)

    if fed.vanished:
        _out(f"  {len(fed.vanished)} declared commitment(s) in an earlier capture and "
             f"not in the latest: {named(fed.vanished)} -- not fed, because the "
             f"tracker no longer holds them; absence is `presence`'s finding")
    if fed.never_seen:
        _out(f"  {len(fed.never_seen)} declared commitment(s) in no capture at all: "
             f"{named(fed.never_seen)} -- not fed; `presence` reports absence over "
             f"this same population, with its own floor")


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
        passed = feeder.run(engagement, exports, model_text)
    except feeder.FeedError as problem:
        return _refuse(str(problem))
    except ImportError:
        return _refuse("detect needs the engine: pip install "
                       "'engagement-deliverable-audit[detect]'")

    envelope, fed = passed.envelope, passed.fed
    findings = [{"kind": _class_of(f.get("problem_type")),
                 "deliverable": f.get("entity_id"),
                 "detail": f.get("reason") or f.get("problem_type")}
                for f in envelope.get("findings") or ()]
    declines = [{"kind": _decline_kind(d),
                 "deliverable": d.get("entity_id"),
                 "detail": d.get("detail") or d.get("reason"),
                 "axiom": d.get("axiom")}
                for d in envelope.get("not_checked") or ()]
    # THE ENGINE IS ASKED WHETHER IT READ THE MODEL, AND `detect` DID NOT ASK.
    #
    # Measured, and the worst thing found in this package: a model declaring an axiom
    # the engine does not recognise -- `axioms: [NOPE]` -- loads, and the engine says
    # `unknown axiom 'NOPE' in domain file - skipped` on stderr and drops the
    # declaration. Nothing was judged, so there are no findings and no declines, and
    # `code_for([])` is CLEAN by design. The run reported exit 0 over a model none of
    # which was applied.
    #
    # `gate` catches exactly this and `detect` never called it: one side owned
    # validating a model and the other owned running it, so no test on either side
    # could fail. The check costs nothing here -- `feeder.run` already returns the
    # `model_describe` payload, because the attestation needs it.
    # IMPORTED UNCONDITIONALLY, and the first version of this wrapped it in
    # `except ImportError: pass`. That branch could not fire -- `describe_gate` imports
    # only `typing` and a sibling module, and this line is reached only after
    # `feeder.run` has already imported the engine. Worse than dead: if it ever HAD
    # fired it would leave `unread` empty and let the run report clean, which is the
    # defect this check exists to close, and `describe_gate`'s own docstring names that
    # shape -- a guard that defaults to *nothing unreachable* reports nothing forever.
    # An import failure here is a packaging defect in this wheel and should say so.
    from .guards import describe_gate

    unread = describe_gate.problems(passed.describe)

    kinds = ([row["kind"] for row in findings] + [row["kind"] for row in declines]
             + ["model_not_read"] * bool(unread))
    code = exit_contract.code_for(kinds, require_complete=args.require_complete)

    if args.attest_out:
        try:
            from arbiter_engine.api import attest as attest_fn  # deferred
            from presence_audit.attestation import build_attestation
        except ImportError as missing:                            # pragma: no cover
            return _refuse(f"an attestation needs the engine and the core: {missing}")
        # The builder reads members off its `manifest` that the Vocabulary protocol
        # does not declare, so the conformance kit cannot see the requirement and
        # `None` fails halfway through writing the artifact. What it reads is DERIVED
        # from its own source rather than transcribed -- see `attestation_manifest`.
        from .attestation_manifest import EngagementManifest

        artifact = build_attestation(
            passed.session, envelope, passed.describe, EngagementManifest(),
            target=args.attest_target or str(args.declaration), attest_fn=attest_fn)
        # THIS RUN'S OWN CODE, BESIDE THE CORE'S KEYS. The core's format carries no
        # verdict, and its `not_checked` copies four fields -- so a decline the engine
        # flagged `floor_unreachable_at_this_rate` arrives indistinguishable from
        # ordinary warming, and `warmup_unreachable` (floor 1) cannot be recovered from
        # the artifact. Recording the code keeps the distinction readable; `attest`
        # composes it with its own scoring using `max`, so this can raise a verdict and
        # never lower one. Measured: `validate_attestation` accepts extra keys, with two
        # controls proving it still rejects a mangled format and a missing list.
        artifact["exit_code"] = code
        # THE DECLARED SLOT, now that there is one. This package invented
        # `verdict` as a bare string because the format carried nowhere to put a
        # conclusion, and said so when reporting it: a slot nobody declared is a
        # slot everybody spells differently. `presence-audit` 0.1.8 declares the
        # block -- `{exit_code, meaning, scored_by}` -- and its validator refuses
        # a `verdict` that is not an object, so the invented spelling is now a
        # refusal rather than an extra key.
        #
        # `scored_by` is required there and is the honest half: the code is this
        # package's claim, not the core's, and the core asserts only that the
        # number is expressible and that the word beside it matches.
        #
        # Both shapes are written across the pinned range. `exit_code` stays at
        # the top level because that is what this package's own `attest` reader
        # composes with, and the validator has always tolerated extra keys.
        from presence_audit import attestation as _pa_attestation
        from . import __version__
        block = getattr(_pa_attestation, "verdict_block", None)
        artifact["verdict"] = (
            block(code, scored_by=f"engagement-deliverable-audit {__version__}")
            if callable(block) else MEANING[code])
        with open(args.attest_out, "w", encoding="utf-8") as handle:
            json.dump(artifact, handle, indent=2)
            handle.write("\n")
        if not args.json:
            _out(f"  attestation written to {args.attest_out}")

    if args.json:
        print(json.dumps({
            "format": formats.DETECT,
            "fed": {"deliverables": list(fed.deliverables),
                    "consultants": list(fed.consultants),
                    "ownership_edges": len(fed.edges),
                    "unowned": list(fed.unowned),
                    "derived_series": len(fed.series),
                    "captures": fed.captures},
            # Declared, in scope, and NOT fed. Two keys rather than one, because a
            # deliverable that disappeared mid-engagement and one the tracker never
            # carried are different facts. Unfloored here on purpose -- see
            # `_report_unfed`.
            "not_fed": {"vanished": list(fed.vanished),
                        "never_seen": list(fed.never_seen)},
            "findings": findings,
            "declines": declines,
            "unread_model": [{"where": p.where, "what": p.what} for p in unread],
            "floors": [{"kind": k, "floor": fl, "why": why}
                       for k, fl, why in exit_contract.reasons(kinds)],
            "unclassified": list(exit_contract.unclassified(kinds)),
            "exit_code": code, "verdict": MEANING[code],
        }, indent=2))
        return code

    _out(f"  fed: {fed.summary()}")
    _report_unfed(fed, engagement)
    for problem in unread:
        _out(f"  model_not_read: {problem.where} -- {problem.what}")
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


# --- draft -----------------------------------------------------------------

def cmd_draft(args: argparse.Namespace) -> int:
    """Propose a declaration from a tracker export, and refuse to call it reviewed.

    A person writing a declaration starts from what the tracker already holds, not
    from a blank file. So this reads a capture and proposes one point per tracked
    deliverable -- and then says, twice, what it is not.

    IT IS NOT A STATEMENT OF WORK. A tracker export contains no contract, so a
    declaration derived from one is the same records under a different name: the
    weakness this package records in its own findings about its first real-data run.
    `reviewed_by` says so on the artifact's face rather than in a docstring.

    IT CARRIES NO WINDOW. A deliverable reads when it has an owner and a transition
    inside a window, and nothing in a tracker decides that number -- so the draft
    leaves it out and `declare` refuses the result until a person supplies it. Two
    refusals, both deliberate: a draft that loaded cleanly would be a statement
    nobody made.
    """
    try:
        export = capture_module.load(_read(args.capture), stall_window_days=1.0)
    except (OSError, ValueError) as problem:
        return _refuse(str(problem))

    points = [{
        "id": point.name,
        "declared_type": "deliverable",
        "text": "",
        "basis": {"document": str(args.capture),
                  "location": point.path,
                  "quote": point.name},
    } for point in export.points]

    draft = {
        "format": formats.DECLARATION,
        "engagement": args.engagement or "(name this engagement)",
        "reviewed_by": None,
        "reviewed_on": None,
        "change_order": 0,
        "sources": [{
            "path": str(args.capture),
            "derived_from": "A TRACKER EXPORT, NOT A STATEMENT OF WORK. Every point "
                            "below is something the tracker holds. Which of them the "
                            "engagement actually owes, what each is called, and which "
                            "are milestones, ceremonies or assumptions are all "
                            "questions only the contract answers",
            "captured_at": export.captured_at,
        }],
        "window_basis": "THIS DRAFT DECLARES NO WINDOW, and declare will refuse it "
                        "until one is supplied with a basis from the engagement's own "
                        "cadence. Nothing in a tracker decides that number",
        "points": points,
    }

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(draft, handle, indent=2)
            handle.write("\n")
        _out(f"  {len(points)} point(s) proposed in {args.out}")
    else:
        print(json.dumps(draft, indent=2))
    _out("  NOT REVIEWED and NO WINDOW, both on purpose: a person has to say which of "
         "these the engagement owes, what type each is, and what window decides a stall")
    _out(f"OUTCOME exit={CLEAN} verdict={MEANING[CLEAN]}")
    return CLEAN


# --- gate ------------------------------------------------------------------

def cmd_gate(args: argparse.Namespace) -> int:
    """Refuse, by name, everything that is not ready to be judged against.

    A pipeline step rather than a second `declare`. `declare` answers about one
    document and stops at the first thing wrong with it; this takes every declaration
    a run would use, names each one that is not signed, and optionally puts the model
    through the four guards as well -- so one command answers *may this run happen*.

    Exit 2 and not 1 when something is refused. A declaration nobody signed has
    produced no verdict to report as findings, which is the rule the rest of this
    package follows for a document it could not act on.
    """
    refused: list[str] = []
    for path in args.declarations:
        try:
            engagement = declaration_module.load(_read(path))
        except (OSError, ValueError) as problem:
            refused.append(f"{path}: {problem}")
            continue
        if not engagement.reviewed:
            refused.append(f"{path}: no reviewed_by and reviewed_on, so it is a "
                           f"candidate and not a statement")
            continue
        signature = (f"NOT SIGNED, disclosed as {engagement.disclosure}"
                     if engagement.disclosure else
                     f"reviewed by {engagement.reviewed_by} on {engagement.reviewed_on}")
        _out(f"  ok  {path}: {signature}, "
             f"window {engagement.stall_window_days:g} day(s)")

    if args.model:
        try:
            import yaml

            from .guards import boundary_gate, describe_gate, model_gate
        except ImportError as missing:
            refused.append(f"{args.model}: the model gates need the engine extra "
                           f"and a YAML reader: {missing}")
        else:
            # `yaml.YAMLError` IS NOT A `ValueError`, and that is the whole reason this
            # except clause names it. PyYAML raises it for an unparseable document and
            # it subclasses `Exception` directly -- so `(OSError, ValueError)` let it
            # through as a traceback, which exits 1. Under this module's own contract 1
            # means FINDINGS, so a document nobody could read reported as a document
            # with something wrong in it. Measured on both verbs before the fix.
            try:
                with open(args.model, encoding="utf-8") as handle:
                    text = handle.read()
                model = yaml.safe_load(text)
            except (OSError, ValueError, yaml.YAMLError) as problem:
                refused.append(f"{args.model}: {problem}")
                model, text = None, None
            # A mapping is what every gate below indexes into. A list parses fine and
            # then `model_gate.problems` calls `.get` on it, which is an AttributeError
            # and the same wrong exit by another route.
            if model is not None and not isinstance(model, dict):
                refused.append(f"{args.model}: this parses to "
                               f"{type(model).__name__} and a domain model is a "
                               f"mapping, so there is nothing here to gate")
                model, text = None, None
            if model is not None:
                found = list(model_gate.problems(model))
                try:
                    from arbiter_engine.api import EngineSession  # deferred

                    session = EngineSession()
                    session.load_model(text)
                    found += list(describe_gate.silence(session))
                except ImportError:
                    refused.append(f"{args.model}: the silence gate needs the engine")
                except Exception as problem:                      # noqa: BLE001
                    refused.append(f"{args.model}: the engine refused it: {problem}")
                for problem in found:
                    refused.append(f"{args.model}:{problem.where}: {problem.what}")
                if not found:
                    _out(f"  ok  {args.model}: every declared axiom has something to "
                         f"judge against, and the engine read every key")

    if not args.declarations and not args.model:
        return _refuse("nothing was given to gate, and a clean exit over nothing is "
                       "the one answer this verb must not produce")
    if refused:
        for line in refused:
            _out(f"  REFUSED {line}")
        return _refuse(f"{len(refused)} document(s) or rule(s) refused")
    _out(f"OUTCOME exit={CLEAN} verdict={MEANING[CLEAN]}")
    return CLEAN


# --- generate --------------------------------------------------------------

def cmd_generate(args: argparse.Namespace) -> int:
    """A model and a manifest, as one pair -- and this domain's generated model is empty.

    The pair is the point. A model declares what gets fed; the manifest names
    everything excluded and why, because emitting the first without the second turns
    *we chose not to watch this* into *we forgot it exists*.

    WHAT THIS PRODUCES HERE IS AN EMPTY MODEL, and that is a measurement rather than a
    shortfall. Generation derives indicators from thresholds a declaration carries, and
    a deliverable carries a due date and an owner -- not a threshold. The declaration
    format has no key for one, so every point is excluded as `no_thresholds` and the
    generated model declares nothing. The model that actually runs is hand-written,
    which is recorded here rather than left for a reader to infer from an empty file.
    """
    try:
        engagement = declaration_module.load(_read(args.declaration))
    except (OSError, ValueError) as problem:
        return _refuse(str(problem))

    excluded, modelled = [], []
    for point in engagement.points:
        if point.disabled:
            excluded.append({"indicator": point.name, "scope": "indicator",
                             "reason": "descoped",
                             "detail": "removed by change order, so the model is not "
                                       "asked about it"})
            continue
        if point.type not in ("deliverable", "milestone"):
            excluded.append({"indicator": point.name, "scope": "indicator",
                             "reason": "not_a_deliverable",
                             "detail": f"declared {point.type}, which this domain "
                                       f"counts out rather than audits"})
            continue
        # The one branch that would add an indicator, and nothing reaches it: a
        # declaration point carries no threshold key, so there is no bound to derive.
        excluded.append({
            "indicator": point.name, "scope": "indicator", "reason": "no_thresholds",
            "detail": "a deliverable carries a due date and an owner, not a bound. "
                      "The declaration format has no threshold key, so there is "
                      "nothing to generate an indicator from"})

    model = {"domain": {
        "id": "engagement-deliverable-audit-generated",
        "name": "Generated from a declaration",
        "description": "Generated. Empty by construction: see the manifest beside it.",
        "entity_types": ["Deliverable"],
        "relationship_types": [],
        "indicators": {"Deliverable": modelled},
    }}
    manifest = {
        "format": formats.MANIFEST,
        "model": args.model_out or "(stdout)",
        "why": "A model declares what gets fed. This names everything excluded and "
               "the reason, because emitting the first without the second turns we "
               "chose not to watch this into we forgot it exists",
        "generated_indicators": len(modelled),
        "excluded": excluded,
    }

    if bool(args.model_out) != bool(args.manifest_out):
        return _refuse("the model and the manifest are written as a pair or not at "
                       "all. A model without its manifest is a claim about coverage "
                       "with the exclusions removed")
    if args.model_out:
        with open(args.model_out, "w", encoding="utf-8") as handle:
            json.dump(model, handle, indent=2)
            handle.write("\n")
        with open(args.manifest_out, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2)
            handle.write("\n")
        _out(f"  wrote {args.model_out} and {args.manifest_out}")
    else:
        print(json.dumps({"model": model, "manifest": manifest}, indent=2))

    _out(f"  {len(modelled)} indicator(s) generated, {len(excluded)} point(s) excluded")
    if not modelled:
        _out("  THE GENERATED MODEL IS EMPTY, and by construction rather than by "
             "accident: nothing a declaration carries is a threshold. The model that "
             "runs is hand-written and the manifest says which points it leaves out")
    _out(f"OUTCOME exit={CLEAN} verdict={MEANING[CLEAN]}")
    return CLEAN


# --- attest ----------------------------------------------------------------

def cmd_attest(args: argparse.Namespace) -> int:
    """Read a stored attestation back and re-report its verdict.

    The same front door a recipient uses, so the artifact is exercised as an artifact
    rather than as whatever was in memory when it was written. An attestation that
    cannot be validated is 2: it produced no verdict anybody can rely on.

    **THE VERDICT IS SCORED FROM `not_checked` AS WELL AS `findings`, and that is the
    defect this verb shipped with.** `FINDINGS if findings else CLEAN` reads only the
    first list, so the one run this package must never call clean -- no Consultant in
    the graph, CONNECTIVITY declining `missing_entity_type`, zero findings -- attested
    as `0` while `detect` on the same run exited `2`. Measured, not reasoned: `detect`
    said 2 and `attest` said 0 over the same file.

    So the artifact is scored with the same floor table `detect` uses. Two things
    follow, and both are deliberate:

    * **The reader scores, rather than trusting a number the writer put in the file.**
      A recipient holding an artifact from anywhere gets this package's floors applied
      to it, which is the whole reason the verdict is recomputed instead of read.
    * **A recorded verdict still cannot be talked DOWN, only up.** The artifact cannot
      carry everything the run knew: the core's `not_checked` copies four fields and
      `floor_unreachable_at_this_rate` is not among them, so `warmup_unreachable`
      (floor 1) is indistinguishable from `insufficient_samples` (floor 0) once
      written. `detect` therefore records its own code beside the core's keys, and
      this verb composes the two with `max`. Neither source can lower the other, and a
      disagreement is reported rather than silently resolved.
    """
    try:
        artifact = _read(args.attestation)
    except (OSError, ValueError) as problem:
        return _refuse(str(problem))
    try:
        from presence_audit.attestation import validate_attestation
    except ImportError as missing:                                # pragma: no cover
        return _refuse(f"the core is not installed, so nothing validated it: {missing}")

    broken = validate_attestation(artifact)
    if broken:
        for line in broken:
            _out(f"  INVALID {line}")
        return _refuse(f"{len(broken)} invariant(s) of the attestation format do not hold")

    findings = artifact.get("findings") or []
    not_checked = artifact.get("not_checked") or []
    _out(f"  target {artifact.get('target')}")
    _out(f"  {len(findings)} finding(s), {len(not_checked)} axiom(s) not checked, "
         f"{len(artifact.get('evidence') or [])} piece(s) of evidence")
    for entry in artifact.get("unattested") or ():
        _out(f"  unattested: {entry}")
    for entry in artifact.get("unread_feeds") or ():
        _out(f"  unread feed: {entry}")

    kinds = ([_class_of(f.get("problem_type")) for f in findings]
             + [_decline_kind(d) for d in not_checked])
    code = exit_contract.code_for(kinds, require_complete=args.require_complete)
    for kind, floor_, why in exit_contract.reasons(kinds):
        _out(f"  {kind} floors this run at {floor_}: {why}")
    for kind in exit_contract.unclassified(kinds):
        _out(f"  {kind} has no row in this package's floor table, so this artifact "
             f"could not be scored")

    # EITHER SPELLING. An artifact written from 0.1.8 on carries the declared
    # `verdict` block, and one written before it carries this package's own
    # top-level pair. A reader that knew only the second would silently stop
    # composing the recorded code the day the block landed -- and a verdict that
    # quietly stops being read is the failure this whole leg exists to prevent.
    recorded = artifact.get("exit_code")
    block = artifact.get("verdict")
    if not isinstance(recorded, int) and isinstance(block, dict):
        recorded = block.get("exit_code")
    if isinstance(recorded, int) and recorded in MEANING:
        if recorded != code:
            _out(f"  the run that wrote this recorded exit={recorded} "
                 f"({MEANING[recorded]}) and scoring the artifact here gives {code} "
                 f"({MEANING[code]}); reporting the worse of the two, because the "
                 f"artifact does not carry everything the run knew")
        code = max(code, recorded)
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
    det.add_argument("--attest-out", default=None,
                     help="write a presence-audit/attestation/1 artifact, which "
                          "`attest` reads back through the same front door a "
                          "recipient uses")
    det.add_argument("--attest-target-label", dest="attest_target", default=None,
                     help="what to call the subject in the artifact, where the "
                          "declaration's path would name something private")
    det.add_argument("--json", action="store_true")
    det.set_defaults(run=cmd_detect)

    dra = verbs.add_parser("draft", help="propose a declaration, unreviewed")
    dra.add_argument("--capture", required=True)
    dra.add_argument("--engagement", default=None)
    dra.add_argument("--out", default=None)
    dra.set_defaults(run=cmd_draft)

    gat = verbs.add_parser("gate", help="refuse what is not ready, by name")
    gat.add_argument("declarations", nargs="*")
    gat.add_argument("--model", default=None,
                     help="also put the model through the gates that read one")
    gat.set_defaults(run=cmd_gate)

    gen = verbs.add_parser("generate", help="a model and a manifest, as a pair")
    gen.add_argument("--declaration", required=True)
    gen.add_argument("--model-out", default=None)
    gen.add_argument("--manifest-out", default=None)
    gen.set_defaults(run=cmd_generate)

    att = verbs.add_parser("attest", help="re-report a stored attestation")
    att.add_argument("attestation")
    # Same meaning as on `detect`: the withheld kinds rise to 2 when the caller asked
    # for a complete answer. A recipient scoring somebody else's artifact gets the same
    # choice the run had.
    att.add_argument("--require-complete", action="store_true")
    att.set_defaults(run=cmd_attest)

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
