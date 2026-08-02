"""Deterministic, domain-neutral synthetic dataset generator (PERF-02).

Phase 11 decisions D-06..D-09 and D-27..D-30:

- One ``random.Random(PERF_SEED)`` instance is threaded through everything;
  repeated runs are byte-identical (D-08).
- Topology is hub-heavy/skewed: ~1% of entities are hubs of the subject
  class, the long tail attaches to hubs with Zipf-ish weights (D-27), and
  edges grow linearly with entities so average degree is constant across
  rungs (D-28).
- Every entity carries 3–10 timestamped observations, hubs at the top of the
  range (D-29). Timestamps derive from a fixed epoch plus seeded offsets —
  never a clock read.
- The same seeded pass emits both the ``SignalEnvelope`` stream and the
  deterministic decision-record stream for the replay ladder (D-30).

All ontology vocabulary (entity classes, payload keys, attribute names,
lexicon words, classification values) lives in
``perf/synth/artifacts/ontology.yaml`` (D-09, CLAUDE.md §6.4) — this module
interprets the artifact and holds none of it.

Structural constraint (single-writer, CLAUDE.md §10): this module imports L1
contracts only. It emits envelopes; ingestion happens exclusively through
``handle.worker.ingest`` in ``perf/conftest.py``.
"""

from __future__ import annotations

import hashlib
import random
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, NamedTuple

import yaml

from ccf.signal.envelope import SignalEnvelope, SourceIdentity

#: The documented fixed seed (D-08). Changing it invalidates every pinned
#: shape/checksum in ``tests/perf_synth/test_determinism.py`` — update those
#: pins in the same commit or the drift alarm fires, as designed.
PERF_SEED = 20260801

#: Scale ladder: log ladder over three decades (D-07). The top rung may flex
#: in plan 11-05's budget calibration.
RUNGS = (1_000, 10_000, 100_000)

#: Constant average degree k (D-28): edge_count == K_AVG_DEGREE * entities at
#: every rung, so curve shape is attributable to entity count alone.
K_AVG_DEGREE = 3

#: Hubs are ~1% of entities (D-27), never fewer than one.
HUB_FRACTION = 0.01

#: Fixed epoch all observation timestamps derive from (never a clock read).
EPOCH = datetime(2026, 1, 1, tzinfo=UTC)

#: Decision records per rung for the replay ladder (D-16/D-30): one decision
#: per ten entities keeps the ladder proportional to the fixture.
DECISIONS_PER_ENTITY_DENOMINATOR = 10

_ARTIFACTS = Path(__file__).resolve().parent / "artifacts"


@lru_cache(maxsize=1)
def _ontology() -> dict[str, Any]:
    document: dict[str, Any] = yaml.safe_load(
        (_ARTIFACTS / "ontology.yaml").read_text(encoding="utf-8")
    )
    return document


class _Entity(NamedTuple):
    """One generated entity: its URI, its ref value, and its resolution rule."""

    uri: str
    ref: str
    rule: dict[str, Any]
    observations: int


class _Topology(NamedTuple):
    """The full deterministic dataset for one rung."""

    hubs: tuple[_Entity, ...]
    tails: tuple[_Entity, ...]
    edges: tuple[tuple[str, str, str], ...]  # (subject_uri, object_uri, type)
    observation_count: int


