"""`gate --published` runs the two guards a user's transcription had no way into.

`boundary_gate` refuses a bound where the number a document published is itself reported as a
violation, and `model_gate.basis_problems` a bound whose quote does not contain its number. Both
were listed in the README's guard table and both ran only in this package's tests: `boundary_gate`
takes the published numbers deliberately apart from the model and `gate` had no flag for them, and
a `basis:` quote inside an indicator is a key the engine does not read, so `gate` refused that model
as unread and never judged the quote. A model declaring `critical: 40` for a volume that *shall not
exceed 40 pages* -- the shape `boundary_gate` exists to refuse -- passed `gate --model` with exit 0.
`gate` now takes the figures the documents published, in a file of their own, and runs both guards
over them beside the model.
"""

from __future__ import annotations

import math

import pytest

from engagement_deliverable_audit.cli import main

LIMIT = "Each technical volume shall not exceed 40 pages."


def _model(tmp_path, bounds: str, name="volume.model.yaml"):
    path = tmp_path / name
    path.write_text(
        "domain:\n  id: proposal\n  name: A proposal's volumes\n  description: a page limit\n"
        "  entity_types: [Volume]\n  relationship_types: []\n  indicators:\n    Volume:\n"
        f"      - {{name: page_count, type: NUMERIC, axioms: [BOUNDEDNESS], {bounds}}}\n",
        encoding="utf-8")
    return str(path)


def _figures(tmp_path, *figures: str, name="published.yaml"):
    path = tmp_path / name
    path.write_text("published:\n" + "".join(figures), encoding="utf-8")
    return str(path)


def _figure(number="40", quote=LIMIT, bound="critical", extra=""):
    return (f"  - entity_type: Volume\n    indicator: page_count\n    bound: {bound}\n"
            f"    number: {number}\n    quote: \"{quote}\"\n{extra}")


REPAIRED = f"critical: {math.nextafter(40.0, math.inf)!r}"


def _gate(capsys, *argv):
    code = main(["gate", *argv])
    return code, capsys.readouterr().out


class TestTheTwoGuardsRun:

    def test_the_model_as_filed_passes_without_the_figures_and_is_refused_with_them(self, tmp_path, capsys):
        model = _model(tmp_path, "critical: 40")
        assert _gate(capsys, "--model", model)[0] == 0
        code, out = _gate(capsys, "--model", model, "--published", _figures(tmp_path, _figure()))
        assert code == 2
        assert "Volume.page_count.critical: the published number 40 itself is reported as a violation" in out

    def test_the_repaired_model_passes(self, tmp_path, capsys):
        figures = _figures(tmp_path, _figure(extra="    source: RFP Section L.3\n"))
        code, out = _gate(capsys, "--model", _model(tmp_path, REPAIRED), "--published", figures)
        assert code == 0, out
        assert "1 published figure(s), each quote containing its number" in out

    def test_a_quote_without_its_number_is_refused(self, tmp_path, capsys):
        figures = _figures(tmp_path, _figure(quote="Each technical volume shall not exceed forty pages."))
        code, out = _gate(capsys, "--model", _model(tmp_path, REPAIRED), "--published", figures)
        assert code == 2
        assert "Volume.page_count.critical: declares 40 and its basis quote does not contain that number" in out

    def test_a_figure_for_what_the_model_does_not_bound_is_refused(self, tmp_path, capsys):
        figures = _figures(tmp_path, _figure(bound="warning", number="38",
                                             quote="A volume over 38 pages needs a waiver."))
        code, out = _gate(capsys, "--model", _model(tmp_path, REPAIRED), "--published", figures)
        assert code == 2
        assert "nothing fires just past the published number 38" in out


class TestWhatTheFileMustBe:

    def test_figures_need_a_model(self, tmp_path, capsys):
        code, out = _gate(capsys, "--published", _figures(tmp_path, _figure()))
        assert code == 2 and "pass --model" in out

    @pytest.mark.parametrize("text", ["published: []\n", "figures: []\n", "- 40\n", "published: [\n"],
                             ids=["no figures", "no published key", "not a mapping", "not YAML"])
    def test_a_file_with_no_figures_is_refused(self, tmp_path, capsys, text):
        path = tmp_path / "published.yaml"
        path.write_text(text, encoding="utf-8")
        code, out = _gate(capsys, "--model", _model(tmp_path, REPAIRED), "--published", str(path))
        assert code == 2 and "published.yaml" in out

    @pytest.mark.parametrize("figure, why", [
        ("  - entity_type: Volume\n    indicator: page_count\n    bound: critical\n    number: 40\n",
         "figure 1 has no quote"),
        (_figure(extra="    page: 3\n"), "figure 1 carries page, which nothing reads"),
        (_figure(number="\"40\""), "figure 1 states '40', which is not a number"),
        (_figure(number="true"), "figure 1 states True, which is not a number"),
        ("  - 40\n", "figure 1 is int, not a mapping"),
    ], ids=["no quote", "an unread key", "a number as text", "a boolean", "not a mapping"])
    def test_a_figure_that_cannot_be_checked_is_refused_by_name(self, tmp_path, capsys, figure, why):
        code, out = _gate(capsys, "--model", _model(tmp_path, REPAIRED),
                          "--published", _figures(tmp_path, figure))
        assert code == 2 and why in out, out


def test_a_bound_no_figure_speaks_for_is_said_and_not_refused(tmp_path, capsys):
    # The model may be right; this run compared that bound with no document, and says so.
    model = _model(tmp_path, f"warning: 38, {REPAIRED}")
    code, out = _gate(capsys, "--model", model, "--published", _figures(tmp_path, _figure()))
    assert code == 0, out
    assert "not checked" in out and "Volume.page_count.warning: no published figure was given for it" in out
    assert "Volume.page_count.critical: no published figure" not in out
