# MIDS Validator

The MIDS Validator checks MIDS-formatted musculoskeletal imaging datasets for
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

The editable installation makes the `mids-validator` command available and
keeps it linked to the checked-out source code.

## Usage

Validate a dataset:

```bash
mids-validator /path/to/dataset
```

Include NIfTI header checks:

```bash
mids-validator /path/to/dataset --inspect-images
```

Write reports under a chosen directory:

```bash
mids-validator /path/to/dataset --output-dir /path/to/reports
```

The report directory must be outside the dataset being validated. Each run
creates a timestamped `mids_reports_YYYY-MM-DD_HHMMSS` directory containing:

- `report.html`: a styled, self-contained report for browser review
- `report.md`: a plain-text-friendly review document
- `report.json`: structured output for downstream use

Ordinary validation is read-only. The `--participants` option is different: it
creates `participants.tsv` when missing and adds subject identifiers discovered
in the dataset. Review the dataset and use this option only when that change is
intended.

```bash
mids-validator /path/to/dataset --participants
```

Generate the current validation-rule catalogue without validating a dataset:

```bash
mids-validator --rules --output-dir /path/to/output
```

This writes `mids_validator_rules.md` directly in the selected output directory
and replaces an existing file with that name.

Run `mids-validator --help` for the complete command reference.

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

- `src/mids_validator/`: validator, command-line interface, and report writers
- `src/mids_validator/rules/`: validation rules organized by layer
- `src/mids_validator/data/`: packaged rule and metadata catalogues
- `tests/`: automated tests organized by validation layer and component
