# CyberPPT AUTHOR Contract

This file is the single operational authority for `AUTHOR`, `CRITIQUE`,
`REWRITE`, targeted page revision and whole-deck script review when the approved
Deck Plan selects `authoring_mode: analytical`. Read it completely before taking
any of those actions. `AGENTS.md` remains the repository-level hard constraint
and overrides this contract if they differ.

Do not copy these rules back into `SKILL.md`. The workflow entrypoint routes here;
this file owns analytical authoring behavior. Project examples, customer names,
industry-specific facts and source-specific vocabulary do not belong in this
contract. They belong in the current Foundation, Deck Plan and Final Script.

The contract has four rule classes:

1. **Execution** — who authors and the required page sequence;
2. **Semantic foundation** — source fidelity, evidence ownership and the
   structured full-copy layer;
3. **Audience-facing construction** — conclusion, argument, onscreen hierarchy,
   relationships, density and speaker notes;
4. **Review and delivery** — Critic, rewrite and deterministic boundaries.

## 1. Execution

### 1.1 Authority

`AUTHOR` is a generative agent stage, not a deterministic transformation from
`deck-plan.json` to Markdown. The current main agent performs reading, judgment,
candidate comparison, writing, Critic and rewrite. There is no separate AUTHOR
Skill, rules-based generator or project-specific author script.

Passing schema, lint, provenance or source-coverage checks does not execute
AUTHOR and does not prove analytical quality. Deterministic checks run after the
generative pass and verify only contracts they can prove.

### 1.2 Required page sequence

Run these steps in order for every analytical content page:

1. **Load the page brief.** Read the document thesis once per deck. For the target
   page, load its approved mission or question, page-bound `source_refs`, adjacent
   page boundaries and relevant typed Foundation records. Do not rerun whole-
   document UNDERSTAND during local AUTHOR or Rewrite work.
2. **Lock source meaning.** Identify the strongest explicit facts, source status,
   actors, actions, objects, numbers, dates, conditions, boundaries, formal
   instruments and explicit relations available to the page. Separate direct
   source meaning from author synthesis.
3. **Author the page conclusion.** `core_message` answers the page question in a
   single decision-bearing statement. It names the business matter and preserves
   source status, responsibility and scope.
4. **Build the page structure.** Form independent arguments that establish,
   explain, qualify or implement the conclusion. Bind every argument to the
   source evidence that supports it. Do not manufacture causality, necessity,
   hierarchy, sequence or completeness from lexical similarity.
5. **Write semantic-preserving full copy.** Reorganize source material into a
   judgment-first hierarchy. Preserve protected payload and keep unsupported
   synthesis visibly qualified.
6. **Set the reading form.** Decide whether the page needs a compact argument,
   classification, mapping, comparison, convergence, roadmap, governance chain
   or `pyramid_prose`. Use the smallest form that exposes the verified logic.
7. **Project to onscreen.** Select only the conclusion, decisive arguments,
   decisive evidence and material conditions needed for independent reading.
   Onscreen text derives from the completed full copy; it does not form a second
   independent argument.
8. **Build visible hierarchy.** Apply `one page, one conclusion; one level, one
   question; peers, one dimension; children, added evidence; different levels,
   visible relationships`.
9. **Check subject and argument continuity.** Keep one primary audience question
   and one principal role per reasoning unit. Split condition, diagnosis,
   response and result when their relationship is not explicit.
10. **Check peer logic.** Siblings must share one comparison dimension and
    comparable analytical depth. Supplementary proof belongs beneath the claim it
    qualifies.
11. **Check strength and scope.** Compare every audience-facing layer with bound
    evidence. Preserve status, modality, responsibility, numbers, conditions and
    page boundaries.
12. **Expose relationships.** When a conclusion depends on mapping, sequence,
    support, conversion, feedback or governance, show both endpoints and the
    connecting action, trigger or landing.
13. **Write incremental speaker notes.** Notes add explanation, subordinate
    evidence, non-material context or a natural transition. They do not merely
    restate the visible page.
