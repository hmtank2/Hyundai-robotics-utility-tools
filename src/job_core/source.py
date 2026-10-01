"""Read JOB sources without depending on the GUI, Excel, or signal analysis."""

from __future__ import annotations

from pathlib import Path


def split_line(line: str) -> tuple[str, str]:
    """따옴표 안의 문자열은 검색에서 제외하고, 밖의 첫 #에서 주석 분리."""
    masked = list(line)
    quote = None
    i = 0
    while i < len(line):
        char = line[i]
        if quote:
            masked[i] = " "
            if char == "\\" and i + 1 < len(line):
                i += 1
                masked[i] = " "
            elif char == quote:
                if i + 1 < len(line) and line[i + 1] == quote:
                    i += 1
                    masked[i] = " "
                else:
                    quote = None
        elif char in ('"', "'"):
            quote = char
            masked[i] = " "
        elif char == "#":
            return "".join(masked[:i]), line[i + 1:].strip()
        i += 1
    return "".join(masked), ""


def read_job(path: Path, encoding: str | None = None) -> tuple[str, str]:
    raw = path.read_bytes()
    if encoding:
        return raw.decode(encoding), encoding
    encodings = ["utf-8-sig", "cp949"]
    if raw.startswith((b'\xff\xfe', b'\xfe\xff')):
        encodings = ["utf-16"]
    for candidate in encodings:
        try:
            return raw.decode(candidate), candidate
        except UnicodeDecodeError:
            pass
    raise ValueError(f"인코딩을 판별할 수 없습니다: {path}\n--encoding 옵션을 지정하세요.")


def collect_files(inputs: list[str], recursive: bool = False) -> list[Path]:
    files = set()
    for item in inputs:
        path = Path(item).expanduser().resolve()
        if path.is_dir():
            candidates = path.rglob('*') if recursive else path.iterdir()
            files.update(p.resolve() for p in candidates if p.is_file() and p.suffix.lower() == '.job')
        elif path.is_file() and path.suffix.lower() == '.job':
            files.add(path)
        else:
            raise ValueError(f"JOB 파일 또는 폴더가 아닙니다: {path}")
    if not files:
        raise ValueError("선택한 경로에 JOB 파일이 없습니다.")
    return sorted(files, key=lambda p: str(p).casefold())
