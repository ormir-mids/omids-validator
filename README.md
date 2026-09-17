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
```

Each run creates a timestamped `mids_reports_YYYY-MM-DD_HHMMSS` directory
under `OUTPUT_DIR` (the current working directory by default) and writes
`report.json`. The command prints a concise summary and returns status `1`
when validation finds an error, `2` when it cannot create the report, and `0`
otherwise.

The standalone `--rules` mode does not validate a dataset. It writes
`MIDS_validator_rules.md` directly under `OUTPUT_DIR`, replacing an existing
generated document with that name, and prints the saved file's absolute path.

## Code layout

- `src/mids_validator/cli.py`: accepts user input and requests a validation run.
- `src/mids_validator/validator.py`: coordinates the validation layers.
- `src/mids_validator/inventory.py`: scans the dataset once.
- `src/mids_validator/models.py`: defines findings, actions, and reports.
- `src/mids_validator/participants.py`: validates or populates
  `participants.tsv`.
- `src/mids_validator/rules/`: contains one module for each validation layer.
- `src/mids_validator/reporters/`: formats terminal and JSON output.
- `tests/`: contains automated tests organized by layer.
- `sample_data/`: contains current development data.
- `sources/`: contains reference material.

## Development approach

Development proceeds in small vertical slices. The first slice will define the
standard `Finding` object, implement one dataset-structure rule, and render that
finding in the terminal. Additional rules will use the same pattern after it is
understood and reviewed.
