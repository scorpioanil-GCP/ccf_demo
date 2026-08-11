# Deferred items — phase 15.5

Out-of-scope discoveries logged during execution. Nothing here was fixed in the
plan that found it.

## `make example-s1-01` does not exist

- **Found during:** plan `15.5-04`, task 1 (reading the example's docstrings).
- **What:** `examples/s1-01-hello-context-product/run.py` tells the reader to
  run the example with `make example-s1-01`, and plan `15.5-13`'s checkpoint
  task 4 uses `make example-s1-01` as its automated verification. No such target
  exists in the `Makefile` — `grep -n "s1" Makefile` returns nothing. The
  aggregate `examples` target (`example-00` … `example-08`, `example-ext-00`)
  does not include `s1-01` either, so the example runs in no CI job.
- **Why deferred:** adding the target and wiring it into `examples` changes what
  `make ci` runs, which is outside plan `15.5-04`'s three-file scope (an example
  added to the always-on aggregate is a CI-surface change, not a deletion).
- **Owner:** plan `15.5-13` rewrites this example and needs the target for its
  own verification step; it is the natural place to add it. If `15.5-13` is
  descoped, this becomes a phase-close finding.
