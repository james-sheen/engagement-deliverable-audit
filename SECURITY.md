# Security

## Reporting

Open an issue at
https://github.com/james-sheen/engagement-deliverable-audit/issues. If the
finding should not be public first, say so in the issue title and leave the
detail out — a way to make contact privately will be arranged in the thread.

## What this tool touches

**Nothing yet.** There is no implementation in this repository: no network
client, no file reader, no credential handling. This section will be wrong the
moment that changes, so it is written as a claim that can be checked rather than
a reassurance — `pyproject.toml` declares no runtime dependency, and the suite is
the shared publication tooling and nothing else.

## What it will touch, and the exposure that is already known

Two inputs are planned: a declaration derived from a statement of work, and a
capture exported from a work tracker.

**The capture carries owner identity by construction.** A deliverable is judged
partly on whether it has an owner, so the person's identity is load-bearing data
rather than incidental metadata — it cannot simply be dropped. Anonymisation has
to map it to a stable placeholder and keep the mapping outside the capture, and
the check that this worked belongs in the suite rather than in a one-time review,
because a placeholder that silently stops surviving a format change looks exactly
like a capture with no owners.

**The declaration carries commercial terms.** Margin, rate and budget figures
belong to an engagement and to a client. Anything this tool writes for a reader
outside the engagement should carry ratios and findings, not the figures behind
them. That decision is not yet made here, and it is recorded as open rather than
assumed.

## Credentials

None are read today. When a tracker export is fetched rather than handed over, a
token will be named by environment variable and never accepted as a literal in a
configuration file, and a literal will be refused rather than ignored — ignoring
it lets a file that looks like it configures authentication sit in version
control holding a real credential while doing nothing.
