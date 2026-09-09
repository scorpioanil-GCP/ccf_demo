"""`R-09`'s evidence — cp-05's real source, through the boundary, into L2.

`D-19`, the required observation, verbatim: *"same external source →
acquisition boundary → 77 nodes / 100 relationship claims"*. `D-18` is why it
lives here and not in `src/`: **cp-05's real SPARQL runs only from the test
harness**, so the 77/100 evidence is preserved without a query, a predicate
IRI, an anchor or a source system name entering the library (CLAUDE.md §6.4).

**Not one byte of cp-05 is modified by this module.** It reads cp-05's
declared Control Plane document as a test input, which the phase boundary
explicitly permits, and reproduces its acquisition against the same read-only
estate. `examples/cp-05-credit-exposure-rollup/` is never written, never rerun
for repair and never re-pinned (`D-IMPL-261`).

**The counts are read off L3, not off the acquisition walk.** Counting the walk
would measure the source; counting the graph measures the boundary. cp-05's own
deployment records why that distinction is load-bearing: *"An earlier draft of
this product answered the question from the acquisition walk directly. It
produced the same 77 entities and was not a Context Product."*

**What the acquisition boundary is.** :class:`SignalSourceProtocol`, which
already existed — see :mod:`ccf.signal.acquisition` for the measurement.
:class:`SparqlExposureSource` below is a deployment-side adapter over it,
carrying its acquisition parameters as constructor state, and its only output
type is :class:`SignalEnvelope` (`D-15`). No second relationship-claim output
was created.

**`24.10-F-05` is measured here, not asserted.** The envelope *resolution* half
of L1→L2 cannot express an edge between two entities that already exist in L3;
the *admission* half can, and does. Both are the existing path `D-15` names, so
the finding is classified and preserved rather than worked around (`D-16`).
"""

from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request
import uuid
from collections.abc import AsyncIterator, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.signal.acquisition import FileRecordAcquisitionSource
from ccf.signal.envelope import SignalEnvelope, SourceIdentity
from ccf.signal.source import SignalSourceProtocol

# --------------------------------------------------------------------------
# cp-05's declarations, read as test inputs. Every value below is READ from
# the example or from the environment; none of it is a value this repository
# invents, and none of it reaches `src/`.
# --------------------------------------------------------------------------

CP_05 = Path(__file__).resolve().parents[2] / "examples" / "cp-05-credit-exposure-rollup"

CONFIG = CP_05 / "ccf_config.yaml"

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "cp05-exposure-acquisition.json"

#: The two variables `backends.yaml` declares for the graph leg, by NAME.
URL_ENV = "CCF_CP_05_FLUREE_URL"
LEDGER_ENV = "CCF_CP_05_FLUREE_LEDGER"

#: The predicate IRIs cp-05 walks, read from its `deployment.py`. **FIBO's own
#: IRIs where FIBO has a term**, and ``example.org`` only where it does not.
#: Reproduced faithfully because a walk that differs by one predicate produces
#: a different node set and the 77 stops meaning what it means — the author's
#: recorded instrument error was probing with prose labels and measuring zero.
FIBO = "https://spec.edmcouncil.org/fibo/ontology"
OWNS = f"{FIBO}/FND/OwnershipAndControl/Ownership/owns"
IS_GUARANTOR_OF = f"{FIBO}/FBC/DebtAndEquities/Guaranty/isGuarantorOf"
ULTIMATELY_CONSOLIDATED_BY = (
    f"{FIBO}/BE/LegalEntities/LEIEntities/isUltimatelyConsolidatedBy"
)
CROSS_DEFAULTS_WITH = "http://example.org/fibo/crossDefaultsWith"
LEI_PREDICATE = "http://example.org/fibo/lei"

FLUREE_QUERY_PATH = "/v1/fluree/query"

#: The demonstrated request, from `artifacts/question.yaml` and the published
#: run transcript: LEI ``5493000Q1S5TJIDIQH89`` (REGIS CORP) at depth 3, both
#: traversal flags on, over ledger ``fibo-v2``.
ANCHOR_LEI = "5493000Q1S5TJIDIQH89"
DEPTH = 3
FOLLOW_GUARANTEES = True
FOLLOW_CROSS_DEFAULT = True