14. **Critique and rewrite the page.** Reconstruct its question, claim, arguments,
    evidence and relation grammar independently. Rewrite from the earliest broken
    reasoning link rather than line-editing downstream symptoms.
15. **Run whole-deck Critic, then deterministic checks.** Review cross-page scope,
    repeated evidence, storyline, density and conclusion synthesis before final
    delivery gates.

## 2. Semantic foundation

### 2.1 Evidence boundary

The approved page `source_refs` defines the available evidence boundary. It is
not a requirement to reproduce every source item, and it is not permission to
invent a relation among those items.

For Final Script 1.1, module and item provenance is authoritative. AUTHOR selects
claim refs and supporting refs and declares the intended relation. Status,
argument duty, actor, condition and claim origin come from Foundation records;
Final Script must not duplicate them as a second semantic authority.

Every visible conclusion or detail must have a traceable disposition:

- **direct** — expresses one source fact without changing its role or strength;
- **synthesis** — combines multiple source facts into an author conclusion whose
  inference is supportable and reviewable;
- **relation** — states a relationship supported by explicit or typed relation
  evidence.

When provenance is unavailable in legacy input, lexical similarity may help
Critic locate candidate evidence, but it never becomes semantic proof.

### 2.2 Source fidelity and protected payload

`full_copy` is the structured semantic source consumed by `onscreen`. It retains
the page's decisive facts and all payload whose removal can change meaning:

- named actor or responsible party;
- action, object and responsibility;
- formal instrument identity and document type;
- number, date, quantity and unit;
- source status, modality and temporal state;
- condition, trigger, exception and applicable boundary;
- negative, optional or independent-choice meaning;
- explicit relationship and its direction.

A source statement cannot be strengthened because a nearby sentence uses a
stronger verb. A status belonging to one object cannot be applied to a group. A
condition attached to one action cannot be borrowed by another action. A number
cannot be reassigned to another object merely because both appear on the same
page.

When shortening risks changing protected payload, retain the complete parent
proposition. Verbatim fallback for the affected passage is preferable to an
unsafe author-created summary.

### 2.3 Direct fact, synthesis and inference

Analytical mode permits synthesis inside the approved evidence boundary. It does
not erase the distinction between source fact and author judgment.

Use the following discipline:

1. A **direct fact** may be paraphrased while preserving actor, predicate, object,
   status, condition and scope.
2. A **synthesis** must state what several facts jointly establish and must not
   imply that the source itself used the synthesized label.
3. An **inferred relation** must be presented with appropriate epistemic strength.
   It cannot be recast as an achieved operating mechanism, mandatory rule or
   source-defined term.
4. An **open question or recommendation** remains visibly non-achieved. Do not
   convert a proposal into an existing capability or a possible path into a
   committed sequence.

The Critic judges whether an inference is substantively supported. Deterministic
code may verify provenance cardinality, relation compatibility and protected
payload, but it must not infer business entailment from a global word list.

### 2.4 Full-copy hierarchy

Write `full_copy` as professional analytical prose, not as a dump of source rows.
Each substantive paragraph advances one principal part of the argument:
conclusion, basis, diagnosis, relationship, action, result, condition or boundary.

Default structure:

`paragraph judgment → supporting explanation → source-backed evidence/qualification`

For genuinely parallel branches:

`paragraph core conclusion → parallel sub-conclusion → supporting detail`

For a directional relation:

`initial state/condition → change or action → resulting state/implication`

For a bounded decision:

`recommended action → evidence basis → material condition/counterargument`

Do not force numbered enumeration onto a causal chain. Do not turn a list of
actors, methods, tasks and outcomes into peer modules unless one declared
classification dimension makes them peers.

### 2.5 Judgment-led prose quality

Apply these authoring tests to `core_message`, `full_copy` and `onscreen`:

1. **Audience takeaway.** A reader can state what the page establishes, changes,
   recommends or constrains.
2. **Judgment before evidence.** Evidence follows the proposition it supports;
   a document title, code or actor name is not itself a conclusion.
