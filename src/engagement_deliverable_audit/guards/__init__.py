"""Checks that run before there is a vertical to check.

Each guard here exists because something it looks for was measured going wrong
somewhere else in this family, and each one is written so that re-introducing
that defect turns it red. A guard that cannot go red is not a guard, so every
module below has a mutation test beside it that proves the point.

The order is deliberate. These come before the adapters, the vocabulary and the
command line, because the checks are the part of a plan most easily left until
last and the part that decides whether the rest is right.
"""

from .problem import Problem

__all__ = ["Problem"]
