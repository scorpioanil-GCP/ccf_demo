"""The consuming bank's two source legs, and nothing else.

[ADAPT] everything here. [MECHANISM] nothing — **this module imports no `ccf`
at all**. It opens OUR two systems of record, reads the syndicate as filed,
our own position as booked, the consent mechanics as drafted and the bilateral
envelopes as negotiated, and hands back what it found.

**It never touches the peer.** There is no peer DSN, no peer ledger and no
peer URL in this module or anywhere else in this tree's code; the co-lender is
reached only through the registered door, by the SDK, on the consumer's own
registration. `CLD-G20` is the gate that keeps it so, and it is a real gate
because the two fabrics sit on one host and differ by a port and a database
name — isolation here is a software property, not a network one.

**The envelope is read, never applied, here.** This module reports each
counterparty's `requestScope` and `discloseScope` as two separate sets;
whether a given ask is inside the request set is a governance decision made at
the child-resolution seam, before any peer is called (`CLD-G10`).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import psycopg
import yaml

HERE = Path(__file__).parent

READ_TIMEOUT_SECONDS = 30.0


class UnknownFacility(LookupError):
    """The anchor resolves to no syndicated facility in our own estate."""


def vocabulary() -> Mapping[str, Any]:
    """Our stores' own names — tables, columns, IRIs."""
    document: Mapping[str, Any] = yaml.safe_load(
        (HERE / "artifacts" / "source-vocabulary.yaml").read_text(encoding="utf-8")
    )
    declaration: Mapping[str, Any] = document["declaration"]
    return declaration


def federation_policy() -> Mapping[str, Any]:
    """The governed federation values — the requested class and the latency bound."""
    document: Mapping[str, Any] = yaml.safe_load(
        (HERE / "artifacts" / "federation-policy.yaml").read_text(encoding="utf-8")
    )
    declaration: Mapping[str, Any] = document["declaration"]
    return declaration


@dataclass(frozen=True)
class Facility:
    """The anchor, as our relational leg holds it."""

    facility_id: str
    borrower_lei: str | None
    commitment_amount: Decimal | None
    syndicated: bool


@dataclass(frozen=True)
class Participation:
    """One member's commitment in the facility, as filed or as we book it."""

    participation_id: str
    member_lei: str | None
    member_label: str | None
    commitment_usd: Decimal | None
    #: ``True`` for the row that is OUR position, read from `own_position`
    #: rather than from the filed commitment schedule. Our own rating and
    #: workout posture ride on it and on nothing else.
    is_own_position: bool
    internal_rating: str | None = None
    workout_posture: str | None = None
    source_passage: str | None = None


@dataclass(frozen=True)
class ConsentThreshold:
    """One consent standard the filed agreement sets for this facility."""

    threshold_id: str
    consent_standard: str | None
    consent_percent: Decimal | None
    amendment_type: str | None
    source_passage: str | None


@dataclass(frozen=True)
class Envelope:
    """One bilateral disclosure envelope, with its TWO scopes kept apart.

    ``request_scope`` is what we may ASK this counterparty for.
    ``disclose_scope`` is what we may TELL it. They are different sets and
    frequently asymmetric — which is the whole reason this product has a
    federation-scope control at all.
    """

    envelope_id: str
    counterparty_lei: str | None
    request_scope: tuple[str, ...]
    disclose_scope: tuple[str, ...]
    envelope_version: str | None
    valid_from: str | None


@dataclass(frozen=True)
class Syndicate:
    """What our two legs found, before any fabric call has been made."""

    facility: Facility
    participations: tuple[Participation, ...]
    thresholds: tuple[ConsentThreshold, ...]
    envelopes: tuple[Envelope, ...]
    ledger_watermark: str


