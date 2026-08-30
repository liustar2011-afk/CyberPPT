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
   review language or relationship-construction note. Execute the mission and
   core-message methods in 3.9 before building the argument.
4. **Build the claim–argument–evidence chain.** State the independent arguments
   that establish `core_message`, then bind each argument to the source-grounded
   evidence that proves, explains or qualifies it. Apply the organising rules in
   2.8, the page-logic normalization in 2.9 and the argument-topology method in
   3.9 before prose selection.
5. **Write semantic-preserving full copy.** Reorganize source prose into a
   judgment-first hierarchy. Preserve protected payload and omit only subordinate
   material that does not support the page conclusion. Draft from the paragraph
   blueprint established in 2.9, then execute the full-copy structure pass in
   2.10 before selecting onscreen information; do not discover the page logic
   while writing prose.
6. **Set the reading form and density boundary.** Before selecting visible copy,
   declare the page's primary reading form, one visible conclusion, its
   top-level information roles and the decisive proof retained for each role.
   Apply the density-and-heading preflight in 2.6 before drafting modules.
7. **Make an editorial selection and project the structure.** Select the decisive
   visible argument, then execute the mandatory onscreen structure-projection
   pass in 3.3. Do not proportionally shorten every paragraph, keep one bullet
   per source fact or rediscover a different page logic during compression.
8. **Build visible hierarchy and close semantics.** Apply `one page, one
   conclusion; one level, one question; peers, one dimension; children, added
   evidence; different levels, visible relationships`. A normal content module
   heading states a complete judgment; the taxonomy exception in 3.2 applies to
   formally defined categories, stages and actors. Every detail is normally a
   complete proposition. A `语义标签：语义完整的短语或说明` is permitted only for a
   direct evidence detail whose role is already clear from its parent; it cannot
   replace the main clause of a module or paragraph. A normal module heading
   must carry a short complete judgment. In the compact `标题：短句` form, the
   heading carries the core subject and predicate; the text after the colon only
   adds scope, condition, result or supporting detail and the whole line must
   remain natural when read aloud. Noun-only headings such as `建设框架`、`治理目标`
   and `编制方法` require rewriting when they carry the page's main judgment.
9. **Check subject and argument continuity.** Before keeping a paragraph or
   visible module, identify its primary audience question, named actor or actor
   group, and the actor's role. Apply the continuity check in 2.7. Split a
   change from condition or demand to response or action into a new reasoning
   unit unless one explicit relationship carries the transition.
10. **Check peer logic.** Visible siblings share one comparison dimension and
   comparable explanatory depth. Attach supplementary facts, certifications and
   evaluation results to the actor or main claim they qualify.
11. **Check strength and scope.** Compare `core_message`, `full_copy`, headings,
   details and `speaker_notes` with the source brief. Preserve status, modality,
   responsibility and page boundary in every layer.
12. **Expose the business relationship.** When the conclusion claims mapping,
   alignment, coordination, conversion, support or a closed loop, show both ends
   and the action between them. For staged paths, show the applicable year or
   trigger and the new state reached. Execute the visual-structure method and
   atomic relationship-edge test in 3.9.
13. **Write incremental speaker notes.** Add explanation, subordinate evidence,
   a secondary condition that does not change the visible claim, an audience
   focus or a natural transition. Material conditions remain onscreen. Do not
   recite the visible modules in sequence. Execute the speaker-note increment
   method in 3.9.
14. **Critique and rewrite the whole page.** Reconstruct the page logic using
   the role and ownership tests in 2.9, the paragraph hierarchy tests in 2.10 and
   the onscreen projection tests in 3.3, then execute the cross-field reverse
   test in 3.9. Compare judgment-led and evidence-led candidates for high-risk,
   dense, peak or conclusion pages. Keep only the rewritten winner. A failed
   question, chain, paragraph role, boundary, conclusion, hierarchy, projection,
   field role or selection causes a rewrite from the earliest failed step, not
   line-by-line patching.
15. **Run whole-deck Critic, then deterministic checks.** Review repeated facts,
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
requirement to compress every source sentence proportionally. It retains the
source's core facts,
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

Full copy may use `语义标签：语义完整的短语或说明` beneath a paragraph judgment
only when that form exposes an evidence role more clearly than a natural
sentence. It must remain subordinate to complete prose and must not turn a
paragraph into a sequence of fields. Use numbered sub-conclusions for parallel
arguments and limited labelled details for attributes, evidence, scope, actions,
conditions or results; do not force either grammar onto every paragraph.

### 2.4 Judgment-led prose quality

`full_copy` and `onscreen` serve different reading depths, but they share one
authoring standard: each must help the audience acquire a specific business
understanding, not merely retain a complete inventory of source materials. Apply
the following tests to both layers before delivery:

1. **Audience takeaway.** A reader must be able to state, in one sentence, what
   has changed, what it means, or what decision follows. A page title names a
   topic; it does not substitute for this judgment.
2. **Judgment before evidence.** Lead with the business conclusion, then use a
   document, standard, date, capability, task or example as evidence for it.
   Formal instruments must not become the grammatical subject of a page merely
   because they are easy to cite.
