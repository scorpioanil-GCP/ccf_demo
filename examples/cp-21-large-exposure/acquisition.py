"""The estate half of `risk.large-exposure` — four stores, one order.

[ADAPT] the readers and the vocabulary here to your own product. This module
holds the deployment's own estate knowledge and nothing of the SDK's.

THREE THINGS MAKE THIS RUNG DIFFERENT FROM EVERY EARLIER POPULATION
(`CP-SPEC-021` §0.2):

1. **The population is DERIVED, not read.** A connected group is computed by
   walking `connectedTo` and, where the caller's `connection_basis` includes
   it, `economicallyDependentOn`. **The basis is formative**: a different basis
   gives a different membership, therefore a different aggregate exposure,
   therefore a different compliance answer (`LEX-G04`).
2. **The RULE is an effective-dated artifact.** The regime in force is selected
   at the determination instant, and a regime's limit may be a PERCENTAGE of
   capital or an ABSOLUTE amount — Regulation O's $500,000 is the second shape
   (`LEX-G05`, `LEX-G09`).
3. **The capital base arrives in a different UNIT from the exposure.**
   `bank_capital` is denominated in thousands of dollars, the FFIEC Call Report
   convention; facility commitments are in dollars. The normalization happens
   HERE, at the acquisition boundary, using a factor DECLARED in
   `artifacts/source-vocabulary.yaml` and never written as a literal in code
   (`Q2`, ruled 2026-09-21). Both figures are carried onward.

AND THE ASYMMETRY IS CARRIED, NOT RESOLVED. Exposure moves intraday; capital is
quarterly. Nothing here ages one into the other's clock: the capital claim
keeps its own `report_date`, and the product discloses the gap (`LEX-G14`).
"""

from __future__ import annotations

import json
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
PERSPECTIVES = HERE / "artifacts" / "perspectives.yaml"

PRICED_INTENTS = ("limit-test", "committee-review", "supervisory-request")


class UnknownRegime(ValueError):
    """The caller named a regime this estate carries no version of."""


class UnknownBasis(ValueError):
    """The caller named a connection basis outside the declared domain."""


class UnpricedIntent(ValueError):
    """The caller named an intent this product prices no envelope for."""


class UnknownRole(ValueError):
    """The caller's role is not declared in `artifacts/perspectives.yaml`."""


class NoncanonicalMagnitude(ValueError):
    """A proposal magnitude was not an integer in canonical units."""


class NoCapitalBase(ValueError):
    """No capital base is observable at or before the determination instant."""


@lru_cache(maxsize=1)
def vocabulary() -> Mapping[str, Any]:
    return yaml.safe_load(VOCABULARY.read_text(encoding="utf-8"))["declaration"]


@lru_cache(maxsize=1)
def perspectives() -> Mapping[str, Any]:
    return yaml.safe_load(PERSPECTIVES.read_text(encoding="utf-8"))["declaration"]


def capital_units() -> Mapping[str, Any]:
    """The declared unit contract for the capital base — never a code literal."""
    return vocabulary()["capital_units"]


def normalize_capital(raw: Decimal) -> Decimal:
    """Raw Call Report amount -> dollars, by the DECLARED factor (`Q2`).

    The factor lives in `artifacts/source-vocabulary.yaml`. Writing `* 1000`
    here would put a regulatory-consequence constant in code, which the ruling
    forbids — and `LEX-G06` gates on the consequence rather than on the number,
    so an implementation that carried the right factor and applied it wrongly
    still fails.
    """
    return raw * Decimal(str(capital_units()["factor"]))


def required_classes() -> tuple[str, ...]:
    return ("group", "member", "exposure", "capital", "regime", "limit")


def connection_bases() -> tuple[str, ...]:
    """THE DECLARED DOMAIN, READ — never a tuple written here.

    `connection_basis` selects the group and therefore the answer, so its
    admissible set is a routing vocabulary and lives in the declared artifact
    under the No-Hardcoding Rule (CLAUDE.md §6.4).
    """
    return tuple(vocabulary()["connection_bases"])


# =========================================================================
# THE PROPOSAL — an explicit hypothetical, in integer canonical units
# =========================================================================


