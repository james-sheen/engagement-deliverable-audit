# Findings

Where building this package against the shared contracts produced a wrong answer,
a surprising one, or one that had to be worked around. Each entry says what was
measured, not what was expected.

## 1. The core's finding text is in another domain's language

`presence` prints the core's own `detail` for the kinds the core raises, and one
of them reads:

    disabled_in_config_but_live: D-5 benefits case -- the configuration marks
    this Status: disabled, and the machine is reporting 1 days

`Status: disabled` and `the machine` belong to a hardware walk. A partner reading
a report about an engagement is not reading about a machine, and a deliverable
that was removed by a change order is not administratively disabled. (`1 days`
is a pluralisation defect in the same string.)

This is adjacent to the open upstream ask about the `sensor` noun, which covers
emitted KEYS, required input keys and API fields. The `detail` PROSE is a
different surface and that ask does not reach it. Printed verbatim here for now,
because re-deriving every kind's wording in this package would put a second
source of truth beside the core's, which is the trade entry 5 is about.

## 2. A vertical's own findings are never scored by the core

`capture_findings` is the member for what only a domain can see, and
`Finding.is_regression` is `self.kind in REGRESSION_KINDS` -- a module-level
frozenset with no vocabulary hook. So a report whose only defect is
`orphaned_deliverable` comes back from `DiffReport.exit_code` as **0**, with the
finding present in the report.

Measured on 0.1.7. Filed upstream as `presence-audit` #7. It is the reason this
package computes its own exit code rather than composing with the core's, and the
reason the floor table is not optional: without it, the one finding this domain
exists to make would exit clean.

The gap is invisible in the family's one fully worked vertical, because
`bmc-sensor-audit`'s own domain finding happens to use `interface_divergence`,
which is already in the set.

## 3. `is_reading` alone does not produce a finding

Measured on the same release. A point with `reading: 3.0` and `is_reading: False`
moves the `present_not_reading` COUNT and raises nothing. Only `reading is None`
raises `declared_unreadable`. The two can also disagree: `reading: None` with
`is_reading: True` is counted as reading and reported unreadable at once.

So this package keeps days-since-transition whatever the verdict and raises its
own `stalled_deliverable`, rather than blanking the number to make a shared kind
fire. The number is the evidence a reader acts on; the kind name is not.

## 4. One report, two spellings of the same subject

A finding the core raises about a declared point names it by `display_name` --
`D-5 benefits case`. A finding raised from a capture names the ticket key alone,
because `capture_findings` is handed the capture and a captured point has no
display name to reach for. Both appear as subjects in the same artifact.

**The document was since fixed; the prose was not, deliberately.** The JSON now
carries the declared key for every subject, because anything joining rows by
subject saw two deliverables where there is one -- and the grader matches subjects
for EQUALITY, so neither spelling could match the other. The prose still prints the
declared title, because a person reading a list of findings is helped by it.

So: inside the document, match the key for equality. Reading the prose, match it as
a substring. Finding 13 records what found this.

## 5. A second implementation costs more than the dependency it saves

A sibling keeps its Stage 1 dependency-free by writing its own three-valued
comparison beside the core's and asserting the two agree. Measured: on one walk
whose only defect is a substituted reading, its own path returns 1 and the core
path returns 0 -- and its agreement test compares states, counts and the presence
of a finding, but not the verdict. Filed as `factory-line-audit` #2.

So this package took the core as a hard dependency and has no second
implementation. A bare install is no longer nothing, which is a real cost. What it
buys is that there is exactly one answer to *which deliverables are moving*.

## 6. A rule this package stated and did not hold

`qa_memory` documents that a snapshot carrying no transition number means *no
transition recorded*, which is not a transition at zero, because reading it as
fresh would turn a gap in the data into a healthy deliverable. A mutation pass
changed exactly that line and **all 147 tests stayed green**.

The rule was in a docstring and nowhere else. Found by mutating the source rather
than by reading it, which is the argument for running that pass on every slice
rather than on the ones that feel risky -- this was the least risky-feeling change
in the set.

## 7. A typed reference date made a real run look like a working audit

The first run against real data dated staleness from the dataset's publication
date, 2025-06-23. Every one of the 248 issues came back stalled, 100%, and the
output looked exactly like an audit finding a great deal.

