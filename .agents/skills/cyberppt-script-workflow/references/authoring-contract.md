# CyberPPT AUTHOR Contract

This file is the single operational authority for `AUTHOR`, `CRITIQUE`,
`REWRITE`, targeted page revision and whole-deck script review. Read it
completely before taking any of those actions. `AGENTS.md` remains the
repository-level hard constraint and overrides this contract if they differ.

Do not copy these rules back into `SKILL.md`. The workflow entrypoint routes here;
this file owns authoring behavior.

The contract has four rule classes:

1. **Execution** — who authors and the required page sequence;
2. **Semantic foundation** — self-read completeness, source fidelity and the
   structured full-copy layer;
3. **Audience-facing construction** — onscreen selection, hierarchy, detail,
   strength, relationships, density and speaker notes;
4. **Review and delivery** — whole-deck Critic, rewrite and deterministic checks.

## 1. Execution

### 1.1 Authority

`AUTHOR` is a generative agent stage, not a deterministic transformation from
`deck-plan.json` to Markdown. The current main agent performs reading, judgment,
candidate comparison, writing, Critic and rewrite. There is no separate AUTHOR
Skill, CLI, rules-based generator or project-specific author script.

Passing schema, lint or source-coverage checks does not execute AUTHOR and does
not prove reading quality. Deterministic checks run after generative writing.

### 1.2 Required page sequence

Run these steps in order for every content page:

1. **Load the page brief.** Load the document thesis and table of contents once
   per deck. For the target page, read its mission, page-bound `source_refs`,
   adjacent-page boundary and approved evidence scope. Reuse this brief in Critic
   and Rewrite; do not rerun whole-document UNDERSTAND.
2. **Lock source meaning.** Record the strongest explicit conclusion and protected
   payload: actor, source predicate, action or status, formal document or task and
   its document type, number, date and owning matter, responsibility, condition,
   boundary and claim strength. Separate source-explicit relationships from
   source-supported editorial inference before drafting.
3. **Author the page conclusion.** `core_message` states what the page means and
   organizes the entire page. It contains no planning label, author self-talk,
   review language or relationship-construction note.
4. **Write semantic-preserving full copy.** Reorganize source prose into a
   judgment-first hierarchy. Preserve protected payload and omit only subordinate
   material that does not support the page conclusion.
5. **Make an editorial selection.** Select the decisive visible argument. Do not
   proportionally shorten every paragraph or keep one bullet per source fact.
6. **Build visible hierarchy and close semantics.** Apply `one page, one
   conclusion; one level, one question; peers, one dimension; children, added
   evidence; different levels, visible relationships`. A normal content module
   heading states a complete judgment; the taxonomy exception in 3.2 applies to
   formally defined categories, stages and actors. Every detail is a complete proposition or
   `语义标签：语义完整的短语或说明`, retaining its action, relation, object and
   material qualifier.
7. **Check peer logic.** Visible siblings share one comparison dimension and
   comparable explanatory depth. Attach supplementary facts, certifications and
   evaluation results to the actor or main claim they qualify.
8. **Check strength and scope.** Compare `core_message`, `full_copy`, headings,
   details and `speaker_notes` with the source brief. Preserve status, modality,
   responsibility and page boundary in every layer.
9. **Expose the business relationship.** When the conclusion claims mapping,
   alignment, coordination, conversion, support or a closed loop, show both ends
   and the action between them. For staged paths, show the applicable year or
   trigger and the new state reached.
10. **Write incremental speaker notes.** Add explanation, subordinate evidence,
    a secondary condition that does not change the visible claim, an audience
    focus or a natural transition. Material conditions remain onscreen. Do not
    recite the visible modules in sequence.
11. **Critique and rewrite the whole page.** Compare judgment-led and
    evidence-led candidates for high-risk, dense, peak or conclusion pages. Keep
    only the rewritten winner. A failed conclusion, hierarchy or selection causes
    a whole-page rewrite, not line-by-line patching.
12. **Run whole-deck Critic, then deterministic checks.** Review repeated facts,
    chapter flow, density, conclusion synthesis and adjacent-page scope before
    lint, audit and delivery.

## 2. Semantic foundation

### 2.1 Self-read page contract

Every deck defaults to `deck.delivery_mode: self_read`. Use `presented` only when
the user explicitly requests a presenter-led sparse deck.