3. **Natural professional syntax.** A module judgment and every full-copy
   paragraph must remain intelligible when read aloud without indentation,
   colour or visual layout. Do not use repeated label-plus-list grammar, pipes,
   stacked modifiers or generic verbs such as `支撑`、`推进`、`形成`、`提升` unless
   their actor, object and material effect are explicit.
4. **Meaningful relationship.** A substantive page shows the relationship that
   matters to the audience: for example condition to outcome, gap to impact,
   requirement to decision, scenario to standard demand, or output to the next
   action. Parallel facts alone do not establish professional analysis.
5. **Decisive selection.** Keep a visible fact only when removing it would
   weaken the reader's understanding of the judgment, its strength, or its
   action implication. Move supporting inventories and non-decisive citations
   to full copy, notes or a genuine taxonomy table. For a taxonomy page, add a
   readable guide explaining what the classification distinguishes or governs.

These are generative authoring and human-review criteria, not a fixed character
count, a mandatory stock sentence, or a deterministic score. Do not satisfy the
tests by replacing one bureaucratic template with another.

### 2.5 Page writing framework selection

Every content page uses two composable expression layers. The layers guide the
reading order of `core_message`, `full_copy` and `onscreen`; they do not add
unsupported facts, force visible framework jargon, or require every method on
every page.

1. **Universal organising framework.** Use claim–argument–evidence on every
   page. Apply Pyramid when the reader needs the answer before its independent
   reasons; apply MECE when the arguments or evidence require a closed,
   non-overlapping grouping; apply SCR when the page or chapter needs to move
   from shared situation through tension to a supported response. These methods
   organise how the author reasons and writes.
2. **Relationship grammar.** Select a grammar when the page must make a
   particular business relationship visible. **Mapping** shows input,
   correspondence rule and business use. **Roadmap** shows start condition,
   stages, newly reached states and feedback or gates. **Governance chain**
   shows actor, mechanism, collaborating parties or resources, and the result
   the mechanism is intended to secure. A formal classification states its
   shared dimension and reader's guide. These grammars determine the relationship
   the reader sees; they can be organised by Pyramid, MECE or SCR.

Examples: a roadmap may use a Pyramid claim followed by stage arguments and
stage evidence; it may also use MECE to test whether each scoped work item has
one stage home. A mapping may use a Pyramid claim to state why the correspondence
matters and MECE to group inputs or outputs. A governance chain may use SCR to
explain why the mechanism is needed. The author selects the smallest combination
that makes the judgment and relationship readable.

At deck level, use SCR as an internal-report storyline when it fits: establish
the shared operating situation, isolate the management-relevant tension, then
present the bounded resolution and its implementation conditions. In the current
project, national deployment, enterprise practice and usable foundations form
the situation; the five-dimensional gap is the complication; the framework,
priorities, roadmap and safeguards form the resolution. Retain the approved
source chapter order and use each page's selected framework inside that arc.

### 2.6 Density and heading preflight

Perform this preflight before drafting `full_copy` or `onscreen` for every
content page. Its purpose is to prevent a page from accumulating valid facts
that answer different audience questions, then relying on late compression or
visual layout to make them fit.

1. **Declare one relationship grammar and its organising method.** Select the
   visible relationship grammar—ordinary argument, classification, mapping,
   roadmap or governance chain—then state whether Pyramid, MECE or SCR governs
   the reading order. A page may add a small evidence table or timeline inside
   its grammar. It may not ask the reader to decode several equal-weight
   relationship grammars at once.
2. **Set the visible information budget.** A normal page contains one visible
   conclusion and two to four top-level information units. This is a default
   authoring budget, not a universal production limit. A formally defined
   taxonomy, roadmap or mapping may exceed it only when the shared dimension,
   reading direction and reader's guide are visible before the inventory.
3. **Separate independent information roles.** Context, diagnosis, requirement,
   task, condition, output and next-step path are distinct information roles.
   When peer modules combine more than two of these roles, split the page or
   express their supported relationship as a chain, map, roadmap or governance
   flow. A vertical list cannot carry a mixed role structure merely because each
   item is source-faithful.
4. **Keep only decision-bearing proof visible.** For every top-level unit, state
   the evidence that makes the page conclusion understandable. Move named
   documents, standard numbers, examples and complete inventories to full copy
   or notes unless their visible absence would weaken the conclusion, its
   strength or its action implication. A taxonomy retains its complete list only
   when the list itself is the audience's required output.
5. **Write one judgment per heading.** A normal module heading has one subject,
   one principal predicate and one reader question. Two independent actions,
   conclusions, dates or transitions in the same heading signal that one must
   become a child, a sibling module or a separate page. Taxonomy names remain
   available under the exception in 3.2, with an explanatory child line.
6. **Shorten by restructuring before wording.** First promote the shared
   subject, condition or conclusion into the page lead. Then retain the unique
   judgment in each module heading. Then move supporting scope, citations and
   secondary conditions into evidence detail. Split the module or page whenever
   two independent judgments remain. Never shorten by removing a protected
   object, action, relation, condition or qualifier.
7. **Use length only as a review signal.** A heading whose plain-text reading
   contains several conjunctions, several actions, a date plus a formal
   instrument, or more than one independent clause requires this preflight
   again. Character counts may flag a review candidate; they cannot certify
   clarity or force truncation.

