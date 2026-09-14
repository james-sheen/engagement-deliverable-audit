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


def test_the_table_covers_the_engines_whole_decline_vocabulary() -> None:
    """The same rule as above, applied to the OTHER upstream that feeds this table.

    The core's regression kinds were derived; the engine's decline reasons were not.
    Six of the engine's twelve had rows and six did not, and the six without got the
    right answer for the wrong reason: anything unknown falls to `UNCLASSIFIED`, which
    is 2, which is the safe direction -- so nothing failed and nothing could. The cost
    was that `detect` reported them as *no row in this package's floor table, so this
    run could not be scored*, which says the table is incomplete rather than that the
    engine declined for a reason this package decided about.

    `NotEvaluatedReason` is a closed enum and the engine's own docstring says so, which
    is what makes deriving from it safe. A thirteenth member now fails here.
    """
    # Imported, not skipped: this suite's convention is that an engine-dependent
    # test fails to import rather than vanishing from the run. A skip is how a
    # check stops running without anybody noticing.
    from arbiter_engine.types import NotEvaluatedReason

    vocabulary = {member.value for member in NotEvaluatedReason}
    assert len(vocabulary) >= 12, (
        f"the engine offered {len(vocabulary)} decline reasons, which is fewer than "
        f"this package was written against; deriving from a shrunken set would make "
        f"this check pass over almost nothing")
    uncovered = sorted(vocabulary - set(x.FLOORS))
    assert uncovered == [], (
        f"the engine can decline with {uncovered} and this table has no row for them, "
        f"so a run would report them as unscorable rather than as decided")


def test_exactly_these_engine_declines_are_floored_clean_and_no_others() -> None:
    """The whole list, pinned, because a 0 can only come from somebody choosing it.

    Everything this table has never heard of floors at 2, so every CLEAN row is a
    decision: this package saying the axiom did not answer and that is nobody's fault.
    There are four from `arbiter-engine` 0.1.14 and three below it, and they are
    different reasons for the same floor -- warming, a gap the model declares
    rather than invents, one arm of a multi-armed axiom while another answers,
    and a subject the engine itself excludes. The list is the decision; which of
    its members the installed engine has is the engine's business, so the
    assertion intersects the two.

    Pinned as a set rather than a count: a count would survive one row being swapped
    for another, which is exactly the edit worth catching.
    """
    # Imported, not skipped: this suite's convention is that an engine-dependent
    # test fails to import rather than vanishing from the run. A skip is how a
    # check stops running without anybody noticing.
    from arbiter_engine.types import NotEvaluatedReason

    vocabulary = {member.value for member in NotEvaluatedReason}
    clean = sorted(reason for reason in vocabulary
                   if x.FLOORS[reason][0] == x.CLEAN)
    # `partially_checked` joined at `arbiter-engine` 0.1.14, and it is CLEAN for
    # the same reason `no_threshold` is: the engine split it out of that reason
    # for the case where one arm of a multi-armed axiom has nothing to judge
    # against while another arm answers. Floored differently from the reason it
    # came from, one envelope would change verdict on a release that changed no
    # behaviour.
    # INTERSECTED WITH WHAT THIS ENGINE OFFERS. The list is the decision; which
    # of its members exist is the engine's business, and this package's pin
    # admits releases on both sides of `partially_checked` arriving. Asserting
    # the full list unconditionally makes the test a claim about the resolver's
    # pick rather than about the decisions in the table.
    decided = {"insufficient_samples", "no_threshold", "not_applicable",
               "partially_checked"}
    assert clean == sorted(decided & vocabulary), (
        f"the engine declines floored CLEAN are {clean}; each is a decline this "
        f"package says is a declared gap or a warming axiom rather than an unanswered "
        f"question, and each is a decision rather than a default")


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
