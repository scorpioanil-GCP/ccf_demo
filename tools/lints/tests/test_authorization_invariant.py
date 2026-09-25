"""Unit tests for the authorization-invariant checker (D-IMPL-353 §4).

Six rules, each with a violating fixture, a clean twin, and a severing
control — a rule whose severing reddens nothing is vacuous, so every rule here
is proven by being switched off and watched to go quiet while its neighbors
keep reporting. Then the two acceptance runs the design names: **fork-point
red** (the lint reports ``create_app``'s ``auth=None, authorizer=None`` at
``d895d889``, D-IMPL-73's own signature) and the **seam roster** (every finding
at HEAD is one of the named reds still owed by another lane — an exact set, so
a new red and a stale entry both fail with a name).
"""

from __future__ import annotations

import pathlib
import subprocess

import pytest

from tools.lints import authorization_invariant as mod
from tools.lints.authorization_invariant import (
    RULE_DEFAULT,
    RULE_MINT_SITE,
    RULE_RAW_REGISTRATION,
    RULE_TYPE_IGNORE,
    RULE_UNGUARDED_ROUTE,
    RULE_WEAK_TYPE,
    check_source,
)
from tools.lints.__main__ import CHECKERS, RULE_TREE_SCOPE, build_parser, run

REPO = pathlib.Path(__file__).resolve().parents[3]

#: The commit D-IMPL-353 forked from — the tree in which ``create_app`` still
#: read ``auth: HttpAuthProtocol | None = None, authorizer:
#: TenantAuthorizerProtocol | None = None``. The lint's acceptance test.
FORK_POINT = "d895d889"

RUNTIME = pathlib.Path("runtime/ccf_runtime/http_api/app.py")
SRC = pathlib.Path("src/ccf/controlplane/registry.py")
ROUTES = pathlib.Path("runtime/ccf_runtime/http_api/routes/hitl.py")
#: The DEFINER of the capability (D-29 moved it into ``src/`` so library
#: handles can require it without importing ``runtime/``).
CAPABILITY = pathlib.Path("src/ccf/authz/capability.py")
#: The runtime re-export shim: an allowed IMPORTER, never an allowed MINTER.
SHIM = pathlib.Path("runtime/ccf_runtime/authz/capability.py")
TENANCY = pathlib.Path("runtime/ccf_runtime/mcp/tenancy.py")
GATE = pathlib.Path("runtime/ccf_runtime/http_api/gate.py")
BOOT = pathlib.Path("src/ccf/boot.py")
DEPLOYMENT = pathlib.Path("src/ccf/deployment/config.py")

RUNTIME_MOD = "ccf_runtime.http_api.app"
SRC_MOD = "ccf.controlplane.registry"
ROUTES_MOD = "ccf_runtime.http_api.routes.hitl"
CAPABILITY_MOD = "ccf.authz.capability"
SHIM_MOD = "ccf_runtime.authz.capability"
TENANCY_MOD = "ccf_runtime.mcp.tenancy"
GATE_MOD = "ccf_runtime.http_api.gate"
BOOT_MOD = "ccf.boot"
DEPLOYMENT_MOD = "ccf.deployment.config"


def _rules(findings: list[str]) -> list[str]:
    return [f.split()[1] for f in findings]


def _lines(findings: list[str]) -> list[int]:
    return [int(f.split(" ", 1)[0].rsplit(":", 1)[1]) for f in findings]


# =============================================================================
# Rule 1 — an authority-typed parameter carries a default
# =============================================================================

DEFAULT_NONE = (
    "from ccf_runtime.http_api.auth import HttpAuthProtocol\n"
    "def create_app(deps, *, auth: HttpAuthProtocol | None = None):\n"
    "    return deps\n"
)


def test_rule1_a_none_default_on_an_authority_parameter_is_flagged() -> None:
    findings = check_source(DEFAULT_NONE, RUNTIME, RUNTIME_MOD)
    assert RULE_DEFAULT in _rules(findings)
    default = [f for f in findings if RULE_DEFAULT in f][0]
    assert "'auth'" in default and "create_app" in default
    assert default.startswith(f"{RUNTIME}:2 ")


def test_rule1_a_non_none_default_is_flagged_too() -> None:
    source = (
        "from ccf_runtime.authz.protocol import TenantAuthorizerProtocol\n"
        "DEFAULT = object()\n"
        "def f(authorizer: TenantAuthorizerProtocol = DEFAULT): ...\n"
    )
    assert RULE_DEFAULT in _rules(check_source(source, RUNTIME, RUNTIME_MOD))


def test_rule1_a_positional_default_is_flagged() -> None:
    source = (
        "from ccf_runtime.mcp.auth import TokenSourceProtocol\n"
        "def f(a, token_source: TokenSourceProtocol = None): ...\n"
    )
    assert RULE_DEFAULT in _rules(check_source(source, RUNTIME, RUNTIME_MOD))


def test_rule1_a_subscripted_authorized_with_a_default_is_flagged() -> None:
    source = (
        "from ccf_runtime.authz.capability import Authorized, ArtifactWrite\n"
        "def put(self, authorized: Authorized[ArtifactWrite] = None, artifact=None): ...\n"
    )
    assert RULE_DEFAULT in _rules(check_source(source, SRC, SRC_MOD))


def test_rule1_a_quoted_forward_reference_is_read() -> None:
    source = 'def f(*, auth: "HttpAuthProtocol | None" = None): ...\n'
    assert RULE_DEFAULT in _rules(check_source(source, RUNTIME, RUNTIME_MOD))


def test_rule1_an_import_alias_does_not_hide_the_type() -> None:
    source = (
        "from ccf_runtime.authz.capability import Authorized as Cap\n"
        "def f(cap: Cap = None): ...\n"
    )
    assert RULE_DEFAULT in _rules(check_source(source, SRC, SRC_MOD))


