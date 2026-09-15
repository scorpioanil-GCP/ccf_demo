"""The deployment-environment document beside a ``ccf_config.yaml``.

**SDK-defined** (CLAUDE.md §11); `D-IMPL-343` design §5.1 and Dave's GO lock:
*"Do not put URLs or tokens in configuration."* A ``ccf_config.yaml`` is
Control Plane content — content-hashed, pinned into replay dimension 2, and
never allowed to carry a DSN, a host, a credential or a URL (`D-IMPL-136`:
*"connection material is deployment environment, not Control Plane state"*).
Every canonical tree therefore kept a second document for the environment's
NAMES, and each tree invented its own shape for it and its own reader
(``backends.yaml`` + a ``_setting()`` in ``acquisition.py``, a ``door.yaml`` +
a ``door_values()`` in ``serve.py``, a ``ttl.yaml`` nobody but the tree read).
This module is the one shape and the one reader.

What ``ccf_environment.yaml`` holds, and what it refuses
---------------------------------------------------------
**Names, never values.** Every connection-shaped thing is an environment
variable's NAME with the remedy text an unset variable raises with — the
posture :class:`~ccf.controlplane.artifacts.McpProducerRegistration` already
takes for a producer's endpoint and credential. The document is not hashed
into anything and is never registered; it is read once, at
:func:`~ccf.products.product.open_product`, and its values are handed to the
deployment's own acquisition as resolved strings.

::

    config: ccf_config.yaml            # the Control Plane document this environment serves
    substrate:                         # the per-question dev fabric, minted under the scratch root
      setting: database_path           # WHICH connection setting receives the minted path
      prefix: cp_03_canonical
      suffix: .db
    sources:                           # the deployment's SOURCE stores, by the deployment's own names
      financial_spread:
        dsn:    {from_env: CCF_CP_03C_POSTGRES_DSN,    remedy: "export a READ-ONLY DSN ..."}
        schema: {from_env: CCF_CP_03C_POSTGRES_SCHEMA, remedy: "the v2 namespace ..."}
    door:                              # the standard door's environment; every member a NAME
      credential:          {from_env: CCF_CP_03C_DOOR_TOKEN, remedy: "..."}
      issuer_url:          {from_env: CCF_CP_03C_DOOR_ISSUER, remedy: "..."}
      resource_server_url: {from_env: CCF_CP_03C_DOOR_RESOURCE, remedy: "..."}
    remote:                            # consumers: the one MCP deadline every remote ask runs under
      call_timeout_seconds: 120

**A Control Plane value written here is refused by name.** Every block is
``extra="forbid"`` (inherited from :class:`~ccf.contracts.base.CCFContract`),
so ``principal_id``, ``role``, ``product_ttl_seconds``, ``record_class`` — the
keys two shipped side documents carried beside a config that already declared
them, and that nothing ever compared — are unknown keys here. A value with one
home cannot be restated in the other document, which is what turns *"the two
copies agree"* from a comment into a property.

**The substrate names no backend.** ``substrate.setting`` is the name of the
connection setting the declared adapter takes for its per-question path, and
``prefix``/``suffix`` are opaque strings the facade joins onto the scratch
root: nothing in this module or in :mod:`ccf.products.product` names a
substrate, and backend selection stays exactly what
:func:`~ccf.deployment.manifest._preflight_adapter` does today (CINV-04).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, field_validator

from ccf.contracts.base import CCFContract
from ccf.contracts.canonical import HASH_TRANSPARENT_KEY

__ccf_mode__ = "algorithmic"

__all__ = [
    "ENVIRONMENT_DOCUMENT_NAME",
    "DoorEnvironment",
    "EnvironmentDocument",
    "EnvironmentMissing",
    "EnvironmentValue",
    "RemoteSettings",
    "SubstrateSettings",
    "load_environment_document",
    "resolve_value",
    "resolve_values",
]

#: The document's name beside ``ccf_config.yaml``. A name, so a reader who
#: opens a paved tree knows where the environment is declared without being
#: told; a deployment that keeps its names elsewhere writes this file to say
#: so.
ENVIRONMENT_DOCUMENT_NAME = "ccf_environment.yaml"

#: What an environment-variable NAME looks like — the same rule
#: :class:`~ccf.controlplane.artifacts.McpProducerRegistration` holds its
#: two ``*_from_env`` members to, so a literal URL, host, port or token cannot
#: be written where a name belongs.
_ENV_VAR_NAME = re.compile(r"[A-Z][A-Z0-9_]*")


class EnvironmentMissing(LookupError):
    """A declared environment variable is not set, or is set to nothing.

    A **deployment/configuration** fact and therefore an exception (the
    `D-IMPL-340` ruling-1 posture): nothing was asked, no source was reached,
    and no governed refusal could honestly describe it. The message carries
    the remedy the document declared, because the document is where the
    deployment said what the variable is for.
    """


class EnvironmentValue(CCFContract):
    """One value the environment supplies: the variable's NAME and the remedy.

    Attributes:
        from_env: The environment variable the value is read from. A name;
            a literal is refused at parse.
        remedy: What an operator does when it is unset — the deployment's own
            words, raised verbatim by :func:`resolve_value`.
    """

    from_env: str
    remedy: str

    @field_validator("from_env")
    @classmethod
    def _is_an_environment_variable_name(cls, value: str) -> str:
        if _ENV_VAR_NAME.fullmatch(value) is None:
            raise ValueError(
                f"{value!r} is not an environment-variable name; the"
                " environment document names WHERE a value is read from,"
                " never the value — a URL, host, port, path or token here is"
                " what CINV-01 forbids (D-IMPL-343)"
            )
        return value

    @field_validator("remedy")
    @classmethod
    def _remedy_is_stated(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(
                "a remedy is the deployment's own words for an unset"
                " variable, and an empty one tells an operator nothing"
                " (D-IMPL-343)"
            )
        return value


class SubstrateSettings(CCFContract):
    """Where the per-question dev fabric is minted, and under which setting.

    Attributes:
        setting: The connection setting of the declared adapter that receives
            the minted per-question path — named by the deployment, so the
            SDK names no adapter's field.
        prefix: The first part of every minted filename.
        suffix: The last part. Opaque to the SDK.
    """

    setting: str
    prefix: str
    suffix: str

    @field_validator("setting", "prefix")
    @classmethod
    def _is_stated(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("a substrate setting or prefix is stated, never blank")
        return value


class DoorEnvironment(CCFContract):
    """The standard door's environment: three names, no value.

    Attributes:
        credential: The bearer credential this boot is reached with. When the
            variable is UNSET the door mints one per boot and exposes it on
            :class:`~ccf_runtime.mcp.product_door.ProductDoor`, because a
            development door reached by the process that spawned it has no
            operator to export a secret; a parent that wants to know the
            credential without a side channel SETS the variable.
        issuer_url: The OAuth issuer the door's auth settings advertise.
        resource_server_url: The resource-server address they advertise.
            Both URL names are consulted by every transport EXCEPT the
            loopback one, which binds its own port and therefore knows its
            own address (see
            :meth:`~ccf_runtime.mcp.product_door.ProductDoor.serve_loopback`).
    """

    credential: EnvironmentValue
    issuer_url: EnvironmentValue
    resource_server_url: EnvironmentValue


class RemoteSettings(CCFContract):
    """A consuming deployment's one MCP deadline (`D-IMPL-340` item 10)."""

    call_timeout_seconds: int

    @field_validator("call_timeout_seconds")
    @classmethod
    def _is_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("a call timeout is a positive number of seconds")
        return value


