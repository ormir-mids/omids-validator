# OMIDS Validator

OMIDS Validator checks MIDS-formatted musculoskeletal imaging datasets for
structural, naming, companion-file, metadata, image-header, and dataset-wide
consistency issues. It produces HTML, Markdown, and JSON reports that can be
reviewed or shared without rerunning the validation.

## Status

OMIDS Validator 0.2 is an early public release intended for testing on
MIDS-formatted datasets. Validation rules and command-line behavior may change
as the MIDS standard and implementation are refined.

If the validator does not handle your dataset or workflow as expected, please
[open a GitHub issue](https://github.com/ormir-mids/mids-validator/issues).

## Installation

OMIDS Validator requires Python 3.10 or newer.

```bash
python -m pip install omids-validator
```

The installation provides two equivalent command spellings:
`omids_validator` and `omids-validator`. The examples below use
`omids_validator`.

## Usage

Validate a dataset and write reports under a chosen directory:

```bash
omids_validator /path/to/dataset --output-dir /path/to/reports
```

The report directory must be outside the dataset. Each run creates a
timestamped `omids_reports_YYYY-MM-DD_HHMMSS` directory containing:

- `report.html`: a styled, self-contained report for browser review
- `report.md`: a plain-text-friendly review document
- `report.json`: structured output for downstream use

Include NIfTI header checks with:

```bash
omids_validator /path/to/dataset --inspect-images \
  --output-dir /path/to/reports
```

NIfTI header inspection is optional because these checks extend beyond the
current MIDS specification.

### Participant table updates

By default, OMIDS Validator does not modify the dataset. To create or update
`participants.tsv` as part of validation, add the `--participants` option:

```bash
omids_validator /path/to/dataset --participants \
  --output-dir /path/to/reports
```

This option adds subject identifiers found in the dataset and can fill blank
age or sex cells from patient JSON sidecars when a value can be selected
safely. Existing nonblank participant values are not overwritten.

### Validation-rule catalogue

Generate the current human-readable rule catalogue without validating a
dataset:

```bash
omids_validator --rules --output-dir /path/to/output
```

This writes `omids_validator_rules.md` in the selected output directory.

Run `omids_validator --help` for the complete command reference.

## Development

Clone the repository and install it in editable mode:

```bash
git clone https://github.com/ormir-mids/mids-validator.git
cd mids-validator
python -m pip install -e .
```

Run the automated tests with:

```bash
python -m unittest discover -s tests -v
```

The installed commands call `omids_validator.cli:main`. Validation is
coordinated by `omids_validator.validator`, rule implementations are organized
by validation layer under `src/omids_validator/rules/`, and the authoritative
rule catalogue is `src/omids_validator/data/rules.json`.

## License

OMIDS Validator is distributed under the GNU General Public License version 3
or any later version. See [`LICENSE`](LICENSE) for the complete terms.
