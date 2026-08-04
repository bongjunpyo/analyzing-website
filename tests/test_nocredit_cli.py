"""무크레딧 모드 진입점(fetch_text / log_result) 검증. 네트워크·API 불필요."""
import datetime as dt
import json

import pytest

import fetch_text
import log_result
import obsidian_log

RESULT = {
    "title": "테스트 공모전",
    "summary": "요약",
    "host": "주최사",
    "deadline_iso": "2026-09-01",
    "trend_fit": {"score": 80, "aligned_trends": ["RAG"], "angle": "앵글"},
    "ideas": [],
}


# --- fetch_text ---

def test_fetch_text_defaults_to_module_cap():
    a = fetch_text.build_parser().parse_args(["http://x"])
    assert a.max_chars == fetch_text.MAX_CHARS


def test_fetch_text_max_chars_override():
    a = fetch_text.build_parser().parse_args(["http://x", "--max-chars", "500"])
    assert a.max_chars == 500


# --- log_result: 입력 검증 ---

def test_check_url_rejects_non_http():
    with pytest.raises(ValueError):
        log_result.check_url("file:///etc/passwd")


def test_check_url_accepts_https():
    assert log_result.check_url("https://x.test/a") == "https://x.test/a"


def test_load_result_rejects_missing_required(tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"title": "제목만"}), encoding="utf-8")
    with pytest.raises(ValueError):
        log_result.load_result(str(p))


def test_load_result_rejects_non_object(tmp_path):
    p = tmp_path / "r.json"
    p.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ValueError):
        log_result.load_result(str(p))


def test_load_result_ok(tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps(RESULT, ensure_ascii=False), encoding="utf-8")
    assert log_result.load_result(str(p))["title"] == "테스트 공모전"


# --- log_result: 로그 기록이 obsidian_log 와 동일 결과인지 ---

def test_logged_section_matches_render(tmp_path):
    log = tmp_path / "_분석로그.md"
    url = "https://x.test/notice"
    today = dt.date(2026, 8, 4)
    obsidian_log.append_to_log(RESULT, url, today, log)
    content = log.read_text(encoding="utf-8")
    assert obsidian_log.render_section(RESULT, url, today).rstrip() in content


def test_upsert_does_not_duplicate(tmp_path):
    log = tmp_path / "_분석로그.md"
    url = "https://x.test/notice"
    today = dt.date(2026, 8, 4)
    obsidian_log.append_to_log(RESULT, url, today, log)
    obsidian_log.append_to_log({**RESULT, "summary": "수정된 요약"}, url, today, log)
    content = log.read_text(encoding="utf-8")
    assert content.count(obsidian_log.MARKER) == 1
    assert "수정된 요약" in content