def test_rule1_a_qualified_annotation_is_read() -> None:
    source = (
        "from ccf_runtime.authz import capability\n"
        "def f(x: capability.Authorized = None): ...\n"
    )
    assert RULE_DEFAULT in _rules(check_source(source, SRC, SRC_MOD))


def test_rule1_an_unannotated_parameter_named_for_authority_with_a_default() -> None:
    source = "def f(deps, authorizer=None): ...\n"
    assert RULE_DEFAULT in _rules(check_source(source, RUNTIME, RUNTIME_MOD))


def test_rule1_a_dataclass_field_default_is_flagged() -> None:
    source = (
        "from dataclasses import dataclass\n"
        "from ccf_runtime.authz.protocol import TenantAuthorizerProtocol\n"
        "@dataclass\n"
        "class Deps:\n"
        "    authorizer: TenantAuthorizerProtocol | None = None\n"
    )
    findings = check_source(source, RUNTIME, RUNTIME_MOD)
    assert RULE_DEFAULT in _rules(findings)
    assert "Deps" in [f for f in findings if RULE_DEFAULT in f][0]


def test_rule1_a_lambda_default_is_flagged() -> None:
    source = "handler = lambda request, authorizer=None: request\n"
    assert RULE_DEFAULT in _rules(check_source(source, RUNTIME, RUNTIME_MOD))


def test_rule1_a_kwonly_default_on_a_method_is_flagged_by_method_name() -> None:
    source = (
        "from ccf_runtime.mcp.auth import TokenSourceProtocol\n"
        "class Auth:\n"
        "    def __init__(self, *, token_source: TokenSourceProtocol | None = None): ...\n"
    )
    findings = check_source(source, RUNTIME, RUNTIME_MOD)
    assert RULE_DEFAULT in _rules(findings)
    assert "Auth.__init__" in [f for f in findings if RULE_DEFAULT in f][0]


# --- rule 1 clean twins ------------------------------------------------------


def test_rule1_a_required_authority_parameter_is_clean() -> None:
    source = (
        "from ccf_runtime.http_api.auth import HttpAuthProtocol\n"
        "from ccf_runtime.authz.protocol import TenantAuthorizerProtocol\n"
        "def create_app(deps, *, auth: HttpAuthProtocol,"
        " authorizer: TenantAuthorizerProtocol): ...\n"
    )
    assert check_source(source, RUNTIME, RUNTIME_MOD) == []


def test_rule1_a_required_kinded_capability_is_clean() -> None:
    source = (
        "from ccf_runtime.authz.capability import Authorized, ArtifactWrite\n"
        "def put(self, authorized: Authorized[ArtifactWrite], artifact): ...\n"
    )
    assert check_source(source, SRC, SRC_MOD) == []


def test_rule1_a_defaulted_parameter_of_another_type_is_clean() -> None:
    source = "def f(deps, *, perspective_resolver: object | None = None): ...\n"
    assert check_source(source, RUNTIME, RUNTIME_MOD) == []


def test_rule1_a_name_that_merely_starts_like_an_authority_name_is_clean() -> None:
    # `author` is not `authorizer`; the name arm matches exactly.
    source = "def f(author=None, auth_header: str | None = None): ...\n"
    assert check_source(source, RUNTIME, RUNTIME_MOD) == []


# =============================================================================
# Rule 2 — an authority parameter with a type that admits absence
# =============================================================================


def test_rule2_a_none_union_without_a_default_is_flagged() -> None:
    source = (
        "from ccf_runtime.authz.protocol import TenantAuthorizerProtocol\n"
        "def f(authorizer: TenantAuthorizerProtocol | None): ...\n"
    )
    findings = check_source(source, RUNTIME, RUNTIME_MOD)
    assert _rules(findings) == [RULE_WEAK_TYPE]


def test_rule2_optional_is_a_none_union() -> None:
    source = (
        "from typing import Optional\n"
        "from mcp.server.auth.provider import TokenVerifier\n"
        "def f(token_verifier: Optional[TokenVerifier]): ...\n"
    )
    assert _rules(check_source(source, RUNTIME, RUNTIME_MOD)) == [RULE_WEAK_TYPE]


def test_rule2_union_with_none_is_a_none_union() -> None:
    source = (
        "from typing import Union\n"
        "from ccf_runtime.authz.capability import Authorized, Resume\n"
        "def f(authorized: Union[Authorized[Resume], None]): ...\n"
    )
    assert _rules(check_source(source, SRC, SRC_MOD)) == [RULE_WEAK_TYPE]


def test_rule2_object_on_an_authority_name_is_flagged() -> None:
    source = "def put(self, authorized: object, artifact): ...\n"
    assert _rules(check_source(source, SRC, SRC_MOD)) == [RULE_WEAK_TYPE]


def test_rule2_any_on_an_authority_name_is_flagged() -> None:
    source = "from typing import Any\ndef f(*, auth: Any): ...\n"
    assert _rules(check_source(source, RUNTIME, RUNTIME_MOD)) == [RULE_WEAK_TYPE]


def test_rule2_an_unannotated_authority_name_is_flagged() -> None:
    source = "def f(token_source): ...\n"
    assert _rules(check_source(source, RUNTIME, RUNTIME_MOD)) == [RULE_WEAK_TYPE]


def test_rule2_a_bare_authorized_is_a_kindless_wand() -> None:
    source = (
        "from ccf_runtime.authz.capability import Authorized\n"
        "def f(authorized: Authorized): ...\n"
    )
    assert _rules(check_source(source, SRC, SRC_MOD)) == [RULE_WEAK_TYPE]


def test_rule2_authorized_of_any_or_of_the_marker_base_is_a_wand() -> None:
    source = (
        "from typing import Any\n"
        "from ccf_runtime.authz.capability import ActionKind, Authorized\n"
        "def f(authorized: Authorized[Any]): ...\n"
        "def g(authorized: Authorized[ActionKind]): ...\n"
    )
    assert _rules(check_source(source, SRC, SRC_MOD)) == [RULE_WEAK_TYPE, RULE_WEAK_TYPE]


