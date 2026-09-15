"""Derive a `DeploymentManifest` and its documents from a `DeploymentConfig`.

SDK-defined mechanism (CLAUDE.md §6.4 and §10). `D-IMPL-136` rules that a
single `ccf_config.yaml` names its sections in the vocabulary an adopter
already uses instead of naming a file, a manifest key and a class id three
times over — *"the section name **is** the class"*. `src/ccf/controlplane
/artifacts.py::DeploymentConfig` (plan `16-28`) is the typed, closed-world
proof that such a document says exactly what it claims to say. This module
is the other half: it turns one parsed `DeploymentConfig` into the
`DeploymentManifest` `~ccf.deployment.manifest.load_and_boot` already
consumes, plus one materialised document per section — the derivation table
of design spec §6, and every refusal §6.1, §11.1 and §11.2 demand.

**This function derives. It does not validate contents, register anything,
or boot anything.** Every materialised document is a plain mapping, not yet
run through :func:`~ccf.controlplane.artifacts.parse_artifact`. That is a
boundary, not an oversight: a document that fails its own class contract is
a `16-30` concern, at the point that phase also decides nothing gets
registered — a derivation that validated as it went would fail on document
four having already built documents one through three, describing a
half-derived deployment nothing asked for. Nothing here reads a file,
reads an environment variable, or calls `resolve_artifact_class` for any
reason but resolving a class *identity* — `derive_deployment` is pure over
its argument.

Why `DerivedDeployment` is a frozen dataclass, not a `CCFContract`
-------------------------------------------------------------------

The same reason :class:`~ccf.deployment.manifest.BootedFabric` gives for
itself: it is a derivation result handed to a caller, not a content-hashable
artifact. Its `manifest` field *is* the content-hashable thing — a
`DeploymentManifest`, which is a `CCFContract` already — and its `documents`
field carries plain mappings that `16-30` will validate and register, not a
second artifact to hash. Wrapping the pair in a contract would either forbid
the plain-mapping `documents` field (canonical serialization has no rendering
for "a document not yet known to satisfy any class") or coerce it into one,
and coercion here is exactly the validate-too-early boundary this module
declines to cross.

The three-line correction (`D-IMPL-138`(a))
--------------------------------------------

Design spec §6.1 originally said HW-1's two adopter sections (`policy`,
`request_contract`) *"each carry two lines"*. **They carry three** —
`class_id` alongside `role` and `registration` — corrected 2026-08-15 by
Dave's ruling `D-IMPL-138`(a). The reason is `D-IMPL-134`'s own words: *"key
and class_id become derived-with-override on the same principle... class_id
from the stem for SDK classes and **from the document** for adopter-owned
ones."* Deriving an adopter's `class_id` from the section name would require
this module to invent an adopter namespace, and `D-IMPL-84` forbids that by
reserving exactly one prefix, `ccf.`. `class_id` is no more derivable for an
adopter-owned class than `role` or `registration` are, for the same reason,
so an adopter-owned section states all three or is refused — see
`_ADOPTER_OWNED_REQUIRED_FIELDS` and the R1 refusal below. Three is strictly
more explicit than two; it does not weaken `D-IMPL-80` or `D-IMPL-85`, it is
a divergence from approved prose that `D-IMPL-138`(a) itself corrects,
recorded here rather than silently absorbed. `docs/superpowers/specs
/2026-08-14-ccf-config-consolidation-design.md` §6 carries the same
correction, marked as a correction rather than overwritten; this module does
not re-edit that document.

Consolidating files does not consolidate claims (design spec §11.2)
----------------------------------------------------------------------

`product_class.required_operator_keys` and the `operators:` mapping's keys
state the same set twice — not across independently authored documents, as
`~ccf.deployment.binder.refuse_operator_set_divergence` compares, but two
enumerations nonetheless, reintroduced by the very act of merging files into
one. *"Consolidating files does not consolidate claims. A guard justified by
'there is only one statement here' needs re-checking whenever the authoring
surface changes shape."* `_refuse_operator_set_divergence` below is the
re-check this section demands, and it is a **parse-time** refusal over one
document's own two fields — deliberately not a call into
:mod:`ccf.deployment.binder`, whose comparison is between the product
class's Control Plane claim and the *projection plan's* own requirements at
plan-build time, a different comparison at a different moment. Conflating
the two would leave one of them uncovered.

What a `ccf_config.yaml` cannot express, named rather than discovered (`16-30`)
--------------------------------------------------------------------------------

There is no `signal_batch` section among the nine reserved names, and that is
a decision, not a gap. Registering one would content-hash raw event data into
Control Plane state and therefore into Decision Replay dimension 2
(`D-IMPL-80`) — events are what the fabric *observed*, not what it was
*permitted to do*. `16-30`'s `load_config_and_boot` is scoped by this
exclusion too: its equivalence test compares the artifact set the config form
can express, and a `ccf.signal-batch` entry is outside that set by
construction, not by omission. A deployment that needs one keeps a manifest —
which the dual model supports indefinitely (Dave's ruling, 2026-08-14) — and
boots it through `~ccf.deployment.manifest.load_and_boot` instead.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, get_args

from ccf.contracts.base import CCFContract
from ccf.agents.definitions import AGENT_DEFINITION
from ccf.controlplane.artifacts import (
    EGRESS_DOOR,
    MCP_PRODUCER,
    TTL_BINDING,
    DEPLOYMENT_CONFIG,
    DeploymentConfig,
    DeploymentManifest,
    EgressDoorBinding,
    ManifestEntry,
    McpProducerRegistration,
    load_artifact,
    parse_artifact,
)
from ccf.products.contract import ChildRequirement, version_satisfies_floor
from ccf.skills.catalog import SKILL_CATALOG_ENTRY, skill_catalog_key
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.deployment.classes import (
    refuse_registration_the_sdk_fixes,
    refuse_role_the_sdk_fixes,
    resolve_artifact_class,
)
from ccf.deployment.keys import DeploymentKeys
from ccf.deployment.manifest import (
    BootedFabric,
    _preflight_adapter,
    _preflight_entries,
    _register_and_boot,
    _resolve_secret_references,
    _resolve_tenant,
)
from ccf.operators.base import OperatorCategory

__ccf_mode__ = "algorithmic"

__all__ = ["DerivedDeployment", "derive_deployment", "load_config_and_boot"]


#: The four keys `design spec §6.2` reserves as override syntax. Stripped
#: from every section body before materialisation, so an override never
#: leaks into an artifact's own content — and therefore never into its
#: content address (T-16-29-04).
_RESERVED_OVERRIDE_KEYS = ("key", "class_id", "role", "registration")

#: The three fields an adopter-owned section states with no default
#: (`D-IMPL-80`, `D-IMPL-85`, `D-IMPL-138`(a)). Order is the order a refusal
#: names them in.
_ADOPTER_OWNED_REQUIRED_FIELDS = ("class_id", "role", "registration")

#: The prefix a derived operator class id is built from. Referenced exactly
#: once as a literal — the class ids are **built**, never enumerated
#: (CLAUDE.md §11, CINV-01): a fifth operator category needs no edit here.
_OPERATOR_CLASS_PREFIX = "ccf.operator-parameters."


#: What the loader knows about each of the nine reserved section names other
#: than `operators` — the reserved-section table design spec §6 describes.
#: `policy_constraints` is in the table like the rest but is derived per key,
#: the way `operators` is, because its section body is a MAPPING of label to
#: constraint document rather than one document (`24.6-L-07`).
#: Hand-maintained, in the voice of `SDK_ARTIFACT_CLASSES`
#: (`src/ccf/deployment/classes.py`), and this is mechanism, not values
#: (CLAUDE.md §11): it enumerates the SDK's own reserved slots and carries
#: no domain vocabulary, no threshold, no policy name and no prompt.
#:
#: Each value is ``(default_class_id, wrapper)``.
#:
#: ``default_class_id`` is the `ccf.*` id the SDK derives for a
#: **SDK-owned** section, or ``None`` for a section whose class is
#: **adopter-owned** — `policy` and `request_contract`, per `D-IMPL-138`(a)
#: above. ``None`` here is what makes `role` and `registration` required
#: with no default for that section: see `_derive_entry`'s branch on it.
#:
#: ``wrapper`` says how a stripped section body becomes a materialised
#: document: ``None`` places it at the document's top level (beside the
#: derived `semver`); ``"entries"`` wraps it under that key, because
#: `HalfLifeTable` declares `entries: Mapping[str, HalfLifeEntry]` and the
#: section itself elides the wrapper the author never writes;
#: ``"declaration"`` wraps it under that key alongside the section's own
#: `class_id`, because an adopter-owned section materialises as a
#: `DeclaredArtifact` (`semver`, `class_id`, `declaration`), exactly the
#: shape `examples/s1-00-companies-over-revenue/artifacts/config
#: /policy-bundle.yaml` and `request-contract.yaml` already carry.
#:
#: Held to `SDK_ARTIFACT_CLASSES` by
#: `tests/deployment/test_config_derivation.py`, so a `ccf.*` id here that
#: the SDK does not actually export cannot go unnoticed the way an entry
#: written and never checked would.
_RESERVED_SECTIONS: Mapping[str, tuple[str | None, str | None]] = {
    "product_class": ("ccf.product-class", None),
    "resolution": ("ccf.resolution-spec", None),
    "half_life": ("ccf.half-life-table", "entries"),
    "debt_profile": ("ccf.debt-profile", None),
    "default_perspective": ("ccf.perspective", None),
    "policy": (None, "declaration"),
    "request_contract": (None, "declaration"),
    "policy_constraints": ("ccf.policy-constraint", None),
    # `R-12` (`D-IMPL-282`, Dave, 2026-09-08). The ninth entry, and exactly
    # one: a deployment's replay binding is deployment CONFIGURATION, so it
    # materialises as a top-level `ccf.replay-binding` document like every
    # other SDK-owned single-document section. The ruling's own boundary is
    # what keeps this to one entry — *"No product-specific replay semantics in
    # the Control Plane—only deployment binding/configuration."*
    "replay": ("ccf.replay-binding", None),
    # `D-IMPL-340`: one `ccf.mcp-producer` document per labeled producer,
    # derived per key exactly as `policy_constraints` is.
    "producers": ("ccf.mcp-producer", None),
    # `D-IMPL-343` (R-3a, R-6/R-9/R-10): the two bindings the paved road
    # reads. Each is deployment BINDING — a TTL window, a door's asserted
    # identity and advertised prose — and materialises as a top-level
    # SDK-owned document like `replay:` does. Appended after `replay:` in the
    # derivation loop, so every key order that existed before them is
    # byte-for-byte what it was.
    "ttl": ("ccf.ttl-binding", None),
    "door": ("ccf.egress-door", None),
}

#: The reserved sections whose class is AUTHOR-VERSIONED (`D-IMPL-343` R-2;
#: `D-IMPL-85`): section name → the `ccf.*` class id, and nothing else.
#:
#: **A second table, and the split is the point.** `_RESERVED_SECTIONS` above
#: derives on the TYPED path: the SDK injects the config's own `semver`, fixes
#: `registration: typed`, and `tests/deployment/test_config_derivation.py`
#: holds every id in it to `SDK_ARTIFACT_CLASSES`. A `ccf.agent-definition`
#: is none of those things — it carries its author's own two lanes
#: (`schema_version`, `artifact_version`), it is registered through the D-05
#: hash-verified bump check, and it lives in `SDK_VERSIONED_ARTIFACT_CLASSES`,
#: which is disjoint from the typed table by construction. Dave's ruling
#: (R-2): *"Do not fight D-IMPL-56 by injecting a fake semver typed class. New
#: reserved derivation that matches the existing artifact, or a dedicated
#: reserved section — pick the one that does not require an author-versioned
#: class in the typed table."* This is that derivation: the section's body IS
#: the artifact document, verbatim, and the only thing the SDK adds is the
#: manifest entry that names it.
_RESERVED_VERSIONED_SECTIONS: Mapping[str, str] = {
    "agent": AGENT_DEFINITION.class_id,
    # `D-IMPL-343` R-7 (the consumer half): one `ccf.skill-catalog-entry` per
    # label under `skills:`, derived per key the way `producers:` is and
    # registered on the versioned path the class requires. What the SDK
    # fills is read off OTHER declared keys — the label, the deployment's
    # tenant, `produces`, the one `producers.*` entry offering that class and
    # its `versions_from` floor — and a stated value is held equal, never
    # overridden. What the SDK never fills: the two author lanes, the
    # description (`D-IMPL-56`) and the requirements envelope (`D-IMPL-29`).
    "skills": SKILL_CATALOG_ENTRY.class_id,
}

#: The one skill type the paved derivation produces (`D-IMPL-343` R-7). A
#: composite on the road asks a REGISTERED producer a governed question; every
#: other skill type is declared in its own catalog document and reaches a
#: composite through the low road's `children=` hatch.
_PAVED_SKILL_TYPE = "mcp_product"

#: The argument schema an `mcp_product` dispatch is structurally held to:
#: :func:`~ccf.skills.dispatch.dispatch_skill` passes ``arguments={}`` on the
#: question path, so the schema of an entry derived here has exactly one
#: legal value. Filled when the section omits it and held equal when stated —
#: a declared value with one legal value is documentation, not control.
_EMPTY_ARGUMENT_SCHEMA: Mapping[str, Any] = {"properties": {}, "required": []}


@dataclass(frozen=True)
class DerivedDeployment:
    """What `derive_deployment` hands back: a manifest and its documents.

    A frozen dataclass rather than a `~ccf.contracts.base.CCFContract` — see
    the module docstring's *"Why `DerivedDeployment` is a frozen dataclass"*
    section for the reasoning, borrowed from
    `~ccf.deployment.manifest.BootedFabric`'s own.

    Attributes:
        manifest: The derived `~ccf.controlplane.artifacts.DeploymentManifest`
            — the content-hashable thing. Every field the multi-file form
            authors by hand, constructed instead.
        documents: Every materialised document, keyed by the manifest key
            the entry it belongs to carries. Plain mappings, not yet
            validated against any class — `16-30`'s loader is what calls
            `~ccf.controlplane.artifacts.parse_artifact` over each one,
            against the class its own manifest entry names.
        keys: The manifest key every section derived, by section name
            (`D-IMPL-343`; :class:`~ccf.deployment.keys.DeploymentKeys`).
            Handed onward to :attr:`~ccf.deployment.BootedFabric.keys` by
            `load_config_and_boot`, so a deployment never restates a key the
            derivation chose.
    """

    manifest: DeploymentManifest
    documents: Mapping[str, Mapping[str, Any]]
    keys: DeploymentKeys


def _derive_versioned_entry(
    *,
    label: str,
    body: Mapping[str, Any],
    config_filename: str,
    class_id: str,
    tenant_id: str | None,
) -> tuple[ManifestEntry, Mapping[str, Any]]:
    """Derive one author-versioned reserved section (`D-IMPL-343` R-2).

    The versioned sibling of `_derive_entry`, and deliberately narrower: no
    `semver` is injected (the class carries its own two lanes), `role` is
    `register` and `registration` is `versioned` — both fixed by the class,
    neither overridable — and the document handed back is the section's body
    with the bookkeeping keys stripped and nothing added. What the SDK checks
    rather than fills: the artifact's own ``tenant`` must be this deployment's
    tenant when both are stated. It is filled from ``tenant_id`` only when the
    section left it out, because a deployment's tenant is the one value it has
    already declared once, and a second statement of it is the duplicated
    authority `D-IMPL-343` exists to delete.

    Raises:
        ValueError: the section names `path:`; overrides `class_id`, `role` or
            `registration` (each is fixed by the class); or states a `tenant`
            that is not the deployment's.
    """
    _refuse_reserved_path_override(label, body)
    for fixed in ("class_id", "role", "registration"):
        if fixed in body:
            raise ValueError(
                f"the {label!r} section states {fixed!r}, which the SDK fixes"
                f" for {class_id!r}: the section IS a {class_id} document, so"
                " its class, its `register` role and its `versioned`"
                " registration are properties of the class and not choices"
                " the section makes (D-IMPL-343 R-2; D-IMPL-85) — remove"
                f" {fixed!r} from {label!r}"
            )
    key = str(body.get("key", label))
    document = {field: value for field, value in body.items() if field != "key"}
    declared_tenant = document.get("tenant")
    if declared_tenant is None:
        if tenant_id is not None:
            document["tenant"] = tenant_id
    elif tenant_id is not None and str(declared_tenant) != tenant_id:
        raise ValueError(
            f"the {label!r} section declares tenant {declared_tenant!r} and"
            f" this deployment's tenant_id is {tenant_id!r}; the composing"
            " agent belongs to the deployment that declares it, and two"
            " tenants for one document is a disagreement only the author can"
            " resolve (D-IMPL-343 R-2) — state one, or omit `tenant` under"
            f" {label!r} to take the deployment's"
        )
    entry = ManifestEntry(
        path=config_filename,
        key=key,
        class_id=class_id,
        role="register",
        registration="versioned",
    )
    return entry, document


def _refuse_door_tenant_disagreement(
    door: EgressDoorBinding | None, tenant_id: str
) -> None:
    """`D-IMPL-343` R-6 — the door asserts the tenant the deployment declares.

    Dave, verbatim: *"Registration declares it; door assertion is held to it;
    the child's served tenant_id never authorizes. Do not derive tenant from
    the answer."* So the `door:` section DECLARES `producer_tenant`, and this
    is where the declaration is held to the deployment's one tenant — refused
    by name, never corrected, before anything is registered. A door asserting
    another tenant would be refused `producer-tenant-mismatch` by every
    consumer registered for this fabric's tenant; refusing it here moves that
    failure from the first remote question to the moment the document was
    written.
    """
    if door is None:
        return
    if door.producer_tenant != tenant_id:
        raise ValueError(
            f"the 'door' section asserts producer_tenant {door.producer_tenant!r}"
            f" and this deployment's tenant is {tenant_id!r}; the door asserts"
            " the tenant the deployment declares and a consumer holds the"
            " assertion to its own registration (D-IMPL-343 R-6; D-IMPL-340"
            " ruling 2) — state the deployment's tenant under 'door'"
        )


def _hold_equal(label: str, field: str, stated: object, derived: object, *, source: str) -> None:
    """Refuse a stated value that disagrees with what the SDK derived it from.

    The `D-IMPL-292` equality shape, applied to a derived document: a section
    may restate a value another declared key already fixes, and when it does
    the two must agree — the SDK never overrides the author in either
    direction, and it never lets two authorities stand.
    """
    if stated != derived:
        raise ValueError(
            f"the {label!r} section states {field}={stated!r} and {source}"
            f" derives {derived!r}; one declared value, or two that agree —"
            " the paved derivation fills what a section omits and never"
            " overrides what it states (D-IMPL-343 R-7)"
        )


def _requirements_of(product_class_document: Mapping[str, Any]) -> tuple[ChildRequirement, ...]:
    """The declared child requirements, parsed once for the derivations that read them.

    Only the ``requires`` rows are parsed here — the whole declaration is
    validated at boot, as it always was — so a config that derived before the
    consumer half existed derives exactly as it did.
    """
    rows = product_class_document.get("requires") or ()
    if not isinstance(rows, list | tuple):
        raise ValueError(
            "`product_class.requires` is not a list; each row names one child"
            " class, whether it is required, and the lane it is admitted from"
            " (D-IMPL-336)"
        )
    return tuple(ChildRequirement.model_validate(row) for row in rows)


def _the_offering_producer(
    produces: str,
    producers: Mapping[str, McpProducerRegistration],
    *,
    label: str,
) -> tuple[str, McpProducerRegistration]:
    """The ONE declared producer offering ``produces`` — none or two refuse by name.

    `D-IMPL-343` design `R-12′`, accepted: two registrations offering one class
    are refused at derivation rather than chosen between, because any rule
    the SDK applied would make composition and replay depend on something the
    deployment never declared (the `D-IMPL-340` ruling-7 posture, held one
    boundary earlier). A stated ``binding.server`` is held EQUAL to the one
    derived; it never selects.
    """
    offering = [
        (server, registration)
        for server, registration in sorted(producers.items())
        if any(offer.product_class == produces for offer in registration.offers)
    ]
    if not offering:
        raise ValueError(
            f"the {label!r} section produces {produces!r} and no entry under"
            " `producers:` offers that class; a skill asking a producer nobody"
            " declared can never fire — declare the producer, with an `offers`"
            " row for the class (D-IMPL-343 R-7; D-IMPL-340)"
        )
    if len(offering) > 1:
        names = ", ".join(repr(server) for server, _registration in offering)
        raise ValueError(
            f"{len(offering)} declared producers offer {produces!r} ({names});"
            " the paved road selects no producer dynamically — declare the one"
            " this deployment asks, or compose the choice through the low"
            " road's `children=` (D-IMPL-343; D-IMPL-340 ruling 7)"
        )
    return offering[0]


def _complete_skill_entry(
    label: str,
    body: Mapping[str, Any],
    *,
    name: str,
    requirements: tuple[ChildRequirement, ...],
    producers: Mapping[str, McpProducerRegistration],
) -> dict[str, Any]:
    """Fill what other declared keys fix; hold what the section states equal (`R-7`).

    The declared keys, and only these, are read: the label (the entry's
    ``name``), ``produces``, the ``producers.*`` registration whose ``offers``
    name that class, and its ``versions_from`` floor. From them the SDK fills
    ``name``, ``skill_type``, ``binding`` (server, class, the floor asked) and
    the structurally empty ``argument_schema``. It fills nothing else: the two
    author lanes, ``description`` (`D-IMPL-56`) and ``requirements``
    (`D-IMPL-29`) are the section's own statements and are refused absent by
    the class itself.

    **`R-13` at the earlier boundary.** The floor a producer is asked from
    (``versions_from``) and the floor the composite admits from
    (``compatible_from``) must open the SAME major lane, or nothing the
    producer served from its floor could ever be admitted — refused here, by
    name, with both floors. Within one major the two may differ in either
    direction: what the producer actually serves is held to the composite's
    floor at admission, exactly as the low road holds it
    (`version-incompatible`, reason retained). The panel's review of this
    half caught the first version of this check, which refused an asked floor
    below the composite's — a same-major producer serving above both would
    have been admitted, so that refusal was a semantic divergence from the
    low road, not a guard.

    Raises:
        ValueError: ``produces`` absent; ``produces`` names a class the
            composite does not require; no or two producers offer it; a stated
            ``name``, ``skill_type``, ``binding`` member or ``argument_schema``
            disagrees with its derivation; or the floor lies outside the lane.
    """
    if "key" in body:
        raise ValueError(
            f"the {label!r} section states 'key'; a skill catalog entry's key"
            " is fixed by its class (`{tenant}/{class}/{name}`, the key its"
            f" grant resolves) — remove 'key' from {label!r} (D-IMPL-343 R-7)"
        )
    document = dict(body)
    produces = document.get("produces")
    if not isinstance(produces, str) or not produces:
        raise ValueError(
            f"the {label!r} section declares no `produces`; a paved skill is"
            " the statement that a declared producer is asked for one product"
            " class, and that class is the one key the SDK reads to derive"
            " the rest (D-IMPL-343 R-7)"
        )
    requirement = next((r for r in requirements if r.product_class == produces), None)
    if requirement is None:
        required = sorted(r.product_class for r in requirements)
        raise ValueError(
            f"the {label!r} section produces {produces!r}, which the product"
            f" class does not require (its `requires` names {required!r}); a"
            " skill producing a class the composite never asks for is wiring"
            " nothing exercises (D-IMPL-343 R-7)"
        )
    server, registration = _the_offering_producer(produces, producers, label=label)
    offer = next(o for o in registration.offers if o.product_class == produces)
    if not _same_major(offer.versions_from, requirement.compatible_from):
        raise ValueError(
            f"producer {server!r} offers {produces!r} from lane"
            f" {offer.versions_from!r} and the composite admits it from"
            f" {requirement.compatible_from!r}; the two floors open different"
            " major lanes, so nothing the producer served from its floor could"
            " ever be admitted — align the majors (D-IMPL-343 R-13). Within one"
            " major the floors may differ: the served lane is held to the"
            " composite's floor at admission"
        )

    source = f"the section label and `produces` ({produces!r})"
    if "name" in document:
        _hold_equal(label, "name", document["name"], name, source="the section label")
    document["name"] = name
    if "skill_type" in document:
        _hold_equal(label, "skill_type", document["skill_type"], _PAVED_SKILL_TYPE, source="the paved road")
    document["skill_type"] = _PAVED_SKILL_TYPE

    derived_binding = {
        "server": server,
        "product_class": produces,
        "product_version": offer.versions_from,
    }
    stated_binding = document.get("binding")
    if stated_binding is not None:
        if not isinstance(stated_binding, Mapping):
            raise ValueError(
                f"the {label!r} section's `binding` is not a mapping; a stated"
                " binding restates the derived one and is held equal to it"
                " (D-IMPL-343 R-7)"
            )
        for member, derived_value in derived_binding.items():
            if member in stated_binding:
                _hold_equal(
                    label,
                    f"binding.{member}",
                    stated_binding[member],
                    derived_value,
                    source=(
                        source
                        if member != "product_version"
                        else f"producer {server!r}'s `versions_from` floor (R-13)"
                    ),
                )
        unknown = sorted(set(stated_binding) - set(derived_binding))
        if unknown:
            raise ValueError(
                f"the {label!r} section's `binding` states {unknown!r}, which"
                " an mcp_product binding does not carry (D-IMPL-340)"
            )
    document["binding"] = derived_binding

    if "argument_schema" in document:
        _hold_equal(
            label,
            "argument_schema",
            document["argument_schema"],
            _EMPTY_ARGUMENT_SCHEMA,
            source="the mcp_product dispatch, which passes no arguments",
        )
    document["argument_schema"] = dict(_EMPTY_ARGUMENT_SCHEMA)
    return document


def _same_major(one: str, other: str) -> bool:
    """Whether two semantic versions open the same major lane — via the ONE floor rule.

    Two versions share a major exactly when one satisfies the other's floor
    (:func:`~ccf.products.contract.version_satisfies_floor`: same major, at or
    above); a second parse of the grammar here would be a second rule.
    """
    return version_satisfies_floor(floor=one, version=other) or version_satisfies_floor(
        floor=other, version=one
    )


def _artifact_ref(key: str, semver: str, *, section: str) -> str:
    """A pinned ``ccf-artifact://`` reference to a derived section, or a refusal by name.

    The reference grammar is ``{tenant}/{class}/{name}@{version}``
    (:func:`~ccf.artifacts.protocol.parse_artifact_uri`), so a section whose
    key is its bare label cannot be referenced by an agent's axis; the remedy
    is the section's own ``key:`` override, and the refusal names it. The
    version is the config's ``semver`` — what the typed derivation injects
    into the section's document, and what a pinned resolution matches.
    """
    if len(key.split("/")) != 3:
        raise ValueError(
            f"the `{section}` section registers under key {key!r}, which a"
            " composing agent cannot reference: an artifact reference is"
            " `ccf-artifact://{tenant}/{class}/{name}@{version}` — declare"
            f" `key: <tenant>/<class>/<name>` under `{section}:` so the agent's"
            " axis pins the same document the deployment runs under"
            " (D-IMPL-343 R-2)"
        )
    return f"ccf-artifact://{key}@{semver}"


def _complete_agent(
    body: Mapping[str, Any],
    *,
    requirements: tuple[ChildRequirement, ...],
    default_perspective: Mapping[str, Any] | None,
    policy_key: str | None,
    debt_profile_key: str | None,
    semver: str,
) -> dict[str, Any]:
    """Fill the composing agent's derivable axes from the deployment's declarations (`R-2`).

    Six axes (CLAUDE.md §6.2), and which side of the derivation each is on:
    the archetype binding, the name and the two author lanes are the
    section's own; the context contract is filled from ``requires`` (each
    class at its ``compatible_from`` floor) or, when stated, checked to cover
    every requirement at a lane the requirement accepts; the perspective is
    filled from ``default_perspective`` or held to its role; the policy regime
    and the debt profile are filled as pinned references to the deployment's
    own ``policy`` and ``debt_profile`` sections, at the config's ``semver``,
    or held equal when stated; instruction bindings default to none.

    Raises:
        ValueError: a stated ``consumes`` omits a required class or names a
            lane its requirement does not accept; a stated role or reference
            disagrees with the deployment's; or an axis cannot be filled
            because the deployment declares no section to fill it from.
    """
    document = dict(body)

    contract = document.get("context_contract")
    if contract is None:
        if requirements:
            document["context_contract"] = {
                "consumes": [
                    {"product_class": r.product_class, "schema_version": r.compatible_from}
                    for r in requirements
                ]
            }
    elif isinstance(contract, Mapping) and isinstance(contract.get("consumes"), list):
        consumed = {
            str(row.get("product_class")): str(row.get("schema_version"))
            for row in contract["consumes"]
            if isinstance(row, Mapping)
        }
        for requirement in requirements:
            lane = consumed.get(requirement.product_class)
            if lane is None:
                raise ValueError(
                    f"the 'agent' section's context contract consumes"
                    f" {sorted(consumed)!r} and the product class requires"
                    f" {requirement.product_class!r}; a composing agent reads"
                    " every class its composite requires, so the contract is"
                    " held to `requires` (D-IMPL-343 R-2)"
                )
            if lane != requirement.compatible_from:
                # Held EQUAL, not merely inside the lane: nothing on the
                # composite path reads the agent's lane, so a stricter or a
                # looser one here would be a second statement of the floor
                # that admission never consults (panel finding, this half).
                raise ValueError(
                    f"the 'agent' section consumes {requirement.product_class!r}"
                    f" at lane {lane!r} and the product class admits it from"
                    f" {requirement.compatible_from!r}; the agent's contract and"
                    " the requirement are one statement, so the lane is the"
                    " requirement's floor — omit it to have it filled, or state"
                    " it equal (D-IMPL-343 R-2, R-13)"
                )

    if default_perspective is not None:
        role = default_perspective.get("role")
        perspective = document.get("perspective")
        if perspective is None:
            document["perspective"] = {"role": role, "selection_params": {}}
        elif isinstance(perspective, Mapping) and "role" in perspective:
            _hold_equal("agent", "perspective.role", perspective["role"], role, source="`default_perspective.role`")

    for axis, key, section in (
        ("policy_regime", policy_key, "policy"),
        ("halflife_debt_profile", debt_profile_key, "debt_profile"),
    ):
        stated = document.get(axis)
        if stated is None and key is None:
            raise ValueError(
                f"the 'agent' section states no `{axis}` and the config"
                f" declares no `{section}:` section to derive one from; the"
                " axis is the deployment's own document, pinned (D-IMPL-343 R-2)"
            )
        if key is None:
            continue  # stated, and nothing declared here to hold it to
        # The deployment's own document, pinned — refused with the `key:`
        # remedy when the section's key cannot be referenced, whether the axis
        # is being filled or was stated (a stated ref beside an unreferenceable
        # section would be the second authority this derivation exists to
        # delete; panel finding, this half).
        derived_ref = _artifact_ref(key, semver, section=section)
        if stated is None:
            document[axis] = {"ref": derived_ref}
        elif isinstance(stated, Mapping):
            _hold_equal(
                "agent",
                f"{axis}.ref",
                stated.get("ref"),
                derived_ref,
                source=f"the `{section}` section's key and the config's semver",
            )
    document.setdefault("instruction_bindings", [])
    return document


def _refuse_reserved_path_override(label: str, body: Mapping[str, Any]) -> None:
    """R3 — `path` is not overridable (design spec §11.1).

    Every derived entry's `path` is the literal authoring filename; the
    authoring file is the only honest answer for where a section came from.
    A section naming `path:` is refused rather than silently ignored, so an
    author who tried to override it learns immediately rather than
    discovering later that the override did nothing.
    """
    if "path" in body:
        raise ValueError(
            f"the {label!r} section states 'path:', which is not"
            " overridable — every derived entry's path is the literal"
            " authoring file (design spec §11.1); remove 'path:' from"
            f" {label!r}"
        )


def _refuse_empty_section(
    section_name: str, body: object, fields_set: set[str]
) -> None:
    """An empty section (heading present, body absent) is not the same as an
    absent one, and design spec §6 makes the distinction meaningful: an
    absent `policy:` declares no regime, an empty one is an authoring
    mistake nobody would choose deliberately.

    `DeploymentConfig`'s optional sections all default to `None`, so a
    section that was never written and a section written as `name:` with
    nothing under it are indistinguishable by value alone — both parse to
    `None`. Pydantic's own `model_fields_set` is what tells them apart: a
    field name lands there only when the input actually supplied it, default
    value or not, so ``field in fields_set`` is true for the written-empty
    case and false for the omitted one.
    """
    if body is None and section_name in fields_set:
        raise ValueError(
            f"the {section_name!r} section is present but empty; an absent"
            f" section means 'this deployment configures no {section_name}',"
            " and an empty one is ambiguous between that and an authoring"
            f" mistake — remove the {section_name!r} heading entirely for"
            " 'none', or fill it in"
        )


def _refuse_adopter_owned_missing_fields(
    section_name: str, body: Mapping[str, Any]
) -> None:
    """R1 — the load-bearing refusal (`D-IMPL-80`, `D-IMPL-85`, `D-IMPL-138`(a)).

    `D-IMPL-134` narrows `D-IMPL-80` and `D-IMPL-85`; it revokes neither. An
    adopter-owned section's `class_id`, `role` and `registration` have no
    default the SDK could supply — deriving one, or defaulting `role` to
    `register` because it is convenient, would silently re-open the exact
    hazard those two rulings exist to prevent: registering content-hashes
    the section into Control Plane state and therefore into Decision Replay
    dimension 2, for a class the SDK does not own and cannot vouch for.
    Refuse. Do not default. Do not warn. Do not infer from the class id's
    prefix.

    Every missing field is named **together**, in one refusal — the
    multi-fault reporting style `~ccf.products.request.ProductRequestContract
    .from_declared` already established, so an adopter fixing a section does
    not discover its second missing field only after fixing the first.
    """
    missing = [
        field for field in _ADOPTER_OWNED_REQUIRED_FIELDS if field not in body
    ]
    if missing:
        names = ", ".join(repr(field) for field in missing)
        raise ValueError(
            f"the {section_name!r} section is adopter-owned; the SDK cannot"
            f" derive {names} for a class it does not own — they are"
            " required with no default (D-IMPL-80, D-IMPL-85), narrowed by"
            " D-IMPL-134 to classes the SDK owns and no further. Defaulting"
            " one would risk content-hashing this deployment's own data into"
            f" Decision Replay dimension 2 with nobody having chosen that."
            f" State {names} explicitly under {section_name!r}."
        )


def _derive_entry(
    *,
    label: str,
    body: Mapping[str, Any],
    semver: str,
    config_filename: str,
    default_class_id: str | None,
    wrapper: str | None,
) -> tuple[ManifestEntry, Mapping[str, Any]]:
    """Derive one `ManifestEntry` and its materialised document.

    Shared by every reserved section and every `operators:` entry — the
    derivation in design spec §12's order: `path` (refused if the section
    tried to name it), `key`, `class_id`, then `role`/`registration`.

    **The one collision the shipped SDK classes actually hit, and how it
    resolves.** Design spec §6.2 names the general hazard: the four override
    keys share a mapping with the section's own content, so *"a section
    whose... schema legitimately contains a field named role, key, class_id
    or registration cannot express it"* under the override syntax alone.
    Measured against every top-level-materialised SDK class this loader
    addresses, exactly one hits it: `~ccf.projection.plan.Perspective`
    (`ccf.perspective`, the `default_perspective` section) declares its own
    `role` — the Π role-conditioning `analyst`/`reviewer`/etc, whitepaper
    §7.5 — which is a different `role` than `ManifestEntry.role`
    (`register`/`load`) and is required on every `Perspective`, not rare.
    Left unresolved, design spec §8.1's own worked example — `default_perspective:
    {principal_id: ..., role: analyst}` — could not be authored: the bare
    string `'analyst'` fails `ManifestEntry.role`'s `register`/`load`
    literal the instant it is read as an override, and no single-file
    `default_perspective` section could ever both supply `Perspective.role`
    and let `ManifestEntry.role` derive silently. **Resolution, principled
    rather than hardcoded to this one class:** a reserved name that the
    *target class's own contract* already declares is content, not
    bookkeeping, and content wins — `ManifestEntry.role`/`.registration`
    fall back to their silent derivation (`register`/`typed`) instead of
    reading the section's colliding field, and the field's value flows
    through into the materialised document exactly as any other content key
    does. This only matters for a top-level document (`wrapper is None`):
    a wrapped section's content never shares the document's own top-level
    mapping with the bookkeeping keys, so no other materialisation shape can
    hit it. None of the four operator-parameter classes or the other three
    top-level SDK classes (`ProductClassDeclaration`, `EntityResolutionSpec`,
    `DebtProfile`) declare any of the four reserved names, so this resolves
    to a no-op for every section but `default_perspective` — a targeted fix
    for a measured collision, not a general escape hatch this module invents.
    `class_id` and `key` never collide with any shipped class's own fields
    and are not run through this precedence at all.

    Args:
        label: The section name, or the operator id for an `operators:`
            entry — used as the default `key` and in every message.
        body: The section's own mapping, override keys and all.
        semver: The config's own top-level `semver`, carried onto every
            materialised document (design spec §6).
        config_filename: The literal authoring filename every derived
            entry's `path` is.
        default_class_id: The `ccf.*` id an SDK-owned section or operator
            entry derives, or `None` for an adopter-owned section — see
            `_RESERVED_SECTIONS`'s own docstring for what `None` means here.
        wrapper: `None` for a top-level document, `"entries"` or
            `"declaration"` for a wrapped one — see `_RESERVED_SECTIONS`.
    """
    _refuse_reserved_path_override(label, body)

    key = str(body.get("key", label))

    if default_class_id is None:
        _refuse_adopter_owned_missing_fields(label, body)
        class_id = str(body["class_id"])
        resolved = resolve_artifact_class(class_id)
        role = body["role"]
        registration = body["registration"]
        collision_fields: frozenset[str] = frozenset()
    else:
        class_id = str(body.get("class_id", default_class_id))
        resolved = resolve_artifact_class(class_id)
        collision_fields = (
            frozenset(resolved.contract.model_fields) & {"role", "registration"}
            if wrapper is None
            else frozenset()
        )
        role = (
            "register"
            if "role" in collision_fields
            else body.get("role", "register")
        )
        registration = (
            "typed"
            if "registration" in collision_fields
            else body.get("registration", "typed")
        )

    # Every derived id, override or default alike, resolves through the same
    # lookup a manifest entry always does — so `D-IMPL-84`'s refusal of a
    # `ccf.`-prefixed id the SDK does not ship covers the derived path
    # exactly as it covers an authored one (T-16-29-03).
    #
    # Run on every entry, derived value and override alike — the same
    # class-wide posture `~ccf.deployment.manifest.load_and_boot` holds
    # every entry to, before anything is materialised.
    refuse_role_the_sdk_fixes(resolved.class_id, role)
    refuse_registration_the_sdk_fixes(resolved.class_id, registration)

    entry = ManifestEntry(
        path=config_filename,
        key=key,
        class_id=class_id,
        role=role,
        registration=registration,
    )

    reserved_keys_to_strip = set(_RESERVED_OVERRIDE_KEYS) - collision_fields
    stripped = {
        field: value
        for field, value in body.items()
        if field not in reserved_keys_to_strip
    }
    payload: Mapping[str, Any]
    if wrapper is None:
        payload = stripped
    elif wrapper == "declaration":
        payload = {"class_id": class_id, "declaration": stripped}
    else:
        payload = {wrapper: stripped}
    document: Mapping[str, Any] = {"semver": semver, **payload}
    return entry, document


def _refuse_operator_set_divergence(
    declared: frozenset[str], configured: frozenset[str]
) -> None:
    """R2 — the operator set enumerated twice (design spec §11.2).

    Neither `product_class.required_operator_keys` nor the `operators:`
    mapping's keys is authoritative; refusing beats picking, because only
    the deployment's author knows which of the two they meant.
    """
    if declared == configured:
        return
    raise ValueError(
        "operator set divergence: product_class.required_operator_keys"
        f" names {sorted(declared)} and the operators: section configures"
        f" {sorted(configured)}, differing on"
        f" {sorted(declared ^ configured)}; neither site is authoritative"
        " and only this deployment's author knows which is wrong (design"
        " spec §11.2) — refusing beats picking"
    )


def _refuse_malformed_unsupported_arguments(
    request_contract: Mapping[str, Any] | None,
) -> None:
    """`24.10-F-12` — the canonical shape is *name → authored reason*, at boot.

    SDK-defined per CLAUDE.md §11; the ruling of record is ``D-IMPL-288`` (2)
    (Dave): *"`F-12` is an SDK validation-timing defect, not an SDK schema
    defect. The Control Plane must reject an invalid `request_contract` at boot
    with a governed, field-specific refusal rather than allowing it to fail
    later with a bare `ValueError`. The canonical `unsupported_arguments:
    mapping[name, reason]` shape remains unchanged."*

    **The third sibling of** :func:`_refuse_operator_set_divergence` **and**
    :func:`_refuse_unproducible_seed_classes`, at the same call site and on the
    same before-materialisation ordering. The difference is what it holds: not
    two declarations against each other, but one declaration against the shape
    the SDK's own :class:`~ccf.products.request.ProductRequestContract` requires.

    **Why the timing is the defect.** ``request_contract`` is adopter-owned and
    **opaque at boot** (``D-IMPL-138`` (a)), so the Control Plane admitted a
    document whose ``unsupported_arguments`` was a bare list, and
    :meth:`~ccf.products.request.ProductRequestContract.from_declared` refused
    it three frames down with a bare ``ValueError`` — or, worse, an adopter
    hand-converted the list and manufactured the reasons, which is exactly the
    information the mapping exists to carry.

    **Deliberately narrow.** This validates ONE key's shape and nothing else.
    It is not general request-contract validation, and ``request_contract``
    stays adopter-owned in every other respect: the SDK owns this key because
    it is the SDK's own contract field, and judges no reason's content — any
    non-blank prose is admitted verbatim, because what makes an argument
    unsupported is the deployment's to say (CLAUDE.md §6.4).

    Raises:
        ValueError: ``unsupported_arguments`` is present and is not a mapping
            of parameter name to reason prose, naming the shape found; or is a
            mapping with blank reasons, naming every offender at once. A blank
            is refused for the reason the mapping exists: an argument declared
            unsupported with no stated reason is the bare list wearing a
            mapping's clothes.
    """
    if not request_contract:
        return
    declared = request_contract.get("unsupported_arguments")
    if declared is None:
        return
    if not isinstance(declared, Mapping):
        raise ValueError(
            "request_contract.unsupported_arguments is"
            f" {type(declared).__name__} and the canonical shape is a mapping"
            " of argument name to the reason it is unsupported"
            f" (found {declared!r}). A bare sequence names WHICH arguments are"
            " refused and never WHY, which is the half of the declaration the"
            " mapping exists to carry; a deployment that fills the reasons in"
            " code has authored filler, not an explanation (D-IMPL-288)"
        )
    blank = sorted(
        name
        for name, reason in declared.items()
        if not isinstance(reason, str) or not reason.strip()
    )
    if blank:
        raise ValueError(
            "request_contract.unsupported_arguments declares"
            f" {blank} with no reason prose; an argument declared unsupported"
            " with a blank reason asserts nothing an adopter could act on, and"
            " is the bare-sequence shape this key was given a mapping to"
            " replace. The SDK judges no reason's content — any non-blank"
            " prose is admitted verbatim (CLAUDE.md §6.4)"
        )


def _refuse_unproducible_seed_classes(
    operators: Mapping[str, Any] | None, resolution: Mapping[str, Any] | None
) -> None:
    """R-10 — an operator seeds on a class the resolution spec cannot mint.

    SDK-defined per CLAUDE.md §11. The ruling of record is ``D-IMPL-279``
    (Dave, 2026-09-08): *"The Control Plane should reject provably incompatible
    declarations at boot/config validation time. If the operator requires seed
    classes that the declared resolution/admission path cannot produce, that is
    a compositional configuration error, not a runtime 'empty graph' result.
    Only validate what can be proven statically; do not infer dynamic
    cardinality."*

    **The sibling of** :func:`_refuse_operator_set_divergence`, deliberately
    and at the same call site: two declarations in one document that cannot
    both be what their author meant, compared before anything is materialized,
    refused rather than reconciled. The difference is only which pair — that
    one holds ``required_operator_keys`` against the ``operators:`` keys, this
    one holds each operator's ``seed_entity_classes`` against the entity
    classes ``resolution.entity_rules`` declares it can mint.

    **STATIC ONLY, and the boundary is load-bearing.** This compares two
    declared SETS. It says nothing about whether any entity of a producible
    class will exist at run time, how many there will be, or whether a walk
    seeded on one will reach anything — all of which are properties of data
    this function never sees. A seed class that *no rule can produce* is
    unsatisfiable by construction; a seed class that *no envelope happened to
    produce* is an empty result, and the empty-operator guard is what speaks
    about that.

    **What it does NOT catch, stated so the check is not over-read.** cp-05's
    own instance of this failure (``CP-SPEC-005`` §F.4 finding 7) was a
    *runtime minting* error, not a declaration error: its config declared both
    ``exposure_anchor`` and ``exposure_member`` correctly, and its interpreter
    passed the wrong flag, so every node minted as a member and the walk seeded
    on an anchor that existed nowhere. **This function would have passed that
    config**, and says so here rather than letting a reader assume the finding
    is closed by it.

    Skips silently — the honest posture for *cannot be proven*, not a
    permissive default — when there is no ``resolution`` section, no
    ``entity_rules`` in it, or an operator declaring no ``seed_entity_classes``.
    """
    rules = ((resolution or {}).get("entity_rules")) or ()
    producible = frozenset(
        str(rule["entity_class"])
        for rule in rules
        if isinstance(rule, Mapping) and rule.get("entity_class")
    )
    if not producible:
        return
    for operator_id, body in sorted((operators or {}).items()):
        if not isinstance(body, Mapping):
            continue
        seeds = body.get("seed_entity_classes")
        if not seeds:
            continue
        unproducible = sorted({str(seed) for seed in seeds} - producible)
        if not unproducible:
            continue
        raise ValueError(
            f"unproducible seed class: operators.{operator_id} seeds on"
            f" {unproducible} and resolution.entity_rules declares only"
            f" {sorted(producible)}; a walk seeded on a class no resolution"
            " rule can mint returns nothing for every request this deployment"
            " will ever serve, which is a compositional configuration error"
            " rather than an empty graph (`D-IMPL-279`)"
        )


def derive_deployment(
    config: DeploymentConfig, config_filename: str = "ccf_config.yaml"
) -> DerivedDeployment:
    """Turn a parsed `DeploymentConfig` into a manifest and its documents.

    Purely over `config` — no file is read, no environment variable is
    consulted, and calling this twice on an equal `config` produces equal
    results (T-16-29-08). See the module docstring for the derive/validate
    boundary this function does not cross.

    Every section is processed once, in an order that lets an early refusal
    stop derivation before a later section is ever touched — since this
    function either returns one complete `DerivedDeployment` or raises,
    there is no partial result a caller could see: a malformed seventh
    section never leaves six materialised documents behind, on the same
    ordering argument `~ccf.deployment.manifest.load_and_boot` states for
    its own two-phase parse-then-register split.

    Args:
        config: The parsed, closed-world authoring document.
        config_filename: The literal name every derived entry's `path`
            becomes (design spec §11.1). Defaults to the name design spec
            §4 recommends.

    Returns:
        The manifest plus every materialised document, keyed by manifest
        key.

    Raises:
        ValueError: any of the five refusals design spec §6.1, §11.1 and
            §11.2 demand — an adopter-owned section missing `class_id`,
            `role` or `registration`; the declared and configured operator
            sets diverging; a section naming `path:`; a key collision after
            overrides (delegated to
            `~ccf.controlplane.artifacts.DeploymentManifest`'s own
            `_keys_are_unique`); or a config naming neither a `resolution:`
            /`policy:` section nor an explicit `resolution_spec_key`
            /`policy_bundle_key`. Also raised for an empty section (heading
            present, body absent), an operator id whose category is not one
            of the four canonical ones, and — via `resolve_artifact_class`
            — a `ccf.`-prefixed class id the SDK does not ship (`D-IMPL-84`).
    """
    entries: list[ManifestEntry] = []
    documents: dict[str, Mapping[str, Any]] = {}
    fields_set = config.model_fields_set

    # `product_class` — required. `DeploymentConfig.product_class` is a
    # non-optional field, so an author who wrote `product_class:` with
    # nothing under it is already refused by that contract (a mapping field
    # cannot validate `None`) before this function is ever called; no
    # empty-section check is needed here the way it is for the seven
    # optional sections below.
    product_class_default_class_id, product_class_wrapper = _RESERVED_SECTIONS[
        "product_class"
    ]
    entry, document = _derive_entry(
        label="product_class",
        body=config.product_class,
        semver=config.semver,
        config_filename=config_filename,
        default_class_id=product_class_default_class_id,
        wrapper=product_class_wrapper,
    )
    entries.append(entry)
    documents[entry.key] = document

    # `operators:` — optional, dynamically keyed. The divergence refusal
    # (R2) runs before any operator entry is derived, on the same
    # before-materialisation ordering every refusal here follows.
    _refuse_empty_section("operators", config.operators, fields_set)
    declared_operator_keys = frozenset(
        config.product_class.get("required_operator_keys") or ()
    )
    configured_operator_keys = frozenset((config.operators or {}).keys())
    _refuse_operator_set_divergence(declared_operator_keys, configured_operator_keys)
    # R-10 (`D-IMPL-279`), beside its sibling and on the same
    # before-materialisation ordering: two declared sets that cannot both be
    # what their author meant.
    _refuse_unproducible_seed_classes(config.operators, config.resolution)
    # `24.10-F-12` (`D-IMPL-288` (2)), the third sibling: one declaration held
    # against the shape the SDK's own request contract requires, refused here
    # rather than three frames down with a bare `ValueError`.
    _refuse_malformed_unsupported_arguments(config.request_contract)

    if config.operators:
        for operator_id, operator_body in sorted(config.operators.items()):
            category = operator_id.split(".", 1)[0]
            if category not in get_args(OperatorCategory):
                raise ValueError(
                    f"operators section names {operator_id!r}, whose"
                    f" category {category!r} is not one of"
                    f" {sorted(get_args(OperatorCategory))}; an operator id"
                    " is '<category>.<name>' and the category is the"
                    " segment before the first '.'"
                )
            entry, document = _derive_entry(
                label=operator_id,
                body=operator_body,
                semver=config.semver,
                config_filename=config_filename,
                default_class_id=f"{_OPERATOR_CLASS_PREFIX}{category}",
                wrapper=None,
            )
            entries.append(entry)
            documents[entry.key] = document

    # `policy_constraints:` — optional, dynamically keyed, and derived per key
    # exactly as `operators` is (`24.6-L-07`, `D-IMPL-253` Q3). One manifest
    # entry per label is what gives each constraint its own key, its own
    # content-hash version and its own effectivity window; a list under one key
    # would collapse all three, which is the "disappearing inside another
    # bundle" the ruling refuses. The class id is fixed here and never read
    # from the body, on the same discipline every SDK-owned section follows.
    _refuse_empty_section(
        "policy_constraints", config.policy_constraints, fields_set
    )
    if config.policy_constraints:
        constraint_class_id, constraint_wrapper = _RESERVED_SECTIONS[
            "policy_constraints"
        ]
        for label, constraint_body in sorted(config.policy_constraints.items()):
            entry, document = _derive_entry(
                label=f"policy_constraints.{label}",
                body=constraint_body,
                semver=config.semver,
                config_filename=config_filename,
                default_class_id=constraint_class_id,
                wrapper=constraint_wrapper,
            )
            entries.append(entry)
            documents[entry.key] = document

    # `producers:` (`D-IMPL-340`) — optional, dynamically keyed, one manifest
    # entry per label on the `policy_constraints` discipline, so each remote
    # producer registration has its own key, content-hash version and
    # effectivity. Appended AFTER the ordered sections below so every key
    # order that existed before this section did is byte-for-byte what it was.
    _refuse_empty_section("producers", config.producers, fields_set)
    producer_entries: list[tuple[ManifestEntry, Mapping[str, Any]]] = []
    producers_by_server: dict[str, McpProducerRegistration] = {}
    if config.producers:
        producer_class_id, producer_wrapper = _RESERVED_SECTIONS["producers"]
        for label, producer_body in sorted(config.producers.items()):
            entry, document = _derive_entry(
                label=f"producers.{label}",
                body=producer_body,
                semver=config.semver,
                config_filename=config_filename,
                default_class_id=producer_class_id,
                wrapper=producer_wrapper,
            )
            # Validated HERE, at derivation, not only at boot: a literal URL
            # or token in the section must never reach a derived document
            # (CINV-01; `D-IMPL-340` ruling 10).
            registration = parse_artifact(document, MCP_PRODUCER)
            assert isinstance(registration, McpProducerRegistration)  # MCP_PRODUCER's contract
            if registration.server in producers_by_server:
                raise ValueError(
                    f"two entries under `producers:` declare server"
                    f" {registration.server!r}; an mcp_product binding selects a"
                    " producer by that name, and one name naming two"
                    " registrations could only be resolved by a rule the"
                    " deployment never declared (D-IMPL-340)"
                )
            producers_by_server[registration.server] = registration
            producer_entries.append((entry, document))
    resolution_section_key: str | None = None
    policy_section_key: str | None = None
    section_keys: dict[str, str] = {}

    for section_name, config_body in (
        ("request_contract", config.request_contract),
        ("resolution", config.resolution),
        ("half_life", config.half_life),
        ("debt_profile", config.debt_profile),
        ("policy", config.policy),
        ("default_perspective", config.default_perspective),
        # `R-12` last, so every derived key order that existed before this
        # section did is byte-for-byte what it was: a config with no `replay:`
        # derives exactly what it derived before, and a config with one appends
        # rather than inserts.
        ("replay", config.replay),
        # `D-IMPL-343`: the two paved-road bindings, after `replay:` for the
        # same reason it sits after the six before it.
        ("ttl", config.ttl),
        ("door", config.door),
    ):
        _refuse_empty_section(section_name, config_body, fields_set)
        if config_body is None:
            continue
        default_class_id, wrapper = _RESERVED_SECTIONS[section_name]
        entry, document = _derive_entry(
            label=section_name,
            body=config_body,
            semver=config.semver,
            config_filename=config_filename,
            default_class_id=default_class_id,
            wrapper=wrapper,
        )
        entries.append(entry)
        documents[entry.key] = document
        section_keys[section_name] = entry.key
        if section_name == "resolution":
            resolution_section_key = entry.key
        elif section_name == "policy":
            policy_section_key = entry.key
        elif section_name == "ttl":
            # Validated HERE, at derivation, on the `producers:` precedent: a
            # non-positive window or a third key (`ttl_anchor_basis`, which one
            # canonical tree declared and nothing read) is refused by name
            # before any document is materialised.
            parse_artifact(document, TTL_BINDING)
        elif section_name == "door":
            # Validated HERE, at derivation, on the `producers:` precedent: a
            # principal, a role, a URL or a credential written under `door:`
            # is refused by name before any document is materialised, and the
            # asserted tenant is held to the deployment's own (R-6) when the
            # config declares one — `load_config_and_boot` holds it to the
            # resolved tenant in every case.
            door = parse_artifact(document, EGRESS_DOOR)
            assert isinstance(door, EgressDoorBinding)  # EGRESS_DOOR's contract
            if config.tenant_id is not None:
                _refuse_door_tenant_disagreement(door, config.tenant_id)

    for entry, document in producer_entries:
        entries.append(entry)
        documents[entry.key] = document

    # `agent:` (`D-IMPL-343` R-2) — optional, author-versioned, derived through
    # the versioned path and validated at derivation so a malformed composing
    # agent is refused before anything is registered. Appended LAST: a config
    # declaring none derives byte-for-byte what it derived before.
    # `skills:` (`D-IMPL-343` R-7) — optional, dynamically keyed, one
    # author-versioned `ccf.skill-catalog-entry` per label. Each is completed
    # from the declared keys it depends on (the product class's `requires`,
    # the `producers:` registrations) and validated at derivation, and each
    # registers under the `{tenant}/{class}/{name}` key its own grant resolves
    # it through. Appended after the producers and before the agent, so every
    # key order that existed before this section did is what it was.
    _refuse_empty_section("skills", config.skills, fields_set)
    skill_keys: list[str] = []
    requirements = _requirements_of(documents[entries[0].key]) if (config.skills or config.agent) else ()
    if config.skills:
        for label, skill_body in sorted(config.skills.items()):
            section = f"skills.{label}"
            completed = _complete_skill_entry(
                section,
                skill_body,
                name=label,
                requirements=requirements,
                producers=producers_by_server,
            )
            # The key the class fixes, computed by the one rule the catalog
            # and the grant ledger resolve through — from the COMPLETED and
            # tenant-filled document, so the two cannot disagree.
            probe, probe_document = _derive_versioned_entry(
                label=section,
                body=completed,
                config_filename=config_filename,
                class_id=_RESERVED_VERSIONED_SECTIONS["skills"],
                tenant_id=config.tenant_id,
            )
            parsed = parse_artifact(probe_document, SKILL_CATALOG_ENTRY)
            entry = ManifestEntry(
                path=probe.path,
                key=skill_catalog_key(parsed),  # type: ignore[arg-type]  # SKILL_CATALOG_ENTRY's contract
                class_id=probe.class_id,
                role=probe.role,
                registration=probe.registration,
            )
            entries.append(entry)
            documents[entry.key] = probe_document
            skill_keys.append(entry.key)

    # `agent:` (`D-IMPL-343` R-2) — optional, author-versioned, derived
    # through the versioned path, its derivable axes completed from the
    # deployment's own declarations, and validated at derivation so a
    # malformed composing agent is refused before anything is registered.
    # Appended LAST: a config declaring none derives byte-for-byte what it
    # derived before.
    _refuse_empty_section("agent", config.agent, fields_set)
    agent_key: str | None = None
    if config.agent is not None:
        entry, document = _derive_versioned_entry(
            label="agent",
            body=_complete_agent(
                config.agent,
                requirements=requirements,
                default_perspective=config.default_perspective,
                policy_key=policy_section_key,
                debt_profile_key=section_keys.get("debt_profile"),
                semver=config.semver,
            ),
            config_filename=config_filename,
            class_id=_RESERVED_VERSIONED_SECTIONS["agent"],
            tenant_id=config.tenant_id,
        )
        parse_artifact(document, resolve_artifact_class(entry.class_id))
        entries.append(entry)
        documents[entry.key] = document
        agent_key = entry.key

    # The two top-level boot pointers (design spec §6.3): derived from the
    # section names, an explicit top-level value on the config wins.
    resolution_spec_key = config.resolution_spec_key or resolution_section_key
    policy_bundle_key = config.policy_bundle_key or policy_section_key

    if resolution_spec_key is None:
        raise ValueError(
            "no resolution_spec_key: boot() needs a pinned version for the"
            " entity-resolution spec in force, and this config names"
            " neither a 'resolution:' section nor an explicit"
            " 'resolution_spec_key' — add a 'resolution:' section, or state"
            " 'resolution_spec_key' explicitly if the spec is registered"
            " under another name"
        )
    if policy_bundle_key is None:
        raise ValueError(
            "no policy_bundle_key: boot() needs a pinned version for the"
            " policy bundle in force, and this config names neither a"
            " 'policy:' section nor an explicit 'policy_bundle_key' — add a"
            " 'policy:' section, or state 'policy_bundle_key' explicitly if"
            " the bundle is registered under another name"
        )

    # R4 (key collision) and the boot-pins-must-be-registered check are both
    # delegated to `DeploymentManifest`'s own validators — one rule, one
    # site — rather than re-implemented here. `_keys_are_unique`'s own
    # docstring is where the rejected `(path, key)` alternative is named;
    # see design spec §11.1 for why it was not taken.
    manifest = DeploymentManifest(
        semver=config.semver,
        artifacts=tuple(entries),
        backend=config.backend,
        backend_secrets=config.backend_secrets,
        resolution_spec_key=resolution_spec_key,
        policy_bundle_key=policy_bundle_key,
        tenant_id=config.tenant_id,
        survivor_cap=config.survivor_cap,
    )
    keys = DeploymentKeys(
        product_class=entries[0].key,
        request_contract=section_keys.get("request_contract"),
        policy_bundle=policy_bundle_key,
        resolution_spec=resolution_spec_key,
        half_life=section_keys.get("half_life"),
        debt_profile=section_keys.get("debt_profile"),
        default_perspective=section_keys.get("default_perspective"),
        replay=section_keys.get("replay"),
        ttl=section_keys.get("ttl"),
        door=section_keys.get("door"),
        agent=agent_key,
        operator_parameters=tuple(
            entry.key
            for entry in entries
            if entry.class_id.startswith(_OPERATOR_CLASS_PREFIX)
        ),
        policy_constraints=tuple(
            entry.key
            for entry in entries
            if entry.class_id == _RESERVED_SECTIONS["policy_constraints"][0]
        ),
        producers=tuple(entry.key for entry, _document in producer_entries),
        skills=tuple(skill_keys),
    )
    return DerivedDeployment(manifest=manifest, documents=documents, keys=keys)


def load_config_and_boot(
    config_path: str | Path,
    *,
    registry: ControlPlaneProtocol,
    connection: Mapping[str, object] | None = None,
    tenant_id: str | None = None,
) -> BootedFabric:
    """Load a `ccf_config.yaml`, derive what a manifest would have named, and boot.

    The single-file front door `D-IMPL-136` commits to. `load_and_boot`'s
    sibling — same signature shape, same `BootedFabric` shape, same
    preflight, and the **same register loop**, reached through
    :func:`~ccf.deployment.manifest._register_and_boot` rather than a second
    copy of it (`16-30`; see that function's own docstring for why a copy
    would be a hazard rather than a convenience).

    What this call does, in order:

    1. Parses the config through :func:`~ccf.controlplane.artifacts.load_artifact`
       against :data:`~ccf.controlplane.artifacts.DEPLOYMENT_CONFIG` — the same
       loader `load_and_boot` uses for a manifest, so the same float and
       naive-timestamp refusals apply.
    2. **Derives** a `DeploymentManifest` and one materialised document per
       section through :func:`derive_deployment` — pure over the parsed
       config, no file read, no environment read.
    3. **Preflights** the tenant, the D-IMPL-80 role and the D-IMPL-85
       registration path of every derived entry, and the declared adapter
       against what this deployment has installed and against ``connection``
       — through :func:`~ccf.deployment.manifest._preflight_entries` and
       :func:`~ccf.deployment.manifest._preflight_adapter`, the same
       functions `load_and_boot` calls. **The derived path resolves to a
       real file, and that is the point:** every derived entry's ``path`` is
       the config's own filename, so the preflight resolves all of them to
       the config document itself — inside the deployment, passing both
       `ManifestEntry` validators and the symlink check. The key → path
       mapping this returns is therefore total and constant; this function
       does not read it back, because the derived documents are already in
       memory. Running the preflight anyway is what holds a derived manifest
       to the same refusal surface an authored one gets — a check skipped
       for this door would be a door the audit plane knows less about.
    4. Validates **every** materialised document through
       :func:`~ccf.controlplane.artifacts.parse_artifact` against the class
       its own derived entry names, then calls
       :func:`~ccf.deployment.manifest._register_and_boot` — the same
       function `load_and_boot` calls — to register the ``role: register``
       ones and boot.

    **What this call does not do — the abstraction line, inherited rather
    than re-decided.** Exactly the boundary `load_and_boot`'s own docstring
    states in the negative, for the same reason (the module docstring's
    *"boundary this module must not cross"*): it does not execute operators,
    does not project, does not build a Context Product, does not run the
    three validation gates, and does not construct a product's lineage
    record.

    **No `config_path` parameter on `load_and_boot`, and no auto-detection by
    filename, considered and rejected.** Two names, two doors, one shared
    spine (`_register_and_boot`). Auto-detection would make *which loader
    ran* a function of a filename, and the loader in force is a fact replay
    should be able to read off the call site — a `Union[manifest, config]`
    argument, or a `load_and_boot` that peeks at the document's shape, would
    both hide that fact behind a guess.

    **What a `ccf_config.yaml` cannot express, by design.** There is no
    `signal_batch` section — see the module docstring's own paragraph on
    this. A deployment that puts a signal batch in its manifest keeps its
    manifest, which the dual model supports indefinitely (Dave's ruling,
    2026-08-14); a config-form deployment that needs one authors a manifest
    alongside it and calls `load_and_boot` instead, which is out of scope
    here and not half-built toward.

    Args:
        config_path: The single-file authoring document. Every derived
            entry's ``path`` is this file's own name, resolved relative to
            **this file's own directory** — never the process's working
            directory, and never able to leave it, for the same two-check
            reason `load_and_boot`'s own `manifest_path` cannot.
        registry: The Control Plane to register into. A caller argument,
            never constructed here — see `load_and_boot`'s own docstring.
        connection: The declared adapter's connection settings. See
            `load_and_boot`'s own docstring; nothing here widens it. No
            field of `DeploymentConfig` may name a connection value either
            (D-08, T-16-28-02).
        tenant_id: The deployment's tenant, when the config does not name it.

    Raises:
        See `load_and_boot`'s own `Raises:` block — every refusal there
        applies here identically, because both doors run the same preflight
        and the same register loop. `derive_deployment` additionally raises
        the five refusals its own docstring names, before any of those run.
    """
    config_file = Path(config_path)
    config = load_artifact(
        config_file.read_text(encoding="utf-8"), DEPLOYMENT_CONFIG
    )
    assert isinstance(config, DeploymentConfig)  # DEPLOYMENT_CONFIG's contract

    derived = derive_deployment(config, config_filename=config_file.name)
    manifest = derived.manifest

    resolved_tenant = _resolve_tenant(manifest, tenant_id)
    root = config_file.parent
    # The returned mapping is deliberately unused: the derived documents are
    # already in memory (`derived.documents`), so only the preflight's
    # refusals matter here. See this function's own docstring, "The derived
    # path resolves to a real file, and that is the point."
    _preflight_entries(manifest, root)
    adapter = _preflight_adapter(manifest, connection or {})
    secrets = _resolve_secret_references(manifest, adapter)

    parsed: dict[str, CCFContract] = {}
    for entry in manifest.artifacts:
        artifact_class = resolve_artifact_class(entry.class_id)
        parsed[entry.key] = parse_artifact(derived.documents[entry.key], artifact_class)

    # `D-IMPL-343` R-6, against the RESOLVED tenant: a config that declares no
    # `tenant_id` and takes it from the caller still asserts, at its door, the
    # tenant it actually runs as.
    if derived.keys.door is not None:
        door = parsed[derived.keys.door]
        assert isinstance(door, EgressDoorBinding)  # its entry names EGRESS_DOOR
        _refuse_door_tenant_disagreement(door, resolved_tenant)

    return _register_and_boot(
        manifest,
        parsed,
        registry=registry,
        connection=connection,
        secrets=secrets,
        resolved_tenant=resolved_tenant,
        keys=derived.keys,
    )
