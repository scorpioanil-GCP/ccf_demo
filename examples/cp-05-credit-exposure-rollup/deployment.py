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
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).parent
ARTIFACTS = HERE / "artifacts"
CONFIG = HERE / "ccf_config.yaml"
BACKENDS = HERE / "backends.yaml"
QUESTION = ARTIFACTS / "question.yaml"
TTL = ARTIFACTS / "ttl.yaml"
#: The named consumers `run.py --scenarios` demonstrates. READ-SIDE vocabulary:
#: a fitness bar and a threshold are things callers ask for, not things this
#: deployment is permitted to do, so they are not in `ccf_config.yaml`.
SCENARIOS = ARTIFACTS / "scenarios.yaml"
#: Where decision records go and under what artifact classes. A separate
#: document because the Control Plane's section vocabulary is closed and has no
#: slot for a deployment's own replay binding — see the artifact's own banner.
REPLAY = ARTIFACTS / "replay.yaml"
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

#: The SDK's name for the traversal-depth technical bound.
CAPABILITY_TRAVERSAL_DEPTH = "traversal-depth"


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


def _as_declared_type(rc: dict[str, Any], name: str, value: Any) -> Any:
    """Coerce a declared default to the Python type its argument declares.

    `integer` -> `int`, `number` -> `Decimal`, everything else unchanged. The
    two numeric cases are NOT interchangeable: an `integer` argument given a
    `Decimal` is refused just as a `number` argument given a `str` is, and both
    refusals name the offending parameter.
    """
    declared = rc["arguments"]["properties"].get(name, {}).get("type")
    if declared == "integer":
        return int(value)
    if declared == "number":
        return Decimal(str(value))
    return value


def request_contract(config: dict[str, Any]):
    """`ccf_config.yaml::request_contract` as the SDK's typed declaration.

    The product author's half of the parameter contract: which arguments exist,
    which are required, what each one's domain is, and what the product
    DEFAULTS to when a caller says nothing. It is the `default` authority in
    `ccf.products.provenance::Authority`, and it is the weakest of the four.
    """
    from ccf.products.request import ArgumentDomain, ProductRequestContract
    from ccf.skills.catalog import SkillArgumentProperty, SkillArgumentSchema

    rc = config["request_contract"]
    props = {
        name: SkillArgumentProperty(type=spec["type"], description=spec["description"])
        for name, spec in rc["arguments"]["properties"].items()
    }
    domains = {}
    for name, bound in rc.get("argument_bounds", {}).items():
        domains[name] = ArgumentDomain(
            minimum=Decimal(str(bound["minimum"])) if "minimum" in bound else None,
            maximum=Decimal(str(bound["maximum"])) if "maximum" in bound else None,
        )
    return ProductRequestContract(
        semver=rc.get("semver", "1.0.0"),
        schema_name=rc["schema_name"],
        schema_version=rc["schema_version"],
        arguments=SkillArgumentSchema(
            properties=props, required=tuple(rc["arguments"]["required"])
        ),
        # PASSED THROUGH UNCHANGED (`24.10-F-12`, `D-IMPL-288` (2)). This was a
        # comprehension minting `"not supported at this tier"` for every name
        # in a bare list — the deployment manufacturing the very information
        # the mapping shape exists to carry, and discarding whatever its author
        # might have said. `ccf_config.yaml` now authors the reason and this
        # line hands it over verbatim: the SDK reads what the document says.
        unsupported_arguments=dict(rc.get("unsupported_arguments", {})),
        # DECLARED AS TEXT, HANDED OVER AS A DECIMAL, and both halves are
        # required by different SDK rules that only look like a conflict.
        #
        # The Control Plane REFUSES a bare float in an artifact — *"not
        # bit-stable across platforms; quote the value so it parses as text and
        # is validated as a decimal."* So the YAML holds `"0.05"`.
        #
        # The request contract then judges a default against its declared
        # argument TYPE, and reads a number by VALUE rather than by Python type:
        # *"`Decimal("2")` IS `2` ... `"1"` is not `1`"*. So a string default
        # for a `number` argument is refused — correctly, because a caller
        # comparing `"0.05"` against a numeric domain would be comparing text.
        #
        # The interpreter is where the two meet. Text in the document, Decimal
        # on the wire. An earlier draft passed the strings through and was
        # refused at construction with every offender named in one pass.
        defaults={
            name: _as_declared_type(rc, name, value)
            for name, value in rc.get("argument_defaults", {}).items()
        },
        argument_domains=domains,
        # `depth` is bounded by the BACKEND as well as by the product. The
        # binding names which technical capability bounds which parameter, so a
        # refusal can say `technical` rather than blaming the product.
        capability_bindings={"depth": CAPABILITY_TRAVERSAL_DEPTH},
    )


