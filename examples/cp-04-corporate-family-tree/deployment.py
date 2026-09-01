"""What this deployment KNOWS: its two estates, its vocabulary, and this question's values.

[ADAPT] all of it. [MECHANISM] nothing — every CCF call is in ``produce.py``.

**THE SEAM.** ``produce.py`` is the fabric's call spine and names no store, no
predicate, no table and no domain word. This module names all of them and makes
no fabric call. It hands the spine a ``FamilyScenario`` carrying this question's
answers.

**WHAT THIS PRODUCT IS.** One company's corporate family, as a tree of typed
parent-to-child edges, with every member's FIBO class chain beside it, its
attributes where an attribute row exists, and the cycles and duplicate
identities the family contains served as findings BESIDE the tree rather than
as flags upon it.

**TWO STORES, AND THIS IS THE FIRST RUNG THAT OPENS TWO.** Fluree is
authoritative for the edges and for the ontology; PostgreSQL is authoritative
for entity attributes. Neither duplicates the other's authority and neither is
a read replica of the other. ``CFT-G10`` asserts the split at runtime and is
sabotaged by serving attributes out of Fluree, which is exactly the shape a
well-meaning optimization would take.

**FIBO-V2 IS A SYSTEM OF RECORD READ AT INGRESS. IT IS NOT THIS FABRIC'S L3,
AND THE DISTINCTION IS THE ONE A READER IS MOST LIKELY TO GET WRONG HERE.**

The fabric's own Context Graph for this example is the SQLite backend
``ccf_config.yaml`` declares — a fresh per-run file, exactly as at rungs 00
through 03 — and ``booted.handle.worker`` is the ONLY write handle to it
anywhere in this process (single-writer, CLAUDE.md section 10). Both source
reads below are ``SELECT``-shaped and read-only: this module issues
``/v1/fluree/query`` and nothing else on the graph leg, and ``SELECT`` and
nothing else on the attribute leg. Nothing here can write to either estate, and
nothing in either estate is a second writer to L3.

``src/ccf/graph/backends/fluree.py`` is the SDK's Fluree ``GraphStore`` — the
adapter for a **CCF-OWNED** ledger holding ``CcfEntity`` and ``CcfEdge`` nodes
in the adapter's own physical model. It is deliberately **not** on this path.
``fibo-v2`` is a foreign RDF dataset in somebody else's vocabulary; reading it
through an adapter that expects CCF's own layout would return nothing from a
syntactically valid query, which is the failure mode that adapter's own
docstring records against Cypher relationship properties. This leg speaks
SPARQL to a foreign store, and the fabric's own graph is a different store
under a different contract.

**THE NO-HARDCODING RULE BITES HARDEST HERE** (CLAUDE.md section 6.4). This
module works with six predicates, two class vocabularies, two connection seams,
a depth ceiling, a depth default and a set of refusals, and **every one of them
arrives from a document**:

* the six family predicates' short names come from ``ccf_config.yaml``'s
  ``operators.traversal.typed-neighborhood.relationship_types``;
* their IRIs, their per-predicate arrow and their half-life signal class come
  from ``artifacts/source-vocabulary.yaml``;
* the walk's seed classes, the depth ceiling and the declared default come from
  ``ccf_config.yaml``;
* the anchor, the pinned instant and the demonstration parameters come from
  ``artifacts/question.yaml``;
* the refusals come from ``ccf_config.yaml``'s ``request_contract`` block; and
* every connection value comes from an environment variable **named** by
  ``backends.yaml``, which itself holds no host, port, path or credential.

A predicate this product stops walking, or starts; a column it stops serving; a
depth it stops accepting — each is an edit to a document and none is an edit to
this file.

**THE INGEST BOUND AND THE CALLER'S BOUND ARE TWO DIFFERENT BOUNDS.** The
source read takes the anchor's reachable component to the DECLARED CEILING; the
L4 operator then applies the CALLER's ``max_depth`` over what was ingested.
:func:`traversal_parameters` is where the caller's depth enters the operator
parameter set, and therefore the content address. See that function for why
pushing the caller's depth into the SPARQL instead would be a defect rather
than an optimization.

**WHAT THIS MODULE DOES NOT YET CARRY, AND WHY — READ THIS BEFORE USING IT.**

Two things the plan for this file asked for are **deliberately absent**, because
building either would have required deciding a question that is open in this
product's own Control Plane document. Both are named here rather than left as a
gap somebody discovers by reading a stack trace:

1. **The L1 envelopes.** ``ccf_config.yaml``'s ``resolution`` block declares two
   entity rules whose ``identity_keys`` are both ``[entity_uri]``, plus twelve
   relationship rules. ``src/ccf/assembly/worker.py::AssemblyWorker`` mints a
   relationship claim by **co-occurrence** — every declared rule whose subject
   and object classes BOTH resolve from one envelope fires — so one envelope
   carrying one ``entity_uri`` mints the same node under both classes and then
   emits six edges between those two, one per declared type. There is no
   payload-selected relationship type, and a member-to-member edge cannot be
   minted at all, because one envelope resolves at most one ``family_member``.
   The declared spec therefore cannot express a typed parent-to-child edge.
   Measured, not reasoned: see this plan's summary.
2. **The policy classification.** ``policy.principal-subgraph`` classifies both
   entity classes on ``entity_jurisdiction`` and
   ``src/ccf/operators/categories.py::PolicyFilter`` refuses a record whose
   classification attribute is ABSENT as firmly as one whose value is outside
   the grant. Measured against the estate, the declared
   ``permitted_classifications`` admits **78 of 748** family nodes and **2 of
   the SMCI subtree's 22**. The other 20 carry no PostgreSQL row and therefore
   no ``entity_jurisdiction``, and they are precisely the population
   ``CFT-G09`` and criterion 33 protect.

Everything else this module was asked for is here and is exercised against the
live estate: both connection seams, the bounded walk, the whole-ledger
enumeration, the normalization with its per-predicate arrow, the cycle detector
with its rotation convention, the duplicate-identity finding, the ONE batched
attribute read, and every refusal.
"""

from __future__ import annotations

import os
import re
import uuid
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import httpx
import psycopg
import yaml

from ccf.controlplane.artifacts import OperatorParametersArtifact
from ccf.products.request import ProductRequest
from ccf.projection.plan import Perspective

HERE = Path(__file__).parent
ARTIFACTS = HERE / "artifacts"

CONFIG = HERE / "ccf_config.yaml"
BACKENDS = HERE / "backends.yaml"
QUESTION = ARTIFACTS / "question.yaml"
TTL = ARTIFACTS / "ttl.yaml"
RECIPE = ARTIFACTS / "assembly-recipe.yaml"
SOURCE_VOCABULARY = ARTIFACTS / "source-vocabulary.yaml"
#: The declared expectation. It is READ BY THE GATES and by nothing on the
#: serving path — a deployment that consulted its own expectations would be
#: agreeing with itself rather than being held to them.
EXPECTED = ARTIFACTS / "expected.yaml"
SPEC = HERE / "spec" / "CP-SPEC-004_Corporate_Family_Tree.md"

