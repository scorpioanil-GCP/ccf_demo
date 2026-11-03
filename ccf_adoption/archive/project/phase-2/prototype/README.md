# CCF Adoption Portal — Phase 2C Prototype

This prototype validates the approved Phase 2 information architecture and dark enterprise visual system before committing to a production site generator.

## Validated page types

- approved landing page / primary navigation;
- assembler tutorial and specification workflow;
- SDK Reference page;
- Financial Services use-case page;
- evidence components for Data Reality, Control Demonstrated, and Boundary / Not Proven.

## Validated landing interactions

- resource routing to overview / whitepaper / architecture / SDK / examples / Context Products;
- developer, Financial Services, and evaluator entry points;
- horizontal Financial Services gallery with previous/next controls;
- navigation among tutorial, reference, and use-case surfaces.

## Prototype implementation

The working prototype is deliberately dependency-free HTML/CSS/JavaScript. This proved the design does not require a heavy application framework and can be implemented as a documentation-first site with targeted custom components.

Generated visual assets used during Product Design exploration are **not being promoted as canonical architecture assets**. Production should preferentially reuse authoritative diagrams and figures from `drcastillo/ccf` and use generated imagery only where it adds value without changing architectural meaning.

## Production implication

MkDocs Material remains viable, but the approved experience requires custom theme/override work for:

- the landing hero and resource strip;
- horizontal use-case gallery;
- audience-routing cards;
- evidence/control/limitation callouts;
- business-first Financial Services page templates.

See `PROTOTYPE_STATUS.md` and `design-qa.md`.