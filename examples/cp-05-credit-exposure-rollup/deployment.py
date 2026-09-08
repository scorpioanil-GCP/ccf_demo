"""cp-05's interpreter — it reads the declarations and holds none of their values.

[ADAPT] the two store clients. [MECHANISM] everything the SDK boots.

**This module contains no domain value.** Not an anchor, not a threshold, not a
half-life, not a host, not a ledger name. Every one of those lives in
``ccf_config.yaml``, ``backends.yaml`` or ``artifacts/``, and this program is
their interpreter (``CLAUDE.md`` §6.4). Delete the declarations beside it and
this module has nothing to connect to and nothing to serve — which is the test
the No-Hardcoding Rule sets for an example.

The two stores, and why neither can answer alone
------------------------------------------------
``exposure_graph`` is Fluree, read over ``/v1/fluree/query`` in the **SPARQL**
dialect with an explicit ``FROM <ledger>`` on every query — the server answers
HTTP 500 without one, so the ledger name is not optional and is never defaulted.
It owns the EDGES: ownership, guarantee, cross-default, borrower-of.

``exposure_amounts`` is PostgreSQL. It owns the AMOUNTS and the POLICY —
commitments, balances, guarantee coverage, limit definitions, the XBRL
reconciliation and entity identity.

The split is the product (spec §C.1). A question about total exposure across a
corporate family cannot be answered by either store on its own, and that is what
makes this a Context Product rather than a query.

Read-only, by construction
--------------------------
Every statement this module issues is a SELECT or a SPARQL read. Spec §C.3:
this product writes nothing, L2 remains the only writer to the graph, and
nothing here acquires a write handle to either store.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).parent
ARTIFACTS = HERE / "artifacts"
CONFIG = HERE / "ccf_config.yaml"
BACKENDS = HERE / "backends.yaml"
QUESTION = ARTIFACTS / "question.yaml"
TTL = ARTIFACTS / "ttl.yaml"
EXPECTED = ARTIFACTS / "expected.yaml"
SPEC = HERE / "spec" / "CP-SPEC-005_Credit_Exposure_Rollup.md"

DECLARATION = "declaration"
SOURCES = "sources"
SETTINGS = "settings"
FROM_ENV = "from_env"
REMEDY = "remedy"
PREFIX = "prefix"
SUFFIX = "suffix"

#: Fluree 4.1.4's read endpoint. The dialect is SPARQL and the ledger is named
#: by an explicit ``FROM`` clause inside the query text — see :func:`sparql`.
FLUREE_QUERY_PATH = "/v1/fluree/query"

#: The predicate IRIs this product walks. **These are FIBO's own IRIs where FIBO
#: has a term**, and ``example.org`` only where it does not: there is no FIBO
#: predicate for a cross-default clause. Read from the ledger rather than
#: guessed — an earlier pass probed with the vault's *prose labels*
#: (``guarantees``, ``borrowerOf``) and measured zero edges, which looked like a
#: spec/estate divergence and was an instrument error.
FIBO = "https://spec.edmcouncil.org/fibo/ontology"
OWNS = f"{FIBO}/FND/OwnershipAndControl/Ownership/owns"
IS_GUARANTOR_OF = f"{FIBO}/FBC/DebtAndEquities/Guaranty/isGuarantorOf"
HAS_BORROWER = f"{FIBO}/FBC/DebtAndEquities/Debt/hasBorrower"
ULTIMATELY_CONSOLIDATED_BY = f"{FIBO}/BE/LegalEntities/LEIEntities/isUltimatelyConsolidatedBy"
CROSS_DEFAULTS_WITH = "http://example.org/fibo/crossDefaultsWith"
LEI_PREDICATE = "http://example.org/fibo/lei"


class DeclarationMissing(RuntimeError):
    """A declared setting has no value in the environment.

    Carries the ``remedy`` the declaration itself supplies, so an operator is
    told what to export and *why* rather than reading a traceback.
    """


class GraphUnavailable(RuntimeError):
    """The graph leg could not be read. Never silently degraded to zero edges."""


def load(path: Path) -> dict[str, Any]:
    """One declaration document, parsed. ``role: load`` — parsed and handed back."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _setting(source: dict[str, Any], name: str) -> str:
    """One connection setting, resolved from the environment ``backends.yaml`` names.

    The declaration holds the variable's NAME; the environment holds its value;
    this function is the only place the two meet. An absent variable raises
    :class:`DeclarationMissing` carrying the declaration's own remedy — it does
    not default, because a defaulted host is a store nobody chose.
    """
    spec = source[SETTINGS][name]
    variable = spec[FROM_ENV]
    value = os.environ.get(variable)
    if not value:
        raise DeclarationMissing(f"{variable} is unset.\n\n  {spec[REMEDY]}")
    return value


