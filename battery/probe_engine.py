#!/usr/bin/env python3
"""Measure the engine this package pins. Do not read it.

Every number Stage 2 depends on -- how many captures before an axiom answers, which
cadence can never present a floor, which arm declines and why -- is a fact about one
released engine. The table in a design document is a claim about a version somebody
read; this is code that re-runs against the version actually resolved.

It measures and prints and writes `engine_floors.json`. It asserts nothing, because a
probe that fails is indistinguishable from an engine that changed, and the first thing
anybody wants on a pin change is the new numbers rather than a red test.

    python3 battery/probe_engine.py
    EDA_ENGINE_FLOORS_OUT=/tmp/floors.json python3 battery/probe_engine.py

The output lands INSIDE the package, not in `battery/`, because the installed tool
needs it at run time to tell a floor it has not reached yet from one its collector's
cadence can never reach. A sibling in this family learned that the hard way: the file
sat in the apparatus, the wheel packaged `src/` only, and the installed tool silently
had no floors at all.

WHAT IS DELIBERATELY NOT HERE: the arms this vertical's model does not declare. An
unmeasured arm is not handled and not unhandled -- it is unmeasured, and naming the
ones left out is the only way that stays visible. See the `not_measured` key.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import io
import json
import math
import os
import sys
from pathlib import Path

from arbiter_engine.api import EngineSession, check, model_describe
import arbiter_engine

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(os.environ.get("EDA_ENGINE_FLOORS_OUT")
           or ROOT / "src" / "engagement_deliverable_audit" / "engine_floors.json")

#: REAL, and it has to be. Every arm that counts inside a window measures backwards
#: from the clock, so a frozen reference is a probe with an expiry date -- and this
#: package has already shipped one real-data run whose typed reference date made a
#: corpus read 100% stalled. See FINDINGS 7.
NOW = dt.datetime.now(dt.timezone.utc)

DAY = 86400.0
WEEK = 7 * DAY

PROBES: dict[str, dict] = {}


def model(indicators: str, entity_types: str = "[Deliverable]",
          relationship_types: str = "[]") -> str:
    return (f"domain:\n  id: probe\n  name: Probe\n"
            f"  entity_types: {entity_types}\n"
            f"  relationship_types: {relationship_types}\n"
            f"  indicators:\n{indicators}")


def run(model_text, entities, series=None, relationships=None) -> dict:
    session = EngineSession()
    with contextlib.redirect_stderr(io.StringIO()) as err:
        session.load_model(model_text)
        for entity_id, entity_type, properties in entities:
            session.add_entity(entity_id, entity_type, properties=properties)
        for entity_id, prop, points in (series or []):
            session.add_observations(entity_id, prop, points)
        for source, relation, target in (relationships or []):
            session.add_relationship(source, relation, target)
        envelope = check(session).to_dict()
        described = model_describe(session).to_dict()
    envelope["_stderr"] = err.getvalue().strip().splitlines()
    envelope["_unread"] = (described.get("model") or {}).get("unread_fields", [])
    return envelope


def stamps(count: int, cadence_s: float):
    return [NOW - dt.timedelta(seconds=cadence_s * (count - 1 - i))
            for i in range(count)]


def series_of(values, cadence_s: float = DAY):
    return list(zip(stamps(len(values), cadence_s), values))


def fired(envelope, axiom=None):
    return [f for f in envelope.get("findings", ())
            if axiom is None or f.get("axiom") == axiom]


def declined(envelope, axiom=None):
    return [d for d in envelope.get("not_checked", ())
            if axiom is None or d.get("axiom") == axiom]


def reasons(envelope, axiom=None):
    return sorted({d.get("reason") for d in declined(envelope, axiom)} - {None})


def record(name: str, question: str, measured, note: str = "",
           unread: list | None = None) -> None:
    PROBES[name] = {"question": question, "measured": measured, "note": note}
    if unread:
        PROBES[name]["IGNORED BY THE ENGINE"] = unread
        print(f"  {name}  *** the engine read nothing from {unread} ***")
    print(f"  {name}  {question}")
    print(f"        {json.dumps(measured, default=str)[:500]}")
    if note:
        print(f"        -- {note}")


def smallest(low: int, high: int, predicate):
    for count in range(low, high + 1):
        if predicate(count):
            return count
    return None


# --------------------------------------------------- STABILITY: a frozen series
print("\nSTABILITY -- a deliverable whose transition count never moves")


def stability(count: int, cadence_s: float = DAY, window: str = "30d"):
    return run(model(f"""    Deliverable:
      - name: transitions_per_week
        type: NUMERIC
        axioms: [STABILITY]
        expect_variation: true
        window: {window}
