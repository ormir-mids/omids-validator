# Deferred and Future Validator Rules

This is a parking lot for useful checks that are intentionally outside the
first working draft. An item belongs here when it may add value but needs more
evidence, design work, test data, or ORMIR-MIDS developer agreement.

Moving an item into the active rule catalogue requires an agreed severity,
clear applicability, a low false-positive risk, and valid/invalid tests.

## Filename and acquisition identity

### Repeated-acquisition identity

Detect repeated logical acquisitions and verify that each has a durable unique
identifier. This is deferred until the group decides between BIDS-style
`run-XX`, leading DICOM series numbers, or another convention.

### Overwrite-risk detection

Identify cases where conversion would map two source acquisitions to the same
output path. This may be better implemented in the converter than in a validator
that only sees the final output, because an overwritten acquisition is no longer
present to inspect.

### Case-normalization guidance

Detect names that differ only by capitalization and could collide when datasets
move between case-sensitive and case-insensitive filesystems.

## JSON metadata

### Plausibility ranges

Check fields for clearly impossible or implausible values, such as negative echo
times, zero magnetic-field strength, or nonsensical exposure values. This is
deferred because ranges must be modality-specific and should not generate noise
for unusual but legitimate research acquisitions.

### Unit validation and conversion

Detect likely unit mistakes and distinguish, for example, seconds from
milliseconds. Automatic correction should not be attempted without explicit
rules and provenance.

### Cross-field scientific consistency

Validate relationships between fields, such as echo-time arrays, repetition
time, acquisition type, and image dimensions.

### Optional metadata completeness scores

Provide dataset-level summaries of recommended or optional metadata coverage
without producing a line for every absent field.

## NIfTI and image-content inspection

### Full voxel-data scan

Optionally inspect arrays for NaN, infinity, unexpected constant images, or
unsupported data ranges. This requires loading image data and may be expensive.

### Detailed affine and orientation checks

Compare qform and sform, identify contradictory spatial transforms, and check
orientation consistency across an acquisition family.

### Cross-subject shape consistency

Group comparable acquisitions and report shape, voxel-spacing, dimension, or
orientation outliers. This is particularly promising for multi-echo data but
needs explicit grouping rules.

### Metadata-to-image dimension checks

Compare metadata array lengths, such as echo times, with the corresponding
NIfTI dimensions.

### Acquisition-family completeness

Check whether expected magnitude, phase, real, imaginary, FID, echo, or derived
components are all present. Legitimate incomplete families must be understood
before this can be enforced.

## Dataset-wide consistency

### Shared-metadata consistency

Compare fields that should remain stable within a subject, session, scanner, or
acquisition family and report meaningful outliers.

### Duplicate-content detection

Use checksums or selected header/content characteristics to identify duplicated
images stored under different names. This may be expensive and duplicates may
be intentional.

### Longitudinal consistency

Check whether sessions, time points, and subject-level metadata are internally
consistent without assuming that biological or acquisition values must remain
unchanged.

## Reporting and operations

### Strictness profiles

Allow projects to promote selected warnings to errors or suppress selected INFO
findings while preserving stable underlying rule IDs.

### Baseline comparison

Compare a current report to an accepted baseline so automated pipelines can
distinguish new findings from known legacy issues.

### Standard interchange formats

Consider exporting SARIF or another established static-analysis format if the
validator is integrated with repository hosting or continuous integration.

### Performance and remote-storage mode

Add controlled parallel header inspection and progress reporting for very large
datasets or high-latency network filesystems.
