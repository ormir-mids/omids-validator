# MIDS Validator

The MIDS validator checks MIDS-formatted musculoskeletal imaging datasets for
structural, naming, companion-file, metadata, image-header, and dataset-wide
consistency issues.

## Project status

The original prototype remains in `validator.py`. A modular replacement is
being developed incrementally under `src/mids_validator/`. The new package is a
scaffold and is not yet the working command-line tool.

## Intended command

```text
mids-validator DATASET [--participants] [--inspect-images] [--json REPORT]
```

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
- `docs/`: contains the rule catalogue, conventions, future ideas, and questions
  for the ORMIR-MIDS developers.
- `sample_data/`: contains current development data.
- `sources/`: contains reference material.

## Development approach

Development proceeds in small vertical slices. The first slice will define the
standard `Finding` object, implement one dataset-structure rule, and render that
finding in the terminal. Additional rules will use the same pattern after it is
understood and reviewed.
