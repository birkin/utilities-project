# /// script
# requires-python = "==3.12.*"
# dependencies = [
#   "playwright",
# ]
# ///


"""
Detects non-loaded images on a page with Playwright <https://github.com/microsoft/playwright>.

Usage:

  (`uvx`, used in the first-time-ever usage-examples, is auto installed when `uv` is installed.
   It creates an ephemeral venv on-the-fly.)

  first time ever:
    uvx --from playwright playwright install && uv run ./check_for_broken_images.py --url https://example.com

  linux first time ever might require:
    uvx --from playwright playwright install --with-deps && uv run ./check_for_broken_images.py --url https://example.com

  ongoing usage:
    uv run check_for_broken_images.py --url https://example.com
"""

import argparse
import json
import sys
import time
from typing import Any, TypedDict

from playwright.sync_api import ElementHandle, Page, Response, sync_playwright


## scrolls page to trigger lazy loading
def _scroll_page(page: Page, max_scrolls: int = 8, pause_s: float = 0.3) -> None:
    """Scrolls down in steps to trigger lazy-loading."""
    for _ in range(max_scrolls):
        page.evaluate('window.scrollBy(0, Math.floor(window.innerHeight * 0.9));')
        page.wait_for_timeout(int(pause_s * 1000))


class NaturalSize(TypedDict):
    """Represents the natural size of an image."""

    w: int
    h: int


class DomImgInfo(TypedDict):
    """Represents DOM-side facts for an <img> element."""

    url: str
    alt: str
    dom_ok: bool
    natural_size: NaturalSize


class NetInfo(TypedDict):
    """Represents salient network response info for an image URL."""

    status: int
    ok: bool
    content_type: str


def _absolute_img_url(page: Page, img: ElementHandle) -> str:
    """Returns absolute URL for an <img> using currentSrc/src and document.baseURI."""
    # prefer currentSrc to account for <source> in <picture>
    current_src: str | None = page.evaluate('el => el.currentSrc || el.src || ""', img)
    return page.evaluate(
        '(u) => new URL(u, document.baseURI).toString()',
        current_src or '',
    )


def _collect_dom_img_info(page: Page, selector: str) -> list[DomImgInfo]:
    """Collects DOM-side facts for each <img> matching selector."""
    imgs: list[ElementHandle] = page.query_selector_all(selector)
    out: list[DomImgInfo] = []
    for img in imgs:
        ok: bool = page.evaluate('el => el.complete && el.naturalWidth > 0', img)
        width: int = page.evaluate('el => el.naturalWidth', img)
        height: int = page.evaluate('el => el.naturalHeight', img)
        alt: str = img.get_attribute('alt') or ''
        src_abs: str = _absolute_img_url(page, img)
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
    """Returns whether the content-type looks like an image."""
    return bool(ct) and ct.lower().startswith('image/')


