"""Refuse a model whose declared axioms cannot answer, before anything runs it.

THE DEFECT THIS EXISTS FOR, and it is the worst of the set. An indicator that
declares CONSISTENCY without a populated `agrees_with` is counted in the
engine's `checked.invariants`, returns no finding, returns no decline, and does
not appear in `unreachable_declarations`. Its output is byte-identical to an
indicator that compared against its peer and agreed. Measured on engine 0.1.13
and on its master: two readings 0.40 apart against a tolerance of 0.02 produce
`redundant_disagreement` with the peer named, and total silence without it.

Silent THREE WAYS, which is why the predicate below is about a populated list
rather than a present block: no `consistency` block at all, a block whose
`agrees_with` is absent, and a block whose `agrees_with` is the empty list all
behave the same. A check asking *is the block there* would have passed two of
the three.

WHAT THIS DELIBERATELY DOES NOT REFUSE. MONOTONICITY without a `monotonicity`
block, because the reversal arm answers without one -- measured, a descending
series still returns `monotonicity_reversal`. Refusing it would reject a
declaration that works. CONNECTIVITY without `target_type` and `relation_type`
is reported and not refused for the same reason: it fires rather than going
silent, though it cannot name what is missing, so it earns a note.

Every entry carries the engine behaviour that was measured for it. An entry
whose behaviour is *the engine already says so* is kept anyway: the engine says
it during a run, and this says it before one.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .problem import Problem

#: axiom -> (the key it reads, the sub-keys that must be present and non-empty,
#:           what the engine does when they are absent)
AXIOM_CONFIGURATION: Mapping[str, tuple[str, tuple[str, ...], str]] = {
    "CONSISTENCY": ("consistency", ("agrees_with",),
                    "says nothing at all, and reads exactly like agreement"),
    "CONSERVATION": ("conservation", ("input_property", "output_properties"),
                     "declines missing_config and lists the pair as unreachable"),
    "HOMEOSTASIS": ("homeostasis", ("setpoint",),
                    "declines insufficient_samples, which sends a reader to wait "
                    "for samples that will never change the answer"),
}

#: Declaring any one of these is enough for BOUNDEDNESS to have something to do.
BOUNDS = ("warning", "critical", "lower_warning", "lower_critical")

#: Read but not required; a missing one is reported rather than refused.
ADVISORY = {"CONNECTIVITY": ("target_type", "relation_type")}


def _populated(block: Any, key: str) -> bool:
    if not isinstance(block, Mapping):
        return False
    value = block.get(key)
    if value is None:
        return False
    if isinstance(value, (str, bytes)):
        return bool(value)
    if isinstance(value, Sequence):
        return len(value) > 0
    return True


def problems(model: Mapping[str, Any]) -> tuple[Problem, ...]:
    """Every declared axiom in `model` that has nothing to judge against.

    Takes the whole mapping as loaded from YAML, `domain` key included, so the
    caller does not have to know where indicators live.
    """
    domain = model.get("domain", model)
    out: list[Problem] = []
    for entity_type, indicators in (domain.get("indicators") or {}).items():
        for indicator in indicators or ():
            name = indicator.get("name", "(unnamed)")
            where = f"{entity_type}.{name}"
            declared = tuple(indicator.get("axioms") or ())
            for axiom in declared:
                if axiom in AXIOM_CONFIGURATION:
                    key, required, behaviour = AXIOM_CONFIGURATION[axiom]
                    absent = [k for k in required
                              if not _populated(indicator.get(key), k)]
                    if absent:
                        out.append(Problem(
                            where=where,
                            what=f"declares {axiom} with no {', '.join(absent)} "
                                 f"under {key}:, so the engine {behaviour}",
                            remedy=f"declare {key}: with {', '.join(required)}, "
                                   f"or remove {axiom} from this indicator's axioms"))
                if axiom == "BOUNDEDNESS" and not any(b in indicator for b in BOUNDS):
                    out.append(Problem(
                        where=where,
                        what="declares BOUNDEDNESS with no bound to judge against, "
                             "so it can only ever decline while still counting "
                             "towards the denominator",
                        remedy=f"declare one of {', '.join(BOUNDS)} with a basis, "
                               f"or remove BOUNDEDNESS from this indicator's axioms"))
                for advisory_axiom, fields in ADVISORY.items():
                    if axiom == advisory_axiom:
                        absent = [f for f in fields if not indicator.get(f)]
                        if absent:
                            out.append(Problem(
                                where=where,
                                what=f"declares {axiom} without {', '.join(absent)}, "
                                     f"so a finding here cannot name what is missing",
                                remedy="declare them, or accept a finding that says "
                                       "only that something is absent"))
    return tuple(out)


def basis_problems(declarations: Sequence[Mapping[str, Any]]) -> tuple[Problem, ...]:
    """A declared bound whose basis does not contain the number it claims.

    A floor is a specification and not a guess, so a bound carries the document
    that published it. The weak form of that rule is a citation naming a
    document; the strong form, which is this, is that the document's quoted text
    contains the NUMBER. A citation can name a real contract and still be the
    author's own invention -- a statement of work that sets a due date does not
    thereby publish a warning line three days before it.
    """
    out: list[Problem] = []
    for entry in declarations:
        name = entry.get("name") or entry.get("id") or "(unnamed)"
        basis = str((entry.get("basis") or {}).get("quote") or "")
        for bound in BOUNDS:
            if bound not in entry:
                continue
            number = entry[bound]
            if str(number) not in basis:
                out.append(Problem(
                    where=f"{name}.{bound}",
                    what=f"declares {number} and its basis quote does not contain "
                         f"that number",
                    remedy="quote the text that publishes the number, or move the "
                           "metric to HOMEOSTASIS against a measured baseline, "
                           "which is what a number nobody published calls for"))
    return tuple(out)