def test_rule2_a_none_default_reports_both_rules_because_both_defects_stand() -> None:
    """Removing the default leaves the union; removing the union leaves the
    default. Two findings, two repairs."""
    findings = check_source(DEFAULT_NONE, RUNTIME, RUNTIME_MOD)
    assert sorted(_rules(findings)) == sorted([RULE_DEFAULT, RULE_WEAK_TYPE])


def test_rule2_a_dataclass_field_admitting_none_is_flagged() -> None:
    source = (
        "from ccf_runtime.http_api.auth import HttpAuthProtocol\n"
        "class Deps:\n"
        "    auth: HttpAuthProtocol | None\n"
    )
    assert _rules(check_source(source, RUNTIME, RUNTIME_MOD)) == [RULE_WEAK_TYPE]


# --- rule 2 clean twins ------------------------------------------------------


def test_rule2_verify_in_the_capability_module_is_typed_object_by_design() -> None:
    source = "def verify(authorized: object, *, kind, resource: str) -> None: ...\n"
    assert check_source(source, CAPABILITY, CAPABILITY_MOD) == []


def test_rule2_a_typevar_kinded_capability_is_clean() -> None:
    source = (
        "from typing import TypeVar\n"
        "from ccf_runtime.authz.capability import ActionKind, Authorized\n"
        'A = TypeVar("A", bound=ActionKind)\n'
        "def record(authorized: Authorized[A]) -> Authorized[A]: ...\n"
    )
    assert check_source(source, SRC, SRC_MOD) == []


def test_rule2_a_callable_taking_a_capability_is_not_an_authority_parameter() -> None:
    source = (
        "from typing import Callable\n"
        "from ccf_runtime.authz.capability import Authorized, Execute\n"
        "def drive(on_decide: Callable[[Authorized[Execute]], None]): ...\n"
    )
    assert check_source(source, SRC, SRC_MOD) == []


def test_rule2_a_return_annotation_is_not_a_parameter() -> None:
    source = (
        "from ccf_runtime.authz.capability import Authorized, Execute\n"
        "def decide(request) -> Authorized[Execute] | None: ...\n"
    )
    assert check_source(source, RUNTIME, RUNTIME_MOD) == []


# =============================================================================
# Rule 3 — a mint site outside the gate module
# =============================================================================


def test_rule3_constructing_authorized_outside_the_capability_module_is_flagged() -> None:
    source = (
        "from ccf_runtime.authz.capability import Authorized, Execute\n"
        "cap = Authorized(object(), kind=Execute, tenant='t', principal='p',"
        " resource='r', decision_id='d')\n"
    )
    findings = check_source(source, RUNTIME, RUNTIME_MOD)
    assert _rules(findings) == [RULE_MINT_SITE]
    assert _lines(findings) == [2]


def test_rule3_an_aliased_or_qualified_construction_is_flagged() -> None:
    source = (
        "from ccf_runtime.authz.capability import Authorized as Cap\n"
        "from ccf_runtime.authz import capability\n"
        "a = Cap(object(), kind=None, tenant='', principal='', resource='', decision_id='')\n"
        "b = capability.Authorized(object(), kind=None, tenant='', principal='',"
        " resource='', decision_id='')\n"
    )
    assert _rules(check_source(source, SRC, SRC_MOD)) == [RULE_MINT_SITE, RULE_MINT_SITE]


def test_rule3_naming_the_sentinel_is_flagged_in_every_spelling() -> None:
    source = (
        "from ccf_runtime.authz.capability import _SENTINEL\n"
        "from ccf_runtime.authz import capability\n"
        "a = _SENTINEL\n"
        "b = capability._SENTINEL\n"
        'c = getattr(capability, "_SENTINEL")\n'
    )
    findings = check_source(source, RUNTIME, RUNTIME_MOD)
    assert _rules(findings) == [RULE_MINT_SITE] * 4
    assert _lines(findings) == [1, 3, 4, 5]


#: The two spellings of the capability module: the definer in ``src/`` and the
#: runtime re-export shim. A mint reached through either is the same mint.
CAPABILITY_SPELLINGS = [CAPABILITY_MOD, SHIM_MOD]


@pytest.mark.parametrize("spelling", CAPABILITY_SPELLINGS)
def test_rule3_calling_mint_from_a_module_that_is_not_a_gate_is_flagged(spelling: str) -> None:
    """The positive control the relocation demands, once per spelling: a
    ``mint`` imported from the definer AND one imported from the shim both
    redden a non-mint-site module."""
    source = (
        f"from {spelling} import mint, Execute\n"
        "def handler(decision, principal):\n"
        "    return mint(Execute, decision=decision, principal=principal, decision_id='d')\n"
    )
    findings = check_source(source, RUNTIME, RUNTIME_MOD)
    assert _rules(findings) == [RULE_MINT_SITE]
    assert "mint" in findings[0] and _lines(findings) == [3]


@pytest.mark.parametrize("spelling", CAPABILITY_SPELLINGS)
def test_rule3_calling_mint_through_a_module_alias_is_flagged(spelling: str) -> None:
    package, _, leaf = spelling.rpartition(".")
    source = (
        f"import {spelling} as cap\n"
        f"from {package} import {leaf}\n"
        "x = cap.mint(None, decision=None, principal='', decision_id='')\n"
        f"y = {leaf}.mint(None, decision=None, principal='', decision_id='')\n"
        f"z = {spelling}.mint(None, decision=None, principal='', decision_id='')\n"
    )
    assert _rules(check_source(source, SRC, SRC_MOD)) == [RULE_MINT_SITE] * 3


@pytest.mark.parametrize("spelling", CAPABILITY_SPELLINGS)
@pytest.mark.parametrize(
    ("path", "module_name"),
    [(CAPABILITY, CAPABILITY_MOD), (GATE, GATE_MOD), (TENANCY, TENANCY_MOD)],
)
def test_rule3_the_two_gates_and_the_definer_may_mint(
    path: pathlib.Path, module_name: str, spelling: str
) -> None:
    source = (
        f"from {spelling} import mint, Execute\n"
        "def gate(decision, principal):\n"
        "    return mint(Execute, decision=decision, principal=principal, decision_id='d')\n"
    )
    assert check_source(source, path, module_name) == []


