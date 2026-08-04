# public/ — the published-surface charter

This directory is the **entire** published documentation surface of the CCF
SDK. Publication is default-deny by existence (D-01): a page is published
because someone deliberately placed it here, never because a build glob
reached it. The site is built by `mkdocs build` into `site/` and uploaded as
a workflow artifact — **nothing is hosted** (D-IMPL-71). The repository is
private, and the artifact inherits repository access.

## The never-publish rule

The internal deliverable tree adjacent to this one holds the canonical
specification `CCF_Whitepaper_1-2.md` together with `DECISIONS.md`,
`SPEC_INVENTORY.md`, `DESIGN.md`, `FEASIBILITY.md`, `ROADMAP.md`, the
`PHASE_I*_GATE.md` records and `09-ruling-batch-minicycle.md`. **Nothing
under `public/` may reference any of them.** No link. No `--8<--` snippet
include. No symlink. No transitive path that resolves into that tree.

The rule is proved, not asserted, and one command reproduces the whole proof
locally:

```console
$ make docs-strict
```

That target runs three checks, in this order, and blocks on any of them:

1. **The pre-build structural scan** over `public/` — symlinks and includes
   that escape the published tree are reported before the build has a chance
   to copy them.
2. **The strict build** — `mkdocs build --strict`, where a broken link, a
   missing anchor, a page outside the nav, or an unresolved snippet is an
   error rather than a warning.
3. **The post-build content scan** over `site/` — the exact tree that
   uploads, checked against the never-publish rule with **no allowlist**
   (D-20). A page that names a proprietary passage fails the build; there is
   no mechanism for excusing one.

The CI `docs` job runs that identical command on every push and pull request
and uploads the result as the `ccf-docs-site` artifact. It is deliberately
not made non-blocking: a gate that can be waved through is not a gate.

## Mermaid diagrams need a browser

Diagrams on these pages render via a browser-side script loaded from a CDN.
A downloaded artifact opened from local disk without network access shows
blank diagram blocks — the source is present, the renderer is not. This is
expected, not a build defect.

## About `D-IMPL-NN` identifiers

Identifiers of the form `D-NN` and `D-IMPL-NN` on these pages refer to the
SDK's internal decision log, which is not published (D-22). They are cited
so that a claim is traceable inside the project; a reader outside it should
treat them as opaque provenance markers.
