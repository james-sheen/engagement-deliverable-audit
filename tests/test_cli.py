"""The verbs: one OUTCOME line, and a malformed document is never findings."""

from __future__ import annotations

import json
import re

import pytest

from engagement_deliverable_audit.cli import main

DECL = "examples/engagement.fixture.json"
SNAP = "examples/tracker.snapshot.json"
MODEL = "examples/engagement.model.yaml"
CAPTURE = "evidence/astropy-cycle5-capture.json"
#: The declaration that MATCHES that capture. Pairing the fixture with the
#: astropy capture feeds nothing, and a verb that judged nothing is a weak
#: exercise of a claim about what it prints.
CAPTURE_DECL = "evidence/astropy-cycle5-declaration.json"


def _outcomes(text: str) -> list[str]:
    return [l for l in text.splitlines() if l.startswith("OUTCOME")]


def test_with_json_stdout_is_a_document_and_nothing_else(tmp_path, capsys) -> None:
    """Every verb that has a `--json`, and the whole of stdout parsed, not a slice.

    `regression` printed its document and then an OUTCOME line, while `presence`
    returned before prose. One verb of one tool, disagreeing with its sibling about
    whether stdout is a document. A harness pointed at it parses the WHOLE of
    stdout, catches the decode error, and carries on with no report -- so the
    expectations that name a finding fail, and every expectation that names the
    absence of one passes for having nothing to look at.

    Asserting on the parse of the entire stream is the whole point: a test that
    sliced the JSON out first would have passed throughout.

    **THE DOCSTRING SAID *EVERY VERB* AND THE LOOP RAN TWO OF THREE.** `detect` also
    takes `--json` and was not here, which matters more than the other two: it is the
    verb with a side effect, and `--attest-out` prints a line about the file it wrote.
    That line is guarded on `--json` -- correctly, as it turns out -- and nothing
    checked it. The verbs are now derived from the parser, so a fourth `--json` lands
    in this loop on the day it is added rather than the day somebody notices.
    """
    out = tmp_path / "c.json"
    main(["capture", "--source", f"qa-memory:{SNAP}", "--out", str(out)])
    capsys.readouterr()

    # Derived from the parser, then matched against the invocations below. A verb with
    # a `--json` and no entry here fails the assertion rather than being skipped.
    import argparse as _argparse

    from engagement_deliverable_audit.cli import build_parser
    takes_json = {
        name for name, sub in next(
            action for action in build_parser()._actions
            if isinstance(action, _argparse._SubParsersAction)).choices.items()
        if any("--json" in (a.option_strings or ()) for a in sub._actions)}

    invocations = {
        "presence": ["presence", "--declaration", DECL, "--capture", str(out)],
        "regression": ["regression", "--before", str(out), "--after", str(out),
                       "--stall-window-days", "14"],
        "detect": ["detect", "--declaration", CAPTURE_DECL, "--model", MODEL,
                   "--capture", CAPTURE,
                   # The side effect, on purpose: the only verb that writes a file
                   # while also claiming stdout is a document.
                   "--attest-out", str(tmp_path / "att.json")],
    }
    assert takes_json == set(invocations), (
        f"the parser offers --json on {sorted(takes_json)} and this test exercises "
        f"{sorted(invocations)}; a verb claiming to emit a document is not checked")

    for argv in invocations.values():
        main([*argv, "--json"])
        captured = capsys.readouterr().out
        payload = json.loads(captured)          # raises if a prose line rode along
        assert payload["format"].startswith("engagement-deliverable-audit/")
        assert "findings" in payload, argv
        assert payload["exit_code"] == main([*argv, "--json"]), argv
        capsys.readouterr()
        assert not _outcomes(captured), f"{argv} put an OUTCOME line in a document"


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


#: Three ways a MODEL is malformed, which is a different axis from a malformed JSON
#: document: a model goes through a YAML reader and then through the engine's loader,
#: and each stage raises a different family. The test above parametrises over verbs
#: with one broken file; this one parametrises over broken files, because the verbs
#: were never the thing that varied.
MALFORMED_MODELS = {
    # `yaml.YAMLError`, which is NOT a ValueError. This is the one that escaped.
    "unparseable": "domain: [not a mapping\n",
    # Parses, and not to a mapping. `.get` on a list is an AttributeError.
    "not a mapping": "- a\n- b\n",
    # NOT a parse failure and NOT an engine refusal, which is why it is here: the
    # engine loads this as a valid DomainModel with no entity types and no indicators,
    # `is_domain_model` says True, and every silence list is legitimately empty. So a
    # run against it judged nothing and scored CLEAN -- pointing a verb at the wrong
    # YAML file was a clean audit. Measured; it is the reason this file is a dict of
    # named shapes rather than a list of broken strings.
    "declares no axiom at all": "something: else\n",
}


