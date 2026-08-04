"""D-12 — regenerate the committed `openapi.json` from `create_app()`.

D-11's posture for the documentation suite is generate-at-build: nothing
derived from code is committed, because a committed derivative is a
derivative that can go stale. D-12 is that posture's one deliberate
exception. The OpenAPI document is the contract *external integrators
consume*, so it is committed at the repo root and reviewed as a diff: an
endpoint that moves, a response body that changes shape, or a description
that starts leaking internal detail all surface as reviewable lines on the
same commit that causes them, rather than as a silent difference between
what the SDK serves and what the published reference page claims.

This module is the regeneration half of that arrangement. The assertion
half is `tests/http_api/test_openapi.py`, which imports `serialize` from
here so the two halves cannot drift apart, and whose failure message names
`make openapi` as the fix.

Determinism recipe
------------------

`json.dumps(..., indent=2, sort_keys=True)` removes dict-ordering
sensitivity, so the bytes do not depend on the order FastAPI happened to
walk its routers or Pydantic happened to register its models. `fastapi`
and `pydantic` are exact pins in `pyproject.toml`, so the
`components.schemas` shapes are fixed for a given checkout.

The corollary is deliberate, not a bug: **a FastAPI or Pydantic bump will
move the spec.** That diff is desirable and reviewable — it is precisely
the moment a maintainer should look at what the dependency changed about
the published contract — and the correct response is to run `make openapi`
and read the diff, never to relax the check.

Why the injected handles can be `None`
--------------------------------------

`create_app` mounts every router unconditionally and the routers only ever
close over `deps`; nothing on the dependency bundle is read at construction
time, and `app.openapi()` walks route signatures rather than calling any
handler. The emitted schema is therefore independent of the injected
handles. This tool constructs the minimal `ApiDependencies` the frozen
dataclass accepts rather than duplicating the whole fabric wiring of
`tests/http_api/conftest.py` — the drift test runs against that fixture's
fully-wired app, so any divergence between the two constructions would
fail the check rather than hide in it.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

#: The committed contract baseline (D-12).
OPENAPI_PATH = REPO_ROOT / "openapi.json"


def build_app() -> Any:
    """Construct the app whose `openapi()` output is the contract."""
    from ccf_runtime.http_api.app import create_app
    from ccf_runtime.http_api.dependencies import ApiDependencies

    # Not read at construction time (see module docstring); the routers
    # merely close over the bundle. Typed as Any so the absence of real
    # handles is explicit rather than smuggled through a fake object.
    unused: Any = None

    return create_app(
        ApiDependencies(
            control_plane=unused,
            artifact_store=unused,
            product_resolver=unused,
            workflow_factory=unused,
            workflow_engine=unused,
            hitl_transport=unused,
            skill_catalog=unused,
            grant_ledger=unused,
        ),
        # This tool is about the document, not the posture; the D-IMPL-73
        # warning has its own dedicated suite.
        acknowledge_insecure_default=True,
    )


def serialize(document: dict[str, Any]) -> str:
    """The one serialization recipe — see "Determinism recipe" above.

    `tests/http_api/test_openapi.py` imports this function rather than
    restating the recipe, so the committed file and the drift assertion
    can never disagree about what "the spec" means.
    """
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate the committed openapi.json from create_app() (D-12)."
        )
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Write nothing; exit 1 if the on-disk file differs from what"
            " create_app() emits."
        ),
    )
    args = parser.parse_args(argv)

    emitted = serialize(build_app().openapi())

    if args.check:
        on_disk = (
            OPENAPI_PATH.read_text(encoding="utf-8")
            if OPENAPI_PATH.exists()
            else ""
        )
        if on_disk != emitted:
            print(
                f"{OPENAPI_PATH} differs from what create_app() emits."
                " Run `make openapi` and review the diff — a moved endpoint"
                " or a FastAPI version bump is a reviewable change to the"
                " published contract, not a test bug.",
                file=sys.stderr,
            )
            return 1
        return 0

    OPENAPI_PATH.write_text(emitted, encoding="utf-8")
    print(f"wrote {OPENAPI_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
