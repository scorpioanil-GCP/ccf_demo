"""The Fluree v4 graph write path (plan 15.3-02).

DESIGN.md §2A.5.3; whitepaper §7.3 (append-only-with-supersession graph state)
and INV-CH7-10 (only the Assembly worker holds a write handle). CCF SDK
extension surface: the module split itself is D-01 of Phase 15.4, not a
whitepaper commitment.

**This module is one of the modules CINV-02 guards.** The
``cinv02-graph-writer`` rule's guarded set is a *class* of modules — the
neutral base :mod:`ccf.graph._writer` plus every
``ccf.graph.backends.<name>_write`` — so this file joined the guard the moment
it existed, with no lint edit. Only ``ccf.assembly`` (L2) and ``ccf.boot`` (the
composition root) may import it. Threat T-15.2-06 is the reason the JSON-LD
batch below is here rather than beside the read statements.

**Import direction is one-way, and that is structural — and D-14 is what that
buys.** This module imports its own reader module,
:mod:`ccf.graph.backends.fluree`, freely. The reverse is forbidden: if the
reader imported the writer, every importer of the reader would transitively
reach write code and the CINV-02 rule would flag the reader itself. The write
module is therefore also where a ``REGISTRATION`` record belongs (plan
15.4-04).

Before the D-01 split, the write path held its own copy of the policy-key
separator on the argument that importing the reader from the writer would break
the CINV-02 confinement and create a cycle. That argument was false then — the
writer already imported the reader — and it is unavailable now. The duplicate
is gone: :func:`~ccf.graph.backends.fluree.policy_key` is called on both sides
of the seam, so the guard that made CR-01 reachable on one copy only now covers
both (WR-01, D-14).

**The wire client is a core pin, so this module imports it at the top and the
registry must not flatten that into "all adapters load the same way."** This
module needs no optional dependency, no lazy import and no mypy override — the
SUBQ-14 evidence, visible as an absence. Its two extras-gated siblings,
:mod:`ccf.graph.backends.neo4j_write` and :mod:`ccf.graph.backends.mongo_write`,
keep their driver imports inside their store constructors on purpose, so
resolving one adapter loads no other adapter's driver. The difference between
the two shapes is a recorded finding about the substrates, not an inconsistency
to normalize away, and ``tests/deployment/test_adapter_config.py`` asserts the
optional-driver half of it in a fresh interpreter.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Any

from pydantic import SecretStr

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import canonical_timestamp
from ccf.graph._writer import BaseGraphWriter, BootToken, _GraphTxn
from ccf.graph.backends.fluree import (
    ADAPTER_CONTEXT,
    DEFAULT_PARTITION,
    L_EDGE,
    L_ENTITY,
    L_ENTITY_CLAIM,
    L_LINEAGE,
    L_RELATIONSHIP_CLAIM,
    LINK_PREDICATE,
    P_ADMIT_KEY,
    P_CLAIM_ID,
    P_CLAIM_JSON,
    P_CLAIM_KIND,
    P_ENTITY_CLASS,
    P_ENTITY_URI,
    P_ENTRY_JSON,
    P_FIRST_OBSERVED_AT,
    P_LAST_OBSERVED_AT,
    P_LINEAGE_ID,
    P_NODE_KEY,
    P_OBJECT_URI,
    P_OBSERVED_AT,
    P_PARTITION,
    P_POLICY_KEY,
    P_POLICY_VERSION,
    P_RELATIONSHIP_KEY,
    P_RELATIONSHIP_TYPE,
    P_SEQ,
    P_SUBJECT_URI,
    P_SUPERSEDED_AT,
    P_SUPERSEDED_BY,
    P_TENANT,
    P_VALID_FROM_CMP,
    P_VALID_TO_CMP,
    FlureeGraphStore,
    _mint_id,
    attribute_predicate,
    policy_key,
)
from ccf.graph.reader import ENTITY_KIND, RELATIONSHIP_KIND, Row, parse_timestamp
from ccf.graph.registry import BackendRegistration, BackendStore

__ccf_mode__ = "algorithmic"

#: The name a manifest uses to select this adapter — the module's own stem less
#: ``_write``, which is how built-in discovery derives it.
ADAPTER_NAME = "fluree"

#: The one config field of this adapter whose value is a credential. It is
#: **not** a field on :class:`FlureeConnection`: it is named here so the Control
#: Plane knows a credential is expected, and the value travels in the separate
#: ``secrets`` mapping :func:`_open_store` receives. See
#: :class:`FlureeConnection` for why the separation is structural.
BEARER_TOKEN_FIELD = "bearer_token"

__all__ = ["REGISTRATION", "FlureeConnection", "FlureeGraphWriter"]


# --- the Fluree v4 write path (plan 15.3-02) ---------------------------------
#
# The nine typed operations as one buffered JSON-LD batch. Every statement
# below is a committed-state read: the batch itself carries no `where` clause,
# because read-before-buffer plus INV-CH7-10 single-writer resolves every
# conditional in Python before the body is built (D-01/D-02, and see
# `_FlureeTxn.commit`).
#
# Statement text is code-authored in full — no identifier interpolation exists
# in this module — and every value binds as a request parameter.

_FLUREE_ENTITY_WINDOW = """
    MATCH (n:CcfEntity {ccf_partition: $partition, ccf_tenant_id: $tenant,
                        ccf_entity_uri: $key})
    RETURN n.ccf_first_observed_at AS first_observed_at,
           n.ccf_last_observed_at AS last_observed_at
