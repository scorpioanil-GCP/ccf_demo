# Wave 17 — `aml-typology-match` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `aml-typology-match` Context Product across all five
stores — invented parties and transactions exhibiting four FinCEN-anchored
laundering typologies — with two safety properties proved rather than
asserted.

**Architecture:** Extract typology patterns from FinCEN advisories first, so
every match cites the passage that defines it; build an ordinary transaction
population second, so the noise alerts are genuine noise; inject the
engineered pattern instances last, into a population that already exists.
The person and beneficial-ownership layer is inherited from
`kyc-refresh-beneficial-ownership` rather than rebuilt.

**Tech Stack:** Python 3 + `uv`, Postgres (`psycopg`), Fluree (SPARQL over
HTTP), MongoDB (`pymongo`), SQLite (stdlib), `pytest`.

**Spec:** `docs/wave17-design.md` — read it before Task 1. The vault spec it
argues from is `context-products/aml-typology-match`, retrieved 2026-08-24.

---

## Global Constraints

Every task's requirements implicitly include this section.

- **CLAUDE.md rule 2 is a legal constraint, not a style preference.** No
  named real company and no real natural person may appear as a party,
  counterparty, alert subject, transaction participant, or beneficial owner.
  Enforce at generation time. A generator that can emit a forbidden entity
  and relies on review has already failed.
- **Two person populations, opposite safety properties.** `PSC-####` keys
  touch no real company (0 rows in `person_role`). Numeric keys (`0001*`,
  `0002*`, `0000*`) are officers **of** real companies — 817 `person_role`
  rows join `legal_entity`. **Wave 17 may use `PSC-*` and must never use a
  numeric person key.**
- **Stores.** Fluree ledger `FLUREE_LEDGER_V2` (`fibo-v2`), Mongo db
  `MONGO_DB_V2` (`fibo_v2`), Postgres schema `PG_SCHEMA_V2` (`ccf_v2`),
  SQLite `SQLITE_PATH` (`data/departmental.sqlite`). **Read these from
  `ccf.config`; never hardcode the literals** — CLAUDE.md's own table was
  stale for many waves.
- **Provenance labelled per element**, one of `public`,
  `synthetic — internal`, `synthetic — engineered`. Every party,
  transaction, alert, SAR, posture version, disposition rule and projection
  plan in this wave is synthetic. Only advisory text, sanctions entries and
  adverse media are `public`.
- **Single-writer discipline.** No element is duplicated into a store §C
  does not name. Fluree nodes carry identity and typed edges; attributes
  resolve from Postgres.
- **No OWL inference.** Type every node explicitly for every role it must be
  queried against.
- **New FIBO/`ex:` terms** are verified absent against
  `sources/fibo/dev.fibo-quickstart.ttl` — **never `prod`**, which omits 40
  Provisional modules — using `ccf.fibo.fibo_absent()`, which requires a
  positive control to fire before any negative result is trusted. **Never
  verify a term by fetching its URL**; `spec.edmcouncil.org` returns HTTP
  200 for names that do not exist.
- **Idempotency.** Every loader is safely re-runnable. Prove it by naming a
  VALUE that must survive a second run, never by comparing a row count — a
  count cannot see a field being reset.
- **Positional identity is a defect class here (5 recorded instances).**
  Never key anything to a row's position in a query result. Derive ids from
  the row's own content.
- **Test commands.** `uv run --with pytest pytest` — plain `uv run pytest`
  is broken repo-wide. Read validator results from the PASS count, never
  from a "0 failed" line, because SKIP hides a broken query.
- **Commit messages:** no backticks inside a shell heredoc — this repo has
  lost words to substitution twice. Write the message to a file with a
  quoted heredoc and grep it before committing.

---

## File Structure

| File | Responsibility |
|---|---|
| `generators/select_fincen_advisories.py` | Enumerate the FinCEN index, match four typologies to real advisories, emit a reviewable artifact |
| `generators/fetch_fincen_advisories.py` | Fetch the selected advisory PDFs with manifest and retrieval dates |
| `generators/extract_advisory_passages.py` | PDF → text → passages with span offsets |
| `generators/derive_typology_patterns.py` | Advisory passages → structural pattern definitions |
| `generators/generate_aml_parties.py` | 200 invented companies + the real-entity name guard |
| `generators/generate_aml_transactions.py` | Ordinary 18-month transaction population |
| `generators/inject_typology_cases.py` | The engineered pattern instances, incl. the depth-3 network |
| `generators/generate_aml_alerts.py` | 150 alerts, ~30 genuine among noise, plus prior-alert links |
| `generators/generate_aml_policy.py` | Two posture versions with the disposition flip, disposition rules |
| `generators/generate_sar_records.py` | SAR narratives and confidentiality classifications |
| `ccf/aml.py` | Pure helpers: name-similarity, typology vocabulary, party-key form checks. No I/O |
| `loaders/load_postgres_wave17.py` | DDL + parties, transactions, alerts, projection plans |
| `loaders/load_fluree_wave17.py` | Typed nodes, `transactedWith`, ownership binding, typology patterns, posture and disposition layer |
| `loaders/load_mongo_wave17.py` | Advisory documents, passages, SAR narratives |
| `loaders/load_sqlite_wave17.py` | `sar_classification` |
| `validators/aml_typology.py` | The six floors and the two safety properties, recomputed live |
| `validators/test_aml_typology.py` | Tests for the validator itself, incl. falsification fixtures |

---

## Task 1: Select the four advisories

The design names this as the task whose output is reviewed before anything
is built on it. Do not guess advisory numbers.

**Files:**
- Create: `generators/select_fincen_advisories.py`
- Create: `sources/fincen/selection.json`
- Test: `validators/test_aml_typology.py` (created here, extended later)

