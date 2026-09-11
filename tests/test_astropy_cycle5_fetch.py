"""The Cycle 5 fetch: the title rule, the join, and what it refuses to call an owner.

Each of these is a rule that was wrong once. The title rule returned a project-team
bullet for half a real document set while reporting it as a title; the owner rule has
to distinguish a representative named from one still to be named; and the join has to
survive the percent-encoding GitHub puts in a link to a file name holding a plus.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "battery"))

import fetch_astropy_cycle5 as fetch  # noqa: E402


# --- the title rule --------------------------------------------------------

def test_a_document_that_fills_in_the_template_label() -> None:
    assert fetch.title_in("### Title\n\nQuantities with Array API support\n\n"
                          "### Project Team\n- someone\n") \
        == "Quantities with Array API support"


def test_a_document_that_replaces_the_label_with_the_title() -> None:
    """The first heading IS the title, and about half of a real set is written this
    way. The rule that missed this skipped every heading and returned the opening
    bullet of the next section, which is a different field entirely."""
    assert fetch.title_in("### Expanding objects to be serialized to ASDF\n\n"
                          "### Project Team\n- Perry Greenfield: 27 years of\n") \
        == "Expanding objects to be serialized to ASDF"


def test_a_blank_label_followed_by_a_heading_is_no_title_at_all() -> None:
    """Not the next line, which is a heading, and not the file name. A point with no
    title has to be able to say so."""
    assert fetch.title_in("### Title\n\n### Project Team\n- someone\n") == ""


def test_a_document_with_no_heading_has_no_title() -> None:
    assert fetch.title_in("just prose, no headings at all\n") == ""


# --- the join --------------------------------------------------------------

def test_the_scope_of_work_link_is_the_join_key() -> None:
    issue = {"body": "Scope of Work - https://github.com/astropy/astropy-project/"
                     "blob/main/finance/proposal-calls/cycle5/votable_vo.md\n"}
    assert fetch.scope_of(issue) == "votable_vo.md"


def test_a_percent_encoded_file_name_joins_to_the_decoded_one() -> None:
    """GitHub writes `+` as `%2B` in a link. The declaration side reads the name from
    the tree, where it is a plus, so a capture that did not decode would report the
    request absent and the issue undeclared -- two findings for one encoding."""
    issue = {"body": "Scope of Work - https://github.com/astropy/astropy-project/blob/"
                     "main/finance/proposal-calls/cycle5/Streicher-Debian%2BUbuntu.md"}
    assert fetch.scope_of(issue) == "Streicher-Debian+Ubuntu.md"


def test_an_issue_naming_no_scope_of_work_is_reported_rather_than_dropped() -> None:
    assert fetch.scope_of({"body": "There will be one contract to fund several"}) is None
    assert fetch.scope_of({"body": None}) is None


# --- the owner rule --------------------------------------------------------

def test_a_named_representative_is_an_owner() -> None:
    assert fetch.cotr_of({"body": "COTR: @tomdonaldson\n"}) == "tomdonaldson"


def test_a_representative_still_to_be_named_is_not_an_owner() -> None:
    """`TBD` is the common case in a real set, and reading it as a name would turn
    fifteen unowned deliverables into fifteen owned ones."""
    assert fetch.cotr_of({"body": "Finance Committee Contact: @kelle\nCOTR: TBD\n"}) is None


def test_the_finance_contact_is_not_read_as_the_owner() -> None:
    """The assignee on these issues is the finance contact, who handles invoices. The
    COTR is who the work is owed by, and the two are different people."""
    assert fetch.cotr_of({"body": "Finance Committee Contact: @kelle\n"}) is None


def test_two_representatives_are_both_kept() -> None:
    assert fetch.cotr_of({"body": "COTR: @one and @two\n"}) == "one, two"


# --- what counts as a funding request --------------------------------------

def test_the_template_and_the_call_are_not_funding_requests() -> None:
    """The call document is named after its own folder and sits beside the requests.
    Counting it produced the only absent deliverable in the first real run -- a
    deliverable the tracker had never heard of, because it was never one."""
    assert not fetch._is_request("template.md", "finance/proposal-calls/cycle5")
    assert not fetch._is_request("cycle5.md", "finance/proposal-calls/cycle5")
    assert not fetch._is_request("aperio-docs.png", "finance/proposal-calls/cycle5")
    assert fetch._is_request("hamogu.md", "finance/proposal-calls/cycle5")


# --- the window the engagement never declared -------------------------------

def _assembled(window):
    import datetime as dt
    return fetch.declaration_for(
        "74af2fa4de15c27b369e65f93432e1538d8b9476", ["hamogu.md"],
        {"hamogu.md": "X-ray spectroscopy"},
        dt.datetime(2026, 9, 11, tzinfo=dt.timezone.utc), window)


def test_no_window_means_no_field_rather_than_a_default() -> None:
    """The refusal is the finding. These documents set a period of performance and
    require updates in the tracking issue without naming an interval, so a number
    here would be the auditor's. `declare` refuses a declaration with no window, and
    that refusal is the first thing this real scope of work produces."""
    assert "stall_window_days" not in _assembled(None)


def test_a_supplied_window_is_carried_and_says_whose_it_is() -> None:
    declaration = _assembled(90.0)
    assert declaration["stall_window_days"] == 90.0
    assert "DECLARES NO WINDOW" in declaration["window_basis"]


def test_the_declaration_refuses_to_load_without_the_window(tmp_path) -> None:
    """The other half: that the package really does refuse, rather than this test
    asserting a key is absent from a document nothing reads."""
    from engagement_deliverable_audit import declaration as module

    with __import__("pytest").raises(module.DeclarationError, match="no stall_window_days"):
        module.load(_assembled(None))
    assert module.load(_assembled(90.0)).stall_window_days == 90.0
