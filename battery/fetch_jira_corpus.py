#!/usr/bin/env python3
"""Re-derive the real-data evidence in `evidence/` from the published dataset.

THE CORPUS IS FETCHED, NOT COMMITTED IN FULL. The source is 5.8 GB and the part
used is a prefix of it, so what ships is the derived declaration and capture plus
this script. Evidence nobody can re-derive is an assertion with a file beside it.

HOW IT AVOIDS DOWNLOADING 5.8 GB. The archive is a zip64 whose issue data sits in
a single member, itself gzipped. Zenodo honours HTTP Range, so this reads the
zip64 central directory from the tail, finds that member's offset, range-fetches a
bounded PREFIX of its deflate stream, inflates it, gunzips the result, and walks
the mongodump framing -- length-prefixed BSON documents with 0xFFFFFFFF as the
namespace terminator. Every layer is streamable, so a prefix of the file yields a
prefix of the documents.

Needs `pymongo` for its `bson`, which is a tool dependency and deliberately not a
dependency of this package.

    python3 battery/fetch_jira_corpus.py [--prefix-bytes N] [--project ZOOKEEPER]

Source: The Public Jira Dataset, Montgomery, Lueders and Maalej, Zenodo record
15719919, CC BY 4.0. Attribution is required by that licence and is carried in
`evidence/README.md` as well as here.
"""

from __future__ import annotations

import argparse
import collections
import datetime
import json
import hashlib
import struct
import urllib.request
import zlib
from pathlib import Path

RECORD = 15719919
URL = (f"https://zenodo.org/api/records/{RECORD}/files/"
       "2025-06-23%20ThePublicJiraDataset.zip/content")
MEMBER = "mongodump-JiraReposAnon.archive"
ARCHIVE_MAGIC = 0x8199E26D


def _range(start: int, end: int) -> bytes:
    request = urllib.request.Request(
        URL, headers={"User-Agent": "curl", "Range": f"bytes={start}-{end}"})
    with urllib.request.urlopen(request, timeout=300) as handle:
        if handle.status != 206:
            raise RuntimeError(
                f"the host answered {handle.status} rather than 206; without "
                f"Range this script would have to fetch 5.8 GB")
        return handle.read()


def _total() -> int:
    request = urllib.request.Request(URL, headers={"User-Agent": "curl"},
                                     method="HEAD")
    with urllib.request.urlopen(request, timeout=120) as handle:
        return int(handle.headers["Content-Length"])


