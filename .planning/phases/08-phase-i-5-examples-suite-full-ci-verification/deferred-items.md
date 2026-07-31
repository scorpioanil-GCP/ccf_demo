
## 2026-07-31 (08-13, post-push observation)
- GitHub warned on push: a historical blob of `.planning/ROADMAP.md` at commit
  `c3555b0` ("fix(06): revise plans per checker findings") is 55 MB (57,710,096
  bytes); the current file is 6 KB. The blob is an ancestor of `main`, so
  removing it requires history rewrite + force-push, which CLAUDE.md §2.2
  forbids on `main`. Under GitHub's 100 MB hard limit; warning only. Deferred
  for Dave: accept as-is, or schedule a coordinated history rewrite post-v0.
