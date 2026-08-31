"""A minimal GitLab REST API (v4) client covering what PR Sentinel needs:
reading a merge request's diff and posting or updating a review note,
including inline discussions on specific lines.

Like the GitHub client, this intentionally avoids pulling in python-gitlab
or any other SDK. It is a handful of requests calls.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import requests

DEFAULT_SERVER_URL = "https://gitlab.com"


class GitLabClientError(Exception):
    pass


@dataclass
class MergeRequestContext:
    server_url: str
    project_id: str
    mr_iid: str


class GitLabClient:
    def __init__(self, token: str, server_url: str = DEFAULT_SERVER_URL):
        self.token = token
        self.server_url = server_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"PRIVATE-TOKEN": token})

    @property
    def api_root(self) -> str:
        return f"{self.server_url}/api/v4"

    @classmethod
    def from_ci_environment(cls) -> tuple["GitLabClient", MergeRequestContext]:
        """Builds a client and merge request context from the predefined
        environment variables GitLab CI provides automatically inside a
        merge request pipeline.
        """

        token = os.environ.get("GITLAB_TOKEN")
        if not token:
            raise GitLabClientError(
                "GITLAB_TOKEN is not set. Create a project or personal "
                "access token with 'api' scope and pass it as a masked CI "
                "variable named GITLAB_TOKEN."
            )

        project_id = os.environ.get("CI_PROJECT_ID")
        mr_iid = os.environ.get("CI_MERGE_REQUEST_IID")
        server_url = os.environ.get("CI_SERVER_URL", DEFAULT_SERVER_URL)

        if not project_id or not mr_iid:
            raise GitLabClientError(
                "CI_PROJECT_ID or CI_MERGE_REQUEST_IID is missing. This "
                "command must run inside a GitLab CI merge request "
                "pipeline (rules: - if: '$CI_PIPELINE_SOURCE == "
                "\"merge_request_event\"')."
            )

        context = MergeRequestContext(
            server_url=server_url, project_id=project_id, mr_iid=mr_iid
        )
        return cls(token=token, server_url=server_url), context

    def get_merge_request_diff(self, ctx: MergeRequestContext) -> str:
        url = (
            f"{self.api_root}/projects/{ctx.project_id}/merge_requests/"
            f"{ctx.mr_iid}/changes"
        )
        response = self.session.get(url)
        self._raise_for_status(response, "fetch the merge request diff")
        return changes_to_unified_diff(response.json())

    def get_diff_refs(self, ctx: MergeRequestContext) -> dict:
        url = f"{self.api_root}/projects/{ctx.project_id}/merge_requests/{ctx.mr_iid}"
        response = self.session.get(url)
        self._raise_for_status(response, "fetch merge request diff refs")
        data = response.json()
        return data.get("diff_refs", {})

    def find_existing_note(
        self, ctx: MergeRequestContext, marker: str
    ) -> Optional[int]:
        url = (
            f"{self.api_root}/projects/{ctx.project_id}/merge_requests/"
            f"{ctx.mr_iid}/notes"
        )
        response = self.session.get(url, params={"per_page": 100})
        self._raise_for_status(response, "list merge request notes")
        for note in response.json():
            if marker in (note.get("body") or ""):
                return note["id"]
        return None

    def upsert_summary_note(
        self, ctx: MergeRequestContext, body: str, marker: str
    ) -> None:
        existing_id = self.find_existing_note(ctx, marker)
        base_url = (
            f"{self.api_root}/projects/{ctx.project_id}/merge_requests/"
            f"{ctx.mr_iid}/notes"
        )
        if existing_id:
            response = self.session.put(f"{base_url}/{existing_id}", json={"body": body})
            self._raise_for_status(response, "update the summary note")
        else:
            response = self.session.post(base_url, json={"body": body})
            self._raise_for_status(response, "post the summary note")

    def submit_inline_discussion(
        self,
        ctx: MergeRequestContext,
        diff_refs: dict,
        file_path: str,
        line: int,
        body: str,
    ) -> bool:
        """Posts a single line-level discussion. Returns False (instead of
        raising) on failure, since one bad line position should not abort
        an otherwise successful review.
        """

        url = (
            f"{self.api_root}/projects/{ctx.project_id}/merge_requests/"
            f"{ctx.mr_iid}/discussions"
        )
        payload = {
            "body": body,
            "position": {
                "position_type": "text",
                "base_sha": diff_refs.get("base_sha"),
                "start_sha": diff_refs.get("start_sha"),
                "head_sha": diff_refs.get("head_sha"),
                "new_path": file_path,
                "new_line": line,
            },
        }
        response = self.session.post(url, json=payload)
        return response.status_code < 400

    def _raise_for_status(self, response: requests.Response, action: str) -> None:
        if response.status_code >= 400:
            raise GitLabClientError(
                f"Failed to {action} ({response.status_code}): "
                f"{response.text[:300]}"
            )


def changes_to_unified_diff(changes_response: dict) -> str:
    """GitLab's merge request 'changes' endpoint returns each file's diff
    as a bare hunk body, without the 'diff --git a/x b/x' header line our
    diff parser expects. This rebuilds a standard unified diff string so
    the same parser works for both GitHub and GitLab.
    """

    parts = []
    for change in changes_response.get("changes", []):
        old_path = change.get("old_path") or change.get("new_path")
        new_path = change.get("new_path") or change.get("old_path")
        diff_body = change.get("diff", "")

        if change.get("new_file"):
            parts.append(f"diff --git a/{old_path} b/{new_path}")
            parts.append("new file mode 100644")
        elif change.get("deleted_file"):
            parts.append(f"diff --git a/{old_path} b/{new_path}")
            parts.append("deleted file mode 100644")
        else:
            parts.append(f"diff --git a/{old_path} b/{new_path}")

        if change.get("diff"):
            parts.append(f"--- a/{old_path}")
            parts.append(f"+++ b/{new_path}")
            parts.append(diff_body)

    return "\n".join(parts)
