"""Up-front probes for the Fluree v4 substrate — no adapter code exists yet.

Plan 15.3-01, D-06. Everything here runs in an environment with **no extra
installed at all**, which is the exact inversion of what
``test_neo4j_backend.py:1-10`` says about itself: ``httpx==0.28.1`` is a direct
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
import shutil
import subprocess
import uuid
from typing import TYPE_CHECKING, Any

import httpx
import pytest

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

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
    acquisition statements plan 15.3-02 copies from ``backends/neo4j.py:519-565``
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
        # (`_writer.py:333-338`). Nothing depends on the cross-check.
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
