# 원본 대응 및 검증 결과

원본 저장소: https://github.com/alexyc9381/hiring-panel-skill
기준 커밋: `3ec597eb85a904efd17f9171e18f1b8d9dfe4e1a`
2026-10-22 원격 HEAD도 이 커밋임을 읽기 전용 Git 조회로 확인했습니다.

| 원본 | Codex 치환 |
|---|---|
| Claude Code | Codex |
| `/hiring-panel` | `$hiring-panel` |
| `~/.claude/skills/hiring-panel/` | 프로젝트 `.agents/skills/hiring-panel/` |
| Claude 하위 에이전트 | 독립 Codex 하위 에이전트 |
| 7개 역할·평가 기준·판정 | 동일 |
| 5명 독립 동시 평가 | 동일 |
| 재검사 포함 8회 호출 | 동일 |
| 문제 통합·수정 규칙·결과 파일 | 동일 |
| 저작권·결과 파일 크레딧 | 원문 그대로 보존 |
| Claude marketplace 설치 | Codex 프로젝트 스킬 설치기로 치환 |

## 완료한 검증

- 원본 1~7단계·Rules 전체: 호출 표기 치환 후 문자열 일치.
- 라이선스: 원문 보존, 설치본과 배포본 바이트 일치.
- 설치: 빈 프로젝트 최초 설치, 동일 파일 반복 설치, 수정된 기존 파일 덮어쓰기 거부.
- Codex 0.163.0 app-server `skills/list`: 새 서버에서 설치 경로의 hiring-panel을 enabled 상태로 발견함을 확인. 모델 호출 없이 실제 Codex 검색 API로 검증.
- 실제 지원서 평가: 초기 자동 검사·면접 판단, 독립 평가자 5명, 수정본 자동 검사 총 8회 독립 호출 및 두 결과 파일 생성.

스킬 발견 검증을 일반 샌드박스에서 실행할 때 Codex 상태 디렉터리가 읽기 전용이라 서버 시작이 실패했습니다. 동일 검증을 허용된 실행 권한으로 재실행해 통과했습니다. 스킬 파일을 바꾸거나 검증을 우회하지 않았습니다.

## 범위

원본에는 수치 점수나 고정 정답이 없습니다. 검증한 동일성은 지침·역할·순서·독립성·출력 요건입니다. 모델 출력 자체의 일치, 실제 채용 ATS 동작, 사용자 컴퓨터 설치, GitHub 업로드는 별개의 확인 대상입니다. GitHub Actions는 구성만 완료했으며 원격 실행 결과는 아직 없습니다.

GitHub API 호출은 Forbidden으로 거부되었으나, 사용자 지정 저장소 `https://github.com/junjara1005-design/-.git`의 Git 읽기 접근은 재확인 후 성공했습니다. Git 전송 경로를 사용하며 GitHub API 권한을 전제로 하지 않습니다. 원격 Actions 실행 결과는 별도 확인 대상입니다.
