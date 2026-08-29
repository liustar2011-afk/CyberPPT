---
name: cyberppt-script-workflow
description: Natural-language router for CyberPPT-Script. Generate or revise PPT scripts from formal source materials while preserving source chapter structure by default and allowing source-supported analytical deepening inside that structure. Never require the user to know internal stages, schemas, or CLI commands.
---

# CyberPPT Script Engine — Natural-Language Workflow

## 1. Routing principle

The source controls content boundary and default chapter order. The engine controls semantic understanding, analytical deepening, page decomposition and PPT expression.

Do not reply by asking the user to choose an internal stage when the route can be inferred from the request and current project artifacts.

Read:

1. `AGENTS.md`;
2. `docs/SOURCE_FIDELITY_AND_ANALYSIS.md`;
3. the stage Skill needed for the current route.

## 2. New source-to-script

Internal route:

`UNDERSTAND -> PLAN -> Gate A -> AUTHOR -> CRITIQUE -> REWRITE -> DELIVER`

Automatically:

1. scaffold `projects/<slug>/` and retain source files;
2. extract/index source structure when possible;
3. build a Foundation with atomic facts, explicit relations and supported inferred relations;
4. preserve source chapters by default and plan PPT pages within that structure;
5. present **脚本规划待确认**;
6. after ordinary approval language, author the complete script;
7. run Critic, rewrite, deterministic audits and delivery validation;
8. report **最终脚本已生成**.

For new planning work, PLAN writes a genuinely lightweight `deck-plan.json`
v2 lean containing only deck purpose, chapter grouping, page allocation,
tentative topic titles, page questions/missions and source boundaries. It must
not pre-author page judgments, content modules, evidence dispositions, onscreen
contracts, visual relations or speaking threads. AUTHOR writes the complete
page argument before selecting onscreen information; high-risk pages compare
judgment-led and evidence-led candidates and keep only the rewritten winner.
These are authoring passes inside the existing three authority artifacts. They
do not create a Content Plan, checkpoint, gate receipt or review manifest.

### AUTHOR execution model

`AUTHOR` is a generative agent stage. It is not a deterministic transformation
from `deck-plan.json` fields to Markdown, and it is not completed by passing a
schema, lint or source-coverage audit.

The current main agent is the AUTHOR executor. There is no separate AUTHOR
Skill, CLI command, deterministic author generator or project-specific author
script to invoke. After the planning gate is approved, the current main agent
must perform the reading, judgment, candidate comparison, writing, Critic and
rewrite itself before it runs deterministic checks. Merely loading this Skill,
creating a schema-valid file, copying PLAN fields, or reporting audit success
does not execute AUTHOR.

The author agent loads the document thesis and table of contents once per deck,
then reads the target page mission, source prose bound by that page's
`source_refs`, adjacent-page scope and approved evidence boundary. Critic and
Rewrite reuse this page semantic brief; they do not rerun UNDERSTAND or reread
unrelated source sections. The author independently decides what a
silent reader must understand, which facts deserve visible weight, how related
facts should be merged, how the page should be written, which business
relationship must become visually legible, and how the presenter should explain
the argument aloud. If the inherited
module grouping is semantically invalid, it returns to PLAN and repairs the
smallest affected page contract before writing.

Every deck defaults to `deck.delivery_mode: self_read`. The author may use
`presented` only when the user explicitly requests a presenter-led, sparse deck.
For `self_read`, each content page must close its own reading loop: identify the
topic, state the page judgment, explain the evidence or reasoning, and retain the
facts, scope, conditions or results needed to understand it without narration.
Treat `core_message` as the page's semantic authority: it states what the page
means. Treat `onscreen` as the reader-facing expression of that authority: its
headings, leads and evidence may decompose or paraphrase the judgment, but the
whole visible composition must stay centered on it. Page-planning labels,
author self-talk, review language and relationship-construction notes belong in
neither field.

