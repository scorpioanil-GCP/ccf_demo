"""Authorization primitives that ``src/`` handles require (D-IMPL-353).

The capability, the action vocabulary and the decision contract live here so
that library handles can demand proof of authorization without importing the
runtime (D-29). The gate and the MCP wrapper that MINT capabilities stay in
``runtime/``; minting needs a door, requiring does not.
"""
