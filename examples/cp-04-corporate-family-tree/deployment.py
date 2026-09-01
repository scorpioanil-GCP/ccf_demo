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

**THE TWO THINGS THAT ONCE STOOD OPEN HERE, AND HOW EACH WAS RULED.** An
earlier revision of this docstring named the L1 envelopes and the policy
classification as deliberately absent, because building either would have
required deciding a question the Control Plane document left open. Both are
now ruled and both are built. The reasoning is kept, because the shape below
is unreadable without it:

1. **The L1 envelopes — ONE PER NODE, and no relationship rule fires.**
   ``src/ccf/assembly/worker.py:381`` mints a relationship claim by **class
   co-occurrence**: every declared rule whose subject and object classes BOTH
   resolve from one envelope fires, and nothing selects the relationship type
   from the payload. Measured live through ``booted.handle.worker``, one
   envelope carrying one ``entity_uri`` minted 2 entities — the same node under
   both classes — and **twelve relationships, six of them self-loops**, across
   all six declared types. A member-to-member edge cannot be minted at all,
   because one envelope resolves at most one ``family_member``. Had the twelve
   rules been kept, this product's ``predicate`` field would have been a lie.
   ``D-35`` records the gap; ``ccf_config.yaml`` now declares
   ``relationship_rules: []``; and :func:`relationship_claims` builds each
   typed edge for admission through ``worker.admit_relationship_claim``
   (``:315``), **carrying its true predicate**. Still one writer, still L2, and
   no file under ``src/`` changes.
2. **The policy classification — the family's OBSERVED jurisdiction set, closed
   at two values.** ``PolicyFilter._admits`` refuses an ABSENT classification
   attribute exactly as firmly as an out-of-grant one, and 20 of the SMCI
   subtree's 22 members hold no PostgreSQL row — so under the struck nine-value
   envelope the Policy step deleted 20 of the 22 members, which is precisely the
   population ``CFT-G09`` and criterion 33 exist to protect. Ruled 2026-09-01 as
   ``D-IMPL-228``: the declared set is ``{NL, US-DE}``, the set this family
   actually exhibits, **closed, with an unknown key refused**; a member carries
   its own ``legal_jurisdiction`` where a row exists and **the family's — the
   anchor's — where none does**. :func:`classify_family` applies it and
   :func:`refuse_open_jurisdiction_world` closes the world in **both**
   directions, so neither a dropped row nor a quietly added one can ship.

**THE WALK IS FAMILY-SCOPED; THE JURISDICTION LIST IS NOT.** ``D-IMPL-228``
refuses the inverse by name — *"Do not 'family-scope' a superset of
jurisdictions so the anchor happens to hit the list."* Family-scoping over the
struck nine would have admitted every member because the anchor is ``US-DE``,
for a reason unrelated to the other seven. Dave, verbatim: *"Nine-row
'coverage' is how idle gates look when the extra rows never fire."*

**WHAT IS EXERCISED HERE:** both connection seams, the bounded walk, the
whole-ledger enumeration, the normalization with its per-predicate arrow, the
cycle detector with its rotation convention, the duplicate-identity finding,
the ONE batched attribute read, the classification, the L1 envelopes, the typed
edge claims, the scenario the spine reads, and every refusal.

**WHAT THIS MODULE STILL DOES NOT COMPUTE, NAMED RATHER THAN LEFT TO A STACK
TRACE.** ``D_c``. ``ccf_config.yaml`` declares a ``debt_profile`` and
``question.yaml`` a ``debt_tolerance``, and :class:`FamilyScenario` carries both
**as data**; what ``F``, ``C`` and ``S`` are measured over for a graph payload
is spec section E.2's question and belongs with the spine that refuses on it,
which is plan ``24.4-07``. Declaring the inputs and computing nothing is the
honest boundary; inventing a formula here would put a domain decision in the
file least likely to be read for one.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

import httpx
import psycopg
import yaml

from ccf.assembly.worker import EntityResolutionSpec
from ccf.contracts.claims import LineageEntry, RelationshipClaim
from ccf.controlplane.artifacts import (
    DebtProfile,
    HalfLifeTable,
    OperatorParametersArtifact,
    PerspectiveArtifact,
    ProductClassDeclaration,
)
from ccf.deployment import BootedFabric
from ccf.products.request import ProductRequest, ProductRequestContract
from ccf.projection.plan import Perspective
from ccf.signal.envelope import SignalEnvelope, SourceIdentity

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
KEY_POLICY_OPERATOR = "policy.principal-subgraph"
KEY_RESOLUTION = "resolution"
KEY_ENTITY_RULES = "entity_rules"
KEY_MATCH_KEY = "match_key"
KEY_ENTITY_CLASS = "entity_class"
KEY_IDENTITY_KEYS = "identity_keys"
KEY_ATTRIBUTE_KEYS = "attribute_keys"
KEY_HALF_LIFE_TABLE = "half_life"
KEY_DEBT_PROFILE = "debt_profile"
KEY_POLICY_BUNDLE = "policy"
KEY_PERMITTED_CLASSIFICATIONS = "permitted_classifications"

REPLAY_RECORD_CLASS = "cp-04.replay-record"
QUERY_PIN_CLASS = "cp-04.graph-query"
ARTIFACT_STORE_DIRNAME = "artifacts-store"