def test_rule3_the_shim_is_an_allowed_importer_and_not_an_allowed_minter() -> None:
    """The shim's real shape — named re-exports — is clean; the same module
    CALLING what it re-exports is a third mint site like any other."""
    reexport = (
        "from ccf.authz.capability import (\n"
        "    Authorized as Authorized,\n"
        "    mint as mint,\n"
        "    mint_at_composition as mint_at_composition,\n"
        "    verify as verify,\n"
        ")\n"
    )
    assert check_source(reexport, SHIM, SHIM_MOD) == []
    minting = reexport + "cap = mint(None, decision=None, principal='', decision_id='')\n"
    findings = check_source(minting, SHIM, SHIM_MOD)
    assert _rules(findings) == [RULE_MINT_SITE]
    assert _lines(findings) == [7]


@pytest.mark.parametrize("spelling", CAPABILITY_SPELLINGS)
def test_rule3_mint_at_composition_belongs_to_the_composition_root_alone(spelling: str) -> None:
    """``ccf.boot`` is the composition root and may mint ``ReplayMint`` at
    boot; the HTTP gate may not (no door declares that action — §2 P3), and
    neither may the adopter-facing wiring package."""
    source = (
        f"from {spelling} import mint_at_composition\n"
        "def wire(tenant):\n"
        "    return mint_at_composition(tenant=tenant, principal='deployment',"
        " resource='replay.record', decision_id='d')\n"
    )
    assert check_source(source, BOOT, BOOT_MOD) == []
    assert check_source(source, CAPABILITY, CAPABILITY_MOD) == []
    for path, module_name in ((GATE, GATE_MOD), (DEPLOYMENT, DEPLOYMENT_MOD), (SHIM, SHIM_MOD)):
        findings = check_source(source, path, module_name)
        assert _rules(findings) == [RULE_MINT_SITE], module_name
        assert "mint_at_composition" in findings[0]


def test_rule3_the_definer_and_the_shim_at_head_are_clean() -> None:
    """The real files, not fixtures: the definer names its own sentinel and
    constructs its own capability; the shim re-exports and mints nothing."""
    assert mod.check(REPO / CAPABILITY, CAPABILITY_MOD) == []
    assert mod.check(REPO / SHIM, SHIM_MOD) == []


def test_rule3_the_capability_module_constructs_and_names_its_own_sentinel() -> None:
    source = (
        "_SENTINEL = object()\n"
        "def mint(kind, *, decision, principal, decision_id):\n"
        "    return Authorized(_SENTINEL, kind=kind, tenant=decision.tenant,"
        " principal=principal, resource=decision.resource, decision_id=decision_id)\n"
    )
    assert check_source(source, CAPABILITY, CAPABILITY_MOD) == []


def test_rule3_a_mint_method_on_another_object_is_not_the_capability_mint() -> None:
    source = (
        "def boot(token_factory, ledger):\n"
        "    token = token_factory.mint(ledger)\n"
        "    return token\n"
    )
    assert check_source(source, SRC, SRC_MOD) == []


def test_rule3_a_lookalike_name_is_not_the_sentinel() -> None:
    source = "_TRANSPARENT_SENTINELS: dict = {}\nSENTINEL = object()\n_sentinel = None\n"
    assert check_source(source, SRC, SRC_MOD) == []


def test_rule3_an_annotation_naming_authorized_is_not_a_construction() -> None:
    source = (
        "from ccf_runtime.authz.capability import Authorized, Execute\n"
        "def run(authorized: Authorized[Execute]) -> None: ...\n"
    )
    assert check_source(source, SRC, SRC_MOD) == []


# =============================================================================
# Rule 4 — MCP registration outside the TenantGuardedServer wrapper
# =============================================================================

RAW_DECORATOR = (
    "from mcp.server.fastmcp import FastMCP\n"
    "server = FastMCP('x')\n"
    "@server.tool(name='t')\n"
    "def body(): ...\n"
)


def test_rule4_a_raw_tool_decorator_is_flagged() -> None:
    findings = check_source(RAW_DECORATOR, RUNTIME, RUNTIME_MOD)
    assert _rules(findings) == [RULE_RAW_REGISTRATION]
    assert _lines(findings) == [3]
    assert "'server'" in findings[0]


def test_rule4_a_raw_resource_decorator_and_a_bare_decorator_are_flagged() -> None:
    source = (
        "from mcp.server.fastmcp import FastMCP\n"
        "server = FastMCP('x')\n"
        "@server.resource('u://{t}')\n"
        "def body(t): ...\n"
        "@server.tool\n"
        "def other(): ...\n"
    )
    assert _rules(check_source(source, RUNTIME, RUNTIME_MOD)) == [RULE_RAW_REGISTRATION] * 2


def test_rule4_a_non_decorator_registration_call_is_flagged() -> None:
    source = (
        "def mount(server, fn):\n"
        "    server.tool(name='t')(fn)\n"
        "    server.add_tool(fn)\n"
        "    server.add_resource(fn)\n"
    )
    assert _rules(check_source(source, RUNTIME, RUNTIME_MOD)) == [RULE_RAW_REGISTRATION] * 3


def test_rule4_a_registration_through_the_wrapper_is_clean() -> None:
    source = (
        "from ccf_runtime.mcp.tenancy import TenantGuardedServer\n"
        "def build(server):\n"
        "    door = TenantGuardedServer(server)\n"
        "    @door.tool(name='t', subject=None, mutating=False)\n"
        "    def body(): ...\n"
        "    def nested():\n"
        "        @door.resource('u://x', subject=None, mutating=False)\n"
        "        def res(): ...\n"
        "    return server\n"
    )
    assert check_source(source, RUNTIME, RUNTIME_MOD) == []