def effective_request(*, config: dict[str, Any], registry, supplied: dict[str, Any],
                      subject: str, intent: str, freshness: str, asked_at):
    """Resolve every request parameter through the SDK, with its AUTHORITY.

    **This is the whole of the parameter model, and none of it is implemented
    here.** `ccf.products.constraints::resolve_effective_request` applies the
    precedence `policy > caller > default`, bounded by `technical`; this
    function only assembles its four inputs from documents that already exist.

    Why it matters that the SDK owns it: an example that hand-rolls a
    ``value if supplied else default`` helper produces the same NUMBER and
    loses the AUTHORITY. A rollup that cannot say whether its 5% threshold was
    the product's default, the caller's choice or a policy ceiling is a rollup
    whose replay cannot reconstruct the question. An earlier draft of this
    example did exactly that, and nothing in the SDK stopped it — the machinery
    is present and is not the obvious path.

    Returns:
        ``(request, outcome)``. The typed `ProductRequest` is handed back
        beside the resolution because the decision record wants it — dimension
        5 carries *which question this decision answered* — and rebuilding it
        at the call site would be a second place for one fact.

        The ``ResolutionOutcome`` — its ``evidence`` is an
        :class:`~ccf.products.provenance.EffectiveRequest` carrying one
        :class:`~ccf.products.provenance.EffectiveParameter` per parameter with
        its authority and source; its ``refusal`` is set when a caller's value
        crosses a bound it may not cross.
    """
    import datetime as _dt

    from ccf.products.constraints import (
        TechnicalCapability,
        constraints_in_force,
        resolve_effective_request,
    )
    from ccf.products.provenance import ProvenanceSource
    from ccf.products.request import ProductRequest
    from ccf.projection.plan import Perspective

    rc = config["request_contract"]
    declared = request_contract(config)
    persp = config["default_perspective"]

    request = ProductRequest(
        schema_name=rc["schema_name"],
        schema_version=rc["schema_version"],
        subject=subject,
        intent=intent,
        freshness=freshness,
        asked_at=asked_at,
        parameters={k: v for k, v in supplied.items() if v is not None},
    )

    # The BACKEND's ceiling, not the product's. `depth`'s request bound is 5
    # because that is what this product offers; the operator's `depth_limit` is
    # what the store can be asked for. A refusal at this bound says `technical`.
    operator_depth = config["operators"]["traversal.typed-neighborhood"]["depth_limit"]
    capabilities = (
        TechnicalCapability(
            capability=CAPABILITY_TRAVERSAL_DEPTH,
            maximum=Decimal(str(operator_depth)),
            identity=f"fluree/{config['product_class']['schema_name']}",
        ),
    )

    return request, resolve_effective_request(
        request=request,
        declared=declared,
        declared_source=ProvenanceSource(
            kind="artifact",
            identity=f"{rc['class_id']}",
            version=rc.get("semver", "1.0.0"),
        ),
        constraints=constraints_in_force(registry, asked_at=asked_at),
        capabilities=capabilities,
        capability_bindings=dict(declared.capability_bindings),
        # No entitled override is presented. `overridable: false` on the
        # materiality ceiling means one would not be honored anyway, and an
        # example that manufactured a grant to demonstrate a waiver would be
        # demonstrating its own fixture.
        verified_overrides=(),
        perspective=Perspective(principal_id=persp["principal_id"], role=persp["role"]),
        tenant=config["tenant_id"],
        class_defaults=dict(declared.defaults),
        class_source=ProvenanceSource(
            kind="artifact", identity=rc["class_id"], version=rc.get("semver", "1.0.0")
        ),
    )