#: The payload key carrying a node's SOURCE identity, and the one
#: `ccf_config.yaml`'s two entity rules both name under `identity_keys`. The
#: MINTED `entity_uri` is not this value — `worker.py:220` hashes the identity
#: map and mints `<entity-class>://<hash>` — which is exactly why
#: :func:`relationship_claims` takes the minted URIs from the ingest results
#: rather than recomputing them here.
ATTR_ENTITY_URI = "entity_uri"

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
VOCAB_JURISDICTION_COLUMN = "jurisdiction_column"
VOCAB_REFUSE_EMPTY_FOLD = "refuse_empty_fold"

#: `artifacts/source-vocabulary.yaml::entitlement` — the block `D-IMPL-228`
#: ruled on 2026-09-01, and the home of WHICH classification value a family
#: member carries. The declared SET lives in `ccf_config.yaml`; the value's
#: PROVENANCE is a source fact and lives here.
VOCAB_ENTITLEMENT = "entitlement"
VOCAB_CLASSIFICATION_ATTRIBUTE = "classification_attribute"
VOCAB_CLASSIFICATION_SOURCES = "classification_sources"

#: The two declared classification sources, in the order the artifact lists
#: them. `own_attribute_row` reads the member's own `jurisdiction_column`;
#: `family_anchor` reads the value the ANCHOR resolved to. A source this module
#: does not implement is a refusal, never a silent skip — otherwise a document
#: could declare a provenance nobody honored and the payload would still look
#: right.
CLASSIFICATION_OWN_ROW = "own_attribute_row"
CLASSIFICATION_FAMILY_ANCHOR = "family_anchor"

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

#: A reference from `ccf_config.yaml` to one of this deployment's own artifacts.
_ARTIFACT_REFERENCE = re.compile(r"artifacts/([A-Za-z0-9._-]+\.yaml)")

#: The word a `ccf_config.yaml` comment uses when it says where the six source
#: predicates' full IRIs live. :func:`refuse_stale_vocabulary_pointer` scans
#: whole COMMENT BLOCKS rather than lines for this, deliberately: the pointer
#: sentence is line-wrapped, and a line-scoped check would be defeated by a
#: re-wrap that moved the path onto its own line — which is a formatting change
#: nobody would think to re-verify.
_IRI_CLAIM = re.compile(r"\bIRIs?\b")

#: How a node's FIBO class chain is rendered into `EntityClaim.attributes`,
#: which is typed `Mapping[str, str]`. A serialization detail and not a domain
#: value: the chain's MEMBERS come from the ledger, and this only fixes how a
#: tuple of them becomes one string. A space cannot occur inside an IRI, so the
#: join is reversible.
_TYPE_CHAIN_SEPARATOR = " "


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


def _comment_blocks(text: str) -> tuple[str, ...]:
    """Consecutive ``#`` lines, joined — one block per prose paragraph."""
    blocks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            current.append(stripped.lstrip("#").strip())
        elif current:
            blocks.append(" ".join(current))
            current = []
    if current:
        blocks.append(" ".join(current))
    return tuple(blocks)


def refuse_stale_vocabulary_pointer() -> tuple[str, ...]:
    """Refuse a ``ccf_config.yaml`` pointer that names the wrong document.

    **A POINTER TO THE WRONG FILE AND A POINTER TO THE WRONG RULING ARE THE
    SAME DEFECT: A READER STOPS LOOKING.** Dave, 2026-09-01, naming both at
    once. This function is the first half made checkable.

    The defect it exists for is not hypothetical and was not caught by any
    schema. ``ccf_config.yaml`` said, in place, that the six family predicates'
    full IRIs were in ``artifacts/assembly-recipe.yaml``. They were not:
    ``grep -rn 'edmcouncil'`` over that file returns **zero**. The recipe
    carries ten steps, a witness per step and a closed operator vocabulary, and
    no IRI anywhere. A reader following that sentence found a document that
    looked authoritative and did not contain the subject.

    **THE POINTER LIVES IN A COMMENT, so a YAML-shaped check cannot see it** —
    which is exactly why it went unverified for a wave. This scans the config's
    comment BLOCKS for any block that both claims to name an IRI home and names
    an artifact, and holds every named document to actually carrying all six.

    Returns the artifact filenames the config points at, so a caller can see
    the check had a non-empty subject.

    Three ways to fail, and the third is the one that makes this a gate rather
    than a formality:

    * a named document does not exist;
    * a named document is missing one or more of the six IRIs — **the shipped
      defect, reproducible by repointing the sentence at
      ``assembly-recipe.yaml``**; and
    * **NO block claims an IRI home at all.** Deleting the pointer would
      otherwise make this check pass over an empty set, so a vacuous subject is
      a refusal. A check that cannot fail is the same defect as the pointer it
      is checking.

    A fourth condition holds the CODE to the same document: the file this
    module actually reads its IRIs from — :data:`SOURCE_VOCABULARY` — must be
    among the ones the config names. A config and an interpreter pointing at
    two different documents is the same reader-stops-looking failure with one
    more step in it.
    """
    named: list[str] = []
    for block in _comment_blocks(CONFIG.read_text(encoding="utf-8")):
        if not _IRI_CLAIM.search(block):
            continue
        named.extend(_ARTIFACT_REFERENCE.findall(block))
    if not named:
        raise SystemExit(
            "ccf_config.yaml names NO document as the home of the six family"
            " predicates' IRIs. The pointer is not optional: a reader who"
            " cannot find the source vocabulary from the deployment document"
            " has the same problem as one sent to the wrong file."
        )
    wanted = set(family_predicate_iris().values())
    for filename in sorted(set(named)):
        target = ARTIFACTS / filename
        if not target.is_file():
            raise SystemExit(
                f"ccf_config.yaml points at artifacts/{filename} for the six"
                f" predicate IRIs and no such file exists."
            )
        held = target.read_text(encoding="utf-8")
        missing = sorted(iri for iri in wanted if iri not in held)
        if missing:
            raise SystemExit(
                f"ccf_config.yaml points at artifacts/{filename} for the six"
                f" predicate IRIs and it carries none of"
                f" {len(missing)} of them:\n  " + "\n  ".join(missing)
            )
    if SOURCE_VOCABULARY.name not in set(named):
        raise SystemExit(
            f"this module reads its predicate IRIs from"
            f" artifacts/{SOURCE_VOCABULARY.name}, and ccf_config.yaml points a"
            f" reader at {sorted(set(named))} instead."
        )
    return tuple(sorted(set(named)))


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


