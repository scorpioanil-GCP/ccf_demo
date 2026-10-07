"""LOW-03 exploit test — an intermediate computed for one tenant is never served to another.

The row (``docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md``,
"LOW-03" and its MEASURED block, D-IMPL-372) found
``src/ccf/operators/planner.py::IntermediateCache._key`` building a 4-tuple
with no tenant. Its premise is only literally true: ``GraphView.tenant_id`` is
a hashed field, so two tenants' VIEWS already key differently and the sketched
two-views test is green before any fix (vacuous). The red case is ONE view
object passed to ``run()`` under two different ``tenant_id`` arguments: the
``tenant_id`` argument is an input ``Operator.apply`` observes that the key did
not, so the second call hit and was served the first tenant's intermediate.

``docs/DECISIONS.md`` D-IMPL-36 rules the key as ``(tenant, operator_key,
parameter_set_version, input_intermediate_keys, graph_snapshot_id)`` — tenant
FIRST. The repair restores the ruled first component; no key-shape test existed
to update, so one is added here.

The deferred path (``_Deferred``) is exercised by construction: the first call
for an operator is always held un-keyed, so a second-call miss proves the
deferred key carries the tenant too.
"""

from __future__ import annotations

from ccf.contracts.canonical import content_hash
from ccf.graph.protocols import GraphView
from ccf.operators.planner import IntermediateCache

from .test_planner import BOUNDARY, TENANT, InertOperator

OTHER = "tenant-other-under-test"


def _op() -> InertOperator:
    return InertOperator(key="a.policy", category="policy", label="a.policy")


def _view() -> GraphView:
    return GraphView(tenant_id=TENANT, as_of=BOUNDARY)


def test_one_view_under_two_tenant_arguments_is_two_entries() -> None:
    cache = IntermediateCache()
    op, view = _op(), _view()
    first = cache.run(op, view=view, tenant_id=TENANT, temporal_boundary=BOUNDARY, upstream=())
    second = cache.run(op, view=view, tenant_id=OTHER, temporal_boundary=BOUNDARY, upstream=())
    assert cache.hits == 0, "tenant B was served tenant A's intermediate"
    assert second is not first


def test_after_materialization_a_second_tenant_still_misses() -> None:
    """Three calls: A, A (materializes A's key and hits), then B — B must miss."""
    cache = IntermediateCache()
    op, view = _op(), _view()
    a1 = cache.run(op, view=view, tenant_id=TENANT, temporal_boundary=BOUNDARY, upstream=())
    a2 = cache.run(op, view=view, tenant_id=TENANT, temporal_boundary=BOUNDARY, upstream=())
    assert cache.hits == 1 and a2 is a1  # same tenant still hits: the cache still works
    b = cache.run(op, view=view, tenant_id=OTHER, temporal_boundary=BOUNDARY, upstream=())
    assert cache.hits == 1, "tenant B was served tenant A's intermediate"
    assert b is not a1


def test_the_key_is_d_impl_36s_five_tuple_tenant_first() -> None:
    op, view = _op(), _view()
    key = IntermediateCache._key(tenant_id=TENANT, operator=op, view=view, upstream=())
    assert key == (
        TENANT,
        op.key,
        content_hash(op.parameters),
        content_hash(view),
        content_hash(()),
    )
    other = IntermediateCache._key(tenant_id=OTHER, operator=op, view=view, upstream=())
    assert other != key and other[1:] == key[1:]
