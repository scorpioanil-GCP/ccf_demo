# 377-03 — SEC-027: the distribution is `ccf-sdk`; the import name stays `ccf`

`D-IMPL-376` ruling 4, built red-first. The row as worded in the 2026-09-23
security review: the distribution name `ccf` is owned on PyPI by Microsoft's
Confidential Consortium Framework, so `pip install ccf` installs Microsoft's
package, a dependency-confusion path. The ruled remedy renames the
DISTRIBUTION to `ccf-sdk` in the package metadata, in the code that reads the
installed version, in the version gate and in the install documentation. The
IMPORT name `ccf` does not change, and its collision with Microsoft's package
in one environment is disclosed (`README.md`, "The distribution is `ccf-sdk`";
the security page, §3.1). The red tests are
`tests/test_distribution_name.py`.

**What a reader of the SDK's own metadata reads.** Before the rename, the
built-in adapter's replay pin looked the SDK up by `ccf`, so in an environment
that also held Microsoft's `ccf` it recorded Microsoft's version as
`graph_adapter_version`, and the release version gate certified that version
as the SDK's. Both now name `ccf-sdk`, and a test holds them to
`[project] name`.

## ccf.graph.registry.SDK_DISTRIBUTION

- Surface: ccf.graph.registry.SDK_DISTRIBUTION
- Public surface: false
- Change type: behavior
- Before: `"ccf"`. `ccf.graph.registry.resolve` read every built-in adapter's version through it (`importlib.metadata.version("ccf")`), and that version reached `ccf.graph.registry.AdapterPin.version` and replay dimension 2's `graph_adapter_version`. A distribution named `ccf` on the path, Microsoft's or this SDK's former install, answered that lookup.
- After: `"ccf-sdk"`. A built-in adapter resolves with `distribution == "ccf-sdk"` and the `ccf-sdk` distribution's version. In an environment where `ccf-sdk` is not installed (a source checkout, or one still holding only the former `ccf` install), the version is the documented `unknown` marker instead of another distribution's version. The constant is not exported (`__all__`) and is absent from the generated manifest, hence `Public surface: false`.
- Why: SEC-027 (`D-IMPL-376` ruling 4). Red test: `tests/test_distribution_name.py::test_the_builtin_adapter_pin_reads_ccf_sdk_and_never_a_distribution_named_ccf`, which on the former code resolved `("ccf", "7.0.18")` with a foreign `ccf` 7.0.18 on the path.
- Migration: none for code that only imports `ccf`. A consumer that looked the SDK's version up by name reads `importlib.metadata.version("ccf-sdk")`.

## The distribution name `ccf` becomes `ccf-sdk`

- Surface: the distribution name in `pyproject.toml` (`[project] name`), its five self-referencing extras, and `tools/check_version_stamp.py::DISTRIBUTION`
- Public surface: false
- Change type: behavior
- Before: the SDK built and installed as the distribution `ccf` (`ccf-<version>.dist-info`), its aggregate extras were spelled `ccf[...]`, the lock was compiled with `--unsafe-package ccf`, and the release version gate discovered `ccf`.
- After: it builds and installs as `ccf-sdk` (`ccf_sdk-<version>.dist-info`; `ccf-sdk`, `ccf_sdk` and `ccf.sdk` are the same project under PEP 503); `harnesses` and `dev` compose `ccf-sdk[...]`; `requirements.lock` is regenerated with `--unsafe-package ccf-sdk` (pins and hashes unchanged); the gate discovers `ccf-sdk` and refuses when it finds none, even if a distribution named `ccf` is present. Installed packages are still `ccf` and `ccf_runtime`, and the `ccf` command is unchanged. The metadata also carries the classifier `Private :: Do Not Upload` (Dave's ruling, 2026-10-07), which PyPI refuses on every upload, so the SDK cannot be published there by accident; the empty name-reservation placeholder in `packaging/pypi-placeholder/` carries none.
- Why: SEC-027 (`D-IMPL-376` ruling 4). Red tests: `tests/test_distribution_name.py::test_the_package_metadata_names_the_distribution_ccf_sdk`, `::test_no_declared_requirement_names_the_foreign_pypi_project_ccf`, `::test_every_reader_of_the_sdks_own_metadata_names_the_declared_distribution`, `::test_the_version_gate_refuses_when_only_a_distribution_named_ccf_is_visible` and `::test_the_version_gate_reads_the_ccf_sdk_distribution_beside_a_foreign_ccf`.
- Migration: in an environment that holds the former install, run `pip uninstall ccf` before installing `ccf-sdk`. pip keeps both names, and uninstalling `ccf` afterwards deletes the files the two share: for a non-editable install, every package file of `ccf-sdk`, repaired with `--force-reinstall`. Never `pip install ccf` and never `pip install "ccf[...]"`: from a public index those install Microsoft's package. Install `ccf-sdk` from the repository.
