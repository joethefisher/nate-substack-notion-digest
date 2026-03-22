import tempfile
import unittest
from pathlib import Path

from tools.check_new_articles import (
    load_processed_state,
    mark_article_processed,
    save_processed_state,
)


class ProcessedStateTests(unittest.TestCase):
    def test_save_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "processed_articles.json"
            state = {
                "processed_urls": ["https://example.com/p/test-post"],
                "last_run": "2026-03-21T00:00:00+00:00",
                "article_count": 1,
            }

            save_processed_state(state, state_file)
            loaded_state = load_processed_state(state_file)

        self.assertEqual(loaded_state, state)

    def test_mark_article_processed_is_idempotent(self):
        original_state = {
            "processed_urls": ["https://example.com/p/test-post"],
            "last_run": None,
            "article_count": 1,
        }

        updated_state = mark_article_processed(
            "https://example.com/p/test-post", original_state
        )

        self.assertEqual(updated_state["processed_urls"], original_state["processed_urls"])
        self.assertEqual(updated_state["article_count"], 1)


if __name__ == "__main__":
    unittest.main()
