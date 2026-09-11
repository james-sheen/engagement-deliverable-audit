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