def _member_data_offset(total: int) -> int:
    """Walk the zip64 tail to the member's compressed data."""
    tail = _range(total - 65536, total - 1)
    locator = tail.rfind(b"PK\x06\x07")
    if locator < 0:
        raise RuntimeError("no zip64 end-of-central-directory locator in the tail")
    eocd64_at = struct.unpack_from("<Q", tail, locator + 8)[0]
    header = _range(eocd64_at, eocd64_at + 55)
    cd_size, cd_at = struct.unpack_from("<QQ", header, 40)
    central = _range(cd_at, cd_at + cd_size - 1)
    position = 0
    while position < len(central) and central[position:position + 4] == b"PK\x01\x02":
        name_len, extra_len, comment_len = struct.unpack_from("<HHH", central, position + 28)
        name = central[position + 46:position + 46 + name_len].decode("utf-8", "replace")
        local = struct.unpack_from("<I", central, position + 42)[0]
        extra = central[position + 46 + name_len:position + 46 + name_len + extra_len]
        if local == 0xFFFFFFFF and extra:
            cursor = 0
            while cursor + 4 <= len(extra):
                tag, length = struct.unpack_from("<HH", extra, cursor)
                if tag == 1:
                    local = struct.unpack_from("<" + "Q" * (length // 8), extra, cursor + 4)[-1]
                    break
                cursor += 4 + length
        if name.endswith(MEMBER):
            head = _range(local, local + 29)
            if head[:4] != b"PK\x03\x04":
                raise RuntimeError("the local header is not where the directory said")
            n_len, e_len = struct.unpack_from("<HH", head, 26)
            return local + 30 + n_len + e_len
        position += 46 + name_len + extra_len + comment_len
    raise RuntimeError(f"{MEMBER} is not in this archive")


#: The SHA-256 of the deflate prefix `issues` actually fetched, set when it runs.
#: Module-level rather than returned because `issues` is a generator and the digest is
#: known before the first document is yielded -- and the capture needs it after the walk.
PREFIX_SHA256: str | None = None


def issues(prefix_bytes: int):
    """Real issue documents from a bounded prefix of the dump."""
    global PREFIX_SHA256
    start = _member_data_offset(_total())
    deflated = _range(start, start + prefix_bytes - 1)
    PREFIX_SHA256 = "sha256:" + hashlib.sha256(deflated).hexdigest()
    gzipped = zlib.decompressobj(-15).decompress(deflated)
    archive = zlib.decompressobj(16 + 15).decompress(gzipped)
    if struct.unpack_from("<I", archive, 0)[0] != ARCHIVE_MAGIC:
        raise RuntimeError("this is not a mongodump archive; the layering changed")
    position, namespace = 4, None
    while position + 4 <= len(archive):
        length = struct.unpack_from("<i", archive, position)[0]
        if length == -1:
            position += 4
            continue
        if length < 5 or position + length > len(archive):
            return
        import bson  # tool dependency, not this package's
        try:
            document = bson.decode(archive[position:position + length])
        except Exception:
            return
        if "db" in document and "collection" in document:
            namespace = document["collection"]
        elif "key" in document:
            yield namespace, document
        position += length


def _last_status_transition(document):
    """`updated` moves on any edit, including a comment. Only a change to
    `status` is a transition, so only that is read."""
    newest = None
    for history in (document.get("changelog") or {}).get("histories") or ():
        if any((item or {}).get("field") == "status"
               for item in (history.get("items") or ())):
            when = history.get("created")
            if isinstance(when, str):
                try:
                    when = datetime.datetime.strptime(when[:19], "%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    continue
            if isinstance(when, datetime.datetime):
                when = when.replace(tzinfo=None)
                if newest is None or when > newest:
                    newest = when
    return newest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix-bytes", type=int, default=70_000_000)
    parser.add_argument("--project", default="ZOOKEEPER")
    parser.add_argument("--window-days", type=float, default=14.0)
    parser.add_argument("--out", default="evidence")
    args = parser.parse_args()

    rows = []
    for _namespace, document in issues(args.prefix_bytes):
        key = document.get("key") or ""
        if not key.startswith(args.project + "-"):
            continue
        fields = document.get("fields") or {}
        if fields.get("resolutiondate"):
            continue
        when = _last_status_transition(document)
        if when is None:
            continue
        assignee = fields.get("assignee")
        owner = None
        if isinstance(assignee, dict):
            owner = assignee.get("name") or assignee.get("accountId")
        elif isinstance(assignee, str):
            owner = assignee
        rows.append({"key": key, "owner": owner, "when": when,
                     "status": (fields.get("status") or {}).get("name")})
    if not rows:
        raise SystemExit(f"no unresolved {args.project} issue carrying a status "
                         f"transition in the first {args.prefix_bytes} byte(s); "
                         f"raise --prefix-bytes or pick another project")

    # THE REFERENCE DATE IS DERIVED FROM THE DATA. An export cannot know about
    # anything after its own newest record, so the high-water mark is its clock.
    # Typing a date instead -- the dataset's publication date -- put every issue
    # past the window and produced a run that looked like a working audit while
    # measuring the distance between a calendar and the data.
    reference = max(row["when"] for row in rows)
    rows.sort(key=lambda row: row["key"])

    declaration = {
        "format": "engagement-deliverable-audit/declaration/1",
        "engagement": f"apache-{args.project.lower()}-open-issues",
        "reviewed_by": ("DERIVED FROM A PUBLIC DATASET, not a statement of work -- "
                        f"The Public Jira Dataset, Zenodo {RECORD}, CC BY 4.0"),
        "reviewed_on": str(datetime.date.today()), "change_order": 0,
        "stall_window_days": args.window_days,
        "sources": [{"path": f"zenodo:{RECORD}",
                     "derived_from": f"JiraReposAnon, project {args.project}, "
                                     f"unresolved issues, reference {reference.date()}"}],
        "points": [{"id": row["key"], "declared_type": "deliverable",
                    "text": f"open issue in the {args.project} tracker, "
                            f"status {row['status']}",
                    "basis": {"document": f"The Public Jira Dataset (Zenodo {RECORD}, CC BY 4.0)",
                              "location": f"project {args.project}, issue {row['key']}",
                              "quote": row["key"]}} for row in rows]}
    capture = {"format": "engagement-deliverable-audit/capture/1",
               "captured_at": reference.isoformat() + "Z",
               # A REAL DIGEST OF THE BYTES ACTUALLY FETCHED, under the key that
               # claims to be one. This wrote a label into a field named
               # `export_sha256`, and the committed corpus carried sixty-four
               # `z` characters there. The prefix is what this script reads, so
               # it is what there is to hash -- and two runs over the same
               # archive hash the same, which is the equality the field is for.
               "exporter": {"id": f"zenodo:{RECORD} JiraReposAnon, "
                                  f"range-fetched prefix",
                            "export_sha256": PREFIX_SHA256},
               "complete": True, "errors": [],
               "points": [{"name": row["key"], "owner": row["owner"],
                           "state": row["status"],
                           "days_since_transition": (reference - row["when"]).days}
                          for row in rows]}
    out = Path(args.out)
    out.mkdir(exist_ok=True)
    (out / "jira-declaration.json").write_text(json.dumps(declaration, indent=1) + "\n")
    (out / "jira-capture.json").write_text(json.dumps(capture, indent=1) + "\n")
    tally = collections.Counter(
        "orphaned" if not p["owner"]
        else ("moving" if p["days_since_transition"] <= args.window_days else "stalled")
        for p in capture["points"])
    print(f"{len(rows)} real issue(s) from {args.project}; reference {reference.date()}")
    print(f"  {dict(tally)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