DECLARATION = "declaration"
PROFILES = "profiles"
SOURCES = "sources"
SETTINGS = "settings"
FROM_ENV = "from_env"
REMEDY = "remedy"
PER_RUN = "per_run"
PER_RUN_PATH = "path"
PREFIX = "prefix"
SUFFIX = "suffix"

KEY_BACKEND = "backend"
KEY_TENANT = "tenant_id"
KEY_PERSPECTIVE = "default_perspective"
KEY_PRODUCT_CLASS = "product_class"
KEY_REQUEST_CONTRACT = "request_contract"
KEY_OPERATORS = "operators"
KEY_TRAVERSAL_OPERATOR = "traversal.typed-neighborhood"

#: The two source bindings `backends.yaml` declares, each for its own thing.
#: `CFT-G10` asserts the split; serving an attribute out of the graph leg is
#: its sabotage.
SOURCE_GRAPH = "corporate_family_graph"
SOURCE_ATTRIBUTES = "corporate_family_attributes"
SETTING_URL = "url"
SETTING_LEDGER = "ledger"
SETTING_DSN = "dsn"
SETTING_SCHEMA = "schema"

#: `artifacts/source-vocabulary.yaml`'s own keys.
VOCAB_GRAPH = "graph"
VOCAB_ATTRIBUTES = "attributes"
VOCAB_FAMILY_PREDICATES = "family_predicates"
VOCAB_NODE_PREDICATES = "node_predicates"
VOCAB_DUPLICATE = "duplicate_identity"
VOCAB_IRI = "iri"
VOCAB_DIRECTION = "direction"
VOCAB_SIGNAL_CLASS = "signal_class"
VOCAB_TABLE = "table"
VOCAB_KEY_COLUMN = "key_column"
VOCAB_SERVED_COLUMNS = "served_columns"
VOCAB_REFUSE_EMPTY_FOLD = "refuse_empty_fold"

NODE_PREDICATE_LEI = "lei"
NODE_PREDICATE_LABEL = "label"
NODE_PREDICATE_TYPE_CHAIN = "type_chain"

#: The two readings a family predicate can carry. **The arrow is the whole
#: game** (spec section C.4 trap 1): reversing exactly one of the six moves the
#: family graph's root count off 83, and a bare COUNT is blind to an arrow —
#: which is how 139 GLEIF edges stayed inverted for seven waves with every
#: check green. The values are compared against the artifact's, never authored
#: as a default: a predicate declaring neither fails closed.
DIRECTION_SUBJECT_TO_OBJECT = "subject_to_object"
DIRECTION_OBJECT_TO_SUBJECT = "object_to_subject"

#: This product's finding vocabulary. Findings are ORTHOGONAL to the tree
#: (`D-12`): a cycle is a SET PLUS THE EDGE THAT CLOSES IT, never a bit on a
#: node, and the closing edge is precisely what a flattened representation
#: loses. `CFT-G08` is sabotaged by flagging cycle membership onto the nodes,
#: which destroys the closing edge while every node count stays right.
FINDING_OWNERSHIP_CYCLE = "ownership_cycle"
FINDING_DUPLICATE_ENTITY = "duplicate_entity_pair"

PARAM_INTENT = "intent"
PARAM_MAX_DEPTH = "max_depth"

KEY_ARGUMENT_DEFAULTS = "argument_defaults"
KEY_ARGUMENT_BOUNDS = "argument_bounds"
KEY_UNSUPPORTED = "unsupported_arguments"
KEY_MINIMUM = "minimum"
KEY_MAXIMUM = "maximum"
KEY_DEPTH_LIMIT = "depth_limit"
KEY_RELATIONSHIP_TYPES = "relationship_types"
KEY_SEED_ENTITY_CLASSES = "seed_entity_classes"

#: Fluree 4.1.4's read endpoint. The query dialect is SPARQL and the ledger is
#: named by an explicit `FROM` — the server answers an unhelpful HTTP 500
#: without one, so the ledger name is not an optional nicety that could
#: default, and `backends.yaml` declares it as its own variable for exactly
#: that reason.
FLUREE_QUERY_PATH = "/v1/fluree/query"
FLUREE_LEDGERS_PATH = "/v1/fluree/ledgers"
FLUREE_QUERY_CONTENT_TYPE = "application/sparql-query"

#: How many frontier nodes one hop's `VALUES` clause carries. A wire-batching
#: detail and not a domain value: the walk's SEMANTICS are identical at any
#: batch size, and the only thing this number changes is how many round trips
#: one hop costs. Chosen so a 748-node frontier is four requests rather than
#: one 50-kilobyte query body.
_FRONTIER_BATCH = 200

_HTTP_TIMEOUT_SECONDS = 180.0

#: Folds a label for the duplicate-identity comparison. Case and punctuation
#: are exactly what the pair differs by — `SUPER MICRO COMPUTER B.V.` against
#: `Super Micro Computer B.V` — so both are folded away and nothing else is.
_NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")


# ---------------------------------------------------------------------------
# Reading the deployment's own documents.
# ---------------------------------------------------------------------------


