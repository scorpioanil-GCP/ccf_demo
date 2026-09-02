"""Up-front probes for the Fluree v4 substrate — no adapter code exists yet.

Plan 15.3-01, D-06. Everything here runs in an environment with **no extra
installed at all**, which is the exact inversion of what
``tests/graph/test_neo4j_backend.py``'s own module docstring says about itself:
``httpx==0.28.1`` is a direct
core pin (``pyproject.toml:44``), so this substrate needs no
``[project.optional-dependencies]`` entry, no lazy import guard and no
``[[tool.mypy.overrides]]`` block. That absence is itself SUBQ-14 evidence —
Fluree costs less packaging than any of the previous three substrates.

These probes deliberately run **before** ``ccf.graph.backends.fluree`` exists.
Nothing here imports adapter code, and nothing here may be adjusted to make a
later adapter convenient: the whole value of D-06's split is that a probe which
runs first cannot be biased by the code that depends on it. Plan 15.2-08's
mandatory A5 probe falsified its assumption and produced D-IMPL-89 precisely
because it ran in this order.

Every request is raw :mod:`httpx` against the pinned ``fluree/server:4.1.4``
container, and every CCF-shaped value travels as an ``xsd:string`` literal
behind an adapter-minted colonless ``@id`` (15.3-RESEARCH.md §R3, threat
T-15.3-03) — no artifact-authored string ever occupies an IRI position.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import uuid
from typing import TYPE_CHECKING, Any

import httpx
import pytest
from pydantic import SecretStr

from ccf.contracts.canonical import canonical_bytes
from ccf.controlplane.registry import ControlPlaneMissing
from ccf.graph.backends.fluree_write import (
    BEARER_TOKEN_FIELD,
)
from ccf.graph.backends.fluree_write import (
    REGISTRATION as FLUREE_REGISTRATION,
)

from tests.conformance.query_corpus import (
    AUTHORING_OFFSETS,
    EARLY,
    LATE,
    ON_BOUNDARY,
    RELATIONSHIP_TYPES,
    SEED_CLASSES,
    TENANT,
    chain_claims,
    chain_uris,
    entity_claim,
    relationship_claim,
)
from tests.conformance.test_substrate_properties import (
    EXCLUDED_CLASSIFICATION,
    MID_CLASS,
    PERMITTED_CLASSIFICATION,
    SEED_CLASS,
    _RULE_B,
)
from tests.properties.strategies import ENTITY_POOL, RELATIONSHIP_RULES

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from ccf.boot import FabricHandle

#: A crossable edge type from the fixture vocabulary — the tests hold
#: mechanism; the vocabulary is the fixtures' (CLAUDE.md §6.4).
EDGE_TYPE = sorted(RELATIONSHIP_TYPES)[0]

#: Canonical RFC3339 UTC at microsecond width — what every temporal property
#: this adapter writes must read back as (§R8 vector 1).
CANONICAL_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")

#: The path-enumeration cap error's identifying substring, **as measured by
#: probe F-A3(c)** rather than as documented — the full message is
#: ``"Query error: Resource limit exceeded: path enumeration exceeded max
#: paths (1000); narrow the pattern (tighter hop bounds, a bound end node, or
#: a specific type)"`` under ``"@type":"err:db/InvalidQuery"``. Spelled out
#: here, in the probe, so the adapter's matcher can be bound to the measurement
#: rather than to itself (see
#: ``test_the_cap_matcher_is_the_string_the_server_actually_sends``).
CAP_ERROR_MARKER = "Resource limit exceeded"

# Layout probes. Deliberately authored HERE rather than in
# `ccf.graph.backends.fluree`: they assert the adapter-owned physical model
# from outside, and a statement that lives in the module under test could be
# changed in lockstep with the layout it is supposed to pin. The property names
# are the adapter's, spelled out, so a rename breaks the assertion loudly.

#: Exactly one interposed edge node per CCF relationship, and its admit key.
_EDGE_NODE_PROBE = """
    MATCH (e:CcfEdge {ccf_partition: $partition, ccf_tenant_id: $tenant,
                      ccf_relationship_key: $key})
    RETURN e.ccf_admit_key AS admit_key
"""

#: Exactly two CCF_LINK triples, joining that node to its two endpoints. The
#: pattern is undirected, so it would also catch a doubled write.
_EDGE_LINK_PROBE = """
    MATCH (e:CcfEdge {ccf_partition: $partition, ccf_tenant_id: $tenant,
                      ccf_relationship_key: $key})-[:CCF_LINK]-(n:CcfEntity)
    RETURN n.ccf_entity_uri AS entity_uri
"""

#: The write-time validity projections the pushed `GQ-09` cut compares.
_VALIDITY_PROBE = """
    MATCH (c:CcfEntityClaim {ccf_partition: $partition, ccf_tenant_id: $tenant,
                             ccf_entity_uri: $key})
    RETURN c.ccf_valid_from_cmp AS valid_from_cmp,
           c.ccf_valid_to_cmp AS valid_to_cmp
"""

# --- F-A2 / F-A3 probe statements (plan 15.3-04, at stage-2 promotion) --------
#
# Spelled out here rather than imported from the adapter, for the same reason
# the layout probes above are: a probe that shares its statement text with the
# module under test can be changed in lockstep with the thing it is supposed to
# pin. `{bound}` is the ONE placeholder, and it is filled with an int by the
# probe itself — F-A2 exists precisely to establish that this cannot be a
# `$param`.

#: F-A2's two candidate forms. Both carry `{"depth": 2}` in `params`.
_FA2_CLASSIC = (
    "MATCH p = (a:CcfEntity)-[:CCF_LINK*1..$depth]-(b:CcfEntity)"
    " RETURN count(p) AS n"
)
_FA2_QUANTIFIED = (
    "MATCH p = (a:CcfEntity)-[:CCF_LINK{1,$depth}]-(b:CcfEntity)"
    " RETURN count(p) AS n"
)

#: The walk's scoped seed. Assembled from fragments rather than written as one
#: block so the ``{bound}`` the probe fills is the only variable part — which
#: is the shape F-A2 exists to establish.
_FA3_SEED = (
    "MATCH p = (seed:CcfEntity {ccf_partition: $partition,"
    " ccf_tenant_id: $tenant})"
)
#: F-A3(f)'s counterfactual seed: the same pattern with the scope terms gone.
_FA3_SEED_UNSCOPED = "MATCH p = (seed:CcfEntity)"
_FA3_TERMINAL = "(x:CcfEntity)\nWHERE seed.ccf_admit_key IN $starts\n"
#: Hop admissibility as ONE node predicate over ONE prefix-namespaced parameter
#: list. No relationship property is read anywhere in it.
_FA3_ADMISSIBLE = (
    "  AND all(n IN nodes(p) WHERE n.ccf_admit_key IN $admissible)\n"
)
_FA3_REACH_RETURN = "RETURN DISTINCT x.ccf_entity_uri AS entity_uri"
#: F-A3(b)'s stronger half: the count of paths, not the set of endpoints. Zero
#: paths is "the path does not exist"; an empty endpoint set alone would also be
#: consistent with "the path exists and its endpoint was filtered out of the
#: output", which is a different and much weaker claim (threat T-15.2-26).
_FA3_PATH_COUNT_RETURN = (
    "  AND x.ccf_entity_uri = $endpoint\nRETURN count(p) AS paths"
)
#: F-A3(d): ``type(r)`` over ``relationships(p)`` — value-only relationship use.
_FA3_TYPES_RETURN = "RETURN [r IN relationships(p) | type(r)] AS types"
#: F-A3(e): ``r.<prop>`` over the same values — the Break-1 confirmation. This
#: is the ONE place in the tree a relationship property is read, and it is here
#: to prove the read returns nothing.
_FA3_PROPS_RETURN = (
    "RETURN [r IN relationships(p) | r.ccf_admit_key] AS props"
)


def _fa3_walk(
    bound: int,
    *,
    tail: str,
    admissible: bool = False,
    scoped: bool = True,
) -> str:
    """Assemble one probe walk at ``bound`` Cypher hops.

    The bound is rendered as a literal because F-A2 measured that it cannot be
    a ``$param`` — which is the whole reason the adapter needs a validated
    formatting site at all.
    """
    seed = _FA3_SEED if scoped else _FA3_SEED_UNSCOPED
    body = f"{seed}-[:CCF_LINK*1..{bound}]-{_FA3_TERMINAL}"
    if admissible:
        body += _FA3_ADMISSIBLE
    return body + tail

#: Overrides the container name assertion (7) runs ``docker exec`` against. In
#: CI the server is an Actions service container with a generated name, so the
#: sub-assertion records "not applicable" rather than failing there.
FLUREE_CONTAINER_ENV = "CCF_TEST_FLUREE_CONTAINER"

#: The documented standalone-server API base. Assertion (2) discovers this from
#: ``/.well-known/fluree.json`` rather than hard-coding it, and falls back to
#: this literal only if the well-known document omits it.
DEFAULT_API_BASE = "/v1/fluree"

#: Probe timeout. Generous: a cold ledger create on a fresh container does
#: real work, and a flaky probe is worse than a slow one.
TIMEOUT = 30.0


def _fresh_ledger() -> str:
    """A ledger nobody has created yet, so 201-then-409 is deterministic.

    D-03 gives production **one** CCF-owned ledger, but a probe that asserts
    the idempotent-bootstrap contract has to observe the 201 as well as the
    409 — and on a container that outlives the test run, a fixed name makes
    the first assertion depend on run order.
    """
    return f"ccf:probe-{uuid.uuid4().hex}"


def _api_base(client: httpx.Client, url: str) -> tuple[str, str]:
    """Discover the API base, returning ``(base_url, discovered_value)``.

    The adapter reads the well-known document once at construction rather than
    hard-coding ``/v1/fluree``, which is what makes it correct behind a
    differently-mounted server (15.3-RESEARCH.md §R2).
    """
    response = client.get(f"{url}/.well-known/fluree.json")
    assert response.status_code == 200, response.text
    discovered = response.json().get("api_base_url", "")
    base = discovered or DEFAULT_API_BASE
    return f"{url}{base}", discovered


def _cypher(
    client: httpx.Client,
    base: str,
    ledger: str,
    statement: str,
    params: Mapping[str, Any] | None = None,
    min_t: int | None = None,
) -> httpx.Response:
    """One parameterized Cypher read over HTTP.

    ``Content-Type: application/cypher`` with the JSON envelope
    ``{"cypher": ..., "params": ...}``. Because the body is Cypher rather than
    a JSON-LD query document, the ``Fluree-Min-T`` **header** is the only
    read-after-write form available — ``opts.min-t`` lives in a JSON-LD body.
    """
    headers = {"Content-Type": "application/cypher"}
    if min_t is not None:
        headers["Fluree-Min-T"] = str(min_t)
    body: dict[str, Any] = {"cypher": statement}
    if params is not None:
        body["params"] = dict(params)
    return client.post(
        f"{base}/query/{ledger}", headers=headers, content=json.dumps(body)
    )


def _rows(response: httpx.Response) -> list[dict[str, Any]]:
    """Extract rows from the cypher-json envelope, as observed — not as documented.

    ``query/output-formats.md`` documents JSON-LD / SPARQL-JSON / typed-JSON /
    AgentJson and **does not describe cypher-json's row structure at all**
    (15.3-RESEARCH.md §R2). The shape below was captured verbatim by F-A1
    assertion (6) against ``fluree/server:4.1.4``::

        {"results":[{"columns":["entity_uri"],
                     "data":[{"row":["counterparty://acme"],"meta":[null]}]}]}

    which is the Neo4j-HTTP tabular envelope. Plan 15.3-02's ``_query`` writes
    its extraction against these bytes; ``dict(zip(columns, row))`` is what
    makes rows satisfy ``ccf.graph.reader.Row`` for ``materialize_view``.
    """
    result = response.json()["results"][0]
    columns: Sequence[str] = result["columns"]
    return [
        dict(zip(columns, entry["row"], strict=True)) for entry in result["data"]
    ]


def _insert(
    client: httpx.Client, base: str, ledger: str, nodes: Sequence[Mapping[str, Any]]
) -> httpx.Response:
    """One ground JSON-LD insert with the fixed zero-coercion ``@context``.

    ``"@context": {}`` — no ``@vocab``, no ``@base``, no term definitions and
    therefore no datatype coercion (15.3-RESEARCH.md §R3). Adding ``@vocab`` to
    a ledger whose data was written bare changes what every Cypher statement
    matches, so the empty context is a hard condition of D-02, not a style.
    """
    body = {"@context": {}, "insert": list(nodes)}
    return client.post(
        f"{base}/update/{ledger}",
        headers={"Content-Type": "application/json"},
        content=json.dumps(body),
    )


def _sparql(
    client: httpx.Client, base: str, ledger: str, query: str
) -> httpx.Response:
    """One SPARQL read — a diagnostic assertion, never the read path.

    D-02's "Cypher reads" governs the adapter's ``query()``; it does not
    govern a probe. ``DATATYPE()`` is the only way to read a literal's datatype
    back directly, and ``v4.0.7`` shipped the fix that makes it return the
    datatype **IRI** rather than a compact string — so the answer here is
    unambiguous in a way no Cypher expression could be.
    """
    return client.post(
        f"{base}/query/{ledger}",
        headers={
            "Content-Type": "application/sparql-query",
            "Accept": "application/sparql-results+json",
        },
        content=query,
    )


def _bootstrap(client: httpx.Client, url: str) -> tuple[str, str]:
    """Discover the API base and create a fresh probe ledger."""
    base, _ = _api_base(client, url)
    ledger = _fresh_ledger()
    created = client.post(
        f"{base}/create",
        headers={"Content-Type": "application/json"},
        content=json.dumps({"ledger": ledger}),
    )
    assert created.status_code == 201, created.text
    return base, ledger


def _assert_context_is_null(client: httpx.Client, base: str, ledger: str) -> None:
    """D-02's other half, re-asserted after writes (Pitfall 9).

    A default ``@context`` — above all one carrying ``@vocab`` — silently
    changes what every Cypher statement matches while writes keep succeeding.
    Cheap to check, and it catches a future change that starts setting one.
    """
    context = client.get(f"{base}/context/{ledger}")
    assert context.status_code == 200, context.text
    assert context.json() == {"@context": None}, context.text


#: The six temporal properties the adapter will write. ``ccf_valid_from_cmp``
#: and ``ccf_valid_to_cmp`` are NOT optional here: §R8 vector 2 is exactly
#: where DI-15.2-03 (closed by D-IMPL-90) could re-enter through the wire, and
#: they are the properties the pushed `GQ-09` validity predicate compares.
TEMPORAL_PROPERTIES = (
    "ccf_observed_at",
    "ccf_superseded_at",
    "ccf_valid_from_cmp",
    "ccf_valid_to_cmp",
    "ccf_first_observed_at",
    "ccf_last_observed_at",
)

#: Separator for the materialized policy key. Code-authored and impossible in
#: a CCF class or attribute name, so no artifact-authored string can forge a
#: key boundary — the F-A6 resolution's whole safety argument.
POLICY_KEY_SEP = "\x00"


def _policy_key(entity_class: str, attr_name: str, attr_value: str) -> str:
    """One materialized policy key — `GQ-08`'s three cuts as pure membership."""
    return f"{entity_class}{POLICY_KEY_SEP}{attr_name}{POLICY_KEY_SEP}{attr_value}"


#: The supersession value F-A4(a)'s ground retraction removes, and which its
#: positive control proves survives when the retraction is absent.
SUPERSEDED_OLD = "2026-03-09T00:00:00.000000Z"

#: The supersession value both bodies assert.
SUPERSEDED_NEW = "2026-03-10T00:00:00.000000Z"


def _seed_supersession(client: httpx.Client, base: str, ledger: str) -> None:
    """Commit the claim both F-A4(a) and its control then update."""
    _insert(
        client,
        base,
        ledger,
        [
            {
                "@id": "ccf_c_sup1",
                "@type": "CcfEntityClaim",
                "ccf_tenant_id": "tenant-sup",
                "ccf_claim_id": "sup1",
                "ccf_superseded_at": SUPERSEDED_OLD,
            }
        ],
    ).raise_for_status()


def _supersession_batch(*, retract: bool) -> dict[str, Any]:
    """The F-A4(a) batch, with or without the ground retraction.

    ONE constructor for both the probe and its positive control, deliberately:
    the only difference between the two bodies must be the presence of the
    retraction key. Built separately they would drift, and the control would
    stop controlling for the thing F-A4(a) actually claims.
    """
    batch: dict[str, Any] = {
        "@context": {},
        "insert": [
            {"@id": "ccf_c_sup1", "ccf_superseded_at": SUPERSEDED_NEW},
            {
                "@id": "ccf_c_new2",
                "@type": "CcfEntityClaim",
                "ccf_tenant_id": "tenant-sup",
                "ccf_claim_id": "new2",
            },
        ],
    }
    if retract:
        batch["delete"] = [{"@id": "ccf_c_sup1", "ccf_superseded_at": SUPERSEDED_OLD}]
    return batch


def _read_supersession(
    client: httpx.Client, base: str, ledger: str, applied: httpx.Response
) -> httpx.Response:
    """Read every supersession value back, at the commit just applied."""
    readback = _cypher(
        client,
        base,
        ledger,
        "MATCH (n:CcfEntityClaim) WHERE n.ccf_tenant_id = $t "
        "RETURN n.ccf_claim_id AS claim_id, n.ccf_superseded_at AS superseded_at",
        params={"t": "tenant-sup"},
        min_t=int(applied.json()["t"]),
    )
    assert readback.status_code == 200, readback.text
    return readback


