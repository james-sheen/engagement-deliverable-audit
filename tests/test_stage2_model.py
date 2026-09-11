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
#: ONLY THE BOUNDS THAT SEPARATE COMPLIANT FROM NOT. Measured: handing the gate the
#: critical figures reports them as violations, and it is right -- 98% utilisation is
#: already past the 95% the contract allows, so it fires on the WARNING bound. An
#: escalation threshold sits inside the violating region by construction, so *does the
#: published number itself fail* is not a question about it. The gate's subject is the
#: boundary a compliant subject can sit exactly on.
PUBLISHED = (
    ("Consultant", "utilisation_pct", "warning", 95.0),
    ("Consultant", "utilisation_pct", "lower_warning", 70.0),
)


@pytest.fixture(scope="module")
def model() -> dict:
    return yaml.safe_load(MODEL.read_text(encoding="utf-8"))


def test_the_model_declares_no_axiom_it_cannot_judge(model) -> None:
    found = model_gate.problems(model)
    assert found == (), "\n".join(f"{p.where}: {p.what}" for p in found)


def test_every_published_bound_leaves_its_own_number_compliant(model) -> None:
    """The contract's figure is not a violation of the contract.

    *Shall not exceed ninety-five* leaves ninety-five compliant, and this engine
    fires at a declared bound as well as past it -- so a model that declared 95 would
    report an engagement that met its terms exactly. The gate probes the number and
    the next representable value past it, which is the only way to tell a comparator
    that includes its bound from one that does not.
    """
    found = boundary_gate.problems(model, PUBLISHED)
    assert found == (), "\n".join(f"{p.where}: {p.what}" for p in found)


def test_the_days_to_due_bound_fires_at_zero_and_that_is_the_choice(model) -> None:
    """The opposite decision, asserted so it cannot be quietly reversed.

    Due today with nothing delivered is worth saying, so this bound is declared
    knowing its own number fires. Handing the gate 0 as a published figure therefore
    MUST report a problem -- and that report is the evidence the choice was made
    rather than missed. If it ever comes back clean, somebody moved the bound.
    """
    found = boundary_gate.problems(model, (("Deliverable", "days_to_due",
                                            "lower_warning", 0.0),))
    assert len(found) == 1
    assert "days_to_due" in found[0].where


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


def test_the_published_figures_here_are_the_ones_the_model_answers_for(model) -> None:
    """NON-VACUITY. Every published bound above must name an indicator the model
    declares, or the gate is probing a model that says nothing about it and passing
    for that reason."""
    declared = {(entity_type, indicator["name"])
                for entity_type, indicators in model["domain"]["indicators"].items()
                for indicator in indicators}
    for entity_type, indicator, _bound, _number in PUBLISHED:
        assert (entity_type, indicator) in declared, f"{entity_type}.{indicator}"
