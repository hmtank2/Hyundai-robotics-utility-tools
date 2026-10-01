"""Shared JOB file reading and line handling for analysis and presentation layers."""

from .source import collect_files, read_job, split_line

__all__ = ['collect_files', 'read_job', 'split_line']
