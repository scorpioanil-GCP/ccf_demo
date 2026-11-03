# Context Skills — SK-01

**Running examples:** [current setup, Fluree 4.2.4 and connection configuration](../CONFIGURATION.md).

The executable example is in the SDK at [examples/sk-01-declare-and-govern-agent-skills](https://github.com/drcastillo/ccf_code/blob/5f85b389efe9e4b1de62e84a5af62ca4b2e12178/examples/sk-01-declare-and-govern-agent-skills/README.md). From that SDK checkout, configure the producer and estate as described below, then run `make example-sk-01`.

- [Context Skills reference](../../05-reference/05-technical-reference/CONTEXT_SKILLS.md): meaning, authority, evidence and supported limitations.
- [Implementation walkthrough](../../05-reference/02-context-product-producer/examples/SK01_DECLARE_AND_GOVERN_AGENT_SKILLS.md): exact declarations, prerequisites, commands and expected results.
- [SME / Information Architect analysis](../../05-reference/02-context-product-producer/examples/SK01_DECLARE_AND_GOVERN_AGENT_SKILLS_ANALYSIS.md): banking problem to Standard v0.3 sections A–G, grounded in the example's actual configuration.

This example grants a composing agent permission to ask the collateral product. It does not expose that Context Skill as a model tool, call an LLM or demonstrate live grant/revoke management. Fluree **4.2.4** is the current requirement for the collateral producer's graph source.
