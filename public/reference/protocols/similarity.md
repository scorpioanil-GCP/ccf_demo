# Similarity index Protocol

The similarity substrate is split into a read surface and a mutation surface, so a deployment
can hand a query-only index to the operator layer without also handing it the ability to write
vectors. Embedding is a separate seam again: which model produces the vectors is a deployment
choice the SDK never makes for you.

::: ccf.similarity.protocol.SimilarityIndexProtocol

::: ccf.similarity.protocol.MutableSimilarityIndexProtocol

::: ccf.similarity.embedder.EmbedderProtocol
