# Evidence

A run of this package against real tracker data, and the two artifacts it ran on.

## Attribution, which the licence requires

The data is derived from **The Public Jira Dataset**, Lloyd Montgomery, Clara
Lueders and Walid Maalej, Zenodo record 15719919, licensed **CC BY 4.0**. The
files here are a derivative: unresolved issues of one project, reduced to a key,
an owner, a status and a count of days. No issue text, comment, or field other
than those is carried.

The dataset is anonymised at source; owner identifiers here are whatever that
anonymisation produced, and a value of `null` means the issue genuinely has no
assignee rather than that an owner was removed in preparing this.

## What ran

    engagement-deliverable-audit declare   --declaration evidence/jira-declaration.json
    engagement-deliverable-audit presence  --declaration evidence/jira-declaration.json \
                                           --capture     evidence/jira-capture.json

248 unresolved Apache ZooKeeper issues, judged against a declared stall window of
14 days.

| | |
|---|---|
| declared | 248 |
| moving | **1** |
| present and not moving | **247** -- 211 stalled, 36 with no owner |
| absent | 0 |
| verdict | exit 1, findings |
| freshest stalled | ZOOKEEPER-4234, 185 days since its last status transition |
| stalest | ZOOKEEPER-80, 4798 days |
| median | 2461 days |

One issue of 248 had moved inside a fortnight. That is the signal this audit
exists to surface and it is not a fixture.

## The part of the acceptance this does NOT meet

**The declaration is not a statement of work.** A Jira dataset is a tracker; it
contains no contract. So this run demonstrates the capture side on real data and
the three-valued comparison working over it, while the declaration side is derived
from the same source as the capture -- one source, two different fields, which is
weaker than two instruments and much weaker than two organisations. That is the
objection this package's own design notes raise against a sibling domain, and it
applies here until a real statement of work is read beside a real tracker.

**Absence cannot arise from a single dump.** An issue that was never created leaves
no trace to declare, so `declared_absent` is 0 here by construction rather than by
good news. Absence stays exercised by the suite.

## What the run reproduced about the core

The report carries **247 findings** and the core's own `DiffReport.exit_code` is
**0**, because both kinds raised here come from this domain's `capture_findings`
and neither is in the core's `REGRESSION_KINDS`. The verdict of 1 comes from this
package's floor table alone.

That is the gap filed upstream as `presence-audit` #7, reproduced on real data
rather than on a fixture -- which is the stronger form, because a fixture can be
built to show anything.

## Re-deriving these files

    python3 battery/fetch_jira_corpus.py          # needs pymongo for its bson

The script range-fetches a bounded prefix of the 5.8 GB source rather than
downloading it, and the reference date is derived from the newest transition in
the data rather than typed. See its docstring for why both of those matter.
