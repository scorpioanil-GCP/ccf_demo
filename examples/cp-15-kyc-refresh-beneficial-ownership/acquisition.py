"""The estate half of `compliance.beneficial-ownership` — three stores, one order.

[ADAPT] the readers and the vocabulary here to your own product. This module
holds the deployment's own estate knowledge and nothing of the SDK's: it takes
settings by name, returns dated claims, and never touches a Control Plane, a
product, a door or the review queue.

THE ORDER IS THE POINT (`CP-SPEC-015` §D.3). The residency entitlement is read
FIRST, from the estate's own `principal.sees_eu_person_data` column, because a
person record outside the principal's entitlement must never be materialized —
not filtered afterwards, never minted. Then the applicable threshold for this
intent and jurisdiction, then the chain, then the resolution and screening
evidence, then the documents.

WHAT THE ENVELOPE'S INPUTS ARE, AND WHERE THEY STOP. The principal register
and the jurisdiction grants are consumed at this seam and are NOT emitted as
claims. The applicable threshold IS emitted, on the entity claim, because the
asking principal is entitled to know what bound its own answer.

THE REVIEW QUEUE IS NOT HERE, AND THAT IS THE RULING. Enqueue happens after a
complete, governed, assessed, immutable product exists (`CP-SPEC-015` §F.4.1).
Nothing in this module knows the queue exists.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).parent
VOCABULARY = HERE / "artifacts" / "source-vocabulary.yaml"


class NoJurisdictionGrant(RuntimeError):
    """This principal holds no jurisdiction grant, so nothing is admissible."""


class UnpricedIntent(ValueError):
    """The caller named an intent this estate prices no threshold for."""


class FloorBreached(ValueError):
    """The caller asked for a threshold or confidence below the estate's floor."""


@lru_cache(maxsize=1)
def vocabulary() -> Mapping[str, Any]:
    """Every source name this deployment reads, from its declared artifact."""
    return yaml.safe_load(VOCABULARY.read_text(encoding="utf-8"))["declaration"]


# =========================================================================
# THE ENVELOPE — what the asking principal may receive, computed first
# =========================================================================


@dataclass(frozen=True)
class Entitlement:
    """What the verified principal may see. Read from the ESTATE's own columns.

    `sees_eu_person_data` is `ccf_v2.principal`'s column, not this
    deployment's declaration — the one rung on the ladder whose estate already
    distinguishes principals on exactly the axis the product needs
    (`CP-SPEC-015` §A).
    """

    principal_id: str
    perspective: str
    sees_eu_person_data: bool
    jurisdictions: tuple[str, ...]

    def admits(self, *, is_eu_resident: bool) -> bool:
        return self.sees_eu_person_data or not is_eu_resident


@dataclass(frozen=True)
class Floors:
    """The estate's declared confidence policy, at its own version."""

    policy_version: str
    review_floor: Decimal
    merge_threshold: Decimal
    auto_clear: Decimal


@dataclass(frozen=True)
class Record:
    """One admissible claim: its class, its edge, its dated attributes."""

    entity_class: str
    edge_type: str
    entity_uri: str
    attributes: Mapping[str, str]
    dated: date | None


@dataclass(frozen=True)
class Estate:
    """Everything one question admitted, and the envelope that admitted it."""

    entity_id: str
    perspective: str
    entitlement: Entitlement | None
    floors: Floors | None
    entity: Mapping[str, str] | None
    applicable_threshold: Decimal | None
    min_confidence: Decimal | None
    records: tuple[Record, ...]
    ledger_t: str
    threshold_basis: str = ""
    withheld_persons: int = 0
    refresh_state: Mapping[str, Any] = field(default_factory=dict)

    @property
    def empty(self) -> bool:
        return self.entity is None


# =========================================================================
# THE READERS
# =========================================================================


