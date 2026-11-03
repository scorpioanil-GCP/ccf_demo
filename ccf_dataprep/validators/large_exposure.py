#!/usr/bin/env python3
"""Wave 19 Task 15 — the eight §F floors for `large-exposure-rwa-concentration`.

## What this is not

A **build-time validator, not an operator** (CLAUDE.md, "What 'operator'
means -- and what it does not"). It registers nothing, composes into no
plan, serves no principal, emits no contract, enforces no TTL, and writes
nothing to any store. It runs against the loaded estate and asks one
question: does this data support what the spec claims?

## The rule that makes it worth anything

Every number below is **recomputed from the stores on every run**. No stored
score, no cached rank, no boolean breach flag is ever read as an answer.
`ccf_v2.exposure_proposal.expected_outcome` records intent only, and this
file never selects that column — a proposal's gross/net crossing is derived
from `ccf_v2.facility`, `ccf_v2.collateral_pledge` / `collateral_asset`, and
the live `ex:LimitEnvelope` / `ex:RegimeVersion` figures, exactly as
`generators/generate_proposals.py` computed it at generation time, but
independently: this file does not import that generator's arithmetic, it
repeats the measurement.

Several of the eight are ordering/flip claims a count cannot establish:

1. `groups_recompute`       -- 26 components from `ex:connectedTo`, ≥ 9 of
                                them individually spanning ≥ 3 countries,
                                reported SEPARATELY from the 26.
2. `dependency_changes_binding_limit` -- ≥ 1 `ex:economicallyDependentOn`
                                edge whose removal changes WHICH limit
                                binds (appetite vs. nothing) for its group.
3. `regime_divergence`      -- ≥ 1 group compliant under CRR/PRA and in
                                breach under Reg O, both recomputed.
4. `proposal_breaches`      -- ≥ 1 hypothetical proposal whose group
                                breaches the 25% limit NET of mitigation
                                (the default the product's own §B request
                                parameters apply) AND a DISTINCT proposal
                                cured by mitigation — derived, never read
                                from `expected_outcome`.
5. `mitigation_is_load_bearing` -- ≥ 1 proposal over the limit gross, under
                                it net of real post-haircut collateral.
6. `debt_tolerance_breached` -- ≥ 1 group whose `memo_context_debt.
                                aggregate_debt` sums above the live
                                `validators/memo_debt.py::policy_tolerance`.
7. `projection_plans_differ` -- the three `elements_included` sets are
                                pairwise distinct.
8. `no_public_row_in_a_breach` -- the provenance floor. See its own
                                docstring below; it is not a flag check.

## Ruling L15-R1 — what "group" means for Reg O (floor 3)

12 CFR 215.4(b)(2) aggregates "that person, AND all related interests of
that person" — a narrower population than a `connectedTo` control
component. So `regime_divergence` groups by the `ex:InsiderDesignation`
node's own `ex:designatedPerson` targets (resolved to a LEI where one
exists — the invented natural person carries none), not by the
control-basis component the OTHER seven floors use. Using the control
component instead would silently substitute a different legal aggregation
for the one the statute actually names.

## Ruling L15-R2 — what floor 8 checks, and what it deliberately does not

`ccf_v2.facility` rows are BOTH-provenance by construction
(`provenance_public='public'`, `provenance_internal='synthetic — internal'`,
confirmed live across every row) — that mixing is the whole design of the
Reg O and mitigation cases: a real, filed, public facility plus an invented
relationship or an invented proposal is what makes the case engineered
rather than fabricated wholesale. So "no public row participates in a
breach" is **not** a `provenance_public != 'public'` scan over `facility` —
every row would fail that trivially and no case in this wave could ever
pass it. It is scoped to the elements that themselves MAKE something a
breach: the `exposure_proposal` rows, the SQLite workbook (including its
free text), the MongoDB methodology material, and the specific Fluree nodes
whose provenance turns a real facility into an engineered case
(`ex:edgeProvenance` on the four dependency edges, `ex:provenance` on the
one `InsiderDesignation`, `ex:provenance` on the `LimitEnvelope`). None of
those may ever read `public`.

    uv run validators/large_exposure.py

Exit code is non-zero if any of the eight fails.
"""
from __future__ import annotations

import collections
import re
import string
import sqlite3
import sys
from dataclasses import dataclass, field

from ccf import fluree
from ccf.config import (
    EX,
    FLUREE_LEDGER_V2 as L,
    PG_SCHEMA_V2 as S,
    SQLITE_PATH,
    mongo_db,
    pg_connect,
)
from validators.memo_debt import policy_tolerance

EX_CONNECTED_TO = f"{EX}connectedTo"
EX_ECONOMICALLY_DEPENDENT_ON = f"{EX}economicallyDependentOn"
EX_EDGE_PROVENANCE = f"{EX}edgeProvenance"
EX_LEI = f"{EX}lei"
EX_PROVENANCE = f"{EX}provenance"
EX_REGIME_VERSION = f"{EX}RegimeVersion"
EX_LIMIT_ENVELOPE = f"{EX}LimitEnvelope"
EX_EFFECTIVE_FROM = f"{EX}effectiveFrom"
EX_EFFECTIVE_TO = f"{EX}effectiveTo"
EX_LIMIT_PCT = f"{EX}limitPctOfCapital"
EX_LIMIT_ABS = f"{EX}limitAbsoluteUsd"
EX_CITES_PROVISION = f"{EX}citesProvision"
EX_INSIDER_DESIGNATION = f"{EX}InsiderDesignation"
EX_DESIGNATED_PERSON = f"{EX}designatedPerson"
EX_DEPENDENCY_BASIS = f"{EX}dependencyBasis"
EX_ASSERTED_BY = f"{EX}assertedBy"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"

#: The two labels this project permits for invented data (CLAUDE.md's three
#: provenance classes, minus `public`). Used only by floor 8 -- never
#: consulted by floors 1-7, which do not care how a row is labelled, only
#: what it says.
SYNTHETIC_PROVENANCE = {"synthetic — internal", "synthetic — engineered"}


def _q(sparql: str) -> list[dict]:
    return fluree.query(sparql)["results"]["bindings"]


def local_name(iri: str) -> str:
    """Last path segment. Labels only -- never used to compare across
    stores (CLAUDE.md, "Normalize to full IRIs before comparing")."""
    return iri.rsplit("/", 1)[-1]


