# Harness adapter Protocol

The harness adapter is the seam at which CCF layers onto somebody else's agent loop. The SDK
never ships a loop and never absorbs one; an adapter binds four things — context injection,
skill exposure, effect capture and replay hooks — and nothing else crosses. Implementations
live under `runtime/ccf_runtime/adapters/<harness>/` and nowhere else; no module in the core
imports a harness.

::: ccf.harness.protocol.HarnessAdapterProtocol