"""

_FLUREE_EDGE_WINDOW = """
    MATCH (n:CcfEdge {ccf_partition: $partition, ccf_tenant_id: $tenant,
                      ccf_relationship_key: $key})
    RETURN n.ccf_first_observed_at AS first_observed_at,
           n.ccf_last_observed_at AS last_observed_at
"""

#: Serves both the boolean "is this claim committed?" question and the
#: supersession values a ground delete needs — one round trip, two answers.
_FLUREE_ENTITY_CLAIM = """
    MATCH (c:CcfEntityClaim {ccf_partition: $partition, ccf_tenant_id: $tenant,
                             ccf_entity_uri: $key, ccf_claim_id: $claim})
    RETURN c.ccf_superseded_by AS superseded_by,
           c.ccf_superseded_at AS superseded_at
"""

_FLUREE_RELATIONSHIP_CLAIM = """
    MATCH (c:CcfRelationshipClaim {ccf_partition: $partition,
                                   ccf_tenant_id: $tenant,
                                   ccf_relationship_key: $key,
                                   ccf_claim_id: $claim})
    RETURN c.ccf_superseded_by AS superseded_by,
           c.ccf_superseded_at AS superseded_at
"""

_FLUREE_ENTITY_CHAIN = """
    MATCH (c:CcfEntityClaim {ccf_partition: $partition, ccf_tenant_id: $tenant,
                             ccf_entity_uri: $key})
    RETURN c.ccf_claim_id AS claim_id, c.ccf_observed_at AS observed_at,
           c.ccf_seq AS seq
    ORDER BY c.ccf_observed_at, c.ccf_seq
"""

_FLUREE_RELATIONSHIP_CHAIN = """
    MATCH (c:CcfRelationshipClaim {ccf_partition: $partition,
                                   ccf_tenant_id: $tenant,
                                   ccf_relationship_key: $key})
    RETURN c.ccf_claim_id AS claim_id, c.ccf_observed_at AS observed_at,
           c.ccf_seq AS seq
    ORDER BY c.ccf_observed_at, c.ccf_seq
"""

_FLUREE_ENTITY_CLAIM_COUNT = """
    MATCH (c:CcfEntityClaim {ccf_partition: $partition, ccf_tenant_id: $tenant,
                             ccf_entity_uri: $key})
    RETURN count(c) AS n
"""

_FLUREE_RELATIONSHIP_CLAIM_COUNT = """
    MATCH (c:CcfRelationshipClaim {ccf_partition: $partition,
                                   ccf_tenant_id: $tenant,
                                   ccf_relationship_key: $key})
    RETURN count(c) AS n
"""

_FLUREE_LINEAGE_COUNT = """
    MATCH (l:CcfLineage {ccf_partition: $partition, ccf_tenant_id: $tenant,
                         ccf_claim_kind: $kind, ccf_node_key: $node,
                         ccf_claim_id: $claim, ccf_lineage_id: $lineage})
    RETURN count(l) AS n