# ===========================================================================
# Pure helpers -- no store access, exercised from test_large_exposure.py
# ===========================================================================

def union_find(edges: list[tuple[str, str]]) -> tuple[dict[str, str], "callable"]:
    """Union-find over (a, b) pairs. Same algorithm `loaders/
    load_group_edges.py::components` and `generators/generate_proposals.py::
    _components` already use -- reproduced here, not imported, because a
    validator sharing code with the loader it is meant to check is the
    exact "agrees with itself" failure `validators/conditions.py`'s own
    module docstring warns about for the crosswalk invariants.
    """
    par: dict[str, str] = {}

    def find(x: str) -> str:
        par.setdefault(x, x)
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            par[ra] = rb
    return par, find


def components(edges: list[tuple[str, str]]) -> dict[str, set[str]]:
    """root -> every node in its component. Nodes that appear in NO edge are
    absent -- a true singleton (zero `connectedTo` edges of any kind, e.g.
    TransDigm Group Inc) is not a "component of size 1" under this
    definition, matching `load_group_edges.py`'s own live-verified count of
    26. `groups_recompute` needs that exact convention to reproduce 26; a
    version that seeded every LEI as its own component would report a
    different number and disagree with the loader's own guard for no
    principled reason.
    """
    par, find = union_find(edges)
    out: dict[str, set[str]] = collections.defaultdict(set)
    for n in par:
        out[find(n)].add(n)
    return out


def group_leis(edges: list[tuple[str, str]], node: str,
               lei_by_uri: dict[str, str]) -> set[str]:
    """Every LEI in `node`'s connected component under `edges` -- or just
    `node`'s own LEI if it has no edge at all (a real singleton, e.g.
    TransDigm before any dependency edge is added)."""
    par, find = union_find(edges)
    if node in par:
        root = find(node)
        members = [n for n in par if find(n) == root]
    else:
        members = [node]
    return {lei_by_uri[m] for m in members if m in lei_by_uri}


def group_dollar_total(edges: list[tuple[str, str]], node: str,
                       lei_by_uri: dict[str, str],
                       by_lei: dict[str, float]) -> float:
    """Sum of `by_lei` (exposure, or collateral) across `node`'s group."""
    leis = group_leis(edges, node, lei_by_uri)
    return sum(by_lei.get(lei, 0.0) for lei in leis)


_BREACH_WORD_RE = re.compile(
    r"^(breach(ed|es|ing)?|exceed(s|ed|ing)?|violat(e|ed|es|ing|ion)|"
    r"non-complian(t|ce))$", re.I)
_REG_KEYWORD_RE = re.compile(
    r"(crr|pra|regulation o|reg\.?\s?o\b|regulatory limit|"
    r"large[- ]exposure limit|25\s?%|\$?500,000)", re.I)
#: Words either side of a breach word searched for a bank reference AND a
#: regulatory keyword. Measured against the real corpus (2 methodology
#: documents, their 12 passages, 5 workbook rows): every real occurrence of
#: a breach word sits near "reporting bank" and near "CRR"/"25%" SEPARATELY
#: -- e.g. "the reporting bank's ... limit ... 'exceeds 25% ...'" is a
#: verbatim quote of the regulation, and "every appetite, breach, and
#: proposal ... belongs to this dataset's synthetic ... envelope" denies the
#: very thing a whole-document scan would flag. A window this wide (8 words)
#: still finds neither signal near any real breach word; an injected
#: sentence naming the bank AND the regulator within a clause of "breached"
#: is what this is built to catch. See `test_large_exposure.py` for the
#: measured, live negative control -- both real corpora, checked, then one
#: fabricated sentence checked against the same function.
_ASSERTION_WINDOW_WORDS = 8

#: Legal-entity suffix words stripped before deriving short forms -- what is
#: left over is the brand-identifying part of the name ("jpmorgan", "chase"),
#: which is exactly what a hostile sentence uses instead of the full legal
#: string ("JPMorgan breached...", "Chase exceeded...").
_ORG_SUFFIX_WORDS = {
    "bank", "banks", "national", "association", "assn", "corp",
    "corporation", "inc", "incorporated", "co", "company", "holdings",
    "holding", "na", "n", "a", "ltd", "limited", "plc", "llc", "group",
    "the", "&",
}


def bank_reference_tokens(legal_name: str, rssd: str | None = None) -> list[str]:
    """Every short form a hostile sentence could plausibly use for the
    reporting bank, derived from its own legal name rather than hard-coded
    to one string (Important 1: `["jpmorgan chase bank, national
    association", "reporting bank"]` matched only the full legal string and
    the literal phrase "reporting bank" -- it missed "JPMorgan", "Chase",
    "JPMorgan Chase Bank", and the RSSD).

    Strips known organisational/legal suffix words (bank, national,
    association, N.A., ...) from the legal name; whatever is left is the
    distinctive part, kept both as individual words ("jpmorgan", "chase")
    and joined ("jpmorgan chase"). The full legal name and the generic
    phrase "reporting bank" (used throughout this estate's own honest
    methodology prose) are always included, plus the RSSD identifier if
    given. Matching in `asserts_regulatory_breach` is word-bounded, so a
    short token like "chase" cannot fire on a substring inside an unrelated
    word (e.g. "purchase")."""
    cleaned = legal_name.lower().replace(",", " ").replace(".", " ")
    words = [w for w in cleaned.split() if w]
    distinctive = [w for w in words if w not in _ORG_SUFFIX_WORDS] or words

    tokens = {legal_name.lower(), "reporting bank", " ".join(distinctive)}
    tokens.update(distinctive)
    if rssd:
        tokens.add(str(rssd).lower())
    return sorted(t for t in tokens if t)


