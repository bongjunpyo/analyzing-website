"""공모전 분석 결과를 옵시디언 단일 러닝 로그에 기록.

표준 라이브러리만 사용. analyze_competition 결과 dict를 입력으로 받는다.
"""
import datetime as dt
import json
from pathlib import Path

MARKER = "<!-- src:"
META = "<!-- meta:"
DEFAULT_LOG = Path.home() / "Documents" / "Obsidian Vault" / "공모전" / "_분석로그.md"


def dday(deadline_iso: str, today: dt.date) -> str:
    """마감일(YYYY-MM-DD)과 오늘로 D-day 문자열 계산. 불명확하면 빈 문자열."""
    try:
        d = dt.date.fromisoformat((deadline_iso or "").strip())
    except ValueError:
        return ""
    delta = (d - today).days
    if delta > 0:
        return f"D-{delta}"
    if delta == 0:
        return "D-DAY"
    return f"마감(+{-delta})"


def _bullets(items, empty="- (명시 없음)"):
    items = [str(i).strip() for i in (items or []) if str(i).strip()]
    return "\n".join(f"- {i}" for i in items) or empty


def _checklist(items):
    items = [str(i).strip() for i in (items or []) if str(i).strip()]
    return "\n".join(f"- [ ] {i}" for i in items) or "- [ ] (공고 확인 필요)"


def _idea_block(idea: dict) -> str:
    title = idea.get("title", "(제목 없음)")
    anchor = idea.get("trend_anchor", "")
    head = f"#### {title}" + (f"  · 트렌드: {anchor}" if anchor else "")
    tech = ", ".join(idea.get("tech_stack") or [])
    flow = (idea.get("flow_diagram") or "").rstrip()
    parts = [head, idea.get("description", "")]
    if tech:
        parts.append(f"- tech: {tech}")
    if flow:
        parts.append("```\n" + flow + "\n```")
    return "\n".join(p for p in parts if p)


def _meta_dict(result: dict, url: str, today: dt.date) -> dict:
    tf = result.get("trend_fit") or {}
    return {
        "title": result.get("title", "(제목 없음)"),
        "url": url,
        "deadline": result.get("deadline", ""),
        "deadline_iso": result.get("deadline_iso", ""),
        "dday": dday(result.get("deadline_iso", ""), today),
        "trend_score": tf.get("score", ""),
        "analyzed": today.isoformat(),
    }


def render_section(result: dict, url: str, today: dt.date) -> str:
    """분석 결과 1건을 사람이 읽는 마크다운 섹션으로. 업서트용 마커/메타 포함."""
    m = _meta_dict(result, url, today)
    tf = result.get("trend_fit") or {}
    score = tf.get("score", "")
    score_str = f"{score}/100" if score != "" else "(미평가)"
    dd = m["dday"]
    deadline_disp = result.get("deadline", "") + (f" ({dd})" if dd else "")
    cats = ", ".join(result.get("categories") or []) or "(명시 없음)"
    trends = ", ".join(tf.get("aligned_trends") or []) or "(명시 없음)"
    ideas = result.get("ideas") or []
    ideas_md = "\n\n".join(_idea_block(i) for i in ideas) or "- (없음)"

    return f"""{MARKER} {url} -->
{META} {json.dumps(m, ensure_ascii=False)} -->
## {result.get("title", "(제목 없음)")}

- 주최: {result.get("host", "")} / 주관: {result.get("organizer", "")}
- 마감: {deadline_disp or "(명시 없음)"}
- 트렌드 적합: {score_str}
- 자격: {result.get("eligibility", "(명시 없음)")}
- 부문: {cats}
- 분석일: {m["analyzed"]}
- 링크: {url}

> {result.get("summary", "")}

### 심사 기준
{_bullets(result.get("judging_criteria"))}

### 제출물 체크리스트
{_checklist(result.get("submissions"))}

### 트렌드 적합 ({score_str})
- 연관 트렌드: {trends}
- 앵글: {tf.get("angle", "(명시 없음)")}

### 아이디어
{ideas_md}
"""


def _split_sections(content: str) -> list[str]:
    """기존 로그 본문을 MARKER 기준 섹션 리스트로. 헤더(첫 마커 이전)는 버린다."""
    if MARKER not in content:
        return []
    return [MARKER + p for p in content.split(MARKER)[1:]]


def _section_url(section: str) -> str:
    first = section.splitlines()[0]
    return first[len(MARKER):].split("-->", 1)[0].strip()


def _section_meta(section: str) -> dict:
    for ln in section.splitlines():
        if ln.startswith(META):
            try:
                return json.loads(ln[len(META):].rsplit("-->", 1)[0].strip())
            except ValueError:
                return {}
    return {}


def _index_table(sections: list[str]) -> str:
    rows = []
    for s in sections:
        m = _section_meta(s)
        dd = m.get("dday", "")
        deadline = m.get("deadline", "") or m.get("deadline_iso", "")
        cell = (deadline + (f" ({dd})" if dd else "")).strip() or "(미정)"
        trend = m.get("trend_score", "")
        trend_cell = f"{trend}/100" if trend != "" else "-"
        row = f"| {m.get('title', '')} | {cell} | {trend_cell} | [링크]({m.get('url', '')}) | {m.get('analyzed', '')} |"
        rows.append((m.get("deadline_iso", "") or "", row))
    rows.sort(key=lambda r: (r[0] == "", r[0]))  # 마감 임박순, 미정은 뒤
    body = "\n".join(r[1] for r in rows) or "| (없음) |  |  |  |  |"
    return ("| 제목 | 마감(D-day) | 트렌드 | 링크 | 분석일 |\n"
            "|---|---|---|---|---|\n" + body)


def _render_file(sections: list[str]) -> str:
    header = (
        "---\ntags: [공모전, 분석로그]\n---\n\n"
        "# 공모전 분석 로그\n\n"
        + _index_table(sections) + "\n\n---\n\n"
    )
    body = "\n\n".join(s.rstrip() for s in sections)
    return header + body + ("\n" if body else "")


def append_to_log(result: dict, url: str, today: dt.date, log_path=DEFAULT_LOG) -> Path:
    """분석 결과를 러닝 로그에 업서트(같은 URL이면 교체)하고 인덱스 표를 재생성."""
    log_path = Path(log_path)
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    sections = _split_sections(existing)
    new_section = render_section(result, url, today)
    for i, s in enumerate(sections):
        if _section_url(s) == url:
            sections[i] = new_section
            break
    else:
        sections.append(new_section)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(_render_file(sections), encoding="utf-8")
    return log_path