A self-read content page closes its own reading loop: it identifies the topic,
states the judgment, explains the evidence or reasoning, and retains the facts,
scope, conditions or results needed without narration. `onscreen` is the
reader-facing expression of `core_message`; headings, leads and evidence may
decompose or paraphrase it, but the visible composition stays centered on it.

Taxonomy codes, acronyms and numbers that carry a core relation appear with their
business names and roles on the same page. Previous-page memory may support
navigation but never completes the current page's meaning.

### 2.2 Source fidelity and full copy

`full_copy` is the structured semantic source consumed by `onscreen`, not a
reader-facing prose transcript and not a requirement to compress every source
sentence proportionally. It retains the source's core facts,
named actors, formal documents, implementation status, task strength, dates and
numbers, responsibilities, conditions, boundaries and explicit conclusions while
improving hierarchy and reading order.

Onscreen consumption is complete when the visible layer carries the paragraph's
leading judgment, the decisive facts or relations that make it understandable,
and every condition or qualifier that materially changes its strength. It may
omit subordinate examples, repeated evidence and supplementary proof. It fails
when it keeps only the named objects but drops what the paragraph says about
them, or when it drops one input, relation or condition that the page conclusion
depends on. Critic must compare `full_copy` and `onscreen` by semantic role, not
by word overlap or item count.

Do not replace strong source statements with author-created dimensions such as
“建设内容、阶段进度、技术规则”, or collapse an issued policy, fixed milestone,
formed technical document or assigned responsibility into a generic arrangement.
AUTHOR may rewrite, reorder and merge repetition inside the page's `source_refs`
boundary. Those refs define available evidence, not an obligation to reproduce
every word.

Complete semantics requires the exact business matter. A child may inherit a
shared subject or action only from its direct, visible structural parent and only
when its label declares the semantic role. Do not rely on the page title, a
previous paragraph, an adjacent module, a previous page or a generic subject to
supply a missing object.
Headings such as `国家已明确建设内容`, `项目将推进相关工作`, `研究形成三项成果`
and `后续推进四项工作` remain incomplete until they name the national
deployment, project, outputs or work items. Prefer specific subjects such as
`国家数据基础设施建设部署`, `中电联先行先试项目` and `本项标准体系研究`.

Avoid umbrella objects such as `电力行业能力建设`, `项目相关能力` and
`后续有关工作` when the source names the actual capabilities, tasks or work
items. An author-created umbrella term may summarize only after the exact source
objects are stated; it cannot expand an actor's responsibility.

Preserve the identity of formal instruments. A policy guideline, action plan,
management measure, trial technical document, national or industry standard,
group standard, initiative and task statement remain distinct document types.
Do not normalize them into an official-sounding collective term such as
`国家规则`, `统一规范` or `政策标准` merely because they all inform the page.
When grouping is useful, use a descriptive proposition that names the covered
types and keep each instrument's actual action: for example, the guideline sets
the deployment, trial technical documents specify technical requirements, and
GB/T 13016 provides the standard-system construction method.

Bind every predicate to the source object that owns it. A maturity statement,
evaluation result, implementation status or allowed action for one enterprise,
domain or standard cannot become a group-wide predicate. In particular, a
source instruction to inherit and extend one information-model standard does not
mean that all existing industry standards can be directly inherited.

Analytical enhancement remains allowed inside the evidence boundary. Preserve
its origin in audience language: use forms such as `由此表明`, `本研究据此形成`
or `可形成` when the relation is inferred rather than directly stated. An
inferred mapping, loop, conversion path or consequence cannot be phrased as a
source-defined term, an operating mechanism or an achieved result.

### 2.3 Full-copy hierarchy

Each substantive paragraph advances one part of the argument: conclusion,
necessary basis, relationship, material boundary, implication or subordinate
context. Default to judgment-first paragraphs. A paragraph that only inventories
actors, categories, dates or tasks has not established a reasoning level.

When a paragraph contains genuinely parallel facts, tasks, stages or results,
use:

`paragraph core conclusion → numbered sub-conclusion → supporting detail`

The sentence before the enumeration states what the paragraph establishes. Each
“一是、二是、三是” begins with a concise, independently intelligible
sub-conclusion, then unfolds the source-grounded document, actor, action, scope,
number, date or result. Prefer `建设任务覆盖四大方向、八个环节和三类建设载体`
over `建设内容`, and `建设进度按照2026年、2028年和2029年三个节点分阶段推进`
over `阶段安排`.

