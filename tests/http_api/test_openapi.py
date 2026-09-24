"""EXPR-03's "valid OpenAPI spec" as a passing test, not prose (07-10 Task 2).

The generated document is asserted from what ``app.openapi()`` actually
emits (research A1: validate the emitted version field, never hardcode
prose about it); the v0 auth posture is asserted as string-equality against
the same module-level constant the served document carries (Ollama S4 /
D-22 honesty); and ``extra=forbid`` contracts surface as
``additionalProperties: false`` in the components, spot-checked.

Since 14-03 this module also carries the **D-12 drift assertion**: the
committed ``openapi.json`` must equal what ``create_app()`` emits right
now. It lives here, beside the other document assertions, because
``tests/`` is the already-always-on ``test`` job — so an endpoint change
fails CI on the same commit that causes it, with no new CI wiring.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import pytest

from ccf_runtime.http_api.app import AUTH_POSTURE_SENTENCE
from tools.dump_openapi import serialize

# Repo root from this file's own path, never ``Path.cwd()`` — pytest may be
# invoked from anywhere and the baseline is a fixed repo artifact.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_COMMITTED_SPEC = _REPO_ROOT / "openapi.json"

# The serialization recipe is stated ONCE, in ``tools/dump_openapi.py``, and
# imported here rather than restated, so the regenerator and this assertion
# cannot disagree about what "the spec" means. Recorded for the SUMMARY, the
# recipe is `json.dumps(document, indent=2, sort_keys=True) + "\n"`:
# sort_keys=True removes dict-ordering sensitivity, and the exact fastapi /
# pydantic pins fix the components.schemas shapes.
_DRIFT_MESSAGE = (
    "The committed openapi.json no longer matches what create_app() emits."
    " Run `make openapi` and commit the result. A moved endpoint or a"
    " FastAPI/Pydantic version bump legitimately changes the published"
    " contract — that diff is reviewable and desirable, not a test bug."
)


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
    """String-equality against the constant, not a loose grep (D-22).

    ``SEC-001`` replaced what the constant says — it used to state that the
    API performs no authentication or authorization — so the two content
    assertions below move with it. What does not move is the shape of the
    claim: the exact constant is served verbatim, and it is one statement an
    adopter can read rather than a paragraph.
    """
    description = _document(app)["info"]["description"]
    assert AUTH_POSTURE_SENTENCE in description
    # one sentence, one full stop
    assert AUTH_POSTURE_SENTENCE.count(".") == 1
    assert "authenticated and authorized" in AUTH_POSTURE_SENTENCE
    assert "no unauthenticated arm" in AUTH_POSTURE_SENTENCE


def test_extra_forbid_surfaces_as_additional_properties_false(
    app: Any,
) -> None:
    """Spot-check two extra=forbid contracts in the emitted components."""
    schemas = _document(app)["components"]["schemas"]
    for contract in ("HitlActionSubmission", "WorkflowInvocationRequest"):
        assert schemas[contract].get("additionalProperties") is False, contract


@pytest.mark.xfail(
    strict=True,
    reason=(
        "SEC-001 changed the served contract — deleted body fields"
        " (ArtifactPutRequest.tenant_id, GrantRequest.actor,"
        " GrantRevocationRequest.actor), deleted query parameters (the hitl"
        " and workflow `tenant`), and new docstrings that FastAPI publishes"
        " as schema descriptions. `openapi.json`, `docs/schemas/` and the"
        " surface log are regenerated ONCE when the parallel lanes join;"
        " regenerating them per lane guarantees a merge conflict in a"
        " generated file. strict=True so this turns red the moment the"
        " regeneration lands, which is exactly when this marker must go."
    ),
)
def test_the_committed_spec_matches_what_the_app_emits(app: Any) -> None:
    """D-12: the baseline external integrators consume is not stale.

    Asserted on **bytes**, not on parsed dicts, because the committed file
    is reviewed as a diff — whitespace and key order are part of what makes
    that diff readable, so they are part of what is asserted.
    """
    committed = _COMMITTED_SPEC.read_text(encoding="utf-8")
    assert committed == serialize(_document(app)), _DRIFT_MESSAGE


def test_the_drift_message_names_the_regeneration_command(app: Any) -> None:
    """Edge case: a failure nobody can act on is a failure that gets muted."""
    assert "make openapi" in _DRIFT_MESSAGE
    assert "openapi.json" in _DRIFT_MESSAGE


def test_the_committed_spec_parses_and_carries_paths(app: Any) -> None:
    """The committed artifact is a servable document, not just some text."""
    document = json.loads(_COMMITTED_SPEC.read_text(encoding="utf-8"))
    assert document["openapi"].startswith("3.")
    assert document["paths"], "the committed spec advertises no endpoints"