The author records this preflight in working judgment only. It creates no new
project artifact, authoring field, approval record or deterministic gate.

### 2.7 Subject and argument continuity

Before prose selection, trace each paragraph and onscreen module through three
internal dimensions: the audience question it answers, the actor or actor group
it describes, and that actor's role. This trace remains author working judgment;
it creates no page field or project artifact.

1. **One reasoning unit, one primary question.** A paragraph or visible module
   may explain one condition, demand, task, response, mechanism, result or
   boundary. When copy moves from a problem or demand to the study's response,
   from a policy requirement to an industry task, or from an existing fact to a
   recommended action, begin a new paragraph or module. Keep the explicit
   relationship between the two units visible in the lead, transition or
   relation layer.
2. **Complete an actor before switching actors.** When several details concern
   the same institution, project, enterprise or standard, keep its
   decision-bearing facts together before introducing the next actor. A return
   to an earlier actor after another actor has appeared requires an explicit new
   relation, such as guidance, coordination, feedback or comparison.
3. **Order actors by source-supported responsibility.** When source material
   establishes a chain such as policy deployment, competent-department guidance,
   industry-organisation stewardship and enterprise practice, present the chain
   in that order. When source material
   does not establish authority, group actors by their stated role and avoid
   inferring an administrative rank from the institution's name alone.
4. **Keep the same continuity on screen.** A visible module that presents
   several actor-specific facts follows the same actor order as its full copy.
   Do not interleave a higher-level actor's deployment, an industry actor's
   responsibility and the higher-level actor's supporting channel as three
   interchangeable bullets. Group each actor's facts, then show the handoff to
   the next actor.
5. **Use a transition to name the handoff.** A paragraph boundary alone does
   not establish why the next unit follows. Name the supported handoff, for
   example `由此提出行业任务`、`在这一需求下`、`依托该渠道` or `验证结果再反馈`.
   Do not use a transition to conceal an unsupported inference or an unshown
   responsibility.

These rules diagnose logic order and actor continuity. They do not impose a
universal hierarchy of institutions, a mandatory paragraph count or a lexical
entity-recognition gate.

### 2.8 Claim–argument–evidence and organising principles

Before drafting prose, express the page in the internal form
`claim → independent argument(s) → source-grounded evidence`. This is an author
working map, not an additional project artifact or a request for visible
framework labels.

For every content page, execute this operating loop. Analytical, decision and
conclusion pages use all six steps. Foundation, status and formal-taxonomy pages
use steps 1, 2, 4 and 6; they do not manufacture a hypothesis, recommendation or
counterfactual absent from the source.

1. **Define the page question and universe.** Restate the page question as an
   answerable audience question. Name the source-scoped universe being examined,
   the required audience takeaway and the boundary reserved for adjacent pages.
   A page whose question is only a topic label must be rewritten before evidence
   selection.
2. **Choose one decomposition logic.** Before listing modules, choose the rule
   that makes them peers: policy-to-industry responsibility, actor role,
   condition, capability, stage, priority, process, or another source-supported
   whole. Write the one-sentence grouping rule internally. For MECE grouping,
   test both a candidate overlap and a plausible uncovered item against that
   rule. Revise the grouping when either test fails.
3. **Form the page's testable proposition.** For an analytical or decision
   page, write `if these source-supported conditions hold, this judgment or
   action follows`. Then name the strongest source-bound fact, condition or
   counterargument that would weaken the proposition. For a source report, this
   is a claim-stress test rather than a request to collect new facts: an
   unverified condition remains visible as a boundary, recommendation or open
   question.
4. **Build argument cards before prose.** For each top-level argument, record
   internally: its complete sub-judgment; the source facts that prove, explain
   or qualify it; the strength of each item—existing fact, stated target,
   inferred relation, recommendation or boundary; and the one fact that a
   reader must retain. Delete a branch that has no decision-bearing evidence;
   demote evidence that has no argument role.
5. **Synthesize in Pyramid order.** State the governing thought, group two to
   four independent arguments by the chosen logic, then place evidence beneath
   its argument. Apply the `so what` test at every level: each fact must change
   the reader's understanding of its argument, and each argument must change the
   reader's understanding of the claim. A conclusion or decision page also
   states the next action, the material boundary and the strongest source-bound
   counterargument or reversal condition.
6. **Project the reasoning into its relationship grammar.** Only after the
   claim, arguments and evidence are stable, select the visible grammar—ordinary
   argument, classification, mapping, roadmap or governance chain. Preserve the
   argument order inside that grammar. A relationship diagram cannot replace an
   argument card, and a Pyramid cannot conceal the relationship the page needs
   to show.

The operating loop produces the following core chain tests:

1. **Claim.** `core_message` states one answer to the page question. It names
   the business object, the supported judgment and the applicable status or
   boundary. A topic, source heading, document name or list of modules cannot
   substitute for the claim.
2. **Argument.** Each top-level module explains one reason why the claim holds,
   one mechanism by which it operates, or one bounded action that implements it.
   An argument is a complete sub-judgment with a distinct role in the page
   answer. A source fact, document title, number, actor name or task label is
   evidence until the author states what it establishes.
