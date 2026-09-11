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

Nothing is released. There is no distribution on the index under this name yet,
and `__version__` carries a `.dev0` suffix so that an accidental build cannot be
mistaken for one.