def test_rule4_a_wrapper_bound_through_an_alias_or_an_annotation_is_clean() -> None:
    source = (
        "from ccf_runtime.mcp.tenancy import TenantGuardedServer as Guard\n"
        "def build(door: Guard, server):\n"
        "    @door.tool(name='t', subject=None, mutating=False)\n"
        "    def body(): ...\n"
        "    inner = Guard(server)\n"
        "    inner.tool(name='u', subject=None, mutating=False)(body)\n"
        "    Guard(server).tool(name='v', subject=None, mutating=False)(body)\n"
    )
    assert check_source(source, RUNTIME, RUNTIME_MOD) == []


def test_rule4_a_name_rebound_to_a_raw_server_anywhere_in_the_module_is_refused() -> None:
    """Every binding of the receiver name must be the wrapper. One that is not
    makes every registration on that name unprovable, so all are refused."""
    source = (
        "from mcp.server.fastmcp import FastMCP\n"
        "from ccf_runtime.mcp.tenancy import TenantGuardedServer\n"
        "def a(server):\n"
        "    door = TenantGuardedServer(server)\n"
        "    @door.tool(name='t', subject=None, mutating=False)\n"
        "    def body(): ...\n"
        "def b():\n"
        "    door = FastMCP('raw')\n"
        "    @door.tool(name='u')\n"
        "    def other(): ...\n"
    )
    findings = check_source(source, RUNTIME, RUNTIME_MOD)
    assert _rules(findings) == [RULE_RAW_REGISTRATION] * 2
    assert _lines(findings) == [5, 9]


def test_rule4_reaching_the_underlying_server_through_the_wrapper_is_refused() -> None:
    source = (
        "from ccf_runtime.mcp.tenancy import TenantGuardedServer\n"
        "def build(server):\n"
        "    door = TenantGuardedServer(server)\n"
        "    @door.fastmcp.tool(name='t')\n"
        "    def body(): ...\n"
    )
    assert _rules(check_source(source, RUNTIME, RUNTIME_MOD)) == [RULE_RAW_REGISTRATION]


def test_rule4_a_second_wrapper_class_is_a_raw_registration() -> None:
    source = (
        "class MyGuard:\n"
        "    def __init__(self, server): self._server = server\n"
        "    def tool(self, name):\n"
        "        return self._server.tool(name=name)\n"
    )
    assert _rules(check_source(source, RUNTIME, RUNTIME_MOD)) == [RULE_RAW_REGISTRATION]


def test_rule4_the_wrapper_module_registers_on_the_raw_server() -> None:
    source = (
        "class TenantGuardedServer:\n"
        "    def tool(self, *, name, **kwargs):\n"
        "        def register(handler):\n"
        "            self._server.tool(name=name, **kwargs)(handler)\n"
        "            return handler\n"
        "        return register\n"
    )
    assert check_source(source, TENANCY, TENANCY_MOD) == []


def test_rule4_a_registration_in_src_is_refused_like_any_other() -> None:
    assert _rules(check_source(RAW_DECORATOR, SRC, SRC_MOD)) == [RULE_RAW_REGISTRATION]


def test_rule4_unrelated_attribute_calls_are_clean() -> None:
    source = "def f(client):\n    client.tools()\n    client.resources.list()\n    client.call_tool('x')\n"
    assert check_source(source, RUNTIME, RUNTIME_MOD) == []


# =============================================================================
# Rule 5 — a route handler with no @authorizes
# =============================================================================

UNGUARDED_ROUTE = (
    "from fastapi import APIRouter\n"
    "router = APIRouter()\n"
    "def mount():\n"
    "    @router.get('/queue')\n"
    "    def queue(): ...\n"
)

GUARDED_ROUTE = (
    "from fastapi import APIRouter\n"
    "from ccf_runtime.authz.route_declaration import ResourceBinding, authorizes\n"
    "router = APIRouter()\n"
    "def mount():\n"
    "    @router.get('/queue')\n"
    "    @authorizes('hitl.queue.read', resource=ResourceBinding.route())\n"
    "    def queue(): ...\n"
)


def test_rule5_a_route_without_authorizes_is_flagged_in_the_routes_package() -> None:
    findings = check_source(UNGUARDED_ROUTE, ROUTES, ROUTES_MOD)
    assert _rules(findings) == [RULE_UNGUARDED_ROUTE]
    assert "'queue'" in findings[0] and "get" in findings[0]
    assert _lines(findings) == [5]


def test_rule5_a_route_with_authorizes_is_clean() -> None:
    assert check_source(GUARDED_ROUTE, ROUTES, ROUTES_MOD) == []


def test_rule5_every_verb_is_a_route() -> None:
    verbs = ["get", "post", "put", "patch", "delete", "head", "options", "trace", "api_route"]
    body = "".join(f"@router.{v}('/x')\ndef h_{v}(): ...\n" for v in verbs)
    findings = check_source("router = None\n" + body, ROUTES, ROUTES_MOD)
    assert _rules(findings) == [RULE_UNGUARDED_ROUTE] * len(verbs)


def test_rule5_an_async_handler_and_an_aliased_authorizes_are_read() -> None:
    source = (
        "from ccf_runtime.authz.route_declaration import authorizes as declares\n"
        "router = None\n"
        "@router.post('/a')\n"
        "@declares('x', resource=None)\n"
        "async def a(): ...\n"
        "@router.post('/b')\n"
        "async def b(): ...\n"
    )
    findings = check_source(source, ROUTES, ROUTES_MOD)
    assert _rules(findings) == [RULE_UNGUARDED_ROUTE]
    assert "'b'" in findings[0]


def test_rule5_programmatic_registration_is_refused() -> None:
    source = "def mount(router, fn):\n    router.add_api_route('/x', fn)\n"
    assert _rules(check_source(source, ROUTES, ROUTES_MOD)) == [RULE_UNGUARDED_ROUTE]


