# Script Quality Rubric

This rubric is used by the Critic and Rewrite passes. Passing schema validation is necessary but insufficient.

## Deck-level checks

### Narrative necessity

Each chapter and page must have a clear reason to exist in the audience's path to the final judgment or action.

### Progression

Adjacent pages must exchange something meaningful: a question, premise, result, mechanism, evidence, decision, or consequence.

### Coverage

All source-critical claims, constraints, numbers, responsibilities, and user-required questions must be represented, intentionally deferred, or explicitly excluded with a reason.

### Non-duplication

Two pages must not make materially the same point with different wording unless repetition has a deliberate communication purpose.

## Page-level checks

1. **Audience question** — the page answers one identifiable audience question.
2. **Core message** — one sentence captures the page's final judgment.
3. **Argument integrity** — supporting points genuinely support the core message.
4. **Evidence adequacy** — claims are supported by facts, source evidence, mechanism, data, or explicit constraints.
5. **Specificity** — replace empty verbs and generic management language with concrete objects, actions, mechanisms, and outcomes.
6. **Hierarchy** — parent concepts and child differences are not redundantly repeated.
7. **Onscreen economy** — onscreen text carries the minimum content needed for comprehension while preserving critical meaning.
8. **Semantic visualizability** — the page contains identifiable objects and relationships that can be rendered visually.
9. **Continuity** — the page receives from the previous page and provides something to the next page.
10. **Source fidelity** — no invented causality, chronology, ranking, responsibility, numeric precision, or policy status.

## Rewrite triggers

Rewrite the page or section when any of the following is true:

- the core message is merely a topic label;
- modules are a collection of related facts without a dominant relationship;
- removing one module does not change the page's answer;
- the title and body repeat the same sentence;
- multiple pages can be swapped without affecting the narrative;
- claims use unsupported intensifiers or policy strength;
- important source content appears only in notes or trace fields without a deliberate reason;
- the page is structurally valid but reads like schema completion.

## Critic output

The Critic should identify the smallest number of root causes that explain the weakness, then issue rewrite instructions. It should not create a second competing script.
