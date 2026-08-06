"""The ``schema`` noun — JSON Schema per SDK artifact class (ERGO-12).

SDK-defined (CLAUDE.md §8.3). Two read-only endpoints: the list of class
ids this route serves the schema of, and one class's JSON Schema document.

**Exactly which classes, stated precisely.** The route serves
:data:`~ccf.deployment.classes.SDK_ARTIFACT_CLASSES` — the classes a manifest
may name for **typed** registration. Since plan 15.1-03 that is no longer the
same set as "every SDK-owned class a manifest may name": the SDK also owns
:data:`~ccf.deployment.classes.SDK_VERSIONED_ARTIFACT_CLASSES`, the six
author-versioned classes a manifest may name for ``registration: versioned``,
and this route answers 404 for those even though ``docs/schemas/`` holds their
committed schemas.

That gap is recorded rather than closed here. Widening the served set is a
runtime surface change nobody has ruled on, and the honest reading of the
route's contract — "schemas the SDK owns" versus "classes a manifest may name
for typed registration" — is the open question, not the symptom. See
``.planning/phases/15.1-ergonomics-gap-closure/deferred-items.md``.

**Emitted from the live models, never read off disk.** The committed
``docs/schemas/`` tree is the *drift baseline* an adopter's editor points
at; this route is what that baseline is checked against, exactly as
``create_app().openapi()`` relates to the committed ``openapi.json``. A
route that served the committed files instead would make the freshness
gate circular — the schemas would agree with themselves and with nothing
else.

**Why this route exists at all** (D-IMPL-79). ``ccf schema export`` could
have generated schemas locally, in the CLI, with no HTTP hop. It does not,
because the CLI's whole posture is that every command travels the same
routes any client uses and holds no privileged path (T-07-27) — and the
first exception to that is the one that makes the second easy. Adding the
route costs one module; adding a privileged CLI path costs the invariant.

The route enumerates no domain vocabulary: the class ids come from
:data:`~ccf.deployment.classes.SDK_ARTIFACT_CLASSES`, the SDK's own
hand-maintained registry of what it owns for typed registration (CINV-01).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ccf.deployment.classes import SDK_ARTIFACT_CLASSES
from ccf_runtime.http_api.dependencies import ApiDependencies

__ccf_mode__ = "algorithmic"

__all__ = ["build_router"]

#: The JSON Schema extension key carrying the CCF artifact class id. Stated
#: here rather than imported from ``tools/`` because ``/runtime`` never
#: depends on the repo's build tooling; ``tests/cli/test_schema_export.py``
#: holds the two spellings equal so they cannot drift.
CLASS_ID_KEY = "x-ccf-class-id"


def build_router(deps: ApiDependencies) -> APIRouter:
    """The schema router. Reads nothing from ``deps`` — the artifact
    classes are SDK mechanism, not deployment state, so no fabric handle
    is involved and none is held."""
    router = APIRouter()

    @router.get(
        "",
        response_model=list[str],
        summary="Schema classes (ERGO-12)",
    )
    def classes() -> list[str]:
        return sorted(SDK_ARTIFACT_CLASSES)

    @router.get("/{class_id}", summary="Schema export (ERGO-12)")
    def schema(class_id: str) -> dict[str, Any]:
        artifact_class = SDK_ARTIFACT_CLASSES.get(class_id)
        if artifact_class is None:
            # A typed 404 rather than the open ``DeclaredArtifact``
            # envelope's schema: the SDK owns the schema of what it ships
            # and never invents one for a namespace that is not its own,
            # so "no schema here" is the honest answer for a
            # deployment-authored class id (CLAUDE.md §11).
            raise HTTPException(
                status_code=404,
                detail=(
                    f"{class_id!r} is not an artifact class the SDK owns the"
                    " schema of; deployment-authored classes carry their own"
                ),
            )
        document: dict[str, Any] = artifact_class.contract.model_json_schema()
        document[CLASS_ID_KEY] = class_id
        return document

    return router
