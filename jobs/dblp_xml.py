"""Shared constant-memory streaming reader for the dblp XML dump.

Used by both profile_dblp.py (Task 0) and etl.py (P2), so the two never
drift on how records are read, entities are resolved, or a venue key
prefix is derived.

DTD resolution note (a real finding from live-testing against lxml 6.1.3):
`etree.iterparse` takes no `parser=`/custom-resolver argument at all, and a
resolver registered on the global default parser is never consulted for
iterparse's own internal DTD loading. What actually resolves the dump's
`<!DOCTYPE dblp SYSTEM "dblp.dtd">` is libxml2's own relative-path lookup
against the parsed file's on-disk location — i.e. exactly the proposal's
own DATA-1 instruction, "keeping dblp.dtd next to it", taken literally.
So instead of a custom Resolver class, we just make sure a file literally
named `dblp.dtd` sits next to the `.xml.gz` being parsed before parsing.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import gzip

from lxml import etree

PUBLICATION_TAGS = (
    "article",
    "inproceedings",
    "proceedings",
    "book",
    "incollection",
    "phdthesis",
    "mastersthesis",
)
ALL_RECORD_TAGS = PUBLICATION_TAGS + ("www",)


def venue_prefix(key: str) -> str:
    parts = key.split("/")
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return parts[0]


def author_key(author_elem) -> str:
    """Natural key for an <author> tag.

    Real finding from profiling the live dump: dblp's bulk XML release
    never carries a `pid` attribute on <author> tags (0% coverage across
    34M+ author tags in the real Sept 2026 release) - that only exists in
    a different dblp interface (the search API), not this format. What it
    does sometimes carry is `orcid` (confirmed present on real records),
    and its actual disambiguation mechanism for the bulk dump is the name
    text itself: dblp bakes a numeric suffix directly into homonymous
    authors' names (e.g. "Wei Wang 0001"), resolvable to a canonical
    identity via the matching <www> person record's own `key` - not via
    any attribute on the <author> tag in publication records.
    """
    orcid = author_elem.get("orcid")
    if orcid:
        return f"orcid:{orcid}"
    text = (author_elem.text or "").strip()
    return f"name:{text}"


def _ensure_dtd_alongside(xml_gz_path: Path, dtd_path: Path) -> None:
    """Copy dtd_path to <xml_gz_path's directory>/dblp.dtd if it isn't
    already there, since that's the literal SYSTEM id every dblp release
    (and our own test fixture) declares."""
    target = xml_gz_path.parent / "dblp.dtd"
    if target.resolve() == dtd_path.resolve():
        return
    if not target.exists():
        shutil.copyfile(dtd_path, target)


def stream_records(xml_gz_path: Path, dtd_path: Path, limit: int | None = None):
    """Yields each top-level record element (article/inproceedings/.../www)
    in document order, in constant memory: each element is cleared and its
    now-empty preceding siblings are dropped from the implicit root as soon
    as it's been yielded and the caller moves on to the next one."""
    _ensure_dtd_alongside(xml_gz_path, dtd_path)

    count = 0
    with gzip.open(xml_gz_path, "rb") as fh:
        context = etree.iterparse(
            fh,
            events=("end",),
            tag=ALL_RECORD_TAGS,
            load_dtd=True,
            resolve_entities=True,
            no_network=True,
            recover=True,
        )
        for _, elem in context:
            yield elem
            count += 1
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
            if limit is not None and count >= limit:
                break
    del context