class _GraphLeg:
    """A read-only SPARQL client for our own syndicate ledger."""

    def __init__(self, *, url: str, ledger: str, client: httpx.Client) -> None:
        self._url = url.rstrip("/")
        self._ledger = ledger
        self._client = client

    @property
    def ledger(self) -> str:
        return self._ledger

    def query(self, body: str) -> list[Mapping[str, Any]]:
        response = self._client.post(
            f"{self._url}/v1/fluree/query",
            headers={"Content-Type": "application/sparql-query"},
            content=body.encode("utf-8"),
        )
        response.raise_for_status()
        bindings: list[Mapping[str, Any]] = response.json()["results"]["bindings"]
        return bindings

    def watermark(self) -> str:
        """The ledger's transaction index, or ``unreported`` — never invented.

        The reporting gap is `AIA-F-04`, a carried repository sweep this rung
        does not open.
        """
        response = self._client.get(f"{self._url}/v1/fluree/ledgers")
        if response.status_code != 200:
            return "unreported"
        name, separator, branch = self._ledger.partition(":")
        if not separator:
            name, branch = self._ledger, "main"
        for entry in response.json():
            if entry.get("name") == name and entry.get("branch", "main") == branch:
                return str(entry.get("t", "unreported"))
        return "unreported"


def _value(row: Mapping[str, Any], key: str) -> str | None:
    binding = row.get(key)
    return None if binding is None else str(binding["value"])


def _decimal(raw: str | None) -> Decimal | None:
    return None if raw is None or raw == "" else Decimal(raw)


def _tail(uri: str | None) -> str:
    """The last path segment of a URI — the estate's own local identifier."""
    return "" if uri is None else uri.rstrip("/").rsplit("/", 1)[-1]


def _relational(
    *, facility_id: str, settings: Mapping[str, str], vocab: Mapping[str, Any]
) -> tuple[Facility, Participation | None, Mapping[str, str]]:
    """Our facility, our own position, and the member id -> LEI map."""
    leg = vocab["relational_leg"]
    schema = settings["schema"]
    facility_columns = leg["facility_columns"]
    with psycopg.connect(settings["dsn"]) as connection:
        rows = connection.execute(
            f"SELECT {facility_columns['facility_id']},"
            f" {facility_columns['borrower_lei']},"
            f" {facility_columns['commitment_amount']},"
            f" {facility_columns['syndicated']}"
            f" FROM {schema}.{leg['facility_table']}"
            f" WHERE {facility_columns['facility_id']} = %s",
            (facility_id,),
        ).fetchall()
        if not rows:
            raise UnknownFacility(
                f"no facility {facility_id!r} in our own estate; an unresolvable"
                " anchor is a refusal, never an empty syndicate"
            )
        identifier, borrower, commitment, syndicated = rows[0]
        facility = Facility(
            facility_id=str(identifier),
            borrower_lei=None if borrower is None else str(borrower),
            commitment_amount=commitment,
            syndicated=bool(syndicated),
        )

        member_columns = leg["member_columns"]
        members = {
            str(member_id): str(lei)
            for member_id, lei in connection.execute(
                f"SELECT {member_columns['member_id']}, {member_columns['lei']}"
                f" FROM {schema}.{leg['member_table']}"
                f" WHERE {member_columns['lei']} IS NOT NULL"
            ).fetchall()
        }
        labels = {
            str(member_id): str(name)
            for member_id, name in connection.execute(
                f"SELECT {member_columns['member_id']}, {member_columns['legal_name']}"
                f" FROM {schema}.{leg['member_table']}"
            ).fetchall()
        }

        own_columns = leg["own_position_columns"]
        own_rows = connection.execute(
            f"SELECT {own_columns['member_id']}, {own_columns['share_usd']},"
            f" {own_columns['internal_rating']}, {own_columns['workout_posture']}"
            f" FROM {schema}.{leg['own_position_table']}"
            f" WHERE {own_columns['facility_id']} = %s",
            (facility_id,),
        ).fetchall()

    own: Participation | None = None
    if own_rows:
        member_id, share, rating, posture = own_rows[0]
        own = Participation(
            participation_id=str(vocab["uri_templates"]["own_participation"]).format(
                facility_id=facility_id
            ),
            member_lei=members.get(str(member_id)),
            member_label=labels.get(str(member_id)),
            commitment_usd=share,
            is_own_position=True,
            internal_rating=None if rating is None else str(rating),
            workout_posture=None if posture is None else str(posture),
        )
    return facility, own, members