3. **Evidence.** Each child fact must prove, explain or qualify its direct
   argument. Preserve the source actor, status, object, action and material
   condition. A fact that does not advance any argument moves to full copy,
   notes or a genuine reference list; an argument without sufficient evidence is
   weakened, removed or recast as a recommendation or open question.
4. **Pyramid test.** Pyramid can organise any relationship grammar when the
   audience needs an answer before its reasons and a decision or next action.
   The claim appears first; two to four arguments are mutually independent ways
   of establishing or implementing it; evidence sits beneath its argument. Order
   arguments by a stated logic such as importance, time, causal sequence or
   decision priority. A roadmap, mapping or governance chain retains its own
   relationship grammar while using this top-down organisation. A source-order
   inventory fails the Pyramid test.
5. **MECE test.** MECE is a grouping discipline available inside any page when
   the source and page mission provide one shared classification question, such
   as which role, stage, category, priority or capability each item represents.
   State the shared dimension and scope before the categories. Test mutual
   exclusivity by asking whether any item belongs under two peers in the stated
   dimension; test collective exhaustion by asking whether every source item
   required for the claimed scope has one home. When the source does not define
   a closed scope, state the classification boundary and do not claim
   completeness. A mixed list of actors, methods, tasks and results fails MECE
   even when each entry is valid; use the appropriate relationship grammar and
   an ordinary evidence grouping instead.
6. **Relationship-grammar-to-evidence fit.** SCR separates situation,
   complication and response; a roadmap separates stage, trigger and newly
   reached state; a mapping separates input, correspondence rule and use. Apply
   the same discipline in each: every visible evidence detail has one parent
   argument or category, and every parent has a source-supported purpose in the
   page claim.

Critic reviews this map by relation rather than word overlap. Passing source
coverage or a semantic-completeness lint does not demonstrate a claim,
argument and evidence chain.

### 2.9 Page-logic normalization and paragraph ownership

Before drafting `full_copy`, AUTHOR must normalize the page logic in working
judgment. This method is mandatory for every analytical, decision, transition or
conclusion page and remains useful in reduced form for foundation and taxonomy
pages. It creates no new project artifact, authoring field, receipt or user gate.

1. **页面问题归一化。** Rewrite the Deck Plan question as one answerable audience
   question with one decision-bearing verb. A question that joins several roles
   such as context, basis, requirement, action and outcome must be narrowed to the
   one role this page owns; the other roles become evidence, an explicit relation
   or adjacent-page material.
2. **论证角色分配。** Assign every candidate source fact one primary role on this
   page: driver or context, existing basis, gap or tension, response or action,
   result or implication, condition or boundary. A fact may support several deck
   arguments, but within one page it must have one principal duty. Do not treat
   these roles as peer modules merely because all facts are relevant.
3. **Build one directional chain.** Order the retained roles so every transition
   answers one of three questions: `because of what`, `therefore what`, or `how
   does it happen`. A valid chain has a readable direction such as `change → new
   requirement → current gap → construction conclusion`. A set of related facts
   without a directional predicate remains an inventory and must be regrouped.
4. **相邻页问题归属。** Compare every proposed paragraph and decision-bearing
   sentence with the current page question and the immediately adjacent page
   questions. The sentence belongs to the page whose question it answers most
   directly. When the same fact is retained on two pages, each occurrence must
   have a different explicit argument role. Material that explains `how to start`,
   `what to build`, `when to advance` or `what result to deliver` moves out of a
   page that only owns `why change is required`, unless that material is the
   source-supported landing of the current causal chain.
5. **段落角色单一性。** Build a paragraph blueprint from the directional chain.
   Each substantive paragraph has one principal role and opens with the
   corresponding sub-judgment. Every following sentence must prove, explain,
   qualify or explicitly transition from that sub-judgment. A sentence that
   introduces a new principal role starts a new paragraph or moves to its owning
   page. Paragraph count does not certify logic; role continuity does.
6. **Keep outcomes at their supported landing.** An implementation entry,
   staged action, capability conversion or long-term result cannot appear as a
   sibling proof of an earlier condition. It appears after the condition through
   an explicit action or trigger, or on the adjacent page that owns implementation
   and delivery.
7. **Run the role-switch Critic.** Ignore the title and visual hierarchy, then
   label each paragraph and each decision-bearing sentence by its primary role.
   Reject the draft when one paragraph silently switches roles, a sentence has no
   parent argument, the response appears before the gap is established, an
   outcome is presented as evidence for an entry condition, or adjacent-page
   material answers a different question more directly.
8. **Rewrite from the earliest failed link.** Repair the page question first,
   then the directional chain, paragraph ownership, full copy and onscreen
   selection in that order. Downstream wording edits cannot compensate for an
   invalid question or chain.

For example, a page that owns `why capability upgrading is required` may use
`operating change → expanded analytical requirement → current capability gap →
upgrade conclusion`. A first-phase business entry belongs to the next page when
that page owns `what to build and where to start`; it stays on the first page
only when the source makes it a necessary condition of the upgrade conclusion
and the transition is stated explicitly.

### 2.10 Mandatory full-copy structure pass

