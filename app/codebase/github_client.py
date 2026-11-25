from urllib.parse import quote, urlparse

import requests


class GitHubClientError(Exception):
    """Raised when a GitHub repository request fails."""


class GitHubClient:
    """
    Client for retrieving files from public GitHub repositories.

    This class only retrieves repository data.
    It does not execute or analyse downloaded source code.
    """

    API_BASE_URL = "https://api.github.com"
    RAW_BASE_URL = "https://raw.githubusercontent.com"

    MAX_FILE_SIZE = 300_000  # 300 KB per file

    ALLOWED_EXTENSIONS = {
        ".py",
        ".html",
        ".htm",
        ".js",
        ".css",
        ".md",
        ".txt",
        ".toml",
        ".ini",
        ".cfg",
        ".yml",
        ".yaml",
        ".json",
    }

    EXCLUDED_DIRECTORIES = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        "site-packages",
        "dist",
        "build",
    }

    EXCLUDED_FILENAMES = {
        ".env",
        "secrets.json",
        "credentials.json",
    }

    def __init__(self, repo_url: str):
        self.owner, self.repo = self._parse_repo_url(repo_url)

        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "User-Agent": "TestWeave",
        })

        self.repository = None
        self.default_branch = None

    @staticmethod
    def _parse_repo_url(repo_url: str) -> tuple[str, str]:
        """Extract the owner and repository name from a GitHub URL."""

        parsed = urlparse(repo_url.strip())

        if parsed.scheme != "https" or parsed.netloc.lower() not in {
            "github.com",
            "www.github.com",
        }:
            raise ValueError("Please provide a valid HTTPS GitHub repository URL.")

        parts = [part for part in parsed.path.strip("/").split("/") if part]

        if len(parts) != 2:
            raise ValueError(
                "Expected a repository URL like "
                "https://github.com/owner/repository"
            )

        owner, repo = parts
        repo = repo.removesuffix(".git")

        if not owner or not repo:
            raise ValueError("GitHub owner and repository name cannot be empty.")

        return owner, repo

    def _request_json(self, url: str) -> dict:
        """Send a GitHub API request and return its JSON response."""

        try:
            response = self.session.get(url, timeout=20)

            if response.status_code == 404:
                raise GitHubClientError(
                    "Repository or requested resource was not found. "
                    "Check that the repository is public and the URL is correct."
                )

            if response.status_code == 403:
                raise GitHubClientError(
                    "GitHub access was denied. You may have reached the API rate limit."
                )

            response.raise_for_status()
            return response.json()

        except requests.RequestException as exc:
            raise GitHubClientError(
                f"GitHub API request failed: {exc}"
            ) from exc

    def get_repository(self) -> dict:
        """Retrieve repository metadata and its default branch."""

        url = (
            f"{self.API_BASE_URL}/repos/"
            f"{self.owner}/{self.repo}"
        )

        self.repository = self._request_json(url)
        self.default_branch = self.repository.get("default_branch")

        if not self.default_branch:
            raise GitHubClientError(
                "Could not determine the repository's default branch."
            )

        return {
            "full_name": self.repository["full_name"],
            "description": self.repository.get("description"),
            "default_branch": self.default_branch,
            "private": self.repository["private"],
            "html_url": self.repository["html_url"],
        }

    def get_file_tree(self) -> list[dict]:
        """Retrieve the complete recursive repository file tree."""

        if not self.default_branch:
            self.get_repository()

        branch = quote(self.default_branch, safe="")

        url = (
            f"{self.API_BASE_URL}/repos/"
            f"{self.owner}/{self.repo}/git/trees/{branch}?recursive=1"
        )

        result = self._request_json(url)

        if result.get("truncated"):
            raise GitHubClientError(
                "GitHub returned a truncated file tree. "
                "A complete tree could not be retrieved."
            )

        return [
            {
                "path": item["path"],
                "size": item.get("size", 0),
                "sha": item.get("sha"),
                "type": item["type"],
            }
            for item in result.get("tree", [])
            if item.get("type") == "blob"
        ]

    def should_download(self, file_info: dict) -> bool:
        """Determine whether a file is suitable for source analysis."""

        path = file_info["path"]
        filename = path.rsplit("/", 1)[-1]
        parts = path.split("/")

        if filename.lower() in self.EXCLUDED_FILENAMES:
            return False

        if any(part.lower() in self.EXCLUDED_DIRECTORIES for part in parts):
            return False

        extension = (
            "." + filename.rsplit(".", 1)[-1].lower()
            if "." in filename
            else ""
        )

        if extension not in self.ALLOWED_EXTENSIONS:
            return False

        if file_info.get("size", 0) > self.MAX_FILE_SIZE:
            return False

        return True

    def download_file(self, file_info: dict) -> dict:
        """Download one eligible source file from the repository."""

        if not self.default_branch:
            self.get_repository()

        path = file_info["path"]

        if not self.should_download(file_info):
            raise ValueError(f"File is not eligible for download: {path}")

        branch = quote(self.default_branch, safe="/")
        encoded_path = quote(path, safe="/")

        raw_url = (
            f"{self.RAW_BASE_URL}/"
            f"{self.owner}/{self.repo}/{branch}/{encoded_path}"
        )

        try:
            response = self.session.get(raw_url, timeout=20)
            response.raise_for_status()

            content = response.content

            if len(content) > self.MAX_FILE_SIZE:
                raise GitHubClientError(
                    f"File exceeded the size limit during download: {path}"
                )

            try:
                if content.startswith((b"\xff\xfe", b"\xfe\xff")):
                    text_content = content.decode("utf-16")
                    encoding = "utf-16"

                elif content.startswith(b"\xef\xbb\xbf"):
                    text_content = content.decode("utf-8-sig")
                    encoding = "utf-8-sig"

                else:
                    text_content = content.decode("utf-8")
                    encoding = "utf-8"

            except UnicodeDecodeError as exc:
                raise GitHubClientError(
                    f"Unsupported or invalid text encoding: {path}"
                ) from exc

            return {
                "path": path,
                "size": len(content),
                "content": text_content,
            }

        except requests.RequestException as exc:
            raise GitHubClientError(
                f"Could not download {path}: {exc}"
            ) from exc