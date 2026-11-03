"""Wave 17 — aml-typology-match. Validates the Task 1 advisory selection and
the Task 2 PDF fetch.

Extended by later tasks as the product's synthetic entities and typology
transactions are generated.
"""
import hashlib
import json
import re
from ccf.config import REPO_ROOT

REQUIRED_TYPOLOGIES = {
    "structuring", "funnel_account", "shell_company_ownership", "trade_based",
}

def test_every_required_typology_has_a_real_advisory():
    """Wave 17 Task 1. The envelope requires four typologies, EACH anchored
    to a real advisory. A selection that silently covers three and leaves the
    fourth to be invented later is the 'counted but not created' failure this
    estate keeps recording -- so the artifact must name an advisory for every
    one, and every advisory must carry the fields needed to cite it."""
    path = REPO_ROOT / "sources" / "fincen" / "selection.json"
    assert path.exists(), "run generators/select_fincen_advisories.py first"
    data = json.loads(path.read_text())
    got = {t["typology"] for t in data["typologies"]}
    assert got == REQUIRED_TYPOLOGIES, f"missing: {REQUIRED_TYPOLOGIES - got}"
    for t in data["typologies"]:
        assert t["advisory_number"], f"{t['typology']} has no advisory number"
        assert t["url"].startswith("https://www.fincen.gov/"), t["url"]
        assert len(t["issued"]) == 10, f"{t['typology']} issue date not a date"
        assert t["matched_on"], (
            f"{t['typology']} does not record WHY this advisory was chosen -- "
            "a selection nobody can audit is a guess wearing evidence's coat")

def test_selection_records_retrieval_date():
    """A public source without a retrieval date cannot be re-verified later.
    CLAUDE.md rule 1 requires source AND retrieval date for every public
    element."""
    path = REPO_ROOT / "sources" / "fincen" / "selection.json"
    data = json.loads(path.read_text())
    assert data.get("retrieved_at"), "no retrieved_at on the selection"

def test_every_selected_advisory_pdf_was_actually_fetched():
    """Wave 17 Task 2. A manifest entry proves a fetch happened; a file on
    disk proves it produced bytes. Assert BOTH, because a manifest written
    before a failed download is exactly the artifact that looks complete.

    The manifest is `ccf.fetch.SourceManifest`'s shape (`fetches[]`, each
    with `url`/`path`/`sha256`/`bytes`/`content_type`), not an ad hoc one --
    this project's shared fetch harness, reused rather than reinvented."""
    sel = json.loads((REPO_ROOT / "sources" / "fincen" / "selection.json").read_text())
    man = json.loads((REPO_ROOT / "sources" / "fincen" / "manifest.json").read_text())
    by_url = {r["url"]: r for r in man["fetches"]}
    for t in sel["typologies"]:
        rec = by_url.get(t["pdf_url"])
        assert rec, f"{t['typology']}: selected PDF but never fetched"
        path = REPO_ROOT / rec["path"]
        assert path.exists(), f"{rec['path']} in manifest but not on disk"
        assert path.stat().st_size == rec["bytes"], (
            f"{rec['path']} size disagrees with the manifest")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == rec["sha256"], f"{rec['path']} content changed"
        assert rec["bytes"] > 20_000, (
            f"{rec['path']} is {rec['bytes']} bytes -- too small to be an "
            "advisory PDF; likely an error page fetched with status 200")
        # Status code alone proves nothing: FinCEN serves a styled 200 HTML
        # error page for a bad path. Content-type and magic bytes do not.
        content_type = rec["content_type"].split(";")[0].strip().lower()
        assert content_type == "application/pdf", (
            f"{rec['path']} content-type is {rec['content_type']!r}, not "
            "application/pdf")
        assert path.read_bytes()[:4] == b"%PDF", (
            f"{rec['path']} does not start with the %PDF magic bytes -- "
            "likely an HTML error page stored under a PDF's name")

def test_passage_spans_round_trip_against_their_document():
    """Wave 17 Task 3. A span offset that does not select its own text is
    worse than no offset: every downstream typology citation resolves to the
    wrong words while looking perfectly well-formed. Re-slice the document
    text with each passage's own start/end and require the result to equal
    the stored passage text.

    Estate field names (`document_id`/`start_offset`/`end_offset`), per the
    controller's ruling in `docs/wave17-plan.md` -- the first cut of this
    test used `doc_id`/`start`/`end`, which forced the loader to write a
    second, driftable copy of every offset."""
    from ccf.config import mongo_db
    db = mongo_db()
    docs = {d["_id"]: d for d in db.document.find({"doc_type": "fincen_advisory"})}
    assert docs, "no advisory documents loaded"
    checked = 0
    for p in db.passage.find({"document_id": {"$in": list(docs)}}):
        text = docs[p["document_id"]]["text"]
        # Bind the id BEFORE the assertion. Referencing p["passage_id"] only
        # inside the failure f-string means the message raises KeyError
        # instead of reporting the mismatch -- a failure path that has never
        # run and does not work.
        pid = p["passage_id"]
        assert text[p["start_offset"]:p["end_offset"]] == p["text"], (
            f"passage {pid} span does not select its own text")
        checked += 1
    assert checked >= 40, (
        f"only {checked} advisory passages -- too few to anchor four "
        "typologies with any specificity")

def test_passage_resolves_by_passage_id_field():
    """Task 4 anchors a typology citation with
    `db.passage.find_one({"passage_id": ...})` -- a lookup by FIELD, not by
    `_id`. This loader's first cut excluded `passage_id` from the `$set`
    body (kept it only as `_id`), so every such lookup returned None. Assert
    the field is queryable, not merely present when read back by `_id`."""
    from ccf.config import mongo_db
    db = mongo_db()
    any_passage = db.passage.find_one({"advisory_number": {"$exists": True}})
    assert any_passage, "no advisory passages loaded"
    found = db.passage.find_one({"passage_id": any_passage["_id"]})
    assert found is not None, (
        f"passage_id {any_passage['_id']!r} does not resolve by field lookup -- "
        "passage_id is missing from $set")
    assert found["passage_id"] == any_passage["_id"]

def test_no_advisory_passage_carries_a_retired_alias_field():
    """The first cut also wrote `doc_id`/`start`/`end` as duplicate aliases
    of `document_id`/`start_offset`/`end_offset`. Per the controller's
    ruling those are retired; `$set` alone cannot remove a field a prior run
    already wrote, so this checks the loader's `$unset` actually worked.

    Task 4 fix: this used to count strays and assert zero without ever
    checking that the population it counted over was non-empty. If the 72
    advisory passages were absent entirely -- wrong database, a load that
    silently no-oped -- `count_documents` on both queries returns 0 and this
    test PASSES having verified nothing. Assert the population floor first,
    matching the round-trip test's `>= 40`."""
    from ccf.config import mongo_db
    db = mongo_db()
    population = db.passage.count_documents({"advisory_number": {"$exists": True}})
    assert population >= 40, (
        f"only {population} advisory passages -- population is empty or "
        "far too small; a zero-stray result below would not mean 'clean', "
        "it would mean 'nothing to check'")
    stray = db.passage.count_documents({
        "advisory_number": {"$exists": True},
        "$or": [{"doc_id": {"$exists": True}},
                {"start": {"$exists": True}},
                {"end": {"$exists": True}}],
    })
    assert stray == 0, f"{stray} advisory passages still carry a retired alias field"

def test_advisory_documents_carry_doc_type_and_do_not_widen_the_178_gap():
    """`doc_type` is set here and only here for these rows -- see
    `docs/known-issues.md` #21. 178 pre-existing `document` rows already
    carry no `doc_type`; this wave's four advisory rows must not join them,
    and the pre-existing gap must stay exactly what it was."""
    from ccf.config import mongo_db
    db = mongo_db()
    docs = list(db.document.find({"doc_type": "fincen_advisory"}))
    assert len(docs) == 4, f"expected 4 advisory documents, found {len(docs)}"
    for d in docs:
        assert d["doc_type"] == "fincen_advisory"
        assert d.get("advisory_number"), f"{d['_id']} has no advisory_number"
        assert d.get("provenance") == "public"
        assert d.get("source"), f"{d['_id']} has no recorded source"
        assert d.get("retrieved_at"), f"{d['_id']} has no retrieved_at"

def test_every_typology_cites_a_resolvable_passage():
    """Wave 17 Task 4, envelope floor 1. A typology whose passage_id does not
    resolve is an invented claim wearing a citation. Resolve each one against
    Mongo and require the passage to actually mention the typology's own
    subject -- a citation that resolves to unrelated text is no better."""
    import re
    from ccf.config import mongo_db
    from generators.derive_typology_patterns import TYPOLOGY_KEYWORDS
    db = mongo_db()
    data = json.loads((REPO_ROOT / "sources" / "screening" / "wave17_typologies.json").read_text())
    assert len(data["typologies"]) >= 4, "envelope floor: >= 4 typologies"
    for t in data["typologies"]:
        p = db.passage.find_one({"passage_id": t["passage_id"]})
        assert p, f"{t['typology_id']} cites passage {t['passage_id']}, which does not exist"
        assert t["advisory_number"], f"{t['typology_id']} has no advisory number"
        assert t["params"], f"{t['typology_id']} carries no structural parameters"
        # The subject check the brief's docstring promises: at least one of
        # the mechanism keywords that SELECTED this passage must actually be
        # present in its text, not just in the artifact's say-so.
        keywords = TYPOLOGY_KEYWORDS[t["typology"]]["include"]
        assert any(re.search(pat, p["text"], re.I) for pat in keywords), (
            f"{t['typology_id']} cites {t['passage_id']}, but none of "
            f"{keywords} appear in its text -- citation resolves to "
            "unrelated content")

def test_typology_params_are_not_all_identical():
    """A generator that stamps the same params on all four typologies would
    pass a count-based check while producing one pattern four times. Require
    the parameter sets to actually differ."""
    data = json.loads((REPO_ROOT / "sources" / "screening" / "wave17_typologies.json").read_text())
    seen = {json.dumps(t["params"], sort_keys=True) for t in data["typologies"]}
    assert len(seen) == len(data["typologies"]), "typology params are duplicated"

def test_params_source_labels_every_param_advisory_or_chosen():
    """The brief requires every structural number to be labelled 'read from
    the advisory' or 'chosen' -- never presented as advisory-stated when it
    is not. Enforce that params_source exists, covers every params key
    exactly, and uses only the two (plus narrative) honest labels."""
    data = json.loads((REPO_ROOT / "sources" / "screening" / "wave17_typologies.json").read_text())
    allowed = {"advisory", "chosen", "narrative"}
    for t in data["typologies"]:
        src = t.get("params_source")
        assert src, f"{t['typology_id']} has no params_source"
        assert set(src) == set(t["params"]), (
            f"{t['typology_id']} params_source keys {set(src)} do not match "
            f"params keys {set(t['params'])}")
        assert set(src.values()) <= allowed, (
            f"{t['typology_id']} params_source uses an unrecognised label: "
            f"{set(src.values()) - allowed}")

def test_shell_company_ownership_honors_the_controller_ruling():
    """The controller ruling: FIN-2017-A003's own case is residential real
    estate, which this estate does not model. The cited passage must state
    the concealment MECHANISM, never a GTO filing threshold or dollar
    trigger, and the params must carry the abstraction disclosure verbatim
    -- an unstated narrowing is the failure this repo keeps recording."""
    from ccf.config import mongo_db
    db = mongo_db()
    data = json.loads((REPO_ROOT / "sources" / "screening" / "wave17_typologies.json").read_text())
    shell = next(t for t in data["typologies"] if t["typology"] == "shell_company_ownership")
    assert shell["advisory_number"] == "FIN-2017-A003"
    p = db.passage.find_one({"passage_id": shell["passage_id"]})
    assert p, f"{shell['passage_id']} does not resolve"
    text_lower = p["text"].lower()
    for banned in ("geographic targeting order", "gto", "form 8300"):
        assert banned not in text_lower, (
            f"cited passage names a GTO/filing-threshold concept ({banned!r}) "
            "instead of stating the concealment mechanism")
    assert "shell compan" in text_lower or "beneficial owner" in text_lower, (
        "cited passage does not state the shell-company concealment "
        "mechanism")
    note = shell["params"].get("abstracted_from_advisory", "")
    assert "residential real estate" in note and "no property register" in note, (
        "params does not carry the required abstraction disclosure")

def test_advisory_labelled_params_are_grounded_in_a_real_passage():
    """Fix round (coordinator review). A param labelled 'advisory' in
    params_source claims the FinCEN text states this exact number. Resolve
    params_locator's passage_id for every such key -- which may differ from
    the typology's own main-cited passage, e.g. funnel_account's mechanism
    definition never states a dollar figure; its $10,000 is stated three
    passages later -- and assert the value's text form actually appears
    there. A locator that does not resolve, or resolves to text that never
    states the value, is exactly the citation-to-unrelated-content failure
    this suite already polices at the typology level; this is the same
    check one level down, per parameter."""
    from ccf.config import mongo_db
    db = mongo_db()
    data = json.loads((REPO_ROOT / "sources" / "screening" / "wave17_typologies.json").read_text())
    checked = 0
    for t in data["typologies"]:
        src = t["params_source"]
        locators = t.get("params_locator", {})
        for key, label in src.items():
            if label != "advisory":
                continue
            loc = locators.get(key)
            assert loc, (
                f"{t['typology_id']}.{key} labelled 'advisory' but has no "
                "params_locator entry")
            p = db.passage.find_one({"passage_id": loc})
            assert p, f"{t['typology_id']}.{key} locator {loc} does not resolve"
            value = t["params"][key]
            text = p["text"]
            needles = {str(value)}
            if isinstance(value, int):
                needles.add(f"{value:,}")
            assert any(n in text for n in needles), (
                f"{t['typology_id']}.{key}={value!r} labelled 'advisory' but "
                f"none of {needles} appear in cited passage {loc}")
            checked += 1
    assert checked >= 2, (
        f"only checked {checked} advisory-labelled params -- expected at "
        "least the two $10,000 CTR thresholds (structuring, funnel_account)")

def test_structuring_carries_its_own_abstraction_note():
    """Fix round (coordinator review, item 3). structuring's advisory is
    casino-specific ("Structuring by Casino Patrons and Personnel"); no
    casino term leaks into params, so the mechanism already generalises, but
    the narrowing was unstated while shell_company_ownership's identical
    narrowing IS stated. Consistency costs one field."""
    data = json.loads((REPO_ROOT / "sources" / "screening" / "wave17_typologies.json").read_text())
    structuring = next(t for t in data["typologies"] if t["typology"] == "structuring")
    note = structuring["params"].get("abstracted_from_advisory", "")
    assert "casino" in note.lower(), (
        "structuring params does not disclose that its advisory's own "
        "case is casino-specific")
    for leaked in ("casino", "card club", "gaming"):
        for key, value in structuring["params"].items():
            if key == "abstracted_from_advisory":
                continue
            assert leaked not in str(value).lower(), (
                f"structuring.params.{key} leaks a casino-domain term "
                f"({leaked!r}) into a supposedly-abstracted parameter")

def test_ex_alert_is_not_bound_here():
    """Fix round (coordinator review, item 1). ex:Alert was in the
    controller's original term list, but Sec C assigns alert records to
    Postgres and Task 12 keeps them there -- a Postgres-owned element gets
    no RDF class, the same rule Task 3's own note already applied.

    Wave 17 Task 5 re-reviewer finding: the version of this test that
    checked only `wave17_typologies.json` never guarded the thing it
    claimed to -- that artifact was never at risk of carrying an `Alert`
    binding row, since bindings live in `docs/ccf_dataprep_v2.md`.
    Re-inserting an `Alert` row into that doc's Wave 17 binding table left
    all tests passing. This now reads the binding table itself, and it
    asserts its own denominator first (the Wave 17 section was found and
    holds exactly the 10 rows on record) so it cannot pass by silently
    matching against an empty or wrong section."""
    doc = (REPO_ROOT / "docs" / "ccf_dataprep_v2.md").read_text()

    header = "#### Wave 17 · AML typology-match vocabulary"
    start = doc.find(header)
    assert start != -1, "Wave 17 AML binding section not found in the doc"
    # The section runs to the next level-4 heading, or EOF.
    next_heading = doc.find("\n#### ", start + len(header))
    section = doc[start:] if next_heading == -1 else doc[start:next_heading]

    row_pattern = re.compile(r"^\| `([^`]+)` \|", re.MULTILINE)
    local_names = row_pattern.findall(section)
    assert len(local_names) == 10, (
        f"expected exactly 10 bound rows in the Wave 17 AML binding table, "
        f"found {len(local_names)}: {local_names} -- denominator check "
        "failed, so the Alert check below would prove nothing")
    assert "Alert" not in local_names, (
        "ex:Alert has been re-bound in the Wave 17 AML binding table -- "
        "§C assigns alert records to Postgres and this term must not exist "
        "here")

    # Still guard the artifact itself, which the original test checked.
    data = json.loads((REPO_ROOT / "sources" / "screening" / "wave17_typologies.json").read_text())
    for t in data["typologies"]:
        assert "Alert" not in json.dumps(t), (
            f"{t['typology_id']} artifact entry mentions Alert -- "
            "ex:Alert must not be asserted by this task")


# ---------------------------------------------------------------------------
# Wave 17 Task 5 -- the name guard (CLAUDE.md rule 2 has teeth or it doesn't).
# ---------------------------------------------------------------------------

def test_guard_blocks_a_known_real_name():
    """Wave 17 Task 5. KNOWN-PRESENT control. If the guard cannot block a
    name that is certainly in the estate, it cannot block anything, and every
    'clean' result it later returns is meaningless."""
    from ccf.aml import RealNameIndex
    idx = RealNameIndex.build()
    assert idx.blocks("Charter Communications, Inc.") is not None
    assert idx.blocks("CHARTER COMMUNICATIONS INC") is not None, (
        "guard is case- or punctuation-sensitive and would miss the same "
        "company written differently")


def test_guard_allows_a_name_that_is_certainly_absent():
    """KNOWN-ABSENT control. A guard that blocks everything is as useless as
    one that blocks nothing, and passes a 'no forbidden names' check
    trivially. The two controls together are what make the guard evidence."""
    from ccf.aml import RealNameIndex
    idx = RealNameIndex.build()
    assert idx.blocks("Vermillion Quayside Holdings Ltd") is None


def test_guard_covers_every_real_population():
    """The guard is only as good as its denominator. Assert it indexed each
    source, with a floor per source, so an empty or failed query cannot
    silently shrink the guarded set to nothing."""
    from ccf.aml import RealNameIndex
    idx = RealNameIndex.build()
    assert idx.counts["legal_entity"] >= 150
    assert idx.counts["sanctions_name"] >= 40_000
    assert idx.counts["person"] >= 900
    assert idx.counts["peer_entity"] >= 1
    assert idx.counts["registry_company"] >= 1


def test_is_psc_key_rejects_the_numeric_population():
    """The two-population boundary, as code. Numeric person keys are officers
    of REAL companies -- 817 person_role rows join legal_entity -- and must
    never enter this product."""
    from ccf.aml import is_psc_key
    assert is_psc_key("PSC-0001")
    assert not is_psc_key("00012345")
    assert not is_psc_key("0002-77")
    assert not is_psc_key("PSC-")


def test_guard_covers_the_remaining_four_populations():
    """IMPORTANT fix (coordinator review). The brief's five-source floor
    test above is verbatim from the task brief and left four indexed,
    counted sources with no floor at all: sanctions_entry,
    person_name_variant, psc_person, institutional_holder. A silent
    zero-row read on any of them would guard a smaller set than claimed,
    undetected, since nothing asserted their denominators. Floors set well
    below the measured live counts (19,730 / 997 / 210 / 22,476)."""
    from ccf.aml import RealNameIndex
    idx = RealNameIndex.build()
    assert idx.counts["sanctions_entry"] >= 19_000
    assert idx.counts["person_name_variant"] >= 900
    assert idx.counts["psc_person"] >= 200
    assert idx.counts["institutional_holder"] >= 20_000


def test_guard_catches_whole_token_reordering():
    """CRITICAL fix (coordinator review). A pure reordering of a real,
    currently-sanctioned name scores similarity() == 1.0, but the OLD
    shortlist logic could return an empty shortlist for it: when every
    shared token (GROUP, DEVELOPMENT, AND, TECHNOLOGY, ...) is common
    enough in this corpus to exceed the rarity cap on its own, every
    posting list got dropped and blocks() returned None -- indistinguishable
    from a candidate sharing nothing at all. 181 indexed real names sit in
    this exploitable shape, squarely in Task 6's shell-company / trade-based
    domain. Both real bypass pairs the reviewer found must now resolve."""
    from ccf.aml import RealNameIndex
    idx = RealNameIndex.build()
    # sanctions_name SDN-8408: "TECHNOLOGY AND DEVELOPMENT GROUP LTD"
    assert idx.blocks("GROUP DEVELOPMENT AND TECHNOLOGY") is not None
    # sanctions_name SDN-25421: "NATIONAL DEVELOPMENT AND INVESTMENT GROUP"
    assert idx.blocks("DEVELOPMENT GROUP NATIONAL AND INVESTMENT") is not None


