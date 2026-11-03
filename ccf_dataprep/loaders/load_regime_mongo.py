#!/usr/bin/env python3
"""Wave 19 Task 4 — regime text (Reg O / CRR / PRA) into MongoDB `fibo_v2`.

Reads `sources/regimes/passages.json` (`generators/extract_regime_passages.py`)
and upserts into the same `document` / `passage` collections every other
wave's corpus lives in. §C assigns regime rule text and passage spans to
MongoDB and nowhere else — nothing here belongs in Postgres or Fluree.

**`doc_type: "regime_text"` is set on these 31 rows and ONLY these 31.**
Follows the Wave 16/17 precedent exactly (`doc_type` is scoped to the rows a
given loader owns; the pre-existing 178-row gap is left alone, untouched and
unwidened).

**No `embedding` is written here.** Embeddings are a separate, resumable,
model-versioned pass (`loaders/embed_passages.py`) — see that module's
docstring for why coupling them to ingestion would be wrong. Run it after
this loader; a passage with no vector is still retrievable by its `regime`
+ `provision`, which is the anchor Task 15 actually needs.

**Field names**: `document_id` / `start_offset` / `end_offset` — the
estate's established spelling, not the brief's literal `doc_id` /
`char_start` / `char_end`. See `generators/extract_regime_passages.py`'s
module docstring for the precedent (Wave 18 Task 11) this follows.

Idempotent: upsert by `_id` (== `document_id` / `passage_id`, both
content-derived), then reconcile away any stale `doc_type: "regime_text"`
row whose id is no longer in the current artifact — scoped strictly to that
`doc_type`, so a re-run after a parsing fix can never leave a phantom
passage behind and can never touch any other wave's rows.

## Task 10 addition — methodology documentation

§C assigns "methodology documentation" to MongoDB as internal model-risk
material, and §F asks for three ProjectionPlans "with the examiner
rendering carrying full methodology and replay attribution". This project
does not build that rendering, its pointing, or its resolution — see
CLAUDE.md's operator boundary. What it owes is the material such a
rendering would point at, and that material has to be true: **`doc_type:
"methodology"` is `synthetic — internal`** (it was authored for this
demonstration), while it *cites* the `doc_type: "regime_text"` passages
above by `passage_id` rather than restating their text — duplicating a
`public` passage into a `synthetic — internal` one would blur the two
provenance classes CLAUDE.md keeps separate.

Two documents, built in-process as paragraph lists rather than read from a
fetched artifact, because there is no source to fetch — this text is
authored, not extracted. Offsets are computed the same way
`extract_regime_passages.py`'s `DocumentBuilder` does it: each paragraph is
appended to a running buffer and its span recorded as exactly the slice it
just wrote, so `document.text[start:end] == passage.text` holds by
construction rather than by a second extraction pass that could diverge
from the first. `_MethodologyBuilder` below is that same pattern,
re-implemented locally rather than imported, because the generator module
is Task 4's and importing from it would make a documentation loader depend
on a regime-text parser for an unrelated reason.

  * `large-exposure-methodology-concentration` — how a group's concentration
    is computed (control-basis vs. both-basis grouping, the unit fix this
    ratio depends on), the corrected CRR/PRA/Reg O regime landscape, and
    **the Reg O narrowing sentence** required by Task 10's brief.
  * `large-exposure-methodology-replay-attribution` — what "replay
    attribution" means for an as-of reconstruction that crosses the one
    real CRR→PRA boundary in this estate's data, and what distinguishes the
    examiner catalog row (Task 12) from the other two — described, not
    implemented.

Every passage in both is checked, at load time, against the offset
invariant above before being written — not merely trusted from
construction — because a documentation loader is exactly the place a
future paragraph edit could shift an offset without anyone re-running the
generator that would have caught it elsewhere.

**`doc_type: "methodology"` is set on these 2 rows and ONLY these 2**,
following the `regime_text` / `sar_narrative` / `fincen_advisory` precedent
above and in Wave 17: idempotent upsert by `_id`, then a `delete_many`
scoped strictly to `doc_type: "methodology"` so a future edit that drops or
renames a document can never leave a phantom passage or document behind,
and can never touch the 31 `regime_text` rows or the pre-existing
178-row `doc_type` gap.

Embeddings are, again, deliberately NOT computed here — run
`loaders/embed_passages.py` afterward.

    uv run loaders/load_regime_mongo.py --dry-run
    uv run loaders/load_regime_mongo.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys

from pymongo import ASCENDING, UpdateOne

from ccf.config import REPO_ROOT, mongo_db

ARTIFACT = REPO_ROOT / "sources" / "regimes" / "passages.json"

METHODOLOGY_PROVENANCE = "synthetic — internal"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class _MethodologyBuilder:
    """Accumulates one authored document's text and its paragraphs' offsets
    together, so `document.text[start:end] == passage.text` can never drift
    from the text — the same shape as `extract_regime_passages.py`'s
    `DocumentBuilder`, for authored prose instead of parsed source text.
    """

    def __init__(self) -> None:
        self._parts: list[str] = []
        self._len = 0
        self.spans: list[tuple[int, int]] = []

    def add(self, paragraph: str) -> None:
        paragraph = paragraph.strip()
        start = self._len
        self._parts.append(paragraph)
        self._len += len(paragraph)
        self.spans.append((start, self._len))
        sep = "\n\n"
        self._parts.append(sep)
        self._len += len(sep)  # separator AFTER measuring end — never inside a span

    def text(self) -> str:
        return "".join(self._parts)


def _build_methodology_doc(document_id: str, title: str,
                            paragraphs: list[str]) -> tuple[dict, list[dict]]:
    """Build one `doc_type: "methodology"` document plus its passages.

    Passage ids follow the estate's content-derived convention
    (`generators/extract_regime_passages.py`): `{document_id}#{sha256(text)[:12]}`,
    disambiguated with a trailing `-N` on a same-document text collision —
    two paragraphs are never expected to be byte-identical here, but the
    disambiguation costs nothing to keep and matches the precedent exactly.
    """
    builder = _MethodologyBuilder()
    for p in paragraphs:
        builder.add(p)
    body = builder.text()

    doc = {
        "document_id": document_id,
        "doc_type": "methodology",
        "title": title,
        "provenance": METHODOLOGY_PROVENANCE,
        "text": body,
    }

    passages: list[dict] = []
    seen_hash: dict[str, int] = {}
    for start, end in builder.spans:
        span_text = body[start:end]
        # The offset invariant checked directly, not assumed from
        # construction — see the module docstring on why this loader
        # checks it explicitly rather than trusting the builder alone.
        assert body[start:end] == span_text
        h = _sha256(span_text)[:12]
        n = seen_hash.get(h, 0)
        seen_hash[h] = n + 1
        pid = f"{document_id}#{h}" if n == 0 else f"{document_id}#{h}-{n + 1}"
        passages.append({
            "passage_id": pid,
            "document_id": document_id,
            "start_offset": start,
            "end_offset": end,
            "text": span_text,
            "provenance": METHODOLOGY_PROVENANCE,
        })
    return doc, passages


#: The Reg O narrowing sentence. Task 16 records this SAME narrowing as a
#: `divergence` string in `spec_coverage.py` — the two must agree, per Task
#: 10's brief, so this is the one place the sentence is composed and every
#: other reference should quote it rather than re-derive it.
#:
#: Fix round 1 (coordinator review): the first cut cited only
#: `#0abca652a7ea` (§215.4(c)) for the 15% / 10% / "12 U.S.C. 84" figures.
#: That passage applies a lending limit to insiders but does not itself
#: state the figures — §215.4(c) reads "...exceeds the lending limit of
#: the member bank specified in § 215.2(i)...", nothing more. The figures
#: live in `#091a96ab5d80` (§215.2(i)) instead. Same shape as the PRA LE
#: 2.3/2.4 problem Task 9 fixed: regulation routinely states a limit by
#: cross-reference, and the passage that *applies* a rule is not the
#: passage that *states* it. Both are now cited, with the sentence
#: explicit about which citation carries which claim.
REG_O_NARROWING = (
    "Regulation O, 12 CFR 215.4, is a stack of insider-lending limits, not "
    "a flat $500,000 test: §215.4(b)(1) requires prior board approval "
    "above the higher of $25,000 or 5% of unimpaired capital and surplus "
    "(reg-o-12cfr215#e3a20d42e411); §215.4(b)(2) sets the $500,000 "
    "absolute ceiling above which that approval is required regardless "
    "(reg-o-12cfr215#f8f8d951ecdb); §215.4(c) applies to insiders a "
    "single-borrower lending limit (reg-o-12cfr215#0abca652a7ea) that "
    "§215.2(i) defines as 15% of unimpaired capital and surplus, plus up "
    "to an additional 10% for fully secured amounts, via 12 U.S.C. 84 "
    "(reg-o-12cfr215#091a96ab5d80); and §215.4(d) sets an aggregate "
    "ceiling across all insiders combined, at up to the bank's unimpaired "
    "capital and surplus (reg-o-12cfr215#07b240b412e2). This estate's "
    "demonstration exercises the $500,000 absolute cap of §215.4(b)(2) "
    "only, because it is the sole limb that binds at this estate's "
    "magnitudes: 5% of the reporting bank's Tier 1 capital is on the order "
    "of $14.8 billion, and the 15% single-borrower and aggregate limits "
    "sit further still, so no exposure in this dataset approaches any "
    "percentage-based limb — only the fixed-dollar cap is engineered to "
    "bind here."
)

#: Per-citation figure-presence checks for `REG_O_NARROWING`. Each entry is
#: (provision label, passage_id, [substrings the sentence attributes to
#: that passage]) — verified against the passage's OWN fetched text, not
#: asserted from the sentence. This is the check the fix-round-1 finding
#: asked for made permanent: a citation that resolves is not the same as a
#: citation that contains the number being attributed to it.
REG_O_CITATION_CHECKS = [
    ("215.4(b)(1)", "reg-o-12cfr215#e3a20d42e411", ["$25,000", "5 percent"]),
    ("215.4(b)(2)", "reg-o-12cfr215#f8f8d951ecdb", ["$500,000"]),
    ("215.4(c)", "reg-o-12cfr215#0abca652a7ea",
     ["215.2(i)"]),  # applies the limit by cross-reference; states no figure itself
    ("215.2(i)", "reg-o-12cfr215#091a96ab5d80",
     ["15 percent", "10 percent", "12 U.S.C. 84"]),
    ("215.4(d)", "reg-o-12cfr215#07b240b412e2",
     ["unimpaired capital and unimpaired surplus"]),
]


def _verify_reg_o_citations(regime_passages: list[dict]) -> bool:
    """Print, for each citation in REG_O_NARROWING, whether the fetched
    passage text actually contains the figure the sentence attributes to
    it -- the mapping made visible rather than asserted. Returns whether
    every check passed.
    """
    by_id = {p["passage_id"]: p["text"] for p in regime_passages}
    print("\nReg O narrowing -- citation figure-presence check\n")
    all_ok = True
    for label, pid, needles in REG_O_CITATION_CHECKS:
        text = by_id.get(pid)
        if text is None:
            print(f"  {label:<14} {pid:<28} MISSING FROM ARTIFACT")
            all_ok = False
            continue
        for needle in needles:
            present = needle in text
            all_ok = all_ok and present
            print(f"  {label:<14} {pid:<28} {needle!r:<18} "
                  f"{'present' if present else 'ABSENT'}")
    return all_ok


REGIME_LANDSCAPE = (
    "Three regime versions are anchored in Fluree with a citable public "
    "provision each. Assimilated CRR Article 395(1) governed the "
    "reporting bank's UK-facing large-exposure limit through 2021-12-31: "
    "‘An institution shall not incur an exposure ... the value of "
    "which exceeds 25% of its eligible capital’ "
    "(crr-art-395-2021-12-31#491d3c2ccd3e). From 2022-01-01 (Statutory "
    "Instrument 2021/1078), the PRA Rulebook's Large Exposures Part "
    "applies alongside it. The PRA Part did not relocate the prohibition: "
    "measured against the fetched PRA corpus, the Large Exposures Part "
    "contains no passage that itself prohibits incurring an exposure — its "
    "only two literal ‘25%’ occurrences sit in LE 2.3, a "
    "core-UK-group notification duty, not a freestanding limit "
    "(pra-large-exposures-01-01-2022#c504aeed7451) — while LE 2.4 requires "
    "a firm to ‘exclude from the limit in Article 395(1) of the "
    "CRR’ certain resolution exposures "
    "(pra-large-exposures-01-01-2022#1ee205cc4796), which is the PRA Part "
    "confirming, by cross-reference, that the operative prohibition still "
    "lives in Article 395(1). The PRA Part applies to and modifies that "
    "CRR limit; it does not replace it. Both regime versions carry the "
    "same 25% limit, so crossing the 2021-12-31 / 2022-01-01 boundary "
    "changes which RegimeVersion node and citation an as-of reconstruction "
    "attaches, without changing the threshold."
)


def _methodology_documents() -> tuple[list[dict], list[dict]]:
    """The two `doc_type: "methodology"` documents and their passages.

    Kept as one function so the reconciliation step below has a single
    place to read the full, current set from — the same shape as the
    `regime_text` artifact's `documents`/`passages` lists, just authored
    here instead of parsed from a fetch.
    """
    concentration_doc, concentration_passages = _build_methodology_doc(
        "large-exposure-methodology-concentration",
        "Large Exposure Concentration Measurement Methodology",
        [
            "This note documents, for internal model-risk review, how this "
            "estate's large-exposure-rwa-concentration demonstration "
            "measures group concentration against the reporting bank's "
            "capital base. It is synthetic — internal: the methodology "
            "itself was authored for this demonstration dataset, and it "
            "cites public regulatory text rather than restating it. Nothing "
            "in this document is an assertion about the real reporting "
            "bank's actual regulatory standing; every appetite, breach, and "
            "proposal it describes belongs to this dataset's synthetic "
            "internal envelope or its deliberately engineered scenarios, "
            "not to any real finding about the institution.",

            "A ‘group’ is a connected component over the Fluree "
            "edges ex:connectedTo (control-basis ownership) and, where the "
            "wider both-basis definition applies, ex:economicallyDependentOn "
            "as well, resolved by application-side union-find rather than "
            "any Fluree graph algorithm — Fluree carries the typed "
            "edges; grouping is computed fresh from them on every run, "
            "never read from a stored group id. Two components are reported "
            "for the same obligor set where a control-basis edge and an "
            "economic-dependence edge would place it in different groups: "
            "the narrower control-basis grouping and the wider both-basis "
            "grouping, so a dependency edge's effect on which limit binds "
            "is visible rather than merged away.",

            "Group exposure is the sum of ccf_v2.facility.commitment_amount "
            "(dollars) across every facility booked to a group member at "
            "the reporting bank, divided by the reporting bank's Tier 1 "
            "capital. Tier 1 capital is sourced from FDIC BankFind Call "
            "Report data in ccf_v2.bank_capital, which publishes in "
            "thousands of dollars; the unit column added to that table "
            "(loaders/load_wave19_postgres.py) and the magnitude assertion "
            "running against it exist because this ratio does not cancel "
            "the unit the way a same-table ratio like CET1 does — an "
            "unconverted thousands figure would understate every "
            "concentration ratio in this methodology by three orders of "
            "magnitude.",

            REGIME_LANDSCAPE,

            REG_O_NARROWING,

            "The internal appetite modeled in this estate's LimitEnvelope "
            "is calibrated, not arbitrary: it sits below the largest real "
            "control-basis group's share of the reporting bank's Tier 1 "
            "capital, so that group is compliant under both CRR and PRA "
            "(25% each) while breaching the synthetic internal appetite "
            "— demonstrating that an internal limit can be the binding "
            "constraint even where every real regulatory limit is "
            "satisfied. A second, engineered ex:economicallyDependentOn "
            "edge is calibrated to be individually immaterial and jointly "
            "consequential: neither endpoint alone crosses the appetite, "
            "but the both-basis group formed by including that edge does, "
            "so the wider grouping changes which limit binds and the "
            "narrower one does not.",

            "This methodology document, and the internal appetite and "
            "grouping logic it describes, are provenance synthetic — "
            "internal: invented for this demonstration because they are "
            "bank-internal by nature. The regime text they cite — CRR, "
            "the PRA Rulebook, and Regulation O — is provenance "
            "public, fetched and retained as separate MongoDB "
            "document/passage records; this note cites those records by "
            "passage_id rather than reproducing their text.",
        ],
    )

    replay_doc, replay_passages = _build_methodology_doc(
        "large-exposure-methodology-replay-attribution",
        "Replay Attribution and As-of Reconstruction Methodology",
        [
            "§F of large-exposure-rwa-concentration calls for three "
            "catalog rows describing what each perspective — "
            "credit-officer, committee, examiner — would receive, with "
            "the examiner rendering carrying full methodology and replay "
            "attribution that the other two do not. This document, and its "
            "companion large-exposure-methodology-concentration, are the "
            "methodology material such a rendering would point at. This "
            "project does not implement the pointing, resolution, or "
            "assembly of any rendering — that is runtime SDK "
            "behaviour; this document only makes the underlying data "
            "support it.",

            "Replay attribution means reconstructing, for an as-of date "
            "the examiner specifies, which RegimeVersion governed the "
            "reporting bank's large-exposure limit at that date, which "
            "public provision it cites, and what the internal appetite and "
            "the recomputed group concentration were at that point — "
            "rather than only the current live answer. It depends on what "
            "this ledger actually records, no more: valid time as "
            "ex:effectiveFrom (and ex:effectiveTo, on the one RegimeVersion "
            "that has closed) on every ex:RegimeVersion and the one "
            "ex:LimitEnvelope, and assertion time as the Fluree ledger's "
            "own commit sequence — not a per-triple assertedOn/assertedAt "
            "predicate, which no ex:RegimeVersion or ex:LimitEnvelope node "
            "carries. The ex:connectedTo control edges carry neither valid "
            "nor assertion time of their own; of the ex:economicallyDependentOn "
            "edges, only the four engineered ones carry an ex:assertedOn "
            "value, and it sits on the subject node rather than the edge "
            "itself. This note describes what an examiner reconstruction "
            "must read, not a new mechanism for reading it.",

            "This estate's regime-version history crosses exactly one "
            "real boundary: assimilated CRR Article 395(1) governed "
            "through 2021-12-31, and the PRA Rulebook's Large Exposures "
            "Part has governed since 2022-01-01 (Statutory Instrument "
            "2021/1078) — both at a 25% limit, so an as-of "
            "reconstruction that crosses that date changes which "
            "RegimeVersion and citation attach to the answer without "
            "changing the threshold itself. Regulation O's $500,000 cap is "
            "a separate, non-percentage limb governing insider lending "
            "rather than group concentration; see "
            "large-exposure-methodology-concentration for its full stack "
            "and the narrowing this estate exercises.",

            "Of the three catalog rows in "
            "ccf_v2.large_exposure_projection_plan, only the examiner "
            "perspective's elements_included is expected to name this "
            "methodology documentation and the regime-version citation "
            "trail; the credit-officer and committee rows are not. That "
            "catalog table is itself explicit that it holds descriptive "
            "data about what each perspective would receive, not a "
            "runtime object that resolves or assembles anything — see "
            "its own table comment. This document is what makes the "
            "examiner row's claim to carry ‘full methodology and "
            "replay attribution’ true of the underlying data, "
            "independent of whatever runtime component might later read "
            "it.",

            "Provenance synthetic — internal, for the same reason as "
            "its companion document: replay-attribution methodology is "
            "bank-internal model-risk material invented for this "
            "demonstration. It names no fact about the real reporting "
            "bank's regulatory standing; every appetite figure, breach, "
            "and as-of scenario it references belongs to this estate's "
            "synthetic envelope.",
        ],
    )

    documents = [concentration_doc, replay_doc]
    passages = concentration_passages + replay_passages

    # The offset invariant, checked once more here across BOTH documents
    # together rather than only inside the builder — the exact assertion
    # Task 10's brief requires, run against what is actually about to be
    # written, not against an intermediate the builder already discarded.
    by_id = {d["document_id"]: d for d in documents}
    for p in passages:
        doc_text = by_id[p["document_id"]]["text"]
        actual = doc_text[p["start_offset"]:p["end_offset"]]
        if actual != p["text"]:
            raise AssertionError(
                f"offset invariant broken for {p['passage_id']}: "
                f"document.text[{p['start_offset']}:{p['end_offset']}] != "
                f"passage.text")

    return documents, passages


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not ARTIFACT.exists():
        print(f"missing {ARTIFACT} -- run "
              f"generators/extract_regime_passages.py first")
        return 1

    art = json.loads(ARTIFACT.read_text())
    documents = art["documents"]
    passages = art["passages"]

    print("Wave 19 Task 4 — MongoDB load\n")
    by_regime: dict[str, list[int]] = {}
    for d in documents:
        by_regime.setdefault(d["regime"], [0, 0])
        by_regime[d["regime"]][0] += 1
    for p in passages:
        by_regime[p["regime"]][1] += 1
    for regime, (n_doc, n_pass) in sorted(by_regime.items()):
        print(f"  {regime:<6} {n_doc:>3} documents  {n_pass:>4} passages")
    print(f"\n  {len(documents)} documents, {len(passages)} passages total")

    meth_documents, meth_passages = _methodology_documents()
    print("\nTask 10 — methodology documentation\n")
    for d in meth_documents:
        n = sum(1 for p in meth_passages if p["document_id"] == d["document_id"])
        print(f"  {d['document_id']:<44} {n:>2} passages  "
              f"provenance={d['provenance']}")
    print(f"\n  {len(meth_documents)} documents, {len(meth_passages)} passages total")

    citations_ok = _verify_reg_o_citations(passages)
    if not citations_ok:
        raise RuntimeError(
            "REG_O_NARROWING cites a figure not present in its passage -- "
            "see the citation check printed above")

    if args.dry_run:
        print("\n  DRY RUN — nothing written.")
        return 0

    db = mongo_db()

    db["document"].bulk_write([
        UpdateOne({"_id": d["document_id"]}, {"$set": d}, upsert=True)
        for d in documents
    ], ordered=False)

    db["passage"].bulk_write([
        UpdateOne({"_id": p["passage_id"]}, {"$set": p}, upsert=True)
        for p in passages
    ], ordered=False)

    # Reconcile, don't just append — this loader is the only writer of
    # doc_type: "regime_text" rows, and the artifact is authoritative for
    # the full set that should exist. A re-run after a parser fix must not
    # leave a document or passage behind for a citation that no longer
    # parses. Scoped to doc_type: "regime_text" specifically, matching the
    # Wave 17 SAR-narrative precedent, so this can never touch any other
    # wave's rows or the pre-existing doc_type gap.
    doc_ids = [d["document_id"] for d in documents]
    passage_ids = [p["passage_id"] for p in passages]
    del_docs = db["document"].delete_many(
        {"doc_type": "regime_text", "_id": {"$nin": doc_ids}})
    del_pass = db["passage"].delete_many(
        {"regime": {"$in": ["reg-o", "crr", "pra"]}, "_id": {"$nin": passage_ids}})

    # Same reconciliation shape, scoped to doc_type: "methodology" instead
    # -- these two writers can never see each other's rows because the
    # $nin lists and the doc_type filters are disjoint by construction.
    meth_doc_ids = [d["document_id"] for d in meth_documents]
    meth_passage_ids = [p["passage_id"] for p in meth_passages]

    db["document"].bulk_write([
        UpdateOne({"_id": d["document_id"]}, {"$set": d}, upsert=True)
        for d in meth_documents
    ], ordered=False)
    db["passage"].bulk_write([
        UpdateOne({"_id": p["passage_id"]}, {"$set": p}, upsert=True)
        for p in meth_passages
    ], ordered=False)
    del_meth_docs = db["document"].delete_many(
        {"doc_type": "methodology", "_id": {"$nin": meth_doc_ids}})
    del_meth_pass = db["passage"].delete_many(
        {"document_id": {"$in": meth_doc_ids}, "_id": {"$nin": meth_passage_ids}})

    db["passage"].create_index([("document_id", ASCENDING),
                                ("start_offset", ASCENDING)])
    db["passage"].create_index([("regime", ASCENDING), ("provision", ASCENDING)])
    db["document"].create_index([("doc_type", ASCENDING)])

    n_doc = db["document"].count_documents({"_id": {"$in": doc_ids}})
    n_pass = db["passage"].count_documents({"_id": {"$in": passage_ids}})
    n_gap = db["document"].count_documents({"doc_type": None})
    print(f"\n  resolved back: {n_doc}/{len(documents)} documents, "
          f"{n_pass}/{len(passages)} passages")
    print(f"  stale regime_text rows reconciled away: "
          f"{del_docs.deleted_count} documents, {del_pass.deleted_count} passages")
    print(f"  pre-existing doc_type gap (untouched, should be unchanged): {n_gap}")

    n_meth_doc = db["document"].count_documents({"_id": {"$in": meth_doc_ids}})
    n_meth_pass = db["passage"].count_documents({"_id": {"$in": meth_passage_ids}})
    print(f"\n  methodology resolved back: {n_meth_doc}/{len(meth_documents)} "
          f"documents, {n_meth_pass}/{len(meth_passages)} passages")
    print(f"  stale methodology rows reconciled away: "
          f"{del_meth_docs.deleted_count} documents, "
          f"{del_meth_pass.deleted_count} passages")

    # Offset invariant re-verified against what is actually now stored,
    # not just what this process built in memory -- a Mongo round-trip
    # (e.g. a codec that mangled the em dash) would show up here and
    # nowhere else.
    bad = 0
    for pid in meth_passage_ids:
        p = db["passage"].find_one({"_id": pid})
        d = db["document"].find_one({"_id": p["document_id"]})
        if d["text"][p["start_offset"]:p["end_offset"]] != p["text"]:
            bad += 1
    print(f"  offset invariant on stored rows: {len(meth_passage_ids) - bad}/"
          f"{len(meth_passage_ids)} hold")

    if n_doc != len(documents) or n_pass != len(passages):
        raise RuntimeError(
            "upsert did not resolve back to the full artifact -- "
            f"{n_doc}/{len(documents)} documents, {n_pass}/{len(passages)} passages")
    if n_meth_doc != len(meth_documents) or n_meth_pass != len(meth_passages):
        raise RuntimeError(
            "methodology upsert did not resolve back to the full set -- "
            f"{n_meth_doc}/{len(meth_documents)} documents, "
            f"{n_meth_pass}/{len(meth_passages)} passages")
    if bad:
        raise RuntimeError(
            f"{bad} stored methodology passage(s) fail the offset invariant")
    return 0


if __name__ == "__main__":
    sys.exit(main())