**Interfaces:**
- Produces: `sources/fincen/selection.json` with shape
  `{"retrieved_at": "<ISO8601>", "index_url": str, "typologies":
  [{"typology": "structuring"|"funnel_account"|"rapid_pass_through"|"trade_based",
    "advisory_number": str, "title": str, "issued": "YYYY-MM-DD",
    "url": str, "pdf_url": str, "matched_on": str}]}`

  **`pdf_url` is RESOLVED from the advisory page, never constructed.** A
  probe on 2026-08-24 found the same site serving PDFs under BOTH
  `/sites/default/files/advisory/...` and `/system/files/...`; a fetcher
  that builds either path by pattern will 404 on half the corpus while
  looking correct. Parse the `.pdf` href out of the advisory page HTML.
  This estate has already been burned by an assumed index
  (`EDGAR index.json is incomplete`) — resolve from the document.

- [ ] **Step 1: Write the failing test**

```python
# validators/test_aml_typology.py
import json
from ccf.config import REPO_ROOT

REQUIRED_TYPOLOGIES = {
    "structuring", "funnel_account", "rapid_pass_through", "trade_based",
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
```

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run --with pytest pytest validators/test_aml_typology.py -q`
Expected: FAIL — `sources/fincen/selection.json` does not exist.

- [ ] **Step 3: Write the selector**

The FinCEN index at
`https://www.fincen.gov/resources/advisoriesbulletinsfact-sheets` is
paginated and lists recent advisories first; the typologies this product
needs are older than page 1. Walk the pagination with `?page=N` until a page
yields no new advisory links or a page cap is hit, collect
`(url, title, issued)` for each, then match titles and subject text against
the keyword sets below. **Record `matched_on` as the actual text that
matched**, so a reviewer can audit the choice.

```python
TYPOLOGY_KEYWORDS = {
    "structuring":        ("structuring", "structured transaction",
                           "below the reporting threshold"),
    "funnel_account":     ("funnel account", "funnel"),
    "rapid_pass_through": ("pass-through", "pass through", "rapid movement",
                           "flow-through"),
    "trade_based":        ("trade-based money laundering", "trade based",
                           "over-invoicing", "under-invoicing"),
}
```