@pytest.mark.parametrize("body", MALFORMED_MODELS.values(), ids=list(MALFORMED_MODELS))
@pytest.mark.parametrize("verb", ["gate", "detect"])
def test_a_malformed_model_is_two_and_never_one(verb, body, tmp_path, capsys) -> None:
    """A model this package could not read is 2, through either verb that reads one.

    Measured before the fix: all six of these combinations left an uncaught exception,
    which exits 1 and prints no OUTCOME line at all. 1 is this package's code for
    *compared and found something*, so a file nobody could parse was reporting as a
    file with a defect in it -- the wrong answer in the wrong direction.

    The OUTCOME line is asserted as well as the code, because a traceback gives a
    caller no line to read and `1` is a number it would otherwise believe.
    """
    # IMPORTED RATHER THAN SKIPPED, and the skip was hiding something worse than a
    # missing run. With no engine installed, `detect` refuses with *needs the engine*
    # and exits 2 -- which is exactly what this test asserts. Measured: every assertion
    # below passes in an engine-free environment, for entirely the wrong reason. So the
    # import makes the test error rather than vanish, and the refusal text is checked
    # below so a 2 from the wrong cause cannot satisfy it either.
    import arbiter_engine  # noqa: F401
    model = tmp_path / "model.yaml"
    model.write_text(body, encoding="utf-8")
    argv = ([verb, "--model", str(model)] if verb == "gate" else
            [verb, "--declaration", DECL, "--model", str(model),
             "--capture", CAPTURE])

    assert main(argv) == 2
    printed = capsys.readouterr().out
    assert _outcomes(printed) == ["OUTCOME exit=2 verdict=could-not-complete"], printed
    assert "needs the engine" not in printed, (
        "this 2 is the refusal for a MISSING ENGINE, not for a malformed model; the "
        "assertion above is satisfied by an environment, not by the behaviour")


def test_a_model_the_engine_silently_dropped_is_never_a_clean_run(
        tmp_path, capsys) -> None:
    """The worst defect found in this package, and no test could have failed on it.

    A model declaring an axiom the engine does not recognise LOADS. The engine writes
    `unknown axiom 'NOPE' in domain file - skipped` to stderr, drops the declaration,
    and judges nothing. No findings, no declines -- and an empty answer is CLEAN by
    design, because the clean case is one this audit must be able to report. So a
    model none of which was applied exited 0.

    `gate` catches this and `detect` did not call it: validating a model and running
    one were owned by different verbs, so neither side had a test that could fail.
    Both verbs are asserted here for that reason.
    """
    import arbiter_engine  # noqa: F401  -- error rather than skip; see the test above
    model = tmp_path / "unknown-axiom.yaml"
    model.write_text(
        "domain:\n"
        "  id: x\n"
        "  name: x\n"
        "  entity_types: [Deliverable]\n"
        "  indicators:\n"
        "    Deliverable:\n"
        "      - name: transitions_per_week\n"
        "        type: NUMERIC\n"
        "        axioms: [NOPE]\n", encoding="utf-8")

    assert main(["gate", "--model", str(model)]) == 2, "the gate never saw this either"
    capsys.readouterr()

    assert main(["detect", "--declaration", DECL, "--model", str(model),
                 "--capture", CAPTURE]) == 2
    printed = capsys.readouterr().out
    assert "model_not_read" in printed, (
        "the run has to say WHICH part of the model the engine did not read; a bare 2 "
        "sends a reader looking for a finding that does not exist")


def test_detect_says_which_declared_deliverables_it_did_not_feed(
        tmp_path, capsys) -> None:
    """The statement, asserted where the silence was: the verb's own output.

    `Fed` carrying the names is necessary and not sufficient -- the defect was that
    `detect` had them and said nothing. So this drives the CLI and reads stdout, in both
    output modes, because a machine reader and a person read different surfaces and the
    document is the one a pipeline parses.

    Measured before the fix: this capture pair exited 0 with the vanished deliverable
    named nowhere at all.
    """
    import arbiter_engine  # noqa: F401  -- error rather than skip
    decl = tmp_path / "d.json"
    decl.write_text(json.dumps({
        "format": "engagement-deliverable-audit/declaration/1",
        "engagement": "VANISH-1",
        "reviewed_by": "FIXTURE -- invented for this test",
        "reviewed_on": "2026-09-11", "change_order": 1, "stall_window_days": 14,
        "sources": [{"path": "tests", "derived_from": "invented for this test"}],
        "points": [{"id": n, "declared_type": "deliverable", "text": n}
                   for n in ("D-1", "D-2", "D-3")],
    }), encoding="utf-8")

    def capture_at(stamp, names):
        path = tmp_path / f"c{stamp[8:10]}.json"
        path.write_text(json.dumps({
            "format": "engagement-deliverable-audit/capture/1",
            "captured_at": stamp, "complete": True,
            "points": [{"name": n, "path": f"t/{n}", "owner": "ana",
                        "state": "In Progress", "days_since_transition": 1}
                       for n in names]}), encoding="utf-8")
        return str(path)

    first = capture_at("2026-09-10T00:00:00Z", ["D-1", "D-2"])
    second = capture_at("2026-09-11T00:00:00Z", ["D-2"])
    argv = ["detect", "--declaration", str(decl), "--model", MODEL,
            "--capture", first, "--capture", second]

    main(argv)
    printed = capsys.readouterr().out
    assert "D-1" in printed, (
        "the deliverable that disappeared from the tracker is named nowhere in the "
        "run that decided not to feed it")
    assert "D-3" in printed, "a deliverable in no capture at all is also unstated"

    main([*argv, "--json"])
    document = json.loads(capsys.readouterr().out)
    assert document["not_fed"] == {"vanished": ["D-1"], "never_seen": ["D-3"]}, (
        "a pipeline parsing the document gets the same two facts, kept apart")


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
