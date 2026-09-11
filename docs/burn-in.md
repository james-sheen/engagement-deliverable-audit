# Stage 2's kill criterion, and the arithmetic that sizes it

Stage 1 answers from one capture: a declaration, an export, and three states. Stage 2
asks a different kind of question -- *has this stopped moving*, *is this drifting* --
and those are questions about a series. A series has to be collected before anything
can be judged, and how long that takes is arithmetic, not opinion.

This file is written before the Stage 2 build, which is the only time a kill criterion
means anything. Every number in it comes from `battery/probe_engine.py` run against
the engine this package pins, and the probe writes
`src/engagement_deliverable_audit/engine_floors.json` so the installed tool can read
the same numbers at run time rather than carrying a second copy of them.

## The criterion

> **If fewer than both of the declared invariants produce a judgment on real captures,
> Stage 2 ships as observation-only: the model is published, the collector runs, the
> history axioms are declared and reported as warming, and no exit code is computed
> from them. They move to a portfolio layer if they ever move at all.**

**This is a restatement, and the first version is kept here because a criterion edited
after measurement is worth nothing if the edit is invisible.** It first read *fewer
than three of the declared invariants*, written against a model that declared six.
Four of those six turned out to be unfeedable -- they named quantities a
project-management system might export and this package's capture does not -- so they
moved to `engagement.manifest.json` with that reason, and the model declares two.

A bar of three against two invariants is unreachable, which would make the criterion
unfalsifiable rather than strict. Against two, *both* is the only bar that still
requires the burn-in to have happened: one of them answers on the first capture and the
other needs ten. So the restatement keeps the property the number was chosen for, and
the reason it moved is the model shrinking rather than the bar being missed.

**The criterion is about real captures and not about the probe.** The probe feeds the
engine synthetic series and says what the engine *can* judge. What a real tracker
export supports is a separate question, and it is the one the criterion asks.

## What answers, and when

Measured at engine 0.1.13, a declared window of 30 days and a daily collector:

| invariant | axiom | fed by | answers from |
|---|---|---|---|
| `owned_by` | CONNECTIVITY | read, from the capture's owner | capture 1 |
| `transitions_per_week` | STABILITY | **derived**, by counting resets of days-since-transition inside a trailing week | capture 11 |

Two, because two is what the capture format can feed. The others are in
`engagement.manifest.json` with a reason each -- four for want of a field, one because
the axiom the family rule prefers is unreachable at this cadence, and one because Stage
1 already answers it and two implementations of one answer is one too many.

So the burn-in is **eleven daily captures**, which is ten days of history. The two
numbers are different and this document published the wrong one. The engine's floor is
ten OBSERVATIONS; `feeder.transitions` derives one point per capture and drops the
first, which has no predecessor to have moved from -- so N captures give N-1 points and
the axiom answers on the eleventh capture. Measured by sweeping the capture count: at
ten captures STABILITY still declines `insufficient_samples`, at eleven it answers. A
probe that feeds the engine observations directly sees ten, and that is the number the
record carries as `observations`; `captures_through_the_feeder` is the one to collect
against. Before the burn-in one invariant answers; after it, both. One consequence worth stating: `boundary_gate` has nothing to probe
against this model, because both indicators that would have carried a published
threshold are excluded. It is not satisfied and not wrong -- unexercised, which is a
fact about the export format, and the manifest records it so a reader of the model does
not have to work it out.

## The window and the cadence are one decision

**The window is a ceiling on how far back samples are counted, not a hint about how
far back to look.** So the question is never *how many captures do I have* but *how
many fall inside the window*, and a window narrower than the cadence can hold only
one however long the collector runs. Sixty captures available, the engine's own count
of what fell inside:

| declared window | hourly | daily | weekly |
|---|---|---|---|
| `1h` | 1 -- unreachable | 1 -- unreachable | 1 -- unreachable |
| `7d` | answers | 7 -- unreachable | 1 -- unreachable |
| `14d` | answers | answers | 2 -- unreachable |
| `30d` | answers | answers | 5 -- unreachable |
| `90d` | answers | answers | answers |

STABILITY requires ten inside the window. Reading off the table: a daily collector
needs a window of at least 14 days, and **this model declares 30** -- the smallest
round window that leaves margin if a capture is missed. A weekly collector needs 90.

The engine states this itself rather than leaving it to be derived. Its decline
carries `observations`, `required`, `window_seconds`, `sampling_interval_seconds` and
`floor_unreachable_at_this_rate`, so a floor that can never be presented at the
current rate is a fact the consumer can read rather than compute.

