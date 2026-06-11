#!/usr/bin/env python3
"""Entry point for GitHub Actions nightly scrape."""
from scheduler import run_nightly_scrape

if __name__ == "__main__":
    result = run_nightly_scrape()
    print("Result:", result)
    for source, info in result.items():
        if info.get("error"):
            print(f"ERROR in {source}: {info['error'][:200]}")
