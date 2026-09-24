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

__all__ = ["CommandRefused", "RequestSpec", "load_document"]


class CommandRefused(ValueError):
    """A verb refuses its own inputs before any request is built.

    SDK-defined (D-IMPL-22). The exit-code contract in
    :mod:`ccf_runtime.cli.main` maps a *typed refusal* to exit 1 with the
    refusal printed on stdout; until this type existed only refusals that
    had already crossed the HTTP boundary could be reported that way, so a
    verb that had to refuse its own local inputs — an untrusted skill
    package, SEC-003 — could only raise and hand the operator a traceback.
    A refusal is a governance outcome and reads like one.
    """


@dataclass(frozen=True)
class RequestSpec:
    """One HTTP request a verb translates to — method, path, inputs.

    ``tolerate_empty_bump`` marks a registration whose re-run with
    byte-identical content is by-design idempotent (the importer's
    unchanged ``references/`` artifacts): a 409 whose typed refusal is
    ``RefuseEmptyBump`` — and only that refusal — is then not a failure.
    """

    method: str
    path: str
    params: Mapping[str, str] = field(default_factory=dict)
    json: object | None = None
    tolerate_empty_bump: bool = False


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
