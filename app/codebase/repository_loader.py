
from pathlib import Path

from app.codebase.github_client import GitHubClient


class RepositoryLoader:
    """
    Retrieves and organises eligible source files
    from a public GitHub repository.
    """

    def __init__(self, repo_url: str):
        self.client = GitHubClient(repo_url)

    def load_repository(self) -> dict:
        """Load repository metadata and eligible source files."""

        print("Connecting to GitHub repository...")

        repository = self.client.get_repository()

        print(f"Repository: {repository['full_name']}")
        print(f"Default branch: {repository['default_branch']}")

        print("\nRetrieving repository file tree...")

        file_tree = self.client.get_file_tree()

        eligible_files = [
            file_info
            for file_info in file_tree
            if self.client.should_download(file_info)
        ]

        print(f"Total files discovered: {len(file_tree)}")
        print(f"Eligible files: {len(eligible_files)}")

        downloaded_files = []
        failed_files = []

        print("\nDownloading source files...")

        for index, file_info in enumerate(eligible_files, start=1):
            path = file_info["path"]

            try:
                downloaded = self.client.download_file(file_info)

                downloaded_files.append(downloaded)

                print(
                    f"[{index}/{len(eligible_files)}] "
                    f"Downloaded: {path}"
                )

            except Exception as exc:
                failed_files.append({
                    "path": path,
                    "error": str(exc),
                })

                print(f"[{index}/{len(eligible_files)}] Failed: {path}")

        result = {
            "repository": repository,
            "total_files_discovered": len(file_tree),
            "eligible_files_count": len(eligible_files),
            "downloaded_files_count": len(downloaded_files),
            "failed_files_count": len(failed_files),
            "files": downloaded_files,
            "failed_files": failed_files,
        }

        return result