def resolve_anchor(lei: str, *, source: GraphSource | None = None) -> str | None:
    """The graph node the request's LEI names, or ``None``.

    **The request's ``subject`` is an LEI and the walk's anchor is an IRI**, and
    the step between them is a read rather than a formatting rule — nothing in
    this module can construct ``.../SuperMicroComputerInc`` from
    ``54930022CZO1N2UGVW07``, and a build that could would be minting node
    identity out of a string.

    ``None`` is a **404** and never an empty payload (spec section B.4). An
    empty family reads as *this company has no subsidiaries*, which is a claim
    about the world; an unresolvable anchor is a fact about the request.
    """
    resolved = source or graph_source()
    predicate = node_predicate_iris()[NODE_PREDICATE_LEI]
    with httpx.Client(timeout=_HTTP_TIMEOUT_SECONDS) as client:
        rows = _sparql(
            client,
            resolved,
            f"SELECT ?s {_from_clause(resolved)} WHERE {{"
            f" ?s <{predicate}> {json.dumps(lei)} }}",
        )
    for row in rows:
        found = _binding(row, "s")
        if found is not None:
            return found
    return None


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
# Entitlement — `D-IMPL-228`. THE FAMILY'S OBSERVED SET, CLOSED AT TWO VALUES.
# ---------------------------------------------------------------------------


def declared_classifications() -> tuple[str, ...]:
    """The jurisdictions this deployment declares — ``{NL, US-DE}``.

    From ``ccf_config.yaml``'s policy operator parameters, because that is the
    set ``src/ccf/operators/categories.py::PolicyFilter._admits`` actually
    tests membership against. Reading it from anywhere else would let the
    declaration and the enforcement drift.
    """
    declared = config()[KEY_OPERATORS][KEY_POLICY_OPERATOR]
    return tuple(str(value) for value in declared[KEY_PERMITTED_CLASSIFICATIONS])


def classification_attribute() -> str:
    """The attribute key both entity classes are classified on."""
    return str(source_vocabulary()[VOCAB_ENTITLEMENT][VOCAB_CLASSIFICATION_ATTRIBUTE])


def classification_sources() -> tuple[str, ...]:
    """Where a member's classification value comes from, in declared order."""
    declared = source_vocabulary()[VOCAB_ENTITLEMENT][VOCAB_CLASSIFICATION_SOURCES]
    return tuple(str(name) for name in declared)


