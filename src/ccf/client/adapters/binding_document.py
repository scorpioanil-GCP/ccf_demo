"""``binding.yaml`` — how a deployment root tells an in-process client its wiring.

**SDK-defined and PROPOSED, not ruled.** ``D-IMPL-141`` in ``docs/DECISIONS.md``
states the question, this resolution and the two rejected alternatives, and
carries the status *proposed, awaiting Dave's ruling at the phase gate*. This
module is deliberately the **only** place the proposed surface is interpreted,
so a different ruling rewrites one file rather than the adapter beside it.

The question this answers
-------------------------
An in-process binding address names a **deployment root**, and the adapter has
to reach that deployment's resolver from it. It cannot come from
``ccf_config.yaml``: that document is a closed-world typed contract with seven
reserved sections plus ``operators`` (:mod:`ccf.deployment.config`), none of
which can name Python, and widening it would reopen ``D-IMPL-136``. So the
deployment contributes Python and states where it is — in the same posture
``backends.yaml`` already has, where the deployment declares its own wiring
rather than the SDK guessing at a filename.

What the document carries
--------------------------
Four keys, three of them required::

    config:     ccf_config.yaml            # required
    resolver:   resolver.py:build_resolver # required
    question:   resolver.py:build_question # required
    connection: resolver.py:connection     # optional

``config:`` is a path relative to the root. The other three are
``<module-path>:<attribute>`` references, also relative to the root, whose
attribute is a **factory** the adapter calls.

This is deployment-environment material and **never a Control Plane artifact**:
it is not registered, not content-hashed, carries no ``semver``, and never
reaches Decision Replay dimension 2. A connection reference is exactly why —
``docs/superpowers/specs/2026-08-15-ccf-client-design.md`` §9 keeps connection
material out of content-hashed state, and a document that named a store would
put deployment environment inside the audit plane.

Why every reference is a reference and never a document
--------------------------------------------------------
``connection:`` names deployment **code**, not a connection-composition
document, and the difference was measured rather than preferred. No module in
``src/`` or ``runtime/`` reads ``backends.yaml``; it is an example-authored
format with no SDK contract, whose ``profiles``/``settings``/``from_env``/
``per_run``/``prefix`` vocabulary each example writes for itself. An SDK module
interpreting it would commit the fabric to a document format it never specified
and would put a deployment's own vocabulary inside library code (CLAUDE.md §11,
CINV-01). Naming a factory instead keeps the composition where it already lives
— ``examples/s1-00-companies-over-revenue/deployment.py::connection`` is that
function today — and leaves this module interpreting **one** thing, a
``module:attribute`` reference, rather than two.

Why a document rather than a fixed filename or an entry point
---------------------------------------------------------------
A fixed filename convention would make the SDK guess, and would give the gates
nothing to assert against. A packaging entry point is unreachable: an example
directory is not an installed distribution, so entry points would need a
``pip install -e`` per deployment. ``D-IMPL-141`` records both with their costs.

Trust posture, stated rather than implied
-------------------------------------------
Loading a reference **executes the deployment's Python**. That is threat
``T-17-19`` and it is *accepted*: the deployment root is the deployment's own
trust boundary, exactly as ``ccf_config.yaml`` and ``backends.yaml`` already
are, and the process is already running that deployment's code. What is
enforced rather than trusted is **containment**: every path this module
resolves stays inside the root, refusing an absolute path or a ``..`` segment
in the posture :class:`~ccf.controlplane.artifacts.ManifestEntry` already holds
a manifest to. A binding document is trusted no further than a manifest is.

This module is algorithmic (CINV-03): document parsing, path resolution and a
module import. No clock, no LLM dependency ever.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import yaml

from ccf.client.errors import BindingError
from ccf.products.request import ProductRequest
from ccf.products.resolver import ServedProductResolverProtocol
from ccf.projection.plan import Perspective

__ccf_mode__ = "algorithmic"

__all__ = [
    "BINDING_DOCUMENT_NAME",
    "OPTIONAL_KEYS",
    "REQUIRED_KEYS",
    "BindingDocument",
    "QuestionFactoryProtocol",
    "ResolverCall",
    "conforming_resolver",
    "load_binding_document",
    "load_reference",
]


#: The filename a deployment root carries. One name, referenced everywhere the
#: loader reports a refusal, so a rename is a single edit rather than a search.
BINDING_DOCUMENT_NAME = "binding.yaml"

#: Keys a binding document must state. Absence of any one is refused by name —
#: a deployment that meant to supply it and mistyped it should be told which.
REQUIRED_KEYS: tuple[str, ...] = ("config", "resolver", "question")

#: Keys a binding document may state. A deployment whose backend needs no
#: connection settings omits ``connection`` entirely; omission is a positive
#: statement, not a missing value.
OPTIONAL_KEYS: tuple[str, ...] = ("connection",)


@dataclass(frozen=True, kw_only=True)
class ResolverCall:
    """The two things the SDK cannot know about a question, supplied by the deployment.

    A resolver's five arguments are *not* five unknowns. Three the SDK holds
    already: ``tenant`` comes off the booted fabric, and ``product_class`` and
    ``version`` are read off :attr:`ProductRequest.schema_name` and
    :attr:`ProductRequest.schema_version` — the request states its own address,
    so asking a deployment to state it twice would be two enumerations that can
    disagree.

    The two below are the genuine remainder, and they are here rather than in
    ``src/`` because the SDK has no way to invent either:

    * a :class:`~ccf.products.request.ProductRequest` needs ``subject``,
      ``intent`` and ``freshness``, which are **domain vocabulary** — ``s1-00``
      reads its three out of its own ``scenario/question.yaml`` — and it needs
      ``asked_at``, which is the deployment's answer to ``D-04``'s *"``as_of=None``
      means the server's decision instant"*: whose clock, and what default,
      belongs to the producer;
    * a :class:`~ccf.projection.plan.Perspective` is the Π role-conditioning a
      calling surface resolves and a deployment's entitlement policy authorizes.
      The client surface exposes no principal in v0 (``D-IMPL-129``, the v0
      not-list), so the deployment names it.

    Attributes:
        perspective: The Π role-conditioning this question is answered under.
        request: The typed question, carrying its own class address, the
            caller's parameters, and the instant it is asked as of.
    """

    perspective: Perspective
    request: ProductRequest


@runtime_checkable
class QuestionFactoryProtocol(Protocol):
    """How a deployment turns a client's question into a resolver's arguments.

    The shape ``examples/s1-00-companies-over-revenue/deployment.py::request``
    already has, widened by the perspective. A Protocol rather than a base class
    (CLAUDE.md §11): a deployment conforms by being callable this way.

    ``@runtime_checkable`` verifies the presence of ``__call__`` only, which
    every function has — so this module checks the factory's **return value**
    against :class:`ResolverCall` as well, which is a real check rather than a
    tautology.
    """

    def __call__(
        self,
        *,
        product_id: str,
        parameters: Mapping[str, Any],
        temporal_boundary: Any,
    ) -> ResolverCall:
        """Build the resolver's remaining arguments for one client question.

        Args:
            product_id: The product class the client asked for, verbatim.
            parameters: The caller's parameters, verbatim. The deployment
                supplies no value for these and no default.
            temporal_boundary: The instant the caller named, or ``None`` for
                ``D-04``'s *use the server's decision instant*. Resolving
                ``None`` is the deployment's decision, not the SDK's.
        """
        ...


@dataclass(frozen=True, kw_only=True)
class BindingDocument:
    """One deployment root's wiring, parsed and resolved.

    Every path here is **already resolved and already contained**: the loader
    refuses anything landing outside the root, so a consumer of this type never
    re-checks and never has a second, weaker copy of the rule.

    Attributes:
        root: The deployment root, resolved absolute. This is the value the
            in-process adapter keys its boot cache on — see
            :mod:`ccf.client.adapters.inprocess` for why resolving it here
            rather than there is what makes ``./deployment`` and its absolute
            spelling one cache entry.
        config: The deployment's ``ccf_config.yaml``, resolved absolute.
        resolver: The ``<module>:<attribute>`` reference to the resolver
            factory, verbatim as authored, for refusal messages.
        question: The ``<module>:<attribute>`` reference to the question
            factory, verbatim as authored.
        connection: The ``<module>:<attribute>`` reference to the connection
            factory, or ``None`` when the document stated none.
    """

    root: Path
    config: Path
    resolver: str
    question: str
    connection: str | None


def _contained(
    candidate: str, *, root: Path, key: str, document: Path
) -> Path:
    """Resolve ``candidate`` inside ``root``, or refuse it by name.

    The containment rule :class:`~ccf.controlplane.artifacts.ManifestEntry`
    already applies to a manifest, applied here for the same reason: a binding
    document is deployment-authored and is trusted no further, so it does not
    get to name a path outside the deployment it describes. Both checks are
    needed and neither covers the other — the string check refuses an absolute
    path or a ``..`` segment as written, and the resolved check closes a plain
    name that is a symlink out.
    """
    written = Path(candidate)
    if written.is_absolute() or ".." in written.parts:
        raise BindingError(
            f"`{key}: {candidate}` in {document} names a path outside the"
            " deployment root — a binding document describes the deployment it"
            " sits in, so its paths are relative to that root and carry no `..`"
            " segment and no leading `/`"
        )
    resolved = (root / written).resolve()
    if resolved != root and root not in resolved.parents:
        raise BindingError(
            f"`{key}: {candidate}` in {document} resolves to {resolved}, which"
            f" is outside the deployment root {root} — a plain name that is a"
            " symlink out of the deployment is refused for the same reason a"
            " `..` segment is"
        )
    return resolved


def load_binding_document(root: str | Path) -> BindingDocument:
    """Read and validate the binding document at ``root``.

    Strict in the :class:`~ccf.controlplane.artifacts.DeploymentConfig`
    posture: an unknown top-level key is refused **by name** rather than
    ignored. A typo in deployment wiring that silently selected a default is a
    deployment running configuration nobody authored, and it would surface as a
    wrong answer rather than as a failed boot.

    Args:
        root: The deployment root the binding address named.

    Returns:
        The parsed document, with every path resolved and contained.

    Raises:
        ccf.client.errors.BindingError: the root does not exist, carries no
            binding document, states a key that is not a key, omits a required
            one, or names a path outside itself. Each message names the file and
            the key at fault, because a refusal that does not say what to fix
            costs the reader the diagnosis the loader already did.
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
            " nothing naming this deployment's config or its resolver. Add"
            f" `{BINDING_DOCUMENT_NAME}` stating"
            f" {', '.join(f'`{key}:`' for key in REQUIRED_KEYS)}"
        )

    parsed = yaml.safe_load(document.read_text(encoding="utf-8"))
    if not isinstance(parsed, Mapping):
        raise BindingError(
            f"{document} is not a mapping of keys to values — a binding"
            f" document states {', '.join(f'`{key}:`' for key in REQUIRED_KEYS)}"
            " at its top level, and this one parsed as"
            f" `{type(parsed).__name__}`"
        )

    known = frozenset(REQUIRED_KEYS) | frozenset(OPTIONAL_KEYS)
    unknown = sorted(str(key) for key in parsed if str(key) not in known)
    if unknown:
        raise BindingError(
            f"{document} states {', '.join(f'`{key}`' for key in unknown)},"
            f" which {'are' if len(unknown) > 1 else 'is'} not"
            " a binding-document key — the keys are"
            f" {', '.join(f'`{key}`' for key in REQUIRED_KEYS)} (required) and"
            f" {', '.join(f'`{key}`' for key in OPTIONAL_KEYS)} (optional)."
            " An unknown key is refused rather than ignored: deployment wiring"
            " that silently selected a default would run configuration nobody"
            " authored"
        )

    missing = [key for key in REQUIRED_KEYS if not str(parsed.get(key, "")).strip()]
    if missing:
        raise BindingError(
            f"{document} omits {', '.join(f'`{key}`' for key in missing)}."
            f" `config` names this deployment's Control Plane document, and"
            " `resolver` and `question` are `<module>:<attribute>` references"
            " to the factories that answer a question here"
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

    connection = parsed.get("connection")
    return BindingDocument(
        root=root_path,
        config=config,
        resolver=str(parsed["resolver"]),
        question=str(parsed["question"]),
        connection=str(connection) if connection is not None else None,
    )


def load_reference(reference: str, *, root: Path, key: str) -> Any:
    """Resolve a ``<module-path>:<attribute>`` reference against ``root``.

    The module is loaded under a name derived from the **resolved root**, so
    two deployment roots carrying a ``resolver.py`` each are two modules rather
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
            " and the name of the factory to call, as in"
            " `resolver.py:build_resolver`"
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


def conforming_resolver(
    candidate: Any, *, reference: str, root: Path
) -> ServedProductResolverProtocol:
    """Refuse a resolver factory whose product is not a resolver.

    :class:`~ccf.products.resolver.ServedProductResolverProtocol` is
    ``@runtime_checkable``, so this is a real structural check rather than a
    comment — which is the whole reason the Protocol carries that decorator.

    Raises:
        ccf.client.errors.BindingError: the factory returned something that is
            not callable as a resolver.
    """
    if not isinstance(candidate, ServedProductResolverProtocol):
        raise BindingError(
            f"`resolver: {reference}` in {root / BINDING_DOCUMENT_NAME} names a"
            " factory that returned"
            f" `{type(candidate).__name__}`, which does not satisfy"
            " `ServedProductResolverProtocol` — the factory returns the"
            " resolver itself, not a module, a class or a configuration object"
        )
    return candidate
