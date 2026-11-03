#!/usr/bin/env python3
"""Wave 8 — audit the anchor cast against the union of all 22 spec §F envelopes.

Waves 0–7 screened the 50 anchors against **8** specs. `docs/spec-digest.md`
records the other 14, and they impose constraints the screen never tested. This
is the audit `spec-digest.md` §0 calls for: cheap now, expensive after five more
waves of loading on top of a cast that cannot carry the conditions.

`conditions.py` asks *"is this condition satisfiable against loaded data?"*. This
asks the prior question: **"can this cast ever carry it?"** — which is a property
of who was selected, not of what has been loaded.

Three verdicts, and the third is not a failure:

    SATISFIED     the cast carries it; checkable against loaded data now
    SHORTFALL     the cast is checkable and does NOT carry it -> extend or engineer
    NEEDS FETCH   not decidable locally; the probe required is named

NEEDS FETCH is honest reporting, not a gap. A condition depending on TRACE cannot
be settled from an estate that has never fetched TRACE, and guessing would be
worse than saying so.

Read-only. Touches Postgres, Fluree, and MongoDB; writes nothing.

    uv run validators/cast_audit.py
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field

from ccf import fluree
from ccf.config import (FLUREE_LEDGER_V2, PG_SCHEMA_V2, REPO_ROOT, mongo_db,
                        pg_connect)

S = PG_SCHEMA_V2
L = FLUREE_LEDGER_V2

SATISFIED = "SATISFIED"
SHORTFALL = "SHORTFALL"
NEEDS_FETCH = "NEEDS FETCH"


@dataclass
class Finding:
    spec: str
    condition: str
    verdict: str
    detail: str = ""
    remedy: str = ""


findings: list[Finding] = []


def record(spec: str, condition: str, verdict: str, detail: str = "",
           remedy: str = "") -> None:
    findings.append(Finding(spec, condition, verdict, detail, remedy))


def threshold(spec: str, condition: str, actual: int, floor: int,
              unit: str = "", remedy: str = "") -> None:
    """A condition the loaded estate can decide outright."""
    ok = actual >= floor
    record(
        spec, condition, SATISFIED if ok else SHORTFALL,
        f"{actual} / {floor} {unit}".strip(),
        "" if ok else remedy,
    )


# --------------------------------------------------------------------------
# A · Cast shape
# --------------------------------------------------------------------------
def audit_cast_shape() -> None:
    anchors = json.loads(
        (REPO_ROOT / "sources" / "screening" / "anchors_final.json").read_text()
    )["anchors"]

    threshold("counterparty-reference-snapshot", "anchor obligors",
              len(anchors), 50, "anchors",
              "re-run generators/select_anchors.py with a wider net")

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM "{S}".legal_entity')
        pg_entities = cur.fetchone()[0]
        cur.execute(
            f'SELECT legal_jurisdiction, COUNT(*) FROM "{S}".legal_entity '
            f"GROUP BY 1 ORDER BY 2 DESC"
        )
        juris = cur.fetchall()

    record("counterparty-reference-snapshot", "entities with attributes",
           SATISFIED, f"{pg_entities} in Postgres")

    # §F says connected GROUPS spanning >= 3 jurisdictions. The unit is the
    # group, not the anchor -- so this must measure the family graph, not
    # `legal_entity`, which holds the 50 anchors and nothing else.
    #
    # An earlier version of this check queried `legal_entity` and reported
    # "3 countries, 3 non-US entities -> SHORTFALL". That was a false positive:
    # it measured anchor DOMICILE and called it the cast's jurisdictional
    # spread. The subsidiaries carrying the cross-border structure were never
    # in the population being counted.
    countries: dict[str, int] = {}
    for code, n in juris:
        countries[(code or "?").split("-")[0]] = (
            countries.get((code or "?").split("-")[0], 0) + n
        )
    record("counterparty-reference-snapshot", "anchor domicile spread", SATISFIED,
           ", ".join(f"{c}={n}" for c, n in
                     sorted(countries.items(), key=lambda kv: -kv[1])[:6])
           + "  (anchors only — NOT the group measure)")

    # The family graph, from the GLEIF Level 2 relationships Wave 3 loaded.
    graph_countries: dict[str, int] = {}
    rels = REPO_ROOT / "sources" / "screening" / "gleif_relationships.json"
    if rels.exists():
        for edge in json.loads(rels.read_text()).get("edges", []):
            code = (edge.get("jurisdiction") or "").split("-")[0]
            if code:
                graph_countries[code] = graph_countries.get(code, 0) + 1

    if not graph_countries:
        record("large-exposure-rwa-concentration", "group jurisdictions",
               SHORTFALL, "no GLEIF relationship jurisdictions available",
               "run generators/fetch_gleif_relationships.py")
        return

    ranked = sorted(graph_countries.items(), key=lambda kv: -kv[1])
    threshold("large-exposure-rwa-concentration",
              "COUNTRIES across the family graph", len(graph_countries), 3,
              "countries", "extend the cast to foreign-domiciled families")
    record("large-exposure-rwa-concentration", "group country spread", SATISFIED,
           ", ".join(f"{c}={n}" for c, n in ranked[:8]))

    non_us = sum(n for c, n in graph_countries.items() if c != "US")
    record(
        "large-exposure-rwa-concentration",
        "cross-border edges available for a connected group",
        SATISFIED if non_us >= 5 else SHORTFALL,
        f"{non_us} non-US relationship edges across "
        f"{len([c for c in graph_countries if c != 'US'])} countries",
        "" if non_us >= 5 else
        "engineer the cross-border group and label it `synthetic — engineered`",
    )

    # The same spread is what makes domestic-vs-global ultimate parent
    # observable: they diverge exactly where a chain crosses a border.
    record(
        "corporate-family-tree",
        "chains crossing a border (domestic != global ultimate parent)",
        SATISFIED if non_us >= 1 else SHORTFALL,
        f"{non_us} cross-border edges — the divergence is demonstrable",
        "" if non_us >= 1 else
        "with no cross-border chain the two ultimate-parent properties collapse "
        "to the same answer and the distinction cannot be shown",
    )

    # kyc-refresh needs UK Companies House PSC -- the only free person-level
    # beneficial-ownership source in the catalog.
    #
    # This previously reported SHORTFALL on "no GB-domiciled entity", having
    # queried `legal_entity` (the 50 anchors, all US-domiciled). The UK entities
    # are subsidiaries and live in the family graph, so the population was wrong
    # -- the same error as the jurisdiction count below.
    gb_leis: set[str] = set()
    rels_path = REPO_ROOT / "sources" / "screening" / "gleif_relationships.json"
    if rels_path.exists():
        for edge in json.loads(rels_path.read_text()).get("edges", []):
            if (edge.get("jurisdiction") or "").upper().startswith("GB"):
                gb_leis |= {edge["parent_lei"], edge["child_lei"]}

    if not gb_leis:
        record("kyc-refresh-beneficial-ownership",
               "UK entities for the PSC register", SHORTFALL,
               "no GB entity anywhere in the family graph",
               "add UK anchors, or source the person layer synthetically")
    else:
        # Having UK companies is necessary, not sufficient. A wholly-owned UK
        # subsidiary of a US filer normally files its parent as a Relevant Legal
        # Entity rather than a natural person, so PSC returns a corporate PSC and
        # no person. The spec wants the graph walked TO natural persons, so the
        # open question is yield, not presence -- and only a fetch settles it.
        record(
            "kyc-refresh-beneficial-ownership",
            "UK entities available to probe against PSC", NEEDS_FETCH,
            f"{len(gb_leis)} GB-jurisdiction entities in the family graph",
            "Resolve these to Companies House numbers and pull PSC records. "
            "Expect mostly RLE (corporate) PSCs rather than natural persons, "
            "because they are subsidiaries of US filers. If the natural-person "
            "yield is too low, the person layer is synthetic — which CLAUDE.md "
            "rule 3 requires pseudonymizing anyway, so little is lost.",
        )


# --------------------------------------------------------------------------
# B · Public filing carriers -- decidable from the screening profile
# --------------------------------------------------------------------------
def audit_filing_carriers() -> None:
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f"""
            SELECT
              COUNT(*) FILTER (WHERE count_8k_item_2_04 > 0),
              COUNT(*) FILTER (WHERE count_8k_item_2_03 > 0),
              COUNT(*) FILTER (WHERE count_8k_item_4_02 > 0),
              COUNT(*) FILTER (WHERE count_8k_item_1_01 > 0)
            FROM "{S}".filing_profile
        """)
        i204, i203, i402, i101 = cur.fetchone()

    threshold("credit-surveillance-early-warning",
              "anchors with a real 8-K Item 2.04 (acceleration)", i204, 2,
              "anchors", "screen additionally on Item 2.04 presence")
    threshold("credit-surveillance-early-warning",
              "anchors with 8-K Item 4.02 (non-reliance)", i402, 1,
              "anchors", "an Item 4.02 filer strengthens the composite case")
    threshold("ib-opportunity-synthesis",
              "anchors with 8-K Item 1.01 (material agreement)", i101, 5,
              "anchors", "Item 1.01 carries the M&A/DCM event signal")

    # Item 2.03 = creation of a direct financial obligation, i.e. debt issuance.
    # The best LOCAL proxy for "has public debt TRACE might carry". It is a
    # proxy, not a substitute -- TRACE coverage still needs a fetch.
    record(
        "rating-and-spread-migration",
        "anchors with public debt issuance (8-K Item 2.03)",
        SATISFIED if i203 >= 30 else SHORTFALL,
        f"{i203} / 30 anchors",
        "" if i203 >= 30 else (
            "§F wants ~30 obligors TRACE actually carries observations for. "
            "Item 2.03 is a local proxy only — confirm against TRACE before "
            "committing (see NEEDS FETCH below)."
        ),
    )


# --------------------------------------------------------------------------
# C · Document-derived -- decidable from the EX-10 corpus already in Mongo
# --------------------------------------------------------------------------
CLAUSE_PROBES: list[tuple[str, str, str, int]] = [
    # (spec, label, regex, floor)
    ("syndicated-lending-co-lender", "credit agreements with a Commitment Schedule",
     r"(commitment\s+schedule|schedule\s+[I1](?:\.\d+)?\s*[-–—:]?\s*commitments|"
     r"schedule\s+2\.0?1\b)", 6),
    ("credit-exposure-rollup", "agreements naming a guarantor schedule",
     r"(guarantor\s+schedule|schedule\s+of\s+guarantors|subsidiary\s+guarantor)", 10),
    ("credit-exposure-rollup", "agreements with a cross-default clause",
     r"cross[\s-]?default", 10),
    ("collateral-and-setoff-coverage", "agreements with a negative pledge",
     r"negative\s+pledge", 1),
    ("collateral-and-setoff-coverage", "agreements with a security/collateral schedule",
     r"(security\s+agreement|collateral\s+schedule|pledge\s+agreement)", 5),
    ("large-exposure-rwa-concentration", "agreements naming related-party dealings",
     r"(related\s+party|affiliate\s+transaction)", 3),
]


def audit_document_corpus() -> None:
    db = mongo_db()
    docs = list(db["document"].find(
        {"form": {"$in": ["8-K", "10-K", "10-Q", "S-1", "424B"]}},
        {"text": 1, "lei": 1, "document_id": 1},
    ))
    if not docs:
        record("covenant-cross-reference", "document corpus", SHORTFALL,
               "no documents in MongoDB", "run the Wave 6 loaders")
        return

    record("covenant-cross-reference", "filed documents available to probe",
           SATISFIED, f"{len(docs)} documents")

    for spec, label, pattern, floor in CLAUSE_PROBES:
        rx = re.compile(pattern, re.I)
        hits = {d["lei"] for d in docs if d.get("text") and rx.search(d["text"])}
        threshold(
            spec, label, len(hits), floor, "obligors",
            "widen the EX-10 fetch, or engineer the structure and label it "
            "`synthetic — engineered`",
        )


# --------------------------------------------------------------------------
# D · Peer cohort spread -- credit-memo's natural Context Debt source
# --------------------------------------------------------------------------
def audit_peer_cohorts() -> None:
    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(f"""
            SELECT sic, COUNT(DISTINCT cik) AS n
            FROM "{S}".peer_entity
            WHERE sic IS NOT NULL
            GROUP BY sic ORDER BY n DESC
        """)
        cohorts = cur.fetchall()

    if not cohorts:
        record("credit-memo-context", "peer cohorts", SHORTFALL,
               "no peer entities loaded", "run loaders/load_xbrl_peers.py")
        return

    rich = [c for c, n in cohorts if n >= 15]
    thin = [c for c, n in cohorts if n <= 3]

    record("credit-memo-context", "a RICH peer cohort (>= 15 comparables)",
           SATISFIED if rich else SHORTFALL,
           f"{len(rich)} cohorts >= 15 (largest SIC {cohorts[0][0]}={cohorts[0][1]})",
           "" if rich else "extend the peer fetch for at least one dense SIC band")
    record("credit-memo-context", "a THIN peer cohort (<= 3 comparables)",
           SATISFIED if thin else SHORTFALL,
           f"{len(thin)} cohorts <= 3",
           "" if thin else (
               "peer thinness is the catalog's most natural Context Debt source; "
               "without a thin cohort it must be engineered instead"
           ))


# --------------------------------------------------------------------------
# E · Graph shape -- connected groups for the capstone
# --------------------------------------------------------------------------
def audit_graph_shape() -> None:
    owns = ("https://spec.edmcouncil.org/fibo/ontology/FND/OwnershipAndControl/"
            "Ownership/owns")
    controls = ("https://spec.edmcouncil.org/fibo/ontology/FND/Relations/"
                "Relations/controls")
    q = (f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{L}> "
         f"WHERE {{ {{ ?s <{owns}> ?o }} UNION {{ ?s <{controls}> ?o }} }}")
    try:
        n = int(fluree.query(q)["results"]["bindings"][0]["n"]["value"])
    except Exception as exc:  # noqa: BLE001
        record("large-exposure-rwa-concentration", "connected groups", SHORTFALL,
               f"Fluree query failed: {str(exc)[:60]}")
        return
    threshold("large-exposure-rwa-concentration",
              "entities heading a group (>= 1 outbound edge)", n, 15, "groups",
              "the capstone wants ~15 connected groups")


# --------------------------------------------------------------------------
# F · Not decidable locally -- name the probe rather than guess
# --------------------------------------------------------------------------
FETCH_GATED: list[tuple[str, str, str]] = [
    ("rating-and-spread-migration",
     "~30 obligors TRACE actually carries observations for",
     "Query FINRA TRACE for each anchor's CUSIPs. Thin-traded names yield a "
     "sparse series and a weak demo — this is the single most likely cast gap."),
    ("large-exposure-rwa-concentration",
     "a reporting bank entity with real Call Report / FR Y-9C data",
     "The cast is obligors only; the bank whose capital base is the denominator "
     "is ABSENT from the estate. Pick an RSSD from FFIEC NIC and load its "
     "Call Report Schedules RC-C / RC-R."),
    ("collateral-and-setoff-coverage",
     "UCC-1 lien filings for the anchors' debtor names",
     "Per-state search; several free, some charge. Confirm coverage BEFORE "
     "committing. Fall back to EX-10 collateral schedules where thin."),
    ("ib-opportunity-synthesis",
     ">= 5 real SC 13D filings against entities in the prospect set",
     "EDGAR full-text search on SC 13D by CIK. Prospects extend beyond the "
     "anchors, so the search set is wider than the cast."),
    ("credit-surveillance-early-warning",
     ">= 3 anchors with real WARN notices matched by name",
     "State WARN registries, matched on legal name — deliberately lossy."),
    ("abs-securitization-surveillance",
     "2–3 real ABS deals across 12 periods",
     "A SEPARATE issuer population — ABS trusts are not corporate obligors, so "
     "this does not constrain the cast. ~480k–720k loan rows."),
    ("aml-typology-match",
     "~200 synthetic parties matching NO real entity",
     "Deliberately DISJOINT from the cast. Hard rule — enforce at generation "
     "time, never at review."),
    ("syndicated-lending-co-lender",
     "a second CCF instance representing a co-lender",
     "Largest infrastructure item in the catalog. Second Fluree + Postgres."),
]


def audit_fetch_gated() -> None:
    for spec, condition, probe in FETCH_GATED:
        record(spec, condition, NEEDS_FETCH, "", probe)


# --------------------------------------------------------------------------
def main() -> int:
    print("CAST AUDIT — the 50 anchors against all 22 spec §F envelopes")
    print("  conditions.py asks 'is it loaded?'. This asks 'can this cast "
          "ever carry it?'\n")

    audit_cast_shape()
    audit_filing_carriers()
    audit_document_corpus()
    audit_peer_cohorts()
    audit_graph_shape()
    audit_fetch_gated()

    by_verdict: dict[str, list[Finding]] = {
        SATISFIED: [], SHORTFALL: [], NEEDS_FETCH: [],
    }
    for f in findings:
        by_verdict[f.verdict].append(f)

    for verdict in (SHORTFALL, SATISFIED, NEEDS_FETCH):
        rows = by_verdict[verdict]
        marker = {SATISFIED: "PASS", SHORTFALL: "FAIL", NEEDS_FETCH: "----"}[verdict]
        print(f"\n  ===== {verdict} ({len(rows)}) =====\n")
        for f in rows:
            print(f"  [{marker}] {f.spec}")
            print(f"         {f.condition}"
                  + (f"  —  {f.detail}" if f.detail else ""))
            if f.remedy:
                for i, line in enumerate(_wrap(f.remedy, 68)):
                    print(f"         {'>' if i == 0 else ' '} {line}")
            print()

    n_short = len(by_verdict[SHORTFALL])
    print(f"\n  {len(by_verdict[SATISFIED])} satisfied · {n_short} shortfall · "
          f"{len(by_verdict[NEEDS_FETCH])} need a fetch\n")
    if n_short:
        print("  Shortfalls are cast-level: resolve by extending the cast, "
              "re-selecting,\n  or engineering the condition and LABELLING it. "
              "Each is cheaper now than\n  after another wave loads on top.\n")
    return 0


def _wrap(text: str, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


if __name__ == "__main__":
    sys.exit(main())
