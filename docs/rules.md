# MIDS Validator Rules

## Purpose

The MIDS validator evaluates a finished dataset produced by the current
ORMIR-MIDS workflow and reports structural, naming, sidecar-file, metadata,
image-header, and dataset-wide consistency findings.

The validator should continue after recoverable findings so the user receives a
complete report rather than only the first problem encountered.

## Severity

- **ERROR:** The user should fix this.
- **WARNING:** The user should probably fix this.
- **INFO:** The user might appreciate knowing this.

An ERROR does not mean that the entire dataset fails, is unusable, or that
validation stops. Severity describes how strongly the user should act on the
finding.

## Rule numbering

- `MIDS-0XX`: dataset structure
- `MIDS-1XX`: file naming and relationships
- `MIDS-2XX`: sidecar files
- `MIDS-3XX`: JSON metadata
- `MIDS-4XX`: optional image integrity and consistency checks
- `MIDS-5XX`: dataset-wide consistency and participants
- `MIDS-6XX` through `MIDS-9XX`: reserved

Rule IDs are intended to remain stable as new rules are added.

## Validation modes

Standard validation examines the directory structure, filenames, sidecar
relationships, every JSON file, metadata fields, and `participants.tsv`.

NIfTI header inspection is opt-in:

```text
mids-validator DATASET --inspect-images
```

Participant-table creation and population is also opt-in:

```text
mids-validator DATASET --participants
mids-validator DATASET -p
```

Without `--participants`, validation is read-only.

## Layer 0: Dataset structure

### MIDS-001 — Invalid dataset path

**Severity:** ERROR

The supplied dataset path must exist, be readable, and be a directory.

### MIDS-002 — Unexpected item in dataset root

**Severity:** ERROR

The dataset root may contain subject directories, `participants.tsv`, and any
other explicitly supported dataset-level files. Other items are reported.
Common operating-system artifacts covered by MIDS-009 are excluded from this
rule.

### MIDS-003 — Invalid subject identifier

**Severity:** ERROR

Subject directories must follow `sub-<ID>`, where `<ID>` contains only accepted
alphanumeric characters.

### MIDS-004 — Invalid session identifier

**Severity:** ERROR

When session directories are present, they must follow `ses-<ID>`, where `<ID>`
contains only accepted alphanumeric characters. Sessions are optional.

### MIDS-005 — Mixed session and direct-datatype structure

**Severity:** ERROR

A subject must use either session directories or datatype directories directly,
not both.

### MIDS-006 — Unrecognized datatype directory

**Severity:** ERROR

Subject or session data must be stored in a recognized datatype directory. The
first draft recognizes:

- `mr-anat`
- `mr-quant`
- `ct`
- `rx`

### MIDS-007 — Empty datatype directory

**Severity:** WARNING

A recognized datatype directory contains no image data.

### MIDS-008 — Subject contains no recognized imaging data

**Severity:** WARNING

A subject directory contains no images in recognized datatype directories.

### MIDS-009 — Operating-system artifact present

**Severity:** WARNING

A common operating-system artifact, such as `.DS_Store`, is present in the
dataset. The artifact should normally be removed before sharing or archiving the
dataset.

## Layer 1: File naming and relationships

### MIDS-101 — Unsupported item in datatype directory

**Severity:** ERROR

A datatype directory may contain only recognized finished image files and their
metadata sidecars. The first draft supports `.nii` and `.nii.gz` NIfTI images
and JSON metadata. Extensions are matched case-insensitively. Unsupported files
and nested directories produce this finding.

### MIDS-102 — Filename subject identifier mismatch

**Severity:** ERROR

Every supported image and JSON filename in a recognized datatype directory must
contain a `sub-<ID>` component that exactly matches its containing subject
directory. A missing subject identifier and a mismatched subject identifier
both produce this finding.

The parser accepts the converter's optional leading DICOM series-number prefix,
such as:

```text
003_sub-01_MESE.nii.gz
```

### MIDS-103 — Recognized suffix is in the wrong datatype directory

**Severity:** ERROR

When a suffix is recognized, it must appear in its recognized datatype
directory. For example, `_ct` must not be stored in `rx`, and `_cr` must not be
stored in `mr-anat`.

This rule inspects `.nii` and `.nii.gz` images in recognized datatype
directories. File extensions and recognized suffixes are matched
case-insensitively. A recognized suffix must occur at the end of the image
stem. JSON placement is validated through its relationship with the
corresponding NIfTI image.

