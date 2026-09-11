"""The manifest the core's attestation builder reads, derived from the builder.

`build_attestation` takes a `manifest` and reads members off it. Which members is
documented nowhere: the `Vocabulary` protocol a vertical implements declares fifteen
and neither of these is among them, so the conformance kit -- which checks a vertical
against that protocol -- cannot see the requirement at all. A vertical discovers it by
calling the builder and getting an `AttributeError` out of the middle of an artifact
it was halfway through writing.

So the members are DERIVED from the builder's own source rather than transcribed, the
same way this package derives what the report writer reads off a declaration's sources.
A transcribed list here would be a second copy of somebody else's private contract,
and it would go stale silently on the day they read one more thing.

    python3 -c "from engagement_deliverable_audit.attestation_manifest import \\
        required_members; print(sorted(required_members()))"

Filed upstream. Until it is answered, this module is the shim, and its test fails if
the builder starts reading something this does not answer.
"""

from __future__ import annotations

import ast
import inspect
from typing import Any

#: The builder's own parameter name, which is what its accesses are written against.
_ELEMENT = "manifest"
_BUILDER = "build_attestation"

#: Every problem type this domain can produce, and the sentence it means. The
#: attestation's `statement` is what a reader sees six months later, so it is this
#: domain's own words -- not the engine's problem type, which names a mechanism.
STATEMENTS = {
    "missing_relationship": "the tracker holds this deliverable and nobody owns it, "
                            "so nobody is going to move it",
    "dangling_relationship": "the tracker names an owner this engagement never "
                             "declared, so the ownership record points at nothing",
    "frozen_series": "this deliverable's transition count has not moved inside the "
                     "declared window, so the tracker is no longer measuring it",
}


def _read_by(tree: ast.AST) -> tuple[frozenset[str], frozenset[str]]:
    """(required, optional), by how the builder reaches for each one.

    TWO KINDS OF ACCESS AND THE DIFFERENCE IS THE WHOLE POINT. `manifest.x` raises if
    absent, so x is required. `getattr(manifest, "y", default)` does not, so y is
    optional and a manifest that answers nothing for it still works.

    A derivation that looked only for attribute access would report one member where
    the builder reaches for two, and the missing one is the one it is SAFE to miss --
    which is the worst way to be right, because the set looks complete. This found
    exactly that: `translate_finding` by attribute, `sensors` by `getattr` with a
    default, and only the first would have appeared.
    """
    required = {node.attr for node in ast.walk(tree)
                if isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == _ELEMENT}
    optional = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "getattr" and len(node.args) >= 2
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id == _ELEMENT
                and isinstance(node.args[1], ast.Constant)):
            (optional if len(node.args) >= 3 else required).add(node.args[1].value)
    return frozenset(required), frozenset(optional - required)


def _tree(builder: Any) -> ast.AST:
    """The builder's source as a tree, or a LookupError that says what went wrong.

    `inspect.getsource` hands back whatever text it finds, and a nested definition
    comes back indented -- which `ast.parse` rejects with an IndentationError from two
    frames down. A guard that cannot read its subject has to say so in its own words,
    or the caller gets a syntax error about code they did not write.
    """
    try:
        return ast.parse(inspect.getsource(builder))
    except (OSError, TypeError, SyntaxError) as error:
        raise LookupError(
            f"cannot read the source of {getattr(builder, '__name__', builder)!r} to "
            f"derive what it reads off its {_ELEMENT}: {error}") from error


def optional_members(builder: Any = None) -> frozenset[str]:
    """Members the builder reaches for with a default, so absence is tolerated."""
    if builder is None:
        from presence_audit import attestation as builder  # deferred: optional extra
    return _read_by(_tree(builder))[1]


def required_members(builder: Any = None) -> frozenset[str]:
    """Every member the attestation builder reads off its `manifest` and needs.

    Raises rather than returning an empty set. An empty requirement would make the
    adapter below look complete against a builder that reads ten things, which is the
    failure this module exists to prevent.
    """
    if builder is None:
        from presence_audit import attestation as builder  # deferred: optional extra
    found, _ = _read_by(_tree(builder))
    if not found:
        raise LookupError(
            f"{builder.__name__} reads nothing off {_ELEMENT!r}. Either the parameter "
            f"was renamed or the builder stopped taking one -- either way this module "
            f"is now answering a contract nobody asked for, and pretending otherwise "
            f"would ship an adapter for a function that has moved on")
    if _BUILDER not in (inspect.getsource(builder) if found else ""):
        raise LookupError(f"{builder.__name__} no longer defines {_BUILDER!r}")
    return frozenset(found)


class EngagementManifest:
    """What this domain answers to the attestation builder.

    `sensors` is empty and that is the right answer rather than a stub. The core uses
    it to map a sanitised entity id back to the name on a board, because a sibling's
    ids are unreadable six months later. Here the entity id IS the declared key -- the
    same string the declaration, the capture, every finding and every report use -- so
    there is nothing to map, and supplying a mapping would create a second vocabulary
    for one set of names.
    """

    sensors: tuple = ()

    def translate_finding(self, finding: Any) -> str:
        """This domain's sentence for a finding, for a reader who has only the artifact.

        Keyed on the class before the colon, because the engine's problem type carries
        the indicator after it and a statement is about the kind of fault. An unknown
        class returns a sentence saying it is unknown rather than the empty string: an
        artifact whose statement is blank reads as a finding nobody could describe.
        """
        problem_type = str((finding or {}).get("problem_type") or "")
        known = STATEMENTS.get(problem_type.split(":", 1)[0])
        if known:
            return known
        return (f"{problem_type or 'an unnamed problem'}: this domain has no sentence "
                f"for this finding, which is a gap in its vocabulary rather than a "
                f"fact about the deliverable")

    def answers(self, builder: Any = None) -> tuple[str, ...]:
        """Members the builder will reach for and this class does not answer."""
        return tuple(sorted(m for m in required_members(builder)
                            if not hasattr(self, m)))