@pytest.mark.fluree
def test_fa1_container_round_trip(fluree_url: str) -> None:
    """F-A1: the pinned container answers, and the read envelope is recorded.

    The nine assertions of 15.3-RESEARCH.md §R4 F-A1, in order, against
    ``fluree/server:4.1.4``. Assertion (6) is the load-bearing one: the
    cypher-json response envelope is documented nowhere, so it is captured
    **verbatim** here and in the plan SUMMARY, and plan 15.3-02's row
    extraction is written against those bytes rather than against a guess.

    Assertions (8) and (9) are additions this plan makes to the research's
    seven, recorded as assumptions **A11** and **A12**: every one of the five
    acquisition statements plan 15.3-02 copies from
    ``src/ccf/graph/backends/neo4j.py::Neo4jGraphReader``
    orders on *two* keys and matches with an inline map pattern, and neither
    shape appears in §R1's confirm/refute table. Probed, not assumed.
    """
    evidence: dict[str, Any] = {}
    ledger = _fresh_ledger()

    with httpx.Client(timeout=TIMEOUT) as client:
        # (1) Health at the server root — NOT under the API base path.
        health = client.get(f"{fluree_url}/health")
        assert health.status_code == 200, health.text
        payload = health.json()
        assert "status" in payload
        assert "version" in payload
        evidence["health"] = payload
        # A version that is not 4.1.4 means the pin is not what ran, and every
        # probe below would be evidence about a different build (D-09).
        assert payload["version"] == "4.1.4", (
            f"pin drift: /health reports {payload['version']!r}, expected '4.1.4'"
        )

        # (2) API base discovery.
        base, discovered = _api_base(client, fluree_url)
        evidence["api_base_url"] = discovered or f"ABSENT (fell back to {DEFAULT_API_BASE})"
        assert discovered == DEFAULT_API_BASE, evidence["api_base_url"]

        # (3) Idempotent ledger bootstrap: 201 once, 409 forever after. Under
        # D-03 every boot after the first sees the 409, so treating it as
        # success is the contract, not a tolerance.
        created = client.post(
            f"{base}/create",
            headers={"Content-Type": "application/json"},
            content=json.dumps({"ledger": ledger}),
        )
        assert created.status_code == 201, created.text
        again = client.post(
            f"{base}/create",
            headers={"Content-Type": "application/json"},
            content=json.dumps({"ledger": ledger}),
        )
        assert again.status_code == 409, again.text
        evidence["create_conflict"] = again.json()

        # (4) D-02's no-default-context condition, asserted rather than assumed.
        # POST /create has no context parameter, so a fresh ledger has none —
        # a non-null value means something called PUT /context, and every
        # Cypher statement would then match different data (Pitfall 9).
        context = client.get(f"{base}/context/{ledger}")
        assert context.status_code == 200, context.text
        assert context.json() == {"@context": None}, context.text

        # (5) One-node ground insert. Colonless @id, colonless @type, code-
        # authored `ccf_`-prefixed property names; the entity URI travels as a
        # string literal, where the strict compact-IRI guard does not apply.
        receipt_response = _insert(
            client,
            base,
            ledger,
            [
                {
                    "@id": "ccf_e_probe_a",
                    "@type": "CcfEntityClaim",
                    "ccf_partition": "ccf",
                    "ccf_tenant_id": "tenant-a",
                    "ccf_entity_uri": "counterparty://acme",
                    "ccf_claim_id": "claim-1",
                    "ccf_observed_at": "2026-03-01T00:00:00.000000Z",
                }
            ],
        )
        assert receipt_response.status_code == 200, receipt_response.text
        receipt = receipt_response.json()
        evidence["commit_receipt"] = receipt
        assert "t" in receipt, receipt
        commit_t = int(receipt["t"])

        # FALSIFIED ASSUMPTION, recorded rather than smoothed over (assumption
        # A13). 15.3-RESEARCH.md §R2 quotes a documented receipt carrying
        # `flakes_added`, `flakes_retracted` and `previous_commit_id`. This
        # build returns NONE of them — only `ledger_id`, `t`, `tx-id` and
        # `commit.hash` (plus `time`/`fuel`/`policy` under `opts.meta`). The
        # consequence is bounded and is recorded in the plan SUMMARY: F-A4's
        # `flakes_added` cross-check DOES NOT EXIST on this server, so the
        # `_GraphTxn` per-operation rowcount contract rests entirely on
        # read-before-buffer plus own-buffer — which is what `_MongoTxn`
        # already does, and which the contract was written to permit
        # (`src/ccf/graph/_writer.py::_claim_payload`). Nothing depends on
        # the cross-check.
        assert "flakes_added" not in receipt, (
            "flakes_added reappeared — re-cost the F-A4(d) cross-check: " f"{receipt}"
        )

        # (6) The undocumented read envelope. Captured verbatim.
        read = _cypher(
            client,
            base,
            ledger,
            "MATCH (n:CcfEntityClaim) WHERE n.ccf_tenant_id = $t "
            "RETURN n.ccf_entity_uri AS entity_uri",
            params={"t": "tenant-a"},
            min_t=commit_t,
        )
        assert read.status_code == 200, read.text
        evidence["cypher_json_verbatim"] = read.text
        evidence["cypher_content_type"] = read.headers.get("content-type", "")
        # `X-Fluree-T` is documented as carrying the transaction time of the
        # data returned. This build does not send it on the Cypher route —
        # recorded, and harmless: `Fluree-Min-T` on the request is what makes
        # read-after-write correct, and it was honoured above.
        evidence["x_fluree_t"] = read.headers.get("X-Fluree-T", "ABSENT")
        assert _rows(read) == [{"entity_uri": "counterparty://acme"}], read.text

        # (7) `curl` in the image — what ci.yml's --health-cmd depends on
        # (D-08). If a future image drops it, the healthcheck must move to a
        # runner-side wait loop, and this is the assertion that catches it.
        evidence["curl_in_image"] = _curl_in_image()

        # (8) A11 — multi-key ORDER BY over a string key then an integer key,
        # the mixed-type shape every acquisition statement needs.
        ordered_tenant = "tenant-order"
        _insert(
            client,
            base,
            ledger,
            [
                {
                    "@id": f"ccf_c_order_{index}",
                    "@type": "CcfOrderProbe",
                    "ccf_tenant_id": ordered_tenant,
                    "ccf_claim_id": f"c{index}",
                    "ccf_observed_at": "2026-03-01T00:00:00.000000Z",
                    "ccf_seq": index,
                }
                for index in (0, 1)
            ],
        ).raise_for_status()
        ordered = _cypher(
            client,
            base,
            ledger,
            "MATCH (c:CcfOrderProbe) WHERE c.ccf_tenant_id = $t "
            "RETURN c.ccf_claim_id AS claim_id, c.ccf_observed_at AS observed_at, "
            "c.ccf_seq AS seq ORDER BY c.ccf_observed_at, c.ccf_seq",
            params={"t": ordered_tenant},
        )
        assert ordered.status_code == 200, ordered.text
        evidence["a11_multi_key_order_by"] = ordered.text
        assert [row["claim_id"] for row in _rows(ordered)] == ["c0", "c1"], ordered.text

        # (9) A12 — the inline map pattern, and that it agrees with the
        # WHERE-clause form of the same question.
        inline = _cypher(
            client,
            base,
            ledger,
            "MATCH (c:CcfOrderProbe {ccf_tenant_id: $t}) RETURN count(c) AS n",
            params={"t": ordered_tenant},
        )
        assert inline.status_code == 200, inline.text
        evidence["a12_inline_map_pattern"] = inline.text
        where_form = _cypher(
            client,
            base,
            ledger,
            "MATCH (c:CcfOrderProbe) WHERE c.ccf_tenant_id = $t RETURN count(c) AS n",
            params={"t": ordered_tenant},
        )
        assert where_form.status_code == 200, where_form.text
        assert _rows(inline) == _rows(where_form) == [{"n": 2}], inline.text

    print("\nF-A1 evidence:\n" + json.dumps(evidence, indent=2, sort_keys=True))


