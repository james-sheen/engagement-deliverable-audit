"""One thing a guard refuses, said in a way a person can act on."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Problem:
    """`where` names the subject, `what` states the defect, `remedy` says what to do.

    All three are required. A refusal that names no remedy gets read as an
    opinion about taste, and the guards below are not about taste -- each one
    refuses a shape that was measured producing a wrong answer.
    """

    where: str
    what: str
    remedy: str

    def __str__(self) -> str:
        return f"{self.where}: {self.what} -- {self.remedy}"