class _Relational:
    """PostgreSQL, read-only, by DSN and schema name."""

    def __init__(self, *, dsn: str, schema: str) -> None:
        self._dsn, self._schema = dsn, schema

    def rows(self, sql: str, args: tuple[Any, ...] = ()) -> list[Mapping[str, Any]]:
        import psycopg  # noqa: PLC0415
        from psycopg.rows import dict_row  # noqa: PLC0415

        with psycopg.connect(self._dsn, autocommit=True) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(f"set search_path to {self._schema}")  # noqa: S608
                cursor.execute(sql, args)
                return [dict(row) for row in cursor.fetchall()]


class _Graph:
    """Fluree — read for the ledger watermark alone."""

    def __init__(self, *, url: str, ledger: str) -> None:
        self._url, self._ledger = url.rstrip("/"), ledger

    def watermark(self) -> str:
        query = f"SELECT ?s FROM <{self._ledger}> WHERE {{ ?s ?p ?o }} LIMIT 1"
        request = urllib.request.Request(
            f"{self._url}/v1/fluree/query", data=query.encode("utf-8"),
            headers={"Content-Type": "application/sparql-query"},
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
                return str(response.headers.get("x-fdb-t") or "unreported")
        except (urllib.error.URLError, TimeoutError):  # pragma: no cover - environment
            return "unreported"


class _Documents:
    """MongoDB — the KYC document corpus."""

    def __init__(self, *, uri: str, database: str) -> None:
        self._uri, self._database = uri, database

    def declarations(self, *, collection: str, chain_id: str, entity_id: str) -> list[Mapping[str, Any]]:
        from pymongo import MongoClient  # noqa: PLC0415

        client = MongoClient(self._uri, serverSelectionTimeoutMS=15000)
        try:
            found = client[self._database][collection].find(
                {"$or": [{"chain_id": chain_id}, {"entity_id": entity_id}]}
            )
            return [dict(document) for document in found]
        finally:
            client.close()


# =========================================================================
# ACQUIRE
# =========================================================================


def acquire(
    *,
    entity_id: str,
    asked_at: datetime,
    as_of: datetime,
    intent: str,
    perspective: str,
    principal_id: str,
    requested_threshold: Decimal | None,
    requested_confidence: Decimal | None,
    max_depth: int,
    relational_settings: Mapping[str, str],
    graph_settings: Mapping[str, str],
    document_settings: Mapping[str, str],
) -> Estate:
    """Everything one question admits, in the one order that is safe."""
    terms = vocabulary()
    tables = terms["relational"]["tables"]
    relational = _Relational(dsn=relational_settings["dsn"], schema=relational_settings["schema"])
    graph = _Graph(url=graph_settings["url"], ledger=graph_settings["ledger"])
    documents = _Documents(uri=document_settings["uri"], database=document_settings["db"])

    # 1. THE ENTITLEMENT, FIRST. A person the envelope excludes is never minted.
    entitlement = entitlement_for(relational, principal_id=principal_id, tables=tables)
    if entitlement is None or not entitlement.jurisdictions:
        raise NoJurisdictionGrant(
            f"principal `{principal_id}` holds no row in `{tables['principal_jurisdiction']}`;"
            f" nothing is admissible"
        )

    # 2. The estate's declared confidence policy, and the caller's floors.
    floors = floors_in_force(relational, table=tables["resolution_policy"])
    min_confidence = _floored(requested_confidence, floors.review_floor, "min_confidence")

    # 3. The anchor. No chain -> an EMPTY estate, never a raise (the A6 comparator).
    chains = relational.rows(
        f"select chain_id, entity_id, entity_kind, person_key, depth, effective_pct,"
        f" jurisdiction_path, crosses_jurisdictions, person_is_eu_resident"
        f" from {tables['chain']} where entity_id = %s", (entity_id,),
    )
    if not chains:
        return Estate(entity_id=entity_id, perspective=perspective, entitlement=entitlement,
                      floors=floors, entity=None, applicable_threshold=None,
                      min_confidence=min_confidence, records=(), ledger_t=graph.watermark())
    chain = chains[0]

    # 4. The threshold in force for THIS intent and the chain's jurisdiction.
    applicable, basis = threshold_for(
        relational, table=tables["threshold"], intent=intent,
        jurisdiction_path=list(chain["jurisdiction_path"] or ()),
    )
    applicable = _floored(requested_threshold, applicable, "threshold")

    records, withheld = _records(
        relational, documents, terms, chain=chain, entitlement=entitlement,
        applicable=applicable, min_confidence=min_confidence, max_depth=max_depth, as_of=as_of,
    )
    return Estate(
        entity_id=entity_id, perspective=perspective, entitlement=entitlement, floors=floors,
        entity={
            "entity_id": str(chain["entity_id"]), "entity_kind": str(chain["entity_kind"]),
            "chain_id": str(chain["chain_id"]), "depth": str(chain["depth"]),
            "jurisdiction_path": ",".join(str(j) for j in (chain["jurisdiction_path"] or ())),
            "crosses_jurisdictions": str(bool(chain["crosses_jurisdictions"])).lower(),
        },
        applicable_threshold=applicable, threshold_basis=basis,
        min_confidence=min_confidence,
        records=records, ledger_t=graph.watermark(), withheld_persons=withheld,
        # STATED ABSENCE. `kyc_refresh_state` is keyed by LEI and every chain
        # anchor in this estate is an offshore vehicle, so the two populations
        # do not join at all (measured 2026-09-21). The member is served with
        # its reason rather than omitted or silently empty.
        refresh_state={
            "available": False,
            "reason": ("the refresh register is keyed by LEI and this product's anchors are"
                       " offshore vehicles; the two populations do not join in this estate"),
        },
    )


def entitlement_for(
    relational: _Relational, *, principal_id: str, tables: Mapping[str, str]
) -> Entitlement | None:
    """The principal's entitlement, from the ESTATE's own columns."""
    rows = relational.rows(
        f"select principal_id, perspective, sees_eu_person_data from {tables['principal']}"
        f" where principal_id = %s", (principal_id,),
    )
    if not rows:
        return None
    grants = relational.rows(
        f"select jurisdiction_prefix from {tables['principal_jurisdiction']}"
        f" where principal_id = %s", (principal_id,),
    )
    return Entitlement(
        principal_id=str(rows[0]["principal_id"]),
        perspective=str(rows[0]["perspective"]),
        sees_eu_person_data=bool(rows[0]["sees_eu_person_data"]),
        jurisdictions=tuple(sorted(str(row["jurisdiction_prefix"]) for row in grants)),
    )


def registered_principals(*, relational_settings: Mapping[str, str]) -> Mapping[str, str]:
    """`principal_id` -> perspective, from the estate's own register."""
    relational = _Relational(dsn=relational_settings["dsn"], schema=relational_settings["schema"])
    table = vocabulary()["relational"]["tables"]["principal"]
    return {
        str(row["principal_id"]): str(row["perspective"])
        for row in relational.rows(f"select principal_id, perspective from {table}")
    }


def floors_in_force(relational: _Relational, *, table: str) -> Floors:
    """The estate's confidence policy at its own version."""
    rows = relational.rows(f"select threshold_name, threshold_value, policy_version from {table}")
    by_name = {str(row["threshold_name"]): Decimal(str(row["threshold_value"])) for row in rows}
    version = rows[0]["policy_version"] if rows else "unversioned"
    return Floors(
        policy_version=str(version),
        review_floor=by_name.get("review_floor", Decimal("0.7")),
        merge_threshold=by_name.get("merge_threshold", Decimal("0.9")),
        auto_clear=by_name.get("auto_clear", Decimal("0.95")),
    )


def threshold_for(
    relational: _Relational, *, table: str, intent: str, jurisdiction_path: Sequence[str]
) -> tuple[Decimal, str]:
    """The reporting threshold for this intent, and WHY it is that value.

    Keyed by jurisdiction AND intent in the estate, so the same entity under
    `onboarding` and under `enhanced-due-diligence` gets different reportable
    sets. The STRICTEST applicable threshold governs: a chain crossing three
    jurisdictions is reportable under the lowest bar any of them sets.

    Returns the basis alongside the value, because a threshold that fell back
    to the intent's strictest declared row — no priced jurisdiction on this
    chain's path — is a different fact from one the chain's own jurisdiction
    set, and a product that reported them identically would be hiding which
    it had.
    """
    wanted = intent.replace("-", "_")
    rows = relational.rows(
        f"select jurisdiction, threshold_pct from {table} where intent = %s", (wanted,)
    )
    if not rows:
        raise UnpricedIntent(
            f"intent `{intent}` has no row in `{table}`; this estate prices"
            f" only the intents its own register declares"
        )
    on_path = {
        str(row["jurisdiction"]): Decimal(str(row["threshold_pct"])) for row in rows
        if str(row["jurisdiction"]) in set(jurisdiction_path)
    }
    if on_path:
        chosen = min(on_path.values())
        named = sorted(j for j, v in on_path.items() if v == chosen)
        return chosen, f"strictest priced jurisdiction on this chain's path: {', '.join(named)}"
    strictest = min(Decimal(str(row["threshold_pct"])) for row in rows)
    return strictest, (
        "no priced jurisdiction on this chain's path; the intent's strictest"
        " declared value applies"
    )


def _floored(requested: Decimal | None, floor: Decimal, name: str) -> Decimal:
    """A caller may raise a floor and may never lower it.

    Lowering would report MORE than the credential permits, which is the test
    the published rule sets. Refused by name rather than silently honored
    (`UBO-G07`).
    """
    if requested is None:
        return floor
    if requested < floor:
        raise FloorBreached(
            f"`{name}` was asked at {requested}, below the estate's declared floor of {floor};"
            f" a caller may raise a floor and may never lower it"
        )
    return requested


# =========================================================================
# THE CLAIMS
# =========================================================================


def _records(
    relational: _Relational, documents: _Documents, terms: Mapping[str, Any], *,
    chain: Mapping[str, Any], entitlement: Entitlement, applicable: Decimal,
    min_confidence: Decimal, max_depth: int, as_of: datetime,
) -> tuple[tuple[Record, ...], int]:
    """Every admissible claim, minted only if the envelope admits it."""
    tables = terms["relational"]["tables"]
    prefixes = terms["entity_uri_prefix"]
    assignment = terms["classification"]["assignment"]
    records: list[Record] = []
    withheld = 0

    person_key = str(chain["person_key"])
    is_eu = bool(chain["person_is_eu_resident"])

    # THE RESIDENCY BOUND. A person the entitlement excludes is never minted,
    # and the WITHHELD COUNT never reaches the product (`UBO-G02`) — a count of
    # what was withheld is itself disclosure.
    if not entitlement.admits(is_eu_resident=is_eu):
        withheld += 1
    else:
        people = relational.rows(
            f"select person_key, nationality, is_eu_national, country_of_residence,"
            f" dob_month, dob_year from {tables['psc_person']} where person_key = %s",
            (person_key,),
        )
        person = people[0] if people else {"person_key": person_key}
        records.append(Record(
            entity_class="person", edge_type="hasBeneficialOwner",
            entity_uri=f"{prefixes['person']}{person_key}",
            attributes={
                "person_key": person_key,
                "nationality": str(person.get("nationality") or ""),
                "country_of_residence": str(person.get("country_of_residence") or ""),
                "is_eu_resident": str(is_eu).lower(),
                "dob_year": str(person.get("dob_year") or ""),
                "effective_pct": str(chain["effective_pct"]),
                "depth": str(chain["depth"]),
                "reportable": str(Decimal(str(chain["effective_pct"])) >= applicable).lower(),
                "classification": assignment["person_eu"] if is_eu else assignment["person"],
            },
            dated=None,
        ))

        # The resolution evidence — carried, never recomputed (`CP-SPEC-015` §F.4).
        for row in relational.rows(
            f"select source_system, source_id, source_name, match_score, match_band,"
            f" is_true_match from {tables['crosswalk']} where person_key = %s", (person_key,),
        ):
            score = Decimal(str(row["match_score"]))
            records.append(Record(
                entity_class="resolution", edge_type="hasResolution",
                entity_uri=f"{prefixes['finding']}res:{person_key}:{row['source_system']}:{row['source_id']}",
                attributes={
                    "person_key": person_key,
                    "source_system": str(row["source_system"]),
                    "source_name": str(row["source_name"] or ""),
                    "match_score": str(score),
                    "match_band": str(row["match_band"]),
                    "below_floor": str(score < min_confidence).lower(),
                    "classification": assignment["finding"],
                },
                dated=None,
            ))

        # The screening evidence — likewise carried.
        for row in relational.rows(
            f"select person_key, entry_id, listed_name, score, disposition, in_review_band"
            f" from {tables['screening']} where person_key = %s", (person_key,),
        ):
            records.append(Record(
                entity_class="screening", edge_type="hasScreening",
                entity_uri=f"{prefixes['finding']}scr:{person_key}:{row['entry_id']}",
                attributes={
                    "person_key": person_key, "entry_id": str(row["entry_id"]),
                    "listed_name": str(row["listed_name"] or ""),
                    "score": str(row["score"]), "disposition": str(row["disposition"]),
                    "in_review_band": str(bool(row["in_review_band"])).lower(),
                    "classification": assignment["finding"],
                },
                dated=None,
            ))

    # The ownership hops, bounded by `max_depth`. These are entity-to-entity
    # and carry no person data, so the residency bound does not reach them.
    for hop in relational.rows(
        f"select hop_index, owner_id, owner_kind, owned_id, owned_kind, stake_pct"
        f" from {tables['hop']} where chain_id = %s order by hop_index", (chain["chain_id"],),
    ):
        if int(hop["hop_index"]) >= max_depth:
            continue
        records.append(Record(
            entity_class="hop", edge_type="hasOwnershipHop",
            entity_uri=f"{prefixes['entity']}hop:{chain['chain_id']}:{hop['hop_index']}",
            attributes={
                "hop_index": str(hop["hop_index"]),
                "owner_id": str(hop["owner_id"]), "owner_kind": str(hop["owner_kind"]),
                "owned_id": str(hop["owned_id"]), "owned_kind": str(hop["owned_kind"]),
                "stake_pct": str(hop["stake_pct"]),
                "classification": assignment["entity"],
            },
            dated=None,
        ))

    # The KYC declarations, served BESIDE the computed figure and never
    # reconciled into it (`UBO-G15`).
    fields = terms["documents"]["fields"]
    for document in documents.declarations(
        collection=terms["documents"]["collection"],
        chain_id=str(chain["chain_id"]), entity_id=str(chain["entity_id"]),
    ):
        identifier = str(document.get(fields["document_id"]) or document.get("_id") or "")
        declared = document.get(fields["declared_pct"])
        records.append(Record(
            entity_class="declaration", edge_type="hasDeclaration",
            entity_uri=f"{prefixes['declaration']}{identifier}",
            attributes={
                "document_id": identifier,
                "kind": str(document.get(fields["kind"]) or ""),
                # THE SIMILARITY CORPUS. A `kind` alone is one word, and an
                # integer-Jaccard index scores a multi-word query against one
                # word at zero for every document — which would empty the
                # class at any floor above zero. The corpus is therefore the
                # document's own descriptive fields, composed here rather than
                # a text field the estate does not carry.
                "text": " ".join(str(document.get(key) or "") for key in
                                 (fields["kind"], "entity_name", "declared_owner_name",
                                  "jurisdiction")).strip(),
                "declared_pct": "" if declared is None else str(declared),
                "declared_owner_person_key": str(document.get(fields["declared_owner_person_key"]) or ""),
                "computed_pct": str(chain["effective_pct"]),
                "contradicts": str(
                    declared is not None
                    and abs(Decimal(str(declared)) - Decimal(str(chain["effective_pct"]))) > Decimal(1)
                ).lower(),
                "classification": assignment["declaration"],
            },
            dated=_as_date(document.get(fields["declared_on"])),
        ))
    return tuple(records), withheld


def required_classes() -> tuple[str, ...]:
    """The classes this product needs for completeness (`C`)."""
    return ("entity", "person", "resolution", "hop")


def _as_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None
