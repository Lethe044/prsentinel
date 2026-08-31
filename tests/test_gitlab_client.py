from prsentinel.diffparser import parse_unified_diff
from prsentinel.gitlab_client import changes_to_unified_diff

SAMPLE_CHANGES_RESPONSE = {
    "changes": [
        {
            "old_path": "app/utils.py",
            "new_path": "app/utils.py",
            "new_file": False,
            "deleted_file": False,
            "diff": (
                "@@ -10,3 +10,4 @@ def divide(a, b):\n"
                "     return a / b\n"
                "+def get_user(user_id):\n"
                "+    return db.query(f\"SELECT * FROM users WHERE id = {user_id}\")\n"
            ),
        },
        {
            "old_path": "README.md",
            "new_path": "README.md",
            "new_file": False,
            "deleted_file": False,
            "diff": "@@ -1,1 +1,1 @@\n-old\n+new\n",
        },
    ]
}


def test_changes_to_unified_diff_produces_parseable_output():
    diff_text = changes_to_unified_diff(SAMPLE_CHANGES_RESPONSE)
    files = parse_unified_diff(diff_text)

    assert [f.path for f in files] == ["app/utils.py", "README.md"]
    assert files[0].hunks
    added = [
        line
        for hunk in files[0].hunks
        for line in hunk.lines
        if line.kind == "add"
    ]
    assert any("get_user" in line.content for line in added)


def test_changes_to_unified_diff_handles_new_file():
    response = {
        "changes": [
            {
                "old_path": "new_module.py",
                "new_path": "new_module.py",
                "new_file": True,
                "deleted_file": False,
                "diff": "@@ -0,0 +1,2 @@\n+def hello():\n+    pass\n",
            }
        ]
    }
    diff_text = changes_to_unified_diff(response)
    files = parse_unified_diff(diff_text)
    assert len(files) == 1
    assert files[0].hunks


def test_changes_to_unified_diff_skips_empty_diff_for_binary_files():
    response = {
        "changes": [
            {
                "old_path": "image.png",
                "new_path": "image.png",
                "new_file": False,
                "deleted_file": False,
                "diff": "",
            }
        ]
    }
    diff_text = changes_to_unified_diff(response)
    files = parse_unified_diff(diff_text)
    assert len(files) == 1
    assert files[0].hunks == []