Execute this pass after page-logic normalization and before onscreen selection
for every content page. It is a generative rewrite pass over `full_copy`, not a
formatting cleanup and not a deterministic text transformation. It creates no
new project artifact, authoring field, receipt or user gate.

1. **Classify each paragraph's internal relation.** Decide whether its retained
   material forms genuinely parallel facts, tasks, stages or results; one causal
   or temporal chain; one claim with qualifications; or a short single point.
   Do not choose enumeration merely because the source contains several nouns or
   sentences.
2. **Build three levels for genuine parallel content.** Rewrite two or more
   substantive parallel branches as `段首核心结论 → 分项结论句 → 事实明细`. The
   paragraph lead states what the complete set establishes. Each `一是、二是、三是`
   starts with an independently intelligible sub-conclusion that names its
   business object and judgment before giving the document, actor, action,
   scope, number, date, condition or result that supports it.
3. **Keep peers on one dimension.** Test the most plausible overlap and the most
   plausible missing branch. If the branches mix actor, business field, method,
   maturity judgment or result, regroup them under their actual parents or use a
   directional chain. A source-faithful mixed list still fails this pass.
4. **Reject label-led pseudo-structure.** Openings such as `一是建设内容`、
   `二是阶段安排` and `三是技术支撑` are labels, not sub-conclusions. Rewrite each
   opening as a complete proposition. The detail may then restate part of that
   proposition for navigation and proof, but it must add evidence, scope or
   qualification rather than mechanically repeat it.
5. **Preserve non-parallel forms.** Keep a short single point as a natural
   paragraph. Keep a causal or staged chain in its supported order with explicit
   transitions. Do not force numbering when it would disguise dependency,
   chronology or qualification as peer logic.
6. **Flatten and audit before projection.** Read the paragraph without visual
   indentation and verify that the lead, every sub-conclusion and every evidence
   detail remains intelligible in sequence. Confirm that each detail has one
   parent, each sub-conclusion advances the paragraph lead, and the paragraph
   advances `core_message`. Rewrite the entire paragraph from its role when any
   link fails; adding ordinal markers to the existing draft does not complete
   this pass.

Critic repeats this classification independently. Deterministic lint may reject
explicit numbered branches whose openings are labels or incomplete clauses, but
it cannot decide whether source meaning is genuinely parallel. A passing lint
therefore confirms only the mechanical floor; completion requires the AUTHOR
pass and the role-switched Critic judgment above.

## 3. Audience-facing construction

### 3.1 Onscreen selection

The onscreen layer is the mandatory selection point. Keep the core conclusion and
only the evidence a silent reader needs to understand why it holds. Visual brevity
never overrides source meaning, and source availability never requires equal
visible rank for every fact.

Module headings carry business meaning by stating the object and its action,
status, role or judgment. A normal module heading must be independently
intelligible in silent reading. Prefer `主语 + 谓词 + 对象/状态`; do not let a
colon's trailing text supply the only predicate. Child lines provide evidence,
explanation and qualification. Do not coin official-sounding group names such as `国家统一基础`,
`行业专业基础`, `国家坐标` or `任务落点` unless the source defines the exact term
and a silent reader can understand it without author explanation.

Lists and numbers state why they are grouped and what they establish. Compression
preserves the object, predicate or action and material qualifier. Do not shorten
copy into slogans, unexplained category labels or presenter cues.

### 3.2 Hierarchy model

Chapter transition pages are navigation-only. Their onscreen copy exactly repeats
the corresponding contents-page chapter title, including the chapter number when
the contents page uses one. Do not add a secondary slogan, keyword chain, summary
or alternate chapter name.

Use one universal hierarchy rule:

`one page, one conclusion → one level, one question → peers, one dimension → children, added evidence → different levels, visible relationships`

Apply it through one shared semantic, syntactic and visual hierarchy. The three
content levels are stable even when the visual design changes:

1. **Page conclusion.** `core_message` answers what the page means. It is one
   complete judgment with the exact business matter, actor and source-supported
   state or action. On a CyberPPT content page it is also the **total thesis**:
   render it, or a display-safe equivalent with the same judgment, as the first
   visible level-1 statement. `core_message` may not exist only in metadata,
   notes or an off-page title.
2. **Module judgment.** Each top-level onscreen module answers which part proves,
   explains or implements the page conclusion. Normal modules are independently
   intelligible sub-judgments; the taxonomy exception below remains available.
3. **Evidence detail.** A module's `text` or `items` answers what fact, scope,
   action, object, condition or result establishes that module. Prefer a
   complete proposition. `语义标签：完整内容` is a limited evidence-detail form,
   never the default reading rhythm of a module or page.

When a page presents three or four parallel content groups, use all three
visible levels: **one visible level-1 total heading → named level-2 card/group
headings → level-3 group judgments or evidence**. The level-1 heading names
the whole field and gives the reader one story line; a page title stored only in
metadata does not satisfy this requirement. Each level-2 heading answers “which
part of the whole story is this?”, and each owns one or more level-3 lines that
explain what it establishes. Every level-1 and level-2 heading is author-written
locked text, never a label inferred by the renderer from a detail sentence.
Author every heading from the verified grouping dimension. For example:

