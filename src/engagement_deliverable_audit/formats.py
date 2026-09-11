"""The named artifacts this package reads and writes.

Every format carries its major version in its own name, and a reader refuses an
unknown major BY NAME rather than guessing. A reader that accepts an unknown
major and then finds a key missing reports a defect in the data; a reader that
refuses reports a defect in the pairing, which is the true one.
"""

from __future__ import annotations

from typing import Any, Mapping

DECLARATION = "engagement-deliverable-audit/declaration/1"
CAPTURE = "engagement-deliverable-audit/capture/1"
PRESENCE = "engagement-deliverable-audit/presence/1"
REGRESSION = "engagement-deliverable-audit/regression/1"
DETECT = "engagement-deliverable-audit/detect/1"

#: Every declared type a point may carry. `ceremony` and `assumption` are
#: deliberately inside the enumeration rather than outside it: a status call is a
#: real thing a statement of work names, and an assumption is a real thing it
#: records, and neither is a deliverable. Counting them out is a claim this
#: package makes out loud, where dropping them would be a silent narrowing of
#: the denominator.
DECLARED_TYPES = ("deliverable", "milestone", "ceremony", "assumption")


class FormatError(ValueError):
    """A document whose format this package will not read, said with both names."""


def require(payload: Mapping[str, Any], expected: str) -> Mapping[str, Any]:
    """Return `payload` if it declares `expected`, else refuse naming both.

    The comparison is on the whole string including the major. A reader that
    compared only the prefix would accept a future major silently, which is the
    one outcome a versioned format exists to prevent.
    """
    if not isinstance(payload, Mapping):
        raise FormatError(
            f"expected a mapping declaring {expected}, got {type(payload).__name__}")
    got = payload.get("format")
    if got is None:
        raise FormatError(
            f"this document declares no format; {expected} was expected. A "
            f"document with no format is not an earlier version of one, it is "
            f"something nobody versioned")
    if got != expected:
        raise FormatError(f"this reader reads {expected} and the document "
                          f"declares {got}")
    return payload
