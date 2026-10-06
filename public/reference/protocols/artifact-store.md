# Artifact store

Every CCF artifact — agent definitions, prompt artifacts, policy bundles, replay records —
persists through one immutable, content-addressed surface. The store is a substrate reached
*through* mechanism, never a second writer to the graph. Two reference implementations ship: a
file-backed one for development and an MCP-backed one for deployments that want to bring their
own persistence.

The file-backed store keeps everything it writes owner-only: every file it creates is `0o600`
and every directory it creates is `0o700`, whatever the process umask. It never changes the
permissions of a directory it did not create: a root that already existed must be `0o700` (or
narrower) and owned by the process, or construction raises
`src/ccf/artifacts/file_store.py::InsecureArtifactStoreRoot`, naming the path and the mode it
found, and leaves the root exactly as it was. These modes are fixed, not configurable
(`SEC-014`, `D-IMPL-369`; `src/ccf/artifacts/file_store.py::FileArtifactStore`).

::: ccf.artifacts.protocol.ArtifactStoreProtocol

::: ccf.artifacts.file_store.FileArtifactStore

::: ccf.artifacts.mcp_store
