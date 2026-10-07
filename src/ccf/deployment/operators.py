"""From operator-parameters artifacts plus a graph view to a populated registry.

SDK-defined mechanism (CLAUDE.md §6.4 and §10) over whitepaper §7.4 (the four
canonical operator categories and the algebra they compose under). The
whitepaper specifies what an operator *is* and what ordering the planner must
impose; it does not specify the wiring that turns a deployment's declared
parameter artifacts into a registry. That wiring is this module, and — like the
rest of :mod:`ccf.deployment` — it is marshalling and construction only.

Why the view is in the signature (D-07)
---------------------------------------

Three of the four categories are pure parameter reads. The fourth is not:
:class:`~ccf.operators.categories.SimilaritySelect` ranks against an injected
index, and that index is built from a **corpus read out of the live graph at a
named temporal boundary** — after boot and after ingest. So this builder cannot
be a pure artifact read, and the honest way to say that is to require the view.

``view`` is therefore a required keyword argument with no default. The ordering
constraint lives in the signature rather than in prose: a registry cannot be
built before there is a view, and a view exists only after the deployment has
booted, ingested, and named the boundary it wants.

**Lazy binding was considered and rejected.** Handing the operator a callable
that built the index at first invocation would make the signature tidier and
would move index construction into the projection engine's execution — inside
the algorithmic path, over a corpus determined by *when the engine happened to
invoke the operator* rather than by a boundary the deployment named. INV-CH7-27
fixes the similarity determinism contract as ``(corpus_version,
embedding_model_version, query, threshold, policy_regime) -> same result``; a
corpus that is a function of invocation timing is not a corpus that contract
can name.

The corpus-extraction ruling: skip a class, refuse a missing attribute
----------------------------------------------------------------------

``similarity_corpus_attribute_by_class`` maps ``entity_class -> attribute key``.
Two things can go wrong when reading a corpus through it, and they get opposite
answers. Both are stated here because nine deployments will follow whatever this
module does, and an unstated rule becomes nine divergent readings.

* **An entity class absent from the map contributes no corpus entry.** Silent,
  and correct: the map is the deployment's *statement of which classes are
  rankable*. A class it does not name is a class the deployment chose not to put
  in the corpus, exactly as
  :class:`~ccf.controlplane.artifacts.SimilaritySelectParametersArtifact` already
  records. There is nothing to repair and nothing to report.
* **An entity whose class the map names, but which carries no such attribute,
  is refused.** :class:`SimilarityCorpusAttributeError`, loudly, at build time.
  The deployment declared "this class's corpus text lives at attribute A" and an
  instance of that class has no A — the declaration and the graph contradict each
  other. Every repair is worse than the refusal: skipping the entity drops it
  from the corpus, :meth:`~ccf.similarity.protocol.TokenOverlapIndex.rank` then
  silently passes over it, and the similarity operator excludes it from the
  view — a governed omission produced by no rule anyone wrote down. Substituting
  an empty string is the same omission with a scoring story attached. **Refuse,
  never repair.**

A corpus value that is not a string is refused by the same rule and for the same
reason: it would otherwise fail deep inside ranking, at invocation time, far from
the artifact that declared it.

What this module is not
-----------------------

It does not run gates, and it may not import :mod:`ccf.products.gates` — the
``cinv02-deployment-gates`` lint rule takes no allowlist. See the package
docstring for D-15A.

It also does not answer "which operators does this product require". The
returned registry's :meth:`~ccf.operators.registry.OperatorRegistry.keys` is
what the fabric *resolved*; the declared side of the empty-operator gate is
:attr:`~ccf.controlplane.artifacts.ProductClassDeclaration.required_operator_keys`,
authored in the product-class artifact. Passing this registry's keys to **both**
sides of that comparison makes the gate compare a value against itself, which is
the tautology :mod:`ccf.products.gates` exists to avoid. This builder
deliberately exposes no "required keys" convenience that would make that easier
to write than to avoid.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ccf.controlplane.artifacts import (
    OperatorParametersArtifact,
    PolicyFilterParametersArtifact,
    RequestBoundParameter,
    SimilaritySelectParametersArtifact,
    TemporalAsOfParametersArtifact,
    TraversalDescendantsParametersArtifact,
    TraversalNeighborhoodParametersArtifact,
)
from ccf.deployment.pins import ResolvedPins
from ccf.graph.protocols import GraphView, require_classification_authority
from ccf.operators.base import Operator, read_intent_of
from ccf.operators.categories import (
    PolicyFilter,
    SimilaritySelect,
    TemporalAsOf,
    TraversalDescendants,
    TraversalNeighborhood,
)
from ccf.operators.params import PolicyFilterParameters, SimilaritySelectParameters
from ccf.operators.registry import OperatorRegistry
from ccf.similarity.protocol import TokenOverlapIndex

__ccf_mode__ = "algorithmic"

__all__ = ["SimilarityCorpusAttributeError", "build_operator_registry"]


class SimilarityCorpusAttributeError(ValueError):
    """An entity's declared corpus attribute is missing or is not text.

    Raised at registry-build time, never at rank time. See the module docstring
    for why this is a refusal rather than a skip: the alternative is an entity
    silently absent from the corpus, and therefore silently excluded from every
    ranked view, by no rule the deployment wrote down.
    """


def _corpus(
    view: GraphView, *, attribute_by_class: Mapping[str, str]
) -> dict[tuple[str, str], str]:
    """Read the ranking corpus out of ``view`` at the boundary it was taken at.

    Args:
        view: The graph state at the boundary the deployment named.
        attribute_by_class: ``entity_class -> attribute key``, from the
            similarity artifact's own field.

    Returns:
        ``(tenant_id, entity_uri) -> text`` for every entity whose class the map
        names. Entities of unnamed classes are absent, deliberately.

    Raises:
        SimilarityCorpusAttributeError: an entity of a named class carries no
            such attribute, or carries a non-string value under it.
    """
    corpus: dict[tuple[str, str], str] = {}
    for record in view.entities:
        attribute = attribute_by_class.get(record.claim.entity_class)
        if attribute is None:
            # The deployment did not name this class. Nothing to read, nothing
            # to report — see the module docstring's ruling.
            continue
        if attribute not in record.claim.attributes:
            raise SimilarityCorpusAttributeError(
                f"entity {record.claim.entity_uri!r} of class"
                f" {record.claim.entity_class!r} carries no attribute"
                f" {attribute!r}, which the similarity parameters artifact names"
                " as that class's corpus attribute; the declaration and the"
                " graph contradict each other and the fabric does not guess"
                " which is right"
            )
        text = record.claim.attributes[attribute]
        if not isinstance(text, str):
            raise SimilarityCorpusAttributeError(
                f"entity {record.claim.entity_uri!r} carries a"
                f" {type(text).__name__} under its declared corpus attribute"
                f" {attribute!r}; a corpus entry is text, and coercing one here"
                " would move the failure into ranking, far from the artifact"
                " that declared it"
            )
        corpus[(view.tenant_id, record.claim.entity_uri)] = text
    return corpus


def build_operator_registry(
    *,
    parameters: Mapping[str, OperatorParametersArtifact],
    view: GraphView,
    pins: ResolvedPins,
    policy_bundle_key: str,
    deployment_operators: Sequence[Operator] = (),
) -> OperatorRegistry:
    """Build a populated :class:`~ccf.operators.registry.OperatorRegistry`.

    Two phases in one call: parameter-only operators first, then the
    index-backed one, which needs the corpus read out of ``view``.

    **Which operators exist is per-deployment policy**, expressed by which
    artifacts ``parameters`` contains. A deployment registering three of the four
    categories passes three entries and gets a three-operator registry; this
    module holds no fixed set of four keys, no operator key literal, and no
    entity class literal (CINV-01). The Traversal category has two artifact
    classes — the undirected neighborhood and the directed descendants walk
    (ledger row ``24.5-L-06``) — and a deployment may register both: they are
    different keys under one category (D-IMPL-223).

    Registration goes through ``register(operator)`` with **no category
    argument**. The registry reads category and parameter schema off the
    operator, and a builder that re-introduced a caller-declared category would
    let the planner order an operator into a position it does not belong in —
    the Policy-after-Similarity failure INV-CH7-26 forbids.
    :class:`~ccf.operators.registry.DuplicateOperatorKey` stays fatal and is not
    caught: two operators answering to one key make every plan naming it
    ambiguous.

    Args:
        parameters: Manifest key -> parsed operator-parameters artifact. Typed
            against the **artifact** marker base, not against
            :class:`~ccf.operators.base.OperatorParameters`, for two reasons.
            First, :class:`~ccf.controlplane.artifacts.PolicyFilterParametersArtifact`
            is deliberately *not* a
            :class:`~ccf.operators.params.PolicyFilterParameters` (D-IMPL-76): it
            declares no ``permitted_policy_bundle_versions``, so a raw policy
            artifact is structurally incapable of being used as an operator
            parameter set, and this builder is the only supported thing that
            completes it. Second, the marker base is what lets an adopter
            assemble this mapping by naming its own manifest keys —
            ``{key: booted.artifacts[key] for key in (...)}`` — rather than
            ``isinstance``-filtering four unrelated classes at every call site,
            which would be a new duplication class of exactly the kind this
            surface exists to remove.
        view: Graph state at the temporal boundary the deployment named.
            Required, no default; see the module docstring.
        pins: The adopter's resolved pin set. Passed **in**, never discovered
            here (D-IMPL-76): the deployment names which policy bundle it
            admits, and the SDK only looks the pin up. There is no
            ``resolve_latest`` in this module — a builder that asked the registry
            what to admit would be the fabric deciding its own admission set.
        policy_bundle_key: The manifest key whose pinned version becomes the
            single admitted policy-bundle version. Read only when ``parameters``
            carries a policy artifact.
        deployment_operators: Already-constructed operators the *deployment*
            owns, registered into this same registry so the operator plan can
            resolve them (D-59). Defaulted and keyword-only, so every call site
            that predates this seam is unchanged. **Registered FIRST**, before
            the manifest's own dispatch, and **sorted by** ``operator.key`` so
            registration order is a function of the operators rather than of the
            caller's sequence order — the same discipline the manifest loop
            below already keeps. Registering first is what makes a collision
            symmetric: a manifest operator colliding with a deployment operator
            and a deployment operator colliding with a manifest operator both
            raise from the manifest loop, so there is one failure site rather
            than two.

            **The honest weakness of this channel, stated because a limitation
            that lives only in a plan document is one its next reader does not
            know.** A deployment operator's parameters do **not** travel as a
            Control Plane artifact here (D-IMPL-38): the operator *instance*
            carries them, and it is the caller's job to have built that instance
            from an artifact. The manifest path above takes artifacts and
            constructs operators; this path takes operators. That asymmetry is
            deliberate — the SDK cannot know how to construct an operator it has
            never seen — but it means this channel carries no pin and the
            replay-determinism argument for these operators rests on the
            caller's own artifact discipline, not on this builder's.

            **A known, deliberate limit.**
            :class:`~ccf.products.resolver.GovernedResolver` and
            :func:`~ccf.products.resolver.build_governed_resolver` have no
            channel to pass these through: they build the registry inline and
            consume it in the same expression chain. Handing this builder's
            result to :class:`~ccf.projection.engine.ProjectionEngine` directly
            — what every shipped example spine does — is the supported route.
            ``ccf/products/resolver.py`` is outside this phase's ruled file
            roster (D-IMPL-214) and was deliberately not touched.

    Returns:
        The populated registry. Nothing is sealed and nothing is frozen — the
        registry is already append-only with no ``unregister``.

    **Where the similarity index version comes from, and why it is not an
    argument** (``24.11-02b`` / ``D-IMPL-292``). It is read off the similarity
    artifact's
    :attr:`~ccf.controlplane.artifacts.SimilaritySelectParametersArtifact.index_version`,
    which is its canonical declarative home. Until ``24.11-02b`` this builder
    took it as a keyword argument, and that made a **decision-affecting semantic
    value** something every caller restated in code — a corpus identity the pin
    set could not see and replay could not be held against. Two refusals used to
    guard the pairing here, one for each direction of mismatch; both are gone
    because neither failure is expressible any more. An artifact with no version
    cannot parse (the field is required), and a version with no artifact has
    nowhere to be supplied from. **A runtime check became a structural
    guarantee**, which is the direction that trade is worth making.

    Deliberately **not** a precedence order between a declared value and a
    passed one. Dave, ``D-IMPL-292``: *"deployment supplies the implementation,
    not an alternate semantic version."* Two disagreeing versions mean two
    different corpora, and silently choosing either makes the determination
    irreproducible — so there is one site rather than a rule for reconciling
    two. (This is a deliberate departure from ``D-IMPL-282`` ``R-12`` ``D-04``,
    where an explicit argument *does* outrank the Control Plane. That is right
    for a **binding** — deployment wiring the Control Plane may default — and
    wrong for a semantic version identity. Same principle, opposite mechanism,
    on purpose.)

    **Classification authority is checked here, at construction** (SEC-023,
    ``D-IMPL-374`` ruling (3) (a)). Every Policy operator this builder
    constructs from a ``PolicyFilterParametersArtifact``, and every operator in
    ``deployment_operators`` whose declared read intent carries a
    classification map, is checked against the
    :class:`~ccf.graph.protocols.ClassificationAuthority` ``view`` was read
    under — the authority ``ccf.boot.boot`` stamps from the resolution spec its
    L2 enforces — before it is registered. The four call shapes the
    boot-time door check never saw (a hand-built operator, a hand-composed
    boot, a per-request build) all pass through here.

    Raises:
        ccf.graph.protocols.ClassificationAuthorityMissing: a classification
            consumer is built over a ``view`` that carries no authority (a
            hand-built view, or one read from a store no boot composed) —
            fail closed.
        ccf.graph.protocols.UngovernedClassificationAttribute: a
            classification consumer admits on an attribute the resolution spec
            writes from the source payload with no ``attribute_authorities``
            declaration.
        ValueError: ``parameters`` holds an artifact of no recognized operator
            category.
        SimilarityCorpusAttributeError: the corpus could not be read; see
            :func:`_corpus`.
        ccf.operators.registry.DuplicateOperatorKey: two entries produce the same
            operator key — whether both come from ``parameters``, both from
            ``deployment_operators``, or one from each. Deliberately uncaught
            across the new channel as well as the old.
        ccf.deployment.pins.UnpinnedArtifactError: ``policy_bundle_key`` names no
            ``role: register`` manifest entry.
    """
    registry = OperatorRegistry()
    similarity: SimilaritySelectParametersArtifact | None = None

    # Phase zero: the deployment's own operators (D-59). `register` takes NO
    # category argument — category and parameter schema are read off the
    # operator, because a caller-declared category would let the planner order
    # an operator into a position it does not belong in, the
    # Policy-after-Similarity failure INV-CH7-26 forbids. Sorted by key for the
    # same reason the manifest loop is sorted, and registered before it so a key
    # collision raises from one place rather than two.
    for operator in sorted(deployment_operators, key=lambda candidate: candidate.key):
        # SEC-023 (`D-IMPL-374` ruling (3) (a)): a hand-built operator carries
        # no artifact the boot-time door check could read, so its declared
        # classification map is checked here, against the authority the view
        # was read under, before it can be built into a registry.
        intent = read_intent_of(operator)
        require_classification_authority(
            view,
            None if intent is None else intent.classification_attribute_by_class,
            consumer=operator.key,
        )
        registry.register(operator)

    # Phase one: the parameter-only categories. Sorted so registration order is
    # a function of the manifest keys, not of mapping iteration order.
    for key, parameter in sorted(parameters.items()):
        if isinstance(parameter, TraversalNeighborhoodParametersArtifact):
            registry.register(TraversalNeighborhood(parameters=parameter))
        elif isinstance(parameter, TraversalDescendantsParametersArtifact):
            # The directed sibling (ledger row 24.5-L-06). The two artifact
            # classes share only the marker base, so neither `isinstance`
            # can match the other's document; the arm order is not
            # load-bearing. The class selects the direction — the document
            # carries no value that could.
            registry.register(TraversalDescendants(parameters=parameter))
        elif isinstance(parameter, TemporalAsOfParametersArtifact):
            registry.register(TemporalAsOf(parameters=parameter))
        elif isinstance(parameter, PolicyFilterParametersArtifact):
            # `24.11-04` / `24.10-F-11` (`D-IMPL-295`). An UNRESOLVED binding
            # must never reach an operator: `GovernedResolver` replaces every
            # `RequestBoundParameter` with the governed effective value before
            # building this registry, so one arriving here means the artifact
            # took a path that skipped that step. Refused by name rather than
            # narrowed with a cast — a cast would let the operator receive a
            # declaration object where it expects the set it filters on, and
            # admit nothing while looking fully configured, which is the exact
            # silent failure `PolicyFilterParametersArtifact`'s own docstring
            # exists to prevent.
            if isinstance(
                parameter.permitted_classifications, RequestBoundParameter
            ):
                raise ValueError(
                    f"operator parameters {key!r} declare"
                    " `permitted_classifications` as bound to request parameter"
                    f" {parameter.permitted_classifications.parameter!r}, and it"
                    " reached the registry builder unresolved. A request-bound"
                    " operator parameter is resolved by"
                    " `ccf.products.resolver.GovernedResolver` against the"
                    " EFFECTIVE request; a caller building a registry directly"
                    " has no request and therefore cannot honor the binding"
                )
            # SEC-023 (`D-IMPL-374` ruling (3) (a)): a per-request registry has
            # no `load_and_boot` spine behind it, so the consumer's
            # classification map is checked here against the authority the
            # view was read under — a view with none is refused, fail closed.
            require_classification_authority(
                view, parameter.classification_attribute_by_class, consumer=key
            )
            # The one conversion in this module. Constructed explicitly rather
            # than by `model_copy(update=...)`: the artifact is not a
            # PolicyFilterParameters, so there is nothing to copy from, and the
            # explicit construction is the single visible place where the
            # admitted-bundle set is assembled (D-IMPL-76).
            registry.register(
                PolicyFilter(
                    parameters=PolicyFilterParameters(
                        permitted_policy_bundle_versions=frozenset(
                            {pins.version_for(policy_bundle_key)}
                        ),
                        classification_attribute_by_class=(
                            parameter.classification_attribute_by_class
                        ),
                        permitted_classifications=parameter.permitted_classifications,
                    )
                )
            )
        elif isinstance(parameter, SimilaritySelectParametersArtifact):
            similarity = parameter
        else:
            raise ValueError(
                f"manifest key {key!r} carries a"
                f" {type(parameter).__name__}, which names no canonical operator"
                " category; the builder does not guess which operator a"
                " deployment meant"
            )

    if similarity is None:
        return registry

    # Phase two: the index-backed category. The single `isinstance` narrowing to
    # the artifact type lives here, in SDK code, precisely so that it does not
    # have to live in every adopter file that needs the corpus attribute map.
    #
    # `24.11-02b` / `D-IMPL-292`. BOTH construction-time values come off the one
    # narrowed artifact — the corpus map and the corpus's version identity. The
    # version used to arrive as a keyword argument, guarded by a pair of
    # runtime refusals for the two directions of mismatch; it now arrives from
    # the declaration that already had to be present for this branch to run at
    # all, so neither mismatch is expressible and neither refusal is needed.
    # The declaration is the authority: nothing here reconciles it against a
    # deployment-supplied second opinion, because there is no second site to
    # hold one.
    registry.register(
        SimilaritySelect(
            parameters=SimilaritySelectParameters(
                query=similarity.query,
                minimum_score_percent=similarity.minimum_score_percent,
                ranked_entity_classes=similarity.ranked_entity_classes,
            ),
            index=TokenOverlapIndex(
                corpus=_corpus(
                    view,
                    attribute_by_class=(
                        similarity.similarity_corpus_attribute_by_class
                    ),
                ),
                index_version=similarity.index_version,
            ),
        )
    )
    return registry
