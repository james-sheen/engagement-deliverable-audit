# A declaration and a capture written by different people

The first real-data run in this repository met two thirds of its acceptance and said
so: a tracker export contains no contract, so its declaration was derived from the
same records as its capture. One source and two fields. This run is the pairing that
objection asked for.

**What is measured here is a tracker, not a person.** Every number below comes from
when a tracking issue last changed and whether it names a COTR. Funded work on these
projects happens in pull requests across many repositories; an issue with no recent
comment is a reporting gap in that issue, and nothing here says anybody is behind.
Two of the three findings are administrative: a contract representative not yet
named, and one contract that covers five requests. Read them that way.

## Attribution, which the licence requires

Both documents derive from **astropy/astropy-project**, licensed **CC BY 4.0**, at
commit `74af2fa4de15c27b369e65f93432e1538d8b9476`, and the source tree is cited by
URL in the declaration's `sources`.

**The copied content is each funding request's title, plus the short fragments of
the cycle template and the call quoted here to state the rules relied on.** Every
field that identified a file, an issue or a person has been substituted: requests
carry `D-NN`, the people who own them carry `C-NN`, and a tracking issue is cited by
number as `issue-NNN` rather than by URL. Issue state is carried as it stood; the
age of the last change is computed from it rather than copied. CC BY 4.0 asks for
attribution and for modifications to be indicated -- the substitution is the
modification, and `NOTICE` says why it was made.

The identifiers were assigned across both documents at once, which is why the
declaration has no `D-13`: that slot fell to the tracking issue that declares no
deliverable at all, and it is named for what it is rather than numbered.

## The two instruments

| | declaration | capture |
|---|---|---|
| artifact | 18 funding requests under `finance/proposal-calls/cycle5/` | 19 issues the tracker labels `cycle 5` |
| written by | the proposer | the finance committee contact, after award |
| purpose | ask for funding | track the work |
| what it fixes | the cycle template: *this section ... will be used as the Scope of Work in the resulting contracts* | the call: *a new tracking issue is created ... which includes the budget, period of performance, and identifies the assigned COTR* |

**The join is mechanical.** Every tracking issue body links its Scope of Work by
path, so the key on both sides is the request's file name. Nothing matches titles or
infers which proposal an issue is about -- which matters, because two of my own
guesses were wrong: one request is tracked by an issue whose title names a
person and an institution rather than the deliverable, and
`D-09.md` by one titled *Astropy Finance and SPOC*. The body link was
right both times and the title would have mismatched both.

Reproduce with `python3 battery/fetch_astropy_cycle5.py --out-dir evidence`.

## The result

18 declared, 2 moving, 16 present and not moving, 0 absent. Exit 1, findings.

| finding | count | what it is |
|---|---|---|
| `orphaned_deliverable` | 15 | the tracking issue names no COTR; the body reads `COTR: TBD` |
| `stalled_deliverable` | 2 | owned, and the issue has not changed inside the declared window |
| `undeclared_present` | 1 | `issue-519` names no Scope of Work path, so nothing joins to it |

Nothing is absent: every funding request on `main` has a tracking issue. The first
run of the fetch reported one absent deliverable, and it was the call document
`cycle5.md` sitting in the same folder as the requests. That was a defect in the
fetch, not a fact about the engagement, and it is fixed rather than kept for the
sake of a fuller table.

## What `declare` found: the window this engagement never set

Run against the declaration these documents alone support, `declare` refuses:

    python3 battery/fetch_astropy_cycle5.py --omit-window --out-dir evidence
    declare: this declaration names no stall_window_days ... There is no default
    OUTCOME exit=2 verdict=could-not-complete

That is the real anomaly in this real scope of work, and it is the load-bearing one.
A deliverable reads when it has an owner *and* a transition inside a window, so the
window decides which deliverables are stalled -- and the call sets a one-year period
of performance, requires work updates in the tracking issue, and names no interval
for them. Nobody decided the number every three-valued verdict here depends on.

So the run below supplies it: 90 days, a quarter of the period, the auditor's
specification and not the engagement's. A verdict resting on a number nobody
published should be reported with its sensitivity, not without it:

| window | moving | stalled, owned | orphaned |
|---|---|---|---|
| 14 days | 0 | 4 | 15 |
| 30 days | 1 | 3 | 15 |
| 60 days | 1 | 3 | 15 |
| 90 days | 2 | 2 | 15 |
| 120 days | 3 | 1 | 15 |
| 180 days | 4 | 0 | 15 |
| 270 days | 4 | 0 | 15 |

The sweep says something the single run cannot: **the window decides the verdict for
four deliverables and for no others.** Only four tracking issues name a COTR at all,
so the other fifteen cannot read at any window -- an unowned deliverable is not
stalled because of a threshold, it is stalled because nobody is going to move it.
The finding that survives every window is the one worth acting on.

## The change order is real, and the probe fires on it

`issue-519` records one contract covering five requests, amended from US$58,600 to
US$120,730 with a per-project breakdown. That is a change order. The declaration is
at change order 0, so asserting the engagement's real state reports it:

    presence --latest-change-order 1
    declaration_stale: this declaration is at change order 0 and the engagement is at 1

Without the assertion the probe stays silent, which is the other half: it reports a
superseded declaration and does not invent one.

## What this still does not establish

**Two authors, one host.** Both artifacts live in one repository on one platform.
That is two instruments in the sense that matters -- different people, different
purposes, different times, and neither derived from the other -- and it is not a
client-signed contract read beside a vendor's own tracker. The stronger pairing
remains unmet and is recorded as unmet.

**The anomaly `declare` cannot reach.** It refuses the missing window, above. It
cannot see the other thing this engagement exhibits -- one contract covering five
declared deliverables -- because the audit joins one deliverable to one tracked item
and has no word for many-to-one. Recorded as finding 11, and deliberately not fixed
by inventing a grouping the core's diff does not have.

**A label is a predicate.** The capture selects issues by the tracker's own
`cycle 5` label rather than by a title match. That caught an issue a title search
missed: `issue-522` tracks `D-02.md` under the title *Tracking Issue:
Unified Astropy Sphinx Theme Migration*, with no cycle in it. The label is the
tracker's own classification and the title is prose; where they disagree the label
is the one to trust, and it would have been easy to never learn they disagreed.
