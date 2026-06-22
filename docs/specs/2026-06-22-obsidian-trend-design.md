# 설계: analyze_competition 옵시디언 연결 + 트렌드 분석 고도화

작성일: 2026-06-22

## 목표
공모전 공고 분석 CLI(`analyze_competition.py`)에 (1) 옵시디언 단일 러닝 로그 기록,
(2) 2026 트렌드 매핑 분석을 추가한다. Claude 전용으로 통일(Gemini 잔재 제거).
`contest_hunter` 패키지가 공유하는 함수 시그니처는 100% 보존한다.

## 제약 (불변)
- `fetch_url(url)`, `extract_text(html, max_chars=MAX_CHARS)`,
  `analyze(client, model, url, text, want_ideas)` 시그니처 유지.
  → `contest_hunter/research.py`, `config.py`가 import.
- 스키마 변경은 **추가만**(additive). 기존 키/필수항목 유지 → 출력 소비측 안전.
- 기본 CLI 동작(JSON stdout)과 기존 플래그(`--model/--no-ideas/--raw`) 불변.
- GitHub PAT 등 비밀값은 코드/노트/문서에 절대 미포함.

## 변경 1 — 스키마/프롬프트 고도화 (`analyze_competition.py`)
추가 필드:
- `deadline_iso`: `string` (`YYYY-MM-DD`, 불명확 시 `""`). D-day 계산 입력.
- `trend_fit`: `object`
  - `score`: `integer` (0-100, 공고 주제의 현재 트렌드 적합도)
  - `aligned_trends`: `array[string]` (공고와 맞닿는 현재 트렌드)
  - `angle`: `string` (트렌드 활용 차별화 앵글, 1-2문장)
- `ideas[].trend_anchor`: `string` (각 아이디어가 올라탄 트렌드)

`SYSTEM_PROMPT`에 2026 트렌드 레퍼런스 목록 주입(고정 텍스트, 웹검색 없음):
에이전틱 AI / 멀티모달 / 온디바이스·sLM / RAG / 공공데이터×AI / 오픈소스·MCP.
기존 규칙("본문 명시 정보만, 추측 금지, 원문 수치·날짜 보존") 유지.
`deadline_iso`는 본문의 마감 표현을 ISO로 재포맷할 뿐, 추측으로 만들지 않는다.

## 변경 2 — 마크다운 렌더러 + 러닝 로그 (신규 `obsidian_log.py`)
- `render_section(result, url, today) -> str`
  분석 결과 1건을 사람이 읽는 마크다운 섹션으로.
  구성: 헤딩(제목) / 메타블록(주최·주관·마감 D-day·트렌드적합 score) /
  요약 / 부문·자격 / 심사기준 / 제출물 체크리스트(`- [ ]`) /
  트렌드 적합(aligned_trends + angle) / 아이디어(설명·tech_stack·trend_anchor·ASCII 흐름) /
  `source:` URL 푸터(업서트 식별자).
- `dday(deadline_iso, today) -> str` 헬퍼: `D-7` / `D-DAY` / `마감(+n)` / `""`.
- `append_to_log(result, url, today, log_path) -> Path`
  - 기본 경로: `~/Documents/Obsidian Vault/공모전/_분석로그.md` (없으면 생성).
  - 파일 구조:
    1. frontmatter `tags: [공모전, 분석로그]`
    2. 상단 인덱스 표: `| 제목 | 마감(D-day) | 트렌드 | 링크 | 분석일 |`,
       마감 임박순 정렬(미상은 뒤).
    3. 하단 섹션들(`<!-- src: <url> -->` 마커로 구분).
  - **업서트**: 같은 URL 섹션이 있으면 교체(중복 방지), 없으면 추가.
    그 후 모든 섹션을 스캔해 인덱스 표를 재생성.
  - 파싱은 마커(`<!-- src: ... -->`) 기준 단순 분할. 외부 의존 없음(표준 라이브러리만).

## 변경 3 — CLI 플래그 (`analyze_competition.py`)
- `--obsidian [PATH]`: 분석 후 러닝 로그에 업서트. PATH 생략 시 기본 볼트 경로.
- `--md`: JSON 대신 `render_section` 마크다운을 stdout 출력.
- `--obsidian`와 `--md` 미지정 시: 기존대로 JSON stdout(하위호환).

## 변경 4 — Gemini 제거 / 문서 정합
- 코드·의존성은 이미 Claude 전용(확인됨). README의 "Claude Haiku" 표기를
  실제 기본값(`claude-opus-4-8`)과 일치시키고, 옵시디언·트렌드·신규 플래그 사용법 추가.
- origin/main(구 Gemini 커밋)은 이번 Claude 작업트리 커밋으로 대체.

## 검증
- 실제 공고 URL 1건으로:
  - `--obsidian` 1회 → 로그 파일·인덱스 표·섹션 생성 확인.
  - 같은 URL `--obsidian` 재실행 → 섹션 1개 유지(업서트, 중복 없음) 확인.
  - `--md` → 마크다운 섹션 stdout 확인.
- 스모크: `from analyze_competition import extract_text, analyze, fetch_url` 정상 import.
- (네트워크/크레딧 불가 시) `render_section`·`append_to_log`·`dday`를 더미 result dict로 단위 확인.

## 산출물
- `analyze_competition.py` (스키마·프롬프트·CLI 갱신)
- `obsidian_log.py` (신규)
- `README.md` (갱신)
- 1커밋으로 `main` 푸시.
