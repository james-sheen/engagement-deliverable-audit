"""The acceptance, against committed real data rather than a fixture.

A fixture can be built to show anything. These assertions run over 248 unresolved
Apache ZooKeeper issues from a published dataset, reduced to keys, owners, statuses
and day counts. `evidence/README.md` carries the attribution the licence requires
and says plainly which half of the acceptance this does not meet.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from engagement_deliverable_audit import capture, declaration, exit_contract
from engagement_deliverable_audit.vertical import register

EVIDENCE = pathlib.Path(__file__).resolve().parent.parent / "evidence"


@pytest.fixture()
def compared():
    from presence_audit import diff, vocabulary

    engagement = declaration.load(json.loads(
        (EVIDENCE / "jira-declaration.json").read_text(encoding="utf-8")))
    export = capture.load(
        json.loads((EVIDENCE / "jira-capture.json").read_text(encoding="utf-8")),
        stall_window_days=engagement.stall_window_days)
    vocabulary.reset()
    register()
    yield diff.compare(engagement, export), engagement, export
    vocabulary.reset()


def test_the_corpus_is_real_and_large_enough_to_mean_something(compared) -> None:
    """NON-VACUITY. Two hundred points agreeing proves more than two, and a file
    that had been truncated would make every assertion below pass over almost
    nothing."""
    _report, engagement, export = compared
    assert len(engagement.points) > 200
    assert len(export.points) == len(engagement.points)
    assert all(p.name.startswith("ZOOKEEPER-") for p in engagement.points)


def test_a_real_stalled_deliverable_is_present_and_not_reading(compared) -> None:
    """The acceptance's own wording. Not *a finding exists* -- the three-valued
    answer specifically, with the stalled ones inside the middle state."""
    report, _engagement, _export = compared
    counts = report.counts()
    assert counts["present_not_reading"] > 0
    assert counts["reading"] > 0, ("every point landing in one state is what a "
                                   "broken window would also produce")
    stalled = [f for f in report.findings if f.kind == "stalled_deliverable"]
    assert stalled, "no real deliverable was reported as owned and not moving"
    assert counts["present_not_reading"] == len(report.findings)


def test_real_orphans_are_separated_from_real_stalls(compared) -> None:
    """Both are present-and-not-moving; only one of them has somebody to ask. On
    this corpus both occur, which a fixture had to be built to achieve."""
    report, _e, _x = compared
    kinds = {f.kind for f in report.findings}
    assert {"stalled_deliverable", "orphaned_deliverable"} <= kinds


def test_absence_is_zero_here_by_construction_and_not_by_good_news(compared) -> None:
    """Recorded as an assertion so the reason survives. An issue that was never
    created leaves nothing to declare, so a single dump cannot produce absence."""
    report, _e, _x = compared
    assert report.counts()["declared_absent"] == 0


def test_the_core_and_this_package_agree_over_two_hundred_real_findings(compared) -> None:
    """The upstream gap, reproduced on real data, and now closed.

    This asserted the core reported CLEAN over two hundred real findings --
    `presence-audit` #7 -- and said in as many words that it was EXPECTED TO
    FAIL when that was resolved, so the workaround would be revisited rather
    than carried. It failed, on the release that resolved it, saying exactly
    that. The floor table was re-read against it and the vertical now declares
    `regression_kinds`.

    What it asserts from here is the stronger claim: the two scorings AGREE on
    real data. Below 0.1.8 the core cannot know, so that arm asserts the gap
    instead -- neither arm skips, because a skip is how a check stops running
    without anybody noticing.
    """
    report, _e, _x = compared
    kinds = [f.kind for f in report.findings]
    assert len(report.findings) > 200
    assert exit_contract.code_for(kinds) == exit_contract.FINDINGS

    from presence_audit import vocabulary as _core_vocabulary

    if hasattr(_core_vocabulary, "regression_kinds"):
        assert report.exit_code == exit_contract.FINDINGS, (
            "the core reads this vertical's own regression kinds from 0.1.8, so "
            "two hundred findings it can now score must not compose a clean "
            "verdict")
        assert report.counts()["regressions"] > 0
    else:
        assert report.exit_code == exit_contract.CLEAN, (
            "the installed core cannot score a domain's own findings, which is "
            "the gap this package works around; it answered something else")
        assert report.counts()["regressions"] == 0


def test_the_evidence_readme_says_what_the_installed_core_reports(compared) -> None:
    """The paragraph describing this run, held to the run.

    `evidence/README.md` went on saying the core's exit code here was 0 for
    twelve days after `presence-audit` 0.1.8 made it 1: the test above asserted
    the behaviour and nothing asserted the sentence. Its numbers are read back
    against whichever core is installed, so each arm of the range is checked
    wherever that arm runs.
    """
    from presence_audit import vocabulary as _core_vocabulary

    report, _e, _x = compared
    text = " ".join((EVIDENCE / "README.md").read_text(encoding="utf-8").split())
    assert f"**{len(report.findings)} findings**" in text
    if hasattr(_core_vocabulary, "regression_kinds"):
        claim = f"`DiffReport.exit_code` is **{report.exit_code}**"
    else:
        claim = f"the core reports {report.exit_code}**"
    assert claim in text, (
        f"evidence/README.md does not state what the installed core reports "
        f"over this corpus: expected {claim!r}")


def test_the_committed_capture_has_the_exporter_shape_the_script_writes() -> None:
    """Evidence that no longer matches its generator, caught without a network fetch.

    `FINDINGS.md` claimed the fetch script computes a real digest of the bytes it
    range-fetches. It does -- and the committed capture had been hand-edited instead of
    regenerated, so it carried the `id` and not the digest, and the claim was true of the
    script and false of the shipped file. Re-deriving the corpus also showed the prose
    had drifted in two more places: the committed declaration said *the Apache tracker*
    where the script now writes the project name.

    Derived from the script's own source rather than transcribed, so a future change to
    what it writes fails here instead of leaving the evidence quietly behind. The bytes
    cannot be re-fetched in a unit test; the SHAPE can, and the shape is what drifted.
    """
    import ast
    import re

    script = (EVIDENCE.parent / "battery" / "fetch_jira_corpus.py").read_text(
        encoding="utf-8")
    # The keys the script puts in the exporter block, read off its AST.
    tree = ast.parse(script)
    written = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (isinstance(key, ast.Constant) and key.value == "exporter"
                        and isinstance(value, ast.Dict)):
                    written = {k.value for k in value.keys
                               if isinstance(k, ast.Constant)}
    assert written, "could not read the exporter keys off the script; the derivation broke"

    capture = json.loads((EVIDENCE / "jira-capture.json").read_text(encoding="utf-8"))
    shipped = set(capture.get("exporter") or {})
    assert shipped == written, (
        f"the script writes {sorted(written)} and the committed evidence carries "
        f"{sorted(shipped)}; the corpus was edited rather than re-derived")

    digest = (capture["exporter"].get("export_sha256") or "").split(":", 1)[-1]
    assert re.fullmatch(r"[0-9a-f]{64}", digest), (
        f"{digest[:24]!r} is not a hex digest")
    assert len(set(digest)) > 4, (
        "a digest of four or fewer distinct characters is a placeholder; the shipped "
        "evidence carried sixty-four of one letter before this")
