# 이력서 검토 — Codex Hiring Panel

Alex Chen의 MIT `hiring-panel-skill`을 Codex용으로 치환한 스킬입니다. 원본 1~7단계와 Rules 전체를 유지하고, 명령·에이전트 실행 방식만 Codex에 맞췄습니다. 별도 웹앱이 아니라 Codex에서 실행하는 스킬입니다.

## 바로 시작

현재 클라우드에는 `/workspace/resume-hiring-panel/.agents/skills/hiring-panel/`에 설치되어 있습니다. 이 폴더를 작업 폴더로 선택한 Codex 세션에서 다음과 같이 요청하세요.

```text
$hiring-panel my-resume.pdf
지원 직무: 모트라스 평택2공장 안전보건
채용 공고: 공고 본문
```

현재 대화에서는 “설치한 hiring-panel 스킬로 이 지원서를 평가해 줘”라고 요청할 수도 있습니다. 실제 지원서로 독립 하위 에이전트 8회 호출과 두 결과 파일 생성을 확인했습니다.

## 다른 컴퓨터·프로젝트에 설치

Codex가 설치·로그인된 환경에서 이 프로젝트를 내려받거나 압축을 해제하세요.

```bash
git clone https://github.com/junjara1005-design/-.git resume-review
cd resume-review
```

Python 3로 아래 명령을 실행하면 지정 프로젝트에만 스킬을 설치합니다.

```bash
python3 scripts/install.py --project /path/to/resume-folder
cd /path/to/resume-folder
codex
```

경로에 공백이 있으면 따옴표로 감싸세요. Windows에서는 `python3` 대신 `python` 또는 `py`를 사용할 수 있습니다. 설치기는 기존 스킬이 다르면 덮어쓰지 않고 중단합니다. 같은 파일이면 재설치해도 변경하지 않습니다. 자동 승인·권한 우회·전역 설정 변경은 수행하지 않습니다. 이 클라우드 설치가 사용자 컴퓨터에도 자동 설치되는 것은 아닙니다.

새 세션에서 `hiring-panel`이 스킬 목록에 있는지 확인하세요. 자동 인식 검증 명령은 다음과 같습니다. Codex CLI app-server와 정상적인 로컬 상태 디렉터리 쓰기 권한이 필요합니다. 모델 호출이나 이력서 전송은 하지 않습니다.

```bash
python3 scripts/check_discovery.py
```

## 동일한 심사 흐름

1. 이력서와 직무 확인. 직무가 없으면 한 번 질문.
2. 자동 서류 검사 1명: 읽기 순서, 경력·날짜, 공고 키워드, 연락처·분량. PASS/REJECT와 최대 5개 인용 근거.
3. 면접 관리자 1명: INTERVIEW/NO, 첫 10초의 결정 요인, 면접 질문, 가장 약한 문장 3개.
4. 팀장·경쟁 지원자·CEO·채용 담당자·동료 5명을 동시 실행. 서로 의견을 보지 않고 각각 120단어 미만, HIRE/MAYBE/PASS와 인용·문제점 제출. 여기서 PASS는 후보를 넘긴다는 뜻입니다.
5. 7명 의견의 중복을 합쳐 중요한 문제부터 정리.
6. 원본 사실만으로 수정. 모르는 사실은 `[ADD: ...]`, 추정은 `assumed`. 새 자동 검사자로 수정본 재검사.
7. `.hiring-panel/날짜-이름/`에 `PANEL.md`, `RESUME-IMPROVED.md` 저장. 원본 보존.

총 하위 에이전트 호출은 8회입니다. 독립 에이전트 동시 실행을 지원하는 Codex 환경이 필요합니다. 이를 지원하지 않으면 한 모델의 역할극으로 대체하지 않고 실행 제한을 보고합니다. 결과 문구·판정은 모델과 입력에 따라 달라지며, 동일성은 평가 지침과 실행 절차를 기준으로 검증합니다.

## 가이드의 다섯 사용 상황

```text
$hiring-panel my-resume.pdf — 채용 공고: 공고 본문
$hiring-panel my-resume.pdf — 희망 직무: 마케팅, 회사 유형: 제조업
$hiring-panel my-resume.pdf — 생산관리에서 안전관리로 전환하려고 합니다. 경험의 관련성을 평가해 줘.
$hiring-panel my-resume.pdf — 정규직 경력 없는 학생이며 안전보건 직무에 지원합니다.
$hiring-panel 방금 작성한 이력서를 안전보건 직무 기준으로 평가해 줘.
```

마지막 예시는 같은 대화에 이력서가 있을 때만 사용합니다. 이력서에 포함된 자료를 모델이 처리하므로 불필요한 개인정보·회사 기밀은 사본에서 제거하세요. 채용공고가 없으면 공고 필수요건 충족 여부는 판단할 수 없습니다.

## 결과 확인

`PANEL.md`에서 일곱 판정과 중요도순 문제, 자동 검사 전후 결과를 확인하고 `RESUME-IMPROVED.md`를 원문과 비교하세요. 회사·직무·기간·실제 도구·업무·수치를 대조해야 합니다. `[ADD]`를 사실로 보완하거나 해당 문장을 삭제한 뒤 제출하세요. 빈칸이 남은 편집 초안은 제출 준비 완료가 아닙니다. 최종 형식·글자 수는 공고와 채용시스템 기준을 따릅니다. 실제 ATS 통과나 취업을 보장하지 않습니다.

## 검증 및 출처

```bash
python3 -m unittest discover -s tests -v
```

원본 1~7단계·Rules 전체 문자열 대응, MIT 라이선스, 최초·반복 설치와 기존 파일 덮어쓰기 거부를 검사합니다. 상세 결과는 `PARITY.md`에 있습니다. GitHub Actions에서도 같은 테스트를 실행하도록 구성했습니다.

- 원본: https://github.com/alexyc9381/hiring-panel-skill
- 기준 커밋: `3ec597eb85a904efd17f9171e18f1b8d9dfe4e1a`
- 원저작자: Alex Chen (@nocodealex), https://chen.media
- 라이선스: MIT (`LICENSE`)

개인 지원서·평가 결과·PDF는 Git과 배포 압축파일에서 제외합니다. 삭제하려면 설치한 프로젝트의 `.agents/skills/hiring-panel/`만 제거하면 됩니다. 직접 수정한 파일은 먼저 백업하세요. 생성된 `.hiring-panel/` 결과는 별도로 유지됩니다.
