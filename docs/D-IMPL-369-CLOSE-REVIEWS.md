# D-IMPL-369 — the BATCH-CLOSE panel on batch 2 (after integration)

**Subject:** `integration-remaining-rows` @ `9b71843b`, the diff from `e41d5737` (end of the pilot): the SEC-014
delta (`row-sec-014` @ `5383c91e`), SEC-021 (`row-sec-021` @ `56b49756`), SEC-015 + SEC-028
(`row-sec-015-028` @ `1deadc6b`). Code, workflows, tests, `pyproject.toml`, `Makefile`, `README.md` and the
head of `requirements.lock` inlined (159,200 bytes) with the three executor reports. **Reviewers:** Codex,
Cursor, Fable (independent agent, tree access, executed probes). **Executor:** Opus, excluded. **Date:**
2026-10-05. **Verifier:** the orchestrator re-measured every claim that carries a disposition.

## Seat reliability

| Seat | Read the tree? | Output |
| --- | --- | --- |
| Codex | diff only (sandbox) | no blocking; 1 advisory, **confirmed by probe** |
| Cursor | yes, symbols resolved | no blocking; 10 advisories; one executor-report understatement, **confirmed** |
| Fable | yes; executed probes (lock hashes against PyPI, pins against `ls-remote`, 32/32 declared requirements satisfied, 4 extra suites run: 1157 passed) | no blocking; 6 advisories, F-1/F-2 **confirmed by probe** |

## Findings, verification, disposition

