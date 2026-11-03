# Reference Manual Maintenance

The manual is tied to a **qualified SDK commit**, not to “whatever main looks like today.”

## Refresh trigger

Refresh when the SDK team identifies a new qualified/merged baseline appropriate for adopters.

Do not refresh from:

- in-flight feature branch;
- partially built example;
- branch under active gate repair;
- unqualified surface diff.

## Refresh procedure

### 1. Pin baseline

Record repository, branch, commit and qualification evidence in `QUALIFIED_BASELINE.yaml`.

### 2. Diff public surface

Compare:

`docs/surface/v0.2-surface.json`

old qualified baseline vs new qualified baseline.

Classify each change:

- additive public name;
- signature/shape change;
- removal;
- relocation;
- new package/module;
- runtime-only;
- internal/non-surface.

### 3. Diff example catalog

Identify:

- new canonical successor;
- frozen historical tree;
- new product rung;
- new client/integration example;
- example that no longer represents preferred implementation.

### 4. Update focused reference pages

Update task-oriented reference prose before regenerating the public-surface index.

### 5. Regenerate public-surface index

The index is mechanical evidence, not the explanatory layer.

### 6. Review developer workflows

Ask:

- does `open_product` shape change?
- do config/environment documents change?
- does the recommended canonical codegen example change?
- does the Standard/spec recipe change?
- are there new retired manual patterns?

### 7. Replay hold

While Replay work is in flight, do not “helpfully” document a branch ahead of qualification.

When its replacement environment/refusal surface qualifies:

- lift the boundary intentionally;
- add a dedicated Replay page/workflow;
- audit older guidance for retired hand-assembly.

### 8. Validate links/imports/examples

Before promotion:

- relative link scan;
- import path verification;
- example path existence;
- no normal navigation to historical specimens;
- current qualified baseline visible on technical pages.

## Principle

**Reference stability comes from qualification + version pinning, not from prose sounding authoritative.**