Unknown researcher-defined suffixes are allowed and do not produce a finding.
This permits the format to expand without requiring every useful acquisition to
be predefined.

The recognized suffix mapping is maintained in the packaged
[`metadata_requirements.json`](../src/mids_validator/data/metadata_requirements.json)
acquisition-profile catalogue. It includes standard suffixes and compound
suffixes produced by the current converter. Compound suffixes are matched
before applying the final-underscore fallback used to describe unknown
researcher-defined suffixes.

The principal mappings are:

| Datatype directory | Recognized suffixes |
| --- | --- |
| `ct` | `ct`, `pcct`, `cbct`, `hrpqct` |
| `rx` | `cr` |
| `mr-anat` | `t1w`, `t1w-fs`, `t2w`, `t2w-fs`, `megre`, `part-phase_megre`, `part-real_megre`, `part-imag_megre`, `megre_reco`, `mese`, `part-phase_mese`, `dess`, `dess-fid`, `dess_echo` |
| `mr-quant` | `t1`, `t2`, `wt2`, `ff`, `b0`, `b1`, `vel`, `strain`, `strain-vec`, `strain-rate`, `strain-rate-vec` |

This mapping must follow actual supported package output and may grow over time.

### MIDS-104 — Case-conflicting filenames

**Severity:** WARNING

Two filenames that differ only by capitalization may collide or behave
differently when moved between case-sensitive and case-insensitive filesystems.
This rule compares supported NIfTI and JSON filenames within the same datatype
directory using case-insensitive text. Each conflicting file receives a
finding.

## Layer 2: Sidecar files

### MIDS-201 — Missing primary JSON sidecar

**Severity:** ERROR

Every NIfTI image must have a primary `<image-stem>.json` sidecar.
The image and sidecar must be in the same datatype directory. Their filenames
are matched case-insensitively, including the JSON extension. Optional
`_patient.json` and `_extra.json` files do not satisfy this requirement.

### MIDS-202 — Malformed primary JSON sidecar

**Severity:** ERROR

The primary JSON sidecar must contain syntactically valid, readable UTF-8 JSON.
All primary JSON files are parsed during standard validation. JSON contents and
metadata values are not reproduced in findings.

### MIDS-203 — Malformed optional JSON sidecar

**Severity:** WARNING

A present `_patient.json` or `_extra.json` sidecar must contain syntactically
valid, readable UTF-8 JSON. Primary and optional sidecars are parsed in the same
validation pass but receive different rule IDs and severities. JSON contents
and metadata values are not reproduced in findings.

### MIDS-204 — Optional patient JSON is absent

**Severity:** INFO

The optional `<image-stem>_patient.json` file is absent. Normal terminal output
should show a count and one example path rather than print one line per image.
The detailed report retains every affected image path. Matching is
case-insensitive and occurs within the image's datatype directory. A malformed
but present sidecar is not considered absent.

### MIDS-205 — Optional extra JSON is absent

**Severity:** INFO

The optional `<image-stem>_extra.json` file is absent. Normal terminal output
should show a count and one example path rather than print one line per image.
The detailed report retains every affected image path. Matching is
case-insensitive and occurs within the image's datatype directory. A malformed
but present sidecar is not considered absent.

### MIDS-206 — Orphan JSON sidecar

**Severity:** WARNING

A primary, patient, or extra JSON sidecar exists without a corresponding NIfTI
image. Primary sidecars are matched by their complete image stem. The
`_patient` or `_extra` qualifier is removed before matching optional sidecars to
their image. Matching is case-insensitive and occurs within the same datatype
directory. All sidecars belonging to the same missing image are consolidated
into one finding, with the primary JSON used as the representative path when it
exists.

### MIDS-207 — Invalid extra JSON structure

**Severity:** WARNING

A present `_extra.json` file should contain the `meta` and `extra` top-level
structures expected by the current ORMIR-MIDS package. The loaded JSON must be
an object whose top-level keys are exactly `meta` and `extra`; key order does
not matter, but missing or additional top-level keys produce this finding.
Malformed or unreadable JSON is reported by MIDS-203 and is not reported again
by this rule.

## Layer 3: JSON metadata

### Standard metadata rules

### MIDS-301 — Required metadata field is missing

**Severity:** WARNING

