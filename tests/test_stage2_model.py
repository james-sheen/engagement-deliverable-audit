"""The four gates, against the real Stage 2 model rather than a fixture.

Phase 1 wrote these guards before anything they could guard. Every one of them was
measured against a hand-made payload shaped to exercise the defect it refuses; none
of them had met a whole model. This is where the model meets them, which is the
acceptance the build plan names first -- and the point at which a guard that only
ever saw its own fixture gets to be wrong.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from engagement_deliverable_audit.guards import (boundary_gate, describe_gate,
                                                 model_gate, source_contract)

MODEL = Path(__file__).resolve().parents[1] / "examples" / "engagement.model.yaml"
DECLARATION = Path(__file__).resolve().parents[1] / "examples" / "engagement.fixture.json"

#: What the DOCUMENT says, separately from what the model declares as a firing point.
#: The two are the same only when the comparator happens to agree with the phrasing,
#: and `boundary_gate` exists because conflating them is the defect. Measured on this
#: engine, a bound fires AT its number, so a compliant published figure has to be
#: declared as the next representable value outside it.
#: The model declares NO bound, and that is measured rather than assumed. The two
#: indicators that would have carried a published threshold -- a consultant's
#: utilisation and a deliverable's days to its due date -- are both excluded for want
#: of a field the capture format does not have, and the manifest says so.
#:
#: So `boundary_gate` is unexercised against this model. Not wrong and not satisfied:
#: unexercised, which is a fact about the export format rather than about the guard.
#: The tests below assert that deliberately, because a gate handed an empty list of
#: published figures returns no problems and would otherwise read as a pass.
MANIFEST = Path(__file__).resolve().parents[1] / "examples" / "engagement.manifest.json"


@pytest.fixture(scope="module")
def model() -> dict:
    return yaml.safe_load(MODEL.read_text(encoding="utf-8"))


def test_the_model_declares_no_axiom_it_cannot_judge(model) -> None:
    found = model_gate.problems(model)
    assert found == (), "\n".join(f"{p.where}: {p.what}" for p in found)


def test_the_model_declares_no_bound_and_the_manifest_says_why() -> None:
    """NOT a gate run. The honest statement of why there is nothing for it to guard.

    `boundary_gate` probes whether a published number is itself reported as a
    violation, and this model declares no threshold at all -- so handing the gate an
    empty set of published figures would return no problems and read exactly like a
    clean probe. What can be asserted is that the absence is deliberate and recorded.
    """
    import json

    model_bounds = [f"{entity_type}.{indicator['name']}"
                    for entity_type, indicators in
                    yaml.safe_load(MODEL.read_text(encoding="utf-8"))
                    ["domain"]["indicators"].items()
                    for indicator in indicators
                    if any(key in indicator for key in
                           ("warning", "critical", "lower_warning", "lower_critical"))]
    assert model_bounds == [], f"a bound is declared after all: {model_bounds}"

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    excluded = {row["indicator"] for row in manifest["excluded"]}
    assert {"utilisation_pct", "days_to_due"} <= excluded
    assert any(row["guard"] == "boundary_gate" for row in manifest["consequences"]), (
        "the manifest does not record that a guard is left unexercised by these "
        "exclusions, which is the thing a reader of the model would want to know")


def test_the_boundary_gate_still_works_where_a_bound_exists() -> None:
    """The gate itself, kept exercised on a model that declares one.

    Without this the gate has no run at all in this suite beyond its own unit tests,
    and an unexercised guard is indistinguishable from a working one. Measured on this
    engine, a declared bound fires AT its number -- so a published figure a subject may
    sit exactly on has to be declared as the next representable value outside it, and
    the gate is what proves the declaration did that.
    """
    import math

    published = 95.0
    firing = math.nextafter(published, math.inf)
    bounded = {"domain": {"indicators": {"Consultant": [
        {"name": "utilisation_pct", "type": "NUMERIC", "axioms": ["BOUNDEDNESS"],
         "warning": firing}]}}}
    assert boundary_gate.problems(
        bounded, (("Consultant", "utilisation_pct", "warning", published),)) == ()

    at_the_number = {"domain": {"indicators": {"Consultant": [
        {"name": "utilisation_pct", "type": "NUMERIC", "axioms": ["BOUNDEDNESS"],
         "warning": published}]}}}
    refused = boundary_gate.problems(
        at_the_number, (("Consultant", "utilisation_pct", "warning", published),))
    assert len(refused) == 1, "declaring the published number itself went unreported"


def test_the_live_engine_has_nothing_unread_in_this_model(model) -> None:
    """Every key this model declares is one the engine reads.

    A misplaced threshold is not a syntax error. `rate_warning` at the indicator's top
    level instead of under `monotonicity:` loads clean, is read by nobody, and leaves
    the axiom judging against a default -- so the model says one thing and the engine
    does another. `unread_fields` is the only surface that reports it, and this probe
    caught exactly that mistake in its own engine probe before the model was written.
    """
    from arbiter_engine.api import EngineSession

    session = EngineSession()
    session.load_model(MODEL.read_text(encoding="utf-8"))
    found = describe_gate.silence(session)
    assert found == (), "\n".join(f"{p.where}: {p.what}" for p in found)


def test_the_declaration_sources_survive_the_report_writer() -> None:
    """The fourth gate is about the declaration rather than the model, and it is run
    here so that *the four gates on the real artifacts* means four and not three."""
    import json

    from engagement_deliverable_audit import declaration as declaration_module

    # Through `check_sources`, which is the door this package uses. Handing the guard
    # the raw JSON dicts is a different question: the guard asks whether an element
    # ANSWERS the members the writer reads off it, and a mapping answers none of them
    # by attribute. That is the call the package never makes.
    engagement = declaration_module.load(
        json.loads(DECLARATION.read_text(encoding="utf-8")))
    found = declaration_module.check_sources(engagement)
    assert found == (), "\n".join(f"{p.where}: {p.what}" for p in found)
    assert engagement.sources, "the fixture declares no sources, so this checked nothing"


def test_the_model_declares_nothing_the_capture_cannot_feed(model) -> None:
    """NON-VACUITY, and the check that the first draft of this model failed.

    It declared four quantities a project-management system might export and this
    package's capture does not. Feeding it would have produced a `missing_property`
    decline for each, which reads as a gap in the DATA. Every indicator must be read
    from a capture field or derived by the feeder, and nothing else.
    """
    from engagement_deliverable_audit import feeder

    readable = {"owner", "state", "days_since_transition"}
    declared = {indicator["name"]
                for indicators in model["domain"]["indicators"].values()
                for indicator in indicators}
    assert declared, "the model declares no indicator, so this compared nothing"
    unfeedable = {name for name in declared
                  if name != feeder.DERIVED and name not in {"owned_by"}
                  and name not in readable}
    assert unfeedable == set(), (
        f"{unfeedable} is declared and nothing feeds it; either the capture format "
        f"grew a field or the indicator belongs in the manifest")
