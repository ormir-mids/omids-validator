# MIDS Validator Development Guidance

## Authoritative project documents

- Use `developer/rules.md` as the local authoritative validation-rule catalogue.
- Use `developer/conventions.md` as the current accepted design.
- Use `developer/decisions.md` as the chronological record of consequential
  decisions and their rationale.
- Keep unresolved questions in `developer/developer_questions.md`, deferred
  ideas in `developer/future_rules.md`, and implementation plans in
  `developer/plans/`.
- Do not duplicate the full rule catalogue, conventions, or decision history in
  this file.

## Document visibility and publication

- Put every Markdown document intended for user or collaborator review in a
  visible project directory. Never place plans, reports, decision records, or
  other reviewable documents in `.codex/`, `.agents/`, or another hidden tool
  directory.
- Use `developer/` for local development records and generated review
  artifacts. The entire directory is intentionally excluded from Git.
- Reserve `docs/` for documentation deliberately approved for the future
  public repository. Moving a document from `developer/` to `docs/` is an
  explicit publication decision, not routine cleanup.
- Keep machine-managed directories such as virtual environments and caches in
  their conventional locations even though Git also ignores them.

## Decision traceability

- Record a decision in `developer/decisions.md` when it affects public
  behavior, rule interpretation or severity, data mutation, architecture,
  compatibility, dependencies, or long-term maintenance.
- Each decision entry must state its status, context, decision, rationale,
  consequences, and links to affected rules, code, tests, plans, or commits.
- Mark retrospective entries as reconstructed. Supersede an earlier decision
  with a new entry instead of silently rewriting its history.
- Treat chats as supporting context, not the durable source of truth. Move
  consequential conclusions into the decision log and current-state documents.

## Collaborative development workflow

- Work on one validation rule at a time.
- Discuss the rule in plain language and pseudocode before editing code.
- Do not implement later rules in advance.
- Make the smallest change needed for the agreed rule.
- Add focused tests for each rule and explain what each test proves.
- Update `developer/rules.md` immediately after changing rule behavior or
  numbering.
- Update the applicable convention and decision entry when behavior or design
  changes. Code, tests, the rule catalogue, and current conventions must agree
  before the change is complete.
- Run the focused tests after each rule. Run broader tests when shared code is
  changed or at the end of a layer.
- Point out repeated patterns that may justify an abstraction. Explain and
  discuss nontrivial abstractions before introducing them.
- Prefer explicit, readable code that a scientist with programming experience
  can follow without expert Python knowledge.
- Use descriptive names, straightforward control flow, and small local helpers.
  Avoid compressed expressions, clever metaprogramming, and generic frameworks
  when a direct implementation communicates the behavior more clearly.
- Introduce an abstraction only when repeated behavior or a stable interface
  justifies it. Keep responsibilities for inventory, validation rules,
  participant mutation, coordination, and reporting visibly separated.
- Explain new Python syntax and software-development concepts as they appear.

## Scope and safety

- Validation is read-only unless the user explicitly requests an approved
  creation feature, such as participants-table generation.
- Preserve existing user changes and avoid unrelated edits.
- Treat unknown researcher-defined acquisition suffixes as valid unless an
  active rule explicitly says otherwise.
- Do not silently resolve ambiguity about the MIDS standard. Record material
  uncertainty in the appropriate project document and discuss it with the user.

## Python and verification

- Use Python 3.10 or newer; prefer the shared ORMIR Python 3.12 environment once
  it is configured.
- Keep tests organized by validation layer.
- Use temporary synthetic datasets for focused rule tests.
- Empty placeholder files are appropriate when a rule examines paths or names
  only. Use structurally valid file contents when a rule parses or opens files.
- Findings must use the shared `Finding` model and contain dataset-relative
  paths.
- Run focused tests first, then the full suite after shared or user-facing
  changes. Exercise the CLI when its command contract or report output changes.
- Before completion, review the diff for generated reports, local paths,
  sensitive data, debugging remnants, unrelated edits, and stale documentation.
- Put generated reports and temporary review artifacts under `developer/` or an
  operating-system temporary directory. Commit only intentional, minimal,
  synthetic fixtures.
