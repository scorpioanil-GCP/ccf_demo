"""SQLite reference ``GraphStore`` — schema, connection, and the read path.

Whitepaper §7.3 (the Context Graph as first-class persisted state); DESIGN.md
§2A.5.2 (the D-IMPL-34 semantics) and D-IMPL-02 (SQLite as the development
reference backend, load-bearing for the §9 examples discipline).

**What this module deliberately does not contain: any way to write.**
:class:`SqliteGraphStore` owns the connection and the schema; the read path is
here (as five statements handed to :class:`ccf.graph.reader.BaseGraphReader`);
every ``INSERT`` and every supersession ``UPDATE`` lives in
``ccf.graph._writer``, which the CINV-02 lint confines to ``ccf.assembly`` and
``ccf.boot``. Putting a "convenience" write helper here would hand a write path
to every module that legitimately needs to read (04-RESEARCH.md anti-patterns).

**Physical layout.** Five tables, none of them normative — the whitepaper's
"~10 collections" is reference grounding, not a count to match:

``entities`` / ``relationships``
    Node and edge identity. ``UNIQUE (tenant_id, entity_uri)`` puts compound
    uniqueness *at the persistence tier*, where a concurrent second writer or a
    buggy caller still cannot get around it — application-layer uniqueness
    checks are advisory in a way an index is not (INV-CH7-16).

``entity_claims`` / ``relationship_claims``
    Append-only claim history. Rows are never deleted and their content is
    never updated; the only columns that change after insert are
    ``superseded_by`` / ``superseded_at``, which is what supersession *is*
    (INV-CH7-04, INV-CH7-21). Keeping identity and history in separate tables
    is what lets both "one node per ``(tenant, uri)``" and "every claim ever
    made survives" be true simultaneously.

``lineage``
    Append-only child table keyed on the full lineage-entry identity, giving L
    set-union semantics for free: a re-delivered envelope collides and is
    ignored, a second source does not (INV-CH7-17).

Timestamps are stored as canonical RFC3339 UTC text
(:func:`ccf.contracts.canonical.canonical_timestamp`) so ordering comparisons
in SQL are chronological and so the text a backend stores is the same text the
canonical serializer produces.

Every statement is parameterized. There is no f-string SQL in this module and
none may be added: string-built SQL is how tenant scoping becomes bypassable.
The translated ``GraphQuery`` statements (plan 15.2-09) are *generated*, and
the rule holds for them in the form that matters: statement text is composed
exclusively of code-authored fragments plus ``?`` placeholder repetition sized
by set cardinality — every tenant id, boundary, policy version,
classification, entity URI, seed, JSON path and depth bound travels as a bound
parameter, never as text (threat T-15.2-01). The translated as-of predicates
compare canonical RFC3339 UTC text exactly as the five fixed statements do,
which is what keeps INV-CH7-14 pushable as plain text comparison (`GQ-24` at
docs/GRAPH_QUERY_SEMANTICS.md:482).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterable, Sequence
from pathlib import Path
from types import TracebackType
from typing import ClassVar

from ccf.contracts.canonical import canonical_timestamp
from ccf.graph.protocols import GraphQuery
from ccf.graph.reader import ENTITY_KIND, RELATIONSHIP_KIND, BaseGraphReader, Row

__ccf_mode__ = "algorithmic"

__all__ = ["ENTITY_KIND", "RELATIONSHIP_KIND", "SqliteGraphReader", "SqliteGraphStore"]

_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS entities (
        tenant_id TEXT NOT NULL,
        entity_uri TEXT NOT NULL,
        entity_class TEXT NOT NULL,
        first_observed_at TEXT NOT NULL,
        last_observed_at TEXT NOT NULL,
        UNIQUE (tenant_id, entity_uri)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS entity_claims (
        tenant_id TEXT NOT NULL,
        entity_uri TEXT NOT NULL,
        claim_id TEXT NOT NULL,
        claim_json TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        policy_bundle_version TEXT NOT NULL,
        superseded_by TEXT,
        superseded_at TEXT,
        PRIMARY KEY (tenant_id, entity_uri, claim_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS relationships (
        tenant_id TEXT NOT NULL,
        relationship_key TEXT NOT NULL,
        relationship_type TEXT NOT NULL,
        subject_uri TEXT NOT NULL,
        object_uri TEXT NOT NULL,
        first_observed_at TEXT NOT NULL,
        last_observed_at TEXT NOT NULL,
        UNIQUE (tenant_id, relationship_key)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS relationship_claims (
        tenant_id TEXT NOT NULL,
        relationship_key TEXT NOT NULL,
        claim_id TEXT NOT NULL,
        claim_json TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        policy_bundle_version TEXT NOT NULL,
        superseded_by TEXT,
        superseded_at TEXT,
        PRIMARY KEY (tenant_id, relationship_key, claim_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS lineage (
        tenant_id TEXT NOT NULL,
        claim_kind TEXT NOT NULL,
        node_key TEXT NOT NULL,
        claim_id TEXT NOT NULL,
        lineage_id TEXT NOT NULL,
        entry_json TEXT NOT NULL,
        PRIMARY KEY (tenant_id, claim_kind, node_key, claim_id, lineage_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_entity_claims_observed
        ON entity_claims (tenant_id, observed_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_relationship_claims_observed
        ON relationship_claims (tenant_id, observed_at)
    """,
)


