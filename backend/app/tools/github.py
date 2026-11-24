from datetime import UTC, datetime, timedelta

import httpx

from app.core.config import get_settings

settings = get_settings()


async def get_recent_deploys(hours: int = 24) -> dict:
    if not settings.github_repo:
        return {"error": "GITHUB_REPO is not configured"}

    hours = max(1, min(hours, 168))
    since = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()

    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    params = {"path": settings.github_deploy_path, "since": since, "per_page": 10}
    url = f"https://api.github.com/repos/{settings.github_repo}/commits"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, headers=headers, params=params)
    except httpx.HTTPError as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}

    if response.status_code != 200:
        return {"error": f"GitHub API returned {response.status_code}", "detail": response.text[:300]}

    commits = response.json()
    return {
        "window_hours": hours,
        "count": len(commits),
        "deploys": [
            {
                "sha": commit["sha"][:7],
                "time": commit["commit"]["committer"]["date"],
                "message": commit["commit"]["message"].splitlines()[0],
                "author": commit["commit"]["author"]["name"],
            }
            for commit in commits
        ],
    }