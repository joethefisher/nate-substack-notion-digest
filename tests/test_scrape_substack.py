import unittest

from tools.scrape_substack import parse_articles_from_scrape

SUBSTACK_URL = "https://natesnewsletter.substack.com/"


class ParseArticlesFromScrapeTests(unittest.TestCase):
    def test_relative_links_are_resolved_and_external_links_are_ignored(self):
        scrape_data = {
            "links": [
                {"href": "/p/test-post", "text": "Test Post"},
                {"href": "https://evil.example.com/p/not-ours", "text": "External"},
                {"href": "https://natesnewsletter.substack.com/about", "text": "About"},
            ]
        }

        articles = parse_articles_from_scrape(scrape_data, SUBSTACK_URL)

        self.assertEqual(
            articles,
            [
                {
                    "url": "https://natesnewsletter.substack.com/p/test-post",
                    "title": "Test Post",
                    "slug": "test-post",
                }
            ],
        )

    def test_markdown_fallback_only_keeps_same_domain_posts(self):
        scrape_data = {
            "links": [],
            "markdown": (
                "Bad link https://evil.example.com/p/not-ours\n"
                "Good link https://natesnewsletter.substack.com/p/real-post"
            ),
        }

        articles = parse_articles_from_scrape(scrape_data, SUBSTACK_URL)

        self.assertEqual(
            articles,
            [
                {
                    "url": "https://natesnewsletter.substack.com/p/real-post",
                    "title": "Real Post",
                    "slug": "real-post",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
