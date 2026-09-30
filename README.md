# JOB Signal Explorer

현대 로봇 JOB 파일에서 DI/DO 신호와 같은 줄의 주석을 찾아 화면에서 탐색하고 Excel 파일로 저장하는 Windows 데스크톱 도구입니다. 불러온 JOB 파일 사이의 숫자 CALL 관계도 그래프와 호출 내역에서 확인할 수 있습니다. 원본 JOB 파일은 읽기만 합니다.

## 실행

Python 3.10 이상과 tkinter가 포함된 Windows Python을 사용합니다.

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python src\job_signal_viewer.py
```

창 없이 Excel만 만들려면 다음 명령을 사용합니다.

```powershell
.venv\Scripts\python src\job_signal_extractor.py tests\fixtures\sample.job -o sample.xlsx
```

입력 폴더와 여러 JOB 파일도 지정할 수 있습니다. 자세한 사용법은 [탐색기 안내](docs/탐색기_사용방법.md)와 [추출기 안내](docs/사용방법.md)를 참고하세요.

## 테스트와 EXE 빌드

```powershell
.venv\Scripts\python -m unittest discover -s tests -p "test_*.py" -v
.venv\Scripts\python -m pip install pyinstaller
.venv\Scripts\python -m PyInstaller --noconfirm --clean --distpath dist --workpath .build\pyinstaller packaging\JOB_Signal_Explorer.spec
.venv\Scripts\python -m unittest discover -s tests -p "test_*.py" -v
```

두 번째 테스트 실행은 `dist\JOB_Signal_Explorer.exe`의 자체 검사까지 포함합니다. 배포 ZIP과 소스 ZIP이 필요하면 `.venv\Scripts\python packaging\package_release.py`를 실행하세요. 산출물은 `dist\`에 생성됩니다. [빌드 안내](docs/빌드방법.md)에 세부 내용이 있습니다.

## 디렉터리

| 위치 | 내용 |
| --- | --- |
| `src/` | GUI와 추출기 소스 |
| `tests/fixtures/` | 공개 가능한 가상 JOB 테스트 데이터 |
| `tests/` | 추출, 화면, 작업 흐름, EXE 검사 |
| `packaging/` | PyInstaller 설정, Tcl/Tk 훅, 배포 스크립트 |
| `docs/` | 사용 및 빌드 안내 |
| `dist/`, `.build/` | 새 빌드 산출물; Git 제외 |
| `outputs/`, `work/` | 이전 작업물 원본 보존; Git 제외 |

프로젝트 라이선스는 아직 정하지 않았습니다.
