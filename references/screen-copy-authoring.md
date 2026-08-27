# Onscreen Copy Authoring

## Purpose

Translate a complete page argument into presentation language without losing the page's judgment, proof logic, distinctions, or source boundaries.

## 1. Write in the correct order

Use this order:

1. complete page argument;
2. information hierarchy;
3. onscreen copy;
4. speaker notes.

Do not start by compressing source paragraphs into short labels. Premature compression is a major cause of generic, repetitive PPT copy.

## 2. Separate title, judgment, and support

A page may use a topical title or a judgmental title depending on context. Do not force one title style for every page.

Regardless of title style:

- `core_message` must contain the page's complete answer or judgment;
- module headings must organize the proof or explanation;
- supporting copy must add differentiated information;
- the title, core message, and first module must not repeat the same sentence in three forms.

## 3. Build a readable semantic hierarchy

A content page normally contains:

- page title;
- optional lead / conclusion line when it materially improves comprehension;
- a small number of semantic groups;
- within each group, a short business heading and differentiated supporting copy;
- selected numbers, labels, annotations, examples, or boundary notes when needed.

Choose semantic groups by argument role, such as:

- reason;
- mechanism;
- evidence;
- stage;
- actor;
- capability;
- application;
- output;
- value;
- boundary.

Do not use parallel boxes merely because several source bullets exist.

## 4. Compression rules

- Preserve the claim, object, action, qualifier, and result that carry meaning.
- Shared predicates or qualifiers should appear once at the parent level when possible.
- Child items should carry differentiated information.
- Keep exact numbers, units, time periods, status, responsibilities, and conditions when material.
- Avoid mechanically converting every source bullet into one visual module.
- Avoid turning background details, form fields, attachment lists, or operational minutiae into equal-weight onscreen blocks.
- Numerical ordering may be used only when the source supports real sequence, phase, priority, timing, dependency, or gating.
- If a boundary controls how a claim may be understood, do not compress it away solely to make the page shorter.

## 5. Relationship-first expression

Before finalizing onscreen copy, identify the page's dominant semantic relationship:

- progression;
- causality;
- hierarchy;
- comparison;
- actor interaction;
- input-output transformation;
- decision criteria;
- closed loop;
- evidence-to-conclusion.

The copy should make this relationship legible before Stage 02 decides how to visualize it.

## 6. Language quality

Prefer concrete institutional, business, technical, and operational wording.

Generic verbs such as “加强、提升、推动、赋能、打造、构建” require a concrete object, mechanism, or result; remove them when they add no information.

Avoid:

- empty management language;
- duplicated labels;
- slogans used as evidence;
- artificial symmetry;
- explanatory meta-language addressed to the author or operator;
- source citations replacing actual explanation;
- `source_refs` / citation codes / the word "证据" appearing inside onscreen wording. Traceability is a separate machine field rendered in its own section; the audience never reads it.

## 7. Density

Do not impose one universal character count on every page. Density should follow the page's role and evidence burden.

A strong page can be concise or dense. The requirement is that hierarchy stays readable and every visible line performs a distinct semantic job.

Default toward a populated hierarchy rather than a flat one. For a page whose `content_load` is `standard` or `dense`, a module built from a single `heading` + one-line `text` and nothing else is the exception, not the default — most modules on such a page should carry an `items` list of concrete sub-points (named entities, numbers, roles, conditions) so the module proves something rather than just naming a topic. Reserve the flat single-line form for `light` pages, transitions, or a module that is genuinely atomic (one number, one relationship, one decision).

When a page is overloaded, first decide whether to:

1. remove non-essential material;
2. move explanation to speaker notes;
3. merge redundant statements;
4. split independent audience questions into separate pages.

