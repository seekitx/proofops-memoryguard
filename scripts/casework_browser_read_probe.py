#!/usr/bin/env python3
"""Read-only desktop/mobile public-page probe; run explicitly with Playwright installed.

No credentials or POST requests are used. This is NOT an authenticated lifecycle
E2E test. Screenshots may show only the public evidence and disconnected workbench.
"""
import argparse
import json
from pathlib import Path
from urllib.parse import urlparse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    parsed = urlparse(args.base_url)
    if (parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.scheme not in {"https", "http"}
            or (parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost"})):
        parser.error("Use HTTPS or loopback HTTP without credentials or query parameters")
    from playwright.sync_api import sync_playwright
    args.out_dir.mkdir(parents=True, exist_ok=False)
    records = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for name, viewport in (("desktop", {"width": 1440, "height": 1000}),
                                   ("mobile", {"width": 390, "height": 844})):
                context = browser.new_context(viewport=viewport)
                page = context.new_page(); errors = []
                page.on("pageerror", lambda error: errors.append(type(error).__name__))
                for endpoint in ("/casework", "/casework/evidence"):
                    response = page.goto(args.base_url.rstrip("/") + endpoint, wait_until="networkidle")
                    if endpoint.endswith("evidence"):
                        page.wait_for_function("document.getElementById('capture-state').textContent !== 'Loading evidence state…'")
                    overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth + 2")
                    record = {"viewport": name, "path": endpoint, "http_status": response.status if response else None,
                              "horizontal_overflow": overflow, "script_errors": list(errors)}
                    records.append(record)
                    page.screenshot(path=str(args.out_dir / f"{name}-{endpoint.rsplit('/', 1)[-1]}.png"), full_page=True)
                context.close()
        finally:
            browser.close()
    report = {"scope": "Public read-only pages; not private authorization or business E2E", "records": records}
    (args.out_dir / "browser-report.json").write_text(json.dumps(report, indent=2))
    return 0 if all(r["http_status"] == 200 and not r["horizontal_overflow"] and not r["script_errors"] for r in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
