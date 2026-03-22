import os
import unittest
from unittest.mock import patch

import run_digest


class ValidateEnvTests(unittest.TestCase):
    def test_dry_run_only_requires_anthropic_key(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True):
            anthropic_key, notion_key, notion_db_id = run_digest.validate_env(
                require_notion=False
            )

        self.assertEqual(anthropic_key, "test-key")
        self.assertIsNone(notion_key)
        self.assertIsNone(notion_db_id)

    def test_full_run_requires_notion_credentials(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True):
            with self.assertRaises(EnvironmentError):
                run_digest.validate_env(require_notion=True)


class RuntimePathTests(unittest.TestCase):
    def test_runtime_paths_are_repo_relative(self):
        self.assertEqual(run_digest.TMP_DIR, run_digest.PROJECT_ROOT / ".tmp")
        self.assertEqual(run_digest.LOG_FILE, run_digest.TMP_DIR / "digest.log")
        self.assertEqual(run_digest.ENV_FILE, run_digest.PROJECT_ROOT / ".env")


if __name__ == "__main__":
    unittest.main()
