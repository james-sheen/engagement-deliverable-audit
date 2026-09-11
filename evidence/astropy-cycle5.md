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

Both documents derive from **astropy/astropy-project**, licensed **CC BY 4.0**,
at commit `74af2fa4de15c27b369e65f93432e1538d8b9476`. The derivative carries each
funding request's file name and title, and for each tracking issue its number, URL,
state, COTR and the age of its last change. No other field is copied.

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
guesses were wrong: `hamogu.md` is tracked by an issue titled *Moritz/MIT* and
`cruz-leadership.md` by one titled *Astropy Finance and SPOC*. The body link was
right both times and the title would have mismatched both.

Reproduce with `python3 battery/fetch_astropy_cycle5.py --out-dir evidence`.

## The result

18 declared, 2 moving, 16 present and not moving, 0 absent. Exit 1, findings.

| finding | count | what it is |
|---|---|---|
| `orphaned_deliverable` | 15 | the tracking issue names no COTR; the body reads `COTR: TBD` |
| `stalled_deliverable` | 2 | owned, and the issue has not changed inside the declared window |
| `undeclared_present` | 1 | issue 519 names no Scope of Work path, so nothing joins to it |

Nothing is absent: every funding request on `main` has a tracking issue. The first
run of the fetch reported one absent deliverable, and it was the call document
`cycle5.md` sitting in the same folder as the requests. That was a defect in the
fetch, not a fact about the engagement, and it is fixed rather than kept for the
sake of a fuller table.

## The one number here that is mine

The stall window is a specification and this package refuses to default it. The
call declares a one-year period of performance and requires work updates in the
tracking issue, but names no interval for them -- so 90 days is the auditor's
choice, a quarter of the period. A verdict that rests on a number nobody published
should be reported with its sensitivity, not without it:

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

Issue 519 records one contract covering five requests, amended from US$58,600 to
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

**`declare` found nothing.** The acceptance also asked for `declare` to find a real
anomaly in a real statement of work. It exits clean here, and the reason is
structural rather than lucky: `declare` reads a transcription, and a transcription
faithful to a well-formed source gives it nothing to find. The anomaly this
engagement does exhibit -- one contract covering five deliverables -- is invisible
to it for a different reason, recorded as finding 11.

**A label is a predicate.** The capture selects issues by the tracker's own
`cycle 5` label rather than by a title match. That caught an issue a title search
missed: issue 522 tracks `aperio-documentation.md` under the title *Tracking Issue:
Unified Astropy Sphinx Theme Migration*, with no cycle in it. The label is the
tracker's own classification and the title is prose; where they disagree the label
is the one to trust, and it would have been easy to never learn they disagreed.