Purposeful restatement is allowed when it provides navigation first and evidence
second. Mechanical repetition adds no value. Do not force numbered enumeration
onto a short paragraph, a single causal chain or facts that are not parallel.

Full copy may also use `语义标签：语义完整的短语或说明` beneath a paragraph
judgment when that form exposes the evidence roles more clearly for later
onscreen selection. Use numbered sub-conclusions for parallel arguments and
labelled details for attributes, evidence, scope, actions, conditions or results;
do not force either grammar onto every paragraph.

## 3. Audience-facing construction

### 3.1 Onscreen selection

The onscreen layer is the mandatory selection point. Keep the core conclusion and
only the evidence a silent reader needs to understand why it holds. Visual brevity
never overrides source meaning, and source availability never requires equal
visible rank for every fact.

Module headings carry business meaning by stating the object and its action,
status, role or judgment. Child lines provide evidence, explanation and
qualification. Do not coin official-sounding group names such as `国家统一基础`,
`行业专业基础`, `国家坐标` or `任务落点` unless the source defines the exact term
and a silent reader can understand it without author explanation.

Lists and numbers state why they are grouped and what they establish. Compression
preserves the object, predicate or action and material qualifier. Do not shorten
copy into slogans, unexplained category labels or presenter cues.

### 3.2 Hierarchy model

Use one universal hierarchy rule:

`one page, one conclusion → one level, one question → peers, one dimension → children, added evidence → different levels, visible relationships`

Apply it through one shared semantic, syntactic and visual hierarchy. The three
content levels are stable even when the visual design changes:

1. **Page conclusion.** `core_message` answers what the page means. It is one
   complete judgment with the exact business matter, actor and source-supported
   state or action.
2. **Module judgment.** Each top-level onscreen module answers which part proves,
   explains or implements the page conclusion. Normal modules are independently
   intelligible sub-judgments; the taxonomy exception below remains available.
3. **Evidence detail.** A module's `text` or `items` answers what fact, scope,
   action, object, condition or result establishes that module. It may be a
   complete proposition or `语义标签：完整内容`.

Cause, progression, mapping, conversion and closed loops form a relationship
layer across these content levels; they are not a fourth list of equal peers.
Show both business endpoints and the action, trigger or landing between them.

- **One page, one conclusion.** Every visible element explains, proves, expands
  or implements `core_message`.
- **One level, one question.** `core_message` answers what the page means; module
  judgments answer which parts establish it; child lines answer what evidence,
  scope, action, object, condition or result establishes each module.
- **Peers, one dimension.** Siblings compare only one semantic role, such as
  actor, problem, capability, stage, task, mechanism, result or category. Method,
  input, process and result do not become equal-weight modules.
- **Children, added evidence.** A child must add a source-grounded fact, action,
  relationship, object, condition or result. Rephrasing the parent is not a new
  level.
- **Labels declare roles.** `标签：短语` is valid when the label states the child's
  role in the parent judgment and the phrase completely fills that role.
- **Different levels, visible relationships.** Cause, progression, mapping,
  conversion, closed loop and structures such as `成果 → 行动 → 价值` require an
  explicit reading direction or landing; do not render them as equal peers.
- **Taxonomy exception.** As the explicit exception to the normal complete-
  judgment heading rule, a formally defined category, stage or actor may serve as
  a module title. Its child line still states what the category regulates, what
  the stage reaches or what the actor undertakes.
- **Material conditions stay visible.** A condition that changes claim strength,
  timing, responsibility or applicability appears in the module judgment or
  detail; full copy or notes alone cannot carry it.

Use structural indentation and line breaks as the primary hierarchy markers.
Reserve the colon for a detail's `label：content` relation; do not use it to
simulate several levels in one line. A module with one unlabeled explanation may
render compactly as `module judgment：complete proposition`. When the explanation
already contains a semantic label, preserve it as a nested child:

```text
- 电力领域数据基础设施标准体系尚未形成统一框架
  - 专业分布：相关标准分散在多个专业领域
  - 层级衔接：国家、行业、团体和企业标准之间关系不明确
```

