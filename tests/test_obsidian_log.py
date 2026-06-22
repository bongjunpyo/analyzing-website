import datetime as dt
import json
from pathlib import Path

import obsidian_log as ol

TODAY = dt.date(2026, 6, 22)
URL = "https://example.org/contest/1"

SAMPLE = {
    "title": "공공데이터 AI 경진대회",
    "host": "부산광역시",
    "organizer": "부산테크노파크",
    "categories": ["아이디어", "서비스"],
    "eligibility": "대학생",
    "period": "2026-06-01 ~ 2026-06-29",
    "deadline": "2026년 6월 29일 18시",
    "deadline_iso": "2026-06-29",
    "prizes": [{"name": "대상", "detail": "500만원"}],
    "submissions": ["기획서", "발표자료"],
    "judging_criteria": ["창의성", "실현가능성"],
    "schedule": [{"phase": "접수마감", "date": "2026-06-29"}],
    "contact": "051-000-0000",
    "summary": "공공데이터로 지역문제 해결.",
    "trend_fit": {
        "score": 82,
        "aligned_trends": ["에이전틱 AI", "공공데이터×AI"],
        "angle": "에이전트가 민원을 자동 분류.",
    },
    "ideas": [
        {
            "title": "민원 에이전트",
            "description": "LLM 에이전트가 민원 라우팅",
            "tech_stack": ["Python", "RAG"],
            "trend_anchor": "에이전틱 AI",
            "flow_diagram": "민원 -> 분류 -> 라우팅",
        }
    ],
}


def test_dday_future():
    assert ol.dday("2026-06-29", TODAY) == "D-7"


def test_dday_today():
    assert ol.dday("2026-06-22", TODAY) == "D-DAY"


def test_dday_past():
    assert ol.dday("2026-06-20", TODAY) == "마감(+2)"


def test_dday_empty_or_bad():
    assert ol.dday("", TODAY) == ""
    assert ol.dday("미정", TODAY) == ""


def test_render_has_marker_and_meta():
    md = ol.render_section(SAMPLE, URL, TODAY)
    assert f"<!-- src: {URL} -->" in md
    meta_line = next(ln for ln in md.splitlines() if ln.startswith("<!-- meta:"))
    meta = json.loads(meta_line[len("<!-- meta:"):-len("-->")].strip())
    assert meta["title"] == "공공데이터 AI 경진대회"
    assert meta["deadline_iso"] == "2026-06-29"
    assert meta["analyzed"] == "2026-06-22"
    assert meta["url"] == URL


def test_render_includes_core_fields():
    md = ol.render_section(SAMPLE, URL, TODAY)
    assert "## 공공데이터 AI 경진대회" in md
    assert "부산광역시" in md
    assert "D-7" in md
    assert "82/100" in md
    assert "공공데이터로 지역문제 해결." in md
    assert "- [ ] 기획서" in md
    assert "창의성" in md


def test_render_includes_idea_and_flow():
    md = ol.render_section(SAMPLE, URL, TODAY)
    assert "민원 에이전트" in md
    assert "에이전틱 AI" in md
    assert "민원 -> 분류 -> 라우팅" in md
    assert "```" in md  # flow diagram fenced


def test_render_handles_missing_optional_keys():
    minimal = {"title": "최소 공고", "summary": "요약"}
    md = ol.render_section(minimal, URL, TODAY)  # must not raise
    assert "## 최소 공고" in md
    assert f"<!-- src: {URL} -->" in md


def _with(overrides):
    d = dict(SAMPLE)
    d.update(overrides)
    return d


def _header(text):
    """첫 섹션 마커 이전의 헤더(인덱스 표 영역)."""
    return text.split(ol.MARKER, 1)[0]


def test_append_creates_file(tmp_path):
    log = tmp_path / "_분석로그.md"
    p = ol.append_to_log(SAMPLE, URL, TODAY, log)
    assert p == log and log.exists()
    text = log.read_text(encoding="utf-8")
    assert "tags: [공모전, 분석로그]" in text
    assert "| 제목 |" in _header(text)
    assert text.count(ol.MARKER) == 1
    assert "## 공공데이터 AI 경진대회" in text


def test_append_two_distinct_urls(tmp_path):
    log = tmp_path / "_분석로그.md"
    ol.append_to_log(SAMPLE, URL, TODAY, log)
    ol.append_to_log(_with({"title": "딴 대회"}), "https://example.org/contest/2", TODAY, log)
    text = log.read_text(encoding="utf-8")
    assert text.count(ol.MARKER) == 2
    header = _header(text)
    assert "공공데이터 AI 경진대회" in header and "딴 대회" in header


def test_append_same_url_upserts(tmp_path):
    log = tmp_path / "_분석로그.md"
    ol.append_to_log(SAMPLE, URL, TODAY, log)
    ol.append_to_log(_with({"title": "수정된 제목"}), URL, TODAY, log)
    text = log.read_text(encoding="utf-8")
    assert text.count(ol.MARKER) == 1          # 중복 없음
    assert "## 수정된 제목" in text
    assert "## 공공데이터 AI 경진대회" not in text


def test_index_sorted_by_deadline(tmp_path):
    log = tmp_path / "_분석로그.md"
    far = _with({"title": "먼대회", "deadline_iso": "2026-06-29"})
    near = _with({"title": "임박대회", "deadline_iso": "2026-06-25"})
    none = _with({"title": "미정대회", "deadline_iso": ""})
    ol.append_to_log(far, "https://e/a", TODAY, log)
    ol.append_to_log(none, "https://e/b", TODAY, log)
    ol.append_to_log(near, "https://e/c", TODAY, log)
    header = _header(log.read_text(encoding="utf-8"))
    assert header.index("임박대회") < header.index("먼대회") < header.index("미정대회")
