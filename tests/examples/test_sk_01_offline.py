# Copyright (c) 2026 David Castillo. All rights reserved.
# Use, copying, modification, and distribution of the covered material
# are governed by the CCF SDK Interim Software and Patent License
# in the repository-root LICENSE.md and any controlling signed agreement.
# Rights under that interim license begin only upon its execution
# and are limited to its stated scope and term.
"""sk-01 — declare and govern agent skills: the estate-free gates (O1–O8, and the README/FINDINGS gate).

`examples/sk-01-declare-and-govern-agent-skills`, built under Dave's ruling of
2026-10-16 16:58 MST (option A: *"Build the honest version now"*). This module is
UNMARKED on purpose: a module-level substrate mark would hide these gates from the
quick suite, and none of them needs an estate. Every opening here points the
producer endpoint at a loopback port nothing listens on, and every opening but
O6's passes ``read_sources=False`` so nothing is asked. **O6 is the one
exception**: it opens with sources resolved, to a loopback DSN (``127.0.0.1``,
port 1 — an explicit host, so an exported ``PGHOST`` can never be followed) that
nothing listens on, replaces the example's ``acquisition.resolve`` with a function
that fails the test if called, and asks a question the temporal boundary refuses
before any leg is read. Nothing here reads 192.168.4.76.

What is held:

* **O1 over-reach** — the variant deployment refuses to open,
  :class:`~ccf.products.product.DeclaredGrantRefused`, on the ledger's tier-1
  check, with exactly the scopes the variant needs and the regime does not
  permit (both read from the documents), and the audit log records the request
  and the refusal of ONE grant and no ``grant_effective``.
* **O2 declared at open** — the main tree opens; each declared grant is
  requested and put in force at open, and only declared grants are; the agent
  consumes exactly what the class requires. **O2b** — a ``skills:`` entry that
  ``grants:`` does not name is refused at open (``GrantNotInForce``), and no grant
  event names it.
* **O3 a shipped gap, written to go RED when it is fixed (SK01-F-01)** — a copy
  of the deployment whose skill states a harness-exposable type is refused at
  open by the paved derivation's own words. When the SDK lets an example declare
  a tool-type skill, this test fails, and the README's "not yet possible" is
  then out of date.
* **O4 the variant copy** — equal to the main document but for its ``$schema``
  depth and the one delimited skill block.
* **O5 no machinery outside the glue file** — no module other than
  ``tool_surface.py`` spells a forbidden constructor call, or imports, names or
  reaches ``GrantLedger``, ``SkillCatalog`` or ``AgentFactory`` under any alias
  (an AST check over imports, attributes and names); and ``tool_surface.py``
  really CALLS all three (an AST check on call nodes, not a substring a docstring
  could satisfy) (SK01-F-02). **Not detected:** a string-keyed lookup
  (``getattr``/``importlib``).
* **O6 dimension 4 names the agent, estate-free** — on a question refused for its
  instant, the record names the declared agent (content hash, URI, archetypes) and
  the skill-set of the grants audited effective at open (`D-IMPL-385`).
* **O7 the child-row check in ``run.py``** — an admitted child row that carries no
  grant, a grant that is not the one audited for the row's skill, and a record
  with no row for the required class each fail the check; a non-admitted row
  without a grant is tolerated.
* **O8 a shipped ordering rule, written to go RED when it is fixed (SK01-F-02)** —
  the paved agent cannot be constructed before the first question
  (``AgentDefinitionError``, the unregistered debt-profile reference).
* The README carries the seven template headings and states SK01-F-01 plainly in
  "What this does not show"; its §7.3 bullet names SK01-F-01; every path its
  artifact table lists exists; and FINDINGS.md holds every SK01-F id this
  example cites, each PARKED under Dave's ruling.
"""

from __future__ import annotations

import ast
import pathlib
import re
import shutil
import sys
from collections.abc import Iterator
from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest
import yaml