@dataclass(frozen=True)
class Proposal:
    """A hypothetical exposure. NOT evidence (`D-GATE-cp-24`, `LEX-G19`)."""

    facility_type: str
    commitment_usd: int
    obligor_lei: str

    def as_attributes(self) -> Mapping[str, str]:
        return {
            "proposal_facility_type": self.facility_type,
            "proposal_commitment_usd": str(self.commitment_usd),
            "proposal_obligor_lei": self.obligor_lei,
        }


def refuse_noncanonical(raw: Mapping[str, Any]) -> None:
    """Refuse a noncanonical magnitude BEFORE a request is built — never coerce."""
    given = raw.get("commitment_usd")
    if given is None:
        return
    if isinstance(given, bool) or not isinstance(given, int):
        raise NoncanonicalMagnitude(
            f"`proposal.commitment_usd` must be an INTEGER in canonical units (whole"
            f" dollars); got {given!r} of type {type(given).__name__}. It is refused"
            f" rather than coerced: rounding would produce a content address nobody"
            f" could reproduce"
        )


def bind_proposal(raw: Mapping[str, Any] | None) -> Proposal | None:
    if not raw:
        return None
    declared = ("facility_type", "commitment_usd", "obligor_lei")
    unknown = sorted(set(raw) - set(declared))
    if unknown:
        raise UnknownBasis(f"the proposal names undeclared member(s) {unknown}")
    refuse_noncanonical(raw)
    return Proposal(
        facility_type=str(raw.get("facility_type", "")),
        commitment_usd=int(raw.get("commitment_usd", 0)),
        obligor_lei=str(raw.get("obligor_lei", "")),
    )


# =========================================================================
# THE SHAPES
# =========================================================================


@dataclass(frozen=True)
class Role:
    role: str
    principal_id: str
    extra_members: tuple[str, ...]


@dataclass(frozen=True)
class Record:
    entity_class: str
    edge_type: str
    entity_uri: str
    attributes: Mapping[str, str]
    dated: date | None


@dataclass(frozen=True)
class Estate:
    anchor_lei: str
    role: Role | None
    group: Mapping[str, str] | None
    members: tuple[str, ...]
    connection_basis: str
    records: tuple[Record, ...]
    ledger_t: str
    proposal: Proposal | None = None
    records_materialized: int = 0
    findings: tuple[Mapping[str, str], ...] = field(default_factory=tuple)

    @property
    def empty(self) -> bool:
        return self.group is None


# =========================================================================
# THE READERS
# =========================================================================


class _Relational:
    def __init__(self, *, dsn: str, schema: str) -> None:
        self._dsn, self._schema = dsn, schema

    def rows(self, sql: str, args: tuple[Any, ...] = ()) -> list[Mapping[str, Any]]:
        import psycopg  # noqa: PLC0415
        from psycopg.rows import dict_row  # noqa: PLC0415
        from psycopg.sql import SQL, Identifier  # noqa: PLC0415

        with psycopg.connect(self._dsn, autocommit=True) as connection, \
                connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(SQL("SET search_path TO {}").format(Identifier(self._schema)))
            cursor.execute(sql, args)
            return [dict(row) for row in cursor.fetchall()]