Use `core_message` to organize `full_copy`, then restructure the bound source
prose without turning it into a summary. `full_copy` is the semantic-preserving
layer: it keeps the source's core facts, named actors, formal documents,
implementation status, task strength, dates and numbers, responsibilities,
conditions, boundaries and explicit conclusions, while improving their
hierarchy and reading order. Do not replace stronger source statements with
author-created dimensions such as “建设内容、阶段进度、技术规则”, or collapse
an issued policy, fixed milestone, formed technical document or assigned
responsibility into a generic arrangement. AUTHOR may rewrite, reorder and
merge repetition inside the page's `source_refs` boundary, and may omit only
subordinate material that does not support the page conclusion. Those refs
define available evidence, not a requirement to reproduce every source word.

AUTHOR must make at least one explicit editorial selection either while writing
`full_copy` or while projecting it into `onscreen`. The onscreen layer is the
latest mandatory selection point: keep the core conclusion and only the decisive
evidence needed to express it. Never produce onscreen copy by proportionally
shortening every full-copy paragraph or retaining one bullet for every cited
source detail.

When a content page carries a long multi-step argument, write `full_copy` as
substantive paragraphs that expose the reasoning hierarchy. Each paragraph must
advance a distinct part of the argument: establish the conclusion, supply its
necessary basis, explain the relationship, state a material boundary or
implication, or provide clearly subordinate context. Default to judgment-first
paragraphs. When the source already states a strong status, requirement,
responsibility or conclusion, use that source judgment as the paragraph opening;
do not weaken it into an abstract dimensional summary. Then use “一是、二是、三是”
for genuinely parallel evidence, or the connector that matches the source's
actual causal, temporal or conditional relation. A paragraph that only inventories actors, categories, dates or tasks has
not established a reasoning level. A topic sentence that merely says a task is
more concrete, a requirement is clearer or a subject is important also fails:
the opening sentence itself must state what has been established, changed or
concluded. Short or genuinely simple narrative pages may
remain a single paragraph; do not manufacture a fixed module count. Organize
reader-facing copy as a semantic anchor, a complete core statement and necessary
details. Module headings must carry business meaning by stating the object and
its action, status, role or judgment; child lines provide evidence, explanation
and qualifications. Prefer claim headings that state who has established, provides, lacks
or must do what. Do not coin official-sounding group names by joining an actor
or scope with an abstract noun, such as `国家统一基础`, `行业专业基础`, `国家坐标`
or `任务落点`, unless the source explicitly defines that exact term and a silent
reader can understand it without author explanation. Lists and numbers must state why they are grouped and what they
establish. Compression must preserve the object, predicate or action, and any
material qualifier. Do not shorten copy into vague slogans, unexplained category
labels or presenter cues.

`标签：短语` is a surface grammar for compact onscreen detail lines only. Here,
"phrase" means removing dispensable function words and terminal punctuation
while retaining the business object, action, relationship and material
qualifiers. It never authorizes label-only `full_copy` topic sentences,
label-only module headings, or semantic fragments that require the reader to
guess the missing predicate.

Complete semantics also requires the exact business matter. Never rely on the
page title, a previous paragraph or a generic subject to supply the missing
object. Headings such as `国家已明确建设内容`, `项目将推进相关工作`,
`研究形成三项成果` and `后续推进四项工作` remain incomplete until they
name the national deployment, the project, the actual成果 or the work items.
Use a specific subject such as `国家数据基础设施建设部署`, `中电联先行先试项目`
or `本项标准体系研究` and state the corresponding object in the same sentence.
Avoid umbrella objects such as `电力行业能力建设`, `项目相关能力` or
`后续有关工作` when the source provides the actual capabilities, tasks or work
items. Name those objects directly; a broader author-created category must not
expand the actor's source-stated responsibility.
When the source defines an official project level, task name, capability name
or responsibility, retain that exact context in the paragraph's topic sentence
before any higher-level grouping. An author-created umbrella term may summarize
only after the exact source objects have been stated; it cannot replace them.

