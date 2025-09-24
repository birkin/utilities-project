# /// script
# requires-python = "==3.12.*"
# dependencies = [
#   "playwright",
# ]
# ///


"""
Detects non-loaded images on a page with Playwright <https://github.com/microsoft/playwright>.

Usage:

  first time ever:
    uv run -m playwright install && uv run ./check_for_broken_images.py --url https://example.com

  linux first time ever might require:
    uv run -m playwright install --with-deps && uv run ./check_for_broken_images.py --url https://example.com

  ongoing usage:
    uv run check_for_broken_images.py --url https://example.com
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from urllib.parse import urlparse

from playwright.sync_api import Page, Response, sync_playwright


def _scroll_page(page: Page, max_scrolls: int = 8, pause_s: float = 0.3) -> None:
    """Scrolls down in steps to trigger lazy-loading."""
    for _ in range(max_scrolls):
        page.evaluate('window.scrollBy(0, Math.ceil(window.innerHeight*0.9));')
        time.sleep(pause_s)


def _absolute_img_url(page: Page, img_handle) -> str:
    """Returns an absolute URL for an <img> (prefers currentSrc)."""
    return page.evaluate(
        """
        (img) => {
          const u = img.currentSrc || img.getAttribute('src') || '';
          try { return new URL(u, document.baseURI).href; } catch { return u; }
        }
        """,
        img_handle,
    )


def _collect_dom_img_info(page: Page, selector: str) -> list[dict]:
    """Collects DOM-side facts for each <img> matching selector."""
    imgs = page.query_selector_all(selector)
    out: list[dict] = []
    for img in imgs:
        ok: bool = page.evaluate('el => el.complete && el.naturalWidth > 0', img)
        width: int = page.evaluate('el => el.naturalWidth', img)
        height: int = page.evaluate('el => el.naturalHeight', img)
        alt = img.get_attribute('alt') or ''
        src_abs = _absolute_img_url(page, img)
        out.append(
            {
                'url': src_abs,
                'alt': alt,
                'dom_ok': ok,
                'natural_size': {'w': width, 'h': height},
            }
        )
    return out


def _looks_like_image_content_type(ct: str | None) -> bool:
    return bool(ct) and ct.lower().startswith('image/')


def run(url: str, selector: str, timeout_s: int, headed: bool, json_out: bool) -> int:
    """Main runner that prints a report and returns an exit code."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        context = browser.new_context()
        page = context.new_page()

        # store image responses as they arrive
        image_responses: dict[str, dict] = {}

        def on_response(res: Response) -> None:
            try:
                rtype = res.request.resource_type
            except Exception:
                rtype = None

            url_ = res.url
            if (rtype == 'image') or urlparse(url_).path.lower().endswith(
                ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.avif')
            ):
                headers = {k.lower(): v for k, v in res.headers.items()}
                image_responses[url_] = {
                    'status': res.status,
                    'ok': res.ok,
                    'content_type': headers.get('content-type', ''),
                }

        page.on('response', on_response)

        # navigate and give the page a chance to settle
        page.goto(url, wait_until='domcontentloaded', timeout=timeout_s * 1000)
        _scroll_page(page, max_scrolls=10, pause_s=0.25)
        # a brief idle wait helps capture late image fetches and retries
        try:
            page.wait_for_load_state('networkidle', timeout=2000)
        except Exception:
            pass
        time.sleep(0.4)

        dom_imgs = _collect_dom_img_info(page, selector)

        # build a verdict for each image
        broken: list[dict] = []
        inspected: list[dict] = []

        for info in dom_imgs:
            abs_url = info['url']
            net = image_responses.get(abs_url)
            reasons: list[str] = []

            # DOM verdict
            if not info['dom_ok']:
                reasons.append('dom-not-rendered')

            # Network verdict (if we saw a response for that URL)
            if net:
                if net['status'] >= 400:
                    reasons.append(f'http-{net["status"]}')
                if not _looks_like_image_content_type(net['content_type']):
                    reasons.append(f'bad-content-type:{net["content_type"] or "none"}')
            else:
                # could be lazy image never requested (offscreen) or CSS background
                reasons.append('no-network-response')

            rec = {
                'url': abs_url,
                'alt': info['alt'],
                'natural_size': info['natural_size'],
                'dom_ok': info['dom_ok'],
                'net': net or {},
                'reasons': reasons,
            }
            inspected.append(rec)
            # treat as broken if either DOM shows not rendered OR network shows a problem
            is_broken = ('dom-not-rendered' in reasons) or any(
                r.startswith('http-') or r.startswith('bad-content-type') for r in reasons
            )
            # also consider totally missing response suspicious if the element is in DOM
            if is_broken or ('no-network-response' in reasons):
                broken.append(rec)

        browser.close()

    # reporting
    broken_hard = [
        r
        for r in broken
        if any(k in r['reasons'] for k in ('dom-not-rendered',))
        or any(rr.startswith('http-') for rr in r['reasons'])
        or any(rr.startswith('bad-content-type') for rr in r['reasons'])
    ]
    # highlight 429s explicitly
    broken_429 = [r for r in broken_hard if r.get('net', {}).get('status') == 429]

    if json_out:
        print(
            json.dumps(
                {
                    'url': url,
                    'selector': selector,
                    'total_imgs': len(dom_imgs),
                    'broken_count': len(broken_hard),
                    'broken_429_count': len(broken_429),
                    'broken': broken_hard,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(f'Checked: {url}')
        print(f'Selector: {selector}')
        print(f'Total <img> elements found: {len(dom_imgs)}')
        print(f'Broken images (hard failures): {len(broken_hard)}')
        if broken_429:
            print(f'  …of which 429s: {len(broken_429)}')
        if broken_hard:
            print('\nExamples:')
            for rec in broken_hard[:10]:
                net = rec.get('net', {})
                print(
                    f'- {rec["url"]} | dom_ok={rec["dom_ok"]} | '
                    f'status={net.get("status")} | ct={net.get("content_type")} | '
                    f'reasons={",".join(rec["reasons"])}'
                )

    # non-zero exit on failures so this can gate CI
    return 1 if broken_hard else 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Detect non-loaded images (incl. 429s) on a page with Playwright.')
    p.add_argument('--url', required=True, metavar='URL', help='target page URL (required)')
    p.add_argument(
        '--selector',
        default='img',
        help='CSS selector for images to check (optional, default: img)',
    )
    p.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='navigation timeout seconds (optional, default: 30)',
    )
    p.add_argument(
        '--headed',
        action='store_true',
        help='run headed (visible browser) for debugging (optional)',
    )
    p.add_argument(
        '--json',
        dest='json_out',
        action='store_true',
        help='emit JSON instead of human-readable text (optional)',
    )
    return p.parse_args()


if __name__ == '__main__':
    args = parse_args()
    try:
        code = run(
            url=args.url,
            selector=args.selector,
            timeout_s=args.timeout,
            headed=args.headed,
            json_out=args.json_out,
        )
        sys.exit(code)
    except KeyboardInterrupt:
        sys.exit(2)
