"""The astropy evidence describes itself, and a self-description is a claim.

`NOTICE` once said nothing here was copied and that no consultant named was real.
Both sentences were false and both were published. The repair pseudonymised the
two JSON documents and the fetch fixtures and left the prose beside them alone, so
`evidence/astropy-cycle5.md` went on naming a funding request after a real
maintainer, and its attribution paragraph went on describing fields the derivative
had stopped carrying -- four of its seven particulars wrong.

Nothing in the toolchain checks a sentence about the artifact itself. The hygiene
sweep matches patterns and cannot know that a paragraph has gone false, and the
suite tests the code rather than the document. What follows makes the prose
answerable to the data it describes: every identifier it cites has to resolve, and
every number it reports has to be the number a run produces.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

from engagement_deliverable_audit import capture, declaration
from engagement_deliverable_audit.vertical import register

EVIDENCE = pathlib.Path(__file__).resolve().parent.parent / "evidence"
PROSE = EVIDENCE / "astropy-cycle5.md"

# The vocabulary the substitution left behind. A deliverable is `D-NN.md`, the
# person who owns one is `C-NN`, a tracking issue is `issue-NNN`, and the one
# issue that declares no deliverable is named for that rather than numbered.
DELIVERABLE = re.compile(r"\bD-\d{2}\.md\b")
OWNER = re.compile(r"\bC-\d{2}\b")
ISSUE = re.compile(r"\bissue-\d+\b")

ALLOWED_FIELD = re.compile(
    r"\A(?:"
    r"D-\d{2}\.md"
    r"|C-\d{2}"
    r"|issue-\d+(?:-names-no-scope-of-work)?"
    r"|finance/proposal-calls/cycle5/D-\d{2}\.md"
    r")\Z")

PINNED_COMMIT = "74af2fa4de15c27b369e65f93432e1538d8b9476"


@pytest.fixture()
def evidence():
    engagement = declaration.load(json.loads(
        (EVIDENCE / "astropy-cycle5-declaration.json").read_text(encoding="utf-8")))
    export = capture.load(
        json.loads((EVIDENCE / "astropy-cycle5-capture.json").read_text(encoding="utf-8")),
        stall_window_days=engagement.stall_window_days)
    return engagement, export


@pytest.fixture()
def compared(evidence):
    from presence_audit import diff, vocabulary

    engagement, export = evidence
    vocabulary.reset()
    register()
    yield diff.compare(engagement, export)
    vocabulary.reset()


# --- the prose has to resolve against the data -----------------------------

def test_every_identifier_the_prose_cites_exists_in_the_evidence(evidence) -> None:
    """The bug this file exists for. The prose named `cruz-leadership.md` -- a real
    request named after a real person -- for as long as the pseudonymous corpus
    shipped beside it, because the commit that substituted the data never opened
    the document describing it. An identifier in the prose resolving nowhere in the
    evidence is either a survival from the source or an invention, and both should
    fail here rather than be read as fact by somebody checking the work."""
    engagement, export = evidence
    text = PROSE.read_text(encoding="utf-8")

    known_deliverables = {p.name for p in engagement.points} | {p.name for p in export.points}
    known_owners = {p.owner for p in export.points if p.owner}
    known_issues = {p.path for p in export.points if p.path}

    for cited in sorted(set(DELIVERABLE.findall(text))):
        assert cited in known_deliverables, (
            f"the prose cites {cited}, which is in neither document")
    for cited in sorted(set(OWNER.findall(text))):
        assert cited in known_owners, (
            f"the prose cites owner {cited}, which no captured point carries")
    for cited in sorted(set(ISSUE.findall(text))):
        assert cited in known_issues, (
            f"the prose cites {cited}, which the capture does not hold")


def test_the_prose_cites_enough_identifiers_to_make_that_check_mean_something(
        evidence) -> None:
    """NON-VACUITY. The loop above passes over an empty set, which is exactly what a
    document with every identifier stripped out would produce -- and stripping them
    was one of the ways this could have been repaired. It was not the way chosen, so
    say so here rather than let a silent zero stand in for a check."""
    text = PROSE.read_text(encoding="utf-8")
    cited = set(DELIVERABLE.findall(text)) | set(ISSUE.findall(text))
    assert len(cited) >= 4, f"only {len(cited)} identifiers cited; the check is nearly vacuous"


def test_the_result_the_prose_reports_is_the_result_the_evidence_produces(
        compared) -> None:
    """A table of findings is a claim about a run. This one is transcribed by hand
    into the document and nothing re-derived it, so it could drift from the evidence
    the moment either was touched -- which is the same failure as the attribution
    paragraph, one section down."""
    text = PROSE.read_text(encoding="utf-8")
    counted: dict[str, int] = {}
    for kind, number in re.findall(r"\|\s+`(\w+)`\s+\|\s+(\d+)\s+\|", text):
        counted[kind] = int(number)
    assert counted, "no findings table found in the prose to check against"

    actual: dict[str, int] = {}
    for finding in compared.findings:
        actual[finding.kind] = actual.get(finding.kind, 0) + 1

    assert counted == actual, (
        f"the prose reports {counted} and the evidence produces {actual}")


# --- no real identifier survives in the data -------------------------------

def test_no_identifying_field_in_either_document_carries_a_real_identifier(
        evidence) -> None:
    """An allow-list and not a deny-list. A deny-list of handles and file names has
    to predict what a real identifier looks like; the source has already produced
    one shaped like a surname, one shaped like a product, and one shaped like a
    sentence. Anything outside the substituted vocabulary fails and gets read by a
    person, which is the outcome worth having."""
    engagement, export = evidence
    for point in engagement.points:
        assert ALLOWED_FIELD.match(point.name), (
            f"declared point name {point.name!r} is outside the pseudonym vocabulary")
    for point in export.points:
        assert ALLOWED_FIELD.match(point.name), (
            f"captured point name {point.name!r} is outside the pseudonym vocabulary")
        assert ALLOWED_FIELD.match(point.path), (
            f"captured point path {point.path!r} is outside the pseudonym vocabulary")
        if point.owner is not None:
            assert ALLOWED_FIELD.match(point.owner), (
                f"captured owner {point.owner!r} is outside the pseudonym vocabulary")


def test_the_basis_of_every_declared_point_is_pseudonymous_too(evidence) -> None:
    """The basis is where a declaration says where it got each point, so it holds a
    path and a quote -- and those were real file names until the substitution. It is
    also the field a reader checks first, and it is not reached by the point-name
    assertions above."""
    raw = json.loads(
        (EVIDENCE / "astropy-cycle5-declaration.json").read_text(encoding="utf-8"))
    for point in raw["points"]:
        basis = point.get("basis") or {}
        for field in ("location", "quote"):
            value = basis.get(field)
            if value is None:
                continue
            assert ALLOWED_FIELD.match(value), (
                f"basis.{field} {value!r} is outside the pseudonym vocabulary")


def test_no_at_handle_appears_anywhere_in_either_document(evidence) -> None:
    """What was actually published: four maintainers by GitHub handle. The pinned
    source is written `astropy/astropy-project@74af2fa4`, which is a git ref and the
    one shape allowed through."""
    for name in ("astropy-cycle5-declaration.json", "astropy-cycle5-capture.json"):
        blob = (EVIDENCE / name).read_text(encoding="utf-8")
        for hit in re.findall(r"@[A-Za-z0-9][A-Za-z0-9_-]*", blob):
            assert hit == "@74af2fa4", f"{name} carries {hit!r}, which reads as a handle"


# --- the licence duty ------------------------------------------------------

def test_the_attribution_names_the_licence_and_the_commit_it_pins(evidence) -> None:
    """CC BY 4.0 asks for attribution and for modifications to be indicated. The
    pseudonymisation is the modification, so the section has to carry both halves --
    losing either one while the derivative still ships is the licence failure, not a
    tidiness one."""
    text = PROSE.read_text(encoding="utf-8")
    heading = "## Attribution, which the licence requires"
    assert heading in text
    section = text.split(heading, 1)[1].split("\n## ", 1)[0]
    assert "CC BY 4.0" in section, "the section names no licence"
    assert PINNED_COMMIT in section, "the section pins no commit"
    assert "substitut" in section, (
        "the section does not indicate that the material was modified")
