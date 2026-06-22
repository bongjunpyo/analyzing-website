#!/usr/bin/env python3
"""범용 공모전/경진대회 공고 분석 CLI.

URL을 받아 페이지를 렌더링 → 본문 추출 → Claude로 구조화 분석(공고 정보 + 아이디어)
하드코딩된 대회/파트너사/수상이력 URL 없음. 어떤 공모전 공고에도 동작.

  export ANTHROPIC_API_KEY="sk-ant-..."
  python analyze_competition.py <URL> [--model claude-opus-4-8] [--no-ideas] [--raw out.html]
"""
import argparse
import datetime as dt
import json
import sys
import asyncio
from urllib.parse import urlparse

import anthropic
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

DEFAULT_MODEL = "claude-opus-4-8"
MAX_CHARS = 16000

SYSTEM_PROMPT = """\
당신은 공모전/경진대회 공고 분석 전문가다.
주어진 웹페이지 본문에서 공고 정보를 추출하고, 응모자가 참고할 분석을 제공한다.

규칙:
- 본문에 명시된 정보만 추출한다. 추측하지 말고, 없으면 빈 문자열/빈 배열로 둔다.
- 상금/일정/자격 등 수치·날짜는 원문 표현을 보존한다.
- deadline_iso는 본문의 마감 표현을 YYYY-MM-DD로 재포맷할 뿐, 추측으로 만들지 않는다(불명확하면 빈 문자열).
- 아이디어 제안 시 심사 기준과 주최 성격에 맞춰 차별화 포인트를 명시한다.
- 모든 출력은 한국어, ASCII 다이어그램은 단순하게.

트렌드 레퍼런스(2026, trend_fit·아이디어의 trend_anchor 판단 기준):
- 에이전틱 AI(자율 에이전트·툴 호출·워크플로 자동화)
- 멀티모달(이미지/음성/문서 통합)
- 온디바이스·sLM(경량 모델, 프라이버시)
- RAG·지식그라운딩
- 공공데이터×AI(행정·도시문제 해결)
- 오픈소스·MCP(상호운용)
trend_fit.score는 공고 주제가 위 트렌드와 얼마나 맞닿는지 0-100으로, angle은 트렌드를 활용한 차별화 한 수.
각 아이디어의 trend_anchor에는 그 아이디어가 올라탄 트렌드를 한 개 명시한다.
"""

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string", "description": "공모전 제목"},
        "host": {"type": "string", "description": "주최"},
        "organizer": {"type": "string", "description": "주관"},
        "categories": {"type": "array", "items": {"type": "string"}, "description": "응모 부문/주제"},
        "eligibility": {"type": "string", "description": "응모 자격"},
        "period": {"type": "string", "description": "접수 기간"},
        "deadline": {"type": "string", "description": "마감일시(원문 표현)"},
        "deadline_iso": {"type": "string", "description": "마감일 YYYY-MM-DD, 불명확하면 빈 문자열"},
        "prizes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "detail": {"type": "string", "description": "상금/상장/인원 등"},
                },
                "required": ["name", "detail"],
            },
        },
        "submissions": {"type": "array", "items": {"type": "string"}, "description": "제출물"},
        "judging_criteria": {"type": "array", "items": {"type": "string"}, "description": "심사 기준"},
        "schedule": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "phase": {"type": "string"},
                    "date": {"type": "string"},
                },
                "required": ["phase", "date"],
            },
        },
        "contact": {"type": "string", "description": "문의처"},
        "summary": {"type": "string", "description": "핵심 요약 2-3문장"},
        "trend_fit": {
            "type": "object",
            "additionalProperties": False,
            "description": "공고 주제의 현재(2026) 기술 트렌드 적합도",
            "properties": {
                "score": {"type": "integer", "description": "트렌드 적합도 0-100"},
                "aligned_trends": {"type": "array", "items": {"type": "string"}, "description": "맞닿는 트렌드"},
                "angle": {"type": "string", "description": "트렌드 활용 차별화 앵글 1-2문장"},
            },
            "required": ["score", "aligned_trends", "angle"],
        },
        "ideas": {
            "type": "array",
            "description": "심사 기준 기반 경쟁력 있는 아이디어 (요청 시)",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "tech_stack": {"type": "array", "items": {"type": "string"}},
                    "trend_anchor": {"type": "string", "description": "이 아이디어가 올라탄 트렌드 1개"},
                    "flow_diagram": {"type": "string", "description": "ASCII 데이터 흐름도"},
                },
                "required": ["title", "description", "tech_stack", "trend_anchor", "flow_diagram"],
            },
        },
    },
    "required": [
        "title", "host", "organizer", "categories", "eligibility",
        "period", "deadline", "deadline_iso", "prizes", "submissions",
        "judging_criteria", "schedule", "contact", "summary", "trend_fit", "ideas",
    ],
}


