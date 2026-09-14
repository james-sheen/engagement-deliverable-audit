"""The four verbs around `detect`, and the contract none of them could see.

`draft` proposes and refuses to call it reviewed; `gate` names what is not ready;
`generate` writes a model and a manifest as a pair and the model is empty by
construction; `attest` reads an artifact back through the door a recipient uses.

The interesting assertions here are the negative ones. A draft that loaded cleanly
would be a statement nobody made; a gate that exited clean over no arguments would be
a pipeline step that never blocks; a generated model with an indicator in it would mean
a declaration carries a threshold, which it does not.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engagement_deliverable_audit import declaration as declaration_module
from engagement_deliverable_audit.cli import main

ROOT = Path(__file__).resolve().parents[1]
DECL = "examples/engagement.fixture.json"
MODEL = "examples/engagement.model.yaml"
CAPTURE = "evidence/astropy-cycle5-capture.json"


# --- draft -----------------------------------------------------------------

def test_a_draft_is_unreviewed_and_carries_no_window(tmp_path, capsys) -> None:
    out = tmp_path / "draft.json"
    assert main(["draft", "--capture", CAPTURE, "--out", str(out)]) == 0
    capsys.readouterr()
    drafted = json.loads(out.read_text(encoding="utf-8"))

    assert drafted["reviewed_by"] is None and drafted["reviewed_on"] is None
    assert "stall_window_days" not in drafted
    assert drafted["points"], "a draft with no points proposes nothing"


def test_a_draft_says_on_its_face_that_it_is_not_a_statement_of_work(tmp_path, capsys) -> None:
    """The weakness this package records about its own first real-data run. A
    declaration derived from a tracker is the same records under another name, and the
    artifact has to say so where a reader will see it rather than in a docstring."""
    out = tmp_path / "draft.json"
    main(["draft", "--capture", CAPTURE, "--out", str(out)])
    capsys.readouterr()
    drafted = json.loads(out.read_text(encoding="utf-8"))
    assert "NOT A STATEMENT OF WORK" in drafted["sources"][0]["derived_from"]
    assert "NO WINDOW" in drafted["window_basis"]


def test_declare_refuses_a_draft(tmp_path, capsys) -> None:
    """Two refusals, and either alone is enough. A draft that any verb would act on is
    a statement somebody was given credit for writing."""
    out = tmp_path / "draft.json"
    main(["draft", "--capture", CAPTURE, "--out", str(out)])
    capsys.readouterr()
    assert main(["declare", "--declaration", str(out)]) == 2

    drafted = json.loads(out.read_text(encoding="utf-8"))
    drafted["stall_window_days"] = 14
    (tmp_path / "windowed.json").write_text(json.dumps(drafted), encoding="utf-8")
    capsys.readouterr()
    assert main(["declare", "--declaration", str(tmp_path / "windowed.json")]) == 2, (
        "with a window supplied it is still unreviewed, and that alone must refuse it")


# --- gate ------------------------------------------------------------------

def test_gate_names_what_is_not_ready_and_passes_what_is(tmp_path, capsys) -> None:
    draft = tmp_path / "draft.json"
    main(["draft", "--capture", CAPTURE, "--out", str(draft)])
    capsys.readouterr()

    assert main(["gate", DECL]) == 0
    assert "ok" in capsys.readouterr().out

    assert main(["gate", DECL, str(draft)]) == 2
    printed = capsys.readouterr().out
    assert "REFUSED" in printed and str(draft) in printed
    assert DECL in printed, "the one that passed was not named, so a reader cannot tell it ran"


def test_gate_over_nothing_is_refused(capsys) -> None:
    """NON-VACUITY, and the only answer this verb must never give. A pipeline step that
    exits clean when handed nothing is a step that never blocks anything."""
    assert main(["gate"]) == 2
    assert "nothing was given" in capsys.readouterr().out


def test_gate_puts_the_model_through_the_gates_that_read_one(capsys) -> None:
    assert main(["gate", DECL, "--model", MODEL]) == 0
    assert MODEL in capsys.readouterr().out


def test_gate_refuses_a_model_that_declares_an_axiom_with_nothing_to_judge(
        tmp_path, capsys) -> None:
    """The other direction, so the clean run above is not satisfied by a gate that
    never looks at the model."""
    broken = tmp_path / "broken.yaml"
    broken.write_text(
        "domain:\n  id: b\n  name: b\n  entity_types: [Deliverable]\n"
        "  relationship_types: []\n  indicators:\n    Deliverable:\n"
        "      - name: x\n        type: NUMERIC\n        axioms: [BOUNDEDNESS]\n",
        encoding="utf-8")
    assert main(["gate", DECL, "--model", str(broken)]) == 2
    assert "REFUSED" in capsys.readouterr().out


# --- generate --------------------------------------------------------------

def test_the_generated_model_is_empty_and_every_point_is_accounted_for(
        tmp_path, capsys) -> None:
    """The prediction this verb exists to test rather than assert.

    Generation derives indicators from thresholds a declaration carries. A deliverable
    carries a due date and an owner, and the declaration format has no threshold key --
    so the generated model declares nothing and every point is excluded with a reason.
    An empty file would be indistinguishable from generation having been skipped, which
    is why the manifest is the other half of the pair.
    """
    model_out, manifest_out = tmp_path / "m.json", tmp_path / "n.json"
    assert main(["generate", "--declaration", DECL,
                 "--model-out", str(model_out), "--manifest-out", str(manifest_out)]) == 0
    capsys.readouterr()

    model = json.loads(model_out.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_out.read_text(encoding="utf-8"))
    assert model["domain"]["indicators"] == {"Deliverable": []}
    assert manifest["generated_indicators"] == 0

    declared = declaration_module.load(
        json.loads((ROOT / DECL).read_text(encoding="utf-8"))).points
    assert len(manifest["excluded"]) == len(declared), (
        "a point is neither modelled nor excluded, so the manifest is not a complete "
        "account of the declaration")
    for row in manifest["excluded"]:
        assert row["reason"] and len(row["detail"]) > 20


def test_the_model_and_the_manifest_are_written_as_a_pair(tmp_path, capsys) -> None:
    """A model without its manifest is a claim about coverage with the exclusions
    removed, which is the one artifact this verb must not produce."""
    assert main(["generate", "--declaration", DECL,
                 "--model-out", str(tmp_path / "m.json")]) == 2
    assert not (tmp_path / "m.json").exists()
    capsys.readouterr()
    assert main(["generate", "--declaration", DECL,
                 "--manifest-out", str(tmp_path / "n.json")]) == 2
    assert not (tmp_path / "n.json").exists()


# --- attest, and the contract nobody declared ------------------------------

def test_an_attestation_round_trips_through_the_front_door(tmp_path, capsys) -> None:
    artifact = tmp_path / "att.json"
    code = main(["detect", "--declaration", "evidence/astropy-cycle5-declaration.json",
                 "--model", MODEL, "--capture", CAPTURE,
                 "--attest-out", str(artifact), "--attest-target-label", "a label"])
    assert code == 1
    capsys.readouterr()

    assert main(["attest", str(artifact)]) == 1
    printed = capsys.readouterr().out
    assert "a label" in printed, "the label was not used, so the artifact names a path"

    stored = json.loads(artifact.read_text(encoding="utf-8"))
    assert len(stored["evidence"]) == len(stored["findings"])
    assert stored["findings"], "an artifact with no findings proves nothing here"
    assert all(f.get("statement") for f in stored["findings"]), (
        "a finding with no statement reads as one nobody could describe")


def _unowned_capture(tmp_path) -> tuple[str, str]:
    """A declaration and a capture where NOBODY owns anything.

    The shape every other test in this file avoids, and the one the attest defect hid
    in: with no owner anywhere there is no Consultant in the graph, so CONNECTIVITY
    declines `missing_entity_type` instead of naming orphans. Zero findings, and a
    decline that floors the run at 2.
    """
    decl = tmp_path / "nobody.declaration.json"
    decl.write_text(json.dumps({
        "format": "engagement-deliverable-audit/declaration/1",
        "engagement": "NOBODY-OWNS-ANYTHING",
        "reviewed_by": "FIXTURE -- invented for this test; no engagement or person",
        "reviewed_on": "2026-09-11",
        "change_order": 1, "stall_window_days": 14,
        "sources": [{"path": "tests", "derived_from": "invented for this test"}],
        "points": [{"id": f"D-{n}", "declared_type": "deliverable", "text": str(n)}
                   for n in (1, 2, 3)],
    }), encoding="utf-8")
    cap = tmp_path / "nobody.capture.json"
    cap.write_text(json.dumps({
        "format": "engagement-deliverable-audit/capture/1",
        "captured_at": "2026-09-01T00:00:00Z", "complete": True,
        "points": [{"name": f"D-{n}", "path": f"t/{n}", "owner": None,
                    "state": "In Progress", "days_since_transition": n}
                   for n in (1, 2, 3)],
    }), encoding="utf-8")
    return str(decl), str(cap)


def test_an_attestation_of_a_could_not_complete_run_is_never_clean(
        tmp_path, capsys) -> None:
    """The one outcome this package says it must not produce, reached through `attest`.

    `attest` scored `FINDINGS if findings else CLEAN`, which reads only one of the two
    lists the artifact carries. Measured before the fix: `detect` exited 2 on this
    capture and `attest` exited 0 over the artifact it had just written.

    Asserted on BOTH ends of the round trip on purpose. Pinning only `attest` would
    pass if `detect` stopped producing a 2 here, and pinning only `detect` is the test
    that already existed.

    **The exit code alone does not pin the fix, and this test said it did.** Reverting
    the scoring left this green: `detect` records its own code, and composing it with
    `max` recovered the 2 without any scoring happening. So the decline that carries
    the floor has to be named in the output too -- that line exists only if the
    artifact was scored. Found by reverting the fix and watching this stay green.
    """
    decl, cap = _unowned_capture(tmp_path)
    artifact = tmp_path / "att.json"
    assert main(["detect", "--declaration", decl, "--model", MODEL,
                 "--capture", cap, "--attest-out", str(artifact)]) == 2, (
        "this capture is supposed to reach a could-not-complete; if it stops doing so "
        "the rest of this test proves nothing")
    capsys.readouterr()

    stored = json.loads(artifact.read_text(encoding="utf-8"))
    assert not stored["findings"], (
        "the defect needed ZERO findings to show; with a finding present the old "
        "scoring returned 1 and nothing looked wrong")
    assert any(d.get("reason") == "missing_entity_type" for d in stored["not_checked"])

    assert main(["attest", str(artifact)]) == 2
    printed = capsys.readouterr().out
    assert "could-not-complete" in printed
    assert "missing_entity_type floors this run at 2" in printed, (
        "the verdict must come from scoring the artifact, not only from the code the "
        "writing run happened to record in it")


def test_attest_scores_an_artifact_that_records_no_verdict_of_its_own(
        tmp_path, capsys) -> None:
    """Artifacts written by 0.1.0 carry no `exit_code`, and must still score correctly.

    The fix records this run's code in the artifact, which would be a fix only for
    files written after it. A recipient holding an older artifact is the case that
    matters, so the recorded key is REMOVED here and the verdict has to come from the
    floors alone.
    """
    decl, cap = _unowned_capture(tmp_path)
    artifact = tmp_path / "att.json"
    assert main(["detect", "--declaration", decl, "--model", MODEL,
                 "--capture", cap, "--attest-out", str(artifact)]) == 2
    capsys.readouterr()

    stored = json.loads(artifact.read_text(encoding="utf-8"))
    assert stored.pop("exit_code") == 2, "detect did not record its own code"
    stored.pop("verdict")
    artifact.write_text(json.dumps(stored), encoding="utf-8")

    assert main(["attest", str(artifact)]) == 2, (
        "scored from the artifact's own lists, an unowned run is still a 2")
    capsys.readouterr()


def _verdict(code: int):
    """A verdict in whatever shape the installed core accepts.

    The declared block from `presence-audit` 0.1.8, and this package's own
    top-level string below it. Derived from the core rather than branched on a
    version, because a version is a proxy for the capability and goes stale the
    moment a backport is in play.
    """
    from presence_audit import attestation

    block = getattr(attestation, "verdict_block", None)
    if callable(block):
        return block(code, scored_by="a fixture")
    from engagement_deliverable_audit.cli import MEANING
    return MEANING[code]


def test_a_recorded_verdict_can_raise_the_score_and_never_lower_it(
        tmp_path, capsys) -> None:
    """The composition rule, exercised in both directions.

    The artifact cannot carry `floor_unreachable_at_this_rate`, so a run that exited 1
    on `warmup_unreachable` re-scores as 0 from the lists alone. The recorded code is
    what recovers it -- and the same mechanism must not let a recorded 0 talk a
    scored 2 down.
    """
    decl, cap = _unowned_capture(tmp_path)
    artifact = tmp_path / "att.json"
    assert main(["detect", "--declaration", decl, "--model", MODEL,
                 "--capture", cap, "--attest-out", str(artifact)]) == 2
    capsys.readouterr()
    stored = json.loads(artifact.read_text(encoding="utf-8"))

    # THE VERDICT IS WRITTEN THE WAY THE INSTALLED CORE SPELLS IT. This fixture
    # hand-built `verdict="clean"`, which was this package's own invented key --
    # and from `presence-audit` 0.1.8 the core declares the slot as an object and
    # its validator refuses a string. Left as a string the artifact stops being
    # valid, `attest` reports the format problem instead of the disagreement, and
    # this test measures the refusal rather than the compose rule it is named
    # for.
    lowered = dict(stored, exit_code=0, verdict=_verdict(0))
    (tmp_path / "lowered.json").write_text(json.dumps(lowered), encoding="utf-8")
    assert main(["attest", str(tmp_path / "lowered.json")]) == 2, (
        "a recorded clean must not lower a run the floors score at 2")
    printed = capsys.readouterr().out
    assert "reporting the worse of the two" in printed, (
        "the disagreement was resolved silently")

    # The other direction: nothing in the lists floors this, and the recorded code is
    # the only thing that knows better.
    raised = {**stored, "findings": [], "evidence": [], "not_checked": [
        {"sensor": "D-1", "axiom": "STABILITY", "reason": "insufficient_samples",
         "detail": "too few observations"}], "exit_code": 1, "verdict": _verdict(1)}
    (tmp_path / "raised.json").write_text(json.dumps(raised), encoding="utf-8")
    assert main(["attest", str(tmp_path / "raised.json")]) == 1, (
        "a recorded 1 must survive lists that score 0")
    capsys.readouterr()


def test_an_attestation_that_does_not_validate_is_never_clean(tmp_path, capsys) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps({"format": "presence-audit/attestation/1",
                                  "findings": [{"sensor": "D-1"}]}), encoding="utf-8")
    assert main(["attest", str(broken)]) == 2
    assert "INVALID" in capsys.readouterr().out


def test_the_manifest_contract_is_derived_and_answered() -> None:
    """The members the attestation builder reads are declared NOWHERE.

    The `Vocabulary` protocol a vertical implements declares fifteen members and
    neither of these is among them, so the conformance kit -- which checks a vertical
    against that protocol -- cannot see the requirement. Passing `None` raises from
    inside a half-written artifact.

    Both kinds of access are derived, and the difference matters: an attribute access
    is required, a `getattr` with a default is not. A derivation that looked only for
    attribute access would report one member where the builder reaches for two, and
    the missing one is the one it is safe to miss -- which is the worst way to be
    right, because the set looks complete.
    """
    from engagement_deliverable_audit import attestation_manifest as shim

    required, optional = shim.required_members(), shim.optional_members()
    # WHICH SIDE `translate_finding` FALLS ON IS THE CORE'S DECISION, not this
    # package's, and it moved: reported from here as a member the builder read
    # bare while no protocol declared it, and `presence-audit` 0.1.8 made it a
    # `getattr` with a default so an artifact degrades to the engine's own
    # problem type instead of raising from inside a half-written file.
    #
    # So this asserts what stays true across the pinned range -- the builder
    # REACHES for it, this shim answers it, and the two kinds of access are told
    # apart -- and not which side of a line the core has since moved.
    assert "translate_finding" in (required | optional), (
        "the builder no longer reaches for it at all, so this shim is answering "
        "a contract nobody asked for")
    assert "sensors" in optional
    assert not required & optional
    assert shim.EngagementManifest().answers() == ()


def test_the_derivation_refuses_a_builder_it_cannot_read() -> None:
    """An empty requirement would make the adapter look complete against a builder
    that reads ten things."""
    from engagement_deliverable_audit import attestation_manifest as shim

    class Nothing:
        __name__ = "nothing"

    with pytest.raises((LookupError, TypeError)):
        shim.required_members(Nothing)


def test_an_unknown_finding_gets_a_sentence_saying_so() -> None:
    """Not the empty string. An artifact whose statement is blank reads as a finding
    nobody could describe, rather than as a gap in this domain's vocabulary."""
    from engagement_deliverable_audit.attestation_manifest import EngagementManifest

    said = EngagementManifest().translate_finding({"problem_type": "from_the_future:x"})
    assert "no sentence" in said and "from_the_future" in said
