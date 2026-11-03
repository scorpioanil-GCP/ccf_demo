#!/usr/bin/env python3
"""Wave 13b Task 5 — load the resolution layer into Postgres and Fluree.

Reads `sources/screening/wave13b_resolution.json`.

    Postgres  resolution_policy          3 thresholds  (P — read by the scorer)
              name_variant_rule          5 rules       (P)
              person_name_variant     +426 rows        (E)
              person_crosswalk         +500 rows       (E)
              sanctions_screening_result 19 rows       (E)
    Fluree    PersonName nodes         426             (R)
              hasPersonName / isIdentifiedBy edges
              IdentityResolution nodes  74 with confidence
              owl:differentFrom         74
              screenedAgainst           19

## The bands do not come from this file

`ccf.resolve.Thresholds.load()` reads `resolution_policy`. Nothing here holds a
threshold constant. `docs/wave13b-design.md` §5 is explicit: a gate whose
bounds sit beside its assertion agrees with itself.

## Two CHECK constraints had to widen, both deliberately

`person_crosswalk.match_band` was pinned by Wave 10 to
`('exact','strong','weak','false_positive')`. This wave's resolver has a fifth
band — `review`, the one §F6 needs exercised — and it is the whole point that
a candidate can land between auto-clear and auto-reject. Widened here as an
idempotent migration and in Wave 10's own DDL, so a fresh database and an
existing one end in the same place.

## `owl:sameAs` is not asserted

Deliberately. Every cross-registry rendering belongs to a person node that
already exists, so the identity edge is `cmns-id:isIdentifiedBy` to a
`PersonName` — not a `sameAs` between two person nodes. See the binding table.

    uv run loaders/load_resolution_wave13b.py --dry-run
    uv run loaders/load_resolution_wave13b.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from ccf import fluree
from ccf.config import (
    EX,
    EX_EXTENSION_SCHEMA_NOTE,
    FLUREE_LEDGER_V2,
    PG_SCHEMA_V2,
    REPO_ROOT,
    assert_v2_schema,
    pg_connect,
)
from ccf.resolve import Thresholds, combined_score

S = PG_SCHEMA_V2
SCREEN = REPO_ROOT / "sources" / "screening"
ARTIFACT = SCREEN / "wave13b_resolution.json"
BATCH = 500

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
OWL = "http://www.w3.org/2002/07/owl#"
OWL_DIFFERENT_FROM = f"{OWL}differentFrom"

FIBO = "https://spec.edmcouncil.org/fibo/ontology/"
C_PERSON = f"{FIBO}FND/AgentsAndPeople/People/Person"
C_PERSON_NAME = f"{FIBO}FND/AgentsAndPeople/People/PersonName"
C_NATURAL_PERSON = f"{FIBO}BE/LegalEntities/LegalPersons/LegallyCompetentNaturalPerson"
P_HAS_PERSON_NAME = f"{FIBO}FND/AgentsAndPeople/People/hasPersonName"
P_IS_IDENTIFIED_BY = "https://www.omg.org/spec/Commons/Identifiers/isIdentifiedBy"

C_IDENTITY_RESOLUTION = f"{EX}IdentityResolution"
P_VARIANT_ID = f"{EX}variantId"
P_RESOLVED_SUBJECT = f"{EX}resolvedSubject"
P_RESOLUTION_CONFIDENCE = f"{EX}resolutionConfidence"
P_SCREENED_AGAINST = f"{EX}screenedAgainst"
P_IS_FIBO_TERM = f"{EX}isFiboTerm"
P_SCHEMA_NOTE = f"{EX}schemaNote"

DDL = f"""
-- Wave 10 pinned match_band to four values. This wave's resolver has a fifth,
-- `review` — the band between auto-clear and auto-reject that §F6 requires be
-- exercised. Idempotent: DROP ... IF EXISTS then ADD re-validates every row.
ALTER TABLE "{S}".person_crosswalk
    DROP CONSTRAINT IF EXISTS person_crosswalk_match_band_check;
ALTER TABLE "{S}".person_crosswalk ADD CONSTRAINT person_crosswalk_match_band_check
    CHECK (match_band IN ('exact', 'strong', 'review', 'weak', 'false_positive'));

-- A surrogate key so Fluree can REACH a variant row without COPYING the name
-- into a second store. Same pattern as `ex:documentId` reaching a MongoDB
-- passage: enough to resolve the row, not a duplicate of it. Wave 10's 571
-- rows keep NULL — they have no Fluree counterpart to join from.
ALTER TABLE "{S}".person_name_variant
    ADD COLUMN IF NOT EXISTS variant_id text;
