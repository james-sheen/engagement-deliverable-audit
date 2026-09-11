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

**Nothing of the vertical is implemented.** What exists is the shared
publication tooling and the four guards below, which come first on purpose: the
checks that decide whether a vertical is right are the part of a plan most
easily left until last.

Each guard refuses a shape that was measured producing a wrong answer in this
family, and each is written so that removing its rule turns its own tests red.

| Guard | Refuses | Because, measured |
|---|---|---|
| `model_gate` | an indicator declaring CONSISTENCY without a populated `agrees_with` | the engine then returns no finding, no decline, and nothing in its unreachable list, while still counting the invariant as checked. Two readings 0.40 apart against a tolerance of 0.02 go unreported. Silent three ways: no block, an absent `agrees_with`, and an empty one |
| `model_gate` | a declared bound whose basis quote does not contain its number | a citation can name a real document and still be the author's invention. A floor is a specification, not a guess |
| `source_contract` | a declaration whose `sources` elements cannot answer what the report writer reads | the protocol documents the member as one word; the writer reads eleven off each element. A path string passes the conformance kit and then raises on the first JSON report, which is the one a harness parses. The eleven are derived from the writer, not typed here |
| `describe_gate` | a silence list that is missing, as well as one that is non-empty | two of the three lists are nested a level deeper than the third, so the obvious reading raises, and the obvious repair -- defaulting to empty -- would report nothing forever |
| `boundary_gate` | a bound where the published number itself is reported as a violation | *shall not exceed forty* leaves forty compliant, and BOUNDEDNESS compares inclusively. It is not uniform either: RESPONSIVENESS does not fire at its declared number, so this probes rather than assumes |

`model_gate` deliberately permits MONOTONICITY with no `monotonicity` block,
because the reversal arm answers without one. A guard that refused it would
reject a declaration that works.

## Licence

Apache-2.0. See `LICENSE` and `NOTICE`.