def _curl_in_image() -> str:
    """Is `curl` present in the running image? Recorded, asserted when knowable.

    In CI the Fluree server is an Actions service container whose name this
    process does not know, so the sub-assertion degrades to a recorded "not
    applicable" rather than a failure. Locally, where the container name is
    known, an absent `curl` is a real failure.
    """
    container = os.environ.get(FLUREE_CONTAINER_ENV, "ccf-fluree-15-3")
    if shutil.which("docker") is None:
        return "not applicable: no docker on PATH"
    exists = subprocess.run(  # noqa: S603
        ["docker", "inspect", "--format", "{{.State.Running}}", container],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    if exists.returncode != 0 or exists.stdout.strip() != "true":
        return f"not applicable: no running container named {container!r}"
    probe = subprocess.run(  # noqa: S603
        ["docker", "exec", container, "curl", "--version"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    assert probe.returncode == 0, (
        "`curl` is absent from the image — ci.yml's --health-cmd must move to a "
        f"runner-side wait loop (D-08): {probe.stderr.strip()}"
    )
    return probe.stdout.splitlines()[0]


@pytest.mark.fluree
def test_fa5_no_datatype_coercion(fluree_url: str) -> None:
    """F-A5: temporal text stays ``xsd:string``. D-02's hard condition.

    Asserted three independent ways because a wrong answer here is **silent**.
    Fluree documents that ordering between incompatible types raises, *but
    also* that "temporal types can be compared with string representations
    that parse to the same temporal type" — so a column coerced to
    ``xsd:dateTime`` compared against a string boundary does **not** error. It
    compares temporally, at whatever precision the engine normalizes to, and
    the as-of cut would keep "working" while diverging from the fallback on
    sub-precision boundaries only. Scattered differential failures, never an
    exception. That is why D-06 puts this probe up front, and why a failure
    here is rung 3: lexicographic-equals-chronological is what makes ``as_of``
    *mean* the same thing on this substrate as on the other four.
    """
    evidence: dict[str, Any] = {}

    with httpx.Client(timeout=TIMEOUT) as client:
        base, ledger = _bootstrap(client, fluree_url)

        # (a) Direct datatype read, over all six temporal properties at once.
        instant = "2026-03-01T00:00:00.000000Z"
        _insert(
            client,
            base,
            ledger,
            [
                {
                    "@id": "ccf_e_datatypes",
                    "@type": "CcfEntityClaim",
                    "ccf_tenant_id": "tenant-dt",
                    **{name: instant for name in TEMPORAL_PROPERTIES},
                }
            ],
        ).raise_for_status()

        datatypes: dict[str, str] = {}
        for name in TEMPORAL_PROPERTIES:
            response = _sparql(
                client,
                base,
                ledger,
                f"SELECT ?v (DATATYPE(?v) AS ?dt) WHERE {{ ?s <{name}> ?v }}",
            )
            assert response.status_code == 200, response.text
            bindings = response.json()["results"]["bindings"]
            assert bindings, f"{name} bound nothing: {response.text}"
            datatypes[name] = bindings[0]["dt"]["value"]
        evidence["datatypes"] = datatypes

        assert set(datatypes.values()) == {
            "http://www.w3.org/2001/XMLSchema#string"
        }, datatypes

        # (b) Behavioural: microsecond granularity actually discriminates. A
        # substrate that coerced to xsd:dateTime at millisecond precision
        # would collapse these two and would NOT error.
        earlier, later = instant, "2026-03-01T00:00:00.000001Z"
        _insert(
            client,
            base,
            ledger,
            [
                {
                    "@id": f"ccf_e_micro_{suffix}",
                    "@type": "CcfMicroProbe",
                    "ccf_tenant_id": "tenant-us",
                    "ccf_claim_id": suffix,
                    "ccf_observed_at": value,
                }
                for suffix, value in (("us0", earlier), ("us1", later))
            ],
        ).raise_for_status()

        discriminated = _cypher(
            client,
            base,
            ledger,
            "MATCH (c:CcfMicroProbe) WHERE c.ccf_tenant_id = $t "
            "AND c.ccf_observed_at > $boundary RETURN c.ccf_claim_id AS claim_id",
            params={"t": "tenant-us", "boundary": earlier},
        )
        assert discriminated.status_code == 200, discriminated.text
        evidence["microsecond_discrimination"] = discriminated.text
        assert _rows(discriminated) == [{"claim_id": "us1"}], discriminated.text

        # (c) The ledger context is still null after every write above.
        _assert_context_is_null(client, base, ledger)

    print("\nF-A5 evidence:\n" + json.dumps(evidence, indent=2, sort_keys=True))


@pytest.mark.fluree
def test_fa6_dynamic_property_access(fluree_url: str) -> None:
    """F-A6: is ``c[$key]`` available for the policy family? Settled before stage 1.

    This binds **stage 1**, not stage 2 — the policy family is a non-traverse
    predicate family — so by D-06's consequence-not-convenience logic it
    belongs up front beside F-A4/F-A5.

    The verdict is taken by **comparison against a static-access control**, not
    by status code, because the observed failure mode is silent: ``c[$key]``
    parses, returns ``200``, and evaluates to null. A verdict taken from the
    status alone would have read "supported" and shipped a policy predicate
    that excludes every claim.

    On the expected FAIL the resolution is proven in this same test, so plan
    15.3-03 inherits a design that was measured rather than sketched: a
    multi-valued ``ccf_policy_key`` property carrying
    ``entity_class \\0 attr_name \\0 attr_value``, selected by plain membership.
    Ladder: rung 1 (materialization) → rung 2 (decline the translation when the
    policy family is present). Never rung 3.
    """
    evidence: dict[str, Any] = {}

    with httpx.Client(timeout=TIMEOUT) as client:
        base, ledger = _bootstrap(client, fluree_url)

        _insert(
            client,
            base,
            ledger,
            [
                {
                    "@id": "ccf_e_dyn",
                    "@type": "CcfEntityClaim",
                    "ccf_tenant_id": "tenant-dyn",
                    "ccf_entity_class": "Counterparty",
                }
            ],
        ).raise_for_status()

        control = _cypher(
            client,
            base,
            ledger,
            "MATCH (c:CcfEntityClaim) WHERE c.ccf_tenant_id IN $values "
            "RETURN count(c) AS n",
            params={"values": ["tenant-dyn"]},
        )
        assert control.status_code == 200, control.text
        assert _rows(control) == [{"n": 1}], control.text

        dynamic = _cypher(
            client,
            base,
            ledger,
            "MATCH (c:CcfEntityClaim) WHERE c[$key] IN $values RETURN count(c) AS n",
            params={"key": "ccf_tenant_id", "values": ["tenant-dyn"]},
        )
        evidence["dynamic_status"] = dynamic.status_code
        evidence["dynamic_body"] = dynamic.text
        supported = dynamic.status_code == 200 and _rows(dynamic) == _rows(control)
        evidence["fa6_verdict"] = "PASS" if supported else "FAIL"
        assert not supported, (
            "c[$key] now agrees with static access — re-cost the stage-1 policy "
            "family: _ENTITY_POLICY (backends/neo4j.py:335-340) may port with "
            f"only the ccf_ prefix changed. {dynamic.text}"
        )

        # --- the resolution, proven end to end (assumption A7) --------------
        #
        # A7 as the plan names it — `any(k IN $keys WHERE k IN c.prop)` — is
        # REJECTED at parse time: "`IN` right-hand side must be an inline list
        # `[a, b, ...]` in v1". A property expression cannot be an IN operand.
        # But a `$param` list CAN (the control above proves it), and a
        # multi-valued property FANS OUT into one row per value rather than
        # yielding a list — so plain `c.ccf_policy_key IN $keys` expresses
        # exactly the intended "any materialized key is admissible", and
        # RETURN DISTINCT collapses the multiplicity.
        rejected = _cypher(
            client,
            base,
            ledger,
            "MATCH (c:CcfPolicyProbe) WHERE any(k IN $keys WHERE k IN c.ccf_policy_key) "
            "RETURN count(c) AS n",
            params={"keys": [_policy_key("Counterparty", "risk_tier", "tier-1")]},
        )
        evidence["a7_named_form"] = f"{rejected.status_code} {rejected.text}"
        assert rejected.status_code == 400, rejected.text

        _insert(
            client,
            base,
            ledger,
            [
                {
                    "@id": "ccf_e_pk1",
                    "@type": "CcfPolicyProbe",
                    "ccf_tenant_id": "tenant-pk",
                    "ccf_claim_id": "pk1",
                    "ccf_policy_key": [
                        _policy_key("Counterparty", "risk_tier", "tier-1"),
                        _policy_key("Counterparty", "region", "emea"),
                    ],
                },
                {
                    "@id": "ccf_e_pk2",
                    "@type": "CcfPolicyProbe",
                    "ccf_tenant_id": "tenant-pk",
                    "ccf_claim_id": "pk2",
                    "ccf_policy_key": [
                        _policy_key("Counterparty", "risk_tier", "tier-9")
                    ],
                },
            ],
        ).raise_for_status()

        statement = (
            "MATCH (c:CcfPolicyProbe) WHERE c.ccf_tenant_id = $t "
            "AND c.ccf_policy_key IN $keys "
            "RETURN DISTINCT c.ccf_claim_id AS claim_id"
        )

        def selected(keys: list[str]) -> set[str]:
            response = _cypher(
                client, base, ledger, statement, params={"t": "tenant-pk", "keys": keys}
            )
            assert response.status_code == 200, response.text
            return {row["claim_id"] for row in _rows(response)}

        # Selects the claim carrying the key, and only it.
        assert selected([_policy_key("Counterparty", "risk_tier", "tier-1")]) == {"pk1"}
        # Two admissible keys span both claims.
        assert selected(
            [
                _policy_key("Counterparty", "risk_tier", "tier-1"),
                _policy_key("Counterparty", "risk_tier", "tier-9"),
            ]
        ) == {"pk1", "pk2"}
        # A claim whose key is absent is inadmissible — GQ-08's third cut.
        assert selected([_policy_key("Counterparty", "risk_tier", "absent")]) == set()
        # The SECOND value of a multi-valued property selects too (fan-out).
        assert selected([_policy_key("Counterparty", "region", "emea")]) == {"pk1"}
        # The NUL separator discriminates: a near-miss value does not match.
        assert selected([_policy_key("Counterparty", "risk_tier", "tier-1x")]) == set()

        evidence["a7_working_form"] = statement
        _assert_context_is_null(client, base, ledger)

    print("\nF-A6 evidence:\n" + json.dumps(evidence, indent=2, sort_keys=True))


@pytest.mark.fluree
def test_fa4_ground_batch_semantics(fluree_url: str) -> None:
    """F-A4 (b)-(e): the ground buffered-batch write, measured.

    Sub-assertion (a) — a ground ``delete`` with no ``where`` — is Task 3's
    ruling gate and is deliberately NOT worked around here.

    **What these assertions do NOT establish.** The ``_GraphTxn`` contract
    needs **per-operation** rowcounts
    (``src/ccf/graph/_writer.py::_claim_payload``) and one POST
    yields at most **one** aggregate receipt, so a receipt field could only
    ever cross-check the sum — it could never implement the contract. On this
    build it cannot even do that: the receipt carries ``ledger_id``, ``t``,
    ``tx-id`` and ``commit.hash`` and **no ``flakes_added`` at all**, contrary
    to the shape 15.3-RESEARCH.md §R2 quotes from the docs. The consequence is
    bounded, because the contract is satisfied exactly as ``_MongoTxn``
    satisfies it: committed-state read before buffering, plus the txn's own
    buffer. The cross-check is a nicety this substrate does not offer.
    """
    evidence: dict[str, Any] = {}

    with httpx.Client(timeout=TIMEOUT) as client:
        base, ledger = _bootstrap(client, fluree_url)

        def batch_probe(index: int) -> dict[str, Any]:
            return {
                "@id": f"ccf_e_b{index}",
                "@type": "CcfBatchProbe",
                "ccf_tenant_id": "tenant-batch",
                "ccf_claim_id": f"b{index}",
                "ccf_observed_at": "2026-03-01T00:00:00.000000Z",
            }

        # (b) One POST touching three distinct subjects is ONE commit. This is
        # what makes a single-POST batch a transaction, and D-01 is a ratified
        # precondition of D-IMPL-88 — a failure here escalates.
        three = [batch_probe(index) for index in range(3)]
        first = _insert(client, base, ledger, three)
        assert first.status_code == 200, first.text
        first_receipt = first.json()
        evidence["multi_subject_receipt"] = first_receipt
        assert int(first_receipt["t"]) == 1, first_receipt

        second = _insert(client, base, ledger, [batch_probe(9)])
        assert second.status_code == 200, second.text
        assert int(second.json()["t"]) == 2, second.json()

        # (c) Re-asserting identical triples is a no-op in the DATA, which is
        # what RDF set semantics buys and what makes a claim re-arrival free.
        # It is NOT observable as `flakes_added == 0` (the field is absent);
        # what IS observable is that the content-addressed `tx-id` is byte
        # identical to the original, and that nothing duplicated.
        replay = _insert(client, base, ledger, three)
        assert replay.status_code == 200, replay.text
        replay_receipt = replay.json()
        evidence["reassert_receipt"] = replay_receipt
        assert replay_receipt["tx-id"] == first_receipt["tx-id"], (
            "a re-asserted identical body produced a different tx-id: "
            f"{replay_receipt} vs {first_receipt}"
        )
        # `t` DOES advance on the no-op — it counts commits, not flakes.
        assert int(replay_receipt["t"]) == 3, replay_receipt

        counted = _cypher(
            client, base, ledger, "MATCH (n:CcfBatchProbe) RETURN count(n) AS n"
        )
        assert _rows(counted) == [{"n": 4}], counted.text

        # (d) The receipt arithmetic, measured against a claim of KNOWN triple
        # count k: one @type triple + four data properties = 5.
        known = {
            "@id": "ccf_e_k1",
            "@type": "CcfCountProbe",
            "ccf_tenant_id": "tenant-k",
            "ccf_claim_id": "k1",
            "ccf_observed_at": "2026-03-01T00:00:00.000000Z",
            "ccf_entity_uri": "counterparty://k",
        }
        sized = _insert(client, base, ledger, [known])
        assert sized.status_code == 200, sized.text
        sized_receipt = sized.json()
        evidence["k"] = 5
        evidence["k_receipt"] = sized_receipt
        evidence["flakes_added"] = sized_receipt.get("flakes_added", "ABSENT")
        assert "flakes_added" not in sized_receipt, sized_receipt

        # (e) Read-before-buffer is correct: the committed claim is visible to
        # a plain existence read, which is exactly what lets a second
        # insert_entity_claim for the same identity resolve to 0 BEFORE
        # commit, with no post-commit round trip. INV-CH7-10 single-writer is
        # what makes that pre-commit read authoritative.
        existence = (
            "MATCH (n:CcfCountProbe) WHERE n.ccf_tenant_id = $t "
            "AND n.ccf_claim_id = $c RETURN count(n) AS n"
        )
        held = _cypher(
            client, base, ledger, existence, params={"t": "tenant-k", "c": "k1"}
        )
        assert _rows(held) == [{"n": 1}], held.text
        absent = _cypher(
            client, base, ledger, existence, params={"t": "tenant-k", "c": "nope"}
        )
        assert _rows(absent) == [{"n": 0}], absent.text

        _assert_context_is_null(client, base, ledger)

    print("\nF-A4 evidence:\n" + json.dumps(evidence, indent=2, sort_keys=True))


@pytest.mark.fluree
def test_fa4a_ground_delete_without_a_guard_clause(fluree_url: str) -> None:
    """F-A4(a): a ground ``delete`` + ``insert`` with no guard clause — the ruling gate.

    This is the assertion the buffered commit primitive rests on. A JSON-LD
    update body carries **one** guard, **one** ``delete`` and **one**
    ``insert``, so independent conditional operations cannot compose — their
    guards would join, not union. Read-before-buffer plus ``INV-CH7-10``
    single-writer already give the adapter the committed state at commit time,
    so every conditional is resolvable in Python and the batch should need no
    guard at all.

    A ground ``insert`` with no guard is documented (the plain insert path). A
    ground ``delete`` with no guard — the JSON-LD analogue of SPARQL's
    ``DELETE DATA`` — is **not** documented, which is why this is a probe and
    not an assumption.

    **The follow-up read is the real assertion, not the 200.** The F-A6 probe
    established that a multi-valued property fans out into one row per value,
    so an ignored ``delete`` would leave the subject carrying BOTH supersession
    values and the read would return two rows. One row, carrying the new
    value, is therefore positive evidence that the retraction actually applied
    — not merely that the request was accepted.

    Deliberately NOT worked around: a guard-bearing body that mixed a
    conditional update with unrelated ground inserts would silently drop the
    inserts whenever the guard missed, which is the documented trap
    (``transactions/conditional-updates.md``) and exactly the failure this
    phase cannot afford.
    """
    evidence: dict[str, Any] = {}

    with httpx.Client(timeout=TIMEOUT) as client:
        base, ledger = _bootstrap(client, fluree_url)
        _seed_supersession(client, base, ledger)

        batch = _supersession_batch(retract=True)
        assert set(batch) == {"@context", "delete", "insert"}, batch
        evidence["request_body"] = batch

        applied = client.post(
            f"{base}/update/{ledger}",
            headers={"Content-Type": "application/json"},
            content=json.dumps(batch),
        )
        evidence["status"] = applied.status_code
        evidence["receipt"] = applied.text
        assert applied.status_code == 200, applied.text

        readback = _read_supersession(client, base, ledger, applied)
        evidence["follow_up_read"] = readback.text
        rows = _rows(readback)

        # The retraction applied: exactly one supersession value, the new one.
        # `test_fa4a_control_...` proves this discriminator has power.
        superseded = [row for row in rows if row["claim_id"] == "sup1"]
        assert superseded == [
            {"claim_id": "sup1", "superseded_at": SUPERSEDED_NEW}
        ], readback.text
        # The assertion applied in the same commit.
        assert {"claim_id": "new2", "superseded_at": None} in rows, readback.text

        _assert_context_is_null(client, base, ledger)

    print("\nF-A4(a) evidence:\n" + json.dumps(evidence, indent=2, sort_keys=True))


@pytest.mark.fluree
def test_fa4a_control_an_unretracted_value_survives_alongside_the_new_one(
    fluree_url: str,
) -> None:
    """F-A4(a)'s POSITIVE CONTROL: without the retraction, BOTH values persist.

    This test exists because F-A4(a)'s conclusion rests on a premise that was
    itself unmeasured. F-A4(a) reads "exactly one supersession value, therefore
    the ground ``delete`` applied" — which only follows if an *un*-retracted
    old value would have produced TWO rows. F-A6 established multi-value
    fan-out for a property inserted as an explicit **array**, but not for a
    property written by two **separate inserts** on an existing subject. Those
    are the same RDF semantic, but this phase's own D-06 discipline is to
    measure rather than infer precisely because this class of thing fails
    silently: had Fluree done last-write-wins on a scalar, F-A4(a) would have
    returned one row whether or not the delete applied, and the probe would
    have "passed" while proving nothing.

    So this runs the identical batch with the ``delete`` key removed and
    asserts both values survive. Both bodies come from
    :func:`_supersession_batch` so the only difference between them is the
    retraction — if they were built separately they could drift, and the
    control would stop controlling for the right thing.

    Keep this test. Without it F-A4(a) silently loses its discriminating power
    the day the substrate changes that semantic, which is exactly the
    silent-failure shape this plan exists to catch.
    """
    evidence: dict[str, Any] = {}

    with httpx.Client(timeout=TIMEOUT) as client:
        base, ledger = _bootstrap(client, fluree_url)
        _seed_supersession(client, base, ledger)

        batch = _supersession_batch(retract=False)
        assert "delete" not in batch, batch
        evidence["request_body"] = batch

        applied = client.post(
            f"{base}/update/{ledger}",
            headers={"Content-Type": "application/json"},
            content=json.dumps(batch),
        )
        assert applied.status_code == 200, applied.text

        readback = _read_supersession(client, base, ledger, applied)
        evidence["follow_up_read"] = readback.text
        rows = _rows(readback)

        # The discriminator has power: the old value SURVIVES beside the new
        # one, fanning out into two rows for the same subject.
        superseded = sorted(
            (row["superseded_at"] for row in rows if row["claim_id"] == "sup1"),
            key=str,
        )
        assert superseded == [SUPERSEDED_OLD, SUPERSEDED_NEW], readback.text

    print("\nF-A4(a) control evidence:\n" + json.dumps(evidence, indent=2, sort_keys=True))


# --- F-A2 / F-A3: the two probes that bind stage 2 (plan 15.3-04) ------------
#
# D-06 puts these HERE, at the stage-2 boundary, rather than up front with
# F-A1/F-A4/F-A5/F-A6: they gate only stage 2 and they fail **loudly** — a
# rejected pattern is a 400, not a silently empty answer. They still run before
# any promotion code exists, which is the half of D-06 that matters.


def _extended_chain() -> tuple[
    "tuple[Any, ...]", "tuple[Any, ...]", tuple[str, str, str, str]
]:
    """The corpus chain with one more hop, so depth 3 is distinguishable.

    ``chain_claims`` is a two-hop mixed-direction chain (seed - mid - target);
    a third hop is what makes an off-by-factor-of-two in the CCF-depth-to-
    Cypher-hop arithmetic **visible**, because at depth >= 2 a doubled bound
    over-reaches by exactly one CCF hop and a halved one under-reaches by one
    (15.3-RESEARCH.md Pitfall 13). The extra edge reuses the ontology's own
    second rule, so no class or type is named in test code (CLAUDE.md §6.4).
    """
    entities, relationships = chain_claims(
        mid_classification=PERMITTED_CLASSIFICATION
    )
    seed_uri, mid_uri, target_uri = chain_uris()
    far_uri = ENTITY_POOL[MID_CLASS][1]
    entities = (
        *entities,
        entity_claim(
            entity_uri=far_uri,
            entity_class=MID_CLASS,
            classification=PERMITTED_CLASSIFICATION,
            observed_at=EARLY,
        ),
    )
    relationships = (
        *relationships,
        relationship_claim(
            relationship_type=_RULE_B[0],
            subject_uri=target_uri,
            object_uri=far_uri,
            observed_at=EARLY,
        ),
    )
    return entities, relationships, (seed_uri, mid_uri, target_uri, far_uri)


def _admit_keys(
    handle: "FabricHandle", entity_uris: "Sequence[str]"
) -> list[str]:
    """Every admissibility key of the graph this handle owns.

    Built the way the adapter builds it — ``e:``-prefixed entity URIs union
    ``r:``-prefixed relationship keys — but assembled here from the write
    results rather than imported, so the probe pins the layout instead of
    agreeing with itself.
    """
    keys = ["e:" + uri for uri in entity_uris]
    rows = handle.reader._store.post_query(
        "MATCH (e:CcfEdge {ccf_partition: $partition, ccf_tenant_id: $tenant})"
        " RETURN DISTINCT e.ccf_admit_key AS admit_key",
        handle.reader._store.scope(TENANT),
    )
    return keys + [row["admit_key"] for row in rows]


def _write_chain(
    handle: "FabricHandle",
    entities: "Sequence[Any]",
    relationships: "Sequence[Any]",
) -> None:
    """Admit a chain through booted L2 — never straight at the store.

    The interposed layout under test has to be the one the **write path**
    produces; a hand-assembled JSON-LD fixture would be testing the probe's
    idea of the layout rather than the adapter's.
    """
    for claim in entities:
        handle.worker.admit_entity_claim(tenant_id=TENANT, claim=claim)
    for edge in relationships:
        handle.worker.admit_relationship_claim(tenant_id=TENANT, claim=edge)


@pytest.mark.fluree
def test_fa2_var_length_bounds_as_parameter(fluree_url: str) -> None:
    """F-A2: can a variable-length bound bind as a ``$param``? **No.**

    Recorded outcome: **FAIL — both forms rejected 400 at parse time.** That is
    the expected verdict (Neo4j rejects both, re-verified at 15.2-12 execution,
    and there was no reason a Cypher front-end would differ), and its ladder
    position is **rung 1 either way**: the workaround is already written,
    shipped and ratified in the Neo4j adapter.

    The consequence is the one thing this probe decides — that
    ``_reach_pattern`` must exist in the Fluree adapter as the **single
    sanctioned string-formatting site**, carrying
    ``backends/neo4j.py``'s validation contract intact (a genuine ``int``,
    ``bool`` refused, range ``[1, MAX_DEPTH_CEILING]``). Had either form
    parsed, the adapter would have kept plan 15.3-03's stronger property of
    having **no formatting site at all**.

    Both errors are parse-time, which is Fluree keeping the half of its
    promise that matters: an unsupported *form* is rejected loudly. Contrast
    F-A6, where an unsupported *expression* parsed and evaluated to null.
    """
    evidence: dict[str, Any] = {}
    with httpx.Client(timeout=TIMEOUT) as client:
        base, ledger = _bootstrap(client, fluree_url)
        for name, statement in (
            ("classic", _FA2_CLASSIC),
            ("quantified", _FA2_QUANTIFIED),
        ):
            response = _cypher(client, base, ledger, statement, {"depth": 2})
            evidence[name] = {
                "status": response.status_code,
                "body": response.text,
            }
            assert response.status_code == 400, (name, response.text)
            # Parse-time rejection, not a runtime resource refusal: this is the
            # form being unsupported, which is exactly what makes the verdict
            # safe to act on.
            assert "CypherParse" in response.text, (name, response.text)

    print("\nF-A2 evidence:\n" + json.dumps(evidence, indent=2, sort_keys=True))


@pytest.mark.fluree
def test_fa3_interposed_walk_primitives(
    fabric_boot: "Callable[..., FabricHandle]",
) -> None:
    """F-A3 (a)-(e), plus one sub-assertion the plan did not name.

    Every sub-assertion runs against a chain admitted through **booted L2**, so
    the interposed layout under test is the one
    ``ccf.graph.backends.fluree_write`` actually produces rather than the
    probe's idea of it.

    Recorded outcomes:

    * **(a) PASS** — the undirected bounded var-length with a path variable
      parses and runs, and the reach grows exactly one CCF hop per **two**
      Cypher hops: ``M=2 -> {mid}``, ``M=4 -> {mid, target}``,
      ``M=6 -> {mid, target, far}``. Stage 2 is available.
    * **(b) PASS** — ``all(n IN nodes(p) WHERE n.ccf_admit_key IN
      $admissible)`` filters **during** the walk: with the intermediate's key
      removed, the path to the target does not exist (zero paths), not merely
      absent from the output.
    * **(c) PASS** — see
      :func:`test_fa3c_the_path_enumeration_cap_errors_identifiably`, which
      needs a dense fixture of its own.
    * **(d) PASS** — ``type(r)`` over ``relationships(p)`` returns ``CCF_LINK``
      per hop from plain triples, so the annotation route stays viable as a
      fallback design.
    * **(e) Break 1 CONFIRMED** — ``r.<prop>`` over the same relationship
      values returns **nulls**. The interposition decision is validated by
      measurement: a direct port of ``_WALK_EDGES_ALL`` would have made
      ``all(...)`` false for every path and returned an empty reached set with
      a ``200``.
    * **(f) executor-added, and load-bearing** — the walk **must** carry
      partition/tenant scope. D-03 puts every partition in one ledger, so an
      unscoped seed match reaches into another fabric's graph. Measured
      directly below, not argued.

    This is the empirical half of 15.3-RESEARCH.md §R5, whose confidence the
    research rates MEDIUM-LOW precisely because the resolution was validated by
    argument until these ran.
    """
    evidence: dict[str, Any] = {}
    entities, relationships, uris = _extended_chain()
    seed_uri, mid_uri, target_uri, far_uri = uris

    handle = fabric_boot(backend="fluree")
    _write_chain(handle, entities, relationships)
    store: Any = handle.reader._store
    scope = store.scope(TENANT)
    admissible = _admit_keys(handle, uris)
    starts = ["e:" + seed_uri]

    # (a) the bounded undirected walk, at three bounds. The doubling shows up
    # here as a fact about the substrate rather than as an adapter claim.
    reach: dict[int, list[str]] = {}
    for bound in (2, 4, 6):
        rows = store.post_query(
            _fa3_walk(bound, tail=_FA3_REACH_RETURN),
            {**scope, "starts": starts},
        )
        reach[bound] = sorted(row["entity_uri"] for row in rows)
    evidence["a_reach_by_cypher_bound"] = {
        str(bound): value for bound, value in reach.items()
    }
    assert reach[2] == [mid_uri]
    assert reach[4] == sorted((mid_uri, target_uri))
    assert reach[6] == sorted((mid_uri, target_uri, far_uri))

    # (b) hop admissibility, and the control that gives it discriminating
    # power. Without the control, "target absent" would also be consistent with
    # "the walk reached nothing at all".
    reach_walk = _fa3_walk(4, tail=_FA3_REACH_RETURN, admissible=True)
    permissive = store.post_query(
        reach_walk, {**scope, "starts": starts, "admissible": admissible}
    )
    without_mid = [key for key in admissible if key != "e:" + mid_uri]
    restricted = store.post_query(
        reach_walk, {**scope, "starts": starts, "admissible": without_mid}
    )
    paths = store.post_query(
        _fa3_walk(4, tail=_FA3_PATH_COUNT_RETURN, admissible=True),
        {
            **scope,
            "starts": starts,
            "admissible": without_mid,
            "endpoint": target_uri,
        },
    )
    evidence["b_admissibility"] = {
        "control_all_keys": sorted(row["entity_uri"] for row in permissive),
        "intermediate_excluded": sorted(
            row["entity_uri"] for row in restricted
        ),
        "paths_to_target_with_intermediate_excluded": paths,
    }
    assert sorted(row["entity_uri"] for row in permissive) == sorted(
        (mid_uri, target_uri)
    )
    assert [row["entity_uri"] for row in restricted] == []
    # The strong form: the PATH does not exist. An empty endpoint set alone
    # would be consistent with output-side filtering, which would leave the
    # resurrection shape (threat T-15.2-26) unprotected.
    assert paths == [{"paths": 0}], paths

    # (d) value-only relationship use works on plain edges.
    types = store.post_query(
        _fa3_walk(2, tail=_FA3_TYPES_RETURN), {**scope, "starts": starts}
    )
    evidence["d_relationship_types"] = types
    assert types == [{"types": ["CCF_LINK", "CCF_LINK"]}], types

    # (e) THE BREAK-1 CONFIRMATION. The one relationship-property read in the
    # tree, here to prove it returns nothing.
    props = store.post_query(
        _fa3_walk(2, tail=_FA3_PROPS_RETURN), {**scope, "starts": starts}
    )
    evidence["e_relationship_properties"] = props
    assert props == [{"props": [None, None]}], props

    # (f) the scope terms are not decoration, and this is the sub-assertion the
    # plan did not name. D-03 puts every partition in ONE ledger, so a second
    # fabric — which is what every `fabric_boot(backend="fluree")` produces —
    # holds the SAME entity URIs under a different partition. Two measurements,
    # in increasing strength.
    short = fabric_boot(backend="fluree")
    _write_chain(short, entities[:2], relationships[:1])
    short_store: Any = short.reader._store
    short_scope = short_store.scope(TENANT)

    # (f.1) the seed pattern itself is not confined. An unscoped
    # `seed.ccf_admit_key IN $starts` matches this URI in every partition of the
    # ledger; the inline-map form matches exactly the one graph being asked.
    seeds_unscoped = short_store.post_query(
        "MATCH (seed:CcfEntity) WHERE seed.ccf_admit_key IN $starts"
        " RETURN count(seed) AS n",
        {"starts": starts},
    )
    seeds_scoped = short_store.post_query(
        "MATCH (seed:CcfEntity {ccf_partition: $partition,"
        " ccf_tenant_id: $tenant})"
        " WHERE seed.ccf_admit_key IN $starts RETURN count(seed) AS n",
        {**short_scope, "starts": starts},
    )
    assert seeds_scoped == [{"n": 1}], seeds_scoped
    assert seeds_unscoped[0]["n"] >= 2, seeds_unscoped

    # (f.2) the counterfactual that shows the confinement CANNOT be left to the
    # admit-key namespace. Given an `$admissible` set that names keys the short
    # graph does not hold — which is not a set the adapter produces today, and
    # that is exactly the point: the walk's tenant/partition confinement must
    # be a property of the STATEMENT, not a side effect of how a parameter
    # happens to be computed elsewhere (threats T-15.2-03 / T-15.2-26) — the
    # unscoped walk answers the SHORT graph's question with the LONG graph's
    # reach, while the scoped walk stays correct.
    foreign_admissible = _admit_keys(handle, uris)
    scoped = short_store.post_query(
        _fa3_walk(6, tail=_FA3_REACH_RETURN, admissible=True),
        {**short_scope, "starts": starts, "admissible": foreign_admissible},
    )
    unscoped = short_store.post_query(
        _fa3_walk(6, tail=_FA3_REACH_RETURN, admissible=True, scoped=False),
        {**short_scope, "starts": starts, "admissible": foreign_admissible},
    )
    scoped_uris = sorted(row["entity_uri"] for row in scoped)
    unscoped_uris = sorted(row["entity_uri"] for row in unscoped)
    evidence["f_partition_scope"] = {
        "seed_matches_unscoped": seeds_unscoped,
        "seed_matches_scoped": seeds_scoped,
        "walk_scoped": scoped_uris,
        "walk_unscoped": unscoped_uris,
    }
    assert scoped_uris == [mid_uri]
    assert target_uri in unscoped_uris, unscoped_uris
    assert target_uri not in scoped_uris

    print("\nF-A3 evidence:\n" + json.dumps(evidence, indent=2, sort_keys=True))


@pytest.mark.fluree
def test_fa3c_the_path_enumeration_cap_errors_identifiably(
    fabric_boot: "Callable[..., FabricHandle]",
) -> None:
    """F-A3(c): the visited/path cap **errors**, and the error is matchable.

    Recorded outcome: **PASS.** A graph of 12 entities and 27 edges — every
    ontology-legal edge over the whole fixture pool, still small — walked at
    CCF depth 5 answers::

        400 {"error":"Query error: Resource limit exceeded: path enumeration
             exceeded max paths (1000); narrow the pattern (tighter hop
             bounds, a bound end node, or a specific type)",
             "status":400,"@type":"err:db/InvalidQuery"}

    Two things follow, and both matter more than the status code:

    1. **The cap is reachable with the adapter's own walk shape**, not only
       with a pathological one. 15.3-RESEARCH.md names it as an operational
       risk on production graphs; this measures it on a graph the fixture
       vocabulary can build, which is what makes the decline path testable
       in-tree rather than merely argued.
    2. **The message is identifiable**, so the decline-to-fallback path can be
       implemented safely. An unidentifiable ``500`` would have forced a
       constraint instead: catch nothing, and let the error propagate.

    The corpus's deepest walk is depth 4 over three-node chains, so nothing in
    CI approaches this — the cap is a production concern the adapter answers
    by declining, never a corpus concern.
    """
    handle = fabric_boot(backend="fluree")
    uris: list[str] = []
    for entity_class, pool in ENTITY_POOL.items():
        for uri in pool:
            handle.worker.admit_entity_claim(
                tenant_id=TENANT,
                claim=entity_claim(
                    entity_uri=uri,
                    entity_class=entity_class,
                    classification=PERMITTED_CLASSIFICATION,
                    observed_at=EARLY,
                ),
            )
            uris.append(uri)
    for relationship_type, subject_class, object_class in RELATIONSHIP_RULES:
        for subject_uri in ENTITY_POOL[subject_class]:
            for object_uri in ENTITY_POOL[object_class]:
                handle.worker.admit_relationship_claim(
                    tenant_id=TENANT,
                    claim=relationship_claim(
                        relationship_type=relationship_type,
                        subject_uri=subject_uri,
                        object_uri=object_uri,
                        observed_at=EARLY,
                    ),
                )

    store: Any = handle.reader._store
    admissible = _admit_keys(handle, uris)
    with pytest.raises(httpx.HTTPStatusError) as caught:
        store.post_query(
            _fa3_walk(10, tail=_FA3_REACH_RETURN, admissible=True),
            {
                **store.scope(TENANT),
                "starts": ["e:" + ENTITY_POOL[SEED_CLASS][0]],
                "admissible": admissible,
            },
        )
    response = caught.value.response
    assert response.status_code == 400, response.text
    assert CAP_ERROR_MARKER in response.text, response.text
    print("\nF-A3(c) evidence:\n" + response.text)


# --- always-on unit tests (plan 15.3-02) --------------------------------------
#
# No server, no marker. The live-server behaviour — writes through booted L2,
# the interposed layout, the offset-authored projection — runs under the
# `fluree` marker below and in tests/conformance/test_graphstore.py.
#
# `test_neo4j_backend.py::test_module_imports_without_the_driver` is
# deliberately NOT ported. (Cited by symbol rather than by line: a line anchor
# into another module drifts every time that module gains an import.) It asserts that a module stays importable without an
# optional extra installed; httpx is a core pin, so the assertion cannot fail
# and a test that cannot fail is worse than no test. The honest parallel — that
# no extra, no lazy import and no mypy override were added at all — is a
# configuration assertion and lives in the phase gate package.


def test_graph_identity_carries_no_credentials() -> None:
    """The identity string drops userinfo entirely (threat T-15.2-05).

    The single-writer check keys on this string and it lands in exception
    messages, so the password and user are dropped rather than merely "not
    usually shown" — the T-04-24 postgres precedent, unit-asserted here given
    a credentialed URL.
    """
    from ccf.graph.backends.fluree import _graph_identity

    identity = _graph_identity(
        "http://alice:s3cret-password@graph.example.com:8090",
        ledger="ccf:main",
        partition="ccf_test",
    )
    assert "s3cret-password" not in identity
    assert "alice" not in identity
    assert identity == "fluree://graph.example.com:8090/ccf:main#ccf_test"


def test_server_root_drops_userinfo_before_the_client_sees_it() -> None:
    """The httpx client is built on a credential-free origin.

    Both credentials are headers and neither reaches the URL; userinfo
    supplied in the URL is removed here, so it survives into no request line,
    no redirect target and no connection-pool key. What *carries* it is
    `_authorization`, asserted separately below — dropping it here without
    that was WR-02.
    """
    from ccf.graph.backends.fluree import _server_root

    root = _server_root("http://alice:s3cret@graph.example.com:8090")
    assert root == "http://graph.example.com:8090"
    assert "s3cret" not in root
    assert "alice" not in root


def test_a_url_below_the_origin_is_refused_rather_than_silently_trimmed() -> None:
    """WR-02's second half: a dropped mount path is a lost capability.

    `_server_root` used to `_replace(path="")`, so `http://host/fluree` became
    `http://host` and a path-mounted server was unreachable *silently*. Every
    request this store issues is rooted at the origin — `/health` and the
    discovery document included — so the honest answer is a refusal naming the
    component, not a trim.
    """
    from ccf.graph.backends.fluree import _server_root

    for url in (
        "http://graph.example.com:8090/fluree",
        "http://graph.example.com:8090/?tenant=a",
        "http://graph.example.com:8090/#frag",
    ):
        with pytest.raises(ValueError, match="bare server origin"):
            _server_root(url)
    # A bare origin, with or without the trailing slash, still resolves.
    assert _server_root("http://host:8090") == "http://host:8090"
    assert _server_root("http://host:8090/") == "http://host:8090"


def test_url_userinfo_becomes_a_basic_credential_not_a_discarded_string() -> None:
    """WR-02, the defect itself: userinfo must AUTHENTICATE or be refused.

    The pre-fix code stripped userinfo in `_server_root` and then did nothing
    with it, and httpx 0.28.1 derives no `Authorization` header from a
    `base_url`'s userinfo (asserted below against the real client, so this
    stays true if the pin moves). A credentialed URL therefore connected
    **anonymously** — the one outcome that must not remain.

    The rule now is `src/ccf/graph/backends/neo4j.py::_split_credentials`'s:
    userinfo a caller supplied is used.
    """
    from ccf.graph.backends.fluree import _authorization

    # (a) httpx really does not do this for us. If a future httpx starts
    #     deriving the header, this assertion fails and the duplication is
    #     surfaced rather than left to rot.
    with httpx.Client(base_url="http://alice:s3cret@host:8090") as probe:
        assert "authorization" not in probe.build_request("GET", "/health").headers

    # (b) so the adapter does it.
    header = _authorization("http://alice:s3cret@host:8090", None)
    assert header is not None
    assert header.startswith("Basic ")
    import base64

    assert base64.b64decode(header.split(" ", 1)[1]).decode() == "alice:s3cret"

    # (c) percent-encoded halves are decoded first: a password containing `@`
    #     or `:` cannot be written into a URL any other way (RFC 3986 §3.2.1).
    encoded = _authorization("http://al%40ice:p%3Ass%40word@host:8090", None)
    assert encoded is not None
    assert (
        base64.b64decode(encoded.split(" ", 1)[1]).decode() == "al@ice:p:ss@word"
    )

    # (d) no credential supplied is still anonymous — a caller's choice, and a
    #     different thing from a supplied credential being dropped.
    assert _authorization("http://host:8090", None) is None

    # (e) the bearer channel.
    assert _authorization("http://host:8090", "tok") == "Bearer tok"


def test_two_credential_channels_at_once_are_refused_without_echoing_either() -> None:
    """Ambiguity is refused, not resolved by precedence.

    "Which credential won" is a question an audit cannot answer by convention,
    so the store refuses instead of picking. The refusal must also not leak:
    neither the password nor the token appears in the message.
    """
    from ccf.graph.backends.fluree import _authorization

    with pytest.raises(ValueError) as caught:
        _authorization("http://alice:s3cret@host:8090", "tok-abc")
    message = str(caught.value)
    assert "s3cret" not in message
    assert "tok-abc" not in message
    assert "alice" not in message


def _offline_fluree_transport(seen: list[httpx.Request]) -> httpx.MockTransport:
    """A server-free stand-in for the three requests construction makes.

    `/health`, `/.well-known/fluree.json`, then the idempotent `POST /create`
    answered `409` as a second boot would answer it. Every request is recorded
    so the test can assert what the WIRE carried, not merely what the store
    computed — the difference between "the header was built" and "the header
    was sent" is exactly the gap WR-02 lived in.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/.well-known/fluree.json":
            return httpx.Response(200, json={"api_base_url": "/v1/fluree"})
        if request.url.path.endswith("/create"):
            return httpx.Response(409, json={})
        return httpx.Response(200, json={})

    return httpx.MockTransport(handler)


def test_a_credentialed_url_authenticates_on_the_wire(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End to end, server-free: every request carries the credential.

    Constructs a real `FlureeGraphStore` over a `MockTransport`, so the
    assertion is about the requests httpx actually built. Before the WR-02 fix
    this test fails on the first request: no `Authorization` header at all.
    """
    import ccf.graph.backends.fluree as fluree_mod

    seen: list[httpx.Request] = []
    real_client = httpx.Client

    def _client(**kwargs: Any) -> httpx.Client:
        return real_client(transport=_offline_fluree_transport(seen), **kwargs)

    monkeypatch.setattr(fluree_mod.httpx, "Client", _client)

    store = fluree_mod.FlureeGraphStore(
        url="http://alice:s3cret@graph.example.com:8090", partition="ccf_test"
    )
    try:
        assert seen, "construction issued no request"
        for request in seen:
            assert request.headers.get("authorization") == "Basic YWxpY2U6czNjcmV0"
            # And the credential never travels in the URL either.
            assert "alice" not in str(request.url)
            assert "s3cret" not in str(request.url)
        # Nor into the identity the single-writer check and replay key on.
        assert "s3cret" not in store.graph_identity
        assert "alice" not in store.graph_identity
    finally:
        store.close()


def test_boot_threads_the_bearer_token_to_the_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WR-03: `bearer_token` is reachable through the supported boot path.

    It was a constructor parameter no supported path could set, which reads as
    a credential path that works. The guarantee is *a token supplied at boot
    reaches the wire and reaches nothing else* — asserted end to end through
    the supported path rather than against a signature.

    The two signature assertions this test used to carry — that
    ``fluree_bearer_token`` is a parameter of ``boot`` and of
    ``load_and_boot`` — are false by design since D-IMPL-93: no parameter names
    a database any more. They are replaced by the assertion below rather than
    deleted, because the guarantee was never the parameter name. The credential
    now travels as a `ResolvedSecret` keyed by the adapter's own config field,
    which is what lets the adapter pin record *which reference* was in force
    rather than merely that some credential was supplied.
    """
    import ccf.graph.backends.fluree as fluree_mod
    from ccf.boot import boot
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.graph.registry import ResolvedSecret

    seen: list[httpx.Request] = []
    real_client = httpx.Client

    def _client(**kwargs: Any) -> httpx.Client:
        return real_client(transport=_offline_fluree_transport(seen), **kwargs)

    monkeypatch.setattr(fluree_mod.httpx, "Client", _client)

    # Boot fails at the Control Plane resolution — the registry is empty — and
    # that is after the store is constructed, which is the step under test.
    # `boot`'s half-booted-fabric cleanup closes the store on the way out, so
    # nothing leaks and this test needs no artifacts.
    with pytest.raises(ControlPlaneMissing):
        boot(
            backend=FLUREE_REGISTRATION.name,
            connection={
                "url": "http://graph.example.com:8090",
                "partition": "ccf_test",
            },
            secrets={
                BEARER_TOKEN_FIELD: ResolvedSecret(
                    field=BEARER_TOKEN_FIELD,
                    ref_name="CCF_FLUREE_TOKEN",
                    value=SecretStr("tok-abc"),
                )
            },
            registry=ControlPlaneRegistry(),
            resolution_spec_key="never",
            resolution_spec_version="never",
            policy_bundle_key="never",
            policy_bundle_version="never",
        )

    assert seen, "construction issued no request"
    for request in seen:
        assert request.headers.get("authorization") == "Bearer tok-abc"
        # Header-only (WR-03): the credential never travels in the URL.
        assert "tok-abc" not in str(request.url)
    # The other half of "reaches nothing else" — the identity the
    # single-writer check and replay key on — is asserted directly by
    # `test_graph_identity_carries_no_credentials`, which builds the identity
    # from a URL that carries one.


def test_a_failed_construction_closes_its_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WR-05 (D-14): a construction that fails leaks no connection pool.

    `__init__` builds an `httpx.Client` and then performs three bootstrap
    requests. Any failure among them used to propagate with the client — and
    its pool — still open, and a failed constructor returns no object the
    caller could have closed, so nothing else could clean it up either.

    This phase is why it stopped being tolerable. D-08 puts a
    secret-resolution step in front of store construction, so a mis-set
    environment variable produces construction failures routinely rather than
    exceptionally, and each one held a pool.

    Asserted on the *observable* fact rather than on the source: `close` is
    counted, and the count must be exactly one — a guard that closed twice
    would be as wrong as one that never closed, and the original exception must
    reach the caller unchanged rather than be swallowed by the cleanup.
    """
    import ccf.graph.backends.fluree as fluree_mod

    closes: list[int] = []
    real_client = httpx.Client
    real_close = httpx.Client.close

    def _counting_close(self: httpx.Client) -> None:
        closes.append(1)
        real_close(self)

    def _refusing_transport() -> httpx.MockTransport:
        """`/health` answers 503 — the first request after the client exists."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, json={})

        return httpx.MockTransport(handler)

    def _client(**kwargs: Any) -> httpx.Client:
        return real_client(transport=_refusing_transport(), **kwargs)

    # Order matters: `fluree_mod.httpx` IS the `httpx` module, so the second
    # patch replaces `httpx.Client` with the factory above and the class is no
    # longer reachable by that name. Patch the class attribute first.
    monkeypatch.setattr(httpx.Client, "close", _counting_close)
    monkeypatch.setattr(fluree_mod.httpx, "Client", _client)

    with pytest.raises(httpx.HTTPStatusError):
        fluree_mod.FlureeGraphStore(
            url="http://graph.example.com:8090", partition="ccf_test"
        )

    assert closes == [1], closes


def test_a_refusal_before_the_client_exists_closes_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The WR-05 guard's other half: there is nothing to close, so nothing is.

    The two credential/origin refusals are raised *before* any client is
    constructed — the credential check runs first, the origin check runs while
    evaluating the client's own argument. A guard that had been placed one line
    too early would close a client that was never built, which is an
    `AttributeError` on the way out of a refusal, and the refusal is the thing
    the caller needs to see. Non-vacuity for the test above: it establishes
    that the counter counts nothing when nothing should be closed.
    """
    import ccf.graph.backends.fluree as fluree_mod

    closes: list[int] = []
    real_close = httpx.Client.close

    def _counting_close(self: httpx.Client) -> None:
        closes.append(1)
        real_close(self)

    monkeypatch.setattr(httpx.Client, "close", _counting_close)

    with pytest.raises(ValueError, match="supply exactly one credential"):
        fluree_mod.FlureeGraphStore(
            url="http://alice:s3cret@graph.example.com:8090",
            bearer_token="tok-abc",
        )
    with pytest.raises(ValueError, match="bare server origin"):
        fluree_mod.FlureeGraphStore(url="http://graph.example.com:8090/mounted")

    assert closes == [], closes


def test_a_credential_for_an_adapter_that_declares_none_is_refused() -> None:
    """A credential for a backend nobody selected would be silently ignored.

    The same failure class as WR-02 one layer up: an argument the caller
    supplied that the machinery quietly drops. This is the *relocation* of the
    old `fluree_bearer_token`-without-`fluree_url` refusal, not a replacement
    for it. Selection is a name now, so the same mistake arrives as a
    credential keyed by a field the resolved adapter does not declare, and
    `boot` refuses it against the adapter's own `secret_fields`.

    The guarantee was split rather than shortened. Its narrower half — a token
    supplied *to this adapter* with no `url` — is now the `missing` refusal on
    `url` in this adapter's connection contract, which
    `tests/deployment/test_adapter_config.py` asserts per adapter.

    The subject adapter here is deliberately one that declares **no** credential
    field, taken off its own registration record rather than named, so the test
    is about the mechanism and not about which adapter happens to have none.

    It must also require **no connection setting**, and that second half is a
    precondition rather than a convenience. ``boot`` validates the connection
    mapping before it checks the credential mapping, and this call supplies no
    connection at all — so a subject with a required setting is refused for the
    missing setting, which is a refusal about the wrong thing. Both halves are
    read off the adapter's own record, so the selection stays derived; naming
    the adapter that happens to satisfy them would put a substrate literal back
    into a test whose whole point is that it has none.

    Plan 15.4-10 is what made the second half load-bearing. Until an out-of-tree
    adapter was installed, every credential-free adapter that sorted first also
    happened to need no connection settings, so the precondition held by
    accident and the test passed without stating it.
    """
    from ccf.boot import boot
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.graph.registry import ResolvedSecret, declared_names, resolve

    def _needs_neither(name: str) -> bool:
        registration = resolve(name).registration
        if registration.secret_fields:
            return False
        return not any(
            field.is_required()
            for field in registration.config_model.model_fields.values()
        )

    credential_free = sorted(
        name for name in declared_names() if _needs_neither(name)
    )
    assert credential_free, (
        "no adapter declares both an empty secret_fields and a connection"
        " contract with no required settings"
    )
    subject = credential_free[0]

    with pytest.raises(ValueError) as caught:
        boot(
            backend=subject,
            secrets={
                BEARER_TOKEN_FIELD: ResolvedSecret(
                    field=BEARER_TOKEN_FIELD,
                    ref_name="CCF_FLUREE_TOKEN",
                    value=SecretStr("tok-abc"),
                )
            },
            registry=ControlPlaneRegistry(),
            resolution_spec_key="never",
            resolution_spec_version="never",
            policy_bundle_key="never",
            policy_bundle_version="never",
        )
    message = str(caught.value)
    assert subject in message
    assert BEARER_TOKEN_FIELD in message
    # Names the adapter and the key, never the value.
    assert "tok-abc" not in message


def test_partitions_are_distinct_graphs() -> None:
    """Two partitions in one ledger are two graph identities.

    The Postgres two-schemas-are-two-graphs rule, carried over: what makes the
    single-writer check meaningful per fabric rather than per server. D-03
    keeps one CCF-owned ledger, so the partition is the whole of what
    distinguishes two fabrics on this substrate.
    """
    from ccf.graph.backends.fluree import _graph_identity

    one = _graph_identity(
        "http://host:8090", ledger="ccf:main", partition="fabric_a"
    )
    two = _graph_identity(
        "http://host:8090", ledger="ccf:main", partition="fabric_b"
    )
    assert one != two


def test_minted_ids_are_colonless_and_content_addressed() -> None:
    """No artifact-authored string ever occupies an IRI position (§R3).

    An `@id` is an IRI position and the strict compact-IRI guard rejects
    `prefix:suffix` with an undefined prefix at parse time — so an
    artifact-authored `entity_uri`, which may legally contain a colon, must
    never become one. `_mint_id` is the single site that produces identifiers
    and it produces colonless, opaque, content-addressed ones.
    """
    from ccf.graph.backends.fluree import _mint_id

    hazard = "counterparty:acme"
    minted = _mint_id("e", "ccf", "tenant-a", hazard)
    assert ":" not in minted
    assert hazard not in minted
    assert minted.startswith("ccf_e_")
    # Content-addressed: the same node identity always mints the same `@id`,
    # which is what makes a re-admission re-assert byte-identical triples.
    assert minted == _mint_id("e", "ccf", "tenant-a", hazard)
    assert minted != _mint_id("e", "ccf", "tenant-b", hazard)


def test_the_adapter_context_carries_no_coercion() -> None:
    """D-02's hard condition, asserted rather than trusted.

    No `@vocab`, no `@base`, no term definitions — therefore no datatype
    coercion, and every string lands as `xsd:string` (probe F-A5 read all six
    temporal datatypes back and confirmed it). `@vocab` in particular is not a
    style question: adding it to a ledger whose data was written bare changes
    what every Cypher statement matches, silently.
    """
    from ccf.graph.backends.fluree import ADAPTER_CONTEXT

    assert ADAPTER_CONTEXT == {}


def test_manifest_declares_fluree_and_preflight_requires_the_url() -> None:
    """`backend: fluree` is a declarable kind; the URL stays environment-supplied.

    The D-08 kind-only posture: a Fluree URL can carry userinfo and a Fluree
    deployment may also hold a bearer token, while the manifest is a
    content-hashed audit artifact — so no connection value lives in it.
    Preflight refuses a `fluree` declaration with no URL before any document is
    read, and refuses the *wrong* connection setting just as loudly.

    The refusals moved and the guarantees did not (15.4-06). Preflight no longer
    holds a substrate-to-argument table: it resolves the adapter the manifest
    names and validates one connection mapping against that adapter's own
    contract, so "the URL is required" is a required field and "this setting is
    not yours" is the inherited `extra="forbid"`. One assertion is *added* while
    migrating, because this path carries a credential: the supplied value must be
    absent from the refusal.
    """
    from ccf.controlplane.artifacts import DeploymentManifest
    from ccf.deployment.manifest import _preflight_adapter

    manifest = DeploymentManifest.model_validate(
        {
            "semver": "1.0.0",
            "backend": "fluree",
            "tenant_id": TENANT,
            "resolution_spec_key": "ccf.resolution-spec",
            "policy_bundle_key": "ccf.policy-bundle",
            "artifacts": [
                {
                    "path": "resolution.yaml",
                    "key": "ccf.resolution-spec",
                    "class_id": "ccf.resolution-spec",
                    "role": "register",
                    "registration": "typed",
                },
                {
                    "path": "policy.yaml",
                    "key": "ccf.policy-bundle",
                    "class_id": "ccf.policy-bundle",
                    "role": "register",
                    "registration": "versioned",
                },
            ],
        }
    )
    with pytest.raises(ValueError, match="fluree") as missing:
        _preflight_adapter(manifest, {})
    assert "url" in str(missing.value)

    # And the mirror: the right setting is accepted, a setting the adapter does
    # not declare is refused.
    _preflight_adapter(manifest, {"url": "http://localhost:8090"})

    stray = "mongodb://user:pw@localhost:27017"
    with pytest.raises(ValueError, match="uri") as refused:
        _preflight_adapter(
            manifest, {"url": "http://localhost:8090", "uri": stray}
        )
    # The refusal names the key and never reproduces what was supplied under
    # it — the same posture `_authorization` holds for this adapter's two
    # credential channels, asserted here because a misspelled connection key is
    # exactly where a credential lands under a name nobody declared.
    assert stray not in str(refused.value)


def test_boot_refuses_this_adapter_plus_another_substrates_setting() -> None:
    """Naming this adapter and supplying another's setting is refused loudly.

    The guarantee is unchanged — the fabric does not infer its substrate and
    does not pick a winner — and so is the property that made this test cheap:
    the refusal still runs before any store is constructed, so it needs no
    reachable server.

    What changed is the shape of the contradiction. Before D-IMPL-93 it was two
    of eleven keyword arguments; now it is a connection key this adapter does
    not declare, refused by the ``extra="forbid"`` its contract inherits.
    """
    from ccf.boot import boot
    from ccf.controlplane.registry import ControlPlaneRegistry
    from ccf.graph.registry import InvalidBackendConfig

    with pytest.raises(InvalidBackendConfig) as caught:
        boot(
            backend=FLUREE_REGISTRATION.name,
            connection={
                "url": "http://localhost:8090",
                "database_path": "never-created.sqlite3",
            },
            registry=ControlPlaneRegistry(),
            resolution_spec_key="never",
            resolution_spec_version="never",
            policy_bundle_key="never",
            policy_bundle_version="never",
        )
    assert FLUREE_REGISTRATION.name in str(caught.value)
    assert "database_path" in str(caught.value)


# --- the live-server half (needs a reachable Fluree v4) -----------------------


@pytest.mark.fluree
def test_l2_writes_round_trip_byte_identically_to_the_memory_backend(
    fabric_boot: "Callable[..., FabricHandle]",
) -> None:
    """A fabric boots on Fluree, writes through L2, and answers identically.

    This plan's own bar, before any translation exists: the same claims
    admitted through booted L2 on Fluree and on the zero-dependency memory
    backend answer byte-identical views at three observed-time boundaries —
    before the revision, on it, and after it — so the supersession chain, the
    lineage set-union and the canonical timestamps all round-trip through the
    JSON-LD batch and the RDF layout unchanged.
    """
    uri = ENTITY_POOL[SEED_CLASS][0]
    other = ENTITY_POOL[SEED_CLASS][1]
    claims = (
        entity_claim(
            entity_uri=uri,
            entity_class=SEED_CLASS,
            classification=PERMITTED_CLASSIFICATION,
            observed_at=EARLY,
        ),
        entity_claim(
            entity_uri=other,
            entity_class=SEED_CLASS,
            classification=PERMITTED_CLASSIFICATION,
            observed_at=EARLY,
        ),
        entity_claim(
            entity_uri=uri,
            entity_class=SEED_CLASS,
            classification=EXCLUDED_CLASSIFICATION,
            observed_at=LATE,
        ),
    )
    edge = relationship_claim(
        relationship_type=EDGE_TYPE,
        subject_uri=uri,
        object_uri=other,
        observed_at=EARLY,
    )

    views: dict[str, list[bytes]] = {}
    for backend in ("fluree", "memory"):
        handle = fabric_boot(backend=backend)
        for claim in claims:
            handle.worker.admit_entity_claim(tenant_id=TENANT, claim=claim)
        handle.worker.admit_relationship_claim(tenant_id=TENANT, claim=edge)
        views[backend] = [
            canonical_bytes(handle.reader.as_of(tenant_id=TENANT, at=at))
            for at in (EARLY, ON_BOUNDARY, LATE)
        ]
        if backend == "fluree":
            # The history read is the second contract the RDF layout has to
            # satisfy: the whole chain, oldest first, with the supersession
            # edge restitched by the shared writer algorithm — which on this
            # substrate means a ground delete of the old value and a ground
            # insert of the new one, since RDF has no `$set`.
            history: Any = handle.reader.entity_history(
                tenant_id=TENANT, entity_uri=uri
            )
            assert len(history) == 2
            assert history[0].superseded_by == history[1].claim_id

    assert views["fluree"] == views["memory"]


@pytest.mark.fluree
def test_the_interposed_edge_layout_is_maintained_by_the_write_path(
    fabric_boot: "Callable[..., FabricHandle]",
) -> None:
    """Every CCF relationship is ONE CcfEdge node and exactly TWO CCF_LINK triples.

    Asserted directly against the store rather than inferred from a traversal
    answer, because the walk in plan 15.3-04 reads exactly this layout and the
    two must not drift.

    The counts are exact, not lower bounds, and both directions of the
    exactness matter. **One** edge node: a second would mean the interposition
    fanned out, which on RDF is what a bare re-assertion of a changed property
    does. **Two** links: three would mean the write path doubled the edge the
    way the Mongo adapter must (`$graphLookup` is directed), and Cypher's
    `-[:T]-` is first-class undirected, so doubling here would be pure waste
    and a second place for the layout to be wrong.
    """
    uri = ENTITY_POOL[SEED_CLASS][0]
    other = ENTITY_POOL[SEED_CLASS][1]
    handle = fabric_boot(backend="fluree")
    for entity_uri in (uri, other):
        handle.worker.admit_entity_claim(
            tenant_id=TENANT,
            claim=entity_claim(
                entity_uri=entity_uri,
                entity_class=SEED_CLASS,
                classification=PERMITTED_CLASSIFICATION,
                observed_at=EARLY,
            ),
        )
    written = handle.worker.admit_relationship_claim(
        tenant_id=TENANT,
        claim=relationship_claim(
            relationship_type=EDGE_TYPE,
            subject_uri=uri,
            object_uri=other,
            observed_at=EARLY,
        ),
    )
    # Admit the same edge twice: re-arrival must not fan the layout out.
    handle.worker.admit_relationship_claim(
        tenant_id=TENANT,
        claim=relationship_claim(
            relationship_type=EDGE_TYPE,
            subject_uri=uri,
            object_uri=other,
            observed_at=EARLY,
        ),
    )

    store: Any = handle.reader._store
    scope = store.scope(TENANT)
    nodes = store.post_query(
        _EDGE_NODE_PROBE, {**scope, "key": written.node_key}
    )
    assert [row["admit_key"] for row in nodes] == ["r:" + written.node_key]

    links = store.post_query(
        _EDGE_LINK_PROBE, {**scope, "key": written.node_key}
    )
    assert sorted(row["entity_uri"] for row in links) == sorted((uri, other))


@pytest.mark.fluree
def test_offset_authored_validity_lands_as_canonical_utc_text(
    fabric_boot: "Callable[..., FabricHandle]",
) -> None:
    """The §R8 vector-1 assertion: DI-15.2-03 cannot re-enter through this wire.

    `_claim_payload` guarantees the `claim_json` *string* is canonical
    (D-IMPL-90). But this adapter also writes projected comparison properties,
    and those are what the pushed `GQ-09` predicate actually compares. The
    projection re-renders both validity bounds through `parse_timestamp` ->
    `canonical_timestamp`; if it ever shortcut by copying the payload's raw
    JSON value, an offset-authored claim would compare as `+05:00` text against
    a canonical `Z` boundary and silently drop out of every pushed answer while
    the fallback kept including it.

    **Fluree has no read-time `_utc_fixed_width`.** The SQL adapters can
    re-normalize on the way out; here write time is the only chance, which is
    why this is asserted directly against the stored bytes rather than through
    an answer that a second normalization could rescue.
    """
    uri = ENTITY_POOL[SEED_CLASS][0]
    handle = fabric_boot(backend="fluree")
    handle.worker.admit_entity_claim(
        tenant_id=TENANT,
        claim=entity_claim(
            entity_uri=uri,
            entity_class=SEED_CLASS,
            classification=PERMITTED_CLASSIFICATION,
            observed_at=EARLY,
            valid_to=LATE,
            # A non-UTC authoring offset — the same instant, a different
            # rendering. This is the corner D-IMPL-90 closed at the contract
            # tier and that this substrate inherits for free.
            authoring_offset=AUTHORING_OFFSETS[0],
        ),
    )

    store: Any = handle.reader._store
    rows = store.post_query(
        _VALIDITY_PROBE, {**store.scope(TENANT), "key": uri}
    )
    assert len(rows) == 1
    for column in ("valid_from_cmp", "valid_to_cmp"):
        value = rows[0][column]
        assert isinstance(value, str), (column, rows[0])
        assert CANONICAL_UTC.fullmatch(value), (column, value)


# --- stage-1 read translation (plan 15.3-03) ---------------------------------
#
# Always-on unit assertions about `_translate_query`'s guards and its one
# artifact-safety encoding. The live-server evidence — byte-identity over the
# generated corpus, and the telemetry proving the push actually happened — is
# under the `fluree` marker in tests/conformance/test_substrate_differential.py
# and in `test_fluree_non_traverse_queries_are_pushed_not_silently_degraded`
# below.


def test_exactly_one_formatting_site_renders_query_text() -> None:
    """Grep the module: exactly one f-string reaches Cypher text.

    **This assertion REPLACES plan 15.3-03's stronger zero-site one, and the
    replacement is a recorded loss rather than a relaxation.** Stage 1 rendered
    no walk, so the module's injection surface was genuinely empty — strictly
    better than Neo4j. Probe F-A2 then measured that a variable-length bound
    cannot be a ``$param`` on this engine either (both forms rejected ``400``
    at parse time), so the walk costs exactly the one site the Neo4j adapter
    pays, on the same value and with the same validation contract
    (`test_neo4j_backend.py::test_exactly_one_formatting_site_renders_query_text`).
    Renaming rather than deleting keeps the property under assertion: a second
    formatting site would still turn this red.

    The other f-strings in the module are inspected individually and none lands
    in a statement: identity strings, URL paths, error messages, and `_query`'s
    `f"p{index}"`, which renders a parameter *name* under the positional
    binding convention.
    """
    import re
    from inspect import getsource

    import ccf.graph.backends.fluree as module

    source = getsource(module)
    cypher_shaped = re.findall(
        r'f"[^"]*(?:MATCH|MERGE|RETURN|WHERE|\[:|\*1\.\.)[^"]*"', source
    )
    assert len(cypher_shaped) == 1, cypher_shaped
    assert "*1..{2 * depth}" in cypher_shaped[0], cypher_shaped


def test_reach_pattern_doubles_the_ccf_depth_and_validates_it() -> None:
    """The ONE formatting site: `-[:CCF_LINK*1..2d]-`, refusing everything else.

    Two claims, both measured rather than reasoned about elsewhere:

    * **the doubling.** A CCF hop is TWO Cypher hops through the interposed
      edge node, so CCF depth 1 renders `*1..2` and CCF depth 3 renders
      `*1..6`. This is the replacement for Mongo's `maxDepth: depth_limit - 1`
      off-by-one — structurally absent because Cypher's `*1..N` is 1-based —
      and it is the same class of error, which is why
      `test_fluree_interposed_depth_matches_the_fallback_at_zero_one_two_and_three`
      asserts it against a live differential control as well as here;
    * **the validation contract**, ported intact from
      `backends/neo4j.py`: the depth literal is the concentrated injection
      surface (threat T-15.2-01), so bools, negatives, zero and over-ceiling
      values all refuse. The ceiling is checked against the **CCF** depth,
      before doubling — `MAX_DEPTH_CEILING` renders `*1..200`, not `*1..100`.
    """
    from ccf.graph.backends.fluree import MAX_DEPTH_CEILING, _reach_pattern

    assert _reach_pattern(1) == "-[:CCF_LINK*1..2]-"
    assert _reach_pattern(3) == "-[:CCF_LINK*1..6]-"
    assert _reach_pattern(MAX_DEPTH_CEILING) == (
        f"-[:CCF_LINK*1..{2 * MAX_DEPTH_CEILING}]-"
    )
    for bad in (0, -1, MAX_DEPTH_CEILING + 1, True):
        with pytest.raises(ValueError, match="depth literal"):
            _reach_pattern(bad)


def test_no_relationship_property_is_read() -> None:
    """Do-not-copy #1, as an executable rule rather than a comment.

    ⛔ `_WALK_EDGES_ALL` (`backends/neo4j.py:440-446`) reads relationship
    properties, and a plain RDF edge on this engine has none — probe F-A3(e)
    measured `[null, null]` over the layout the write path produces. A ported
    predicate would make `all(...)` false for every path and return an **empty
    reached set with a 200**: a silently wrong answer, not covered by Fluree's
    parse-time-rejection promise, and undetectable from the status code.

    So the module is grepped for the shape that would do it. Note the failure
    this guards against is exactly the one the four-trap-shape telemetry and
    the depth 0/1/2/3 differential would also catch — three independent
    detectors on one silent failure, because it is the phase's dominant risk.
    """
    import re
    from inspect import getsource

    import ccf.graph.backends.fluree as module

    source = getsource(module)
    assert re.findall(r"relationships\(\w+\)", source) == []


def test_no_relationship_type_alternation_appears_in_any_pattern() -> None:
    """`CCF_LINK` and nothing else — the Break-2 constraint, held shut.

    The only bounded variable-length pattern this engine admits is a **single
    fixed relationship type**: bounded type-alternation (`-[:A|B*1..3]-`) and
    undirected-untyped (`-[*]-`) are both deferred upstream. A two-predicate
    interposition (`HAS_EDGE`/`TO`) would have needed the alternation and so
    would have reintroduced the very constraint the interposition escapes —
    considered and rejected, and asserted here so it cannot creep back in.

    The regex is scoped to Cypher relationship-pattern text deliberately: a
    bare `|` alternative matches every `str | None` union in a `mypy --strict`
    module, so it could never return zero and would be waived by hand — and a
    criterion waived by hand has stopped being a criterion.
    """
    import re
    from inspect import getsource

    import ccf.graph.backends.fluree as module

    source = getsource(module)
    assert re.findall(r"\[:[A-Za-z_]+\|", source) == []
    assert "CCF_LINK" in source


def test_over_ceiling_depth_declines_to_the_fallback() -> None:
    """`_translate_query` returns None above MAX_DEPTH_CEILING (D-04).

    The ceiling bounds a rendered pattern, never the query vocabulary: an
    over-ceiling `depth_limit` is still answered — by the memory-bounded
    fallback (`GQ-29`). Asserted with no store and no server: the decline is a
    pure function of the query value and runs before any request is built.

    **This assertion is now discriminating.** In stage 1 it could not be: the
    blanket traverse decline sat immediately below the ceiling check, so the
    query would have declined either way and the test could not say *which*
    guard fired. Plan 15.3-04's promotion removed that branch, so the ceiling
    is the only thing standing between this query and a walk — and it is
    checked against the **CCF** depth, before the interposed layout doubles it
    into Cypher hops.
    """
    from datetime import UTC, datetime

    from ccf.graph.backends.fluree import MAX_DEPTH_CEILING, FlureeGraphReader
    from ccf.graph.protocols import GraphQuery, TraversalSpec

    reader = FlureeGraphReader.__new__(FlureeGraphReader)
    over_ceiling = GraphQuery(
        tenant_id="t",
        as_of=datetime(2026, 1, 1, tzinfo=UTC),
        traverse=TraversalSpec(
            seed_entity_classes=frozenset({SEED_CLASS}),
            relationship_types=RELATIONSHIP_TYPES,
            depth_limit=MAX_DEPTH_CEILING + 1,
        ),
    )
    assert reader._translate_query(over_ceiling) is None


def test_the_traverse_family_is_no_longer_declined_at_the_boundary() -> None:
    """The FLIPPED stage-1 assertion: a walk is translated, not handed over.

    Plan 15.3-03 asserted the opposite here — `_translate_query` returned
    `None` for every traverse query, which was the recorded stage-1 boundary.
    It is **flipped rather than deleted**, because the flip is the promotion's
    most direct in-process evidence: deleting it would remove the only unit
    assertion that distinguishes "the walk is pushed" from "the whole family
    still declines".

    Driven with a recording double rather than a live server so the claim is
    about the *branch*, not about the answer. Zero survivor rows means zero
    walk starts, so no walk statement is issued and the return is the empty
    row pair — which is emphatically **not** `None`, and that is the whole
    assertion. The statements the translation did build are captured so the
    two-statement shape is visible too.
    """
    from datetime import UTC, datetime

    from ccf.graph.backends.fluree import FlureeGraphReader
    from ccf.graph.protocols import GraphQuery, TraversalSpec

    issued: list[str] = []

    class _RecordingStore:
        partition = "ccf_test"

        def post_query(
            self, cypher: str, params: dict[str, Any]
        ) -> list[dict[str, Any]]:
            issued.append(cypher)
            return []

    reader = FlureeGraphReader.__new__(FlureeGraphReader)
    reader._store = _RecordingStore()  # type: ignore[assignment]
    walk = GraphQuery(
        tenant_id="t",
        as_of=datetime(2026, 1, 1, tzinfo=UTC),
        traverse=TraversalSpec(
            seed_entity_classes=frozenset({SEED_CLASS}),
            relationship_types=RELATIONSHIP_TYPES,
            depth_limit=1,
        ),
    )
    assert reader._translate_query(walk) == ([], [])
    assert len(issued) == 2, issued
    # Typed crossability is decided by the EDGES statement, which is what lets
    # the walk's hop predicate be pure membership (§R5 Break 2).
    assert "ccf_relationship_type IN $types" in issued[1], issued[1]


def test_empty_allowed_set_answers_empty_without_a_round_trip() -> None:
    """The empty survivor set IS the answer (`GQ-04`) — no request built."""
    from datetime import UTC, datetime

    from ccf.graph.backends.fluree import FlureeGraphReader
    from ccf.graph.protocols import GraphQuery

    reader = FlureeGraphReader.__new__(FlureeGraphReader)
    empty = GraphQuery(
        tenant_id="t",
        as_of=datetime(2026, 1, 1, tzinfo=UTC),
        allowed_entities=frozenset(),
    )
    assert reader._translate_query(empty) == ((), ())


def test_policy_key_refuses_a_separator_bearing_component() -> None:
    """A NUL in an artifact-authored component cannot forge a key boundary.

    The policy key is a separator-joined encoding, and such an encoding is only
    injective while no component carries the separator. **All three components
    are artifact-authored**: a class name is user-declared ontology vocabulary
    held as a bare `str` on `EntityClaim` with no charset validation, an
    attribute name comes from the opaque deployment-defined attribute map the
    SDK never enumerates, and a classification value is deployment data too. A
    NUL in any of the three could make two different `(class, attribute,
    value)` triples encode to one key — a pushed answer admitting a claim the
    fallback excludes (threats T-15.2-01 / T-15.2-03). The builder refuses
    instead, and the caller declines the translation.

    This asserted the attribute and value components only until the CR-01
    correction of 2026-08-09; the un-asserted third is the one that shipped
    broken, so the coverage here is now exhaustive over the components rather
    than representative of them.
    """
    from ccf.graph.backends.fluree import POLICY_KEY_SEPARATOR, policy_key

    assert policy_key("Counterparty", "risk_tier", "tier-1") == (
        POLICY_KEY_SEPARATOR.join(("Counterparty", "risk_tier", "tier-1"))
    )
    assert policy_key(f"C{POLICY_KEY_SEPARATOR}p", "a", "b") is None
    assert policy_key("Counterparty", f"a{POLICY_KEY_SEPARATOR}b", "c") is None
    assert policy_key("Counterparty", "a", f"b{POLICY_KEY_SEPARATOR}c") is None


def test_no_pushed_policy_key_can_collide_with_a_stored_one() -> None:
    """The CR-01 regression: pushed and fallback cannot disagree by collision.

    The defect this pins closed. `policy_key` gated `attribute` and `value` but
    not `entity_class`, so a class carrying the separator re-cut the key at a
    different boundary and matched a *different* claim's stored key:

        claim   : entity_class="A", attributes={"B\\0C": "D"}
        stored  : ["A\\0B\\0C\\0D"]      # _fluree_claim_projection
        query   : classification_attribute_by_class={"A\\0B": "C"},
                  permitted_classifications={"D"}
        pushed  : "A\\0B\\0C\\0D"        # policy_key("A\\0B", "C", "D")

    `_ENTITY_POLICY` pushes `c.ccf_policy_key IN $policy_keys`, so the
    translated statement returned that claim — while `_admissible_entity`
    excludes it, because the claim's own class `"A"` has no declared
    classification attribute. The pushed path over-disclosed a record the
    policy family excludes: threats T-15.2-01 / T-15.2-03, and exactly the
    divergence the differential bar exists to catch. The differential suite
    could not catch it because the corpus generates no control characters in
    class names, which is why the assertion is made here and directly.

    Two things are asserted, because either alone would be satisfiable by a
    wrong fix: the *key* no longer collides, AND the query declines so the
    fallback answers the whole thing — pushed and fallback then agree by
    construction (D-04). No server: the collision is a pure function of the
    claim and the query, which is why it could have been caught before it
    shipped.

    **Amended at D-14 (2026-08-09).** As first fixed, the guard lived on the
    read side only and the write path still materialized the forgeable key;
    this test asserted that, and then asserted the key was unreachable anyway
    by a separator count. D-14 deleted the write path's duplicate constant and
    routed `_fluree_claim_projection` through the same `policy_key`, so the
    forgeable key is **not stored at all**. That is strictly stronger —
    unreachable by non-existence rather than by arithmetic — and the assertion
    below now says so. Both halves of the divergence claim are unchanged: the
    query still declines, and the fallback still excludes the claim.
    """
    import json as _json
    from datetime import UTC, datetime

    from ccf.graph.backends.fluree_write import _fluree_claim_projection
    from ccf.graph.backends.fluree import (
        POLICY_KEY_SEPARATOR,
        P_POLICY_KEY,
        FlureeGraphReader,
        policy_key,
    )
    from ccf.graph.fallback import _admissible_entity
    from ccf.graph.protocols import EntityRecord, GraphQuery
    from ccf.graph.reader import ENTITY_KIND

    sep = POLICY_KEY_SEPARATOR
    victim_class = SEED_CLASS
    forged_class = f"{victim_class}{sep}part"
    split_attribute = f"part{sep}attr"

    claim = entity_claim(
        entity_uri=ENTITY_POOL[victim_class][0],
        entity_class=victim_class,
        classification=PERMITTED_CLASSIFICATION,
        observed_at=EARLY,
    ).model_copy(
        update={"attributes": {split_attribute: PERMITTED_CLASSIFICATION}}
    )
    claim_json = _json.dumps(
        {
            "entity_class": claim.entity_class,
            "attributes": dict(claim.attributes),
        }
    )
    projected = _fluree_claim_projection(claim_json, kind=ENTITY_KIND)
    # D-14: the write path calls the same guarded builder, so the triple whose
    # attribute name carries the separator produces no key — the claim stores
    # no policy key at all rather than a forgeable one.
    assert policy_key(
        victim_class, split_attribute, PERMITTED_CLASSIFICATION
    ) is None
    assert P_POLICY_KEY not in projected, projected.get(P_POLICY_KEY)
    # The read side refuses the key that used to equal the stored one, for the
    # same reason and independently: every key either side CAN build carries
    # exactly two separators, so a smuggled component can never round-trip.
    assert policy_key(forged_class, "attr", PERMITTED_CLASSIFICATION) is None
    # Non-vacuity: the projection is still doing its job for a well-formed
    # triple, so the absence above is the guard firing and not the function
    # having stopped producing keys.
    clean_json = _json.dumps(
        {
            "entity_class": victim_class,
            "attributes": {"attr": PERMITTED_CLASSIFICATION},
        }
    )
    clean = _fluree_claim_projection(clean_json, kind=ENTITY_KIND)
    assert clean[P_POLICY_KEY] == [
        sep.join((victim_class, "attr", PERMITTED_CLASSIFICATION))
    ]

    # The refusal is wired to a decline, not swallowed into a narrowed push.
    reader = FlureeGraphReader.__new__(FlureeGraphReader)
    forged = GraphQuery(
        tenant_id=TENANT,
        as_of=datetime(2026, 1, 1, tzinfo=UTC),
        permitted_policy_bundle_versions=frozenset({"v1"}),
        classification_attribute_by_class={forged_class: "attr"},
        permitted_classifications=frozenset({PERMITTED_CLASSIFICATION}),
    )
    assert reader._translate_query(forged) is None

    # And the other half of the divergence, asserted rather than assumed: the
    # audited fallback — the answer the decline routes to — excludes this
    # claim, because its own class has no declared classification attribute.
    record = EntityRecord(
        claim_id="cr01", claim=claim, policy_bundle_version="v1"
    )
    assert _admissible_entity(record, query=forged) is False


def test_a_query_whose_policy_family_cannot_be_encoded_declines() -> None:
    """The refusal above is wired to a decline, not swallowed.

    Without this the builder could return `None` and the caller could push a
    key set missing an entry — narrowing the answer silently, which is the one
    failure mode worse than declining.
    """
    from datetime import UTC, datetime

    from ccf.graph.backends.fluree import (
        POLICY_KEY_SEPARATOR,
        FlureeGraphReader,
    )
    from ccf.graph.protocols import GraphQuery

    reader = FlureeGraphReader.__new__(FlureeGraphReader)
    forged = GraphQuery(
        tenant_id="t",
        as_of=datetime(2026, 1, 1, tzinfo=UTC),
        permitted_policy_bundle_versions=frozenset({"v1"}),
        classification_attribute_by_class={
            SEED_CLASS: f"clearance{POLICY_KEY_SEPARATOR}forged"
        },
        permitted_classifications=frozenset({PERMITTED_CLASSIFICATION}),
    )
    assert reader._translate_query(forged) is None


def test_an_over_budget_rendered_body_is_refused() -> None:
    """The byte budget measures the bytes that would actually be sent.

    `MAX_QUERY_BODY_BYTES` sits under the documented 1 MB `--max-query-size`,
    and `allowed_entities` is the caller-influenced term that can approach it
    (threat T-15.3-09). The guard bounds the generated request, never the
    vocabulary: an over-budget query is still answered, by the fallback.
    """
    from ccf.graph.backends.fluree import (
        MAX_QUERY_BODY_BYTES,
        FlureeGraphReader,
    )

    small = {"allowed": ["u://one", "u://two"]}
    assert FlureeGraphReader._within_body_budget("MATCH (c)", small)

    oversized = {"allowed": ["u://" + "x" * 64] * (MAX_QUERY_BODY_BYTES // 32)}
    assert not FlureeGraphReader._within_body_budget("MATCH (c)", oversized)


class _SeqOnlyStore:
    """The narrowest ``FlureeGraphStore`` ``_FlureeTxn`` can buffer against.

    ``insert_entity_claim`` / ``insert_relationship_claim`` touch the store in
    exactly two ways before they buffer: ``scope()`` for the two bound
    parameters, and ``post_query()`` for the committed-state existence read and
    the committed-state ``count()``. Nothing is sent until ``commit()``, which
    this test never calls — so the whole `P_SEQ` arithmetic is reachable with
    no server and no marker.

    ``committed`` maps a claim key to the number of claims for that key already
    in the ledger, which is what makes the ACROSS-transaction half of the
    collision expressible: the second transaction's read is the first
    transaction's write.
    """

    def __init__(self, committed: "dict[str, int] | None" = None) -> None:
        self.partition = "ccf"
        self._committed = dict(committed or {})

    def scope(self, tenant_id: str) -> dict[str, str]:
        return {"partition": self.partition, "tenant": tenant_id}

    def post_query(
        self, cypher: str, params: dict[str, object]
    ) -> list[dict[str, Any]]:
        from ccf.graph.backends.fluree_write import (
            _FLUREE_ENTITY_CLAIM_COUNT,
            _FLUREE_RELATIONSHIP_CLAIM_COUNT,
        )

        if cypher in (
            _FLUREE_ENTITY_CLAIM_COUNT,
            _FLUREE_RELATIONSHIP_CLAIM_COUNT,
        ):
            return [{"n": self._committed.get(str(params["key"]), 0)}]
        # Every other read is the existence check, and an empty ledger answers
        # it with no rows — so no insert resolves to the idempotent 0 and the
        # sequence arithmetic is what the test observes.
        return []


def _seqs(documents: "list[dict[str, Any]]", key_property: str, key: str) -> list[int]:
    from ccf.graph.backends.fluree import P_SEQ

    return [
        int(document[P_SEQ])
        for document in documents
        if document[key_property] == key
    ]


def test_buffered_claim_sequences_are_scoped_to_their_own_node() -> None:
    """`P_SEQ` counts THIS node's claims, never the whole transaction buffer.

    `P_SEQ` is "the graph rendering of SQLite's `rowid`" — the tiebreaker that
    orders two claims of one entity sharing an `observed_at`, under
    `SELECT_ENTITY_HISTORY`'s `ORDER BY c.ccf_observed_at, c.ccf_seq`. It is
    computed as *committed count for this key* + *this transaction's own
    buffered claims*, and the two terms must be scoped to the same key or the
    sum is not a sequence at all.

    Buffering `A1, B1, A2` in one transaction is the discriminating case. With
    an unscoped buffer term, `A` receives seq 0 and **2** while `B` receives
    **1** — and the collision is not merely cosmetic: the next transaction
    reads `count(A) == 2` and computes seq **2**, duplicating `A2`. Two claims
    of one entity sharing an `observed_at` and a `seq` then order
    non-deterministically and `_restitch_chain` yields a different supersession
    chain per read, silently.

    The defect was dormant because `BaseGraphWriter.upsert_entity` opens one
    transaction per claim, so `len(buffer)` was always 0. That is a property of
    today's caller, not of the adapter — and this is the batched adapter whose
    whole premise is buffering (review finding WR-07).
    """
    from ccf.graph.backends.fluree_write import _FlureeTxn
    from ccf.graph.backends.fluree import P_ENTITY_URI, P_RELATIONSHIP_KEY

    a, b = "counterparty://a", "counterparty://b"
    store = _SeqOnlyStore()
    txn = _FlureeTxn(store=store)  # type: ignore[arg-type]

    for entity_uri, claim_id in ((a, "a1"), (b, "b1"), (a, "a2")):
        assert (
            txn.insert_entity_claim(
                tenant_id="tenant-a",
                entity_uri=entity_uri,
                claim_id=claim_id,
                claim_json=json.dumps({"entity_class": SEED_CLASS}),
                observed_at="2026-03-01T00:00:00.000000Z",
                policy_bundle_version="v1",
            )
            == 1
        )

    buffered = txn._entity_claims
    assert _seqs(buffered, P_ENTITY_URI, a) == [0, 1], (
        "A's two buffered claims must form a gapless chain of their own; a "
        "whole-buffer count gives [0, 2]"
    )
    assert _seqs(buffered, P_ENTITY_URI, b) == [0], (
        "B's first claim is B's claim 0 — unrelated buffered claims for A "
        "must not advance it"
    )

    # The relationship mirror, same arithmetic on `relationship_key`.
    ab, cd = "rel://a-b", "rel://c-d"
    rel_txn = _FlureeTxn(store=_SeqOnlyStore())  # type: ignore[arg-type]
    for relationship_key, claim_id in ((ab, "r1"), (cd, "r2"), (ab, "r3")):
        assert (
            rel_txn.insert_relationship_claim(
                tenant_id="tenant-a",
                relationship_key=relationship_key,
                claim_id=claim_id,
                claim_json=json.dumps(
                    {
                        "relationship_type": "linked_to",
                        "subject_uri": "counterparty://a",
                        "object_uri": "counterparty://b",
                    }
                ),
                observed_at="2026-03-01T00:00:00.000000Z",
                policy_bundle_version="v1",
            )
            == 1
        )
    rel_buffered = rel_txn._relationship_claims
    assert _seqs(rel_buffered, P_RELATIONSHIP_KEY, ab) == [0, 1]
    assert _seqs(rel_buffered, P_RELATIONSHIP_KEY, cd) == [0]


def test_a_following_transaction_never_reissues_a_buffered_sequence() -> None:
    """The collision itself: seq values stay unique per node ACROSS commits.

    The previous test measures one transaction's arithmetic; this one measures
    the consequence that actually corrupts a chain. Transaction 1 buffers
    `A1, B1, A2`. Transaction 2 opens against the ledger those writes produced
    — `count(A) == 2`, `count(B) == 1` — and claims `A3`.

    `A3` must receive a sequence no earlier `A` claim holds. Under the unscoped
    buffer term `A2` held 2 and `A3` computes 2, which is the duplicate. The
    assertion is stated as "no repeat in the union", not "A3 == 2", so it
    remains discriminating if the sequence base ever changes.
    """
    from ccf.graph.backends.fluree_write import _FlureeTxn
    from ccf.graph.backends.fluree import P_ENTITY_URI

    a, b = "counterparty://a", "counterparty://b"
    first = _FlureeTxn(store=_SeqOnlyStore())  # type: ignore[arg-type]
    for entity_uri, claim_id in ((a, "a1"), (b, "b1"), (a, "a2")):
        first.insert_entity_claim(
            tenant_id="tenant-a",
            entity_uri=entity_uri,
            claim_id=claim_id,
            claim_json=json.dumps({"entity_class": SEED_CLASS}),
            observed_at="2026-03-01T00:00:00.000000Z",
            policy_bundle_version="v1",
        )
    committed_a = _seqs(first._entity_claims, P_ENTITY_URI, a)

    # Transaction 2 reads what transaction 1 wrote: two A claims, one B claim.
    second = _FlureeTxn(store=_SeqOnlyStore({a: 2, b: 1}))  # type: ignore[arg-type]
    second.insert_entity_claim(
        tenant_id="tenant-a",
        entity_uri=a,
        claim_id="a3",
        claim_json=json.dumps({"entity_class": SEED_CLASS}),
        observed_at="2026-03-01T00:00:00.000000Z",
        policy_bundle_version="v1",
    )
    next_a = _seqs(second._entity_claims, P_ENTITY_URI, a)

    chain = committed_a + next_a
    assert len(set(chain)) == len(chain), (
        f"two claims of one entity share a `ccf_seq`: {chain} — they would "
        "then order non-deterministically under ORDER BY observed_at, seq"
    )
    assert chain == sorted(chain), f"the chain is not monotonic: {chain}"


def test_the_write_path_materializes_exactly_the_key_the_read_path_pushes(
) -> None:
    """Write-side and read-side key construction cannot drift apart.

    The materialization still spans two modules — CINV-02 confines write code
    to `ccf.graph.backends.fluree_write`, which imports this backend, so the
    dependency cannot run the other way — but since D-14 it is **one
    construction called twice** rather than two copies of a separator-joined
    encoding. Two copies is exactly the shape that rots silently: a drifted
    separator produces a policy family matching *nothing*, with a `200` and an
    empty answer, which is the same silent-failure class probe F-A6 caught, and
    a guard on one copy only is what made CR-01 reachable. The agreement is
    asserted here anyway rather than assumed from the shared call, because what
    matters is the *projected value*, and a future projection could stop
    routing through `policy_key` without this assertion noticing the
    difference.
    """
    import json as _json

    from ccf.graph.backends.fluree import P_POLICY_KEY, policy_key
    from ccf.graph.backends.fluree_write import _fluree_claim_projection
    from ccf.graph.reader import ENTITY_KIND
    from tests.properties.strategies import CLASSIFICATION_ATTRIBUTE

    attribute = CLASSIFICATION_ATTRIBUTE[SEED_CLASS]
    claim_json = _json.dumps(
        {
            "entity_class": SEED_CLASS,
            "attributes": {attribute: PERMITTED_CLASSIFICATION},
        }
    )
    projected = _fluree_claim_projection(claim_json, kind=ENTITY_KIND)
    expected = policy_key(SEED_CLASS, attribute, PERMITTED_CLASSIFICATION)
    assert expected is not None
    assert projected[P_POLICY_KEY] == [expected]


@pytest.mark.fluree
def test_the_write_path_materializes_exactly_the_admit_keys_the_walk_pushes(
    fabric_boot: "Callable[..., FabricHandle]",
) -> None:
    """The walk's `$admissible` prefixes cannot drift from the write path's.

    Second instance of the same two-module problem the policy-key separator
    had, with a worse failure mode — and, unlike that one, still an actual
    duplicate. CINV-02 confines every write to
    `ccf.graph.backends.fluree_write`, and that module imports this backend, so
    the dependency cannot run the other way; the `e:` / `r:` prefixes
    nonetheless exist on both sides of the boundary as two literals, which is
    why the agreement is read back off the server here. D-14 collapsed the
    policy-key pair into one function and left this pair alone, so this test is
    what stands in for that collapse.

    A drifted prefix would make `all(n IN nodes(p) WHERE n.ccf_admit_key IN
    $admissible)` false for **every** path: an empty reached set, a `200`, and
    no error — indistinguishable from a correct empty answer without
    telemetry, and precisely the do-not-copy #1 failure the interposition
    exists to avoid. So the agreement is read back off the server, not
    commented.
    """
    from ccf.graph.backends.fluree import (
        ENTITY_ADMIT_PREFIX,
        RELATIONSHIP_ADMIT_PREFIX,
    )

    uri = ENTITY_POOL[SEED_CLASS][0]
    other = ENTITY_POOL[MID_CLASS][0]
    handle = fabric_boot(backend="fluree")
    for entity_uri, entity_class in ((uri, SEED_CLASS), (other, MID_CLASS)):
        handle.worker.admit_entity_claim(
            tenant_id=TENANT,
            claim=entity_claim(
                entity_uri=entity_uri,
                entity_class=entity_class,
                classification=PERMITTED_CLASSIFICATION,
                observed_at=EARLY,
            ),
        )
    written = handle.worker.admit_relationship_claim(
        tenant_id=TENANT,
        claim=relationship_claim(
            relationship_type=EDGE_TYPE,
            subject_uri=uri,
            object_uri=other,
            observed_at=EARLY,
        ),
    )

    store: Any = handle.reader._store
    scope = store.scope(TENANT)
    entities = store.post_query(
        "MATCH (n:CcfEntity {ccf_partition: $partition,"
        " ccf_tenant_id: $tenant, ccf_entity_uri: $key})"
        " RETURN n.ccf_admit_key AS admit_key",
        {**scope, "key": uri},
    )
    edges = store.post_query(
        _EDGE_NODE_PROBE, {**scope, "key": written.node_key}
    )
    assert [row["admit_key"] for row in entities] == [
        ENTITY_ADMIT_PREFIX + uri
    ]
    assert [row["admit_key"] for row in edges] == [
        RELATIONSHIP_ADMIT_PREFIX + written.node_key
    ]


def test_the_cap_matcher_is_the_string_the_server_actually_sends() -> None:
    """The decline matcher is bound to probe F-A3(c)'s measurement.

    `PATH_CAP_MARKER` decides whether a `400` becomes a decline or propagates.
    Matched too broadly it would swallow genuine statement defects into a
    silent permanent degrade; matched against a string the server never sends
    it would let a cap error reach the caller as a `500`-shaped failure for a
    question the fallback can answer. Neither is visible from reading the
    adapter, so the constant is pinned against the text the probe captured.
    """
    from ccf.graph.backends.fluree import PATH_CAP_MARKER

    assert PATH_CAP_MARKER == CAP_ERROR_MARKER
    # Narrow enough to exclude the error CLASS, which also covers genuine
    # statement defects that must keep failing loudly.
    assert "InvalidQuery" not in PATH_CAP_MARKER


@pytest.mark.fluree
def test_fluree_non_traverse_queries_are_pushed_not_silently_degraded(
    fabric_boot: "Callable[..., FabricHandle]",
) -> None:
    """The Cypher ran in the engine — telemetry, not byte-identity alone.

    **Byte-identity to the fallback is a conformance bar, not a pushdown
    bar.** D-04 makes the degraded posture byte-identical *by design* (`GQ-34`
    at docs/GRAPH_QUERY_SEMANTICS.md:609), so a `_translate_query` that always
    returned ``None`` would pass the entire differential corpus — green, with
    zero pushdown actually happening. That is precisely the defect the 15.2
    §3.1 phase-close review caught on Neo4j, where the leg's whole evidence was
    the corpus; this test ships in the same plan as the translation so the
    claim never rests on evidence that cannot distinguish a working
    translation from an absent one (threat T-15.3-11).

    The four shapes are the non-traverse families stage 1 actually pushes —
    the traverse family declines by design and is asserted separately below:

    * **as-of only** at a boundary instant — the degenerate everything-question
      (`GQ-05`), which every other family is layered on;
    * **validity-constrained** — the `GQ-09` window over the write-time
      canonical re-renderings, the projection §R8 vector 1 could have
      re-broken;
    * **the policy family** — the one whose design probe F-A6 *determined*
      rather than left to preference, pushed as membership over the
      materialized key instead of the dynamic property access that evaluates
      to null here;
    * **`allowed_entities`-bearing** — the uniform rule (`GQ-15`) as a request
      list parameter, and the term that can reach the query-body budget.

    ``memory`` is the differential control — the always-on KV floor, which has
    no native translation at all — so the canonical bytes and the reached sets
    are held identical while only the fluree leg is asserted pushed.
    """
    from ccf.graph.protocols import GraphQuery
    from tests.conformance.test_substrate_properties import (
        PERMITTED_CLASSIFICATIONS,
    )
    from tests.properties.strategies import CLASSIFICATION_ATTRIBUTE

    entities, relationships = chain_claims(
        mid_classification=PERMITTED_CLASSIFICATION
    )
    seed_uri, mid_uri, target_uri = chain_uris()

    answers: dict[str, list[bytes]] = {}
    reached: dict[str, list[list[str]]] = {}
    for backend in ("fluree", "memory"):
        handle = fabric_boot(backend=backend)
        for claim in entities:
            handle.worker.admit_entity_claim(tenant_id=TENANT, claim=claim)
        for edge in relationships:
            handle.worker.admit_relationship_claim(
                tenant_id=TENANT, claim=edge
            )
        # The booted worker's own stamped version is the only one persisted
        # records can carry, so it is the only one a policy family can
        # meaningfully admit.
        version = handle.worker.policy_bundle_version
        queries = (
            GraphQuery(tenant_id=TENANT, as_of=ON_BOUNDARY),
            GraphQuery(
                tenant_id=TENANT,
                as_of=ON_BOUNDARY,
                require_valid_at_boundary=True,
            ),
            GraphQuery(
                tenant_id=TENANT,
                as_of=ON_BOUNDARY,
                permitted_policy_bundle_versions=frozenset({version}),
                classification_attribute_by_class=dict(
                    CLASSIFICATION_ATTRIBUTE
                ),
                permitted_classifications=frozenset(PERMITTED_CLASSIFICATIONS),
            ),
            GraphQuery(
                tenant_id=TENANT,
                as_of=ON_BOUNDARY,
                allowed_entities=frozenset({seed_uri, mid_uri}),
            ),
        )
        views = [handle.reader.query(q) for q in queries]
        answers[backend] = [canonical_bytes(view) for view in views]
        reached[backend] = [
            sorted(record.claim.entity_uri for record in view.entities)
            for view in views
        ]
        if backend == "fluree":
            # The whole point of this test: every one of the four answers came
            # out of Cypher, none out of the fallback.
            assert handle.reader.translated_answers == len(queries)
            assert handle.reader.fallback_answers == 0

    assert answers["fluree"] == answers["memory"]
    assert reached["fluree"] == [
        sorted((seed_uri, mid_uri, target_uri)),
        sorted((seed_uri, mid_uri, target_uri)),
        sorted((seed_uri, mid_uri, target_uri)),
        sorted((seed_uri, mid_uri)),
    ]


@pytest.mark.fluree
def test_fluree_traversal_is_pushed_not_silently_degraded(
    fabric_boot: "Callable[..., FabricHandle]",
) -> None:
    """The interposed walk ran in the engine — telemetry, not byte-identity.

    **Byte-identity to the fallback is a conformance bar, not a pushdown
    bar.** D-04 makes the degraded posture byte-identical *by design* (`GQ-34`
    at docs/GRAPH_QUERY_SEMANTICS.md:609), so a `_translate_query` that always
    returned ``None`` would pass the entire differential corpus — green, with
    zero pushdown actually happening. Plan 15.3-03 did not argue that; it
    **demonstrated** it, monkeypatching the translation away and watching all
    seven differential tests stay green while the telemetry test went red. This
    test is the traversal half of the same discrimination, and it was
    falsification-tested the same way before the promotion was claimed.

    The four shapes are the ones a variable-length ``MATCH`` can get wrong,
    mirroring the Neo4j and Mongo trap-shape tests so a regression names
    *which* correction broke:

    * **depth 0** — starts only, no hop (`GQ-10`). The ``*1..0`` bound does not
      exist, so this must skip the ``MATCH`` entirely;
    * **depth 1** — one CCF hop, which is TWO Cypher hops through the
      interposed edge node;
    * **depth 2 over a mixed-direction chain** — CCF traversal is undirected,
      so the second edge pointing target->mid must still be crossable. Cypher's
      ``-[:T]-`` is first-class undirected, which is why the interposed model
      is written once and needs none of Mongo's forward/reverse doubling;
    * **the resurrection shape** — the same depth-2 question with the
      intermediate outside ``allowed_entities``. A walk that crossed it would
      re-reach the target the set excludes (`GQ-15` at
      docs/GRAPH_QUERY_SEMANTICS.md:300; threat T-15.2-26). **This is the one
      that most needs the telemetry, because a degrade answers it correctly
      too** — and on this substrate it is also the shape that proves hop
      admissibility is enforced *during* the walk rather than on its output,
      which probe F-A3(b) measured as a path count of zero.

    ``memory`` is the differential control — the always-on KV floor, which has
    no native translation at all — so the reached sets and the canonical bytes
    are held identical while only the fluree leg is asserted pushed.
    """
    from ccf.graph.protocols import GraphQuery, TraversalSpec

    seed_uri, mid_uri, target_uri = chain_uris()
    entities, relationships = chain_claims(
        mid_classification=PERMITTED_CLASSIFICATION
    )

    def walk_at(depth: int) -> TraversalSpec:
        return TraversalSpec(
            seed_entity_classes=SEED_CLASSES,
            relationship_types=RELATIONSHIP_TYPES,
            depth_limit=depth,
        )

    queries = (
        GraphQuery(tenant_id=TENANT, as_of=ON_BOUNDARY, traverse=walk_at(0)),
        GraphQuery(tenant_id=TENANT, as_of=ON_BOUNDARY, traverse=walk_at(1)),
        GraphQuery(tenant_id=TENANT, as_of=ON_BOUNDARY, traverse=walk_at(2)),
        GraphQuery(
            tenant_id=TENANT,
            as_of=ON_BOUNDARY,
            traverse=walk_at(2),
            allowed_entities=frozenset({seed_uri, target_uri}),
        ),
    )

    answers: dict[str, list[bytes]] = {}
    reached: dict[str, list[set[str]]] = {}
    for backend in ("fluree", "memory"):
        handle = fabric_boot(backend=backend)
        _write_chain(handle, entities, relationships)
        views = [handle.reader.query(q) for q in queries]
        answers[backend] = [canonical_bytes(view) for view in views]
        reached[backend] = [
            {record.claim.entity_uri for record in view.entities}
            for view in views
        ]
        if backend == "fluree":
            # The whole point of this test: every one of the four answers came
            # out of Cypher, none out of the fallback.
            assert handle.reader.translated_answers == len(queries)
            assert handle.reader.fallback_answers == 0

    assert answers["fluree"] == answers["memory"]
    assert reached["fluree"] == [
        {seed_uri},
        {seed_uri, mid_uri},
        {seed_uri, mid_uri, target_uri},
        {seed_uri},
    ]


@pytest.mark.fluree
def test_a_capped_walk_declines_to_the_fallback_rather_than_failing(
    fabric_boot: "Callable[..., FabricHandle]",
) -> None:
    """T-15.3-13's mitigation, executed rather than described.

    The path-enumeration cap **errors rather than truncating** (probe
    F-A3(c)), so it is a hard failure that would otherwise reach the caller as
    an `httpx.HTTPStatusError` for a question the fallback can answer
    perfectly well. The adapter catches it and declines the whole query.

    Three things are asserted together, and the combination is the mitigation:

    * the query is still **answered**, byte-identically to the `memory`
      control — a decline changes which path answers, never the answer
      (D-04 / `GQ-34`);
    * the decline is **visible**: `fallback_answers == 1`, which is the
      operator-facing signal the residual risk is recorded against;
    * `translated_answers == 0`, so nothing partial was returned — the
      all-or-nothing contract (`GQ-32`) holds across a decline that happens
      *after* a round trip.

    The graph is every ontology-legal edge over the whole fixture pool (12
    entities, 27 edges) — small, and still enough at CCF depth 5 to exceed the
    server's 1000-path budget. The corpus's deepest walk is depth 4 over
    three-node chains, so nothing in the differential suite approaches this.
    """
    from ccf.graph.protocols import GraphQuery, TraversalSpec

    query = GraphQuery(
        tenant_id=TENANT,
        as_of=ON_BOUNDARY,
        traverse=TraversalSpec(
            seed_entity_classes=SEED_CLASSES,
            relationship_types=RELATIONSHIP_TYPES,
            depth_limit=5,
        ),
    )
    answers: dict[str, bytes] = {}
    for backend in ("fluree", "memory"):
        handle = fabric_boot(backend=backend)
        for entity_class, pool in ENTITY_POOL.items():
            for uri in pool:
                handle.worker.admit_entity_claim(
                    tenant_id=TENANT,
                    claim=entity_claim(
                        entity_uri=uri,
                        entity_class=entity_class,
                        classification=PERMITTED_CLASSIFICATION,
                        observed_at=EARLY,
                    ),
                )
        for rtype, subject_class, object_class in RELATIONSHIP_RULES:
            for subject_uri in ENTITY_POOL[subject_class]:
                for object_uri in ENTITY_POOL[object_class]:
                    handle.worker.admit_relationship_claim(
                        tenant_id=TENANT,
                        claim=relationship_claim(
                            relationship_type=rtype,
                            subject_uri=subject_uri,
                            object_uri=object_uri,
                            observed_at=EARLY,
                        ),
                    )
        answers[backend] = canonical_bytes(handle.reader.query(query))
        if backend == "fluree":
            assert handle.reader.fallback_answers == 1
            assert handle.reader.translated_answers == 0

    assert answers["fluree"] == answers["memory"]


@pytest.mark.fluree
def test_fluree_interposed_depth_matches_the_fallback_at_zero_one_two_and_three(
    fabric_boot: "Callable[..., FabricHandle]",
) -> None:
    """The CCF-depth-to-Cypher-hop doubling, MEASURED at four depths.

    **Do not reason about the ×2 — measure it.** Mongo's four `$graphLookup`
    corrections adjudicate as: two transfer verbatim (they are really Neo4j's),
    one (`maxDepth: depth_limit - 1`) is structurally absent because Cypher's
    `*1..N` is 1-based, and one is **replaced** — interposition introduces
    `M = 2d`, which is an off-by-factor-of-two and exactly the same class of
    error. The honest count of corrections is five, not zero.

    An off-by-factor-of-two is silent: it produces a plausible answer that is
    simply the answer to a different question, and it surfaces only as an
    ordinary differential failure at depth >= 2 (15.3-RESEARCH.md Pitfall 13).
    So the chain here is **three hops**, not the corpus's two — a doubled bound
    over-reaches by one CCF hop and a halved one under-reaches by one, and both
    are visible only once depth 3 is asked. This assertion runs BEFORE the
    promotion gate rather than after it.

    `memory` is the differential control: the always-on KV floor, which has no
    native translation at all, so its answer is the fallback's by construction.
    Both `canonical_bytes` and the reached entity-URI sets are held identical,
    because equal bytes alone would not localise a divergence to the walk.
    """
    from ccf.graph.protocols import GraphQuery, TraversalSpec

    entities, relationships, uris = _extended_chain()
    seed_uri, mid_uri, target_uri, far_uri = uris
    depths = (0, 1, 2, 3)
    queries = tuple(
        GraphQuery(
            tenant_id=TENANT,
            as_of=ON_BOUNDARY,
            traverse=TraversalSpec(
                seed_entity_classes=SEED_CLASSES,
                relationship_types=RELATIONSHIP_TYPES,
                depth_limit=depth,
            ),
        )
        for depth in depths
    )

    answers: dict[str, list[bytes]] = {}
    reached: dict[str, list[list[str]]] = {}
    for backend in ("fluree", "memory"):
        handle = fabric_boot(backend=backend)
        _write_chain(handle, entities, relationships)
        views = [handle.reader.query(q) for q in queries]
        answers[backend] = [canonical_bytes(view) for view in views]
        reached[backend] = [
            sorted(record.claim.entity_uri for record in view.entities)
            for view in views
        ]

    assert answers["fluree"] == answers["memory"]
    assert reached["fluree"] == reached["memory"]
    # Spelled out as well as compared, so a control that silently broke in the
    # same direction could not make this pass.
    assert reached["fluree"] == [
        [seed_uri],
        sorted((seed_uri, mid_uri)),
        sorted((seed_uri, mid_uri, target_uri)),
        sorted((seed_uri, mid_uri, target_uri, far_uri)),
    ]


@pytest.mark.fluree
def test_the_traverse_posture_is_recorded_in_telemetry(
    fabric_boot: "Callable[..., FabricHandle]",
) -> None:
    """A depth-1 walk is answered IN THE ENGINE, and that is *visible*.

    **This is the flipped assertion, and the flip is the promotion's most
    direct evidence.** Plan 15.3-03 pinned the stage-1 posture here exactly —
    `fallback_answers == 1`, `translated_answers == 0` — precisely so that
    landing the walk would have to come here and invert it. Under D-04 a
    declined translation is fully conformant (the fallback's answer *is* the
    definition), so this counter is the ONLY thing distinguishing "walk
    deferred" from "walk pushed"; deleting the assertion instead of inverting
    it would have removed that distinction from the tree.

    The numbers stay pinned exactly rather than bounded, for the same reason
    they were pinned before.
    """
    from ccf.graph.protocols import GraphQuery, TraversalSpec

    entities, relationships = chain_claims(
        mid_classification=PERMITTED_CLASSIFICATION
    )
    handle = fabric_boot(backend="fluree")
    for claim in entities:
        handle.worker.admit_entity_claim(tenant_id=TENANT, claim=claim)
    for edge in relationships:
        handle.worker.admit_relationship_claim(tenant_id=TENANT, claim=edge)

    handle.reader.query(
        GraphQuery(
            tenant_id=TENANT,
            as_of=ON_BOUNDARY,
            traverse=TraversalSpec(
                seed_entity_classes=SEED_CLASSES,
                relationship_types=RELATIONSHIP_TYPES,
                depth_limit=1,
            ),
        )
    )
    assert handle.reader.fallback_answers == 0
    assert handle.reader.translated_answers == 1


# --- the pinned read (plan 24.5-02; ledger rows 24.5-L-01, L-03, L-04) -------
#
# Criterion 5: a Fluree read can be PINNED to a transaction `t` as an upper
# bound, distinct from the `Fluree-Min-T` FLOOR — proven by advancing a fresh
# ledger between two reads and watching the two answer DIFFERENTLY. Research
# measured (24.5-RESEARCH.md §A.1) that the Cypher route ignores every pin
# form silently, which is why the pin rides JSON-LD `from: <ledger>@t:N`
# (D-IMPL-240 (2)) and why the probe below is the criterion-5 test itself: a
# future server change that starts honoring a header, or stops honoring the
# JSON-LD pin, is caught here rather than inferred (Pitfall 2).

#: The JSON-LD pinned-select envelope, captured VERBATIM on
#: ``fluree/server:4.1.4`` (2026-09-02) — the F-A1 discipline applied to the
#: second read dialect, because this envelope is documented nowhere in the
#: tree (24.5-PATTERNS.md "No Analog Found" row 1) and ``_pinned_row`` is
#: written against these bytes. Two facts it fixes: the answer is a BARE
#: array of node objects keyed by predicate name, and a predicate a node does
#: not carry is ABSENT rather than ``null`` — the second node was written
#: superseded, the first was not. Values are probe values, not vocabulary.
PINNED_SELECT_ENVELOPE_AT_T2: list[dict[str, Any]] = [
    {
        "ccf_claim_id": "c1",
        "ccf_claim_json": '{"a":1}',
        "ccf_entity_uri": "e://1",
        "ccf_policy_bundle_version": "v1",
    },
    {
        "ccf_claim_id": "c2",
        "ccf_claim_json": '{"a":2}',
        "ccf_entity_uri": "e://2",
        "ccf_policy_bundle_version": "v1",
        "ccf_superseded_at": "2026-02-01T00:00:00Z",
        "ccf_superseded_by": "c9",
    },
]

#: The three phrases criterion 7 requires the adapter's module docstring to
#: name — the ``TEMPORAL_AXES`` vocabulary in prose, one phrase per axis.
TEMPORAL_AXIS_PHRASES: tuple[str, ...] = ("event time", "transaction time", "as_of")


def _axes_named(docstring: str) -> list[str]:
    """The axis phrases ``docstring`` does NOT name — empty when all three are.

    Shared by the test and its in-test control so the two cannot drift: the
    control proves this predicate can be made to fail, which is what makes
    the test's green worth anything.
    """
    return [phrase for phrase in TEMPORAL_AXIS_PHRASES if phrase not in docstring]


def _claim_nodes(
    claim: "EntityClaim", *, partition: str, policy_bundle_version: str
) -> list[dict[str, Any]]:
    """One entity claim as ``fluree_write.py`` writes it — a claim node and its lineage node.

    The same predicates, the same canonical renderings: ``claim_json`` is
    the claim minus lineage through ``canonical_bytes`` (the
    ``ccf.graph._writer._claim_payload`` rule), ``observed_at`` is canonical
    UTC text, the lineage entry rides in its own ``CcfLineage`` node keyed
    the way ``SELECT_LINEAGE`` binds. Written here, outside the adapter, so
    the pinned read is measured against rows the adapter did not author.
    """
    from ccf.contracts.canonical import canonical_timestamp, content_hash
    from ccf.contracts.claims import EntityClaim
    from ccf.graph.backends.fluree import (
        L_ENTITY_CLAIM,
        L_LINEAGE,
        P_CLAIM_ID,
        P_CLAIM_JSON,
        P_CLAIM_KIND,
        P_ENTITY_CLASS,
        P_ENTITY_URI,
        P_ENTRY_JSON,
        P_LINEAGE_ID,
        P_NODE_KEY,
        P_OBSERVED_AT,
        P_PARTITION,
        P_POLICY_VERSION,
        P_SEQ,
        P_TENANT,
    )
    from ccf.graph.reader import ENTITY_KIND

    payload = canonical_bytes(
        {
            name: getattr(claim, name)
            for name in EntityClaim.model_fields
            if name != "lineage"
        }
    ).decode("utf-8")
    claim_id = content_hash(payload)
    entry = next(iter(claim.lineage))
    return [
        {
            "@id": f"ccf_ec_{content_hash([claim.entity_uri, claim_id])}",
            "@type": L_ENTITY_CLAIM,
            P_PARTITION: partition,
            P_TENANT: claim.tenant_id,
            P_ENTITY_URI: claim.entity_uri,
            P_CLAIM_ID: claim_id,
            P_CLAIM_JSON: payload,
            P_OBSERVED_AT: canonical_timestamp(claim.observed_at),
            P_POLICY_VERSION: policy_bundle_version,
            P_SEQ: 0,
            P_ENTITY_CLASS: claim.entity_class,
        },
        {
            "@id": f"ccf_l_{content_hash([claim.entity_uri, claim_id])}",
            "@type": L_LINEAGE,
            P_PARTITION: partition,
            P_TENANT: claim.tenant_id,
            P_CLAIM_KIND: ENTITY_KIND,
            P_NODE_KEY: claim.entity_uri,
            P_CLAIM_ID: claim_id,
            P_LINEAGE_ID: content_hash([entry.envelope_id]),
            P_ENTRY_JSON: canonical_bytes(entry).decode("utf-8"),
        },
    ]


@pytest.mark.fluree
def test_fa7_a_pinned_read_answers_the_pinned_state_and_the_floor_answers_the_head(
    fluree_url: str,
) -> None:
    """Criterion 5, `24.5-L-01`: floor and pin answer DIFFERENTLY on an advanced ledger.

    A fresh ledger takes one claim at ``t=1`` and a second at ``t=2``. Then,
    against the same ledger and the same ``as_of``:

    (a) the reader's ``snapshot_pin()`` reports the head, ``t=2``;
    (b) ``query_pinned`` at ``t=1`` answers ONE entity — with its lineage,
        because the L axis is pinned with the claims;
    (c) the unpinned ``as_of`` — which threads only the ``Fluree-Min-T``
        FLOOR on the Cypher route — answers TWO, and is byte-identical to
        ``query_pinned`` at the head, the D-04 oracle equality;
    (d) a raw Cypher read with ``Fluree-Min-T: 1`` — the floor stated
        explicitly, at exactly the value the pin used — ALSO answers two.
        That is `L-01`'s finding restated as an assertion: a floor is a
        lower bound and cannot express what the pin expresses;
    (e) the as-of cut still applies UNDER the pin: an ``as_of`` before either
        ``observed_at`` answers nothing at ``t=2``. Two axes, never one.

    The raw envelope of one pinned select is asserted against the verbatim
    capture ``PINNED_SELECT_ENVELOPE_AT_T2`` records the SHAPE of, and
    ``_pinned_row`` is shown mapping that capture to the six Cypher column
    names with ``None`` where a predicate is absent.
    """
    from datetime import UTC, datetime

    from ccf.graph.backends.fluree import (
        _PINNED_ENTITY_COLUMNS,
        FlureeGraphStore,
        _pinned_row,
        _pinned_select,
    )
    from ccf.graph.protocols import GraphQuery, StoreSnapshotPin

    partition = "ccf"
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    observed = datetime(2026, 3, 1, tzinfo=UTC)
    after_both = datetime(2026, 4, 1, tzinfo=UTC)
    before_both = datetime(2026, 1, 1, tzinfo=UTC)
    ledger = _fresh_ledger()
    first, second = (
        entity_claim(
            entity_uri=uri,
            entity_class=SEED_CLASS,
            classification=PERMITTED_CLASSIFICATION,
            observed_at=observed,
            tenant_id=tenant,
        )
        for uri in (chain_uris(0)[0], chain_uris(1)[0])
    )

    with FlureeGraphStore(url=fluree_url, partition=partition, ledger=ledger) as store:
        with httpx.Client(timeout=TIMEOUT) as client:
            base, _ = _api_base(client, fluree_url)
            for claim in (first, second):
                receipt = _insert(
                    client,
                    base,
                    ledger,
                    _claim_nodes(claim, partition=partition, policy_bundle_version="pb-1"),
                )
                assert receipt.status_code == 200, receipt.text
            assert receipt.json()["t"] == 2, receipt.text

            # (d) the FLOOR, stated at the pin's own value, answers the head.
            floored = _cypher(
                client,
                base,
                ledger,
                "MATCH (c:CcfEntityClaim {ccf_partition: $partition,"
                " ccf_tenant_id: $tenant}) RETURN c.ccf_entity_uri AS entity_uri",
                {"partition": partition, "tenant": tenant},
                min_t=1,
            )
            assert floored.status_code == 200, floored.text
            assert len(_rows(floored)) == 2, _rows(floored)

        reader = store.reader
        # (a)
        assert reader.snapshot_pin() == StoreSnapshotPin(substrate="fluree", pin="2")

        # The envelope, measured against the live server: bare array, keyed by
        # predicate, absent predicates absent — the shape the capture records.
        envelope = store.post_query_pinned(
            _pinned_select(
                "CcfEntityClaim",
                partition=partition,
                tenant=tenant,
                columns=_PINNED_ENTITY_COLUMNS,
            ),
            pin_t=1,
        )
        assert isinstance(envelope, list) and len(envelope) == 1, envelope
        assert set(envelope[0]) == {
            "ccf_claim_id",
            "ccf_claim_json",
            "ccf_entity_uri",
            "ccf_policy_bundle_version",
        }, envelope
        assert envelope[0]["ccf_entity_uri"] == first.entity_uri
        # The verbatim capture maps to the six Cypher columns, None for absent.
        mapped = [
            _pinned_row(node, columns=_PINNED_ENTITY_COLUMNS)
            for node in PINNED_SELECT_ENVELOPE_AT_T2
        ]
        assert [sorted(row) for row in mapped] == [
            sorted(_PINNED_ENTITY_COLUMNS)
        ] * 2
        assert mapped[0]["superseded_by"] is None
        assert mapped[0]["superseded_at"] is None
        assert mapped[1]["superseded_by"] == "c9"
        assert mapped[1]["superseded_at"] == "2026-02-01T00:00:00Z"

        # (b) pinned at t=1: ONE, with lineage.
        q = GraphQuery(tenant_id=tenant, as_of=after_both)
        pinned = reader.query_pinned(q, pin=StoreSnapshotPin(substrate="fluree", pin="1"))
        assert [e.claim.entity_uri for e in pinned.entities] == [first.entity_uri]
        assert len(pinned.entities[0].claim.lineage) == 1

        # (c) unpinned — floor only — TWO; byte-identical to the pin at head.
        head = reader.as_of(tenant_id=tenant, at=after_both)
        assert sorted(e.claim.entity_uri for e in head.entities) == sorted(
            (first.entity_uri, second.entity_uri)
        )
        at_head = reader.query_pinned(q, pin=StoreSnapshotPin(substrate="fluree", pin="2"))
        assert canonical_bytes(at_head) == canonical_bytes(head)

        # (e) the as-of cut still applies under the pin.
        early = GraphQuery(tenant_id=tenant, as_of=before_both)
        assert (
            reader.query_pinned(early, pin=StoreSnapshotPin(substrate="fluree", pin="2")).entities
            == ()
        )


@pytest.mark.fluree
def test_fa7_a_pin_past_the_head_is_refused_identifiably(fluree_url: str) -> None:
    """A pin the ledger has not reached is `FlureePinAhead`, naming both `t`s.

    The measured ``408 err:db/ReadAfterWriteTimeout`` — the same server
    condition a floor past the head raises on the Cypher route — surfaces as
    the `LookupError` subclass `SnapshotPinnable.query_pinned` declares, with
    the asked pin and the server's ``current t`` in the message and nothing
    from the URL (threat T-24.5-04).
    """
    from datetime import UTC, datetime

    from ccf.graph.backends.fluree import FlureeGraphStore, FlureePinAhead
    from ccf.graph.protocols import GraphQuery, StoreSnapshotPin

    ledger = _fresh_ledger()
    tenant = f"tenant-{uuid.uuid4().hex[:8]}"
    claim = entity_claim(
        entity_uri=chain_uris(0)[0],
        entity_class=SEED_CLASS,
        classification=PERMITTED_CLASSIFICATION,
        observed_at=datetime(2026, 3, 1, tzinfo=UTC),
        tenant_id=tenant,
    )
    with FlureeGraphStore(url=fluree_url, partition="ccf", ledger=ledger) as store:
        with httpx.Client(timeout=TIMEOUT) as client:
            base, _ = _api_base(client, fluree_url)
            for _ in range(2):
                receipt = _insert(
                    client,
                    base,
                    ledger,
                    _claim_nodes(claim, partition="ccf", policy_bundle_version="pb-1"),
                )
                assert receipt.status_code == 200, receipt.text
        assert store.head_t() == 2
        q = GraphQuery(tenant_id=tenant, as_of=datetime(2026, 4, 1, tzinfo=UTC))
        with pytest.raises(FlureePinAhead) as ahead:
            store.reader.query_pinned(q, pin=StoreSnapshotPin(substrate="fluree", pin="3"))
        assert isinstance(ahead.value, LookupError)
        assert "t=3" in str(ahead.value)
        assert "current t=2" in str(ahead.value)
        assert fluree_url not in str(ahead.value)


def test_a_t_offered_as_an_as_of_is_refused(
    fabric_boot: "Callable[..., FabricHandle]",
) -> None:
    """Criterion 5's `D-IMPL-88` guard: three plants, each refused, before any I/O.

    * a `StoreSnapshotPin` where `GraphQuery.as_of` is typed — pydantic
      refuses the model at the seam (the type-level guard);
    * a `datetime` offered as a pin — `TypeError` naming `D-IMPL-88`;
    * a bare `int` offered as a pin — the same `TypeError`.

    The reader is constructed without a store and never reaches the wire:
    `_require_fluree_pin` runs first. And the Protocol is structural — the
    Fluree reader IS `SnapshotPinnable`; a SQLite reader, which has no
    native pin, is NOT, with no stub anywhere (D-10).
    """
    from datetime import UTC, datetime

    import pydantic

    from ccf.graph.backends.fluree import FlureeGraphReader
    from ccf.graph.protocols import GraphQuery, SnapshotPinnable, StoreSnapshotPin

    at = datetime(2026, 9, 2, tzinfo=UTC)
    with pytest.raises(pydantic.ValidationError):
        GraphQuery(tenant_id="t", as_of=StoreSnapshotPin(substrate="fluree", pin="2"))  # type: ignore[arg-type]

    reader = FlureeGraphReader.__new__(FlureeGraphReader)
    q = GraphQuery(tenant_id="t", as_of=at)
    with pytest.raises(TypeError, match="D-IMPL-88"):
        reader.query_pinned(q, pin=at)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="D-IMPL-88"):
        reader.query_pinned(q, pin=2)  # type: ignore[arg-type]

    assert isinstance(reader, SnapshotPinnable)
    sqlite_reader = fabric_boot(backend="sqlite").reader
    assert not isinstance(sqlite_reader, SnapshotPinnable)


def test_the_module_docstring_names_the_three_temporal_axes() -> None:
    """Criterion 7, `24.5-L-03`/`L-04`: the adapter's docstring names all three axes.

    ``event time``, ``transaction time`` and ``as_of`` — the
    ``TEMPORAL_AXES`` vocabulary in prose — plus the ruling that keeps them
    apart, ``D-IMPL-88``. Then the control, in the
    ``tests/products/test_refusal_envelope.py::test_control_1_a_new_direct_gate_subclass_fails_the_gate`` voice: for
    each phrase, the docstring with that phrase removed must FAIL the same
    predicate, naming exactly that phrase. A predicate that cannot be made
    to fail proves nothing.
    """
    import ccf.graph.backends.fluree as module

    docstring = module.__doc__ or ""
    assert _axes_named(docstring) == [], _axes_named(docstring)
    assert "D-IMPL-88" in docstring

    for phrase in TEMPORAL_AXIS_PHRASES:
        mutated = docstring.replace(phrase, "")
        assert _axes_named(mutated) == [phrase], (phrase, _axes_named(mutated))
