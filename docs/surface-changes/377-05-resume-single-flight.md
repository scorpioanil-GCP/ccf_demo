# 377-05 — one resumption per execution at a time, in one process

Dave's ruling on 2026-10-07 at 14:27 MST (*"Small fix now"*), recorded under
`D-IMPL-377`. It closes residual 2(a) of the ledger in
`runtime/ccf_runtime/workflow/engine.py::WorkflowEngine._gate_authority` for a
single process. Measured on 2026-10-07 against `34a1f6bf`: two concurrent
resumes of ONE approved suspension both passed the gate's authority and conflict
checks, ran the node after the gate twice, and wrote two attributed
`workflow_resumed` rows for the one approval. That held in 5 of 5 runs on one
event loop with a downstream skill that awaits once, in 5 of 5 with two OS
threads (one engine, and two engines over one Control Plane), and in 3 of 3
through `POST /workflow/resumptions`. The red tests are
`tests/workflow/test_resume_single_flight.py` and
`tests/http_api/test_resume_single_flight_door.py`.

**What this does NOT do.** The claim lives in one process's memory. It does not
serialize resumptions across processes, or across several state-store objects
that front one durable store, because `ControlPlaneStateStore` offers no
compare-and-set. It does not reach residual 2(b), a verdict recorded while a
resumption is in flight: verdicts are recorded through the HITL transport, which
the claim never touches. Re-measured on this branch, a rejection recorded
between a resumption's conflict check and its commit still leaves the execution
at the approving terminal with both verdicts on record (15 of 15 forced-timing
runs). It makes no step idempotent. A resumption that fails or is cancelled
after its step started gives the claim back, and the retry runs the step again.

## ccf_runtime.workflow.engine.WorkflowEngine

- Surface: ccf_runtime.workflow.engine.WorkflowEngine
- Public surface: true
- Change type: behavior
- Before: `resume` took no claim on the execution. Two concurrent resumptions of one suspension each read the state record before either wrote over it. Both passed the gate's authority and conflict checks and ran the node after the gate, and each appended an attributed `workflow_resumed` row for the one approval.
- After: `resume` takes a single-flight claim on the execution before it reads the record and gives it back on every exit: completion, refusal, exception and cancellation. The claim is keyed by the Control Plane state store the record lives in and by the execution's state key, and every engine in the process over that store shares it. A second resumption of the same execution while one is in flight returns `WorkflowResumeRefused`, whose reason says the execution "already has a resumption in flight in this process". It is audited `resolved=False` with no actor, and the HTTP door answers it 409, as it answers the sequential refusal. Nothing is queued, and no lock is held across an await.
- Why: `D-IMPL-377` (Dave, 2026-10-07: *"Small fix now"*): one human approval must authorize one passage past its gate.
- Migration: a caller that resumes one execution concurrently in one process now receives a refusal for every request but one, and presents it again after the first has returned. A deployment that can resume one execution from several processes, or through several state-store objects fronting one durable store, must still serialize resumptions per execution in front of the door. Keep the steps after a gate idempotent.
