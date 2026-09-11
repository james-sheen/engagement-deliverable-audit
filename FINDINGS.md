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

Consequence for anything downstream: match the key as a substring, never for
equality. Asserting equality passes on this package's own findings and fails on
the core's.

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
