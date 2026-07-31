# Phase 07 — Deferred Items

Out-of-scope discoveries logged during execution; not fixed in-wave.

- **[07-13] `SequentialAgent` deprecated at google-adk 2.5.0** — the ADK
  orchestration driver leg uses `SequentialAgent` per the plan's verified
  interface ruling; ADK deprecates it in favor of `Workflow` ("cannot yet be
  used as an LlmAgent sub-agent" at 2.5.0). Emits `DeprecationWarning` only.
  Revisit at the next google-adk pin bump; migration is mechanical (the
  driver's sub-agents are plain `BaseAgent` subclasses).