```text
- 供需研判范围扩展
  - 研判对象发生扩展
    - 供给、需求与市场变化共同扩大供需研判范围
  - 研判维度形成覆盖
    - 总量、结构、区域、时段与风险纳入统一研判
  - 成果形态延伸决策支撑
    - 预测延伸至区间、概率和情景分析，形成多类决策支撑
```

For another four-card field, the visible total heading can name `统一预测闭环的
运行要求`, followed by group headings such as `周期规则贯通`、`分析口径统一`、
`预测流程固化` and `成果校核复盘`. A business detail sentence, card visual or a
page title stored only in metadata does not substitute for the visible total
heading and named level-2 headings. A page with one or two arguments does not
need this extra hierarchy.

The three-level ladder controls **reading order**; it does not prescribe a
single business relationship for all level-2 units. Before authoring a page,
choose one verified **relation grammar** from the source and use it consistently:

| Relation grammar | Level-2 units answer | Level-3 detail must show |
| --- | --- | --- |
| MECE classification | What independent parts jointly establish the total thesis? | The distinct judgment and source-grounded proof for that part. |
| Flow, causal chain, or operating loop | What happens at each stage? | Input, action, output, handoff, condition, or feedback at that stage. |
| Convergence | Which independent inputs jointly form the result? | How that input supports, constrains, or contributes to the stated result. |
| Mapping | Which source corresponds to which target, response, owner, or capability? | Both ends of the mapping and their concrete correspondence. |
| Comparison | What are the two matched objects under one criterion? | The shared criterion, material difference, and applicable condition. |
| Boundary or governance | Which requirement, boundary, or control protects the total thesis? | What it governs, limits, enables, or verifies. |

`core_message → relation units → evidence` remains visible in every content
page. The relation grammar changes the connections among the units, their
reading path, and their visual carrier. A flow must not be written as a peer
classification; convergence must not be written as a staged process; comparison
must preserve a matched dimension; mapping must expose both endpoints. The
author selects the grammar from verified source relationships, records it in
`上屏表达结构` when available, and lets visual design express that grammar without
creating a second narrative chain.

Use this authoring sequence for every content page:

1. Write `core_message` as one complete total thesis and project it to the
   first visible level-1 entry statement.
2. State the relation grammar and the reader question for the level-2 units.
3. Draft level-2 units from the same relation role; use MECE only for genuine
   classifications.
4. Add level-3 proof that belongs to one unit and adds an object, action,
   condition, scope, output, or result.
5. Check that the chosen visual relationship matches the authored grammar:
   groups for classification, path for flow, convergence for aggregation,
   paired field for comparison, and explicit endpoints for mapping.

Run the **card independence self-read** before finalizing: cover the level-3
copy and confirm that every level-2 heading still names a different part of the
page story; then cover the heading and confirm the level-3 copy adds new object,
action, scope, condition or result. A heading that paraphrases its detail, or a
card that repeats another card's heading or detail, fails this test and must be
rewritten or merged.

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
- **Claim–evidence role fit.** A child must prove, explain or qualify the
  relation asserted by its direct parent. A module claiming that a project is
  ready, has a basis, meets a condition, causes an outcome or creates an impact
  must show the corresponding readiness facts, basis, conditions, causal link or
  outcome. Project scope, capabilities, work packages, task lists and named
  deliverables explain what will be done; they do not by themselves prove a
  readiness or condition claim. When the source provides both, split the task
  module from the condition module and make the condition evidence visible.
- **Labels declare roles.** Use `标签：短语` sparingly and only when the label
  states the child's evidence role in the parent judgment and the phrase
  completely fills that role. A run of label-plus-list lines fails the
  read-aloud test even when each line is semantically complete.
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
Do not use a colon as the default way to compress a relationship. A colon may
mark one evidence detail's `label：content` relation; it must not simulate several
levels in one line. A module with one natural explanation may render compactly
as `module judgment：complete proposition`. When the explanation already contains
a semantic label, preserve it as a nested child:

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

### 3.3 Mandatory onscreen structure-projection pass

Execute this pass after the full-copy structure is stable and before visible
wording is finalized for every content page. This is a semantic projection and
editorial selection pass, not proportional abbreviation, paragraph-to-bullet
conversion or a second page-planning stage. It creates no new project artifact,
authoring field, receipt or user gate.

1. **Lock the invariant logic skeleton.** Carry forward `core_message`, the
   retained argument order, each argument's decisive evidence, every material
   condition and the selected relationship grammar. Compression may reduce
   evidence volume; it may not change a branch's role, reverse a relation,
   strengthen its status or create a new grouping dimension.
2. **Select before shortening.** Decide which full-copy arguments a silent
   reader must retain. Omit subordinate examples, repeated proof and
   non-decisive citations. Do not create one visible module for every paragraph
   or preserve every source fact at equal rank.
3. **Project semantic levels explicitly.** Project the page conclusion into the
   visible lead or governing composition; project each retained argument into an
   independently intelligible module judgment; project only its decisive proof,
   scope, condition or result into child text or items. For a three- or four-card
   field, write one visible level-1 total heading, write every level-2 card/group
   heading, and retain its judgment or evidence at level 3. A normal multi-module self-read
   page must expose both the argument layer and an evidence layer.
