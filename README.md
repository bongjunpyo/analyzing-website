# analyzing-website

경쟁 대회 및 공모전 웹사이트를 분석하여 기술 트렌드를 파악하고 경쟁력 있는 프로젝트 아이디어를 자동으로 생성하는 AI 기반 분석 도구입니다.

## 기능

- **웹 분석**: 대회/공모전 사이트에서 HTML 크롤링 및 텍스트 추출
- **수상 이력 분석**: 과거 입상 프로젝트의 기술 스택 및 분야 분석
- **기술 트렌드 추출**: 사이트에서 언급된 기술 키워드 자동 추출
- **아이디어 생성**: 분석 결과 기반 경쟁력 있는 3가지 프로젝트 아이디어 제시
- **기술 스택 제안**: 각 아이디어별 추천 기술 스택 (임베디드 제외)
- **데이터 흐름도**: ASCII 형식의 시스템 아키텍처 다이어그램 자동 생성
- **토큰 최적화**: Claude Haiku + 프롬프트 캐싱으로 API 비용 최소화

## 파일 설명

### `analyze_competition.py`
메인 분석 스크립트입니다.

**기능:**
- `fetch_url()`: requests 라이브러리로 웹사이트 HTML 다운로드
- `extract_text_from_html()`: BeautifulSoup으로 의미 있는 텍스트만 추출 (토큰 절약)
- `extract_structured_data()`: 수상 이력, 연도, 기술 키워드 정규표현식으로 추출
- `analyze_with_claude()`: Claude Haiku API + 프롬프트 캐싱으로 분석
  - 시스템 프롬프트 캐싱 (ephemeral TTL 5분)
  - max_tokens=1024로 응답 크기 제한
  - JSON 형식 구조화 출력

**출력 형식:**
```json
{
  "awards_analysis": "상위 기술/분야",
  "tech_trends": ["기술1", "기술2", ...],
  "ideas": [
    {
      "title": "아이디어 제목",
      "description": "설명",
      "tech_stack": ["기술1", "기술2", ...],
      "flow_diagram": "ASCII 데이터 흐름도"
    }
  ]
}
```

### `requirements.txt`
필요한 Python 라이브러리입니다.

- `anthropic`: Claude API 호출
- `beautifulsoup4`: HTML 파싱 및 크롤링
- `requests`: HTTP 요청

## 설치

```bash
pip install -r requirements.txt
```

## 환경 설정

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

## 사용법

### 기본 사용

```bash
python3 analyze_competition.py https://www.eswcontest.or.kr/competition/free.php
```

### 출력 예시

```json
{
  "awards_analysis": "임베디드SW, IoT, 스마트가전, 자동차모빌리티",
  "tech_trends": ["AI/ML", "클라우드", "실시간처리"],
  "ideas": [
    {
      "title": "스마트홈 에너지관리 AI시스템",
      "description": "가전기기 전력사용 최적화",
      "tech_stack": ["Python", "TensorFlow", "AWS IoT", "React"],
      "flow_diagram": "가전 → MQTT → AWS → ML분석 → 제어"
    }
  ]
}
```

## 토큰 효율성

### 최적화 전략

1. **모델 선택**: Claude Haiku (저비용, 고속)
2. **프롬프트 캐싱**: 시스템 프롬프트 ephemeral 캐싱으로 반복 분석 시 비용 60% 감소
3. **텍스트 제한**: HTML을 8000자로 제한하여 불필요한 토큰 소비 방지
4. **구조화 출력**: JSON 형식으로 파싱 오류 최소화
5. **응답 크기**: max_tokens=1024로 과도한 출력 방지

### 예상 토큰 사용량

- 첫 요청: ~1200 토큰
- 반복 요청: ~400 토큰 (캐시 재사용)
- 월간 100회 분석: ~$0.15

## 기술 스택

| 구분 | 기술 |
|------|------|
| 언어 | Python 3.8+ |
| API | Claude API (Anthropic) |
| 웹 크롤링 | BeautifulSoup4, Requests |
| 출력 | JSON |

## 주의사항

- API 크레딧 확인 필수
- 웹사이트 robots.txt 준수
- User-Agent 포함으로 호출
