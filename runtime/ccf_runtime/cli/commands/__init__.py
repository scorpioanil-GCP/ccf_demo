"""Shared command plumbing: the request spec and document loading (07-11).

SDK-defined (D-IMPL-22). Each sibling module exposes
``register(subparsers)`` adding one ruled noun with its verbs; every verb
handler is a pure translation from parsed arguments to one or more
:class:`RequestSpec` values — the CLI never interprets what it sends or
receives, it moves typed documents between the operator and the same
routes any client uses (T-07-27).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

__ccf_mode__ = "algorithmic"

__all__ = ["RequestSpec", "load_document"]


@dataclass(frozen=True)
class RequestSpec:
    """One HTTP request a verb translates to — method, path, inputs."""

    method: str
    path: str
    params: Mapping[str, str] = field(default_factory=dict)
    json: object | None = None


def load_document(path: str) -> dict[str, Any]:
    """Load one YAML/JSON artifact document from ``path``.

    The file carries the artifact; the CLI carries nothing inline
    (No-Hardcoding Rule, CLAUDE.md §6.4 — T-07-29).
    """
    loaded = yaml.safe_load(Path(path).read_text())
    if not isinstance(loaded, dict):
        raise ValueError(
            f"{path!r} does not hold a mapping document; an artifact file"
            " is a single YAML/JSON mapping"
        )
    return loaded
