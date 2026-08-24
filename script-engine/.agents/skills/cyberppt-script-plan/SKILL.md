---
name: cyberppt-script-plan
description: Convert a validated Script Engine foundation and communication goal into a lightweight whole-deck plan. Use after UNDERSTAND and before AUTHOR. Decide narrative, chapters, page sequence, audience questions, page messages, proof logic, required content, and transitions. Do not write full page copy or renderer-specific visual instructions.
---

# PLAN

## Mission

Design the smallest coherent deck structure that can achieve the communication goal while preserving source-critical content.

Output one authoritative `deck-plan.json`.

## Inputs

1. `foundation.json`;
2. user communication goal or a source-grounded proposed goal;
3. explicit audience, length, scenario, and required questions when provided.

## Whole-deck planning

First determine:

- what the audience already knows or assumes;
- what they must understand, decide, approve, or remember;
- the final judgment or action the deck should enable;
- the narrative arc required to move from the starting state to that destination.

Chapters represent different audience understanding tasks. Do not reproduce source document headings mechanically.

## Page plan

Each content page contains only these required planning fields:

- `question`: the audience question answered by this page;
- `message`: the single source-supported answer or judgment;
- `logic`: the dominant reasoning path used to establish the message;
- `content`: the source-critical content required to complete that reasoning;
- `next`: why the next page logically follows, when applicable.

Optional `source_refs` preserve traceability.

## Split / merge test

Split when one page contains multiple independent audience questions or incompatible dominant relationships.

Merge when two candidate pages answer the same audience question and can be proven through one coherent logic chain without losing readability or an indispensable judgment.

Page-count pressure alone is not a reason to merge unrelated reasoning.

## Deck review before delivery

Check:

1. every page has a non-substitutable role;
2. adjacent pages form a meaningful progression;
3. no material source requirement disappears;
4. no two pages make essentially the same judgment;
5. detailed evidence is allocated to the page where it actually proves something;
6. the deck can be explained as one narrative in a few sentences.

## Output

Write `deck-plan.json` conforming to `contracts/deck-plan.schema.json`.

Then present Gate A: communication goal, chapter structure, page sequence, and page-level messages for review.