3. **Natural professional syntax.** Statements remain intelligible without cards,
   colour, indentation or narration.
4. **Object completeness.** Generic verbs such as `推进`, `形成`, `支撑`, `提升`
   require a clear actor or subject, object and material effect when they carry
   the analytical judgment.
5. **Source-owned strength.** Stronger status, responsibility, necessity or
   exclusivity is used only when supported by typed evidence.
6. **Decisive selection.** Keep a visible fact because it changes understanding of
   the conclusion, not because it happens to be available in the source.

These are generative criteria. Character count, sentence count, similarity score
and generic predicate detection may create review signals only.

### 2.6 Page writing framework selection

In analytical mode, use two composable layers.

#### Universal organising framework

Use **claim–argument–evidence** as the basic reasoning discipline. Apply:

- **Pyramid** when the audience needs the answer before independent reasons;
- **MECE** when a closed, non-overlapping grouping can be justified against a
  defined universe;
- **SCR** when the page or chapter needs to move from a shared situation through
  a material complication to a supported response.

The methods organize reasoning. Do not expose framework jargon unless it helps
the audience.

#### Relationship grammar

Choose a visible grammar only when the page needs to express that relationship:

- **classification** — independent parts under one dimension;
- **mapping** — source, correspondence rule and target/use;
- **comparison** — matched objects under one criterion;
- **convergence** — several independent inputs jointly support one result;
- **roadmap** — stage, trigger and newly reached state;
- **governance chain** — actor, mechanism, collaboration/resource and result;
- **flow/loop** — input, action, output, handoff and optional feedback.

A Pyramid can organize a roadmap, mapping or governance chain. MECE can group
inputs or categories inside a larger relationship grammar. SCR can organize a
chapter while individual pages use other grammars. Select the smallest
combination needed to make the supported reasoning readable.

### 2.7 Density and heading preflight

Perform this preflight before drafting a dense content page:

1. State one primary audience question.
2. State one `core_message` answer.
3. Select one primary relationship grammar.
4. Identify two to four top-level argument roles as the normal authoring budget.
   A source-defined taxonomy or roadmap may exceed this when its dimension and
   reading direction remain clear.
5. Attach decisive evidence to each argument.
6. Move non-decisive inventories to full copy, notes or a genuine reference
   structure.
7. Shorten by restructuring before wording. Promote a shared proposition, split
   mixed roles, or divide the page before dropping protected meaning.

The budget is an authoring heuristic, not a deterministic production limit.

### 2.8 Subject and argument continuity

Trace each paragraph and onscreen module through three dimensions:

- audience question;
- actor or subject;
- argument role.

Rules:

1. One reasoning unit owns one primary question.
2. Complete one actor's decision-bearing evidence before switching actors unless
   a supported relationship requires interleaving.
3. Follow source-supported responsibility order; never infer administrative rank
   from an institution name alone.
4. A transition names the handoff when the next unit changes from condition to
   response, diagnosis to action, input to output or evidence to implication.
5. Re-entry to an earlier actor needs a new explicit relationship such as
   feedback, comparison or responsibility handoff.

These are Critic methods, not lexical entity-recognition gates.

### 2.9 Claim–argument–evidence operating loop

Before prose, express the page internally as:

`claim → independent argument(s) → source-grounded evidence`

Execute this loop:

1. **Define question and universe.** Restate the page mission as one answerable
   question and define the evidence-scoped universe.
2. **Choose decomposition logic.** State the rule that makes top-level arguments
   peers: stage, actor role, condition, capability, priority, cause, response or
   another supported dimension.
3. **Form a testable proposition.** State what must be true for the conclusion to
   hold and identify the strongest source-bound fact or condition that could
   weaken it.
4. **Build argument cards.** For each argument, record internally its complete
   sub-judgment, evidence refs, source strength and decisive retained fact.
5. **Synthesize in Pyramid order when useful.** Put the governing answer first,
   then independent reasons, then evidence.
6. **Project into the relation grammar.** Choose the visual/reading grammar only
   after the reasoning is stable.

