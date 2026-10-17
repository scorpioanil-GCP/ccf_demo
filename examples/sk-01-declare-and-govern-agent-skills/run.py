# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""Declare an agent's skills, show the record naming them, and show an over-reaching grant refused.

[ADAPT] freely — this file is presentation and verification, and the ONLY module
in this example that writes to a terminal.

Usage::

    export CCF_SK_01_POSTGRES_DSN=...  CCF_SK_01_POSTGRES_SCHEMA=ccf_v2
    export CCF_SK_01_COLLATERAL_URL=http://127.0.0.1:<port>/mcp  CCF_SK_01_COLLATERAL_TOKEN=...
    .venv/bin/python examples/sk-01-declare-and-govern-agent-skills/run.py
    .venv/bin/python examples/sk-01-declare-and-govern-agent-skills/run.py --facility FAC-D3D1A4 --lei B3BS7ACMDUWISF18KY76

The producer is cp-06-canonical's own door
(``examples/cp-06-canonical-collateral-and-setoff-coverage/run.py --door``), which
prints ``READY {port}``; the token is the one that door was started with
(``CCF_CP_06C_DOOR_TOKEN``).

Five movements, in this order:

1. **Skills declared at start** — the product opens; the audit log shows each
   declared grant requested and put in force.
2. **One question** — the decision record names the agent and the skill-set it
   held (dimension 4) and, on the child row, the grant the child was asked
   under (dimension 5); both are held to the audit log.
3. **What a model would see** — the Claude Agent SDK adapter's tool list for this
   agent, with no model call (``tool_surface.py``, finding SK01-F-02). It must
   follow movement 2: the agent cannot be constructed before a question.
4. **Over-reach** — the variant deployment, whose skill also wants a scope the
   regime does not permit, refuses to open; the audit log shows the refusal.
5. **Not yet available** — what this SDK cannot show yet (``artifacts/not-yet-available.yaml``).

Exit 0 when every movement behaves as declared — a governed refusal of the
question included. Exit 1 when the over-reach variant opens, or any record check
in movement 2 prints ``NO``: dimension 4's agent or skill-set, or dimension 5's
child rows — an admitted child row that carries no grant, a grant that is not
the one audited effective at open for the skill the row names, or no row at
all for the class the brief requires.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import deployment
import produce
import tool_surface
import yaml
from ccf.agents.definitions import AGENT_DEFINITION
from ccf.artifacts.protocol import artifact_uri
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.product import DeclaredGrantRefused, OpenedProduct
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.record import CHILD_ADMITTED, ChildResolution
from ccf.replay.serve import ServedProduct
from ccf.skills.grants import SKILL_GRANT, grant_set_hash

HERE = Path(__file__).parent

#: The audit actions that record what happened to a grant: the ``grant_*`` family
#: ``src/ccf/controlplane/audit.py`` documents. ``AuditLog.events()`` takes no
#: filter, so this example filters it itself (FINDINGS.md §E).
GRANT_ACTION_PREFIX = "grant_"


def _short(value: str | None) -> str:
    return "-" if not value else f"{value[:16]}…"


def _yes(value: bool) -> str:
    return "yes" if value else "NO"


def _grant_events(registry: ControlPlaneRegistry) -> list[Any]:
    return [event for event in registry.audit_log.events() if event.action.startswith(GRANT_ACTION_PREFIX)]


def _print_grant_events(registry: ControlPlaneRegistry) -> None:
    for event in _grant_events(registry):
        print(
            f"    audit #{event.sequence:<3} {event.action:<16} {event.key}  grant {_short(event.version)}"
            f"  resolved={event.resolved}  by {event.actor}"
        )


def _skills_line(opened: OpenedProduct) -> None:
    permitted = list(opened.config.policy["skill_governance"]["permitted_scopes"])
    for name in opened.config.grants:
        section: Mapping[str, Any] = opened.config.skills[name]
        needs = list(section["requirements"]["required_scopes"])
        print(f"    skill {name}@{section['artifact_version']} needs {needs}   regime permits {permitted}")


def movement_one(opened: OpenedProduct, registry: ControlPlaneRegistry) -> None:
    agent = opened.agent
    assert agent is not None
    uri = artifact_uri(
        tenant_id=opened.tenant_id, artifact_class=AGENT_DEFINITION.class_id,
        name=agent.name, artifact_version=agent.artifact_version,
    )
    print("1 · SKILLS DECLARED AT START")
    print(f"    agent {agent.name} {list(agent.archetypes)} {_short(content_hash(agent))} {uri}")
    _skills_line(opened)
    _print_grant_events(registry)


