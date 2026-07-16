"""옵시디언 러닝 로그(_분석로그.md)를 파싱해 수집 공고 통계 리포트 생성.

표준 라이브러리만 사용. obsidian_log.py 가 기록한 섹션(마커/메타)을 그대로 읽는다.
집계: 분야별 건수 / 상금 분포 / 마감 D-day 분포 / trend_fit 점수 분포.

상금은 로그 메타에 구조화 저장되지 않으므로, 섹션 본문 텍스트에서 원문 금액 표현을
정규식으로 추출한다(analyze_competition 이 요약에 상금 표현을 보존함). 휴리스틱임에 유의.
"""
import datetime as dt
import re
import sys
from collections import Counter
from pathlib import Path

from obsidian_log import (
    DEFAULT_LOG,
    MARKER,
    _section_meta,
    _split_sections,
)

# ── 상금 추출 ───────────────────────────────────────────────────
# 원문 금액 표현 → 만원 단위 정수로 정규화
_MONEY_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(억|천만|천\s*만|만)\s*원?")


def _to_manwon(num: str, unit: str) -> float:
    """(숫자, 단위) → 만원 단위 값. 억=10000, 천만=1000, 만=1."""
    val = float(num.replace(",", ""))
    unit = unit.replace(" ", "")
    if unit == "억":
        return val * 10000
    if unit == "천만":
        return val * 1000
    return val  # 만


def max_prize_manwon(text: str):
    """텍스트에서 가장 큰 금액을 만원 단위로. 없으면 None."""
    vals = [_to_manwon(n, u) for n, u in _MONEY_RE.findall(text)]
    return max(vals) if vals else None


def prize_bucket(manwon) -> str:
    if manwon is None:
        return "미상"
    if manwon >= 10000:
        return "1억원 이상"
    if manwon >= 1000:
        return "1천만~1억원"
    if manwon >= 500:
        return "500만~1천만원"
    if manwon >= 100:
        return "100만~500만원"
    return "100만원 미만"


PRIZE_ORDER = ["1억원 이상", "1천만~1억원", "500만~1천만원",
               "100만~500만원", "100만원 미만", "미상"]


# ── 마감 D-day ──────────────────────────────────────────────────
def dday_bucket(deadline_iso: str, today: dt.date) -> str:
    try:
        d = dt.date.fromisoformat((deadline_iso or "").strip())
    except ValueError:
        return "미정"
    delta = (d - today).days
    if delta < 0:
        return "마감됨"
    if delta <= 7:
        return "임박(D-7 이내)"
    if delta <= 30:
        return "D-8~30"
    if delta <= 90:
        return "D-31~90"
    return "D-90 초과"


DDAY_ORDER = ["임박(D-7 이내)", "D-8~30", "D-31~90", "D-90 초과", "마감됨", "미정"]


# ── 트렌드 점수 ─────────────────────────────────────────────────
def trend_bucket(score) -> str:
    if score == "" or score is None:
        return "미평가"
    try:
        s = int(score)
    except (TypeError, ValueError):
        return "미평가"
    if s >= 90:
        return "90-100"
    if s >= 70:
        return "70-89"
    if s >= 50:
        return "50-69"
    return "50 미만"


TREND_ORDER = ["90-100", "70-89", "50-69", "50 미만", "미평가"]


# ── 분야(부문) ──────────────────────────────────────────────────
_CAT_LINE_RE = re.compile(r"^-\s*부문:\s*(.+)$", re.MULTILINE)


def section_categories(section: str) -> list:
    m = _CAT_LINE_RE.search(section)
    if not m:
        return []
    raw = m.group(1).strip()
    if raw in ("(명시 없음)", ""):
        return []
    return [c.strip() for c in raw.split(",") if c.strip() and c.strip() != "(명시 없음)"]


# ── 집계 ────────────────────────────────────────────────────────
def aggregate(sections: list, today: dt.date) -> dict:
    cats = Counter()
    prizes = Counter()
    ddays = Counter()
    trends = Counter()
    prize_values = []  # (title, manwon)

    for s in sections:
        meta = _section_meta(s)
        for c in section_categories(s):
            cats[c] += 1
        mw = max_prize_manwon(s)
        prizes[prize_bucket(mw)] += 1
        if mw is not None:
            prize_values.append((meta.get("title", ""), mw))
        ddays[dday_bucket(meta.get("deadline_iso", ""), today)] += 1
        trends[trend_bucket(meta.get("trend_score", ""))] += 1

    return {
        "total": len(sections),
        "categories": cats,
        "prizes": prizes,
        "ddays": ddays,
        "trends": trends,
        "prize_values": sorted(prize_values, key=lambda t: -t[1]),
    }


# ── 렌더링 ──────────────────────────────────────────────────────
def _dist_table(counter: Counter, order: list, label: str) -> str:
    total = sum(counter.values()) or 1
    lines = [f"| {label} | 건수 | 비율 |", "|---|---|---|"]
    keys = [k for k in order if k in counter] + \
           [k for k in counter if k not in order]
    for k in keys:
        n = counter[k]
        bar = "█" * round(n / total * 20)
        lines.append(f"| {k} | {n} | {n / total:.0%} {bar} |")
    return "\n".join(lines)


def _cat_table(cats: Counter) -> str:
    lines = ["| 분야/부문 | 건수 |", "|---|---|"]
    if not cats:
        lines.append("| (없음) | 0 |")
        return "\n".join(lines)
    for name, n in cats.most_common():
        lines.append(f"| {name} | {n} |")
    return "\n".join(lines)


def build_report(sections: list, today: dt.date) -> str:
    agg = aggregate(sections, today)
    parts = [
        "# 공모전 수집 통계 리포트",
        "",
        f"- 생성일: {today.isoformat()}",
        f"- 수집 공고 수: **{agg['total']}건**",
        "",
        "## 분야별 건수",
        "",
        _cat_table(agg["categories"]),
        "",
        "## 상금 분포",
        "",
        "> 섹션 본문의 원문 금액 표현에서 추출한 최대 금액 기준(휴리스틱).",
        "",
        _dist_table(agg["prizes"], PRIZE_ORDER, "상금 구간"),
        "",
        "## 마감 D-day 분포",
        "",
        _dist_table(agg["ddays"], DDAY_ORDER, "D-day 구간"),
        "",
        "## 트렌드 적합도 분포",
        "",
        _dist_table(agg["trends"], TREND_ORDER, "점수 구간"),
    ]
    if agg["prize_values"]:
        parts += ["", "## 상금 상위 공고", "", "| 공고 | 최대 상금(만원) |", "|---|---|"]
        for title, mw in agg["prize_values"][:10]:
            parts.append(f"| {title} | {mw:,.0f} |")
    return "\n".join(parts) + "\n"


def report_from_log(log_path=DEFAULT_LOG, today=None) -> str:
    today = today or dt.date.today()
    log_path = Path(log_path)
    content = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    sections = _split_sections(content)
    return build_report(sections, today)


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    log_path = Path(argv[0]) if argv else DEFAULT_LOG
    if not Path(log_path).exists():
        print(f"로그 파일 없음: {log_path}", file=sys.stderr)
        return 1
    print(report_from_log(log_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