def asserts_regulatory_breach(text: str, bank_tokens: list[str]) -> bool:
    """Does `text` read as an assertion that the REAL institution (named by
    one of `bank_tokens`, lower-cased) breached a REGULATORY limit?

    Two false-positive traps a naive whole-text scan hits on this estate's
    OWN methodology documents (verified live, not assumed): the regulation
    text itself is quoted ("...exceeds 25% of its eligible capital...") next
    to the phrase "the reporting bank", and the documents explicitly DENY
    any real finding ("every appetite, breach, and proposal it describes
    belongs to this dataset's synthetic ... envelope") using the word
    "breach" itself. A substring-anywhere-in-the-document check would flag
    both as violations; neither is one. So this requires a bank reference
    and a regulatory keyword to sit within `_ASSERTION_WINDOW_WORDS` words
    of the SAME breach-word occurrence -- narrow enough that this project's
    own honest methodology prose (measured, see the module-level constant's
    docstring) never trips it, wide enough that "The reporting bank
    breached the CRR 25% limit" does.
    """
    words = text.split()
    lowered = [w.lower().strip(string.punctuation) for w in words]
    for i, w in enumerate(lowered):
        if not _BREACH_WORD_RE.match(w):
            continue
        lo = max(0, i - _ASSERTION_WINDOW_WORDS)
        hi = min(len(words), i + _ASSERTION_WINDOW_WORDS + 1)
        window = " ".join(words[lo:hi]).lower()
        # Word-bounded, not `tok in window`: a short distinctive token like
        # "chase" must not fire on a substring inside an unrelated word
        # (e.g. "purchase", "chaser").
        bank_hit = any(re.search(rf"\b{re.escape(tok)}\b", window) for tok in bank_tokens)
        if bank_hit and _REG_KEYWORD_RE.search(window):
            return True
    return False


def regime_key_to_name(key: str) -> str:
    """`regime-version-{key}` node's local key -> its regime string.

    No triple on the `RegimeVersion` node itself carries a bare "crr" /
    "pra" / "reg-o" label (`loaders/load_policy_fluree.py` asserts
    `rdfs:label`, `effectiveFrom`, `limitPctOfCapital` / `limitAbsoluteUsd`,
    and `citesProvision` -- never a `regime` literal), and `citesProvision`
    cannot be used instead: the PRA node cites a CRR passage as the
    provision that STATES its limit (Ruling from
    `generators/generate_limit_envelope.py`'s fix round 1), so reading
    "regime" off a citation would call the PRA node "crr". The node's own
    minted key (`uri(f"regime-version-{rv['key']}")`, `rv['key']` in
    `{"crr-2014-2021", "pra-2022", "reg-o"}`) is unambiguous instead.
    """
    if key.startswith("reg-o"):
        return "reg-o"
    if key.startswith("crr"):
        return "crr"
    if key.startswith("pra"):
        return "pra"
    raise ValueError(f"regime-version key {key!r} matches no known regime prefix")


# ===========================================================================
# Context
# ===========================================================================

