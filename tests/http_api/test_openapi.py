"""EXPR-03's "valid OpenAPI spec" as a passing test, not prose (07-10 Task 2).

The generated document is asserted from what ``app.openapi()`` actually
emits (research A1: validate the emitted version field, never hardcode
prose about it); the v0 auth posture is asserted as string-equality against
the same module-level constant the served document carries (Ollama S4 /
D-22 honesty); and ``extra=forbid`` contracts surface as
``additionalProperties: false`` in the components, spot-checked.
"""

from __future__ import annotations

import json
from typing import Any

from ccf_runtime.http_api.app import AUTH_POSTURE_SENTENCE


def _document(app: Any) -> dict[str, Any]:
    document: dict[str, Any] = app.openapi()
    return document


def test_the_emitted_document_is_openapi_3(app: Any) -> None:
    """The version field of the document itself, not a claim about it."""
    document = _document(app)
    version = document["openapi"]
    assert isinstance(version, str)
    assert version.startswith("3."), version
    # Recorded for the SUMMARY: FastAPI 0.140.0 emits this exact value.
    assert version == "3.1.0"


def test_the_document_serializes_as_json(app: Any) -> None:
    """Parseable end to end — the document is servable, not just buildable."""
    round_tripped = json.loads(json.dumps(_document(app)))
    assert round_tripped["info"]["title"] == "CCF HTTP API"


def test_every_contract_bearing_route_lands_a_schema(app: Any) -> None:
    """The components carry the SDK's own contracts — the API adds
    serialization and routing, no new semantics (D-IMPL-23)."""
    schemas = _document(app)["components"]["schemas"]
    for contract in (
        "AgentDeclarationRequest",
        "AgentDeclared",
        "GrantRequest",
        "GrantIssued",
        "SkillCatalogEntry",
        "WorkflowInvocationRequest",
        "WorkflowResumptionRequest",
        "WorkflowSuspended",
        "WorkflowCompleted",
        "WorkflowStateRecord",
        "PendingHitlEvent",
        "HitlActionSubmission",
        "ArtifactPutRequest",
        "ArtifactRef",
    ):
        assert contract in schemas, contract


def test_the_exact_auth_posture_sentence_is_served(app: Any) -> None:
    """String-equality against the constant, not a loose grep (D-22)."""
    description = _document(app)["info"]["description"]
    assert AUTH_POSTURE_SENTENCE in description
    # and the constant is the honest, single-sentence statement it claims
    assert AUTH_POSTURE_SENTENCE.count(".") == 1
    assert "no authentication" in AUTH_POSTURE_SENTENCE


def test_extra_forbid_surfaces_as_additional_properties_false(
    app: Any,
) -> None:
    """Spot-check two extra=forbid contracts in the emitted components."""
    schemas = _document(app)["components"]["schemas"]
    for contract in ("HitlActionSubmission", "WorkflowInvocationRequest"):
        assert schemas[contract].get("additionalProperties") is False, contract