It was measuring the distance between a calendar and the data. The prefix of the
dump that was read tops out at a status transition in September 2021, so every
issue in it is three and a half years past a 14-day window no matter what the
tracker says.

The reference is now DERIVED: the newest transition in the captured set, because
an export cannot know about anything after its own newest record, so the
high-water mark is its clock. With that, 1 of 248 is moving and 247 are not --
which is a finding about ZooKeeper's open issues rather than about my clock.

The tell was the 100%. A verdict that is unanimous over a real corpus is usually a
statement about the instrument.

## 8. The acceptance could not be fully met by the dataset it names

The plan asked for the three-valued diff on the Public Jira Dataset, at least one
real stalled deliverable reported as present and not reading, and `declare`
finding a real anomaly in a real statement of work.

The first two are met. The third cannot be met from this dataset at all: a Jira
export is a tracker and contains no contract. So the declaration here is derived
from the same source as the capture -- one source, two different fields -- which is
weaker than two instruments and much weaker than two organisations.

That is the same objection this package's design notes raise against a sibling
domain, and it applies to this evidence. It is recorded in `evidence/README.md`
beside the numbers rather than only here, because that is the file somebody
reading the result will open.

## 9. The floor of a range is the one end nothing ever runs

Both pins here were declared provisional, and the file said so: the numbers were
the releases the design was measured against while this package was still a plan,
and `pyproject.toml` recorded that they would be replaced by whatever
`battery/probe_pin.py` reported. That probe did not exist. A declared leg with
nothing behind it reads, one document later, exactly like a leg that ran.

Writing it changed one of the two numbers. The probe installs every release a
range admits, plus the highest release below it, and runs the suite in each:

- `presence-audit>=0.1.7` is exact. 0.1.6 fails, and it fails because
  `presence_audit.exit_contract` does not exist there -- the module this package
  composes an exit code against. The floor is the release the thing it needs first
  appeared in.
- `arbiter-engine>=0.1.13` was **three releases too high**. 0.1.10 through 0.1.13
  all pass; 0.1.9 and below fail on `describe_gate` reading `unread_properties`,
  a field the engine added in 0.1.10. 0.1.13 was the newest release on the day the
  pin was written, which is a date, not a reason.

Nothing in this repository could have noticed. Every job resolves each dependency
to the newest release its range admits, so a range is only ever exercised at one
end -- and it is never the floor, which is the end a consumer with an older
install actually lands on. The suite was green on four engine releases and had
never met any of them.

The probe sweeps the releases below the floor rather than bisecting for it. A
bisection assumes the failure is monotonic in the version, which is the assumption
a floor is supposed to be measuring; the first real sweep happened to be monotonic,
and the branch that reports a non-monotonic one is tested while nothing has
produced that shape.

One thing the probe cannot settle: a release passing 172 tests is not a release
that does everything this package needs. Lowering a floor to where the suite stops
failing widens the claim to exactly the breadth the suite has -- so the reason
recorded beside the new number is the engine's own changelog entry for the field
the guard reads, not the green.

## 10. The transcription answered with a different field, and called it the title

The declaration for the Astropy run carries each funding request's title, read from
the document rather than from its file name. The rule looked for the cycle
template's `### Title` heading and, failing that, fell through to the first line
that was not a heading.

About half the real requests do not use the label. They replace it with the title
itself, as a heading -- so the fallback skipped the title *because* it was a heading
and returned the first line of the next section. Nine of eighteen declared
deliverables carried the opening bullet of the project team, and the declaration
named that field `text` with a `basis` that claimed the document.

Nothing was red. The documents parsed, every point had a text, the counts were
right, and the diff ran. It was visible only by reading eighteen values and noticing
that several of them were people's names and one was *Approximately 27 years of
scientific python programming experience*.

The rule is now: the title is the document's first heading, unless that heading is
the template's label, in which case it is the first line beneath it -- and the empty
string when the document titles nothing, rather than the file name, which is the one
field that is never missing. It was also lifted out of the fetch so it can be tested
without the network, because the first version's wrong answers were only ever
visible in its output.

## 11. One contract, five deliverables, and a model that has only one shape

