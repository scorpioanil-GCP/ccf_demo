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
    needs **per-operation** rowcounts (``_writer.py:333-338``) and one POST
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
