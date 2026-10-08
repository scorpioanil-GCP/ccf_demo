# packaging/

## `pypi-placeholder/` — the PyPI name reservation for `ccf-sdk`

`SEC-027` (`D-IMPL-376` ruling 4). The SDK's distribution name is `ccf-sdk`,
and the SDK itself is published to no index. This directory is the EMPTY
distribution Dave uploads to public PyPI from his own account, so that nobody
else can publish under the SDK's distribution name: without it, anyone could
register `ccf-sdk` there and become what `pip install ccf-sdk` installs.

It is not the SDK and must never become it. Everything in `pypi-placeholder/`
is published verbatim, because the source distribution carries
`pyproject.toml` and `README.md`, so nothing internal belongs there. That is
why this note sits one level up.

- **No code, by construction.** `packages = []` and `py-modules = []` switch off
  setuptools' automatic discovery. The built wheel holds only its four
  `.dist-info` files, with an empty `top_level.txt`, no `Requires-Dist` and no
  entry points.
- **`requires-python = "<3"`: no Python 3 installer can ever select it.** pip
  skips every candidate whose `Requires-Python` excludes the running
  interpreter. Without the fence, an installer resolving a `ccf-sdk`
  requirement that the installed SDK cannot satisfy at that moment backtracks
  to the empty 0.0.0, which has no dependencies and so always resolves, and
  replaces the SDK with it. The SEC-027 re-review measured exactly that with
  `pip install "ccf-sdk[mongo]"` against an index holding only the
  placeholder (exit 0, `ccf/__init__.py` gone).
- **Version `0.0.0`.** An index that serves both this placeholder and a real
  build of the SDK resolves to the real one, because every real version is
  higher.
- **Never add the `Private :: Do Not Upload` classifier here:** PyPI refuses any
  upload that carries it.
- **Nothing in this repository builds or uploads it.** No `make` target, test
  or workflow builds this directory, although whole-tree scans such as the
  lints and the retirement sweep read its files like any others. The upload is
  Dave's action.
- **Building it reproducibly.** Use the build toolchain from
  `requirements.lock` (`build`, `setuptools`, `pyproject-hooks` and
  `packaging`, installed with `--require-hashes`) in an environment that does
  NOT also hold `setuptools-scm`, because its file finder changes what a source
  distribution includes. Build with `--no-isolation` and a fixed
  `SOURCE_DATE_EPOCH`, and the wheel is byte-identical from build to build. The
  source distribution is not, because its gzip header records the build time.
