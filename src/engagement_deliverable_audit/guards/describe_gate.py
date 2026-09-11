"""Ask the engine what it cannot reach, at the nesting where the answer lives.

THE DEFECT THIS EXISTS FOR. The published acceptance for a Stage 2 model was a
one-liner reading three keys off `model_describe(...).to_dict()` and requiring
all three to be empty. Two of those keys are not at the top level -- they sit
under `model` -- so run verbatim it raises `KeyError` rather than reporting
anything, and the one key it placed correctly is the only one that really is top
level. An acceptance that cannot execute has never been met by anything.

WHY A MISSING PATH IS A PROBLEM AND NOT AN EMPTY ANSWER. The obvious repair is
`.get(key, [])`, and that is worse than the crash: a key the engine stopped
emitting, or one this guard spells wrongly, would read as *nothing unreachable*
forever. So a path that is not there is reported as a defect in this guard,
naming the keys the engine did offer.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .problem import Problem

#: Where each answer lives, as a path through the dictionary. Two levels deep
#: for two of them, and that asymmetry is the whole reason this file exists.
PATHS: Mapping[str, tuple[str, ...]] = {
    "unreachable_declarations": ("model", "unreachable_declarations"),
    "unread_fields": ("model", "unread_fields"),
    "unread_properties": ("unread_properties",),
}


def _walk(payload: Mapping[str, Any], path: Sequence[str]):
    """Return (found, value_or_offered_keys)."""
    here: Any = payload
    for step in path:
        if not isinstance(here, Mapping) or step not in here:
            offered = sorted(here) if isinstance(here, Mapping) else type(here).__name__
            return False, offered
        here = here[step]
    return True, here


def problems(described: Mapping[str, Any]) -> tuple[Problem, ...]:
    """Every non-empty silence list, plus any path that was not there at all.

    Takes the dictionary rather than a session so the caller can hand over a
    stored one, and so this is testable without an engine installed.

    **A model that declares NOTHING is reported here too, and that is not the same
    question as the silence lists.** Measured: `something: else` loads as a valid
    `DomainModel` with no entity types and no indicators, `is_domain_model` returns
    True, and every list below is legitimately empty -- there is nothing unread
    because nothing was declared. So the three silence checks all pass and a run
    against that model judges nothing and scores CLEAN. Pointing a verb at the wrong
    YAML file was a clean audit.
    """
    out: list[Problem] = []
    model = described.get("model")
    # PRESENT AND EMPTY, not merely absent. A live engine always emits
    # `declared_axioms`, so gating on presence costs nothing against a real session --
    # and it keeps this rule out of the way of a hand-written payload that carries only
    # the keys under test. Treating an absent key as *declares nothing* made the two
    # path-nesting tests fail for a reason that had nothing to do with their subject.
    if (isinstance(model, Mapping) and "declared_axioms" in model
            and not (model.get("declared_axioms") or ())):
        out.append(Problem(
            where="model.declared_axioms",
            what="is empty, so this model declares no axiom and judging anything "
                 "against it can only come back clean",
            remedy="declare an indicator with an axiom, or do not pass this file as "
                   "a model; `generate` writes an empty model on purpose and it is a "
                   "template to fill in rather than one to judge with"))
    for label, path in PATHS.items():
        found, value = _walk(described, path)
        if not found:
            out.append(Problem(
                where=".".join(path),
                what=f"is not in what the engine returned; it offered {value}",
                remedy="re-derive the path from the engine rather than defaulting "
                       "to empty, because a missing key reads as nothing to report"))
            continue
        for entry in value or ():
            out.append(Problem(
                where=".".join(path),
                what=f"{entry}",
                remedy="declare the axiom the field belongs to, remove the field, "
                       "or record in the manifest that the gap is deliberate"))
    return tuple(out)


def silence(session: Any) -> tuple[Problem, ...]:
    """The same check, asked of a live session."""
    from arbiter_engine.api import model_describe  # deferred: optional extra

    return problems(model_describe(session).to_dict())