The **MECE test** requires both mutual exclusivity and collective exhaustion
against a declared scope. If the source does not define a closed scope, state the
boundary and do not claim completeness.

The **Pyramid test** requires the answer before its reasons and evidence beneath
the argument it supports. Source-order paraphrase does not pass merely because it
is concise.

The **SCR test** requires a real complication before a response. Do not invent a
tension simply to fit the framework.

### 2.10 Page-logic normalization

Before drafting `full_copy`, normalize the page in working judgment:

1. Rewrite the page question as one decision-bearing question.
2. Assign each candidate fact one principal page role: context, basis, gap,
   response, result, condition or boundary.
3. Build one readable relation among retained roles. Related facts without a
   directional or grouping predicate remain an inventory.
4. Compare each paragraph with adjacent-page questions. Material belongs to the
   page whose question it answers most directly.
5. Give each paragraph one principal role and one parent argument.
6. Place results only after the action/condition that supports them or on the page
   that owns implementation/results.
7. Run a role-switch Critic with titles and visual design hidden.
8. Rewrite from the earliest invalid link: question, chain, paragraph ownership,
   full copy, then onscreen.

### 2.11 Mandatory full-copy structure pass

After page-logic normalization:

1. Classify each paragraph as parallel facts, directional chain, qualified claim
   or single point.
2. For genuine parallel content, use a paragraph judgment followed by independent
   sub-conclusions and evidence.
3. Test peers for one dimension. Regroup mixed actors, methods, tasks and outcomes.
4. Reject label-led pseudo-structure. A label is not a sub-conclusion unless its
   visible parent supplies the complete relation.
5. Preserve non-parallel forms instead of forcing enumeration.
6. Flatten and read the paragraph. Every detail must have one parent and every
   sub-conclusion must advance the paragraph judgment.

Critic performs the semantic classification. Deterministic lint may check explicit
structure, IDs and policy constraints but does not decide whether business facts
are genuinely parallel.

## 3. Audience-facing construction

### 3.1 Onscreen selection

`onscreen` is the mandatory selection point. It contains the smallest visible set
that lets a silent reader understand the page conclusion and its decisive basis.

Keep:

- the page conclusion or an equivalent level-1 thesis;
- the top-level arguments needed to establish it;
- decisive evidence beneath each argument;
- material status, condition, number, responsibility or boundary;
- visible endpoints for non-parallel relationships.

Move subordinate examples, repeated proof and non-decisive citations to full copy
or notes.

When the user requests conclusion-first complete prose, use `pyramid_prose`: the
heading carries the conclusion and the text retains complete supporting
paragraphs. Do not convert complete prose into artificial short labels merely to
satisfy a visual density preference.

### 3.2 Hierarchy model

Use one universal hierarchy rule:

`one page, one conclusion → one level, one question → peers, one dimension → children, added evidence → different levels, visible relationships`

Three semantic levels:

1. **Page conclusion** — one complete answer to the page question.
2. **Module judgment** — one independent reason, mechanism, bounded action or
   source-defined category that advances the conclusion.
3. **Evidence detail** — fact, scope, condition, number, action, object or result
   that establishes the module judgment.

A taxonomy category, stage or actor may serve as a module heading when it is
source-defined. Its child still states what that category regulates, what the
stage reaches or what the actor undertakes.

For a multi-group field, write one visible total heading when the page would
otherwise look like several unrelated cards. Example:

```text
- 统一服务体系覆盖完整业务链
  - 资源组织
    - 目录、质量与授权规则共同形成可管理的资源入口
  - 可信使用
    - 身份、权限与审计共同约束受控使用
  - 服务交付
    - 标准接口与交付流程把可用资源转化为可验证服务
```

This example is intentionally domain-neutral. Replace every object with the
verified objects from the current source; never promote example vocabulary into
a global rule.

### 3.3 Relation grammar

Before finalizing visible modules, classify the page's primary relationship:

