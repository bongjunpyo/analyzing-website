import analyze_competition as ac


# --- 스키마 고도화 (additive) ---

def test_schema_has_deadline_iso():
    assert "deadline_iso" in ac.SCHEMA["properties"]


def test_schema_has_trend_fit():
    props = ac.SCHEMA["properties"]["trend_fit"]["properties"]
    assert {"score", "aligned_trends", "angle"} <= set(props)


def test_idea_has_trend_anchor():
    idea_props = ac.SCHEMA["properties"]["ideas"]["items"]["properties"]
    assert "trend_anchor" in idea_props


# --- contest_hunter 공유 심볼 보존 ---

def test_shared_symbols_present():
    for name in ("fetch_url", "extract_text", "analyze"):
        assert callable(getattr(ac, name))


# --- CLI 플래그 ---

def test_cli_absent_defaults():
    a = ac.build_parser().parse_args(["http://x"])
    assert a.obsidian is None and a.md is False


def test_cli_obsidian_default_sentinel():
    a = ac.build_parser().parse_args(["http://x", "--obsidian"])
    assert a.obsidian == ""


def test_cli_obsidian_explicit_path():
    a = ac.build_parser().parse_args(["http://x", "--obsidian", "/tmp/l.md"])
    assert a.obsidian == "/tmp/l.md"


def test_cli_md_flag():
    a = ac.build_parser().parse_args(["http://x", "--md"])
    assert a.md is True