def classify_family(
    *,
    anchor_uri: str,
    nodes: Sequence[str],
    node_leis: Mapping[str, str],
    rows: Mapping[str, Mapping[str, Any]],
) -> Mapping[str, str]:
    """One classification value per family member — ``D-IMPL-228``.

    **A MEMBER CARRIES ITS OWN JURISDICTION WHERE POSTGRESQL HOLDS A ROW, AND
    THE FAMILY'S — THE ANCHOR'S — WHERE IT DOES NOT.** The order comes from
    ``artifacts/source-vocabulary.yaml``'s ``classification_sources``, not from
    this function, and a declared source this module cannot honor raises rather
    than being skipped: a document declaring a provenance nobody implemented
    would leave the payload looking right and the declaration meaning nothing.

    **WHY THE SECOND SOURCE EXISTS, and it is the whole reason this product has
    a Policy step it can keep.** ``PolicyFilter._admits`` refuses a record whose
    classification attribute is ABSENT exactly as firmly as one whose value is
    out of grant. 20 of the SMCI subtree's 22 members hold no
    ``ccf_v2.legal_entity`` row, so under a per-node-only rule the Policy step
    deleted 20 of 22 — precisely the population ``CFT-G09`` and criterion 33
    exist to protect. It is not a leniency: a corporate family is the anchor's
    group, and a borrowing group is entitled as a group. Spec section B.2 draws
    the line this rests on — *"whether an edge to an entity in a restricted
    jurisdiction may be returned to a principal outside it is not the same
    question as whether that entity's attributes may be."* The TREE inherits;
    the ATTRIBUTES do not, and a member with no row is served with a null
    attribute resolution rather than with the anchor's figures.

    **THE THIRD ROUTE WAS MEASURED AND IS UNAVAILABLE, not argued away.**
    Deriving a missing value from the graph leg's own ``jurisdictionCode`` fails
    twice: the vocabularies differ (ISO 3166-1 alpha-3 against
    ``legal_jurisdiction``'s 3166-2-style values), and over the committed
    fixture **0 of the 22 subtree nodes carry a ``jurisdictionCode`` at all**. A
    mapping table nobody measured would have been mapping an empty set.

    **AN ANCHOR THAT RESOLVES TO NO JURISDICTION REFUSES.** There is no literal
    fallback below and no ``or "US"``. If the family's own head carries no
    classification, inheriting it would classify 22 members on a value nobody
    has — which is the shape a default is always mistaken for.
    """
    declared_sources = classification_sources()
    unknown = [
        name
        for name in declared_sources
        if name not in (CLASSIFICATION_OWN_ROW, CLASSIFICATION_FAMILY_ANCHOR)
    ]
    if unknown:
        raise SystemExit(
            f"artifacts/source-vocabulary.yaml declares classification"
            f" source(s) {unknown} that this deployment does not implement;"
            f" refusing to classify against a provenance nobody honors"
        )
    column = str(
        source_vocabulary()[VOCAB_ATTRIBUTES][VOCAB_JURISDICTION_COLUMN]
    )

    def own(uri: str) -> str | None:
        lei = node_leis.get(uri)
        if lei is None:
            return None
        value = rows.get(lei, {}).get(column)
        return str(value) if value else None

    anchor_value = own(anchor_uri) if CLASSIFICATION_OWN_ROW in declared_sources else None
    if CLASSIFICATION_FAMILY_ANCHOR in declared_sources and anchor_value is None:
        raise SystemExit(
            f"the anchor {anchor_uri!r} resolves to no {column!r}, so there is"
            f" no family classification for the {len(nodes)} members that carry"
            f" none of their own; refusing rather than inventing one"
        )

    classified: dict[str, str] = {}
    for uri in nodes:
        for name in declared_sources:
            value = own(uri) if name == CLASSIFICATION_OWN_ROW else anchor_value
            if value is not None:
                classified[uri] = value
                break
    return classified


def refuse_open_jurisdiction_world(classified: Mapping[str, str]) -> tuple[str, ...]:
    """Hold the declared set to the family's OBSERVED set, in both directions.

    **CLOSED WORLD, the same discipline ``artifacts/gates.yaml`` carries.**
    ``D-IMPL-228``: *"Declared jurisdictions = the family's observed set,
    closed."* ``PolicyFilter`` already refuses a member whose value is outside
    the declaration — that is the first direction, and it is the SDK's. This
    function adds the second, which the SDK has no reason to hold: **a DECLARED
    value that no family member exhibits is refused too.**

    The second direction is the one that matters, and Dave named why. The list
    this replaced carried nine values where the family exhibits two, and
    family-scoping over the nine would have admitted every member because the
    anchor is ``US-DE`` — for a reason unrelated to the other seven. *"Nine-row
    'coverage' is how idle gates look when the extra rows never fire."* A
    declared row that cannot fire is the idle-gate defect wearing a
    jurisdiction's name, and without this check the closed world is a
    convention rather than a gate: nothing else in the tree notices a list
    quietly re-widened.

    Returns the observed set, so a caller can see what the check ran against
    rather than taking a bare pass.

    The three named sabotages, and each is REFUSED here:

    * drop ``NL`` — ``SuperMicroComputerBV`` carries a value nobody declared;
    * drop ``US-DE`` — the anchor and the 20 members inheriting from it do;
    * add ``US-NY`` **as if it were in-family** — a declared row firing on
      nothing.

    An empty declaration is refused for the same reason the vacuity guard in
    :func:`refuse_stale_vocabulary_pointer` exists: over an empty family this
    would otherwise pass by having nothing to compare.
    """
    declared = set(declared_classifications())
    observed = set(classified.values())
    if not declared:
        raise SystemExit(
            "ccf_config.yaml declares an EMPTY permitted_classifications set;"
            " a policy envelope that admits nothing is not a narrower grant,"
            " it is an absent one"
        )
    if not classified:
        raise SystemExit(
            "no family member was classified, so the declared jurisdiction set"
            " has nothing to be held against; refusing a check that cannot fail"
        )
    undeclared = sorted(observed - declared)
    if undeclared:
        raise SystemExit(
            f"family members carry classification(s) {undeclared} that"
            f" ccf_config.yaml does not declare. The declared set is the"
            f" FAMILY'S OBSERVED SET and it is CLOSED (`D-IMPL-228`): an"
            f" unknown key is refused, never admitted."
        )
    idle = sorted(declared - observed)
    if idle:
        raise SystemExit(
            f"ccf_config.yaml declares jurisdiction(s) {idle} that no member of"
            f" this family exhibits. The declared set is the family's OBSERVED"
            f" set (`D-IMPL-228`); a row that never fires is how an idle gate"
            f" looks, and the observed set is {sorted(observed)}."
        )
    return tuple(sorted(observed))


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


# ---------------------------------------------------------------------------
# L1 — one envelope PER NODE, and the typed edges admitted beside them.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EntityRule:
    """One ``ccf_config.yaml`` entity rule, read rather than assumed.

    The rule's ``match_key`` is what selects it: `worker.py:211` skips a rule
    whose ``match_key`` is absent from the payload. That is the whole mechanism
    by which one envelope resolves to exactly ONE entity here — the anchor's
    envelope carries the anchor rule's key and no other, and a member's carries
    the member rule's.
    """

    match_key: str
    entity_class: str
    identity_keys: tuple[str, ...]
    attribute_keys: tuple[str, ...]


