#!/usr/bin/env python3
"""Build a declaration and a capture for Astropy's Cycle 5 funded work.

This exists because the first real-data run could not meet half of its own
acceptance. A tracker export contains no contract, so the declaration there was
derived from the same records as the capture -- one source and two fields, which
is weaker than two instruments. This pairs two artifacts written by different
people for different purposes:

* **The declaration** is the set of Cycle 5 funding requests in
  `astropy/astropy-project`, under `finance/proposal-calls/cycle5/`. The cycle's
  own template says of that section: *this section ... will be used as the Scope
  of Work in the resulting contracts funding approved FRs*. A proposer writes it.
* **The capture** is the set of Cycle 5 tracking issues in the same repository's
  issue tracker, selected by the tracker's own `cycle 5` label rather than by a
  title match of mine. The call's post-request process says a tracking issue is
  created by the finance committee contact and carries the budget, the period of
  performance and the assigned COTR. A different person writes it, after award.

The join between them is mechanical and not a judgement: every tracking issue body
links its Scope of Work by path, so the key on both sides is the funding request's
file name. Nothing here matches titles, infers ownership from a name, or decides
which proposal an issue is about.

    python3 battery/fetch_astropy_cycle5.py --out-dir evidence
    GITHUB_TOKEN=... python3 battery/fetch_astropy_cycle5.py   # raises the rate limit

Exit 0 wrote both documents, 2 could not -- including when either side comes back
empty, because a diff over nothing reports no findings and looks like agreement.

WHAT THIS IS NOT: two organisations. Both artifacts are hosted in one repository
on one platform. They are two authors and two purposes, which is what makes the
pairing better than the previous run, and it is not the same as a client-signed
contract read beside a vendor's tracker. `evidence/astropy-cycle5.md` says so
beside the numbers.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OWNER_REPO = "astropy/astropy-project"
CYCLE_DIR = "finance/proposal-calls/cycle5"
CYCLE_LABEL = "cycle 5\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}"

# Not funding requests: the blank the proposers copy, and the call document, which
# is named after its own directory. Both sit in the same folder as the requests and
# neither is one. Including the call produced the only `declared_absent` finding in
# the first run of this fetch -- a deliverable the tracker had never heard of,
# because it was never a deliverable.
NOT_A_REQUEST = {"template.md", "README.md"}


def _is_request(name: str, directory: str) -> bool:
    """A request is an `.md` file in the cycle folder that is not one of its fixtures."""
    return (name.endswith(".md") and name not in NOT_A_REQUEST
            and name != directory.rsplit("/", 1)[1] + ".md")

# The Scope of Work link every tracking issue body carries, in either the bare or
# the percent-encoded spelling GitHub produces for a file name holding a `+`.
SCOPE = re.compile(re.escape(CYCLE_DIR) + r"/([A-Za-z0-9%_.+&,-]+?\.md)")
COTR = re.compile(r"COTR\s*:?\s*(.+)", re.IGNORECASE)
APPROVED = re.compile(r"approved in\s+(?:#(\d+)|\S*?/pull/(\d+))", re.IGNORECASE)

EXIT_CLEAN, EXIT_ERROR = 0, 2


class CannotRun(Exception):
    """The fetch could not produce both documents. Never written as a partial pair."""


def _get(url: str, accept: str = "application/vnd.github+json"):
    request = urllib.request.Request(url, headers={"Accept": accept,
                                                   "User-Agent": "engagement-deliverable-audit"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        raise CannotRun(f"{url} returned {error.code}; "
                        "set GITHUB_TOKEN if this is a rate limit") from error
    except (urllib.error.URLError, OSError) as error:
        raise CannotRun(f"cannot reach {url}: {error}") from error
    return json.loads(body) if accept.endswith("json") else body.decode("utf-8", "replace")


def head_sha() -> str:
    return _get(f"https://api.github.com/repos/{OWNER_REPO}/commits/HEAD")["sha"]


# --- the declaration side: the funding requests themselves -----------------

def requests_at(sha: str) -> list[str]:
    """The Cycle 5 funding request file names, read out of the tree at `sha`."""
    tree = _get(f"https://api.github.com/repos/{OWNER_REPO}/git/trees/{sha}?recursive=1")
    if tree.get("truncated"):
        raise CannotRun("the tree listing was truncated, so the declaration would be "
                        "missing requests without saying which")
    names = sorted(
        entry["path"].rsplit("/", 1)[1] for entry in tree.get("tree", ())
        if entry["type"] == "blob" and entry["path"].startswith(CYCLE_DIR + "/")
        and _is_request(entry["path"].rsplit("/", 1)[1], CYCLE_DIR))
    if not names:
        raise CannotRun(f"no funding requests found under {CYCLE_DIR} at {sha[:8]}")
    return names


def title_of(sha: str, name: str) -> str:
    """The request's own title, read from the document rather than its file name.

    The cycle template offers a bare `### Title` heading to fill in under, and the
    requests split about evenly between filling it in and replacing it with the
    title itself. So the title is the document's FIRST heading, except where that
    heading is the template's label, in which case it is the first line beneath it.

    An earlier version of this looked only for the label and otherwise fell through
    to the first non-heading line -- which skipped the real title, because the real
    title IS a heading, and returned the opening bullet of the project team instead.
    Half of the declaration's texts were a different field, and the declaration said
    `title` over all of them. Returns the empty string when the document names no
    title at all, rather than substituting something that is not one.
    """
    return title_in(_get(f"https://raw.githubusercontent.com/{OWNER_REPO}/{sha}/"
                         f"{CYCLE_DIR}/{urllib.parse.quote(name)}", accept="text/plain"))


def title_in(text: str) -> str:
    """The title rule itself, separated from the fetch so it can be tested.

    A rule that only runs against the network is a rule whose wrong answers are
    found by reading its output, which is how the first version survived: it looked
    plausible over eighteen documents and was wrong about nine of them.
    """
    lines = [line.strip() for line in text.splitlines()]
    for number, line in enumerate(lines):
        if not line.startswith("#"):
            continue
        label = line.lstrip("# ").strip()
        if label.lower() != "title":
            return label
        for following in lines[number + 1:]:
            if not following:
                continue
            # A heading immediately after the label means the label was left blank.
            return "" if following.startswith("#") else following
        return ""
    return ""


def declaration_for(sha: str, names: list[str], titles: dict[str, str],
                    captured: dt.datetime, window: float | None) -> dict:
    """Assemble the declaration. `window` of None omits the field entirely.

    Omitting it is not a degraded mode, it is the reading these documents alone
    support: the call sets a one-year period of performance and requires work
    updates in the tracking issue, and names no interval for them. `declare`
    refuses a declaration with no window, so that refusal is the first thing this
    scope of work produces, and any number here is the auditor's.
    """
    declaration = {
        "format": "engagement-deliverable-audit/declaration/1",
        "engagement": "astropy-cycle-5",
        # NOT A SIGNATURE, AND THIS FIELD USED TO READ LIKE ONE.
        #
        # It said "the Astropy SPOC and Finance Committee" with the call's nominal
        # selection date, because that committee is who a real Cycle 5 contract would
        # be signed by. But the committee selected funding requests; it did not read --
        # and could not have read -- a JSON document this script generates. The date was
        # the selection date wearing a review date's field name, the explanation lived
        # here rather than in the artifact, and `Engagement.reviewed` is
        # `bool(who) and bool(when)`, so nothing downstream could tell the difference. A
        # reader of `evidence/` saw a signed statement of work naming real people.
        #
        # The two other declarations in this repository already disclosed themselves in
        # this field. This one now does the same, and `DISCLOSURE_MARKERS` makes the
        # convention something callers can report rather than a habit.
        "reviewed_by": (
            f"DERIVED -- not signed by anybody. Built by "
            f"battery/fetch_astropy_cycle5.py from {OWNER_REPO}@{sha[:8]}. The "
            f"Astropy SPOC and Finance Committee selected these funding requests on "
            f"a nominal date of 2025-12-19 and did not review this declaration"),
        # The date the DERIVATION ran, which is the only review-shaped act that
        # happened. The call's 2025-12-19 is named above as what it is.
        "reviewed_on": captured.strftime("%Y-%m-%d"),
        "change_order": 0,
        "sources": [{
            "path": f"https://github.com/{OWNER_REPO}/tree/{sha}/{CYCLE_DIR}",
            "derived_from": "Astropy Cycle 5 funding requests. The cycle template "
                            "says this section will be used as the Scope of Work "
                            "in the resulting contracts",
            "captured_at": captured.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }],
        "window_basis": (
            "THE ENGAGEMENT DECLARES NO WINDOW. The call sets a one-year period of "
            "performance (Jan 1-Dec 31, 2026) and requires work updates in the "
            "tracking issue, and names no interval for them. So a window here is the "
            "AUDITOR'S specification; with --omit-window there is no field at all and "
            "`declare` refuses, which is what the documents alone support."),
        "points": [{
            "id": name,
            "declared_type": "deliverable",
            # Empty when the document titles nothing. `declare` reports that;
            # putting the file name here would answer the question with the
            # one field that is never missing.
            "text": titles[name],
            "basis": {
                "document": f"{OWNER_REPO} at {sha[:8]}",
                "location": f"{CYCLE_DIR}/{name}",
                "quote": name,
            },
        } for name in names],
    }
    if window is not None:
        declaration["stall_window_days"] = window
    return declaration


# --- the capture side: the tracking issues ---------------------------------

def tracking_issues() -> list[dict]:
    """Every issue the tracker itself labels as Cycle 5, all pages."""
    found, page = [], 1
    while True:
        batch = _get(
            f"https://api.github.com/repos/{OWNER_REPO}/issues"
            f"?labels={urllib.parse.quote(CYCLE_LABEL)}&state=all&per_page=100&page={page}")
        if not isinstance(batch, list):
            raise CannotRun(f"the issue listing came back as {type(batch).__name__}")
        found.extend(item for item in batch if "pull_request" not in item)
        if len(batch) < 100:
            break
        page += 1
        if page > 20:
            raise CannotRun("more than 20 pages of issues; refusing to guess the tail")
    if not found:
        raise CannotRun(f"the tracker holds no issue labelled {CYCLE_LABEL!r}, so the "
                        "capture would be empty and every declared deliverable would "
                        "read as absent for a reason that is about this fetch")
    return found


def scope_of(issue: dict) -> str | None:
    """The funding request this issue tracks, as the issue itself names it."""
    match = SCOPE.search(issue.get("body") or "")
    return urllib.parse.unquote(match.group(1)) if match else None


def cotr_of(issue: dict) -> str | None:
    """The COTR, or None when the issue does not yet name one.

    The COTR and not the assignee. The call makes the COTR responsible for
    reviewing deliverables and for ensuring work updates happen; the assignee on
    these issues is the finance committee contact, who handles invoices. An owner
    in this package's sense is whoever the work is owed by.
    """
    for line in (issue.get("body") or "").splitlines():
        match = COTR.match(line.strip())
        if not match:
            continue
        value = match.group(1).strip().strip("*_` ")
        if not value or value.upper().startswith("TBD") or value.upper() == "NONE":
            return None
        handles = re.findall(r"@([A-Za-z0-9-]+)", value)
        return ", ".join(handles) if handles else value
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", default="evidence", type=Path)
    parser.add_argument("--sha", default=None,
                        help="pin the astropy-project commit; default resolves HEAD "
                             "and records what it resolved to")
    parser.add_argument("--stall-window-days", type=float, default=90.0,
                        help="the auditor's specification, not the engagement's -- see "
                             "the basis recorded in the declaration")
    parser.add_argument("--omit-window", action="store_true",
                        help="write the declaration with NO window, which is what these "
                             "documents actually determine. The call sets a one-year "
                             "period of performance and requires work updates in the "
                             "tracking issue, and names no interval for them, so every "
                             "three-valued verdict rests on a number the engagement "
                             "never declared. `declare` refuses such a declaration, "
                             "which is the honest first reading of this scope of work")
    args = parser.parse_args(argv)

    try:
        sha = args.sha or head_sha()
        names = requests_at(sha)
        titles = {name: title_of(sha, name) for name in names}
        issues = tracking_issues()
        captured = dt.datetime.now(dt.timezone.utc)

        declaration = declaration_for(sha, names, titles, captured,
                                      None if args.omit_window else args.stall_window_days)

        points = []
        for issue in issues:
            scope = scope_of(issue)
            age = (captured - dt.datetime.strptime(
                issue["updated_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=dt.timezone.utc)).days
            points.append({
                "name": scope or f"issue-{issue['number']}-names-no-scope-of-work",
                "path": issue["html_url"],
                "owner": cotr_of(issue),
                "state": issue["state"],
                "days_since_transition": age,
            })

        capture = {
            "format": "engagement-deliverable-audit/capture/1",
            "captured_at": captured.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "exporter": {
                "source": f"{OWNER_REPO} issues labelled {CYCLE_LABEL}",
                "join": "the Scope of Work path in each issue body",
            },
            # Every page was read and the loop refuses rather than truncating, so
            # this is a measurement of the fetch and not a default.
            "complete": True,
            "points": points,
            "errors": [],
        }

        args.out_dir.mkdir(parents=True, exist_ok=True)
        for stem, document in (("astropy-cycle5-declaration", declaration),
                               ("astropy-cycle5-capture", capture)):
            path = args.out_dir / f"{stem}.json"
            path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
            print(f"wrote {path}")

        unresolved = [p["name"] for p in points if p["name"].startswith("issue-")]
        print(f"\nastropy-project at {sha[:8]}")
        print(f"  declared  : {len(names)} funding request(s) under {CYCLE_DIR}")
        print(f"  tracked   : {len(points)} issue(s) labelled Cycle 5")
        print(f"  joined    : {len(points) - len(unresolved)} by Scope of Work path")
        if unresolved:
            print(f"  unjoinable: {len(unresolved)} issue(s) name no Scope of Work -- "
                  "reported rather than dropped")
        print(f"  owners    : {sum(1 for p in points if p['owner'])} of {len(points)} "
              "issue(s) name a COTR")
        return EXIT_CLEAN
    except CannotRun as error:
        print(f"\nfetch-astropy-cycle5: could not run -- {error}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