A field classified as mandatory for the recognized acquisition profile is
absent from the primary JSON sidecar. Proposed and draft fields are not
enforced by this rule. MIDS-301, MIDS-303, and MIDS-304 are evaluated in one
pass so each primary JSON sidecar is parsed only once.

### MIDS-302 — Metadata field has an invalid type

**Severity:** INFO

A recognized metadata field is present but cannot be interpreted using the
field type required by its acquisition profile. This rule is deferred until
representative output is available for the recognized acquisition profiles and
the expected JSON types can be verified. Type requirements must not be inferred
solely to enable this check.

### MIDS-303 — Required metadata field is empty

**Severity:** WARNING

A required metadata field is present but is null, an empty string, or an empty
collection. Unless an acquisition profile states otherwise, this is treated as
equivalent to a missing value. Whitespace-only strings are also empty. Zero and
`false` are not treated as empty.

Unknown metadata fields are allowed and do not produce findings.

### MIDS-304 — Optional metadata field is missing

**Severity:** INFO

A field classified as optional for the recognized acquisition profile is absent
from the primary JSON sidecar. Normal terminal output should summarize repeated
findings rather than print one line per missing field. Proposed and draft fields
do not produce findings. Present but empty optional fields do not currently
produce findings.

Metadata field checks are skipped when the image suffix is unrecognized or the
primary JSON sidecar is missing, malformed, or unreadable. The corresponding
Layer 2 finding reports the sidecar problem without a cascade of metadata-field
findings. A primary sidecar containing valid JSON that is not an object is also
skipped until MIDS-302 type validation is implemented.

## Layer 4: Optional image integrity and consistency

Image inspection is a practical validator extension rather than a requirement
currently defined by the MIDS standard. MIDS-401 is currently implemented as a
module-level check; command-line `--inspect-images` wiring remains pending.
It reads image headers without loading complete voxel arrays.

### MIDS-401 — Unreadable or invalid NIfTI file

**Severity:** ERROR

The image cannot be opened and interpreted as a NIfTI file.

The header collector attempts to open each discovered NIfTI image exactly once.
An unsuccessful attempt produces this finding; later image rules receive only
successfully opened image records.

### MIDS-402 — Acquisition dimension outlier

**Severity:** WARNING

An image's dimensions differ from the common shape for the same image type
across the dataset. The image type is the complete case-insensitive filename
label following `sub-<ID>_`; it is distinct from the final acquisition suffix
used for metadata-profile lookup. For example, `part-phase_megre` and
`part-real_megre` are separate image types.

The rule runs only when one shape represents at least 80% of the readable
images with an image type. It reports only the remaining images. When no shape
reaches that threshold, the group produces no finding because it has no
defensible common shape.

## Layer 5: Dataset-wide consistency and participants

### MIDS-501 — Participants table is absent

**Severity:** WARNING

The dataset does not contain `participants.tsv`. If `--participants` is
supplied, the validator creates the table and reports the action.

### MIDS-502 — Participants table cannot be parsed

**Severity:** ERROR

`participants.tsv` is not valid tab-separated tabular data. A malformed table
must not be automatically rewritten.

### MIDS-503 — Participant identifier column is absent

**Severity:** ERROR

`participants.tsv` must contain a `participant_id` column.

### MIDS-504 — Duplicate participant identifier

**Severity:** ERROR

Two or more rows contain the same non-empty `participant_id`.

### MIDS-505 — Subject is missing from participants table

**Severity:** WARNING

A `sub-<ID>` directory has no corresponding row in `participants.tsv`. If
`--participants` is supplied, the missing subject is added without changing
existing values.

### MIDS-506 — Participant row has no subject directory

**Severity:** WARNING

A participant row has no corresponding `sub-<ID>` directory. The validator
reports but never automatically deletes the row.

### MIDS-507 — Invalid participant identifier

**Severity:** ERROR

A non-empty `participant_id` does not follow the accepted `sub-<ID>` form.

### MIDS-508 — Malformed participant row

**Severity:** ERROR

A participant row has an inconsistent number of fields or cannot be interpreted
using the table header. The validator must not overwrite a malformed table.

## Deferred rules and open questions

Rules requiring additional evidence or developer agreement are recorded in
[`future_rules.md`](future_rules.md). Questions for the ORMIR-MIDS developers are
recorded in [`developer_questions.md`](developer_questions.md). Agreed behavioral
decisions are recorded in [`conventions.md`](conventions.md).
