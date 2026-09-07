"""Refresh queued SEC evidence from GitHub Actions into short-lived Upstash storage."""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime

import httpx

from warren.cache import RedisJSONStore


TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
QUEUE_KEY = "ask-warren:v1:sec-relay:queue"
TTL_SECONDS = 6 * 60 * 60


def main() -> int:
    store = RedisJSONStore.from_env()
    if store is None:
        print("Upstash Redis credentials are not configured", file=sys.stderr)
        return 2
    symbols = sorted(set(store.smembers(QUEUE_KEY)))[:25]
    if not symbols:
        print("No SEC tickers are waiting")
        return 0

    user_agent = os.getenv("SEC_USER_AGENT", "AskWarren/0.8 drmaganti@users.noreply.github.com")
    headers = {"User-Agent": user_agent, "Accept": "application/json", "Accept-Encoding": "gzip, deflate"}
    completed = 0
    with httpx.Client(headers=headers, timeout=30, follow_redirects=True) as client:
        response = client.get(TICKER_MAP_URL)
        response.raise_for_status()
        mapping = {
            str(row.get("ticker") or "").upper(): (int(row["cik_str"]), str(row.get("title") or ""))
            for row in response.json().values() if row.get("ticker") and row.get("cik_str") is not None
        }
        for symbol in symbols:
            company = mapping.get(symbol)
            if company is None:
                print(f"No exact SEC mapping for {symbol}")
                store.srem(QUEUE_KEY, symbol)
                continue
            cik, sec_name = company
            try:
                submissions = client.get(SUBMISSIONS_URL.format(cik=cik))
                submissions.raise_for_status()
                facts = client.get(COMPANY_FACTS_URL.format(cik=cik))
                facts.raise_for_status()
                store.set(
                    f"ask-warren:v1:sec-relay:{symbol}:fresh",
                    {
                        "cik": cik,
                        "sec_name": sec_name,
                        "submissions": submissions.json(),
                        "company_facts": facts.json(),
                        "fetched_at": datetime.now(UTC).isoformat(),
                    },
                    TTL_SECONDS,
                )
                if store.get(f"ask-warren:v1:sec-relay:{symbol}:fresh") is None:
                    raise RuntimeError("Upstash did not confirm the relayed payload")
                store.srem(QUEUE_KEY, symbol)
                completed += 1
                print(f"Refreshed official SEC evidence for {symbol}")
            except (httpx.HTTPError, RuntimeError, ValueError, TypeError) as exc:
                print(f"SEC refresh failed for {symbol}: {type(exc).__name__}", file=sys.stderr)
    print(f"Completed {completed} of {len(symbols)} queued SEC refreshes")
    return 0 if completed == len(symbols) else 1


if __name__ == "__main__":
    raise SystemExit(main())
