"""Coordinate a complete dataset validation run.

This module will build the dataset inventory, optionally update participants,
run each validation layer in order, and combine the findings into one report.
Individual rule logic belongs in ``mids_validator.rules``.
"""
