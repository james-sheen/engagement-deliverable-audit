# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

Answers a second verification report, on 0.1.1, which again ran nothing. It confirmed
all of A-G fixed and raised five residuals. Every one reproduced; two were materially
worse than filed, one was a repeated factual error, and one recommendation was right for
a reason the report did not give. `FINDINGS.md` 31-35.

### Fixed

- **`detect` said nothing about a deliverable it decided not to feed.** 0.1.1 stopped
  feeding a deliverable the latest complete capture no longer holds; measured over two
  captures, the run then exited 0 with the name absent from the prose and from the
  `--json` document. `Fed` now carries `vanished` and `never_seen` as separate keys --
  two different facts -- and `detect` states both. Deliberately unfloored: measured
  against Stage 1, scoring them would report a declared ceremony as a missing
  deliverable, because `presence` filters on `declared_type` and the feeder does not.
- **`engine_floors.json` no longer has a `captures` key.** The off-by-one in 0.1.1 came
  from that name holding an observation count; adding correctly-named keys beside it
  fixed the test and left the ambiguity in the data, where by then the word meant three
  things in one record -- an observation count, a capture count, and a dict. Every key
  now names its unit, and two tests hold it: one bans the word, one asserts the gap
  between units is 0 or 1 per floor.
- **Four tests skipped without the engine, and removing the skip alone would have been
  worse.** Measured in an engine-free environment, `detect` refuses with *needs the
  engine* and exits 2, which is exactly what the malformed-model tests assert -- so they
  passed for the environment rather than the behaviour. The engine is now imported
  explicitly, so the tests error rather than vanish, and the refusal text is asserted so
  a 2 from the wrong cause cannot satisfy them.
- **A real signature could read as NOT SIGNED.** `Engagement.disclosure` compared the
  first word case-insensitively, so `Fixture Consulting Ltd` returned `FIXTURE` and
  `declare` would print *NOT SIGNED, disclosed as FIXTURE* over a genuine signature --
  the property's own failure mode reversed. A marker must now be upper case as written.
  The near-miss list had `Fixtures` plural and was one letter from catching it.
- `cmd_detect` imports the silence gate unconditionally. The `except ImportError` around
  it could not fire, and had it fired it would have left the unread-model check empty and
  restored the clean-run defect it exists to close.

### Changed

- **`evidence/jira-*.json` regenerated rather than hand-edited.** 0.1.1 renamed the
  placeholder digest and taught the fetch script to compute a real one, but edited the
  committed file -- so the script computed a digest the evidence did not carry, and a
  findings entry said otherwise. Re-deriving showed two further drifts: the declaration
  said *the Apache tracker* where the script writes the project name. Now 248 issues, the
  same data-derived reference date, byte-identical capture points, and a real digest. A
  test reads the exporter keys off the script's AST so the shape cannot drift again
  without a network fetch.

## 0.1.1 -- 2026-09-11

Answers an outside verification report that read the whole tree statically and ran
none of it. Every item it raised was reproduced before anything was changed; three were
wrong in detail and one was considerably worse than filed, which only running them
showed. `FINDINGS.md` 21-30 records each one.

### Fixed

- **`attest` turned a could-not-complete run into a clean one.** It scored from
  `findings` alone, and the artifact carries two lists. Measured: a capture where
  nobody owns anything exits 2 from `detect` and exited 0 from `attest` over the
  artifact `detect` had just written. It now scores the artifact with the same floor
  table, and `detect` records its own code beside the core's keys -- the core's format
  carries no verdict and drops `floor_unreachable_at_this_rate`, so
  `warmup_unreachable` cannot be recovered from the artifact alone. The two compose
  with `max`: a recorded verdict can raise a score, never lower one, and a
  disagreement is printed.
- **`detect` never asked whether the engine had read the model.** A model declaring an
  axiom the engine does not recognise loads, is skipped with a line on stderr, and
  judges nothing -- and an empty answer is clean, so a model none of which was applied
  reported exit 0. `gate` already caught this and `detect` did not call it. The silence
  gate now runs in `detect` too, floored at 2 under a new `model_not_read` row. A model
  that declares no axiom at all is refused by both verbs for the same reason.
- **A malformed model exited 1, which this package's contract reads as findings.**
  `yaml.YAMLError` is not a `ValueError`, so an unparseable model, one that parses to a
  list, and one the engine refuses structurally all escaped as tracebacks with no
  OUTCOME line. Every way a model can fail to load now arrives as `FeedError`, raised
  where the engine is imported.
- **Six of the engine's twelve decline reasons had no floor row.** They fell to the
  unclassified floor, which is 2 and is the safe direction -- so the answer was right
  and the run reported them as unscorable rather than decided. All twelve have rows,
  derived from the engine's closed enum so a thirteenth fails a test.
