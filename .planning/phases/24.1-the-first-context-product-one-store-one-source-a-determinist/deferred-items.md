## From plan 24.1-03 (Wave 3) — out of scope, NOT fixed

- **`examples/s1-00-companies-over-revenue/backends.yaml` line 1 declares
  `$schema=../../../../docs/schemas/ccf.declared-artifact.json` — one level too
  deep.** The file sits at depth 2 under the repo root, so the correct prefix is
  `../../`. Measured: the declared path does **not** resolve; the same header at
  the correct depth does. Every `s1-01/artifacts/*.yaml` header is correct, so
  this is one file, not a convention.
  **Pre-existing at `phase-24.1-base` and unrelated to this plan's changes** —
  logged rather than fixed, per the scope boundary. It costs editor schema
  completion in that one file and nothing at runtime; no lint checks it.
