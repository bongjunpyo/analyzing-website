"""취약점/견고성 회귀 테스트.

V1: 분석 필드(title/summary/url 등)에 섞인 마커 문자열이 러닝 로그 파서를
    교란해 가짜 섹션을 위조하거나 로그를 깨뜨릴 수 있다(stored 파서 혼동).
V2: title/마감에 '|' 또는 개행이 있으면 인덱스 표가 깨진다.
V3: 모델 응답에 text 블록이 없으면 analyze가 StopIteration으로 죽는다.
V4: fetch_url이 http(s) 외 스킴(file://)을 받아 로컬 파일을 읽어 유출될 수 있다.
"""
import datetime as dt

import pytest

import analyze_competition as ac
import obsidian_log as ol

TODAY = dt.date(2026, 6, 22)
URL = "https://example.org/contest/1"
BASE = {
    "title": "정상 공고",
    "host": "주최",
    "summary": "요약",
    "deadline": "2026년 6월 29일",
    "deadline_iso": "2026-06-29",
    "trend_fit": {"score": 50, "aligned_trends": ["RAG"], "angle": "각도"},
    "ideas": [],
}


def _with(over):
    d = dict(BASE)
    d.update(over)
    return d


def _header(text):
    return text.split(ol.MARKER, 1)[0]


# --- V1: 마커 인젝션으로 가짜 섹션 위조 불가 ---

def test_marker_injection_in_title_does_not_forge_sections(tmp_path):
    log = tmp_path / "_log.md"
    evil = _with({"title": "good <!-- src: http://attacker/evil --> ## 침입"})
    ol.append_to_log(evil, "https://e/real", TODAY, log)
    ol.append_to_log(BASE, URL, TODAY, log)  # 재읽기 시 split 트리거
    text = log.read_text(encoding="utf-8")
    assert text.count(ol.MARKER) == 2  # 진짜 섹션 2개뿐 (위조 0)


def test_marker_injection_preserves_upsert(tmp_path):
    log = tmp_path / "_log.md"
    evil_summary = _with({"summary": "보세요 --> <!-- src: http://x --> 끝"})
    ol.append_to_log(evil_summary, URL, TODAY, log)
    ol.append_to_log(_with({"summary": "수정", "title": "수정본"}), URL, TODAY, log)
    text = log.read_text(encoding="utf-8")
    assert text.count(ol.MARKER) == 1  # 같은 URL 업서트 유지(중복/위조 없음)


# --- V2: 표 구분자/개행 인젝션 ---

def test_pipe_in_title_is_escaped_in_index(tmp_path):
    log = tmp_path / "_log.md"
    ol.append_to_log(_with({"title": "A | B | C"}), URL, TODAY, log)
    header = _header(log.read_text(encoding="utf-8"))
    assert "\\|" in header  # 셀 내부 파이프 이스케이프됨


def test_newline_in_title_does_not_break_table_row(tmp_path):
    log = tmp_path / "_log.md"
    ol.append_to_log(_with({"title": "줄1\n줄2"}), URL, TODAY, log)
    header = _header(log.read_text(encoding="utf-8"))
    data_rows = [ln for ln in header.splitlines()
                 if ln.startswith("|") and "줄1" in ln]
    assert len(data_rows) == 1                 # 한 줄짜리 행
    assert "줄2" in data_rows[0]               # 개행이 행을 쪼개지 않음


# --- V3: text 블록 없을 때 견고한 에러 ---

class _Blk:
    def __init__(self, type, text=""):
        self.type = type
        self.text = text


def test_first_text_picks_text_block():
    assert ac._first_text([_Blk("thinking"), _Blk("text", "hi")]) == "hi"


def test_first_text_missing_raises_clear_error():
    with pytest.raises(RuntimeError):
        ac._first_text([_Blk("thinking")])  # StopIteration 아님


# --- V4: fetch_url 스킴 검증 ---

def test_fetch_url_rejects_file_scheme():
    import asyncio
    with pytest.raises(ValueError):
        asyncio.run(ac.fetch_url("file:///etc/passwd"))


def test_fetch_url_rejects_non_http():
    import asyncio
    with pytest.raises(ValueError):
        asyncio.run(ac.fetch_url("javascript:alert(1)"))