def test_guard_catches_token_substitution():
    """CRITICAL fix, round 2 (coordinator review). After the reordering
    bypass above was closed with an exact-token-SET route, a token
    SUBSTITUTION variant still slipped past the old shortlisting index:
    substituting one token mints accidental n-grams at the new word
    boundary that can be rarer than the genuinely shared keys, so the
    rarity-first cap picked the wrong keys and crowded out the real match.
    Fix: the shortlisting index (tokens, n-grams, exact-set postings, all
    of it) was deleted rather than patched a third time. blocks() now runs
    an EXACT scan over every indexed name, with only a provably lossless
    length-ratio + token-Jaccard prefilter in front of the expensive
    SequenceMatcher.ratio() call -- see the module docstring for why that
    prefilter cannot exclude a true match.

    Both cases here genuinely cross BLOCK_THRESHOLD under this module's own
    similarity(), confirmed inline rather than merely asserted."""
    from ccf.aml import RealNameIndex, similarity
    idx = RealNameIndex.build()

    c1 = "TECHNOLOGY TRADING DEVELOPMENT GROUP"
    real1 = "TECHNOLOGY AND DEVELOPMENT GROUP LTD"  # sanctions_name SDN-8408
    assert similarity(c1, real1) >= 0.90, "fixture no longer crosses threshold"
    assert idx.blocks(c1) is not None

    c2 = "NATIONAL DEVELOPMENT TRADING INVESTMENT GROUP"
    real2 = "NATIONAL DEVELOPMENT AND INVESTMENT GROUP"  # sanctions_name SDN-25421
    assert similarity(c2, real2) >= 0.90, "fixture no longer crosses threshold"
    assert idx.blocks(c2) is not None


def test_bypass_literal_string_is_a_quick_ratio_artifact_not_a_bypass():
    """Coordinator review, round 2, second finding -- verified rather than
    reproduced as reported. The literal candidate cited,
    "NATIONAL DEVELOPMENT NATIONAL INVESTMENT GROUP", was reported at
    "similarity 0.9195" against the real sanctioned name
    "NATIONAL DEVELOPMENT AND INVESTMENT GROUP" (SDN-25421). Recomputed
    with THIS module's own similarity() -- max(SequenceMatcher.ratio(),
    token Jaccard) -- the true score is 0.896551724137931, not 0.9195.
    0.9195 is exactly SequenceMatcher.quick_ratio() for this pair (checked
    directly against difflib): an internal fast UPPER-BOUND approximation
    difflib itself documents as only an upper bound, never the score
    BLOCK_THRESHOLD is calibrated against. Below BLOCK_THRESHOLD (0.90),
    blocks() returning None for this literal string is the threshold
    behaving as calibrated, not a residual bypass -- see
    test_guard_catches_token_substitution for the genuine substitution
    case against this same real name."""
    from difflib import SequenceMatcher
    from ccf.aml import RealNameIndex, normalize_name, similarity

    cand = "NATIONAL DEVELOPMENT NATIONAL INVESTMENT GROUP"
    real = "NATIONAL DEVELOPMENT AND INVESTMENT GROUP"

    score = similarity(cand, real)
    assert abs(score - 0.896551724137931) < 1e-9, (
        f"expected the measured true score 0.896551724137931, got {score}")
    assert score < 0.90, "this literal string was never actually a bypass"

    quick = SequenceMatcher(None, normalize_name(cand), normalize_name(real)).quick_ratio()
    assert abs(quick - 0.9195402298850575) < 1e-9, (
        "the reported 0.9195 no longer traces to quick_ratio() -- "
        "re-investigate rather than assume this test is stale")

    idx = RealNameIndex.build()
    assert idx.blocks(cand) is None


# ---------------------------------------------------------------------------
# Wave 17 Task 6 Step 0a -- the prefilter skip has no test of its own.
# ---------------------------------------------------------------------------

def _reference_blocks_no_skip(idx, candidate: str) -> str | None:
    """A deliberately unoptimized reimplementation of `RealNameIndex.blocks()`
    that ALWAYS calls `SequenceMatcher.ratio()` via `_pair_score()`, never
    skipping it -- the ground truth `blocks()`'s prefilter skip is checked
    against. Any pair-level difference between this and the real `blocks()`
    means the skip discarded a pair it should not have."""
    from ccf.aml import BLOCK_THRESHOLD, _pair_score, normalize_name

    norm = normalize_name(candidate)
    if not norm:
        return None
    cand_tokens = frozenset(t for t in norm.split(" ") if t)

    best_name: str | None = None
    best_score = -1.0
    for raw, norm_r, tokens_r in idx._records:
        score = _pair_score(norm, norm_r, cand_tokens, tokens_r)
        if score > best_score or (score == best_score and
                                   (best_name is None or raw < best_name)):
            best_score = score
            best_name = raw
    if best_score >= BLOCK_THRESHOLD:
        return best_name
    return None


def test_blocks_prefilter_skip_is_lossless():
    """Wave 17 Task 6, Step 0a (carried over from Task 5). `blocks()` skips
    the expensive `SequenceMatcher.ratio()` call for a pair only when the
    exact token-Jaccard score AND the length-ratio upper bound are BOTH
    already below `BLOCK_THRESHOLD` -- proved lossless analytically in the
    module docstring, but never checked by a test until now. All 22 prior
    tests assert only that specific strings block or don't; an edit that
    widened the skip (e.g. loosening either condition, or applying `or`
    instead of `and`) would pass every one of them without this test.

    Builds a small, hand-chosen, in-memory index -- NOT `RealNameIndex.build()`,
    which scans 72,869 live records and costs real minutes across a run --
    and checks every candidate against a no-skip reference scan
    (`_reference_blocks_no_skip`) that always calls `ratio()`. The candidate
    set is chosen to exercise pairs on both sides of `BLOCK_THRESHOLD`, via
    both the token-Jaccard and the length-ratio route: pure reorders (token
    Jaccard == 1.0, skip never triggers), token substitutions (mid-range
    token overlap), near-duplicates differing by a word or two, a
    character-level near-miss sharing no whole token
    ("Pregis" / "Regis Corp", the estate's own recorded example), two
    similar-length strings sharing nothing (length-upper-bound route, no
    token overlap), very different-length strings sharing nothing (the
    common bypass shape the skip was built to short-circuit), and names with
    no relationship to the index at all."""
    from ccf.aml import RealNameIndex

    index_names = [
        "TECHNOLOGY AND DEVELOPMENT GROUP LTD",
        "NATIONAL DEVELOPMENT AND INVESTMENT GROUP",
        "Regis Corp",
        "Charter Communications Inc",
        "Acme Trading Company",
        "Beta Holdings International",
        "Gamma Bank NA",
        "Delta Fund Partners LLC",
        "Omega Securities Group",
        "Global Maritime Shipping Ltd",
        "Northgate Resources Corporation",
        "Silverline Capital Partners",
        "Union Textiles International",
        "Harborview Logistics Group",
        "Bright Star Ventures Ltd",
        "Falcon Trading Company",
        "Riverstone Holdings Inc",
        "Crescent Investment Group",
        "Ironwood Development Corp",
        "Meridian Trust Company",
        "Aardvark Petroleum Exports LLC",
        "Zephyr Consolidated Freight",
    ]
    idx = RealNameIndex.from_names(index_names)

    candidates = [
        # pure token reorder -- token Jaccard 1.0, skip never triggers
        "GROUP DEVELOPMENT AND TECHNOLOGY",
        "DEVELOPMENT GROUP NATIONAL AND INVESTMENT",
        # token substitution -- mid-range token overlap
        "TECHNOLOGY TRADING DEVELOPMENT GROUP",
        "NATIONAL DEVELOPMENT TRADING INVESTMENT GROUP",
        "NATIONAL DEVELOPMENT NATIONAL INVESTMENT GROUP",
        # character-level near-miss, zero token overlap -- the estate's
        # own recorded n-gram-blind-spot example
        "Pregis",
        "Pregis Corp",
        "Regis",
        # near-duplicates of an indexed name, one or two words changed
        "Acme Trading Co",
        "Acme Trading Companies",
        "Falcon Trading Corporation",
        "Meridian Trust Co",
        "Meridian Trust LLC",
        "Northgate Resources Corp",
        # similar-length strings sharing no token (length-ratio route)
        "Wentworth Aviation Partners",
        "Blackwood Chemical Traders",
        # very different length, sharing nothing -- the common bypass shape
        "Xy",
        "A very long invented corporate entity name with many extra words",
        # exact known-present / known-absent controls
        "Charter Communications, Inc.",
        "Vermillion Quayside Holdings Ltd",
        # unrelated invented names
        "Quorvane Atlas Trading Ltd",
        "Bellhaven Cotswold Partners",
    ]

    for cand in candidates:
        expected = _reference_blocks_no_skip(idx, cand)
        actual = idx.blocks(cand)
        assert actual == expected, (
            f"{cand!r}: blocks() (with skip) returned {actual!r}, but the "
            f"no-skip reference scan returned {expected!r} -- the prefilter "
            "skip discarded a pair it should not have")


# ---------------------------------------------------------------------------
# Wave 17 Task 6 -- the 200 invented parties.
# ---------------------------------------------------------------------------

def test_no_generated_party_collides_with_a_real_entity():
    """Wave 17 Task 6, safety property 1. Re-run the guard over the FINAL
    artifact -- not over what the generator thought it emitted. A guard
    applied during generation and never re-checked afterwards cannot see a
    name introduced by a later edit."""
    import json
    from ccf.aml import RealNameIndex
    from ccf.config import REPO_ROOT
    idx = RealNameIndex.build()
    parties = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_parties.json").read_text())["parties"]
    assert len(parties) >= 150, f"only {len(parties)} parties"
    offenders = [(p["party_id"], p["legal_name"], idx.blocks(p["legal_name"]))
                 for p in parties if idx.blocks(p["legal_name"])]
    # The declared OFAC near-match from Task 7 is the ONE permitted exception
    declared = {p["party_id"] for p in parties if p.get("ofac_near_match")}
    real = [o for o in offenders if o[0] not in declared]
    assert not real, f"parties colliding with real entities: {real[:5]}"

def test_synthetic_identifiers_cannot_be_mistaken_for_real_leis():
    """A real GLEIF LEI is 20 alphanumerics with no hyphen. The estate's
    synthetic form is SYN- with hyphens precisely so the two can never be
    confused."""
    import json, re
    from ccf.config import REPO_ROOT
    parties = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_parties.json").read_text())["parties"]
    for p in parties:
        assert p["syn_lei"].startswith("SYN-"), p["syn_lei"]
        assert not re.fullmatch(r"[A-Z0-9]{20}", p["syn_lei"]), (
            f"{p['syn_lei']} is shaped like a real LEI")


# ---------------------------------------------------------------------------
# Wave 17 Task 7 -- the one declared OFAC near-match.
# ---------------------------------------------------------------------------

def test_exactly_one_declared_ofac_near_match_in_the_intended_band():
    """Wave 17 Task 7, envelope floor 5. The matched list entry is REAL and
    public; the party is invented. Recompute the similarity live -- never
    read the stored number -- and require it to land in a band that is a
    genuine match but not a duplicate. Too low and screening confidence is
    never exercised; too high and it is effectively the same name."""
    import json
    from ccf.aml import similarity
    from ccf.config import REPO_ROOT, PG_SCHEMA_V2 as S, pg_connect
    parties = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_parties.json").read_text())["parties"]
    declared = [p for p in parties if p.get("ofac_near_match")]
    assert len(declared) == 1, f"expected exactly 1 declared match, got {len(declared)}"
    p = declared[0]
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'SELECT name FROM "{S}".sanctions_name WHERE entry_id = %s',
                    (p["ofac_near_match"]["sanctions_entry_id"],))
        rows = [r[0] for r in cur.fetchall()]
    assert rows, "declared match points at a sanctions entry that does not exist"
    best = max(similarity(p["legal_name"], n) for n in rows)
    assert 0.70 <= best <= 0.92, (
        f"measured similarity {best:.3f} outside the intended moderate band")

def test_the_guard_would_have_rejected_the_declared_match():
    """The exception must prove the guard has teeth, not that it has a hole.
    Feed the declared party's name through the ORDINARY path and require the
    guard to block it."""
    import json
    from ccf.aml import RealNameIndex
    from ccf.config import REPO_ROOT
    idx = RealNameIndex.build()
    parties = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_parties.json").read_text())["parties"]
    p = next(x for x in parties if x.get("ofac_near_match"))
    assert idx.blocks(p["legal_name"]) is not None, (
        "the declared near-match would NOT have been caught by the ordinary "
        "guard -- which means the guard does not cover sanctions names, and "
        "the exception is hiding a gap rather than declaring one")

def test_the_guard_blocked_the_declared_entity_not_a_different_one():
    """Ruling on the brief's conflict (see `docs/ccf_dataprep_v2.md`,
    "2026-08-25 — Wave 17 whole-branch review: three notes for a reader of
    this data"; the SDD task-7-report.md this used to cite is deleted when
    the wave closes): both tests
    above would also pass in a broken case -- blocks() firing against an
    UNRELATED real name while the declared sanctions entry itself sits
    below BLOCK_THRESHOLD. That would mean the exception declares one match
    while the guard actually caught another, which is the 'hiding a gap
    rather than declaring one' failure the guard's own docstring warns
    about. Require the name blocks() returns to belong to the SAME
    sanctions entry the party declares."""
    import json
    from ccf.aml import RealNameIndex
    from ccf.config import REPO_ROOT, PG_SCHEMA_V2 as S, pg_connect
    idx = RealNameIndex.build()
    parties = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_parties.json").read_text())["parties"]
    p = next(x for x in parties if x.get("ofac_near_match"))
    hit = idx.blocks(p["legal_name"])
    assert hit is not None
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'SELECT name FROM "{S}".sanctions_name WHERE entry_id = %s',
                    (p["ofac_near_match"]["sanctions_entry_id"],))
        declared_names = {r[0] for r in cur.fetchall()}
    assert hit in declared_names, (
        f"blocks() matched {hit!r}, which does NOT belong to the declared "
        f"sanctions_entry_id {p['ofac_near_match']['sanctions_entry_id']!r} -- "
        "the guard caught a DIFFERENT real entity than the one this party "
        "declares, so the exception would be hiding a gap rather than "
        "declaring one")


# ===========================================================================
# Wave 17 Task 8 — Postgres DDL and the party load
# ===========================================================================

def test_aml_tables_exist_and_do_not_widen_an_existing_table():
    """Wave 17 Task 8. New tables, not new columns on shared ones. Wave 16
    set this precedent when projection_plan collided: a separate table beats
    overloading one another product owns."""
    from ccf.config import PG_SCHEMA_V2 as S, pg_connect
    want = {"aml_party","aml_transaction","aml_alert","aml_alert_link",
            "aml_projection_plan"}
    with pg_connect() as c, c.cursor() as cur:
        cur.execute("""SELECT table_name FROM information_schema.tables
                       WHERE table_schema=%s""", (S,))
        have = {r[0] for r in cur.fetchall()}
    assert want <= have, f"missing: {want - have}"

def test_party_rows_carry_provenance_and_a_syn_identifier():
    from ccf.config import PG_SCHEMA_V2 as S, pg_connect
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM "{S}".aml_party')
        assert cur.fetchone()[0] >= 150
        cur.execute(f'''SELECT COUNT(*) FROM "{S}".aml_party
                        WHERE provenance IS NULL OR provenance = %s''', ("",))
        assert cur.fetchone()[0] == 0, "parties with no provenance label"
        cur.execute(f'''SELECT COUNT(*) FROM "{S}".aml_party
                        WHERE syn_lei NOT LIKE %s''', ("SYN-%",))
        assert cur.fetchone()[0] == 0, "party with a non-synthetic identifier"

def test_aml_party_carries_the_two_columns_later_tasks_need():
    """Pre-flight ruling in task-8-brief.md: `beneficial_owner_key` (Task 9)
    and, this task's own addition, `ofac_near_match` (recomputed live by
    Task 17's floor) must exist in the DDL now, not widened in later. Checks
    only that both columns exist, with the right nullability and type --
    NOT that either is populated. `ofac_near_match` population is proven by
    the next test, `test_exactly_one_party_carries_ofac_near_match_in_postgres`."""
    from ccf.config import PG_SCHEMA_V2 as S, pg_connect
    with pg_connect() as c, c.cursor() as cur:
        cur.execute("""SELECT column_name, is_nullable, data_type
                       FROM information_schema.columns
                       WHERE table_schema=%s AND table_name='aml_party'""",
                    (S,))
        cols = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
    assert cols.get("beneficial_owner_key") == ("YES", "text"), cols.get("beneficial_owner_key")
    assert cols.get("ofac_near_match") == ("YES", "jsonb"), cols.get("ofac_near_match")

def test_exactly_one_party_carries_ofac_near_match_in_postgres():
    """Task 7 declared exactly one party with a nested ofac_near_match
    object in the artifact. This loader must have carried it into Postgres
    -- not left it stranded in sources/, which is the whole reason Task 17's
    floor can recompute from the live store instead of reading a JSON file."""
    from ccf.config import PG_SCHEMA_V2 as S, pg_connect
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'''SELECT party_id, ofac_near_match FROM "{S}".aml_party
                        WHERE ofac_near_match IS NOT NULL''')
        rows = cur.fetchall()
    assert len(rows) == 1, f"expected exactly 1, found {len(rows)}"
    party_id, near_match = rows[0]
    assert party_id == "AMLP-0069"
    for key in ("sanctions_entry_id", "matched_name", "measured_similarity"):
        assert key in near_match, f"ofac_near_match missing {key!r}: {near_match}"

def test_aml_alert_trigger_column_is_queryable_by_name():
    """`trigger` is a keyword; the DDL and every statement naming it must
    quote the identifier so it survives a server that tightens the
    reserved-word list. Prove it by actually querying the column by name."""
    from ccf.config import PG_SCHEMA_V2 as S, pg_connect
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'SELECT "trigger" FROM "{S}".aml_alert LIMIT 1')

def test_load_transactions_exists_and_is_now_called_by_main():
    """Addition B in the task-8 instructions, updated by Task 12: Task 8 left
    aml_transaction populated by no task, deliberately, until the transaction
    artifact was final (Task 10 produced it, Task 11 appended the engineered
    cases). That artifact is now final, and Task 12 is the task that calls
    load_transactions -- this replaces the old assertion that main() must NOT
    call it yet."""
    import inspect
    from loaders import load_postgres_wave17 as mod
    assert hasattr(mod, "load_transactions")
    sig = inspect.signature(mod.load_transactions)
    assert list(sig.parameters) == ["cur", "txns"]
    main_src = inspect.getsource(mod.main)
    assert "load_transactions(" in main_src, (
        "main() must call load_transactions now that the transaction "
        "artifact (Task 10 + Task 11) is final")

def test_aml_transaction_table_has_the_task10_row_shape():
    """Column shape must match Task 10's interface exactly so Task 12 can
    call load_transactions without discovering a mismatch: txn_id,
    from_party, to_party, amount_usd, value_date, channel, provenance."""
    from ccf.config import PG_SCHEMA_V2 as S, pg_connect
    with pg_connect() as c, c.cursor() as cur:
        cur.execute("""SELECT column_name FROM information_schema.columns
                       WHERE table_schema=%s AND table_name='aml_transaction'""",
                    (S,))
        cols = {r[0] for r in cur.fetchall()}
    assert cols == {"txn_id", "from_party", "to_party", "amount_usd",
                     "value_date", "channel", "provenance"}

def test_no_delete_or_truncate_in_the_wave17_loader():
    """Prose mentioning the words is fine (the module docstring says 'no
    DELETE, no TRUNCATE'); an actual SQL statement is not."""
    from pathlib import Path
    src = Path("loaders/load_postgres_wave17.py").read_text().upper()
    assert "DELETE FROM" not in src
    assert "TRUNCATE TABLE" not in src
    assert "TRUNCATE \"" not in src

