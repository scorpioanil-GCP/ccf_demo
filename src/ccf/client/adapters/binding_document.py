"""``binding.yaml`` — a **data** document, with exactly one named exception.

**SDK-defined and RULED.** ``D-IMPL-141`` in ``docs/DECISIONS.md`` records the
ruling; ``docs/superpowers/specs/2026-08-16-reference-plan-factory-and-debt-scorer.md``
**Amendment A** is the ruling being implemented. The shape this module used to
carry — ``resolver:`` and ``question:`` as ``<module>:<attribute>`` factories the
loader imports and calls — was **rejected by Dave on 2026-08-16** for
reintroducing producer Python into a deployment directory, the shape declined at
the 2026-08-15 brainstorm.

What replaced it, and why
--------------------------
Measurement dissolved most of the argument for factories (spec §3).
:class:`~ccf.projection.plan.Perspective` is **two plain strings**;
:attr:`~ccf.products.request.ProductRequest.subject`,
:attr:`~ccf.products.request.ProductRequest.intent` and
:attr:`~ccf.products.request.ProductRequest.freshness` are **plain ``str``**.
None of them needs computing, so none of them needs a factory. They are
declared here as data.

One gap survived measurement and only one (Amendment A.2):
:class:`~ccf.projection.plan.ProjectionPlan` is **itself a Protocol** — code,
not data — and no declarative plan artifact exists in the tree. Mapping a
:class:`~ccf.graph.protocols.GraphView` of entities onto a payload schema's
declared fields is *invention*, not mapping. So the deployment supplies the
projection, and **nothing else**.

The mechanism that keeps the exception an exception
-----------------------------------------------------
Amendment A.4's load-bearing sentence is *"an exception with no mechanism
holding it narrow is not an exception; it is a precedent."* This module is that
mechanism, and it enforces the narrowing **twice**, because either check alone
leaks:

* :data:`RULED_OUT_KEYS` refuses ``resolver:`` and ``connection``-as-a-reference
  **by name**, with a message that says the key was ruled out and points at the
  spec. A refusal that only said *"unknown key"* would read as a typo report and
  invite a re-spelling.
* :func:`looks_like_a_reference` refuses a ``<module-path>:<attribute>``-shaped
  value **in any data position**, naming the position. Without it a deployment
  could smuggle a second reference through a key the schema *does* permit — and
  the schema would have been widened by nobody's decision. Key-name refusal
  alone cannot see that; shape refusal alone would let ``resolver:`` return
  under a new spelling.

Keeping :data:`REFERENCE_KEYS` a **one-element** tuple is deliberate. It is the
single place a second exception could be introduced, so introducing one is a
visible edit to a named constant rather than a widened condition inside a
branch.

What survived the rejection, and is kept here
-----------------------------------------------
``binding.yaml`` is **deployment-environment material, never a Control Plane
artifact**: not registered, not content-hashed, carrying no ``semver``, and it
never reaches Decision Replay dimension 2. That posture is why connection
material may live here at all —
``docs/superpowers/specs/2026-08-15-ccf-client-design.md`` §9 keeps connection
material out of content-hashed state, and a *Control Plane* document naming a
store would put deployment environment inside the audit plane.

The strict loader survives too: an unknown top-level key is refused **by name**
rather than ignored, in the :class:`~ccf.controlplane.artifacts.DeploymentConfig`
posture. So does containment: every path resolved here stays inside the root,
refusing an absolute path, a ``..`` segment, *and* a plain name that resolves
out — the two-check rule :class:`~ccf.controlplane.artifacts.ManifestEntry`
already holds a manifest to.

Trust posture, stated rather than implied
-------------------------------------------
Loading the one permitted reference **executes the deployment's Python**. That
is threat ``T-17-19`` and it is *accepted*: the deployment root is the
deployment's own trust boundary, exactly as ``ccf_config.yaml`` already is, and
the process is already running that deployment's code. What is enforced rather
than trusted is containment, and the fact that there is exactly **one** such
reference rather than an open set.

This module is algorithmic (CINV-03): document parsing, path resolution and a
module import. No clock, no LLM dependency ever.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml

from ccf.client.errors import BindingError
from ccf.products.resolver import ProjectionPlanFactoryProtocol
from ccf.projection.plan import Perspective

__ccf_mode__ = "algorithmic"

__all__ = [
    "BINDING_DOCUMENT_NAME",
    "DATA_KEYS",
    "OPTIONAL_KEYS",
    "REFERENCE_KEYS",
    "RULED_OUT_KEYS",
    "BindingDocument",
    "DebtDeclaration",
    "QuestionDeclaration",
    "conforming_plan_factory",
    "load_binding_document",
    "load_reference",
    "looks_like_a_reference",
]


#: The filename a deployment root carries. One name, referenced everywhere the
#: loader reports a refusal, so a rename is a single edit rather than a search.
BINDING_DOCUMENT_NAME = "binding.yaml"

#: **The whole permitted reference surface, and it has one element.**
#:
#: Amendment A.3 grants the deployment *one* Python module — the projection —
#: and A.4 requires the loader to refuse any other ``module:attribute``
#: reference by name. A tuple rather than a bare string because the refusals
#: below enumerate it, and because widening the exception must be an edit to
#: this constant that a reviewer can see, not a condition somewhere in a branch.
REFERENCE_KEYS: tuple[str, ...] = ("plan",)

#: Keys a binding document states as **data**. Required, all of them: a document
#: omitting one is refused by name, because a deployment that meant to supply it
#: and mistyped it should be told which.
#:
#: ``question`` and ``perspective`` are here rather than behind factories
#: because measurement said so (spec §3) — two plain strings and three plain
#: ``str``\\ s do not need computing. The remainder are the resolver arguments
#: :class:`~ccf.products.resolver.GovernedResolver` takes that are plain data.
DATA_KEYS: tuple[str, ...] = (
    "config",
    "question",
    "perspective",
    "product_class_key",
    "request_contract_key",
    "operator_parameter_keys",
    "policy_bundle_key",
    "replay_record_class",
    "query_pin_class",
    "max_ttl_seconds",
    "product_ttl_seconds",
    "artifact_store",
    "debt",
)

#: Keys a binding document may state. ``connection`` carries the declared
#: adapter's own settings as **data** — see :func:`_connection` for why a value
#: may be a scalar or a rooted path and for nothing else. A deployment whose
#: backend needs no settings omits it; omission is a positive statement.
#:
#: ``server`` names this deployment's own server program — the single path a
#: transport that must *launch* something would otherwise have to be told by
#: the client, which is the client's business only by accident (``D-01``). It
#: is the one key resolved against the directory **holding** the deployment
#: rather than against the deployment root, because a server program is not
#: deployment content. Omitting it is likewise a positive statement, and it is
#: the ordinary one: a deployment reached at an endpoint launches nothing and
#: declares no server at all.
OPTIONAL_KEYS: tuple[str, ...] = ("connection", "server")

#: Keys that were **ruled out**, mapped to what to do instead.
#:
#: Refused by name and separately from an unknown key, because the two are
#: different mistakes with different remedies. An unknown key is a typo; one of
#: these is a deployment following the shape ``D-IMPL-141`` proposed before it
#: was rejected, and telling its author *"not a binding-document key"* would
#: invite a re-spelling of the very thing that was declined.
RULED_OUT_KEYS: Mapping[str, str] = {
    "resolver": (
        "the SDK builds the resolver itself from the data keys below — a"
        " deployment supplies the projection through `plan:` and nothing else"
    ),
    "connection_factory": (
        "connection material is data under `connection:`, not a factory the"
        " loader imports and calls"
    ),
}


@dataclass(frozen=True, kw_only=True)
class QuestionDeclaration:
    """The request vocabulary a deployment declares, measured to be data.

    Spec §3: ``subject``, ``intent`` and ``freshness`` are plain ``str`` on
    :class:`~ccf.products.request.ProductRequest`, so a factory to produce them
    would be a factory producing constants.

    ``asked_at`` **is not the fallback for** ``as_of=None``, and this docstring
    used to say it was. ``D-04`` rules that ``as_of=None`` means *the server's
    decision instant*, and ``~ccf.client.client.ProductClient.ask`` spells that
    out as the producing deployment answering against its own **clock**. Reading
    a declared literal instead made the default path answer as of a fixed moment
    in the document: the Phase 17 close review measured the shipped example
    printing ``answer expires 2026-03-02 12:10:00+00:00`` on 2026-08-16 with no
    ``--as-of``, five and a half months expired, against a README promising
    "today's answer". Ruled by Dave 2026-08-16 — ``None`` resolves to now, in
    ``~ccf.client.adapters.inprocess.InProcessAdapter.ask``.

    The field remains declared, validated as a **zoned** ISO 8601 instant, and
    is retained as an explicit demonstration value per that same ruling. **No
    code path reads it.** Whether a required-but-unread field should stay
    required, become optional, or be removed is an open question surfaced with
    the Phase 17 gate package rather than decided here — widening a ruled
    closed-world schema (``D-IMPL-141``) is not an in-phase fix.

    Attributes:
        subject: What the question is about.
        intent: Why it is being asked.
        freshness: How current the answer must be.
        asked_at: An OPTIONAL declared, zone-bearing instant, or ``None`` when
            the document states none. Demonstration only — it is **not**
            consulted when a caller passes no temporal boundary.
    """

    subject: str
    intent: str
    freshness: str
    asked_at: datetime | None


@dataclass(frozen=True, kw_only=True)
class DebtDeclaration:
    """Where ``D_c``'s inputs come from, and the two the SDK cannot measure.

    ``17-11`` shipped :class:`~ccf.products.debt_scorer.AssemblyDebtScorer`, the
    reference ``GraphView`` → ``DebtAssessment`` adapter, and measured that
    ``C`` and ``S`` have **no** SDK reference scorer —
    :class:`~ccf.halflife.assessment.DebtFactors` records that position in its
    own docstring. So a deployment either measures them itself or *declares*
    them, and a declared value lands in replay under
    :class:`~ccf.products.debt_scorer.DeclaredFactor`'s own scorer pin: an
    examiner can tell an assertion from a measurement without reading code.

    Declared here rather than defaulted in library code because a default would
    be the SDK choosing a debt figure for every deployment, inside a delivered
    product's content address — the ``D-IMPL-38`` defect this whole pause exists
    to remove, reappearing one layer down.

    Attributes:
        half_life_key: Control Plane key of this deployment's ``λ_c`` table.
        debt_profile_key: Control Plane key of its ``D_c`` bands.
        completeness: The ``C`` this deployment asserts, pending a measurement.
        semantic_consistency: The ``S`` this deployment asserts.
    """

    half_life_key: str
    debt_profile_key: str
    completeness: Decimal
    semantic_consistency: Decimal


@dataclass(frozen=True, kw_only=True)
class BindingDocument:
    """One deployment root's wiring: data, plus the single permitted reference.

    Every path here is **already resolved and already contained** — the loader
    refuses anything landing outside the root, so a consumer of this type never
    re-checks and never holds a second, weaker copy of the rule.

    Attributes:
        root: The deployment root, resolved absolute. This is the value the
            in-process adapter keys its boot cache on — see
            :mod:`ccf.client.adapters.inprocess` for why resolving it here
            rather than there is what makes ``./deployment`` and its absolute
            spelling one cache entry.
        config: The deployment's ``ccf_config.yaml``, resolved absolute.
        plan: **The one** ``<module>:<attribute>`` reference this document is
            permitted to carry, verbatim as authored. Amendment A.3.
        question: The declared request vocabulary.
        perspective: The Π role-conditioning questions here are served under.
        product_class_key: Control Plane key of the served class.
        request_contract_key: Control Plane key of the request contract.
        operator_parameter_keys: Control Plane keys of the operator parameters.
        policy_bundle_key: Control Plane key of the policy regime in force.
        replay_record_class: Artifact class replay records are filed under.
        query_pin_class: Artifact class executed-query bytes are filed under.
        max_ttl_seconds: The class's registered TTL ceiling.
        product_ttl_seconds: A served product's own lifetime. Two figures, and
            they stay two — one serving as both would have Gate 3 compare a
            ceiling against itself.
        artifact_store: Where this deployment files artifacts, resolved absolute
            and contained.
        debt: Where ``D_c``'s inputs come from.
        connection: The declared adapter's own settings, already composed, or
            ``None`` when the document stated none.
        server: This deployment's own server program, resolved absolute against
            the directory **holding** the deployment, or ``None`` when the
            deployment states none. Contained but **not** existence-checked:
            whether the program has to be there is the transport's question,
            and an in-process deployment never asks it.
    """

    root: Path
    config: Path
    plan: str
    question: QuestionDeclaration
    perspective: Perspective
    product_class_key: str
    request_contract_key: str
    operator_parameter_keys: tuple[str, ...]
    policy_bundle_key: str
    replay_record_class: str
    query_pin_class: str
    max_ttl_seconds: int
    product_ttl_seconds: int
    artifact_store: Path
    debt: DebtDeclaration
    connection: Mapping[str, object] | None
    server: Path | None


def looks_like_a_reference(value: object) -> bool:
    """Is ``value`` shaped like a ``<module-path>:<attribute>`` reference?

    **This is the check that keeps Amendment A.3's exception from widening.**
    Refusing unknown *keys* cannot see a reference smuggled through a key the
    schema permits, and a schema widened by nobody's decision is exactly the
    precedent A.4 forbids.

    The shape is deliberately narrow — a module path ending ``.py``, a colon,
    and a non-empty attribute — because the alternative *"contains a colon"*
    would refuse every declared timestamp in the document. ``asked_at:
    2026-03-02T12:00:00+00:00`` carries three colons and is data; a value is a
    reference when it names a **Python file**, which is the property that makes
    it executable and therefore the property worth refusing.

    Args:
        value: Any value from the document. Non-strings are never references.

    Returns:
        ``True`` when the value names a Python module and an attribute in it.
    """
    if not isinstance(value, str):
        return False
    module_path, separator, attribute = value.partition(":")
    if not separator:
        return False
    return module_path.strip().endswith(".py") and bool(attribute.strip())


def _refuse_references_in_data(
    value: object, *, position: str, document: Path
) -> None:
    """Walk ``value`` and refuse any reference-shaped scalar, naming where.

    Recursive because the data keys are not all scalars: ``question`` and
    ``perspective`` are mappings, ``operator_parameter_keys`` is a sequence, and
    a check that only looked at top-level values would leave a nested position
    as an unguarded way in.

    Raises:
        ccf.client.errors.BindingError: a reference-shaped value appears
            somewhere other than :data:`REFERENCE_KEYS`. The message names the
            **position**, dotted, so an adopter is told which line to change.
    """
    if isinstance(value, Mapping):
        for key, nested in value.items():
            _refuse_references_in_data(
                nested, position=f"{position}.{key}", document=document
            )
        return
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for index, nested in enumerate(value):
            _refuse_references_in_data(
                nested, position=f"{position}[{index}]", document=document
            )
        return
    if looks_like_a_reference(value):
        raise BindingError(
            f"`{position}: {value}` in {document} is a"
            " `<module-path>:<attribute>` reference in a **data** position."
            f" This document carries exactly one reference, under"
            f" {', '.join(f'`{key}`' for key in REFERENCE_KEYS)}, and it names"
            " this deployment's projection. Every other key is data — see"
            " `docs/superpowers/specs/2026-08-16-reference-plan-factory-and-"
            "debt-scorer.md` Amendment A.3, which grants the deployment one"
            " Python module and no second one"
        )


def _contained(
    candidate: str,
    *,
    root: Path,
    key: str,
    document: Path,
    base_description: str = "the deployment root",
) -> Path:
    """Resolve ``candidate`` inside ``root``, or refuse it by name.

    The containment rule :class:`~ccf.controlplane.artifacts.ManifestEntry`
    already applies to a manifest, applied here for the same reason: a binding
    document is deployment-authored and is trusted no further, so it does not
    get to name a path outside the deployment it describes. Both checks are
    needed and neither covers the other — the string check refuses an absolute
    path or a ``..`` segment as written, and the resolved check closes a plain
    name that is a symlink out.

    Args:
        base_description: What ``root`` **is**, in the caller's words, so a
            refusal describes the directory it actually resolved against.
            Almost every key here is rooted at the deployment and takes the
            default; ``server:`` is rooted at the directory *holding* the
            deployment and says so. Defaulted rather than required because a
            refusal that misnames the base sends an adopter to the wrong file,
            and the way that defect arrives is a caller not thinking about it —
            so the callers that need no thought are the ones that pass nothing.
    """
    written = Path(candidate)
    if written.is_absolute() or ".." in written.parts:
        raise BindingError(
            f"`{key}: {candidate}` in {document} names a path outside"
            f" {base_description} — a binding document describes the deployment"
            " it sits in, so its paths are relative and carry no `..` segment"
            " and no leading `/`"
        )
    resolved = (root / written).resolve()
    if resolved != root and root not in resolved.parents:
        raise BindingError(
            f"`{key}: {candidate}` in {document} resolves to {resolved}, which"
            f" is outside {base_description} {root} — a plain name that is a"
            " symlink out is refused for the same reason a `..` segment is"
        )
    return resolved


def _mapping(parsed: Mapping[str, Any], *, key: str, document: Path) -> Mapping[str, Any]:
    """The value at ``key``, refused unless it is a mapping."""
    value = parsed[key]
    if not isinstance(value, Mapping):
        raise BindingError(
            f"`{key}:` in {document} parsed as `{type(value).__name__}`, not a"
            " mapping of names to values"
        )
    return value


def _field(
    section: Mapping[str, Any], *, key: str, field: str, document: Path
) -> str:
    """One required string out of a declared mapping, refused by name if absent."""
    value = section.get(field)
    if value is None or not str(value).strip():
        raise BindingError(
            f"`{key}:` in {document} omits `{field}` — the section states"
            f" {', '.join(f'`{name}`' for name in sorted(section))} and a"
            f" binding document's `{key}` needs `{field}` as well"
        )
    return str(value)


def _decimal(
    section: Mapping[str, Any], *, key: str, field: str, document: Path
) -> Decimal:
    """One declared decimal, refused rather than coerced through a float.

    ``str`` first and never ``float``: a binding document is hand-authored, and
    ``Decimal(0.1)`` is not ``Decimal("0.1")``. The refusal names the field
    because *"invalid decimal"* on its own costs the reader the diagnosis.
    """
    raw = _field(section, key=key, field=field, document=document)
    try:
        return Decimal(raw)
    except InvalidOperation as malformed:
        raise BindingError(
            f"`{key}.{field}: {raw}` in {document} is not a decimal number"
        ) from malformed


def _integer(parsed: Mapping[str, Any], *, key: str, document: Path) -> int:
    """One declared integer, refused rather than coerced from a float.

    A ``float`` is refused by type rather than truncated, in the posture
    :func:`~ccf.controlplane.artifacts.load_artifact` already takes for a
    manifest: a TTL silently rounded is a governance figure nobody authored.
    """
    value = parsed[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise BindingError(
            f"`{key}: {value}` in {document} is `{type(value).__name__}`, not a"
            " whole number of seconds"
        )
    return value


def _connection(
    parsed: Mapping[str, Any], *, root: Path, document: Path
) -> Mapping[str, object] | None:
    """Compose the declared adapter's own settings from data.

    **The SDK learns no adapter's vocabulary here**, which is the objection that
    sank the rejected ``connection:``-as-a-factory shape and is preserved: the
    *names* under this key are the declared adapter's, this loader never reads
    one, and the composed mapping is validated against the adapter's own
    contract by :func:`~ccf.deployment.manifest._preflight_adapter`.

    Two value forms, because one is not enough and three would be a language:

    * a **scalar**, carried verbatim;
    * a single-key mapping ``{path: <relative>}``, resolved against the
      deployment root and contained. This form exists because a rooted path is
      the one setting a deployment genuinely cannot spell as a literal — the
      root is not known until the client names it, and a relative path would
      resolve against the *caller's* working directory, which is a different
      deployment on every invocation.

    A credential never belongs here: this document is deployment-environment
    material sitting in the deployment's own tree, and the *store* it names is
    a path. ``docs/superpowers/specs/2026-08-15-ccf-client-design.md`` §9 keeps
    connection material out of content-hashed state, and nothing here is
    content-hashed.
    """
    if "connection" not in parsed:
        return None
    declared = _mapping(parsed, key="connection", document=document)
    composed: dict[str, object] = {}
    for setting, value in declared.items():
        if isinstance(value, Mapping):
            if set(value) != {"path"}:
                raise BindingError(
                    f"`connection.{setting}:` in {document} states"
                    f" {', '.join(f'`{name}`' for name in sorted(value))} — a"
                    " connection setting is a plain value, or `{path: …}` for a"
                    " path resolved against the deployment root"
                )
            composed[str(setting)] = str(
                _contained(
                    str(value["path"]),
                    root=root,
                    key=f"connection.{setting}.path",
                    document=document,
                )
            )
            continue
        composed[str(setting)] = value
    return composed


def load_binding_document(root: str | Path) -> BindingDocument:
    """Read and validate the binding document at ``root``.

    Strict in the :class:`~ccf.controlplane.artifacts.DeploymentConfig`
    posture: an unknown top-level key is refused **by name** rather than
    ignored. A typo in deployment wiring that silently selected a default is a
    deployment running configuration nobody authored, and it would surface as a
    wrong answer rather than as a failed boot.

    The refusals run in a deliberate order — ruled-out keys before unknown ones,
    and the reference-shape sweep before any value is read — so an adopter
    carrying the rejected ``D-IMPL-141`` shape is told *that* rather than being
    told a key is unrecognised.

    Args:
        root: The deployment root the binding address named.

    Returns:
        The parsed document, with every path resolved and contained.

    Raises:
        ccf.client.errors.BindingError: the root does not exist, carries no
            binding document, states a key that was ruled out, states a key that
            is not a key, omits a required one, carries a ``module:attribute``
            reference in a data position, or names a path outside itself. Each
            message names the file and the key at fault, because a refusal that
            does not say what to fix costs the reader the diagnosis the loader
            already did.
    """
    root_path = Path(root).expanduser().resolve()
    document = root_path / BINDING_DOCUMENT_NAME

    if not root_path.is_dir():
        raise BindingError(
            f"`{root}` is not a deployment root — it resolves to {root_path},"
            " which is not a directory. An in-process binding address names the"
            f" directory holding the deployment's `{BINDING_DOCUMENT_NAME}`"
        )
    if not document.is_file():
        raise BindingError(
            f"{root_path} carries no `{BINDING_DOCUMENT_NAME}`, so there is"
            " nothing naming this deployment's config, its question or its"
            f" projection. Add `{BINDING_DOCUMENT_NAME}` stating"
            f" {', '.join(f'`{key}:`' for key in (*DATA_KEYS, *REFERENCE_KEYS))}"
        )

    parsed = yaml.safe_load(document.read_text(encoding="utf-8"))
    if not isinstance(parsed, Mapping):
        raise BindingError(
            f"{document} is not a mapping of keys to values — a binding"
            f" document states {', '.join(f'`{key}:`' for key in DATA_KEYS)}"
            f" and {', '.join(f'`{key}:`' for key in REFERENCE_KEYS)} at its top"
            f" level, and this one parsed as `{type(parsed).__name__}`"
        )

    ruled_out = [str(key) for key in parsed if str(key) in RULED_OUT_KEYS]
    if ruled_out:
        raise BindingError(
            f"{document} states"
            f" {', '.join(f'`{key}`' for key in sorted(ruled_out))}, which"
            " `D-IMPL-141` **ruled out** rather than never defined: "
            + "; ".join(
                f"`{key}` — {RULED_OUT_KEYS[key]}" for key in sorted(ruled_out)
            )
            + ". See `docs/superpowers/specs/2026-08-16-reference-plan-factory-"
            "and-debt-scorer.md` Amendment A"
        )

    known = frozenset(DATA_KEYS) | frozenset(REFERENCE_KEYS) | frozenset(OPTIONAL_KEYS)
    unknown = sorted(str(key) for key in parsed if str(key) not in known)
    if unknown:
        raise BindingError(
            f"{document} states {', '.join(f'`{key}`' for key in unknown)},"
            f" which {'are' if len(unknown) > 1 else 'is'} not"
            " a binding-document key — the keys are"
            f" {', '.join(f'`{key}`' for key in DATA_KEYS)} (data, required),"
            f" {', '.join(f'`{key}`' for key in REFERENCE_KEYS)} (the one"
            " permitted `module:attribute` reference) and"
            f" {', '.join(f'`{key}`' for key in OPTIONAL_KEYS)} (optional)."
            " An unknown key is refused rather than ignored: deployment wiring"
            " that silently selected a default would run configuration nobody"
            " authored"
        )

    for key, value in parsed.items():
        if str(key) in REFERENCE_KEYS:
            continue
        _refuse_references_in_data(value, position=str(key), document=document)

    required = (*DATA_KEYS, *REFERENCE_KEYS)
    missing = [
        key
        for key in required
        if key not in parsed or parsed[key] is None or str(parsed[key]).strip() == ""
    ]
    if missing:
        raise BindingError(
            f"{document} omits {', '.join(f'`{key}`' for key in missing)}."
            " `config` names this deployment's Control Plane document, `plan`"
            " names its projection, and the remaining keys are the data the"
            " SDK's resolver is built from"
        )

    config = _contained(
        str(parsed["config"]), root=root_path, key="config", document=document
    )
    if not config.is_file():
        raise BindingError(
            f"`config: {parsed['config']}` in {document} names {config}, which"
            " does not exist — the key names this deployment's Control Plane"
            " document, relative to the deployment root"
        )

    question = _mapping(parsed, key="question", document=document)
    perspective = _mapping(parsed, key="perspective", document=document)
    debt = _mapping(parsed, key="debt", document=document)
    # `asked_at` is OPTIONAL, and was required until 2026-08-16. It stopped
    # being read when `BL-02` made `as_of=None` resolve to the server's clock
    # rather than to this literal, and Dave ruled the same day: *"a required
    # field that no code path reads is a latent defect... keeping it required
    # solely because the schema was closed earlier is the wrong reason."*
    # Dropping the requirement is the narrow amendment to `D-IMPL-141`'s data
    # shape that records why — the field became unread, therefore it stopped
    # being mandatory. It may still be declared, and when declared it is held to
    # exactly the same standard as before, because a value stated wrongly is
    # worse than a value not stated.
    asked_at_raw = question.get("asked_at")
    asked_at: datetime | None = None
    if asked_at_raw is not None and str(asked_at_raw).strip():
        try:
            asked_at = datetime.fromisoformat(str(asked_at_raw))
        except ValueError as malformed:
            raise BindingError(
                f"`question.asked_at: {asked_at_raw}` in {document} is not an"
                " ISO 8601 instant"
            ) from malformed
        if asked_at.tzinfo is None:
            raise BindingError(
                f"`question.asked_at: {asked_at_raw}` in {document} states no"
                " time zone — a zone-less instant is a silent default"
                " (`D-IMPL-38`), and which zone it silently meant is the"
                " difference between two different answers"
            )

    operator_keys = parsed["operator_parameter_keys"]
    if isinstance(operator_keys, str) or not isinstance(operator_keys, Sequence):
        raise BindingError(
            f"`operator_parameter_keys:` in {document} parsed as"
            f" `{type(operator_keys).__name__}`, not a list of Control Plane keys"
        )

    # `server:` is the ONE key resolved against the deployment root's PARENT
    # (`D-10`, Dave, 2026-08-18), and it exists for the reason `connection`'s
    # rooted `{path: …}` form exists: a location the deployment genuinely
    # cannot spell as a literal, because the root is not known until a client
    # names it. The base is the parent rather than the root because a
    # deployment's server program is not deployment content — the ordinary case
    # is a remote server reached at an endpoint with this key absent entirely,
    # and a rule forcing the program inside the root would teach that a server
    # belongs in a deployment, which is false.
    #
    # Contained and returned, NOT existence-checked — the `artifact_store`
    # precedent rather than the `config` one. Whether the program must be on
    # disk is transport-specific: `mcp_stdio` asks, because it launches it; an
    # in-process deployment never does.
    server: Path | None = None
    declared_server = parsed.get("server")
    if declared_server is not None and str(declared_server).strip():
        server = _contained(
            str(declared_server),
            root=root_path.parent,
            key="server",
            document=document,
            base_description="the directory holding this deployment",
        )
        # `D-18` (Dave, 2026-08-18). Containment has just passed and the value
        # is still wrong: a base one level out also admits a path reaching back
        # INSIDE the root, which would quietly give that directory a second
        # Python module where Amendment A.3 grants one. Refused in the
        # `RULED_OUT_KEYS` register — an author writing this has not made a
        # typo, and a message about an unrecognised path would invite a
        # re-spelling of the thing that was declined. The key itself is NOT in
        # `RULED_OUT_KEYS`: that mapping refuses a key unconditionally by name,
        # and `server:` is legitimate. What is refused here is a value.
        if server == root_path or root_path in server.parents:
            raise BindingError(
                f"`server: {declared_server}` in {document} resolves to"
                f" {server}, which is inside the deployment root {root_path} —"
                " `D-IMPL-141` Amendment A.3 grants that directory **one**"
                " Python module, its projection, and a server program is not"
                " deployment content. Name it beside the deployment rather than"
                " inside it — `server` resolves against the directory holding"
                " the deployment for exactly that reason. See"
                " `docs/superpowers/specs/2026-08-16-reference-plan-factory-"
                "and-debt-scorer.md` Amendment A"
            )

    return BindingDocument(
        root=root_path,
        config=config,
        plan=str(parsed["plan"]),
        question=QuestionDeclaration(
            subject=_field(
                question, key="question", field="subject", document=document
            ),
            intent=_field(question, key="question", field="intent", document=document),
            freshness=_field(
                question, key="question", field="freshness", document=document
            ),
            asked_at=asked_at,
        ),
        perspective=Perspective(
            principal_id=_field(
                perspective, key="perspective", field="principal_id", document=document
            ),
            role=_field(perspective, key="perspective", field="role", document=document),
        ),
        product_class_key=str(parsed["product_class_key"]),
        request_contract_key=str(parsed["request_contract_key"]),
        operator_parameter_keys=tuple(str(key) for key in operator_keys),
        policy_bundle_key=str(parsed["policy_bundle_key"]),
        replay_record_class=str(parsed["replay_record_class"]),
        query_pin_class=str(parsed["query_pin_class"]),
        max_ttl_seconds=_integer(parsed, key="max_ttl_seconds", document=document),
        product_ttl_seconds=_integer(
            parsed, key="product_ttl_seconds", document=document
        ),
        artifact_store=_contained(
            str(parsed["artifact_store"]),
            root=root_path,
            key="artifact_store",
            document=document,
        ),
        debt=DebtDeclaration(
            half_life_key=_field(
                debt, key="debt", field="half_life_key", document=document
            ),
            debt_profile_key=_field(
                debt, key="debt", field="debt_profile_key", document=document
            ),
            completeness=_decimal(
                debt, key="debt", field="completeness", document=document
            ),
            semantic_consistency=_decimal(
                debt, key="debt", field="semantic_consistency", document=document
            ),
        ),
        connection=_connection(parsed, root=root_path, document=document),
        server=server,
    )


def load_reference(reference: str, *, root: Path, key: str) -> Any:
    """Resolve a ``<module-path>:<attribute>`` reference against ``root``.

    Reached for :data:`REFERENCE_KEYS` and nothing else. It is a public function
    rather than a private one because the gate that proves the exception stays
    narrow needs to resolve the same reference the loader does, and a gate
    re-implementing its subject is not a gate.

    The module is loaded under a name derived from the **resolved root**, so
    two deployment roots carrying a ``projection.py`` each are two modules rather
    than one shadowing the other. A bare module name would be a real collision:
    the conformance suite boots more than one deployment in a process, and
    ``sys.modules`` is process-wide.

    ``root`` goes on :data:`sys.path` for the duration of the load, so a
    deployment's module can import its own siblings. It is removed afterwards.
    The residual is stated rather than hidden: two deployments whose modules
    import a *same-named sibling* would still share that sibling's entry in
    ``sys.modules``. That is the ordinary hazard of any path-based plugin
    surface and is inside the deployment's own trust boundary (``T-17-19``).

    Args:
        reference: The reference as authored, ``<module-path>:<attribute>``.
        root: The deployment root, already resolved.
        key: The binding-document key this reference came from, for refusals.

    Returns:
        The attribute the reference names. Callers check what it *is*; this
        function's job ends at producing it.

    Raises:
        ccf.client.errors.BindingError: the reference is not
            ``module:attribute`` shaped, the module does not resolve or does not
            import, or the module holds no such attribute. Each names the key
            and the reference.
    """
    document = root / BINDING_DOCUMENT_NAME
    module_path, separator, attribute = reference.partition(":")
    if not separator or not module_path.strip() or not attribute.strip():
        raise BindingError(
            f"`{key}: {reference}` in {document} is not a"
            " `<module-path>:<attribute>` reference — a module path, a colon"
            " and the name of the attribute to use, as in"
            " `projection.py:build_projection`"
        )

    module_file = _contained(
        module_path.strip(), root=root, key=key, document=document
    )
    if not module_file.is_file():
        raise BindingError(
            f"`{key}: {reference}` in {document} names {module_file}, which does"
            " not exist — the module path is relative to the deployment root"
        )

    digest = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:16]
    module_name = f"_ccf_binding_{digest}_{module_file.stem}"
    spec = importlib.util.spec_from_file_location(module_name, module_file)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise BindingError(
            f"`{key}: {reference}` in {document} names {module_file}, which"
            " Python declined to load as a module"
        )

    module = importlib.util.module_from_spec(spec)
    on_path = str(root)
    added = on_path not in sys.path
    if added:
        sys.path.insert(0, on_path)
    try:
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    except Exception as failed:
        sys.modules.pop(module_name, None)
        raise BindingError(
            f"`{key}: {reference}` in {document} names {module_file}, which"
            f" raised while importing: {failed}"
        ) from failed
    finally:
        if added:
            sys.path.remove(on_path)

    try:
        return getattr(module, attribute.strip())
    except AttributeError as absent:
        raise BindingError(
            f"`{key}: {reference}` in {document} names attribute"
            f" `{attribute.strip()}`, which {module_file} does not define"
        ) from absent


def conforming_plan_factory(
    candidate: Any, *, reference: str, root: Path
) -> ProjectionPlanFactoryProtocol:
    """Refuse a ``plan:`` reference that is not a projection plan factory.

    :class:`~ccf.products.resolver.ProjectionPlanFactoryProtocol` is
    ``@runtime_checkable``, so this is a real structural check rather than a
    comment — which is the whole reason the Protocol carries that decorator.

    The check is worth its own function because ``plan:`` is the **single**
    permitted reference (Amendment A.3): the one thing a deployment may hand the
    SDK as code is also the one thing worth verifying is the code it claimed.

    Raises:
        ccf.client.errors.BindingError: the reference named something that is
            not callable as a plan factory.
    """
    if not isinstance(candidate, ProjectionPlanFactoryProtocol):
        raise BindingError(
            f"`plan: {reference}` in {root / BINDING_DOCUMENT_NAME} names"
            f" `{type(candidate).__name__}`, which does not satisfy"
            " `ProjectionPlanFactoryProtocol` — `plan:` names the projection"
            " itself or a factory returning one, not a module, a class"
            " attribute or a configuration object"
        )
    return candidate
