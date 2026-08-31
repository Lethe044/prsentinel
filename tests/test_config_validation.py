from prsentinel.config import Config, validate_config


def test_default_config_is_valid():
    assert validate_config(Config()) == []


def test_invalid_provider_is_reported():
    errors = validate_config(Config(provider="chatgpt"))
    assert any("provider" in e for e in errors)


def test_invalid_severity_threshold_is_reported():
    errors = validate_config(Config(severity_threshold="urgent"))
    assert any("severity_threshold" in e for e in errors)


def test_invalid_fail_on_is_reported():
    errors = validate_config(Config(fail_on="urgent"))
    assert any("fail_on" in e for e in errors)


def test_negative_max_files_is_reported():
    errors = validate_config(Config(max_files=-1))
    assert any("max_files" in e for e in errors)


def test_non_string_ignore_list_is_reported():
    errors = validate_config(Config(ignore=[1, 2, 3]))
    assert any("ignore" in e for e in errors)


def test_multiple_problems_are_all_reported():
    errors = validate_config(Config(provider="bad", fail_on="bad", max_workers=0))
    assert len(errors) == 3
