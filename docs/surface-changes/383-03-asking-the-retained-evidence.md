# 383-03 (D-IMPL-383, 2026-10-16) — asking the retained evidence: `decisions`, `why`, `replay`

`D-IMPL-383`. Dave, 2026-10-16, on the four bank questions — *"Why was this request refused?" "Which
policies and data supported this answer?" "Show decisions involving this company last Tuesday." "Replay
this decision and verify that it reproduces."* — *"Yes — build the three commands."* Each command reads
only an opened product's evidence index and store; none asks a new question or needs a running door, and
nothing here reads an environment variable.

## ccf.replay.inspection.explain_decision

- Surface: ccf.replay.inspection.explain_decision
- Public surface: true
- Change type: added
- Before: a decision's reasons were reachable only as raw record JSON (`OpenedProduct.record_of`), and only for an outcome object the caller still held.
- After: `explain_decision(*, store, evidence, record_address)` reads the record at its exact address and returns a `DecisionExplanation`: served or refused; the refusal's kind, reason code and the `detail` sentence the refusal envelope wrote when it refused; every policy binding in force at its pinned version; every resolved request input with its authority (caller or default) and source version; and, when a graph was read, its snapshot id, as-of instant, entity and relationship counts, operator plan and Context Debt. Every value is copied from the record. It needs no retained graph. Raises `ReplayEvidenceUnavailable` for an address the index does not hold, or whose record the store no longer holds.
- Why: `D-IMPL-383`, Dave 2026-10-16. Red tests: `tests/replay/test_replay_inspection_383.py` (all 11 fail on `3dbd7ef8`: `No module named 'ccf.replay.inspection'`).
- Migration: none.

## ccf.replay.inspection.DecisionExplanation

- Surface: ccf.replay.inspection.DecisionExplanation
- Public surface: true
- Change type: added
- Before: no such contract.
- After: the explanation above. An operator/auditor handle, as `record_of` is: the refusal detail is the internal one, which a caller at a minimal disclosure level was not shown.
- Why: `D-IMPL-383`.
- Migration: none.

## ccf.replay.inspection.ParameterOrigin

- Surface: ccf.replay.inspection.ParameterOrigin
- Public surface: true
- Change type: added
- Before: no such contract; a resolved input's authority and source were reachable only by parsing dimension 2's `request_resolution` string.
- After: one resolved request input: name, value, authority (`caller` or where the value came from), source and source version.
- Why: `D-IMPL-383` ("which policies and data supported this answer").
- Migration: none.

## ccf.replay.inspection.PolicyVersion

- Surface: ccf.replay.inspection.PolicyVersion
- Public surface: true
- Change type: added
- Before: no such contract.
- After: one Control Plane binding in force, by key and pinned version.
- Why: `D-IMPL-383`.
- Migration: none.

## ccf_runtime.cli.evidence.register

- Surface: ccf_runtime.cli.evidence.register
- Public surface: true
- Change type: added
- Before: no command answered from retained evidence; the `ccf` CLI's `replay` noun queries a running HTTP server.
- After: `register(subparsers)` adds `decisions [--involving ID] [--since WHEN] [--until WHEN] [--json]`, `why <decision> [--json]` and `replay <decision>` to a launcher's commands. A decision may be named by a unique prefix of at least 8 characters; a bare date covers the whole local day; times print in UTC and local time. cp-06C's launcher (`server/serve.py`) is the first to offer them.
- Why: `D-IMPL-383`, Dave 2026-10-16. Red tests: `tests/examples/test_cp_06_canonical_evidence_dir.py` (4 of 15 fail on `3dbd7ef8`).
- Migration: none.

## ccf_runtime.cli.evidence.run

- Surface: ccf_runtime.cli.evidence.run
- Public surface: true
- Change type: added
- Before: no such function.
- After: `run(args, opened, *, out)` answers one verb against an opened product's evidence index and store and returns its exit status: `0` answered, `2` malformed, `3` evidence unavailable, `4` did not reproduce.
- Why: `D-IMPL-383`, Dave 2026-10-16. Red tests: `tests/examples/test_cp_06_canonical_evidence_dir.py` (4 of 15 fail on `3dbd7ef8`).
- Migration: none.

## ccf_runtime.cli.evidence.VERBS

- Surface: ccf_runtime.cli.evidence.VERBS
- Public surface: true
- Change type: added
- Before: no such name.
- After: the tuple of verbs `register` adds: `decisions`, `why`, `replay`.
- Why: `D-IMPL-383`, Dave 2026-10-16. Red tests: `tests/examples/test_cp_06_canonical_evidence_dir.py` (4 of 15 fail on `3dbd7ef8`).
- Migration: none.