4. **Preserve relationship grammar.** Parallel arguments may become peer
   modules only when they share one dimension. Cause, progression, mapping,
   conversion, governance and closed-loop relations retain their endpoints,
   direction, trigger or landing. Do not flatten an `入口 → 基础 → 能力转化`
   chain into three interchangeable cards.
5. **Close every visible statement.** Normal module headings remain complete
   sub-conclusions; evidence lines state what fact establishes them. A formal
   taxonomy name may remain a heading only with a child that explains its role.
   Do not shorten a full-copy sub-conclusion into a noun label such as `业务入口`,
   `实施基础` or `能力转化`.
   **Reject abstract transformation claims.** Grammatical completeness is not
   business intelligibility. A heading such as `五类体系化建设推动统计分析基础转化为
   公共预测能力` still fails because the counted construction, transformation
   mechanism and observable operating result remain unnamed. Replace it with
   the concrete change a business user can recognize, such as shared data and
   methods across monthly, quarterly and annual forecasting, followed by the
   resulting review, release or warning workflow.
6. **Check projection completeness by role.** Compare onscreen content with
   `full_copy`, branch by branch. Every visible item must trace to one retained
   argument or its evidence. Every omitted item must be subordinate to a visible
   argument. A condition that changes strength, timing, responsibility or scope
   remains visible even when its supporting detail moves to notes.
7. **Flatten and reverse-test the page.** Read only the plain onscreen text and
   reconstruct `page conclusion → module judgment → decisive evidence` plus the
   relationship grammar. Then compare that reconstruction with `full_copy`.
   Rewrite the complete projection when a module has no argument role, a child
   proves a different claim, peer dimensions differ, evidence disappears or a
   directional relation becomes a flat list.

Critic performs this reverse test independently. Deterministic lint may reject a
multi-module page whose modules contain no evidence layer, incomplete headings,
dangling details or aggregate drift from `core_message`; it cannot determine the
correct semantic role or relationship grammar. Passing lint confirms the
mechanical floor only. Completion requires the AUTHOR projection and Critic
judgment above.

### 3.4 Peer dimension and supplementary evidence

Before keeping a visible sibling list, identify its single comparison dimension:
actor, capability, stage, problem, task or result. Do not place an actor, a
business field and that actor's evaluation result at the same indentation level.

Attach a supplementary fact, maturity rating, certification or result to the
actor or main claim it qualifies. If it only strengthens an already sufficient
claim, keep it in `full_copy` or `speaker_notes`; retain it onscreen only when it
provides unique proof the conclusion otherwise lacks.

Peer groups use comparable explanatory depth. If one standard names its regulated
object or role, its peers cannot stop at titles alone.

### 3.5 Detail grammar and evidence payload

`标签：短语` is an optional compact grammar for a direct evidence detail, not a
default onscreen sentence pattern. Use it only when the parent has already
stated a complete judgment, the label declares a real semantic relation, and
the short value completely fills that semantic slot. Valid examples include
`覆盖范围：电力数据全生命周期和全产业链` and
`推进条件：技术路线和业务模式成熟后转化`. `建设依据：国家政策` and
`推进方式：协同实施` remain abstract. Repeated label-plus-list lines must be
rewritten as propositions or consolidated into a genuine taxonomy table.

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

For self-read pages, prefer `国家建设指引明确四大方向和八项能力：覆盖数据
基础设施全生命周期` over `建设框架：四大方向、八项能力`. Prefer
`GB/T 13016规范体系表编制原则、程序和格式：提供统一编制依据` over
`编制方法：原则、程序和格式`. Visual wrapping supports layout only. It does not
permit a heading to retain multiple judgments or omit the subject, predicate,
object or material qualifier required for self-read meaning.

A standard number, document title, framework name, initiative, institution or
category list identifies evidence but does not yet explain it. State what the
named source defines, regulates, unifies, supports, enables, requires or proves.
Prefer `编制方法：GB/T 13016规定体系表编制原则、程序和格式` over
`编制方法：GB/T 13016`, and `信息模型：DL/T 890以CIM和CIS支撑调度资源信息交换`
over `信息模型：DL/T 890、CIM、CIS`. When the source provides only a name,
keep it for traceability or omit it from the visible layer; do not invent an
effect.

### 3.6 Strength, status and modality

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

### 3.7 Relationship, time and density

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
Apply the 2.6 preflight before this late-stage remedy: it governs page reading
form, information roles and heading scope before prose accumulates.

### 3.8 Speaker notes

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

### 3.9 Mandatory supporting-field construction pass

Execute this pass for every content page. It gives `mission`, `core_message`,
`argument`, `visual_thesis`, `relationships` and `speaker_notes` the same
method discipline already applied to `full_copy` and `onscreen`. The pass occurs
inside Final Script and creates no new project artifact, authoring field,
receipt or user gate.

1. **Mission ownership method.** Start from the approved Deck Plan question.
   Rewrite it as one page duty with one decision-bearing verb and one owned
   audience question. State what this page must resolve and keep context,
   response, result, condition and adjacent-page material out unless an explicit
   relationship makes one of them necessary. A list of topics after `说明` or
   `明确` does not establish page ownership.