| Relation grammar | Level-2 units answer | Level-3 evidence shows |
| --- | --- | --- |
| Classification | What independent parts jointly cover the declared scope? | Distinct proof for each part |
| Flow / causal chain | What happens at each step? | Input, action, output, handoff, condition |
| Convergence | Which independent inputs jointly support the result? | Contribution of each input |
| Mapping | Which source corresponds to which target or use? | Both endpoints and correspondence |
| Comparison | What differs under one criterion? | Criterion, difference, condition |
| Governance / boundary | What requirement or control protects the result? | Governed object, limit, enablement or verification |

Do not render a flow as a peer classification, convergence as a staged process,
comparison without a shared criterion or mapping without both endpoints.

### 3.4 Mandatory onscreen structure-projection pass

Execute after `full_copy` is stable:

1. Lock the invariant logic skeleton: conclusion, argument order, decisive
   evidence, material conditions and relation grammar.
2. Select arguments before shortening wording.
3. Project each retained argument into an independently intelligible module.
4. Project decisive proof into child details.
5. Preserve direction, trigger and landing for non-parallel relationships.
6. Compare onscreen with full copy by semantic role, not word overlap.
7. Flatten the visible page and reconstruct `conclusion → argument → evidence`.
8. Rewrite the full projection when a child proves a different claim, a peer
   changes dimension or a relationship becomes unreadable.

A text-similarity score may flag a review candidate. It cannot prove that a
paraphrase is unsupported.

### 3.5 Detail grammar

`标签：内容` is an optional compact grammar for a direct evidence detail. Use it
only when the visible parent already supplies the complete proposition and the
label declares the child's evidence role.

Good generic forms:

- `覆盖范围：目标对象的完整生命周期`
- `适用条件：授权完成且安全策略生效后`
- `责任主体：经批准的运营单位`
- `研制对象：参考架构的实施细则`

Weak forms:

- `建设依据：相关政策`
- `推进方式：协同实施`
- `主要内容：若干事项`

A standard number, document title, acronym or category name identifies evidence
but does not explain what it establishes. Prefer a complete relation such as
`方法标准规定编制原则、程序和格式：提供统一编制依据` over a bare standard
identifier, and `信息模型定义交换语义：支撑跨系统信息交换` over a list of
acronyms.

### 3.6 Strength, status and modality

Before rewriting a material statement, classify its source status. Preserve the
difference among:

- existing fact;
- achieved result;
- stated target;
- planned task;
- recommended action;
- optional action;
- conditional action;
- open question.

Do not rewrite `建议建立` as `已经建立`, `可采用` as `必须采用`, a planned task as
an achieved result or one actor's responsibility as a group-wide obligation.

When status is represented by typed Foundation fields, those fields govern.
Lexical status markers can support Critic review but do not constitute a blocking
semantic proof by themselves.

### 3.7 Relationship, time and density

A relationship claim shows both endpoints and its action. Spatial proximity does
not establish causality, mapping, hierarchy or sequence.

For a staged path, show the trigger or applicable period and the new state reached
at each stage. Dates remain attached to the source matter that owns them; one
schedule cannot be reassigned to another object.

For dense pages, distinguish conclusion, primary structure, decisive visible
proof and lower-priority complete evidence. Reduce rank, revise scope or split the
page instead of shrinking every line or truncating protected meaning.

### 3.8 Speaker notes

Speaker notes use complete spoken language. They do not mention page production,
review instructions, hidden metadata or how the author constructed the slide.

Each note adds at least one role absent from the visible layer:

- why the evidence supports the conclusion;
- subordinate evidence intentionally omitted onscreen;
- a non-material boundary or context;
- an audience focus;
- a natural handoff to the next business question.

Material conditions that change strength, responsibility, timing or applicability
remain visible rather than living only in notes.

### 3.9 Mandatory supporting-field construction pass

Execute this pass for every analytical content page.

1. **Mission ownership method.** Start from the approved Deck Plan question and
   restate one page duty with one decision-bearing verb.
2. **Core-answer method.** Answer the mission directly with the business object,
   supported judgment/action, status and material boundary.