def _hub_and_tail_rules(
    ontology: dict[str, Any],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    """Split entity rules into the hub rule and the tail rules.

    Hubs are the class(es) that appear as *subjects* in the relationship
    rules (D-27: traversal expands hub-outward); everything else is tail.
    """
    subjects = {r["subject_entity_class"] for r in ontology["relationship_rules"]}
    hub_rules = [r for r in ontology["entity_rules"] if r["entity_class"] in subjects]
    tail_rules = [
        r for r in ontology["entity_rules"] if r["entity_class"] not in subjects
    ]
    if len(hub_rules) != 1 or not tail_rules:
        raise ValueError(
            "ontology artifact must declare exactly one hub (subject) class "
            f"and at least one tail class; got hubs={hub_rules!r}"
        )
    return hub_rules[0], tuple(tail_rules)


def _relationship_for(
    ontology: dict[str, Any], *, object_class: str
) -> dict[str, Any]:
    for rule in ontology["relationship_rules"]:
        if rule["object_entity_class"] == object_class:
            return dict(rule)
    raise ValueError(f"no relationship rule with object class {object_class!r}")


def _entity_uri(rule: dict[str, Any], ref: str) -> str:
    # Generator-side canonical name: class + ref. (The fabric mints its own
    # content-hashed URIs at L2; these exist for shape/checksum pinning and
    # for the decision stream's cross-references.)
    return f"{rule['entity_class']}://{ref}"


@lru_cache(maxsize=8)
def _topology(rung: int) -> _Topology:
    """Build the deterministic topology for one rung (D-27/D-28/D-29)."""
    ontology = _ontology()
    hub_rule, tail_rules = _hub_and_tail_rules(ontology)
    rng = random.Random(PERF_SEED + rung)

    hub_count = max(1, int(rung * HUB_FRACTION))
    tail_count = rung - hub_count

    # D-29: 3–10 observations per entity, hubs at the top of the range.
    hubs = tuple(
        _Entity(
            uri=_entity_uri(hub_rule, f"h{i:06d}"),
            ref=f"h{i:06d}",
            rule=hub_rule,
            observations=rng.randint(8, 10),
        )
        for i in range(hub_count)
    )
    tails = tuple(
        _Entity(
            uri=_entity_uri(tail_rules[i % len(tail_rules)], f"t{i:06d}"),
            ref=f"t{i:06d}",
            rule=tail_rules[i % len(tail_rules)],
            observations=rng.randint(3, 7),
        )
        for i in range(tail_count)
    )

    # D-27: Zipf-ish hub attachment weights 1/1, 1/2, 1/3, ...
    weights = [1.0 / (i + 1) for i in range(hub_count)]

    # Every tail attaches at least once, then extra edges fill to k * rung
    # unique (subject, object) pairs (D-28: constant average degree).
    target_edges = K_AVG_DEGREE * rung
    edge_set: set[tuple[str, str, str]] = set()
    for tail in tails:
        hub = rng.choices(hubs, weights=weights, k=1)[0]
        rel = _relationship_for(ontology, object_class=tail.rule["entity_class"])
        edge_set.add((hub.uri, tail.uri, rel["relationship_type"]))
    while len(edge_set) < target_edges:
        hub = rng.choices(hubs, weights=weights, k=1)[0]
        tail = tails[rng.randrange(tail_count)]
        rel = _relationship_for(ontology, object_class=tail.rule["entity_class"])
        edge_set.add((hub.uri, tail.uri, rel["relationship_type"]))

    observation_count = sum(e.observations for e in hubs) + sum(
        e.observations for e in tails
    )
    return _Topology(
        hubs=hubs,
        tails=tails,
        edges=tuple(sorted(edge_set)),
        observation_count=observation_count,
    )


def rung_shape(rung: int) -> tuple[int, int, int]:
    """Return ``(entity_count, edge_count, observation_count)`` for a rung."""
    topology = _topology(rung)
    return (
        len(topology.hubs) + len(topology.tails),
        len(topology.edges),
        topology.observation_count,
    )


def rung_checksum(rung: int) -> str:
    """sha256 over the SORTED entity URIs and edge triples (D-08).

    Strings only, sorted before hashing — insertion order and hash
    randomization cannot leak in (research Pitfall 4).
    """
    topology = _topology(rung)
    digest = hashlib.sha256()
    for uri in sorted(e.uri for e in topology.hubs + topology.tails):
        digest.update(uri.encode("utf-8"))
        digest.update(b"\n")
    for subject, obj, relationship in topology.edges:
        digest.update(f"{subject}|{relationship}|{obj}".encode())
        digest.update(b"\n")
    return digest.hexdigest()


def _observation_payload(
    entity: _Entity, *, rng: random.Random, ontology: dict[str, Any]
) -> dict[str, Any]:
    """One observation's raw payload, entirely from artifact vocabulary."""
    rule = entity.rule
    lexicon = ontology["attribute_values"]["label_lexicon"]
    label_key, tag_key = rule["attribute_keys"]
    return {
        rule["match_key"]: entity.ref,
        label_key: " ".join(rng.choices(lexicon, k=3)),
        tag_key: ontology["attribute_values"]["classification"],
    }


def generate_events(rung: int) -> tuple[SignalEnvelope, ...]:
    """Emit the deterministic ``SignalEnvelope`` stream for one rung.

    Ordering (deterministic): one creation observation per entity, then all
    edge envelopes (one per unique edge — the envelope carries both endpoint
    refs so L2 mints the typed edge), then the remaining observations per
    entity. Timestamps derive from :data:`EPOCH` plus seeded offsets.
    """
    ontology = _ontology()
    topology = _topology(rung)
    rng = random.Random(PERF_SEED + rung + 1)
    tenant: str = ontology["tenant_id"]
    source = SourceIdentity(system_id="perf-synth")
    by_uri = {e.uri: e for e in topology.hubs + topology.tails}

    envelopes: list[SignalEnvelope] = []
    sequence = 0

    def emit(payload: dict[str, Any]) -> None:
        nonlocal sequence
        observed = EPOCH + timedelta(
            minutes=sequence, seconds=rng.randrange(60)
        )
        envelopes.append(
            SignalEnvelope(
                tenant_id=tenant,
                envelope_id=f"env-{rung}-{sequence:08d}",
                source=source,
                ingestion_timestamp=observed + timedelta(seconds=1),
                observed_time=observed,
                raw_payload=payload,
            )
        )
        sequence += 1

    for entity in topology.hubs + topology.tails:
        emit(_observation_payload(entity, rng=rng, ontology=ontology))

    for subject_uri, object_uri, _relationship in topology.edges:
        subject, obj = by_uri[subject_uri], by_uri[object_uri]
        emit(
            {
                subject.rule["match_key"]: subject.ref,
                obj.rule["match_key"]: obj.ref,
            }
        )

    for entity in topology.hubs + topology.tails:
        for _ in range(entity.observations - 1):
            emit(_observation_payload(entity, rng=rng, ontology=ontology))

    return tuple(envelopes)


def decision_stream(rung: int) -> tuple[dict[str, Any], ...]:
    """Emit the deterministic decision-record stream for the replay ladder.

    D-30: same seed discipline as the fixtures; every record references an
    entity URI that exists in the generated topology, so replay records point
    at real fixture state. D-16 sizes the ladder proportionally to the rung.
    """
    topology = _topology(rung)
    rng = random.Random(PERF_SEED + rung + 2)
    entities = topology.hubs + topology.tails
    count = max(1, rung // DECISIONS_PER_ENTITY_DENOMINATOR)
    records: list[dict[str, Any]] = []
    for index in range(count):
        entity = entities[rng.randrange(len(entities))]
        boundary = EPOCH + timedelta(hours=1, minutes=index)
        records.append(
            {
                "decision_id": f"decision-{rung}-{index:08d}",
                "entity_uri": entity.uri,
                "temporal_boundary": boundary.isoformat(),
                "sequence": index,
            }
        )
    return tuple(records)
