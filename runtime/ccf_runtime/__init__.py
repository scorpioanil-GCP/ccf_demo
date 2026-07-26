"""CCF runtime host package — SDK-defined (CLAUDE.md §14, D-IMPL-04).

SDK packaging root. Contains no logic: ingestion adapters (async), harness
adapters under `adapters/<harness>/` (CLAUDE.md §7.3), the MCP and A2A
surfaces (§7.1, §7.2), and the Experience Layer surfaces (§8.3) land in their
own plans.

Unlike `ccf`, this package is the only place harness-specific code may live.
"""

__all__: list[str] = []