CREATE UNIQUE INDEX IF NOT EXISTS person_name_variant_variant_id_idx
    ON "{S}".person_name_variant (variant_id) WHERE variant_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS "{S}".name_variant_rule (
    rule_name   text PRIMARY KEY,
    description text NOT NULL,
    provenance  text NOT NULL
);

CREATE TABLE IF NOT EXISTS "{S}".sanctions_screening_result (
    person_key    text    NOT NULL
                  REFERENCES "{S}".person(person_key) ON DELETE CASCADE,
    entry_id      text    NOT NULL
                  REFERENCES "{S}".sanctions_entry(entry_id) ON DELETE CASCADE,
    listed_name   text    NOT NULL,
    name_kind     text    NOT NULL,
    alias_category text   NOT NULL,
    score         numeric NOT NULL,
    sequence_score numeric NOT NULL,
    token_score   numeric NOT NULL,
    carried_by    text    NOT NULL,
    -- Derived from the LOADED thresholds at generation time. Kept so a
    -- consumer can see the verdict, and recomputable from `score` plus
    -- `resolution_policy` so it can be checked rather than trusted.
    disposition   text    NOT NULL,
    in_review_band boolean NOT NULL,
    provenance    text    NOT NULL,
    PRIMARY KEY (person_key, entry_id)
);

CREATE INDEX IF NOT EXISTS sanctions_screening_review_idx
    ON "{S}".sanctions_screening_result (in_review_band) WHERE in_review_band;
