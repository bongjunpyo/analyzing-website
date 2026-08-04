#!/usr/bin/env python3
"""공고 URL -> 본문 텍스트(stdout). API 키·크레딧 불필요.

무크레딧 모드용 진입점: 렌더링·본문추출만 코드가 하고, 분석은 호출한 쪽(Claude)이 직접 한다.

  ~/venv/bin/python fetch_text.py "<URL>" [--max-chars 16000]
"""
import argparse
import asyncio
import sys

from analyze_competition import MAX_CHARS, extract_text, fetch_url


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="공고 URL -> 본문 텍스트")
    ap.add_argument("url")
    ap.add_argument("--max-chars", type=int, default=MAX_CHARS,
                    help=f"본문 상한 (기본 {MAX_CHARS})")
    return ap


async def main() -> None:
    args = build_parser().parse_args()
    html = await fetch_url(args.url)
    text = extract_text(html, args.max_chars)
    if not text:
        print("본문 추출 실패", file=sys.stderr)
        sys.exit(1)
    print(text)


if __name__ == "__main__":
    asyncio.run(main())