@dataclass
class Context:
    """Snapshots of every store, taken once and shared read-only across the
    eight floors (`validators/syndicate.py`'s shape). If a floor ever
    mutates this, the sharing becomes a defect -- Wave 18's own recorded
    lesson, restated here because it would be relearned the same way.
    """

    as_of: str

    # --- Fluree, R ---------------------------------------------------------

    #: (subject_uri, object_uri), one per `ex:connectedTo` edge
    control_edges: list[tuple[str, str]]

    #: same shape, one per `ex:economicallyDependentOn` edge
    dependency_edges: list[tuple[str, str]]

    #: entity_uri -> lei, from every `ex:lei` triple in the ledger
    lei_by_uri: dict[str, str]

    #: subject_uri (of a dependency edge) -> its `ex:edgeProvenance` literal
    dependency_provenance: dict[str, str]

    #: one per `ex:RegimeVersion` node: regime, effective_from, effective_to,
    #: limit_pct_of_capital, limit_absolute_usd, cites_passage_id (list),
    #: provenance
    regimes: list[dict]

    #: the one `ex:LimitEnvelope` node (the internal appetite): key,
    #: limit_pct_of_capital, effective_from, provenance
    appetite: dict

    #: one per `ex:InsiderDesignation` node: node uri, designated LEIs
    #: (only targets that resolve via `ex:lei` -- the invented natural
    #: person never does), provenance
    insider_designations: list[dict]

    # --- Postgres, E ---------------------------------------------------------

    #: lei -> ISO 3166-1 alpha-2 country, from `ccf_v2.v_entity_jurisdiction`
    jurisdiction: dict[str, str]

    #: lei -> booked commitment in DOLLARS, `SUM(commitment_amount)` from
    #: `ccf_v2.facility`, grouped by `borrower_lei`
    exposure: dict[str, float]

    #: lei -> total POST-HAIRCUT pledged collateral in DOLLARS
    #: (`valuation * (1 - haircut)`, summed), joined
    #: `collateral_pledge` -> `collateral_asset` -> `facility.borrower_lei`
    collateral: dict[str, float]

    #: report_date (ISO string) -> tier 1 capital in DOLLARS. Converted on
    #: load from the row's OWN `unit` column -- never assumed
    #: `USD_THOUSANDS` -- because an unread unit is exactly Task 1's defect.
    capital: dict[str, float]

    #: `ccf_v2.exposure_proposal` rows, `expected_outcome` DELIBERATELY NOT
    #: SELECTED (module docstring, Ruling: never read intent as outcome).
    #: Each: proposal_id, subject_lei, facility_type, commitment_amount,
    #: currency, is_hypothetical, provenance.
    proposals: list[dict]

    #: lei -> `memo_context_debt.aggregate_debt`
    debt: dict[str, float]

    #: `validators/memo_debt.py::policy_tolerance`, read live -- never a
    #: local copy of the number.
    debt_tolerance: float

    #: `ccf_v2.large_exposure_projection_plan` rows: plan_id, perspective,
    #: elements_included (list[str]), carries_methodology,
    #: carries_replay_attribution, provenance.
    projection_plans: list[dict]

    #: `ccf_v2.reporting_bank` row where role='reporting_bank' -- its own
    #: legal_name and rssd, used only by the provenance floor's
    #: breach-assertion scan (via `bank_reference_tokens`).
    reporting_bank_name: str
    reporting_bank_rssd: str

    # --- The provenance floor's own population ------------------------------

    #: every free-text / labelled surface floor 8 enumerates: dict with
    #: `store`, `location`, `text`, `provenance`. See the floor's own
    #: docstring for exactly what is and is not included.
    narrative: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def _load_fluree() -> dict:
    control_edges = [(r["a"]["value"], r["b"]["value"]) for r in _q(
        f"SELECT ?a ?b FROM <{L}> WHERE {{ ?a <{EX_CONNECTED_TO}> ?b }}")]
    dependency_edges = [(r["a"]["value"], r["b"]["value"]) for r in _q(
        f"SELECT ?a ?b FROM <{L}> WHERE {{ ?a <{EX_ECONOMICALLY_DEPENDENT_ON}> ?b }}")]
    lei_by_uri = {r["s"]["value"]: r["l"]["value"] for r in _q(
        f"SELECT ?s ?l FROM <{L}> WHERE {{ ?s <{EX_LEI}> ?l }}")}

    dep_subjects = {a for a, _ in dependency_edges}
    dependency_provenance: dict[str, str] = {}
    for r in _q(f"SELECT ?s ?p FROM <{L}> WHERE {{ ?s <{EX_EDGE_PROVENANCE}> ?p }}"):
        s = r["s"]["value"]
        if s in dep_subjects:
            dependency_provenance[s] = r["p"]["value"]

    # Important 2: the free text that actually sits on these subject nodes
    # -- ex:dependencyBasis states the invented economic-dependency claim as
    # fact ("Super Micro's ... designates Extreme Networks' switch fabric
    # as the sole qualified network interconnect"), on a node whose own
    # ex:provenance is `public` (only ex:edgeProvenance, read separately
    # above, disambiguates). Fetched per subject so floor 8 has something
    # to actually scan instead of `"text": ""`.
    dependency_text: dict[str, str] = {}
    for s in dep_subjects:
        label_rows = _q(f"SELECT ?v FROM <{L}> WHERE {{ <{s}> <{RDFS_LABEL}> ?v }}")
        basis_rows = _q(f"SELECT ?v FROM <{L}> WHERE {{ <{s}> <{EX_DEPENDENCY_BASIS}> ?v }}")
        asserted_rows = _q(f"SELECT ?v FROM <{L}> WHERE {{ <{s}> <{EX_ASSERTED_BY}> ?v }}")
        parts = [r["v"]["value"] for r in label_rows + basis_rows + asserted_rows]
        dependency_text[s] = " ".join(parts)

    # --- RegimeVersion nodes ------------------------------------------------
    rv_rows = _q(f"SELECT ?s ?ef ?p FROM <{L}> WHERE "
                 f"{{ ?s a <{EX_REGIME_VERSION}> ; <{EX_EFFECTIVE_FROM}> ?ef ; "
                 f"<{EX_PROVENANCE}> ?p }}")
    regimes: list[dict] = []
    for r in rv_rows:
        node = r["s"]["value"]
        key = local_name(node).removeprefix("regime-version-")
        pct_rows = _q(f"SELECT ?v FROM <{L}> WHERE {{ <{node}> <{EX_LIMIT_PCT}> ?v }}")
        abs_rows = _q(f"SELECT ?v FROM <{L}> WHERE {{ <{node}> <{EX_LIMIT_ABS}> ?v }}")
        to_rows = _q(f"SELECT ?v FROM <{L}> WHERE {{ <{node}> <{EX_EFFECTIVE_TO}> ?v }}")
        cites = sorted(b["c"]["value"] for b in _q(
            f"SELECT ?c FROM <{L}> WHERE {{ <{node}> <{EX_CITES_PROVISION}> ?c }}"))
        regimes.append({
            "node": node,
            "regime": regime_key_to_name(key),
            "effective_from": r["ef"]["value"],
            "effective_to": to_rows[0]["v"]["value"] if to_rows else None,
            "limit_pct_of_capital": float(pct_rows[0]["v"]["value"]) if pct_rows else None,
            "limit_absolute_usd": float(abs_rows[0]["v"]["value"]) if abs_rows else None,
            "cites_passage_id": cites,
            "provenance": r["p"]["value"],
        })

    # --- LimitEnvelope (the one internal appetite) --------------------------
    le_rows = _q(f"SELECT ?s ?l ?ef ?p FROM <{L}> WHERE {{ "
                 f"?s a <{EX_LIMIT_ENVELOPE}> ; <{EX_LIMIT_PCT}> ?l ; "
                 f"<{EX_EFFECTIVE_FROM}> ?ef ; <{EX_PROVENANCE}> ?p }}")
    if len(le_rows) != 1:
        raise RuntimeError(
            f"expected exactly 1 ex:LimitEnvelope node, found {len(le_rows)} -- "
            "run loaders/load_policy_fluree.py")
    le = le_rows[0]
    le_label_rows = _q(f"SELECT ?v FROM <{L}> WHERE {{ <{le['s']['value']}> <{RDFS_LABEL}> ?v }}")
    appetite = {
        "node": le["s"]["value"],
        "limit_pct_of_capital": float(le["l"]["value"]),
        "effective_from": le["ef"]["value"],
        "provenance": le["p"]["value"],
        "text": le_label_rows[0]["v"]["value"] if le_label_rows else "",
    }

    # --- InsiderDesignation nodes --------------------------------------------
    designations: list[dict] = []
    for r in _q(f"SELECT ?s ?p FROM <{L}> WHERE {{ "
                f"?s a <{EX_INSIDER_DESIGNATION}> ; <{EX_PROVENANCE}> ?p }}"):
        node = r["s"]["value"]
        targets = [b["d"]["value"] for b in _q(
            f"SELECT ?d FROM <{L}> WHERE {{ <{node}> <{EX_DESIGNATED_PERSON}> ?d }}")]
        designated_leis = sorted({lei_by_uri[t] for t in targets if t in lei_by_uri})
        # Important 2: ex:assertedBy on this node reads e.g. "JPMorganChase
        # General Counsel -- Related Persons Policy review" -- an invented
        # determination attributed to a real bank's real office. rdfs:label
        # carries the case description itself. Both fed to floor 8's scan.
        label_rows = _q(f"SELECT ?v FROM <{L}> WHERE {{ <{node}> <{RDFS_LABEL}> ?v }}")
        asserted_rows = _q(f"SELECT ?v FROM <{L}> WHERE {{ <{node}> <{EX_ASSERTED_BY}> ?v }}")
        text = " ".join(r2["v"]["value"] for r2 in label_rows + asserted_rows)
        designations.append({
            "node": node,
            "targets": targets,
            "designated_leis": designated_leis,
            "provenance": r["p"]["value"],
            "text": text,
        })

    return {
        "control_edges": control_edges,
        "dependency_edges": dependency_edges,
        "lei_by_uri": lei_by_uri,
        "dependency_provenance": dependency_provenance,
        "dependency_text": dependency_text,
        "regimes": regimes,
        "appetite": appetite,
        "insider_designations": designations,
    }


