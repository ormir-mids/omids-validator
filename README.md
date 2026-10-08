# OMIDS Validator

The OMIDS Validator checks MIDS-formatted musculoskeletal imaging datasets for
structural, naming, companion-file, metadata, image-header, and dataset-wide
consistency issues. It produces self-contained HTML, Markdown, and JSON reports
that can be reviewed or shared without rerunning the validation.

## Status

This repository contains the current development version of the validator.
Validation rules and command-line behavior may change while the MIDS standard
and the implementation are being refined.

## Requirements

- Python 3.10 or newer
- `pip`

Runtime dependencies are declared in `pyproject.toml`. Installing the project
also installs the required version of NiBabel and its dependencies.

## Installation

From the repository root, create a virtual environment and install the package:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

The editable installation makes the `omids_validator` command available and
keeps it linked to the checked-out source code.

The former `mids-validator` and `mids_validator` commands remain available as
temporary compatibility aliases for the 0.2 development line.

## Usage

Validate a dataset:

```bash
omids_validator /path/to/dataset
```

Include NIfTI header checks:

```bash
omids_validator /path/to/dataset --inspect-images
```

Write reports under a chosen directory:

```bash
omids_validator /path/to/dataset --output-dir /path/to/reports
```

The report directory must be outside the dataset being validated. Each run
creates a timestamped `omids_reports_YYYY-MM-DD_HHMMSS` directory containing:

- `report.html`: a styled, self-contained report for browser review
- `report.md`: a plain-text-friendly review document
- `report.json`: structured output for downstream use

Ordinary validation is read-only. The `--participants` option is different: it
creates `participants.tsv` when missing and adds subject identifiers discovered
in the dataset. Review the dataset and use this option only when that change is
intended.

```bash
omids_validator /path/to/dataset --participants
```

Generate the current validation-rule catalogue without validating a dataset:

```bash
omids_validator --rules --output-dir /path/to/output
```

This writes `omids_validator_rules.md` directly in the selected output directory
and replaces an existing file with that name.

Run `omids_validator --help` for the complete command reference.

## Exit status

- `0`: validation completed without errors, or the rule catalogue was written
- `1`: validation completed and found one or more errors
- `2`: the validator could not complete the requested operation

An exit status of `1` means the reports were generated successfully and contain
validation findings.

## Running the tests

With the virtual environment active and the package installed:

```bash
python -m unittest discover -s tests -v
```

## Repository layout

- `src/omids_validator/`: validator, command-line interface, and report writers
- `src/omids_validator/rules/`: validation rules organized by layer
- `src/omids_validator/data/`: packaged rule and metadata catalogues
- `tests/`: automated tests organized by validation layer and component

## How the code fits together

The installed `omids_validator` command calls `omids_validator.cli:main`.
`cli.py` reads the command-line options and calls `validator.validate`, which
scans the dataset once, runs the rule layers in order, and returns one complete
report. The modules under `reporters/` then write that report in each output
format.

`__main__.py` is intentionally small. It sends `python -m omids_validator` to
the same `cli.main` function used by the installed command.

The main supporting modules are:

- `inventory.py`: scans and organizes dataset paths for all rule layers
- `file_types.py`: shared NIfTI and JSON filename helpers
- `acquisition_profiles.py`: scan suffix, folder, and metadata definitions used
  by Layers 1 and 3
- `rule_catalog.py`: rule titles, severities, descriptions, and next steps from
  `data/rules.json`
- `participant_table.py` and `participants.py`: reading and explicitly requested
  updates of `participants.tsv`
- `models.py`: the findings and report objects shared by validation and reporting