def entity_rules() -> tuple[EntityRule, ...]:
    """The declared entity rules, in declaration order."""
    declared = config()[KEY_RESOLUTION][KEY_ENTITY_RULES]
    return tuple(
        EntityRule(
            match_key=str(rule[KEY_MATCH_KEY]),
            entity_class=str(rule[KEY_ENTITY_CLASS]),
            identity_keys=tuple(str(key) for key in rule[KEY_IDENTITY_KEYS]),
            attribute_keys=tuple(
                str(key) for key in rule.get(KEY_ATTRIBUTE_KEYS, ())
            ),
        )
        for rule in declared
    )


def _rule_for(entity_class: str) -> EntityRule:
    for rule in entity_rules():
        if rule.entity_class == entity_class:
            return rule
    raise SystemExit(
        f"ccf_config.yaml declares no entity rule for {entity_class!r}; the"
        f" seed class and the resolution vocabulary have to agree or the walk"
        f" seeds an empty frontier"
    )


def anchor_entity_class() -> str:
    """Which declared class the ANCHOR is minted under.

    Read from the traversal operator's ``seed_entity_classes``, because that is
    the set `src/ccf/operators/categories.py` seeds the frontier from. Declaring
    an anchor class here that the walk does not seed on would produce a bounded
    walk that returned nothing and read as an empty family.
    """
    seeds = seed_entity_classes()
    if len(seeds) != 1:
        raise SystemExit(
            f"this deployment mints ONE anchor per request and"
            f" ccf_config.yaml seeds the walk from {list(seeds)}; a family with"
            f" two anchors is a different question than the one this product"
            f" answers"
        )
    return seeds[0]


def member_entity_class() -> str:
    """The other declared class. Every non-anchor family node is minted here."""
    anchor = anchor_entity_class()
    others = [rule.entity_class for rule in entity_rules() if rule.entity_class != anchor]
    if len(others) != 1:
        raise SystemExit(
            f"ccf_config.yaml declares entity classes"
            f" {[rule.entity_class for rule in entity_rules()]}; this"
            f" deployment mints exactly two — one anchor and one member class"
        )
    return others[0]


def build_envelopes(
    *,
    tenant: str,
    at: datetime,
    anchor_uri: str,
    facts: Mapping[str, NodeFacts],
    classified: Mapping[str, str],
) -> tuple[tuple[SignalEnvelope, ...], Mapping[str, str]]:
    """ONE ENVELOPE PER NODE — ``D-35``, ruled 2026-09-01.

    **The shape is forced by a measured property of the SDK, not chosen for
    tidiness.** ``src/ccf/assembly/worker.py:381`` mints relationship claims by
    CLASS CO-OCCURRENCE: every declared rule whose subject and object classes
    both resolve from one envelope fires, and nothing selects the relationship
    type from the payload. Measured live, one envelope carrying one
    ``entity_uri`` and matching both rules minted 2 entities — the same node
    under both classes, identical identity hash — and **twelve relationships,
    six of them self-loops**, spanning all six declared types.

    So each envelope carries the match key of exactly ONE rule and resolves to
    exactly ONE entity. With ``relationship_rules: []`` beside it, no
    relationship rule can fire at all — and the typed edges arrive instead
    through :func:`relationship_claims` and
    ``worker.admit_relationship_claim``, each carrying its TRUE predicate.
    **Still one writer, still L2, and no file under ``src/`` changes.**

    Returns the envelopes and a map from ``envelope_id`` back to the SOURCE
    node IRI. The spine needs that map because the graph mints its own
    ``entity_uri`` — ``<entity-class>://<identity-hash>`` (`worker.py:220`) —
    so the URI an edge must be built from is knowable only after ingest, from
    each ``IngestResult``'s own ``node_key``. Recomputing the hash here would
    be this module reimplementing L2's identity rule, which is exactly the
    duplication that goes stale in silence.

    **Every payload key comes from the declared rule**, and a rule declaring a
    key this module cannot supply raises. That refusal is what keeps
    ``attribute_keys`` a real declaration: without it, adding a key to the
    document would change nothing and look like it had.
    """
    envelopes: list[SignalEnvelope] = []
    by_envelope: dict[str, str] = {}
    anchor_rule = _rule_for(anchor_entity_class())
    member_rule = _rule_for(member_entity_class())
    system = SourceIdentity(system_id=SOURCE_GRAPH)
    for uri in sorted(facts):
        node = facts[uri]
        rule = anchor_rule if uri == anchor_uri else member_rule
        supplied: dict[str, Any] = {
            ATTR_ENTITY_URI: uri,
            NODE_PREDICATE_LEI: node.lei,
            NODE_PREDICATE_LABEL: node.label,
            NODE_PREDICATE_TYPE_CHAIN: _TYPE_CHAIN_SEPARATOR.join(node.type_chain),
            classification_attribute(): classified.get(uri),
        }
        payload: dict[str, Any] = {rule.match_key: uri}
        for key in (*rule.identity_keys, *rule.attribute_keys):
            if key not in supplied:
                raise SystemExit(
                    f"ccf_config.yaml's {rule.entity_class!r} rule declares"
                    f" payload key {key!r} and this deployment reads no such"
                    f" value out of either system of record"
                )
            value = supplied[key]
            # An ABSENT attribute is absent, never an empty string: `lei` and
            # `label` are nullable by section D.6, and a node with no LEI that
            # carried `""` would resolve in PostgreSQL against nothing while
            # LOOKING resolved.
            if value is not None:
                payload[key] = value
        envelope_id = f"family:{rule.entity_class}:{uri}"
        by_envelope[envelope_id] = uri
        envelopes.append(
            SignalEnvelope(
                tenant_id=tenant,
                envelope_id=envelope_id,
                source=system,
                ingestion_timestamp=at,
                # NO `observed_time`, AND THE ABSENCE IS DELIBERATE RATHER THAN
                # AN OVERSIGHT. `SignalEnvelope`'s own contract reads: "``None``
                # means unknown — L2 reconciles against the bitemporal T axis
                # rather than guessing a value here." Measured over the
                # committed fixture, **no family node and no family edge carries
                # an assertion date of any kind** — the ledger holds the six
                # predicates, `ex:lei`, `rdfs:label` and `rdf:type`, and no
                # timestamp. Fluree's own `t` is TRANSACTION time and
                # `D-IMPL-88` rules it must not stand in for an observation, so
                # the honest value is unknown. See `FamilyScenario.expires_at`
                # for what that costs the declared TTL anchor.
                raw_payload=payload,
            )
        )
    return tuple(envelopes), by_envelope