def _load_postgres() -> dict:
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT entity_id, legal_country FROM "{S}".v_entity_jurisdiction')
        jurisdiction = {lei: country for lei, country in cur.fetchall() if country}

        cur.execute(f'SELECT borrower_lei, SUM(commitment_amount) '
                    f'FROM "{S}".facility WHERE borrower_lei IS NOT NULL '
                    f'GROUP BY borrower_lei')
        exposure = {lei.strip(): float(amt) for lei, amt in cur.fetchall() if amt is not None}

        cur.execute(f'''
            SELECT f.borrower_lei, ca.valuation, ca.haircut
            FROM "{S}".collateral_pledge p
            JOIN "{S}".collateral_asset ca ON ca.asset_id = p.asset_id
            JOIN "{S}".facility f ON f.facility_id = p.facility_id
            WHERE f.borrower_lei IS NOT NULL
        ''')
        collateral: dict[str, float] = collections.defaultdict(float)
        for lei, valuation, haircut in cur.fetchall():
            collateral[lei.strip()] += float(valuation) * (1 - float(haircut))

        cur.execute(f'SELECT report_date, tier1_capital, unit FROM "{S}".bank_capital')
        capital: dict[str, float] = {}
        for report_date, tier1, unit in cur.fetchall():
            if unit != "USD_THOUSANDS":
                raise RuntimeError(
                    f"bank_capital {report_date}: unexpected unit {unit!r} -- "
                    "this is exactly the unit regression Task 1 repaired; "
                    "refusing to assume a conversion factor")
            capital[report_date.isoformat()] = float(tier1) * 1000

        cur.execute(f'SELECT proposal_id, subject_lei, facility_type, '
                    f'commitment_amount, currency, is_hypothetical, provenance '
                    f'FROM "{S}".exposure_proposal')
        cols = ["proposal_id", "subject_lei", "facility_type", "commitment_amount",
                "currency", "is_hypothetical", "provenance"]
        proposals = [dict(zip(cols, row)) for row in cur.fetchall()]

        cur.execute(f'SELECT lei, aggregate_debt FROM "{S}".memo_context_debt')
        debt = {lei.strip(): float(v) for lei, v in cur.fetchall()}

        debt_tolerance = policy_tolerance(cur)

        cur.execute(f'SELECT plan_id, perspective, elements_included, '
                    f'carries_methodology, carries_replay_attribution, provenance '
                    f'FROM "{S}".large_exposure_projection_plan')
        pcols = ["plan_id", "perspective", "elements_included",
                 "carries_methodology", "carries_replay_attribution", "provenance"]
        projection_plans = [dict(zip(pcols, row)) for row in cur.fetchall()]

        cur.execute(f'SELECT legal_name, rssd FROM "{S}".reporting_bank '
                    f"WHERE role = 'reporting_bank'")
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("no reporting_bank row with role='reporting_bank' -- "
                               "run loaders/load_reporting_bank.py first")
        reporting_bank_name, reporting_bank_rssd = row

    return {
        "jurisdiction": jurisdiction,
        "exposure": exposure,
        "collateral": dict(collateral),
        "capital": capital,
        "proposals": proposals,
        "debt": debt,
        "debt_tolerance": debt_tolerance,
        "projection_plans": projection_plans,
        "reporting_bank_name": reporting_bank_name,
        "reporting_bank_rssd": reporting_bank_rssd,
    }


def _load_narrative(proposals: list[dict], insider_designations: list[dict],
                    dependency_provenance: dict[str, str],
                    dependency_text: dict[str, str],
                    appetite: dict) -> list[dict]:
    """Every surface floor 8 enumerates. Four groups, matching the brief's
    own four surfaces:

    1. `exposure_proposal` rows (breach and proposal records)
    2. every SQLite `large_exposure_limit_workbook` row, free text included
    3. every MongoDB `doc_type='methodology'` document AND passage
    4. the Fluree elements whose provenance is what makes a real facility
       into an engineered case: the dependency edges, the one
       InsiderDesignation, the one LimitEnvelope

    `regime_text` passages (the 464 rows of actual statute text) are
    deliberately excluded -- they are `public` by design (real, filed
    regulatory text), never claim anything about the real reporting bank's
    OWN standing, and are not "methodology or narrative" in the brief's
    sense. Including them would either fail the label check for a reason
    that is not a defect, or (if exempted ad hoc) quietly narrow the check
    without saying so.
    """
    narrative: list[dict] = []

    for p in proposals:
        narrative.append({
            "store": "postgres",
            "location": f"exposure_proposal.{p['proposal_id']}",
            "text": f"{p['facility_type']} proposal for {p['subject_lei']}",
            "provenance": p["provenance"],
        })

    con = sqlite3.connect(SQLITE_PATH)
    try:
        rows = con.execute(
            "SELECT line_id, group_label, limit_intent, note, owner, provenance "
            "FROM large_exposure_limit_workbook").fetchall()
    finally:
        con.close()
    for line_id, group_label, limit_intent, note, owner, provenance in rows:
        text = " ".join(str(x) for x in (group_label, limit_intent, note, owner) if x)
        narrative.append({
            "store": "sqlite",
            "location": f"large_exposure_limit_workbook.{line_id}",
            "text": text,
            "provenance": provenance,
        })

    db = mongo_db(write=False)
    methodology_doc_ids: list[str] = []
    for d in db["document"].find({"doc_type": "methodology"}):
        methodology_doc_ids.append(d["document_id"])
        narrative.append({
            "store": "mongo_document",
            "location": d["document_id"],
            "text": d["text"],
            "provenance": d.get("provenance"),
        })
    # Important 5: derived from the documents just found above, not a
    # hardcoded two-id `$in` -- a third methodology document would
    # otherwise silently escape the passage half of this scan.
    for p in db["passage"].find({"document_id": {"$in": methodology_doc_ids}}):
        narrative.append({
            "store": "mongo_passage",
            "location": p["passage_id"],
            "text": p["text"],
            "provenance": p.get("provenance"),
        })

    for subject, prov in dependency_provenance.items():
        narrative.append({
            "store": "fluree",
            "location": f"economicallyDependentOn({local_name(subject)})",
            "text": dependency_text.get(subject, ""),
            "provenance": prov,
        })
    for d in insider_designations:
        narrative.append({
            "store": "fluree",
            "location": f"InsiderDesignation({local_name(d['node'])})",
            "text": d.get("text", ""),
            "provenance": d["provenance"],
        })
    narrative.append({
        "store": "fluree",
        "location": f"LimitEnvelope({local_name(appetite['node'])})",
        "text": appetite.get("text", ""),
        "provenance": appetite["provenance"],
    })

    return narrative