@dataclass(frozen=True)
class GraphSource:
    """The Fluree leg — URL and ledger, both from named variables."""

    url: str
    ledger: str


@dataclass(frozen=True)
class AmountsSource:
    """The PostgreSQL leg — DSN and schema, both from named variables."""

    dsn: str
    schema: str


def resolve_sources(backends: dict[str, Any]) -> tuple[GraphSource, AmountsSource]:
    """Both legs, resolved from ``backends.yaml``'s declared variable names."""
    sources = backends[DECLARATION][SOURCES]
    graph = sources["exposure_graph"]
    amounts = sources["exposure_amounts"]
    return (
        GraphSource(url=_setting(graph, "url"), ledger=_setting(graph, "ledger")),
        AmountsSource(dsn=_setting(amounts, "dsn"), schema=_setting(amounts, "schema")),
    )


def _from_clause(source: GraphSource) -> str:
    """``FROM <ledger>`` — mandatory, and the reason is not stylistic.

    Fluree 4.1.4 answers HTTP 500 to a SPARQL query carrying no ``FROM``. The
    ledger name therefore cannot be defaulted: a default would be a value nobody
    chose pointing at a store nobody named, and the failure it produces is a 500
    rather than a clear refusal.
    """
    return f"FROM <{source.ledger}>"


def sparql(source: GraphSource, body: str) -> list[dict[str, Any]]:
    """One SPARQL read against the declared ledger.

    Raises :class:`GraphUnavailable` rather than returning an empty binding set.
    **An unreachable graph and a graph with no matching edges are different
    facts**, and a product that conflated them would report a one-node family
    for a network partition — the empty-operator guard (spec §D.7) exists to
    catch exactly that, and it cannot fire on an exception this function
    swallowed.
    """
    request = urllib.request.Request(
        source.url.rstrip("/") + FLUREE_QUERY_PATH,
        data=body.encode("utf-8"),
        headers={"Content-Type": "application/sparql-query"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        raise GraphUnavailable(f"{source.url}{FLUREE_QUERY_PATH}: {exc}") from exc
    return list(payload.get("results", {}).get("bindings", []))


def one_column(bindings: list[dict[str, Any]], name: str) -> list[str]:
    """The values of one SPARQL variable, in binding order."""
    return [row[name]["value"] for row in bindings if name in row]


def connection(backends: dict[str, Any], root: Path) -> dict[str, object]:
    """The per-run L3 path, minted from ``backends.yaml``'s RECIPE.

    The declaration holds ``{per_run: path, prefix, suffix}`` — a recipe, not a
    path — so two asks of the same question build two separate graphs from the
    same two estates and must still agree byte for byte. A fixed path would let
    the second ask inherit the first's L3 and call the agreement reproducibility
    when it was only reuse.
    """
    import uuid

    profile = backends[DECLARATION]["profiles"]["sqlite"][SETTINGS]["database_path"]
    root.mkdir(parents=True, exist_ok=True)
    name = f"{profile[PREFIX]}_{uuid.uuid4().hex[:12]}{profile[SUFFIX]}"
    return {"database_path": str(root / name)}


def boot(root: Path):
    """The fabric, booted from this deployment's own Control Plane document.

    Returns the ``BootedFabric`` and the registry it registered into. The
    registry is the audit plane; the caller holds it so a gate run and a replay
    write reach the same one.
    """
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.deployment import load_config_and_boot

    registry = ControlPlaneRegistry()
    fabric = load_config_and_boot(
        CONFIG, registry=registry, connection=connection(load(BACKENDS), root)
    )
    return fabric, registry
