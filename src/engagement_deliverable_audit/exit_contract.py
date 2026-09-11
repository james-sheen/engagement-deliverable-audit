"""Which findings floor a run, decided here, at design time, with the reason.

The shared core composes exit codes and declares no floors, deliberately: a
shared default would be chosen once by whoever wrote the first vertical and
inherited by everyone after them without anybody deciding. So this table is this
package's, and every row carries why.

THIS PACKAGE COMPUTES ITS OWN CODE RATHER THAN COMPOSING WITH THE CORE'S, and
that is necessity rather than principle. Measured: a report carrying
`orphaned_deliverable` -- the one finding only this domain can see, and this
vertical's first scenario -- returns `exit_code` 0 from the core, because the
core scores only its own regression kinds. Composing with `max` would therefore
report a clean run over a finding that is in the report. Composition also cannot
lower anything, so a floor of 0 is only expressible by computing the code here.

CLEAN is 0, FINDINGS is 1, INCOMPLETE is 2. A code outside that set, and an
unclassified finding kind, are both 2: an answer nobody designed must not read
as clean.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

CLEAN, FINDINGS, INCOMPLETE = 0, 1, 2

#: kind -> (floor, why this floor and not another)
FLOORS: Mapping[str, tuple[int, str]] = {
    # The statement of work names it and the tracker has never heard of it.
    "declared_absent": (
        FINDINGS, "a commitment nobody is tracking is the thing this audit exists "
                  "to find"),
    # Present and not moving. Both arrive from this domain rather than the core,
    # because a tracked row with a number in it is present and enabled by every
    # structural test the core applies.
    "stalled_deliverable": (
        FINDINGS, "owned and not moving inside the window the engagement itself "
                  "declared; the window is a specification, so crossing it is a "
                  "finding and not a matter of taste"),
    "orphaned_deliverable": (
        FINDINGS, "tracked with no owner, so nobody is going to move it. A board "
                  "that colours this the same as work in progress has hidden it"),
    # The declaration said it was descoped and the tracker is still working on it.
    "disabled_in_config_but_live": (
        FINDINGS, "a change order removed it and somebody is still delivering it, "
                  "which is unbilled work or an unrecorded change order"),
    "declared_disabled": (FINDINGS, "the tracker says it is switched off"),
    "declared_unreadable": (FINDINGS, "declared, present, and carrying no value"),
    # The declaration is behind the engagement.
    "declaration_stale": (
        FINDINGS, "the statement of work this was judged against is not the latest "
                  "one; every verdict in the run was reached against superseded "
                  "commitments"),
    # Reported and not scored. A tracker carrying work the statement of work does
    # not name is normal: internal tasks, spikes, somebody else's board.
    "undeclared_present": (
        CLEAN, "a tracker holds more than an engagement's deliverables, and saying "
               "so is information rather than a fault"),
    "matched_inexactly": (
        CLEAN, "the pairing is attributed in the report; a name that needed "
               "normalising is worth seeing and is not itself a defect"),
    # We did not look. Never clean, and 2 only when the caller asked for it --
    # under `--require-complete` a partial export is a could-not-complete, and
    # without it the findings that DID come back still stand.
    "walk_incomplete": (
        FINDINGS, "absence was withheld, so the run is honest but partial; 2 under "
                  "--require-complete"),
    # --- Stage 2, from the engine -------------------------------------------
    #
    # Keyed on the CLASS and not the indicator. The engine's problem types carry the
    # indicator after a colon -- `frozen_series:transitions_per_week` -- and a floor
    # is a decision about the kind of fault, so `detect` scores the prefix. A table
    # keyed on the whole string would need a new row for every indicator anybody
    # declares, and would fall to the unclassified floor the day one landed.
    "frozen_series": (
        FINDINGS, "the quantity the model declares should vary has not varied inside "
                  "the window, so the number is no longer a measurement of anything"),
    "missing_relationship": (
        FINDINGS, "a deliverable with nobody on the other end. No threshold decided "
                  "this: the model declares that one owner is required, and an "
                  "orphan is the one finding that needs no history to see"),
    "dangling_relationship": (
        FINDINGS, "the tracker names an owner the engagement never declared, so the "
                  "edge points at nothing and crediting it toward the floor would "
                  "let a phantom topology pass"),

    # Declines. An axiom that did not answer is not a pass, and the reason decides
    # whether it is anybody's fault.
    "insufficient_samples": (
        CLEAN, "the series is still short. A warming axiom is not a fault and must "
               "not floor a run -- it is the burn-in doing what it says"),
    "warmup_unreachable": (
        FINDINGS, "the collector's cadence can NEVER present this floor, however "
                  "long it runs, which the engine states in the decline itself. "
                  "Warming ends; this does not, so it is a configuration fault and "
                  "not patience"),
    "no_threshold": (
        CLEAN, "a declared gap. No contract publishes a rate for this quantity and "
               "the model says so rather than inventing one; the other arm of the "
               "axiom still answers"),
    "missing_config": (
        INCOMPLETE, "the model declares an axiom with nothing to judge against. That "
                    "is a defect in the model, and a model defect is never findings"),
    "missing_property": (
        INCOMPLETE, "the model asks for a property the feeder did not supply. A "
                    "defect in this package rather than in the tracker, and reading "
                    "it as a clean run would hide it"),
    "missing_entity_type": (
        INCOMPLETE, "the model names an entity type nothing was fed under"),
    "missing_role": (
        INCOMPLETE, "an indicator never declared what it IS to the axiom reading it, "
                    "so somebody owes a declaration"),

    "config_unreadable": (
        FINDINGS, "every deliverable this document declares is unverifiable rather "
                  "than absent; 2 under --require-complete"),
}

#: Raised to 2 when the caller asked for a complete answer and did not get one.
WITHHELD = ("walk_incomplete", "config_unreadable")

#: Anything not in the table. Deliberately the worst code: a kind this package
#: has never classified is a kind nobody decided a floor for.
UNCLASSIFIED = INCOMPLETE


def floor(kind: str, *, require_complete: bool = False) -> int:
    if kind in WITHHELD and require_complete:
        return INCOMPLETE
    known = FLOORS.get(kind)
    return UNCLASSIFIED if known is None else known[0]


def unclassified(kinds: Iterable[str]) -> tuple[str, ...]:
    """Kinds this table has no row for, so a caller can name them in its output."""
    return tuple(sorted({k for k in kinds if k not in FLOORS}))


def code_for(kinds: Iterable[str], *, require_complete: bool = False) -> int:
    """The run's code, from the kinds it produced. Empty is clean.

    Empty being CLEAN is the one place this differs from the core's `compose`,
    where composing nothing is 2. The difference is deliberate and the subjects
    are different: composing nothing means no stage reported, which is a
    could-not-complete; producing no findings means the comparison ran and found
    nothing, which is the clean case this audit exists to be able to report.
    """
    codes = [floor(k, require_complete=require_complete) for k in kinds]
    return max(codes) if codes else CLEAN


def reasons(kinds: Iterable[str]) -> tuple[tuple[str, int, str], ...]:
    """(kind, floor, why) for each kind present, for a report that shows its work."""
    out = []
    for kind in dict.fromkeys(kinds):
        known = FLOORS.get(kind)
        out.append((kind, UNCLASSIFIED, "no row in this package's floor table")
                   if known is None else (kind, known[0], known[1]))
    return tuple(out)
