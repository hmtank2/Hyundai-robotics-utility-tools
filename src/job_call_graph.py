"""Find numeric JOB calls and link them to files that are already loaded."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from job_core import split_line


CALL_RE = re.compile(r"(?<![\w.])call[ \t]+(?P<target>[0-9]+)(?![\w.])", re.I)


@dataclass(frozen=True)
class JobCall:
    source: str
    target: str
    line: int
    code: str
    raw: str
    comment: str


@dataclass(frozen=True)
class CallLink:
    call: JobCall
    target_path: str | None
    candidates: tuple[str, ...]

    @property
    def status(self) -> str:
        if self.target_path is not None:
            return 'resolved'
        return 'ambiguous' if self.candidates else 'missing'


def parse_calls(text: str, source: str = '') -> list[JobCall]:
    """Read literal numeric CALL targets outside comments and quoted strings."""
    calls = []
    for line_no, raw in enumerate(text.splitlines(), 1):
        masked_code, comment = split_line(raw)
        for match in CALL_RE.finditer(masked_code):
            calls.append(JobCall(source, match['target'], line_no,
                                 raw[:len(masked_code)].strip(), raw, comment))
    return calls


def resolve_calls(calls: list[JobCall], file_paths: list[str]) -> list[CallLink]:
    """Match loaded JOBs by folder and numeric name, preserving ambiguity."""
    paths = sorted(file_paths, key=str.casefold)
    links = []
    for call in calls:
        caller_folder = str(Path(call.source).parent).casefold()
        same_folder = [path for path in paths
                       if str(Path(path).parent).casefold() == caller_folder]
        numeric_target = int(call.target)

        def exact(pool: list[str]) -> list[str]:
            return [path for path in pool if Path(path).stem.casefold() == call.target.casefold()]

        def numeric(pool: list[str]) -> list[str]:
            return [path for path in pool if Path(path).stem.isascii()
                    and Path(path).stem.isdecimal() and int(Path(path).stem) == numeric_target]

        preferred = (exact(same_folder) or numeric(same_folder)
                     or exact(paths) or numeric(paths))
        target_path = preferred[0] if len(preferred) == 1 else None
        links.append(CallLink(call, target_path, tuple(preferred)))
    return links
