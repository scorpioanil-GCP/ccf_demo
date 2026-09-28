"""Step 3 severings: each load-bearing line of `ccf.controlplane.temporal_boundary`.

`D-IMPL-358` step 3. **Step 3 severings, not additions to Step 2(a)'s counts** —
that campaign covered the census instrument and reached nothing here.

**A scratch COPY, never an edit-and-revert**, on the in-repo idiom
(`tests/mcp/test_egress_refusal_channels.py::_scratch_egress`): the shipped
source is read, mutated as a string, written to a fresh file under ``tmp_path``
and imported under a unique module name. The tree is never written, so
byte-for-byte restoration is automatic; and a file that did not exist a moment
ago has no stale ``.pyc``, which sidesteps structurally the trap that CPython
validates a ``.pyc`` on ``(mtime-seconds, size)`` alone.

**Every severing asserts its anchor occurs EXACTLY ONCE before substituting**, and
verifies the SHIPPED control is green first. A stale anchor silently applies no
mutation and the severing then "passes" having changed nothing — the purest form
of a control that cannot fail.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

from ccf.controlplane.registry import (
    ControlPlaneMissing,
    ControlPlaneRegistry,
    CrossTenantKeyRefused,
    content_hash,
)
from ccf.controlplane.temporal_boundary import (
    TEMPORAL_BOUNDARY_POLICY,
    PinnedTemporalBoundary,
    TemporalBoundaryPolicy,
    TemporalBoundaryUndeclared,
    resolve_temporal_boundary,
    temporal_boundary_policy_key,
)
from tests.composition import register_typed_at_composition
from tests.controlplane.test_temporal_boundary import (
    TENANT_A,
    TENANT_B,
    _FailingPlane,
    _OpaqueVersionPlane,
    declare,
)

MODULE_PATH = Path("src/ccf/controlplane/temporal_boundary.py")

#: What each severing is expected to cost. All four are ``"state"``: each property
#: rests on the single line the severing removes, with no second detector behind it.
STEP3_SEVERING_LEDGER: dict[str, str] = {
    "T1-version-discarded": "state",
    "T2-tenant-removed-from-key": "state",
    "T3-missing-means-default": "state",
    "T4-broad-exception-becomes-absence": "state",
}


def severed(
    tmp_path: Path, *, anchor: str, replacement: str, label: str
) -> types.ModuleType:
    """Import a MUTATED copy of the temporal-boundary module under a unique name."""
    repo_root = Path(__file__).resolve().parents[2]
    source = (repo_root / MODULE_PATH).read_text()
    occurrences = source.count(anchor)
    assert occurrences == 1, (
        f"{label}: anchor occurs {occurrences} times in {MODULE_PATH}, expected"
        " exactly 1 — fix the anchor, do not widen the match"
    )
    mutated = source.replace(anchor, replacement)
    assert mutated != source, f"{label}: the severing did not take"
    target = tmp_path / f"severed_{label.replace('-', '_')}.py"
    target.write_text(mutated)
    name = f"ccf_severed_{label.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(name, target)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_the_step3_ledger_is_complete_and_named() -> None:
    assert len(STEP3_SEVERING_LEDGER) == 4
    assert set(STEP3_SEVERING_LEDGER) == {
        "T1-version-discarded",
        "T2-tenant-removed-from-key",
        "T3-missing-means-default",
        "T4-broad-exception-becomes-absence",
    }


def test_a_stale_anchor_refuses_rather_than_silently_mutating_nothing(tmp_path: Path) -> None:
    """THE POSITIVE CONTROL for the driver. Without it every severing below could
    pass while changing nothing at all."""
    with pytest.raises(AssertionError, match="anchor occurs 0 times"):
        severed(
            tmp_path,
            anchor="this_text_does_not_occur_in_the_module",
            replacement="x",
            label="stale-anchor-probe",
        )


# --------------------------------------------------------------------------
# T1 — the registry's version discarded and recomputed.
# --------------------------------------------------------------------------


def test_T1_severing_version_discarded(tmp_path: Path) -> None:
    """Sever the resolver so it ignores the registry's returned version and derives
    one from the policy instead — the realistic wrong implementation, and the one
    the real registry cannot detect. The pin control must RED."""
    module = severed(
        tmp_path,
        anchor="    return PinnedTemporalBoundary(key=key, version=version, policy=artifact)",
        replacement=(
            "    from ccf.controlplane.registry import content_hash as _ch\n"
            "    return PinnedTemporalBoundary(key=key, version=_ch(artifact), policy=artifact)"
        ),
        label="T1-version-discarded",
    )
    policy = TemporalBoundaryPolicy(max_past_seconds=86_400, permitted_clock_skew_seconds=60)

    shipped = resolve_temporal_boundary(
        registry=_OpaqueVersionPlane(policy), tenant_id=TENANT_A  # type: ignore[arg-type]
    )
    assert isinstance(shipped, PinnedTemporalBoundary)
    assert shipped.version == _OpaqueVersionPlane.OPAQUE_VERSION, (
        "the shipped control is not green — nothing is proved below"
    )

    # The severed module re-defines the contract class, so its `isinstance` check
    # legitimately rejects an instance of the SHIPPED class. Hand it its own.
    severed_policy = module.TemporalBoundaryPolicy(
        max_past_seconds=86_400, permitted_clock_skew_seconds=60
    )
    broken = module.resolve_temporal_boundary(
        registry=_OpaqueVersionPlane(severed_policy), tenant_id=TENANT_A
    )
    assert broken.version != _OpaqueVersionPlane.OPAQUE_VERSION, (
        "the severing cost nothing — the property does not rest on that line"
    )
    assert broken.version == content_hash(severed_policy), "the severing did something else"
    assert broken.binding != shipped.binding, "the pin did not move, so replay would not notice"


# --------------------------------------------------------------------------
# T2 — the tenant removed from the key.
# --------------------------------------------------------------------------


def test_T2_severing_tenant_removed_from_key(tmp_path: Path) -> None:
    """Sever tenant qualification from the key. The cross-tenant isolation control
    must RED: two tenants then share one key and one policy."""
    module = severed(
        tmp_path,
        anchor='    return f"{tenant_id}/{TEMPORAL_BOUNDARY_POLICY.class_id}"',
        replacement="    return TEMPORAL_BOUNDARY_POLICY.class_id  # severed",
        label="T2-tenant-removed-from-key",
    )
    assert temporal_boundary_policy_key(tenant_id=TENANT_A) != temporal_boundary_policy_key(
        tenant_id=TENANT_B
    ), "the shipped control is not green"

    assert module.temporal_boundary_policy_key(
        tenant_id=TENANT_A
    ) == module.temporal_boundary_policy_key(tenant_id=TENANT_B), "the severing cost nothing"

    # AND a finding worth recording: this property is defended TWICE. The severed
    # key has no tenant segment, and the registry refuses to register such a key at
    # all — `CrossTenantKeyRefused`, the one tenant comparison `D-IMPL-353` §1.3
    # places on the registry. So the severing falsifies the isolation control at
    # the key level, and the degenerate key it produces could not be populated
    # even if a caller tried. The second defense is the registry's, not this
    # module's, so the key helper's own property is still the one under test.
    registry = ControlPlaneRegistry()
    with pytest.raises(CrossTenantKeyRefused):
        register_typed_at_composition(
            registry,
            module.temporal_boundary_policy_key(tenant_id=TENANT_A),
            module.TemporalBoundaryPolicy(
                max_past_seconds=3_600, permitted_clock_skew_seconds=0
            ),
            TEMPORAL_BOUNDARY_POLICY,
        )


# --------------------------------------------------------------------------
# T3 — a missing policy answered with an invented one.
# --------------------------------------------------------------------------


def test_T3_severing_missing_means_default(tmp_path: Path) -> None:
    """Inject a fabricated default when the registry reports absence. The
    missing-policy / no-default control must RED — and note what the severing
    produces: a pin with a version nobody issued, which is exactly what
    `D-IMPL-358` ruling 11 forbids."""
    module = severed(
        tmp_path,
        anchor="        return TemporalBoundaryUndeclared(",
        replacement=(
            "        return PinnedTemporalBoundary(  # severed\n"
            "            key=key,\n"
            '            version="sdk-default",\n'
            "            policy=TemporalBoundaryPolicy(\n"
            "                max_past_seconds=86_400, permitted_clock_skew_seconds=60\n"
            "            ),\n"
            "        )\n"
            "        _unreachable = TemporalBoundaryUndeclared("
        ),
        label="T3-missing-means-default",
    )
    registry = ControlPlaneRegistry()
    shipped = resolve_temporal_boundary(registry=registry, tenant_id=TENANT_A)
    assert isinstance(shipped, TemporalBoundaryUndeclared), "the shipped control is not green"

    invented = module.resolve_temporal_boundary(registry=ControlPlaneRegistry(), tenant_id=TENANT_A)
    assert isinstance(invented, module.PinnedTemporalBoundary), (
        "the severing cost nothing — absence is still absence"
    )
    assert invented.policy.max_past_seconds == 86_400, "the severing invented no window"
    assert invented.version == "sdk-default", (
        "the severed path fabricated a version for a policy that does not exist"
    )


# --------------------------------------------------------------------------
# T4 — the narrow catch widened, so an outage reads as absence.
# --------------------------------------------------------------------------


def test_T4_severing_broad_exception_becomes_absence(tmp_path: Path) -> None:
    """Widen the missing-policy catch. Every registry failure then reads as an
    undeclared bound — the boundary silently disabled on the day the control plane
    was unwell. The outage-vs-absence control must RED."""
    module = severed(
        tmp_path,
        anchor="    except ControlPlaneMissing:",
        replacement="    except Exception:  # severed",
        label="T4-broad-exception-becomes-absence",
    )
    outage = RuntimeError("the control plane is unreachable")

    with pytest.raises(RuntimeError):
        resolve_temporal_boundary(registry=_FailingPlane(outage), tenant_id=TENANT_A)  # type: ignore[arg-type]

    swallowed = module.resolve_temporal_boundary(
        registry=_FailingPlane(outage), tenant_id=TENANT_A
    )
    assert isinstance(swallowed, module.TemporalBoundaryUndeclared), (
        "the severing cost nothing — the outage still propagates"
    )
    assert swallowed.reason == "temporal-boundary-undeclared", (
        "an outage was reported as an undeclared boundary"
    )


def test_control_plane_missing_still_means_absence_under_no_severing() -> None:
    """A guard against T4's severing being indistinguishable from correct behavior:
    absence must work through the NARROW catch, not only through a broad one."""
    undeclared = resolve_temporal_boundary(
        registry=_FailingPlane(ControlPlaneMissing("nothing there")),  # type: ignore[arg-type]
        tenant_id=TENANT_A,
    )
    assert isinstance(undeclared, TemporalBoundaryUndeclared)