def relationship_claims(
    *,
    tenant: str,
    at: datetime,
    edges: FamilyEdges,
    nodes: Sequence[str],
    minted: Mapping[str, str],
    envelopes_by_node: Mapping[str, str],
) -> tuple[RelationshipClaim, ...]:
    """The typed parent-to-child edges, ready for L2's admission path.

    **EACH CLAIM CARRIES ITS TRUE PREDICATE** — the ruled half of ``D-35``. One
    claim per (pair, predicate), so a pair the source asserts under both
    ``owns`` and ``hasGlobalUltimateParent`` becomes two typed edges rather than
    one edge under a predicate somebody picked. That is not a duplication: the
    source really does say both things, and collapsing them would decide which
    assertion to discard.

    The subject and object are the **MINTED** URIs, taken from what
    ``worker.ingest`` reported for each node's envelope. Nothing here mints a
    URI, so L2's identity rule stays L2's.

    **LINEAGE NAMES BOTH ENDPOINTS' ENVELOPES.** An edge was observed in the
    same graph read that produced the node facts on both ends of it, so both
    envelopes are genuine evidence for it and ``LineageEntry`` is a frozenset
    precisely so multi-source evidence accumulates by set-union (INV-CH7-17).
    Naming only one end would be choosing an arbitrary half of the provenance
    and would make the L axis quietly incomplete.

    Edges are restricted to the node set passed in, so an edge whose far end was
    dropped upstream — an untyped node, per section D.6 — is not admitted
    pointing into nothing.
    """
    admissible = set(nodes)
    system = SourceIdentity(system_id=SOURCE_GRAPH)
    claims: list[RelationshipClaim] = []
    for parent, child in sorted(edges.by_pair):
        if parent not in admissible or child not in admissible:
            continue
        if parent not in minted or child not in minted:
            continue
        lineage = frozenset(
            LineageEntry(source=system, envelope_id=envelope_id, observed_at=at)
            for envelope_id in (
                envelopes_by_node[parent],
                envelopes_by_node[child],
            )
        )
        for predicate in sorted(edges.predicates_for((parent, child))):
            claims.append(
                RelationshipClaim(
                    tenant_id=tenant,
                    relationship_type=predicate,
                    subject_uri=minted[parent],
                    object_uri=minted[child],
                    observed_at=at,
                    valid_from=at,
                    lineage=lineage,
                )
            )
    return tuple(claims)


# ---------------------------------------------------------------------------
# The two source reads, composed — and what one run needs.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FamilySourceRead:
    """Everything the two systems of record answered for one question."""

    anchor_uri: str | None
    facts: Mapping[str, NodeFacts]
    edges: FamilyEdges
    findings: tuple[Finding, ...]
    attributes: AttributeResolution
    classifications: Mapping[str, str]
    observed_classifications: tuple[str, ...]
    envelopes: tuple[SignalEnvelope, ...]
    envelopes_by_node: Mapping[str, str]
    collapsed: int
    ledger_t: int | None
    stores_opened: tuple[str, ...]


