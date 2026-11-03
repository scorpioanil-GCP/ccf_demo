"""Anchor nodes must be uniquely keyed, typed, and hash to what they claim.

The defect this guards was a URI missing a field. `load_anchors_wave6.py` keyed
a node on `COVSRC-{accession}-{covenant_type[:8]}`, and
`covenants_extracted.json` holds 60 document entries across 47 accessions --
one filing appears once per exhibit. XPO `0001104659-26-068522` carries two
separate credit agreements, each with its own `leverage`,
`fixed_charge_coverage` and `secured_leverage` covenant. Six URIs therefore
received two covenants from two agreements.

Nothing failed. The node existed, answered every predicate query, and carried
two of everything. A join over the four anchor literals returned the
cross-product -- 79 candidate citations of which 36 did not hash to what the
node said they should, and 12 sliced to empty because a start from one
agreement paired with an end from the other.

`ex:evidencedBy` was intact at 43/43 throughout, which is why nothing noticed:
the correct route always worked and only the obvious one was wrong.
"""

from __future__ import annotations

import hashlib

import pytest
from pymongo import MongoClient

from ccf import config as C
from ccf import fluree

EX = "http://example.org/fibo/"


def _q(select: str, where: str) -> list:
    return fluree.query(
        f"SELECT {select} FROM <{C.FLUREE_LEDGER_V2}> WHERE {{ {where} }}"
    )["results"]["bindings"]


@pytest.fixture(scope="module")
def anchors() -> list:
    return _q("?s ?doc ?st ?en ?sha",
              f"?s a <{EX}PassageAnchor> ; <{EX}documentId> ?doc ; "
              f"<{EX}startOffset> ?st ; <{EX}endOffset> ?en ; "
              f"<{EX}passageSha256> ?sha .")


def test_the_four_literal_join_does_not_fan_out(anchors) -> None:
    """One row per anchor. A collided URI shows up here as extra rows.

    This is the shape of the original defect and the cheapest way to see it
    return: 44 anchors joining to 79 rows means some node carries two of
    everything again.
    """
    subjects = {b["s"]["value"] for b in anchors}
    assert anchors, "no anchors found -- this check would pass vacuously"
    assert len(anchors) == len(subjects), (
        f"{len(anchors)} join rows over {len(subjects)} subjects -- a node "
        f"carries more than one anchor, so the URI key has lost a field again")


def test_every_anchor_hashes_to_what_it_claims(anchors) -> None:
    """The claim the anchor exists to support, checked rather than trusted.

    A count cannot catch this: before the fix there were 79 rows and every one
    of them had all four literals present. 36 were wrong anyway.
    """
    db = MongoClient(C.MONGO_URI, serverSelectionTimeoutMS=15000)[C.MONGO_DB_V2]
    texts: dict[str, str] = {}
    bad = []
    for b in anchors:
        did = b["doc"]["value"]
        if did not in texts:
            doc = db.document.find_one({"document_id": did}) or {}
            texts[did] = doc.get("text") or ""
        st, en = int(b["st"]["value"]), int(b["en"]["value"])
        got = hashlib.sha256(texts[did][st:en].encode()).hexdigest()
        if got != b["sha"]["value"]:
            bad.append((b["s"]["value"].rsplit("/", 1)[-1], st, en))
    assert not bad, f"{len(bad)} of {len(anchors)} anchors do not hash: {bad[:3]}"


def test_no_span_is_inverted(anchors) -> None:
    """start > end slices to "" in Python, which is indistinguishable from an
    empty span and from a correct zero-length one. Assert it directly."""
    inverted = [(b["s"]["value"].rsplit("/", 1)[-1],
                 int(b["st"]["value"]), int(b["en"]["value"]))
                for b in anchors if int(b["st"]["value"]) > int(b["en"]["value"])]
    assert not inverted, f"spans with start > end: {inverted}"


def test_every_anchor_node_is_typed() -> None:
    """CLAUDE.md rule 7 -- no inference, so an untyped node is unreachable
    from any type-anchored traversal."""
    untyped = _q("?s", f"?s <{EX}covenantType> ?c . "
                       f'FILTER(CONTAINS(STR(?s),"/COVSRC-")) '
                       f"FILTER NOT EXISTS {{ ?s a ?t }}")
    assert not untyped, f"{len(untyped)} COVSRC nodes carry no rdf:type"


def test_point_anchors_are_distinguishable_from_spans() -> None:
    """`declaredAt` selects exactly the point anchors; start+end exactly the
    resolvable spans. Appended rather than narrowing `startOffset`, so the
    superset stays honest."""
    declared = {b["s"]["value"] for b in _q("?s", f"?s <{EX}declaredAt> ?o")}
    spans = {b["s"]["value"] for b in
             _q("?s", f"?s <{EX}startOffset> ?a ; <{EX}endOffset> ?b .")}
    assert declared, "no declaredAt -- point anchors are not distinguishable"
    assert spans, "no complete spans"
    assert not (declared & spans), (
        f"{len(declared & spans)} subjects claim to be both a point anchor and "
        f"a resolvable span")
