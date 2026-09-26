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

**Released at 0.1.0. Stage 1 and Stage 2 both run.**

    pip install engagement-deliverable-audit            # Stage 1
    pip install 'engagement-deliverable-audit[detect]'   # and the engine

Ten verbs: `draft`, `gate`, `declare`, `capture`, `validate-capture`, `presence`,
`regression`, `generate`, `detect`, `attest`. Two formats for the artifacts Stage 1
reads, a floor table where every row carries its reason, and the four guards that came
before any of it. `capture` reads either an export in this package's format or a
`qa-memory/1` harness snapshot, so a scenario can make a deliverable stall, lose its
owner or vanish and do it the same way twice.

**One thing Stage 2 cannot yet show, and it is in the release notes rather than only
here.** Its ownership invariant answers on the first capture and has, on real data. Its
history invariant needs eleven daily captures of a live tracker before it says anything
(ten derived points; the first capture yields none),
so the kill criterion in `docs/burn-in.md` is recorded as NOT met and that axiom ships
as observation-only. The path is exercised end to end on a derived series; what is
missing is an engagement captured daily for eleven days, which only time supplies.

It has now been run against **real tracker data twice**, and the second run exists
because of what the first one could not meet.

The first: 248 unresolved Apache ZooKeeper issues from a published CC BY 4.0
dataset, of which **one** had moved inside a fortnight. The artifacts, the numbers,
the attribution and the two halves of the acceptance this does *not* meet are in
`evidence/README.md`; the corpus is re-derivable with `battery/fetch_jira_corpus.py`,
which range-fetches a bounded prefix of the 5.8 GB source rather than downloading it.

The second: **Astropy's Cycle 5 funded work**, where the declaration and the capture
are written by different people for different purposes -- 18 funding requests whose
own template says they become the Scope of Work, against the finance committee's
tracking issues, joined by the Scope of Work path each issue carries. 2 moving, 2
stalled, 15 with no contract representative named, and a window sweep showing that
the one number the auditor supplies decides the verdict for four deliverables and
for none of the rest. In `evidence/astropy-cycle5.md`, with what it still does not
establish.

What that run does not establish: the declaration there is derived from the same
source as the capture, because a tracker export contains no statement of work. One
source and two fields is weaker than two instruments, and this package says so
rather than counting it as met. `examples/` is invented in full and says so on its
face; it lives in the repository rather than in the distribution, as does `battery/`.

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
| `describe_gate` | a model that declares no axiom at all | `something: else` loads as a valid domain model with no indicators, so every silence list is honestly empty and a run against it judges nothing. An empty answer is clean, so pointing a verb at the wrong YAML file was a clean audit |
| `boundary_gate` | a bound where the published number itself is reported as a violation | *shall not exceed forty* leaves forty compliant, and BOUNDEDNESS compares inclusively. RESPONSIVENESS does not, so this probes rather than assumes |

`model_gate` deliberately permits MONOTONICITY with no `monotonicity` block,
because the reversal arm answers without one.

### The verbs Stage 2 adds

`draft` proposes a declaration from a tracker export and refuses to call it reviewed --
and carries no window, so `declare` refuses the result twice over. Both are deliberate:
a tracker holds no contract, so a declaration derived from one is the same records under
another name, and nothing in a tracker decides the window a stall is measured against.

`gate` names, in one pass, everything that is not ready to be judged against: every
unsigned declaration, and with `--model` the model gates too. It exits 2 rather than 1,
because a document nobody signed has produced no verdict to report as findings, and it
refuses to exit clean when handed nothing.

`generate` writes a model and a manifest as a pair or neither. **This domain's generated
model is empty**, by construction: generation derives indicators from thresholds a
declaration carries, and a deliverable carries a due date and an owner rather than a
bound. So every point is excluded as `no_thresholds` and the manifest is the account of
that -- an empty model on its own is indistinguishable from generation never having run.

`detect --attest-out` writes a `presence-audit/attestation/1` artifact and `attest` reads
one back through the door a recipient uses. The members the core's builder reads off its
manifest are declared by no protocol, so this package derives them from the builder's own
source -- distinguishing an attribute access, which is required, from a `getattr` with a
default, which is not. Filed upstream; `FINDINGS.md` has the rest.

**`attest` scores the artifact rather than trusting a verdict written into it.** A
recipient holding an artifact from anywhere gets this package's floor table applied to
it, which is the only reason re-reporting is worth doing. `detect` also records its own
code in the artifact -- in the `verdict` block the core's format declares from
`presence-audit` 0.1.8, `{exit_code, meaning, scored_by}`, and as a bare string before
it. Below 0.1.8 the core's `not_checked` drops the flag that separates a cadence which
can never reach a floor from one that has not reached it yet; from 0.1.8 it keeps it
under each row's `measurement`, and `attest` reads it there. The two compose with `max`, so a recorded verdict can raise a score
and never lower one, and a disagreement between them is printed rather than resolved.

**`detect` also asks the engine whether it read the model.** A declaration the engine
dropped -- an unknown axiom, a field nothing reads -- means part of the model was never
applied, and a run that judged nothing would otherwise report clean. That is
`model_not_read`, floored at 2.

**And it says which declared deliverables it did not feed**, as two separate facts: one
that was in an earlier capture and is gone from the latest, and one that has appeared in
no capture at all. Neither is floored here, and that is Stage 1's decision rather than
tidiness: `presence` reports `declared_absent` only for points declared as deliverables,
so a declared ceremony or assumption missing from a tracker is correctly not a finding.
The feeder has no such filter, so flooring its unfed set would report a steering call as
a missing deliverable. Not feeding something is still a decision, and a decision the run
does not state reads as nothing to say.

### The grader

This package registers with `qa-orchestrator` as a referee and a tier, so a scenario
can make a deliverable stall, lose its owner or vanish and do it the same way twice.
It lives in `battery/` rather than in the wheel, because a package that audits
deliverables should not make every consumer install a test harness:

    qa-orchestrator --plugin battery/qa_vertical.py check battery/scenarios/*.yaml
    qa-orchestrator --plugin battery/qa_vertical.py run battery/scenarios/orphaned-deliverable.yaml
    python3 battery/probe_qa_vertical.py            # every claim above, as one leg each

Four verbs are added -- `orphan`, `reassign`, `slip`, `bounce` -- because an entity's
value in the harness's snapshot is days since the last transition, so `remove` and
`set` already say *absent* and *moving* without help, and what they cannot say is
anything about an owner or a status. Every phase asserts both channels: the
referee's verdict and the substrate's own state. If an injection silently failed,
the substrate expectation is the only thing that could show the referee was right to
stay quiet.

`must-fail.yaml` is wrong on purpose and must stay wrong. The probe requires it to
fail in BOTH channels, and requires each of its two errors to fail on its own --
two mismatches from one cause would look the same from outside.

One scenario runs in `detect` mode, so the same ownership fault is judged by the engine
rather than by the three-valued diff. It names two configs: the declaration, then the
model.

Pointing it at the tool found three defects no test and no real-data run had.
`regression --json` printed a document and then a prose line; the document named one
deliverable two ways; and the feeder kept an owner who had left, which no single
capture could reveal and which the detect scenario caught on its first run. All three
are in `FINDINGS.md`.

## Licence

Apache-2.0. See `LICENSE` and `NOTICE`.
