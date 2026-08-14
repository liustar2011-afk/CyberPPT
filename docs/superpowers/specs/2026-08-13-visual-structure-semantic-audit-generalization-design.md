# Visual Structure Semantic Audit Generalization

## Goal

Remove education-gateway-specific knowledge from the global Stage 01 visual-structure audit while retaining rules that can be established from a page's own declared semantic relation.

## Decision

The global audit will retain only relation-local diagnostics:

- a visible result requested by the visual handoff must occur in locked on-screen text;
- Stage 01 must not prescribe geometry or add a second primary narrative;
- a node explicitly described as cross-cutting in the same page must not also be staged as a peer of the page's primary chain;
- a mechanism labelled as an isolation or degradation control must not be peer-staged with declared business chains in a swimlane relation.

The audit will remove the gateway-centered visual-center rule and the boundary-shell versus depth-defense primitive rule. Both infer a preferred visual carrier from a fixed project's vocabulary; the Stage 01 script does not contain enough structured, project-neutral evidence to make those inferences safely.

## Boundaries

This change does not introduce project profiles or configuration files. A profile would preserve unsupported domain knowledge behind another interface. It also does not make Stage 01 select a Stage 02 visual carrier; that responsibility remains in the visual-structure stage.

## Testing

Tests will prove that cross-cut and mechanism warnings still fire with non-education domain language, while gateway, engine, and depth-defense vocabulary no longer produces project-specific mismatch diagnostics.
