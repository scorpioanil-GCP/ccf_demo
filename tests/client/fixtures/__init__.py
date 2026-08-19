"""Where the client suite's fixture deployment and its server program live.

The deployment under ``deployment/`` is **data only** — ``D-IMPL-141``
Amendment A.3 grants it exactly one Python module, its projection, and
``tests/client/test_data_only_deployment.py`` refuses a second by name. So the
deployment's MCP server program sits **here**, one level up — which is exactly
where ``binding.yaml``'s ``server:`` key looks, because that key resolves
against the directory *holding* the deployment rather than against the
deployment root (``D-10``, Dave, 2026-08-18).
"""

from __future__ import annotations

from pathlib import Path

import yaml

__all__ = ["STDIO_SERVER", "declare_server"]

#: The fixture deployment's own MCP server program. Named once so the adapter
#: tests and the conformance binding launch the same thing.
STDIO_SERVER = Path(__file__).parent / "stdio_server.py"

#: The document a deployment root states its wiring in. Spelled here rather
#: than imported so this module stays importable without the SDK on the path.
_BINDING_DOCUMENT_NAME = "binding.yaml"


def declare_server(root: Path, program: Path) -> None:
    """Point a copied deployment's ``server:`` at ``program``.

    ``program`` is an **absolute path to the file as it now sits on disk**; the
    value written is its position relative to ``root.parent``, because that is
    the base the loader resolves this key against. One signature, used
    identically at every call site.

    **This is the only place in the suite that writes a ``server:`` value.** A
    test spelling its own into a copied ``binding.yaml`` would be a second place
    the program's location is decided, and a copy that drifted from the
    committed fixture would make the adapter's refusal fire for the wrong
    reason — a refusal about a program that is missing because the *test* put
    it somewhere else reads exactly like a refusal about a deployment that
    declared none.

    Raises:
        ValueError: ``program`` does not sit under ``root.parent``. Refused
            rather than written, because a value the loader would refuse for
            containment is a fixture that fails for a reason no test is about.
    """
    base = root.parent.resolve()
    resolved = program.resolve()
    try:
        relative = resolved.relative_to(base)
    except ValueError as outside:
        raise ValueError(
            f"{resolved} is not under {base}, so no `server:` value spells it —"
            " the program a deployment declares sits in the directory holding"
            " that deployment"
        ) from outside

    document = root / _BINDING_DOCUMENT_NAME
    body = yaml.safe_load(document.read_text(encoding="utf-8"))
    body["server"] = str(relative)
    document.write_text(yaml.safe_dump(body), encoding="utf-8")
