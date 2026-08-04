#!/usr/bin/env python3
"""분석 결과 JSON -> 옵시디언 러닝 로그 업서트. API 키·크레딧 불필요.

무크레딧 모드용 진입점: 호출한 쪽(Claude)이 만든 결과 dict를 그대로 기록한다.
스키마는 analyze_competition.SCHEMA 와 동일.

  ~/venv/bin/python log_result.py result.json --url "<URL>"
  ~/venv/bin/python log_result.py - --url "<URL>" --md   # stdin, 기록 없이 마크다운만
"""
import argparse
import datetime as dt
import json
import sys
from urllib.parse import urlparse

import obsidian_log

REQUIRED = ("title", "summary")


def load_result(path: str) -> dict:
    """결과 JSON 로드 + 최소 검증. 빈 껍데기가 로그에 들어가는 사고를 막는다."""
    if path == "-":
        raw = sys.stdin.read()
    else:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("결과 JSON은 객체여야 합니다")
    missing = [k for k in REQUIRED if not str(result.get(k, "")).strip()]
    if missing:
        raise ValueError(f"필수 필드 누락: {', '.join(missing)}")
    return result


def check_url(url: str) -> str:
    """업서트 키이자 로그에 링크로 박히는 값이므로 http(s)만 허용."""
    if urlparse(url).scheme.lower() not in ("http", "https"):
        raise ValueError(f"http/https URL만 허용됩니다: {url!r}")
    return url


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="분석 결과 JSON -> 옵시디언 러닝 로그 업서트")
    ap.add_argument("result", help="결과 JSON 파일 경로 ('-'면 stdin)")
    ap.add_argument("--url", required=True, help="공고 URL (업서트 키)")
    ap.add_argument("--log", default=None, metavar="PATH", help="로그 경로 (기본 볼트)")
    ap.add_argument("--date", default=None, metavar="YYYY-MM-DD", help="기준일 (기본 오늘)")
    ap.add_argument("--md", action="store_true", help="기록하지 않고 마크다운 섹션만 출력")
    return ap


def main() -> None:
    args = build_parser().parse_args()
    try:
        url = check_url(args.url)
        result = load_result(args.result)
        today = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"입력 오류: {e}", file=sys.stderr)
        sys.exit(1)

    if args.md:
        print(obsidian_log.render_section(result, url, today))
        return

    path = obsidian_log.append_to_log(result, url, today, args.log or obsidian_log.DEFAULT_LOG)
    print(f"옵시디언 로그 기록: {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