class SqliteGraphStore:
    """Connection and schema owner for the SQLite reference backend.

    Args:
        database_path: File to open. A distinct path per fabric is what makes
            "one writer per graph" a checkable statement at boot.

    The store is *not* a ``GraphStore`` in the sense of offering both halves of
    the Protocol: it offers :attr:`reader` and, to the writer module alone, the
    connection. See the module docstring.
    """

    def __init__(self, *, database_path: Path | str) -> None:
        self._database_path = str(database_path)
        self._connection = sqlite3.connect(self._database_path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA foreign_keys = ON")
        with self._connection:
            for statement in _SCHEMA:
                self._connection.execute(statement)
        self._reader = SqliteGraphReader(self._connection)

    @property
    def graph_identity(self) -> str:
        """Stable identity of the persisted graph this store is attached to.

        The single-writer boot check keys on this: two writers over two
        different databases are two fabrics, while two writers over the same
        database are the violation.
        """
        return self._database_path

    @property
    def reader(self) -> SqliteGraphReader:
        """The read-only view of this graph — safe to hand to anyone."""
        return self._reader

    @property
    def connection(self) -> sqlite3.Connection:
        """The raw connection.

        Reachable in principle by any importer, which is why the write
        *statements* — not merely the handle — live behind the CINV-02 lint.
        The honest claim is DESIGN.md §9's: no unforced path exists, and every
        forced path fails CI or fails at boot.
        """
        return self._connection

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> SqliteGraphStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


# --- GraphQuery translation (plan 15.2-09) -----------------------------------
#
# The native pushdown path: `_translated_statements` renders one GraphQuery as
# two SQL statements — surviving entity claims and surviving relationship
# claims — that together constitute the whole answer's row set, per the
# all-or-nothing hook contract (`GQ-32` at docs/GRAPH_QUERY_SEMANTICS.md:583).
# The statements share one WITH chain and one parameter tuple; only the outer
# SELECT differs. Both feed `ccf.graph.reader.materialize_view` exactly as the
# five fixed statements do, so lineage-at-boundary and supersession-as-of stay
# rendered in the one shared place (INV-CH7-14).

#: The charset under which an attribute name maps 1:1 onto a JSON path step.
_ATTRIBUTE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")

#: A constant-false predicate: SQL has no empty IN list, and an empty set
#: admits nothing.
_FALSE = "0 = 1"

#: The six answer columns, aliased from the survivors CTE.
_ENTITY_ANSWER = (
    "SELECT s.entity_uri, s.claim_id, s.claim_json, s.policy_bundle_version,\n"
    "       s.superseded_by, s.superseded_at\n"
    "FROM survivors s\n"
)

#: The six answer columns, aliased from the edges CTE.
_RELATIONSHIP_ANSWER = (
    "SELECT c.relationship_key, c.claim_id, c.claim_json,\n"
    "       c.policy_bundle_version, c.superseded_by, c.superseded_at\n"
    "FROM edges c\n"
)

#: The undirected step: whichever endpoint of the joined crossable edge is
#: not the walk row's own node (`GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201
#: — an edge is crossable in either direction).
_REACHED = (
    "CASE WHEN c.subject_uri = w.uri THEN c.object_uri ELSE c.subject_uri END"
)


def _json_attribute_path(attribute: str) -> str | None:
    """The ONE site where an artifact-authored attribute name becomes a path.

    Plan 15.2-09 identifier/path safety: classification attribute names are
    ARTIFACT-AUTHORED data, never SQL. The whole path is bound as a ``?``
    parameter to ``json_extract`` — the name never enters statement text —
    but a name outside the ``^[A-Za-z0-9_-]+$`` charset would change the
    *path semantics* (``$.attributes.a.b`` names a nested key, not the
    literal key ``a.b``), silently diverging from the fallback's
    ``attributes.get(name)``. Such a name declines translation: the hook
    returns ``None`` and the fallback answers the whole query instead
    (`GQ-32` at docs/GRAPH_QUERY_SEMANTICS.md:583) — byte-identical under
    D-04, visible only in telemetry.
    """
    if _ATTRIBUTE_NAME.fullmatch(attribute) is None:
        return None
    return "$.attributes." + attribute


def _placeholders(count: int) -> str:
    """A generated ``?`` list of ``count`` members — structure, never values."""
    return ", ".join(["?"] * count)


def _in_clause(
    expression: str, values: Iterable[str]
) -> tuple[str, tuple[str, ...]]:
    """``expression IN (?, ...)`` with sorted bound values; empty is false.

    Set members are always values, never text (threat T-15.2-01): the
    fragment carries generated placeholders only, and the members return as
    parameters. Sorting makes the rendered statement a deterministic
    function of the query value.
    """
    ordered = tuple(sorted(values))
    if not ordered:
        return _FALSE, ()
    return expression + " IN (" + _placeholders(len(ordered)) + ")", ordered


def _utc_fixed_width(expression: str) -> str:
    """Normalize a claim-JSON timestamp rendering to fixed-width UTC text.

    Claim JSON renders UTC datetimes with a ``Z`` suffix and either no
    fractional part (whole seconds) or exactly six fractional digits — two
    widths that do NOT compare chronologically against the fixed-width
    canonical boundary (``...05Z`` sorts *after* ``...05.000000Z``). This
    expression widens the whole-second form so both compare as canonical
    text (`GQ-24` at docs/GRAPH_QUERY_SEMANTICS.md:482). A rendering that
    is not ``Z``-suffixed (a claim authored with a non-UTC offset — legal
    at the contract tier) yields NULL, and NULL fails every comparison:
    the pushed predicate is fail-closed on state it cannot chronologically
    order as text, never over-disclosing (threats T-15.2-03/T-15.2-26).
    """
    return (
        "CASE WHEN substr(" + expression + ", -1, 1) = 'Z'"
        " THEN CASE WHEN instr(" + expression + ", '.') > 0"
        " THEN " + expression
        + " ELSE replace(" + expression + ", 'Z', '.000000Z') END END"
    )


def _validity_clauses(
    prefix: str, json_column: str, boundary: str
) -> tuple[str, tuple[str, str]]:
    """The validity-window cut over the claim's own JSON fields.

    `GQ-09` at docs/GRAPH_QUERY_SEMANTICS.md:185: when the temporal family
    requires validity at the boundary, a record additionally survives only
    if ``valid_from <= as_of AND (valid_to IS NULL OR valid_to > as_of)``
    — cut 3 of the in-process temporal operator (INV-CH7-25), pushed as
    canonical-text comparison over the width-normalized renderings.
    """
    valid_from = "json_extract(" + json_column + ", '$.valid_from')"
    valid_to = "json_extract(" + json_column + ", '$.valid_to')"
    text = (
        prefix + "AND " + _utc_fixed_width(valid_from) + " <= ?\n"
        + prefix + "AND (" + valid_to + " IS NULL OR "
        + _utc_fixed_width(valid_to) + " > ?)\n"
    )
    return text, (boundary, boundary)


def _translated_statements(
    q: GraphQuery,
) -> tuple[str, str, tuple[object, ...]] | None:
    """Render ``q`` as the two whole-answer statements, or decline.

    Returns ``(entity_sql, relationship_sql, params)`` — both statements
    share one WITH chain and one positional parameter tuple — or ``None``
    when a classification attribute name falls outside the safe path
    charset (see :func:`_json_attribute_path`), in which case the fallback
    answers (`GQ-32` at docs/GRAPH_QUERY_SEMANTICS.md:583; D-04).
    """
    boundary = canonical_timestamp(q.as_of)
    policy_versions = q.permitted_policy_bundle_versions
    attribute_by_class = q.classification_attribute_by_class
    classifications = q.permitted_classifications
    # Constraint presence gates endpoint closure exactly as the fallback's
    # step 4 does: any family present, or `allowed_entities` non-None. The
    # degenerate everything-question is exempt — its answer keeps dangling
    # first-class edges (`GQ-05` at docs/GRAPH_QUERY_SEMANTICS.md:122;
    # `GQ-21` at docs/GRAPH_QUERY_SEMANTICS.md:446).
    constrained = (
        q.allowed_entities is not None
        or policy_versions is not None
        or q.require_valid_at_boundary is not None
        or q.traverse is not None
    )
    require_validity = q.require_valid_at_boundary is True

    text: list[str] = []
    params: list[object] = []

    # survivors: the surviving entity claims. The as-of cut is INV-CH7-14
    # rendered at the query tier (`GQ-07` at docs/GRAPH_QUERY_SEMANTICS.md:148)
    # over the canonical-text observed_at / superseded_at columns; the
    # remaining families narrow within it.
    # MATERIALIZED (SQLite 3.35+; well below the Python 3.12 floor's era)
    # removes planner discretion: each CTE computes once per statement, so
    # the walk's recursive term expands over a computed row set rather than
    # re-evaluating a subquery per candidate row — the difference between a
    # bounded walk and a combinatorial re-scan on demo-scale graphs.
    text.append("survivors AS MATERIALIZED (\n")
    text.append(
        "    SELECT ec.entity_uri, ec.claim_id, ec.claim_json,\n"
        "           ec.policy_bundle_version, ec.superseded_by,\n"
        "           ec.superseded_at\n"
        "    FROM entity_claims ec\n"
        "    WHERE ec.tenant_id = ?\n"
        "      AND ec.observed_at <= ?\n"
        "      AND (ec.superseded_at IS NULL OR ec.superseded_at > ?)\n"
    )
    params += [q.tenant_id, boundary, boundary]
    if require_validity:
        clause, bound = _validity_clauses("      ", "ec.claim_json", boundary)
        text.append(clause)
        params += list(bound)
    if policy_versions is not None:
        # Policy admissibility, all three cuts of `GQ-08` at
        # docs/GRAPH_QUERY_SEMANTICS.md:163 (INV-CH7-26): a permitted bundle
        # version; a class with a declared classification attribute — a
        # class with none is inadmissible, so admissibility is an OR over
        # the declared classes; and a permitted value of that attribute —
        # json_extract answers NULL for an absent attribute, and NULL is
        # never IN a permitted set, so "carries no value" is inadmissible.
        assert attribute_by_class is not None  # noqa: S101 - GQ-02 whole family
        assert classifications is not None  # noqa: S101 - GQ-02 whole family
        clause, values = _in_clause("ec.policy_bundle_version", policy_versions)
        text.append("      AND " + clause + "\n")
        params += list(values)
        alternatives: list[str] = []
        if classifications:
            for entity_class in sorted(attribute_by_class):
                path = _json_attribute_path(attribute_by_class[entity_class])
                if path is None:
                    return None
                alternatives.append(
                    "(json_extract(ec.claim_json, '$.entity_class') = ?"
                    " AND json_extract(ec.claim_json, ?) IN ("
                    + _placeholders(len(classifications))
                    + "))"
                )
                params += [entity_class, path, *sorted(classifications)]
        if alternatives:
            text.append(
                "      AND ("
                + "\n           OR ".join(alternatives)
                + ")\n"
            )
        else:
            text.append("      AND " + _FALSE + "\n")
    if q.allowed_entities is not None:
        # The uniform rule's set membership on entity selection (`GQ-15` at
        # docs/GRAPH_QUERY_SEMANTICS.md:300): every family computes within
        # the survivor set, restricted before anything else evaluates. The
        # set travels natively as generated placeholders (`GQ-30` at
        # docs/GRAPH_QUERY_SEMANTICS.md:563); a temp-table strategy is a
        # documented adapter-internal alternative for very large sets, not
        # required for conformance — the Control Plane cap (`GQ-18`)
        # governs set size upstream of this statement.
        clause, values = _in_clause("ec.entity_uri", q.allowed_entities)
        text.append("      AND " + clause + "\n")
        params += list(values)
    text.append(")")

    # edges: the surviving relationship claims that may appear in the answer
    # — and, on a traverse query, the walk's whole expansion surface: the
    # relationship_claims join carries the as-of predicate (INV-CH7-14;
    # `GQ-07` at docs/GRAPH_QUERY_SEMANTICS.md:148) plus the segment's
    # validity and policy predicates when present, and endpoint closure
    # below restricts crossability to edges between surviving entities.
    text.append(",\nedges AS MATERIALIZED (\n")
    text.append(
        "    SELECT rc.relationship_key, rc.claim_id, rc.claim_json,\n"
        "           rc.policy_bundle_version, rc.superseded_by,\n"
        "           rc.superseded_at, r.subject_uri, r.object_uri\n"
        "    FROM relationship_claims rc\n"
        "    JOIN relationships r\n"
        "      ON r.tenant_id = ?\n"
        "     AND r.relationship_key = rc.relationship_key\n"
        "    WHERE rc.tenant_id = ?\n"
        "      AND rc.observed_at <= ?\n"
        "      AND (rc.superseded_at IS NULL OR rc.superseded_at > ?)\n"
    )
    params += [q.tenant_id, q.tenant_id, boundary, boundary]
    if require_validity:
        clause, bound = _validity_clauses("      ", "rc.claim_json", boundary)
        text.append(clause)
        params += list(bound)
    if policy_versions is not None:
        # A relationship is admissible under the policy family iff its
        # bundle version is permitted (`GQ-08` at
        # docs/GRAPH_QUERY_SEMANTICS.md:163) — no classification cut of its
        # own; endpoint survival governs its exposure below.
        clause, values = _in_clause("rc.policy_bundle_version", policy_versions)
        text.append("      AND " + clause + "\n")
        params += list(values)
    if q.allowed_entities is not None:
        # The induced-subgraph rule (`GQ-16` at
        # docs/GRAPH_QUERY_SEMANTICS.md:316): both endpoints members of the
        # set, stated natively on the edge's own columns.
        clause, values = _in_clause("r.subject_uri", q.allowed_entities)
        text.append("      AND " + clause + "\n")
        params += list(values)
        clause, values = _in_clause("r.object_uri", q.allowed_entities)
        text.append("      AND " + clause + "\n")
        params += list(values)
    if q.traverse is not None:
        # Typed crossability doubles as answer membership: edges of other
        # types are absent even between reached endpoints (`GQ-10` at
        # docs/GRAPH_QUERY_SEMANTICS.md:201).
        clause, values = _in_clause(
            "r.relationship_type", q.traverse.relationship_types
        )
        text.append("      AND " + clause + "\n")
        params += list(values)
    if constrained:
        # Endpoint closure against the surviving universe (`GQ-16` at
        # docs/GRAPH_QUERY_SEMANTICS.md:316, INV-CH7-40): an answer view
        # never retains an edge to a node its principal may not see. The
        # degenerate everything-question skips this — a dangling
        # first-class edge is state, not a leak, in the unconstrained
        # answer (`GQ-05` at docs/GRAPH_QUERY_SEMANTICS.md:122).
        text.append(
            "      AND EXISTS (SELECT 1 FROM survivors s\n"
            "                  WHERE s.entity_uri = r.subject_uri)\n"
            "      AND EXISTS (SELECT 1 FROM survivors s\n"
            "                  WHERE s.entity_uri = r.object_uri)\n"
        )
    text.append(")\n")

    if q.traverse is not None:
        # hops: the crossable set stated ONCE per direction, so the walk's
        # recursive term can find its next hops by EQUALITY on the walk row's
        # own node. `GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201 makes an edge
        # crossable in either direction, and the natural rendering of that —
        # `JOIN edges c ON (c.subject_uri = w.uri OR c.object_uri = w.uri)` —
        # is a disjunction SQLite cannot serve from an index, so every step of
        # the walk re-scanned the whole crossable set: |walk| x |edges| row
        # comparisons, quadratic in the segment's own answer. Pre-symmetrizing
        # is the same relation written so an equality join can index it; the
        # UNION (never UNION ALL) makes a self-loop's two renderings one row,
        # exactly as the disjunction's single match did. The reached-node
        # expression below is unchanged and still reads as the general
        # undirected step: under this join its CASE simply always takes the
        # `object_uri` branch.
        text.append(",\nhops(subject_uri, object_uri) AS MATERIALIZED (\n")
        text.append(
            "    SELECT c.subject_uri, c.object_uri FROM edges c\n"
            "  UNION\n"
            "    SELECT c.object_uri, c.subject_uri FROM edges c\n"
            ")\n"
        )
        # The bounded typed undirected walk (`GQ-10` at
        # docs/GRAPH_QUERY_SEMANTICS.md:201, INV-CH7-24). Walk starting
        # points are the union of seed-class selection and explicit seeds,
        # computed over survivors only (`GQ-11` at
        # docs/GRAPH_QUERY_SEMANTICS.md:221) — so starts satisfy every
        # segment predicate and, when `allowed_entities` is present, sit
        # inside the set (seed classes select within it; explicit seeds
        # intersect with it, and a URI naming nothing in scope contributes
        # no start). depth_limit=0 is the base case alone: the walk
        # starting points only, a legal bound and not an error.
        text.append(",\nwalk(uri, depth) AS (\n")
        text.append(
            "    SELECT s.entity_uri, 0\n"
            "    FROM survivors s\n"
            "    WHERE "
        )
        starts: list[str] = []
        clause, values = _in_clause(
            "json_extract(s.claim_json, '$.entity_class')",
            q.traverse.seed_entity_classes,
        )
        starts.append(clause)
        params += list(values)
        if q.seeds:
            clause, values = _in_clause("s.entity_uri", q.seeds)
            starts.append(clause)
            params += list(values)
        text.append("(" + " OR ".join(starts) + ")\n")
        # The recursive term: hop admissibility enforced on every hop, not
        # on the result set (`GQ-13` at docs/GRAPH_QUERY_SEMANTICS.md:261,
        # INV-CH7-40). The expansion surface is the materialized crossable
        # set above — relationship_claims joined with the as-of predicate,
        # the segment's validity and policy predicates, the permitted
        # types, and BOTH endpoints surviving — so an edge to an excluded
        # node is not a hop the walk can take, and a path through an
        # excluded node does not exist. Prune before walking, exactly the
        # fallback's shape. The expansion surface is reached through `hops`,
        # which is that same set with each edge stated in both directions —
        # every predicate above still governs it, because `hops` is derived
        # from `edges` and adds no row of its own.
        text.append(
            "  UNION\n"
            "    SELECT " + _REACHED + ",\n"
            "           w.depth + 1\n"
            "    FROM walk w\n"
            "    JOIN hops c\n"
            "      ON c.subject_uri = w.uri\n"
            "    WHERE w.depth < ?\n"
        )
        # Depth is a bound parameter in SQL — the literal-inlining
        # exception is Cypher-only (plan 15.2-09).
        params.append(q.traverse.depth_limit)
        if q.allowed_entities is not None:
            # The uniform rule inside the recursive term (`GQ-15` at
            # docs/GRAPH_QUERY_SEMANTICS.md:300): a hop to an out-of-set
            # node must not extend the walk — the D-IMPL-87 resurrection
            # defect closed in SQL. The crossable set's endpoint predicates
            # already imply membership (survivors are restricted to the
            # set); this predicate states it on the reached node itself, so
            # the closure is explicit in the term that expands the walk.
            clause, values = _in_clause(_REACHED, q.allowed_entities)
            text.append("      AND " + clause + "\n")
            params += list(values)
        if q.traverse.admitted_entity_classes is not None:
            # Node-class admission on the REACHED node, honored natively
            # (`GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201, semantics
            # version 1.1.0; ledger row 24.5-L-05): a hop lands only on a
            # survivor whose class is admitted. Stated inside the recursive
            # term so a path through an unadmitted node does not exist, and
            # never on the base case — starts are selected by `GQ-11` and
            # are not filtered by admission. The class list binds as
            # parameters, appended in the same order the seed-class binder
            # appends (threat T-24.5-10); an empty set renders the always-
            # false clause, so no hop is admitted and the starts answer.
            clause, values = _in_clause(
                "json_extract(a.claim_json, '$.entity_class')",
                q.traverse.admitted_entity_classes,
            )
            text.append(
                "      AND " + _REACHED + " IN (\n"
                "        SELECT a.entity_uri FROM survivors a\n"
                "        WHERE " + clause + ")\n"
            )
            params += list(values)
        text.append(")\n")

    prologue = "WITH RECURSIVE " if q.traverse is not None else "WITH "
    with_chain = prologue + "".join(text)

    entity_answer = _ENTITY_ANSWER
    relationship_answer = _RELATIONSHIP_ANSWER
    if q.traverse is not None:
        # The traverse answer: reached entities, and the permitted-type
        # surviving edges among them (`GQ-10` at
        # docs/GRAPH_QUERY_SEMANTICS.md:201).
        entity_answer += "WHERE s.entity_uri IN (SELECT uri FROM walk)\n"
        relationship_answer += (
            "WHERE c.subject_uri IN (SELECT uri FROM walk)\n"
            "  AND c.object_uri IN (SELECT uri FROM walk)\n"
        )
    entity_answer += "ORDER BY s.entity_uri"
    relationship_answer += "ORDER BY c.relationship_key"
    return (
        with_chain + entity_answer,
        with_chain + relationship_answer,
        tuple(params),
    )


class SqliteGraphReader(BaseGraphReader):
    """``GraphReader`` over a SQLite connection — dialect and rows only.

    The bitemporal rendering rules live in
    :class:`ccf.graph.reader.BaseGraphReader`; what is here is the SQLite
    dialect of the five reads and the connection they run on. ``rowid`` is the
    insertion-order tiebreak within one observed-time instant, which is what
    keeps history ordering total rather than merely chronological.

    Since plan 15.2-09 the reader also holds a native ``GraphQuery``
    translation: :meth:`_translate_query` answers whole queries by generated
    SQL — as-of + policy + validity predicates, ``allowed_entities``
    membership, and bounded undirected traversal via recursive CTE — and the
    differential suite holds the translated answers byte-identical to the
    fallback (`GQ-31` at docs/GRAPH_QUERY_SEMANTICS.md:573).
    """

    # The bitemporal read. `observed_at <= ?` excludes what the fabric had not
    # yet learned at the read boundary; the supersession clause keeps a claim
    # current until the instant it was superseded. Together: no future
    # information leaks into a historical view (INV-CH7-14).
    SELECT_LINEAGE: ClassVar[str] = """
        SELECT entry_json FROM lineage
        WHERE tenant_id = ? AND claim_kind = ? AND node_key = ? AND claim_id = ?
    """
    SELECT_ENTITY_HISTORY: ClassVar[str] = """
        SELECT entity_uri, claim_id, claim_json, policy_bundle_version,
               superseded_by, superseded_at
        FROM entity_claims
        WHERE tenant_id = ? AND entity_uri = ?
        ORDER BY observed_at, rowid
    """
    SELECT_RELATIONSHIP_HISTORY: ClassVar[str] = """
        SELECT relationship_key, claim_id, claim_json, policy_bundle_version,
               superseded_by, superseded_at
        FROM relationship_claims
        WHERE tenant_id = ? AND relationship_key = ?
        ORDER BY observed_at, rowid
    """
    SELECT_ENTITIES_AS_OF: ClassVar[str] = """
        SELECT entity_uri, claim_id, claim_json, policy_bundle_version,
               superseded_by, superseded_at
        FROM entity_claims
        WHERE tenant_id = ?
          AND observed_at <= ?
          AND (superseded_at IS NULL OR superseded_at > ?)
        ORDER BY entity_uri
    """
    SELECT_RELATIONSHIPS_AS_OF: ClassVar[str] = """
        SELECT relationship_key, claim_id, claim_json, policy_bundle_version,
               superseded_by, superseded_at
        FROM relationship_claims
        WHERE tenant_id = ?
          AND observed_at <= ?
          AND (superseded_at IS NULL OR superseded_at > ?)
        ORDER BY relationship_key
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def _query(self, sql: str, params: tuple[object, ...]) -> Sequence[Row]:
        return self._connection.execute(sql, params).fetchall()

    def _translate_query(
        self, q: GraphQuery
    ) -> tuple[Sequence[Row], Sequence[Row]] | None:
        """Answer the whole query natively, or decline (plan 15.2-09).

        The hook contract is all-or-nothing (`GQ-32` at
        docs/GRAPH_QUERY_SEMANTICS.md:583): a non-``None`` return is the
        complete answer's row pair — every predicate family applied, hop
        admissibility applied, ``allowed_entities`` membership applied —
        and ``None`` hands the whole query to the fallback, which D-04
        makes byte-identical and invisible outside telemetry. This
        translation covers every well-formed query shape; the one decline
        is a classification attribute name outside the safe JSON-path
        charset (:func:`_json_attribute_path`). ``admitted_entity_classes``
        (`GQ-10` at docs/GRAPH_QUERY_SEMANTICS.md:201, 1.1.0) is HONORED
        natively — a class predicate on the reached survivor inside the
        recursive walk term, the classes bound as parameters.
        """
        if q.allowed_entities is not None and not q.allowed_entities:
            # The empty survivor set IS the answer (`GQ-04` at
            # docs/GRAPH_QUERY_SEMANTICS.md:98): the empty view, answered
            # here without a substrate round trip. An empty answer is an
            # answer, never an error (`GQ-23` at
            # docs/GRAPH_QUERY_SEMANTICS.md:474).
            return (), ()
        statements = _translated_statements(q)
        if statements is None:
            return None
        entity_sql, relationship_sql, params = statements
        return (
            self._query(entity_sql, params),
            self._query(relationship_sql, params),
        )