## Two corrections to the plan this implements

**A weekly collector is not permanently blind.** The plan states that a weekly
collector makes every history axiom in this vertical permanently unreachable. Measured,
that is true of the windows a weekly collector would plausibly declare and false in
general: at a 90-day window, weekly capture fits 13 observations inside and STABILITY
answers. The honest statement is narrower -- *a weekly collector needs a 90-day window,
and at that width a frozen deliverable is not reported for up to thirteen weeks*, which
is a reason to collect daily rather than a reason it cannot work.

**Learned HOMEOSTASIS is the axiom a daily collector cannot reach.** It needs 30
observations inside a baseline window of its own, and a daily collector fits 7 into it
at any number of captures: `floor_unreachable_at_this_rate` is true at daily, at
6-hourly (28 of 30), and at weekly. Only hourly capture reaches it, at 30 captures.

That collides with the family rule that a lower-is-worse metric with no published line
should use HOMEOSTASIS rather than an invented floor. The rule is right and the axiom
is unreachable here, so the choice is between a cadence nobody will run for an
engagement tracker and a **declared setpoint**, which answers on one capture and fires
on the side `direction:` names. A setpoint is a transcription when the engagement
published a target and an invention when it did not -- so it is declared only where a
statement of work gives the number, and `satisfaction` carries no axiom at all where
none does. That is the same decision the declaration format already makes about the
stall window, and it is recorded here rather than resolved by filling the model.

## What the first capture of real data actually answered

One capture, the Astropy Cycle 5 engagement, **eighteen** deliverables fed:
**one invariant of two answered.** `owned_by` reported 14 deliverables with nobody
named on the other end, and STABILITY declined `insufficient_samples` on all eighteen
in-scope deliverables -- warming, floor 0, which is the burn-in doing what it says.

The capture holds nineteen tracked items and Stage 1 reports fifteen orphans over
them; Stage 2 feeds the eighteen the declaration names, so it reports fourteen. The
nineteenth (`issue-519-names-no-scope-of-work`) is undeclared and unowned, which is
Stage 1's `undeclared_present` and not the engine's to judge. Two stages, two
universes, and this paragraph used to quote Stage 1's numbers for the engine's run.
The run exits 1 on the orphans alone.

So on today's evidence the criterion is **not met**, and not for a reason that is the
engine's or the model's: the series does not exist yet. That is what the criterion is
for, and the answer it produces is observation-only for the history axiom, with
CONNECTIVITY computed from capture one.

The other half has been exercised, on a synthetic series rather than a real one: twelve
daily captures where one deliverable's transition count never changes and another's
changes every third day produce `frozen_series` on the first and silence on the second.
So the path works and what is missing is a real engagement captured daily for ten days,
which is a thing only time supplies.

## What the four gates said when they first met a real model

Phase 1 wrote the guards before there was anything to guard, and each was measured
against a payload shaped to exercise the defect it refuses. A whole model asks them
something else, and two of the four had an answer nobody expected.

**`boundary_gate` reported two problems and was right about the subject.** The band
declares an outer bound a compliant subject may sit exactly on and an inner one where
severity escalates. Handed all four published figures it reports the escalation ones,
because a figure past the outer bound fires on the outer bound -- the correct answer
about the reading and the wrong answer to the question asked. So the caller passes the
compliance boundaries only, and says so. Recorded as finding 14.

**`source_contract` refuses a mapping, and the package never hands it one.** Asked
about the declaration's raw JSON it reports every member unanswered, because the guard
asks whether an element ANSWERS what the writer reads off it and a dict answers nothing
by attribute. Through `check_sources`, which is the door the package actually uses, it
is clean. A guard is only as meaningful as the call site it is reached through.

`model_gate` and `describe_gate` were clean on the first run, and `describe_gate`
earned its place before that: it caught a misplaced threshold in this package's own
engine probe, where `rate_warning` sat at the indicator's top level instead of under
`monotonicity:`. That loads clean, is read by nobody, and leaves the axiom judging
against a default. `unread_fields` is the only surface that reports it.

## What was not measured

CONSERVATION, RESPONSIVENESS, CONSISTENCY and the remaining axioms. This model
declares none of them, so no arm of them has been exercised. They are not handled and
not unhandled; they are unmeasured, and `engine_floors.json` names them under
`not_measured` so that stays visible.

Re-run `battery/probe_engine.py` on any change to the engine pin. A probe that has not
been re-run against the resolved version is a table in a document with extra steps.
