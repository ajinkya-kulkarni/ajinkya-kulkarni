from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

API_ROOT = "https://api.github.com"
USER = os.environ["GITHUB_USER"]
TOKEN = os.environ["PROFILE_STATS_TOKEN"]


def get_json(path: str, params: dict[str, str | int] | None = None):
    query = ""
    if params:
        query = "?" + urllib.parse.urlencode(params)

    request = urllib.request.Request(
        f"{API_ROOT}{path}{query}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {TOKEN}",
            "User-Agent": "profile-stats-action",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def owned_public_repositories() -> list[dict]:
    repositories: list[dict] = []
    page = 1
    while True:
        batch = get_json(
            f"/users/{urllib.parse.quote(USER)}/repos",
            {"type": "owner", "per_page": 100, "page": page},
        )
        if not batch:
            break
        repositories.extend(repo for repo in batch if not repo["fork"])
        page += 1
    return repositories


def search_count(endpoint: str, query: str) -> int:
    result = get_json(endpoint, {"q": query, "per_page": 1})
    if result.get("incomplete_results"):
        raise RuntimeError(f"GitHub returned incomplete search results for: {query}")
    return int(result["total_count"])


def twelve_months_ago(today: date) -> date:
    try:
        return today.replace(year=today.year - 1)
    except ValueError:
        # February 29 -> February 28 in the previous year.
        return today.replace(year=today.year - 1, day=28)


def render_svg(stars: int, commits: int, pull_requests: int, issues: int) -> str:
    values = [
        ("Total stars", stars),
        ("Commits · 12 months", commits),
        ("PRs authored", pull_requests),
        ("Issues opened", issues),
    ]
    x_positions = [40, 225, 440, 625]

    cells = []
    for (label, value), x in zip(values, x_positions, strict=True):
        cells.append(
            f'<text x="{x}" y="43" class="label">{label}</text>'
            f'<text x="{x}" y="82" class="value">{value:,}</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="120" viewBox="0 0 800 120" role="img" aria-label="GitHub activity statistics">
<style>
  text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }}
  .border {{ fill: none; stroke: #d0d7de; }}
  .label {{ fill: #57606a; font-size: 14px; }}
  .value {{ fill: #1f2328; font-size: 30px; font-weight: 600; }}
  .divider {{ stroke: #d8dee4; }}
  @media (prefers-color-scheme: dark) {{
    .border {{ stroke: #30363d; }}
    .label {{ fill: #8b949e; }}
    .value {{ fill: #f0f6fc; }}
    .divider {{ stroke: #30363d; }}
  }}
</style>
<rect x="0.5" y="0.5" width="799" height="119" rx="8" class="border"/>
<line x1="200" y1="25" x2="200" y2="95" class="divider"/>
<line x1="415" y1="25" x2="415" y2="95" class="divider"/>
<line x1="600" y1="25" x2="600" y2="95" class="divider"/>
{''.join(cells)}
</svg>
'''


def main() -> None:
    repositories = owned_public_repositories()
    stars = sum(int(repo["stargazers_count"]) for repo in repositories)

    start = twelve_months_ago(date.today()).isoformat()
    commits = search_count(
        "/search/commits",
        f"author:{USER} author-date:>={start}",
    )
    pull_requests = search_count("/search/issues", f"author:{USER} is:pr")
    issues = search_count("/search/issues", f"author:{USER} is:issue")

    output = Path("assets/github-stats.svg")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_svg(stars, commits, pull_requests, issues),
        encoding="utf-8",
    )

    print(
        f"stars={stars} commits_12m={commits} "
        f"pull_requests={pull_requests} issues={issues}"
    )


if __name__ == "__main__":
    main()