def _participations(
    *, facility_uri: str, leg: _GraphLeg, vocab: Mapping[str, Any]
) -> tuple[Participation, ...]:
    """Every filed commitment in this facility, from the commitment schedule."""
    graph = vocab["graph_leg"]
    predicates = graph["predicates"]
    rows = leg.query(
        f"SELECT ?p ?member ?lei ?label ?commitment ?passage FROM <{leg.ledger}> WHERE {{"
        f" ?p a <{graph['participation_type']}> ."
        f" ?p <{predicates['participation_in']}> <{facility_uri}> ."
        f" ?p <{predicates['participation_of']}> ?member ."
        f" OPTIONAL {{ ?p <{predicates['commitment_usd']}> ?commitment }}"
        f" OPTIONAL {{ ?p <{predicates['source_passage']}> ?passage }}"
        f" OPTIONAL {{ ?member <{predicates['member_lei']}> ?lei }}"
        f" OPTIONAL {{ ?member <{predicates['label']}> ?label }} }}"
    )
    return tuple(
        Participation(
            participation_id=_tail(_value(row, "p")),
            member_lei=_value(row, "lei"),
            member_label=_value(row, "label"),
            commitment_usd=_decimal(_value(row, "commitment")),
            is_own_position=False,
            source_passage=_value(row, "passage"),
        )
        for row in rows
    )


def _thresholds(
    *, facility_uri: str, leg: _GraphLeg, vocab: Mapping[str, Any]
) -> tuple[ConsentThreshold, ...]:
    """Every consent standard the filed agreement sets for this facility."""
    graph = vocab["graph_leg"]
    predicates = graph["predicates"]
    rows = leg.query(
        f"SELECT ?t ?standard ?percent ?kind ?passage FROM <{leg.ledger}> WHERE {{"
        f" ?t a <{graph['threshold_type']}> ."
        f" ?t <{predicates['threshold_governs']}> <{facility_uri}> ."
        f" OPTIONAL {{ ?t <{predicates['consent_standard']}> ?standard }}"
        f" OPTIONAL {{ ?t <{predicates['consent_percent']}> ?percent }}"
        f" OPTIONAL {{ ?t <{predicates['amendment_type']}> ?kind }}"
        f" OPTIONAL {{ ?t <{predicates['source_passage']}> ?passage }} }}"
    )
    return tuple(
        ConsentThreshold(
            threshold_id=_tail(_value(row, "t")),
            consent_standard=_value(row, "standard"),
            consent_percent=_decimal(_value(row, "percent")),
            amendment_type=_value(row, "kind"),
            source_passage=_value(row, "passage"),
        )
        for row in rows
    )


def _envelopes(
    *, leg: _GraphLeg, vocab: Mapping[str, Any], members: Mapping[str, str]
) -> tuple[Envelope, ...]:
    """Every bilateral disclosure envelope, with its two scopes read SEPARATELY.

    The two predicates are queried in two passes rather than one, because a
    single pass joining both would multiply the rows and invite a reader to
    treat the product as one set. They are two sets; `CLD-G11` asserts it.
    """
    graph = vocab["graph_leg"]
    predicates = graph["predicates"]
    policy = federation_policy()
    request_predicate = str(policy["scope_predicates"]["request"])
    disclose_predicate = str(policy["scope_predicates"]["disclose"])

    def scopes(predicate: str) -> dict[str, list[str]]:
        found: dict[str, list[str]] = {}
        for row in leg.query(
            f"SELECT ?e ?scope FROM <{leg.ledger}> WHERE {{"
            f" ?e a <{graph['envelope_type']}> ."
            f" ?e <{predicate}> ?scope }}"
        ):
            key = _value(row, "e")
            value = _value(row, "scope")
            if key is not None and value is not None:
                found.setdefault(key, []).append(value)
        return found

    requested = scopes(request_predicate)
    disclosed = scopes(disclose_predicate)

    rows = leg.query(
        f"SELECT ?e ?counterparty ?version ?from FROM <{leg.ledger}> WHERE {{"
        f" ?e a <{graph['envelope_type']}> ."
        f" OPTIONAL {{ ?e <{predicates['envelope_counterparty']}> ?counterparty }}"
        f" OPTIONAL {{ ?e <{predicates['envelope_version']}> ?version }}"
        f" OPTIONAL {{ ?e <{predicates['valid_from']}> ?from }} }}"
    )
    return tuple(
        Envelope(
            envelope_id=_tail(_value(row, "e")),
            # The envelope names the member by its estate id; the LEI is the
            # token both fabrics share, so the join happens here rather than
            # leaving the product to compare two different namespaces.
            counterparty_lei=members.get(_tail(_value(row, "counterparty"))),
            request_scope=tuple(sorted(requested.get(_value(row, "e") or "", ()))),
            disclose_scope=tuple(sorted(disclosed.get(_value(row, "e") or "", ()))),
            envelope_version=_value(row, "version"),
            valid_from=_value(row, "from"),
        )
        for row in rows
    )