from ccf.agents.definitions import AGENT_DEFINITION
from ccf.agents.errors import AgentDefinitionError
from ccf.artifacts.protocol import artifact_uri
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.halflife.assessment import DebtFactors
from ccf.products.product import DeclaredGrantRefused, GrantNotInForce
from ccf.products.refusal import RefusalEnvelope
from ccf.replay.record import CHILD_ADMITTED, NO_GRANTS_SET_HASH, ChildResolution
from ccf.skills.grants import SKILL_GRANT, grant_set_hash
from ccf.skills.toolsurface import HARNESS_EXPOSABLE_SKILL_TYPES
from tests.examples.test_cp_readme_template import README_HEADINGS, headings

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "sk-01-declare-and-govern-agent-skills"
VARIANT = EXAMPLE / "variants" / "over-reach"
UNREACHABLE = "http://127.0.0.1:1/mcp"
BLOCK_OPEN = "# >>> SK-01 SKILL DECLARATION"
BLOCK_CLOSE = "# <<< SK-01 SKILL DECLARATION"
EXAMPLE_MODULES = ("acquisition", "deployment", "produce", "projection", "tool_surface", "run")


def _config(root: pathlib.Path) -> dict[str, Any]:
    document: dict[str, Any] = yaml.safe_load((root / "ccf_config.yaml").read_text(encoding="utf-8"))
    return document


def _environ(config: dict[str, Any]) -> dict[str, str]:
    """The producer's endpoint and credential, by the NAMES the document declares — a closed port."""
    environ: dict[str, str] = {}
    for producer in config["producers"].values():
        environ[producer["endpoint_from_env"]] = UNREACHABLE
        environ[producer["credential_from_env"]] = "no-door-is-contacted"
    return environ


@pytest.fixture(scope="module")
def example() -> Iterator[dict[str, Any]]:
    """The example's modules, imported from its own directory."""
    saved = {name: sys.modules.pop(name, None) for name in EXAMPLE_MODULES}
    sys.path.insert(0, str(EXAMPLE))
    try:
        import acquisition  # noqa: PLC0415
        import deployment  # noqa: PLC0415
        import produce as module  # noqa: PLC0415
        import run  # noqa: PLC0415
        import tool_surface  # noqa: PLC0415

        yield {"produce": module, "deployment": deployment, "acquisition": acquisition, "run": run, "tool_surface": tool_surface}
    finally:
        sys.path.remove(str(EXAMPLE))
        for name, original in saved.items():
            sys.modules.pop(name, None)
            if original is not None:
                sys.modules[name] = original


@pytest.fixture(scope="module")
def produce(example: dict[str, Any]) -> Any:
    """The example's ``produce``."""
    return example["produce"]


def _grant_events(registry: ControlPlaneRegistry) -> list[Any]:
    return [event for event in registry.audit_log.events() if event.action.startswith("grant_")]


# --- O1 over-reach --------------------------------------------------------------------


def test_o1_the_over_reaching_grant_is_refused_at_open_and_audited(produce: Any, tmp_path: pathlib.Path) -> None:
    variant = _config(VARIANT)
    regime = set(variant["policy"]["skill_governance"]["permitted_scopes"])
    (name,) = variant["grants"]
    needs = set(variant["skills"][name]["requirements"]["required_scopes"])

    registry = ControlPlaneRegistry()
    with pytest.raises(DeclaredGrantRefused) as raised:
        with produce.product(tmp_path / "scratch", control_plane=registry, config_root=VARIANT,
                             environ=_environ(variant), read_sources=False):
            pytest.fail("the over-reach variant opened")
    assert needs - regime, "the variant must need a scope its regime does not permit, or it proves nothing"
    refusal = raised.value
    assert refusal.skill == name
    assert refusal.refusal is not None
    assert refusal.refusal.check == "tier-1-policy-compatibility"
    assert set(refusal.refusal.excess_scopes) == needs - regime
    # The refusal mechanism's own words — the tier-1 check, not any other guard.
    assert "declares requirements the agent's envelope does not cover" in str(refusal), str(refusal)

    events = _grant_events(registry)
    assert [event.action for event in events] == ["grant_requested", "grant_refused"], events
    requested, refused = events
    assert requested.version == refused.version, "one grant, requested and refused"
    assert requested.resolved is True and refused.resolved is False
    assert requested.key.endswith(f"/{name}") and refused.key == requested.key


