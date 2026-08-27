# MIDS Validator Conventions

## Purpose and scope

The MIDS validator evaluates MIDS-formatted musculoskeletal imaging datasets to
promote open and reproducible science. Consistent dataset organization allows
research groups to share data and transfer analysis code between studies with
less project-specific adaptation.

The first release targets finished datasets produced by the current
`ormir-mids` package. Where the package and written specification differ, known
package output is accepted. Metadata requirements are based on the written
specification and decisions agreed with the ORMIR-MIDS developers.

## Severity

Severity communicates the recommended attention or action:

- **ERROR:** A convention violation likely to cause problems in downstream
  pipelines or prevent data and code from being interoperable between research
  groups. The user should fix it.
- **WARNING:** A probable problem or important inconsistency that the user should
  review and probably fix.
- **INFO:** A non-blocking observation the user may appreciate knowing.


## Rule identifiers

The first digit identifies the validation layer:

- `MIDS-0XX`: dataset structure
- `MIDS-1XX`: file naming and relationships
- `MIDS-2XX`: sidecar files
- `MIDS-3XX`: metadata and optional NIfTI inspection
- `MIDS-4XX`: dataset-wide consistency and participants
- `MIDS-5XX` through `MIDS-9XX`: reserved

Rule IDs remain stable as the catalogue grows.

## Dataset conventions

- Supported datatype directories are initially `mr-anat`, `mr-quant`, `ct`, and
  `rx`.
- Finished images may use either `.nii` or `.nii.gz`.
- File extensions and recognized acquisition suffixes are matched
  case-insensitively. Original filename capitalization is preserved in reports.
- Sessions are optional. A subject may contain datatype directories directly or
  inside `ses-<ID>`, but must not mix both structures.
- Session IDs are not required in filenames because the current converter does
  not include them when saving session-based output.
- Filenames must contain a subject ID matching the containing `sub-<ID>`
  directory.
- Unknown researcher-defined acquisition suffixes are allowed. Recognized
  suffixes are checked for placement in the appropriate datatype directory.
- Leading DICOM series-number prefixes such as `003_sub-01_MESE.nii.gz` are
  provisionally accepted because the converter can produce them.

## Sidecar files and metadata

- Every NIfTI image is expected to have a primary JSON sidecar with the same
  stem.
- `_patient.json` and `_extra.json` are optional.
- All present JSON files are parsed during standard validation.
- Missing mandatory metadata fields are warnings because absent metadata may
  reduce reproducibility or interoperability without making the image unusable.
- Missing optional metadata fields are informational findings.
- Proposed and draft metadata fields are not enforced.
- Metadata fields with unusable types are informational findings. Type checking
  is deferred until representative output and expected JSON types are verified.
- Unknown metadata fields are allowed and are not reported.
- Reports identify patient-metadata problems without reproducing sensitive
  values.

## NIfTI inspection

NIfTI header inspection is initially opt-in:

```text
mids-validator DATASET --inspect-images
```

It checks whether images are readable and examines dimensions, voxel spacing,
spatial transforms, and dimension consistency without loading complete voxel
arrays. Outlier summaries are preferred over one finding for every normal
image.

## Participants workflow

The intended workflow is:

```text
ormir_init -> ormir-mids conversion -> mids-validator
```

Because the preceding tools do not populate `participants.tsv`, the validator
can create the table and add missing subject IDs when explicitly requested:

```text
mids-validator DATASET --participants
mids-validator DATASET -p
```

Participant updates preserve existing columns, rows, and values. The validator
does not delete unmatched rows, overwrite participant information, or rewrite a
malformed table. Without this option, validation is read-only.

A newly created table contains only the `participant_id` column because subject
IDs are the only participant information available from the directory
structure. Age, sex, and other participant attributes are not inferred or
created.

## Reporting conventions

- Human-readable and JSON reports are produced from the same structured
  findings.
- Finding paths are relative to the dataset root.
- Findings are ordered deterministically.
- Optional-file INFO findings may be summarized in normal terminal output.
- The JSON report schema is versioned independently of ORMIR-MIDS.

The active rule catalogue is in [`rules.md`](rules.md). Unresolved design
questions are in [`developer_questions.md`](developer_questions.md), and
possible later checks are in [`future_rules.md`](future_rules.md). The working,
machine-readable catalogue of acquisition profiles and metadata fields is in
[`metadata_requirements.json`](../src/mids_validator/data/metadata_requirements.json).
Requirements in that file must be verified before they are enforced by Layer 3
rules.
