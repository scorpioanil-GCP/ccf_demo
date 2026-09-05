"""Class-id → :class:`~ccf.controlplane.artifacts.ArtifactClass` resolution.

SDK-defined mechanism (CLAUDE.md §6.4 and §10), not whitepaper-derived. The
whitepaper fixes that Control Plane artifacts are typed and versioned; it says
nothing about how a *deployment manifest* names one. A manifest declares each
artifact by ``path, key, class``, where ``class`` is a string — so something has
to turn that string into the contract that validates the document.

:mod:`ccf.controlplane.artifacts` deliberately has no registry: its
:class:`~ccf.controlplane.artifacts.ArtifactClass` values are module-level
constants that callers import by name. That is the right shape for callers who
know statically which class they want, and the wrong shape for a manifest, whose
whole point is that it does not. This module supplies the missing direction, and
nothing else.

Two paths, and the split is the D-01 line
-----------------------------------------

* A class-id the SDK **owns** resolves to the SDK's own constant, from
  :data:`SDK_ARTIFACT_CLASSES` or :data:`SDK_VERSIONED_ARTIFACT_CLASSES` — two
  hand-maintained mappings, reviewed with the code (the shape of
  ``tools/lints/__main__.py::CHECKERS``). They are written out by name rather
  than scanned out of ``globals()`` so that a new SDK artifact class becomes a
  deliberate two-line addition rather than something that appears by import
  accident. ``tests/deployment/test_class_lookup.py`` holds both mappings to the
  SDK's actual exports, so neither can fall behind.
* A class-id the SDK **does not own**, *and that does not claim the SDK's
  namespace*, resolves through
  :func:`~ccf.controlplane.artifacts.declared_artifact_class` to the
  :class:`~ccf.controlplane.artifacts.DeclaredArtifact` envelope. This is not a
  fallback for failure — it is the design. The SDK owns the schema of what it
  ships and never invents one for what it does not, so an unrecognized class-id
  *is* a deployment-authored schema and gets the open envelope, which fixes class
  identity, semver lane, and canonical serializability while leaving the
  declaration itself to its author.

Ordering matters for the same reason: SDK ids resolve from the reviewed
constants **first**, so a manifest cannot shadow an SDK class by naming it and
receiving the permissive envelope instead of the real contract.

The ``ccf.`` prefix is the SDK's, and it is reserved (D-IMPL-84)
----------------------------------------------------------------

An earlier revision of this module said that refusing an id it did not
recognize "would be the SDK claiming ownership of a namespace that is not its
own". That reading was too wide, and D-IMPL-84 narrows it: the SDK claims
**exactly one prefix**, ``ccf.``, and nothing else. Every other namespace stays
the adopter's, on the envelope path, unchanged.

The reservation exists because the envelope path was reachable *under an SDK
class name*. A document that is a valid
:class:`~ccf.controlplane.artifacts.DeclaredArtifact` — ``semver``,
``class_id``, ``declaration`` — and that claims ``class_id:
ccf.workflow-definition`` used to boot: it resolved to the open envelope,
registered, pinned, bound the Control Plane key to the SDK class id, and entered
Decision Replay dimension 2 with arbitrary content and no bump check. The
class-binding check in :mod:`ccf.controlplane.registry` compares ``class_id``
*strings*, which match, so a later correct
:meth:`~ccf.controlplane.registry.ControlPlaneRegistry.register_versioned` on
the same key was admitted on top of the squat.

**Why namespace-wide and not a list of the four author-versioned ids.** Dave
ruled the wider refusal over the narrower list because the squat was verified
reachable for ``ccf.hitl-policy`` (an SDK class this module does not map),
``ccf.skill-grant``, and a wholly invented ``ccf.made-up-class``. A four-id list
would close roughly a third of the hole and leave the identical shape reachable
under every other spelling — a refusal that does not close the shape does not
close the defect.

So a ``ccf.``-prefixed id in neither mapping is refused rather than enveloped.
Two kinds of id land there and both are refusals for the same reason: an SDK
class that is not manifest-addressable (``ccf.hitl-policy``,
``ccf.scope-mapping`` — registered by adopter code against their real contracts,
never through a manifest), and an id the SDK does not own at all. In both cases
the envelope would be the wrong contract wearing the SDK's name.

The module holds no key name, no path, and no domain value — it maps SDK-owned
identifiers to SDK-owned contracts (CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from ccf.agents.definitions import AGENT_DEFINITION, PROMPT_ARTIFACT, TASK_DEFINITION
from ccf.controlplane.artifacts import (
    DEBT_PROFILE,
    DEPLOYMENT_CONFIG,
    DEPLOYMENT_MANIFEST,
    HALF_LIFE_TABLE,
    OPERATOR_PARAMETERS_POLICY,
    OPERATOR_PARAMETERS_SIMILARITY,
    OPERATOR_PARAMETERS_TEMPORAL,
    OPERATOR_PARAMETERS_TRAVERSAL,
    OPERATOR_PARAMETERS_TRAVERSAL_DESCENDANTS,
    PERSPECTIVE,
    POLICY_CONSTRAINT,
    PRODUCT_CLASS,
    PROJECTION_REQUIREMENTS,
    RESOLUTION_SPEC,
    SIGNAL_BATCH,
    ArtifactClass,
    ArtifactRole,
    RegistrationMode,
    declared_artifact_class,
)
from ccf.skills.catalog import SKILL_CATALOG_ENTRY
from ccf.skills.grants import SKILL_GRANT
from ccf.workflow.definitions import WORKFLOW_DEFINITION

__ccf_mode__ = "algorithmic"

__all__ = [
    "SDK_ARTIFACT_CLASSES",
    "SDK_ARTIFACT_ROLES",
    "SDK_VERSIONED_ARTIFACT_CLASSES",
    "refuse_registration_the_sdk_fixes",
    "refuse_role_the_sdk_fixes",
    "resolve_artifact_class",
]

#: The prefix the SDK owns (D-IMPL-84). Private and stated once, so the
#: reservation and its refusal message cannot drift apart. Deliberately not in
#: ``__all__``: the reservation is a *behavior* of
#: :func:`resolve_artifact_class`, and exporting the string would invite an
#: adopter to branch on it instead of letting the refusal fire.
_CCF_NAMESPACE = "ccf."

#: Every artifact class whose schema the SDK owns, keyed by ``class_id``.
#:
#: Hand-maintained on purpose, and held to :mod:`ccf.controlplane.artifacts` by
#: ``tests/deployment/test_class_lookup.py``: adding an ``ArtifactClass``
#: constant there without adding it here is a test failure, because a class the
#: SDK ships that a manifest cannot address is a class no adopter can register.
SDK_ARTIFACT_CLASSES: dict[str, ArtifactClass] = {
    HALF_LIFE_TABLE.class_id: HALF_LIFE_TABLE,
    DEBT_PROFILE.class_id: DEBT_PROFILE,
    RESOLUTION_SPEC.class_id: RESOLUTION_SPEC,
    OPERATOR_PARAMETERS_TRAVERSAL.class_id: OPERATOR_PARAMETERS_TRAVERSAL,
    # The directed sibling (ledger row 24.5-L-06). A manifest selects the walk's
    # direction by naming this class rather than the neighborhood's; the
    # builder's dispatch reads the class, never a document value.
    OPERATOR_PARAMETERS_TRAVERSAL_DESCENDANTS.class_id: (
        OPERATOR_PARAMETERS_TRAVERSAL_DESCENDANTS
    ),
    OPERATOR_PARAMETERS_TEMPORAL.class_id: OPERATOR_PARAMETERS_TEMPORAL,
    OPERATOR_PARAMETERS_POLICY.class_id: OPERATOR_PARAMETERS_POLICY,
    OPERATOR_PARAMETERS_SIMILARITY.class_id: OPERATOR_PARAMETERS_SIMILARITY,
    # A `role: load` class under D-IMPL-80: addressable by a manifest so it can
    # be *parsed*, never registered. The manifest's own `role` field carries the
    # distinction, and :data:`SDK_ARTIFACT_ROLES` below is what makes the
    # distinction machine-checkable rather than a docstring anyone may misread.
    SIGNAL_BATCH.class_id: SIGNAL_BATCH,
    PERSPECTIVE.class_id: PERSPECTIVE,
    PRODUCT_CLASS.class_id: PRODUCT_CLASS,
    # Design E2's second authored operator set (D-IMPL-86). Manifest-addressable
    # for the same reason every class here is: a class the SDK ships that a
    # manifest cannot name is a class no adopter can register — and this one has
    # to be registerable, because the binder's authored input is one of the two
    # documents it compares.
    PROJECTION_REQUIREMENTS.class_id: PROJECTION_REQUIREMENTS,
    DEPLOYMENT_MANIFEST.class_id: DEPLOYMENT_MANIFEST,
    # The single-file authoring document (D-IMPL-136). Manifest-addressable
    # for the same reason every entry here is: a class the SDK ships that a
    # manifest cannot name is a class no adopter can register — and, more
    # immediately, because `tools/dump_schemas.py` enumerates this mapping
    # and the committed schema it produces is what an adopter's editor reads.
    DEPLOYMENT_CONFIG.class_id: DEPLOYMENT_CONFIG,
    # The parameter-level policy constraint (ledger row `24.6-L-07`,
    # `D-IMPL-253` Q3). Manifest-addressable because a deployment registers one
    # constraint per key: independent identity, lane and effectivity is the
    # whole point of the class, and a class a manifest cannot name is a class
    # no adopter can register.
    POLICY_CONSTRAINT.class_id: POLICY_CONSTRAINT,
}

#: Every SDK-owned artifact class whose contract declares an ``artifact_version``
#: field — the classes :meth:`~ccf.controlplane.registry.ControlPlaneRegistry
#: .register_versioned` exists for — keyed by ``class_id``.
#:
#: **A separate mapping, and the split is the point.**
#: :data:`SDK_ARTIFACT_CLASSES` means *typed-registerable*: the classes a
#: manifest may name for :meth:`register_typed
#: <ccf.controlplane.registry.ControlPlaneRegistry.register_typed>`, which is
#: also the set the HTTP ``/schema`` route, the ``ccf schema export`` CLI verb
#: and ``tools/dump_schemas.py`` enumerate. This mapping means
#: *versioned-registerable*: the classes a manifest may name for
#: :meth:`register_versioned
#: <ccf.controlplane.registry.ControlPlaneRegistry.register_versioned>` and its
#: D-05 hash-verified bump check. The two are **disjoint by construction** — a
#: contract either declares a string ``artifact_version`` or it does not, and
#: :func:`refuse_registration_the_sdk_fixes` below is what makes that fact
#: machine-checkable rather than a docstring anyone may misread. Merging them
#: would silently widen a runtime contract nobody has ruled on.
#:
#: Held to the SDK's own exports by ``tests/deployment/test_class_lookup.py``,
#: which computes the author-versioned set by walking the exported
#: ``ArtifactClass`` constants rather than repeating this list — so the mapping
#: cannot fall behind the way :data:`SDK_ARTIFACT_CLASSES` could not.
SDK_VERSIONED_ARTIFACT_CLASSES: dict[str, ArtifactClass] = {
    AGENT_DEFINITION.class_id: AGENT_DEFINITION,
    PROMPT_ARTIFACT.class_id: PROMPT_ARTIFACT,
    TASK_DEFINITION.class_id: TASK_DEFINITION,
    WORKFLOW_DEFINITION.class_id: WORKFLOW_DEFINITION,
    SKILL_CATALOG_ENTRY.class_id: SKILL_CATALOG_ENTRY,
    SKILL_GRANT.class_id: SKILL_GRANT,
}

#: The role an SDK-owned class **fixes**, for the classes where the SDK owns the
#: answer rather than the adopter (D-IMPL-80).
#:
#: A class appears here only when declaring the other role would delete a
#: whitepaper property, not merely be unusual. Today exactly one does:
#: ``ccf.signal-batch`` is fixed to ``load``, because registering a batch would
#: content-hash raw event data into Control Plane state, and by D-06's rationale
#: the registered artifact set is dimension 2 of the five-dimension Decision
#: Replay record (whitepaper §7.10.1). Re-authoring an events file would then
#: change "what was in force" exactly as a policy-bundle bump does — which is
#: not what an event stream is. Events are what the fabric *observed*; the
#: Control Plane is what the fabric was *permitted to do*.
#:
#: Why a mapping and not a rule in the manifest module: the fact is a property
#: of the *class*, so it belongs beside the class registry that already answers
#: "what does the SDK own here". :class:`~ccf.deployment.manifest.ManifestEntry`
#: reads it and refuses a contradicting entry at parse, before anything is
#: registered.
#:
#: **Every class absent from this mapping is the adopter's call**, and that is
#: the default. The SDK fixes a role only where it can say why.
SDK_ARTIFACT_ROLES: dict[str, ArtifactRole] = {
    SIGNAL_BATCH.class_id: "load",
}


def refuse_role_the_sdk_fixes(class_id: str, role: ArtifactRole) -> None:
    """Raise if ``role`` contradicts the role the SDK fixes for ``class_id``.

    The machine-checkable half of D-IMPL-80. The required ``role`` field on a
    manifest entry stops the choice being made *silently*; this stops it being
    made *wrongly* for the one class where the SDK knows the answer. Without it
    an adopter could write ``role: register`` against ``ccf.signal-batch``, and
    nothing — no contract, no lint, no test — would fire before raw event data
    was content-hashed into replay dimension 2.

    A class the SDK does not fix is not checked here at all: the adopter's
    declaration stands, which is the default and the common case.

    Raises:
        ValueError: the entry declares a role the SDK fixes otherwise. Refused,
            never corrected — silently rewriting the entry would leave the
            manifest saying one thing and the deployment doing another, and the
            manifest is the document the audit plane reads back.
    """
    fixed = SDK_ARTIFACT_ROLES.get(class_id)
    if fixed is not None and role != fixed:
        raise ValueError(
            f"artifact class {class_id!r} is role {fixed!r} and the manifest"
            f" declares {role!r}; the SDK fixes this class's role because the"
            " other choice would put raw event data into Decision Replay"
            " dimension 2 (D-IMPL-80) — correct the manifest entry"
        )


def refuse_registration_the_sdk_fixes(
    class_id: str, registration: RegistrationMode
) -> None:
    """Raise if ``registration`` contradicts the path ``class_id``'s contract fixes.

    The class-property half of D-IMPL-85, shaped exactly like
    :func:`refuse_role_the_sdk_fixes` above and for the same reason: the
    required ``registration`` field on a manifest entry stops the choice being
    made *silently*, and this stops it being made *wrongly* for the classes
    where the SDK knows the answer — because the answer is a property of the
    contract, not of the deployment.

    Two refusals, and each names what the wrong declaration would cost:

    * an author-versioned class (:data:`SDK_VERSIONED_ARTIFACT_CLASSES`)
      declared ``typed`` — this is CR-1's core. ``register_typed`` runs no bump
      check, so the author's ``artifact_version`` claim would never be held
      against content identity and a changed document could re-enter Decision
      Replay dimension 2 under an unbumped version, with nothing recording that
      the governance the class exists to carry was skipped.
    * a typed-only class (:data:`SDK_ARTIFACT_CLASSES`) declared ``versioned`` —
      :meth:`~ccf.controlplane.registry.ControlPlaneRegistry.register_versioned`
      would raise ``TypeError`` from inside the registry, because the contract
      declares no string ``artifact_version`` for the bump check to verify. The
      failure is loud either way; a refusal at preflight, before any document is
      read and before anything is registered, is the better of the two.

    A class in **neither** mapping is a deployment-authored class and is not
    checked here at all: the adopter's declaration stands, exactly as
    :func:`refuse_role_the_sdk_fixes` leaves the default with the adopter.

    Raises:
        ValueError: the entry declares a registration path the class's own
            contract contradicts. Refused, never corrected — silently rewriting
            the entry would leave the manifest saying one thing and the
            deployment doing another, and the manifest is the document the audit
            plane reads back.
    """
    if class_id in SDK_VERSIONED_ARTIFACT_CLASSES and registration == "typed":
        raise ValueError(
            f"artifact class {class_id!r} is author-versioned and the manifest"
            " declares registration 'typed', which runs no D-05 bump check"
            " (D-IMPL-85) — declare 'versioned'"
        )
    if class_id in SDK_ARTIFACT_CLASSES and registration == "versioned":
        raise ValueError(
            f"artifact class {class_id!r} declares no artifact_version and the"
            " manifest declares registration 'versioned', so the D-05 bump check"
            " has nothing to verify (D-IMPL-85) — declare 'typed'"
        )


def resolve_artifact_class(class_id: str) -> ArtifactClass:
    """Return the :class:`ArtifactClass` a manifest's ``class`` string names.

    SDK-owned ids resolve to the SDK's own constant — from
    :data:`SDK_ARTIFACT_CLASSES` first, then
    :data:`SDK_VERSIONED_ARTIFACT_CLASSES`, both before the envelope, so a
    manifest cannot shadow either into the permissive path. An id in an
    adopter's own namespace resolves to the
    :class:`~ccf.controlplane.artifacts.DeclaredArtifact` envelope: not an
    error, but a deployment-authored schema, and the SDK never invents one for
    what it does not ship.

    A ``ccf.``-prefixed id in neither mapping is **refused** (D-IMPL-84). See
    the module docstring for the squat this closes and for why the reservation
    is namespace-wide rather than a list of the author-versioned ids.

    Raises:
        ValueError: ``class_id`` is empty or whitespace-only. Refused rather
            than defaulted: an unnamed class is a manifest the audit plane
            cannot read back, and only the manifest's author knows what it
            should have said. Or ``class_id`` claims the SDK's reserved
            ``ccf.`` prefix without being a class the SDK ships (D-IMPL-84).
    """
    if not class_id.strip():
        raise ValueError(
            "refusing an empty artifact class id: an unnamed class leaves the"
            " audit plane unable to say what was registered; name it in the"
            " manifest"
        )
    sdk_class = SDK_ARTIFACT_CLASSES.get(class_id)
    if sdk_class is not None:
        return sdk_class
    versioned_class = SDK_VERSIONED_ARTIFACT_CLASSES.get(class_id)
    if versioned_class is not None:
        return versioned_class
    if class_id.startswith(_CCF_NAMESPACE):
        raise ValueError(
            f"artifact class id {class_id!r} claims the SDK's reserved"
            f" {_CCF_NAMESPACE!r} prefix but is not a class the SDK ships"
            " (D-IMPL-84); the open DeclaredArtifact envelope is refused here"
            " because a document that satisfies it would register, pin and"
            " enter Decision Replay dimension 2 under an SDK class name with"
            " arbitrary content — choose a class id in your own namespace, or"
            " correct the spelling of the SDK class you meant"
        )
    return declared_artifact_class(class_id)