def source_read(
    tenant: str,
    *,
    at: datetime,
    subject: str,
    graph: GraphSource | None = None,
    attributes: AttributeSource | None = None,
) -> FamilySourceRead:
    """Open BOTH systems of record, each for its declared role.

    **``CFT-G10`` READS THIS FUNCTION.** The gate asserts that THE ASSEMBLY
    opened Fluree and PostgreSQL — not that the runner did (criterion 34, as
    clarified by Dave at Gate 1). ``stores_opened`` is the evidence, recorded
    where the connections are actually made rather than asserted by a caller
    that could have been handed a pre-populated graph. Policy is **not** that
    proof and is not consulted for it: ``D-IMPL-228`` says so in terms.

    The order is: resolve the anchor, walk to the DECLARED CEILING, read the
    node facts, batch-resolve the attributes, classify, then close the
    jurisdiction world. The classification runs before any envelope is built,
    because a member's classification is part of the claim L2 will admit, and
    the closed-world refusal runs before anything is served.
    """
    resolved_graph = graph or graph_source()
    refuse_stale_vocabulary_pointer()
    anchor_uri = resolve_anchor(subject, source=resolved_graph)
    empty = AttributeResolution(rows={}, statements=(), requested=())
    if anchor_uri is None:
        return FamilySourceRead(
            anchor_uri=None,
            facts={},
            edges=FamilyEdges(by_pair={}),
            findings=(),
            attributes=empty,
            classifications={},
            observed_classifications=(),
            envelopes=(),
            envelopes_by_node={},
            collapsed=0,
            ledger_t=ledger_t(resolved_graph),
            stores_opened=(SOURCE_GRAPH,),
        )

    triples = walk_from_anchor(anchor_uri, source=resolved_graph)
    edges = normalize_edges(triples)
    # The anchor is a family of one where the ledger holds no family edge for
    # it, and it is still a member of its own tree.
    reached = sorted(edges.nodes | {anchor_uri})
    facts = read_node_facts(reached, source=resolved_graph)

    resolved_attributes = attributes or attribute_source()
    node_leis = {uri: node.lei for uri, node in facts.items() if node.lei}
    attribute_rows = resolve_attributes(
        tuple(sorted(set(node_leis.values()))), source=resolved_attributes
    )

    classified = classify_family(
        anchor_uri=anchor_uri,
        nodes=tuple(sorted(facts)),
        node_leis=node_leis,
        rows=attribute_rows.rows,
    )
    observed = refuse_open_jurisdiction_world(classified)

    envelopes, by_envelope = build_envelopes(
        tenant=tenant,
        at=at,
        anchor_uri=anchor_uri,
        facts=facts,
        classified=classified,
    )
    findings = (
        *detect_cycles(edges),
        *surface_duplicate_pairs(
            {uri: node.label for uri, node in facts.items() if node.label}
        ),
    )
    return FamilySourceRead(
        anchor_uri=anchor_uri,
        facts=facts,
        edges=edges,
        findings=findings,
        attributes=attribute_rows,
        classifications=classified,
        observed_classifications=observed,
        envelopes=envelopes,
        envelopes_by_node={uri: eid for eid, uri in by_envelope.items()},
        collapsed=collapse(triples, edges),
        ledger_t=ledger_t(resolved_graph),
        stores_opened=(SOURCE_GRAPH, SOURCE_ATTRIBUTES),
    )


@dataclass(frozen=True)
class FamilyScenario:
    """This deployment's answers to what the spine asks for.

    Satisfied STRUCTURALLY by the spine's ``Scenario`` Protocol, exactly as
    rungs 02 and 03 do it — this class imports nothing from ``produce.py`` and
    ``produce.py`` will name no member of this one. Plan ``24.4-07`` writes that
    Protocol against this shape; the dependency points one way.
    """

    envelopes: tuple[SignalEnvelope, ...]
    envelopes_by_node: Mapping[str, str]
    request: ProductRequest
    request_contract: ProductRequestContract
    product_class: ProductClassDeclaration
    perspective: PerspectiveArtifact
    operator_parameters: Mapping[str, OperatorParametersArtifact]
    resolution: EntityResolutionSpec
    half_life_table: HalfLifeTable
    debt_profile: DebtProfile
    anchor_uri: str
    max_depth: int
    facts: Mapping[str, NodeFacts]
    edges: FamilyEdges
    findings: tuple[Finding, ...]
    attributes: AttributeResolution
    classifications: Mapping[str, str]
    observed_classifications: tuple[str, ...]
    collapsed: int
    ledger_t: int | None
    stores_opened: tuple[str, ...]
    ttl_seconds: int
    max_ttl_seconds: int
    halflife_debt_profile: str
    debt_tolerance: str

    request_contract_key: str = KEY_REQUEST_CONTRACT
    policy_bundle_key: str = KEY_POLICY_BUNDLE
    replay_record_class: str = REPLAY_RECORD_CLASS
    query_pin_class: str = QUERY_PIN_CLASS
    artifact_store_dirname: str = ARTIFACT_STORE_DIRNAME

    @property
    def plan_id(self) -> str:
        return self.product_class.schema_name

    @property
    def temporal_boundary(self) -> datetime:
        """Off the request, never off a clock — so replay feeds it back."""
        return self.request.asked_at

    @property
    def now(self) -> datetime:
        return self.request.asked_at

    @property
    def depth_by_node(self) -> Mapping[str, int]:
        """Breadth-first depth from the anchor at the CALLER's ``max_depth``.

        **This is the deployment's own reading and not what the payload is
        built from.** The served member set comes out of the L4 traversal
        operator, whose ``depth_limit`` :func:`traversal_parameters` binds to
        this same value — which is what puts depth into the parameter set's
        content hash. This property exists so a caller can render the depth
        beside each member, and it is a second computation of the same number,
        deliberately: if the two ever disagree, the walk is not doing what the
        operator parameters say it is.
        """
        return self.edges.reach(self.anchor_uri, depth_limit=self.max_depth)

    @property
    def expires_at(self) -> datetime:
        """The declared TTL applied to the anchor ``ttl.yaml`` names.

        **AND THE ANCHOR DEGENERATES AT THIS RUNG, WHICH IS RECORDED RATHER
        THAN HIDDEN.** ``ttl.yaml`` declares
        ``ttl_anchor_basis: latest_family_edge_assertion_time_in_payload`` and
        ``product_class.ttl_anchor: from_entity_freshness``. Measured over the
        committed fixture, **no family edge and no family node carries an
        assertion date of any kind** — the ledger holds the six predicates,
        ``ex:lei``, ``rdfs:label`` and ``rdf:type``, and no timestamp. So the
        latest assertion time the payload can honestly report is the instant the
        payload was read, and every envelope carries ``observed_time=None`` to
        say the source could not tell us.

        The consequence is that this expiry is the request instant plus the
        declared window, which is what a read-time anchor gives. **It is not
        equivalent to rung 03's**, whose anchor moved with a filing date. This
        is a finding for the TTL artifact and for the spine that refuses on it,
        not something to fix by picking a date: Fluree's ``t`` is TRANSACTION
        time and ``D-IMPL-88`` rules it must not back an observation axis, so
        there is no second candidate in the store either.
        """
        return self.request.asked_at + timedelta(seconds=self.ttl_seconds)