def test_rule5_the_rule_reads_only_the_routes_package() -> None:
    """``app.py`` mounts ``/health`` with its own declaration and the gate
    refuses an undeclared route at boot; the static twin is scoped to the
    package where handlers are defined, and the scope is a named constant."""
    assert check_source(UNGUARDED_ROUTE, RUNTIME, RUNTIME_MOD) == []
    lookalike = pathlib.Path("runtime/ccf_runtime/http_api/routes_evil.py")
    assert check_source(UNGUARDED_ROUTE, lookalike, "ccf_runtime.http_api.routes_evil") == []


def test_rule5_a_non_route_decorator_with_a_verb_name_on_a_bare_name_is_not_a_route() -> None:
    source = "def get(f): return f\n@get\ndef h(): ...\n"
    assert check_source(source, ROUTES, ROUTES_MOD) == []


# =============================================================================
# Rule 6 — a `# type: ignore` beside an authority argument (§1.5b, §4)
# =============================================================================

SPLAT_IGNORE = (
    "def run(dependencies, authority):\n"
    "    from ccf_runtime.http_api.app import create_app\n"
    "    return create_app(dependencies, **authority)  # type: ignore[arg-type]\n"
)


def test_rule6_a_splat_forced_past_the_type_checker_is_flagged() -> None:
    findings = check_source(SPLAT_IGNORE, RUNTIME, RUNTIME_MOD)
    assert _rules(findings) == [RULE_TYPE_IGNORE]
    assert _lines(findings) == [3]
    assert "'create_app'" in findings[0] and "**" in findings[0]


def test_rule6_an_authority_keyword_forced_past_the_type_checker_is_flagged() -> None:
    source = (
        "def build(deps, create_app):\n"
        "    return create_app(\n"
        "        deps,\n"
        "        auth=None,  # type: ignore[arg-type]\n"
        "        authorizer=None,  # type: ignore\n"
        "    )\n"
    )
    findings = check_source(source, RUNTIME, RUNTIME_MOD)
    assert _rules(findings) == [RULE_TYPE_IGNORE] * 2
    assert _lines(findings) == [4, 5]


def test_rule6_a_positional_splat_and_an_annotated_assignment_are_flagged() -> None:
    source = (
        "from ccf_runtime.authz.capability import Authorized, Execute\n"
        "def f(registry, parts):\n"
        "    registry.register(*parts)  # type: ignore[arg-type]\n"
        "    cap: Authorized[Execute] = None  # type: ignore[assignment]\n"
    )
    assert _rules(check_source(source, SRC, SRC_MOD)) == [RULE_TYPE_IGNORE] * 2


def test_rule6_an_override_ignore_on_an_authority_signature_is_flagged() -> None:
    source = (
        "from ccf_runtime.authz.capability import Authorized, ArtifactWrite\n"
        "class Store:\n"
        "    def put(self, authorized: Authorized[ArtifactWrite], artifact):  # type: ignore[override]\n"
        "        ...\n"
    )
    assert _rules(check_source(source, SRC, SRC_MOD)) == [RULE_TYPE_IGNORE]


def test_rule6_an_ignore_with_no_authority_nearby_is_not_this_rule() -> None:
    source = (
        "def f(record, model_type, parse, reason):\n"
        "    claim = record.claim  # type: ignore[attr-defined]\n"
        "    fields = model_type.model_fields  # type: ignore[attr-defined]\n"
        "    return parse(\n"
        "        reason=reason,  # type: ignore[arg-type]\n"
        "    )\n"
    )
    assert check_source(source, SRC, SRC_MOD) == []


def test_rule6_a_docstring_mentioning_the_comment_is_not_a_comment() -> None:
    source = (
        "def f(deps, create_app, authority):\n"
        '    """A cast, a ``# type: ignore``, or an untyped caller."""\n'
        "    return create_app(deps, **authority)\n"
    )
    assert check_source(source, RUNTIME, RUNTIME_MOD) == []


def test_rule6_a_typed_call_needs_no_ignore_and_gets_no_finding() -> None:
    source = (
        "from ccf_runtime.http_api.auth import HttpAuthProtocol\n"
        "from ccf_runtime.authz.protocol import TenantAuthorizerProtocol\n"
        "def run(dependencies, auth: HttpAuthProtocol,"
        " authorizer: TenantAuthorizerProtocol, create_app):\n"
        "    return create_app(dependencies, auth=auth, authorizer=authorizer)\n"
    )
    assert check_source(source, RUNTIME, RUNTIME_MOD) == []


# =============================================================================
# Severing controls — each rule switched off alone, and only its finding goes quiet
# =============================================================================

#: One fixture per rule, in a runtime module (rule 5 in the routes package).
SABOTAGE_FIXTURES: dict[str, tuple[str, pathlib.Path, str]] = {
    RULE_DEFAULT: (DEFAULT_NONE, RUNTIME, RUNTIME_MOD),
    RULE_WEAK_TYPE: (
        "from ccf_runtime.authz.protocol import TenantAuthorizerProtocol\n"
        "def f(authorizer: TenantAuthorizerProtocol | None): ...\n",
        RUNTIME,
        RUNTIME_MOD,
    ),
    RULE_MINT_SITE: (
        "from ccf_runtime.authz.capability import Authorized\n"
        "a = Authorized(object(), kind=None, tenant='', principal='', resource='', decision_id='')\n",
        RUNTIME,
        RUNTIME_MOD,
    ),
    RULE_RAW_REGISTRATION: (RAW_DECORATOR, RUNTIME, RUNTIME_MOD),
    RULE_UNGUARDED_ROUTE: (UNGUARDED_ROUTE, ROUTES, ROUTES_MOD),
    RULE_TYPE_IGNORE: (SPLAT_IGNORE, RUNTIME, RUNTIME_MOD),
}