def acquire(
    *, facility_id: str, relational: Mapping[str, str], graph: Mapping[str, str]
) -> Syndicate:
    """Open both of OUR stores; read the syndicate, our position, the mechanics and the envelopes.

    Raises:
        UnknownFacility: the anchor resolves to no facility in our estate.
    """
    vocab = vocabulary()
    facility, own, members = _relational(
        facility_id=facility_id, settings=relational, vocab=vocab
    )
    facility_uri = f"{vocab['graph_leg']['facility_uri_prefix']}{facility_id}"
    with httpx.Client(timeout=READ_TIMEOUT_SECONDS) as client:
        leg = _GraphLeg(url=graph["url"], ledger=graph["ledger"], client=client)
        filed = _participations(facility_uri=facility_uri, leg=leg, vocab=vocab)
        thresholds = _thresholds(facility_uri=facility_uri, leg=leg, vocab=vocab)
        envelopes = _envelopes(leg=leg, vocab=vocab, members=members)
        watermark = leg.watermark()

    participations: Sequence[Participation] = filed if own is None else (*filed, own)
    return Syndicate(
        facility=facility,
        participations=tuple(participations),
        thresholds=thresholds,
        envelopes=envelopes,
        ledger_watermark=watermark,
    )


def envelopes_in_force(
    *, relational: Mapping[str, str], graph: Mapping[str, str]
) -> tuple[Envelope, ...]:
    """The bilateral envelopes ALONE — the minimum second read the child seam needs.

    `CLD-F-06` Option 1 (Dave, 2026-09-23). The per-question child seam may
    raise a governed refusal as of `D-IMPL-347` A2, but it receives no source
    handles — neither `ConsumerContext` nor `resolve_for` carries them — so a
    refusal decided on THIS deployment's own facts has to read them itself.

    **Narrow, and narrow deliberately.** This is NOT `acquire` again: it reads
    the member id -> LEI map and the three envelope queries, and nothing else.
    No facility row, no participations, no consent thresholds, no ledger
    watermark. Four source calls against `acquire`'s nine, and the product's
    own acquisition is untouched — a second FULL acquisition would be a second
    answer, and two answers to one question is the thing this must not become.

    **Temporally aligned by construction.** Both legs are read at the same
    ledger and schema the acquisition reads, under the same tenant's
    configuration, for the same question. The envelope rows are negotiated
    agreements rather than a moving market series, so re-reading them cannot
    produce a figure that disagrees with the served payload; nothing here
    reaches a per-instant series, and nothing here calls a peer.

    The friction is recorded as `CLD-F-11`, a category-2 DX candidate — not a
    missing capability, because this is implementable with no SDK change.
    """
    vocab = vocabulary()
    leg = vocab["relational_leg"]
    member_columns = leg["member_columns"]
    with psycopg.connect(relational["dsn"]) as connection:
        members = {
            str(member_id): str(lei)
            for member_id, lei in connection.execute(
                f"SELECT {member_columns['member_id']}, {member_columns['lei']}"
                f" FROM {relational['schema']}.{leg['member_table']}"
                f" WHERE {member_columns['lei']} IS NOT NULL"
            ).fetchall()
        }
    with httpx.Client(timeout=READ_TIMEOUT_SECONDS) as client:
        return _envelopes(
            leg=_GraphLeg(url=graph["url"], ledger=graph["ledger"], client=client),
            vocab=vocab,
            members=members,
        )