def register_class(*, registry, config: dict[str, Any], ttl: dict[str, Any]):
    """Register this product class with the Control Plane, and return it PINNED.

    **A `RegisteredProductClass` is the object `run_gates` requires**, and it
    exists so the gates read a class the Control Plane pinned rather than a
    declaration the producer hands them at serve time. `max_ttl_key` names the
    key; registering the VALUE is what mints its version, which is why the
    ceiling lives in `artifacts/ttl.yaml` and not in the class declaration.

    Both registrations happen here, in the interpreter, from documents. Nothing
    in this function is a value: the ceiling, the anchor, the assembly mode and
    the request contract are all read.
    """
    from ccf.products.contract import MaxTTL, register_product_class

    declared = config["product_class"]
    rc = config["request_contract"]
    max_ttl_version = registry.register(
        declared["max_ttl_key"], MaxTTL(seconds=int(ttl["max_ttl_seconds"]))
    )
    request_contract_version = registry.register(rc["class_id"], request_contract(config))
    return register_product_class(
        registry=registry,
        schema_name=declared["schema_name"],
        schema_version=declared["schema_version"],
        ttl_anchor=declared["ttl_anchor"],
        assembly_mode=declared["assembly_mode"],
        max_ttl_key=declared["max_ttl_key"],
        max_ttl_version=max_ttl_version,
        request_contract_key=rc["class_id"],
        request_contract_version=request_contract_version,
    )


def replay_writers(root: Path):
    """The file-backed store and the two writers, from `artifacts/replay.yaml`.

    **The SAME store and the SAME record class for a served and a withheld
    determination** — `D-IMPL-253` Q13: *"Refusal is itself a decision and
    deserves the same five-dimensional replay model. Do not create second-class
    replay."* A second writer, or a second record shape, would be exactly that.

    Returns `(store, replay_writer, query_pin_writer)`. The query-pin writer is
    only spendable on the served path, because `ccf.replay.serve::serve` is what
    spends it and a withheld determination never reaches that call.
    """
    from ccf.artifacts.file_store import FileArtifactStore
    from ccf.replay.serve import QueryPinWriter, ReplayWriter

    declared = load(REPLAY)[DECLARATION]
    store = FileArtifactStore(root=root / declared["store_dirname"])
    return (
        store,
        ReplayWriter(store=store, artifact_class=declared["record_class"]),
        QueryPinWriter(store=store, artifact_class=declared["query_pin_class"]),
    )


def envelope_for_node(node: str, lei: str | None, label: str | None, *,
                      tenant: str, asked_at, family: str,
                      is_anchor: bool = False) -> Any:
    """One L1 envelope per family node — what L2 mints an entity from.

    `raw_payload` carries `member_ref`, the `match_key` `ccf_config.yaml`'s
    resolution spec declares, and under it `entity_uri` as the IDENTITY key.
    **Identity is the source IRI, not the LEI.** 58 of this family's 77 members
    carry no LEI (spec §C.1); a resolution spec keyed on LEI would mint nothing
    for three quarters of the family and the graph would be smaller, tidier and
    wrong.
    """
    from ccf.signal.envelope import SignalEnvelope, SourceIdentity

    return SignalEnvelope(
        tenant_id=tenant,
        envelope_id=f"cp05:{node}",
        source=SourceIdentity(system_id="exposure_graph"),
        ingestion_timestamp=asked_at,
        observed_time=asked_at,
        # FLAT, NOT NESTED, and the shape caught the author. `match_key` is only
        # a PRESENCE FLAG — `AssemblyWorker`'s resolver asks `rule.match_key in
        # payload` and then reads every identity and attribute key from the TOP
        # LEVEL of the same mapping, as siblings. Nesting them under the match
        # key resolves the rule and then refuses: *"matched rule for
        # 'exposure_member' but lacks identity keys ['entity_uri']; the fabric
        # refuses to mint a URI from partial identity."* Refusing to mint from
        # partial identity is right; the shape that provokes it is easy to get
        # wrong from the declaration alone.
        raw_payload={
            ("anchor_ref" if is_anchor else "member_ref"): True,
            "entity_uri": node,
            "lei": lei or "",
            "label": label or "",
            # THE POLICY ADMISSION KEY, and it is an OBSERVED fact rather than
            # an inherited one: this node was reached from this anchor by the
            # acquisition walk, which is the only thing anyone measured about
            # it. `D-IMPL-229` (rung 4, Dave): *"If PolicyFilter can only key
            # off a claim attribute, that attribute is membership, minted when
            # the node is admitted to the walk."* `ccf_config.yaml` has
            # declared `family_id` on both entity rules from the start; until
            # this line existed it was declared and never carried, and
            # `PolicyFilter` refuses a missing attribute exactly as firmly as
            # a wrong one — *"the fabric does not admit state it cannot prove
            # is admissible."*
            "family_id": family,
        },
    )


