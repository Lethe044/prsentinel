from prsentinel.diffparser import parse_unified_diff
from prsentinel.suppressions import build_suppressions

IGNORE_LINE_DIFF = """\
diff --git a/app.py b/app.py
index 111..222 100644
--- a/app.py
+++ b/app.py
@@ -1,2 +1,4 @@
 def run():
+    eval(user_input)  # prsentinel-ignore-line
+    exec(other_input)
"""

IGNORE_NEXT_LINE_DIFF = """\
diff --git a/app.py b/app.py
index 111..222 100644
--- a/app.py
+++ b/app.py
@@ -1,2 +1,4 @@
 def run():
+    # prsentinel-ignore-next-line
+    eval(user_input)
+    exec(other_input)
"""

IGNORE_FILE_DIFF = """\
diff --git a/generated.py b/generated.py
index 111..222 100644
--- a/generated.py
+++ b/generated.py
@@ -1,1 +1,2 @@
+# prsentinel-ignore-file
+eval(user_input)
"""


def get_file(diff_text: str):
    return parse_unified_diff(diff_text)[0]


def test_ignore_line_marker_suppresses_only_that_line():
    diff_file = get_file(IGNORE_LINE_DIFF)
    suppressions = build_suppressions(diff_file)

    assert suppressions.covers(2) is True
    assert suppressions.covers(3) is False
    assert suppressions.file_suppressed is False


def test_ignore_next_line_marker_suppresses_the_following_line():
    diff_file = get_file(IGNORE_NEXT_LINE_DIFF)
    suppressions = build_suppressions(diff_file)

    assert suppressions.covers(3) is True
    assert suppressions.covers(4) is False


def test_ignore_file_marker_suppresses_every_line():
    diff_file = get_file(IGNORE_FILE_DIFF)
    suppressions = build_suppressions(diff_file)

    assert suppressions.file_suppressed is True
    assert suppressions.covers(1) is True
    assert suppressions.covers(999) is True


def test_no_markers_suppresses_nothing():
    diff_text = """\
diff --git a/app.py b/app.py
index 111..222 100644
--- a/app.py
+++ b/app.py
@@ -1,1 +1,2 @@
 def run():
+    pass
"""
    diff_file = get_file(diff_text)
    suppressions = build_suppressions(diff_file)
    assert suppressions.file_suppressed is False
    assert suppressions.covers(2) is False
    assert suppressions.covers(None) is False
