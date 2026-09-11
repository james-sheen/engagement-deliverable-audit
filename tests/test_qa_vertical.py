"""The grader vertical, without the harness: what the tier grades and what it refuses.

`battery/probe_qa_vertical.py` runs the scenarios end to end. These are the claims
that should fail here, fast, rather than as a mismatch inside a six-phase run -- and
one of them is a tripwire that goes red if this package ever moves its findings,
because the harness reads that key with a plain `.get()` and a nested one would read
as no findings at all.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "battery"))

import qa_vertical  # noqa: E402
from qa_orchestrator.substrates.memory import MemorySubstrate  # noqa: E402
from qa_orchestrator.vocabulary import ScenarioError, SubstrateUnavailable  # noqa: E402

WINDOW = 14.0


def _setup(**extra):
    return {"entities": [{"name": "D-1", "value": 2, "owner": "ana",
                          "state": "In Progress"}], **extra}


def _tier(**extra):
    return qa_vertical.EngagementSubstrate(_setup(**extra))


# --- what the tier grades --------------------------------------------------

def test_a_stalled_deliverable_is_present_and_not_reading() -> None:
    """The override's whole reason, and the base tier is the control.

    `MemorySubstrate` calls anything carrying a number `reading`, and a transition
    sixty days old is a number. In this domain that is the STALLED case, which is
    the answer the package exists to keep apart from absent. Asserting both halves
    here means the day somebody deletes the override, this fails rather than a
    scenario passing for the wrong reason.
    """
    tier = _tier()
    tier.slip("D-1", 60)
    assert tier.state("D-1") == "disabled"
    assert MemorySubstrate.state(tier, "D-1") == "reading"


def test_an_orphaned_deliverable_cannot_read_at_any_age() -> None:
    tier = _tier()
    tier.orphan("D-1")
    assert tier.state("D-1") == "disabled"


def test_a_reassignment_leaves_it_reading() -> None:
    """The other half of every detection claim: this is not a fault."""
    tier = _tier()
    tier.reassign("D-1", "erin")
    assert tier.state("D-1") == "reading"


def test_a_removed_deliverable_is_absent_and_an_unknown_one_is_neither() -> None:
    """`absent` means declared and not in the tracker. An entity this tier never
    served is a different fact, and answering `absent` to both lets another
    vertical's scenario -- or a typo -- have its expectation met by a tier that was
    not serving the thing at all."""
    tier = _tier()
    tier.remove("D-1")
    assert tier.state("D-1") == "absent"
    with pytest.raises(SubstrateUnavailable, match="not one of them"):
        tier.state("Fan1")


def test_the_window_is_read_from_the_declaration_and_never_defaulted(tmp_path) -> None:
    bad = tmp_path / "no-window.json"
    bad.write_text(json.dumps({"points": []}), encoding="utf-8")
    with pytest.raises(SubstrateUnavailable, match="stall_window_days"):
        _tier(declaration=str(bad))


def test_slip_refuses_a_deliverable_with_no_recorded_transition() -> None:
    """`value: null` is *no transition recorded*, not a transition at zero. Adding
    days to it would invent a history the export does not carry."""
    tier = _tier()
    tier.disable("D-1")
    with pytest.raises(SubstrateUnavailable, match="no recorded transition"):
        tier.slip("D-1", 5)


# --- what the verbs refuse -------------------------------------------------

@pytest.mark.parametrize("payload", [{}, {"entity": "D-1"}, {"to": "erin"},
                                     {"entity": "D-1", "to": "erin", "extra": 1}])
def test_reassign_refuses_a_payload_it_cannot_act_on(payload) -> None:
    with pytest.raises(ScenarioError):
        qa_vertical.REASSIGN.validate(payload, "phase 1", 1)


@pytest.mark.parametrize("payload", [{"entity": "D-1"}, {"entity": "D-1", "days": "soon"},
                                     {"entity": "D-1", "days": 0},
                                     {"entity": "D-1", "days": -3}])
def test_slip_refuses_a_payload_it_cannot_act_on(payload) -> None:
    with pytest.raises(ScenarioError):
        qa_vertical.SLIP.validate(payload, "phase 1", 1)


def test_orphan_takes_a_name_and_not_a_mapping() -> None:
    assert qa_vertical.ORPHAN.validate("D-1", "phase 1", 1) == "D-1"
    with pytest.raises(ScenarioError):
        qa_vertical.ORPHAN.validate({"entity": "D-1"}, "phase 1", 1)


def test_every_verb_this_vertical_adds_is_one_the_core_does_not_ship() -> None:
    """`register_verb` refuses a name already taken, so a collision is a hard error
    at registration rather than a shadowed built-in. This is the cheaper place to
    find out, and it names the four rather than counting them."""
    from qa_orchestrator import actions

    shipped = set(actions.known_verbs())
    mine = {verb.name for verb in qa_vertical.VERBS}
    assert mine == {"orphan", "reassign", "slip", "bounce"}
    assert not mine & shipped, f"{mine & shipped} already exist in this build"


# --- the tripwire ----------------------------------------------------------

def test_the_schema_names_keys_this_package_actually_writes(tmp_path, capsys) -> None:
    """DERIVED: run the tool, read the document, and require every key the profile
    names to be in it.

    `ReportSchema.findings` is read with a plain `.get()` and no dotted path, so a
    findings list that moved under another key would leave the harness with nothing
    -- and an expectation naming the absence of a finding is true of an empty list.
    A sibling in this family has exactly that defect and carries it as an open
    upstream ask. This package is only safe from it while `findings` stays at the
    top level, which is what this asserts.
    """
    from engagement_deliverable_audit.cli import main

    import qa_orchestrator.referee as referee_module
    schema = qa_vertical._schema(referee_module)

    capture = tmp_path / "c.json"
    main(["capture", "--source", "qa-memory:examples/tracker.snapshot.json",
          "--out", str(capture)])
    capsys.readouterr()
    main(["presence", "--declaration", "examples/engagement.fixture.json",
          "--capture", str(capture), "--json"])
    document = json.loads(capsys.readouterr().out)

    assert schema.findings in document, (
        f"the profile reads findings from {schema.findings!r} and the document has "
        f"{sorted(document)}; the harness would see none and report agreement")
    assert document[schema.findings], "the fixture produced no findings to check keys against"
    for finding in document[schema.findings]:
        assert any(key in finding for key in schema.subject), schema.subject
        assert any(key in finding for key in schema.text), schema.text


def test_the_document_names_a_deliverable_one_way(tmp_path, capsys) -> None:
    """A finding the core raises named the point by its display name while one from
    the capture named the key, in the same document. Anything joining rows by
    subject saw two deliverables, and the grader matches subjects for EQUALITY, so
    neither could match the other."""
    from engagement_deliverable_audit.cli import main

    capture = tmp_path / "c.json"
    main(["capture", "--source", "qa-memory:examples/tracker.snapshot.json",
          "--out", str(capture)])
    capsys.readouterr()
    main(["presence", "--declaration", "examples/engagement.fixture.json",
          "--capture", str(capture), "--json"])
    document = json.loads(capsys.readouterr().out)

    declared = {point["id"] for point in json.loads(
        Path("examples/engagement.fixture.json").read_text(encoding="utf-8"))["points"]}
    named = {f["deliverable"] for f in document["findings"]}
    # A subject that is not a declared id is fine and expected: `undeclared_present`
    # names a tracker key this declaration never mentioned, which is the finding.
    # The defect was narrower and is what this pins: a subject spelled as an id
    # followed by the declared title.
    titled = sorted(name for name in named
                    for point in declared if name.startswith(point + " "))
    assert not titled, (f"these subjects carry the declared title beside the key, so "
                        f"the same deliverable is named two ways: {titled}")
    assert any(name in declared for name in named), (
        "no finding named a declared deliverable, so this check compared nothing")