def load_context(as_of: str | None = None) -> Context:
    """Build one `Context`, read-only, from all four live stores.

    Expensive (Fluree round-trips, a handful of Postgres joins, two Mongo
    reads, one SQLite read) -- callers share ONE instance across all eight
    floors, exactly `validators/syndicate.py`'s shape.
    """
    from datetime import date

    fl = _load_fluree()
    pg = _load_postgres()
    narrative = _load_narrative(pg["proposals"], fl["insider_designations"],
                                fl["dependency_provenance"], fl["dependency_text"],
                                fl["appetite"])

    return Context(
        as_of=as_of or date.today().isoformat(),
        control_edges=fl["control_edges"],
        dependency_edges=fl["dependency_edges"],
        lei_by_uri=fl["lei_by_uri"],
        dependency_provenance=fl["dependency_provenance"],
        regimes=fl["regimes"],
        appetite=fl["appetite"],
        insider_designations=fl["insider_designations"],
        jurisdiction=pg["jurisdiction"],
        exposure=pg["exposure"],
        collateral=pg["collateral"],
        capital=pg["capital"],
        proposals=pg["proposals"],
        debt=pg["debt"],
        debt_tolerance=pg["debt_tolerance"],
        projection_plans=pg["projection_plans"],
        reporting_bank_name=pg["reporting_bank_name"],
        reporting_bank_rssd=pg["reporting_bank_rssd"],
        narrative=narrative,
    )


# ---------------------------------------------------------------------------
# Shared recomputation helpers (used by more than one floor)
# ---------------------------------------------------------------------------

def current_tier1_usd(ctx: Context) -> float:
    """Most recent `bank_capital` report date's tier 1, in dollars."""
    if not ctx.capital:
        raise RuntimeError("ctx.capital is empty -- no bank_capital rows loaded")
    latest = max(ctx.capital)
    return ctx.capital[latest]


def current_crr_pra_pct(ctx: Context) -> float:
    """The CRR/PRA large-exposure percentage limit actually in force --
    'in force' meaning no `effective_to` (open-ended), matching
    `generators/generate_proposals.py::current_pct_limit_fraction`'s own
    definition, reproduced independently rather than imported."""
    pcts = {r["limit_pct_of_capital"] for r in ctx.regimes
            if r["regime"] in ("crr", "pra") and r["effective_to"] is None
            and r["limit_pct_of_capital"] is not None}
    if not pcts:
        raise RuntimeError("no in-force CRR/PRA RegimeVersion carries limitPctOfCapital")
    if len(pcts) > 1:
        raise RuntimeError(f"in-force CRR/PRA regimes disagree: {sorted(pcts)}")
    return pcts.pop()


def reg_o_absolute_usd(ctx: Context) -> float:
    rows = [r for r in ctx.regimes if r["regime"] == "reg-o"]
    abs_vals = {r["limit_absolute_usd"] for r in rows if r["limit_absolute_usd"] is not None}
    if len(abs_vals) != 1:
        raise RuntimeError(f"expected exactly one reg-o limitAbsoluteUsd, found {abs_vals}")
    return abs_vals.pop()


# ===========================================================================
# The eight floors
# ===========================================================================

#: 26 is not a floor -- it is the measured, live-verified component count
#: (`loaders/load_group_edges.py` asserts the identical number against the
#: same edges at load time). A recomputation that disagreed would mean the
#: control graph changed under this validator, which is worth failing loudly
#: on rather than silently adopting a new number.
EXPECTED_CONTROL_COMPONENTS = 26
MIN_MULTI_COUNTRY_GROUPS = 9
MIN_COUNTRIES_FOR_SPAN = 3


def groups_recompute(ctx: Context | None = None) -> tuple[bool, str]:
    """Forms connected components FRESH from `ex:connectedTo` -- there is no
    stored group id anywhere to read instead. Country-spanning is reported
    per-group and counted separately from the collective 26, so one cannot
    stand in for the other."""
    ctx = ctx or load_context()
    groups = components(ctx.control_edges)
    n_components = len(groups)

    multi_country = 0
    for members in groups.values():
        leis = {ctx.lei_by_uri[m] for m in members if m in ctx.lei_by_uri}
        countries = {ctx.jurisdiction[lei] for lei in leis if ctx.jurisdiction.get(lei)}
        if len(countries) >= MIN_COUNTRIES_FOR_SPAN:
            multi_country += 1

    ok = (n_components == EXPECTED_CONTROL_COMPONENTS
          and multi_country >= MIN_MULTI_COUNTRY_GROUPS)
    detail = (f"{n_components} component(s) (expected {EXPECTED_CONTROL_COMPONENTS}); "
              f"{multi_country} span >= {MIN_COUNTRIES_FOR_SPAN} countries "
              f"individually (floor {MIN_MULTI_COUNTRY_GROUPS})")
    return ok, detail


def dependency_changes_binding_limit(ctx: Context | None = None) -> tuple[bool, str]:
    """For each `economicallyDependentOn` edge, recompute its subject's group
    % of tier 1 WITH and WITHOUT that one edge (control edges always
    present), and which of {internal appetite, CRR/PRA 25%} each breaches.
    If the breached set differs, removing the edge changed which limit
    binds -- a claim about ORDERING no count could establish."""
    ctx = ctx or load_context()
    tier1 = current_tier1_usd(ctx)
    appetite_pct = ctx.appetite["limit_pct_of_capital"]
    crr_pra_pct = current_crr_pra_pct(ctx)

    def breach_set(pct: float) -> frozenset[str]:
        breached = set()
        if pct > appetite_pct:
            breached.add("appetite")
        if pct > crr_pra_pct:
            breached.add("crr_pra")
        return frozenset(breached)

    consequential = []
    for edge in ctx.dependency_edges:
        subject, _ = edge
        remaining = [e for e in ctx.dependency_edges if e != edge]
        pct_with = (group_dollar_total(ctx.control_edges + ctx.dependency_edges,
                                       subject, ctx.lei_by_uri, ctx.exposure)
                    / tier1 * 100)
        pct_without = (group_dollar_total(ctx.control_edges + remaining,
                                          subject, ctx.lei_by_uri, ctx.exposure)
                       / tier1 * 100)
        if breach_set(pct_with) != breach_set(pct_without):
            consequential.append((subject, pct_without, pct_with,
                                  breach_set(pct_without), breach_set(pct_with)))

    ok = bool(consequential)
    if ok:
        s, before, after, bset_before, bset_after = consequential[0]
        detail = (f"{len(consequential)}/{len(ctx.dependency_edges)} edge(s) change "
                  f"the binding limit, e.g. {local_name(s)}: {before:.4f}% "
                  f"(breaches {sorted(bset_before) or 'nothing'}) -> {after:.4f}% "
                  f"(breaches {sorted(bset_after) or 'nothing'})")
    else:
        detail = (f"none of {len(ctx.dependency_edges)} dependency edge(s) change "
                  f"which limit binds (appetite={appetite_pct}%, crr/pra={crr_pra_pct}%)")
    return ok, detail


