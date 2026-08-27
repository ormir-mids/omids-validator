# MIDS Validator Development Guidance

## Authoritative project documents

- Use `docs/rules.md` as the authoritative validation-rule catalogue.
- Use `docs/conventions.md` as the authoritative record of design decisions.
- Keep unresolved questions in `docs/developer_questions.md` and deferred ideas
  in `docs/future_rules.md`.
- Do not duplicate the full rule catalogue or conventions in this file.

## Collaborative development workflow

- Work on one validation rule at a time.
- Discuss the rule in plain language and pseudocode before editing code.
- Do not implement later rules in advance.
- Make the smallest change needed for the agreed rule.
- Add focused tests for each rule and explain what each test proves.
- Update `docs/rules.md` immediately after changing rule behavior or numbering.
- Run the focused tests after each rule. Run broader tests when shared code is
  changed or at the end of a layer.
- Point out repeated patterns that may justify an abstraction. Explain and
  discuss nontrivial abstractions before introducing them.
- Prefer clear, maintainable code over premature generalization.
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