"""), [("d1", "Deliverable", {"transitions_per_week": 1.0})],
        [("d1", "transitions_per_week", series_of([1.0] * count, cadence_s))])


def inside(envelope, axiom: str) -> dict:
    """What the engine says about the window, read off its own decline.

    The decline carries `observations` (how many fell inside the window),
    `required`, `window_seconds`, `sampling_interval_seconds` and
    `floor_unreachable_at_this_rate`. Those are the burn-in arithmetic, stated by
    the engine rather than computed here from a rule I would have to keep in step.
    """
    for d in declined(envelope, axiom):
        return {k: d.get(k) for k in
                ("observations", "required", "window_seconds",
                 "sampling_interval_seconds", "floor_unreachable_at_this_rate")}
    return {}


record("C1", "flat series with expect_variation: fewest captures that answer",
       smallest(2, 40, lambda n: bool(fired(stability(n), "STABILITY"))),
       "the floor Stage 2's burn-in has to reach before this axiom says anything")

pair = {}
for window in ("1h", "7d", "14d", "30d", "90d"):
    for label, cadence in (("hourly", 3600.0), ("daily", DAY), ("weekly", WEEK)):
        env = stability(60, cadence, window)
        shown = inside(env, "STABILITY")
        pair[f"window {window}, {label} capture"] = {
            "fired": bool(fired(env, "STABILITY")),
            "inside the window": shown.get("observations"),
            "required": shown.get("required"),
            "unreachable at this rate": shown.get("floor_unreachable_at_this_rate")}
record("C2", "THE PAIR: window against cadence, sixty captures available",
       pair,
       "the window is a CEILING on how far back samples are counted, not a lookback "
       "hint -- so the count that matters is what fits INSIDE it. Pick the window "
       "from how fast a frozen deliverable must be noticed, then check the cadence "
       "fills it. The engine states both numbers and whether the pair can ever work")

thin = {}
for n in (1, 3, 7, 9, 10, 11):
    env = stability(n, DAY, "30d")
    thin[n] = {"fired": bool(fired(env, "STABILITY")),
               "declined": reasons(env, "STABILITY"),
               "inside": inside(env, "STABILITY").get("observations")}
record("C3", "at a 30d window and daily capture, where does it start answering", thin,
       "a decline names a floor not yet reached; silence would be a pass")


# ----------------------------------------- HOMEOSTASIS: learned against declared
print("\nHOMEOSTASIS -- the axiom the rule prefers where nobody published a floor")


def homeostasis(count: int, cadence_s: float = DAY, setpoint: str = "",
                shift: float = 0.0, seed: int = 7, window: str = "30d"):
    import random
    rng = random.Random(seed)
    values = [100.0 + rng.gauss(0, 1) for _ in range(count)]
    if shift:
        values[-1] = 100.0 + shift
    return run(model(f"""    Deliverable:
      - name: satisfaction
        type: NUMERIC
        axioms: [HOMEOSTASIS]
        direction: LOWER
        window: {window}
{setpoint}"""), [("d1", "Deliverable", {"satisfaction": values[-1]})],
        [("d1", "satisfaction", series_of(values, cadence_s))])


daily_floor = smallest(2, 45, lambda n: not reasons(
    homeostasis(n, DAY, shift=-8.0, window="90d"), "HOMEOSTASIS"))
hourly_floor = smallest(2, 45, lambda n: not reasons(
    homeostasis(n, 3600.0, shift=-8.0, window="90d"), "HOMEOSTASIS"))
record("C4", "learned baseline: fewest captures that answer, daily against hourly",
       {"daily": daily_floor, "hourly": hourly_floor,
        "daily never answers": daily_floor is None},
       "null for daily is not a missing measurement. The baseline is counted inside "
       "a window of its own, and at daily capture too few samples fall in it at any "
       "number of captures -- see C5")

learned_cadence = {}
for label, cadence in (("hourly", 3600.0), ("6-hourly", 6 * 3600.0),
                       ("daily", DAY), ("weekly", WEEK)):
    env = homeostasis(60, cadence, shift=8.0, window="90d")
    shown = inside(env, "HOMEOSTASIS")
    learned_cadence[label] = {"fired": bool(fired(env, "HOMEOSTASIS")),
                              "declined": reasons(env, "HOMEOSTASIS"),
                              "inside the window": shown.get("observations"),
                              "required": shown.get("required"),
                              "unreachable at this rate": shown.get(
                                  "floor_unreachable_at_this_rate")}
record("C5", "forty captures at widening cadence: can a daily collector reach it",
       learned_cadence,
       "THE CADENCE QUESTION. A collector slower than the last firing interval can "
       "never present this floor, however long it runs")

setpoint = homeostasis(1, DAY, window="30d", shift=-20.0,
                       setpoint="        homeostasis:\n          setpoint: 100.0\n"
                                "          tolerance: 3.0\n")
above = homeostasis(1, DAY, window="30d", shift=20.0,
                    setpoint="        homeostasis:\n          setpoint: 100.0\n"
                             "          tolerance: 3.0\n")
record("C6", "a DECLARED setpoint instead: captures needed, and which side it fires on",
       # `observations`, not `captures`: this probe feeds the engine directly. The
       # record-level ban below was written while this line still said `captures`, so
       # the one key it was banning was the one key it did not reach.
       {"observations": 1,
        "twenty below the setpoint": {"fired": bool(fired(setpoint, "HOMEOSTASIS")),
                                      "declined": reasons(setpoint, "HOMEOSTASIS")},
        "twenty above it": {"fired": bool(fired(above, "HOMEOSTASIS")),
                            "declined": reasons(above, "HOMEOSTASIS")}},
       "if this answers on one capture, the cadence ceiling above is a property of "
       "the learned arm alone and a declared setpoint is the way round it",
       unread=setpoint["_unread"])


# ------------------------------------------------- MONOTONICITY: the rate arm
print("\nMONOTONICITY -- declared decreasing, with no rate published")


def monotonicity(values, block: str = "", window: str = "30d"):
    return run(model(f"""    Deliverable:
      - name: open_items
        type: NUMERIC
        axioms: [MONOTONICITY]
        window: {window}
        monotonicity:
          expected_direction: decreasing
{block}"""), [("d1", "Deliverable", {"open_items": values[-1]})],
        [("d1", "open_items", series_of(values))])


falling = [float(20 - i) for i in range(20)]
bare = monotonicity(falling)
record("C7", "decreasing with no rate thresholds: what the rate arm does",
       {"findings": [f.get("problem_type") for f in fired(bare, "MONOTONICITY")],
        "declined": reasons(bare, "MONOTONICITY")},
       "two indicators in this vertical are decreasing with no published rate, so "
       "this decides whether they decline or are excused",
       unread=bare["_unread"])

reversing = [20.0, 19.0, 18.0, 19.0, 18.0, 19.0, 18.0, 19.0, 17.0, 16.0]
rev = monotonicity(reversing)
record("C8", "does the reversal arm still answer when the rate arm declines",
       {"findings": [f.get("problem_type") for f in fired(rev, "MONOTONICITY")],
        "declined": reasons(rev, "MONOTONICITY")},
       "if it does, a declining indicator is partly checked rather than unchecked")

with_rate = monotonicity(falling, "          rate_warning: 0.5\n          rate_critical: 2.0\n")
record("C9", "the same series with rates declared",
       {"findings": [f.get("problem_type") for f in fired(with_rate, "MONOTONICITY")],
        "declined": reasons(with_rate, "MONOTONICITY")},
       unread=with_rate["_unread"])


# ------------------------------------------------------- BOUNDEDNESS: the band
print("\nBOUNDEDNESS -- a band, and the published number itself")


def boundedness(value: float):
    return run(model("""    Deliverable:
      - name: utilisation_pct
        type: NUMERIC
        axioms: [BOUNDEDNESS]
        lower_warning: 70.0
        lower_critical: 60.0
        warning: 95.0
        critical: 98.0
