# Artifact store

Every CCF artifact — agent definitions, prompt artifacts, policy bundles, replay records —
persists through one immutable, content-addressed surface. The store is a substrate reached
*through* mechanism, never a second writer to the graph. Two reference implementations ship: a
file-backed one for development and an MCP-backed one for deployments that want to bring their
own persistence.

::: ccf.artifacts.protocol.ArtifactStoreProtocol

::: ccf.artifacts.file_store.FileArtifactStore

::: ccf.artifacts.mcp_store