Never emit `parent：generic label：content`. A visible line carries at most one
hierarchy-bearing colon. Prefer specific roles such as `专业分布`, `层级衔接`,
`适用范围`, `推进条件` and `研制对象`; generic labels such as `具体表现`,
`主要内容`, `相关情况` and `直接影响` are allowed only when they add a real,
non-redundant semantic role that a more specific business label cannot express.
Flatten the page to plain text during Critic: if the reader cannot distinguish
the page conclusion, module judgments, evidence details and relationship layer
without color, cards or narration, the hierarchy fails.

### 3.3 Peer dimension and supplementary evidence

Before keeping a visible sibling list, identify its single comparison dimension:
actor, capability, stage, problem, task or result. Do not place an actor, a
business field and that actor's evaluation result at the same indentation level.

Attach a supplementary fact, maturity rating, certification or result to the
actor or main claim it qualifies. If it only strengthens an already sufficient
claim, keep it in `full_copy` or `speaker_notes`; retain it onscreen only when it
provides unique proof the conclusion otherwise lacks.

Peer groups use comparable explanatory depth. If one standard names its regulated
object or role, its peers cannot stop at titles alone.

### 3.4 Detail grammar and evidence payload

`标签：短语` is a valid compact onscreen grammar when the label declares a real
semantic relation and the short value completely fills that semantic slot. Valid examples include
`覆盖范围：电力数据全生命周期和全产业链` and
`推进条件：技术路线和业务模式成熟后转化`. `建设依据：国家政策` and
`推进方式：协同实施` remain abstract.

Shortness, punctuation and bullet indentation do not prove semantic completeness.
A short value may inherit the business relation explicitly declared by its label
and a shared subject or action explicitly declared by its direct visible parent
module; it may not inherit from the page title, another module, a prior paragraph
or a prior page, and it may not rely on the reader to guess an omitted action or relation. A named standard, task,
deliverable or category may therefore use `研制对象：电力数据基础设施参考架构
行业实施细则` after a parent judgment such as `第一优先级具有明确上位依据，建议
尽快启动立项`. The detached bullet `参考架构行业实施细则` fails because neither
the line nor its syntax states what is being done with that standard. If the
shared proposition cannot be stated accurately, keep the name in `full_copy` or
`speaker_notes`.

A label does not authorize a dangling modifier such as
`建设依据：以《指引》为总纲`. A line beginning with `以、基于、围绕、结合、
按照、通过、面向、依托、针对` must complete the business action or result.

A standard number, document title, framework name, initiative, institution or
category list identifies evidence but does not yet explain it. State what the
named source defines, regulates, unifies, supports, enables, requires or proves.
Prefer `编制方法：GB/T 13016规定体系表编制原则、程序和格式` over
`编制方法：GB/T 13016`, and `信息模型：DL/T 890以CIM和CIS支撑调度资源信息交换`
over `信息模型：DL/T 890、CIM、CIS`. When the source provides only a name,
keep it for traceability or omit it from the visible layer; do not invent an
effect.

### 3.5 Strength, status and modality

Protect source terms such as issued, formed, undertakes, target, planned,
recommended, provides a basis and may be connected. Check each audience layer
independently. A qualified paragraph does not license a stronger visible heading.

Do not upgrade `一定基础` to `具备条件`, `承担项目` to `进入实施`, `建议建立`
to `已经建立`, or `可衔接` to `直接继承`. Do not weaken `亟需` to `承接需求`.
Do not move evidence across page boundaries without repairing the approved scope.

Classify each material statement before rewriting it as one of four states:
existing fact, stated target, recommended action, or proposed standard direction.
Keep that state visible in its predicate. Source-table verbs such as `制定` and
`完善` describe work to be done; render them as `拟制定`, `拟完善` or
`研制方向`, not as if the standard already unifies, regulates or safeguards its
object. Likewise, `提出`, `明确构建`, `具备条件`, `提供依据`, `建议`, `推动`
and `配合` retain their own force and are not interchangeable with `已形成`,
`已进入`, `确保完成`, `已建立`, `已实现` or `直接支撑完成`.

Keep responsibility syntax explicit. After compression, the grammatical subject
of a gap, task or recommendation must still be the actor responsible for the
action. For example, when the source says the power sector has not developed
supporting implementation rules, do not recast the national technical
requirements themselves as having failed to develop those rules.

