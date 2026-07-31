"""``ccf skill import <dir>`` — the one-way SKILL.md importer (D-IMPL-56).

SDK-defined (D-IMPL-22 surface; the D-IMPL-56 SKILL.md-authoring ruling).
SKILL.md is an authoring format, never a canonical artifact: import maps
frontmatter ``name``/``description`` onto a ``procedure`` catalog entry,
registers the body as a ``ccf.prompt-artifact``, registers ``references/``
files as further pinned artifacts, and binds the body by
:class:`~ccf.agents.definitions.InstructionBinding` reference — the
command authors no prose of its own; everything comes from the imported
directory (No-Hardcoding, CLAUDE.md §6.4).

``allowed-tools`` is deliberately **not** mapped onto
``SkillRequirements``: a harness permission token is not a policy-regime
identifier, and the SDK never interprets a requirement identifier
(D-IMPL-29). Requirements come only from explicit ``--required-scope`` /
``--required-context-product`` flags — the operator's statement.

Registration travels the same routes any client uses (over HTTP or
``--local``), so re-import is a normal versioned Control Plane
registration — the working tree is read, never written (one-way; replay
pins exact artifact versions, D-IMPL-26).

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import jinja2.meta
import jinja2.sandbox
import yaml

from ccf.agents.definitions import PROMPT_ARTIFACT
from ccf_runtime.cli.commands import RequestSpec

__ccf_mode__ = "algorithmic"

__all__ = ["register"]

#: Current schema lanes of the two SDK artifact classes the importer emits.
_PROMPT_SCHEMA_VERSION = "1.0.0"
_ENTRY_SCHEMA_VERSION = "2.0.0"


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split a SKILL.md into (frontmatter mapping, body)."""
    parts = text.split("---", 2)
    if len(parts) < 3 or parts[0].strip():
        raise ValueError(
            "SKILL.md must open with a `---`-delimited YAML frontmatter block"
        )
    frontmatter = yaml.safe_load(parts[1])
    if not isinstance(frontmatter, dict):
        raise ValueError("SKILL.md frontmatter is not a mapping")
    return frontmatter, parts[2].strip() + "\n"


def _template_parameters(template: str) -> tuple[str, ...]:
    """Derive the declared parameters from the body itself — never invented."""
    environment = jinja2.sandbox.SandboxedEnvironment()
    return tuple(
        sorted(jinja2.meta.find_undeclared_variables(environment.parse(template)))
    )


def _prompt_registration(
    *,
    tenant: str,
    name: str,
    version: str,
    template: str,
    tolerate_empty_bump: bool = False,
) -> RequestSpec:
    return RequestSpec(
        method="POST",
        path="/config/registrations",
        tolerate_empty_bump=tolerate_empty_bump,
        json={
            "key": f"{tenant}/{PROMPT_ARTIFACT.class_id}/{name}",
            "class_id": PROMPT_ARTIFACT.class_id,
            "artifact": {
                "schema_version": _PROMPT_SCHEMA_VERSION,
                "artifact_version": version,
                "name": name,
                "tenant": tenant,
                "template": template,
                "declared_parameters": list(_template_parameters(template)),
            },
        },
    )


def _build(args: argparse.Namespace) -> tuple[RequestSpec, ...]:
    directory = Path(args.directory)
    frontmatter, body = _split_frontmatter(
        (directory / "SKILL.md").read_text()
    )
    name = str(frontmatter["name"])
    description = str(frontmatter["description"])
    version = args.version or str(frontmatter.get("version", ""))
    if not version:
        raise ValueError(
            "no artifact version: pass --version or declare `version` in"
            " the SKILL.md frontmatter (D-IMPL-26: registration is"
            " exact-version)"
        )

    specs: list[RequestSpec] = [
        _prompt_registration(
            tenant=args.tenant, name=name, version=version, template=body
        )
    ]
    references = directory / "references"
    if references.is_dir():
        for reference in sorted(references.iterdir()):
            if reference.is_file():
                specs.append(
                    _prompt_registration(
                        tenant=args.tenant,
                        name=f"{name}-reference-{reference.stem}",
                        version=version,
                        template=reference.read_text(),
                        # a re-import with this reference unchanged is the
                        # by-design idempotent case, not a failure
                        tolerate_empty_bump=True,
                    )
                )

    prompt_uri = (
        f"ccf-artifact://{args.tenant}/{PROMPT_ARTIFACT.class_id}/"
        f"{name}@{version}"
    )
    specs.append(
        RequestSpec(
            method="POST",
            path="/skill/catalog",
            json={
                "schema_version": _ENTRY_SCHEMA_VERSION,
                "artifact_version": version,
                "name": name,
                "tenant": args.tenant,
                "skill_type": "procedure",
                "description": description,
                "argument_schema": {"properties": {}, "required": []},
                "binding": {
                    "instruction": {
                        "prompt": prompt_uri,
                        "parameters": list(_template_parameters(body)),
                    }
                },
                # allowed-tools is NOT mapped here (D-IMPL-29): only the
                # operator's explicit flags become requirement identifiers
                "requirements": {
                    "required_scopes": list(args.required_scope or ()),
                    "required_context_products": list(
                        args.required_context_product or ()
                    ),
                },
            },
        )
    )
    return tuple(specs)


def register(
    subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """Add the import verb under the skill noun."""
    importer = subparsers.add_parser(
        "import", help="one-way SKILL.md directory import (D-IMPL-56)"
    )
    importer.add_argument("directory", help="directory holding SKILL.md")
    importer.add_argument("--tenant", required=True)
    importer.add_argument(
        "--version", help="artifact version (else frontmatter `version`)"
    )
    importer.add_argument(
        "--required-scope", action="append", default=[]
    )
    importer.add_argument(
        "--required-context-product", action="append", default=[]
    )
    importer.set_defaults(build=_build)
