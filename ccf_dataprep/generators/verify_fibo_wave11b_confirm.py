#!/usr/bin/env python3
"""Wave 11b — confirm the surveillance vocabulary against the estate, offline.

Wave 8 shipped `verify_fibo_wave8_confirm.py`: a machine-checkable pass over
the exact terms proposed for the binding table, reporting `ok` / `MISSING` per
term so an absence claim lived in CI-style output rather than only in prose.
Wave 11b Task 1 did the same verification work — 295 FIBO modules, 22 OMG
Commons modules, every `rdf:about` / `rdf:ID` / `rdfs:label` — but recorded it
only as prose in `docs/ccf_dataprep_v2.md` and a commit message. Nothing could
re-check it. This closes that gap.

## What it can and cannot re-verify

Wave 8's script confirms **presence** in FIBO, which needs the live endpoint.
Wave 11b's central claim is the opposite — **absence** from FIBO and Commons —
and absence cannot be confirmed offline at all: a fetch that fails looks
exactly like a term that is not there, which is the `Tranche` trap from Wave 8
in a new costume. So this script is honest about the split:

    checked offline   every ex: term the ESTATE asserts is bound in the doc;
                      every bound term is materialised at the EXACT IRI the
                      doc records; the reused terms carry the counts claimed;
                      published_claims.json covers every bound term
    needs --live      the absence-from-FIBO / absence-from-Commons claims

Without `--live` the absence rows report `not re-verified offline` and are
counted separately. They are never silently passed, and they never fail — a
network-shaped failure reported as a vocabulary defect is worse than a gap.

## Why the offline half is worth having on its own

It catches the drift that actually happens between waves: a loader minting an
`ex:` term nobody added to the binding table, or a doc row whose IRI no longer
matches what the ledger holds. Both validate cleanly inside this repo and
cannot be consumed downstream — CLAUDE.md's named expensive failure.

    uv run generators/verify_fibo_wave11b_confirm.py
    uv run generators/verify_fibo_wave11b_confirm.py --live
    uv run generators/verify_fibo_wave11b_confirm.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys

from ccf import fluree
from ccf.config import EX, FLUREE_LEDGER_V2, REPO_ROOT

DOC = REPO_ROOT / "docs" / "ccf_dataprep_v2.md"
CLAIMS = REPO_ROOT / "sources" / "screening" / "published_claims.json"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
FIBO = "https://spec.edmcouncil.org/fibo/ontology/"

#: The terms Wave 11b minted, with the kind that decides how the ledger is
#: asked about them. IRIs are NOT written here — they are read out of the
#: binding table, so a doc row and a constant cannot silently disagree.
#:
#: `item` was ADDED 2026-08-21 by the whole-branch review. This dict said
#: **five** terms until then, and the estate→doc sweep below did not catch the
#: sixth because that sweep was substring-based — see `doc_binds`.
WAVE11B_TERMS = {
    "WarningSignal": "class",
    "SignalSource": "class",
    "PriorObservation": "class",
    "signalAbout": "property",
    "triggeredBy": "property",
    "item": "property",
}

#: Terms Wave 11b REUSES rather than mints, with the minimum this wave's load
#: should have produced. The failure these guard against is a future reader
#: minting `ex:supersedes` or `ex:CovenantBreach` beside a term that already
#: exists and already carries data.
REUSED = {
    f"{EX}supersededBy": ("ex:supersededBy", "property", 750),
    f"{EX}IssuanceEvent": ("ex:IssuanceEvent", "class", 1),
    f"{FIBO}FND/Agreements/Contracts/BreachOfCovenant":
        ("fibo-fnd-agr-ctr:BreachOfCovenant", "class", 1),
}

#: `ex:` terms the ESTATE asserts that the binding contract does not carry —
#: found by this script on 2026-08-21 and pinned here so the finding cannot
#: quietly grow. **Every one predates Wave 11b** (Waves 4-7: amendments,
#: booking-lag provenance, the information barrier, passage offsets, the Wave 5
#: covenant attributes). None is a shadowed FIBO term — the six classes are
#: allowlisted with written rationale in `validators/partition.py`'s
#: `PERMITTED_EX_TYPES`, and the attributes are the same kind of thing as the
#: `ex:` predicate table in `docs/ccf_dataprep_v2.md`. What is missing is the
#: binding-table row, which CLAUDE.md's definition of done item 5 requires and
#: which the vault mirror consumes.
#:
#: CORRECTED 2026-08-21 (whole-branch review): this set held **31** terms and
#: its comment said *"None is this wave's."* Both were wrong. `doc_binds` used
#: to be a bare substring test, so three terms whose local names are ordinary
#: English words never reached this list at all — `unit` and `direction`
#: (Wave 5 covenant attributes, 180 assertions each) are ADDED here, and
#: `item` (Wave 11b's, 535 assertions) was genuinely this wave's and is now
#: BOUND in `docs/ccf_dataprep_v2.md` rather than added here. 31 -> 33.
#:
#: CORRECTED AGAIN 2026-08-21 (scoped re-review, second pass): the gate itself
#: was still bypassable — a `mention`-only term (a backtick somewhere in the
#: doc, no binding-table row) counted as "bound" for gate purposes, same as a
#: real `iri` row. Only `iri` now satisfies the gate (see `main()`); `mention`
#: is treated the same as no evidence at all. That makes the 12 pre-existing
#: mention-only terms newly gate-failing unless frozen here alongside the 33,
#: so they are ADDED: `assertedAt`, `covenantType`, `evidence`, `grade`,
#: `observedValue`, `provenance`, `reason`, `sourceAccession`, `threshold`,
#: `trigger`, `validFrom`, `validTo`. 33 -> 45. Every one is already asserted
#: in the estate today (verified via `estate_ex_terms()` before adding) — the
#: freeze only holds if nothing is added here that isn't real debt already.
#:
#: Reported as DEBT, not FAIL, and deliberately: a Wave 11b gate that is
#: permanently red over a Wave 4 omission is a gate people learn to ignore.
#: But the list is FROZEN — a NEW unbound term, from this wave or any later
#: one, is not in this set and therefore fails. See docs/known-issues.md §10.7.
KNOWN_UNBOUND: set[str] = set()
#:
#: PAID IN FULL 2026-08-21 (Wave 11c). All 45 terms this set used to hold now
#: carry a real full-IRI row in `docs/ccf_dataprep_v2.md` § *Wave 11c: the
#: binding debt paid*. The set is deliberately left in place and EMPTY rather
#: than deleted, because the shape of the rule is the thing worth keeping:
#:
#:     while this set is non-empty:  fail if a term is NEW and unbound
#:     now that it is empty:         fail if a term is unbound
#:
#: The second rule has no hand-maintained forgiveness list, so there is
#: nothing left to fall out of date. Re-adding an entry here is not a routine
#: act — it re-introduces the maintenance burden this wave removed, and it
#: should carry a reason and a date, as every entry above used to.
#:
#: The history it replaced is preserved in `docs/known-issues.md` §10.7: the
#: set was 31, then 33 once `doc_binds` stopped being a bare substring test,
#: then 45 once a code-span `mention` stopped satisfying the gate. Each
#: correction was found by attacking the check, never by reading it.

#: Absence claims from Task 1. Re-checkable only with --live.
ABSENCE_CLAIMS = [
    ("FIBO", "signal", "zero rdf:about / rdf:ID / rdfs:label hits, all 295 modules"),
    ("FIBO", "warning", "zero hits, all 295 modules"),
    ("OMG Commons", "signal", "zero hits, all 22 modules"),
    ("OMG Commons", "warning", "zero hits, all 22 modules"),
]


def doc_bound_iris() -> dict[str, str]:
    """local name -> full IRI, read out of the binding table's own rows.

    The Wave 11b rows have the shape

        | `WarningSignal` | class | `http://example.org/fibo/WarningSignal` | ... |

    so the IRI is taken from the document rather than restated in this file.
    A doc row that is edited to a different IRI therefore FAILS here instead
    of being silently overridden by a constant that agrees with the loader.
    """
    text = DOC.read_text()
    found: dict[str, str] = {}
    row = re.compile(
        r"^\|\s*`(\w+)`\s*\|\s*(class|property)\s*\|\s*`(http://example\.org/fibo/[\w]+)`",
        re.M)
    for local, _kind, iri in row.findall(text):
        found[local] = iri
    return found


def doc_binds(local: str, text: str) -> bool:
    """Does the binding document carry ANY evidence for this local name?

    **NOT the gate test.** This is the original (first-fix) definition —
    "bound" means either a backticked token or a full IRI — kept for its
    descriptive value (it is what makes a term worth naming in prose at
    all). `main()`'s pass/fail gate does **not** call this function; see the
    CORRECTED note there. `doc_binds` answers "does the document know about
    this term at all", not "is it bound-enough-to-satisfy-the-gate".

    **This function is the fix for the defect that got `ex:item` into the
    estate unbound.** It used to be `local_name in DOC.read_text()` — a bare
    substring test against 1,700 lines of prose. Any `ex:` term whose local
    name is an ordinary English word passed: the document says "item",
    "unit" and "direction" in ordinary sentences all over, so three real
    unbound terms reported as bound and the guard was green while the
    contract was incomplete.

    A term counts as having evidence only on something a reader could act on:

        a backticked token   `item`  or  `ex:item`
        the full IRI         http://example.org/fibo/item

    Both are things the document does *on purpose*; neither can be produced
    by accident by prose. Nothing else counts — in particular a bare word,
    a heading, or the term appearing inside a longer identifier.
    """
    return doc_binding_strength(local, text) is not None


def doc_binding_strength(local: str, text: str) -> str | None:
    """`"iri"`, `"mention"`, or `None` — how strong the doc's evidence is.

    Reported alongside the gate because the gate the review specified
    (backticked token OR full IRI) still cannot tell a **binding-table row**
    from a **deliberate code-span mention**. That difference is real: the
    Wave 11a paragraph in the register names `ex:grade`, `ex:validFrom` and
    five siblings precisely in order to record that they get NO row, and the
    Wave 5 precedent it cites names four more the same way. Under the gate
    those eleven read as bound; only the terms carrying a full IRI have
    something the vault mirror can actually consume.

    So the split is printed rather than averaged away. `mention` is not a
    failure — it is a smaller, named residual hole, measured every run.
    See `docs/known-issues.md` §10.7.

    **The IRI test is word-boundary anchored.** CORRECTED 2026-08-21 by the
    scoped re-review of this wave's own fix: it used to be
    `f"{EX}{local}" in text`, a bare substring test, so any term whose local
    name is a *prefix* of an already-bound term's IRI read as bound-by-IRI on
    zero evidence — `signal` inside `.../signalAbout`, `Warning` inside
    `.../WarningSignal`, `trigger` inside `.../triggeredBy`. None of those
    three carries a binding-table row. This was a **gate bypass**, not merely
    a reporting defect: it let an unbound term slip past `main()`'s exit code
    silently. `re.search` with a negative lookahead for a following word
    character or hyphen closes it — `.../item` still matches `item` (nothing
    follows it in that IRI), but `.../signalAbout` no longer matches `signal`.
    """
    if re.search(re.escape(f"{EX}{local}") + r"(?![\w-])", text):
        return "iri"
    if re.search(r"`(?:ex:)?" + re.escape(local) + r"`", text):
        return "mention"
    return None


def count(pattern: str) -> int:
    q = f"SELECT (COUNT(*) AS ?n) FROM <{FLUREE_LEDGER_V2}> WHERE {{ {pattern} }}"
    rows = fluree.query(q).get("results", {}).get("bindings", [])
    return int(rows[0]["n"]["value"]) if rows else 0


def materialised(iri: str, kind: str) -> int:
    if kind == "class":
        return count(f"?s <{RDF_TYPE}> <{iri}>")
    return count(f"?s <{iri}> ?o")


def estate_ex_terms() -> tuple[set[str], set[str]]:
    """(ex: classes asserted, ex: predicates asserted) — what the ledger
    ACTUALLY holds, which is the side that drifts."""
    classes = {b["t"]["value"] for b in fluree.query(
        f"SELECT DISTINCT ?t FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?s a ?t . "
        f"FILTER(STRSTARTS(STR(?t), '{EX}')) }}"
    ).get("results", {}).get("bindings", [])}
    preds = {b["p"]["value"] for b in fluree.query(
        f"SELECT DISTINCT ?p FROM <{FLUREE_LEDGER_V2}> WHERE {{ ?s ?p ?o . "
        f"FILTER(STRSTARTS(STR(?p), '{EX}')) }}"
    ).get("results", {}).get("bindings", [])}
    return classes, preds


def live_absence(corpus: str, token: str) -> tuple[bool, str]:
    """Re-run one absence probe against the live source. --live only."""
    import requests
    if corpus == "FIBO":
        url = f"{FIBO}"
    else:
        url = "https://www.omg.org/spec/Commons/AboutCommons/"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        return False, f"unreachable: {type(exc).__name__}"
    hit = token.lower() in r.text.lower()
    return not hit, ("no hit in the fetched index"
                     if not hit else f"'{token}' APPEARS — re-open the claim")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true",
                    help="also re-probe the absence-from-FIBO/Commons claims "
                         "against the published sources. Off by default: an "
                         "unreachable endpoint must never be reported as a "
                         "vocabulary defect.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows: list[tuple[str, str, str]] = []   # (status, term, detail)
    bound = doc_bound_iris()

    # 1 — every Wave 11b term is bound in the doc, at the IRI the loader uses.
    for local, kind in WAVE11B_TERMS.items():
        iri = bound.get(local)
        if iri is None:
            rows.append(("MISSING", f"ex:{local}",
                         "no binding-table row in docs/ccf_dataprep_v2.md"))
            continue
        if iri != f"{EX}{local}":
            rows.append(("MISSING", f"ex:{local}",
                         f"doc binds {iri}, loaders write {EX}{local}"))
            continue
        n = materialised(iri, kind)
        rows.append(("ok" if n else "MISSING", f"ex:{local}",
                     f"bound and materialised — {n} {kind} assertion(s)"
                     if n else "bound but NOT materialised in fibo-v2"))

    # 2 — reused terms still carry their data. Guards duplicate minting.
    for iri, (label, kind, floor) in REUSED.items():
        n = materialised(iri, kind)
        rows.append(("ok" if n >= floor else "MISSING", label,
                     f"reused, not re-minted — {n} assertion(s) (floor {floor})"))

    # 3 — the drift direction that matters: the ESTATE asserting an ex: term
    #     the document never bound. Wave 8's script could not catch this at
    #     all, because it read only the proposal list.
    #
    # CORRECTED 2026-08-21 (scoped re-review, second pass on this same gate).
    # This used to accept EITHER `iri` OR `mention` as "bound enough" via
    # `doc_binds()`. That was itself a gate bypass: a `mention` is a backtick
    # occurring ANYWHERE in a 1,700-line document, coincidental hits included
    # (`signal` matched off unrelated absence-search prose, not a binding
    # row) — and the published debt arithmetic already counted mention-only
    # terms as debt (45 = 33 + 12), while the gate counted them as bound. One
    # of the two was wrong; a backtick in prose is not a binding row, so the
    # gate is now the one that changed. Only `strength == "iri"` counts as
    # bound for gate purposes; `mention` is treated the same as no evidence
    # at all and must be frozen in KNOWN_UNBOUND like any other pre-existing
    # debt, or it now fails as a NEW unbound term.
    classes, preds = estate_ex_terms()
    asserted = classes | preds
    in_doc = DOC.read_text()
    locals_ = sorted(u.rsplit("/", 1)[-1] for u in asserted)
    strength = {l: doc_binding_strength(l, in_doc) for l in locals_}
    by_iri = [l for l in locals_ if strength[l] == "iri"]
    by_mention = [l for l in locals_ if strength[l] == "mention"]
    by_none = [l for l in locals_ if strength[l] is None]

    unbound = sorted(by_mention) + sorted(by_none)   # gate: only iri passes
    new_unbound = sorted(set(unbound) - KNOWN_UNBOUND)

    rows.append(("ok" if not new_unbound else "MISSING", "estate -> doc coverage",
                 f"{len(asserted)} ex: terms asserted; {len(by_iri)} bound by "
                 f"full IRI (the only evidence the gate accepts); "
                 f"{len(by_mention)} by mention only + {len(by_none)} with no "
                 f"evidence = {len(unbound)} not gate-bound; no NEW unbound term"
                 if not new_unbound
                 else f"UNBOUND and not pre-existing: {new_unbound[:5]}"))
    if by_mention:
        rows.append(("debt", "bound by mention, not by row",
                     f"{len(by_mention)} ex: terms are named in a code span but "
                     f"carry NO full-IRI binding row: {by_mention} — gated as "
                     "debt (frozen in KNOWN_UNBOUND), not treated as bound; "
                     "see §10.7"))
    if by_none:
        rows.append(("debt", "pre-existing unbound terms",
                     f"{len(by_none)} ex: terms from Waves 4-7 assert data but "
                     "have no binding-table row and no mention — see "
                     "known-issues.md §10.7"))

    # 4 — published_claims.json carries a row for every Wave 11b term, so
    #     binding_drift.py can see them. A term bound in the doc but absent
    #     here is invisible to the punch-list generator.
    claims = {c["term"] for c in json.loads(CLAIMS.read_text())["claims"]}
    absent = sorted(set(WAVE11B_TERMS) - claims)
    rows.append(("ok" if not absent else "MISSING", "published_claims.json",
                 f"all {len(WAVE11B_TERMS)} Wave 11b terms carry a claim row"
                 if not absent else f"no claim row for {absent}"))

    # 5 — the absence claims. Reported, never silently passed.
    deferred = 0
    for corpus, token, recorded in ABSENCE_CLAIMS:
        if not args.live:
            deferred += 1
            rows.append(("deferred", f"{corpus} absence: '{token}'",
                         f"{recorded} — not re-verified offline (--live)"))
            continue
        ok, detail = live_absence(corpus, token)
        rows.append(("ok" if ok else "MISSING",
                     f"{corpus} absence: '{token}'", detail))

    confirmed = sum(1 for s, _, _ in rows if s == "ok")
    missing = [r for r in rows if r[0] == "MISSING"]
    n_debt = sum(1 for s, _, _ in rows if s == "debt")

    if args.json:
        print(json.dumps({"confirmed": confirmed, "missing": len(missing),
                          "deferred": deferred, "debt": n_debt,
                          "known_unbound": sorted(KNOWN_UNBOUND),
                          "rows": [{"status": s, "term": t, "detail": d}
                                   for s, t, d in rows]}, indent=2))
    else:
        print("WAVE 11b VOCABULARY CONFIRMATION — doc <-> estate, offline\n")
        for status, term, detail in rows:
            mark = {"ok": "ok  ", "MISSING": "FAIL", "deferred": "-- ",
                    "debt": "DEBT"}[status]
            print(f"  [{mark}] {term:<34} {detail}")
        print(f"\n  {confirmed} confirmed · {len(missing)} missing "
              f"· {deferred} deferred to --live · {n_debt} pre-existing debt")
        if n_debt:
            print("\n  DEBT is reported, not failed: every one predates this "
                  "wave and the")
            print("  list is frozen, so a NEW unbound term fails instead of "
                  "joining the pile.")
        if deferred:
            print("\n  Deferred rows are absence claims. Absence cannot be "
                  "confirmed offline —")
            print("  a failed fetch and a missing term are indistinguishable "
                  "(Wave 8's Tranche trap).")
        if missing:
            print("\n  A MISSING row is a term the estate and the binding "
                  "contract disagree about.")
            print("  Fix the binding table or the loader — never this script.")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
