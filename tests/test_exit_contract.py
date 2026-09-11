"""The floor table: complete over what this package can emit, and never silent."""

from __future__ import annotations

import pytest

from engagement_deliverable_audit import exit_contract as x

#: Kinds the shared core can raise that this domain cannot produce, with why.
#: Written down rather than left out, because an absent row and an impossible
#: kind look identical in a table.
CANNOT_OCCUR = {
    "threshold_missing": "points here carry no thresholds; a deliverable has a due "
                         "date, not a limit",
    "threshold_drift": "the same reason",
    "threshold_direction_conflict": "the same reason",
    "interface_divergence": "belongs to a hardware walk and has no analogue here",
}


def test_every_kind_in_the_table_carries_a_reason() -> None:
    """A floor with no reason is a preference. The table is the place the decision
    is recorded, so an empty reason is a defect in the record."""
    thin = [k for k, (_, why) in x.FLOORS.items() if len(why) < 20]
    assert thin == [], f"{thin} have no stated reason"


def test_the_table_covers_every_regression_kind_this_domain_can_produce() -> None:
    """Derived from the core rather than typed, so a new regression kind upstream
    shows up here instead of quietly falling to the unclassified floor."""
    from presence_audit.diff import REGRESSION_KINDS

    assert REGRESSION_KINDS, "the core yielded no kinds; this check would pass over nothing"
    uncovered = sorted(set(REGRESSION_KINDS) - set(x.FLOORS) - set(CANNOT_OCCUR))
    assert uncovered == [], f"no floor decided for {uncovered}"


def test_the_exclusions_are_real_kinds_and_not_typos() -> None:
    """A misspelled exclusion would silently widen the check above."""
    from presence_audit.diff import REGRESSION_KINDS

    stray = sorted(set(CANNOT_OCCUR) - set(REGRESSION_KINDS))
    assert stray == [], f"{stray} are excused and are not kinds the core raises"


def test_nothing_produced_is_clean_and_that_differs_from_the_core_on_purpose() -> None:
    """Composing nothing is 2 in the core, because no stage reported. Producing no
    findings is 0 here, because the comparison ran and found nothing -- which is
    the answer this audit exists to be able to give."""
    from presence_audit.exit_contract import compose

    assert x.code_for([]) == x.CLEAN
    assert compose() == x.INCOMPLETE


def test_a_kind_nobody_classified_is_never_clean() -> None:
    assert x.code_for(["a_kind_from_the_future"]) == x.INCOMPLETE
    assert x.unclassified(["a_kind_from_the_future", "declared_absent"]) \
        == ("a_kind_from_the_future",)


@pytest.mark.parametrize("kind", ["undeclared_present", "matched_inexactly"])
def test_the_reported_and_not_scored_rows_really_are_zero(kind) -> None:
    """These are the rows that a `max` composition with the core's exit code could
    not express, which is the other half of why the code is computed here."""
    assert x.floor(kind) == x.CLEAN


def test_withholding_is_never_clean_and_is_two_only_when_asked() -> None:
    for kind in x.WITHHELD:
        assert x.floor(kind) == x.FINDINGS
        assert x.floor(kind, require_complete=True) == x.INCOMPLETE


def test_the_worst_kind_present_decides() -> None:
    mixed = ["undeclared_present", "stalled_deliverable", "matched_inexactly"]
    assert x.code_for(mixed) == x.FINDINGS
    assert x.code_for(mixed + ["a_kind_from_the_future"]) == x.INCOMPLETE


def test_reasons_are_reported_for_what_was_actually_seen() -> None:
    out = dict((kind, why) for kind, _floor, why in
               x.reasons(["stalled_deliverable", "a_kind_from_the_future"]))
    assert "window" in out["stalled_deliverable"]
    assert "no row" in out["a_kind_from_the_future"]
