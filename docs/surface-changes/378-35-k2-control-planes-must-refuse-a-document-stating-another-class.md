# 378-35 (K2) — every Control Plane must refuse a document that states another class

`D-IMPL-378` K2, ruled (b) by Dave on 2026-10-08 at 12:29 MST: amend the `ControlPlaneProtocol` text
*"plus a conformance check demonstrating rejection by a third-party implementation. Documentation alone
is not enforcement evidence."* Built in lane 378e-small.

Lane 378d-classid made `src/ccf/controlplane/artifact_base.py::ArtifactClass.validate` refuse an artifact
whose own top-level `class_id` disagrees with the class it is presented as
(`ArtifactClassIdMismatch`, fragment 378-28). The SDK's registry and every SDK boot door enforce it. A
third-party `ControlPlaneProtocol` implementation got the registry-level guard only if it validated the
same way, and nothing the SDK offered could tell whether it did.

**What changed.** The Protocol's own text now obliges both typed registration methods to validate with
`artifact_class.validate(artifact)` before anything is stored or audited, and names the conformance check.
The signature is unchanged. The check is new:
`tests/conformance/test_control_plane_class_identity.py::check_registration_refuses_a_document_stating_another_class`,
run against every factory in that module's `PLANES`, the way the SDK's other Protocol conformance suites
are run (`D-16`). It fails a plane by name (`ClassIdentityNotEnforced`, naming the method) when the plane
admits a disagreeing document, refuses it with anything other than `ArtifactClassIdMismatch`, or files or
audits anything before refusing. It also fails a plane that refuses everything, because the same plane
must register a document stating the class it is registered as.

**Demonstrated with two minimal third-party implementations** in the same module. One validates with
`artifact_class.validate` and passes. The other checks only the contract's type, as a plane written before
`D-IMPL-378` does, and the check fails it by name: for `register_typed` and for `register_versioned`, each
cut on its own. The SDK's `ControlPlaneRegistry` passes.

**What this does NOT do.** The SDK cannot run the check inside a remote Control Plane at run time: an
implementation is held to it by running the conformance module with its factory listed. The SDK's boot
doors are unaffected either way: they parse every document through `ArtifactClass.validate` before
registering anything (fragment 378-28).

## ccf.controlplane.registry.ControlPlaneProtocol

- Surface: ccf.controlplane.registry.ControlPlaneProtocol
- Public surface: true
- Change type: behavior
- Before: same members and signatures. `register_typed` said it validates against `artifact_class` without saying how, and `register_versioned` said nothing about validation, so an implementation that checked only the contract's type conformed on paper while filing a document stating one class under another
- After: same members and signatures; documentation only. Both methods are obliged to call `artifact_class.validate(artifact)` before anything is stored or audited, so an artifact whose own `class_id` disagrees with the class it is registered as is refused as `ArtifactClassIdMismatch`. The text names the conformance check
- Why: `D-IMPL-378` K2 (b). Red test: `tests/conformance/test_control_plane_class_identity.py::test_the_protocol_states_the_class_identity_obligation`; enforcement evidence: `::test_registration_refuses_a_document_stating_another_class` and `::test_the_check_fails_a_third_party_plane_that_does_not_validate_by_name`
- Migration: a third-party Control Plane calls `artifact_class.validate(artifact)` in `register_typed` and `register_versioned` before storing or auditing, adds its factory to `PLANES` in `tests/conformance/test_control_plane_class_identity.py`, and runs that module

## tests/conformance/test_control_plane_class_identity.py

- Surface: tests/conformance/test_control_plane_class_identity.py
- Public surface: false
- Change type: added
- Before: absent. The SDK offered no conformance check for `ControlPlaneProtocol`
- After: the conformance check for a Control Plane's class-identity obligation, run against the reference registry and a validating third-party implementation, and shown to fail a contract-only implementation by name, per method
- Why: `D-IMPL-378` K2 (b): documentation alone is not enforcement evidence
- Migration: none for a deployment on the SDK's registry; a deployment with its own Control Plane lists its factory and runs the module