def _load(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def config() -> Mapping[str, Any]:
    return _load(CONFIG)


def question() -> Mapping[str, Any]:
    return _load(QUESTION)[DECLARATION]


def ttl_declaration() -> Mapping[str, Any]:
    return _load(TTL)[DECLARATION]


def assembly_recipe() -> Mapping[str, Any]:
    """The ten section D steps as data, with a witness per step."""
    return cast(Mapping[str, Any], _load(RECIPE)[DECLARATION])


def source_vocabulary() -> Mapping[str, Any]:
    """The IRIs this product reads, and the arrow each predicate is read in.

    Separate from ``ccf_config.yaml`` on purpose. That document holds the
    fabric's OWN vocabulary — ``owns`` there is a CCF ``relationship_type`` —
    and this one holds somebody else's: ``.../Ownership/owns`` is a predicate
    in a foreign RDF store. Collapsing the two would make a change to the
    source's vocabulary look like a change to the fabric's.
    """
    return cast(Mapping[str, Any], _load(SOURCE_VOCABULARY)[DECLARATION])


def tenant_id() -> str:
    """The tenant this deployment runs as, from its own configuration."""
    return str(config()[KEY_TENANT])


def perspective() -> Perspective:
    """The role-conditioning this product is served under.

    ``principal_id`` here is the DEFAULT and not the rule. Whether the calling
    principal changes WHICH MEMBERS EXIST is spec section B.2's
    ``[TBC — identity and access]``: no equivalent of rung 03's measured
    49/47/0/0 discrimination has been taken over the family population, and
    this module does not assume one.
    """
    declared = config()[KEY_PERSPECTIVE]
    return Perspective(
        principal_id=str(declared["principal_id"]), role=str(declared["role"])
    )


# ---------------------------------------------------------------------------
# The declared vocabulary — read, never authored here.
# ---------------------------------------------------------------------------


def declared_relationship_types() -> tuple[str, ...]:
    """The six family predicates, in the short-name vocabulary the fabric mints.

    From ``ccf_config.yaml``'s traversal operator parameters, because that is
    the set the L4 walk is typed on (`GQ-10`: the walk crosses only edges whose
    ``relationship_type`` is a member of ``relationship_types``). Reading the
    roster from the operator's own parameters is what keeps the walk and the
    source read talking about the same six predicates.
    """
    declared = config()[KEY_OPERATORS][KEY_TRAVERSAL_OPERATOR]
    return tuple(str(name) for name in declared[KEY_RELATIONSHIP_TYPES])


def seed_entity_classes() -> tuple[str, ...]:
    """Where the walk STARTS. Not which classes it may step onto.

    ``src/ccf/operators/categories.py::TraversalNeighborhood`` seeds the
    frontier with every entity whose ``entity_class`` is in this set and then
    hops over the adjacency for ``depth_limit`` rounds with **no per-hop class
    filter**; ``src/ccf/graph/protocols.py::GraphQuery`` documents the field as
    walk starting points. Declaring it constrains nothing about which
    neighbours are admitted, and nothing in this module treats it as though it
    did.
    """
    declared = config()[KEY_OPERATORS][KEY_TRAVERSAL_OPERATOR]
    return tuple(str(name) for name in declared[KEY_SEED_ENTITY_CLASSES])


def declared_depth_ceiling() -> int:
    """The ceiling, from ``request_contract.argument_bounds``.

    Measured rather than picked: walking all 83 roots, the deepest tree
    anywhere in this estate is depth 6, which ``PSC-0124`` attains — one of
    seven roots that do, so this is never phrased as *the* deepest root. A
    ceiling of 6 truncates no tree in this estate.
    """
    bounds = config()[KEY_REQUEST_CONTRACT][KEY_ARGUMENT_BOUNDS][PARAM_MAX_DEPTH]
    return int(bounds[KEY_MAXIMUM])


def declared_depth_floor() -> int:
    bounds = config()[KEY_REQUEST_CONTRACT][KEY_ARGUMENT_BOUNDS][PARAM_MAX_DEPTH]
    return int(bounds[KEY_MINIMUM])


def declared_depth_default() -> int:
    """The DECLARED default — ``CFT-G04``'s whole subject.

    Read from ``request_contract.argument_defaults`` and never invented here.
    The gate is sabotaged by defaulting at serve time instead of reading the
    declaration, and a default living in this module would make that sabotage
    indistinguishable from the shipped code.
    """
    declared = config()[KEY_REQUEST_CONTRACT][KEY_ARGUMENT_DEFAULTS]
    return int(declared[PARAM_MAX_DEPTH])


def unsupported_arguments() -> Mapping[str, str]:
    """Parameters this tier DECLARES and always REFUSES.

    Read from ``ccf_config.yaml``'s ``request_contract`` block, never listed
    here: a parameter this deployment stops refusing, or starts, is a change to
    that document and not to this module.

    ``as_of`` is the one, and the reason it is refused rather than ignored is
    specific. This is the first rung whose store carries a time axis of its
    own, and neither of the two is what ``as_of`` asks: Fluree's ``t`` is
    transaction time and ``D-IMPL-88`` rules it must not back ``as_of``, and
    Fluree's event-time addressing is nearest-at-or-before and BACKDATABLE. The
    declared reason the caller is handed therefore opens
    ``not_supported_at_tier`` — and that string is READ from the document
    rather than written here, because a refusal reason authored in code is a
    Control Plane value a deployment could not change without a release.
    """
    declared = config()[KEY_REQUEST_CONTRACT]
    return cast(Mapping[str, str], declared.get(KEY_UNSUPPORTED, {}))


def declared_ttl_seconds() -> int:
    return int(ttl_declaration()["declared_ttl_seconds"])


def max_ttl_seconds() -> int:
    return int(ttl_declaration()["max_ttl_seconds"])


def family_predicate_iris() -> Mapping[str, str]:
    """Short name to source IRI, for the six ``ccf_config.yaml`` declares.

    The roster comes from the config and the IRI from the source vocabulary, so
    a predicate declared in one document and missing from the other raises here
    rather than silently contributing no triples — which would present as a
    predicate that legitimately holds none.
    """
    declared = source_vocabulary()[VOCAB_GRAPH][VOCAB_FAMILY_PREDICATES]
    resolved: dict[str, str] = {}
    for name in declared_relationship_types():
        if name not in declared:
            raise SystemExit(
                f"{name!r} is declared in ccf_config.yaml but carries no entry"
                f" in artifacts/source-vocabulary.yaml"
            )
        resolved[name] = str(declared[name][VOCAB_IRI])
    return resolved


def family_predicate_directions() -> Mapping[str, str]:
    """Short name to arrow, for the six.

    A predicate with no declared direction FAILS CLOSED. A guessed arrow is an
    arrow nobody chose and it presents as a perfectly clean edge count — which
    is the failure ``ccf_dataprep``'s own direction validator exists to catch.
    """
    declared = source_vocabulary()[VOCAB_GRAPH][VOCAB_FAMILY_PREDICATES]
    resolved: dict[str, str] = {}
    for name in declared_relationship_types():
        reading = str(declared.get(name, {}).get(VOCAB_DIRECTION, ""))
        if reading not in (DIRECTION_SUBJECT_TO_OBJECT, DIRECTION_OBJECT_TO_SUBJECT):
            raise SystemExit(
                f"{name!r} declares no usable direction in"
                f" artifacts/source-vocabulary.yaml: {reading!r}"
            )
        resolved[name] = reading
    return resolved


def signal_class_for(predicate: str) -> str:
    """Which half-life row an edge asserted by ``predicate`` decays against.

    Section E.1's table is keyed per SIGNAL CLASS rather than per product, and
    this product is the clearest case on the ladder: one payload carries an
    ownership edge decaying at ~180 days beside a consolidation relationship at
    ~365. A single product-level rate could not express it, and the binding
    from predicate to class lived only in a comment until this artifact.
    """
    declared = source_vocabulary()[VOCAB_GRAPH][VOCAB_FAMILY_PREDICATES]
    return str(declared[predicate][VOCAB_SIGNAL_CLASS])


def node_predicate_iris() -> Mapping[str, str]:
    """The literal predicates every node fact is read through."""
    return cast(
        Mapping[str, str], source_vocabulary()[VOCAB_GRAPH][VOCAB_NODE_PREDICATES]
    )


# ---------------------------------------------------------------------------
# The two connection seams. Neither holds a value; each names a variable.
# ---------------------------------------------------------------------------


def _setting(binding: str, setting: str) -> str:
    """One connection setting, from the environment ``backends.yaml`` names.

    No default and no in-tree fallback: an unset variable raises carrying the
    remedy that document declares, because a deployment that quietly reached a
    different store than the one it names is the failure this refuses. The
    ledger name and the schema name are variables for the same reason as the
    URL and the DSN — each selects WHICH store or namespace is read, and a
    defaulted one is a store nobody chose.
    """
    declared = _load(BACKENDS)[DECLARATION][SOURCES][binding][SETTINGS][setting]
    variable = declared[FROM_ENV]
    value = os.environ.get(variable)
    if not value:
        raise SystemExit(f"{variable} is not set.\n\n{declared[REMEDY]}")
    return str(value)


@dataclass(frozen=True)
class GraphSource:
    """Where the edges and the ontology are read from, and under which ledger."""

    url: str
    ledger: str


@dataclass(frozen=True)
class AttributeSource:
    """Where the attributes are read from, and out of which namespace."""

    dsn: str
    schema: str


def graph_source() -> GraphSource:
    """The Fluree leg — spec section F.3 row 1. Read-only to this repository."""
    return GraphSource(
        url=_setting(SOURCE_GRAPH, SETTING_URL).rstrip("/"),
        ledger=_setting(SOURCE_GRAPH, SETTING_LEDGER),
    )


def attribute_source() -> AttributeSource:
    """The PostgreSQL leg — spec section F.3 row 2. ``SELECT`` and nothing else."""
    return AttributeSource(
        dsn=_setting(SOURCE_ATTRIBUTES, SETTING_DSN),
        schema=_setting(SOURCE_ATTRIBUTES, SETTING_SCHEMA),
    )


def connection(*, root: Path) -> Mapping[str, str]:
    """Compose the declared backend kind's connection settings for the FABRIC.

    This reaches ``backends.yaml``'s ``profiles:`` block and nothing else. The
    two systems of record are :func:`graph_source` and
    :func:`attribute_source`'s business, and the three are deliberately
    separate: the fabric's own state is per-run scratch this function invents a
    path for, while the two estates are durable stores this deployment may only
    read.

    The only branch here is over the value ``backends.yaml`` declares, never
    over a substrate name — a function that switched on a literal backend name
    would put the substrate into code, and the point of the document is that
    the deployment names its backend as a KIND.
    """
    kind = config()[KEY_BACKEND]
    profiles = _load(BACKENDS)[DECLARATION][PROFILES]
    settings: Mapping[str, Any] = profiles[kind][SETTINGS]
    composed: dict[str, str] = {}
    for setting, source in settings.items():
        if FROM_ENV in source:
            variable = source[FROM_ENV]
            value = os.environ.get(variable)
            if not value:
                raise SystemExit(f"{variable} is not set.\n\n{source[REMEDY]}")
            composed[setting] = value
        elif source.get(PER_RUN) == PER_RUN_PATH:
            # A FRESH PATH PER RUN. Two runs of the same question build two
            # separate graphs from the same estates and must still agree byte
            # for byte; reusing one file would let the second run read the
            # first one's state and agree with itself.
            name = f"{source[PREFIX]}_{uuid.uuid4().hex}{source[SUFFIX]}"
            composed[setting] = str(root / name)
        else:
            raise SystemExit(
                f"backends.yaml declares setting {setting!r} for backend"
                f" {kind!r} in a form this deployment cannot compose:"
                f" {sorted(source)}"
            )
    return composed


# ---------------------------------------------------------------------------
# The graph leg — SPARQL against the declared ledger.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceTriple:
    """One family triple AS THE SOURCE STORES IT, before any arrow is applied.

    Subject and object are the RDF subject and object, not a parent and a
    child. Keeping the source orientation all the way to
    :func:`normalize_edges` is what makes the arrow a single, testable step
    rather than a decision spread across every read: flip the declared
    direction of one predicate and the normalized edge set moves, which is the
    control criterion 22 runs.
    """

    predicate: str
    subject: str
    object: str


def _sparql(client: httpx.Client, source: GraphSource, query: str) -> list[Any]:
    """Issue one SPARQL SELECT and hand back the bindings.

    The query carries an explicit ``FROM <ledger>`` — :func:`_from_clause`
    builds it — because the server answers HTTP 500 rather than a helpful 400
    without one.
    """
    response = client.post(
        f"{source.url}{FLUREE_QUERY_PATH}",
        headers={"Content-Type": FLUREE_QUERY_CONTENT_TYPE},
        content=query.encode("utf-8"),
    )
    response.raise_for_status()
    bindings: list[Any] = response.json()["results"]["bindings"]
    return bindings


def _from_clause(source: GraphSource) -> str:
    return f"FROM <{source.ledger}>"


def _binding(row: Mapping[str, Any], name: str) -> str | None:
    cell = row.get(name)
    if cell is None:
        return None
    value = str(cell.get("value", "")).strip()
    return value or None


def ledger_t(source: GraphSource | None = None) -> int | None:
    """The transaction the graph leg read at — section D.6's ``lineage.ledger_t``.

    **Recorded BESIDE ``graph_snapshot_at`` and never inside it** (section
    B.1.1). Fluree's ``t`` is TRANSACTION time: it advances on a data no-op and
    it orders writes rather than observations, and ``D-IMPL-88`` rules it must
    not back ``as_of``. It is a fact about the read, which is exactly why it is
    worth recording and exactly why it is not a temporal axis.

    Returns ``None`` rather than raising when the server lists no such ledger:
    an unknown ``t`` is a missing lineage detail, not a reason to refuse a
    family the store answered for.
    """
    resolved = source or graph_source()
    with httpx.Client(timeout=_HTTP_TIMEOUT_SECONDS) as client:
        response = client.get(f"{resolved.url}{FLUREE_LEDGERS_PATH}")
        response.raise_for_status()
        listed = response.json()
    wanted = resolved.ledger.split(":")[0]
    for entry in listed:
        if entry.get("name") in (resolved.ledger, wanted):
            value = entry.get("t")
            return int(value) if value is not None else None
    return None


def enumerate_family_triples(
    source: GraphSource | None = None,
    *,
    predicates: Mapping[str, str] | None = None,
) -> tuple[SourceTriple, ...]:
    """Every family triple in the ledger, ONE ENUMERATION PER PREDICATE.

    **Enumerated, never aggregated.** Over this ledger the aggregate forms
    invent phantoms — ``COUNT(DISTINCT ?p)`` answers 178 and ``GROUP BY ?p``
    answers 198 where ``SELECT DISTINCT ?p`` answers 171, which is the correct
    number — so every count in this product is taken in Python over enumerated
    rows. The shape is the measurement pass's own:
    ``SELECT ?s ?o FROM <ledger> WHERE { ?s <PREDICATE-IRI> ?o }``.

    This is the WHOLE-LEDGER read. It is what the census and the cycle controls
    run over; the product's own read is :func:`walk_from_anchor`, which is
    bounded. Six queries, one per predicate, and the predicate is known from
    which query answered rather than from a ``BIND`` — so nothing about the
    result depends on the server binding a constant back to the caller.
    """
    resolved = source or graph_source()
    iris = predicates or family_predicate_iris()
    triples: list[SourceTriple] = []
    with httpx.Client(timeout=_HTTP_TIMEOUT_SECONDS) as client:
        for name, iri in iris.items():
            rows = _sparql(
                client,
                resolved,
                f"SELECT ?s ?o {_from_clause(resolved)} WHERE {{ ?s <{iri}> ?o }}",
            )
            for row in rows:
                subject = _binding(row, "s")
                obj = _binding(row, "o")
                if subject is None or obj is None:
                    continue
                triples.append(
                    SourceTriple(predicate=name, subject=subject, object=obj)
                )
    return tuple(triples)


def _hop_query(
    source: GraphSource,
    *,
    frontier: Sequence[str],
    iris: Mapping[str, str],
    bind_on_subject: bool,
) -> str:
    """One hop, as a UNION of fixed-length patterns over the current frontier.

    **Bounded depth is expressed as unioned fixed-length patterns because
    SPARQL 1.1 property paths support ``+ * ?`` and NOT bounded ``{m,n}``
    repetition** (spec section C.2). The union here is over the PREDICATES at
    one fixed length rather than over the LENGTHS, and that is a deliberate
    difference from the shape the sentence first suggests: a single query
    unioning every predicate at every length to the ceiling is six to the sixth
    alternations, which is a query nobody can read and no server should be
    asked to plan. Iterating the one-hop union to the ceiling reaches exactly
    the same set.

    The two orientations are split into two queries rather than combined,
    because the frontier binds to ``?subject`` for a subject-to-object
    predicate and to ``?object`` for an object-to-subject one, and one query
    cannot carry two different ``VALUES`` targets. Both shapes return the
    triple in SOURCE orientation, so :func:`normalize_edges` stays the one and
    only place the arrow is applied.
    """
    values = " ".join(f"<{node}>" for node in frontier)
    anchor_variable = "?s" if bind_on_subject else "?o"
    branches = " UNION ".join(
        f"{{ ?s <{iri}> ?o . BIND(<{iri}> AS ?p) }}" for iri in iris.values()
    )
    return (
        f"SELECT ?s ?o ?p {_from_clause(source)} WHERE {{"
        f" VALUES {anchor_variable} {{ {values} }} {branches} }}"
    )


def walk_from_anchor(
    anchor_uri: str,
    *,
    source: GraphSource | None = None,
    ceiling: int | None = None,
) -> tuple[SourceTriple, ...]:
    """The anchor's reachable component, BOUNDED BY THE DECLARED CEILING.

    **The ceiling bounds the INGEST; the caller's ``max_depth`` is applied
    later, at L4.** Stating the split as a comment rather than leaving it to be
    inferred, because the alternative looks like an optimization and is a
    defect: bounding this read by the caller's depth instead would take depth
    out of the operator's parameter set, and therefore out of the parameter
    hash, and two different depths would then share one content address. That
    is exactly what ``CFT-G05`` forbids, and it is the reason
    :func:`traversal_parameters` exists.

    Cycle-safe by construction: a node already assigned a depth is never
    re-queued, so the walk terminates inside cycle 1 rather than running
    forever. An edge back to an already-known node is still RECORDED — the
    closing edge of a circuit is precisely such an edge, and dropping it would
    make the headline finding undetectable while every node count stayed right.
    """
    resolved = source or graph_source()
    bound = ceiling if ceiling is not None else declared_depth_ceiling()
    directions = family_predicate_directions()
    iris = family_predicate_iris()
    forward = {
        name: iri
        for name, iri in iris.items()
        if directions[name] == DIRECTION_SUBJECT_TO_OBJECT
    }
    reverse = {
        name: iri
        for name, iri in iris.items()
        if directions[name] == DIRECTION_OBJECT_TO_SUBJECT
    }
    by_iri = {iri: name for name, iri in iris.items()}

    seen: set[str] = {anchor_uri}
    frontier: list[str] = [anchor_uri]
    collected: dict[tuple[str, str, str], SourceTriple] = {}

    with httpx.Client(timeout=_HTTP_TIMEOUT_SECONDS) as client:
        for _ in range(bound):
            if not frontier:
                break
            discovered: list[str] = []
            for start in range(0, len(frontier), _FRONTIER_BATCH):
                batch = frontier[start : start + _FRONTIER_BATCH]
                for group, on_subject in ((forward, True), (reverse, False)):
                    if not group:
                        continue
                    rows = _sparql(
                        client,
                        resolved,
                        _hop_query(
                            resolved,
                            frontier=batch,
                            iris=group,
                            bind_on_subject=on_subject,
                        ),
                    )
                    for row in rows:
                        subject = _binding(row, "s")
                        obj = _binding(row, "o")
                        iri = _binding(row, "p")
                        if subject is None or obj is None or iri is None:
                            continue
                        name = by_iri.get(iri)
                        if name is None:
                            continue
                        collected[(name, subject, obj)] = SourceTriple(
                            predicate=name, subject=subject, object=obj
                        )
                        child = obj if on_subject else subject
                        if child not in seen:
                            seen.add(child)
                            discovered.append(child)
            frontier = discovered
    return tuple(collected[key] for key in sorted(collected))


# ---------------------------------------------------------------------------
# Normalization — recipe step 4. THE ONE PLACE THE ARROW IS APPLIED.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FamilyEdges:
    """The distinct parent-to-child edge SET, with the predicates asserting each.

    **Set semantics, not list semantics** (spec section D.3 step 4). Over the
    whole ledger, 1,058 raw triples become 722 distinct edges — six predicates
    routinely assert the same parent-child pair — and reporting 1,058 would be
    reporting ASSERTIONS and calling them RELATIONSHIPS. That error looks
    larger and more complete rather than smaller and more suspicious, which is
    why the collapse is reported rather than hidden.

    The mapping is pair to the set of predicates that asserted it, so both
    facts survive: ``len(by_pair)`` is the distinct edge count, and each edge
    still knows which of the six spoke for it.
    """

    by_pair: Mapping[tuple[str, str], frozenset[str]]

    @classmethod
    def from_pairs(cls, pairs: Iterable[tuple[str, str]]) -> FamilyEdges:
        """Build an edge set from bare pairs, with no predicate attribution.

        The control in criterion 21 needs exactly this: the RAW reading, every
        triple taken subject-to-object with no arrow applied, fed to the SAME
        detector the product ships. Over this ledger that reading is 825
        distinct pairs and the detector finds 130 circuits rather than 2 — a
        gap wide enough that the control DISCRIMINATES rather than merely
        differing.
        """
        collected: dict[tuple[str, str], frozenset[str]] = {}
        for pair in pairs:
            collected[pair] = frozenset()
        return cls(by_pair=collected)

    @property
    def pairs(self) -> frozenset[tuple[str, str]]:
        return frozenset(self.by_pair)

    @property
    def nodes(self) -> frozenset[str]:
        """Every endpoint of every edge — 748 over the whole ledger."""
        found: set[str] = set()
        for parent, child in self.by_pair:
            found.add(parent)
            found.add(child)
        return frozenset(found)

    @property
    def roots(self) -> frozenset[str]:
        """Every node that is nobody's child — 83 over the whole ledger.

        The figure the arrow is asserted against: reversing exactly one of the
        six declared directions moves this count off 83, including ``controls``
        whose three triples move it by one.
        """
        children = {child for _, child in self.by_pair}
        return frozenset(self.nodes - children)

    @property
    def children(self) -> Mapping[str, tuple[str, ...]]:
        adjacency: dict[str, list[str]] = defaultdict(list)
        for parent, child in self.by_pair:
            adjacency[parent].append(child)
        return {parent: tuple(sorted(kids)) for parent, kids in adjacency.items()}

    def predicates_for(self, pair: tuple[str, str]) -> frozenset[str]:
        return self.by_pair.get(pair, frozenset())

    def reach(self, anchor: str, *, depth_limit: int) -> Mapping[str, int]:
        """Breadth-first depth from ``anchor``, the anchor itself at depth 0.

        Cycle-safe: a node already assigned a depth is never re-queued. From
        the demonstration anchor at depth 3 this reaches 22 nodes, with cycle
        1's three members at depths 1, 2 and 3 — which is the measurement the
        declared default of 3 rests on.
        """
        adjacency = self.children
        depth: dict[str, int] = {anchor: 0}
        frontier = [anchor]
        while frontier:
            following: list[str] = []
            for node in frontier:
                for child in adjacency.get(node, ()):
                    if child in depth:
                        continue
                    depth[child] = depth[node] + 1
                    if depth[child] < depth_limit:
                        following.append(child)
            frontier = following
        return depth


def normalize_edges(
    triples: Iterable[SourceTriple],
    *,
    directions: Mapping[str, str] | None = None,
) -> FamilyEdges:
    """Turn source triples into the distinct parent-to-child edge set.

    **The six predicates do not all run parent to child.** ``owns`` and
    ``controls`` read subject to object; the two consolidation predicates and
    the two ultimate-parent predicates read object to subject. The table comes
    from ``artifacts/source-vocabulary.yaml`` and never from this function, and
    a predicate with no declared arrow raises rather than defaulting to either
    reading — a guessed arrow is an arrow nobody chose, and it presents as a
    perfectly clean edge count.

    ``directions`` is overridable for exactly one reason: the control in
    criterion 22 flips one predicate's arrow and asserts the root count moves
    off 83. That control has to drive the SHIPPED normalization rather than a
    copy written inside a test, or it proves something about the test.
    """
    table = directions or family_predicate_directions()
    collected: dict[tuple[str, str], set[str]] = defaultdict(set)
    for triple in triples:
        reading = table.get(triple.predicate)
        if reading == DIRECTION_SUBJECT_TO_OBJECT:
            pair = (triple.subject, triple.object)
        elif reading == DIRECTION_OBJECT_TO_SUBJECT:
            pair = (triple.object, triple.subject)
        else:
            raise SystemExit(
                f"{triple.predicate!r} has no declared direction; refusing to"
                f" normalize a triple whose arrow nobody chose"
            )
        collected[pair].add(triple.predicate)
    return FamilyEdges(
        by_pair={pair: frozenset(names) for pair, names in collected.items()}
    )


def collapse(triples: Sequence[SourceTriple], edges: FamilyEdges) -> int:
    """How many raw triples the normalization absorbed — 336 over the ledger.

    Reported rather than hidden, because the collapse is the difference between
    an assertion count and a relationship count and a build that never
    subtracts them cannot tell the two apart.
    """
    return len(triples) - len(edges.by_pair)


# ---------------------------------------------------------------------------
# Findings — recipe steps 7 and 8. ORTHOGONAL TO THE TREE.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """One thing the family CONTAINS, served beside the tree and never upon it.

    Four fields, always present, nullable where they do not apply — the shape
    ``artifacts/expected.yaml`` declares under
    ``finding_keys_always_present``. A cycle is a SET PLUS THE EDGE THAT CLOSES
    IT; the closing edge is what a flattened representation loses, and
    ``CFT-G07`` is sabotaged by dropping precisely that.
    """

    type: str
    predicate: str | None
    members: tuple[str, ...]
    closing_edge: tuple[str, str] | None


def _rotate(circuit: Sequence[str]) -> tuple[str, ...]:
    """Rotate a circuit to start at its lexicographically smallest member.

    **THE CONVENTION IS LOAD-BEARING, NOT COSMETIC.** The locked criteria
    assert EXACT ORDERED rosters, and the same elementary circuit entered from
    a different node is the same SET in a different ORDER — so a correct
    detector using a different rotation would fail a correct assertion. The
    convention is stated at spec section C.4 trap 5 and section D.2.2 so the
    shipped detector INHERITS it rather than rediscovering it, and this is the
    function that carries it.
    """
    ordered = tuple(circuit)
    start = min(range(len(ordered)), key=lambda index: ordered[index])
    return ordered[start:] + ordered[:start]


def detect_cycles(edges: FamilyEdges) -> tuple[Finding, ...]:
    """Enumerate the elementary circuits, APPLICATION-SIDE.

    **This is L2 work and the recipe declares ``operator: null`` for it**, for
    three reasons and the third is binding. The store cannot do it: Fluree has
    no graph-algorithm library, so the caller maintains the visited set. None
    of the SDK's four scheduling classes describes it: ``OperatorCategory`` is
    a plan-order class carrying correctness rules, and circuit enumeration over
    an already-collected edge set is none of them. And ``D-IMPL-223`` forbids
    registering it under Traversal to make a category fit — registering it
    there would make the lineage record say something untrue.

    Depth-first over an explicit stack; a back edge to the start closes a
    circuit. Only circuits whose smallest member is the start node are
    explored, so each is found exactly once rather than once per entry point,
    and :func:`_rotate` then fixes the order the roster is reported in.

    The predicate a circuit is attributed to is DERIVED from the edges rather
    than declared: the predicates common to every edge of the circuit, smallest
    first, or ``None`` when nothing is common to all of them. Over this ledger
    both circuits attribute to ``owns``, and all six of their edges are present
    in the ``owns`` enumeration read subject to object.
    """
    adjacency = edges.children
    circuits: dict[tuple[str, ...], tuple[str, ...]] = {}

    def walk(start: str, node: str, stack: list[str], on_stack: set[str]) -> None:
        for neighbour in adjacency.get(node, ()):
            if neighbour == start and len(stack) >= 2:
                rotated = _rotate(stack)
                circuits[rotated] = rotated
            elif neighbour not in on_stack and neighbour > start:
                stack.append(neighbour)
                on_stack.add(neighbour)
                walk(start, neighbour, stack, on_stack)
                stack.pop()
                on_stack.discard(neighbour)

    for start in sorted(edges.nodes):
        walk(start, start, [start], {start})

    findings: list[Finding] = []
    for members in sorted(circuits):
        closing = (members[-1], members[0])
        ring = [*zip(members, members[1:]), closing]
        common: frozenset[str] | None = None
        for pair in ring:
            asserted = edges.predicates_for(pair)
            common = asserted if common is None else (common & asserted)
        attributed = sorted(common) if common else []
        findings.append(
            Finding(
                type=FINDING_OWNERSHIP_CYCLE,
                predicate=attributed[0] if attributed else None,
                members=members,
                closing_edge=closing,
            )
        )
    return tuple(findings)


def _fold(label: str) -> str:
    return " ".join(_NON_ALPHANUMERIC.sub(" ", label.casefold()).split())


def surface_duplicate_pairs(labels: Mapping[str, str]) -> tuple[Finding, ...]:
    """The same company entered twice — recipe step 8, spec section C.4 trap 3.

    **The comparison is on the label, case- and punctuation-folded, and on
    nothing else.** Not on the LEI: exactly one of the demonstrated pair has
    one, so an LEI-keyed comparison finds nothing. Not on the URI: the two
    differ by a ``Sub`` prefix, and a prefix rule would fire on all seventeen
    Exhibit 21 stubs beside them.

    **A label that folds to nothing is not a duplicate**, and the guard is
    measured rather than defensive: over the whole family graph fifteen label
    buckets hold more than one node, and one of the fifteen is a bucket of nine
    whose labels fold to the empty string. Without the guard those nine would
    be reported as one company entered nine times.

    Neither member is dropped and neither is merged — findings are ORTHOGONAL
    to the tree (``D-12``). A family that double-counts a subsidiary is a
    concentration denominator wrong in the safe-looking direction, and a family
    that silently merges two is a member that vanished.
    """
    declared = source_vocabulary()[VOCAB_DUPLICATE]
    refuse_empty = bool(declared.get(VOCAB_REFUSE_EMPTY_FOLD, True))
    buckets: dict[str, list[str]] = defaultdict(list)
    for uri, label in labels.items():
        folded = _fold(label)
        if not folded and refuse_empty:
            continue
        buckets[folded].append(uri)
    return tuple(
        Finding(
            type=FINDING_DUPLICATE_ENTITY,
            predicate=None,
            members=tuple(sorted(members)),
            closing_edge=None,
        )
        for _, members in sorted(buckets.items())
        if len(members) > 1
    )


# ---------------------------------------------------------------------------
# Node facts — the ontology, the labels and the LEIs, batched.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NodeFacts:
    """What the graph leg knows about one family node.

    ``type_chain`` is NOT nullable and ``lei`` and ``label`` are (section D.6).
    An untyped node is not admitted at all, which is what makes ``CFT-G01``'s
    predicate over EVERY node non-vacuous rather than a check that passes on an
    empty set — and it is why the ontology witness in the recipe sits on this
    read: nothing in the request, nothing in PostgreSQL and nothing the
    assembler computes carries a FIBO class chain.
    """

    uri: str
    lei: str | None
    label: str | None
    type_chain: tuple[str, ...]


def read_node_facts(
    nodes: Sequence[str], *, source: GraphSource | None = None
) -> Mapping[str, NodeFacts]:
    """The class chain, label and LEI for every node the walk collected.

    Three enumerations over the whole node set rather than three per node, on
    the same batching reasoning the attribute leg carries: a per-node fan-out
    works at depth 2 and collapses at depth 4. The ``VALUES`` clause is
    chunked, so the number of round trips is a function of the frontier size
    and never of the depth.

    A node the ledger holds no ``rdf:type`` for is DROPPED HERE rather than
    served untyped: section D.6 makes ``type_chain`` non-nullable, and an
    untyped node admitted quietly is exactly what ``CFT-G01`` exists to catch.
    """
    resolved = source or graph_source()
    predicates = node_predicate_iris()
    leis: dict[str, str] = {}
    labels: dict[str, str] = {}
    chains: dict[str, set[str]] = defaultdict(set)
    with httpx.Client(timeout=_HTTP_TIMEOUT_SECONDS) as client:
        for start in range(0, len(nodes), _FRONTIER_BATCH):
            batch = nodes[start : start + _FRONTIER_BATCH]
            values = " ".join(f"<{node}>" for node in batch)
            for key, target in (
                (NODE_PREDICATE_LEI, leis),
                (NODE_PREDICATE_LABEL, labels),
            ):
                rows = _sparql(
                    client,
                    resolved,
                    f"SELECT ?s ?o {_from_clause(resolved)} WHERE {{"
                    f" VALUES ?s {{ {values} }}"
                    f" ?s <{predicates[key]}> ?o }}",
                )
                for row in rows:
                    subject = _binding(row, "s")
                    value = _binding(row, "o")
                    if subject is not None and value is not None:
                        target[subject] = value
            rows = _sparql(
                client,
                resolved,
                f"SELECT ?s ?o {_from_clause(resolved)} WHERE {{"
                f" VALUES ?s {{ {values} }}"
                f" ?s <{predicates[NODE_PREDICATE_TYPE_CHAIN]}> ?o }}",
            )
            for row in rows:
                subject = _binding(row, "s")
                value = _binding(row, "o")
                if subject is not None and value is not None:
                    chains[subject].add(value)
    return {
        uri: NodeFacts(
            uri=uri,
            lei=leis.get(uri),
            label=labels.get(uri),
            type_chain=tuple(sorted(chains[uri])),
        )
        for uri in nodes
        if chains.get(uri)
    }


# ---------------------------------------------------------------------------
# The attribute leg — ONE batched statement for the whole node set.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AttributeResolution:
    """What the attribute leg resolved, and how many statements it took.

    ``statements`` is the evidence ``CFT-G11`` reads. It is counted at the
    CONNECTION rather than inside the resolving function, through a cursor
    factory that tallies every ``execute`` on the connection — so a sabotage
    that fires one query per node anywhere on that connection is counted even
    if it does not go through :func:`resolve_attributes`' own call site.
    """

    rows: Mapping[str, Mapping[str, Any]]
    statements: tuple[str, ...]
    requested: tuple[str, ...]

    @property
    def unresolved(self) -> tuple[str, ...]:
        """The LEIs the estate answered nothing for.

        A NULL RESOLUTION, never a dropped member (``D-16``). 606 of the 748
        family nodes have no attribute row at all, and a build that quietly
        served only the 142 that do would return a smaller, tidier, WRONG
        family — with no error, and with a concentration denominator wrong in
        the safe-looking direction.
        """
        return tuple(lei for lei in self.requested if lei not in self.rows)


def _counting_cursor(tally: list[str]) -> type[psycopg.Cursor[Any]]:
    """A cursor class that records every statement executed on its connection."""

    class _Cursor(psycopg.Cursor[Any]):
        def execute(self, query: Any, params: Any = None, **kwargs: Any) -> Any:
            tally.append(
                query if isinstance(query, str) else query.decode("utf-8", "replace")
            )
            return super().execute(query, params, **kwargs)

    return _Cursor


def resolve_attributes(
    leis: Sequence[str], *, source: AttributeSource | None = None
) -> AttributeResolution:
    """Resolve the collected LEIs in ONE batched statement.

    **Batching is mandatory, not a variant.** The Standard retired the ``Batch``
    qualifier from the enrichment operator for exactly this reason, and
    ``CFT-G11`` asserts the count rather than a preference. A per-node fan-out
    over 748 nodes is the shape the gate exists to forbid: it works at depth 2
    and collapses at depth 4, which is the failure the whitepaper's
    DataLoader-style resolution exists to prevent.

    **The table is ``legal_entity`` and the decoy is ``crosswalk``** (spec
    section C.4 trap 4). Measured over the family graph's 181 LEI-bearing
    nodes, ``legal_entity`` resolves 142 and ``crosswalk`` resolves 39 — both
    real numbers about the estate, only one an answer to the question asked,
    and far enough apart that a check reading the wrong table cannot report the
    right answer by accident. The table name comes from
    ``artifacts/source-vocabulary.yaml``.

    An empty LEI set issues NO statement and resolves nothing, which is a
    legitimate answer rather than an error: a family whose members carry no
    LEI at all is a family this product serves whole.
    """
    resolved = source or attribute_source()
    declared = source_vocabulary()[VOCAB_ATTRIBUTES]
    table = str(declared[VOCAB_TABLE])
    key_column = str(declared[VOCAB_KEY_COLUMN])
    columns = tuple(str(name) for name in declared[VOCAB_SERVED_COLUMNS])
    wanted = tuple(sorted({lei for lei in leis if lei}))
    tally: list[str] = []
    rows: dict[str, Mapping[str, Any]] = {}
    if wanted:
        projection = ", ".join([key_column, *columns])
        with psycopg.connect(
            resolved.dsn, cursor_factory=_counting_cursor(tally)
        ) as connection_handle:
            with connection_handle.cursor() as cursor:
                cursor.execute(
                    f'SELECT {projection} FROM "{resolved.schema}".{table}'
                    f" WHERE {key_column} = ANY(%s)",
                    (list(wanted),),
                )
                for record in cursor.fetchall():
                    key = str(record[0])
                    rows[key] = {
                        name: record[index + 1] for index, name in enumerate(columns)
                    }
    return AttributeResolution(
        rows=rows, statements=tuple(tally), requested=wanted
    )


# ---------------------------------------------------------------------------
# The request surface, and the refusals. Checked at the door.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DepthOutOfBounds:
    """``max_depth`` above the declared ceiling — REFUSED BY NAME, NEVER CLAMPED.

    **A clamp would be a different program, not a nearby one.** The request
    says 8, the walk does 6, the payload looks fine and the content address
    greens — a wrong answer to a question nobody asked, returned with no error.
    ``CFT-G03`` is sabotaged by replacing this refusal with a silent clamp,
    which is precisely the sabotage a count-based check would not see.

    Returned AS DATA, on the ``ProductRequestViolation`` model: a refusal is an
    answer about the request, and raising would make the caller's error
    handling the place the contract lives.
    """

    parameter: str
    requested: int
    minimum: int
    maximum: int


def resolve_max_depth(
    parameters: Mapping[str, Any],
) -> int | DepthOutOfBounds:
    """The depth this request walks at — declared default, declared bounds.

    **Absent takes the DECLARED default** read from
    ``request_contract.argument_defaults`` (``D-08``, ``CFT-G04``). There is no
    serve-time default in this function and no literal depth anywhere in this
    module: the value a missing parameter resolves to is a property of the
    Control Plane document, and a default living here would make the gate's own
    sabotage — defaulting at serve time — indistinguishable from shipped code.

    **Over the ceiling is refused by name** (``D-07``, ``CFT-G03``). There is no
    branch below that clamps, and the absence is the point.
    """
    minimum = declared_depth_floor()
    maximum = declared_depth_ceiling()
    if PARAM_MAX_DEPTH not in parameters or parameters[PARAM_MAX_DEPTH] is None:
        return declared_depth_default()
    requested = int(cast(Any, parameters[PARAM_MAX_DEPTH]))
    if requested < minimum or requested > maximum:
        return DepthOutOfBounds(
            parameter=PARAM_MAX_DEPTH,
            requested=requested,
            minimum=minimum,
            maximum=maximum,
        )
    return requested


def traversal_parameters(
    declared: OperatorParametersArtifact, *, max_depth: int
) -> OperatorParametersArtifact:
    """Bind the CALLER's depth onto the declared traversal parameter set.

    **This is what makes depth part of the product's identity** (``D-09``,
    ``CFT-G05``). ``ccf_config.yaml`` declares ``depth_limit`` as the CEILING —
    the bound the source read is taken at — and this function substitutes the
    caller's ``max_depth`` for it per request, so the operator parameter set's
    content hash differs between two depths and the two products get two
    addresses. From the demonstration anchor, depth 1 reaches 20 nodes, depth 2
    reaches 21 and depth 3 reaches 22: three depths, three different answers,
    three addresses.

    Had the caller's depth gone into the SPARQL instead, depth would have been
    a source-read detail invisible to the parameter hash and two depths could
    have shared one address.
    """
    return cast(
        OperatorParametersArtifact,
        declared.model_copy(update={KEY_DEPTH_LIMIT: max_depth}),
    )


def request(
    *, parameters: Mapping[str, object], asked_at: datetime | None = None
) -> ProductRequest:
    """Build the typed question from the caller's parameters and this
    deployment's declared vocabulary.

    The address tokens come from ``artifacts/question.yaml`` and the class
    identity from ``ccf_config.yaml``. ``parameters`` is the CALLER'S — this
    function supplies no value for it and no default, which is what keeps the
    contract's requirement real.
    """
    declaration = question()
    declared = config()[KEY_PRODUCT_CLASS]
    return ProductRequest(
        schema_name=declared["schema_name"],
        schema_version=declared["schema_version"],
        subject=declaration["subject"],
        intent=declaration["parameters"][PARAM_INTENT],
        freshness=declaration["freshness"],
        asked_at=asked_at or datetime.fromisoformat(declaration["asked_at"]),
        parameters=parameters,
    )


def demonstration_parameters() -> Mapping[str, Any]:
    """The bundled demonstration's request parameters — all defaulted."""
    return cast(Mapping[str, Any], question()["parameters"])


def demonstration_anchor() -> str:
    """The anchor the bundled demonstration asks about, from scenario material.

    **Nothing in this module names an LEI.** Re-asking the same question of
    another company is a parameter, and the anchor is swappable because it
    lives in an artifact rather than here.
    """
    return str(question()["subject"])
