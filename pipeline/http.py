"""Polite HTTP fetching shared by the collectors."""

from __future__ import annotations

import io
import time

import requests

USER_AGENT = "Mozilla/5.0 (compatible; DeepwellCBMonitor/0.1; internal research)"
MIN_INTERVAL = 1.0  # seconds between requests to the same run
_last = 0.0
_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT


def get(url: str, retries: int = 3, timeout: float = 30) -> requests.Response:
    """GET with a pause between requests; retries network errors and 5xx only."""
    global _last
    for attempt in range(retries):
        wait = MIN_INTERVAL - (time.monotonic() - _last)
        if wait > 0:
            time.sleep(wait)
        _last = time.monotonic()
        last_try = attempt == retries - 1
        try:
            r = _session.get(url, timeout=timeout)
        except requests.RequestException:
            if last_try:
                raise
            time.sleep(2 ** attempt)
            continue
        if r.status_code >= 500 and not last_try:
            time.sleep(2 ** attempt)
            continue
        r.raise_for_status()
        return r


def get_text(url: str) -> str:
    r = get(url)
    r.encoding = r.encoding or "utf-8"
    return r.text


def pdf_text(url: str) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(get(url).content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)
