---
name: analyzing-website
description: 공모전·경진대회 공고 URL 하나를 받아 구조화 분석(주최/자격/마감/상금/심사기준 + 2026 트렌드 적합도 + 아이디어 3개)하고, 옵시디언 러닝 로그에 업서트하거나 누적 로그의 통계 리포트를 뽑는다. "이 공고 분석해줘", "공모전 링크 분석", "wevity/링커리어 URL 정리해줘", "분석로그 통계", "지금까지 모은 공모전 요약" 같은 요청에 반드시 사용하고, 사용자가 공고 페이지 URL을 그냥 붙여넣기만 해도 이 스킬을 쓴다. 마감일 계산·트렌드 점수·상금 분포가 필요한 모든 경우에 해당한다.
---

# analyzing-website

공고 **URL 1개**를 분석해 구조화 결과를 내고, 옵시디언 단일 로그에 누적한다.
코드는 이 스킬 디렉터리 = `~/analyzing-website` (github.com/bongjunpyo/analyzing-website).

## contest-hunter 와의 경계

두 스킬은 코드를 공유하지만 하는 일이 다르다. 먼저 갈라라.

| 요청 | 스킬 |
|------|------|
| "공모전 찾아줘", "이번주 공모전" (발굴 + 서류작성) | `contest-hunter` |
| URL 주고 "이거 분석해줘" / 로그 누적 / 통계 | **이 스킬** |

발굴 후 개별 공고를 로그에 남기고 싶으면 contest-hunter 로 찾고 이 스킬로 기록한다.

## 기본 경로: 무크레딧 모드

**분석은 네가 직접 한다.** 코드는 렌더링·본문추출과 기록만 맡는다 — Anthropic API 키도 크레딧도 안 쓴다.
작업 디렉터리는 항상 `~/analyzing-website` (모듈이 서로를 상대 import 한다).

### 1) 본문 추출

```bash
cd ~/analyzing-website && ~/venv/bin/python fetch_text.py "<URL>"
```

stdout 으로 본문 텍스트가 나온다. 이걸 읽는다.

### 2) 아래 계약대로 결과 JSON 작성

임시 파일에 쓴다(스크래치패드 등, 볼트 안에 두지 말 것).

```jsonc
{
  "title": "", "host": "주최", "organizer": "주관",
  "categories": [], "eligibility": "", "period": "접수 기간",
  "deadline": "원문 표현 그대로", "deadline_iso": "YYYY-MM-DD 또는 \"\"",
  "prizes": [{"name": "", "detail": "상금/상장/인원"}],
  "submissions": [], "judging_criteria": [],
  "schedule": [{"phase": "", "date": ""}],
  "contact": "", "summary": "핵심 요약 2-3문장",
  "trend_fit": {"score": 0, "aligned_trends": [], "angle": "차별화 앵글 1-2문장"},
  "ideas": [{"title": "", "description": "", "tech_stack": [],
             "trend_anchor": "올라탄 트렌드 1개", "flow_diagram": "ASCII 흐름도"}]
}
```

지켜야 할 규칙 — 이게 이 도구의 신뢰도를 만든다:

- **본문에 있는 것만 쓴다.** 추측하지 말고, 없으면 빈 문자열/빈 배열로 둔다. 로그는 나중에 의사결정 근거로 쓰이므로, 그럴듯하게 채운 값이 없는 값보다 훨씬 해롭다.
- **상금·일정·자격의 수치와 날짜는 원문 표현을 보존한다.** `deadline` 은 원문 그대로, `deadline_iso` 는 그걸 `YYYY-MM-DD` 로 재포맷할 뿐이다. 마감이 애매하면(예: "추후 공지", "11월 중") `deadline_iso` 는 빈 문자열로 두라 — 빈 값은 통계에서 "미정"으로 정상 처리되지만, 지어낸 날짜는 D-day 정렬을 통째로 망친다.
- **아이디어 3개**는 그 공고의 `judging_criteria` 와 주최 성격에 맞춰 차별화 포인트를 명시한다. 일반론적인 AI 아이디어를 붙여넣지 말 것.
- **`summary` 에 대표 상금 금액을 원문 표현으로 넣어라**(예: "대상 1000만원"). 로그 섹션에는 `prizes` 배열이 렌더링되지 않아서, `report.py` 의 상금 분포는 `summary` 본문에서 금액을 긁는다. 여기 빠뜨리면 그 공고는 통계에서 "미상"으로 빠진다.
- 출력은 한국어, `flow_diagram` 은 단순한 ASCII.

`trend_fit` / `trend_anchor` 판단 기준 트렌드(2026, 고정 6종):
에이전틱 AI(자율 에이전트·툴 호출·워크플로 자동화) / 멀티모달 / 온디바이스·sLM / RAG·지식그라운딩 / 공공데이터×AI / 오픈소스·MCP.
`score` 는 공고 주제가 이 트렌드들과 얼마나 맞닿는지 0-100, `angle` 은 트렌드를 활용한 차별화 한 수.

### 3) 로그에 기록

```bash
~/venv/bin/python log_result.py /path/to/result.json --url "<URL>"
```