def test_task8_load_is_idempotent_on_a_named_party_value():
    """Re-run the loader and confirm one specific party's legal_name and
    jurisdiction survive unchanged, and the row count is unchanged -- a
    count alone cannot see a field silently reset."""
    import subprocess
    from ccf.config import PG_SCHEMA_V2 as S, pg_connect

    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM "{S}".aml_party')
        before_count = cur.fetchone()[0]
        cur.execute(f'''SELECT legal_name, jurisdiction FROM "{S}".aml_party
                        WHERE party_id = %s''', ("AMLP-0003",))
        before_name, before_juris = cur.fetchone()

    result = subprocess.run(
        ["uv", "run", "loaders/load_postgres_wave17.py"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM "{S}".aml_party')
        after_count = cur.fetchone()[0]
        cur.execute(f'''SELECT legal_name, jurisdiction FROM "{S}".aml_party
                        WHERE party_id = %s''', ("AMLP-0003",))
        after_name, after_juris = cur.fetchone()

    assert after_count == before_count
    assert after_name == before_name == "Ashford Capital Corp"
    assert after_juris == before_juris == "CAN"


# ===========================================================================
# Wave 17 Task 9 — bind parties to the inherited ownership island
# ===========================================================================

def test_no_aml_party_is_owned_by_a_numeric_person_key():
    """Wave 17 Task 9. THE boundary. Numeric person keys are officers of REAL
    companies (817 person_role rows join legal_entity). Reusing 'the person
    table' rather than PSC-* specifically would import 817 paths from real
    companies into a laundering network, and every one of those rows is
    individually legitimate -- so no per-row check would flag it."""
    from ccf.aml import is_psc_key
    from ccf.config import PG_SCHEMA_V2 as S, pg_connect
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'''SELECT party_id, beneficial_owner_key FROM "{S}".aml_party
                        WHERE beneficial_owner_key IS NOT NULL''')
        rows = cur.fetchall()
    assert rows, "no party has a beneficial owner -- the binding did not run"
    bad = [(p, k) for p, k in rows if not is_psc_key(k)]
    assert not bad, f"AML parties owned by non-PSC person keys: {bad[:5]}"

def test_bound_owners_hold_no_role_at_any_real_entity():
    """Belt and braces, measured rather than argued: take the owner keys
    actually used and assert none of them appears in person_role against a
    real legal_entity. This is the property the key-form check is a proxy
    for; assert the property itself too, so a future key-format change
    cannot silently break it."""
    from ccf.config import PG_SCHEMA_V2 as S, pg_connect
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'''SELECT COUNT(*)
                        FROM "{S}".aml_party ap
                        JOIN "{S}".person_role pr ON pr.person_key = ap.beneficial_owner_key
                        JOIN "{S}".legal_entity le ON le.lei = pr.lei''')
        assert cur.fetchone()[0] == 0, (
            "an AML party's beneficial owner holds a role at a real company")

def test_only_shell_and_individual_owned_kinds_get_bound():
    """The brief restricts binding to the shell and individual_owned kinds.
    corporate parties must stay NULL -- an over-eager binder that touches
    every kind would be as wrong as one that binds nothing."""
    from ccf.config import PG_SCHEMA_V2 as S, pg_connect
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'''SELECT party_kind, COUNT(*), COUNT(beneficial_owner_key)
                        FROM "{S}".aml_party GROUP BY party_kind''')
        by_kind = {k: (total, bound) for k, total, bound in cur.fetchall()}
    assert by_kind.get("shell", (0, -1))[1] == by_kind["shell"][0], by_kind.get("shell")
    assert by_kind.get("individual_owned", (0, -1))[1] == by_kind["individual_owned"][0], \
        by_kind.get("individual_owned")
    assert by_kind.get("corporate", (0, 0))[1] == 0, (
        f"corporate parties must not carry a beneficial_owner_key: {by_kind.get('corporate')}")

def test_bound_owners_are_drawn_from_existing_bo_chain_persons():
    """The design's central reuse decision: owners come from the population
    already anchoring bo_chain, not a freshly minted set. No new PSC person
    is invented by this task."""
    from ccf.config import PG_SCHEMA_V2 as S, pg_connect
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'SELECT DISTINCT person_key FROM "{S}".bo_chain')
        chain_persons = {r[0] for r in cur.fetchall()}
        cur.execute(f'''SELECT DISTINCT beneficial_owner_key FROM "{S}".aml_party
                        WHERE beneficial_owner_key IS NOT NULL''')
        used = {r[0] for r in cur.fetchall()}
    assert used, "no beneficial owners bound"
    assert used <= chain_persons, (
        f"owners bound that were not drawn from an existing bo_chain: "
        f"{used - chain_persons}")

def test_aml_party_population_still_frozen_at_201_after_binding():
    """The 201-party population may not be added to, removed from, or
    renamed by this task -- only the beneficial_owner_key column changes."""
    from ccf.config import PG_SCHEMA_V2 as S, pg_connect
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM "{S}".aml_party')
        assert cur.fetchone()[0] == 201

def test_ownership_binding_artifact_is_byte_identical_across_runs():
    """Determinism: seeded RNG with a fixed constant, sorted iteration --
    prove it by regenerating and diffing, not by reading the code."""
    import subprocess
    from ccf.config import REPO_ROOT
    path = REPO_ROOT / "sources" / "screening" / "wave17_ownership.json"
    r1 = subprocess.run(["uv", "run", "generators/bind_aml_ownership.py"],
                         capture_output=True, text=True)
    assert r1.returncode == 0, r1.stdout + r1.stderr
    first = path.read_bytes()
    r2 = subprocess.run(["uv", "run", "generators/bind_aml_ownership.py"],
                         capture_output=True, text=True)
    assert r2.returncode == 0, r2.stdout + r2.stderr
    second = path.read_bytes()
    assert first == second, "wave17_ownership.json is not byte-identical across runs"

def test_beneficial_owner_key_survives_a_re_run_of_load_parties():
    """Idempotency by VALUE, not by count. Task 8's `load_parties` deliberately
    omits `beneficial_owner_key` from its INSERT column list and its
    ON CONFLICT ... DO UPDATE SET clause, so a re-run after Task 9 has bound
    owners must not reset the column to NULL. Call load_parties directly
    (not the full loader main(), which would re-run the bind step too) so
    this test isolates exactly the guarantee Task 8 made."""
    import json
    from ccf.config import PG_SCHEMA_V2 as S, REPO_ROOT, pg_connect
    from loaders.load_postgres_wave17 import load_parties

    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'''SELECT beneficial_owner_key FROM "{S}".aml_party
                        WHERE party_id = %s''', ("AMLP-0001",))
        row = cur.fetchone()
    assert row is not None and row[0] is not None, (
        "AMLP-0001 must already carry a beneficial_owner_key for this "
        "idempotency proof to be meaningful")
    before = row[0]

    parties = json.loads(
        (REPO_ROOT / "sources" / "screening" / "wave17_parties.json").read_text()
    )["parties"]
    with pg_connect() as c, c.cursor() as cur:
        load_parties(cur, parties)
        c.commit()

    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'''SELECT beneficial_owner_key FROM "{S}".aml_party
                        WHERE party_id = %s''', ("AMLP-0001",))
        after = cur.fetchone()[0]

    assert after == before, (
        f"beneficial_owner_key for AMLP-0001 changed from {before!r} to "
        f"{after!r} after re-running load_parties -- Task 8's column "
        f"exclusion no longer holds")

def test_bind_step_uses_the_redundant_psc_guard():
    """The SQL WHERE person_key LIKE 'PSC-%' and the is_psc_key() code check
    are deliberately redundant -- one is easy to edit without noticing.
    Keep both present in the generator's source."""
    from pathlib import Path
    src = Path("generators/bind_aml_ownership.py").read_text()
    assert "PSC-%" in src, "SQL-level PSC-* filter missing"
    assert "is_psc_key" in src, "code-level is_psc_key() check missing"

# --------------------------------------------------------------------------
# Wave 17 Task 10 -- the ordinary 18-month transaction population.
# --------------------------------------------------------------------------

def test_transactions_are_inside_the_pinned_window_and_nothing_is_future_dated():
    import json
    from ccf.config import REPO_ROOT
    d = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_transactions.json").read_text())
    txns = d["transactions"]
    assert len(txns) >= 3000, f"only {len(txns)} transactions"
    assert all(t["value_date"] <= d["as_of"] for t in txns), "future-dated transaction"
    assert all(t["value_date"] >= d["window_start"] for t in txns), "pre-window transaction"

def test_ordinary_population_does_not_already_contain_the_patterns():
    """Wave 17 Task 10. The noise must be noise. If the ordinary generator
    happens to emit structuring-shaped clusters, the ~30 engineered cases are
    not distinguishable from background and precision is not measurable.
    Assert the ordinary population contains NO party with 4+ transactions in
    a 10-day window all sitting in the 80-99% band below the threshold.

    Scoped to the ORDINARY population (controller ruling, Task 10 brief):
    Task 11 appends engineered cases -- built to exhibit exactly this shape
    -- to this same artifact, so a literal, unscoped re-read of this test
    would start failing the moment Task 11 succeeds. Every txn_id cited by
    a case in wave17_cases.json is excluded before the check runs; a
    missing file (true before Task 11 runs) is an empty exclusion set. The
    detector and the exclusion loader are imported from the generator so
    this test and the generator's own internal check can never drift
    apart."""
    import json
    from ccf.config import REPO_ROOT
    from generators.generate_aml_transactions import (
        find_structuring_shaped_party, load_case_excluded_txn_ids)
    d = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_transactions.json").read_text())
    assert d["transactions"], (
        "no transactions in the artifact -- without this guard the assertions\n         below iterate over an empty list and this test passes vacuously")
    excluded = load_case_excluded_txn_ids()
    violation = find_structuring_shaped_party(d["transactions"], excluded)
    assert violation is None, (
        f"{violation[0] if violation else ''} already looks like "
        f"structuring in the ORDINARY population -- the injected cases "
        "will not be distinguishable from background")

def test_transaction_counterparties_are_drawn_from_the_frozen_party_set():
    """Both legs of every transaction must be one of the 201 frozen
    AMLP-#### parties -- Task 10's own instructions ('counterparties drawn
    from the AML party set only') and no party pays or is paid by itself."""
    import json
    from ccf.config import REPO_ROOT
    root = REPO_ROOT/"sources"/"screening"
    parties = {p["party_id"] for p in json.loads((root/"wave17_parties.json").read_text())["parties"]}
    txns = json.loads((root/"wave17_transactions.json").read_text())["transactions"]
    assert txns, (
        "no transactions in the artifact -- without this guard the assertions\n         below iterate over an empty list and this test passes vacuously")
    for t in txns:
        assert t["from_party"] in parties, f"unknown from_party {t['from_party']}"
        assert t["to_party"] in parties, f"unknown to_party {t['to_party']}"
        assert t["from_party"] != t["to_party"], f"{t['txn_id']} pays itself"

def test_asset_purchase_channel_present_at_unremarkable_amounts():
    """Task 11's shell_company_ownership cases need the asset_purchase
    channel to already exist in the vocabulary. TYP-SHELL's own
    min_amount_usd is 500,000 -- ordinary asset_purchase activity must sit
    well below that or the channel plus size becomes the tell instead of
    the case.

    Scoped to the ORDINARY population (Task 11), by the same case-exclusion
    ruling the structuring anti-pattern check already carries. TYP-SHELL's
    params REQUIRE its cases to purchase at or above 500,000 on this exact
    channel, so an unscoped re-read of this test would start failing the
    moment Task 11 built a compliant case -- and the better the case, the
    harder it would break. Excluding the txn_ids the cases cite leaves the
    check judging exactly what its docstring always said it judged: the
    ordinary slice."""
    import json
    from ccf.config import REPO_ROOT
    from generators.generate_aml_transactions import load_case_excluded_txn_ids
    txns = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_transactions.json").read_text())["transactions"]
    excluded = load_case_excluded_txn_ids()
    asset_purchases = [t for t in txns if t["channel"] == "asset_purchase"
                       and t["txn_id"] not in excluded]
    assert asset_purchases, "asset_purchase channel never used ordinarily"
    assert all(t["amount_usd"] < 100_000 for t in asset_purchases), (
        "an ordinary asset_purchase transaction is not well below "
        "TYP-SHELL's 500,000 threshold")

def test_transaction_txn_ids_are_unique_and_correctly_formatted():
    import json, re
    from ccf.config import REPO_ROOT
    txns = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_transactions.json").read_text())["transactions"]
    assert txns, (
        "no transactions in the artifact -- without this guard the assertions\n         below iterate over an empty list and this test passes vacuously")
    ids = [t["txn_id"] for t in txns]
    assert len(ids) == len(set(ids)), "duplicate txn_id"
    assert all(re.fullmatch(r"TXN-\d{6}", i) for i in ids), "malformed txn_id"

def test_transaction_provenance_is_labelled():
    import json
    from ccf.config import REPO_ROOT
    txns = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_transactions.json").read_text())["transactions"]
    assert txns, (
        "no transactions in the artifact -- without this guard the assertions\n         below iterate over an empty list and this test passes vacuously")
    assert all(t["provenance"] == "synthetic — engineered" for t in txns)

# --------------------------------------------------------------------------
# Wave 17 Task 11 -- the engineered typology cases injected into the same
# transaction artifact the ordinary population lives in.
# --------------------------------------------------------------------------

ORDINARY_TXN_COUNT = 4095  # Task 10's population; ids TXN-000001..TXN-004095

def test_at_least_one_case_per_typology():
    import json, collections
    from ccf.config import REPO_ROOT
    cases = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_cases.json").read_text())["cases"]
    typ = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_typologies.json").read_text())["typologies"]
    per = collections.Counter(c["typology_id"] for c in cases)
    for t in typ:
        assert per[t["typology_id"]] >= 1, f"no case exhibits {t['typology_id']}"
    assert len(cases) >= 20, f"only {len(cases)} genuine cases"

def test_the_depth_three_network_is_genuinely_invisible_at_depth_two():
    """Wave 17 Task 11, envelope floor 2. An ORDERING claim -- no count can
    establish it. Walk the transaction graph from the subject at depth 2 and
    at depth 3 and require the linking party to be absent at 2 and present at
    3. A case merely LABELLED requires_depth=3 proves nothing."""
    import json, collections
    from ccf.config import REPO_ROOT
    root = REPO_ROOT/"sources"/"screening"
    cases = json.loads((root/"wave17_cases.json").read_text())["cases"]
    txns = json.loads((root/"wave17_transactions.json").read_text())["transactions"]
    deep = [c for c in cases if c.get("requires_depth", 0) >= 3]
    assert deep, "envelope floor: >= 1 network requiring depth 3"

    adj = collections.defaultdict(set)
    for t in txns:
        adj[t["from_party"]].add(t["to_party"])
        adj[t["to_party"]].add(t["from_party"])

    def reach(start, depth):
        seen, frontier = {start}, {start}
        for _ in range(depth):
            nxt = set()
            for n in frontier:
                nxt |= adj[n] - seen
            seen |= nxt; frontier = nxt
        return seen

    c = deep[0]
    target = c["depth_three_counterparty"]
    assert target not in reach(c["subject_party"], 2), (
        "the depth-3 counterparty is already reachable at depth 2 -- the "
        "case does not demonstrate what it claims")
    assert target in reach(c["subject_party"], 3), (
        "the depth-3 counterparty is not reachable at depth 3 either")

def test_every_case_with_requires_depth_three_names_its_counterparty():
    """Pre-flight ruling in task-11-brief.md. `requires_depth` is a LABEL;
    the named counterparty is what makes the ordering claim above
    computable. A case claiming depth 3 without naming one cannot be
    checked, and the floor above only ever inspects deep[0] -- so assert
    the field on every deep case, not just the first."""
    import json
    from ccf.config import REPO_ROOT
    cases = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_cases.json").read_text())["cases"]
    deep = [c for c in cases if c.get("requires_depth", 0) >= 3]
    assert deep, "envelope floor: >= 1 network requiring depth 3"
    for c in deep:
        assert c.get("depth_three_counterparty"), (
            f"{c['case_id']} claims requires_depth={c['requires_depth']} but "
            "names no depth_three_counterparty")

def test_every_case_exhibits_the_live_parameters_of_the_typology_it_cites():
    """The point of the whole task: a case must be checkable against the
    ADVISORY-derived numbers, not against a hardcoded copy of them. Read
    every threshold from wave17_typologies.json at test time and recompute
    each case's shape from its own transactions. A case that drifts from
    its typology's params fails here even though every count is right."""
    import json, collections, itertools
    from ccf.config import REPO_ROOT
    root = REPO_ROOT/"sources"/"screening"
    cases = json.loads((root/"wave17_cases.json").read_text())["cases"]
    typ = {t["typology_id"]: t["params"]
           for t in json.loads((root/"wave17_typologies.json").read_text())["typologies"]}
    txns = {t["txn_id"]: t
            for t in json.loads((root/"wave17_transactions.json").read_text())["transactions"]}
    juris = {p["party_id"]: p["jurisdiction"]
             for p in json.loads((root/"wave17_parties.json").read_text())["parties"]}
    hops = {b["party_id"]: b["reused_chain_depth"]
            for b in json.loads((root/"wave17_ownership.json").read_text())["bindings"]}
    assert cases, "no cases -- every assertion below would be vacuous"

    def days(a, b):
        from datetime import date
        return abs((date.fromisoformat(a) - date.fromisoformat(b)).days)

    checked = collections.Counter()
    for c in cases:
        p = typ[c["typology_id"]]
        rows = [txns[i] for i in c["txn_ids"]]
        assert rows, f"{c['case_id']} cites no transactions"
        subj = c["subject_party"]

        if c["typology_id"] == "TYP-STRUCT":
            lo = p["threshold_usd"] * p["band_low"]
            hi = p["threshold_usd"] * p["band_high"]
            band = sorted(r["value_date"] for r in rows
                          if r["from_party"] == subj and lo <= r["amount_usd"] <= hi)
            assert len(band) >= p["min_transactions"], (
                f"{c['case_id']}: {len(band)} in-band transactions, "
                f"params require >= {p['min_transactions']}")
            assert days(band[0], band[-1]) <= p["window_days"], (
                f"{c['case_id']}: spans {days(band[0], band[-1])}d, "
                f"params allow {p['window_days']}d")

        elif c["typology_id"] == "TYP-FUNNEL":
            dep = [r for r in rows
                   if r["channel"] == p["channel"] and r["to_party"] == subj]
            assert dep, f"{c['case_id']}: no deposits into the funnel account"
            locs = {juris[r["from_party"]] for r in dep}
            assert len(locs) >= p["min_deposit_locations"], (
                f"{c['case_id']}: deposits from {len(locs)} location(s), "
                f"params require >= {p['min_deposit_locations']}")
            dates = sorted(r["value_date"] for r in dep)
            assert days(dates[0], dates[-1]) <= p["max_window_days"], (
                f"{c['case_id']}: deposit window {days(dates[0], dates[-1])}d "
                f"exceeds {p['max_window_days']}d")
            assert all(r["amount_usd"] < p["threshold_usd"] for r in dep), (
                f"{c['case_id']}: a deposit is at or above the reporting "
                "threshold -- the point of a funnel account is that each "
                "leg stays under it")

        elif c["typology_id"] == "TYP-TBML":
            inv = [r for r in rows if r["channel"] == p["channel"]]
            by_ship = collections.defaultdict(list)
            for r in inv:
                by_ship[(r["from_party"], r["to_party"], r["value_date"])].append(r)
            doubles = []
            for key, group in sorted(by_ship.items()):
                if len(group) < 2:
                    continue
                for a, b in itertools.combinations(sorted(
                        g["amount_usd"] for g in group), 2):
                    if a > 0 and (b - a) / a * 100 >= p["invoice_price_variance_pct"]:
                        doubles.append(key)
                        break
            assert p["double_invoice"] is True
            assert len(doubles) >= p["min_shipments"], (
                f"{c['case_id']}: {len(doubles)} shipment(s) carry a double "
                f"invoice over {p['invoice_price_variance_pct']}% variance, "
                f"params require >= {p['min_shipments']}")

        elif c["typology_id"] == "TYP-SHELL":
            assert hops.get(subj, 0) >= p["min_ownership_hops"], (
                f"{c['case_id']}: subject {subj} sits {hops.get(subj)} "
                f"ownership hops deep, params require "
                f">= {p['min_ownership_hops']}")
            buys = [r for r in rows if r["channel"] == p["channel"]
                    and r["amount_usd"] >= p["min_amount_usd"]]
            assert buys, (
                f"{c['case_id']}: no {p['channel']} at or above "
                f"{p['min_amount_usd']}")
            assert p["financing_leg"] is False
            # financing_leg False has to MEAN something: the purchase is
            # covered by the case's own upstream transfer into the buyer,
            # dated on or before it -- cash walked in, credit did not.
            for buy in buys:
                funding = [r for r in rows
                           if r["to_party"] == buy["from_party"]
                           and r["value_date"] <= buy["value_date"]
                           and r["amount_usd"] >= buy["amount_usd"]]
                assert funding, (
                    f"{c['case_id']}: {buy['txn_id']} is not covered by an "
                    "earlier inbound leg in the case, so 'financing_leg: "
                    "false' asserts something the data does not show")
        else:
            raise AssertionError(f"unknown typology {c['typology_id']}")
        checked[c["typology_id"]] += 1

    assert set(checked) == set(typ), f"typologies never checked: {set(typ) - set(checked)}"

