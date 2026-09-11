# engagement-deliverable-audit

Of the deliverables a statement of work says should exist, which are moving,
which are tracked and stalled, and which are absent.

Those are three answers and not two. A deliverable is **moving** when the
tracker shows an owner and a transition inside the declared window. It is
**tracked and stalled** when it is in the tracker and neither of those holds. It
is **absent** when the tracker has never heard of it. A board that colours all
three "open" has collapsed the one answer somebody would act on.

A fourth state is kept separate from all of them: *the export did not finish*.
An incomplete capture withholds every absence rather than reporting a deliverable
as missing because a page of the export failed.

## Status

**Stage 1 is taking shape. Nothing is released.** What exists: the two formats,
the adapters that satisfy the shared core's protocols, the vocabulary, the floor
table, and the four guards that came before all of it.

What is not here yet: the command line, the regression verb, the capture source
that reads a harness snapshot, and any run against real tracker data. The last of
those is the acceptance that matters, and it has not happened.

### The two decisions this domain had to make for itself

**The stall window is a specification, and it is required.** A deliverable reads
when it is tracked with an owner *and* a transition inside a window, so the window
is what decides which deliverables are stalled. It is declared per engagement,
and a declaration that omits it is refused rather than defaulted — a default would
be a number nobody decided, inherited by every engagement after the first. The
window is passed *into* the capture reader rather than read out of the export, so
an export cannot widen the rule it is judged by.

**The review gate takes one signature.** A `reviewed_by` with a `reviewed_on`,
matching who actually reads a statement of work. A sibling in this family takes
two names because a settlement batch is checked by four eyes as a matter of
regulation; an engagement is not, and a second name nobody is accountable for
produces a signature rather than a review. That a person signs at all is not
optional.

### The floor table, and why the exit code is computed here

The shared core composes exit codes and declares no floors, so the table is this
package's. Computing the code here rather than composing with the core's is
necessity, not principle: measured, a report carrying `orphaned_deliverable` —
the one finding only this domain can see — comes back from the core as exit 0,
because the core scores only its own regression kinds. Composition also cannot
lower anything, so the rows that are reported and deliberately not scored
(`undeclared_present`, `matched_inexactly`) are only expressible this way.

### The guards

Each refuses a shape that was measured producing a wrong answer, and each is
written so that removing its rule turns its own tests red.

| Guard | Refuses | Because, measured |
|---|---|---|
| `model_gate` | an indicator declaring CONSISTENCY without a populated `agrees_with` | the engine then returns no finding, no decline, and nothing in its unreachable list, while still counting the invariant as checked. Silent three ways: no block, an absent `agrees_with`, and an empty one |
| `model_gate` | a declared bound whose basis quote does not contain its number | a citation can name a real document and still be the author's invention. A floor is a specification, not a guess |
| `source_contract` | a declaration whose `sources` elements cannot answer what the report writer reads | the protocol documents the member as one word; the writer reads eleven off each element. The eleven are derived from the writer, and each is proven necessary by dropping it |
| `describe_gate` | a silence list that is missing, as well as one that is non-empty | two of the three lists nest a level deeper than the third, so the obvious reading raises and the obvious repair would report nothing forever |
| `boundary_gate` | a bound where the published number itself is reported as a violation | *shall not exceed forty* leaves forty compliant, and BOUNDEDNESS compares inclusively. RESPONSIVENESS does not, so this probes rather than assumes |

`model_gate` deliberately permits MONOTONICITY with no `monotonicity` block,
because the reversal arm answers without one.

## Licence

Apache-2.0. See `LICENSE` and `NOTICE`.
