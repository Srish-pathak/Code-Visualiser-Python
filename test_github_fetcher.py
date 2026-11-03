import unittest
from unittest.mock import patch

from github_fetcher import (
    GitHubFetchError,
    SUPPORTED_EXTENSIONS,
    parse_github_url,
)


class ParseGitHubUrlTests(unittest.TestCase):
    def test_standard_repository_url(self):
        self.assertEqual(
            parse_github_url("https://github.com/owner/repository"),
            ("owner", "repository", None),
        )

    def test_url_with_simple_branch(self):
        self.assertEqual(
            parse_github_url("https://github.com/owner/repository/tree/main"),
            ("owner", "repository", "main"),
        )

    def test_url_with_branch_containing_slashes(self):
        github_response = {"ref": "refs/heads/feature/new-ui"}
        with patch("github_fetcher._github_get", return_value=github_response):
            result = parse_github_url(
                "https://github.com/owner/repository/tree/feature/new-ui"
            )
        self.assertEqual(result, ("owner", "repository", "feature/new-ui"))

    def test_url_with_source_folder_after_branch(self):
        def github_response(url):
            if url.endswith("/feature/new-ui"):
                return {"ref": "refs/heads/feature/new-ui"}
            raise GitHubFetchError("Branch not found")

        with patch("github_fetcher._github_get", side_effect=github_response):
            result = parse_github_url(
                "https://github.com/owner/repository/tree/feature/new-ui/src"
            )
        self.assertEqual(result, ("owner", "repository", "feature/new-ui"))

    def test_invalid_github_url(self):
        with self.assertRaises(GitHubFetchError):
            parse_github_url("https://example.com/owner/repository")


class SupportedFrontendExtensionsTests(unittest.TestCase):
    def test_frontend_extensions_are_supported(self):
        expected = {
            ".js": "JavaScript",
            ".jsx": "JSX",
            ".ts": "TypeScript",
            ".tsx": "TSX",
            ".html": "HTML",
            ".css": "CSS",
            ".scss": "SCSS",
        }
        for extension, language in expected.items():
            with self.subTest(extension=extension):
                self.assertEqual(SUPPORTED_EXTENSIONS.get(extension), language)


if __name__ == "__main__":
    unittest.main()
