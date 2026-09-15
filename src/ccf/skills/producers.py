"""Producer registrations — from a Control Plane document to an askable producer.

`D-IMPL-340`. The composition root's half of capability A: it holds the
deployment's ``ccf.mcp-producer`` documents (Control Plane artifacts,
:class:`~ccf.controlplane.artifacts.McpProducerRegistration`), reads the
endpoint and credential from the environment variables those documents
**name**, builds the shared MCP client for each producer and registers it on
the :class:`~ccf.skills.dispatch.McpSkillRegistry`.

**This is the only place a producer's URL or credential is ever resolved**,
and it is the same posture the artifact server already has: a deployment
value read at the composition root, held by nothing in this package
(CINV-01). A document carries names; this module turns names into a client;
the registry holds the client and the *registration* — never the address.

SDK-defined (CLAUDE.md §7.1, §11). Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from ccf.contracts.canonical import content_hash
from ccf.controlplane.artifacts import McpProducerRegistration
from ccf.mcp.client import HttpClientFactory, McpResourceClient, SyncMcpBridge
from ccf.skills.dispatch import McpSkillRegistry, ProducerOffer, ProducerRegistration

__all__ = [
    "ProducerEnvironmentMissing",
    "producer_registration_from_artifact",
    "register_declared_producer",
]


class ProducerEnvironmentMissing(LookupError):
    """A producer document names an environment variable the process lacks.

    A **deployment/configuration** fact and therefore an exception (ruling 1):
    nothing was asked, no producer was reached, and no governed refusal could
    honestly describe it.
    """


#: How the composition root turns a bearer credential into transport
#: credentials: given the credential VALUE, return the ``httpx`` client factory
#: the shared MCP client threads to every call (the D-26 ``Authorization``
#: header lives on the client the deployment builds, never in the SDK).
CredentialFactory = Callable[[str], HttpClientFactory]


def producer_registration_from_artifact(
    artifact: McpProducerRegistration,
) -> ProducerRegistration:
    """The registry's view of one ``ccf.mcp-producer`` document.

    Carries the document's own content address, so every acquisition through
    the registration can name, in replay, exactly which governed statement
    authorized it — and carries neither of the two environment-variable names,
    because the registry holds a client, not an address.
    """
    return ProducerRegistration(
        server=artifact.server,
        producer_id=artifact.producer_id,
        producer_tenant=artifact.producer_tenant,
        offers=tuple(
            ProducerOffer(
                product_class=offer.product_class, versions_from=offer.versions_from
            )
            for offer in artifact.offers
        ),
        artifact_address=content_hash(artifact),
    )


def register_declared_producer(
    registry: McpSkillRegistry,
    *,
    artifact: McpProducerRegistration,
    environ: Mapping[str, str],
    bridge: SyncMcpBridge,
    credential_factory: CredentialFactory | None = None,
) -> ProducerRegistration:
    """Register one declared producer: names → client → registration.

    Args:
        registry: The deployment's MCP skill registry.
        artifact: The parsed ``ccf.mcp-producer`` document.
        environ: Where the two named variables are read from — passed in,
            never ``os.environ`` reached for here, so a test can supply a
            mapping and a deployment can supply its secret source.
        bridge: The deployment's one sync bridge, so an ``mcp_product``
            dispatch runs on the same background loop and under the same
            deadline as every other MCP call.
        credential_factory: Turns the credential value into the client
            factory that carries it. ``None`` means the endpoint is
            unauthenticated **and** the document must then name a credential
            variable that is set to the empty string — an absent credential
            is refused, a deliberately empty one is honored.

    Raises:
        ProducerEnvironmentMissing: a named variable is not present.
        ValueError: the logical name is already registered.
    """
    try:
        endpoint = environ[artifact.endpoint_from_env]
        credential = environ[artifact.credential_from_env]
    except KeyError as absent:
        raise ProducerEnvironmentMissing(
            f"producer {artifact.server!r} names environment variable"
            f" {absent.args[0]!r}, which is not set; the document names where"
            " the value lives and this process does not have it (D-IMPL-340)"
        ) from None
    if not endpoint.strip():
        raise ProducerEnvironmentMissing(
            f"producer {artifact.server!r}: {artifact.endpoint_from_env!r} is"
            " set but empty; an empty endpoint is not an endpoint"
        )
    registration = producer_registration_from_artifact(artifact)
    client = McpResourceClient(
        url=endpoint,
        bridge=bridge,
        http_client_factory=(
            None
            if credential_factory is None or not credential
            else credential_factory(credential)
        ),
    )
    registry.register_producer(client=client, registration=registration)
    return registration
