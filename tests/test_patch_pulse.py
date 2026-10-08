import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from patch_pulse import analyze, main


SAMPLE = """diff --git a/app.py b/app.py
@@ -1,2 +1,3 @@
 def run():
-    return 1
+    return 2
+    return 3
diff --git a/tests/test_app.py b/tests/test_app.py
@@ -0,0 +1 @@
+def test_run(): pass
"""


class PatchPulseTests(unittest.TestCase):
    def test_counts_changes_and_detects_tests(self):
        pulse = analyze(SAMPLE)
        self.assertEqual((pulse.files, pulse.additions, pulse.deletions), (2, 3, 1))
        self.assertTrue(pulse.tests_touched)
        self.assertEqual(pulse.level, "low")

    def test_sensitive_file_is_high_risk(self):
        pulse = analyze("diff --git a/.env b/.env\n@@ -1 +1 @@\n-OLD=x\n+NEW=y\n")
        self.assertEqual(pulse.sensitive_files, [".env"])
        self.assertEqual(pulse.level, "high")

    def test_json_output(self):
        with patch("sys.stdin", io.StringIO(SAMPLE)):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["--json"]), 0)
        self.assertEqual(json.loads(output.getvalue())["files"], 2)


if __name__ == "__main__":
    unittest.main()