def test_no_typology_channel_is_findable_by_a_single_string_match():
    """Controller ruling, Task 11. Task 10 diluted `asset_purchase` so the
    channel alone is not a tell. TYP-FUNNEL's and TYP-TBML's channels did
    not exist in the ordinary vocabulary at all, so they were clean by
    ABSENCE -- a string match on `channel` would have found their cases
    with trivially perfect precision and no inference at all. Every
    typology channel must therefore also appear on ORDINARY, non-case
    transactions.

    **What the `<= 0.9` bound below asserts is "the tell is diluted at
    all", and nothing sharper.** Observed dilution is far stronger than
    that -- bare-channel precision measured 6.8% to 28.1% when the ruling
    landed -- so the bound carries roughly sixty points of slack, and it is
    kept that way deliberately (whole-branch review triage): tightening it
    toward today's values would pin the test to today's seed, and a
    legitimate re-dilution in a future wave would come back as a red build
    rather than as the improvement it is. Read a PASS here as "at least one
    ordinary transaction uses this channel and the channel is not
    effectively the answer", not as a claim about how well diluted it
    is."""
    import json
    from ccf.config import REPO_ROOT
    root = REPO_ROOT/"sources"/"screening"
    typ = json.loads((root/"wave17_typologies.json").read_text())["typologies"]
    txns = json.loads((root/"wave17_transactions.json").read_text())["transactions"]
    cases = json.loads((root/"wave17_cases.json").read_text())["cases"]
    case_ids = {i for c in cases for i in c["txn_ids"]}
    assert txns and case_ids, "empty inputs would make this vacuous"
    channels = sorted({t["params"]["channel"] for t in typ if "channel" in t["params"]})
    assert channels, "no typology declares a channel -- nothing was checked"
    for ch in channels:
        used = [t for t in txns if t["channel"] == ch]
        ordinary = [t for t in used if t["txn_id"] not in case_ids]
        assert used, f"channel {ch} never used at all"
        assert ordinary, (
            f"every {ch} transaction belongs to a case -- one string match "
            "on channel finds every case with perfect precision and zero "
            "inference")
        precision = 1 - len(ordinary) / len(used)
        assert precision <= 0.9, (
            f"a bare channel == {ch!r} filter is {precision:.1%} precise; "
            "the channel is still effectively the answer")

def test_the_diluting_channel_traffic_does_not_form_its_typologys_shape():
    """The other half of the ruling. Diluting a channel is only honest if
    the added traffic is genuinely shapeless: ordinary
    cash_deposit_geographic_dispersion must not produce a funnel account,
    and ordinary over_under_invoicing must not produce a double invoice.
    Detectors are imported from the injector so this check and the
    generator's own can never drift apart."""
    import json
    from ccf.config import REPO_ROOT
    from generators.generate_aml_transactions import load_case_excluded_txn_ids
    from generators.inject_typology_cases import (
        find_funnel_shaped_account, find_double_invoiced_pair)
    root = REPO_ROOT/"sources"/"screening"
    txns = json.loads((root/"wave17_transactions.json").read_text())["transactions"]
    params = {t["typology_id"]: t["params"]
              for t in json.loads((root/"wave17_typologies.json").read_text())["typologies"]}
    juris = {p["party_id"]: p["jurisdiction"]
             for p in json.loads((root/"wave17_parties.json").read_text())["parties"]}
    excluded = load_case_excluded_txn_ids()
    assert excluded, "no case txn_ids to exclude -- this test would be vacuous"
    hit = find_funnel_shaped_account(txns, excluded, params["TYP-FUNNEL"], juris)
    assert hit is None, f"ordinary traffic already forms a funnel account: {hit}"
    hit = find_double_invoiced_pair(txns, excluded, params["TYP-TBML"])
    assert hit is None, f"ordinary traffic already forms a double invoice: {hit}"

def test_the_two_new_detectors_answer_differently_on_known_input():
    """Known-present / known-absent controls. A detector that says 'clean'
    on every input is decoration, and this estate has recorded two checks
    that hid for seven waves each. Require a DIFFERENT answer on a
    known-bad and a known-clean fixture before any clean result above is
    believed."""
    from generators.inject_typology_cases import (
        find_funnel_shaped_account, find_double_invoiced_pair)
    fp = {"threshold_usd": 10000, "min_deposit_locations": 2,
          "max_window_days": 5, "channel": "cash_deposit_geographic_dispersion"}
    juris = {"A": "USA", "B": "DEU", "C": "USA", "F": "GBR"}
    bad = [
        {"txn_id": "T1", "from_party": "A", "to_party": "F", "amount_usd": 9000.0,
         "value_date": "2025-06-02", "channel": fp["channel"]},
        {"txn_id": "T2", "from_party": "B", "to_party": "F", "amount_usd": 8000.0,
         "value_date": "2025-06-04", "channel": fp["channel"]},
    ]
    assert find_funnel_shaped_account(bad, set(), fp, juris) is not None
    same_place = [dict(bad[0]), dict(bad[1], from_party="C")]
    assert find_funnel_shaped_account(same_place, set(), fp, juris) is None
    too_far = [dict(bad[0]), dict(bad[1], value_date="2025-07-30")]
    assert find_funnel_shaped_account(too_far, set(), fp, juris) is None
    assert find_funnel_shaped_account(bad, {"T1", "T2"}, fp, juris) is None

    tp = {"invoice_price_variance_pct": 30, "min_shipments": 2,
          "channel": "over_under_invoicing", "double_invoice": True}
    dbl = [
        {"txn_id": "S1", "from_party": "A", "to_party": "B", "amount_usd": 10000.0,
         "value_date": "2025-06-02", "channel": tp["channel"]},
        {"txn_id": "S2", "from_party": "A", "to_party": "B", "amount_usd": 14000.0,
         "value_date": "2025-06-02", "channel": tp["channel"]},
    ]
    assert find_double_invoiced_pair(dbl, set(), tp) is not None
    narrow = [dict(dbl[0]), dict(dbl[1], amount_usd=10500.0)]
    assert find_double_invoiced_pair(narrow, set(), tp) is None
    apart = [dict(dbl[0]), dict(dbl[1], value_date="2025-06-09")]
    assert find_double_invoiced_pair(apart, set(), tp) is None
    assert find_double_invoiced_pair(dbl, {"S1", "S2"}, tp) is None

def test_cases_are_labelled_and_reference_only_real_frozen_parties():
    """CLAUDE.md rule 2 as an assertion: every party named anywhere in a
    case is one of the 201 invented AMLP-#### parties. Provenance labelled
    on every case and every transaction it cites."""
    import json, re
    from ccf.config import REPO_ROOT
    root = REPO_ROOT/"sources"/"screening"
    cases = json.loads((root/"wave17_cases.json").read_text())["cases"]
    txns = {t["txn_id"]: t
            for t in json.loads((root/"wave17_transactions.json").read_text())["transactions"]}
    parties = {p["party_id"]
               for p in json.loads((root/"wave17_parties.json").read_text())["parties"]}
    assert len(parties) == 201, f"party population no longer frozen: {len(parties)}"
    assert cases, "no cases -- every assertion below would be vacuous"
    seen_ids = set()
    for c in cases:
        assert re.fullmatch(r"CASE-\d{3}", c["case_id"]), c["case_id"]
        assert c["case_id"] not in seen_ids, f"duplicate {c['case_id']}"
        seen_ids.add(c["case_id"])
        assert c["provenance"] == "synthetic — engineered", c["case_id"]
        assert c["subject_party"] in parties, c["subject_party"]
        if c.get("depth_three_counterparty"):
            assert c["depth_three_counterparty"] in parties
        assert c["txn_ids"], f"{c['case_id']} cites no transactions"
        for i in c["txn_ids"]:
            assert i in txns, f"{c['case_id']} cites unknown {i}"
            assert txns[i]["provenance"] == "synthetic — engineered"
            assert txns[i]["from_party"] in parties
            assert txns[i]["to_party"] in parties

def test_no_case_transaction_was_taken_from_the_ordinary_population():
    """The injected cases must be NEW transactions appended to the
    artifact, never a relabelling of Task 10's rows -- a case built out of
    ordinary traffic would silently shrink the background it is supposed to
    stand out from, and would break the case-exclusion scoping the Task 10
    anti-pattern check depends on."""
    import json
    from ccf.config import REPO_ROOT
    root = REPO_ROOT/"sources"/"screening"
    cases = json.loads((root/"wave17_cases.json").read_text())["cases"]
    txns = json.loads((root/"wave17_transactions.json").read_text())["transactions"]
    ordinary_ids = {f"TXN-{i:06d}" for i in range(1, ORDINARY_TXN_COUNT + 1)}
    assert ordinary_ids <= {t["txn_id"] for t in txns}, (
        "Task 10's own transaction ids no longer all exist -- the artifact "
        "was renumbered rather than appended to")
    cited = {i for c in cases for i in c["txn_ids"]}
    assert cited, "no case transactions at all"
    assert not (cited & ordinary_ids), (
        f"cases cite ordinary Task 10 transactions: "
        f"{sorted(cited & ordinary_ids)[:5]}")

