#!/usr/bin/env python3
"""Pure tests for bounded rendering search over DEF 14A / 8-K prose.

The point of the inversion: we are not asking "what officers exist in this
document?" — we hold the roster already. We are asking "how does this document
render RAMESH SRINIVASAN?". That has a known answer set, so a miss is visible.

    uv run validators/test_renderings.py
"""

from __future__ import annotations

import sys

from generators.fetch_def14a import find_renderings, strip_html

PROXY = """
<html><body>
<p>Our Board has nominated <b>Ramesh Srinivasan</b>, who has served as
President and Chief Executive Officer since 2017.</p>
<table><tr><td>Mr. R. Srinivasan</td><td>President &amp; CEO</td></tr>
<tr><td>Dana Sue Jones</td><td>Director</td></tr></table>
</body></html>
"""


def check_strip() -> list[tuple[str, bool]]:
    text = strip_html(PROXY)
    return [
        ("tags are removed", "<b>" not in text and "<td>" not in text),
        ("entities are unescaped", "&amp;" not in text and "&" in text),
        ("text survives", "Ramesh Srinivasan" in text),
        ("adjacent cells do not fuse into one token",
         "CEODana" not in text),
    ]


def check_find() -> list[tuple[str, bool]]:
    text = strip_html(PROXY)
    roster = [
        {"person_key": "0001277036", "last": "SRINIVASAN", "first": "RAMESH",
         "name_as_filed": "SRINIVASAN RAMESH"},
        {"person_key": "0001775010", "last": "Jones", "first": "Dana",
         "name_as_filed": "Jones Dana Sue"},
        {"person_key": "0000000001", "last": "Nobody", "first": "Absent",
         "name_as_filed": "Nobody Absent"},
    ]
    found = {r["person_key"]: r for r in find_renderings(text, roster, source="def14a")}
    return [
        ("a display-order rendering is found", "0001277036" in found),
        ("the variant is the DOCUMENT's rendering, not the filed one",
         found.get("0001277036", {}).get("variant_name") == "Ramesh Srinivasan"),
        ("a second person is found independently", "0001775010" in found),
        ("a person absent from the document is not invented",
         "0000000001" not in found),
        ("provenance is public", all(v["provenance"] == "public"
                                     for v in found.values())),
        ("source is carried", all(v["source"] == "def14a" for v in found.values())),
    ]


def main() -> int:
    cases = check_strip() + check_find()
    failures = sum(not ok for _, ok in cases)
    for label, ok in cases:
        print(f"  [{'ok  ' if ok else 'FAIL'}] {label}")
    print(f"\n  {len(cases) - failures}/{len(cases)} cases behave as specified\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