Rate-limit politely (the estate's `ccf.fetch` carries a limiter; reuse it)
and identify the client honestly in the user agent.

**If a typology finds no advisory, exit non-zero and say which one.** Do not
emit a partial selection that a later task will silently build on.

- [ ] **Step 4: Run the selector, then the tests**

```bash
uv run generators/select_fincen_advisories.py
uv run --with pytest pytest validators/test_aml_typology.py -q
```
Expected: 2 passed.

- [ ] **Step 5: STOP and surface the selection for review**

Print the four chosen advisories with number, title, issue date and the text
that matched. **This is the reviewed checkpoint named in the design.** Do
not proceed to Task 2 until the selection has been looked at — a wrong
advisory here silently mis-anchors every typology claim downstream.

- [ ] **Step 6: Commit**

```bash
git add generators/select_fincen_advisories.py sources/fincen/selection.json \
        validators/test_aml_typology.py
git commit -F <message-file>
```

---

## Task 2: Fetch the advisory PDFs

**Files:**
- Create: `generators/fetch_fincen_advisories.py`
- Create: `sources/fincen/*.pdf`, `sources/fincen/manifest.json`

**Interfaces:**
- Consumes: `sources/fincen/selection.json` from Task 1
- Produces: one PDF per typology plus a manifest recording url, sha256,
  byte count and retrieval date per file

- [ ] **Step 1: Write the failing test**

```python
def test_every_selected_advisory_was_actually_fetched():
    """Wave 17 Task 2. A manifest entry proves a fetch happened; a file on
    disk proves it produced bytes. Assert BOTH, because a manifest written
    before a failed download is exactly the artifact that looks complete."""
    import hashlib, json
    from ccf.config import REPO_ROOT
    sel = json.loads((REPO_ROOT/"sources"/"fincen"/"selection.json").read_text())
    man = json.loads((REPO_ROOT/"sources"/"fincen"/"manifest.json").read_text())
    # Manifest schema is the SHARED ccf.fetch harness shape:
    #   {"source","description","licence","fetches":[
    #      {"url","path","retrieved_at","sha256","bytes","http_status",
    #       "content_type","notes"}]}
    # `path` is repo-relative (e.g. "sources/fincen/fin-2010-a001.pdf").
    # Look the PDF up by its OWN url -- `pdf_url`, not the page `url`.
    by_url = {r["url"]: r for r in man["fetches"]}
    for t in sel["typologies"]:
        rec = by_url.get(t["pdf_url"])
        assert rec, f"{t['typology']}: selected but its PDF was never fetched"
        path = REPO_ROOT / rec["path"]
        assert path.exists(), f"{rec['path']} in manifest but not on disk"
        assert path.stat().st_size == rec["bytes"], (
            f"{rec['path']} size disagrees with the manifest")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == rec["sha256"], f"{rec['path']} content changed"
        assert rec["bytes"] > 20_000, (
            f"{rec['path']} is {rec['bytes']} bytes -- too small to be an "
            "advisory PDF; likely an error page fetched with status 200")
```

**Schema note (controller ruling, after Task 2).** The plan originally wrote
this test against `manifest["records"]` with a `filename` field. That shape
does not exist — the shared `ccf.fetch` harness writes `fetches[]` with
`path`. Task 2's implementer caught it and adapted while preserving every
assertion. The plan text is corrected here so Task 3 does not inherit the
same wrong field names. **Read `sources/fincen/manifest.json` before writing
any code against it** rather than trusting a schema quoted in prose.

- [ ] **Step 2: Run it and watch it fail** — no manifest yet.

- [ ] **Step 3: Implement the fetcher**

Fetch each advisory PAGE first, parse the `.pdf` href from it, then fetch
that. Do not construct the PDF path.

Use `ccf.fetch.fetch()` so the estate's rate limiter, manifest shape and
`already_fetched()` short-circuit are reused rather than reinvented. Assert
`content-type` is `application/pdf` and the payload starts with `%PDF`;
FinCEN returns a styled 200 HTML error page for a bad path, and a fetcher
that trusts the status code will store it happily.

- [ ] **Step 4: Fetch and test**

```bash
uv run generators/fetch_fincen_advisories.py
uv run --with pytest pytest validators/test_aml_typology.py -q
```

- [ ] **Step 5: Re-run the fetcher to prove idempotency**

Run it a second time. Expected: it reports every file already fetched and
re-downloads nothing; the sha256 values in the manifest are unchanged. Name
the sha256 of one specific file in the commit message — a value, not a
count.

- [ ] **Step 6: Commit**

---

## Task 3: Advisory text and passages into MongoDB

**Files:**
- Create: `generators/extract_advisory_passages.py`
- Create: `loaders/load_mongo_wave17.py`
- Modify: `pyproject.toml` (add `pypdf` — the project's first PDF dependency)
- Modify: `validators/test_aml_typology.py`

**Interfaces:**
- Consumes: the PDFs and manifest from Task 2
- Produces: Mongo `document` rows with `doc_type: "fincen_advisory"` and
  `passage` rows carrying `{document_id, passage_id, text, start_offset,
  end_offset, advisory_number}`. Span offsets index into the extracted text
  of that document and must round-trip.

  **Field names follow the ESTATE convention, not new ones** (controller
  ruling, after Task 3's first cut). 37,305 existing passages use
  `document_id` / `passage_id` / `start_offset` / `end_offset`, and
  `validators/partition.py`'s orphan-anchor check already queries
  `document_id`. The plan's first draft of the test below used `doc_id` /
  `start` / `end`, which forced the implementer to write BOTH name sets onto
  every row. Two fields holding the same offset are two things that can
  drift. Write one set: the estate's.

- [ ] **Step 1: Write the failing test**

```python
def test_passage_spans_round_trip_against_their_document():
    """Wave 17 Task 3. A span offset that does not select its own text is
    worse than no offset: every downstream typology citation resolves to the
    wrong words while looking perfectly well-formed. Re-slice the document
    text with each passage's own start/end and require the result to equal
    the stored passage text."""
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
```

- [ ] **Step 2: Run it and watch it fail** — no documents loaded.

- [ ] **Step 3: Extract and load**

**This wave adds the project's first PDF dependency — deliberately.**
Measured on 2026-08-24: `pyproject.toml` carries no PDF library and no
generator reads PDFs, and the advisory HTML page yields only ~2,057
characters of navigation boilerplate while the advisory body lives solely in
the PDF. So HTML scraping is not an option here, and `pypdf` (pure Python,
permissive licence) is added to `pyproject.toml` as an explicit step of this
task rather than assumed present.

Extract text with `pypdf`. Split into passages on paragraph
boundaries, keeping the character offsets from the extracted text — compute
offsets from the same string you store as `document.text`, never from a
re-extraction, or the two drift.

Upsert on an exact `_id` derived from the advisory number and passage index,
so a re-run replaces rather than duplicates. `doc_type` is set here:
**do not leave it unset** — 178 pre-existing Mongo documents already have no
`doc_type` (known-issues §21) and this wave must not add to that.

- [ ] **Step 4: Load and test**

```bash
uv run loaders/load_mongo_wave17.py
uv run --with pytest pytest validators/test_aml_typology.py -q
```

- [ ] **Step 5: Prove idempotency by value**

Note the `_id` and `text` of one specific passage. Re-run the loader. Assert
the same `_id` still holds the same `text` and that
`db.passage.count_documents({...})` is unchanged. Record the passage id in
the commit message.

- [ ] **Step 6: Commit**

---

## Task 4: Typology structural patterns, and the new bindings

**Files:**
- Create: `generators/derive_typology_patterns.py`
- Create: `sources/screening/wave17_typologies.json`
- Modify: `docs/ccf_dataprep_v2.md` (binding table)
- Modify: `validators/test_aml_typology.py`

**Interfaces:**
- Consumes: Mongo advisory passages from Task 3
- Produces: `sources/screening/wave17_typologies.json`, shape
  `{"typologies": [{"typology_id": "TYP-STRUCT", "typology": "structuring",
   "advisory_number": str, "passage_id": str, "params": {...},
   "provenance": "public"}]}`. `params` carries the structural thresholds
  the injector in Task 10 builds cases against (e.g. for structuring:
  `{"threshold_usd": 10000, "band_low": 0.80, "band_high": 0.99,
    "min_transactions": 4, "window_days": 10}`).

- [ ] **Step 0: Close a Task 3 minor first (one line, same file)**

`validators/test_aml_typology.py`'s
`test_no_advisory_passage_carries_a_retired_alias_field` counts rows carrying
a retired key and asserts the count is zero, but never asserts its own
population is non-empty. If those 72 rows were ever absent — wrong database,
a load that silently no-ops — it would report zero strays and pass, having
verified nothing. Assert the population floor (`>= 40`, matching the
round-trip test) before trusting the zero. This estate has recorded this
exact defect class — a gate blind to its own population — more than once.

- [ ] **Step 1: Bind the new terms BEFORE generating against them**

Terms this wave needs that the binding table does not carry:
`ex:Typology`, `ex:TypologyPattern`, `ex:matchesTypology`,
`ex:transactedWith`, `ex:AMLParty`, `ex:Alert`, `ex:FilingPosture`,
`ex:DispositionRule`, `ex:postureEffectiveFrom`, `ex:permitsDisposition`,
`ex:anchoredToPassage`.

For **each** term, run the estate's own absence check:

```python
from ccf.fibo import fibo_absent
assert fibo_absent("Typology"), "term exists in FIBO -- bind the FIBO IRI instead"
```

`fibo_absent` reads `dev.fibo-quickstart.ttl` and requires its positive
control (`LegalEntity`, 1,887 hits) to fire before any negative is trusted.
**Never** substitute a URL fetch: `spec.edmcouncil.org` returns 200 for
names that do not exist. If a term IS present in FIBO, bind the FIBO IRI and
do not mint an `ex:` one.

Add a row per term to `docs/ccf_dataprep_v2.md`'s binding table in a Wave 17
section, each stating what asserts it and how many times.

- [ ] **Step 2: Write the failing test**

```python
def test_every_typology_cites_a_resolvable_passage():
    """Wave 17 Task 4, envelope floor 1. A typology whose passage_id does not
    resolve is an invented claim wearing a citation. Resolve each one against
    Mongo and require the passage to actually mention the typology's own
    subject -- a citation that resolves to unrelated text is no better."""
    import json
    from ccf.config import REPO_ROOT, mongo_db
    db = mongo_db()
    data = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_typologies.json").read_text())
    assert len(data["typologies"]) >= 4, "envelope floor: >= 4 typologies"
    for t in data["typologies"]:
        p = db.passage.find_one({"passage_id": t["passage_id"]})
        assert p, f"{t['typology_id']} cites passage {t['passage_id']}, which does not exist"
        assert t["advisory_number"], f"{t['typology_id']} has no advisory number"
        assert t["params"], f"{t['typology_id']} carries no structural parameters"

def test_typology_params_are_not_all_identical():
    """A generator that stamps the same params on all four typologies would
    pass a count-based check while producing one pattern four times. Require
    the parameter sets to actually differ."""
    import json
    from ccf.config import REPO_ROOT
    data = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_typologies.json").read_text())
    seen = {json.dumps(t["params"], sort_keys=True) for t in data["typologies"]}
    assert len(seen) == len(data["typologies"]), "typology params are duplicated"
```

- [ ] **Step 3: Run and watch it fail.**

- [ ] **Step 4: Derive the patterns**

For each typology in `selection.json`, locate the passage in that advisory
that defines the pattern (search the passages of that document for the
typology's keywords), record its `passage_id`, and attach the structural
parameters.

**`shell_company_ownership` carries a controller ruling** (made after Task 1
substituted it for `rapid_pass_through`, which FinCEN does not cover).
FIN-2017-A003's worked case is residential real estate, and this estate
models no property register. Extract the typology at the MECHANISM level:

- Pick the passage that states the **mechanism** — a shell company
  concealing its beneficial owner — NOT a passage about GTO filing
  thresholds or dollar triggers, which describe a reporting regime this
  estate does not model.
- `params` for this typology are ownership-structural:
  `{"min_ownership_hops": 2, "channel": "asset_purchase",
    "min_amount_usd": <high-value threshold>, "financing_leg": false}`.
- `params` MUST also carry
  `"abstracted_from_advisory": "the advisory's own case is residential real
  estate; this estate models no property register, so the concealment
  mechanism is exhibited with the asset class abstracted"`.
- **Do NOT fabricate a real-estate domain** — no property entities, no
  deeds, no GTO thresholds. That imports a domain for one typology that
  nothing else in this wave uses.

Task 18 records this in `spec_coverage.py` as satisfied-with-divergence and
in `known-issues.md`. A stated narrowing is acceptable; an unstated one is
the "counted but not created" failure. Parameters are **read from the advisory text where it states
them** (e.g. the CTR threshold) and otherwise chosen and labelled as chosen
— do not present a number the advisory did not state as though it did.

- [ ] **Step 5: Run and test.**

- [ ] **Step 6: Commit, and say in the message that the vault mirror needs
      refreshing**, naming the terms added. Bundle is sent in Task 18.

---

## Task 5: `ccf/aml.py` — the name guard, and proof it has teeth

This is the mechanism CLAUDE.md rule 2 turns on. It gets its own task
because a reviewer must be able to reject it independently.

**Files:**
- Create: `ccf/aml.py`
- Modify: `validators/test_aml_typology.py`

**Interfaces:**
- Produces:
  - `normalize_name(s: str) -> str` — casefold, strip punctuation and
    corporate suffixes, collapse whitespace
  - `similarity(a: str, b: str) -> float` — 0.0–1.0
  - `RealNameIndex` with `.blocks(candidate: str) -> str | None` returning
    the colliding real name, or `None`
  - `is_psc_key(k: str) -> bool` — `True` only for `PSC-` + digits
  - `BLOCK_THRESHOLD: float`

- [ ] **Step 0: Close two Task 4 minors first (same test file, both cheap)**

1. `test_ex_alert_is_not_bound_here` **does not test what its name claims.**
   It reads `sources/screening/wave17_typologies.json` — an artifact that was
   never at risk — and never opens `docs/ccf_dataprep_v2.md`, where the
   binding table actually lives. Task 4's re-reviewer proved it: re-inserting
   an `Alert` binding row into the doc leaves all 14 tests passing. Repoint it
   at the binding table itself so it would catch a re-binding, and make it
   assert its own denominator (that the Wave 17 section was found and holds
   the expected 10 rows) so it cannot pass by reading an empty or wrong file.
   A test that names a guarantee it does not provide is worse than no test —
   it stops anyone from writing the real one.
2. `docs/ccf_dataprep_v2.md`'s "Vault mirror" line above the binding table
   still reads "All **11** rows above are outstanding". It is 10 since
   `ex:Alert` was pulled. One-line fix.

- [ ] **Step 1: Write the failing tests — including the falsification ones**

```python
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
```

- [ ] **Step 2: Run and watch all four fail.**

- [ ] **Step 3: Implement `ccf/aml.py`**

`RealNameIndex.build()` reads, in one pass each:
`legal_entity` (legal name + any variant columns), `sanctions_entry` +
`sanctions_name`, `person` + `person_name_variant`, `psc_person` native
forms, `peer_entity`, `registry_company`, `institutional_holder`. It stores
normalized forms plus a token index so `blocks()` does not do 45,511
pairwise comparisons per candidate: look up candidates sharing a rare token
first, then score only those.

`counts` is a dict of source → rows indexed, populated from the queries
themselves so the test above measures the real denominator rather than a
constant.

No I/O beyond those reads; no Fluree, no Mongo. Pure enough to test.

- [ ] **Step 4: Run the tests until all four pass.**

- [ ] **Step 5: Calibrate `BLOCK_THRESHOLD` against real evidence**

The estate already carries a deliberate false-positive pair (two different
people who fuzzy-match strongly, per CLAUDE.md rule 5). Score that pair.
`BLOCK_THRESHOLD` must sit **below** it, so a name that similar to a real
one is refused. Record the measured score and the chosen threshold in the
module docstring — a threshold set by taste is the "tolerance wider than the
bias" failure this estate has recorded.

- [ ] **Step 6: Commit.**

---

## Task 6: Generate the 200 parties

**Files:**
- Create: `generators/generate_aml_parties.py`
- Create: `sources/screening/wave17_parties.json`

**Interfaces:**
- Consumes: `ccf.aml.RealNameIndex`, `BLOCK_THRESHOLD`
- Produces: `wave17_parties.json` — `{"parties": [{"party_id": "AMLP-0001",
  "legal_name": str, "syn_lei": "SYN-...", "jurisdiction": ISO-α3,
  "party_kind": "corporate"|"individual_owned"|"shell",
  "incorporated": "YYYY-MM-DD", "provenance": "synthetic — engineered"}]}`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run and watch it fail.**

- [ ] **Step 3: Implement the generator**

Seeded `random.Random` with a fixed constant, all iteration in sorted order,
so two runs produce byte-identical output. Compose names from an invented
word bank — **reuse `generators/name_bank.py`'s discipline**: every emitted
token comes from a closed vocabulary, so a real name cannot appear by
accident. Every candidate goes through `idx.blocks()`; a blocked candidate
is **regenerated**, and the generator counts rejections and prints the
count. A rejection count of zero across 200 draws is suspicious and should
be reported as such — it usually means the guard is not wired in.

`party_id` is `AMLP-####` assigned from a sorted, content-derived ordering —
never from enumerate over a query result.

- [ ] **Step 4: Run and test.**

- [ ] **Step 5: Re-run and diff the artifact**

`git diff --exit-code sources/screening/wave17_parties.json` must be clean
after a second run. Determinism is the claim; the diff is the proof.

- [ ] **Step 6: Commit.**

---

## Task 7: The one declared OFAC near-match

Envelope floor 5. This is the single permitted exception to the name guard,
and it must be a *declared* exception rather than a hole.

**Files:**
- Modify: `generators/generate_aml_parties.py`
- Modify: `sources/screening/wave17_parties.json`

**Interfaces:**
- Produces: exactly one party carrying
  `"ofac_near_match": {"sanctions_entry_id": <id>, "matched_name": str,
   "measured_similarity": float}`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run and watch both fail.**

- [ ] **Step 3: Implement the declared path**

Pick a real sanctions entry, derive a name that is *similar but clearly
different* (change the given name, alter a token, keep a distinctive
surname), measure the similarity, and emit the party through a separate
function named so it is visible in a grep — e.g.
`generate_declared_ofac_near_match()`. Store the measured value; the test
recomputes it and does not trust it.

- [ ] **Step 4: Run and test.**

- [ ] **Step 5: Commit.**

---

## Task 8: Postgres DDL and the party load

**Files:**
- Create: `loaders/load_postgres_wave17.py`

**Interfaces:**
- Produces tables in `PG_SCHEMA_V2`: `aml_party`, `aml_transaction`,
  `aml_alert`, `aml_alert_link`, `aml_projection_plan`
- Produces: `load_parties(cur, parties) -> int`

**Two columns exist for later tasks and MUST be in this task's DDL**
(pre-flight ruling): `aml_party.beneficial_owner_key TEXT NULL`, populated by
Task 9, and `aml_projection_plan.elements JSONB NOT NULL`, populated by
Task 16. A later task cannot add a column to a table this task owns without
re-opening the single-writer boundary mid-plan.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run and watch it fail.**

- [ ] **Step 3: Write the DDL and loader**

`CREATE TABLE IF NOT EXISTS` for each. Natural primary keys: `aml_party
(party_id)`, `aml_transaction (txn_id)`, `aml_alert (alert_id)`,
`aml_alert_link (alert_id, related_alert_id)`, `aml_projection_plan
(perspective)`. Every insert is `ON CONFLICT (<natural key>) DO UPDATE`, so
a re-run converges instead of duplicating.

**Refuse to run against the wrong schema** — call
`assert_v2_schema(PG_SCHEMA_V2)` first, as the other loaders do. No
`DELETE`, no `TRUNCATE`.

- [ ] **Step 4: Load and test.**

- [ ] **Step 5: Prove idempotency by value**

Pick one party, note its `legal_name` and `jurisdiction`. Re-run. Assert
both fields are unchanged AND the row count is unchanged. Name that party
in the commit message.

- [ ] **Step 6: Commit.**

---

## Task 9: Bind parties to the inherited ownership island

The design's central reuse decision. This task connects AML parties to the
existing `PSC-*` / `bo_chain` island and must not touch anything else.

**Files:**
- Create: `generators/bind_aml_ownership.py`
- Modify: `loaders/load_postgres_wave17.py`

**Interfaces:**
- Consumes: `psc_person` (`PSC-*` only), `bo_chain`, `bo_chain_hop`
- Produces: `aml_party.beneficial_owner_key` populated for the subset of
  parties that sit in an ownership structure, plus
  `sources/screening/wave17_ownership.json` recording chain bindings

- [ ] **Step 1: Write the failing test — the boundary, first**

```python
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
```

- [ ] **Step 2: Run and watch both fail.**

- [ ] **Step 3: Implement the binding**

Select owner candidates with `WHERE person_key LIKE 'PSC-%'` **and** run
each through `is_psc_key()` — the SQL pattern and the code check are
deliberately redundant, because one is easy to edit without noticing.

Bind a subset of parties (the `shell` and `individual_owned` kinds) to
existing `bo_chain` structures, reusing chains rather than minting new ones.
Where a new chain is genuinely needed, build it from invented holding
companies exactly as `bo_chain` already does — never anchoring on a real
`legal_entity`.

- [ ] **Step 4: Run and test.**

- [ ] **Step 5: Commit.**

---

## Task 10: The ordinary transaction population

Built **before** the engineered cases, so the noise is genuine noise.

**Files:**
- Create: `generators/generate_aml_transactions.py`
- Create: `sources/screening/wave17_transactions.json`

**Interfaces:**
- Produces: `{"as_of": "YYYY-MM-DD", "window_start": "YYYY-MM-DD",
  "transactions": [{"txn_id": "TXN-000001", "from_party": str,
  "to_party": str, "amount_usd": float, "value_date": "YYYY-MM-DD",
  "channel": str, "provenance": "synthetic — engineered"}]}` over an
  18-month window ending at a pinned `AS_OF_AML`.

  **The top-level `as_of` and `window_start` keys are required** (pre-flight
  ruling): this task's own test reads them, and the pinned window is the
  reproducibility claim — it belongs in the artifact, not only in the
  generator's source.

- [ ] **Step 1: Pin the as-of instant**

```python
AS_OF_AML = "2026-08-24"          # pinned; NEVER datetime.now()
WINDOW_START = "2025-02-24"       # AS_OF_AML minus 18 months
```

A population whose window reads the clock changes shape on every run and
every downstream floor becomes unreproducible. Wave 16 learned this;
`AS_OF_IB` exists for the same reason.

- [ ] **Step 2: Write the failing test**

```python
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
    a 10-day window all sitting in the 80-99% band below the threshold."""
    import json, collections, datetime as dt
    from ccf.config import REPO_ROOT
    d = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_transactions.json").read_text())
    by_party = collections.defaultdict(list)
    for t in d["transactions"]:
        if 8000 <= t["amount_usd"] < 10000:
            by_party[t["from_party"]].append(dt.date.fromisoformat(t["value_date"]))
    for party, dates in by_party.items():
        dates.sort()
        for i in range(len(dates) - 3):
            span = (dates[i+3] - dates[i]).days
            assert span > 10, (
                f"{party} already looks like structuring in the ORDINARY "
                f"population ({span}d) -- the injected cases will not be "
                "distinguishable from background")
```

- [ ] **Step 3: Run and watch it fail.**

- [ ] **Step 4: Implement**

Seeded and deterministic. Amounts drawn from a heavy-tailed distribution
(most small, few large), value dates spread across the window with weekday
weighting, counterparties drawn from the AML party set only.

`channel` vocabulary must include `asset_purchase` — Task 11's
`shell_company_ownership` cases need it, per the controller ruling in Task 4.
The ordinary population uses it at a low rate for unremarkable amounts, so
the channel alone is not a tell. After
generating, run the anti-pattern check above **inside the generator** and
resample any party that trips it — do not leave it to the test to discover.

- [ ] **Step 5: Run and test; re-run and diff for determinism.**

- [ ] **Step 6: Commit.**

---

## Task 11: Inject the engineered typology cases

**Files:**
- Create: `generators/inject_typology_cases.py`
- Modify: `sources/screening/wave17_transactions.json`
- Create: `sources/screening/wave17_cases.json`

**Interfaces:**
- Consumes: `wave17_typologies.json` params, `wave17_parties.json`,
  `wave17_transactions.json`
- Produces: `wave17_cases.json` — `{"cases": [{"case_id": "CASE-001",
  "typology_id": str, "subject_party": str, "txn_ids": [...],
  "requires_depth": int, "depth_three_counterparty": str|None,
  "provenance": "synthetic — engineered"}]}` and the additional transactions
  appended to the transaction artifact

  **`depth_three_counterparty` is required on any case with
  `requires_depth >= 3`** (pre-flight ruling). `requires_depth` is a label,
  and floor 2's test explicitly refuses to trust labels — the named
  counterparty is what makes the depth-2 / depth-3 comparison computable.

- [ ] **Step 1: Write the failing tests, including floor 2**

```python
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
```

- [ ] **Step 2: Run and watch it fail.**

- [ ] **Step 3: Implement the injector**

For each typology, build cases directly from that typology's `params`, so a
case cannot drift from the advisory it cites. For the depth-3 case,
construct a chain subject → intermediary A → intermediary B → target and
**verify with the same reachability function the test uses** that the target
is absent at depth 2 — compute it, do not assume the construction implies
it.

Record `depth_three_counterparty` explicitly on that case.

- [ ] **Step 4: Run and test.**

- [ ] **Step 5: Commit.**

---

## Task 12: Alerts, noise, and prior-alert history

**Files:**
- Create: `generators/generate_aml_alerts.py`
- Create: `sources/screening/wave17_alerts.json`
- Modify: `loaders/load_postgres_wave17.py`

**Interfaces:**
- Produces: `{"alerts": [{"alert_id": "ALT-000001", "subject_party": str,
  "raised_at": "YYYY-MM-DD", "case_id": str|None, "trigger": str,
  "provenance": "synthetic — internal"}], "links": [{"alert_id": str,
  "related_alert_id": str, "relation": str}]}`

Alerts on a genuine case carry that `case_id`; noise alerts carry `None`.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run and watch it fail.**

- [ ] **Step 3: Implement**, then load into `aml_alert` / `aml_alert_link`.

- [ ] **Step 4: Run and test.**

- [ ] **Step 5: Commit.**

---

## Task 13: Fluree — nodes, network, ownership, typologies

**Files:**
- Create: `loaders/load_fluree_wave17.py`

**Interfaces:**
- Produces in ledger `FLUREE_LEDGER_V2`: `ex:AMLParty` nodes,
  `ex:transactedWith` edges, `ex:matchesTypology` edges,
  `ex:Typology` / `ex:TypologyPattern` nodes with `ex:anchoredToPassage`

- [ ] **Step 1: Write the failing test**

```python
def test_every_matches_typology_edge_cites_an_advisory_passage():
    """Wave 17 Task 13, envelope floor 1 in the store that owns it. A
    typology match with no anchor is an unsupported accusation about a party
    -- invented or not, it is the shape of claim this product exists to make
    defensible."""
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
```

- [ ] **Step 2: Run and watch it fail.**

- [ ] **Step 3: Implement the loader**

Follow `loaders/load_fluree_wave16.py`'s structure: build every triple
first, deterministically, then transact in batches. Retraction is
**subject-scoped** — never a blind predicate-wide `DELETE`, which would take
other waves' assertions with it. Fluree takes plain string literals, not
`xsd:date`.

Type every node explicitly for every role it must be queried against; there
is no inference.

**Assert only what §C assigns to Fluree.** Party attributes (legal name,
jurisdiction, incorporation date) belong to Postgres and must not appear
here — `partition.py`'s Postgres-owned-attribute scan is what catches it.

- [ ] **Step 4: Load and test.**

- [ ] **Step 5: Prove idempotency by value**

Record the ledger `t` and one specific party's edge count. Re-run **without**
`--reconcile`. Assert the edge count is unchanged. Then note in the commit
message that literal-valued predicates accumulate on re-run if their VALUE
changes — Wave 16 lost 26 stale literals to exactly this and needed
`--reconcile` to clear them.

- [ ] **Step 6: Commit.**

---

## Task 14: Two posture versions, and the disposition that flips

Envelope floor 3. The design calls this the case that demonstrates the
Policy Blind counterfactual and the `as_of` requirement together.

**Files:**
- Create: `generators/generate_aml_policy.py`
- Create: `sources/screening/wave17_policy.json`
- Modify: `loaders/load_fluree_wave17.py`

**Interfaces:**
- Produces: `{"postures": [{"posture_id": "POST-2025-01", "effective_from":
  "YYYY-MM-DD", "advisory_number": str|None, "provenance":
  "synthetic — internal"}], "rules": [{"rule_id": str, "posture_id": str,
  "typology_id": str, "disposition": "close-no-action"|"escalate-l2"|
  "file-sar"|"monitor", "permitted": bool}]}`
- Produces in Fluree: `ex:FilingPosture` nodes with
  `ex:postureEffectiveFrom`, `ex:DispositionRule` nodes with
  `ex:permitsDisposition`

- [ ] **Step 1: Write the failing test — the flip itself**

```python
def test_a_disposition_flips_from_permitted_to_forbidden_across_postures():
    """Wave 17 Task 14, envelope floor 3. The whole as_of argument rests on
    this single case: the SAME disposition for the SAME typology must be
    permitted under the earlier posture and forbidden under the later one.
    Evaluate both and require the two answers to DIFFER -- a count of
    postures proves nothing, and two postures that agree everywhere
    demonstrate nothing."""
    import json
    from ccf.config import REPO_ROOT
    d = json.loads((REPO_ROOT/"sources"/"screening"/"wave17_policy.json").read_text())
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
    from ccf import fluree
    from ccf.config import EX, FLUREE_LEDGER_V2 as L
    rows = fluree.query(f"SELECT ?s ?d FROM <{L}> WHERE "
                        f"{{ ?s <{EX}postureEffectiveFrom> ?d }}")["results"]["bindings"]
    assert len(rows) >= 2, "fewer than two postures in Fluree"
    for r in rows:
        assert len(r["d"]["value"]) == 10, "effective date is not a plain YYYY-MM-DD string"
```

- [ ] **Step 2: Run and watch both fail.**

- [ ] **Step 3: Implement**

Two postures with distinct effective dates inside the transaction window.
The later posture tightens: a disposition that was `close-no-action` for one
typology under the earlier posture becomes forbidden under the later, with
`escalate-l2` taking its place. Anchor the later posture to one of the
fetched advisories by number where the advisory's own issue date supports
it; where it does not, leave `advisory_number` null rather than inventing a
justification.

- [ ] **Step 4: Run, load, and test.**

- [ ] **Step 5: Commit.**

---

## Task 15: SAR narratives and confidentiality

Envelope floor 4.

**Files:**
- Create: `generators/generate_sar_records.py`
- Create: `loaders/load_sqlite_wave17.py`
- Modify: `loaders/load_mongo_wave17.py`

**Interfaces:**
- Produces: Mongo `document` rows with `doc_type: "sar_narrative"`
- Produces: SQLite table `sar_classification (sar_id TEXT PRIMARY KEY,
  alert_id TEXT NOT NULL, classification TEXT NOT NULL,
  visible_to_perspectives TEXT NOT NULL, provenance TEXT NOT NULL)`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run and watch it fail.**

- [ ] **Step 3: Implement.** SAR narratives reference alert ids and typology
      language; they never name a real person or company (the parties are
      invented, so this follows, but assert it with the Task 5 guard rather
      than assuming).

- [ ] **Step 4: Run and test.**

- [ ] **Step 5: Commit.**

---

## Task 16: Projection plans for three perspectives

Envelope floor 6 — the three renderings must differ in **assembled content**,
not formatting.

**Files:**
- Modify: `loaders/load_postgres_wave17.py`
- Create: `sources/screening/wave17_projection.json`

**Interfaces:**
- Produces: three `aml_projection_plan` rows keyed by perspective, each
  carrying an `elements` JSON array naming what that perspective assembles

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run and watch it fail.**

- [ ] **Step 3: Implement**, following `ib_projection_plan`'s shape from
      Wave 16 rather than widening the shared `projection_plan` table.

- [ ] **Step 4: Run and test.**

- [ ] **Step 5: Commit.**

---

## Task 17: `validators/aml_typology.py` — the floors, recomputed

The instrument, not the product. It registers nothing, composes into no
plan, serves no principal, emits no contract. It reads the stores and
answers one question: does this data support what the spec claims?

**Files:**
- Create: `validators/aml_typology.py`
- Modify: `validators/test_aml_typology.py`

**Interfaces:**
- Produces: `main() -> int` printing one line per floor and exiting non-zero
  if any fails; plus importable
  `typology_anchoring()`, `depth_three_holds()`, `posture_flip_holds()`,
  `sar_confidentiality_holds()`, `ofac_band_holds()`,
  `renderings_differ()`, `no_path_to_real_entity()`

- [ ] **Step 1: Write the failing test for the safety property**

```python
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
```

- [ ] **Step 2: Run and watch both fail.**

- [ ] **Step 3: Implement the validator**

Structure it like `validators/ib_rank.py`. Every floor recomputes from the
stores: no stored score, no cached rank, no boolean flag. Specifically:

- `typology_anchoring()` resolves every `ex:anchoredToPassage` object
  against Mongo and requires the passage to exist and be non-empty.
- `depth_three_holds()` builds the adjacency from Fluree
  `ex:transactedWith` and runs the depth-2 / depth-3 comparison **live**,
  rather than reading `requires_depth`.
- `posture_flip_holds()` evaluates the same disposition under both
  `as_of` values and asserts the answers differ.
- `sar_confidentiality_holds()` assembles from an unauthorized perspective
  and asserts the SAR fields are **absent**, not null.
- `ofac_band_holds()` recomputes the similarity from live Postgres names.
- `renderings_differ()` compares assembled element sets.
- `no_path_to_real_entity()` builds the adjacency from Fluree across **all**
  predicates and delegates to `walk_for_crossings()`, which is pure and
  therefore testable against a planted edge.

Separate the pure walk from the store reads precisely so the falsification
test above is possible.

- [ ] **Step 4: Run the validator and the tests.**

```bash
uv run validators/aml_typology.py
uv run --with pytest pytest validators/test_aml_typology.py -q
```

- [ ] **Step 5: Commit.**

---

## Task 18: Registration, docs, and the vault bundle

A product that is built but unregistered is invisible — this estate carried
one complete-but-uncounted for eleven waves.

**Files:**
- Modify: `validators/conditions.py`
- Modify: `validators/partition.py`
- Modify: `validators/spec_coverage.py`
- Modify: `docs/ccf_dataprep_v2.md`, `docs/HANDOFF.md`, `docs/known-issues.md`

- [ ] **Step 1: Register the conditions**

Add a `# --- #19 aml-typology-match (Wave 17)` block to `conditions.py`
following the Wave 16 block's shape. **Register only floors that carry a
condition**; the envelope's ~200 / ~5,000 / ~150 figures are shape, not
targets, and must not be registered as floors.

Where a floor is an ordering or an absence rather than a count, delegate to
`validators/aml_typology.py` exactly as the IB block delegates to
`ib_rank.py`, and say so in the note column.

**Never wrap a check body in a bare `except Exception -> None`** — that
renders a genuine bug as SKIP. Only a real missing-table precondition may
SKIP; everything else FAILs loud.

- [ ] **Step 2: Register the partition checks**

Add bidirectional checks: the AML elements ARE in the stores §C names, and
are NOT in the stores it does not name. Include the SAR-not-in-Postgres
check from Task 15 and a Postgres-owned-attribute scan for the AML party
attributes.

- [ ] **Step 3: Map the §C catalog**

Walk the vault's §C table row by row in `spec_coverage.py`. **Confirm the
spec is Q019 form by reading the section NAME**, not the letter: §F must
read "Manufacture envelope". In v0.3 specs §F is "Source binding &
readiness" and a letter-based read returns the wrong section while parsing
cleanly.

Record the section-4 reuse decision as a **satisfied** row, not a gap.

- [ ] **Step 4: Run everything and read the PASS counts**

```bash
uv run validators/conditions.py
uv run validators/partition.py
uv run validators/aml_typology.py
uv run --with pytest pytest validators/ -q
```

Read the PASS count from `conditions.py`, never the "0 failed" line.

- [ ] **Step 5: Update the docs and send the bundle**

Add the Wave 17 binding rows to `docs/ccf_dataprep_v2.md`, update
`docs/HANDOFF.md`, and record any defects found in `docs/known-issues.md`.

Send one exchange bundle to `~/.agent-exchange/ccf-dataprep/outbox/`, built
as `<YYYY-MM-DDTHH-MM-SSZ>-<slug>.tmp/` and renamed to publish. Hyphens in
the time, never colons. Bundles are immutable: a correction is a NEW bundle
naming what it supersedes. State each count once, in prose.

**Say explicitly in the final response which terms were added and that the
vault mirror needs refreshing.**

- [ ] **Step 6: Commit.**

---

## Self-Review

**Spec coverage.** Every §C row maps to a task: sanctions (existing, Task
5 index + Task 7), typology definitions (Tasks 1–4), structural patterns
(Task 4, 13), filing posture (14), ownership and intermediaries (9),
beneficial ownership (9), adverse media (existing `gdelt_mention`, mapped in
18), passage spans (3), parties (6, 7, 8), transactions (10, 11), alerts
(12), network edges (13), SAR narratives (15), SAR classification (15),
disposition rules (14), projection plans (16).

Every §F floor maps to a task and a test: ≥4 typologies (4), depth-3 (11),
posture flip (14), SAR invisibility (15), OFAC band (7), three renderings
(16). Both safety properties: name guard (5, 6) and graph disconnect (17).

**Type consistency.** `party_id` is `AMLP-####` throughout; `case_id` is
`CASE-###`; `alert_id` is `ALT-######`; `txn_id` is `TXN-######`;
`typology_id` is `TYP-*`; `posture_id` is `POST-*`; `sar_id` is `SAR-*`.
`is_psc_key` and `similarity` are defined in Task 5 and used in 6, 7, 9, 15.
`walk_for_crossings` is defined in Task 17 and used only there.

**Known gaps, stated rather than hidden.** FATF is blocked (403), so all
four typologies anchor to FinCEN; recorded in the design's §10 and to be
recorded again in `known-issues`. The advisory selection in Task 1 is a
human checkpoint, not an automated gate.