def movement_two(opened: OpenedProduct, registry: ControlPlaneRegistry, parsed: argparse.Namespace) -> tuple[bool, datetime]:
    """Ask the one question; print and check what the record says about the agent. Returns (checks held, asked_at)."""
    brief = deployment.QUESTION["brief"]
    asked = opened.question(
        subject=parsed.lei,
        asked_at=datetime.fromisoformat(parsed.asked_at),
        intent=str(brief["intent"]),
        freshness=str(brief["freshness"]),
        parameters={str(brief["facility_parameter"]): parsed.facility},
    )
    outcome = opened.answer(asked)
    record = opened.record_of(outcome)
    print("2 · ONE QUESTION")
    print(f"    {parsed.lei}  {parsed.facility} @ {asked.asked_at.isoformat()}")
    if isinstance(outcome, ServedProduct):
        product = outcome.product
        print(f"    -> SERVED  product {_short(content_hash(product))}  record {_short(outcome.replay_ref.content_address)}")
        for product_class, section in product.payload["sections"].items():
            summary = "  ".join(f"{key}={value}" for key, value in section["summary"].items())
            print(f"    § {product_class}  child={_short(section['child_content_address'])}  {summary}")
    else:
        assert isinstance(outcome, RefusalEnvelope)
        print(f"    -> REFUSED kind={outcome.kind} reason={outcome.reason}")
        print(f"       record {outcome.replay_reference}")

    effective = {event.key: event.version for event in _grant_events(registry) if event.action == "grant_effective"}
    for row in record.content_generation_path.child_resolutions:
        print(
            f"    child row   {row.required_product_class} {row.outcome_status}"
            f"  skill={row.producing_skill_name or '-'}@{row.producing_skill_version or '-'}"
            f"  grant={_short(row.grant_hash)}  producer={row.producer_id or '-'}"
            f"  producer refusal={row.producer_refusal_kind or '-'}/{row.producer_refusal_reason or '-'}"
        )

    d4 = record.perspective_conditioning
    agent = opened.agent
    assert agent is not None
    caller = opened.default_perspective
    print(
        f"    dimension 4 agent {_short(d4.agent_definition_hash)} {d4.agent_definition_uri}"
        f" {list(d4.archetype_composition)}  skill-set {_short(d4.grant_set_hash)}"
        f"  caller {d4.principal_id} / {d4.role}"
    )
    expected_uri = artifact_uri(
        tenant_id=opened.tenant_id, artifact_class=AGENT_DEFINITION.class_id,
        name=agent.name, artifact_version=agent.artifact_version,
    )
    agent_named = (
        d4.agent_definition_hash == content_hash(agent)
        and d4.agent_definition_uri == expected_uri
        and tuple(d4.archetype_composition) == tuple(agent.archetypes)
        and (d4.principal_id, d4.role) == (caller.principal_id, caller.role)
    )
    skill_set = d4.grant_set_hash == grant_set_hash(frozenset(effective.values()))
    print(f"    checks      agent in record = declared agent: {_yes(agent_named)}")
    print(f"                skill-set in record = hash of the grants audited effective at start: {_yes(skill_set)}")
    rows_held = child_rows_held(
        record.content_generation_path.child_resolutions,
        effective=effective,
        tenant=opened.tenant_id,
        grants=tuple(opened.config.grants or ()),
        required_class=deployment.CHILD_CLASS,
        served=isinstance(outcome, ServedProduct),
    )
    return agent_named and skill_set and rows_held, asked.asked_at