Deterministic code runs only after the generative pass. Its role is to detect
source loss, proposition drift, unsupported relations, broken boundaries and
delivery-format defects. It must never create onscreen copy by abbreviating
source bullets, splitting one source sentence into cards, or filling one output
field from each PLAN field. It must not synthesize `visual_thesis` by copying the
core message or synthesize `speaker_notes` by concatenating module headings and
items. An audit result proves compliance with a bounded
contract; it does not prove authorship or reading quality.

For revisions, the author agent rewrites the page from its semantic brief. It
does not patch the previous onscreen copy line by line unless the user has
explicitly requested a literal wording correction.

The agent may report **最终脚本已生成** only after this generative pass has
actually rewritten the complete requested scope and the resulting authoritative
`dist/final-script.md` has passed the required deterministic checks.

## 3. Re-plan

Distinguish two cases.

### Expression / pagination re-plan

Examples:

- `重新做分页`
- `第3章页数太多`
- `这几节怎么合页更好`
- `整套PPT表达逻辑再优化`

Keep `source_structure_mode: preserve`. Re-plan page split/merge, chapter-internal logic, analysis model and page arguments.

### User-authorized source restructuring

Examples:

- `把合作机会提前到第二章`
- `重新安排五章顺序`
- `删掉建设背景，重点讲合作`

Set `source_structure_mode: user_authorized_restructure` and record `user_authorized_cross_chapter` only where the request requires it.

Do not infer restructuring permission merely from a request for a better PPT.

## 4. Continue

Identify the active project and run `cyberppt-script status projects/<slug>`. Resume from the next unresolved gate. Approval language after an approved plan authorizes whole-deck writing; never ask the user to say an internal stage name.

## 5. Targeted page edit

Read:

- target page and adjacent pages;
- corresponding deck-plan entry;
- `source_scope`;
- relevant Foundation facts/relations/boundaries;
- `analysis_basis` where present.

Preserve source chapter boundaries unless the requested edit explicitly authorizes a structural change.

## 6. Whole-deck review / rewrite

Run Critic + Rewrite against Foundation, plan and current script. Review source structure, inference boundary, analytical depth, group-claim strength, classification/progression, optionality, visibility, compression loss and formal register.

Do not expose Critic self-dialogue. Return only the rewritten result and a concise summary of material changes when useful.

## 7. Planning gate

Show a readable **脚本规划待确认** containing:

- source chapter structure to be preserved;
- planned page allocation by chapter;
- each page's tentative title, question, mission and source boundary;
- split/merge decisions that materially change Word-to-PPT projection;
- inferred relationships or source conflicts that merit user attention;
- any restricted/internal material requiring an exposure decision.

Do not dump internal JSON by default.

Run `cyberppt-script review-plan <deck-plan.json> <foundation.json>` and present
its Markdown reading strip at this gate. The command is a derived review view and
must not create another authoritative artifact or approval state. For internal
and mixed audiences, apply the internal-expert voice check: enterprise operating
topics remain valid, while external-consultant address and viewpoint are rejected.

## 8. Stage 02 boundary and formal handoff

Stage 01 owns the three authoritative script artifacts:

- `script/foundation.json`;
- `script/deck-plan.json`;
- `script/dist/final-script.md`.

After the final script is locked, Stage 02 remains in the CyberPPT repository and
has one formal orchestration entry:

`.venv/bin/python3 -m cyberppt final-script-pages --production-build ...`

`final-script-pages` consumes the locked final script and the current Stage 02
handoff/visual contracts before running image generation, image-text audit and
the requested PPTX assembly branch. For high-fidelity editable reconstruction,
use `--production-mode image-to-editable-svg` with the registered `editable`
assembly branch; picture and dual delivery use the same orchestrator with their
declared assembly branch. Do not call a Stage 02 adapter directly or create a
parallel image/PPTX production route.

The Stage 01/Stage 02 boundary is the locked
`script/dist/final-script.md` plus its validated handoff. Visual production may
derive runtime prompts, manifests and QA records, but it must not rewrite the
three Stage 01 authority artifacts or become a second content authority.