### 3.6 Relationship, time and density

If a page claims mapping, alignment, coordination, conversion, support or a closed
loop, visible copy shows both business objects and the action between them.
Proximity or parallel placement on the canvas does not establish a relationship.

When a page claims alignment with national milestones, project cadence or a
maturity path, show the applicable year or trigger and the new state reached at
each stage. `近期、中期、远期` alone does not establish alignment.

A date remains attached to the source matter that owns it. National construction
milestones, industry standard-system stages, project cadence and individual
standard schedules are not interchangeable. A cross-paragraph date mapping may
be expressed as `参照`, `衔接` or `对应国家目标` when supported; it must not turn
a national milestone into an unstated hard deadline for an industry or project.

For a page with many categories or semantic units, distinguish the conclusion,
primary structure, decisive visible evidence and lower-priority complete list.
Reduce visual rank, revise the mission or split the page when all items cannot
remain readable. Do not solve density only by shortening every line, and do not
impose a universal fixed module or character count as a substitute for judgment.
Deterministic length limits remain production constraints rather than authoring
targets. When semantically complete copy exceeds them, preserve meaning by
splitting distinct semantic roles, promoting a shared proposition into a module
lead, revising the page mission or paginating. Never pass a length gate by
truncating a protected object, action, relationship, condition or qualifier.

### 3.7 Speaker notes

Speaker notes use complete spoken language that can be read aloud or naturally
paraphrased. They do not mention “本页”“下一页”“上页”“页面设计”“审核稿” or
production instructions. Use audience-facing transitions such as
“接下来重点看……” or “在这个基础上，我们再看……”.

Notes add at least one element absent from the visible layer: why the evidence
supports the judgment, a subordinate fact omitted onscreen, a secondary condition
or boundary that does not alter the visible claim's strength, timing,
responsibility or applicability, an audience focus or a natural transition.
Material conditions remain visible. Sequentially paraphrasing every visible
module fails Critic.

## 4. Review and delivery

### 4.1 Whole-deck Critic

After all pages are drafted, review the complete deck:

1. Preserve status and modality across every audience layer.
2. Assign a distinct argument role to every repeated fact. A recurrence proves a
   new proposition such as requirement, reusable basis, framework derivation,
   role mapping or synthesis; otherwise delete or subordinate it.
3. Equalize peer dimensions and evidence depth.
4. Make codes, abbreviations and numbering self-readable.
5. Anchor staged paths with time or trigger and new state.
6. Layer dense evidence and revise page scope when needed.
7. Expose relationship actions, not only related objects.
8. Make conclusion pages state what the outputs resolve, who acts next and how
   outputs enter continued work. Do not reproduce complete prior lists.
9. Ensure speaker notes provide incremental value.
10. Review adjacent pages after every local repair so the fix does not create a
    new repetition or boundary conflict.
11. For every content page, verify that the visible hierarchy answers five
    questions: the page conclusion is intelligible alone; normal module judgments
    show how it is established and taxonomy exceptions have explanatory children;
    siblings share one dimension; each child adds a fact,
    action, relationship, object or condition; every non-parallel relationship
    has a visible direction or landing.
12. Audit formal terms and predicates across all four audience layers. Every
    policy or technical term must resolve to a source-defined term or a clearly
    descriptive grouping; every `directly`, `ensures`, `completes`, `forms`,
    `achieves`, `inherits` or `converts` claim must retain its source-supported
    actor, object, status, scope and relation basis.

### 4.2 Revision and deterministic boundary

For revisions, rewrite the page from its semantic brief. Do not patch previous
onscreen copy line by line unless the user requests a literal wording correction.
If inherited module grouping is semantically invalid, repair the smallest affected
PLAN contract before writing.

Deterministic code runs after the generative pass. It detects source loss,
proposition drift, unsupported relations, broken boundaries and format defects.
It must not create onscreen copy by abbreviating bullets, split one source sentence
into cards, fill output fields mechanically from PLAN, copy `core_message` into
`visual_thesis`, or concatenate headings into `speaker_notes`.

An audit result proves compliance with a bounded contract; it does not prove
authorship or reading quality. Report **最终脚本已生成** only after the requested
scope has undergone AUTHOR, Critic and rewrite and the authoritative
`dist/final-script.md` passes required deterministic checks.
