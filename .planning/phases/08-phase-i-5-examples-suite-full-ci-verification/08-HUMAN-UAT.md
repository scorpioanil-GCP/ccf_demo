---
status: complete
phase: 08-phase-i-5-examples-suite-full-ci-verification
source: [08-VERIFICATION.md]
started: 2026-07-31T14:44:03Z
updated: 2026-07-31T14:44:03Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. First remote GitHub Actions run is green
expected: The push of main/v0.1.0 (commits 33c72e0/47d6daa) triggered ci.yml on GitHub; the always-on jobs including the examples job (make examples, CCF_REQUIRE_HARNESSES=1) conclude success. Check https://github.com/drcastillo/ccf_code/actions
result: passed — approved by Dave 2026-07-31 after Actions-check request

### 2. (Optional) live-legs.yml Ollama dispatch executes
expected: Manually dispatching the examples-live-ollama job (workflow_dispatch, default model qwen3:0.6b) completes green, confirming the opt-in live leg runs on a hosted runner.
result: skipped — opt-in leg, dispatch at any time

## Summary

total: 2
passed: 1
issues: 0
pending: 0
skipped: 1
blocked: 0

## Gaps