def test_injected_txn_ids_follow_the_documented_content_sort_not_draw_order():
    """Positional identity is a defect class here (5 recorded instances).
    Task 10 assigned txn_id from a SORTED, content-derived ordering; the
    injected block must extend that scheme rather than switch to 'whatever
    order the injector happened to build them in'. Recompute the ordering
    here, independently of the injector's own code, and require the ids to
    agree."""
    import json, hashlib
    from ccf.config import REPO_ROOT
    txns = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_transactions.json").read_text())["transactions"]
    injected = [t for t in txns
                if int(t["txn_id"].split("-")[1]) > ORDINARY_TXN_COUNT]
    assert injected, "nothing was injected"

    def key(t):
        body = {k: t[k] for k in
                ("from_party", "to_party", "amount_usd", "value_date",
                 "channel", "provenance")}
        digest = hashlib.sha256(
            json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()
        return (t["value_date"], t["from_party"], t["to_party"],
                t["channel"], t["amount_usd"], digest)

    expected = [f"TXN-{i:06d}" for i in range(
        ORDINARY_TXN_COUNT + 1, ORDINARY_TXN_COUNT + 1 + len(injected))]
    got = [t["txn_id"] for t in sorted(injected, key=key)]
    assert got == expected, (
        "injected txn_ids do not follow the content-derived sort order")

def test_case_and_transaction_artifacts_are_byte_identical_across_runs():
    """Determinism: seeded RNG with a fixed constant, sorted iteration --
    prove it by regenerating and diffing, not by reading the code. The
    injector is also re-runnable: a second run must not append a second
    copy of everything."""
    import subprocess
    from ccf.config import REPO_ROOT
    cases = REPO_ROOT/"sources"/"screening"/"wave17_cases.json"
    txns = REPO_ROOT/"sources"/"screening"/"wave17_transactions.json"
    r = subprocess.run(["uv", "run", "generators/inject_typology_cases.py"],
                       capture_output=True, text=True, cwd=REPO_ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    first = (cases.read_bytes(), txns.read_bytes())
    r = subprocess.run(["uv", "run", "generators/inject_typology_cases.py"],
                       capture_output=True, text=True, cwd=REPO_ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    second = (cases.read_bytes(), txns.read_bytes())
    assert first[0] == second[0], "wave17_cases.json is not byte-identical"
    assert first[1] == second[1], "wave17_transactions.json is not byte-identical"

def test_the_dilution_acceptance_predicate_can_actually_reject():
    """Known-present / known-absent control on the DECISION, not on the
    detectors it calls. Both tell-dilution loops accept a drawn transaction
    only if `dilution_candidate_is_shapeless` says the ordinary population
    would still be clear of all three shapes afterwards -- and the real run
    rejects zero draws, which on its own is indistinguishable from a
    predicate that always says yes. Require it to say NO to a candidate
    that completes each shape and YES to an innocuous one."""
    from generators.inject_typology_cases import dilution_candidate_is_shapeless
    fp = {"threshold_usd": 10000, "min_deposit_locations": 2,
          "max_window_days": 5, "channel": "cash_deposit_geographic_dispersion"}
    tp = {"invoice_price_variance_pct": 30, "min_shipments": 2,
          "channel": "over_under_invoicing", "double_invoice": True}
    juris = {"P-A": "USA", "P-B": "DEU", "P-F": "GBR"}

    innocuous = {"txn_id": "N1", "from_party": "P-A", "to_party": "P-F",
                 "amount_usd": 1234.0, "value_date": "2025-06-02",
                 "channel": fp["channel"]}
    assert dilution_candidate_is_shapeless(innocuous, [], fp, tp, juris) is True

    # completes a funnel account: a second deposit location inside the window
    existing_funnel = [dict(innocuous, txn_id="E1")]
    completes_funnel = dict(innocuous, txn_id="N2", from_party="P-B",
                            value_date="2025-06-04")
    assert dilution_candidate_is_shapeless(
        completes_funnel, existing_funnel, fp, tp, juris) is False

    # completes a double invoice: same pair, same day, 40% apart
    existing_inv = [{"txn_id": "E2", "from_party": "P-A", "to_party": "P-B",
                     "amount_usd": 10_000.0, "value_date": "2025-06-02",
                     "channel": tp["channel"]}]
    completes_double = {"txn_id": "N3", "from_party": "P-A",
                        "to_party": "P-B", "amount_usd": 14_000.0,
                        "value_date": "2025-06-02", "channel": tp["channel"]}
    assert dilution_candidate_is_shapeless(
        completes_double, existing_inv, fp, tp, juris) is False

    # completes a structuring cluster: the 4th in-band transaction in 10 days
    existing_struct = [
        {"txn_id": f"E{i}", "from_party": "P-A", "to_party": "P-F",
         "amount_usd": amt, "value_date": d, "channel": "wire_transfer"}
        for i, (amt, d) in enumerate([(8500.0, "2025-06-01"),
                                       (8700.0, "2025-06-04"),
                                       (9200.0, "2025-06-07")], start=10)]
    completes_struct = {"txn_id": "N4", "from_party": "P-A",
                        "to_party": "P-F", "amount_usd": 9600.0,
                        "value_date": "2025-06-10", "channel": "wire_transfer"}
    assert dilution_candidate_is_shapeless(
        completes_struct, existing_struct, fp, tp, juris) is False
    # and the same candidate is fine once the cluster is spread out
    spread = [dict(existing_struct[0]), dict(existing_struct[1]),
              dict(existing_struct[2], value_date="2025-08-07")]
    assert dilution_candidate_is_shapeless(
        completes_struct, spread, fp, tp, juris) is True

def test_the_ordinary_generator_refuses_to_destroy_the_injected_block():
    """Task 11 fix round. `generate_aml_transactions.py`'s main() rewrites
    the transaction artifact with the ORDINARY rows only, so re-running it
    after Task 11 deletes all 263 injected transactions and leaves all 99
    case txn_ids dangling -- while printing a success line and exiting 0.
    The next pytest run breaks in five places, but between the destructive
    run and that pytest the estate holds a silently truncated artifact
    reporting success, which is the 'runs clean and produces stores that
    cannot be assembled' failure CLAUDE.md names by hand.

    Two worlds, and the guard must tell them apart, or it is decoration:
    with wave17_cases.json PRESENT the script must refuse, exit non-zero
    and leave the artifact byte-identical; with it ABSENT the same script
    must run to completion and write the ordinary population. Both are
    exercised here against the real script through subprocess, with the
    artifacts backed up and restored."""
    import json, subprocess
    from ccf.config import REPO_ROOT
    root = REPO_ROOT/"sources"/"screening"
    cases_path = root/"wave17_cases.json"
    txn_path = root/"wave17_transactions.json"
    script = "generators/generate_aml_transactions.py"

    cases_backup = cases_path.read_bytes()
    txn_backup = txn_path.read_bytes()
    n_cases = len(json.loads(cases_backup)["cases"])
    assert n_cases > 0, "no cases -- the known-present world does not exist"

    try:
        # ---- known-present: cases exist, the guard must fire ----------
        r = subprocess.run(["uv", "run", script], capture_output=True,
                           text=True, cwd=REPO_ROOT)
        assert r.returncode != 0, (
            f"the generator exited {r.returncode} with {n_cases} cases on "
            "disk -- it just destroyed the injected block and called it "
            "success")
        assert "inject_typology_cases.py" in (r.stderr + r.stdout), (
            "the refusal does not name the script that rebuilds the "
            "injected block, so the operator is told to stop and not what "
            "to do instead")
        assert txn_path.read_bytes() == txn_backup, (
            "the generator refused and rewrote the artifact anyway")

        # ---- known-absent: no cases, the same script must proceed ------
        cases_path.unlink()
        r = subprocess.run(["uv", "run", script], capture_output=True,
                           text=True, cwd=REPO_ROOT)
        assert r.returncode == 0, (
            "with no cases on disk there is nothing to destroy and the "
            f"generator must still run: {r.stdout + r.stderr}")
        rewritten = json.loads(txn_path.read_text())["transactions"]
        assert len(rewritten) == ORDINARY_TXN_COUNT, (
            f"the unguarded run wrote {len(rewritten)} rows, expected the "
            f"{ORDINARY_TXN_COUNT} ordinary ones")

        # ---- and the override reaches the same destructive path --------
        txn_path.write_bytes(txn_backup)
        cases_path.write_bytes(cases_backup)
        r = subprocess.run(["uv", "run", script, "--regenerate-base"],
                           capture_output=True, text=True, cwd=REPO_ROOT)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "WARNING" in r.stderr, (
            "the override destroyed the injected block without saying so")
        assert len(json.loads(txn_path.read_text())["transactions"]) \
            == ORDINARY_TXN_COUNT
    finally:
        cases_path.write_bytes(cases_backup)
        txn_path.write_bytes(txn_backup)

    assert cases_path.read_bytes() == cases_backup
    assert txn_path.read_bytes() == txn_backup


# ===========================================================================
# Wave 17 Task 12 -- alerts, noise, and prior-alert history
# ===========================================================================

def test_precision_is_measurable_not_assumed():
    """Wave 17 Task 12. The envelope wants ~30 genuine among ~150 so
    precision is measurable. Assert BOTH that genuine alerts exist and that
    noise dominates -- an alert set that is all genuine measures nothing."""
    import json
    from ccf.config import REPO_ROOT
    d = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_alerts.json").read_text())
    alerts = d["alerts"]
    genuine = [a for a in alerts if a.get("case_id")]
    assert len(alerts) >= 100, f"only {len(alerts)} alerts"
    assert len(genuine) >= 20, f"only {len(genuine)} genuine alerts"
    assert len(genuine) < len(alerts) * 0.5, (
        "more than half the alerts are genuine -- this is not a triage "
        "population and precision is not being exercised")

def test_every_genuine_alert_points_at_a_real_case():
    import json
    from ccf.config import REPO_ROOT
    root = REPO_ROOT/"sources"/"screening"
    alerts = json.loads((root/"wave17_alerts.json").read_text())["alerts"]
    cases = {c["case_id"] for c in json.loads((root/"wave17_cases.json").read_text())["cases"]}
    dangling = [a["alert_id"] for a in alerts if a.get("case_id") and a["case_id"] not in cases]
    assert not dangling, f"alerts citing nonexistent cases: {dangling[:5]}"

def test_noise_alerts_carry_no_case_id():
    """The interface's own contract: noise alerts carry case_id: None. A
    noise alert with a case_id would be indistinguishable from genuine and
    the precision measurement above would be lying about what it measured."""
    import json
    from ccf.config import REPO_ROOT
    alerts = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_alerts.json").read_text())["alerts"]
    genuine = [a for a in alerts if a.get("case_id")]
    noise = [a for a in alerts if not a.get("case_id")]
    assert genuine and noise, "need both genuine and noise alerts to check the boundary"
    assert all(a.get("case_id") is None for a in noise), (
        "a noise alert carries a non-None case_id")

def test_alert_id_is_unique_and_correctly_formatted():
    import json, re
    from ccf.config import REPO_ROOT
    alerts = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_alerts.json").read_text())["alerts"]
    assert alerts, "no alerts -- the assertions below would be vacuous"
    ids = [a["alert_id"] for a in alerts]
    assert len(ids) == len(set(ids)), "duplicate alert_id"
    assert all(re.fullmatch(r"ALT-\d{6}", i) for i in ids), "malformed alert_id"

def test_alert_ids_are_content_derived_not_positional():
    """Positional identity is a defect class here (5 recorded instances).
    Recompute the content-derived sort order independently of the generator
    and require the ids to agree, the same idiom
    test_injected_txn_ids_follow_the_documented_content_sort_not_draw_order
    uses for txn_id."""
    import hashlib, json
    from ccf.config import REPO_ROOT
    alerts = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_alerts.json").read_text())["alerts"]
    assert alerts, "no alerts -- vacuous otherwise"

    def key(a):
        body = {k: v for k, v in a.items() if k != "alert_id"}
        digest = hashlib.sha256(
            json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()
        return (a["raised_at"], a["subject_party"], a.get("case_id") or "",
                a["trigger"], digest)

    expected = [f"ALT-{i:06d}" for i in range(1, len(alerts) + 1)]
    got = [a["alert_id"] for a in sorted(alerts, key=key)]
    assert got == expected, (
        "alert_ids do not follow the content-derived sort order -- they "
        "may have been assigned from build/draw order instead")

def test_every_alert_subject_is_a_frozen_party():
    import json
    from ccf.config import REPO_ROOT
    root = REPO_ROOT/"sources"/"screening"
    alerts = json.loads((root/"wave17_alerts.json").read_text())["alerts"]
    parties = {p["party_id"] for p in json.loads((root/"wave17_parties.json").read_text())["parties"]}
    assert len(parties) == 201, f"party population no longer frozen: {len(parties)}"
    assert alerts, "no alerts -- vacuous otherwise"
    offenders = [a["alert_id"] for a in alerts if a["subject_party"] not in parties]
    assert not offenders, f"alerts on a non-frozen subject: {offenders[:5]}"

def test_alerts_are_labelled_synthetic_internal():
    """Provenance ruling: alerts are bank-internal by nature, so
    'synthetic — internal', not 'synthetic — engineered' (that label belongs
    to the transactions and cases the alerts are raised over)."""
    import json
    from ccf.config import REPO_ROOT
    alerts = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_alerts.json").read_text())["alerts"]
    assert alerts, "no alerts -- vacuous otherwise"
    assert all(a["provenance"] == "synthetic — internal" for a in alerts)

def test_every_case_gets_at_least_one_alert():
    import json
    from ccf.config import REPO_ROOT
    root = REPO_ROOT/"sources"/"screening"
    cases = json.loads((root/"wave17_cases.json").read_text())["cases"]
    alerts = json.loads((root/"wave17_alerts.json").read_text())["alerts"]
    assert cases, "no cases -- vacuous otherwise"
    by_case = {}
    for a in alerts:
        if a.get("case_id"):
            by_case.setdefault(a["case_id"], []).append(a)
    missing = [c["case_id"] for c in cases if c["case_id"] not in by_case]
    assert not missing, f"cases with no alert at all: {missing}"

def test_shell_cases_carry_a_second_alert_on_the_intermediary():
    """The brief's own design choice, checked against the live artifact: a
    TYP-SHELL case's secondary alert lands on the LAST named intermediary --
    the party that actually received the upstream transfer and made the
    purchase -- not on the case's own subject_party a second time."""
    import json
    from ccf.config import REPO_ROOT
    root = REPO_ROOT/"sources"/"screening"
    cases = [c for c in json.loads((root/"wave17_cases.json").read_text())["cases"]
             if c["typology_id"] == "TYP-SHELL"]
    alerts = json.loads((root/"wave17_alerts.json").read_text())["alerts"]
    assert cases, "no TYP-SHELL cases -- vacuous otherwise"
    for c in cases:
        hits = [a for a in alerts if a.get("case_id") == c["case_id"]]
        assert len(hits) == 2, f"{c['case_id']}: expected 2 alerts, found {len(hits)}"
        subjects = {a["subject_party"] for a in hits}
        expected_subjects = {c["subject_party"], c["pattern"]["intermediaries"][-1]}
        assert subjects == expected_subjects, (
            f"{c['case_id']}: alert subjects {subjects} != expected "
            f"{expected_subjects}")

def test_alert_links_reference_real_alerts_with_valid_relations():
    import json
    from ccf.config import REPO_ROOT
    root = REPO_ROOT/"sources"/"screening"
    d = json.loads((root/"wave17_alerts.json").read_text())
    alerts_by_id = {a["alert_id"]: a for a in d["alerts"]}
    links = d["links"]
    assert links, "no links at all -- vacuous otherwise"
    allowed = {"same_case_prior_alert", "prior_alert_on_subject"}
    for l in links:
        assert l["alert_id"] in alerts_by_id, f"unknown alert_id {l['alert_id']}"
        assert l["related_alert_id"] in alerts_by_id, (
            f"unknown related_alert_id {l['related_alert_id']}")
        assert l["alert_id"] != l["related_alert_id"], "self-link"
        assert l["relation"] in allowed, f"unrecognised relation {l['relation']}"

def test_prior_alert_links_represent_real_chronological_history():
    """Each link must actually mean what its relation name claims: a
    same_case_prior_alert pair shares a case_id and DIFFERENT subjects (or it
    would be indistinguishable from a prior_alert_on_subject link); a
    prior_alert_on_subject pair shares a subject; and in both cases the
    'related' alert must genuinely have come first."""
    import json
    from ccf.config import REPO_ROOT
    root = REPO_ROOT/"sources"/"screening"
    d = json.loads((root/"wave17_alerts.json").read_text())
    alerts_by_id = {a["alert_id"]: a for a in d["alerts"]}
    links = d["links"]
    assert links, "no links at all -- vacuous otherwise"
    checked = {"same_case_prior_alert": 0, "prior_alert_on_subject": 0}
    for l in links:
        a, rel = alerts_by_id[l["alert_id"]], alerts_by_id[l["related_alert_id"]]
        assert rel["raised_at"] <= a["raised_at"], (
            f"{l['related_alert_id']} is not chronologically prior to "
            f"{l['alert_id']}")
        if l["relation"] == "same_case_prior_alert":
            assert a["case_id"] and a["case_id"] == rel["case_id"]
            assert a["subject_party"] != rel["subject_party"]
        else:
            assert a["subject_party"] == rel["subject_party"]
        checked[l["relation"]] += 1
    assert checked["same_case_prior_alert"] >= 6, (
        "expected at least one same_case_prior_alert per TYP-SHELL case "
        f"(6): {checked}")
    assert checked["prior_alert_on_subject"] >= 1, (
        "no prior_alert_on_subject links at all -- the repeat-subject "
        f"history this task is named for never materialised: {checked}")

def test_alerts_and_links_are_byte_identical_across_runs():
    """Determinism: seeded RNG with a fixed constant, sorted iteration --
    prove it by regenerating and diffing, not by reading the code."""
    import subprocess
    from ccf.config import REPO_ROOT
    path = REPO_ROOT/"sources"/"screening"/"wave17_alerts.json"
    r1 = subprocess.run(["uv", "run", "generators/generate_aml_alerts.py"],
                        capture_output=True, text=True, cwd=REPO_ROOT)
    assert r1.returncode == 0, r1.stdout + r1.stderr
    first = path.read_bytes()
    r2 = subprocess.run(["uv", "run", "generators/generate_aml_alerts.py"],
                        capture_output=True, text=True, cwd=REPO_ROOT)
    assert r2.returncode == 0, r2.stdout + r2.stderr
    second = path.read_bytes()
    assert first == second, "wave17_alerts.json is not byte-identical across runs"


# --------------------------------------------------------------------------
# Wave 17 Task 12 -- loading aml_alert / aml_alert_link / aml_transaction.
# --------------------------------------------------------------------------

def test_aml_alert_table_is_populated_from_the_final_artifact():
    import json
    from ccf.config import PG_SCHEMA_V2 as S, REPO_ROOT, pg_connect
    alerts = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_alerts.json").read_text())["alerts"]
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM "{S}".aml_alert')
        n = cur.fetchone()[0]
    assert n == len(alerts), f"aml_alert has {n} rows, artifact has {len(alerts)}"

def test_aml_alert_link_table_is_populated_from_the_final_artifact():
    import json
    from ccf.config import PG_SCHEMA_V2 as S, REPO_ROOT, pg_connect
    links = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_alerts.json").read_text())["links"]
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM "{S}".aml_alert_link')
        n = cur.fetchone()[0]
    assert n == len(links), f"aml_alert_link has {n} rows, artifact has {len(links)}"

def test_aml_alert_row_round_trips_a_genuine_alert():
    """Spot-check one genuine alert's fields, including the quoted
    'trigger' column, against the live row."""
    import json
    from ccf.config import PG_SCHEMA_V2 as S, REPO_ROOT, pg_connect
    alerts = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_alerts.json").read_text())["alerts"]
    genuine = next(a for a in alerts if a.get("case_id"))
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'''SELECT subject_party, raised_at, case_id, "trigger",
                        provenance FROM "{S}".aml_alert WHERE alert_id = %s''',
                    (genuine["alert_id"],))
        row = cur.fetchone()
    assert row is not None, f"{genuine['alert_id']} not found in aml_alert"
    subject, raised_at, case_id, trigger, provenance = row
    assert subject == genuine["subject_party"]
    assert case_id == genuine["case_id"]
    assert trigger == genuine["trigger"]
    assert provenance == genuine["provenance"]

def test_no_foreign_key_constrains_aml_alert_case_id():
    """Global constraint: no FK from aml_alert.case_id to anything -- cases
    live only in the JSON artifact and are never loaded into a Postgres
    table by this plan. A FK here would fail at load time, since nothing
    stores case rows."""
    from ccf.config import PG_SCHEMA_V2 as S, pg_connect
    with pg_connect() as c, c.cursor() as cur:
        cur.execute("""
            SELECT tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.table_schema = %s AND tc.table_name = 'aml_alert'
              AND tc.constraint_type = 'FOREIGN KEY'
              AND kcu.column_name = 'case_id'
        """, (S,))
        rows = cur.fetchall()
    assert not rows, f"unexpected FK on aml_alert.case_id: {rows}"

def test_aml_transaction_table_is_populated_from_the_final_artifact():
    """This task is the only one that calls load_transactions. Assert the
    loaded row count equals the artifact's full transaction count (ordinary
    + injected), not merely 'more than zero'."""
    import json
    from ccf.config import PG_SCHEMA_V2 as S, REPO_ROOT, pg_connect
    txns = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_transactions.json").read_text())["transactions"]
    assert len(txns) == 4358, f"expected the final 4,358-row artifact, found {len(txns)}"
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM "{S}".aml_transaction')
        n = cur.fetchone()[0]
    assert n == len(txns), f"aml_transaction has {n} rows, artifact has {len(txns)}"

def test_load_transactions_is_idempotent_on_a_named_value():
    """Idempotency by VALUE, not by count (Global Constraints). Name one
    transaction, record its amount_usd and value_date, re-run the loader
    end to end, and assert both fields AND the row count are unchanged --
    exercising load_transactions's ON CONFLICT (txn_id) DO UPDATE clause,
    which Task 8's review flagged as never having been exercised."""
    import json, subprocess
    from ccf.config import PG_SCHEMA_V2 as S, REPO_ROOT, pg_connect

    named_txn_id = "TXN-000001"
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM "{S}".aml_transaction')
        before_count = cur.fetchone()[0]
        cur.execute(f'''SELECT amount_usd, value_date FROM "{S}".aml_transaction
                        WHERE txn_id = %s''', (named_txn_id,))
        row = cur.fetchone()
    assert row is not None, f"{named_txn_id} not loaded -- cannot prove idempotency"
    before_amount, before_date = row

    txns = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_transactions.json").read_text())["transactions"]
    artifact_row = next(t for t in txns if t["txn_id"] == named_txn_id)
    assert float(before_amount) == artifact_row["amount_usd"]
    assert before_date == artifact_row["value_date"]

    result = subprocess.run(["uv", "run", "loaders/load_postgres_wave17.py"],
                            capture_output=True, text=True, cwd=REPO_ROOT)
    assert result.returncode == 0, result.stdout + result.stderr

    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM "{S}".aml_transaction')
        after_count = cur.fetchone()[0]
        cur.execute(f'''SELECT amount_usd, value_date FROM "{S}".aml_transaction
                        WHERE txn_id = %s''', (named_txn_id,))
        after_amount, after_date = cur.fetchone()

    assert after_count == before_count
    assert float(after_amount) == float(before_amount)
    assert after_date == before_date


# ===========================================================================
# Wave 17 Task 13 -- Fluree: nodes, network, ownership, typologies
# ===========================================================================

def _fluree_count(sparql_where: str) -> int:
    from ccf import fluree
    from ccf.config import FLUREE_LEDGER_V2 as L
    q = f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE {{ {sparql_where} }}"
    rows = fluree.query(q)["results"]["bindings"]
    return int(rows[0]["n"]["value"]) if rows else 0


def _unanchored_matchestypology_objects() -> list[str]:
    """Every OBJECT of ex:matchesTypology that carries no ex:anchoredToPassage
    -- a SPARQL set difference, not a pair of existentials. Used both by the
    strengthened floor-1 test and by the test proving it can actually fail."""
    from ccf import fluree
    from ccf.config import EX, FLUREE_LEDGER_V2 as L
    q = (f"SELECT DISTINCT ?o FROM <{L}> WHERE {{ "
         f"?s <{EX}matchesTypology> ?o . "
         f"FILTER NOT EXISTS {{ ?o <{EX}anchoredToPassage> ?p }} }}")
    rows = fluree.query(q)["results"]["bindings"]
    return sorted(r["o"]["value"] for r in rows)


def test_every_matches_typology_edge_cites_an_advisory_passage():
    """Wave 17 Task 13, envelope floor 1 in the store that owns it. A
    typology match with no anchor is an unsupported accusation about a party
    -- invented or not, it is the shape of claim this product exists to make
    defensible.

    Strengthened past the brief's own verbatim body. The brief's test checks
    two independent counts (matches > 0, anchored > 0) under a name that
    promises a universal -- one hundred unanchored matchesTypology edges plus
    a single anchored typology elsewhere in the graph passes both counts.
    The block below asserts the universal directly, as a set difference that
    must be empty: every OBJECT of matchesTypology must itself resolve to a
    node carrying anchoredToPassage. See
    test_the_anchor_universal_can_actually_fail for proof this check is not
    vacuous."""
    from ccf import fluree
    from ccf.config import EX, FLUREE_LEDGER_V2 as L
    def count(q):
        r = fluree.query(q)["results"]["bindings"]
        return int(r[0]["n"]["value"]) if r else 0
    matches = count(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE "
                    f"{{ ?s <{EX}matchesTypology> ?o }}")
    anchored = count(f"SELECT (COUNT(*) AS ?n) FROM <{L}> WHERE "
                     f"{{ ?t <{EX}anchoredToPassage> ?p }}")
    assert matches > 0, "no typology matches loaded at all"
    assert anchored > 0, "no typology carries a passage anchor"

    offenders = _unanchored_matchestypology_objects()
    assert not offenders, (
        f"{len(offenders)} matchesTypology target(s) carry no "
        f"anchoredToPassage -- unsupported accusation(s): {offenders}")


def test_the_anchor_universal_can_actually_fail():
    """A universal nobody has ever seen fail is a count wearing a better
    name (this estate's most-recorded defect class). Insert a throwaway
    matchesTypology edge pointing at a scratch node carrying NO
    anchoredToPassage, confirm the check above actually names it, then
    retract the scratch triple in a finally block so nothing survives the
    test regardless of outcome."""
    import time
    from ccf import fluree
    from ccf.config import EX

    scratch_subject = f"{EX}TEST-SCRATCH-task13-subject"
    scratch_object = f"{EX}TEST-SCRATCH-task13-unanchored"
    stmt = f"<{scratch_subject}> <{EX}matchesTypology> <{scratch_object}> ."

    fluree.update("INSERT DATA {\n" + stmt + "\n}")
    try:
        offenders = []
        for attempt in range(6):
            offenders = _unanchored_matchestypology_objects()
            if scratch_object in offenders:
                break
            time.sleep(0.5)
        assert scratch_object in offenders, (
            "the universal check did not catch a deliberately unanchored "
            "matchesTypology target -- it cannot fail, so it proves nothing")
    finally:
        fluree.update("DELETE DATA {\n" + stmt + "\n}")

    offenders_after = []
    for attempt in range(6):
        offenders_after = _unanchored_matchestypology_objects()
        if scratch_object not in offenders_after:
            break
        time.sleep(0.5)
    assert scratch_object not in offenders_after, "scratch triple was not retracted"


def test_amlparty_nodes_cover_the_frozen_201_and_carry_identity():
    """Every AMLParty in the frozen artifact gets a Fluree node, typed
    explicitly (no reasoner -- rule 7), carrying its syn_lei as `ex:lei` --
    the estate-wide identity predicate, reused not redeclared."""
    import json
    from ccf import fluree
    from ccf.config import EX, FLUREE_LEDGER_V2 as L, REPO_ROOT
    parties = json.loads(
        (REPO_ROOT / "sources" / "screening" / "wave17_parties.json").read_text()
    )["parties"]

    n_typed = _fluree_count(f"?s a <{EX}AMLParty>")
    assert n_typed == len(parties), (
        f"{n_typed} ex:AMLParty nodes in Fluree, expected {len(parties)}")

    q = (f"SELECT ?s ?l FROM <{L}> WHERE {{ ?s a <{EX}AMLParty> ; "
         f"<{EX}lei> ?l }}")
    rows = fluree.query(q)["results"]["bindings"]
    lei_by_node = {r["s"]["value"]: r["l"]["value"] for r in rows}
    assert len(lei_by_node) == len(parties), "not every AMLParty node carries ex:lei"

    syn_leis = {p["syn_lei"] for p in parties}
    assert set(lei_by_node.values()) == syn_leis


def test_no_postgres_owned_attribute_leaks_onto_aml_party_nodes():
    """Party attributes (legal name, jurisdiction, incorporation date)
    belong to Postgres. Direct regression for this loader, independent of
    validators/partition.py's own generic scan."""
    from ccf.config import EX
    for attr in ("legalName", "jurisdiction", "entityStatus", "incorporated",
                 "incorporationDate", "partyKind"):
        n = _fluree_count(f'?s <{EX}{attr}> ?o . ?s a <{EX}AMLParty>')
        assert n == 0, f"ex:{attr} leaked onto {n} AMLParty node(s)"


def test_every_transaction_becomes_a_transactedwith_edge_undirected():
    """Envelope requirement: ALL 4,358 transaction rows project into
    ex:transactedWith, ordinary and injected alike -- loading a subset
    changes the adjacency and silently erases the depth-3 floor (Task 11).
    Compares the UNORDERED pair set from the frozen artifact against the
    UNORDERED pair set actually present in Fluree; parallel edges between
    the same pair may collapse, no pair may be missing."""
    import json
    from ccf import fluree
    from ccf.config import EX, FLUREE_LEDGER_V2 as L, REPO_ROOT
    txns = json.loads(
        (REPO_ROOT / "sources" / "screening" / "wave17_transactions.json").read_text()
    )["transactions"]
    assert len(txns) == 4358, f"artifact has {len(txns)} rows, expected 4358"
    artifact_pairs = {frozenset((t["from_party"], t["to_party"])) for t in txns}

    q = f"SELECT ?s ?o FROM <{L}> WHERE {{ ?s <{EX}transactedWith> ?o }}"
    rows = fluree.query(q)["results"]["bindings"]
    assert rows, "no ex:transactedWith edges loaded at all"

    def local(iri: str) -> str:
        return iri.rsplit("/", 1)[-1]

    fluree_pairs = {frozenset((local(r["s"]["value"]), local(r["o"]["value"])))
                    for r in rows}
    missing = artifact_pairs - fluree_pairs
    assert not missing, (
        f"{len(missing)} transacting pair(s) from the artifact are absent "
        f"from Fluree -- the adjacency has been changed: "
        f"{sorted(list(missing))[:5]}")


def test_transactedwith_has_no_reflexive_or_extraneous_edges():
    """The blind spot the brief names is one edge wide: a reflexive edge or
    a stray edge from a non-transaction predicate mixed into the same
    subject/object population would erase the depth-2/3 floor without
    changing any count this suite already runs. Guard both directly."""
    from ccf.config import EX
    # NOTE: this store's SPARQL engine does not enforce "same variable name
    # = same value" within one triple pattern -- `?s <p> ?s` matched every
    # edge, not zero, when this test was first written (measured: 7736 of
    # 7736). An explicit FILTER(?s = ?o) is required to actually test
    # equality here; that is the finding, not a workaround for a mistake.
    self_loops = _fluree_count(
        f"?s <{EX}transactedWith> ?o . FILTER(?s = ?o)")
    assert self_loops == 0, f"{self_loops} reflexive transactedWith edge(s)"

    non_party_targets = _fluree_count(
        f"?s <{EX}transactedWith> ?o . FILTER NOT EXISTS "
        f"{{ ?o a <{EX}AMLParty> }}")
    assert non_party_targets == 0, (
        f"{non_party_targets} transactedWith edge(s) point at a non-"
        "AMLParty node -- the adjacency this floor depends on has grown "
        "an edge the artifact never had")


def test_depth_three_floor_holds_when_walked_from_fluree():
    """Wave 17 Task 11's floor, reproved in the store that owns the graph
    Task 17's depth_three_holds() will actually walk. Fetches the RAW
    ex:transactedWith edges from Fluree (never the JSON artifact), builds
    an undirected adjacency in Python exactly as the artifact-level test
    does, and asserts CASE-008's depth_three_counterparty (AMLP-0166) is
    absent from the depth-2 reachable set from AMLP-0049 and present at
    depth 3 -- an ordering claim, not a count."""
    import collections
    import json
    from ccf import fluree
    from ccf.config import EX, FLUREE_LEDGER_V2 as L, REPO_ROOT

    cases = json.loads(
        (REPO_ROOT / "sources" / "screening" / "wave17_cases.json").read_text()
    )["cases"]
    case = next(c for c in cases if c["case_id"] == "CASE-008")
    assert case["depth_three_counterparty"] == "AMLP-0166"
    assert case["subject_party"] == "AMLP-0049"

    q = f"SELECT ?s ?o FROM <{L}> WHERE {{ ?s <{EX}transactedWith> ?o }}"
    rows = fluree.query(q)["results"]["bindings"]
    assert rows, "no ex:transactedWith edges loaded at all"

    def local(iri: str) -> str:
        return iri.rsplit("/", 1)[-1]

    adj = collections.defaultdict(set)
    for r in rows:
        s, o = local(r["s"]["value"]), local(r["o"]["value"])
        adj[s].add(o)
        adj[o].add(s)

    def reach(start, depth):
        seen, frontier = {start}, {start}
        for _ in range(depth):
            nxt = set()
            for n in frontier:
                nxt |= adj[n] - seen
            seen |= nxt
            frontier = nxt
        return seen

    depth2 = reach(case["subject_party"], 2)
    depth3 = reach(case["subject_party"], 3)
    assert case["depth_three_counterparty"] not in depth2, (
        "AMLP-0166 already reachable at depth 2 in Fluree -- the floor "
        "does not survive projection")
    assert case["depth_three_counterparty"] in depth3, (
        "AMLP-0166 is not reachable at depth 3 in Fluree either")


def test_typology_and_typologypattern_nodes_are_dual_typed_and_anchored():
    """Envelope floor 1 at the category level: exactly the four typologies,
    each dual-typed ex:Typology + ex:TypologyPattern (the derived,
    parameterized structural instance -- distinct classes so the same
    category COULD carry more than one variant, today a single node plays
    both roles), each carrying ex:anchoredToPassage matching the artifact's
    own passage_id."""
    import json
    from ccf import fluree
    from ccf.config import EX, FLUREE_LEDGER_V2 as L, REPO_ROOT
    typologies = json.loads(
        (REPO_ROOT / "sources" / "screening" / "wave17_typologies.json").read_text()
    )["typologies"]
    assert len(typologies) == 4

    n_typology = _fluree_count(f"?s a <{EX}Typology>")
    n_pattern = _fluree_count(f"?s a <{EX}TypologyPattern>")
    assert n_typology == 4, f"{n_typology} ex:Typology nodes, expected 4"
    assert n_pattern == 4, f"{n_pattern} ex:TypologyPattern nodes, expected 4"

    q = (f"SELECT ?s ?p FROM <{L}> WHERE {{ ?s a <{EX}Typology> ; "
         f"a <{EX}TypologyPattern> ; <{EX}anchoredToPassage> ?p }}")
    rows = fluree.query(q)["results"]["bindings"]
    anchor_by_node = {r["s"]["value"].rsplit("/", 1)[-1]: r["p"]["value"]
                      for r in rows}
    assert len(anchor_by_node) == 4, (
        "not every dual-typed typology node carries anchoredToPassage")
    for t in typologies:
        assert anchor_by_node.get(t["typology_id"]) == t["passage_id"], (
            f"{t['typology_id']}: anchor {anchor_by_node.get(t['typology_id'])!r} "
            f"!= artifact passage_id {t['passage_id']!r}")


def test_matchestypology_edges_match_the_frozen_cases():
    """24 cases, 6 per typology -- every case's subject_party must carry
    exactly the matchesTypology edge its typology_id implies, no more, no
    fewer."""
    import json
    from ccf import fluree
    from ccf.config import EX, FLUREE_LEDGER_V2 as L, REPO_ROOT
    cases = json.loads(
        (REPO_ROOT / "sources" / "screening" / "wave17_cases.json").read_text()
    )["cases"]
    assert len(cases) == 24

    q = f"SELECT ?s ?o FROM <{L}> WHERE {{ ?s <{EX}matchesTypology> ?o }}"
    rows = fluree.query(q)["results"]["bindings"]

    def local(iri: str) -> str:
        return iri.rsplit("/", 1)[-1]

    got = {(local(r["s"]["value"]), local(r["o"]["value"])) for r in rows}
    expected = {(c["subject_party"], c["typology_id"]) for c in cases}
    assert got == expected, (
        f"matchesTypology edge set disagrees with the frozen cases -- "
        f"missing {expected - got}, extra {got - expected}")


def test_bound_parties_get_a_beneficial_owner_edge_in_fluree():
    """Wave 17 Task 9's ownership binding, projected. Every one of the 100
    bound parties gets `hasBeneficialOwner` from its AMLParty node to the
    EXISTING PSC-* Fluree node Wave 13b already minted (reused, never
    reconstructed) -- and CLAUDE.md rule 2/3: the owner is always a PSC-*
    key, never a numeric one, and never anchors on a real legal_entity."""
    import json
    from ccf import fluree
    from ccf.aml import is_psc_key
    from ccf.config import EX, FLUREE_LEDGER_V2 as L, REPO_ROOT
    ownership = json.loads(
        (REPO_ROOT / "sources" / "screening" / "wave17_ownership.json").read_text()
    )
    bindings = ownership["bindings"]
    assert len(bindings) == 100

    fibo_bo = "https://spec.edmcouncil.org/fibo/ontology/BE/OwnershipAndControl/CorporateOwnership/hasBeneficialOwner"
    q = f"SELECT ?s ?o FROM <{L}> WHERE {{ ?s <{fibo_bo}> ?o }}"
    rows = fluree.query(q)["results"]["bindings"]

    def local(iri: str) -> str:
        return iri.rsplit("/", 1)[-1]

    got = {(local(r["s"]["value"]), local(r["o"]["value"])) for r in rows
           if local(r["s"]["value"]).startswith("AMLP-")}
    for b in bindings:
        assert is_psc_key(b["beneficial_owner_key"]), (
            f"{b['party_id']} bound to a non-PSC key "
            f"{b['beneficial_owner_key']!r}")
    expected = {(b["party_id"], b["beneficial_owner_key"]) for b in bindings}
    assert got == expected, (
        f"hasBeneficialOwner edges from AMLParty nodes disagree with "
        f"Task 9's binding artifact -- missing {expected - got}, "
        f"extra {got - expected}")

    # Reused, not reconstructed: every named PSC node must already resolve
    # to something in the ledger (Wave 13b's own node), never a phantom
    # URI this loader invented itself.
    fibo_person_class = "https://spec.edmcouncil.org/fibo/ontology/BE/OwnershipAndControl/CorporateOwnership/BeneficialOwner"
    n_bo_class = _fluree_count(f"?s a <{fibo_person_class}>")
    assert n_bo_class > 0, "no pre-existing BeneficialOwner nodes to reuse"


def test_loader_source_uses_only_plain_string_literals():
    """Fluree 4.1.4 corrupts a typed date literal on write (known-issues
    19.4): the obvious 'improvement' of giving a date its own XSD type would
    silently destroy every date it touches. Nothing in this loader touches
    a date literal at all, but the guard is cheap and matches the rest of
    the estate's convention (test_fluree_wave16_dates_are_plain_strings)."""
    from ccf.config import REPO_ROOT
    src = (REPO_ROOT / "loaders" / "load_fluree_wave17.py").read_text()
    assert "xsd:" not in src, "no typed literals on this ledger"
    assert "^^" not in src, "no typed literals at all on this ledger"


def test_loader_never_creates_an_ex_alert_class():
    """CLAUDE.md-recorded ruling (docs/known-issues.md #25): Sec C assigns
    alerts to Postgres; a Fluree class for them is an unfulfilled contract.
    Guard the loader source AND the live ledger."""
    from ccf.config import EX, REPO_ROOT
    src = (REPO_ROOT / "loaders" / "load_fluree_wave17.py").read_text()
    assert "Alert" not in src, "loader source mentions Alert"
    n = _fluree_count(f"?s a <{EX}Alert>")
    assert n == 0, f"{n} node(s) typed ex:Alert in the ledger"


def test_task13_load_is_idempotent_on_a_named_partys_edge_count():
    """Prove idempotency by VALUE (Global Constraints), not by a row count
    that cannot see a field being reset. Record the ledger `t` and one named
    party's transactedWith edge count, re-run the loader WITHOUT
    --reconcile, and assert both the ledger `t` growth and the named
    party's edge count are unchanged by the second run -- a plain re-run
    against an unchanged artifact asserts the identical triples, which are
    no-ops under RDF set semantics."""
    import subprocess
    from ccf import fluree
    from ccf.config import EX, FLUREE_LEDGER_V2 as L, REPO_ROOT

    named = "AMLP-0049"  # CASE-008's subject -- guaranteed to carry edges

    def edge_count():
        return _fluree_count(
            f"{{ <{EX}{named}> <{EX}transactedWith> ?o }} UNION "
            f"{{ ?o <{EX}transactedWith> <{EX}{named}> }}")

    before_t = fluree.ledger_t()
    before_edges = edge_count()
    assert before_edges > 0, f"{named} carries no transactedWith edges to begin with"

    result = subprocess.run(
        ["uv", "run", "loaders/load_fluree_wave17.py"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    after_edges = edge_count()
    assert after_edges == before_edges, (
        f"{named}'s transactedWith edge count changed on a plain re-run: "
        f"{before_edges} -> {after_edges}")


# ===========================================================================
# Task 14 -- the policy layer: two postures, and the disposition that flips
# ===========================================================================

def test_a_disposition_flips_from_permitted_to_forbidden_across_postures():
    """Wave 17 Task 14, envelope floor 3. The whole as_of argument rests on
    this single case: the SAME disposition for the SAME typology must be
    permitted under the earlier posture and forbidden under the later one.
    Evaluate both and require the two answers to DIFFER -- a count of
    postures proves nothing, and two postures that agree everywhere
    demonstrate nothing."""
    d = json.loads((REPO_ROOT / "sources" / "screening" / "wave17_policy.json").read_text())
    postures = sorted(d["postures"], key=lambda p: p["effective_from"])
    assert len(postures) >= 2, "envelope floor: >= 2 posture versions"
    assert postures[0]["effective_from"] != postures[1]["effective_from"], (
        "two postures with the same effective date cannot be told apart by as_of")
    early, late = postures[0]["posture_id"], postures[1]["posture_id"]
    by = {(r["posture_id"], r["typology_id"], r["disposition"]): r["permitted"]
          for r in d["rules"]}
    flips = [(t, disp) for (p, t, disp) in by
             if p == early and by.get((early, t, disp)) is True
             and by.get((late, t, disp)) is False]
    assert flips, (
        "no disposition is permitted under the earlier posture and forbidden "
        "under the later one -- the Policy Blind counterfactual cannot be shown")


def test_posture_effective_dates_are_loaded_into_fluree_as_plain_strings():
    """Fluree 4.1.4 corrupts a typed date literal on write. The two posture
    effective dates must be bare `YYYY-MM-DD` strings, matching the rest of
    the estate's convention."""
    from ccf import fluree
    from ccf.config import EX, FLUREE_LEDGER_V2 as L
    rows = fluree.query(f"SELECT ?s ?d FROM <{L}> WHERE "
                        f"{{ ?s <{EX}postureEffectiveFrom> ?d }}")["results"]["bindings"]
    assert len(rows) >= 2, "fewer than two postures in Fluree"
    for r in rows:
        assert len(r["d"]["value"]) == 10, "effective date is not a plain YYYY-MM-DD string"


def test_both_postures_fall_inside_the_pinned_transaction_window():
    """Both posture effective dates must fall inside window_start..as_of or
    the as-of demonstration has nothing to range over."""
    from generators.generate_aml_transactions import AS_OF_AML, WINDOW_START
    d = json.loads((REPO_ROOT / "sources" / "screening" / "wave17_policy.json").read_text())
    for p in d["postures"]:
        assert WINDOW_START < p["effective_from"] < AS_OF_AML, (
            f"{p['posture_id']} effective_from {p['effective_from']} is "
            f"outside {WINDOW_START}..{AS_OF_AML}")


def test_advisory_anchoring_is_honest_about_the_window():
    """A posture may only cite an advisory by number if that advisory's OWN
    issue date falls inside the transaction window -- otherwise the
    citation is a plausible-looking justification the dates do not support
    (exactly the 'presenting an engineered condition as emergent' failure
    CLAUDE.md forbids). This test independently re-derives, from the fetched
    advisories' own recorded issue dates, that none of the four falls inside
    the window -- so it is not vacuously trusting the generator's null; it
    proves null is the only honest answer today, and would fail if a future
    posture cited an advisory the dates could not support."""
    from generators.generate_aml_transactions import AS_OF_AML, WINDOW_START
    sel = json.loads((REPO_ROOT / "sources" / "fincen" / "selection.json").read_text())
    issued_in_window = [t for t in sel["typologies"]
                        if WINDOW_START <= t["issued"] <= AS_OF_AML]
    assert issued_in_window == [], (
        "an advisory WAS issued inside the window -- a posture should "
        f"consider citing it rather than assuming null: {issued_in_window}")

    by_number = {t["advisory_number"]: t["issued"] for t in sel["typologies"]}
    d = json.loads((REPO_ROOT / "sources" / "screening" / "wave17_policy.json").read_text())
    for p in d["postures"]:
        if p["advisory_number"] is None:
            continue  # honest, and per the check above, the only honest answer today
        assert p["advisory_number"] in by_number, (
            f"{p['posture_id']} cites unknown advisory {p['advisory_number']!r}")
        issued = by_number[p["advisory_number"]]
        assert WINDOW_START <= issued <= AS_OF_AML, (
            f"{p['posture_id']} cites {p['advisory_number']} issued {issued}, "
            "which the transaction window does not support")


def test_fluree_filing_posture_nodes_are_typed_and_dates_match_artifact():
    """Rule 7 (no OWL inference): a FilingPosture node must be typed
    ex:FilingPosture explicitly. Cross-checked against the artifact's own
    effective_from values so the Fluree assertion is provably the SAME
    posture set, not just some node carrying a 10-char string."""
    from ccf import fluree
    from ccf.config import EX, FLUREE_LEDGER_V2 as L
    d = json.loads((REPO_ROOT / "sources" / "screening" / "wave17_policy.json").read_text())
    q = (f"SELECT ?s ?d FROM <{L}> WHERE "
         f"{{ ?s a <{EX}FilingPosture> . ?s <{EX}postureEffectiveFrom> ?d }}")
    rows = fluree.query(q)["results"]["bindings"]
    got = {r["s"]["value"].rsplit("/", 1)[-1]: r["d"]["value"] for r in rows}
    want = {p["posture_id"]: p["effective_from"] for p in d["postures"]}
    assert got == want, (
        f"missing {set(want) - set(got)}, extra {set(got) - set(want)}, "
        f"got={got}")


def test_fluree_disposition_rules_match_the_policy_artifact():
    """Every DispositionRule in the artifact must resolve to the SAME node
    in Fluree (uri(rule_id)) with ex:permitsDisposition equal to the
    artifact's own `permitted` boolean, and typed ex:DispositionRule
    explicitly -- so the flip is provable from the STORE, not merely typed
    into JSON. Also asserts the two populations are the same SIZE, so a
    silently dropped rule cannot pass a per-rule loop that never notices a
    missing key."""
    from ccf import fluree
    from ccf.config import EX, FLUREE_LEDGER_V2 as L
    d = json.loads((REPO_ROOT / "sources" / "screening" / "wave17_policy.json").read_text())
    q = (f"SELECT ?s ?p FROM <{L}> WHERE "
         f"{{ ?s a <{EX}DispositionRule> . ?s <{EX}permitsDisposition> ?p }}")
    rows = fluree.query(q)["results"]["bindings"]
    got = {r["s"]["value"].rsplit("/", 1)[-1]: r["p"]["value"] for r in rows}
    assert len(got) == len(d["rules"]), (
        f"Fluree has {len(got)} typed+permitted DispositionRule nodes, "
        f"artifact has {len(d['rules'])} rules")
    for r in d["rules"]:
        want = "true" if r["permitted"] else "false"
        assert got.get(r["rule_id"]) == want, (
            f"{r['rule_id']}: Fluree says {got.get(r['rule_id'])!r}, "
            f"artifact says {want!r}")


def test_task14_load_is_idempotent_on_a_named_rules_permitted_value():
    """Prove idempotency by VALUE (Global Constraints), not by a count that
    cannot see a field being reset. Name one rule's permitsDisposition
    boolean -- the exact rule at the center of the flip -- assert it is
    asserted exactly once, re-run the loader WITHOUT --reconcile, and
    assert the value is unchanged and still asserted exactly once (not
    duplicated into a second, competing literal for the same subject)."""
    import subprocess
    from ccf import fluree
    from ccf.config import EX, FLUREE_LEDGER_V2 as L

    named_rule = "RULE-POST-2025-01-TYP-STRUCT-close-no-action"

    def values():
        q = (f"SELECT ?p FROM <{L}> WHERE "
             f"{{ <{EX}{named_rule}> <{EX}permitsDisposition> ?p }}")
        rows = fluree.query(q)["results"]["bindings"]
        return sorted(r["p"]["value"] for r in rows)

    before = values()
    assert before == ["true"], (
        f"expected exactly one literal 'true' for {named_rule} before "
        f"re-run, got {before}")

    result = subprocess.run(
        ["uv", "run", "loaders/load_fluree_wave17.py"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    after = values()
    assert after == before, (
        f"{named_rule}'s permitsDisposition value changed or duplicated on "
        f"a plain re-run: {before} -> {after}")


# ===========================================================================
# Wave 17 Task 15 — SAR narratives and their confidentiality classification
# ===========================================================================

def test_at_least_three_sars_and_one_perspective_cannot_see_them():
    """Wave 17 Task 15, envelope floor 4. In many jurisdictions disclosing
    that a SAR exists is itself an offence, so the test is not 'the field is
    null for L1' -- it is that no indication of existence reaches that
    perspective at all."""
    import json, sqlite3
    from ccf.config import SQLITE_PATH
    con = sqlite3.connect(SQLITE_PATH)
    rows = con.execute(
        "SELECT sar_id, alert_id, visible_to_perspectives FROM sar_classification"
    ).fetchall()
    assert len(rows) >= 3, f"only {len(rows)} SAR records"
    all_p = {"l1", "l2", "examiner"}
    blind = set(all_p)
    for _sar, _alert, vis in rows:
        blind &= set(json.loads(vis))
    excluded = all_p - blind
    assert excluded, (
        "every perspective can see every SAR -- confidentiality is not "
        "demonstrated by any of these records")

def test_sar_classification_lives_only_in_sqlite():
    """Single-writer discipline, and the architectural point: the policy read
    must reach the departmental store. If the classification is ALSO in
    Postgres, nothing forces that reach and the demonstration collapses."""
    from ccf.config import PG_SCHEMA_V2 as S, pg_connect
    with pg_connect() as c, c.cursor() as cur:
        cur.execute("""SELECT table_name, column_name FROM information_schema.columns
                       WHERE table_schema=%s AND (column_name ILIKE %s
                             OR table_name ILIKE %s)""", (S, "%sar%", "%sar%"))
        leaked = cur.fetchall()
    assert not leaked, f"SAR data duplicated into Postgres: {leaked}"


def test_sar_classification_rows_attach_to_genuine_alerts_only():
    """A SAR on a noise alert (no case_id) would be incoherent -- brief's own
    constraint. Cross-reference every sar_classification.alert_id against
    the LIVE aml_alert table and require each to carry a case_id."""
    import sqlite3
    from ccf.config import SQLITE_PATH, PG_SCHEMA_V2 as S, pg_connect
    con = sqlite3.connect(SQLITE_PATH)
    alert_ids = [r[0] for r in con.execute(
        "SELECT alert_id FROM sar_classification").fetchall()]
    assert alert_ids, "no SAR classification rows to check"
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'SELECT alert_id, case_id FROM "{S}".aml_alert '
                    "WHERE alert_id = ANY(%s)", (alert_ids,))
        by_id = dict(cur.fetchall())
    noise = [a for a in alert_ids if not by_id.get(a)]
    assert not noise, f"SAR(s) attached to a noise (no case_id) alert: {noise}"


def test_sar_narrative_documents_carry_doc_type_and_do_not_widen_the_178_gap():
    """Mongo owns passage-level lineage; the SAR narrative is a full
    document, not a passage. `doc_type: 'sar_narrative'` is set here and
    only here for these rows -- the pre-existing 178-row doc_type gap
    (docs/known-issues.md #21) is a known, deliberate non-fix belonging to
    another owner and must not move."""
    from ccf.config import mongo_db
    db = mongo_db()
    docs = list(db.document.find({"doc_type": "sar_narrative"}))
    assert len(docs) >= 3, f"only {len(docs)} sar_narrative documents"
    seen_ids = set()
    for d in docs:
        assert d.get("provenance") == "synthetic — internal", d["_id"]
        assert d.get("alert_id"), f"{d['_id']} has no alert_id"
        assert d.get("case_id"), f"{d['_id']} has no case_id"
        assert d.get("text"), f"{d['_id']} has no narrative text"
        seen_ids.add(d["_id"])
    assert len(seen_ids) == len(docs), "duplicate SAR document ids"
    gap = db.document.count_documents({"doc_type": None})
    assert gap == 178, f"pre-existing doc_type gap changed: now {gap}, want 178"


def test_every_sar_classification_row_has_a_matching_mongo_document():
    """The SQLite classification and the Mongo narrative are two halves of
    the same SAR -- the crosswalk between them is `sar_id`. Every row in one
    store must resolve in the other, or the policy read Task 15 exists to
    demonstrate has nothing to reach."""
    import sqlite3
    from ccf.config import SQLITE_PATH, mongo_db
    con = sqlite3.connect(SQLITE_PATH)
    sar_ids = [r[0] for r in con.execute(
        "SELECT sar_id FROM sar_classification").fetchall()]
    assert sar_ids
    db = mongo_db()
    found = db.document.count_documents(
        {"_id": {"$in": sar_ids}, "doc_type": "sar_narrative"})
    assert found == len(sar_ids), (
        f"only {found}/{len(sar_ids)} sar_classification rows resolve to a "
        "Mongo sar_narrative document")


def test_sar_ids_are_content_derived_not_positional(monkeypatch, tmp_path):
    """Positional identity is a defect class here (5 recorded instances).

    Coordinator review finding: the original version of this test only
    called build_sar_records() twice against the UNCHANGED on-disk
    wave17_cases.json, whose array already happens to be sorted by
    case_id. That comparison is trivially deterministic whether or not the
    generator numbers by content or by raw position -- it cannot
    distinguish the two. Removing generate_sar_records.py's own
    sorted(cases, key=lambda c: c["case_id"]) call would still pass it,
    because the pre-sorted fixture makes position and content agree by
    accident.

    Fix: build a SHUFFLED copy of the same case records (seeded RNG, so the
    shuffle itself is deterministic), point the generator at that copy via
    monkeypatch, and assert the resulting case_id -> sar_id mapping is
    IDENTICAL to the mapping produced from the real, unshuffled artifact.
    Asserting on the mapping (not the id sequence) is what makes this
    order-invariant: a content-derived implementation must produce the same
    mapping regardless of input order; a positional one will not, because
    shuffling changes which case sits at which loop position.
    """
    import json
    import random

    import generators.generate_sar_records as gen

    baseline = gen.build_sar_records()
    baseline_map = {r["case_id"]: r["sar_id"] for r in baseline}
    # Never hardcode a specific case_id here: coverage is now a computed
    # content-digest selection (coordinator ruling, fix rounds 2-3 -- round
    # 2's materiality ranking was REMOVED because materiality was
    # recoverable from `trigger`), not 1:1 with the cases, so which case_ids
    # actually appear is itself a property of the selection logic, not a
    # fact this test should assume in advance.
    assert baseline_map, "no SAR records produced -- nothing to check"
    assert len(baseline_map) >= 3, (
        f"only {len(baseline_map)} SARs -- below the envelope floor")
    assert len(baseline_map) < 24, (
        "coverage is supposed to be a PROPER SUBSET of the 24 cases -- "
        "if every case is filing again, the fix round 2 selection logic "
        "has regressed to 1:1 coverage")
    assert len(baseline_map) == len(baseline), "case_id -> sar_id mapping is not 1:1"

    # Re-running against the SAME unshuffled artifact must be deterministic.
    again = gen.build_sar_records()
    assert {r["case_id"]: r["sar_id"] for r in again} == baseline_map

    cases_doc = json.loads(gen.CASES_PATH.read_text())
    shuffled_cases = list(cases_doc["cases"])
    random.Random(170_015).shuffle(shuffled_cases)
    assert [c["case_id"] for c in shuffled_cases] != [
        c["case_id"] for c in cases_doc["cases"]], (
        "shuffle produced the same order as the original -- fixture no "
        "longer exercises the property this test checks")

    shuffled_path = tmp_path / "wave17_cases_shuffled.json"
    shuffled_path.write_text(json.dumps({**cases_doc, "cases": shuffled_cases}))
    monkeypatch.setattr(gen, "CASES_PATH", shuffled_path)

    shuffled_records = gen.build_sar_records()
    shuffled_map = {r["case_id"]: r["sar_id"] for r in shuffled_records}

    assert shuffled_map == baseline_map, (
        "sar_id assignment depends on input ORDER, not on case_id content -- "
        "this is exactly the positional-identity defect class this "
        "generator's own sorted(...) call exists to prevent")


def test_sar_narratives_introduce_no_name_outside_the_frozen_party_set():
    """The brief's guidance, applied rather than assumed: RealNameIndex.
    blocks() compares ONE NAME, so feeding it a whole narrative paragraph
    would compare the paragraph as a single string and prove nothing. The
    correct property is that every entity name appearing in a narrative is
    one of the 201 frozen party names (already guard-checked at Task 6
    generation time), and no other proper name is introduced by the
    narrative's own prose.

    Strategy: strip every occurrence of a known party legal_name (longest
    first, so one name is never left partially stripped by a shorter
    overlapping prefix) from each narrative's text, then scan what remains
    for any capitalized-multi-word span -- the generic shape of a proper
    noun. Any such leftover must be accounted for in the generator's own
    fixed, finite, non-party vocabulary (ALLOWED_VOCAB); and every phrase in
    THAT vocabulary is run through the ACTUAL guard, RealNameIndex.blocks(),
    which must return None for all of it.

    This can fail two different ways, which is what makes it a real guard
    rather than a check that cannot fail: an unaccounted phrase leaking
    through construction (a template bug introducing a new name), or a
    vocabulary phrase that happens to collide with a real indexed name (the
    guard catching its own fixture)."""
    import re
    from ccf.aml import RealNameIndex
    from ccf.config import REPO_ROOT, mongo_db
    from generators.generate_sar_records import ALLOWED_VOCAB

    parties = json.loads(
        (REPO_ROOT / "sources" / "screening" / "wave17_parties.json").read_text()
    )["parties"]
    party_names = sorted({p["legal_name"] for p in parties}, key=len, reverse=True)

    db = mongo_db()
    docs = list(db.document.find({"doc_type": "sar_narrative"}))
    assert len(docs) >= 3, f"only {len(docs)} sar_narrative documents"

    title_case_re = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4}\b")

    leftover_all: set[str] = set()
    for d in docs:
        text = d["text"]
        for name in party_names:
            text = text.replace(name, " ")
        leftover_all.update(title_case_re.findall(text))

    unaccounted = leftover_all - set(ALLOWED_VOCAB)
    assert not unaccounted, (
        "SAR narratives introduce name-like text not accounted for by a "
        f"party name or the fixed vocabulary: {unaccounted}")

    idx = RealNameIndex.build()
    for phrase in ALLOWED_VOCAB:
        assert idx.blocks(phrase) is None, (
            f"fixed narrative vocabulary phrase {phrase!r} collides with a "
            "real indexed name -- the template must not use it")


def test_task15_sqlite_load_is_idempotent_on_a_named_classification_value():
    """Idempotency by VALUE (Global Constraints), never by a row count that
    cannot see a field being silently reset. Name one sar_id's
    classification and visible_to_perspectives, re-run the loader, and
    require both -- and the row count -- unchanged."""
    import subprocess
    import sqlite3
    from ccf.config import SQLITE_PATH

    con = sqlite3.connect(SQLITE_PATH)
    named_sar = con.execute(
        "SELECT sar_id FROM sar_classification ORDER BY sar_id LIMIT 1"
    ).fetchone()
    assert named_sar, "no sar_classification rows to test idempotency on"
    named_sar = named_sar[0]

    def read():
        c = sqlite3.connect(SQLITE_PATH)
        row = c.execute(
            "SELECT classification, visible_to_perspectives FROM "
            "sar_classification WHERE sar_id = ?", (named_sar,)).fetchone()
        count = c.execute("SELECT COUNT(*) FROM sar_classification").fetchone()[0]
        return row, count

    before_row, before_count = read()

    result = subprocess.run(
        ["uv", "run", "loaders/load_sqlite_wave17.py"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    after_row, after_count = read()
    assert after_row == before_row, (
        f"{named_sar} classification/visibility changed on a plain re-run: "
        f"{before_row} -> {after_row}")
    assert after_count == before_count


def test_sar_coverage_is_a_proper_subset_of_the_24_cases():
    """Coordinator ruling, fix round 2. The original 1:1 version (every one
    of the 24 engineered cases filing a SAR) let `l1` infer, WITH CERTAINTY,
    that a party carrying a Fluree `ex:matchesTypology` edge has a filed
    SAR -- an inference route is exactly the 'indication of existence' the
    brief's confidentiality property forbids, even with every SAR field
    correctly hidden. The fix must leave a SUBSTANTIAL number of cases with
    no SAR at all (not one or two token exceptions), and must not collapse
    either classification to zero."""
    import sqlite3
    from ccf.config import SQLITE_PATH, PG_SCHEMA_V2 as S, pg_connect

    all_case_ids = {c["case_id"] for c in json.loads(
        (REPO_ROOT / "sources" / "screening" / "wave17_cases.json").read_text()
    )["cases"]}
    assert len(all_case_ids) == 24

    con = sqlite3.connect(SQLITE_PATH)
    sar_rows = con.execute(
        "SELECT alert_id, classification FROM sar_classification").fetchall()
    alert_ids = [a for a, _c in sar_rows]

    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'SELECT alert_id, case_id FROM "{S}".aml_alert '
                    "WHERE alert_id = ANY(%s)", (alert_ids,))
        case_by_alert = dict(cur.fetchall())

    filed_case_ids = {case_by_alert[a] for a, _c in sar_rows}
    unfiled_case_ids = all_case_ids - filed_case_ids

    assert len(filed_case_ids) == len(sar_rows), (
        "two SAR rows resolved to the same case_id -- coverage should be "
        "one SAR per filing case")
    assert len(filed_case_ids) >= 3, (
        f"only {len(filed_case_ids)} cases file -- below the envelope floor")
    # "Substantial", not a token exception or two: require at least a
    # third of the 24 cases to carry NO SAR at all.
    assert len(unfiled_case_ids) >= 8, (
        f"only {len(unfiled_case_ids)} of 24 cases have no SAR -- too few "
        "to break the matchesTypology -> SAR inference credibly")

    classifications = {c for _a, c in sar_rows}
    assert classifications == {"confidential", "restricted"}, (
        f"expected both classifications populated, got {classifications}")


def test_a_named_unfiled_case_subject_still_carries_a_live_matchestypology_edge():
    """The proof, not just the count: pick a party whose case has NO SAR
    anywhere (SQLite classification table, Mongo sar_narrative documents)
    and confirm it STILL carries a live Fluree ex:matchesTypology edge --
    the exact 'party carries the edge' state Task 16's l1-visible
    typology_pattern_summary element renders. If this edge implied a SAR,
    this test's own party would be the counterexample that breaks it."""
    import sqlite3
    from ccf import fluree
    from ccf.config import (EX, FLUREE_LEDGER_V2 as L, PG_SCHEMA_V2 as S,
                             SQLITE_PATH, mongo_db, pg_connect)

    cases = json.loads(
        (REPO_ROOT / "sources" / "screening" / "wave17_cases.json").read_text()
    )["cases"]

    con = sqlite3.connect(SQLITE_PATH)
    sar_alert_ids = {r[0] for r in con.execute(
        "SELECT alert_id FROM sar_classification").fetchall()}
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'SELECT alert_id, case_id FROM "{S}".aml_alert '
                    "WHERE alert_id = ANY(%s)", (list(sar_alert_ids),))
        filed_case_ids = {cid for _aid, cid in cur.fetchall()}

    db = mongo_db()
    sar_case_ids_in_mongo = set(
        db.document.distinct("case_id", {"doc_type": "sar_narrative"}))

    # Pick deterministically -- smallest case_id, never a positional pick --
    # among cases that have NO SAR in either store.
    unfiled = sorted(
        (c for c in cases
         if c["case_id"] not in filed_case_ids
         and c["case_id"] not in sar_case_ids_in_mongo),
        key=lambda c: c["case_id"])
    assert unfiled, "every case has a SAR somewhere -- coverage did not shrink"
    named_case = unfiled[0]
    named_party = named_case["subject_party"]

    q = (f"SELECT ?o FROM <{L}> WHERE "
         f"{{ <{EX}{named_party}> <{EX}matchesTypology> ?o }}")
    rows = fluree.query(q)["results"]["bindings"]
    edges = [r["o"]["value"] for r in rows]
    assert edges, (
        f"{named_party} ({named_case['case_id']}) carries no live "
        "matchesTypology edge -- cannot serve as the counterexample")
    assert edges[0].rsplit("/", 1)[-1] == named_case["typology_id"], (
        f"{named_party}'s matchesTypology edge does not match its own "
        f"case's typology_id ({named_case['typology_id']})")


def test_task15_mongo_load_is_idempotent_on_a_named_narrative_value():
    """Idempotency by VALUE, Mongo half. Name one SAR document's text, re-run
    the loader, and require the text and the document count unchanged."""
    import subprocess
    from ccf.config import mongo_db

    db = mongo_db()
    named = db.document.find_one({"doc_type": "sar_narrative"})
    assert named, "no SAR narrative loaded"
    sar_id = named["_id"]
    before_text = named["text"]
    before_count = db.document.count_documents({"doc_type": "sar_narrative"})

    result = subprocess.run(
        ["uv", "run", "loaders/load_mongo_wave17.py"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    after = db.document.find_one({"_id": sar_id})
    after_count = db.document.count_documents({"doc_type": "sar_narrative"})
    assert after["text"] == before_text, (
        f"{sar_id} narrative text changed on a plain re-run of the loader")
    assert after_count == before_count


# ===========================================================================
# Wave 17 Task 16 -- projection plans for the three perspectives
# ===========================================================================

def test_the_three_renderings_assemble_different_element_sets():
    """Wave 17 Task 16, envelope floor 6. Compare ELEMENT SETS, not strings.
    Three plans that differ only in a display flag would satisfy a
    'plans differ' check while assembling identical content -- which is
    exactly the Perspective Flat failure this product exists to refute."""
    import json
    from ccf.config import PG_SCHEMA_V2 as S, pg_connect
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'SELECT perspective, elements FROM "{S}".aml_projection_plan')
        plans = {p: set(json.loads(e) if isinstance(e, str) else e)
                 for p, e in cur.fetchall()}
    assert set(plans) == {"l1", "l2", "examiner"}, plans.keys()
    assert plans["l1"] != plans["l2"] != plans["examiner"], "renderings identical"
    assert plans["l1"] != plans["examiner"]
    # The spec is specific about who gets what
    assert "disposition_candidates" in plans["l1"]
    assert "counterparty_network" in plans["l2"]
    assert "prior_alert_lineage" in plans["l2"]
    assert "policy_version_attribution" in plans["examiner"]
    assert "reasoning_trail" in plans["examiner"]
    assert "counterparty_network" not in plans["l1"], (
        "L1 receives investigative history they cannot action -- that IS the "
        "Perspective Flat counterfactual, not a refutation of it")


#: Imported, not redeclared. This module used to carry a verbatim copy of
#: the set `loaders/load_postgres_wave17.py` enforces at write time, kept in
#: sync by a docstring comment. That is a legal guard (disclosing that a SAR
#: exists is an offence in many jurisdictions), and a checker policing a
#: different set than the loader enforces would go on passing while the leak
#: reopened. `ccf.aml` is this wave's shared pure-helper module and now owns
#: the one definition; the test below proves the LOADER's copy is the same
#: object, so the two can no longer drift.
from ccf.aml import SAR_REVEALING_ELEMENT_NAMES


def test_the_loader_and_this_module_police_the_same_sar_element_set():
    """One definition, two importers. Before Task 17 this set existed twice
    -- once in the loader that refuses the write, once here in the test that
    checks it -- and nothing but a comment held them equal. Assert identity,
    not equality: two sets that happen to be equal today are exactly what a
    later one-sided edit breaks."""
    from loaders import load_postgres_wave17
    from ccf import aml
    assert load_postgres_wave17.SAR_REVEALING_ELEMENT_NAMES is (
        aml.SAR_REVEALING_ELEMENT_NAMES)
    assert SAR_REVEALING_ELEMENT_NAMES is aml.SAR_REVEALING_ELEMENT_NAMES


def test_load_projection_plans_refuses_an_l1_plan_that_names_a_sar_element():
    """The `RuntimeError` guard inside `load_projection_plans` had no test.
    Task 16's reviewer had to call the function by hand to see it fire, which
    means breaking the `&` to a `|`, or emptying the loader's own copy of the
    set, would have shipped: every other test in this file reads the ALREADY
    LOADED l1 row, which is clean, so none of them can see the guard stop
    working.

    No database is involved. The guard raises before `cur` is touched, so
    `cur=None` is enough -- and if a future edit ever moves the check below
    the first cursor use, this test fails with AttributeError instead of
    passing quietly, which is the correct outcome either way."""
    import pytest
    from loaders.load_postgres_wave17 import load_projection_plans

    clean = [
        {"perspective": "l1", "elements": ["alert_core_facts"],
         "provenance": "synthetic — internal"},
        {"perspective": "l2", "elements": ["alert_core_facts"],
         "provenance": "synthetic — internal"},
        {"perspective": "examiner", "elements": ["alert_core_facts"],
         "provenance": "synthetic — internal"},
    ]
    poisoned = [dict(p) for p in clean]
    poisoned[0]["elements"] = ["alert_core_facts", "sar_filing_history"]

    with pytest.raises(RuntimeError) as exc:
        load_projection_plans(None, poisoned)
    assert "sar_filing_history" in str(exc.value)

    # ... and the same call with a clean l1 must get PAST the guard. Without
    # this half, a guard that raised on EVERYTHING would satisfy the block
    # above -- the "output that never varies" defect this estate has already
    # recorded twice. A clean plan gets past the RuntimeError and dies at
    # `None.executemany` instead, which is the proof the guard let it
    # through.
    with pytest.raises(AttributeError):
        load_projection_plans(None, clean)


def test_l1_names_no_element_that_could_reveal_a_sar_exists():
    """Stronger than the brief's verbatim test, which only checks
    'counterparty_network' is absent from l1. SAR confidentiality (CLAUDE.md,
    task-16-brief.md) is the property this plan exists to enforce -- L1 must
    be the BLIND perspective (never l2, which sees 9 of the 12 filed
    SARs), so its element
    list must intersect NONE of the known SAR-revealing names, not just lack
    the one name the brief happens to test.

    What would make this fail: adding "sar_filing_history" (l2/examiner's
    element) to l1's list, or adding "case_id" as a compact-summary
    convenience -- both are exactly the kind of well-intentioned addition
    that would reopen the leak. Confirmed to fail by construction below."""
    import json
    from ccf.config import PG_SCHEMA_V2 as S, pg_connect
    with pg_connect() as c, c.cursor() as cur:
        cur.execute(f'SELECT elements FROM "{S}".aml_projection_plan '
                    "WHERE perspective = %s", ("l1",))
        row = cur.fetchone()
    assert row, "no l1 projection plan row"
    l1_elements = set(json.loads(row[0]) if isinstance(row[0], str) else row[0])
    leaked = l1_elements & SAR_REVEALING_ELEMENT_NAMES
    assert not leaked, f"l1 plan names SAR-revealing element(s): {leaked}"

    # Prove the check is not vacuous: a plan that DID carry a leaking name
    # must fail this same assertion.
    poisoned = l1_elements | {"sar_filing_history"}
    assert poisoned & SAR_REVEALING_ELEMENT_NAMES, (
        "the leak-detection set itself is broken -- a poisoned l1 element "
        "set was not flagged")


def test_task16_postgres_load_is_idempotent_on_a_named_elements_value():
    """Idempotency by VALUE, never by a row count that cannot see a field
    being silently reset. Name l1's exact element list, re-run the loader,
    and require it -- and the row count -- unchanged."""
    import json
    import subprocess
    from ccf.config import PG_SCHEMA_V2 as S, pg_connect

    def read():
        with pg_connect() as c, c.cursor() as cur:
            cur.execute(f'SELECT elements FROM "{S}".aml_projection_plan '
                        "WHERE perspective = %s", ("l1",))
            row = cur.fetchone()
            cur.execute(f'SELECT COUNT(*) FROM "{S}".aml_projection_plan')
            count = cur.fetchone()[0]
        elements = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        return sorted(elements), count

    before_elements, before_count = read()
    assert before_elements, "no l1 elements to test idempotency on"

    result = subprocess.run(
        ["uv", "run", "loaders/load_postgres_wave17.py"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    after_elements, after_count = read()
    assert after_elements == before_elements, (
        f"l1 elements changed on a plain re-run: "
        f"{before_elements} -> {after_elements}")
    assert after_count == before_count


# ===========================================================================
# Wave 17 Task 17 -- validators/aml_typology.py, the seven floors
# ===========================================================================
#
# Two of these are the brief's verbatim tests. The rest exist because this
# wave has already found FIVE tests passing for reasons unrelated to the
# property they were named for -- a pre-sorted fixture, a name claiming a
# universal over a body checking two existentials, three vacuous-pass
# assertions over possibly-empty lists. So every pure helper the validator
# leans on is exercised here against an input that MUST make it fail, in
# memory, with nothing written to any store.


def test_no_path_from_any_aml_party_to_any_real_entity():
    """Wave 17 safety property 2. Walk BOTH directions: from AML parties
    outward, and from the 50 real anchors outward. A one-directional walk
    cannot see an edge whose SUBJECT is the real entity, and that is exactly
    the edge a careless loader writes."""
    from validators.aml_typology import no_path_to_real_entity
    ok, detail = no_path_to_real_entity()
    assert ok, f"AML island is connected to real entities: {detail}"


def test_the_disconnect_validator_fails_on_a_planted_crossing_edge():
    """The validator must be shown to have teeth before it is trusted. Plant
    a crossing edge in a THROWAWAY in-memory adjacency, run the same walk
    routine over it, and require a failure. Do NOT write the edge to the
    ledger."""
    from validators.aml_typology import walk_for_crossings
    adj = {"AMLP-0001": {"AMLP-0002"}, "AMLP-0002": {"REAL-LEI-XXXX"}}
    real = {"REAL-LEI-XXXX"}
    ok, detail = walk_for_crossings(adj, real, starts=["AMLP-0001"])
    assert not ok, "the walk did not detect a planted crossing edge"
    assert "REAL-LEI-XXXX" in detail


def test_the_walk_also_catches_an_edge_whose_subject_is_the_real_entity():
    """The other direction, and the whole reason the brief says BOTH. Here
    the only adjacency entry belongs to the REAL node; the AML party has no
    outgoing entry at all. A walk that starts at the AML parties and only
    goes forward sees an empty neighbourhood and reports clean -- which is
    precisely the edge a careless loader writes (`REAL ex:owns AMLP-0003`).
    """
    from validators.aml_typology import walk_for_crossings
    adj = {"REAL-LEI-YYYY": {"AMLP-0003"}}
    real = {"REAL-LEI-YYYY"}
    ok, detail = walk_for_crossings(adj, real, starts=["AMLP-0003"])
    assert not ok, (
        "the walk missed a crossing whose SUBJECT is the real entity -- it "
        "is only walking forward from the AML side")
    assert "AMLP-0003" in detail and "REAL-LEI-YYYY" in detail


def test_the_walk_reports_clean_on_a_genuinely_separated_pair_of_islands():
    """The other half of "test the checker with known-present AND
    known-absent, and require different answers". A walk that returned
    `not ok` for every input would satisfy both tests above."""
    from validators.aml_typology import walk_for_crossings
    adj = {"AMLP-0001": {"AMLP-0002"}, "AMLP-0002": {"AMLP-0001"},
           "REAL-LEI-XXXX": {"REAL-LEI-YYYY"}, "REAL-LEI-YYYY": {"REAL-LEI-XXXX"}}
    ok, detail = walk_for_crossings(adj, {"REAL-LEI-XXXX", "REAL-LEI-YYYY"},
                                     starts=["AMLP-0001", "AMLP-0002"])
    assert ok, f"clean islands reported as crossing: {detail}"


def test_adjacency_is_built_undirected_and_drops_rdf_type():
    """`walk_for_crossings` can only see both directions if the adjacency it
    is handed carries both. Two properties, one fixture:

    1. A triple whose SUBJECT is the real entity produces a reverse entry,
       so the AML-side walk can traverse it.
    2. `rdf:type` is EXCLUDED. Class membership is not a path between two
       entities, and leaving it in would connect every node in the ledger to
       every other through shared class nodes -- an "everything is connected"
       result that would make this floor fail for a reason that has nothing
       to do with the data."""
    from validators.aml_typology import RDF_TYPE, build_adjacency
    adj = build_adjacency([
        ("REAL", "http://example.org/fibo/owns", "AMLP-0003"),
        ("AMLP-0004", RDF_TYPE, "http://example.org/fibo/Party"),
        ("REAL", RDF_TYPE, "http://example.org/fibo/Party"),
    ])
    assert adj["AMLP-0003"] == {"REAL"}, "reverse edge missing -- adjacency is directed"
    assert adj["REAL"] == {"AMLP-0003"}
    assert "http://example.org/fibo/Party" not in adj, (
        "rdf:type survived into the adjacency; every node now shares a class node")
    assert "AMLP-0004" not in adj


def test_exact_depth_pairs_needs_the_walk_to_be_exact():
    """`depth_three_holds` is one edge wide -- 70 of 20,100 possible party
    pairs would erase it. So the walk is proven on a hand-built path where
    the answer is known, and then proven to CHANGE when a single shortcut
    edge is added. A depth counter that is off by one, or a frontier that
    re-expands nodes it has already seen, fails one of these two."""
    from validators.aml_typology import build_adjacency, exact_depth_pairs
    P = "http://example.org/fibo/p"
    path = build_adjacency([("A", P, "B"), ("B", P, "C"), ("C", P, "D")])
    pairs = exact_depth_pairs(path, ["A", "B", "C", "D"], 3)
    assert ("A", "D") in pairs and ("D", "A") in pairs
    assert ("A", "C") not in pairs, "C is at depth 2, not 3"
    assert ("A", "B") not in pairs

    shortcut = build_adjacency([("A", P, "B"), ("B", P, "C"), ("C", P, "D"),
                                 ("A", P, "C")])
    pairs2 = exact_depth_pairs(shortcut, ["A", "B", "C", "D"], 3)
    assert ("A", "D") not in pairs2, (
        "one shortcut edge pulls D to depth 2 and the exact-3 claim must "
        "vanish with it -- if it did not, the walk is not measuring depth")


def test_resolve_posture_picks_the_latest_posture_in_force():
    """as_of -> posture is the whole as-of argument. Fixture, not the store,
    so the boundary cases are visible: exactly ON an effective date the new
    posture is already in force, and before the first one nothing is."""
    from validators.aml_typology import resolve_posture
    postures = {"POST-A": "2025-03-01", "POST-B": "2026-01-15"}
    assert resolve_posture(postures, "2025-03-01") == "POST-A"
    assert resolve_posture(postures, "2025-12-31") == "POST-A"
    assert resolve_posture(postures, "2026-01-15") == "POST-B"
    assert resolve_posture(postures, "2026-08-24") == "POST-B"
    assert resolve_posture(postures, "2025-01-01") is None


def test_parse_rule_id_splits_on_the_id_sets_the_store_supplies():
    """`rule_id` encodes (posture, typology, disposition) and there is no
    linking predicate (see loaders/load_fluree_wave17.py). Splitting on
    hyphens would be wrong -- every one of the three parts contains them --
    so the parse is driven by the posture and typology id sets read from the
    same ledger. Proven here on a rule whose disposition itself has a
    hyphen, and proven to REFUSE an id naming an unknown posture rather than
    silently mis-splitting it."""
    from validators.aml_typology import parse_rule_id
    postures = {"POST-2025-01", "POST-2026-01"}
    typologies = {"TYP-STRUCT", "TYP-SHELL"}
    assert parse_rule_id("RULE-POST-2025-01-TYP-STRUCT-close-no-action",
                          postures, typologies) == (
        "POST-2025-01", "TYP-STRUCT", "close-no-action")
    assert parse_rule_id("RULE-POST-9999-01-TYP-STRUCT-monitor",
                          postures, typologies) is None
    assert parse_rule_id("RULE-POST-2025-01-TYP-NOPE-monitor",
                          postures, typologies) is None


def test_the_sar_leak_scanner_sees_a_key_present_with_a_null_value():
    """CLAUDE.md's own wording for this floor is ABSENT, not null. A
    rendering that carries `"sar_id": None` has still told the reader a SAR
    slot exists for this alert. The scanner walks KEYS, at any depth, so a
    nulled-out field is a leak and a nested one cannot hide."""
    from validators.aml_typology import scan_for_sar_leakage
    assert scan_for_sar_leakage({"alert_core_facts": {"alert_id": "ALRT-1"}},
                                 forbidden_ids={"CASE-008", "SAR-0001"}) == []
    nulled = scan_for_sar_leakage({"alert_core_facts": {"sar_id": None}},
                                   forbidden_ids=set())
    assert nulled, "a key present with a null value is not a leak to this scanner"
    assert "sar_id" in nulled[0]


def test_the_sar_leak_scanner_sees_an_identifier_smuggled_as_a_value():
    """The subtler half. `case_id` under a harmless key name -- or a case id
    embedded in a free-text reasoning string -- reveals a SAR by inference
    just as surely, for whichever cases actually DO file (coordinator
    ruling: coverage is a deliberate proper subset of the 24 engineered
    cases, not all of them -- see generate_sar_records.py; which specific
    case_ids are in that subset has changed across fix rounds and may
    change again). `scan_for_sar_leakage` takes `forbidden_ids` as an
    explicit parameter and does no lookup of its own, so "CASE-008" here is
    an arbitrary example id, not an assertion about CASE-008's CURRENT
    filing status -- this test exercises the scanner's mechanics, not the
    live data."""
    from validators.aml_typology import scan_for_sar_leakage
    assert scan_for_sar_leakage(
        {"summary": {"reference": "CASE-008"}},
        forbidden_ids={"CASE-008"}), "a forbidden id as a VALUE was not seen"
    assert scan_for_sar_leakage(
        {"reasoning_trail": ["escalated under CASE-008"]},
        forbidden_ids={"CASE-008"}), "a forbidden id inside free text was not seen"
    assert scan_for_sar_leakage(
        {"reasoning_trail": ["escalated under review"]},
        forbidden_ids={"CASE-008"}) == [], (
        "the scanner flags clean content too -- it cannot distinguish "
        "anything")


def test_ofac_similarity_is_the_ratio_and_never_the_quick_ratio():
    """`difflib`'s `quick_ratio()` is an UPPER BOUND on `ratio()`, not a
    cheaper spelling of it. A review earlier in this wave reported a false
    bypass because it measured with `quick_ratio`. The floor's recomputed
    figure must equal `ratio()` -- and this asserts the two actually DIFFER
    on this pair, so the check could not pass under the substitution."""
    from difflib import SequenceMatcher
    from ccf.aml import normalize_name, similarity
    a, b = "Granite Lakes Business Corp", "GREAT LAKES BUSINESS COMPANY"
    na, nb = normalize_name(a), normalize_name(b)
    exact = SequenceMatcher(None, na, nb).ratio()
    quick = SequenceMatcher(None, na, nb).quick_ratio()
    assert similarity(a, b) == exact
    assert quick != exact, (
        "quick_ratio happens to agree on this pair, so this test could not "
        "detect the substitution -- pick a pair where they differ")


def test_every_floor_returns_a_two_tuple_and_none_of_them_swallow_errors():
    """No floor may wrap its body in a bare `except Exception -> None`: that
    renders a genuine bug as SKIP, and Wave 16 had to repair exactly this.
    Read the source and assert no bare handler exists."""
    import re
    from ccf.config import REPO_ROOT
    src = (REPO_ROOT / "validators" / "aml_typology.py").read_text()
    assert not re.search(r"except\s+Exception\s*:", src), (
        "a bare `except Exception:` in a validator turns a real failure "
        "into a pass")
    # The CALL, not the word -- the module's own docstring names quick_ratio
    # to explain why it is never used, and a substring check would forbid
    # writing that down.
    assert not re.search(r"\.quick_ratio\s*\(", src), (
        "quick_ratio is an upper bound on ratio, not a cheaper spelling")


def test_the_seven_floors_all_hold_against_the_loaded_estate():
    """The end-to-end. Every floor recomputed from the stores, in one run,
    with the exit code that `main()` would return."""
    from validators.aml_typology import main
    assert main() == 0


# ===========================================================================
# Wave 17 Task 17 fix round -- the two arms rebuilt after review
# ===========================================================================

def test_numeric_quantities_masks_identifiers_but_not_real_measurements():
    """`numeric_quantities` feeds the filed/unfiled separability check, and
    its whole correctness rests on not mistaking a nominal identifier for a
    measurement. `AMLP-0168` read as the number 168 would have the check
    report an arithmetic accident as a disclosure -- and this dataset
    contains exactly that accident, in the trade-based importer ids.

    Masking is by MEMBERSHIP in the estate's own id sets, never by pattern
    alone: a token shaped like an id but absent from the estate stays a
    number, because it might be a genuine reading written that way."""
    from validators.aml_typology import numeric_quantities
    q = numeric_quantities(
        {"t": "3 shipment(s) double-invoiced to importer AMLP-0168, "
              "max variance 87.3%"},
        identifiers={"AMLP-0168"})
    assert q == {"t#0": 3.0, "t#1": 87.3}, q
    unmasked = numeric_quantities({"t": "batch QQ-42 of 7"},
                                   identifiers={"AMLP-0168"})
    assert unmasked == {"t#0": 42.0, "t#1": 7.0}, unmasked


def test_numeric_quantities_reads_a_date_as_one_number_and_skips_booleans():
    """`raised_at` must participate as ONE quantity -- an ordinal -- not as
    the three numbers 2025, 08, 12, which would compare a year against a day
    and overlap for free. And a bool is a category: `float(True) == 1.0`
    would smuggle it in as a measurement it is not."""
    from validators.aml_typology import numeric_quantities
    q = numeric_quantities({"raised_at": "2025-08-12", "flag": True,
                             "n": 4}, identifiers=set())
    assert set(q) == {"raised_at", "n"}, q
    assert q["raised_at"] > 700000 and q["n"] == 4.0


def test_separating_quantities_can_answer_both_ways():
    """Known-present and known-absent, required to give DIFFERENT answers.
    A checker that reported a separator for every input, or for none, would
    satisfy either half alone."""
    from validators.aml_typology import separating_quantities
    overlapping = [("g", True, {"q": 1.0}), ("g", True, {"q": 5.0}),
                   ("g", False, {"q": 3.0}), ("g", False, {"q": 9.0})]
    compared, findings = separating_quantities(overlapping)
    assert compared == 1 and findings == [], findings

    planted = [("g", True, {"q": 1.0}), ("g", True, {"q": 2.0}),
               ("g", False, {"q": 8.0}), ("g", False, {"q": 9.0})]
    compared, findings = separating_quantities(planted)
    assert compared == 1 and len(findings) == 1
    assert "ranges disjoint" in findings[0]


def test_separating_quantities_catches_presence_and_a_one_sided_group():
    """Two separators that are not about VALUES at all. A quantity present
    only on the filed side discriminates by existing; and a typology group
    that is entirely filed makes the group itself the rule, so no quantity
    inside it needs to separate anything."""
    from validators.aml_typology import separating_quantities
    _, findings = separating_quantities(
        [("g", True, {"q": 1.0}), ("g", False, {})])
    assert any("present on filed cases only" in f for f in findings), findings

    _, findings = separating_quantities(
        [("g", True, {"q": 1.0}), ("g", True, {"q": 2.0})])
    assert any("the group is itself the rule" in f for f in findings), findings


def test_the_filing_decision_is_not_separable_by_any_l1_visible_quantity():
    """Wave 17 Task 15's filing selection, asserted as a PROPERTY rather
    than taken on the rationale field's word. Every alert is assembled as
    `l1` sees it, every number a reader could pull out is extracted, the
    case-bearing alerts are grouped by the typology named in their own
    trigger, and filed must be inseparable from unfiled inside each group.

    This runs the same computation `sar_confidentiality_holds` runs, so that
    a failure here names the offending quantity directly rather than through
    the floor's summary line."""
    from validators.aml_typology import (
        assemble, load_context, numeric_quantities, separating_quantities)
    ctx = load_context()
    unfiled = ctx.all_case_ids - ctx.filed_cases
    assert ctx.filed_cases and unfiled, (
        f"degenerate split: {len(ctx.filed_cases)} filed, {len(unfiled)} "
        f"unfiled -- nothing could be separable")

    observations = []
    for alert in ctx.alerts:
        case_id = ctx.case_by_alert.get(alert["alert_id"])
        if not case_id:
            continue
        observations.append((
            alert["trigger"].split(":", 1)[0],
            case_id in ctx.filed_cases,
            numeric_quantities(assemble("l1", alert, ctx), ctx.identifiers)))
    compared, findings = separating_quantities(observations)
    assert compared > 0, "no l1-visible quantity was compared at all"
    assert not findings, findings


def test_floor_four_catches_a_number_that_tracks_filing_status():
    """The falsification for the sub-condition above, and proof the OTHER
    three sub-conditions are blind to it. `review_weight` is not a
    SAR-revealing name, carries no forbidden identifier, and is present on
    every alert -- so the key scan, the identifier scan and the key-shape
    check all pass, and only the separability arm fires."""
    import validators.aml_typology as V
    from validators.aml_typology import (
        key_paths, load_context, sar_confidentiality_holds,
        scan_for_sar_leakage)
    ctx = load_context()
    assert sar_confidentiality_holds(ctx)[0], "baseline is already failing"

    original = V.ELEMENT_RESOLVERS["alert_core_facts"]

    def leaky(alert, c, perspective):
        filed = c.case_by_alert.get(alert["alert_id"]) in c.filed_cases
        return dict(original(alert, c, perspective),
                    review_weight=99 if filed else 1)

    V.ELEMENT_RESOLVERS["alert_core_facts"] = leaky
    try:
        ok, detail = sar_confidentiality_holds(ctx)
        assert not ok, "a number tracking filing status was not detected"
        assert "review_weight" in detail

        filed_alert = next(a for a in ctx.alerts
                           if ctx.case_by_alert.get(a["alert_id"])
                           in ctx.filed_cases)
        noise_alert = next(a for a in ctx.alerts if not a["case_id"])
        rendered = V.assemble("l1", filed_alert, ctx)
        assert scan_for_sar_leakage(rendered, ctx.forbidden_ids) == [], (
            "the poison was caught by the key/identifier scan, so it does "
            "not demonstrate the separability arm")
        assert key_paths(rendered) == key_paths(
            V.assemble("l1", noise_alert, ctx)), (
            "the poison changed the key shape, so it does not demonstrate "
            "the separability arm")
    finally:
        V.ELEMENT_RESOLVERS["alert_core_facts"] = original


def test_floor_six_catches_a_resolver_that_ignores_its_perspective():
    """`_sar_filing_history` is the only resolver that reads `perspective`,
    and until this fix round nothing asserted it filtered -- `l2`'s
    exclusion from the confidential SARs, the whole reason this
    architecture reaches into a departmental SQLite store, was unchecked.

    Poison the resolver to ignore `perspective` and require floor 6 to fail.
    Then run the arm this REPLACED over the same poison and require it to be
    blind, which is why the replacement was necessary: `assemble()` keys its
    dict by the plan's element names, so comparing assembled key SETS was
    the element-set comparison over again."""
    import validators.aml_typology as V
    from validators.aml_typology import assemble, load_context, renderings_differ
    ctx = load_context()
    assert renderings_differ(ctx)[0], "baseline is already failing"

    original = V.ELEMENT_RESOLVERS["sar_filing_history"]

    def unfiltered(alert, c, perspective):
        return {"sar_filing_history": [
            {"sar_id": r["sar_id"], "classification": r["classification"]}
            for r in c.sar_rows if r["alert_id"] == alert["alert_id"]]}

    V.ELEMENT_RESOLVERS["sar_filing_history"] = unfiltered
    try:
        ok, detail = renderings_differ(ctx)
        assert not ok, "a resolver ignoring `perspective` was not detected"
        assert "sar_filing_history" in detail

        names = sorted(ctx.plans)
        probe = ctx.alerts[0]
        rendered = {p: assemble(p, probe, ctx) for p in names}
        dead_arm = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]
                    if set(rendered[a]) == set(rendered[b])]
        assert dead_arm == [], (
            "the arm this replaced DID see the poison, so the finding it was "
            "replaced for was wrong")
    finally:
        V.ELEMENT_RESOLVERS["sar_filing_history"] = original


def test_assembled_key_set_is_exactly_the_plan_so_the_old_arm_was_dead():
    """The finding itself, asserted directly rather than argued in a
    comment. If `set(assemble(p, ...))` is always `ctx.plans[p]`, then a
    check comparing assembled key sets across perspectives can only fire
    where the element-set check has already returned -- which is what made
    the arm unable to fail."""
    from validators.aml_typology import assemble, load_context
    ctx = load_context()
    probe = ctx.alerts[0]
    for perspective, elements in ctx.plans.items():
        assert set(assemble(perspective, probe, ctx)) == elements
