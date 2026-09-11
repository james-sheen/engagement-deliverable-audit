# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- The repository, wired into the shared publication tooling: the hygiene sweep,
  the commit-message check and the authorship check, each running in CI where no
  local setting can switch it off.
- Four guards under `engagement_deliverable_audit.guards`, with the measurement
  that produced each one recorded beside it: a model gate, a declaration-source
  contract derived from the report writer rather than transcribed, a silence gate
  that treats a missing key as a defect, and a boundary gate that probes where a
  declared bound actually fires. Removing any one of their rules turns that
  guard's own tests red, which is checked rather than claimed.
- Stage 1's artifacts: the declaration and capture formats, each refusing an
  unknown major by name; the adapters; `EngagementVocabulary` answering all
  fifteen members of the core's contract and passing its conformance kit; and the
  floor table, with the reason recorded beside every row.
- The verbs: `declare`, `capture`, `presence`, `regression`, `validate-capture`.
  `capture` reads a `qa-memory/1` harness snapshot as well as an export, mapped so
  that three of the harness's own verbs already exercise the three states. Every
  verb ends on exactly one OUTCOME line, and a document that could not be read
  exits 2 rather than 1 -- it produced no verdict to report as findings.
- `FINDINGS.md`, recording what measuring turned up -- several filed upstream, one a
  rule this package stated in a docstring and did not hold, found by mutating the line
  rather than by reading it. No count here: a number in prose expires on the day the
  next entry lands and nothing goes red.
- Stage 2's `detect`, with the vertical's own feeder. Every deliverable the capture
  presents is fed and the ownership edge only where an owner is named, which is what
  lets an orphan be a finding rather than a gap; `transitions_per_week` is derived by
  counting resets of days-since-transition inside a trailing week, because a tracker
  export carries no transition count of its own.
- `examples/engagement.model.yaml` with `examples/engagement.manifest.json` beside it,
  as one pair. The model declares only what the capture format can feed; the manifest
  names every exclusion with its reason, including one guard the exclusions leave
  unexercised.
- `docs/burn-in.md`: Stage 2's kill criterion, written before the build and restated
  once in the open when the model shrank, plus the window-and-cadence arithmetic
  measured against the pinned engine rather than reasoned about.
- `battery/probe_engine.py`, which measures the engine and ships its floors inside the
  package so the installed tool can tell a floor it has not reached yet from one its
  cadence can never present. `battery/probe_pin.py` installs every release each
  declared range claims and runs the suite in each, which moved one floor down by three
  releases and found a second already correct.
- `battery/qa_vertical.py` with four scenarios: this tool as a `qa-orchestrator` referee
  and tier, the verbs `orphan`, `reassign`, `slip` and `bounce`, and one scenario that
  is wrong on purpose and whose two errors are each required to fail on their own.
- Real-data evidence under `evidence/`: a published Jira corpus, and an engagement whose
  declaration and capture are written by different people for different purposes.

### Changed

- `regression --json` prints a document and nothing else. It used to print the document
  and then a prose OUTCOME line, which no caller parsing the whole of stdout can read --
  found by pointing a harness at it, and guarded now for every verb that has a `--json`.
- A finding in the presence document names a deliverable by its declared key. The core
  names a declared point by its display name and the capture side names the key, so one
  document carried two spellings of one subject and nothing joining rows by subject
  could match them.

Nothing is released. There is no distribution on the index under this name yet,
and `__version__` carries a `.dev0` suffix so that an accidental build cannot be
mistaken for one.
