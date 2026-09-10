# Questions for the ORMIR-MIDS Developers

These questions require clarification from the ORMIR-MIDS developers before the
validator behavior can be finalized.

## 1. How should repeated acquisitions be represented and preserved?

With `series_number=False`, repeated acquisitions assigned to the same subject,
datatype directory, and suffix resolve to the same output path. The converter
does not check for a collision before writing, so a later acquisition may
replace an earlier one.

With `series_number=True`, the package retains both using leading DICOM series
numbers:

```text
003_sub-01_MESE.nii.gz
007_sub-01_MESE.nii.gz
```

BIDS instead uses run entities:

```text
sub-01_run-01_MESE.nii.gz
sub-01_run-02_MESE.nii.gz
```

- Should repeated acquisitions use `run-XX`, leading series numbers, or either?
- Should the converter refuse to overwrite an existing output?
- What stable identifier should be used when DICOM series numbers are absent or
  change after export?

## 2. Is the primary JSON sidecar formally required?

The converter always writes `<image-stem>.json`, but the package loader tolerates
its absence. The proposed validator reports a missing primary JSON as an error
because its metadata cannot otherwise be validated.

## 3. What is the intended session convention?

The package optionally creates a `ses-<ID>` directory but currently does not
include the session ID in saved filenames. Should this remain accepted package
behavior, or should future output include the session entity in the filename?

## 4. Are leading DICOM series-number prefixes part of the intended format?

The package can emit `003_sub-01_MESE.nii.gz`, so the filename does not begin
with `sub-<ID>`. Is this an intended ORMIR-MIDS convention or a temporary method
of avoiding output collisions?

## 5. Should participant-table creation be automatic or explicit?

The current proposal requires an explicit option:

```text
mids-validator DATASET --participants
mids-validator DATASET -p
```

It creates `participants.tsv` when missing and adds unrepresented subject IDs
without deleting or overwriting existing information.

## 6. Should dataset setup include a mirrored derivatives structure?

Datasets initialized with `ormir_init` should already contain a `derivatives`
directory. When creating or populating `participants.tsv`, the tool could also
create a matching subject/session directory structure below `derivatives`.

- Should this be part of `--participants`, or a separate explicit option?
- Should only subject/session folders be mirrored, or datatype folders as well?
- Should existing derivative content always be left untouched?

## 7. What is the required participants.tsv column structure?

The MIDS standard does not currently provide an example `participants.tsv`,
so the required columns and their meanings are unclear. The validator's
creation workflow currently follows the available BIDS study example, whose
header is:

```text
participant_id	age	sex	group
```

Only `participant_id` can be obtained from the MIDS directory structure; the
other columns are created blank. Should MIDS require these four columns, allow
arbitrary study-specific columns, or define a different minimum schema?
