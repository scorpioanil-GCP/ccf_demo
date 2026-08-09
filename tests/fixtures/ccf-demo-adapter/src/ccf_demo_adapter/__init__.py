"""An out-of-tree CCF graph adapter — the proof, not a substrate to use.

This package is a test fixture that ships as its own installable distribution.
It exists so that the backend registration seam's central claim can fail: a
third party adds a graph adapter by installing a package and naming it in a
manifest, and no line changes inside the CCF SDK.

Two modules, and the split is the same one every in-tree adapter observes:

* :mod:`ccf_demo_adapter.store` holds the state and the read seam. Anyone may
  import it.
* :mod:`ccf_demo_adapter.demo_write` holds the transaction, the writer, and the
  ``REGISTRATION`` record the entry point names. It imports the read module;
  the reverse would put write code on every reader's import path.

**This module body is deliberately empty of imports.** Importing either
submodule here would make ``import ccf_demo_adapter`` drag the write path in,
and the discovery test asserts that listing installed adapters imports nothing
at all — a package whose ``__init__`` reached for its own submodules would
still satisfy that test, but it would make the property accidental. Nothing is
re-exported for the same reason: the entry point names a module and an
attribute, so a convenience alias here would serve no caller.

See ``README.md`` beside this package for what the distribution is for, how it
installs, and why it is always installed rather than opt-in.
"""

from __future__ import annotations

__all__: list[str] = []