#: The instant the request named. A boundary, never a clock, so replay feeds
#: the same instant back through the same code path.
ASKED_AT = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)

#: This run's family scope. `ccf_config.yaml` declares
#: ``permitted_classifications: []`` on purpose and binds the family per
#: request; the acquisition carries it as an OBSERVED fact about each node —
#: this node was reached from this anchor by this walk.
FAMILY = "cp05-acquisition-boundary"

SOURCE = SourceIdentity(system_id="exposure_graph")


class GraphUnavailable(RuntimeError):
    """The estate did not answer.

    An unreachable graph and a graph with no matching edges are different
    facts, and a harness that conflated them would report a one-node family
    for a network partition.
    """


# --------------------------------------------------------------------------
# The acquisition adapter — deployment-side, over the seam that already exists
# --------------------------------------------------------------------------


class SparqlExposureSource:
    """cp-05's acquisition as a `SignalSourceProtocol` deployment-side adapter.

    **The acquisition parameters are constructor state**, which is the whole
    `R-09` measurement in one class: the Protocol declares
    ``envelopes(*, tenant_id)`` and nothing else, and a deployment that needs
    to acquire *for a question* constructs its source for that question. The
    fabric then asks the constructed object for its envelopes under the one
    parameter the Protocol carries.

    Its only output type is :class:`SignalEnvelope` (`D-15`). Node facts and
    edge facts are both envelopes; nothing here resolves an entity or mints a
    relationship claim, because interpretation is L2's monopoly.
    """

    def __init__(
        self,
        *,
        url: str,
        ledger: str,
        anchor_lei: str,
        depth: int,
        follow_guarantees: bool,
        follow_cross_default: bool,
        family: str,
        asked_at: datetime,
    ) -> None:
        self._url = url
        self._ledger = ledger
        self._anchor_lei = anchor_lei
        self._depth = depth
        self._follow_guarantees = follow_guarantees
        self._follow_cross_default = follow_cross_default
        self._family = family
        self._asked_at = asked_at

    def source_identity(self) -> SourceIdentity:
        """Identity, never location — the URL belongs to the estate, not here."""
        return SOURCE

    # -- the estate reads -------------------------------------------------

    def _sparql(self, body: str) -> list[dict[str, Any]]:
        """One SPARQL read against the declared ledger.

        Raises rather than returning an empty binding set, for the reason
        cp-05 records: the empty-operator guard cannot fire on an exception
        this function swallowed.
        """
        request = urllib.request.Request(
            self._url.rstrip("/") + FLUREE_QUERY_PATH,
            data=body.encode("utf-8"),
            headers={"Content-Type": "application/sparql-query"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.load(response)
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as error:
            raise GraphUnavailable(f"{self._url}{FLUREE_QUERY_PATH}: {error}") from error
        return list(payload.get("results", {}).get("bindings", []))

    def _predicates(self) -> list[str]:
        """The predicate types of the ONE walk, per the declared flags."""
        predicates = [OWNS, ULTIMATELY_CONSOLIDATED_BY]
        if self._follow_guarantees:
            predicates.append(IS_GUARANTOR_OF)
        if self._follow_cross_default:
            predicates.append(CROSS_DEFAULTS_WITH)
        return predicates

    def _anchor_node(self) -> str:
        """The source IRI for the anchor LEI, through the ledger's own bridge.

        The ``lei`` predicate is the only sound slug→LEI bridge; cp-05 records
        it as a join hazard because joining slug to LEI directly yields a 100%
        miss that reads like a finding rather than a defect.
        """
        rows = self._sparql(
            f'SELECT ?s FROM <{self._ledger}> WHERE '
            f'{{ ?s <{LEI_PREDICATE}> "{self._anchor_lei}" }}'
        )
        nodes = [row["s"]["value"] for row in rows if "s" in row]
        if len(nodes) != 1:
            raise AssertionError(
                f"anchor LEI {self._anchor_lei!r} resolved to {len(nodes)} nodes; "
                "exactly one is required for the walk to mean what it means"
            )
        return nodes[0]

    def _walk(self, anchor_node: str) -> list[str]:
        """ONE walk, several predicate types, BOTH directions.

        Bidirectional on purpose: a guarantee RECEIVED matters as much as one
        given, and a cross-default is symmetric by nature.
        """
        predicates = self._predicates()
        seen = {anchor_node}
        frontier = {anchor_node}
        for _ in range(self._depth):
            found: set[str] = set()
            for node in frontier:
                for predicate in predicates:
                    found.update(
                        row["o"]["value"]
                        for row in self._sparql(
                            f"SELECT ?o FROM <{self._ledger}> "
                            f"WHERE {{ <{node}> <{predicate}> ?o }}"
                        )
                        if "o" in row
                    )
                    found.update(
                        row["s"]["value"]
                        for row in self._sparql(
                            f"SELECT ?s FROM <{self._ledger}> "
                            f"WHERE {{ ?s <{predicate}> <{node}> }}"
                        )
                        if "s" in row
                    )
            frontier = found - seen
            seen |= found
            if not frontier:
                break
        return sorted(seen)

    def _edges(self, nodes: Sequence[str]) -> list[tuple[str, str, str]]:
        """Every edge among the acquired nodes, as ``(subject, predicate, object)``.

        The SHORT NAME is the relationship type, because that is what
        ``ccf_config.yaml`` declares under the traversal operator's
        ``relationship_types``: a full IRI here and a short name there would be
        a traversal the Control Plane permitted and the graph could not answer.
        """
        within = set(nodes)
        edges: set[tuple[str, str, str]] = set()
        for predicate in self._predicates():
            for row in self._sparql(
                f"SELECT ?s ?o FROM <{self._ledger}> "
                f"WHERE {{ ?s <{predicate}> ?o }}"
            ):
                subject, obj = row["s"]["value"], row["o"]["value"]
                if subject in within and obj in within:
                    edges.add((subject, predicate.rsplit("/", 1)[-1], obj))
        return sorted(edges)

    def _leis(self, nodes: Sequence[str]) -> dict[str, str]:
        """The ledger's own ``lei`` predicate for the acquired nodes."""
        rows = self._sparql(
            f"SELECT ?s ?lei FROM <{self._ledger}> "
            f"WHERE {{ ?s <{LEI_PREDICATE}> ?lei }}"
        )
        every = {
            row["s"]["value"]: row["lei"]["value"]
            for row in rows
            if "s" in row and "lei" in row
        }
        return {node: every[node] for node in nodes if node in every}

    # -- the emission -----------------------------------------------------

    def payloads(self) -> list[dict[str, Any]]:
        """The acquired source records, in the deployment's declared vocabulary.

        This is the shaping a *deployment* does: which payload key means
        "member" and which means "identity" is declared in
        ``ccf_config.yaml``'s resolution spec, and the SDK reads neither. The
        shape is FLAT because the resolver asks ``rule.match_key in payload``
        and then reads every identity and attribute key from the TOP LEVEL of
        the same mapping, as siblings.

        Captured verbatim into the committed fixture, so the offline half
        replays exactly these records through the same L1→L2 path.
        """
        anchor_node = self._anchor_node()
        nodes = self._walk(anchor_node)
        lei_by_node = self._leis(nodes)
        records: list[dict[str, Any]] = [
            {
                ("anchor_ref" if node == anchor_node else "member_ref"): True,
                "entity_uri": node,
                "lei": lei_by_node.get(node, ""),
                "label": "",
                "family_id": self._family,
            }
            for node in nodes
        ]
        records.extend(
            {"subject": subject, "predicate": predicate, "object": obj}
            for subject, predicate, obj in self._edges(nodes)
        )
        return records

    async def envelopes(self, *, tenant_id: str) -> AsyncIterator[SignalEnvelope]:
        """One envelope per acquired record, for ``tenant_id``.

        ``tenant_id`` is the only argument, and every acquisition parameter is
        constructor state — so a payload a previous read returned cannot steer
        the next read, because there is no argument through which it could.
        """
        for record in self.payloads():
            yield envelope_for(record, tenant_id=tenant_id, asked_at=self._asked_at)


def envelope_for(
    record: Mapping[str, Any], *, tenant_id: str, asked_at: datetime
) -> SignalEnvelope:
    """One acquired record as an envelope, with the record verbatim inside.

    ``envelope_id`` is derived from the record's own identity so two
    acquisitions of an unchanged estate mint the same signal and collapse
    under the graph's idempotent upsert (INV-CH7-17).
    """
    if "predicate" in record:
        envelope_id = (
            f"cp05:edge:{record['subject']}|{record['predicate']}|{record['object']}"
        )
    else:
        envelope_id = f"cp05:{record['entity_uri']}"
    return SignalEnvelope(
        tenant_id=tenant_id,
        envelope_id=envelope_id,
        source=SOURCE,
        ingestion_timestamp=asked_at,
        observed_time=asked_at,
        raw_payload=dict(record),
    )


# --------------------------------------------------------------------------
# The L1 → L2 drive, unchanged from what cp-05 already does through the SDK
# --------------------------------------------------------------------------


def boot_fabric(root: Path) -> Any:
    """A fabric booted from cp-05's declared Control Plane document.

    The document is a **test input**, read and never written. The L3 path is
    per-run, so two runs of this module build two separate graphs.
    """
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.deployment import load_config_and_boot

    root.mkdir(parents=True, exist_ok=True)
    database = root / f"cp_05_{uuid.uuid4().hex[:12]}.sqlite3"
    return load_config_and_boot(
        CONFIG,
        registry=ControlPlaneRegistry(),
        connection={"database_path": str(database)},
    )


def drive_into_l2(fabric: Any, envelopes: Sequence[SignalEnvelope]) -> dict[str, str]:
    """Drive acquired envelopes through the EXISTING L1→L2 path.

    Node envelopes go through :meth:`AssemblyWorker.ingest` — the resolution
    half. Edge envelopes go through
    :meth:`AssemblyWorker.admit_relationship_claim` — the admission half.
    Both halves are L2, both are the single writer, and `D-15` names both:
    *"Reuse the existing L1→L2 resolution/admission path."*

    **Why the edges take the admission half is measured, not assumed** — see
    ``test_the_resolution_half_cannot_express_an_edge_between_existing_entities``
    below, which is finding `24.10-F-05`.

    Returns the source-IRI → minted-node-key map, so the caller can see that
    every acquired node became exactly one entity.
    """
    from ccf.contracts.claims import LineageEntry, RelationshipClaim

    worker = fabric.handle.worker
    tenant = fabric.tenant_id

    minted: dict[str, str] = {}
    edges: list[SignalEnvelope] = []
    for envelope in envelopes:
        if "predicate" in envelope.raw_payload:
            edges.append(envelope)
            continue
        result = worker.ingest(envelope)
        for entity in getattr(result, "entities", ()):
            minted[str(envelope.raw_payload["entity_uri"])] = entity.node_key

    for envelope in edges:
        payload = envelope.raw_payload
        subject, obj = str(payload["subject"]), str(payload["object"])
        if subject not in minted or obj not in minted:
            continue
        worker.admit_relationship_claim(
            tenant_id=tenant,
            claim=RelationshipClaim(
                tenant_id=tenant,
                observed_at=ASKED_AT,
                valid_from=ASKED_AT,
                lineage=frozenset(
                    {
                        LineageEntry(
                            source=envelope.source,
                            envelope_id=envelope.envelope_id,
                            observed_at=ASKED_AT,
                        )
                    }
                ),
                relationship_type=str(payload["predicate"]),
                subject_uri=minted[subject],
                object_uri=minted[obj],
            ),
        )
    return minted


def counts_off_l3(fabric: Any) -> tuple[int, int]:
    """``(entities, relationship claims)`` read off L3 at the asked instant.

    Off the GRAPH, never off the acquisition walk — counting the walk would
    measure the source rather than the boundary.
    """
    view = fabric.handle.reader.as_of(tenant_id=fabric.tenant_id, at=ASKED_AT)
    return len(view.entities), len(view.relationships)


def acquire_and_count(
    source: SparqlExposureSource | FileRecordAcquisitionSource,
    tmp_path: Path,
) -> tuple[int, int, dict[str, str]]:
    """Drain ``source``, drive it into L2, and count off L3."""

    async def collect() -> list[SignalEnvelope]:
        return [
            envelope
            async for envelope in source.envelopes(tenant_id="cp-05-demo")
        ]

    envelopes = asyncio.run(collect())
    fabric = boot_fabric(tmp_path)
    try:
        minted = drive_into_l2(fabric, envelopes)
        entities, relationships = counts_off_l3(fabric)
    finally:
        fabric.handle.close()
    return entities, relationships, minted


# --------------------------------------------------------------------------
# The live half — env-gated, never vacuous
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def estate() -> tuple[str, str]:
    """The read-only exposure ledger, from the variables `backends.yaml` names.

    Skips when either is unset, naming both and the remedy — never invents a
    default, on `backends.yaml`'s own reasoning: a defaulted ledger name would
    be a value nobody chose pointing at a store nobody named.
    """
    url = os.environ.get(URL_ENV)
    ledger = os.environ.get(LEDGER_ENV)
    if not url or not ledger:
        pytest.skip(
            f"{URL_ENV} and {LEDGER_ENV} must both be set to run the live half; "
            f"export {URL_ENV} with the base URL of a READ-ONLY Fluree server "
            f"carrying the exposure ledger and {LEDGER_ENV} with the ledger name "
            "(the published transcript names the one the evidence was read from)"
        )
    return url, ledger


@pytest.fixture(scope="module")
def live_source(estate: tuple[str, str]) -> SparqlExposureSource:
    """cp-05's acquisition, constructed for the demonstrated question."""
    url, ledger = estate
    return SparqlExposureSource(
        url=url,
        ledger=ledger,
        anchor_lei=ANCHOR_LEI,
        depth=DEPTH,
        follow_guarantees=FOLLOW_GUARANTEES,
        follow_cross_default=FOLLOW_CROSS_DEFAULT,
        family=FAMILY,
        asked_at=ASKED_AT,
    )


@pytest.mark.fluree
def test_the_live_acquisition_conforms_to_the_existing_seam(
    live_source: SparqlExposureSource,
) -> None:
    """`R-09`'s verdict, on the real adapter: the seam already existed.

    The adapter that reads someone else's graph store over SPARQL satisfies
    :class:`ccf.signal.source.SignalSourceProtocol` with its acquisition
    parameters carried as constructor state, and no new Protocol was needed
    to make it do so (`D-IMPL-277`, resolved by discoverability).
    """
    assert isinstance(live_source, SignalSourceProtocol)
    assert live_source.source_identity() == SOURCE


@pytest.mark.fluree
def test_the_same_external_source_yields_77_entities_and_100_claims(
    live_source: SparqlExposureSource, tmp_path: Path
) -> None:
    """`D-19` — the evidence, live, from the real estate.

    Same external source → acquisition boundary → **77** entities and **100**
    relationship claims, read off L3 at the asked instant. Anchor LEI
    ``5493000Q1S5TJIDIQH89``, depth 3, both traversal flags on.
    """
    entities, relationships, minted = acquire_and_count(live_source, tmp_path)

    assert entities == 77
    assert relationships == 100
    assert len(minted) == 77, "every acquired node became exactly one entity"


@pytest.mark.fluree
def test_the_committed_fixture_still_matches_the_live_estate(
    live_source: SparqlExposureSource,
) -> None:
    """The live half is what keeps the offline fixture honest.

    An offline assertion over a fixture nobody re-derives is a test of a
    snapshot, not of a boundary. This is the test that fails the day the
    estate and the committed capture part company, so the offline 77/100 keeps
    meaning what it means.
    """
    assert live_source.payloads() == json.loads(
        FIXTURE.read_text(encoding="utf-8")
    ), (
        "the live acquisition no longer reproduces the committed fixture; "
        "re-capture it deliberately rather than relaxing this assertion"
    )


# --------------------------------------------------------------------------
# The offline half — the same numbers, no estate reachable
# --------------------------------------------------------------------------


@pytest.fixture()
def offline_source() -> FileRecordAcquisitionSource:
    """The committed capture, through the shipped reference implementation."""
    return FileRecordAcquisitionSource(
        path=FIXTURE, source=SOURCE, clock=lambda: ASKED_AT
    )


def test_the_fixture_replays_to_the_same_77_and_100(
    offline_source: FileRecordAcquisitionSource, tmp_path: Path
) -> None:
    """`D-17`'s reference implementation carries the same evidence offline.

    The captured records, through :class:`FileRecordAcquisitionSource`, through
    the *same* L1→L2 path, land the same 77 entities and 100 relationship
    claims — so CI has a real assertion and not a skip.
    """
    entities, relationships, minted = acquire_and_count(offline_source, tmp_path)

    assert entities == 77
    assert relationships == 100
    assert len(minted) == 77


def test_the_offline_run_is_not_vacuous() -> None:
    """The fixture holds real acquired records, not an empty document."""
    records = json.loads(FIXTURE.read_text(encoding="utf-8"))
    nodes = [record for record in records if "predicate" not in record]
    edges = [record for record in records if "predicate" in record]

    assert len(nodes) == 77
    assert len(edges) == 100
    assert sum(1 for record in nodes if record.get("anchor_ref")) == 1


def test_acquisition_emits_only_envelopes(
    offline_source: FileRecordAcquisitionSource,
) -> None:
    """`D-15` — one output type, and it has nowhere to put an interpretation.

    Node facts and edge facts are both :class:`SignalEnvelope`. There is no
    entity field and no relationship field on that contract, so the boundary
    cannot leak interpreted state even if an adapter wanted to (T-24.10-03-01).
    """

    async def collect() -> list[SignalEnvelope]:
        return [
            envelope
            async for envelope in offline_source.envelopes(tenant_id="cp-05-demo")
        ]

    envelopes = asyncio.run(collect())
    assert len(envelopes) == 177
    assert all(isinstance(envelope, SignalEnvelope) for envelope in envelopes)
    assert not any(
        hasattr(envelope, field) for envelope in envelopes
        for field in ("entities", "relationships", "claims")
    )


# --------------------------------------------------------------------------
# `24.10-F-05` — the D-16 evidence, measured rather than inherited
# --------------------------------------------------------------------------


def resolution_probe(
    tmp_path: Path,
    *,
    extra_entity_rules: Sequence[Mapping[str, Any]],
    relationship_rules: Sequence[Mapping[str, Any]],
    edge_payload: Mapping[str, Any],
) -> tuple[int, int, tuple[str, ...], tuple[tuple[str, str, str], ...]]:
    """Mint two entities the ordinary way, then push ONE edge envelope at `ingest`.

    Returns ``(entities_before, entities_after, pre_existing_uris, edges)``.

    The Control Plane document is a **copy** of cp-05's with the resolution
    section varied — cp-05 itself is never written.
    """
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    config["resolution"]["entity_rules"] = [
        *config["resolution"]["entity_rules"],
        *extra_entity_rules,
    ]
    config["resolution"]["relationship_rules"] = list(relationship_rules)

    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.deployment import load_config_and_boot

    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "ccf_config.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    database = tmp_path / f"probe_{uuid.uuid4().hex[:8]}.sqlite3"
    fabric = load_config_and_boot(
        path,
        registry=ControlPlaneRegistry(),
        connection={"database_path": str(database)},
    )
    try:
        worker = fabric.handle.worker
        for uri, is_anchor in (("urn:A", True), ("urn:B", False)):
            worker.ingest(
                envelope_for(
                    {
                        ("anchor_ref" if is_anchor else "member_ref"): True,
                        "entity_uri": uri,
                        "lei": "",
                        "label": "",
                        "family_id": FAMILY,
                    },
                    tenant_id=fabric.tenant_id,
                    asked_at=ASKED_AT,
                )
            )
        before = fabric.handle.reader.as_of(
            tenant_id=fabric.tenant_id, at=ASKED_AT
        )
        pre_existing = tuple(sorted(e.claim.entity_uri for e in before.entities))
        worker.ingest(
            SignalEnvelope(
                tenant_id=fabric.tenant_id,
                envelope_id="cp05:probe-edge",
                source=SOURCE,
                ingestion_timestamp=ASKED_AT,
                observed_time=ASKED_AT,
                raw_payload=dict(edge_payload),
            )
        )
        after = fabric.handle.reader.as_of(tenant_id=fabric.tenant_id, at=ASKED_AT)
        edges = tuple(
            (r.claim.relationship_type, r.claim.subject_uri, r.claim.object_uri)
            for r in after.relationships
        )
        return len(before.entities), len(after.entities), pre_existing, edges
    finally:
        fabric.handle.close()


ENDPOINT_RULE: dict[str, Any] = {
    "relationship_type": "owns",
    "subject_entity_class": "exposure_member",
    "object_entity_class": "exposure_member",
    "predicate_key": "predicate",
    "subject_rule": "edge_subject_ref",
    "object_rule": "edge_object_ref",
}


def test_the_resolution_half_cannot_express_an_edge_between_existing_entities(
    tmp_path: Path,
) -> None:
    """`24.10-F-05`, measured — and the reason the edges take the admission half.

    An entity URI is ``f"{entity_class}://{content_hash(identity)}"`` where
    ``identity`` is ``{key: value}`` over the rule's ``identity_keys``, so the
    hash covers the identity **key name**. Two consequences, both asserted
    here against a real fabric:

    1. Two endpoint rules reading the *same* identity key resolve one edge
       envelope's two endpoints to the *same* URI, and the pair is dropped as
       a self-loop. Zero relationships.
    2. Two endpoint rules reading *distinct* key names mint two **new**
       entities and join those — neither of them the entities that already
       existed.

    So an edge envelope can only join entities the same envelope resolved.
    cp-05's edges join entities minted by *earlier* envelopes, which the
    resolution half therefore cannot express.

    **This is preserved and classified, not worked around** (`D-16`). The
    existing *admission* half — :meth:`AssemblyWorker.admit_relationship_claim`
    — expresses them exactly, is still L2 and still the single writer, and is
    where all 100 of cp-05's claims land. No second relationship-claim output
    type was created.
    """
    same_key_before, same_key_after, _, same_key_edges = resolution_probe(
        tmp_path / "same-key",
        extra_entity_rules=[
            {
                "match_key": "edge_subject_ref",
                "entity_class": "exposure_member",
                "identity_keys": ["entity_uri"],
            },
            {
                "match_key": "edge_object_ref",
                "entity_class": "exposure_member",
                "identity_keys": ["entity_uri"],
            },
        ],
        relationship_rules=[ENDPOINT_RULE],
        edge_payload={
            "edge_subject_ref": True,
            "edge_object_ref": True,
            "entity_uri": "urn:A",
            "predicate": "owns",
        },
    )
    assert (same_key_before, same_key_after) == (2, 3)
    assert same_key_edges == (), "both endpoints are one URI; the self-loop is dropped"

    distinct_before, distinct_after, pre_existing, distinct_edges = resolution_probe(
        tmp_path / "distinct-keys",
        extra_entity_rules=[
            {
                "match_key": "edge_subject_ref",
                "entity_class": "exposure_member",
                "identity_keys": ["subject_uri"],
            },
            {
                "match_key": "edge_object_ref",
                "entity_class": "exposure_member",
                "identity_keys": ["object_uri"],
            },
        ],
        relationship_rules=[ENDPOINT_RULE],
        edge_payload={
            "edge_subject_ref": True,
            "edge_object_ref": True,
            "subject_uri": "urn:A",
            "object_uri": "urn:B",
            "predicate": "owns",
        },
    )
    assert (distinct_before, distinct_after) == (2, 4), (
        "distinct identity key names mint two NEW entities for the same values"
    )
    assert len(distinct_edges) == 1
    _, subject_uri, object_uri = distinct_edges[0]
    assert subject_uri not in pre_existing and object_uri not in pre_existing, (
        "the minted edge joins the two new entities, not the two that existed — "
        "which is 24.10-F-05 in one assertion"
    )


def test_the_admission_half_expresses_exactly_the_acquired_edges(
    offline_source: FileRecordAcquisitionSource, tmp_path: Path
) -> None:
    """The other side of `24.10-F-05`: the existing path does express them.

    Every relationship claim in L3 carries the predicate the source stated and
    joins two entities the acquisition minted — no self-loop, no class
    co-occurrence fan-out, no second output type.
    """

    async def collect() -> list[SignalEnvelope]:
        return [
            envelope
            async for envelope in offline_source.envelopes(tenant_id="cp-05-demo")
        ]

    envelopes = asyncio.run(collect())
    fabric = boot_fabric(tmp_path)
    try:
        minted = drive_into_l2(fabric, envelopes)
        view = fabric.handle.reader.as_of(
            tenant_id=fabric.tenant_id, at=ASKED_AT
        )
        node_keys = set(minted.values())
        acquired = {
            (
                str(envelope.raw_payload["subject"]),
                str(envelope.raw_payload["predicate"]),
                str(envelope.raw_payload["object"]),
            )
            for envelope in envelopes
            if "predicate" in envelope.raw_payload
        }
        in_graph = {
            (r.claim.subject_uri, r.claim.relationship_type, r.claim.object_uri)
            for r in view.relationships
        }
        assert len(in_graph) == len(acquired) == 100
        assert all(
            subject in node_keys and obj in node_keys
            for subject, _, obj in in_graph
        )
        assert not any(subject == obj for subject, _, obj in in_graph)
        assert {predicate for _, predicate, _ in in_graph} == {
            predicate for _, predicate, _ in acquired
        }
    finally:
        fabric.handle.close()


def test_cp_05_is_not_modified_by_this_module() -> None:
    """The phase boundary, asserted rather than trusted.

    cp-05 is read for its declarations and its measured numbers, and nothing
    else. If this module ever acquires a write to that tree, this fails.
    """
    import subprocess

    changed = subprocess.run(
        ["git", "status", "--short", "--", "examples/"],
        cwd=CP_05.parents[1],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert changed == "", f"examples/ is not clean: {changed!r}"


def test_the_harness_holds_the_domain_and_the_library_does_not() -> None:
    """`D-18` — cp-05's SPARQL lives here, and nowhere under `src/ccf/signal/`.

    The scoped check, and it is the operative one: this row writes only under
    ``src/ccf/signal/``, so that is the scope in which "nothing new" is
    answerable. A tree-wide count would not be a delta.
    """
    signal = Path(__file__).resolve().parents[2] / "src" / "ccf" / "signal"
    offending = [
        f"{module.name}:{number}"
        for module in sorted(signal.glob("*.py"))
        for number, line in enumerate(
            module.read_text(encoding="utf-8").splitlines(), start=1
        )
        if "SELECT" in line or "sparql" in line
    ]
    assert offending == [], f"query vocabulary reached ccf.signal: {offending}"


def test_the_iterator_is_the_boundary_and_carries_no_graph_handle(
    offline_source: FileRecordAcquisitionSource,
) -> None:
    """T-24.10-03-02 across both adapters in this module.

    Neither the live SPARQL adapter's class nor the shipped reference
    implementation declares any graph-shaped method, so single-writer
    (INV-CH7-10) holds across the acquisition boundary by the seam's shape.
    """
    for candidate in (SparqlExposureSource, type(offline_source)):
        names = dir(candidate)
        assert "upsert_entity" not in names
        assert "admit_relationship_claim" not in names
        assert set(names) & {"writer", "graph", "reader"} == set()


def test_the_estate_variables_are_named_and_never_valued() -> None:
    """T-24.10-03-03 — no connection value enters the tree.

    This module holds the two variable NAMES `backends.yaml` declares and no
    host, port, path or credential. The estate's address arrives from the
    environment or the live half skips.
    """
    text = Path(__file__).read_text(encoding="utf-8")
    assert URL_ENV in text and LEDGER_ENV in text

    # Assembled from parts so the guard's own needles are not the thing it
    # finds. A self-matching literal made the first draft of this test fail
    # against itself, which is a measurement of the instrument and not of the
    # tree.
    scheme = "://"
    forbidden = (
        scheme + "192.",
        scheme + "10.",
        "local" + "host:",
        "pass" + "word",
        "PG" + "PASSWORD",
    )
    for needle in forbidden:
        assert needle not in text, f"a connection value reached the tree: {needle}"