"""


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def triple(s: str, p: str, o: str, *, literal: bool = False) -> str:
    obj = f'"{esc(o)}"' if literal else f"<{o}>"
    return f"<{s}> <{p}> {obj} ."


def uri(local: str) -> str:
    return f"{EX}{local}"


def variant_id(i: int) -> str:
    """The surrogate key shared by the Postgres row and the Fluree node."""
    return f"PNV-{i:04d}"


def build_triples(doc: dict, persons: list[dict]) -> list[str]:
    triples: list[str] = []

    # --- person nodes -----------------------------------------------------
    for p in persons:
        node = uri(p["person_id"])
        triples += [
            triple(node, RDF_TYPE, C_PERSON),
            # Explicit second typing: no reasoner, so a query for a legally
            # competent natural person will not find a node typed only Person.
            triple(node, RDF_TYPE, C_NATURAL_PERSON),
            triple(node, RDFS_LABEL, p["display_name"], literal=True),
        ]

    # --- one PersonName node per registry rendering -----------------------
    #
    # The node carries its TYPE and a JOIN KEY and nothing else. The name
    # string, its source registry and its rendering all live in
    # `person_name_variant`, and copying any of them here would put the same
    # attribute in two stores — which `validators/partition.py` catches, and
    # which Wave 12 lost a day to.
    for i, v in enumerate(doc["variants"], start=1):
        name_node = uri(variant_id(i))
        person_node = uri(v["person_key"])
        triples += [
            triple(name_node, RDF_TYPE, C_PERSON_NAME),
            triple(name_node, P_VARIANT_ID, variant_id(i), literal=True),
            triple(person_node, P_HAS_PERSON_NAME, name_node),
            triple(person_node, P_IS_IDENTIFIED_BY, name_node),
        ]

    # --- false positives: a reified decision, plus owl:differentFrom ------
    for i, fp in enumerate(doc["false_positives"], start=1):
        res = uri(f"RES-{i:04d}")
        a, b = uri(fp["person_key_a"]), uri(fp["person_key_b"])
        triples += [
            triple(res, RDF_TYPE, C_IDENTITY_RESOLUTION),
            # Labelled by KEY, not by name: the names are Postgres attributes
            # and this node is in Fluree.
            triple(res, RDFS_LABEL,
                   f"{fp['person_key_a']} / {fp['person_key_b']} — "
                   f"distinct persons above the merge threshold",
                   literal=True),
            triple(res, P_RESOLVED_SUBJECT, a),
            triple(res, P_RESOLVED_SUBJECT, b),
            triple(res, P_RESOLUTION_CONFIDENCE, str(fp["score"]), literal=True),
            # The negative finding, stated as a fact. Without it a downstream
            # resolver can re-merge the pair by scoring the names again.
            triple(a, OWL_DIFFERENT_FROM, b),
        ]

    # --- sanctions screening ---------------------------------------------
    # Screening: the EDGE is the graph's business; the score, the disposition
    # and the listed name are all `sanctions_screening_result` columns and stay
    # there. The entry node's local name IS the entry_id, so the edge resolves
    # to Postgres with no attribute copied.
    for h in doc["sanctions_hits"]:
        triples.append(triple(uri(h["person_key"]), P_SCREENED_AGAINST,
                              uri(f"OFAC-{h['entry_id']}")))

    for term in (C_IDENTITY_RESOLUTION, P_VARIANT_ID, P_RESOLVED_SUBJECT,
                 P_RESOLUTION_CONFIDENCE, P_SCREENED_AGAINST):
        triples += [
            triple(term, P_IS_FIBO_TERM, "false", literal=True),
            triple(term, P_SCHEMA_NOTE, EX_EXTENSION_SCHEMA_NOTE, literal=True),
        ]
    return triples


def main() -> int:
    ap = argparse.ArgumentParser(description="Load the resolution layer")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    doc = json.loads(ARTIFACT.read_text())
    persons = json.loads((SCREEN / "wave13b_psc_persons.json").read_text())["persons"]
    by_key = {p["person_id"]: p for p in persons}

    variant_rows = [(v["person_key"], v["variant_name"], v["source"],
                     v["rendering"], v["provenance"], variant_id(i))
                    for i, v in enumerate(doc["variants"], start=1)]

    rule_rows = [(r["rule_name"], r["description"], r["provenance"])
                 for r in doc["variant_rules"]]

    # Crosswalk: each registry rendering resolves to its person, scored by the
    # SAME function the gate will re-run. The score is recomputed here rather
    # than copied, so a generator/loader disagreement shows up as a number.
    crosswalk_rows = []
    for i, v in enumerate(doc["variants"], start=1):
        person = by_key[v["person_key"]]
        score = combined_score(v["variant_name"], person["display_name"])
        crosswalk_rows.append((
            v["source"], f"{v['source']}-{i:04d}", v["variant_name"],
            v["person_key"], round(score, 4),
            "exact" if score >= 0.999 else ("strong" if score >= 0.90 else "review"),
            True, v["provenance"],
            f"cross-registry rendering ({v['rendering']})",
        ))
    for fp in doc["false_positives"]:
        crosswalk_rows.append((
            "psc_register", f"fp-{fp['person_key_b']}", fp["name_b"],
            fp["person_key_a"], fp["score"], "false_positive", False,
            fp["provenance"],
            f"fuzzy-matches at {fp['score']} but conflicts on "
            f"{', '.join(fp['conflicting_on'])}",
        ))

    screening_rows = [
        (h["person_key"], h["entry_id"], h["listed_name"], h["name_kind"],
         h["alias_category"], h["score"], h["sequence"], h["token"],
         h["carried_by"], h["disposition"], h["in_review_band"],
         h["provenance"])
        for h in doc["sanctions_hits"]
    ]

    triples = build_triples(doc, persons)

    print(f"Wave 13b Task 5 — resolution layer into {S} + Fluree\n")
    print(f"  thresholds in artifact  {doc['thresholds']}")
    print(f"\n  name_variant_rule       {len(rule_rows):>5}")
    print(f"  person_name_variant     {len(variant_rows):>5}   "
          f"sources: {dict(Counter(v[2] for v in variant_rows))}")
    print(f"  person_crosswalk        {len(crosswalk_rows):>5}   "
          f"bands: {dict(Counter(r[5] for r in crosswalk_rows))}")
    print(f"  sanctions_screening     {len(screening_rows):>5}   "
          f"review band: {sum(1 for r in screening_rows if r[10])}")
    print(f"  Fluree triples          {len(triples):>5}")

    if args.dry_run:
        print("\n  [dry-run] nothing written")
        return 0

    assert_v2_schema(S)

    with pg_connect() as conn, conn.cursor() as cur:
        cur.execute(DDL)

        # The thresholds the artifact was generated under must still be the
        # thresholds in the store. A policy edited between generation and load
        # would silently reband every row.
        live = Thresholds.load(cur)
        stated = doc["thresholds"]
        drift = {k: (stated[k], getattr(live, k))
                 for k in ("auto_clear", "review_floor", "merge_threshold")
                 if abs(float(stated[k]) - getattr(live, k)) > 1e-9}
        if drift:
            print(f"\n  FAIL: resolution_policy has changed since the artifact "
                  f"was generated: {drift}")
            print("  Re-run generators/generate_resolution_wave13b.py.")
            return 1

        cur.executemany(
            f'INSERT INTO "{S}".name_variant_rule '
            "(rule_name, description, provenance) VALUES (%s,%s,%s) "
            "ON CONFLICT (rule_name) DO UPDATE SET "
            "description=EXCLUDED.description, provenance=EXCLUDED.provenance",
            rule_rows,
        )
        cur.executemany(
            f'INSERT INTO "{S}".person_name_variant '
            "(person_key, variant_name, source, rendering, provenance, "
            " variant_id) VALUES (%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (person_key, variant_name, source) DO UPDATE SET "
            "rendering=EXCLUDED.rendering, provenance=EXCLUDED.provenance, "
            "variant_id=EXCLUDED.variant_id",
            variant_rows,
        )
        cur.executemany(
            f'INSERT INTO "{S}".person_crosswalk '
            "(source_system, source_id, source_name, person_key, match_score, "
            " match_band, is_true_match, provenance, note) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (source_system, source_id, person_key) DO UPDATE SET "
            "source_name=EXCLUDED.source_name, "
            "match_score=EXCLUDED.match_score, match_band=EXCLUDED.match_band, "
            "is_true_match=EXCLUDED.is_true_match, "
            "provenance=EXCLUDED.provenance, note=EXCLUDED.note",
            crosswalk_rows,
        )
        cur.executemany(
            f'INSERT INTO "{S}".sanctions_screening_result '
            "(person_key, entry_id, listed_name, name_kind, alias_category, "
            " score, sequence_score, token_score, carried_by, disposition, "
            " in_review_band, provenance) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (person_key, entry_id) DO UPDATE SET "
            "listed_name=EXCLUDED.listed_name, name_kind=EXCLUDED.name_kind, "
            "alias_category=EXCLUDED.alias_category, score=EXCLUDED.score, "
            "sequence_score=EXCLUDED.sequence_score, "
            "token_score=EXCLUDED.token_score, carried_by=EXCLUDED.carried_by, "
            "disposition=EXCLUDED.disposition, "
            "in_review_band=EXCLUDED.in_review_band, "
            "provenance=EXCLUDED.provenance",
            screening_rows,
        )
        conn.commit()

        cur.execute(f'SELECT count(*) FROM "{S}".person_name_variant v '
                    f'JOIN "{S}".person p USING (person_key) '
                    f"WHERE p.person_key_source = 'psc'")
        n_variants = cur.fetchone()[0]
        cur.execute(f"SELECT count(DISTINCT source) FROM \"{S}\".person_name_variant")
        n_sources = cur.fetchone()[0]
        cur.execute(f"SELECT count(*) FROM \"{S}\".person_crosswalk "
                    "WHERE match_band = 'false_positive'")
        n_fp = cur.fetchone()[0]
        cur.execute(f'SELECT count(*) FROM "{S}".sanctions_screening_result '
                    "WHERE in_review_band")
        n_review = cur.fetchone()[0]

    for i in range(0, len(triples), BATCH):
        fluree.update("INSERT DATA {\n" + "\n".join(triples[i:i + BATCH]) + "\n}")

    n_names = fluree.stable_scalar(
        f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?s a <{C_PERSON_NAME}> }}")
    n_diff = fluree.stable_scalar(
        f"SELECT (COUNT(?o) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?s <{OWL_DIFFERENT_FROM}> ?o }}")
    n_screened = fluree.stable_scalar(
        f"SELECT (COUNT(?o) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?s <{P_SCREENED_AGAINST}> ?o }}")
    n_persons = fluree.stable_scalar(
        f"SELECT (COUNT(DISTINCT ?s) AS ?n) FROM <{FLUREE_LEDGER_V2}> "
        f"WHERE {{ ?s a <{C_NATURAL_PERSON}> }}")

    print(f"\n  Postgres: psc variants {n_variants} across {n_sources} sources · "
          f"{n_fp} false positives · {n_review} in review band")
    print(f"  Fluree:   {n_persons} natural persons · {n_names} PersonName nodes · "
          f"{n_diff} differentFrom · {n_screened} screenedAgainst")
    print(f"  ledger now at t={fluree.ledger_t()} · "
          f"{fluree.count_triples():,} triples")

    failures = []
    if n_variants != len(variant_rows):
        failures.append(f"{n_variants} psc variants loaded, expected "
                        f"{len(variant_rows)}")
    if n_sources < 2:
        failures.append(f"variants span {n_sources} source(s); §F5 requires "
                        f"variants ACROSS sources")
    if n_fp < 1:
        failures.append("no false-positive pair in person_crosswalk")
    if n_review < 1:
        failures.append("no sanctions match in the review band (§F6)")
    if n_names != len(doc["variants"]):
        failures.append(f"{n_names} PersonName nodes, expected "
                        f"{len(doc['variants'])}")
    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        return 1
    print("  both stores match the artifact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