2. **Core-answer method.** Answer the mission directly. Name the business object,
   the source-supported judgment or action, its status and the material boundary.
   Run a one-sentence takeaway test and a claim-stress test. When two independent
   answers remain, narrow the mission, make their relationship explicit or split
   the page.
3. **Argument-topology method.** Choose the smallest topology that proves the
   core answer: directed chain, parallel grouping, convergence, mapping,
   governance chain, roadmap or bounded decision package. `argument.pattern`
   names that topology; every `argument.chain` node has one semantic role; every
   directed transition has a supported relation. Do not use an arrow to connect
   items that are merely parallel, grouped or jointly sufficient.
4. **Visual-structure method.** Project the verified argument topology into
   `visual_thesis` and atomic `relationships`. The thesis states the visible
   relationship or spatial grammar, not a shortened copy of `core_message`.
   Each relationship edge carries one source object, one target object and one
   connecting action. Split an edge that hides a second actor, intermediate
   process, trigger or result. Visual fields may simplify evidence volume; they
   may not reverse direction, invent sequence or strengthen the claim.
5. **Speaker-note increment method.** Choose the note's incremental role before
   writing: basis explanation, subordinate evidence, non-material boundary,
   audience focus or natural transition. Write complete spoken language, then
   remove every sentence that only repeats the title, core message or visible
   modules. A longer paraphrase still fails when it adds no new role.
6. **Cross-field reverse test.** Read only these fields in order:
   `mission → core_message → argument → visual_thesis/relationships →
   speaker_notes`. Reconstruct the audience question, answer, proof topology,
   visible direction and spoken increment. Rewrite from the earliest field whose
   role cannot be reconstructed or conflicts with a later field.

Critic repeats all six methods independently. Deterministic checks enforce field
presence, registered topology, non-empty chains, visual relationship grammar,
high-confidence restatement and incompatible rendering. They provide execution
evidence for the artifact shape; they do not replace semantic Critic judgment.

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
13. For every module that asserts readiness, a basis, a condition, a cause, an
    outcome or an impact, read its child lines as the sole proof set. Confirm
    that they establish that asserted relation rather than merely inventory the
    project's scope, capabilities, tasks or deliverables. Split mixed proof
    roles before delivery.
14. Reapply the density preflight to every high-density page. Confirm that one
    visible grammar governs the page, the top-level modules stay within the
    normal information budget or carry a declared taxonomy, mapping or roadmap
    exception, and peer modules do not mix independent roles without an explicit
    relationship.
15. Read every normal module heading in plain text. Confirm that it states one
    complete judgment and survives when the page title, visual wrapping and
    layout are removed. Restructure headings with multiple independent clauses;
    a shorter but semantically weakened heading fails review.
16. Trace every substantive paragraph and visible module by its audience
    question, actor and actor role. Split a demand from its response, a
    condition from its action, or an existing fact from a recommendation unless
    a source-supported relationship is explicit and visible.
17. Review actor order inside every evidence group. Keep the same actor's
    decision-bearing facts together and follow source-supported responsibility
    chains across actors. Treat an `A → B → A` sequence as a review failure
    unless the return to A states a new explicit relationship.
18. For every content page, reconstruct the internal chain from visible copy:
    claim → argument → evidence. Confirm that every module is an independently
    intelligible reason, mechanism or bounded action for the page claim, and
    that every child proves, explains or qualifies that direct module. Remove or
    demote orphan evidence and unsupported arguments.
19. For every page organised with Pyramid, confirm that the answer appears
    before its reasons, peer arguments are independent, their order has a stated
    logic, and the evidence is grouped beneath the argument it supports. Apply
    this test whether the visible relationship grammar is a roadmap, mapping,
    governance chain, classification or ordinary argument. Source-order
    paraphrase fails this test.
20. For every page using MECE grouping, state the shared dimension and claimed
    scope, test each item for a single category home, and verify that every
    source item required by that scope is represented. Apply this test inside a
    roadmap, mapping, governance chain or ordinary argument when items are
    presented as a complete grouping. Mixed lists require an ordinary evidence
    grouping or an explicit relationship grammar.
21. Confirm that the universal organising framework and visible relationship
    grammar reinforce the same page claim. A Pyramid claim cannot obscure the
    stage relation of a roadmap, MECE categories cannot hide a mapping rule, and
    SCR resolution cannot appear before the source-supported complication.
22. Reconstruct the six-step operating loop for every analytical, decision and
    conclusion page. Verify an answerable question and scoped universe, one
    peer-grouping rule, a source-bound claim-stress test, complete argument
    cards, Pyramid synthesis and a visible relationship grammar. Repair the
    earliest failed step instead of polishing downstream prose.
23. For every asserted MECE grouping, test one potential overlap and one
    plausible uncovered item against the declared universe. Remove the MECE claim
    or revise the grouping whenever either test fails; a neat layout is not
    evidence of mutual exclusivity or collective exhaustion.
24. For every recommendation, condition or forward path, identify the strongest
    source-supported boundary, counterargument or reversal condition. Keep it
    visible when it materially changes the decision; retain it in full copy or
    notes when it explains scope without changing the visible claim.

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