def run(
    url: str,
    selector: str,
    timeout_s: int,
    headed: bool,
    json_out: bool,
    pause_for_human: bool,
    persist: str | None,
    engine: str,
    slow_mo_ms: int,
    wait_selector: str | None,
) -> int:
    """Runs the check, optionally pausing so a human can pass challenges, then reports."""
    exit_code: int = 0

    with sync_playwright() as p:
        # choose engine
        browser_type = {'chromium': p.chromium, 'firefox': p.firefox, 'webkit': p.webkit}[engine]

        # build a context; persistent profile only supported by Chromium
        if persist:
            if engine != 'chromium':
                raise SystemExit('--persist requires --engine chromium')
            context = browser_type.launch_persistent_context(
                persist,
                headless=not headed,
                slow_mo=slow_mo_ms if slow_mo_ms > 0 else 0,
            )
            page = context.new_page()
        else:
            browser = browser_type.launch(
                headless=not headed,
                slow_mo=slow_mo_ms if slow_mo_ms > 0 else 0,
            )
            context = browser.new_context()
            page = context.new_page()

        # capture image responses
        image_responses: dict[str, NetInfo] = {}

        def on_response(res: Response) -> None:
            try:
                rtype: str | None = res.request.resource_type
            except Exception:
                rtype = None
            if rtype == 'image':
                try:
                    url_abs: str = res.url
                    status: int = res.status
                    ok: bool = res.ok
                    ct_hdr: str | None = res.headers.get('content-type')
                    image_responses[url_abs] = {
                        'status': status,
                        'ok': ok,
                        'content_type': ct_hdr or '',
                    }
                except Exception:
                    pass

        page.on('response', on_response)

        # navigate
        page.goto(url, wait_until='domcontentloaded', timeout=timeout_s * 1000)

        # optional wait for a specific selector (eg: viewer container)
        if wait_selector:
            try:
                page.wait_for_selector(wait_selector, timeout=timeout_s * 1000)
            except Exception:
                # keep going; we will still inspect whatever loaded
                pass

        # optional human step to solve Turnstile/login
        if pause_for_human:
            if not headed:
                print('note: --pause-for-human is most useful with --headed')
            print('\n>>> Pause: solve any Cloudflare Turnstile or login prompts in the browser.')
            print('>>> When the page content is visible, press Enter here to continue...')
            try:
                input()
            except KeyboardInterrupt:
                return 2

        # give the page a chance to pull images
        try:
            page.wait_for_load_state('networkidle', timeout=2000)
        except Exception:
            pass

        _scroll_page(page, max_scrolls=10, pause_s=0.25)
        try:
            page.wait_for_load_state('networkidle', timeout=2000)
        except Exception:
            pass
        time.sleep(0.4)

        dom_imgs: list[DomImgInfo] = _collect_dom_img_info(page, selector)

        # build a verdict per image
        inspected: list[dict[str, Any]] = []
        for info in dom_imgs:
            abs_url: str = info['url']
            # best-effort match against network data (exact URL including query string)
            net: NetInfo | None = image_responses.get(abs_url)
            reasons: list[str] = []

            if not info['dom_ok']:
                reasons.append('dom-not-rendered')

            if net:
                if net['status'] >= 400:
                    reasons.append(f'http-{net["status"]}')
                if not _looks_like_image_content_type(net['content_type']):
                    reasons.append(f'bad-content-type:{net["content_type"] or "none"}')
            else:
                reasons.append('no-network-response')

            rec: dict[str, Any] = {
                'url': abs_url,
                'alt': info['alt'],
                'natural_size': info['natural_size'],
                'dom_ok': info['dom_ok'],
                'net': net or {},
                'reasons': reasons,
            }
            inspected.append(rec)

        # decide failures
        broken_hard: list[dict[str, Any]] = []
        for rec in inspected:
            reasons = rec['reasons']
            is_bad_http = any(r.startswith('http-') for r in reasons)
            is_bad_ct = any(r.startswith('bad-content-type') for r in reasons)
            is_dom_bad = 'dom-not-rendered' in reasons
            if is_bad_http or is_bad_ct or is_dom_bad:
                broken_hard.append(rec)

        # output
        if json_out:
            print(
                json.dumps(
                    {
                        'checked_url': url,
                        'selector': selector,
                        'count_dom': len(dom_imgs),
                        'broken_hard': broken_hard,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            print(f'Checked: {url}')
            print(f'Selector: {selector}')
            print(f'Total <img> elements found: {len(dom_imgs)}')
            print(f'Broken images (hard failures): {len(broken_hard)}')
            for rec in broken_hard[:10]:
                net: dict[str, Any] = rec.get('net', {})
                print(
                    f'- {rec["url"]} | dom_ok={rec["dom_ok"]} | '
                    f'status={net.get("status")} | ct={net.get("content_type")} | '
                    f'reasons={",".join(rec["reasons"])}'
                )

        # non-zero exit on failures so this can gate CI
        exit_code = 1 if broken_hard else 0

        # tidy shutdown
        try:
            context.close()
        except Exception:
            pass

    return exit_code


def parse_args() -> argparse.Namespace:
    """Parses CLI args."""
    p: argparse.ArgumentParser = argparse.ArgumentParser(
        description='Detect non-loaded images (incl. 429s) on a page with Playwright.'
    )
    p.add_argument('--url', required=True, metavar='URL', help='target page URL (required)')
    p.add_argument(
        '--selector',
        default='img',
        help='CSS selector for images to check (default: img)',
    )
    p.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='navigation timeout seconds (default: 30)',
    )
    p.add_argument(
        '--headed',
        action='store_true',
        help='run with a visible browser window',
    )
    p.add_argument(
        '--pause-for-human',
        action='store_true',
        help='after initial load, pause so a human can solve challenges, then continue',
    )
    p.add_argument(
        '--persist',
        metavar='DIR',
        help='Chromium user-data-dir to persist cookies/session (requires --engine chromium)',
    )
    p.add_argument(
        '--engine',
        choices=['chromium', 'firefox', 'webkit'],
        default='chromium',
        help='browser engine to use (default: chromium)',
    )
    p.add_argument(
        '--slow-mo',
        dest='slow_mo',
        type=int,
        default=0,
        help='milliseconds to slow down actions (default: 0)',
    )
    p.add_argument(
        '--wait-selector',
        dest='wait_selector',
        help='optional CSS selector to wait for before scanning (eg: viewer container)',
    )
    p.add_argument(
        '--json-out',
        action='store_true',
        help='emit JSON instead of human-readable text',
    )
    return p.parse_args()


if __name__ == '__main__':
    args: argparse.Namespace = parse_args()
    try:
        code: int = run(
            url=args.url,
            selector=args.selector,
            timeout_s=args.timeout,
            headed=args.headed,
            json_out=args.json_out,
            pause_for_human=args.pause_for_human,
            persist=args.persist,
            engine=args.engine,
            slow_mo_ms=args.slow_mo,
            wait_selector=args.wait_selector,
        )
        sys.exit(code)
    except KeyboardInterrupt:
        sys.exit(2)