async def fetch_url(url: str) -> str:
    """Playwright로 렌더링된 HTML 반환. http(s) 외 스킴은 거부(로컬파일/스킴 악용 방지)."""
    if urlparse(url).scheme.lower() not in ("http", "https"):
        raise ValueError(f"http/https URL만 허용됩니다: {url!r}")
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(args=["--disable-dev-shm-usage"])
        except Exception:
            browser = await p.chromium.launch(args=["--no-sandbox", "--disable-setuid-sandbox"])
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            html = await page.content()
        finally:
            await browser.close()
    return html


def extract_text(html: str, max_chars: int = MAX_CHARS) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    return "\n".join(lines)[:max_chars]


def analyze(client: anthropic.Anthropic, model: str, url: str, text: str, want_ideas: bool) -> dict:
    ideas_req = (
        "심사 기준에 맞춰 경쟁력 있는 아이디어 3개를 ideas에 채워라."
        if want_ideas else
        "ideas는 빈 배열로 둔다."
    )
    user_msg = (
        f"공고 URL: {url}\n\n"
        f"=== 페이지 본문 ===\n{text}\n\n"
        f"위 본문에서 공고 정보를 스키마에 맞게 추출하라. {ideas_req}"
    )
    resp = client.messages.create(
        model=model,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={
            "effort": "medium",
            "format": {"type": "json_schema", "schema": SCHEMA},
        },
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_msg}],
    )
    out = _first_text(resp.content)
    try:
        return json.loads(out)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"구조화 출력 JSON 파싱 실패: {e}") from e


def _first_text(content) -> str:
    """응답 콘텐츠 블록에서 첫 text 블록 반환. 없으면 명확한 에러(StopIteration 방지)."""
    for b in content:
        if getattr(b, "type", None) == "text":
            return b.text
    raise RuntimeError("모델 응답에 text 블록이 없습니다 (거부/토큰 한도/stop_reason 확인).")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="범용 공모전 공고 분석")
    ap.add_argument("url")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--no-ideas", action="store_true", help="아이디어 제안 생략")
    ap.add_argument("--raw", metavar="FILE", help="추출 본문을 파일로 저장")
    ap.add_argument("--md", action="store_true", help="JSON 대신 마크다운 리포트 출력")
    ap.add_argument(
        "--obsidian", nargs="?", const="", default=None, metavar="PATH",
        help="옵시디언 러닝 로그에 업서트 (PATH 생략 시 기본 볼트)",
    )
    return ap


async def main() -> None:
    args = build_parser().parse_args()

    try:
        client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 환경변수 사용
    except Exception as e:
        print(f"클라이언트 초기화 실패 (ANTHROPIC_API_KEY 확인): {e}", file=sys.stderr)
        sys.exit(1)

    print(f"렌더링 중: {args.url}", file=sys.stderr)
    html = await fetch_url(args.url)
    text = extract_text(html)
    if not text:
        print("본문 추출 실패", file=sys.stderr)
        sys.exit(1)
    if args.raw:
        with open(args.raw, "w") as f:
            f.write(text)

    print("Claude 분석 중...", file=sys.stderr)
    result = analyze(client, args.model, args.url, text, not args.no_ideas)

    today = dt.date.today()
    if args.obsidian is not None:
        import obsidian_log
        log_path = args.obsidian or obsidian_log.DEFAULT_LOG
        path = obsidian_log.append_to_log(result, args.url, today, log_path)
        print(f"옵시디언 로그 기록: {path}", file=sys.stderr)
    if args.md:
        import obsidian_log
        print(obsidian_log.render_section(result, args.url, today))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