The Astropy capture holds an issue recording a single contract that funds five of
the declared requests, amended from one total to a larger one with a per-project
breakdown. It names no Scope of Work path, because it is not about one request.

This package joins a declaration to a capture one deliverable to one tracked item.
So that issue reads as `undeclared_present` -- correct, and under-described: it is
not an undeclared deliverable, it is a contract covering five declared ones. The
five requests it funds each read as `orphaned_deliverable`, because their own
tracking issues name no COTR, and the contract that does cover them is the item the
audit cannot connect them to.

Nothing here is wrong, in the sense that every finding is true. What is missing is a
shape: a declaration and a capture can relate many to one, and the vocabulary has no
word for it. A deliberate non-fix for now -- inventing a grouping the core's diff
does not have would put a second model of the relationship inside a vertical, which
is the thing finding 5 paid a dependency to avoid. It is recorded as a real limit
found by running against a real engagement rather than as a design note.

## 12. Two verbs of one tool disagreed about whether stdout is a document

`presence --json` returns before it prints any prose, so its whole stdout is the
report. `regression --json` printed the report and then the `OUTCOME` line, because
it fell through to the shared ending.

Nothing in this repository could see that, and it took pointing a harness at the
tool to find it. The harness parses the WHOLE of stdout as JSON, catches the decode
error, and carries on **with no report**. Then: an expectation naming a finding
fails, which looks like the tool missing a fault; an expectation naming the ABSENCE
of a finding passes, because it is true of an empty list. Half the assertions go
quiet and the other half blame the wrong thing.

Fixed by making the regression document a document -- a `format` of its own, the
same `exit_code` and `verdict` keys its sibling carries, and an early return. The
guard is in `tests/test_cli.py` and it parses the entire stream for every verb that
has a `--json`, because a test that sliced the JSON out first would have passed
throughout. Reverting the fix reddens it.

The findings key was renamed too, from `changes` to `findings`.
`ReportSchema.findings` is a single key and is read with a plain `.get()`; one name
for one thing across both verbs is what lets one profile describe either mode.
`changes` remains the word the prose uses.

## 13. The grader found the subject spelling, by matching for equality

Finding 4 recorded that one report named a deliverable two ways and advised
downstream readers to match the key as a substring. That advice is fine for a
reader you control. The harness is not one: it collects the subject of each finding
and compares sets, so `D-4` never matches `D-4 steering sign-off`.

The scenario failed on exactly that phase, and the cheap repair was to write the
display name into the scenario. That would have pinned the inconsistency in place
and left the next consumer to rediscover it -- and it would have broken the day
somebody edited the fixture's title, which is a guard with an expiry date.

So the document was fixed instead: subjects are the declared key, and the prose
keeps the title. Two things now detect a regression of it -- a unit test on the
document and the scenario itself -- and reverting the fix reddens both.

What this says about the other direction: a report is an interface, and the reader
that finds its defects is the one you did not write. Two real runs and a review
could not see this; a harness that joins rows by subject saw it on the fourth phase
of the first scenario.

## 14. A guard whose question does not apply to half the bounds it was handed

`boundary_gate` asks one thing: does the published number itself get reported as a
violation. It was written against hand-made payloads with a single threshold, and it
was right about every one of them.

The real model declares a band -- an outer bound the contract allows a subject to sit
exactly on, and an inner one where the severity escalates. Handed all four published
figures, the gate reported two problems, and it was not wrong: 98% utilisation fires,
because 98 is already past the 95 the contract allows. It fires on the *warning*
bound, which is the correct answer about the subject and the wrong answer to the
question asked.

The distinction the guard has no word for: **an escalation threshold sits inside the
violating region by construction.** *Does the published number itself fail* is a
question about the boundary between compliant and not, and there is exactly one of
those per direction. Asking it of a critical limit guarantees a problem report and
teaches a reader that the gate cries wolf.

Not fixed in the guard, deliberately. The guard's job is to answer what it is asked
about the numbers it is given, and deciding which bound is the compliance boundary is
a fact about the contract that only the caller has. So the caller passes the outer
bounds and says why, and the model carries the decision beside the literals. A guard
that tried to infer which bound was which would be guessing at the contract.

