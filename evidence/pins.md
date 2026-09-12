# What the declared version ranges were actually run against

Produced by `python3 battery/probe_pin.py`, which reads the ranges out of
`pyproject.toml` rather than holding a copy of them, installs each release into its
own environment, installs this package beside it, and runs the suite there.

Reproduce with:

    python3 -m pip install virtualenv packaging
    python3 battery/probe_pin.py                               # the declared ranges
    python3 battery/probe_pin.py --dist arbiter-engine --sweep-below

The run below is the one that set the floors now in `pyproject.toml`. CI repeats the
first command on every push, so a release landing inside a range is exercised
without anybody editing a version number.

## The sweep that moved a floor

`arbiter-engine` was pinned at `>=0.1.13`. Sweeping every release below it:

| release | result |
|---|---|
| 0.1.13 | pass |
| 0.1.12 | pass |
| 0.1.11 | pass |
| 0.1.10 | pass |
| 0.1.9 | fail -- `test_the_live_gate_is_silent_on_a_model_with_nothing_unread` |
| 0.1.8 | fail -- same |
| 0.1.7 | fail -- same |
| 0.1.6 | fail -- same, plus `test_a_floor_is_probed_downwards` |
| 0.1.5 | fail -- same two |
| 0.1.4 | fail -- same two |
| 0.1.1 | fail -- same two |
| 0.1.0 | fail -- same two |

The boundary is 0.1.10, and the reason is in the engine's own changelog: 0.1.10
added `unread_properties` to `model_describe`, which is the field `describe_gate`
reads. Before it, the field is not there to read.

A sweep rather than a bisection, deliberately. Bisecting assumes the failure is
monotonic in the version, and that assumption is the thing a floor is supposed to
be measuring. This sweep was monotonic; that is a result, not a premise.

## Both ranges, after the change

| pin | in range, all run | below the floor | verdict |
|---|---|---|---|
| `presence-audit>=0.1.7,<0.2` | 0.1.7 | 0.1.6 fails | floor holds |
| `arbiter-engine>=0.1.10,<0.2` | 0.1.10, 0.1.11, 0.1.12, 0.1.13 | 0.1.9 fails | floor holds |
| `qa-orchestrator>=0.3.0,<0.4` | 0.3.0, 0.3.1, 0.3.2 | 0.2.0 fails, and so does every release below it | floor holds |

Eight in-range releases installed and passing; every release below every floor fails.

## Re-measured after the verification-report fixes

Every row above was re-run, because a floor is a claim about behaviour and the
behaviour changed. All three floors still hold and all eight in-range releases pass the
suite, now 293 tests rather than 217 (re-run after each round of fixes; 278 at 0.1.1,
287 at 0.1.2). The below-floor failure sets are unchanged from 0.1.2 in all three.

**The below-floor failure set grew from two tests to five, and one of them is new
evidence for the same boundary.** The floor table's coverage is now derived from the
engine's `NotEvaluatedReason` enum rather than transcribed, and that enum has **nine**
members at 0.1.9 and **twelve** from 0.1.10: `missing_role`, `precondition_unmet` and
`undefined_for_values` arrive at the same release as `unread_properties`. So the floor
is supported by two independent facts about 0.1.10 rather than one.

The other two newly-failing tests are pre-existing -- the gate's own model pass and the
attestation round trip -- and they fail below the floor for the original reason: the
silence gate reads a field that is not there before 0.1.10.

**A note on what this document used to name.** The sweep table above cites a test by
name as the one that fails below 0.1.10. That test's fixture was changed by these fixes:
it passed a model declaring `axioms: []`, which was silent because it declared nothing
rather than because the engine had read all of it, and a model declaring no axiom is now
refused. It still fails below the floor and still for the original reason -- but evidence
that names a test rather than a behaviour goes stale when the test is rewritten, and this
paragraph exists because it nearly did.

The third pin arrived with the grader vertical and was declared provisional, the same
way the other two were. Sweeping it found the declared number already correct:
`actions`, `substrate`, `substrates.memory` and `vocabulary` do not exist before
0.3.0, the release that made the harness domain-free, so nothing below it can import
the vertical at all. A floor that survives its own measurement earns the same
sentence as one that does not -- until it was run it was a guess.

`presence-audit` fails at 0.1.6 on `test_nothing_produced_is_clean_and_that_differs_from_the_core_on_purpose`,
because `presence_audit.exit_contract` does not exist in 0.1.6 -- the module this
package composes an exit code against.

## What this does not establish

A release that passes the suite is not a release that does everything this package
needs; it is a release that does everything the suite asks of it. The floor was
lowered to the measured boundary and the reason recorded beside it is the engine's
changelog entry for the field the guard reads, not the fact that the tests were
green.

`presence-audit` has one release inside its range today, so *every release in
range* is a claim about one. That widens on its own as releases land, which is why
CI derives the range instead of naming the version.