class EnvironmentDocument(CCFContract):
    """The whole document. See the module docstring for the shape it holds.

    Attributes:
        config: The Control Plane document this environment serves, relative
            to the environment document's own directory.
        substrate: Required — every paved-road question boots a fresh fabric
            and the SDK will not choose where.
        sources: The deployment's source stores, keyed by the deployment's
            own names, each a mapping of setting name to
            :class:`EnvironmentValue`. Empty for a deployment that reads no
            source (a pure consumer).
        door: The standard door's environment, or ``None`` for a deployment
            that opens none.
        remote: Consumer settings, or ``None``.
    """

    # Hash-transparent at every default (`D-IMPL-243`): this document is never
    # content-hashed into anything, and the key says so structurally rather
    # than leaving the lint to ask.
    config: str = Field(default="ccf_config.yaml", json_schema_extra={HASH_TRANSPARENT_KEY: True})
    substrate: SubstrateSettings
    sources: Mapping[str, Mapping[str, EnvironmentValue]] = Field(
        default_factory=dict, json_schema_extra={HASH_TRANSPARENT_KEY: True}
    )
    door: DoorEnvironment | None = Field(default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True})
    remote: RemoteSettings | None = Field(default=None, json_schema_extra={HASH_TRANSPARENT_KEY: True})

    @field_validator("config")
    @classmethod
    def _config_stays_beside_this_document(cls, value: str) -> str:
        candidate = Path(value)
        if not value.strip() or candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError(
                f"`config` names {value!r}; the Control Plane document an"
                " environment serves lives beside it, named relatively and"
                " never above it (D-IMPL-343)"
            )
        return value


