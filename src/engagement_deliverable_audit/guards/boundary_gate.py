"""Does the number a document published actually pass?

THE DEFECT THIS EXISTS FOR. A published limit is normally phrased as a bound
rather than as a firing point. *Shall not exceed forty pages* leaves forty
compliant. Declaring `critical: 40` against this engine fails a compliant
forty-page volume, because BOUNDEDNESS compares inclusively -- measured across
the boundary on 0.1.13 and on master: 39.999 clean, 40.0 critical.

AND IT IS NOT UNIFORM, which is why this probes rather than assumes. BOUNDEDNESS
fires at the declared number on all four of its bounds. RESPONSIVENESS does not:
`warning: 120` returns nothing at 120.0 and fires just past it. Two axioms, the
same field names, opposite comparators, and the engine's modelling guide contains
neither *inclusive* nor *exclusive*. So the only honest way to know where a bound
fires is to put a value there and look.

WHAT THIS ASSERTS. For each bound, the caller supplies the number the document
published. The published number must be CLEAN and the next representable value
past it must FIRE. Where that does not hold, the model is transcribing the
document wrongly even though the citation is real.

ONE BOUND AT A TIME, AT ITS OWN SEVERITY. The engine reports a value at the
worst severity it reaches, so a page count of 40 against `warning: 38` and a
critical line just past 40 is a WARNING -- correctly: the volume is past its
warning line and inside its limit. Counting any finding, as this did while it
had only ever met one bound per indicator, read that warning as the critical
bound firing at its own published number, and refused a model that transcribed
both lines right. A bound's probe counts findings at its severity or worse.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Optional

from .problem import Problem

#: Which way is worse, per bound. A ceiling is crossed upwards, a floor
#: downwards, and `nextafter` needs to be told which.
DIRECTION: Mapping[str, float] = {
    "warning": math.inf,
    "critical": math.inf,
    "lower_warning": -math.inf,
    "lower_critical": -math.inf,
}

#: The severity a bound's own finding carries, and the order a probe counts up from.
SEVERITY: Mapping[str, str] = {
    "warning": "warning",
    "lower_warning": "warning",
    "critical": "critical",
    "lower_critical": "critical",
}
_RANK: Mapping[str, int] = {"warning": 1, "critical": 2}


def _fires(model: Mapping[str, Any], entity_type: str, indicator: str,
           value: float, severity: Optional[str] = None) -> bool:
    """Whether a finding comes back for `value` -- at `severity` or worse, when named."""
    from arbiter_engine.api import EngineSession, check  # deferred: optional extra

    session = EngineSession()
    session.load_model(model)
    session.add_entity("probe", entity_type, properties={indicator: value})
    findings = check(session).to_dict()["findings"]
    if severity is None:
        return bool(findings)
    floor = _RANK[severity]
    return any(_RANK.get(str(f.get("severity")), 0) >= floor for f in findings)


def problems(model: Mapping[str, Any],
             published: Iterable[tuple[str, str, str, float]]) -> tuple[Problem, ...]:
    """`published` is (entity_type, indicator, bound, the number the document states).

    Deliberately separate from the model. The number in the model is where the
    author put the firing point; the number here is what the document says. They
    are the same only when the comparator happens to agree with the phrasing, and
    conflating them is the defect.
    """
    out: list[Problem] = []
    for entity_type, indicator, bound, number in published:
        if bound not in DIRECTION:
            out.append(Problem(
                where=f"{entity_type}.{indicator}.{bound}",
                what=f"is not one of {', '.join(DIRECTION)}",
                remedy="name the bound the engine reads"))
            continue
        at = _fires(model, entity_type, indicator, float(number), SEVERITY[bound])
        past = _fires(model, entity_type, indicator,
                      math.nextafter(float(number), DIRECTION[bound]), SEVERITY[bound])
        if at:
            out.append(Problem(
                where=f"{entity_type}.{indicator}.{bound}",
                what=f"the published number {number} itself is reported as a "
                     f"violation, so a subject that complies exactly is failed",
                remedy=f"declare the next representable value past {number} as the "
                       f"threshold, and keep {number} in the basis as the published "
                       f"limit"))
        if not past:
            out.append(Problem(
                where=f"{entity_type}.{indicator}.{bound}",
                what=f"nothing fires just past the published number {number}, so "
                     f"crossing the limit is not reported at all",
                remedy="check the indicator declares this bound, carries a role the "
                       "axiom reads, and names the axiom in its axioms list"))
    return tuple(out)