# --- O2 declared at open ----------------------------------------------------------------


def test_o2_each_declared_grant_is_requested_and_put_in_force_at_open(produce: Any, tmp_path: pathlib.Path) -> None:
    config = _config(EXAMPLE)
    registry = ControlPlaneRegistry()
    with produce.product(tmp_path / "scratch", control_plane=registry, environ=_environ(config), read_sources=False) as opened:
        assert opened.agent is not None and opened.agent.name == config["agent"]["name"]
        assert tuple(opened.config.grants) == tuple(config["grants"])
        consumed = [contract.product_class for contract in opened.agent.context_contract.consumes]
        assert consumed == [requirement["product_class"] for requirement in config["product_class"]["requires"]]
    events = _grant_events(registry)
    assert not [event for event in events if event.action in ("grant_refused", "grant_revoked")], events
    for name in config["grants"]:
        mine = [event for event in events if event.key.endswith(f"/{name}")]
        assert [event.action for event in mine] == ["grant_requested", "grant_effective"], mine
        assert mine[0].version == mine[1].version and all(event.resolved for event in mine)
    # Only declared grants were requested or put in force (key = {tenant}/ccf.skill-grant/{name},
    # src/ccf/skills/grants.py::skill_grant_key). Vacuous on this one-skill tree; O2b is the gate that bites.
    assert {event.key.rsplit("/", 1)[1] for event in events} == set(config["grants"]), events


UNDECLARED = """  collateral-ask-undeclared:
    schema_version: "1.0.0"
    artifact_version: "1.0.0"
    description: a second skill the deployment declares and does not grant
    produces: credit-risk.collateral-coverage
    requirements:
      required_scopes: [collateral-coverage.read]
      required_context_products: []
"""


