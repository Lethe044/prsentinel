"""A minimal GitHub REST API client covering exactly what PR Sentinel needs:
reading the diff for a pull request, and posting or updating a review.

Deliberately does not depend on PyGithub or any other SDK. It is a handful
of requests calls, which keeps the dependency footprint small and the
behaviour easy to audit.
"""

from __future__ import annotations

import json as json_module
import os
from dataclasses import dataclass
from typing import Optional

import requests

API_ROOT = "https://api.github.com"


class GitHubClientError(Exception):
    pass


@dataclass
class PullRequestContext:
    owner: str
    repo: str
    pull_number: int
    head_sha: str


class GitHubClient:
    def __init__(self, token: str, api_root: str = API_ROOT):
        self.token = token
        self.api_root = api_root.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    @classmethod
    def from_event(cls) -> tuple["GitHubClient", PullRequestContext]:
        """Builds a client and pull request context from the standard
        environment variables a GitHub Actions workflow provides.
        """

        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise GitHubClientError(
                "GITHUB_TOKEN is not set. In a workflow, pass it as "
                "'env: {GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}}'."
            )

        repository = os.environ.get("GITHUB_REPOSITORY")
        if not repository or "/" not in repository:
            raise GitHubClientError(
                "GITHUB_REPOSITORY is not set or malformed. This must run "
                "inside a GitHub Actions job."
            )
        owner, repo = repository.split("/", 1)

        event_path = os.environ.get("GITHUB_EVENT_PATH")
        if not event_path or not os.path.exists(event_path):
            raise GitHubClientError(
                "GITHUB_EVENT_PATH is missing. This command must run in a "
                "pull_request or pull_request_target workflow."
            )

        with open(event_path, "r", encoding="utf-8") as handle:
            event = json_module.load(handle)

        pr = event.get("pull_request")
        if not pr:
            raise GitHubClientError(
                "No pull_request object found in the workflow event. Make "
                "sure the workflow trigger is pull_request or "
                "pull_request_target."
            )

        context = PullRequestContext(
            owner=owner,
            repo=repo,
            pull_number=pr["number"],
            head_sha=pr["head"]["sha"],
        )
        return cls(token=token), context

    def get_pull_diff(self, ctx: PullRequestContext) -> str:
        url = f"{self.api_root}/repos/{ctx.owner}/{ctx.repo}/pulls/{ctx.pull_number}"
        response = self.session.get(
            url, headers={"Accept": "application/vnd.github.v3.diff"}
        )
        self._raise_for_status(response, "fetch the pull request diff")
        return response.text

    def find_existing_comment(
        self, ctx: PullRequestContext, marker: str
    ) -> Optional[int]:
        url = f"{self.api_root}/repos/{ctx.owner}/{ctx.repo}/issues/{ctx.pull_number}/comments"
        response = self.session.get(url, params={"per_page": 100})
        self._raise_for_status(response, "list pull request comments")
        for comment in response.json():
            if marker in comment.get("body", ""):
                return comment["id"]
        return None

    def upsert_summary_comment(
        self, ctx: PullRequestContext, body: str, marker: str
    ) -> None:
        existing_id = self.find_existing_comment(ctx, marker)
        if existing_id:
            url = f"{self.api_root}/repos/{ctx.owner}/{ctx.repo}/issues/comments/{existing_id}"
            response = self.session.patch(url, json={"body": body})
            self._raise_for_status(response, "update the summary comment")
        else:
            url = f"{self.api_root}/repos/{ctx.owner}/{ctx.repo}/issues/{ctx.pull_number}/comments"
            response = self.session.post(url, json={"body": body})
            self._raise_for_status(response, "post the summary comment")

    def submit_review(
        self,
        ctx: PullRequestContext,
        event: str,
        body: str,
        comments: list[dict],
    ) -> None:
        url = f"{self.api_root}/repos/{ctx.owner}/{ctx.repo}/pulls/{ctx.pull_number}/reviews"
        payload = {
            "commit_id": ctx.head_sha,
            "event": event,
            "body": body,
            "comments": comments,
        }
        response = self.session.post(url, json=payload)
        if response.status_code >= 400:
            # Inline comments fail as a whole batch if even one line number
            # does not exist in the diff (for example a line outside any
            # hunk). Fall back to a plain review with no inline comments so
            # the run still succeeds and reports something useful.
            fallback_payload = {
                "commit_id": ctx.head_sha,
                "event": event,
                "body": body + "\n\n_Inline comments could not be posted; "
                "see the summary above for details._",
            }
            fallback = self.session.post(url, json=fallback_payload)
            self._raise_for_status(fallback, "submit the pull request review")

    def _raise_for_status(self, response: requests.Response, action: str) -> None:
        if response.status_code >= 400:
            raise GitHubClientError(
                f"Failed to {action} ({response.status_code}): "
                f"{response.text[:300]}"
            )
