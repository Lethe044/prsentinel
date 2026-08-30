from pathlib import Path

from prsentinel.diffparser import parse_unified_diff

FIXTURE = Path(__file__).parent / "fixtures" / "sample.diff"


def load_fixture() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_parses_two_files():
    files = parse_unified_diff(load_fixture())
    paths = [f.path for f in files]
    assert paths == ["app/utils.py", "app/config.lock"]


def test_extracts_added_lines_with_new_line_numbers():
    files = parse_unified_diff(load_fixture())
    utils_file = files[0]
    added = [line for hunk in utils_file.hunks for line in hunk.lines if line.kind == "add"]
    contents = [line.content for line in added]
    assert any("SELECT * FROM users WHERE id = %s" in c for c in contents)
    for line in added:
        assert line.new_lineno is not None


def test_removed_lines_have_no_new_line_number():
    files = parse_unified_diff(load_fixture())
    utils_file = files[0]
    removed = [line for hunk in utils_file.hunks for line in hunk.lines if line.kind == "remove"]
    assert removed
    for line in removed:
        assert line.new_lineno is None


def test_empty_diff_returns_no_files():
    assert parse_unified_diff("") == []


def test_handles_binary_marker():
    text = (
        "diff --git a/image.png b/image.png\n"
        "index 111..222 100644\n"
        "Binary files a/image.png and b/image.png differ\n"
    )
    files = parse_unified_diff(text)
    assert len(files) == 1
    assert files[0].is_binary is True
    assert files[0].hunks == []
