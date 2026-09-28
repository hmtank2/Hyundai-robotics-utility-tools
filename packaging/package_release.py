"""Create release archives from a built EXE and the repository sources."""

from __future__ import annotations

import hashlib
import importlib.metadata as metadata
import shutil
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
EXE = DIST / 'JOB_Signal_Explorer.exe'
RELEASE = DIST / 'release'


def add_license(source: Path, label: str, destination: Path) -> None:
    if source.is_file():
        shutil.copy2(source, destination / label)


def main() -> None:
    if not EXE.is_file():
        raise FileNotFoundError(f'Build the EXE first: {EXE}')

    licenses = RELEASE / 'licenses'
    licenses.mkdir(parents=True, exist_ok=True)
    shutil.copy2(EXE, RELEASE / EXE.name)
    shutil.copy2(ROOT / 'docs' / '탐색기_사용방법.md', RELEASE / '사용방법.txt')

    runtime = Path(sys.base_prefix)
    for label, source in (
        ('Python.txt', runtime / 'LICENSE.txt'),
        ('Tcl.txt', runtime / 'tcl' / 'tcl8.6' / 'license.terms'),
        ('Tk.txt', runtime / 'tcl' / 'tk8.6' / 'license.terms'),
    ):
        add_license(source, label, licenses)
    for package in ('openpyxl', 'et_xmlfile', 'pillow', 'lxml', 'pyinstaller'):
        try:
            distribution = metadata.distribution(package)
        except metadata.PackageNotFoundError:
            continue
        for item in distribution.files or []:
            if '.dist-info' in str(item) and ('license' in item.name.lower() or 'copying' in item.name.lower()):
                add_license(Path(distribution.locate_file(item)), f'{package}_{item.name}.txt', licenses)

    distribution_zip = DIST / 'JOB_Signal_Explorer_배포.zip'
    with zipfile.ZipFile(distribution_zip, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(RELEASE.rglob('*')):
            if path.is_file():
                archive.write(path, path.relative_to(RELEASE))

    source_zip = DIST / 'JOB_Signal_Explorer_소스.zip'
    source_files = [ROOT / '.gitignore', ROOT / 'README.md', ROOT / 'requirements.txt']
    for directory in ('src', 'tests', 'packaging', 'docs'):
        source_files.extend(
            path for path in (ROOT / directory).rglob('*')
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc'
        )
    with zipfile.ZipFile(source_zip, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_files):
            archive.write(path, path.relative_to(ROOT))

    for archive_path in (distribution_zip, source_zip):
        with zipfile.ZipFile(archive_path) as archive:
            assert archive.testzip() is None
    print('EXE SHA256:', hashlib.sha256(EXE.read_bytes()).hexdigest())
    print('Created:', distribution_zip)
    print('Created:', source_zip)


if __name__ == '__main__':
    main()
