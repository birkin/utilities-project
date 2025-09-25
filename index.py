# /// script
# requires-python = "==3.12.*"
# dependencies = [
#   "httpx"
# ]
# ///


"""
Print a sorted list of top-level .py filenames in the GitHub repo root,
excluding this file (index.py).
"""

import os

import httpx


def list_top_level_py_files_from_repo(owner: str, repo: str, token_env: str = 'GITHUB_TOKEN') -> list[str]:
    """
    Return a sorted list of top-level .py filenames from the GitHub repo root, excluding index.py.
    """
    url: str = f'https://api.github.com/repos/{owner}/{repo}/contents'
    headers: dict[str, str] = {'Accept': 'application/vnd.github+json', 'User-Agent': 'birkin-utilities-project'}
    token: str | None = os.getenv(token_env)
    if token:
        headers['Authorization'] = f'Bearer {token}'

    names: list[str] = []
    with httpx.Client(timeout=10.0, headers=headers) as client:
        resp: httpx.Response = client.get(url)
        if resp.status_code != 200:
            # Keep a single return; bubble up error context via exception
            raise RuntimeError(f'GitHub API error {resp.status_code}: {resp.text}')
        items: list[dict] = resp.json()
        exclude: set[str] = {'index.py'}
        for item in items:
            # item keys include: name, path, sha, size, url, html_url, git_url, download_url, type
            if item.get('type') == 'file':
                name: str = item.get('name', '')
                if name.endswith('.py') and name not in exclude:
                    names.append(name)
    names.sort()
    return names


def main() -> None:
    """
    Print top-level .py filenames in the GitHub repo root.
    """
    owner: str = 'birkin'
    repo: str = 'utilities-project'
    names: list[str] = list_top_level_py_files_from_repo(owner, repo)
    for name in names:
        print(name)


if __name__ == '__main__':
    main()