| # | Seat(s) | Row | Finding | Verified how | Disposition |
| --- | --- | --- | --- | --- | --- |
| B1 | Fable F-1, Cursor | SEC-028 | `tools/lints/dependency_lock.py` reports **nothing** for `pip -q install -e ".[dev]"`, `pip3.12 install -e .`, `uv sync`; the editable operand is unconstrained (`-e git+https://…` passes with the two flags) | **PROBED** by the orchestrator: `check_workflow` → 0 findings on a four-step bypass fixture | **CONFIRMED.** The shipped workflows are correct; the guard is bypassable by the idiomatic shapes it exists to refuse — the pilot treated this class (the Makefile lint's directive skip) as BLOCKING, and consistency holds: **SEC-028 reopened for its one corrective round** |
| B2 | Codex | SEC-015 | `tools/lints/ci_posture.py` accepts a job-level `permissions: read-all` string, which widens to every readable token scope | **PROBED**: 0 findings on a job-level `read-all` fixture | **CONFIRMED.** Same class; **SEC-015 reopened for its one corrective round** |
| B3 | Cursor | SEC-021 | `runtime/ccf_runtime/peering/typed_http.py::TypedHttpWire.emit` raises `PeerUnreachable` with the status only, so an SDK sender never sees the `ReceiveQueueFull` name the 503 body carries; the executor's "name in the response body" understated this | INSPECTED (`raise PeerUnreachable(… f" {response.status_code}"`) | **ADVISORY, CARRIED** as **SEC-021-C-01**: include the body or a typed mapping on 503 |
| B4 | Cursor | SEC-021 | The exploit test reads the private `wire._received`; a decoy could keep it green | Fable executed the opposite probe: the private read fails loudly, `_declared_cap` reddens on the length assertion | **ADVISORY, CARRIED** as **SEC-021-C-02**: drive assertions through `receive()` and the wire |
| B5 | Cursor | SEC-021 | Queue count is bounded but concurrent in-flight handlers can each buffer `max_request_bytes` before `_enqueue` | INSPECTED | **CARRIED** as a new row candidate (process-wide in-flight byte bound) |
| B6 | Fable F-5/F-6 | SEC-021 | LF-leg full queue renders as a JSON-RPC `InternalError` with 2–3 ERROR tracebacks per carriage; the typed 503 reflects the peer-id header | Fable executed | **ADVISORY, CARRIED** as **SEC-021-C-03** |
| B7 | Cursor | SEC-014 | `_make_private_dirs` still `continue`s on an intermediate `FileExistsError` without the refuse check (pilot C-02); symlinked root still followed (pilot C-04); the `_umask` helper still detects only a leaked umask (pilot C-01) | INSPECTED; unchanged from the pilot's carried set | **CARRIED** (already named) |
| B8 | Fable F-3 | SEC-014 | `InsecureArtifactStoreRoot` cannot be pickled or copied (its `__init__` signature) | Fable executed | **ADVISORY, CARRIED** as **SEC-014-C-06** |
| B9 | Fable F-4 | SEC-015 class | Service images `postgres:16`, `neo4j:5-community`, `mongo:7`, fluree in `ci.yml` are mutable tags the lint never reads | INSPECTED | **CARRIED** as a new row candidate (image digests) |
| B10 | Cursor | SEC-015 | The lint accepts any 40-hex + `# vN`; it does not check the SHA equals the tag | INSPECTED; the orchestrator and Fable each verified all three pins equal `ls-remote` of the tags **this once** | **ADVISORY, CARRIED** as **SEC-015-C-01**: Dependabot keeps them moving by PR; a periodic `ls-remote` check is a deployment control |
| B11 | Cursor | SEC-028 | `README.md` still leads with the unlocked `pip install -e ".[dev]"` | INSPECTED | **ADVISORY, CARRIED** as **SEC-028-C-01** |
| B12 | all | all | Hosted-runner behavior: Fable executed the checks that can be executed off-runner (140 lock entries' hashes are real, un-yanked PyPI files; every package has a cp312/abi3 x86_64 wheel so no sdist build; no job needs a write grant; node20 on all three actions) | Fable executed | **No finding.** The workflows have still not been run on GitHub; that is the first thing a `main` merge would show |
| B13 | all | all | Executor reports vs tree | — | No contradiction except B3's understatement |

## Rejected

None.

## Behavior changes the integration carries (for Dave)

- An insecure pre-existing artifact-store root is refused by name without `chmod` (ruled, `D-IMPL-369`).
- Both peering transports require `max_pending` at construction (no default); the frozen archive example 04
  pair now fails with `TypeError` (frozen by `D-IMPL-351`; the perf crossproc suite that spawns it was already
  erroring at setup on the base).
- Every CI and Makefile install now runs from the hash-pinned lock; `pip-tools` is a `dev` extra.

## Reopen — SEC-015 and SEC-028 corrective rounds

Dispatched to the SEC-015/028 executor as each row's one corrective round with the two probe fixtures, the
required grammar, fixtures and severings. Result: `row-sec-015-028` @ `0ac58e62`; only the two lints and
their tests changed. `dependency_lock` now recognizes `pip`, `pip3`, `pip3.N`, `python -m pip`, `uv pip`
with global options before `install`, refuses `uv sync`/`run`/`add`/`tool`, `uvx`, poetry, pdm, pipenv,
pipx, conda, mamba, `easy_install`, `pip-sync` and `setup.py install`/`develop` by name, and requires an
in-repo editable operand; `ci_posture` refuses every non-mapping job-level `permissions:` value and lists
job write grants by name. The executor measured 37 of 121 new-fixture cases red against the previous lints.
**Re-verified by the orchestrator:** the five-step bypass fixture draws **4** findings and the ruled shape
none; a job-level `read-all` draws **1**; `python -m tools.lints --all` rc=0 on the real tree;
`tools/lints/tests` **777 passed, 0 failed, 0 errors** (723 before); re-allowing `read-all` by hand →
**1 failed, 38 passed in 0.17s**, restore sha-matched. Re-integrated `--no-ff` at **`77a1ae47`**. B1 and B2 CLOSED. Still carried as
**SEC-028-C-02**: the installer list is a fixed set (hatch, rye, pixi, `py -m pip` would pass) and installs
hidden inside `$(…)`, backticks or `bash -c` are not seen. Both rows have now used both rounds.