- **A deliverable that vanished between captures kept its owner and its ownership
  edge**, asserting that a consultant owns something the tracker no longer holds. It is
  no longer fed; absence is Stage 1's finding and has its own word for it. Guarded on
  the latest capture being complete, so a partial export is not read as a departure.
- **The burn-in was published off by one.** The engine's floor is ten observations and
  the feeder derives one point per capture while dropping the first, so the tool needs
  eleven captures. Measured by sweeping, not by arithmetic. The record now carries both
  numbers and the documents cite the one they are about.
- **The Astropy declaration's numbers were Stage 1's**, attributed to the Stage 2 run:
  18 deliverables are fed and 14 orphans reported, where three passages said 19 and 15.
- `[project.urls]`, so the published page links to its own source, issues and the
  findings beside them. 0.1.0 shipped without them and a release's metadata is
  immutable, so the gap stands on that version. Three of the five published siblings
  carry these and two did not, which is an omission rather than a choice -- and nothing
  in the parity test that wires a new repository looks for it.

### Changed

- **The Astropy declaration no longer names a real committee as its reviewer.** It
  signed as the Astropy SPOC and Finance Committee with the funding call's nominal
  selection date; that committee selected funding requests and never read a document
  this repository generates. It now discloses itself the way the fixture and the Jira
  corpus already did. `Engagement.disclosure` makes the convention reportable --
  `declare` and `gate` print *NOT SIGNED, disclosed as DERIVED* rather than *reviewed
  by* -- and a disclosed declaration stays admitted, because a derived corpus has to
  fill those fields to be usable at all.
- **The grader job no longer goes red because upstream published.** It installed the
  newest in-range engine and failed on any difference, so the day `arbiter-engine`
  0.1.14 lands every push reddens over nothing this repository did. The reproduction is
  now pinned to the recorded version -- which is the question that step is really about
  -- and a newer release is reported as an advisory notice.
- `exporter.export_sha256` is read as `exporter.id` where the value is an identity
  rather than a hash; the digest key is still read, so captures written by 0.1.0 keep
  loading. A content hash would have been wrong here: two captures of one engagement
  differ by design, so hashing contents would make every pair incomparable and turn
  every regression into a SKIP.
- The hygiene sweep has two new rules, for an absolute scratch path and for a
  placeholder under a digest-named key. Both were proven against the published 0.1.0
  files, which carried one of each in fields nothing reads.
- `engine_floors.json` records the engine's module name rather than the absolute path
  it was imported from, and no longer lists `CAUSALITY` among the axioms this model
  leaves undeclared -- the engine has eight declarable families and that is not one of
  them.

## 0.1.0 -- 2026-09-11

The first release.

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
- A `detect`-mode scenario, so the ownership invariant is exercised through the engine
  and not only through the three-valued diff.
- The verbs `draft`, `gate`, `generate` and `attest`, completing the set. `draft` refuses
  to call its own output reviewed; `gate` exits 2 over anything not ready and over nothing
  at all; `generate` writes a model and a manifest as a pair and this domain's generated
  model is empty by construction; `attest` reads an artifact back through a recipient's
  door, and `detect --attest-out` writes one.
- `attestation_manifest`, which derives what the core's attestation builder reads off its
  manifest from the builder's own source, distinguishing a required attribute access from
  an optional `getattr` with a default. The contract is declared by no protocol and the
  conformance kit cannot see it.

### Changed

- `regression --json` prints a document and nothing else. It used to print the document
  and then a prose OUTCOME line, which no caller parsing the whole of stdout can read --
  found by pointing a harness at it, and guarded now for every verb that has a `--json`.
- The feeder forgets an owner who left. It recorded an owner only when a capture named
  one, so a deliverable owned early and unowned later kept the earlier name and could
  not be seen as an orphan -- which no single capture could reveal.
- `capture` stamps a harness snapshot with the present when no `--captured-at` is given.
  A snapshot has no clock of its own and a capture made now is stamped now; with no
  stamp at all, `detect` refuses the series for want of a reference to count back from.
- A finding in the presence document names a deliverable by its declared key. The core
  names a declared point by its display name and the capture side names the key, so one
  document carried two spellings of one subject and nothing joining rows by subject
  could match them.

### Not in this release

No `portfolio`, `certificate` or pipeline layer, and no `transitions_per_week`
judgment from a real engagement -- that one needs ten daily captures of a live
tracker, which is a thing only time supplies. `docs/burn-in.md` says what is
warming and what is unreachable at this cadence, and the kill criterion there is
recorded as NOT met, with the consequence that the history axiom ships as
observation-only.
