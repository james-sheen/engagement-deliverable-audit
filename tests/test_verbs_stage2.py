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
    assert "translate_finding" in required
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
