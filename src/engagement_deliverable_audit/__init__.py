"""An engagement's deliverables, against the statement of work that declared them.

Three answers, not two. A deliverable is MOVING when it is tracked with an owner
and a transition inside the declared window; it is TRACKED AND STALLED when it
exists in the tracker and neither of those holds; and it is ABSENT when the
tracker has never heard of it. A board that colours everything "open" collapses
the middle answer into the first, which is the answer somebody would act on.

The declaration comes from a statement of work, read by a person and signed. The
capture comes from a tracker export. Those are two instruments with unrelated
failure modes, which is the only reason a difference between them means anything.

Nothing here is wired yet beyond the published-repository tooling. The guards
come before the vertical, deliberately: the checks that decide whether this
package is right are the part most easily left until last.
"""

__version__ = "0.1.3"

__all__ = ["__version__"]