def regime_divergence(ctx: Context | None = None) -> tuple[bool, str]:
    """For each `InsiderDesignation`'s aggregated LEI group (Ruling L15-R1),
    recompute exposure against BOTH the CRR/PRA percentage limit and Reg
    O's absolute cap. A group compliant under one and in breach under the
    other is the divergence claim -- two different recomputed answers over
    the identical exposure figure."""
    ctx = ctx or load_context()
    tier1 = current_tier1_usd(ctx)
    crr_pra_threshold = tier1 * current_crr_pra_pct(ctx) / 100
    try:
        reg_o_cap = reg_o_absolute_usd(ctx)
    except RuntimeError as exc:
        # Strip Reg O from the context (the brief's own negative control)
        # and there is no second regime to diverge against -- fail rather
        # than let a KeyError/RuntimeError masquerade as a floor result.
        return False, f"cannot establish Reg O's absolute cap: {exc}"

    for d in ctx.insider_designations:
        if not d["designated_leis"]:
            continue
        total = sum(ctx.exposure.get(lei, 0.0) for lei in d["designated_leis"])
        compliant_crr_pra = total <= crr_pra_threshold
        breaches_reg_o = total > reg_o_cap
        if compliant_crr_pra and breaches_reg_o:
            return True, (
                f"{local_name(d['node'])}: ${total:,.0f} across "
                f"{d['designated_leis']} is compliant under CRR/PRA "
                f"(<= ${crr_pra_threshold:,.0f}) and breaches Reg O "
                f"(> ${reg_o_cap:,.0f}, {total / reg_o_cap:.0f}x)")
    return False, (
        f"no InsiderDesignation group is both compliant under CRR/PRA "
        f"(<= ${crr_pra_threshold:,.0f}) and in breach of Reg O "
        f"(> ${reg_o_cap:,.0f})")


def _proposal_gross_net(ctx: Context) -> tuple[list[dict], float]:
    """One row per proposal: `proposal_id`, `gross` (booked group exposure +
    proposed commitment) and `net` (gross minus the group's real
    post-haircut collateral), plus the live 25%-of-tier-1 threshold.

    Shared by `proposal_breaches` and `mitigation_is_load_bearing` so the
    two floors' arithmetic -- and the distinctness check between them --
    can never silently diverge into two different numbers for the same
    proposal. `expected_outcome` is never selected into `ctx.proposals` in
    the first place (`_load_postgres`), so there is nothing here to
    accidentally read as the answer.
    """
    tier1 = current_tier1_usd(ctx)
    threshold = tier1 * current_crr_pra_pct(ctx) / 100
    rows: list[dict] = []
    for p in ctx.proposals:
        uri = next((u for u, lei in ctx.lei_by_uri.items() if lei == p["subject_lei"]), None)
        if uri is None:
            continue
        existing = group_dollar_total(ctx.control_edges, uri, ctx.lei_by_uri, ctx.exposure)
        existing_collateral = group_dollar_total(ctx.control_edges, uri, ctx.lei_by_uri,
                                                 ctx.collateral)
        gross = existing + float(p["commitment_amount"])
        net = gross - existing_collateral
        rows.append({"proposal_id": p["proposal_id"], "existing": existing,
                     "collateral": existing_collateral, "gross": gross, "net": net})
    return rows, threshold


def proposal_breaches(ctx: Context | None = None) -> tuple[bool, str]:
    """Recomputes NET-of-mitigation group exposure for each proposal and
    compares to the LIVE 25%-of-tier-1 threshold.

    Fix round 1 (coordinator finding, Important): the product's own §B
    request-parameter table defaults `apply_mitigation` to `true`, so the
    figure a caller gets BY DEFAULT is the NET one, not gross. A proposal
    over the limit gross but under it net is not a breaching proposal under
    that default -- it is the `mitigation_is_load_bearing` case. Asserting
    on gross alone let two proposals that were both "over gross, under net"
    pass THIS floor and floor 5 identically, on data that demonstrated the
    same thing twice instead of the two distinct §F conditions.

    So this floor now requires two things, together, neither of which the
    old gross-only check nor `mitigation_is_load_bearing` alone could see:
    (1) at least one proposal breaches NET of real post-haircut collateral
    -- the breach survives the default mitigation, not merely the gross
    figure; (2) a DIFFERENT proposal is cured by mitigation (over gross,
    under net) -- §F asks for both a breach and a cure, and a dataset where
    the same proposal (or no second proposal at all) satisfies both would
    not have shown that.
    """
    ctx = ctx or load_context()
    rows, threshold = _proposal_gross_net(ctx)

    breaches = [r for r in rows if r["net"] > threshold]
    cured = [r for r in rows if r["gross"] > threshold and r["net"] <= threshold]

    if not breaches:
        return False, (
            f"no proposal's recomputed NET exposure (post-haircut) exceeds "
            f"${threshold:,.0f} -- a gross-only breach does not survive the "
            f"product's default apply_mitigation=true")
    if not cured:
        return False, (
            f"{breaches[0]['proposal_id']} breaches net of mitigation "
            f"(${breaches[0]['net']:,.0f} > ${threshold:,.0f}), but no "
            f"DISTINCT proposal is cured by mitigation -- §F wants both a "
            f"breach that survives it and a case cured by it")
    overlap = {r["proposal_id"] for r in breaches} & {r["proposal_id"] for r in cured}
    if overlap:
        # Cannot happen given `net > threshold` and `net <= threshold` are
        # mutually exclusive on the same computed value for the same
        # proposal -- kept as a loud, checked invariant rather than a
        # comment trusting that exclusivity silently.
        return False, (
            f"{sorted(overlap)} satisf(ies) both the breach and the "
            f"mitigation-cured predicate -- they must be distinct proposals")

    b, c = breaches[0], cured[0]
    return True, (
        f"{b['proposal_id']}: gross ${b['gross']:,.0f}, net ${b['net']:,.0f} "
        f"(post-haircut, - ${b['collateral']:,.0f} collateral) both exceed "
        f"${threshold:,.0f} -- breach SURVIVES mitigation; distinct from "
        f"{c['proposal_id']} (gross ${c['gross']:,.0f} > limit, net "
        f"${c['net']:,.0f} <= limit), which mitigation CURES")


