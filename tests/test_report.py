import datetime as dt

import obsidian_log as ol
import report

TODAY = dt.date(2026, 6, 22)


def _log(tmp_path, results):
    """SAMPLE 스타일 결과들을 실제 로그 파일로 기록하고 경로 반환."""
    p = tmp_path / "_분석로그.md"
    for r, url in results:
        ol.append_to_log(r, url, TODAY, log_path=p)
    return p


def _mk(title, deadline_iso, score, cats, summary, prizes=None):
    return {
        "title": title, "host": "주최", "organizer": "주관",
        "categories": cats, "eligibility": "대학생",
        "period": "", "deadline": deadline_iso, "deadline_iso": deadline_iso,
        "prizes": prizes or [], "submissions": ["기획서"],
        "judging_criteria": ["창의성"], "schedule": [], "contact": "",
        "summary": summary,
        "trend_fit": {"score": score, "aligned_trends": ["AI"], "angle": "각"},
        "ideas": [],
    }


# ── 금액 파싱 ───────────────────────────────────────────────────
def test_money_units():
    assert report.max_prize_manwon("총 상금 1억원") == 10000
    assert report.max_prize_manwon("대상 500만원") == 500
    assert report.max_prize_manwon("상금 3천만원") == 3000
    assert report.max_prize_manwon("1,500만원 지급") == 1500
    assert report.max_prize_manwon("상금 미정") is None


def test_money_takes_max():
    assert report.max_prize_manwon("대상 1000만원, 최우수 300만원") == 1000
    assert report.max_prize_manwon("총상금 2억원(대상 5000만원)") == 20000


def test_prize_bucket():
    assert report.prize_bucket(None) == "미상"
    assert report.prize_bucket(50) == "100만원 미만"
    assert report.prize_bucket(300) == "100만~500만원"
    assert report.prize_bucket(700) == "500만~1천만원"
    assert report.prize_bucket(3000) == "1천만~1억원"
    assert report.prize_bucket(10000) == "1억원 이상"


# ── D-day / 트렌드 버킷 ─────────────────────────────────────────
def test_dday_bucket():
    assert report.dday_bucket("2026-06-25", TODAY) == "임박(D-7 이내)"
    assert report.dday_bucket("2026-07-10", TODAY) == "D-8~30"
    assert report.dday_bucket("2026-08-30", TODAY) == "D-31~90"
    assert report.dday_bucket("2027-01-01", TODAY) == "D-90 초과"
    assert report.dday_bucket("2026-06-01", TODAY) == "마감됨"
    assert report.dday_bucket("", TODAY) == "미정"


def test_trend_bucket():
    assert report.trend_bucket(95) == "90-100"
    assert report.trend_bucket(80) == "70-89"
    assert report.trend_bucket(55) == "50-69"
    assert report.trend_bucket(30) == "50 미만"
    assert report.trend_bucket("") == "미평가"


# ── 부문 파싱 ───────────────────────────────────────────────────
def test_section_categories(tmp_path):
    p = _log(tmp_path, [
        (_mk("A", "2026-07-01", 80, ["아이디어", "서비스"], "총 상금 1000만원"),
         "https://x/1"),
    ])
    sections = ol._split_sections(p.read_text(encoding="utf-8"))
    assert report.section_categories(sections[0]) == ["아이디어", "서비스"]


def test_empty_categories(tmp_path):
    p = _log(tmp_path, [
        (_mk("A", "2026-07-01", 80, [], "상금 미정"), "https://x/1"),
    ])
    sections = ol._split_sections(p.read_text(encoding="utf-8"))
    assert report.section_categories(sections[0]) == []


# ── 통합 집계 ───────────────────────────────────────────────────
def _fixture(tmp_path):
    return _log(tmp_path, [
        (_mk("공모A", "2026-06-25", 92, ["아이디어", "AI"], "총 상금 1억원"),
         "https://x/1"),
        (_mk("공모B", "2026-07-15", 78, ["서비스", "AI"], "대상 500만원"),
         "https://x/2"),
        (_mk("공모C", "2026-09-01", 45, ["창업"], "상금 정보 없음"),
         "https://x/3"),
    ])


def test_aggregate_counts(tmp_path):
    p = _fixture(tmp_path)
    sections = ol._split_sections(p.read_text(encoding="utf-8"))
    agg = report.aggregate(sections, TODAY)
    assert agg["total"] == 3
    assert agg["categories"]["AI"] == 2
    assert agg["categories"]["아이디어"] == 1
    assert agg["prizes"]["1억원 이상"] == 1
    assert agg["prizes"]["500만~1천만원"] == 1
    assert agg["prizes"]["미상"] == 1
    assert agg["ddays"]["임박(D-7 이내)"] == 1
    assert agg["ddays"]["D-8~30"] == 1
    assert agg["ddays"]["D-31~90"] == 1
    assert agg["trends"]["90-100"] == 1
    assert agg["trends"]["70-89"] == 1
    assert agg["trends"]["50 미만"] == 1


def test_prize_values_sorted(tmp_path):
    p = _fixture(tmp_path)
    sections = ol._split_sections(p.read_text(encoding="utf-8"))
    agg = report.aggregate(sections, TODAY)
    assert agg["prize_values"][0] == ("공모A", 10000)
    assert len(agg["prize_values"]) == 2  # 미상 제외


def test_build_report_smoke(tmp_path):
    p = _fixture(tmp_path)
    out = report.report_from_log(p, TODAY)
    assert "# 공모전 수집 통계 리포트" in out
    assert "수집 공고 수: **3건**" in out
    assert "## 분야별 건수" in out
    assert "## 상금 분포" in out
    assert "## 마감 D-day 분포" in out
    assert "## 트렌드 적합도 분포" in out
    assert "공모A" in out


def test_empty_log(tmp_path):
    p = tmp_path / "empty.md"
    p.write_text("---\ntags: [공모전]\n---\n\n# 비어있음\n", encoding="utf-8")
    out = report.report_from_log(p, TODAY)
    assert "수집 공고 수: **0건**" in out


def test_main_missing_file(tmp_path, capsys):
    rc = report.main([str(tmp_path / "nope.md")])
    assert rc == 1
    assert "로그 파일 없음" in capsys.readouterr().err
