"""The backend registration seam — the one place an adapter is resolved.

SDK-defined mechanism (CLAUDE.md §11 "mechanism, not values" and §6.4 "code
contains interpreters and factories, never the things interpreted"). D-IMPL-93.
The whitepaper specifies the ``GraphStore`` seam (§7.3) and the single-writer
invariant; it does not specify how a deployment *selects* the adapter behind
that seam. This module is that selection, and it is SDK-defined.

Before this seam the dependency arrow ran the wrong way: the composition root
and the write module each named every adapter, so adding a substrate cost an
edit in core and a substrate name in core was unavoidable. After it, an adapter
declares itself and core resolves the one a deployment named. **No substrate
name appears in this file, including in prose.** The vocabulary comes off disk;
every refusal message is built from what discovery found.

Two discovery sources, one record, one resolution path
------------------------------------------------------

**Built-in adapters are found by reading module names out of the adapter
package's directory** — a disk read, not an import, and no packaging metadata
is involved. That is deliberate twice over. A stale editable install or a
shadowing ``*.egg-info`` cannot make the SDK unbootable, and a built-in cannot
be shadowed by an installed distribution because it never travels the
entry-point path at all. Entry-point names are *not* deduplicated across
distributions and the stdlib's mapping form returns the first match silently,
so a built-in that travelled that path could be answered for by somebody else's
package.

**Third-party adapters are found through the** :data:`BACKEND_ENTRY_POINT_GROUP`
**entry-point group**, which is what lets an adapter ship as a separate
installable distribution with no line changing in this repository. That is
D-04's "both, not either".

Neither source imports anything (D-05). Only :func:`resolve` imports, and it
imports exactly one adapter.

What this module deliberately does not do
-----------------------------------------

Stated here so a later reader does not reach for either as a de-risking step.

* **It does not import every declared adapter at start-up.** D-06 considered
  and rejected: that runs arbitrary installed packages' module-level code at
  every boot, and it would undo the optional-extra deferral that keeps a
  driver's package unloaded when a deployment booted something else.
* **It does not infer an adapter from the shape of a connection value.**
  Selection is a name in a manifest. That is the rule :func:`ccf.boot.boot`'s
  required ``backend`` argument states — a fabric that guessed its own
  substrate could boot against a development store in production and still
  pass every test — and this module inherits it rather than re-deciding it.

Fail-closed on bad metadata, ruled rather than fallen into
----------------------------------------------------------

:func:`resolve` calls :func:`declared_names` first, so a duplicated, reserved
or malformed name declared by *any* installed distribution refuses *every*
boot — including a boot of a built-in that has nothing to do with it. This is a
real choice: D-05 requires only that unselected code is not imported; it does
not by itself require bad metadata to fail every boot.

The ruling is fail-closed, because each of the three refusals is evidence that
the environment's answer to "which code does this name select" is ambiguous or
wrong, and a fabric that boots past an ambiguity it cannot resolve has already
decided something nobody asked it to decide. The narrower alternative —
degrade only :func:`declared_names`'s listing and the resolution of the
offending name, leaving unrelated boots working — was considered and rejected
for now. It can be adopted later as a decision with its own entry; a fabric
that quietly booted past a packaging conflict cannot be un-booted.

One requirement follows and it is what keeps fail-closed operable: the refusal
must read as a *packaging conflict*. It names the offending distributions and
says the requested adapter was never reached, so an operator can tell "this
deployment's installed adapters conflict" from "the adapter I asked for is not
installed".

The residual this module carries, and the compensating control
--------------------------------------------------------------

Stated in the voice ``src/ccf/boot.py`` uses for the determined-insider claim,
because a check that does not say what it is blind to is how a defect class
survives review.

An AST import lint reads ``import`` statements. :func:`resolve` reaches the
adapter a deployment named with :func:`importlib.import_module`, and no import
lint can see a dynamically-constructed module name. The claim strength here is
therefore *no unforced path exists*, never *no path exists*.

The compensating control is confinement rather than detection: that call
appears exactly once, in one private function in this module, and nowhere else
under ``src/`` or ``runtime/`` — the same two trees ``cinv02-backend-import``
is scoped to. ``tests/graph/test_backend_registry.py`` parses both trees and
asserts it. The scan matches the rule's scope on purpose: narrowed to this
package it would miss a dynamic adapter import in the deployment wiring, which
holds the adapter name and is exactly where someone would reach for one. A
compensating control narrower than the threat is not a control.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import importlib
import importlib.metadata
import pkgutil
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from pydantic import SecretStr, ValidationError

from ccf.contracts.base import CCFContract
from ccf.graph.protocols import GraphReader

if TYPE_CHECKING:
    # The registry *types* the write seam and stops there: it names these two
    # so :attr:`BackendRegistration.make_writer` can be typed under
    # ``mypy --strict``, and it mints no token and calls no factory. The
    # ``cinv02-graph-writer`` carve-out (plan 15.4-01) permits this module to
    # name the neutral base — and only the neutral base, never a per-backend
    # write module. Guarded by ``TYPE_CHECKING`` so importing the registry
    # costs nothing at runtime, which is what keeps the D-06 rejection above
    # honest: a registry that dragged the whole write path in on import would
    # have imported adapters at start-up by another door.
    from ccf.graph._writer import BaseGraphWriter, BootToken

__ccf_mode__ = "algorithmic"

__all__ = [
    "AdapterPin",
    "BackendRegistration",
    "BackendStore",
    "DuplicateBackendName",
    "InvalidBackendConfig",
    "ReservedBackendName",
    "ResolvedBackend",
    "ResolvedSecret",
    "UnknownBackend",
    "declared_names",
    "resolve",
    "validate_connection",
]

#: The entry-point group a third-party distribution declares an adapter under.
#: The PyPA convention is a group name starting with the consuming
#: distribution's own name followed by a dot. This distribution is unpublished,
#: so the namespace is *conventional* rather than owned — worth knowing before
#: anyone treats the prefix as a guarantee.
BACKEND_ENTRY_POINT_GROUP = "ccf.graph_backends"

#: Suffix marking a module inside the adapter package as that adapter's write
#: module. Kept in step with ``tools.lints.harness_imports.WRITE_MODULE_SUFFIX``
#: by D-01, which gives the rule and the registry one convention to read.
WRITE_MODULE_SUFFIX = "_write"

#: The module-level attribute an adapter's write module carries.
REGISTRATION_ATTRIBUTE = "REGISTRATION"

#: Shape every adapter name must match: exact, lower case, no dots (D-16).
#: A versioned document should not need a convention to say which case won, and
#: a name with a dot in it would be indistinguishable from a dotted entry-point
#: name that means something else.
ADAPTER_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

#: The adapter package, as a dotted name for building a write module's path and
#: as a directory name for reading the package off disk. The directory read is
#: what makes built-in discovery independent of packaging metadata — and the
#: reason this module does not *import* the package: ``cinv02-backend-import``
#: denies the adapter package to every module outside it, and the registry is
#: meant to be the module that rule can be proven against, not the module that
#: needs an exemption from it.
BACKENDS_PACKAGE = "ccf.graph.backends"
BACKENDS_DIR_NAME = "backends"

#: This distribution's name, used to derive a built-in adapter's pin.
SDK_DISTRIBUTION = "ccf"

#: Positive "the environment could not tell us" markers. A source checkout that
#: was never installed has no distribution metadata, and a pin that silently
#: said nothing would be worse than one that says it does not know.
UNKNOWN_VERSION = "unknown"
UNKNOWN_DISTRIBUTION = "unknown-distribution"


class UnknownBackend(ValueError):
    """No installed adapter registers the requested name.

    A ``ValueError`` subclass because that is what a caller refusing a bad
    manifest already catches; the precise type is available to a caller that
    wants to tell this apart from a malformed connection mapping.
    """


class DuplicateBackendName(ValueError):
    """Two installed distributions declare one adapter name.

    The fabric does not choose between them. Refused during discovery, so
    neither candidate is ever loaded.
    """


class ReservedBackendName(ValueError):
    """An installed distribution declares a name the SDK's own adapters hold.

    D-16, on the precedent that reserves the SDK's artifact-class prefix
    against manifest squatting: a name the SDK ships cannot be claimed from
    outside, because the alternative is a deployment whose adapter set depends
    on discovery order.
    """


class InvalidBackendConfig(ValueError):
    """A connection mapping does not satisfy its adapter's config model.

    Subclasses ``ValueError`` so every caller that already refuses a bad
    manifest with ``ValueError`` keeps working, while a caller that wants to
    tell a malformed connection mapping apart from an unresolvable adapter name
    can have the precise type.
    """


class BackendStore(Protocol):
    """What booting needs of a graph backend, whichever substrate it is.

    Relocated from the composition root's own private Protocol and made public
    because a third-party adapter has to implement it. Protocol rather than a
    base class, per CLAUDE.md §11 (Protocols over inheritance): an adapter
    conforms structurally and inherits nothing, so nothing in this package can
    become a place adapter behaviour accumulates.

    SDK extension (CLAUDE.md §7.3-adjacent seam discipline); the whitepaper
    specifies the store's *semantics* (§7.3, D-IMPL-34), not its lifecycle.
    """

    @property
    def graph_identity(self) -> str: ...

    @property
    def reader(self) -> GraphReader: ...

    def close(self) -> None: ...


@dataclass(frozen=True)
class BackendRegistration:
    """What one adapter declares about itself.

    A record the registry *interprets*, never a base class an adapter
    subclasses (CLAUDE.md §6.4, §11). An adapter is data to this module: it
    supplies a name, the typed shape of its connection settings, which of those
    settings carry a credential, and two constructors. Nothing here can carry
    behaviour the registry would then have to know about.

    Attributes:
        name: The name a manifest uses to select this adapter. Must match
            :data:`ADAPTER_NAME_PATTERN`, and must equal the name it was
            resolved under — :func:`resolve` refuses a record that disagrees.
        config_model: The typed connection contract, deriving from
            :class:`~ccf.contracts.base.CCFContract` so that ``extra="forbid"``
            is inherited rather than re-declared. That inheritance is the whole
            of one refusal: a settings key the adapter does not declare is
            rejected by the contract base, and a model written against a plain
            open base would lose that refusal with no test failing.
        secret_fields: Config keys whose value is a credential — supplied at
            boot rather than declared in a versioned document. Empty for an
            adapter with no credential.
        open_store: Constructs the store from validated settings plus resolved
            credentials keyed by config field. The credential mapping is
            separate from the validated model on purpose: a resolved value must
            never sit inside something that could be echoed by a validation
            error or content-hashed into an artifact.
        make_writer: Constructs the write handle from the store and the boot
            token. The registry never calls this — the composition root does,
            and a test asserts it is the only caller under ``src/`` and
            ``runtime/``.
    """

    name: str
    config_model: type[CCFContract]
    secret_fields: frozenset[str]
    open_store: Callable[[CCFContract, Mapping[str, SecretStr]], BackendStore]
    make_writer: Callable[[BackendStore, BootToken], BaseGraphWriter]


@dataclass(frozen=True)
class ResolvedBackend:
    """One adapter, resolved: its record plus where it came from.

    ``version`` and ``distribution`` are *derived by the registry*, never
    declared by the adapter, which is why a third-party adapter gets its replay
    pin for free and cannot mis-state it. For an adapter found through the
    entry-point group they come from the declaring distribution's own metadata;
    for a built-in they come from this distribution's metadata, with a
    documented fallback when that metadata is absent — a source checkout that
    was never installed.
    """

    registration: BackendRegistration
    version: str
    distribution: str


class AdapterPin(CCFContract):
    """What a booted fabric can hand to Decision Replay about its adapter.

    Whitepaper §7.10.1 dimension 2 (Policy Bindings Snapshot) — which adapter,
    which version, and which credential *references* were in force. A later
    plan threads this into the replay record; this class is the shape it
    travels in.

    It has no field that can hold a resolved credential. ``secret_refs``
    carries reference **names** only, which is the fact that makes the
    credential path auditable without ever recording a credential.
    """

    name: str
    version: str
    secret_refs: tuple[str, ...]


class ResolvedSecret(CCFContract):
    """One credential, with the name of the reference it came from.

    It exists because :class:`AdapterPin` needs reference *names* while a
    store constructor needs *values*, and two parallel mappings can disagree.
    A mapping keyed by config field can only say that some field was supplied
    — never which reference supplied it, which is exactly the fact D-08 makes
    auditable. One object carries both, so a pin cannot record a reference the
    value did not come from and no caller has to keep two mappings in step.

    Two properties of the value field are load-bearing:

    * ``SecretStr`` renders as a fixed mask in ``repr``, ``str`` and
      ``model_dump_json``, so the value does not reach a log through the
      ordinary routes.
    * :func:`~ccf.contracts.canonical.canonical_bytes` **refuses**
      ``SecretStr`` outright, so a :class:`ResolvedSecret` cannot be
      content-hashed into an artifact even by accident. That turns the
      no-persistence guarantee into a mechanism rather than a promise.

    The composition root unwraps these at the last moment: an adapter's
    ``open_store`` still receives a mapping of config field to ``SecretStr``,
    so :class:`BackendRegistration` and every adapter constructor are untouched
    by this shape. The reference name travels only as far as the pin.

    Attributes:
        field: The config field this credential satisfies.
        ref_name: The name of the reference it was resolved from.
        value: The resolved credential.
    """

    field: str
    ref_name: str
    value: SecretStr


def _backends_directory() -> Path:
    """The adapter package's directory on disk, beside this module.

    A path, never an import. Reading the directory is what makes built-in
    discovery independent of packaging metadata, and it is what lets this
    module stay outside the set of modules that may name the adapter package
    in an ``import`` statement.
    """
    return Path(__file__).resolve().parent / BACKENDS_DIR_NAME


def _builtin_names() -> dict[str, str]:
    """Adapter name -> dotted write-module path, for adapters shipped here.

    Imports nothing: :func:`pkgutil.iter_modules` is given a filesystem path
    and reports module names. A module is an adapter's write module when its
    name ends with :data:`WRITE_MODULE_SUFFIX`; the suffix is stripped to give
    the adapter name.
    """
    found: dict[str, str] = {}
    for info in pkgutil.iter_modules([str(_backends_directory())]):
        if info.ispkg or not info.name.endswith(WRITE_MODULE_SUFFIX):
            continue
        adapter = info.name[: -len(WRITE_MODULE_SUFFIX)]
        if not adapter:
            continue
        found[adapter] = f"{BACKENDS_PACKAGE}.{info.name}"
    return found


def _declared_entry_points() -> importlib.metadata.EntryPoints:
    """Every declaration in the adapter group. Metadata only, never a load.

    Reads ``.name``, ``.value``, ``.dist.name`` and ``.dist.version`` and calls
    ``.load()`` never — that call is the only thing in the stdlib's entry-point
    API that imports, and it happens in :func:`resolve` alone (D-05).
    """
    return importlib.metadata.entry_points(group=BACKEND_ENTRY_POINT_GROUP)


def _distribution_of(entry_point: importlib.metadata.EntryPoint) -> str:
    distribution = entry_point.dist
    if distribution is None:
        return UNKNOWN_DISTRIBUTION
    return distribution.name


def _version_of(entry_point: importlib.metadata.EntryPoint) -> str:
    distribution = entry_point.dist
    if distribution is None:
        return UNKNOWN_VERSION
    return distribution.version


def _sdk_version() -> str:
    """This distribution's version, or a positive "unknown" marker.

    Absent distribution metadata is a source checkout that was never installed
    — a normal development state, not a failure. A pin that said nothing would
    be worse than one that says it could not tell.
    """
    try:
        return importlib.metadata.version(SDK_DISTRIBUTION)
    except importlib.metadata.PackageNotFoundError:
        return UNKNOWN_VERSION


def _check_name_shape(name: str, origin: str) -> None:
    """Refuse a declared adapter name that is not of the required shape."""
    if ADAPTER_NAME_PATTERN.match(name):
        return
    raise ValueError(
        f"adapter name {name!r} declared by {origin} is not a valid adapter"
        f" name; a name matches {ADAPTER_NAME_PATTERN.pattern} — lower case,"
        " starting with a letter, no dots. Adapter names are compared exactly,"
        " because a versioned document should not need a convention to say"
        " which case won."
    )


def _declared() -> tuple[dict[str, str], dict[str, importlib.metadata.EntryPoint]]:
    """The two discovery sources, with every name refusal already applied.

    Returns built-in adapters (name -> dotted write module) and third-party
    adapters (name -> the entry point that declares it). Nothing is imported
    and nothing is loaded here.

    The refusals are computed at this level rather than in :func:`resolve` so
    that no caller can reach a name the fabric would not honour, and so that
    :func:`declared_names` and :func:`resolve` cannot disagree about what is
    available.
    """
    builtins = _builtin_names()
    for name in sorted(builtins):
        _check_name_shape(name, "the SDK's own adapter package")

    third_party: dict[str, importlib.metadata.EntryPoint] = {}
    for entry_point in _declared_entry_points():
        origin = (
            f"distribution {_distribution_of(entry_point)}"
            f" {_version_of(entry_point)}"
        )
        _check_name_shape(entry_point.name, origin)

        if entry_point.name in builtins:
            raise ReservedBackendName(
                f"{origin} declares adapter name {entry_point.name!r} under"
                f" {BACKEND_ENTRY_POINT_GROUP!r}, but that name belongs to an"
                " adapter this SDK ships and is reserved. This is a packaging"
                " conflict in the installed environment, not a missing"
                " adapter: no adapter was resolved and no adapter was loaded."
                " Rename the third-party adapter, or run"
                f" `pip uninstall {_distribution_of(entry_point)}`."
            )

        previous = third_party.get(entry_point.name)
        if previous is None:
            third_party[entry_point.name] = entry_point
            continue
        if _distribution_of(previous) == _distribution_of(entry_point):
            # One distribution declaring one name twice is a malformed table,
            # not an ambiguity: both declarations name the same code, so there
            # is nothing for the fabric to choose between.
            continue
        conflicting = ", ".join(
            sorted(
                {
                    f"{_distribution_of(previous)} {_version_of(previous)}",
                    f"{_distribution_of(entry_point)} {_version_of(entry_point)}",
                }
            )
        )
        raise DuplicateBackendName(
            f"adapter name {entry_point.name!r} is declared by more than one"
            f" installed distribution ({conflicting}); the fabric does not"
            " choose between them. This is a packaging conflict in the"
            " installed environment, not a missing adapter: no adapter was"
            " resolved and neither candidate was loaded. Run"
            " `pip uninstall` on one of them, or ask its author to rename its"
            " adapter."
        )

    return builtins, third_party


def declared_names() -> frozenset[str]:
    """Every adapter name this deployment has installed. Imports nothing.

    The union of the two discovery sources, with three refusals applied first
    so that a name this function returns is a name :func:`resolve` will honour:

    * a third-party declaration of a name the SDK's own adapters hold
      (:class:`ReservedBackendName`, D-16);
    * one name declared by two different installed distributions
      (:class:`DuplicateBackendName`);
    * a declared name that is not of the required shape (``ValueError``).

    All three refuse the *whole* call, not just the offending name — see the
    module docstring for why that ruling is fail-closed and what the narrower
    alternative would have been.

    Raises:
        ReservedBackendName: an installed distribution claims a built-in name.
        DuplicateBackendName: two distributions declare one name.
        ValueError: a declared name is not of the required shape.
    """
    builtins, third_party = _declared()
    return frozenset(builtins) | frozenset(third_party)


def resolve(name: str) -> ResolvedBackend:
    """Import exactly the adapter `name` selects, and nothing else.

    The only function in this module that imports anything. Discovery runs
    first, so the packaging refusals above fire before any third-party code
    runs.

    A built-in is reached by importing its write module and reading the
    module-level registration record off it. A third-party adapter is reached
    through the declaration's own object reference. In both cases the loaded
    object is checked: it must be a :class:`BackendRegistration` and its name
    must equal the name it was resolved under, because a record that answers to
    a name it does not carry is an adapter claiming to be another one.

    Raises:
        UnknownBackend: no installed adapter registers `name`.
        ReservedBackendName: discovery found a reserved-name conflict.
        DuplicateBackendName: discovery found one name from two distributions.
        ValueError: a declared name is malformed, a discovered built-in carries
            no registration record, or the loaded object is not the adapter it
            was resolved as.
    """
    builtins, third_party = _declared()
    known = frozenset(builtins) | frozenset(third_party)

    if name not in known:
        available = ", ".join(sorted(known)) if known else "none"
        raise UnknownBackend(
            f"no installed adapter registers the backend name {name!r}."
            f" Registered adapters: {available}. An adapter becomes available"
            " by installing a distribution that declares it under the"
            f" {BACKEND_ENTRY_POINT_GROUP!r} entry-point group."
        )

    if name in builtins:
        module_path = builtins[name]
        registration = _load_builtin(module_path)
        if registration is None:
            raise ValueError(
                f"adapter {name!r} is discovered but not registered: module"
                f" {module_path!r} exists and imports, but carries no"
                f" module-level {REGISTRATION_ATTRIBUTE!r}. Discovery reads"
                " the adapter package's directory, so a write module without"
                " a registration record is visible and unusable. Add the"
                " record to that module."
            )
        origin = f"module {module_path!r}"
        version = _sdk_version()
        distribution = SDK_DISTRIBUTION
    else:
        # ``.select(name=...)`` returns *every* match. The mapping form
        # ``eps[name]`` returns the first silently, which is the shadowing
        # hazard D-16 exists to close — measured, not assumed. Duplicates are
        # already refused above, so this collection holds exactly one element.
        matches = tuple(_declared_entry_points().select(name=name))
        entry_point = matches[0]
        registration = entry_point.load()
        origin = (
            f"distribution {_distribution_of(entry_point)}"
            f" {_version_of(entry_point)} entry point {entry_point.value!r}"
        )
        version = _version_of(entry_point)
        distribution = _distribution_of(entry_point)

    if not isinstance(registration, BackendRegistration):
        raise ValueError(
            f"{origin} was resolved for adapter {name!r} but produced a"
            f" {type(registration).__name__}, not a BackendRegistration. An"
            " adapter registers a record the fabric interprets; it does not"
            " register an object of its own shape."
        )
    if registration.name != name:
        raise ValueError(
            f"{origin} was resolved for adapter {name!r} but its registration"
            f" carries the name {registration.name!r}. A record that answers"
            " to a name it does not carry is an adapter claiming to be"
            " another one."
        )

    return ResolvedBackend(
        registration=registration,
        version=version,
        distribution=distribution,
    )


def _load_builtin(module_path: str) -> object | None:
    """Import one built-in write module and read its registration record.

    **The only dynamic import in this module, and — asserted by test — the
    only one under ``src/`` and ``runtime/``.** See the module docstring for
    the residual this confinement compensates for and for the exact strength
    of the claim.

    Returns ``None`` when the module carries no registration attribute, so the
    caller can refuse by name rather than let an ``AttributeError`` escape.
    """
    module = importlib.import_module(module_path)
    return getattr(module, REGISTRATION_ATTRIBUTE, None)


def validate_connection(
    registration: BackendRegistration,
    connection: Mapping[str, object],
) -> CCFContract:
    """Validate a connection mapping against one adapter's config model.

    **The one place a connection refusal is built.** Three callers need this —
    the composition root, the manifest preflight, and the fixture that boots a
    conformance leg — and three hand-rolled versions is how a credential gets
    back into a message: a refusal formatted from a ``ValidationError``'s own
    rendering embeds the value that was supplied, and one of those values is a
    credential.

    It takes the *record* rather than a name because every caller already holds
    one from :func:`resolve`; taking a name would run discovery a second time
    for nothing.

    The message contract, which is the reason this is a function at all:

    * **Every line is built from the error's field location and reason only.**
      The supplied value is never read and the error's own rendering is never
      interpolated. See the comment at the construction site for the two keys
      that are forbidden and why.
    * **The message names the adapter.** Pydantic names the *model class*,
      which is not the same thing, and the refusal this replaces named the
      adapter — so a migration that kept only Pydantic's text would quietly
      have lost half of the refusal.
    * **The message names the field**, as a dotted path so a nested field reads
      as one.
    * **Lines are sorted**, so two runs over one bad mapping produce one
      message.
    * **One exception carries every problem.** A mapping with three problems
      should say all three; an adopter who fixes them one at a time reads the
      same file four times.
    * **The raised exception carries no chain.** The refusal is raised after
      the handler has exited, so ``__context__`` and ``__cause__`` are both
      empty. ``raise ... from None`` would not have been enough: it suppresses
      the *printed* chain and leaves the ``ValidationError`` — text and
      supplied values intact — reachable on the exception object, which is
      where a structured logger or an error reporter would find it.

    The case to get exactly right is an undeclared key, because that is the one
    carrying an adopter's typo — and a typo in a connection key means the value
    beside it was meant for somewhere else. The error's field location holds the
    offending key, which is what the message needs; the error's input holds what
    was supplied under it, which is what the message must never contain.

    What this deliberately does not do, because "the registry validates
    everything" is the natural next assumption and would put a second wrapper
    here for no gain:

    * It does not resolve an adapter.
    * It does not touch the credential mapping. The refusal for a credential
      supplied for a field an adapter never declared names a *key* and never a
      value, so it needs no sanitizing, and it stays where the selection is
      made — in the composition root for a direct caller, in preflight for a
      manifest. Both of those refusals read in the same shape as this one:
      adapter, then field.

    The residual, stated rather than claimed away: an adapter's own validator
    can put whatever it likes in the message it raises, and Pydantic reports
    that text as the reason. An adapter config model's validators stay
    value-free for the same reason this function does — the posture the
    networked adapters already take, where neither credential appears in any
    message the module raises.

    Args:
        registration: The adapter's record, as returned by :func:`resolve`.
        connection: The settings mapping to validate. **References, never
            resolved values** — a resolved credential inside a mapping that is
            about to be validated is the one input shape this contract cannot
            protect.

    Returns:
        The validated settings model.

    Raises:
        InvalidBackendConfig: the mapping does not satisfy the config model.
    """
    try:
        return registration.config_model.model_validate(dict(connection))
    except ValidationError as error:
        refusal = _connection_refusal(registration, error)
    # Raised **outside** the ``except`` block, and that placement is the whole
    # of one mitigation. ``raise ... from None`` sets ``__suppress_context__``
    # so a printed traceback omits the chained error — but it leaves
    # ``__context__`` pointing at the ``ValidationError``, whose text carries
    # the supplied value. Anything that walks exception chains explicitly (a
    # structured logger, an error reporter) would find the credential there.
    # Raising after the handler has exited attaches no implicit context at all,
    # so the object carries nothing to walk.
    raise InvalidBackendConfig(refusal)


def _connection_refusal(
    registration: BackendRegistration, error: ValidationError
) -> str:
    """The refusal text for one failed connection validation.

    Its own function so the two safe keys and the two forbidden ones are stated
    in one place a reviewer can read whole.
    """
    # ``detail["loc"]`` is the field path and ``detail["msg"]`` is the reason;
    # both are safe. ``detail["input"]`` is the value that was supplied and is
    # NEVER read, and neither is ``str(error)``, which embeds that value
    # verbatim. Do not simplify this back to either: one of those values is a
    # credential, and a misspelled connection key is precisely the case where a
    # credential lands under a key nobody declared.
    lines = sorted(
        f"  {'.'.join(str(part) for part in detail['loc']) or '<root>'}"
        f" — {detail['msg']}"
        for detail in error.errors()
    )
    return "\n".join(
        [
            f"backend {registration.name!r}: its connection settings are"
            " invalid:",
            *lines,
        ]
    )