def load_environment_document(config_root: Path) -> EnvironmentDocument:
    """Read and validate ``ccf_environment.yaml`` under ``config_root``.

    Raises:
        FileNotFoundError: the document is absent — a paved deployment has
            exactly two documents, and this is the second.
        ValueError: the document does not satisfy :class:`EnvironmentDocument`
            — a value where a name belongs, a Control Plane key restated, a
            block the SDK does not know.
    """
    path = Path(config_root) / ENVIRONMENT_DOCUMENT_NAME
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} does not exist; a paved-road deployment declares its"
            " environment — the substrate, its source variables' names, its"
            " door's names — in that one document beside ccf_config.yaml"
            " (D-IMPL-343)"
        )
    loaded: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, Mapping):
        raise ValueError(f"{path} is not a mapping of names to blocks")
    try:
        return EnvironmentDocument.model_validate(dict(loaded))
    except ValueError as error:
        raise ValueError(f"{path} is not a valid environment document: {error}") from error


def resolve_value(value: EnvironmentValue, environ: Mapping[str, str]) -> str:
    """The value ``value`` names, from ``environ``, or the declared remedy.

    Raises:
        EnvironmentMissing: the variable is unset or empty. The message is
            the document's own remedy text, because the deployment is the
            party that knows what the variable is for.
    """
    found = environ.get(value.from_env)
    if not found:
        raise EnvironmentMissing(f"{value.from_env} is not set.\n\n{value.remedy}")
    return found


def resolve_values(
    sources: Mapping[str, Mapping[str, EnvironmentValue]], environ: Mapping[str, str]
) -> Mapping[str, Mapping[str, str]]:
    """Every declared source setting, resolved — the mapping ``acquire`` receives.

    Resolved ONCE, at open, so a missing variable is refused before the first
    question rather than three frames inside a source read; and refused for
    every missing name together, so an operator fixes the environment in one
    pass rather than one variable per attempt.

    Raises:
        EnvironmentMissing: one or more variables are unset; every remedy is
            carried.
    """
    resolved: dict[str, dict[str, str]] = {}
    missing: list[str] = []
    for source, settings in sources.items():
        resolved[source] = {}
        for name, value in settings.items():
            try:
                resolved[source][name] = resolve_value(value, environ)
            except EnvironmentMissing as absent:
                missing.append(str(absent))
    if missing:
        raise EnvironmentMissing("\n\n".join(missing))
    return resolved