"""

#: The five node kinds `_mint_id` addresses. Short, code-authored, and part of
#: the hashed identity, so two node classes sharing an identity tuple still
#: mint distinct `@id`s.
_FLUREE_ENTITY = "e"
_FLUREE_ENTITY_CLAIM_KIND = "ec"
_FLUREE_EDGE = "r"
_FLUREE_RELATIONSHIP_CLAIM_KIND = "rc"
_FLUREE_LINEAGE = "l"

#: Namespace prefixes on :data:`P_ADMIT_KEY`. These are what make the entity
#: and relationship admissibility namespaces disjoint, so an ``entity_uri`` can
#: never collide with a ``relationship_key`` inside the walk's single
#: ``$admissible`` parameter list (15.3-RESEARCH.md §R5).
_ENTITY_ADMIT_PREFIX = "e:"
_RELATIONSHIP_ADMIT_PREFIX = "r:"


def _fluree_claim_projection(claim_json: str, *, kind: str) -> dict[str, object]:
    """Write-time projections of the predicate-relevant claim fields.

    The Fluree twin of :func:`_mongo_claim_projection` and
    :func:`_neo4j_claim_projection`, and the same D-IMPL-34 argument: the
    adapter's physical model stores, beside the verbatim ``claim_json``, the
    fields the pushed predicates compare — so the read path needs no JSON
    parsing inside a query.

    **This is the DI-15.2-03 non-reintroduction site (§R8 vector 1), and it
    carries a burden its two twins do not.** ``valid_from`` / ``valid_to`` are
    re-rendered through :func:`~ccf.graph.reader.parse_timestamp` →
    :func:`~ccf.contracts.canonical.canonical_timestamp` into
    :data:`P_VALID_FROM_CMP` / :data:`P_VALID_TO_CMP`, and the payload's raw
    JSON value is **never** copied as a shortcut. The SQL adapters can afford a
    second chance because they re-normalize at read time via
    ``_utc_fixed_width``; **Fluree has no read-time equivalent.** The
    normalization happens here, in Python, at write time, and if it is skipped
    there is nowhere left to recover it — an offset-authored claim would
    compare as raw text against a canonical boundary and silently drop out of
    every pushed answer while the fallback kept including it (D-IMPL-90's
    original defect, re-entering through a different door).

    * entity claims: ``entity_class``, the multi-valued policy key below, and
      every **string-valued** attribute whose name
      :func:`~ccf.graph.backends.fluree.attribute_predicate` admits as a
      predicate. Both exclusions are harmless: a non-string value can never
      satisfy the `GQ-08` membership test against a set of strings (assumption
      A10), and an unsafe name is not made into an IRI at all — the attribute
      still travels verbatim inside ``claim_json``, and it still contributes
      its policy key unless the triple is one
      :func:`~ccf.graph.backends.fluree.policy_key` refuses (see below);
    * relationship claims: ``relationship_type`` / ``subject_uri`` /
      ``object_uri`` — the edge triple the traverse family and the
      induced-subgraph rule (`GQ-16` at
      docs/GRAPH_QUERY_SEMANTICS.md:316) constrain.

    **The multi-valued policy key (probe F-A6, D-07 rung 1).** Neo4j pushes
    `GQ-08`'s classification cut with dynamic property access
    ``c[$attribute_by_class[ec]]``. On this engine that expression **parses,
    returns 200 and evaluates to null** — it fails *silently*, so porting
    ``_ENTITY_POLICY`` would have produced a policy family excluding every
    claim while reporting success on the predicate family that gates the
    majority of real queries. The resolution materializes the cut instead: one
    :func:`~ccf.graph.backends.fluree.policy_key` value per string-valued
    attribute, pushed as ``c.ccf_policy_key IN $keys`` with ``RETURN DISTINCT``
    — semantically identical because a multi-valued property fans out into one
    row per value rather than yielding a list.

    That materialization is exactly `GQ-08`'s three cuts as pure membership: a
    class with no declared attribute contributes no key and is inadmissible; a
    claim carrying no value for its class's attribute produces no matching key
    and is inadmissible; and **no artifact-authored string ever enters query
    text** — the keys travel as a parameter list and the stored keys are
    literal values.

    **One construction, called from both sides (WR-01, D-14).** Until the
    Phase 15.4 writer split this module held its own copy of the separator and
    joined the triple by hand, on the stated argument that importing the reader
    from the writer would break the CINV-02 confinement and cycle. The argument
    was false — the write path already imported the reader — and the duplicate
    is what made CR-01 possible, because the injectivity guard lived on the
    read copy only. Both sides now call
    :func:`~ccf.graph.backends.fluree.policy_key`, so a triple this function
    refuses to encode is a triple the read side also refuses: the key is not
    stored, nothing pushed can match it, and the query declines to the fallback
    (D-04). A stored key and a pushed key can no longer be built two different
    ways.

    ``None`` values are omitted rather than stored: on RDF an absent property
    already reads back as null, and writing an explicit null would create a
    value where the read path's ``IS NULL`` expects none.
    """
    payload: dict[str, Any] = json.loads(claim_json)
    fields: dict[str, object] = {}
    valid_from = payload.get("valid_from")
    if valid_from is not None:
        parsed_from = parse_timestamp(valid_from)
        assert parsed_from is not None  # narrowed by the None check above
        fields[P_VALID_FROM_CMP] = canonical_timestamp(parsed_from)
    valid_to = payload.get("valid_to")
    if valid_to is not None:
        parsed_to = parse_timestamp(valid_to)
        assert parsed_to is not None  # narrowed by the None check above
        fields[P_VALID_TO_CMP] = canonical_timestamp(parsed_to)
    if kind == ENTITY_KIND:
        entity_class = payload["entity_class"]
        fields[P_ENTITY_CLASS] = entity_class
        policy_keys: list[str] = []
        for name, value in payload.get("attributes", {}).items():
            if not isinstance(value, str):
                continue
            # `policy_key` is the ONE construction, called from both sides of
            # the seam (WR-01, D-14). A `None` here is a triple whose own
            # components carry the separator: unencodable, therefore
            # unreachable from the read side, therefore not stored — the
            # fail-closed direction, and the claim is answered by the
            # fallback (D-04).
            key = policy_key(entity_class, name, value)
            if key is not None:
                policy_keys.append(key)
            predicate = attribute_predicate(name)
            if predicate is not None:
                fields[predicate] = value
        if policy_keys:
            # Sorted so the rendered body is a deterministic function of the
            # claim, exactly as the Mongo filter renderings are.
            fields[P_POLICY_KEY] = sorted(policy_keys)
    else:
        fields[P_RELATIONSHIP_TYPE] = payload["relationship_type"]
        fields[P_SUBJECT_URI] = payload["subject_uri"]
        fields[P_OBJECT_URI] = payload["object_uri"]
    return fields


class _FlureeTxn:
    """The nine :class:`_GraphTxn` operations as one buffered JSON-LD batch.

    The batched-adapter shape the Protocol contract names (D-IMPL-88) in its
    purest form: every mutation is appended to a ground-triple accumulator and
    **nothing reaches the server until** :meth:`commit`, which issues exactly
    one ``POST``. Both contract rules hold:

    * **Rowcounts resolve before commit.** ``insert_*_claim`` returns 0 for a
      re-arrival of a claim id already held — committed or buffered — which is
      the writer's idempotency signal, and ``insert_lineage`` returns 0 on a
      full-entry-identity collision, which *is* the L-axis set-union
      (INV-CH7-17). Single-writer (INV-CH7-10) is what makes the pre-buffer
      read authoritative.
    * **Reads see this transaction's own operations.** ``select_*_chain``
      merges the committed chain with claims appended earlier in the same
      transaction, and a supersession set earlier in the transaction is applied
      to the buffered triple too — by mutating it, since it has not been sent.

    **The commit body carries no guard clause, and that is a ruling rather than
    a preference.** A JSON-LD update body carries one ``where``, one ``delete``
    and one ``insert``; independent conditionals would *join* rather than
    union, and a body mixing a guarded update with unrelated ground inserts
    **silently drops the inserts whenever the guard misses** — the documented
    trap. Probe F-A4(a) established that a ground ``delete`` with no ``where``
    is accepted and applied, and its positive control established that the
    probe had discriminating power (without the ``delete``, both values
    survive). **Dave ruled `approved` on 2026-08-08**: D-02's letter holds
    unchanged and the SPARQL UPDATE multi-operation departure is not taken.

    **``opts.eventTime`` is never set.** Backdated commits look like the answer
    to CCF's bitemporality and are not (Pitfall 12): they require monotonically
    non-decreasing RFC 3339 values along the commit chain, and L2's write
    stream guarantees none — ``observed_at`` is data, arbitrary and frequently
    late-arriving. Tying it to Fluree's commit clock is the
    transaction-time-for-observation-time substitution D-IMPL-88 forbids. A
    future reader who discovers the feature should find the refusal already
    argued here.

    **``flakes_added`` cannot implement the per-operation rowcount contract,
    and on this build does not exist.** The contract requires a rowcount *per
    operation* while one POST yields at most one aggregate receipt, so a
    receipt field could only ever have cross-checked the sum. Probe F-A4(d)
    then measured that ``fluree/server:4.1.4`` returns no ``flakes_added`` at
    all (nor ``flakes_retracted``, ``previous_commit_id`` or ``timestamp``) —
    the documented receipt shape is not what this build sends. So no
    cross-check is written: there is nothing to cross-check against, and the
    read-before-buffer mechanism was always the authority.

    Ordering inside the body carries no meaning beyond ``delete`` preceding
    ``insert``: the five identities are independent and every operation is an
    assertion about its own subject.

    Lives in this module and only this module, per the CINV-02 rule the module
    docstring states (threat T-15.2-06): **no write operation exists in
    ``ccf.graph.backends.fluree``.**
    """

    def __init__(self, *, store: FlureeGraphStore) -> None:
        self._store = store
        self._insert: list[dict[str, Any]] = []
        self._delete: list[dict[str, Any]] = []
        self._entity_claims: list[dict[str, Any]] = []
        self._relationship_claims: list[dict[str, Any]] = []
        self._lineage: set[tuple[str, ...]] = set()
        # Node id -> the observed window currently in effect (committed or
        # buffered). Populated lazily by one read per node per transaction.
        self._windows: dict[str, tuple[str, str]] = {}
        # Node id -> the pending insert document for a node this transaction
        # created. Nothing in here has been sent, so widening it is a mutation
        # rather than a delete/insert pair.
        self._pending: dict[str, dict[str, Any]] = {}

    # -- buffer mechanics ----------------------------------------------------

    def _replace(
        self,
        node_id: str,
        predicate: str,
        old: object | None,
        new: object | None,
    ) -> None:
        """Retract one committed value and assert its replacement.

        The ground delete + ground insert pair F-A4(a) proved and Dave ruled
        `approved`. It exists because JSON-LD offers no ``$set`` analog: RDF
        set semantics means asserting a second value **adds** it beside the
        first rather than overwriting, so a supersession update must know the
        old value in order to retract it. This is the one operation where
        :class:`_MongoTxn` is not a complete template — the rowcount half
        carries verbatim, this mutation half is new.

        A no-op replacement emits nothing: ``_restitch_chain`` re-states every
        link of a chain on every write, so identical-value calls are the common
        case rather than the exception.
        """
        if old == new:
            return
        if old is not None:
            self._delete.append({"@id": node_id, predicate: old})
        if new is not None:
            self._insert.append({"@id": node_id, predicate: new})

    def _rows(self, statement: str, params: dict[str, object]) -> list[dict[str, Any]]:
        """One committed-state read."""
        return self._store.post_query(statement, params)

    def _count(self, statement: str, params: dict[str, object]) -> int:
        """One committed-state ``count()`` read."""
        rows = self._rows(statement, params)
        return int(rows[0]["n"]) if rows else 0

    def _upsert_node(
        self,
        *,
        node_id: str,
        window_statement: str,
        window_params: dict[str, object],
        document: dict[str, Any],
        observed_at: str,
    ) -> int:
        """Create the node on first sight, widen its observed window after.

        ``first_observed_at`` only ever moves earlier and ``last_observed_at``
        only ever moves later; nothing is deleted. Canonical text compares
        lexicographically as chronologically, so ``min`` / ``max`` over the
        stored strings render ``MIN()`` / ``MAX()`` exactly.

        The widening is a delete/insert pair rather than an overwrite for the
        same reason supersession is (:meth:`_replace`): a bare second assertion
        would leave the node carrying *two* ``first_observed_at`` values, and
        RDF's fan-out would then surface both.
        """
        window = self._windows.get(node_id)
        if window is None:
            committed = self._rows(window_statement, window_params)
            if not committed:
                self._insert.append(document)
                self._pending[node_id] = document
                self._windows[node_id] = (observed_at, observed_at)
                return 1
            window = (
                str(committed[0]["first_observed_at"]),
                str(committed[0]["last_observed_at"]),
            )
        first = min(window[0], observed_at)
        last = max(window[1], observed_at)
        if (first, last) != window:
            pending = self._pending.get(node_id)
            if pending is not None:
                pending[P_FIRST_OBSERVED_AT] = first
                pending[P_LAST_OBSERVED_AT] = last
            else:
                self._replace(node_id, P_FIRST_OBSERVED_AT, window[0], first)
                self._replace(node_id, P_LAST_OBSERVED_AT, window[1], last)
        self._windows[node_id] = (first, last)
        return 1

    @staticmethod
    def _apply_supersession(
        document: dict[str, Any],
        *,
        superseded_by: str | None,
        superseded_at: str | None,
    ) -> None:
        """Set or clear supersession on a triple that has not been sent yet.

        Clearing **removes** the key rather than writing null: on RDF an absent
        property already reads back as null, and an explicit null would create
        a value where the read path's ``IS NULL`` expects none.
        """
        for predicate, value in (
            (P_SUPERSEDED_BY, superseded_by),
            (P_SUPERSEDED_AT, superseded_at),
        ):
            if value is None:
                document.pop(predicate, None)
            else:
                document[predicate] = value

    def commit(self) -> None:
        """Apply the whole buffer as ONE ground JSON-LD transaction."""
        if self._insert or self._delete:
            body: dict[str, object] = {"@context": ADAPTER_CONTEXT}
            if self._delete:
                body["delete"] = list(self._delete)
            if self._insert:
                body["insert"] = list(self._insert)
            self._store.post_update(body)
        self.rollback()

    def rollback(self) -> None:
        """Drop the buffer. Nothing was applied, so nothing is undone."""
        self._insert.clear()
        self._delete.clear()
        self._entity_claims.clear()
        self._relationship_claims.clear()
        self._lineage.clear()
        self._windows.clear()
        self._pending.clear()

    # -- the nine typed operations -------------------------------------------

    def upsert_entity_node(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        entity_class: str,
        observed_at: str,
    ) -> int:
        scope = self._store.scope(tenant_id)
        partition = scope["partition"]
        node_id = _mint_id(_FLUREE_ENTITY, partition, tenant_id, entity_uri)
        return self._upsert_node(
            node_id=node_id,
            window_statement=_FLUREE_ENTITY_WINDOW,
            window_params={**scope, "key": entity_uri},
            document={
                "@id": node_id,
                "@type": L_ENTITY,
                P_PARTITION: partition,
                P_TENANT: tenant_id,
                P_ENTITY_URI: entity_uri,
                P_ENTITY_CLASS: entity_class,
                # The `e:` prefix is what keeps the entity and relationship
                # admissibility namespaces disjoint, so an `entity_uri` can
                # never collide with a `relationship_key` in the walk's one
                # `$admissible` parameter list.
                P_ADMIT_KEY: _ENTITY_ADMIT_PREFIX + entity_uri,
                P_FIRST_OBSERVED_AT: observed_at,
                P_LAST_OBSERVED_AT: observed_at,
            },
            observed_at=observed_at,
        )

    def insert_entity_claim(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        claim_id: str,
        claim_json: str,
        observed_at: str,
        policy_bundle_version: str,
    ) -> int:
        scope = self._store.scope(tenant_id)
        partition = scope["partition"]
        buffered = {row[P_CLAIM_ID] for row in self._entity_claims}
        if claim_id in buffered:
            return 0
        identity: dict[str, object] = {
            **scope,
            "key": entity_uri,
            "claim": claim_id,
        }
        if self._rows(_FLUREE_ENTITY_CLAIM, identity):
            return 0
        node_id = _mint_id(
            _FLUREE_ENTITY_CLAIM_KIND, partition, tenant_id, entity_uri, claim_id
        )
        document: dict[str, Any] = {
            "@id": node_id,
            "@type": L_ENTITY_CLAIM,
            P_PARTITION: partition,
            P_TENANT: tenant_id,
            P_ENTITY_URI: entity_uri,
            P_CLAIM_ID: claim_id,
            P_CLAIM_JSON: claim_json,
            P_OBSERVED_AT: observed_at,
            P_POLICY_VERSION: policy_bundle_version,
            # Committed count for THIS entity plus this transaction's own
            # buffered claims for THIS entity. Both terms must be scoped to
            # the same key or the sum is not a sequence: an unscoped
            # `len(self._entity_claims)` would count claims buffered for
            # OTHER entities, so `A1, B1, A2` in one transaction gives `A`
            # seq 0 and 2, and the next transaction's `A3` reads
            # `count(A) == 2` and computes 2 — a duplicate. Two claims of one
            # entity sharing an `observed_at` and a `seq` then order
            # non-deterministically under `ORDER BY observed_at, seq`, and
            # `_restitch_chain` yields a different supersession chain per
            # read. Dormant while `BaseGraphWriter` opens one transaction per
            # claim, but that is a property of the caller, not of a buffered
            # batch adapter (review finding WR-07).
            P_SEQ: self._count(
                _FLUREE_ENTITY_CLAIM_COUNT, {**scope, "key": entity_uri}
            )
            + sum(
                1
                for buffered_claim in self._entity_claims
                if buffered_claim[P_ENTITY_URI] == entity_uri
            ),
            **_fluree_claim_projection(claim_json, kind=ENTITY_KIND),
        }
        # One object in two roles: the pending insert triple AND the buffer
        # `select_entity_chain` merges. They cannot drift because they are the
        # same dict.
        self._entity_claims.append(document)
        self._insert.append(document)
        return 1

    def select_entity_chain(
        self, *, tenant_id: str, entity_uri: str
    ) -> Sequence[Row]:
        scope = self._store.scope(tenant_id)
        rows: list[dict[str, Any]] = list(
            self._rows(_FLUREE_ENTITY_CHAIN, {**scope, "key": entity_uri})
        )
        rows += [
            {
                "claim_id": document[P_CLAIM_ID],
                "observed_at": document[P_OBSERVED_AT],
                "seq": document[P_SEQ],
            }
            for document in self._entity_claims
            if document[P_ENTITY_URI] == entity_uri
        ]
        # Stable sort on (observed_at, seq) — the graph rendering of
        # `ORDER BY observed_at, rowid`.
        rows.sort(key=lambda row: (row["observed_at"], row["seq"]))
        return rows

    def update_entity_supersession(
        self,
        *,
        tenant_id: str,
        entity_uri: str,
        claim_id: str,
        superseded_by: str | None,
        superseded_at: str | None,
    ) -> int:
        scope = self._store.scope(tenant_id)
        partition = scope["partition"]
        matched = 0
        for document in self._entity_claims:
            if (
                document[P_CLAIM_ID] == claim_id
                and document[P_ENTITY_URI] == entity_uri
            ):
                self._apply_supersession(
                    document,
                    superseded_by=superseded_by,
                    superseded_at=superseded_at,
                )
                matched = 1
        if matched == 1:
            return matched
        held = self._rows(
            _FLUREE_ENTITY_CLAIM,
            {**scope, "key": entity_uri, "claim": claim_id},
        )
        if not held:
            return 0
        node_id = _mint_id(
            _FLUREE_ENTITY_CLAIM_KIND, partition, tenant_id, entity_uri, claim_id
        )
        self._replace(
            node_id, P_SUPERSEDED_BY, held[0]["superseded_by"], superseded_by
        )
        self._replace(
            node_id, P_SUPERSEDED_AT, held[0]["superseded_at"], superseded_at
        )
        return 1

    def upsert_relationship_node(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        relationship_type: str,
        subject_uri: str,
        object_uri: str,
        observed_at: str,
    ) -> int:
        scope = self._store.scope(tenant_id)
        partition = scope["partition"]
        node_id = _mint_id(
            _FLUREE_EDGE, partition, tenant_id, relationship_key
        )
        result = self._upsert_node(
            node_id=node_id,
            window_statement=_FLUREE_EDGE_WINDOW,
            window_params={**scope, "key": relationship_key},
            document={
                "@id": node_id,
                "@type": L_EDGE,
                P_PARTITION: partition,
                P_TENANT: tenant_id,
                P_RELATIONSHIP_KEY: relationship_key,
                P_RELATIONSHIP_TYPE: relationship_type,
                P_SUBJECT_URI: subject_uri,
                P_OBJECT_URI: object_uri,
                P_ADMIT_KEY: _RELATIONSHIP_ADMIT_PREFIX + relationship_key,
                P_FIRST_OBSERVED_AT: observed_at,
                P_LAST_OBSERVED_AT: observed_at,
            },
            observed_at=observed_at,
        )
        # The interposed-edge layout (15.3-RESEARCH.md §R5). A CCF relationship
        # is NOT a Cypher relationship here: on this engine a property-reading
        # relationship variable sees only reifier-bundled edges, so a hop
        # predicate stated on `r.prop` returns an empty reached set from a
        # query that answers 200 (Break 1); and the only bounded var-length
        # pattern admitted is a single fixed type, so the CCF type has nowhere
        # to live on the edge either (Break 2). Interposing a node moves both
        # onto node properties, where Cypher reads them reliably.
        #
        # Written ONCE, not doubled: Cypher's `-[:T]-` is first-class
        # undirected, so unlike `$graphLookup` (which follows
        # connectFromField -> connectToField in one direction and forced the
        # Mongo adapter to store every edge forward AND reverse) there is
        # nothing to compose around. Doubling would double the write cost for
        # nothing and create a second place for the layout to be wrong.
        #
        # The two links are maintained here, in the same buffered transaction
        # as the node they join — the layout cannot drift from the edge it
        # represents. Crossability is decided by the read path against the
        # surviving relationship claims, so this node carries identity and
        # endpoints only; it never carries admissibility.
        self._insert.append(
            {
                "@id": node_id,
                LINK_PREDICATE: [
                    {
                        "@id": _mint_id(
                            _FLUREE_ENTITY, partition, tenant_id, subject_uri
                        )
                    },
                    {
                        "@id": _mint_id(
                            _FLUREE_ENTITY, partition, tenant_id, object_uri
                        )
                    },
                ],
            }
        )
        return result

    def insert_relationship_claim(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        claim_id: str,
        claim_json: str,
        observed_at: str,
        policy_bundle_version: str,
    ) -> int:
        scope = self._store.scope(tenant_id)
        partition = scope["partition"]
        buffered = {row[P_CLAIM_ID] for row in self._relationship_claims}
        if claim_id in buffered:
            return 0
        identity: dict[str, object] = {
            **scope,
            "key": relationship_key,
            "claim": claim_id,
        }
        if self._rows(_FLUREE_RELATIONSHIP_CLAIM, identity):
            return 0
        node_id = _mint_id(
            _FLUREE_RELATIONSHIP_CLAIM_KIND,
            partition,
            tenant_id,
            relationship_key,
            claim_id,
        )
        document: dict[str, Any] = {
            "@id": node_id,
            "@type": L_RELATIONSHIP_CLAIM,
            P_PARTITION: partition,
            P_TENANT: tenant_id,
            P_RELATIONSHIP_KEY: relationship_key,
            P_CLAIM_ID: claim_id,
            P_CLAIM_JSON: claim_json,
            P_OBSERVED_AT: observed_at,
            P_POLICY_VERSION: policy_bundle_version,
            # Scoped to `relationship_key` on both terms, for the reason
            # `insert_entity_claim` states in full (review finding WR-07).
            P_SEQ: self._count(
                _FLUREE_RELATIONSHIP_CLAIM_COUNT,
                {**scope, "key": relationship_key},
            )
            + sum(
                1
                for buffered_claim in self._relationship_claims
                if buffered_claim[P_RELATIONSHIP_KEY] == relationship_key
            ),
            **_fluree_claim_projection(claim_json, kind=RELATIONSHIP_KIND),
        }
        self._relationship_claims.append(document)
        self._insert.append(document)
        return 1

    def select_relationship_chain(
        self, *, tenant_id: str, relationship_key: str
    ) -> Sequence[Row]:
        scope = self._store.scope(tenant_id)
        rows: list[dict[str, Any]] = list(
            self._rows(
                _FLUREE_RELATIONSHIP_CHAIN, {**scope, "key": relationship_key}
            )
        )
        rows += [
            {
                "claim_id": document[P_CLAIM_ID],
                "observed_at": document[P_OBSERVED_AT],
                "seq": document[P_SEQ],
            }
            for document in self._relationship_claims
            if document[P_RELATIONSHIP_KEY] == relationship_key
        ]
        rows.sort(key=lambda row: (row["observed_at"], row["seq"]))
        return rows

    def update_relationship_supersession(
        self,
        *,
        tenant_id: str,
        relationship_key: str,
        claim_id: str,
        superseded_by: str | None,
        superseded_at: str | None,
    ) -> int:
        scope = self._store.scope(tenant_id)
        partition = scope["partition"]
        matched = 0
        for document in self._relationship_claims:
            if (
                document[P_CLAIM_ID] == claim_id
                and document[P_RELATIONSHIP_KEY] == relationship_key
            ):
                self._apply_supersession(
                    document,
                    superseded_by=superseded_by,
                    superseded_at=superseded_at,
                )
                matched = 1
        if matched == 1:
            return matched
        held = self._rows(
            _FLUREE_RELATIONSHIP_CLAIM,
            {**scope, "key": relationship_key, "claim": claim_id},
        )
        if not held:
            return 0
        node_id = _mint_id(
            _FLUREE_RELATIONSHIP_CLAIM_KIND,
            partition,
            tenant_id,
            relationship_key,
            claim_id,
        )
        self._replace(
            node_id, P_SUPERSEDED_BY, held[0]["superseded_by"], superseded_by
        )
        self._replace(
            node_id, P_SUPERSEDED_AT, held[0]["superseded_at"], superseded_at
        )
        return 1

    def insert_lineage(
        self,
        *,
        tenant_id: str,
        claim_kind: str,
        node_key: str,
        claim_id: str,
        lineage_id: str,
        entry_json: str,
    ) -> int:
        scope = self._store.scope(tenant_id)
        partition = scope["partition"]
        fingerprint = (tenant_id, claim_kind, node_key, claim_id, lineage_id)
        if fingerprint in self._lineage:
            return 0
        held = self._count(
            _FLUREE_LINEAGE_COUNT,
            {
                **scope,
                "kind": claim_kind,
                "node": node_key,
                "claim": claim_id,
                "lineage": lineage_id,
            },
        )
        if held:
            return 0
        self._lineage.add(fingerprint)
        node_id = _mint_id(
            _FLUREE_LINEAGE,
            partition,
            tenant_id,
            claim_kind,
            node_key,
            claim_id,
            lineage_id,
        )
        self._insert.append(
            {
                "@id": node_id,
                "@type": L_LINEAGE,
                P_PARTITION: partition,
                P_TENANT: tenant_id,
                P_CLAIM_KIND: claim_kind,
                P_NODE_KEY: node_key,
                P_CLAIM_ID: claim_id,
                P_LINEAGE_ID: lineage_id,
                P_ENTRY_JSON: entry_json,
            }
        )
        # The returned integer carries the meaning, not the storage outcome:
        # ignore-on-conflict here IS the L-axis set-union (INV-CH7-17). RDF set
        # semantics would make the re-assertion a data no-op anyway, but the
        # contract needs the number resolved BEFORE commit, which is why the
        # read above is the authority rather than the substrate's behaviour.
        return 1


class FlureeGraphWriter(BaseGraphWriter):
    """The single ``GraphWriter`` over one Fluree graph (plan 15.3-02).

    Same algorithm as every other writer, inherited rather than restated. What
    differs is the transaction: :class:`_FlureeTxn` implements the nine typed
    operations as one buffered JSON-LD batch — no SQL ``ClassVar`` statements
    are set here, exactly as the memory, Neo4j and Mongo backends.
    All-or-nothing on the failure path comes from the buffer: an exception
    drops it, and nothing was applied.

    Note what this docstring does **not** say, where its Mongo and Neo4j twins
    do: *extras-gated*. There is no extra. ``httpx`` is a core pin, so this
    writer needs no optional dependency, no lazy import and no mypy override —
    the SUBQ-14 evidence, visible as an absence.
    """

    def __init__(self, *, store: FlureeGraphStore, token: BootToken) -> None:
        super().__init__(store=store, token=token)
        self._store = store

    @contextmanager
    def _transaction(self) -> Iterator[_GraphTxn]:
        self._check_open()
        txn = _FlureeTxn(store=self._store)
        try:
            yield txn
        except BaseException:
            txn.rollback()
            raise
        else:
            txn.commit()


class FlureeConnection(CCFContract):
    """The connection settings this adapter takes — and it takes no others.

    Plan 15.4-04, D-07. Derives from :class:`~ccf.contracts.base.CCFContract`
    so ``extra="forbid"`` is inherited: a settings key this adapter does not
    declare is refused rather than ignored.

    **The bearer token is deliberately not a field on this model, and it must
    not be added later for convenience** (threat T-15.4-05). Pydantic reports
    ``input_value=`` **verbatim** in a ``ValidationError`` — measured, for
    ``extra_forbidden`` as well as for type errors. So the one case that matters
    is the one that will actually happen: an adopter misspells a connection key
    and puts a live token under the misspelling. If the token were a field on
    this model, the mapping carrying it would be the mapping being validated,
    and the refusal would print the credential into a log, a traceback and an
    error reporter.

    Instead this adapter *names* its credential field in
    :data:`BEARER_TOKEN_FIELD` and in
    :attr:`~ccf.graph.registry.BackendRegistration.secret_fields`, and the
    resolved value travels in the separate ``secrets`` mapping
    :func:`_open_store` receives — a mapping that is never validated and never
    canonicalized. That is the same posture the store itself already takes:
    ``_authorization``'s refusal states that neither credential value appears in
    its message, and ``_graph_identity`` drops userinfo entirely.

    Attributes:
        url: The Fluree server **origin** this fabric's graph lives behind.
            Required: a manifest declaring this adapter and omitting it is
            refused, and the fabric does not fall back. It may carry userinfo,
            which the store converts into an HTTP Basic header rather than
            discarding — the WR-02 fix, unchanged here.
        partition: Which graph in the CCF-owned ledger this store attaches to.
            Optional, and the default stays ``None`` rather than the adapter's
            ``DEFAULT_PARTITION`` because the behaviour to preserve is
            ``_open_backend``'s: an unsupplied partition resolves to the
            adapter's default at construction, in :func:`_open_store`, not on
            the model.
    """

    url: str
    partition: str | None = None


def _open_store(
    config: CCFContract, secrets: Mapping[str, SecretStr]
) -> BackendStore:
    """Construct this adapter's store from validated settings plus credentials.

    Typed against the contract base so it is assignable to
    :attr:`~ccf.graph.registry.BackendRegistration.open_store` under
    ``mypy --strict``, then narrowed.

    The credential is unwrapped **once, at the call site**, and is never bound to
    a name that outlives the call: a :class:`~pydantic.SecretStr` masks itself in
    ``repr``, ``str`` and ``model_dump_json``, and
    :func:`~ccf.contracts.canonical.canonical_bytes` refuses it outright, so the
    only moment the plain value exists is the argument expression below.
    """
    if not isinstance(config, FlureeConnection):
        raise TypeError(
            f"adapter {ADAPTER_NAME!r} takes a {FlureeConnection.__name__},"
            f" got a {type(config).__name__}"
        )
    bearer = secrets.get(BEARER_TOKEN_FIELD)
    return FlureeGraphStore(
        url=config.url,
        partition=(
            config.partition if config.partition is not None else DEFAULT_PARTITION
        ),
        bearer_token=None if bearer is None else bearer.get_secret_value(),
    )


def _make_writer(store: BackendStore, token: BootToken) -> BaseGraphWriter:
    """Construct the write handle — called by the composition root alone."""
    if not isinstance(store, FlureeGraphStore):
        raise TypeError(
            f"adapter {ADAPTER_NAME!r} writes through a"
            f" {FlureeGraphStore.__name__}, got a {type(store).__name__}"
        )
    return FlureeGraphWriter(store=store, token=token)


#: What this adapter declares about itself — the record
#: :func:`ccf.graph.registry.resolve` reads off this module. The one adapter
#: shipped here whose ``secret_fields`` is non-empty.
REGISTRATION = BackendRegistration(
    name=ADAPTER_NAME,
    config_model=FlureeConnection,
    secret_fields=frozenset({BEARER_TOKEN_FIELD}),
    open_store=_open_store,
    make_writer=_make_writer,
)
