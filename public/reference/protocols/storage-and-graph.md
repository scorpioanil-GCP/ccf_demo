# Storage and Context Graph Protocols

The Context Graph is reached through two deliberately asymmetric surfaces. `GraphReader` is
handed out freely; `GraphWriter` is the single-writer seam, and only the Context Assembly layer
ever holds one. The Control Plane surfaces sit beside them because graph state is only
interpretable under a pinned Control Plane resolution.

::: ccf.graph.protocols.GraphReader

::: ccf.graph.protocols.GraphWriter

::: ccf.controlplane.state.ControlPlaneStateStore

::: ccf.controlplane.registry.ControlPlaneProtocol
