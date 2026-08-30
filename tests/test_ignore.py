from prsentinel.ignore import is_ignored

PATTERNS = ["*.lock", "dist/**", "node_modules/**", "*.png"]


def test_matches_extension_pattern():
    assert is_ignored("app/config.lock", PATTERNS) is True


def test_matches_directory_pattern():
    assert is_ignored("dist/bundle.js", PATTERNS) is True
    assert is_ignored("node_modules/react/index.js", PATTERNS) is True


def test_does_not_match_unrelated_file():
    assert is_ignored("app/utils.py", PATTERNS) is False


def test_matches_nested_extension_without_leading_path():
    assert is_ignored("assets/images/logo.png", PATTERNS) is True