def test_o2b_a_declared_skill_that_grants_does_not_name_is_refused_at_open(produce: Any, tmp_path: pathlib.Path) -> None:
    """The SDK grants only what ``grants:`` names: an extra ``skills:`` entry refuses the open, by name."""
    root = tmp_path / "deployment"
    root.mkdir()
    shutil.copyfile(EXAMPLE / "ccf_environment.yaml", root / "ccf_environment.yaml")
    text = (EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8")
    assert text.count(BLOCK_CLOSE) == 1
    (root / "ccf_config.yaml").write_text(text.replace(BLOCK_CLOSE, UNDECLARED + BLOCK_CLOSE), encoding="utf-8")
    config = _config(root)
    extra = sorted(set(config["skills"]) - set(config["grants"]))
    assert extra == ["collateral-ask-undeclared"], extra

    registry = ControlPlaneRegistry()
    with pytest.raises(GrantNotInForce) as raised:
        with produce.product(tmp_path / "scratch", control_plane=registry, config_root=root,
                             environ=_environ(config), read_sources=False):
            pytest.fail("a skill declared under `skills:` and absent from `grants:` was put in force")
    assert not isinstance(raised.value, DeclaredGrantRefused), "the declared grants are compatible; this is the undeclared one"
    message = str(raised.value)
    assert f"skill(s) {extra!r} declared in `skills:` are not granted to agent" in message, message
    assert not [event for event in _grant_events(registry) if event.key.endswith("/collateral-ask-undeclared")]


# --- O3 the shipped gap, written to go red when fixed ----------------------------------------


def _with_stated_skill_type(root: pathlib.Path, skill_type: str) -> pathlib.Path:
    """A copy of the deployment's two documents whose one skill STATES ``skill_type``."""
    root.mkdir(parents=True)
    shutil.copyfile(EXAMPLE / "ccf_environment.yaml", root / "ccf_environment.yaml")
    text = (EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8")
    anchor = '    artifact_version: "1.0.0"\n    description: asks the registered collateral producer'
    assert text.count(anchor) == 1, "the skill block moved; re-anchor this copy"
    head, block = text.split(BLOCK_OPEN, 1)
    assert anchor in block
    block = block.replace(anchor, anchor.replace("    description:", f"    skill_type: {skill_type}\n    description:", 1), 1)
    (root / "ccf_config.yaml").write_text(head + BLOCK_OPEN + block, encoding="utf-8")
    assert _config(root)["skills"]["collateral-ask"]["skill_type"] == skill_type
    return root


@pytest.mark.parametrize("skill_type", sorted(HARNESS_EXPOSABLE_SKILL_TYPES))
def test_o3_a_harness_exposable_skill_cannot_be_declared_on_the_paved_road(
    produce: Any, tmp_path: pathlib.Path, skill_type: str
) -> None:
    """SK01-F-01, asserted as SHIPPED. Goes red when the SDK lets an example declare a tool-type skill.

    Every type in ``HARNESS_EXPOSABLE_SKILL_TYPES`` — the only types that ever
    appear as model tools — is refused at open by the paved derivation, by its
    own words (`D-IMPL-343` R-7), and the refusal is not the grant ledger's.
    """
    root = _with_stated_skill_type(tmp_path / "deployment", skill_type)
    registry = ControlPlaneRegistry()
    # PermissionError too, so a grant-side refusal (GrantNotInForce and its
    # DeclaredGrantRefused) is CAUGHT and fails the assertion below, rather than
    # escaping the block as an error.
    with pytest.raises((ValueError, PermissionError)) as raised:
        with produce.product(tmp_path / "scratch", control_plane=registry, config_root=root,
                             environ=_environ(_config(root)), read_sources=False):
            pytest.fail(f"a skill stating skill_type={skill_type!r} opened — SK01-F-01 may be fixed; update the README")
    assert isinstance(raised.value, ValueError) and not isinstance(raised.value, GrantNotInForce), type(raised.value)
    message = str(raised.value)
    assert f"states skill_type='{skill_type}' and the paved road derives 'mcp_product'" in message, message
    assert "D-IMPL-343 R-7" in message, message
    assert not _grant_events(registry), "refused before any grant was requested"


# --- O4 the variant copy ------------------------------------------------------------------


def _split(text: str) -> tuple[str, str]:
    assert text.count(BLOCK_OPEN) == 1 and text.count(BLOCK_CLOSE) == 1, "exactly one delimited block"
    head, rest = text.split(BLOCK_OPEN, 1)
    block, tail = rest.split(BLOCK_CLOSE, 1)
    assert not tail.strip(), "nothing may follow the skill block"
    return head, block


def test_o4_the_variant_is_the_deployment_but_for_the_skill_block() -> None:
    assert sorted(path.name for path in VARIANT.iterdir()) == ["ccf_config.yaml", "ccf_environment.yaml"]
    assert (VARIANT / "ccf_environment.yaml").read_bytes() == (EXAMPLE / "ccf_environment.yaml").read_bytes()
    main_head, main_block = _split((EXAMPLE / "ccf_config.yaml").read_text(encoding="utf-8"))
    variant_head, variant_block = _split((VARIANT / "ccf_config.yaml").read_text(encoding="utf-8"))
    main_first, main_rest = main_head.split("\n", 1)
    variant_first, variant_rest = variant_head.split("\n", 1)
    assert variant_rest == main_rest, "the variant drifted from the deployment outside its skill block"
    # The one header line differs only in depth: both resolve to the same schema file.
    prefix = "# yaml-language-server: $schema="
    main_schema = (EXAMPLE / main_first.removeprefix(prefix)).resolve()
    variant_schema = (VARIANT / variant_first.removeprefix(prefix)).resolve()
    assert main_schema == variant_schema and main_schema.is_file()

    main_skills = yaml.safe_load(main_block)["skills"]
    variant_skills = yaml.safe_load(variant_block)["skills"]
    assert sorted(main_skills) == sorted(variant_skills)
    for name, section in main_skills.items():
        changed = variant_skills[name]
        assert changed["artifact_version"] != section["artifact_version"], "a refused grant needs its own version (SK01-F-03)"
        main_scopes = set(section["requirements"]["required_scopes"])
        variant_scopes = set(changed["requirements"]["required_scopes"])
        assert main_scopes < variant_scopes, "the variant must need strictly more than the deployment"
        assert {k: v for k, v in changed.items() if k not in ("artifact_version", "requirements")} == {
            k: v for k, v in section.items() if k not in ("artifact_version", "requirements")
        }


# --- O5 no machinery outside the glue file ---------------------------------------------------

#: What an example must never construct or reach for outside the one glue file.
FORBIDDEN = (
    "GrantLedger(", "SkillCatalog(", "SkillGrant(", "AgentDefinition(", "AgentFactory(", "Authorized(",
    "McpSkillRegistry", "QuestionBoundChildResolver", "CompositeAdmissionGate", "mint_at_composition",
    "register_manifest_entries",
)
#: The glue file, and the three constructions it alone may hold.
GLUE = "tool_surface.py"
GLUE_ONLY = ("GrantLedger(", "SkillCatalog(", "AgentFactory(")
_MINT_CALL = re.compile(r"\bmint\w*\s*\(")


def _imports(path: pathlib.Path) -> list[str]:
    names: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


#: The three names only the glue file may reach, under any alias.
GLUE_NAMES = frozenset(token.rstrip("(") for token in GLUE_ONLY)


def _names_reached(tree: ast.AST) -> list[str]:
    """Every GLUE_NAMES member a module imports, names or reaches as an attribute."""
    reached: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            reached.extend(alias.name for alias in node.names if alias.name in GLUE_NAMES)
        elif isinstance(node, ast.Attribute) and node.attr in GLUE_NAMES:
            reached.append(node.attr)
        elif isinstance(node, ast.Name) and node.id in GLUE_NAMES:
            reached.append(node.id)
    return reached


def _calls(tree: ast.AST) -> set[str]:
    """The plain names a module CALLS (``Name(...)``) — docstrings and comments cannot satisfy this."""
    return {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}


def test_o5_no_sdk_machinery_outside_the_glue_file() -> None:
    modules = sorted(path.name for path in EXAMPLE.glob("*.py"))
    assert modules == sorted(f"{name}.py" for name in EXAMPLE_MODULES), modules
    for module in modules:
        path = EXAMPLE / module
        text = path.read_text(encoding="utf-8")
        allowed = GLUE_ONLY if module == GLUE else ()
        for token in FORBIDDEN:
            if token not in allowed:
                assert token not in text, f"{module} holds {token}"
        assert not _MINT_CALL.search(text), f"{module} calls a mint"
        assert not [name for name in _imports(path) if name == "tests" or name.startswith("tests.")], f"{module} imports test code"
        if module != GLUE:
            reached = _names_reached(ast.parse(text))
            assert not reached, f"{module} reaches {reached}: only {GLUE} may (SK01-F-02)"
    glue_calls = _calls(ast.parse((EXAMPLE / GLUE).read_text(encoding="utf-8")))
    for name in sorted(GLUE_NAMES):
        assert name in glue_calls, f"the glue file no longer calls {name}(: re-read SK01-F-02 before deleting this check"
    # No model name in code: the adapter's placeholder lives in the artifact alone.
    model = yaml.safe_load((EXAMPLE / "artifacts" / "harness.yaml").read_text(encoding="utf-8"))["declaration"]["model"]
    for module in modules:
        constants = [
            node.value for node in ast.walk(ast.parse((EXAMPLE / module).read_text(encoding="utf-8")))
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]
        assert model not in constants, f"{module} spells the harness model value"


# --- the README ----------------------------------------------------------------------------


_FINDING_ID = re.compile(r"\bSK01-F-\d\d\b")
#: Internal shorthand a bank reader cannot follow: a bare gap number or a TP id.
_SHORTHAND = re.compile(r"\bgap \d\b|\bTP-\d\d\b")


def test_the_readme_carries_the_seven_template_headings_and_states_sk01_f01() -> None:
    """The template gate globs ``cp-*`` only; this example follows it voluntarily and is held to it here."""
    readme = EXAMPLE / "README.md"
    assert headings(readme) == README_HEADINGS
    text = readme.read_text(encoding="utf-8")
    demonstrates = text.split("## What this demonstrates", 1)[1].split("\n## ", 1)[0]
    assert "### What this does not show" in demonstrates
    does_not_show = demonstrates.split("### What this does not show", 1)[1]
    assert re.search(r"\bnot yet possible \(SK01-F-01\)", does_not_show), "the 'does not show' subsection no longer states SK01-F-01 as 'not yet possible'"
    assert "> **Illustrative calibration:**" in text
    assert not (EXAMPLE / "page").exists() and not (EXAMPLE / "summary_explanations.md").exists(), "README only (Dave, 2026-10-16)"
    # The §7.3 bullet says the seam is CALLED, not demonstrated, and names the finding that says why.
    sections = text.split("## Whitepaper / CLAUDE.md sections exercised", 1)[1].split("\n## ", 1)[0]
    (seam,) = [bullet for bullet in sections.split("\n- ") if bullet.startswith("**CLAUDE.md §7.3**")]
    assert "SK01-F-01" in seam and "not demonstrated" in seam, seam
    assert not _SHORTHAND.search(text), _SHORTHAND.findall(text)


def test_movement_five_prints_each_item_in_plain_words(
    example: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    """Movement 5 prints one line per item, each item's own words, and no internal id."""
    items = yaml.safe_load((EXAMPLE / "artifacts" / "not-yet-available.yaml").read_text(encoding="utf-8"))
    items = items["declaration"]["items"]
    example["run"].movement_five()
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "5 · NOT YET AVAILABLE", lines
    assert len(lines) == 1 + len(items), lines
    for line, item in zip(lines[1:], items):
        assert item["what"] in line and item["status"] in line, (line, item)
        assert ("recorded_as" in item) == ("recorded as SK01-F-" in line), (line, item)
    assert not re.search(r"\[|\bgap \d\b|\bTP-\d\d\b", "\n".join(lines[1:])), lines


def test_every_listed_artifact_exists_and_findings_holds_every_cited_id() -> None:
    """The artifact table's paths exist, and FINDINGS.md records every SK01-F id the example cites, PARKED.

    The citation lint skips paths it cannot resolve, so a dangling FINDINGS.md
    reference was invisible to every gate until this one.
    """
    text = (EXAMPLE / "README.md").read_text(encoding="utf-8")
    table = text.split("## Artifact-by-artifact", 1)[1].split("\n## ", 1)[0]
    listed = re.findall(r"^\| `([^`]+)` \|", table, re.MULTILINE)
    assert "FINDINGS.md" in listed and len(listed) >= 10, listed
    missing = [path for path in listed if not (EXAMPLE / path).exists()]
    assert not missing, f"the README's artifact table lists paths that do not exist: {missing}"

    findings = (EXAMPLE / "FINDINGS.md").read_text(encoding="utf-8")
    assert "Dave, 2026-10-16 16:58" in findings
    cited: set[str] = set()
    for path in sorted(EXAMPLE.rglob("*")):
        if path.is_file() and path.suffix in (".md", ".py", ".yaml"):
            cited.update(_FINDING_ID.findall(path.read_text(encoding="utf-8")))
    for path in (pathlib.Path(__file__), pathlib.Path(__file__).with_name("test_sk_01_estate.py")):
        cited.update(_FINDING_ID.findall(path.read_text(encoding="utf-8")))
    nya = yaml.safe_load((EXAMPLE / "artifacts" / "not-yet-available.yaml").read_text(encoding="utf-8"))
    items = nya["declaration"]["items"]
    assert items and all(item["what"] and item["status"] for item in items), items
    recorded = [item["recorded_as"] for item in items if "recorded_as" in item]
    assert recorded and all(_FINDING_ID.fullmatch(value) for value in recorded), recorded
    assert set(recorded) <= cited  # and each is held to a PARKED FINDINGS.md entry below
    for item in items:  # movement 5 prints these words verbatim to a bank reader
        assert not _SHORTHAND.search(f"{item['what']} {item['status']}"), item
    assert cited >= {f"SK01-F-0{n}" for n in range(1, 6)}, sorted(cited)
    for finding in sorted(cited):
        heading = re.search(rf"^## {finding}\b.*$", findings, re.MULTILINE)
        assert heading, f"FINDINGS.md has no `## {finding}` entry, and the example cites it"
        body = findings[heading.end():].split("\n## ", 1)[0]
        assert "PARKED" in body, f"{finding} is not marked PARKED"


# --- O6 dimension 4 names the agent, estate-free -----------------------------------------

#: Outside the declared one-hour temporal boundary: refused before any leg is read.
OUTSIDE_THE_BOUNDARY = "2026-09-07T10:00:00+00:00"


def test_o6_a_refused_decision_names_the_declared_agent_and_its_audited_skill_set(
    example: dict[str, Any], tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`D-IMPL-385` bound by THIS example, with no estate: dimension 4 names who decided and what they held.

    The one opening here that resolves sources: to a loopback DSN nothing
    listens on, with the identity leg replaced by a function that fails the test
    if called. The question is refused for its instant before any leg is read,
    and the refusal's record still names the agent and the skill-set.
    """
    produce, deployment = example["produce"], example["deployment"]

    def no_leg_is_read(*args: object, **kwargs: object) -> None:
        pytest.fail("the identity leg was read; O6 must contact nothing")

    monkeypatch.setattr(example["acquisition"], "resolve", no_leg_is_read)
    config = _config(EXAMPLE)
    environ = _environ(config) | {
        "CCF_SK_01_POSTGRES_DSN": "host=127.0.0.1 port=1 dbname=never-used",
        "CCF_SK_01_POSTGRES_SCHEMA": "ccf_v2",
    }
    question = deployment.QUESTION
    registry = ControlPlaneRegistry()
    with produce.product(tmp_path / "scratch", control_plane=registry, environ=environ) as opened:
        outcome = opened.answer(opened.question(
            subject=str(question["demonstration"]["subject"]),
            asked_at=datetime.fromisoformat(OUTSIDE_THE_BOUNDARY),
            intent=str(question["brief"]["intent"]),
            freshness=str(question["brief"]["freshness"]),
            parameters={str(question["brief"]["facility_parameter"]): str(question["demonstration"]["facility"])},
        ))
        assert isinstance(outcome, RefusalEnvelope), outcome
        assert outcome.reason == "asked-at-outside-temporal-bound", (outcome.kind, outcome.reason)
        record = opened.record_of(outcome)
        agent = opened.agent
        assert agent is not None
        caller = opened.default_perspective
        tenant = opened.tenant_id
    d4 = record.perspective_conditioning
    assert d4.agent_definition_hash == content_hash(agent), "dimension 4 does not name the declared agent"
    assert d4.agent_definition_uri == artifact_uri(
        tenant_id=tenant, artifact_class=AGENT_DEFINITION.class_id, name=agent.name, artifact_version=agent.artifact_version,
    )
    assert tuple(d4.archetype_composition) == tuple(agent.archetypes)
    effective = frozenset(event.version for event in _grant_events(registry) if event.action == "grant_effective")
    assert effective, "no grant was put in force at open"
    assert d4.grant_set_hash != NO_GRANTS_SET_HASH, "dimension 4 claims no grants while one is in force"
    assert d4.grant_set_hash == grant_set_hash(effective)
    # The caller's own viewpoint, unchanged — true with or without an agent, so it does not discriminate.
    assert (d4.principal_id, d4.role) == (caller.principal_id, caller.role)


# --- O7 run.py's child-row check -----------------------------------------------------------


def _admitted(*, grant_hash: str | None, skill: str | None, required_class: str) -> ChildResolution:
    return ChildResolution(
        required_product_class=required_class, required=True, outcome_status=CHILD_ADMITTED,
        producing_skill_name=skill, producing_skill_version="1.0.0" if skill else None, grant_hash=grant_hash,
        child_content_address="0" * 64, child_schema_name=required_class, child_schema_version="1.0.0",
        child_asked_at=datetime.fromisoformat("2026-09-07T12:00:00+00:00"), child_debt=Decimal("0.1"),
        child_debt_factors=DebtFactors(freshness=Decimal("0.9"), completeness=Decimal(1), semantic_consistency=Decimal(1)),
        eligibility_basis="provider-controls",
    )


def test_o7_the_child_row_check_refuses_an_admitted_row_without_its_grant(example: dict[str, Any]) -> None:
    """``run.child_rows_held``: an admitted row must carry the grant audited for its skill; a refused one may carry none.

    A served brief must carry an admitted row for the class it requires; a refused
    one may carry no row at all (the temporal boundary refuses before any child is
    asked — measured live 2026-10-16, ``--asked-at`` outside the boundary).
    """
    run, deployment = example["run"], example["deployment"]
    config = _config(EXAMPLE)
    (skill,) = config["grants"]
    tenant = config["tenant_id"]
    required = deployment.CHILD_CLASS
    grant = "a" * 64
    effective = {f"{tenant}/{SKILL_GRANT.class_id}/{skill}": grant}

    def held(rows: list[ChildResolution], *, served: bool = True) -> bool:
        result: bool = run.child_rows_held(
            rows, effective=effective, tenant=tenant, grants=(skill,), required_class=required, served=served,
        )
        return result

    assert held([_admitted(grant_hash=grant, skill=skill, required_class=required)]) is True
    assert held([_admitted(grant_hash=None, skill=None, required_class=required)]) is False, "an admitted row without a grant passed"
    assert held([_admitted(grant_hash="b" * 64, skill=skill, required_class=required)]) is False, "a grant not audited for the skill passed"
    assert held([]) is False, "a served record with no row for the required class passed"
    unavailable = ChildResolution(required_product_class=required, required=True, outcome_status="producer-unavailable")
    assert held([unavailable]) is False, "a served record whose only row was not admitted passed"
    assert held([unavailable], served=False) is True, "a refused row that was not admitted may carry no grant"
    assert held([], served=False) is True, "a refusal before any child was asked has no row, and that is correct"


# --- O8 a shipped ordering rule, written to go red when fixed -----------------------------


def test_o8_the_paved_agent_cannot_be_constructed_before_the_first_question(
    example: dict[str, Any], tmp_path: pathlib.Path
) -> None:
    """SK01-F-02, asserted as SHIPPED. Goes red when the paved agent can be built straight after open.

    Before the first question the agent's pinned debt-profile reference resolves
    to nothing the Control Plane has registered, so the factory refuses. Nothing
    on the public surface states this ordering; movement 3 follows movement 2 for
    this reason.
    """
    produce, tool_surface = example["produce"], example["tool_surface"]
    config = _config(EXAMPLE)
    with produce.product(tmp_path / "scratch", control_plane=ControlPlaneRegistry(), environ=_environ(config), read_sources=False) as opened:
        with pytest.raises(AgentDefinitionError) as raised:
            tool_surface.tool_surface(opened, instant=datetime.fromisoformat("2026-09-07T12:00:00+00:00"))
    message = str(raised.value)
    assert "ccf.debt-profile" in message and "resolves to nothing the Control Plane has registered" in message, message
