"""Checks a Meta Model API key with one cheap call (GET /models, 10 s timeout). Used by `make up`.

The key is read from the META_API_KEY environment variable (never from argv, which other users can see in ps) and is
never printed. Output: one line with the reason. Exit code: 0 ok, 2 key rejected, 3 no internet, 4 other problem.
"""

from __future__ import annotations

import os
import sys

import httpx

OK, REJECTED, OFFLINE, OTHER = 0, 2, 3, 4


def check_key(
    key: str, base_url: str, *, timeout: float = 10.0, transport: httpx.BaseTransport | None = None
) -> tuple[int, str]:
    if not key.strip():
        return REJECTED, "no key given"
    try:
        with httpx.Client(timeout=timeout, transport=transport) as client:
            r = client.get(f"{base_url.rstrip('/')}/models", headers={"Authorization": f"Bearer {key.strip()}"})
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
        return OFFLINE, f"no internet ({type(e).__name__})"
    except httpx.HTTPError as e:
        return OTHER, f"could not reach the Meta API ({type(e).__name__})"
    if r.status_code in (401, 403):
        return REJECTED, "key rejected"
    if r.status_code == 429:
        return OTHER, "the Meta API says too many requests; try again in a minute"
    if r.status_code >= 400:
        return OTHER, f"unexpected answer from the Meta API (HTTP {r.status_code})"
    return OK, "key accepted"


def main() -> int:
    code, reason = check_key(
        os.environ.get("META_API_KEY", ""), os.environ.get("META_BASE_URL", "https://api.meta.ai/v1")
    )
    print(reason)
    return code


if __name__ == "__main__":
    sys.exit(main())