def relationship_claim(*, tenant: str, subject: str, object_: str,
                       predicate: str, envelope_id: str, asked_at) -> Any:
    """One edge, carrying ITS TRUE PREDICATE.

    Admitted through `AssemblyWorker.admit_relationship_claim` rather than minted
    by `ingest`'s declared rules, for the reason cp-04 measured and recorded
    (`D-35`): `ingest` mints relationship claims by CLASS CO-OCCURRENCE — every
    declared rule whose subject and object classes both resolve from one
    envelope fires, and nothing selects the predicate from the payload. cp-04
    measured one envelope minting two entities and TWELVE relationships, six of
    them self-loops. So `ccf_config.yaml` declares `relationship_rules: []` and
    each normalized edge is admitted here instead. Still one writer, still L2.
    """
    from ccf.contracts.claims import LineageEntry, RelationshipClaim
    from ccf.signal.envelope import SourceIdentity

    source = SourceIdentity(system_id="exposure_graph")
    return RelationshipClaim(
        tenant_id=tenant,
        observed_at=asked_at,
        valid_from=asked_at,
        lineage=frozenset({LineageEntry(source=source, envelope_id=envelope_id,
                                        observed_at=asked_at)}),
        relationship_type=predicate,
        subject_uri=subject,
        object_uri=object_,
    )


def refuse_unbound_family_scope(bound, *, expected: str) -> None:
    """The BOUND policy set names exactly the one family this request asked.

    Two failures, and each is silent without this refusal. An EMPTY bound set
    admits NOTHING and serves an empty family, which reads as *this company has
    no exposure* — a claim about the world. A bound set naming some OTHER family
    admits nothing for the same reason while looking configured.

    **This is what makes the substitution below mandatory rather than
    conventional.** `ccf_config.yaml` declares `permitted_classifications`
    empty on purpose — the family a request names is not knowable when the
    document is written — so a path that skipped the binding would surface as an
    empty answer rather than by name. Rung 4 ruled this shape (`D-IMPL-229`).
    """
    values = tuple(sorted(bound))
    if not values:
        raise SystemExit(
            "the policy envelope was left as declared, which admits NOTHING."
            " ccf_config.yaml declares an empty permitted set deliberately —"
            " the family a request names is not knowable at declaration time —"
            " and populate_and_traverse is what binds it (`D-IMPL-229`)"
        )
    if values != (expected,):
        raise SystemExit(
            f"the policy envelope admits {values} but this request asked about"
            f" {expected!r}. A bound set naming another family admits nothing"
            " for this one while looking fully configured."
        )


