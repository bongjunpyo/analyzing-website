# analyzing-website

공모전/경진대회 공고 URL을 받아 **Claude**로 공고 정보를 구조화 추출하고,
2026 기술 트렌드 적합도와 경쟁력 있는 아이디어를 분석한 뒤 **옵시디언 러닝 로그**에 기록하는 CLI.

하드코딩된 대회/파트너사 URL 없음 — 어떤 공고 페이지에도 동작.

## Claude Code 스킬로 사용

레포 루트의 `SKILL.md` 가 이 도구를 Claude Code 스킬로 노출한다. 설치:

```bash
git clone https://github.com/bongjunpyo/analyzing-website.git ~/analyzing-website
ln -s ../../analyzing-website ~/.claude/skills/analyzing-website
```

기본 동작은 **무크레딧 모드** — `fetch_text.py` 로 본문만 뽑아 Claude 가 직접 분석하고
`log_result.py` 로 기록하므로 Anthropic API 키·크레딧이 필요 없다.
크레딧이 있으면 `analyze_competition.py` 로 전 과정을 자동화할 수 있다(아래 CLI 사용법).

## 흐름

```
fetch_url(Playwright 렌더링) -> extract_text(BeautifulSoup 본문) ->
analyze(Claude json_schema 구조화 + 프롬프트 캐싱) ->
[--md 마크다운 출력] / [--obsidian 러닝 로그 업서트] / 기본 JSON
```

## 파일

- `SKILL.md` — Claude Code 스킬 정의(무크레딧 모드 기본, API 모드 대안)
- `fetch_text.py` — URL -> 본문 텍스트(stdout). API 키 불필요
- `log_result.py` — 결과 JSON -> 옵시디언 로그 업서트. API 키 불필요
- `analyze_competition.py` — 분석 코어 + CLI
  - `fetch_url(url)`: Playwright(chromium)로 렌더링된 HTML
  - `extract_text(html, max_chars=16000)`: 본문 텍스트 추출(토큰 절약)
  - `analyze(client, model, url, text, want_ideas)`: Claude 구조화 분석
    (시스템 프롬프트 ephemeral 캐싱, adaptive thinking, json_schema 출력)
- `obsidian_log.py` — 옵시디언 단일 러닝 로그 기록(표준 라이브러리만)
  - `render_section(result, url, today)`: 사람이 읽는 마크다운 섹션
  - `append_to_log(result, url, today, log_path)`: 같은 URL이면 교체(업서트) + 상단 인덱스 표 재생성
- `report.py` — 러닝 로그를 파싱해 수집 통계 리포트 생성(표준 라이브러리만)
- `tests/` — pytest (네트워크/크레딧 불필요한 순수 함수 검증)

> `extract_text`, `analyze`, `fetch_url`는 `contest_hunter` 패키지가 공유하므로 시그니처를 보존한다.

## 분석 출력 (json_schema)

공고 정보(title/host/organizer/categories/eligibility/period/deadline/prizes/
submissions/judging_criteria/schedule/contact/summary)에 더해:

- `deadline_iso`: 마감일 `YYYY-MM-DD`(불명확 시 `""`) — D-day 계산용
- `trend_fit`: `{ score(0-100), aligned_trends[], angle }` — 2026 트렌드 적합도
- `ideas[]`: `{ title, description, tech_stack[], trend_anchor, flow_diagram }`

트렌드 레퍼런스(고정): 에이전틱 AI / 멀티모달 / 온디바이스·sLM / RAG / 공공데이터×AI / 오픈소스·MCP.

## 옵시디언 러닝 로그

`--obsidian` 사용 시 분석 결과를 단일 노트에 누적한다.
- 기본 경로: `~/Documents/Obsidian Vault/공모전/_분석로그.md`
- 구조: frontmatter(`tags: [공모전, 분석로그]`) + **상단 인덱스 표**(마감 임박순) + 공고별 섹션
- **업서트**: 같은 URL을 다시 분석하면 해당 섹션만 교체(중복 없음), 인덱스 표 자동 재생성
- 섹션 식별/메타는 `<!-- src: ... -->` `<!-- meta: ... -->` 주석으로 저장(프리뷰에 안 보임)

## 통계 리포트

`report.py`는 누적된 러닝 로그(`_분석로그.md`)를 파싱해 **수집 공고 통계**를 마크다운으로 출력한다.
네트워크·API 키 불필요(순수 파싱). 집계 항목:

- **분야별 건수** — 각 공고의 `- 부문:` 라인 기준
- **상금 분포** — 섹션 본문 원문 금액 표현을 정규식으로 추출(억/천만/만원 → 만원 단위), 최대 금액 기준(휴리스틱)
- **마감 D-day 분포** — `deadline_iso`와 기준일로 임박/D-8~30/D-31~90/D-90 초과/마감됨/미정 버킷
- **트렌드 적합도 분포** — `trend_fit.score` 90-100/70-89/50-69/50 미만 버킷

```bash
# 기본 로그(~/Documents/Obsidian Vault/공모전/_분석로그.md) 리포트
python report.py

# 로그 경로 지정 → 파일로 저장
python report.py /path/to/_분석로그.md > 통계리포트.md
```

## 설치

```bash
pip install -r requirements.txt
playwright install chromium
```

## 사용법

```bash
export ANTHROPIC_API_KEY="sk-ant-..."

# 기본: JSON 출력
python analyze_competition.py <URL>

# 마크다운 리포트 출력
python analyze_competition.py <URL> --md

# 옵시디언 러닝 로그에 업서트(기본 볼트)
python analyze_competition.py <URL> --obsidian

# 로그 경로 지정
python analyze_competition.py <URL> --obsidian /path/to/_분석로그.md

# 기타: --model <id>(기본 claude-opus-4-8), --no-ideas, --raw out.txt
```

## 테스트

```bash
python -m pytest tests/ -q
```

## 의존성

| 구분 | 기술 |
|------|------|
| 언어 | Python 3.x |
| 모델 | Claude (Anthropic, 기본 `claude-opus-4-8`) |
| 렌더링 | Playwright (chromium) |
| 파싱 | BeautifulSoup4 |
| 출력 | JSON / Markdown / Obsidian note |

## 주의

- ANTHROPIC_API_KEY 및 크레딧 필요
- 웹사이트 robots.txt 준수
