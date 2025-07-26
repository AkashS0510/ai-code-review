import requests
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from services.code_review import ai_code_review


class GitHubPRAnalyzer:
    def __init__(
        self, repo_url: str, pr_number: int, github_token: Optional[str] = None
    ):
        self.owner, self.repo = self._parse_github_url(repo_url)
        self.pr_number = pr_number
        self.github_token = github_token
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AI-Code-Review-System",
        }

        if github_token:
            self.headers["Authorization"] = f"token {github_token}"

    def _parse_github_url(self, repo_url: str) -> Tuple[str, str]:
        parsed = urlparse(repo_url)
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) >= 2:
            return path_parts[0], path_parts[1]
        else:
            raise ValueError("Invalid GitHub repository URL")

    def _make_request(self, url: str) -> Optional[Dict]:
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"GitHub API error: {e}")

    def get_pr_details(self) -> Optional[Dict]:
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/pulls/{self.pr_number}"
        return self._make_request(url)

    def get_pr_files(self) -> List[Dict]:
        """Get the list of files changed in the PR"""
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/pulls/{self.pr_number}/files"
        files_data = self._make_request(url)
        return files_data or []

    def prepare_for_ai_review(self) -> Dict:
        """Prepare structured data for AI code review and run the analysis"""
        pr_details = self.get_pr_details()
        files = self.get_pr_files()

        # Structure the data for AI review
        review_input = {
            "pr_info": {
                "title": pr_details.get("title", ""),
                "description": pr_details.get("body", ""),
            },
            "code_changes": [],
        }

        # Process each file for AI analysis
        for file in files:
            change_data = {
                "filename": file["filename"],
                "language": (
                    file["filename"].split(".")[-1]
                    if "." in file["filename"]
                    else "unknown"
                ),
                "diff": file.get("patch", ""),
            }
            review_input["code_changes"].append(change_data)

        # Run AI code review
        try:
            ai_review_result = ai_code_review(review_input)
            review_input["ai_review"] = ai_review_result

        except Exception as e:
            print(f"AI review failed: {e}")
            review_input["ai_review"] = None

        return review_input