def mitigation_is_load_bearing(ctx: Context | None = None) -> tuple[bool, str]:
    """Recomputes gross (booked + proposed) and net-of-real-post-haircut-
    collateral for each proposal, from the same `_proposal_gross_net` rows
    `proposal_breaches` uses. A flip -- over the limit gross, under it net
    -- proves the mitigation is load-bearing, which no static count of
    collateral rows could show."""
    ctx = ctx or load_context()
    rows, threshold = _proposal_gross_net(ctx)

    for r in rows:
        if r["gross"] > threshold and r["net"] <= threshold:
            return True, (
                f"{r['proposal_id']}: gross ${r['gross']:,.0f} > ${threshold:,.0f} "
                f"before mitigation; net ${r['net']:,.0f} (- ${r['collateral']:,.0f} "
                f"post-haircut collateral) <= threshold after")
    return False, f"no proposal flips from over to under ${threshold:,.0f} after collateral"


def debt_tolerance_breached(ctx: Context | None = None) -> tuple[bool, str]:
    """Sums `memo_context_debt.aggregate_debt` across each `connectedTo`
    group and compares to the LIVE policy tolerance -- an aggregation
    across a group, against a value read from policy, neither of which a
    stored per-entity flag could represent."""
    ctx = ctx or load_context()
    groups = components(ctx.control_edges)

    for members in groups.values():
        leis = {ctx.lei_by_uri[m] for m in members if m in ctx.lei_by_uri}
        total = sum(ctx.debt.get(lei, 0.0) for lei in leis)
        if total > ctx.debt_tolerance:
            return True, (
                f"group of {len(leis)} member(s) sums aggregate_debt to "
                f"{total:.4f}, above tolerance {ctx.debt_tolerance:.4f}")
    return False, f"no group's summed aggregate_debt exceeds tolerance {ctx.debt_tolerance:.4f}"


def projection_plans_differ(ctx: Context | None = None) -> tuple[bool, str]:
    """The three `elements_included` sets must be pairwise distinct -- three
    identical rows would satisfy a count of 3 and demonstrate nothing about
    what each perspective actually receives."""
    ctx = ctx or load_context()
    sets = [(p["perspective"], frozenset(p["elements_included"]))
            for p in ctx.projection_plans]
    if len(sets) < 2:
        return False, f"only {len(sets)} projection plan(s) loaded, need >= 2 to compare"

    distinct = len({s for _, s in sets}) == len(sets)
    detail = "; ".join(f"{persp}={sorted(s)}" for persp, s in sets)
    return distinct, (f"{len(sets)} plan(s), "
                      f"{'pairwise distinct' if distinct else 'NOT all distinct'}: {detail}")


def no_public_row_in_a_breach(ctx: Context | None = None) -> tuple[bool, str]:
    """The provenance floor -- two SEPARATE assertions, by enumeration, over
    `ctx.narrative` (Ruling L15-R2 explains its exact population):

    1. every row is labelled `synthetic — internal` or
       `synthetic — engineered` (never `public`, and never anything else --
       an unrecognised label is exactly as concerning as `public` here,
       since it means this floor is not looking at what it thinks it is);
    2. no free-text row reads as an assertion that the REAL institution
       breached a regulatory limit (`asserts_regulatory_breach`) -- NOT
       implied by (1): a correctly-labelled row can still carry a sentence
       that reads as fact once quoted out of its table.
    """
    ctx = ctx or load_context()
    if not ctx.narrative:
        raise RuntimeError("ctx.narrative is empty -- the floor would pass vacuously")

    mislabelled = [n for n in ctx.narrative if n["provenance"] not in SYNTHETIC_PROVENANCE]
    if mislabelled:
        return False, (
            f"{len(mislabelled)}/{len(ctx.narrative)} row(s) not labelled "
            f"synthetic (public or unrecognised provenance): "
            f"{[n['location'] for n in mislabelled][:5]}")

    bank_tokens = bank_reference_tokens(ctx.reporting_bank_name, ctx.reporting_bank_rssd)
    hits = [n for n in ctx.narrative
            if n["text"] and asserts_regulatory_breach(n["text"], bank_tokens)]
    if hits:
        return False, (
            f"{len(hits)} free-text row(s) assert a regulatory breach by the "
            f"real institution: {[n['location'] for n in hits]}")

    return True, (
        f"{len(ctx.narrative)} row(s) checked across "
        f"{len({n['store'] for n in ctx.narrative})} store(s): all labelled "
        f"synthetic, 0 free-text assertions of a real regulatory breach")


FLOORS: list[tuple[str, "callable"]] = [
    ("1. groups recompute (26 components, >=9 span >=3 countries)", groups_recompute),
    ("2. dependency edge changes binding limit", dependency_changes_binding_limit),
    ("3. regime divergence (CRR/PRA compliant, Reg O breach)", regime_divergence),
    ("4. proposal breaches net of mitigation, distinct from the cure", proposal_breaches),
    ("5. mitigation is load-bearing (gross over, net under)", mitigation_is_load_bearing),
    ("6. debt tolerance breached (live policy_tolerance)", debt_tolerance_breached),
    ("7. three ProjectionPlans pairwise distinct", projection_plans_differ),
    ("8. no public row in a breach (provenance floor)", no_public_row_in_a_breach),
]


def render(state: str, condition: str, detail: str) -> str:
    return f"  [{state}] {condition:56s} {detail}"


def main() -> int:
    ctx = load_context()
    print("LARGE-EXPOSURE-RWA-CONCENTRATION — §F floors, recomputed from the "
          f"stores at as_of={ctx.as_of}\n")

    failures = 0
    for label, floor in FLOORS:
        ok, detail = floor(ctx)
        if not ok:
            failures += 1
        print(render("PASS" if ok else "FAIL", label, detail))

    print(f"\n  {len(FLOORS) - failures} passed · {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