def populate_and_traverse(*, fabric, graph: GraphSource, anchor_node: str,
                          nodes: list[str], edges: list[tuple[str, str, str]],
                          leis: dict[str, str], asked_at, family: str):
    """Acquisition → L2 → L3 → the DECLARED L4 traversal. Returns its family.

    **The distinction this function exists to make explicit, and it is cp-05's
    central assembler lesson:**

    > *Acquisition may use backend-specific logic; decision logic must execute
    > through the declared fabric mechanisms.*

    Reading someone else's Fluree estate over SPARQL is ACQUISITION — it is
    backend-specific by nature and has no SDK surface today (`D-IMPL-277`,
    open). Deciding which entities constitute the family is DECISION LOGIC, and
    it runs here through the operator the Control Plane registered, over a
    time-bounded `GraphView` of L3, seeded from the entity class
    `ccf_config.yaml` declares.

    An earlier draft of this product answered the question from the acquisition
    walk directly. It produced the same 77 entities and was not a Context
    Product: the Control Plane permitted a traversal that never ran, and a
    hand-rolled walk ran one it never saw.
    """
    from ccf.deployment import build_operator_registry

    worker = fabric.handle.worker
    tenant = fabric.tenant_id

    minted: dict[str, str] = {}
    for node in nodes:
        result = worker.ingest(
            envelope_for_node(node, leis.get(node), None, tenant=tenant,
                              asked_at=asked_at, family=family,
                              is_anchor=(node == anchor_node))
        )
        for entity in getattr(result, "entities", ()):
            minted[node] = entity.node_key

    for subject, predicate, obj in edges:
        if subject in minted and obj in minted:
            worker.admit_relationship_claim(
                tenant_id=tenant,
                claim=relationship_claim(
                    tenant=tenant, subject=minted[subject], object_=minted[obj],
                    predicate=predicate, envelope_id=f"cp05:{subject}",
                    asked_at=asked_at,
                ),
            )

    # The view at the boundary the REQUEST named, never a clock — so replay
    # feeds the same instant back through the same code path.
    view = fabric.handle.reader.as_of(tenant_id=tenant, at=asked_at)

    # BIND THIS REQUEST'S FAMILY ONTO THE DECLARED POLICY ENVELOPE. The
    # declaration is empty on purpose and admits nothing; the substitution is
    # what makes it admit THIS family and no other. Two families are two
    # parameter-set hashes and therefore two content addresses, so the replay
    # record says WHICH family a decision admitted rather than leaving it to be
    # inferred from the payload.
    declared_policy = fabric.artifacts["policy.principal-subgraph"]
    bound_policy = declared_policy.model_copy(
        update={"permitted_classifications": frozenset({family})}
    )
    refuse_unbound_family_scope(bound_policy.permitted_classifications,
                                expected=family)

    registry = build_operator_registry(
        parameters={
            "policy.principal-subgraph": bound_policy,
            "traversal.typed-neighborhood":
                fabric.artifacts["traversal.typed-neighborhood"],
        },
        view=view, pins=fabric.pins, policy_bundle_key=worker.policy_bundle_key,
    )

    # POLICY RUNS FIRST AND THE TRAVERSAL CHAINS FROM ITS OUTPUT.
    #
    # **This is the correction of a real defect, recorded rather than quietly
    # repaired.** An earlier revision passed `upstream=()` to the traversal —
    # which invokes the policy operator's registration and then discards its
    # result. The product answered 77 from a walk that never passed through the
    # policy envelope, while its lineage declared `policy.principal-subgraph`
    # among the operators invoked. The replay record was the thing that found
    # it: dimension 1 reported `touched_entities: 0` for a determination over
    # 77 members, because the ENGINE's chained pipeline (which does compose
    # them) was correctly returning nothing while the answer came from
    # somewhere else.
    #
    # On a graph the ordering is not decoration. A node the principal may not
    # see is never materialized, so no edge to it is ever built.
    admitted = registry.resolve("policy.principal-subgraph").apply(
        view=view, tenant_id=tenant, temporal_boundary=asked_at, upstream=()
    )
    output = registry.resolve("traversal.typed-neighborhood").apply(
        view=admitted.view, tenant_id=tenant, temporal_boundary=asked_at,
        upstream=(admitted.provenance,),
    )

    records = output.view.entities
    records = list(records.values()) if isinstance(records, dict) else list(records)
    family_leis = sorted({
        lei for r in records
        if (lei := (r.claim.attributes or {}).get("lei"))
    })
    return {
        "records": records,
        "family_size": len(records),
        "family_leis": family_leis,
        "minted": minted,
        "view": view,
        "registry": registry,
        "fabric": fabric,
    }


