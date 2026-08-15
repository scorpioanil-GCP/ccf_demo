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

There is no `signal_batch` section among the eight reserved names, and that is
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
from ccf.controlplane.artifacts import (
    DEPLOYMENT_CONFIG,
    DeploymentConfig,
    DeploymentManifest,
    ManifestEntry,
    load_artifact,
    parse_artifact,
)
from ccf.controlplane.registry import ControlPlaneProtocol
from ccf.deployment.classes import (
    refuse_registration_the_sdk_fixes,
    refuse_role_the_sdk_fixes,
    resolve_artifact_class,
)
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


#: What the loader knows about each of the seven reserved, non-`operators`
#: section names — the reserved-section table design spec §6 describes.
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
}


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
    """

    manifest: DeploymentManifest
    documents: Mapping[str, Mapping[str, Any]]


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

    resolution_section_key: str | None = None
    policy_section_key: str | None = None

    for section_name, config_body in (
        ("request_contract", config.request_contract),
        ("resolution", config.resolution),
        ("half_life", config.half_life),
        ("debt_profile", config.debt_profile),
        ("policy", config.policy),
        ("default_perspective", config.default_perspective),
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
        if section_name == "resolution":
            resolution_section_key = entry.key
        elif section_name == "policy":
            policy_section_key = entry.key

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
    return DerivedDeployment(manifest=manifest, documents=documents)


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

    return _register_and_boot(
        manifest,
        parsed,
        registry=registry,
        connection=connection,
        secrets=secrets,
        resolved_tenant=resolved_tenant,
    )
