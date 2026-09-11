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

**Stage 1 runs. Nothing is released.** The verbs are `declare`, `capture`,
`presence`, `regression` and `validate-capture`, over two formats, with a floor
table and the four guards that came before any of it. `capture` reads either an
export in this package's format or a `qa-memory/1` harness snapshot, so a scenario
can make a deliverable stall, lose its owner or vanish and do it the same way
twice.

It has now been run against **real tracker data**: 248 unresolved Apache ZooKeeper
issues from a published CC BY 4.0 dataset, of which **one** had moved inside a
fortnight. The artifacts, the numbers, the attribution and the two halves of the
acceptance this does *not* meet are in `evidence/README.md`; the corpus is
re-derivable with `battery/fetch_jira_corpus.py`, which range-fetches a bounded
prefix of the 5.8 GB source rather than downloading it.

What that run does not establish: the declaration there is derived from the same
source as the capture, because a tracker export contains no statement of work. One
source and two fields is weaker than two instruments, and this package says so
rather than counting it as met. `examples/` is invented in full and says so on its
face.

`FINDINGS.md` records where building against the shared contracts produced a wrong
answer.

The core is a **hard dependency**, not an extra, and that is a departure from a
sibling in this family. Keeping Stage 1 dependency-free means writing a second
three-valued comparison beside the core's; measured, the sibling that does so has
two paths that disagree about the verdict for one walk, with an agreement test
that compares states and counts and not the code. One answer, one implementation,
one dependency.

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
