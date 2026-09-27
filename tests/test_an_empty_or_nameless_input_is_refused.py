"""An input that holds nothing, or names nothing, is refused wherever it enters.

Measured across every verb before this: an export of no points ran `detect`,
`regression` and `validate-capture` clean, a declaration naming no deliverable
passed `gate` and ran `presence` and `detect`, a snapshot of no entities was
written out as a capture, an attestation of a run that judged nothing attested
clean, and a point or a declared entry with no name was a KeyError -- which exits
1, and this package's contract reads 1 as findings. Each answer described the
engagement when the fact was about the input.

Every refusal here is 2, never 1: an input that could not be read has produced no
verdict. The producers are the exception, deliberately: `draft` of an empty export
proposes nothing and `declare` of an empty declaration counts zero, and both say so.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engagement_deliverable_audit import capture, declaration, feeder, qa_memory
from engagement_deliverable_audit.cli import main

DECL = "examples/engagement.fixture.json"
SNAP = "examples/tracker.snapshot.json"
MODEL = "examples/engagement.model.yaml"
CAPTURE_FORMAT = "engagement-deliverable-audit/capture/1"
STAMP = "2026-09-20T00:00:00Z"


def _outcomes(printed: str) -> list[str]:
    return [line for line in printed.splitlines() if line.startswith("OUTCOME")]


def _export(points, **extra) -> dict:
    return {"format": CAPTURE_FORMAT, "captured_at": STAMP, "exporter": {"id": "x"},
            "complete": True, "errors": [], "points": points, **extra}


def _snapshot_capture() -> dict:
    return qa_memory.as_capture(json.loads(Path(SNAP).read_text(encoding="utf-8")),
                                captured_at=STAMP)


@pytest.fixture()
def inputs(tmp_path):
    """Every document the table below runs, written where a verb reads it."""
    declared = json.loads(Path(DECL).read_text(encoding="utf-8"))
    tracked = _snapshot_capture()
    nameless = [{k: v for k, v in point.items() if k != "name"}
                for point in tracked["points"]]
    documents = {
        "decl": declared,
        "decl_empty": dict(declared, points=[]),
        "decl_ceremonies": dict(declared, points=[
            p for p in declared["points"] if p["declared_type"] in ("ceremony", "assumption")]),
        "decl_nameless": dict(declared, points=[
            {k: v for k, v in p.items() if k != "id"} for p in declared["points"]]),
        "cap": tracked,
        "cap_empty": _export([]),
        # Holds something, and nothing the declaration names: the engine is fed no
        # entity. The pairing an earlier test in this suite made by accident.
        "cap_elsewhere": _export([{"name": "Z-1", "owner": "anon-9",
                                   "days_since_transition": 1}]),
        "cap_nameless": dict(tracked, points=nameless),
        "cap_incomplete_silent": dict(tracked, complete=False, errors=[]),
        "snap_empty": {"format": "qa-memory/1", "entities": {}, "errors": {}},
        "snap_blank": {"format": "qa-memory/1", "entities": {"": {"value": 1}},
                       "errors": {}},
    }
    paths = {}
    for name, body in documents.items():
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(body), encoding="utf-8")
        paths[name] = str(path)
    paths["out"] = str(tmp_path / "out.json")
    return paths


# --- the readers, called directly -----------------------------------------------

class TestTheCaptureReader:

    def test_an_export_of_nothing_is_refused_by_the_shared_sentence(self):
        with pytest.raises(capture.CaptureError) as refused:
            capture.load(_export([]), stall_window_days=14)
        assert capture.EMPTY_EXPORT in str(refused.value)

    def test_the_producer_may_read_one(self):
        """`draft` proposes a declaration from an export, and of nothing it
        proposes nothing -- which it says -- rather than refusing."""
        assert capture.load(_export([]), stall_window_days=14,
                            allow_empty=True).points == ()

    def test_a_point_with_no_name_is_refused_by_its_position(self):
        points = [{"name": "D-1", "owner": "a", "days_since_transition": 1},
                  {"owner": "b", "days_since_transition": 2},
                  {"name": "  ", "owner": "c", "days_since_transition": 3}]
        with pytest.raises(capture.CaptureError) as refused:
            capture.load(_export(points), stall_window_days=14)
        assert "points[1] and 1 more have no name" in str(refused.value)

    def test_an_entry_that_is_not_a_point_is_refused_by_its_position(self):
        with pytest.raises(capture.CaptureError) as refused:
            capture.load(_export(["D-1"]), stall_window_days=14)
        assert "points[0] is not a point" in str(refused.value)

    def test_an_incomplete_export_has_to_say_what_failed(self):
        """The core names the first failure when it withholds absence; with none
        recorded that was an IndexError, and there is no honest reading of it."""
        tracked = _snapshot_capture()
        with pytest.raises(capture.CaptureError) as refused:
            capture.load(dict(tracked, complete=False, errors=[]), stall_window_days=14)
        assert "records no error" in str(refused.value)
        failed = dict(tracked, complete=False, errors=[["board/2", "stopped at 50 rows"]])
        assert capture.load(failed, stall_window_days=14).complete is False

    def test_an_error_that_is_not_a_pair_is_refused(self):
        tracked = _snapshot_capture()
        with pytest.raises(capture.CaptureError) as refused:
            capture.load(dict(tracked, complete=False, errors=["timeout"]),
                         stall_window_days=14)
        assert "errors[0] is not a [where, what] pair" in str(refused.value)

    def test_a_readable_export_raises_no_problem(self):
        assert capture.problems(_snapshot_capture()) == []


class TestTheDeclarationReader:

    def test_a_point_with_no_id_is_refused_by_its_position(self):
        declared = json.loads(Path(DECL).read_text(encoding="utf-8"))
        declared["points"][2].pop("id")
        with pytest.raises(declaration.DeclarationError) as refused:
            declaration.load(declared)
        assert "points[2] has no id" in str(refused.value)

    def test_an_entry_that_is_not_a_point_is_refused_by_its_position(self):
        declared = json.loads(Path(DECL).read_text(encoding="utf-8"))
        declared["points"].insert(0, "D-9")
        with pytest.raises(declaration.DeclarationError) as refused:
            declaration.load(declared)
        assert "points[0] is str" in str(refused.value)

    def test_nothing_to_judge_is_said_and_a_descoped_deliverable_still_counts(self):
        declared = json.loads(Path(DECL).read_text(encoding="utf-8"))
        assert declaration.nothing_to_judge(declaration.load(declared)) is None
        empty = declaration.load(dict(declared, points=[]))
        assert "names no deliverable and no milestone" in \
            declaration.nothing_to_judge(empty)
        ceremonies = declaration.load(dict(declared, points=[
            p for p in declared["points"]
            if p["declared_type"] in ("ceremony", "assumption")]))
        assert "counts out" in declaration.nothing_to_judge(ceremonies)
        descoped = declaration.load(dict(declared, points=[
            dict(p, descoped=True) for p in declared["points"]
            if p["declared_type"] == "deliverable"]))
        assert declaration.nothing_to_judge(descoped) is None


class TestTheSnapshotReader:

    def test_an_empty_substrate_is_refused(self):
        with pytest.raises(qa_memory.SnapshotError) as refused:
            qa_memory.as_capture({"format": "qa-memory/1", "entities": {}})
        assert "An empty substrate" in str(refused.value)

    def test_an_entity_with_a_blank_name_is_refused(self):
        with pytest.raises(qa_memory.SnapshotError) as refused:
            qa_memory.as_capture({"format": "qa-memory/1", "entities": {" ": {"value": 1}}})
        assert "blank name" in str(refused.value)


class TestTheFeeder:

    def test_a_run_that_would_feed_nothing_is_refused(self):
        """The API answer, which is the CLI's: the engine given no entity answered
        an unavailable envelope, and findings-and-declines scoring called it clean."""
        pytest.importorskip("arbiter_engine")
        declared = declaration.load(json.loads(Path(DECL).read_text(encoding="utf-8")))
        elsewhere = capture.load(_export([{"name": "Z-1", "owner": "a",
                                           "days_since_transition": 1}]),
                                 stall_window_days=14)
        with pytest.raises(feeder.FeedError) as refused:
            feeder.run(declared, [elsewhere], Path(MODEL).read_text(encoding="utf-8"))
        assert "the engine would judge nothing" in str(refused.value)

    def test_the_same_run_over_the_tracker_feeds(self):
        pytest.importorskip("arbiter_engine")
        declared = declaration.load(json.loads(Path(DECL).read_text(encoding="utf-8")))
        tracked = capture.load(_snapshot_capture(), stall_window_days=14)
        ran = feeder.run(declared, [tracked], Path(MODEL).read_text(encoding="utf-8"))
        assert ran.fed.deliverables


# --- the verbs -------------------------------------------------------------------

#: Every path measured answering clean, or exiting 1 on a traceback, before this.
REFUSED = {
    "capture qa-memory, no entities": lambda p: [
        "capture", "--source", f"qa-memory:{p['snap_empty']}", "--out", p["out"]],
    "capture qa-memory, blank name": lambda p: [
        "capture", "--source", f"qa-memory:{p['snap_blank']}", "--out", p["out"]],
    "capture export, no points": lambda p: [
        "capture", "--source", f"export:{p['cap_empty']}", "--out", p["out"]],
    "capture export, nameless": lambda p: [
        "capture", "--source", f"export:{p['cap_nameless']}", "--out", p["out"]],
    "validate-capture, no points": lambda p: ["validate-capture", p["cap_empty"]],
    "validate-capture, nameless": lambda p: ["validate-capture", p["cap_nameless"]],
    "validate-capture, incomplete and silent": lambda p: [
        "validate-capture", p["cap_incomplete_silent"]],
    "presence, no points": lambda p: [
        "presence", "--declaration", p["decl"], "--capture", p["cap_empty"]],
    "presence, nameless capture": lambda p: [
        "presence", "--declaration", p["decl"], "--capture", p["cap_nameless"]],
    "presence, incomplete and silent": lambda p: [
        "presence", "--declaration", p["decl"], "--capture", p["cap_incomplete_silent"]],
    "presence, empty declaration": lambda p: [
        "presence", "--declaration", p["decl_empty"], "--capture", p["cap"]],
    "presence, ceremonies only": lambda p: [
        "presence", "--declaration", p["decl_ceremonies"], "--capture", p["cap"]],
    "presence, nameless declaration": lambda p: [
        "presence", "--declaration", p["decl_nameless"], "--capture", p["cap"]],
    "regression, nothing to nothing": lambda p: [
        "regression", "--before", p["cap_empty"], "--after", p["cap_empty"],
        "--stall-window-days", "14"],
    "regression, something to nothing": lambda p: [
        "regression", "--before", p["cap"], "--after", p["cap_empty"],
        "--stall-window-days", "14"],
    "regression, nameless": lambda p: [
        "regression", "--before", p["cap_nameless"], "--after", p["cap_nameless"],
        "--stall-window-days", "14"],
    "detect, no points": lambda p: [
        "detect", "--declaration", p["decl"], "--model", MODEL,
        "--capture", p["cap_empty"]],
    "detect, empty declaration": lambda p: [
        "detect", "--declaration", p["decl_empty"], "--model", MODEL,
        "--capture", p["cap"]],
    "detect, nothing declared in the capture": lambda p: [
        "detect", "--declaration", p["decl"], "--model", MODEL,
        "--capture", p["cap_elsewhere"]],
    "detect, nameless capture": lambda p: [
        "detect", "--declaration", p["decl"], "--model", MODEL,
        "--capture", p["cap_nameless"]],
    "gate, empty declaration": lambda p: ["gate", p["decl_empty"]],
    "gate, nameless declaration": lambda p: ["gate", p["decl_nameless"]],
    "declare, nameless declaration": lambda p: [
        "declare", "--declaration", p["decl_nameless"]],
    "generate, nameless declaration": lambda p: [
        "generate", "--declaration", p["decl_nameless"]],
    "draft, nameless capture": lambda p: [
        "draft", "--capture", p["cap_nameless"], "--out", p["out"]],
}


@pytest.mark.parametrize("argv", REFUSED.values(), ids=list(REFUSED))
def test_the_verb_refuses_and_never_reports_findings(argv, inputs, capsys):
    if "detect" in argv(inputs)[0]:
        pytest.importorskip("arbiter_engine")
    assert main(argv(inputs)) == 2
    printed = capsys.readouterr().out
    assert _outcomes(printed) == ["OUTCOME exit=2 verdict=could-not-complete"], printed
    assert "needs the engine" not in printed


#: The same verbs on inputs that hold something, each answering as before.
UNCHANGED = {
    "presence": (lambda p: ["presence", "--declaration", p["decl"],
                            "--capture", p["cap"]], 1),
    "regression": (lambda p: ["regression", "--before", p["cap"], "--after", p["cap"],
                              "--stall-window-days", "14"], 0),
    "validate-capture": (lambda p: ["validate-capture", p["cap"]], 0),
    "gate": (lambda p: ["gate", p["decl"]], 0),
    "declare, empty declaration (a count of zero, said)": (
        lambda p: ["declare", "--declaration", p["decl_empty"]], 0),
    "draft, no points (proposes nothing, and says so)": (
        lambda p: ["draft", "--capture", p["cap_empty"], "--out", p["out"]], 0),
}


@pytest.mark.parametrize("argv,code", UNCHANGED.values(), ids=list(UNCHANGED))
def test_an_input_that_holds_something_answers_as_before(argv, code, inputs):
    assert main(argv(inputs)) == code


def test_detect_over_the_tracker_still_judges(inputs):
    pytest.importorskip("arbiter_engine")
    assert main(["detect", "--declaration", inputs["decl"], "--model", MODEL,
                 "--capture", inputs["cap"]]) == 1


def test_regression_says_which_side_could_not_be_read(inputs, capsys):
    main(["regression", "--before", inputs["cap"], "--after", inputs["cap_empty"],
          "--stall-window-days", "14"])
    assert f"--after {inputs['cap_empty']}:" in capsys.readouterr().out


def _attestation_of_nothing() -> dict:
    """What `detect` wrote before it refused a run that fed nothing: built the way
    it built one, over a session holding no entity, so it validates."""
    from arbiter_engine.api import EngineSession, attest, check, model_describe
    from presence_audit.attestation import build_attestation, validate_attestation

    from engagement_deliverable_audit.attestation_manifest import EngagementManifest

    session = EngineSession()
    session.load_model(Path(MODEL).read_text(encoding="utf-8"))
    envelope = check(session).to_dict()
    described = model_describe(session).to_dict()
    envelope["model"] = described.get("model") or {}
    envelope["unread_properties"] = described.get("unread_properties") or []
    artifact = build_attestation(session, envelope, described, EngagementManifest(),
                                 target="an empty run", attest_fn=attest, spelled=True)
    artifact["exit_code"] = 0
    assert validate_attestation(artifact) == [], "the artifact must be valid, so the " \
        "refusal below is the empty denominator and not the format"
    assert artifact["checked"] == {"invariants": 0, "entities": 0}
    return artifact


def test_an_attestation_of_nothing_is_not_clean(tmp_path, capsys):
    pytest.importorskip("arbiter_engine")
    path = tmp_path / "attestation.json"
    path.write_text(json.dumps(_attestation_of_nothing()), encoding="utf-8")
    assert main(["attest", str(path)]) == 2
    printed = capsys.readouterr().out
    assert "attests nothing" in printed
    assert _outcomes(printed) == ["OUTCOME exit=2 verdict=could-not-complete"]