def child_rows_held(
    rows: Sequence[ChildResolution],
    *,
    effective: Mapping[str, str],
    tenant: str,
    grants: Sequence[str],
    required_class: str,
    served: bool,
) -> bool:
    """Print and check dimension 5's child rows against the grants audited effective at open.

    ``effective`` maps each grant's Control Plane key to the grant hash the audit
    log recorded ``grant_effective`` for. Each row is joined by the skill it names,
    under that key (``{tenant}/ccf.skill-grant/{name}``), not by membership in
    the set. An ADMITTED row must carry a grant, and that grant must be a declared
    one and the one audited for its skill. A row that was NOT admitted (refused,
    unavailable, …) may carry no grant, and is printed as such. A SERVED brief
    with no admitted row for the class it requires is ``NO``, never a vacuous
    ``yes``. A refused brief may have no row at all: a refusal such as the
    temporal boundary's comes before any child is asked.
    """
    held_all = True
    admitted = any(row.required_product_class == required_class and row.outcome_status == CHILD_ADMITTED for row in rows)
    if served and not admitted:
        print(f"                served with an admitted child row for {required_class}: {_yes(False)}")
        held_all = False
    elif not served and not any(row.required_product_class == required_class for row in rows):
        print(f"                no child row for {required_class}: the question was refused before any child was asked")
    for row in rows:
        if row.grant_hash is None and row.outcome_status != CHILD_ADMITTED:
            print(f"                child row carries no grant ({row.outcome_status}); dimension 4 still names the skill-set")
            continue
        key = f"{tenant}/{SKILL_GRANT.class_id}/{row.producing_skill_name}"
        held = (
            row.grant_hash is not None
            and row.producing_skill_name in grants
            and effective.get(key) == row.grant_hash
        )
        held_all = held_all and held
        label = "admitted child row carries a grant, and it is" if row.outcome_status == CHILD_ADMITTED else "grant on child row ="
        print(f"                {label} the grant audited at start for its skill: {_yes(held)}")
    return held_all


def movement_three(opened: OpenedProduct, *, instant: datetime) -> None:
    surface = tool_surface.tool_surface(opened, instant=instant)
    bound = "  ".join(f"{name} ({kind})" for name, kind in surface.bound.items())
    print("3 · WHAT A MODEL WOULD SEE")
    print(f"    bound: {bound}  ->  model tools: {list(surface.exposed) or 'none'}  allowed_tools={list(surface.allowed_tools)}")
    print(f"    tool-surface types: {sorted(surface.exposable_types)}")
    print("    why: a skill that asks another product is carried out by the product, which checks and admits the answer; it is never a tool the model calls")


def movement_four(scratch: Path) -> bool:
    """Open the over-reach variant. Returns True when it was refused, as declared."""
    registry = ControlPlaneRegistry()
    print("4 · OVER-REACH")
    variant = yaml.safe_load((produce.OVER_REACH / "ccf_config.yaml").read_text(encoding="utf-8"))
    for name, section in variant["skills"].items():
        print(f"    variant skill {name}@{section['artifact_version']} needs {section['requirements']['required_scopes']}"
              f"   regime permits {variant['policy']['skill_governance']['permitted_scopes']}")
    try:
        with produce.product(scratch, control_plane=registry, config_root=produce.OVER_REACH, read_sources=False):
            print("    -> OPENED — the over-reaching grant was put in force. This is a defect.")
            refused = False
    except DeclaredGrantRefused as refusal:
        detail = refusal.refusal
        print(f"    -> REFUSED at open: DeclaredGrantRefused skill={refusal.skill}"
              f" check={getattr(detail, 'check', '-')} excess={sorted(getattr(detail, 'excess_scopes', ()) or ())}")
        print("       nothing opened, nothing can be asked")
        refused = True
    _print_grant_events(registry)
    return refused


def movement_five() -> None:
    document = yaml.safe_load((HERE / "artifacts" / "not-yet-available.yaml").read_text(encoding="utf-8"))
    print("5 · NOT YET AVAILABLE")
    for item in document["declaration"]["items"]:
        recorded = f" (recorded as {item['recorded_as']} in FINDINGS.md)" if "recorded_as" in item else ""
        print(f"    - {item['what']}: {item['status']}{recorded}")


def main(argv: list[str]) -> int:
    demonstration = deployment.QUESTION["demonstration"]
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--lei", default=str(demonstration["subject"]), help="the obligor — the brief's subject")
    parser.add_argument("--facility", default=str(demonstration["facility"]))
    parser.add_argument("--asked-at", default=str(demonstration["asked_at"]), help="ISO instant with offset")
    parsed = parser.parse_args(argv[1:])

    registry = ControlPlaneRegistry()
    with tempfile.TemporaryDirectory(prefix="sk01-") as scratch:
        root = Path(scratch)
        with produce.product(root / "brief", control_plane=registry) as opened:
            movement_one(opened, registry)
            held, asked_at = movement_two(opened, registry, parsed)
            movement_three(opened, instant=asked_at)
        refused = movement_four(root / "over-reach")
    movement_five()
    return 0 if held and refused else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv))
