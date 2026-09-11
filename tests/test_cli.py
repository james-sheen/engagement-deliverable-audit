"""The verbs: one OUTCOME line, and a malformed document is never findings."""

from __future__ import annotations

import json
import re

import pytest

from engagement_deliverable_audit.cli import main

DECL = "examples/engagement.fixture.json"
SNAP = "examples/tracker.snapshot.json"


def _outcomes(text: str) -> list[str]:
    return [l for l in text.splitlines() if l.startswith("OUTCOME")]


def test_capture_prints_exactly_one_outcome_line(tmp_path, capsys) -> None:
    """A caller parsing output needs one place to look. Two OUTCOME lines is two
    answers; prose that might be the answer will be parsed wrongly."""
    out = tmp_path / "c.json"
    assert main(["capture", "--source", f"qa-memory:{SNAP}", "--out", str(out)]) == 0
    assert len(_outcomes(capsys.readouterr().out)) == 1


def test_every_verb_ends_on_one_outcome_line(tmp_path, capsys) -> None:
    """NON-VACUITY for the check above: the rule is the family's, not capture's."""
    out = tmp_path / "c.json"
    main(["capture", "--source", f"qa-memory:{SNAP}", "--out", str(out)])
    capsys.readouterr()
    for argv in (["declare", "--declaration", DECL],
                 ["presence", "--declaration", DECL, "--capture", str(out)],
                 ["validate-capture", str(out)],
                 ["regression", "--before", str(out), "--after", str(out),
                  "--stall-window-days", "14"]):
        main(argv)
        assert len(_outcomes(capsys.readouterr().out)) == 1, argv


@pytest.mark.parametrize("argv_for", [
    lambda p: ["declare", "--declaration", str(p)],
    lambda p: ["presence", "--declaration", str(p), "--capture", str(p)],
    lambda p: ["validate-capture", str(p)],
])
def test_a_malformed_document_is_two_and_never_one(argv_for, tmp_path, capsys) -> None:
    """Exit 1 means this package compared two documents and found something. A
    file it could not read produced no verdict at all."""
    broken = tmp_path / "broken.json"
    broken.write_text("{ this is not json", encoding="utf-8")
    assert main(argv_for(broken)) == 2
    assert "exit=2" in capsys.readouterr().out


def test_an_unreviewed_declaration_is_refused_by_name(tmp_path, capsys) -> None:
    payload = json.loads(open(DECL, encoding="utf-8").read())
    payload["reviewed_by"] = None
    candidate = tmp_path / "candidate.json"
    candidate.write_text(json.dumps(payload), encoding="utf-8")
    assert main(["declare", "--declaration", str(candidate)]) == 2
    assert "NOT REVIEWED" in capsys.readouterr().out


def test_presence_refuses_to_judge_against_an_unreviewed_declaration(tmp_path, capsys) -> None:
    payload = json.loads(open(DECL, encoding="utf-8").read())
    payload["reviewed_on"] = None
    candidate = tmp_path / "candidate.json"
    candidate.write_text(json.dumps(payload), encoding="utf-8")
    out = tmp_path / "c.json"
    main(["capture", "--source", f"qa-memory:{SNAP}", "--out", str(out)])
    capsys.readouterr()
    assert main(["presence", "--declaration", str(candidate),
                 "--capture", str(out)]) == 2
    assert "unreviewed" in capsys.readouterr().out


def test_presence_reports_the_three_states_and_exits_one(tmp_path, capsys) -> None:
    out = tmp_path / "c.json"
    main(["capture", "--source", f"qa-memory:{SNAP}", "--out", str(out)])
    capsys.readouterr()
    assert main(["presence", "--declaration", DECL, "--capture", str(out)]) == 1
    text = capsys.readouterr().out
    assert "2 moving" in text and "present and not moving" in text and "absent" in text
    assert "stalled_deliverable: D-2" in text
    assert "orphaned_deliverable: D-3" in text


def test_the_json_report_shows_which_floor_scored_the_run(tmp_path, capsys) -> None:
    """A verdict with no visible reason is a number to argue with."""
    out = tmp_path / "c.json"
    main(["capture", "--source", f"qa-memory:{SNAP}", "--out", str(out)])
    capsys.readouterr()
    main(["presence", "--declaration", DECL, "--capture", str(out), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["exit_code"] == 1 and payload["verdict"] == "findings"
    floors = {row["kind"]: row for row in payload["floors"]}
    assert floors["stalled_deliverable"]["floor"] == 1
    assert floors["undeclared_present"]["floor"] == 0
    assert all(row["why"] for row in payload["floors"])
    assert payload["unclassified"] == []


def test_a_stale_declaration_is_reported_only_when_asked(tmp_path, capsys) -> None:
    out = tmp_path / "c.json"
    main(["capture", "--source", f"qa-memory:{SNAP}", "--out", str(out)])
    capsys.readouterr()
    main(["presence", "--declaration", DECL, "--capture", str(out),
          "--latest-change-order", "3", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert "declaration_stale" in [f["kind"] for f in payload["findings"]]


def test_an_unknown_source_scheme_is_refused_naming_the_known_ones(tmp_path, capsys) -> None:
    out = tmp_path / "c.json"
    assert main(["capture", "--source", f"tracker:{SNAP}", "--out", str(out)]) == 2
    assert "qa-memory" in capsys.readouterr().out


def test_regression_requires_a_window_rather_than_defaulting_one() -> None:
    """Two exports judged under different windows are not comparable, so the
    window cannot be something the caller forgets."""
    with pytest.raises(SystemExit):
        main(["regression", "--before", "a.json", "--after", "b.json"])


def test_the_digest_is_stable_and_the_shape_is_right(tmp_path, capsys) -> None:
    out = tmp_path / "c.json"
    main(["capture", "--source", f"qa-memory:{SNAP}", "--out", str(out),
          "--print-digest"])
    first = capsys.readouterr().out
    main(["validate-capture", str(out), "--print-digest"])
    second = capsys.readouterr().out
    pattern = r"sha256:[0-9a-f]{64}"
    assert re.search(pattern, first) and re.search(pattern, second)
    assert re.search(pattern, first).group() == re.search(pattern, second).group()