3. **Argument-topology method.** Choose the smallest topology that proves the
   answer: directed chain, parallel grouping, convergence, mapping, governance
   chain, roadmap or bounded decision package. `argument.pattern` names that
   topology; every `argument.chain` node has one semantic role.
4. **Visual-structure method.** Project the verified topology into
   `visual_thesis` and atomic `relationships`. Each edge carries one source
   object, one target object and one connecting action.
5. **Speaker-note increment method.** Choose the note's incremental role before
   writing and delete sentences that only repeat visible copy.
6. **Cross-field reverse test.** Read only
   `mission → core_message → argument → visual_thesis/relationships → speaker_notes`
   and reconstruct the audience question, answer, proof topology, visible
   direction and spoken increment.

Critic repeats these methods independently. Deterministic checks may enforce field
presence, registered topology, IDs, provenance and explicit structure, but they
do not replace semantic Critic judgment.

## 4. Review and delivery

### 4.1 Whole-deck Critic

After all pages are drafted, review the deck as one argument system:

1. Preserve status and modality across every audience layer.
2. Give every repeated fact a distinct argument role or remove the repetition.
3. Keep peer dimensions and evidence depth comparable.
4. Make codes, abbreviations and formal names self-readable when visible.
5. Anchor staged paths with trigger/period and new state.
6. Layer dense evidence and revise page scope when needed.
7. Expose relationship actions, not only related objects.
8. Make conclusion pages state what the synthesis resolves and what follows.
9. Ensure speaker notes add incremental value.
10. Recheck adjacent-page boundaries after every local rewrite.
11. Reconstruct `claim → argument → evidence` for every analytical page.
12. For every Pyramid page, verify answer-first order and evidence ownership.
13. For every MECE grouping, test one plausible overlap and one plausible missing
    item against the declared universe.
14. For every SCR sequence, verify the complication is source-supported before
    the response.
15. For every mapping, comparison, roadmap, convergence or governance page,
    verify the visible grammar matches the asserted relation.
16. Check each recommendation and forward path against its strongest material
    condition or reversal boundary.
17. Hide visual layout and reread headings and details as plain text; the semantic
    hierarchy must survive.
18. Compare final conclusions with module provenance and typed Foundation roles,
    not with a global keyword list.

### 4.2 Deterministic boundary

Deterministic code runs after the generative pass. It may block when it can prove
one of the following:

- schema or ID invalidity;
- missing or out-of-scope source references;
- invalid provenance target/cardinality;
- structured evidence-role incompatibility;
- loss or reassignment of protected exact numbers, dates, actors, conditions or
  other explicit payload;
- malformed or PLAN-unapproved structured relationship edges;
- internal-only evidence exposed to an external audience;
- explicit delivery-cleanliness or delivery-policy violation;
- artifact synchronization or locked-text failure.

The following are review signals unless backed by structured evidence:

- character count or paragraph count;
- n-gram/text similarity;
- generic subject, actor or predicate vocabulary;
- lexical status/modality markers;
- progression, gap, optionality or causality word lists;
- visible-density counts;
- inferred bare-label or incomplete-sentence detection;
- relation-visibility keywords.

Unknown deterministic findings remain fail-closed until classified in the central
rule registry. A finding may be downgraded only with an explicit registry entry
that records kind, severity, scope, confidence, owner and rationale.

### 4.3 Revision

For revisions, rewrite from the semantic brief rather than patching onscreen copy
line by line unless the user requests a literal wording correction. If the
approved page scope or structured topology is wrong, repair the smallest upstream
contract first.

Do not add a new global keyword, customer name, industry term, project phrase or
historical accident sentence to fix one regression. Preserve the regression as a
benchmark input and fix the general contract, provenance model or Critic method.

### 4.4 Completion

An audit result proves compliance with a bounded deterministic contract; it does
not prove authorship or analytical quality. Report **最终脚本已生成** only after the
requested scope has undergone AUTHOR, Critic and rewrite and the authoritative
`dist/final-script.md` passes all required deterministic checks.