부가 플래그: `--md` (기록 없이 마크다운 섹션만 stdout — 대화창에 보여줄 때),
`--log /경로/파일.md` (기본 볼트 대신 다른 로그), `--date YYYY-MM-DD` (기준일 고정).
`-` 를 파일 대신 주면 stdin 으로 받는다.

## 대안: API 자동 모드 (크레딧 필요)

전 과정을 코드가 한 번에 돌린다. 사용자가 "자동으로", "API로" 라고 하거나 대량 처리일 때만 쓴다.

```bash
cd ~/analyzing-website && source ~/.anthropic_key
~/venv/bin/python analyze_competition.py "<URL>" --obsidian   # 로그 업서트
~/venv/bin/python analyze_competition.py "<URL>" --md         # 마크다운만
~/venv/bin/python analyze_competition.py "<URL>"              # 원시 JSON
```

부가 플래그: `--no-ideas`, `--raw out.txt`, `--obsidian /경로/파일.md`, `--model <id>`.
기본 모델은 `claude-opus-4-8`. 사용자가 요청하지 않는 한 레포 기본값을 임의로 바꾸지 말 것.
키를 프롬프트나 커맨드라인에 노출하지 말고 반드시 `source ~/.anthropic_key` 로 넣는다.

## 통계 리포트 (무료)

```bash
~/venv/bin/python report.py                    # 기본 볼트 로그
~/venv/bin/python report.py /경로/_분석로그.md   # 경로 지정
```

누적 로그를 파싱해 분야별 건수 / 상금 분포 / 마감 D-day 분포 / 트렌드 점수 분포를 낸다. 네트워크·API 불필요.

상금 분포는 섹션 본문의 금액 표현을 정규식으로 긁는 **휴리스틱**이다(억/천만/만원 → 만원 단위, 최댓값 기준).
`prizes` 배열은 로그에 렌더링되지 않으므로 실질적으로 `summary` 의 금액 표현에 의존한다 — "미상" 비율이 높으면
집계가 안 된 것이지 상금이 없는 게 아니다. 정확한 상금이 중요한 자리면 원문 공고를 재확인하라고 덧붙여라.

## 사용자에게 보고할 때

전체 JSON을 쏟지 마라. **제목 / 마감 D-day / 상금 / 트렌드 점수 / 아이디어 제목 3개**만 요약하고 로그 경로를 알려준다.
전문이 필요하면 `--md` 로 마크다운을 보여준다.

## 옵시디언 로그

- 기본 경로: `~/Documents/Obsidian Vault/공모전/_분석로그.md` (없으면 첫 실행 때 생성)
- **URL 기준 업서트**다. 같은 공고를 다시 분석하면 그 섹션만 교체되고 중복이 안 생긴다 —
  "정보가 바뀐 것 같다" 싶으면 그냥 다시 돌려라. 수동으로 지울 필요 없다.
  단 업서트 키가 URL 문자열이므로, 같은 공고라도 쿼리스트링이 다르면 별개 섹션이 된다. 재분석 때는 처음 쓴 URL을 그대로 쓴다.
- 상단 인덱스 표는 마감 임박순으로 매번 재생성된다.
- 섹션 식별자는 `<!-- src: ... -->` / `<!-- meta: ... -->` HTML 주석이다.
  **이 줄을 사람이 편집하거나 지우면 업서트와 통계가 깨진다** — 로그를 손으로 고칠 일이 있으면 본문만 건드려라.

## 막히는 지점

| 증상 | 원인 / 대응 |
|------|------------|
| `본문 추출 실패` | JS 렌더 후에도 텍스트가 없는 페이지(이미지 공고, iframe). 사용자에게 공고 본문을 직접 받아라 |
| `http/https URL만 허용됩니다` | 의도된 차단. `file:` 등 다른 스킴은 안 받는다 |
| goto timeout (30s) | `wait_until="networkidle"` 이라 광고·트래커 많은 페이지에서 난다. 재시도하거나 다른 링크를 요청 |
| `필수 필드 누락` (log_result) | 결과 JSON 의 `title`/`summary` 가 비었다. 본문 추출이 실패했는데 억지로 채운 건 아닌지 먼저 의심하라 |
| 본문이 16000자에서 잘림 | `extract_text` 의 의도된 상한(토큰 절약). 뒷부분에 심사기준이 있는 긴 공고면 `--max-chars` 를 올리고 사용자에게 알려라 |
| 인증/401 (API 모드) | `source ~/.anthropic_key` 를 빠뜨린 것 |

## 코드 수정 시

`fetch_url` / `extract_text` / `analyze` 시그니처는 `contest_hunter` 패키지(`~/contest_hunter`)가 그대로 갖다 쓴다.
바꾸면 contest-hunter 스킬이 깨지므로 시그니처는 보존하고, 수정 후 `~/venv/bin/python -m pytest tests/ -q` 를 돌려라(현재 49 passed).
버그를 잡으면 `docs/PITFALLS.md` 에 증상/원인/어떻게잡혔나/다음에 형식으로 적립한다(없으면 새로 만든다).
