"""Control Plane — the plane that defines what the fabric may do.

Whitepaper §7.8; DESIGN.md §7. The Control Plane holds versioned
configuration (policy definitions, operator behavior rules, projection logic,
D_c thresholds, λ_c tables, materialization policy) plus the SDK-defined
artifact classes (agent/task definitions, prompt artifacts, skill catalog and
grants, workflow definitions, HITL policies, A2A trust policy — CLAUDE.md §10).
It is **also the audit plane** (INV-CH7-71): every configuration change is
versioned, timestamped, and retained against the decisions made under it.

v0 realization is an in-process versioned registry with a remote extension
point (:class:`ccf.controlplane.registry.ControlPlaneProtocol`). It holds
mechanism only — every value in it arrives from user configuration
(CLAUDE.md §11, CINV-01).

Four modules, one responsibility each:

* :mod:`ccf.controlplane.artifacts` — the typed artifact classes and the one
  supported path from a serialized artifact to a validated one.
* :mod:`ccf.controlplane.audit` — the audit-event contract and append-only log
  that make the Control Plane the audit plane (INV-CH7-71).
* :mod:`ccf.controlplane.registry` — versioned, append-only storage and
  resolution, plus the replay-only resolver that cannot reach "latest".
* :mod:`ccf.controlplane.resolution` — the read-surface Protocol and the one
  implementation of pinned ``ccf-artifact://`` reference resolution, shared
  by every consumer that follows a versioned reference (IN-01).
* :mod:`ccf.controlplane.state` — the pluggable seam for mutable-until-terminal
  state records, per D-IMPL-27's mutability split and D-IMPL-18's ruling that
  such state lives on the Control Plane's storage seam (WR-05).
"""

from __future__ import annotations

__all__ = ["artifacts", "audit", "registry", "resolution", "state"]