@pytest.mark.parametrize("rule", sorted(SABOTAGE_FIXTURES))
def test_severing_one_rule_silences_exactly_that_rule(
    rule: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Positive control first: every fixture reports its own rule. Then the
    rule's checker is removed from the dispatch table and the same fixture
    reports nothing under that rule — while every OTHER fixture still reports
    its own, so the severing is specific and the table is not one function
    wearing six names."""
    for other, (source, path, module_name) in SABOTAGE_FIXTURES.items():
        assert other in _rules(check_source(source, path, module_name)), other

    severed = tuple(entry for entry in mod.RULES if entry[0] != rule)
    assert len(severed) == len(mod.RULES) - 1, "the rule id names one table entry"
    monkeypatch.setattr(mod, "RULES", severed)

    source, path, module_name = SABOTAGE_FIXTURES[rule]
    assert rule not in _rules(check_source(source, path, module_name))
    for other, (o_source, o_path, o_module) in SABOTAGE_FIXTURES.items():
        if other != rule:
            assert other in _rules(check_source(o_source, o_path, o_module)), other


def test_severing_the_authority_type_set_blinds_the_type_arm_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A semantic severing beside the structural one: with no authority types,
    ``auth: HttpAuthProtocol | None = None`` is still caught by NAME, and a
    parameter named ``cap`` typed ``Authorized = None`` is not caught at all."""
    by_name = DEFAULT_NONE
    by_type_only = (
        "from ccf_runtime.authz.capability import Authorized, Execute\n"
        "def f(cap: Authorized[Execute] = None): ...\n"
    )
    assert RULE_DEFAULT in _rules(check_source(by_type_only, SRC, SRC_MOD))
    monkeypatch.setattr(mod, "AUTHORITY_TYPES", frozenset())
    assert RULE_DEFAULT in _rules(check_source(by_name, RUNTIME, RUNTIME_MOD))
    assert check_source(by_type_only, SRC, SRC_MOD) == []


def test_severing_the_authority_name_set_blinds_the_name_arm_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    by_name_only = "def f(authorizer=None): ...\n"
    assert RULE_DEFAULT in _rules(check_source(by_name_only, RUNTIME, RUNTIME_MOD))
    monkeypatch.setattr(mod, "AUTHORITY_PARAM_NAMES", frozenset())
    assert check_source(by_name_only, RUNTIME, RUNTIME_MOD) == []
    assert RULE_DEFAULT in _rules(check_source(DEFAULT_NONE, RUNTIME, RUNTIME_MOD))


def test_widening_the_mint_sites_admits_a_third_site(monkeypatch: pytest.MonkeyPatch) -> None:
    source = (
        "from ccf_runtime.authz.capability import mint, Execute\n"
        "x = mint(Execute, decision=None, principal='', decision_id='')\n"
    )
    assert _rules(check_source(source, RUNTIME, RUNTIME_MOD)) == [RULE_MINT_SITE]
    monkeypatch.setattr(mod, "MINT_SITES", mod.MINT_SITES | {RUNTIME_MOD})
    assert check_source(source, RUNTIME, RUNTIME_MOD) == []


def test_widening_the_composition_mint_sites_admits_a_third_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = (
        "from ccf.authz.capability import mint_at_composition\n"
        "x = mint_at_composition(tenant='t', principal='p', resource='r', decision_id='d')\n"
    )
    assert _rules(check_source(source, DEPLOYMENT, DEPLOYMENT_MOD)) == [RULE_MINT_SITE]
    monkeypatch.setattr(
        mod, "COMPOSITION_MINT_SITES", mod.COMPOSITION_MINT_SITES | {DEPLOYMENT_MOD}
    )
    assert check_source(source, DEPLOYMENT, DEPLOYMENT_MOD) == []


def test_the_shim_is_not_in_either_mint_site_set() -> None:
    """A constant-level guard beside the behavioral ones: adding the shim to a
    site set would let a call that reaches the real mint through the shim
    pass, which is the hole the relocation notice names."""
    assert mod.CAPABILITY_SHIM not in mod.MINT_SITES
    assert mod.CAPABILITY_SHIM not in mod.COMPOSITION_MINT_SITES
    assert mod.CAPABILITY_MODULE == "ccf.authz.capability"


def test_emptying_the_registration_methods_blinds_rule_4(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _rules(check_source(RAW_DECORATOR, RUNTIME, RUNTIME_MOD)) == [RULE_RAW_REGISTRATION]
    monkeypatch.setattr(mod, "REGISTRATION_METHODS", frozenset())
    assert check_source(RAW_DECORATOR, RUNTIME, RUNTIME_MOD) == []


def test_emptying_the_route_verbs_blinds_rule_5(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _rules(check_source(UNGUARDED_ROUTE, ROUTES, ROUTES_MOD)) == [RULE_UNGUARDED_ROUTE]
    monkeypatch.setattr(mod, "ROUTE_VERBS", frozenset())
    assert check_source(UNGUARDED_ROUTE, ROUTES, ROUTES_MOD) == []


# =============================================================================
# Registration in the runner
# =============================================================================


def test_the_rule_is_registered_scoped_to_core_and_has_a_flag() -> None:
    assert CHECKERS["authorization-invariant"] is mod.check
    assert RULE_TREE_SCOPE["authorization-invariant"] == ("src", "runtime")
    parsed = build_parser().parse_args(["--authorization-invariant"])
    assert parsed.selected == ["authorization-invariant"]


def _write(base: pathlib.Path, rel: str, source: str) -> None:
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def test_the_same_violation_in_five_trees_is_reported_in_exactly_two(
    tmp_path: pathlib.Path,
) -> None:
    """Population: five copies of ``create_app``'s defaulted signature, one per
    linted tree. Reported: the two in ``src`` and ``runtime``. ``examples``,
    ``tests`` and ``archive`` are outside the rule's scope by the same
    reasoning as the other core-scoped rules — a test fixture legitimately
    builds impostors, and the examples are the frozen specimens D-IMPL-261
    refuses to rewrite."""
    for tree in ("src", "runtime", "examples", "tests", "archive"):
        _write(tmp_path, f"{tree}/pkg/mod.py", DEFAULT_NONE)
    findings = run(tmp_path, ["authorization-invariant"])
    reported = sorted({f.split(":", 1)[0].replace(str(tmp_path) + "/", "") for f in findings})
    assert reported == ["runtime/pkg/mod.py", "src/pkg/mod.py"]
    assert len(findings) == 4, "two files x (rule 1 + rule 2) on the one parameter"


# =============================================================================
# THE ACCEPTANCE TEST — red at the fork point (D-IMPL-353 §4)
# =============================================================================


def _findings_at(commit: str, tmp_path: pathlib.Path) -> tuple[list[str], int]:
    """The lint's findings over ``commit``, relative paths, plus the number of
    Python files the rule read — every count names its population.

    A detached worktree, removed in ``finally``. FAILS rather than skips when
    the commit is absent: a check that cannot read its subject must not report
    clean, and the CI lint job checks out ``fetch-depth: 0`` for exactly this
    class of test (``test_base_roster.py`` is the precedent)."""
    target = tmp_path / "tree"
    subprocess.run(
        ["git", "-C", str(REPO), "worktree", "add", "--detach", str(target), commit],
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        findings = run(target, ["authorization-invariant"])
        population = sum(
            1
            for tree in RULE_TREE_SCOPE["authorization-invariant"]
            for _ in (target / tree).rglob("*.py")
        )
    finally:
        subprocess.run(
            ["git", "-C", str(REPO), "worktree", "remove", "--force", str(target)],
            check=True,
            capture_output=True,
            text=True,
        )
    prefix = str(target) + "/"
    return [f.replace(prefix, "", 1) for f in findings], population


def test_the_lint_is_red_at_the_fork_point_on_create_app(tmp_path: pathlib.Path) -> None:
    """``create_app(deps, *, auth: HttpAuthProtocol | None = None, authorizer:
    TenantAuthorizerProtocol | None = None, ...)`` at ``d895d889:runtime/
    ccf_runtime/http_api/app.py:193-194`` — D-IMPL-73's own signature. A lint
    that would not have reported it is not the lint."""
    findings, population = _findings_at(FORK_POINT, tmp_path)
    assert population > 0, "the fork-point tree was read"
    by_prefix = {f.split(" ", 2)[0] + " " + f.split(" ", 2)[1]: f for f in findings}

    auth = by_prefix.get(f"runtime/ccf_runtime/http_api/app.py:193 {RULE_DEFAULT}")
    authorizer = by_prefix.get(f"runtime/ccf_runtime/http_api/app.py:194 {RULE_DEFAULT}")
    assert auth is not None and "'auth'" in auth and "create_app" in auth, findings
    assert authorizer is not None and "'authorizer'" in authorizer and "create_app" in authorizer

    # Both parameters also admit None — the second defect on the same line.
    assert f"runtime/ccf_runtime/http_api/app.py:193 {RULE_WEAK_TYPE}" in by_prefix
    assert f"runtime/ccf_runtime/http_api/app.py:194 {RULE_WEAK_TYPE}" in by_prefix


def test_the_fork_point_reds_are_the_defect_classes_the_design_names(
    tmp_path: pathlib.Path,
) -> None:
    """Beyond ``create_app``: the MCP HITL authorizer default (P4), the product
    door's optional verifier, and every route handler — ``@authorizes`` did
    not exist at the fork point, so rule 5 reports each one."""
    findings, _ = _findings_at(FORK_POINT, tmp_path)
    joined = "\n".join(findings)
    assert f"runtime/ccf_runtime/mcp/hitl_server.py:" in joined
    assert "'authorizer'" in joined and "build_hitl_server" in joined
    assert "'token_verifier'" in joined and "open_door" in joined
    routes = [f for f in findings if RULE_UNGUARDED_ROUTE in f]
    assert routes, "rule 5 is red across the fork-point routes package"
    assert all(f.startswith("runtime/ccf_runtime/http_api/routes/") for f in routes)


# =============================================================================
# The seam — green except for the reds still owed by other lanes
# =============================================================================

#: ``(relative path, rule, the parameter the message names)`` — every finding
#: the lint reports at the seam ``934a4ce9``, each one a repair another lane of
#: D-IMPL-353 §8 owns (the MCP lane: ``hitl_server.py`` and ``product_door.py``;
#: the CLI's ``main.py`` belongs to whichever lane retypes ``create_app``'s
#: callers — a handoff, recorded in the lane report).
#: Set EQUALITY below: a finding not in this roster fails as a new red, and an
#: entry the tree no longer produces fails as stale — this is a measurement
#: kept equal to the tree, never an allowlist, and it is deleted entry by entry
#: as the lanes land.
EXPECTED_SEAM_REDS: frozenset[tuple[str, str, str]] = frozenset(
    {
        # The CLI entry that stood here was closed at the join (HttpAuthority,
        # 3729ada6); the four below fall when Lane MCP and Lane HITL-DOOR land.
        ("runtime/ccf_runtime/mcp/hitl_server.py", RULE_DEFAULT, "'authorizer'"),
        ("runtime/ccf_runtime/mcp/hitl_server.py", RULE_WEAK_TYPE, "'authorizer'"),
        ("runtime/ccf_runtime/mcp/product_door.py", RULE_DEFAULT, "'token_verifier'"),
        ("runtime/ccf_runtime/mcp/product_door.py", RULE_WEAK_TYPE, "'token_verifier'"),
    }
)


def _roster(findings: list[str], base: pathlib.Path) -> set[tuple[str, str, str]]:
    prefix = str(base) + "/"
    roster: set[tuple[str, str, str]] = set()
    for finding in findings:
        location, rule, message = finding.split(" ", 2)
        path = location.replace(prefix, "", 1).rsplit(":", 1)[0]
        named = next((tok for tok in message.split() if tok.startswith("'")), "")
        roster.add((path, rule, named.rstrip(",.")))
    return roster


def test_at_head_the_lint_reports_exactly_the_named_seam_reds() -> None:
    findings = run(REPO, ["authorization-invariant"])
    assert _roster(findings, REPO) == set(EXPECTED_SEAM_REDS), "\n".join(findings)
