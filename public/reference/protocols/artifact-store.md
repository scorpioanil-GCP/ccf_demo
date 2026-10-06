# Artifact store

Every CCF artifact — agent definitions, prompt artifacts, policy bundles, replay records —
persists through one immutable, content-addressed surface. The store is a substrate reached
*through* mechanism, never a second writer to the graph. Two reference implementations ship: a
file-backed one for development and an MCP-backed one for deployments that want to bring their
own persistence.

The file-backed store keeps everything it writes owner-only: every file it creates is `0o600`
and every directory it creates is `0o700`, whatever the process umask, and a root that already
existed is tightened to `0o700` when the store is constructed. These modes are fixed, not
configurable (`SEC-014`; `src/ccf/artifacts/file_store.py::FileArtifactStore`).

::: ccf.artifacts.protocol.ArtifactStoreProtocol

::: ccf.artifacts.file_store.FileArtifactStore

::: ccf.artifacts.mcp_store