Overload and low density are different failure modes — do not fix one by silently causing the other. If compression starts erasing the sub-points that make a module concrete, the page needs a split (see storyline-planning.md's split test), not a thinner module.

One hard, page-role-independent ceiling does apply: each short phrase inside an onscreen `text`/`items` line's body — the part after a `标签：` prefix, if present, split on `、，,；;` into individual phrases — must stay at or under 30 meaningful (Chinese/Latin/numeric) characters. The ceiling is per phrase, not per line: a line holding several punctuation-separated phrases (e.g. "供得出、流得动、用得好、保安全") is fine even if their combined length exceeds 30 — that per-phrase distillation is what makes on-screen copy read as PPT phrasing instead of Word-style prose. This is not a house-style preference; it is CyberPPT Stage 02's own ImageGen readiness gate (`assert_imagegen_onscreen_readiness`), enforced here by `cyberppt-script lint` so a paragraph-like phrase is caught during AUTHOR/CRITIQUE rather than at the Stage 02 handoff. A phrase at risk of exceeding it should be split into more, shorter parallel items (preserving every named entity) rather than trimmed down to a vaguer phrase — the full sentence belongs in `full_copy`/`speaker_notes`, which carry no such ceiling.

A paired floor applies in the other direction: a `content` page's total onscreen body (all `text` + `items` meaningful characters summed across every module on the page, headings excluded) must reach at least 240 characters, also enforced by `cyberppt-script lint`. The per-phrase ceiling above stops a single phrase from reading like prose; without a floor, a page can still be compressed down to a handful of near-empty labels that lose the source's concrete sub-points. When a page is under the floor, add more short, parallel `items` per module — pull real sub-facts, numbers, roles, and conditions from `foundation.json` — rather than lengthening any one phrase, which would trip the ceiling instead. A `light`-density page is exempt: the floor only applies to `content`-type pages, and within those, `cyberppt-script lint` additionally skips any page whose `content_load` is `light` (cover/divider/contents pages are naturally `light` by page type; a genuinely thin `content` page — e.g. a short executive-summary table row with only a handful of source facts — should also be planned as `content_load: light` in `deck-plan.json` rather than forced to invent filler to clear the floor).

## 5a. Density floors are met by new facts, never by restating one

Both density floors above (240 onscreen chars, and `full_copy`'s 350-char floor in 6a below) exist to stop content from being compressed into bare labels. They do not license the opposite failure: hitting the number by adding a second `items` line that says the same thing as the first in different words. `cyberppt-script lint` catches this mechanically — `check_onscreen_structure` flags any two lines within the same module whose normalized text similarity is 60% or higher. When a module is short of the floor, go back to `foundation.json` and pull a sub-fact, number, role, or condition the module does not yet carry; do not paraphrase what is already on the page. Within a module, order the lines the way the source presents them — chronologically for a sequence of events, causally for a mechanism, by stated priority for a list — rather than in whatever order they were added during drafting; an out-of-order list reads as assembled, not authored, even when every individual line is accurate.

## 5b. A "relationship" module is not a density strategy

Every onscreen module must carry a concrete distinguishing fact — a number, named entity, role, condition, or boundary — that is not already stated by the other modules on the same page. A module whose entire content is commentary on how the *other* modules relate to each other ("A与B共同构成…的基础"、"C衡量…是否合理"、"D检验…能否…") adds no new fact; it just restates what the peer modules already show, wearing a "关系"/"相互关系"/"对应关系" heading. This is the multi-module version of the 5a anti-pattern (restating a point to reach the density floor) and is banned for the same reason, even though 5a's line-similarity check does not catch it (the restatement is spread across a whole module, in different words, not one duplicate line).

The dominant semantic relationship identified in section 5 belongs in `visual_thesis` (as the page's stated judgment) and in `relationships` (as the structure Stage 02 renders) — and it may thread through `full_copy`'s connective sentences. It does not need, and should not get, its own onscreen card unless that card itself introduces a fact the audience has not yet seen (e.g. a genuine dependency the audience must act on, stated as that dependency's concrete content, not as a meta-description of "the relationship"). When a page is short of the density floor and no such module exists, the page's source material is thin — plan it as `content_load: light` (see section 7) rather than manufacturing a relationship-narration module to hit the count.

## 6a. `full_copy` needs its own floor, not just onscreen

`full_copy` is the fully-argued paragraph a presenter could read verbatim — it carries no per-line ceiling, so it is not subject to the 30-character rule above. But it is not exempt from being thin: a `content` page's `full_copy` must reach at least 350 meaningful characters, enforced by `cyberppt-script lint`. A page under the floor is usually missing one of: an enumerated sub-point the source actually states (an "一是/二是/三是" item silently dropped), a concrete number or named entity, or the closing synthesis sentence that ties the enumerated points back to the page's core claim. Diagnose which is missing and pull it from `foundation.json` — do not pad by restating the same claim in different words, which reads as filler rather than substance.

## 8. Renderer independence

Do not specify font, color, icon style, decorative treatment, image-generation model, layout coordinates, or visual-style preset in the final script. Those belong to Stage 02.