## 15. Two checks whose subjects disagreed, and the environment built to break one

`tests/test_engine_floors.py` asserted that the recorded engine version equals the
engine installed. `battery/probe_pin.py` installs *every* release the pin claims and
runs the whole suite inside each one, to prove the floor of the range holds.

Both are right on their own and they cannot both hold: the second deliberately builds
environments where the first is false. CI found it immediately -- the floors job went
red on the commit that added the test, on an engine release the package fully supports.

The repair was to fix the subject rather than relax the assertion. What a record of
measurements can claim on its own is that it describes an engine this package
supports, and the pin is the authority on that; whether the numbers still REPRODUCE is
a behaviour question, and the grader job re-runs the probe and compares every
measurement in the declared environment. That is strictly stronger than comparing a
version string, and it is the check that goes red on a pin change.

The general shape: a test that pins an environmental fact will eventually meet a probe
whose job is to vary it. The tell is that the failure names a configuration nobody
would ship and everybody supports.

## 16. The ownership check is quietest when nobody owns anything

CONNECTIVITY over ownership is the one invariant this model can answer on its first
capture, and on the real engagement it did: nineteen deliverables, four with a
representative named, fifteen orphans reported.

Then the same run with no owner at all reports **nothing**. The axiom needs an entity
of the target type to have been OBSERVED, and with nobody owning anything there is no
Consultant in the graph, so it declines `missing_entity_type` instead of naming a
single orphan. The worse the engagement, the quieter the model -- and the shape where
every deliverable is unowned is not hypothetical, it is the first week of an
engagement before the contracts are signed.

What stops it reading as a pass is the floor rather than the finding.
`missing_entity_type` is a model or feed defect and floors at 2, so a run where the
axiom could not be evaluated exits could-not-complete. An audit that said *no orphans*
there would be worse than useless; one that says *this could not be checked* is
correct, and the floor is doing the work the finding cannot.

Not worked around in the feeder. Inventing a placeholder consultant so the axiom has
something of the right type to look at would make the orphans fire -- and would put an
entity nobody declared into the graph to get an answer out of it, which is the
phantom-topology shape the engine's own dangling-edge finding exists to refuse.

`tests/test_feeder.py` asserts the decline AND the floor together, because the decline
alone is satisfied by a run nobody scored.

## 17. The window is measured from the clock, not from the newest observation

Twelve captures, a thirty-day window, eleven derived points, a floor of ten -- and
STABILITY declined `insufficient_samples`. Nothing was wrong with the series: it ended
six weeks before the run.

The window is a ceiling measured backwards from the moment of the run, so a series
that stopped a month ago falls outside a thirty-day window however many captures it
holds. Re-dating the same twelve captures to end at the present made the axiom answer
immediately.

Two things follow, and the second is the one worth remembering. An audit of an
archived engagement cannot use the history axioms at all, however complete its record
-- the window will hold none of it. And **any test fixture built from a frozen date
becomes unreachable by its own model as the clock moves**, which is the inverse of the
defect in finding 7: there a typed *now* made a real corpus look entirely stalled, and
here a typed past makes a complete corpus look unmeasured. Both come from a date
written down instead of derived. `tests/test_feeder.py` builds its series from the
real clock and says why.

## 18. An owner who left stayed in the graph, and only a series could show it

The feeder reads an owner out of each capture and feeds an ownership edge where one is
named. It recorded the owner only when a capture named one -- which reads as careful
and is the defect: a deliverable owned in an early capture and unowned in the latest
kept the earlier name, kept its edge, and could not be seen as an orphan.

**One capture has no history to go stale.** The real-data run fed nineteen deliverables
from a single capture and reported fourteen orphans correctly; every test of the feeder
used one capture or a series with stable owners. Nothing could have shown this.

What showed it was a scenario: orphan a deliverable between two captures and require the
engine to report it. It failed on the first run, in the phase that takes the owner away.
That is the harness earning its place -- the fault needs two of something, and until a
scenario made the second one exist, the code was correct on every input anybody had
tried.

The rule is now stated where it is implemented: the latest capture is the state,
including when the latest says nobody. Both directions are tested, because a feeder that
simply never recorded an owner would satisfy the first half perfectly.
