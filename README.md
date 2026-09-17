# MIDS Validator

The MIDS validator checks MIDS-formatted musculoskeletal imaging datasets for
structural, naming, companion-file, metadata, image-header, and dataset-wide
consistency issues.

## Project status

The modular implementation under `src/mids_validator/` provides the current
command-line tool and continues to be developed incrementally.

## Command

```text
mids-validator DATASET [-p] [-i] [-o OUTPUT_DIR]
mids-validator --rules [-o OUTPUT_DIR]
mids_validator --rules [-o OUTPUT_DIR]
```

Each run creates a timestamped `mids_reports_YYYY-MM-DD_HHMMSS` directory
under `OUTPUT_DIR` (the current working directory by default) and writes
`report.html`, `report.md`, and `report.json`. `report.html` is a self-contained,
styled report that can be opened in a browser without an internet connection.
The report destination must be outside the dataset. The command prints a
concise summary and returns status `1` when validation finds an error, `2` when
it cannot validate or create the reports, and `0` otherwise.

The standalone `--rules` mode does not validate a dataset. It writes
`mids_validator_rules.md` directly under `OUTPUT_DIR` (the current working
directory by default), replacing an existing generated document with that
name. On success it prints the saved file's absolute path. Running the command
with no arguments displays the help text.

## Code layout

- `src/mids_validator/cli.py`: accepts user input and requests a validation run.
- `src/mids_validator/validator.py`: coordinates the validation layers.
- `src/mids_validator/inventory.py`: scans the dataset once.
- `src/mids_validator/models.py`: defines findings, actions, and reports.
- `src/mids_validator/participant_table.py`: reads and validates the shared
  participant-table structure.
- `src/mids_validator/participants.py`: explicitly creates or populates
  `participants.tsv`.
- `src/mids_validator/rules/`: contains one module for each validation layer.
- `src/mids_validator/reporters/`: formats terminal, HTML, Markdown, and JSON
  output.
- `tests/`: contains automated tests organized by layer.
- `sample_data/`: contains current development data.

## Development approach

The code is written for scientific programmers who need to inspect and defend
its behavior without learning a framework first. Validation rules use explicit
control flow, descriptive names, shared immutable findings, and one inventory
of the dataset. Each layer owns one visible rule registry, and packaged rule and
metadata catalogues are checked before use.

Changes should remain small and traceable across behavior, tests, and rule
documentation. Ordinary validation is read-only; participant-table mutation is
available only through the explicit `--participants` option.
