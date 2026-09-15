"""The manifest keys a single-file deployment derived — read, never restated.

**SDK-defined** (CLAUDE.md §11); `D-IMPL-343` design §5.3. The reserved
section names of a ``ccf_config.yaml`` ARE its manifest keys unless a section
overrides ``key:``, and :func:`~ccf.deployment.config.derive_deployment` is
the one place that mapping is decided. Before this module every canonical tree
restated the five keys it needed as string properties on a scenario object —
``"product_class"``, ``"request_contract"``, ``"policy"``, ``"half_life"``,
``"debt_profile"`` — one file over from the config that declared them, so a
section renamed in the document was silent until the first request. The keys
are now handed back on :attr:`~ccf.deployment.BootedFabric.keys`, derived by
the same code that derived the entries, and a deployment reads them rather than
spelling them.

A frozen dataclass rather than a contract, on :class:`~ccf.deployment.pins
.ArtifactPin`'s reasoning inverted: this carries no version and no content,
only the names the derivation chose, and it is never hashed into anything.
``None`` for an optional section the config did not declare is a positive
statement — *this deployment declares no such section* — never a default the
SDK filled in.

Its own module rather than a member of :mod:`ccf.deployment.config`, because
:mod:`ccf.deployment.manifest` must name the type on the fabric it returns and
already sits underneath the config loader in the import graph.
"""

from __future__ import annotations

from dataclasses import dataclass

__ccf_mode__ = "algorithmic"

__all__ = ["DeploymentKeys"]


@dataclass(frozen=True)
class DeploymentKeys:
    """Every manifest key a derived deployment put in force, by section.

    Attributes:
        product_class: The ``product_class`` section's key — required, so
            never ``None``.
        request_contract: The ``request_contract`` section's key, or ``None``
            when the deployment declared none.
        policy_bundle: The bundle in force — the ``policy`` section's key, or
            the explicit ``policy_bundle_key`` the config named instead.
        resolution_spec: The entity-resolution spec in force, resolved the
            same way.
        half_life: The ``half_life`` section's key, or ``None``.
        debt_profile: The ``debt_profile`` section's key, or ``None``.
        default_perspective: The ``default_perspective`` section's key, or
            ``None``.
        replay: The ``replay`` section's key (`D-IMPL-282` R-12), or ``None``.
        ttl: The ``ttl`` section's key (`D-IMPL-343`), or ``None``.
        door: The ``door`` section's key (`D-IMPL-343`), or ``None``.
        agent: The ``agent`` section's key (`D-IMPL-343` R-2), or ``None``.
        operator_parameters: The ``operators:`` entries' keys, in the sorted
            order the derivation registered them — the tuple
            :func:`~ccf.products.resolver.build_governed_resolver` takes as
            ``operator_parameter_keys``.
        policy_constraints: The ``policy_constraints:`` entries' keys, sorted.
        producers: The ``producers:`` entries' keys, sorted (`D-IMPL-340`).
    """

    product_class: str
    request_contract: str | None
    policy_bundle: str
    resolution_spec: str
    half_life: str | None
    debt_profile: str | None
    default_perspective: str | None
    replay: str | None
    ttl: str | None
    door: str | None
    agent: str | None
    operator_parameters: tuple[str, ...]
    policy_constraints: tuple[str, ...]
    producers: tuple[str, ...]