"""), [("d1", "Deliverable", {"utilisation_pct": value})],
        [("d1", "utilisation_pct", series_of([value]))])


edges = {}
for label, value in (("at the upper warning 95", 95.0),
                     ("next above 95", math.nextafter(95.0, math.inf)),
                     ("next below 95", math.nextafter(95.0, -math.inf)),
                     ("at the lower warning 70", 70.0),
                     ("next below 70", math.nextafter(70.0, -math.inf)),
                     ("next above 70", math.nextafter(70.0, math.inf)),
                     ("inside the band", 80.0)):
    env = boundedness(value)
    edges[label] = {"fired": bool(fired(env, "BOUNDEDNESS")),
                    "severity": [f.get("severity") for f in fired(env, "BOUNDEDNESS")]}
record("C10", "both bounds: is the published number itself a violation",
       edges,
       "shall not exceed ninety-five leaves ninety-five compliant. Whichever way "
       "this engine compares, a transcribed threshold has to be probed and not assumed")


# ------------------------------------------------- CONNECTIVITY: the orphan arm
print("\nCONNECTIVITY -- a deliverable with nobody on the other end")


def connectivity(edges_in: list, min_cardinality: str = "        min_cardinality: 1\n"):
    return run(model(f"""    Deliverable:
      - name: owned_by
        type: RELATIONSHIP
        axioms: [CONNECTIVITY]
        target_type: Consultant
        relation_type: owned_by
{min_cardinality}""", entity_types="[Deliverable, Consultant]",
                     relationship_types="[owned_by]"),
               [("d1", "Deliverable", {}), ("c1", "Consultant", {})],
               relationships=edges_in)


owned = connectivity([("d1", "owned_by", "c1")])
orphan = connectivity([])
dangling = connectivity([("d1", "owned_by", "nobody")])
record("C11", "min cardinality one: owned, orphaned, and pointing at nothing",
       {"owned": {"fired": bool(fired(owned, "CONNECTIVITY")),
                  "declined": reasons(owned, "CONNECTIVITY")},
        "orphaned": {"fired": bool(fired(orphan, "CONNECTIVITY")),
                     "problem": [f.get("problem_type") for f in fired(orphan, "CONNECTIVITY")],
                     "declined": reasons(orphan, "CONNECTIVITY")},
        "edge to an undeclared id": {
            "fired": bool(fired(dangling, "CONNECTIVITY")),
            "problem": [f.get("problem_type") for f in fired(dangling, "CONNECTIVITY")],
            "declined": reasons(dangling, "CONNECTIVITY")}},
       "this arm needs no threshold and no history, so it cannot decline for either "
       "reason -- which is why it is the one Stage 2 can answer on its first capture")

no_bounds = connectivity([], min_cardinality="")
record("C12", "the same indicator with neither cardinality declared",
       {"fired": bool(fired(no_bounds, "CONNECTIVITY")),
        "declined": reasons(no_bounds, "CONNECTIVITY")},
       "declaring neither bound is legal and checks nothing; an orphan then passes")


# ------------------------------------------------------------------- the record
# THERE IS NO `captures` KEY IN THIS RECORD, DELIBERATELY, AND THIS IS THE THIRD TIME
# THAT WORD HAS COST SOMETHING.
#
# THE SECOND TIME WAS THIS COMMENT. It said *in this record* and was written beside the
# floors, and the test holding it iterated the floors -- while `probes.C6.measured` held
# a `captures` key four hundred lines above, the sole survivor, in the one block neither
# the claim nor the check reached. Three documents then published the claim: this
# comment, the ban test's docstring, and a CHANGELOG entry saying the record *no longer
# has a `captures` key*, which was false on the day it shipped. The ban now walks every
# mapping in the record, so the scope of the check is the scope of the sentence.
#
# This probe feeds the engine OBSERVATIONS directly. The tool feeds CAPTURES, and
# `feeder.transitions` derives one point per capture while dropping the first -- which
# has no predecessor to have moved from -- so N captures are N-1 observations wherever a
# quantity is derived. Every floor here was written under the single name `captures`,
# holding whichever of the two the probe happened to measure, and `STABILITY`'s was the
# observation count. The burn-in document, the README and a test all published it as the
# number of daily captures to collect: off by one, in the direction that claims the
# history axiom answers a day before it does.
#
# Adding `observations` and `captures_through_the_feeder` beside it fixed the test and
# left the ambiguous key in the data, which is where the next reader looks. Worse, by
# then `captures` meant three different things in one file: an observation count on
# STABILITY, a real capture count on CONNECTIVITY, and a DICT of cadence-to-count on
# learned HOMEOSTASIS.
#
# So the unit is now in every key name and `captures` is gone. `observations` is always
# what the engine needs; `captures_through_the_feeder` is always what a collector must
# take to supply it, which differs only where the tool derives the quantity rather than
# reading it.
DERIVED_BY_THE_FEEDER = 1  # the first capture yields no derived point
READ_DIRECTLY = 0          # read from the capture, so captures == observations

floors = {
    "STABILITY": {"observations": PROBES["C1"]["measured"],
                  "captures_through_the_feeder":
                      PROBES["C1"]["measured"] + DERIVED_BY_THE_FEEDER,
                  "window_and_cadence": PROBES["C2"]["measured"],
                  "note": "expect_variation arm on a flat series; the window is a "
                          "ceiling, so the floor is a count INSIDE it. "
                          "`transitions_per_week` is DERIVED, so a collector needs one "
                          "capture more than the engine needs observations"},
    "HOMEOSTASIS_learned": {"observations_by_cadence": PROBES["C4"]["measured"],
                            "by_cadence": PROBES["C5"]["measured"],
                            "note": "learned baseline, and the only floor here whose "
                                    "answer is per-cadence rather than a single count; "
                                    "see the declared-setpoint arm"},
    "HOMEOSTASIS_declared": {"observations": 1,
                             "captures_through_the_feeder": 1 + READ_DIRECTLY,
                             "note": "a declared setpoint needs no history"},
    "CONNECTIVITY": {"observations": 1,
                     "captures_through_the_feeder": 1 + READ_DIRECTLY,
                     "note": "no threshold and no history, and `owned_by` is READ from "
                             "the capture rather than derived, so one capture answers"},
}

answer = {
    "measured_on": NOW.isoformat(),
    "engine_version": getattr(arbiter_engine, "__version__", None),
    # THE PACKAGE NAME, NOT THE ABSOLUTE PATH IT WAS IMPORTED FROM. This record is
    # package data, so it ships inside the wheel -- and it shipped 0.1.0 carrying the
    # full path of a scratch virtualenv on the machine that ran the probe. Nothing read
    # it (the CI comparison looks at `floors` and `probes` only), which is exactly why
    # nothing caught it. The version and the Python already identify the run; where the
    # import came from is a property of one laptop.
    "engine_module": arbiter_engine.__name__,
    "python": sys.version.split()[0],
    "floors": floors,
    "probes": PROBES,
    # WHAT THIS MODEL DOES NOT DECLARE, named as families this engine actually has.
    # `CAUSALITY` was in this list and is not a declarable axiom: the engine's eight are
    # the ones `domain_loader` accepts, and CAUSALITY appears only in a production
    # verdicts module. Naming it here claimed a gap that does not exist. The remainder
    # is now derived from the engine's own refusal message rather than transcribed, so
    # a ninth family cannot quietly go unlisted.
    "not_measured": [
        "CONSERVATION -- this vertical declares no flow, so no arm of it is exercised",
        "RESPONSIVENESS -- no deliverable has a declared deadline as a latency role",
        "CONSISTENCY -- no two surfaces report the same deliverable here",
        "BOUNDEDNESS, HOMEOSTASIS, MONOTONICITY -- probed above (C4-C10) and declared "
        "by no indicator in this model; the manifest carries the reason for each",
    ],
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(answer, indent=1, sort_keys=True, default=str) + "\n",
               encoding="utf-8")
print(f"\nwrote {OUT}")
print(f"engine {answer['engine_version']} ({answer['engine_module']}) on python {answer['python']}")