def read(
    booted: BootedFabric,
    asked: ProductRequest,
    *,
    max_depth: int,
) -> FamilyScenario | None:
    """Name this deployment's artifact keys and read this question's values.

    ``max_depth`` is resolved by :func:`resolve_max_depth` **before** this
    function, and that is a deliberate split rather than an awkward signature:
    an over-ceiling depth is a **400** carried as a
    :class:`DepthOutOfBounds` and an unresolvable anchor is a **404** carried as
    ``None``, and one return type cannot hold both without the caller having to
    tell them apart by inspection. The refusals stay distinguishable.

    Returns ``None`` when the anchor resolves to nothing. *An anchor that
    resolves to no entity is never an empty payload* — an empty family reads as
    a claim about the world.
    """
    artifacts = booted.artifacts
    read_source = source_read(
        booted.tenant_id, at=asked.asked_at, subject=asked.subject
    )
    if read_source.anchor_uri is None:
        return None

    # THE POLICY PARAMETERS PASS THROUGH DECLARED, and rung 03's shape is
    # deliberately NOT copied here. Rung 03 built them per request from the
    # calling principal's grant read out of the estate, because it had measured
    # a real discrimination — 49 / 47 / 0 / 0 across four principals. NO
    # EQUIVALENT MEASUREMENT HAS BEEN TAKEN OVER THE FAMILY POPULATION (spec
    # section F.4 row 6, still open), so this rung declares a CLOSED set and
    # reads it as declared. Inventing a per-principal expansion here would be
    # asserting a discrimination nobody measured.
    declared_policy = cast(OperatorParametersArtifact, artifacts[KEY_POLICY_OPERATOR])
    declared_traversal = cast(
        OperatorParametersArtifact, artifacts[KEY_TRAVERSAL_OPERATOR]
    )
    return FamilyScenario(
        envelopes=read_source.envelopes,
        envelopes_by_node=read_source.envelopes_by_node,
        request=asked,
        request_contract=ProductRequestContract.from_declared(
            cast(Any, artifacts[KEY_REQUEST_CONTRACT])
        ),
        product_class=cast(ProductClassDeclaration, artifacts[KEY_PRODUCT_CLASS]),
        perspective=cast(PerspectiveArtifact, artifacts[KEY_PERSPECTIVE]),
        # TWO entries, so a two-operator registry — this is the rung where the
        # count moves off one. The traversal set carries the CALLER's depth;
        # the policy set carries the declared closed jurisdiction world.
        operator_parameters={
            KEY_POLICY_OPERATOR: declared_policy,
            KEY_TRAVERSAL_OPERATOR: traversal_parameters(
                declared_traversal, max_depth=max_depth
            ),
        },
        resolution=cast(EntityResolutionSpec, artifacts[KEY_RESOLUTION]),
        half_life_table=cast(HalfLifeTable, artifacts[KEY_HALF_LIFE_TABLE]),
        debt_profile=cast(DebtProfile, artifacts[KEY_DEBT_PROFILE]),
        anchor_uri=read_source.anchor_uri,
        max_depth=max_depth,
        facts=read_source.facts,
        edges=read_source.edges,
        findings=read_source.findings,
        attributes=read_source.attributes,
        classifications=read_source.classifications,
        observed_classifications=read_source.observed_classifications,
        collapsed=read_source.collapsed,
        ledger_t=read_source.ledger_t,
        stores_opened=read_source.stores_opened,
        ttl_seconds=declared_ttl_seconds(),
        max_ttl_seconds=max_ttl_seconds(),
        # A PINNED REFERENCE, never the resolved artifact: the profile has its
        # own version lane, and inlining it would give one record two version
        # identities.
        halflife_debt_profile=(
            f"ccf-artifact://{booted.tenant_id}/ccf.debt-profile/"
            f"{KEY_DEBT_PROFILE}@{booted.pins.version_for(KEY_DEBT_PROFILE)}"
        ),
        # Carried AS DATA and computed nowhere in this module — see the module
        # docstring for why `D_c` belongs with the spine that refuses on it.
        debt_tolerance=str(demonstration_parameters()["debt_tolerance"]),
    )