def assess_context_debt(*, fabric, balance_observations: list[tuple[str, Any]],
                        reconciliation_rows: list[tuple[str, bool]],
                        family_size: int, checkable_members: int,
                        enrich_failures: int, asked_at):
    """Context Debt from EVIDENCE — never from result cardinality.

    **The rule this function exists to hold:** debt describes confidence in the
    assembled truth, not how aggressively the caller chooses to project it. The
    same evidence must yield the same debt whether the caller asked at 2%, 5% or
    10%, because caller preference cannot make the underlying knowledge more or
    less trustworthy.

    **Cardinality is not evidence.** 77 entities is not evidence of low debt and
    0 would not be evidence of high debt. Each factor below is derived from
    something the estate actually attests:

    * **freshness** — the real `balance_as_of` dates on the family's facilities,
      scored against the declared `λ_c` by the SDK's own `FreshnessScorer`.
      Nothing is fabricated: an earlier draft stamped `observed_at` with the
      REQUEST time, which would have scored perfect freshness out of nothing.
    * **completeness** — what fraction of the family the product could CHECK for
      exposure at all. Facilities are keyed by LEI, so a family member carrying
      no LEI cannot be examined and its exposure is UNKNOWN rather than zero.
      **This is not the enriched-over-asked ratio.** A first draft computed
      books-found ÷ LEIs-asked and got 5/19 — which charges the product for
      members that legitimately hold nothing, and is cardinality wearing an
      evidence costume. A member with an LEI and no facility is a determined
      answer; a member with no LEI is an undetermined one. A genuine enrich
      FAILURE would also count here, and is tracked separately.
    * **semantic_consistency** — reconciliation disagreement **among the
      obligors this determination actually used**. The estate carries one
      implausible reconciliation out of fourteen; measured, it is not in this
      family, so it contributes nothing here. A ratio encoded mechanically
      would have charged this product for a disagreement it never relied on.

    `debt = 1 - min(F, C, S)`: the weakest link bounds confidence.

    **This function returns an assessment, never a verdict.** Whether a debt
    figure refuses a request is a FULFILLMENT determination against a tolerance,
    made downstream. Debt is the measured uncertainty; the refusal is a governed
    outcome of comparing it to what the caller or policy will accept.
    """
    from decimal import Decimal

    from ccf.halflife.assessment import DebtFactors
    from ccf.halflife.debt import FreshnessScorer, assess_debt
    from ccf.halflife.decay import Observation

    table = fabric.artifacts["half_life"]
    profile = fabric.artifacts["debt_profile"]

    observations = [
        Observation(observation_type="outstanding_balances",
                    observed_at=observed, subject=subject)
        for subject, observed in balance_observations
    ]
    if not observations:
        # The SDK refuses to score freshness over zero observations, and its
        # reason is the right one: *"an empty assembly is a completeness
        # shortfall, not a fresh one."* Manufacturing a freshness figure here
        # would be inventing confidence, so the absence is charged to
        # completeness where it belongs.
        freshness = Decimal(0)
    else:
        freshness = FreshnessScorer(
            table, Decimal(str(profile.risk_sensitivity))
        ).score(observations, now=asked_at)

    checkable = max(checkable_members - enrich_failures, 0)
    completeness = (
        Decimal(checkable) / Decimal(family_size) if family_size else Decimal(1)
    )

    used = [plausible for _lei, plausible in reconciliation_rows]
    consistency = (
        Decimal(sum(1 for p in used if p)) / Decimal(len(used)) if used else Decimal(1)
    )

    assessment = assess_debt(
        DebtFactors(freshness=freshness, completeness=completeness,
                    semantic_consistency=consistency),
        profile=profile,
    )
    return assessment, {
        "freshness": str(freshness),
        "completeness": str(completeness),
        "semantic_consistency": str(consistency),
        "family_size": family_size,
        "checkable_members": checkable,
        "unresolvable_members": family_size - checkable,
        "enrich_failures": enrich_failures,
        "balance_observations": len(observations),
        "reconciliations_used": len(used),
        "reconciliations_implausible": sum(1 for p in used if not p),
    }