class _Graph:
    """Fluree — the connection edges AND the effective-dated regime versions."""

    def __init__(self, *, url: str, ledger: str) -> None:
        self._url, self._ledger = url.rstrip("/"), ledger
        self._watermark = "unreported"

    def query(self, sparql: str) -> list[Mapping[str, str]]:
        request = urllib.request.Request(
            f"{self._url}/v1/fluree/query", data=sparql.encode("utf-8"),
            headers={"Content-Type": "application/sparql-query"},
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:  # noqa: S310
                payload = json.loads(response.read())
                self._watermark = str(response.headers.get("x-fdb-t") or self._watermark)
        except (urllib.error.URLError, TimeoutError):  # pragma: no cover - environment
            return []
        return [
            {key: value["value"] for key, value in row.items()}
            for row in payload.get("results", {}).get("bindings", [])
        ]

    @property
    def watermark(self) -> str:
        return self._watermark

    def connected(self, *, seed_names: Sequence[str], basis: str) -> list[Mapping[str, str]]:
        """The connection edges the BASIS admits — and only those.

        `control` walks `connectedTo` alone; `economic-dependency` walks
        `economicallyDependentOn` alone; `both` walks the union. The basis is
        formative: it decides which edges exist for this determination
        (`LEX-G04`).
        """
        terms = vocabulary()["graph"]
        clauses = []
        if basis in ("control", "both"):
            clauses.append(f"{{ ?a <{terms['connected_to']}> ?b BIND(\"control\" AS ?basis) }}")
        if basis in ("economic-dependency", "both"):
            clauses.append(
                f"{{ ?a <{terms['economically_dependent_on']}> ?b"
                f" BIND(\"economic-dependency\" AS ?basis) }}"
            )
        union = " UNION ".join(clauses)
        return self.query(
            f"SELECT ?a ?b ?basis FROM <{self._ledger}> WHERE {{ {union} }}"
        )

    def dependency_bases(self) -> Mapping[str, str]:
        terms = vocabulary()["graph"]
        return {
            row["s"]: row["o"]
            for row in self.query(
                f"SELECT ?s ?o FROM <{self._ledger}> WHERE"
                f" {{ ?s <{terms['dependency_basis']}> ?o }}"
            )
        }

    def regimes(self) -> list[Mapping[str, str]]:
        """Every declared regime version, with its effective date and rule form."""
        terms = vocabulary()["graph"]
        return self.query(
            f"SELECT ?s ?p ?o FROM <{self._ledger}> WHERE"
            f" {{ ?s a <{terms['regime_version_class']}> . ?s ?p ?o }}"
        )

    def limit_envelope(self) -> list[Mapping[str, str]]:
        terms = vocabulary()["graph"]
        return self.query(
            f"SELECT ?s ?p ?o FROM <{self._ledger}> WHERE"
            f" {{ ?s a <{terms['limit_envelope_class']}> . ?s ?p ?o }}"
        )


class _Documents:
    """MongoDB — the published rulebook text a limit must cite."""

    def __init__(self, *, uri: str, database: str) -> None:
        self._uri, self._database = uri, database

    def provisions(self, *, collection: str, passage_ids: Sequence[str]) -> Mapping[str, Mapping[str, Any]]:
        """`passage_id` -> the provision's own words.

        **NO HASH IS MINTED** (`LEX-G08`, ruled 2026-09-21). These passages
        carry no `sha256` and one is not invented: anchoring is proved by the
        authority resolving, the passage resolving, and the quoted text being
        the cited rule's.
        """
        if not passage_ids:
            return {}
        from pymongo import MongoClient  # noqa: PLC0415

        client = MongoClient(self._uri, serverSelectionTimeoutMS=15000)
        try:
            found = client[self._database][collection].find(
                {"passage_id": {"$in": list(passage_ids)}},
                {"passage_id": 1, "text": 1, "document_id": 1, "_id": 0},
            )
            return {str(doc["passage_id"]): dict(doc) for doc in found}
        finally:
            client.close()


def role_for(role: str) -> Role:
    declared = perspectives()["perspectives"].get(role)
    if declared is None:
        raise UnknownRole(
            f"role `{role}` is not declared in `artifacts/perspectives.yaml`;"
            f" the declared roles are {sorted(perspectives()['perspectives'])}"
        )
    return Role(role=role, principal_id=str(declared["principal_id"]),
                extra_members=tuple(declared.get("members", ()) or ()))


# =========================================================================
# ACQUIRE
# =========================================================================


def acquire(
    *,
    anchor_lei: str,
    as_of: datetime,
    intent: str,
    perspective: str,
    regime: str,
    connection_basis: str,
    proposal: Proposal | None,
    apply_mitigation: bool,
    relational_settings: Mapping[str, str],
    graph_settings: Mapping[str, str],
    document_settings: Mapping[str, str],
) -> Estate:
    """One anchor, one basis, one regime, at one instant."""
    terms = vocabulary()
    tables = terms["relational"]["tables"]
    relational = _Relational(dsn=relational_settings["dsn"], schema=relational_settings["schema"])
    graph = _Graph(url=graph_settings["url"], ledger=graph_settings["ledger"])
    documents = _Documents(uri=document_settings["uri"], database=document_settings["db"])

    if intent not in PRICED_INTENTS:
        raise UnpricedIntent(
            f"this product prices no envelope for intent `{intent}`;"
            f" the priced intents are {list(PRICED_INTENTS)}"
        )
    if connection_basis not in connection_bases():
        raise UnknownBasis(
            f"connection basis `{connection_basis}` is outside the declared domain"
            f" {list(connection_bases())}"
        )
    role = role_for(perspective)

    # 1. THE REGIME IN FORCE AT THE DETERMINATION INSTANT.
    regime_records, selected = _regimes(graph, documents, regime=regime, as_of=as_of, terms=terms)
    if selected is None:
        raise UnknownRegime(
            f"this estate carries no version of regime `{regime}` effective at"
            f" {as_of.date()}"
        )

    # 2. THE GROUP, DERIVED. The basis decides which edges exist.
    members, edge_records = _group(graph, anchor_lei=anchor_lei, basis=connection_basis,
                                   relational=relational, tables=tables, terms=terms)
    if not members:
        return Estate(anchor_lei=anchor_lei, role=role, group=None, members=(),
                      connection_basis=connection_basis, records=(),
                      ledger_t=graph.watermark, proposal=proposal)

    # 3. EXPOSURE over the derived group.
    exposures = relational.rows(
        f"select f.facility_id, f.borrower_lei lei, f.facility_type, f.commitment_amount,"  # noqa: S608
        f" coalesce(d.drawn, 0) drawn_amount, f.maturity_date"
        f" from {tables['facility']} f"
        f" left join (select facility_id, sum(amount) drawn from {tables['drawdown']}"
        f"            where drawdown_date <= %s group by 1) d on d.facility_id = f.facility_id"
        f" where f.borrower_lei = any(%s) order by f.facility_id",
        (as_of.date(), list(members)),
    )
    # THE GUARANTEE LEG. Read BOTH ways round: a guarantee the group GIVES is
    # additional exposure where the limit counts it, and a guarantee the group
    # RECEIVES is eligible mitigation. Both legs are measured and both counts
    # are served, because in this estate the second one is nearly empty and
    # saying so is the honest result (see the finding below).
    guarantees_given = relational.rows(
        f"select guarantor_lei, obligor_uri, kind, covered_pct, cap_amount"  # noqa: S608
        f" from {tables['guarantee']} where guarantor_lei = any(%s)",
        (list(members),),
    )
    member_names = {
        _slug(str(row["legal_name"] or row["gleif_legal_name"] or "")): str(row["lei"])
        for row in relational.rows(
            f"select lei, legal_name, gleif_legal_name from {tables['entity']}"  # noqa: S608
            f" where lei = any(%s)", (list(members),))
    }
    # `_local` of a graph URI is ALREADY slug-shaped, so it is compared against
    # `_slug(legal_name)` directly — exactly as `_group` does. Slugging it a
    # second time lower-cases the interior capitals and the join silently
    # matches nothing.
    guarantees_received = [
        row for row in relational.rows(
            f"select guarantor_lei, obligor_uri, kind, covered_pct, cap_amount"  # noqa: S608
            f" from {tables['guarantee']}")
        if _local(str(row["obligor_uri"])) in member_names
    ]

    # 4. THE CAPITAL BASE — normalized HERE, with the raw figure kept.
    capital_rows = relational.rows(
        f"select rssd, report_date, tier1_capital, tier2_capital, total_assets"  # noqa: S608
        f" from {tables['capital']} where report_date <= %s order by report_date desc limit 1",
        (as_of.date(),),
    )
    if not capital_rows:
        raise NoCapitalBase(
            f"no capital base is observable at or before {as_of.date()};"
            f" a limit calculation without a denominator is not served"
        )
    capital = capital_rows[0]

    # 5. THE TWO INTERNAL LIMIT AUTHORITIES — both read, neither discarded.
    declared_limits = relational.rows(f"select * from {tables['limit_definition']}")  # noqa: S608
    envelope = _limit_envelope(graph)

    # THE COVER EACH LEG ACTUALLY CARRIES, computed from the exposure already
    # acquired — never asserted as a constant. An obligor that holds no
    # facility contributes nothing, which is most of this corpus (`LEX-F-08`).
    exposure_by_lei: dict[str, Decimal] = {}
    for row in exposures:
        exposure_by_lei[str(row["lei"])] = (
            exposure_by_lei.get(str(row["lei"]), Decimal(0))
            + Decimal(str(row["commitment_amount"]))
        )
    cover_given = _cover(guarantees_given, exposure_by_lei, member_names)
    cover_received = _cover(guarantees_received, exposure_by_lei, member_names)

    records = [
        *edge_records,
        *_exposures(exposures, terms=terms),
        *regime_records,
        *_capital(capital, terms=terms),
        *_limits(declared_limits, envelope, terms=terms),
    ]

    findings: list[Mapping[str, str]] = []
    if (guarantees_given or guarantees_received) and not cover_received:
        findings.append({
            "finding": "guarantee-cover-resolves-to-nothing-measurable",
            "detail": (
                f"this group gives {len(guarantees_given)} guarantee(s) and receives"
                f" {len(guarantees_received)} whose obligor is a group member, but every covered"
                f" obligor holds no facility, so the recognized cover is zero. The corpus says so"
                f" itself: most rows note that the guaranteed subsidiary holds no facility. The"
                f" recognized mitigation here is therefore undrawn-commitment relief alone, and"
                f" the payload names which component applied rather than presenting one netted"
                f" figure"
            ),
        })
    if envelope and declared_limits:
        internal = next((r for r in declared_limits if str(r["intent"]) == "internal-appetite"), None)
        envelope_pct = envelope.get("limitPctOfCapital")
        if internal is not None and envelope_pct is not None:
            postgres_pct = Decimal(str(internal["limit_pct_of_capital"])) * Decimal(100)
            if Decimal(str(envelope_pct)) != postgres_pct:
                findings.append({
                    "finding": "internal-limit-authorities-disagree",
                    "detail": (
                        f"the relational limit register prices the internal appetite at"
                        f" {postgres_pct}% of capital and the graph's limit envelope at"
                        f" {envelope_pct}%. Both are served; neither is presented as wrong,"
                        f" and the rule that selects one for a determination is named"
                    ),
                })

    group = {
        "anchor_lei": anchor_lei,
        "connection_basis": connection_basis,
        # THE LEDGER POINT THE GROUP WAS DERIVED AT. Replay reconstructs the
        # membership from this `t`, never by re-walking "now" (`LEX-G21`).
        "ledger_t": graph.watermark,
        "member_count": str(len(members)),
        "members_lei_registered": str(len(members)),
        "regime": str(selected["id"]),
        "regime_label": str(selected.get("label", "")),
        "regime_effective_from": str(selected.get("effectiveFrom", "")),
        "rule_form": str(selected["rule_form"]),
        "limit_pct_of_capital": str(selected.get("limitPctOfCapital", "")),
        "limit_absolute_usd": str(selected.get("limitAbsoluteUsd", "")),
        # BOTH FIGURES, with their units (`Q2`, `LEX-G07`).
        "capital_raw_value": str(capital["tier1_capital"]),
        "capital_source_unit": str(capital_units()["source_unit"]),
        "capital_normalized_value": str(normalize_capital(Decimal(str(capital["tier1_capital"])))),
        "capital_normalized_unit": str(capital_units()["normalized_unit"]),
        "capital_unit_authority": str(capital_units()["authority"]),
        "capital_report_date": str(capital["report_date"]),
        "capital_age_days": str((as_of.date() - capital["report_date"]).days),
        "exposure_instant": as_of.isoformat(),
        # MITIGATION IS A CALLER CHOICE AND IT IS LOAD-BEARING (`LEX-G15`).
        "apply_mitigation": str(apply_mitigation).lower(),
        "guarantees_given": str(len(guarantees_given)),
        "guarantee_cover_given": str(cover_given),
        "guarantees_received_resolvable": str(len(guarantees_received)),
        "guarantee_cover_received": str(cover_received),
        **(proposal.as_attributes() if proposal else {}),
    }
    return Estate(
        anchor_lei=anchor_lei, role=role, group=group, members=tuple(sorted(members)),
        connection_basis=connection_basis, records=tuple(records), ledger_t=graph.watermark,
        proposal=proposal, records_materialized=len(records), findings=tuple(findings),
    )


# =========================================================================
# THE DERIVED GROUP
# =========================================================================


def _group(
    graph: _Graph, *, anchor_lei: str, basis: str, relational: _Relational,
    tables: Mapping[str, str], terms: Mapping[str, Any],
) -> tuple[set[str], list[Record]]:
    """Walk the admitted edges from the anchor and close over the component.

    The estate's connection edges are between NAMED entity nodes, so the anchor
    LEI is resolved to its name first and the members are resolved back to LEIs
    at the end. No join is invented: the mapping is `legal_entity`'s own.
    """
    names = relational.rows(
        f"select lei, legal_name, gleif_legal_name from {tables['entity']}"  # noqa: S608
    )
    by_lei = {str(r["lei"]): str(r["legal_name"] or r["gleif_legal_name"] or "") for r in names}
    anchor_name = by_lei.get(anchor_lei, "")
    if not anchor_name:
        return set(), []

    edges = graph.connected(seed_names=[anchor_name], basis=basis)
    bases = graph.dependency_bases()
    adjacency: dict[str, list[tuple[str, str, str]]] = {}
    for row in edges:
        a, b = _local(row["a"]), _local(row["b"])
        adjacency.setdefault(a, []).append((b, row.get("basis", ""), row["a"]))
        adjacency.setdefault(b, []).append((a, row.get("basis", ""), row["a"]))

    seed = _slug(anchor_name)
    seen: set[str] = {seed}
    frontier, walked = [seed], []
    while frontier:
        node = frontier.pop()
        for neighbour, edge_basis, subject_uri in adjacency.get(node, ()):
            walked.append((node, neighbour, edge_basis, subject_uri))
            if neighbour not in seen:
                seen.add(neighbour)
                frontier.append(neighbour)

    # A CONNECTED GROUP EXTENDS BEYOND THE LEI-REGISTERED SET. Measured
    # 2026-09-21: 106 of the graph's 166 connected nodes resolve to a
    # `legal_entity` row, so 60 do not. Those members are real and are served
    # WITHOUT an LEI rather than dropped — dropping them would shrink the group
    # and understate the exposure denominator, which is the *Context Starved*
    # counterfactual this product exists to refuse (`LEX-F-02`).
    slug_to_lei = {_slug(name): lei for lei, name in by_lei.items() if name}
    members = {slug_to_lei[s] for s in seen if s in slug_to_lei}
    members.add(anchor_lei)
    unregistered = sorted(s for s in seen if s not in slug_to_lei)

    records: list[Record] = []
    emitted: set[str] = set()
    for node in unregistered:
        records.append(Record(
            entity_class="member", edge_type="hasMember",
            entity_uri=f"{terms['entity_uri_prefix']['member']}unregistered:{node}",
            attributes={
                "lei": "", "legal_name": node, "is_anchor": "false", "in_group": "true",
                "admitted_by": basis,
                # STATED, not inferred: this member is in the group and carries
                # no measurable exposure, and the product says which.
                "lei_registered": "false",
                "classification": terms["classification"]["assignment"]["member"],
            }, dated=None))
    for lei in sorted(members):
        records.append(Record(
            entity_class="member", edge_type="hasMember",
            entity_uri=f"{terms['entity_uri_prefix']['member']}{lei}",
            attributes={
                "lei": lei,
                "legal_name": by_lei.get(lei, ""),
                "is_anchor": str(lei == anchor_lei).lower(),
                "in_group": "true",
                "admitted_by": basis,
                "lei_registered": "true",
                "classification": terms["classification"]["assignment"]["member"],
            }, dated=None))
    for node, neighbour, edge_basis, subject_uri in walked:
        key = f"{node}->{neighbour}:{edge_basis}"
        if key in emitted:
            continue
        emitted.add(key)
        if edge_basis != "economic-dependency":
            continue
        # ECONOMIC DEPENDENCY CARRIES ITS BASIS AND ITS PROVENANCE, so a
        # judgment stays distinguishable from a filing (`LEX-G20`).
        records.append(Record(
            entity_class="member", edge_type="hasMember",
            entity_uri=f"{terms['entity_uri_prefix']['member']}dependency:{node}:{neighbour}",
            attributes={
                "lei": "", "legal_name": neighbour, "is_anchor": "false", "in_group": "true",
                "admitted_by": "economic-dependency",
                "dependency_basis": bases.get(subject_uri, ""),
                "dependency_provenance": "synthetic — internal",
                "classification": terms["classification"]["assignment"]["member"],
            }, dated=None))
    return members, records


# =========================================================================
# THE REGIME, THE CAPITAL, THE LIMITS
# =========================================================================


def _regimes(
    graph: _Graph, documents: _Documents, *, regime: str, as_of: datetime, terms: Mapping[str, Any]
) -> tuple[list[Record], Mapping[str, Any] | None]:
    """Every declared regime version; the one in force at the instant is selected."""
    rows = graph.regimes()
    by_subject: dict[str, dict[str, Any]] = {}
    for row in rows:
        subject = row["s"]
        node = by_subject.setdefault(subject, {"id": _local(subject), "citesProvision": []})
        key = _local(row["p"])
        if key == "citesProvision":
            node["citesProvision"].append(row["o"])
        elif key == "rdf-schema#label" or row["p"].endswith("#label"):
            node["label"] = row["o"]
        elif not key.endswith("#type"):
            node.setdefault(key, row["o"])

    provisions = documents.provisions(
        collection=terms["documents"]["passage_collection"],
        passage_ids=[p for node in by_subject.values() for p in node["citesProvision"]],
    )

    records: list[Record] = []
    selected: Mapping[str, Any] | None = None
    for node in sorted(by_subject.values(), key=lambda n: str(n["id"])):
        effective = _as_date(node.get("effectiveFrom"))
        # THE RULE FORM — a percentage OR an absolute amount. Regulation O is
        # the second shape, and a product that assumed the first could not
        # express it (`LEX-G09`).
        rule_form = "percentage-of-capital" if node.get("limitPctOfCapital") else (
            "absolute-amount" if node.get("limitAbsoluteUsd") else "unstated")
        node["rule_form"] = rule_form
        # IN FORCE MEANS IN FORCE AT THE INSTANT, AT BOTH ENDS. The estate's
        # CRR version carries `effectiveTo 2021-12-31`: it is a real regime
        # that really expired, and selecting it for a 2026 determination would
        # apply repealed law. An earlier instant selects it correctly
        # (`LEX-G05`).
        until = _as_date(node.get("effectiveTo"))
        in_force = (
            effective is not None
            and effective <= as_of.date()
            and (until is None or as_of.date() <= until)
        )
        if node["id"].replace("regime-version-", "") == regime and in_force:
            selected = node
        cited = [
            {"passage_id": pid, **{k: v for k, v in provisions.get(pid, {}).items() if k != "passage_id"}}
            for pid in node["citesProvision"]
        ]
        records.append(Record(
            entity_class="regime", edge_type="hasRegime",
            entity_uri=f"{terms['entity_uri_prefix']['regime']}{node['id']}",
            attributes={
                "regime_id": str(node["id"]),
                "label": str(node.get("label", "")),
                "effective_from": str(node.get("effectiveFrom", "")),
                "effective_to": str(node.get("effectiveTo", "")),
                "in_force_at_instant": str(in_force).lower(),
                "rule_form": rule_form,
                "limit_pct_of_capital": str(node.get("limitPctOfCapital", "")),
                "limit_absolute_usd": str(node.get("limitAbsoluteUsd", "")),
                "provenance": str(node.get("provenance", "")),
                # THE AUTHORITY AND ITS OWN WORDS. No hash is minted.
                "cited_provisions": json.dumps(cited, sort_keys=True),
                "provisions_cited": str(len(node["citesProvision"])),
                "provisions_resolved": str(sum(1 for pid in node["citesProvision"] if pid in provisions)),
                "classification": terms["classification"]["assignment"]["regime"],
            },
            dated=effective,
        ))
    return records, selected


def _limit_envelope(graph: _Graph) -> Mapping[str, str]:
    node: dict[str, str] = {}
    for row in graph.limit_envelope():
        key = _local(row["p"])
        if not key.endswith("#type"):
            node.setdefault(key, row["o"])
    return node


def _capital(row: Mapping[str, Any], *, terms: Mapping[str, Any]) -> list[Record]:
    """The capital base as a claim — RAW and NORMALIZED, both with their unit."""
    raw = Decimal(str(row["tier1_capital"]))
    return [Record(
        entity_class="capital", edge_type="hasCapital",
        entity_uri=f"{terms['entity_uri_prefix']['capital']}{row['rssd']}:{row['report_date']}",
        attributes={
            "rssd": str(row["rssd"]),
            "report_date": str(row["report_date"]),
            "tier1_raw": str(raw),
            "source_unit": str(capital_units()["source_unit"]),
            "tier1_normalized": str(normalize_capital(raw)),
            "normalized_unit": str(capital_units()["normalized_unit"]),
            "unit_authority": str(capital_units()["authority"]),
            "classification": terms["classification"]["assignment"]["capital"],
        },
        # THE CAPITAL KEEPS ITS OWN DATE. Nothing ages it to the exposure
        # instant and nothing ages exposure back to it (`LEX-G14`).
        dated=_as_date(row["report_date"]),
    )]


def _limits(
    declared: Sequence[Mapping[str, Any]], envelope: Mapping[str, str], *, terms: Mapping[str, Any]
) -> list[Record]:
    """BOTH internal authorities, each naming where it came from."""
    records = [
        Record(entity_class="limit", edge_type="hasLimit",
               entity_uri=f"{terms['entity_uri_prefix']['limit']}relational:{row['intent']}",
               attributes={
                   "limit_id": str(row["intent"]),
                   "authority": "relational-limit-register",
                   "limit_pct_of_capital": str(Decimal(str(row["limit_pct_of_capital"])) * Decimal(100)),
                   "counts_guarantees": str(bool(row["counts_guarantees"])).lower(),
                   "counts_undrawn": str(bool(row["counts_undrawn"])).lower(),
                   "connection_basis": str(row["connection_basis"]),
                   "classification": terms["classification"]["assignment"]["limit"],
               }, dated=None)
        for row in declared
    ]
    if envelope:
        records.append(Record(
            entity_class="limit", edge_type="hasLimit",
            entity_uri=f"{terms['entity_uri_prefix']['limit']}graph:internal-appetite",
            attributes={
                "limit_id": "internal-appetite",
                "authority": "graph-limit-envelope",
                "limit_pct_of_capital": str(envelope.get("limitPctOfCapital", "")),
                "counts_guarantees": "", "counts_undrawn": "",
                "connection_basis": "",
                "effective_from": str(envelope.get("effectiveFrom", "")),
                "classification": terms["classification"]["assignment"]["limit"],
            }, dated=None))
    return records


def _exposures(rows: Sequence[Mapping[str, Any]], *, terms: Mapping[str, Any]) -> list[Record]:
    return [
        Record(entity_class="exposure", edge_type="hasExposure",
               entity_uri=f"{terms['entity_uri_prefix']['exposure']}{row['facility_id']}",
               attributes={
                   "facility_id": str(row["facility_id"]),
                   "lei": str(row["lei"]),
                   "facility_type": str(row["facility_type"] or ""),
                   "commitment_amount": str(row["commitment_amount"]),
                   "drawn_amount": str(row["drawn_amount"]),
                   "undrawn_amount": str(
                       Decimal(str(row["commitment_amount"])) - Decimal(str(row["drawn_amount"]))),
                   "maturity_date": str(row["maturity_date"] or ""),
                   "classification": terms["classification"]["assignment"]["exposure"],
               }, dated=None)
        for row in rows
    ]


# --- helpers ------------------------------------------------------------------------


def _cover(
    guarantees: Sequence[Mapping[str, Any]], exposure_by_lei: Mapping[str, Decimal],
    member_names: Mapping[str, str],
) -> Decimal:
    """Cover = the covered share of the obligor's OWN exposure, capped if stated.

    An obligor that holds no facility carries no exposure, so the cover is
    zero however generous the percentage. That is a fact about this corpus, not
    a modelling choice, and it is reported rather than smoothed away.
    """
    total = Decimal(0)
    for row in guarantees:
        lei = member_names.get(_local(str(row["obligor_uri"])), "")
        exposure = exposure_by_lei.get(lei, Decimal(0))
        if not exposure:
            continue
        covered = exposure * Decimal(str(row["covered_pct"] or 0))
        cap = row.get("cap_amount")
        if cap is not None:
            covered = min(covered, Decimal(str(cap)))
        total += covered
    return total


def _local(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def _slug(name: str) -> str:
    return "".join(ch for ch in name.title() if ch.isalnum())


def _as_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None
