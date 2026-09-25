"""The authorization-invariant rule's tree scope, proven through the runner.

Fixture-driven, mirroring ``tests/lints/test_deployment_gates_ban.py``: every
case drives ``tools.lints.__main__.run`` — the entrypoint CI uses — over a
synthetic tree, so what is asserted is the posture the gate actually has, not
the constant that describes it (``tools/lints/tests/test_scope.py`` gates the
constant; this module gates the behavior).

Population, stated once: six violating modules per rule, one under each of
the five linted trees. Reported: the two under ``src`` and ``runtime`` —
D-IMPL-353 §4's own wording. ``tests`` is out because the §9 fabrication and
retargeting controls build impostor capabilities on purpose; ``examples`` and
``archive`` are out because the specimens are frozen (D-IMPL-261) and the
example servers that register raw MCP surfaces are gap-ledger entries under §7.
"""

from __future__ import annotations

import pathlib

import pytest

from tools.lints.authorization_invariant import (
    RULE_DEFAULT,
    RULE_MINT_SITE,
    RULE_RAW_REGISTRATION,
    RULE_TYPE_IGNORE,
    RULE_UNGUARDED_ROUTE,
    RULE_WEAK_TYPE,
)
from tools.lints.__main__ import LINTED_TREES, RULE_TREE_SCOPE, run

RULE = "authorization-invariant"

#: One violating module per rule. Rule 5 is defined over the routes package,
#: so its module path names that package under whichever tree it is planted in.
VIOLATIONS: dict[str, tuple[str, str]] = {
    RULE_DEFAULT: (
        "ccf_runtime/http_api/app.py",
        "from ccf_runtime.http_api.auth import HttpAuthProtocol\n"
        "def create_app(deps, *, auth: HttpAuthProtocol = None): ...\n",
    ),
    RULE_WEAK_TYPE: (
        "ccf_runtime/mcp/hitl_server.py",
        "from ccf_runtime.authz.protocol import TenantAuthorizerProtocol\n"
        "def build(*, authorizer: TenantAuthorizerProtocol | None): ...\n",
    ),
    RULE_MINT_SITE: (
        "ccf/controlplane/registry.py",
        "from ccf_runtime.authz.capability import Authorized\n"
        "cap = Authorized(object(), kind=None, tenant='', principal='', resource='', decision_id='')\n",
    ),
    RULE_RAW_REGISTRATION: (
        "ccf_runtime/mcp/egress.py",
        "from mcp.server.fastmcp import FastMCP\n"
        "server = FastMCP('x')\n"
        "@server.tool(name='t')\n"
        "def body(): ...\n",
    ),
    RULE_UNGUARDED_ROUTE: (
        "ccf_runtime/http_api/routes/hitl.py",
        "router = None\n@router.get('/queue')\ndef queue(): ...\n",
    ),
    RULE_TYPE_IGNORE: (
        "ccf_runtime/cli/main.py",
        "def run(deps, authority, create_app):\n"
        "    return create_app(deps, **authority)  # type: ignore[arg-type]\n",
    ),
}


def _write(base: pathlib.Path, rel: str, source: str) -> None:
    path = base / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def _trees(findings: list[str], base: pathlib.Path) -> list[str]:
    prefix = str(base) + "/"
    return sorted({f.replace(prefix, "", 1).split("/", 1)[0] for f in findings})


def test_the_scope_is_src_and_runtime_and_the_walk_visits_both() -> None:
    assert RULE_TREE_SCOPE[RULE] == ("src", "runtime")
    assert set(RULE_TREE_SCOPE[RULE]) <= set(LINTED_TREES)


@pytest.mark.parametrize("rule", sorted(VIOLATIONS))
def test_each_rule_fires_in_core_and_in_no_other_tree(
    rule: str, tmp_path: pathlib.Path
) -> None:
    rel, source = VIOLATIONS[rule]
    for tree in LINTED_TREES:
        _write(tmp_path, f"{tree}/{rel}", source)
    findings = run(tmp_path, [RULE])
    assert _trees(findings, tmp_path) == ["runtime", "src"], "\n".join(findings)
    assert all(rule in f for f in findings if rule in f)
    assert any(rule in f for f in findings), f"{rule} reported nothing in core"


def test_a_clean_core_tree_yields_no_findings(tmp_path: pathlib.Path) -> None:
    """The negative control for the positive ones above."""
    _write(
        tmp_path,
        "runtime/ccf_runtime/http_api/app.py",
        "from ccf_runtime.http_api.auth import HttpAuthProtocol\n"
        "from ccf_runtime.authz.protocol import TenantAuthorizerProtocol\n"
        "def create_app(deps, *, auth: HttpAuthProtocol, authorizer: TenantAuthorizerProtocol): ...\n",
    )
    _write(
        tmp_path,
        "src/ccf/controlplane/registry.py",
        "from ccf_runtime.authz.capability import Authorized, Register\n"
        "class ControlPlaneRegistry:\n"
        "    def register(self, authorized: Authorized[Register], artifact): ...\n",
    )
    assert run(tmp_path, [RULE]) == []
