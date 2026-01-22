# /// script
# requires-python = "==3.12.*"
# dependencies = [
#   "pypandoc-binary",
#   "playwright"
# ]
# ///
"""html_to_markdown.py

Converts HTML input (URL or local file) to Markdown using Pandoc via pypandoc.

For URLs, this script uses Playwright to load the page in a real browser engine
and extracts the rendered DOM (HTML after JavaScript execution).
"""

import argparse
import logging
import sys
from pathlib import Path

import pypandoc

LOGGER: logging.Logger = logging.getLogger(__name__)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parses command-line arguments."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description=(
            'Convert HTML (URL or local file) to Markdown using Pandoc (via pypandoc). '
            'For URLs, uses Playwright to capture the rendered DOM (post-JS).'
        ),
    )

    input_group: argparse._MutuallyExclusiveGroup = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--url',
        type=str,
        help='Input URL to load in Playwright and extract rendered HTML from.',
    )
    input_group.add_argument(
        '--html_path',
        type=Path,
        help='Path to an input HTML file.',
    )

    parser.add_argument(
        '--timeout_seconds',
        type=float,
        default=30.0,
        help='Playwright timeout in seconds (applies to navigation and selector waits). Default: 30.',
    )
    parser.add_argument(
        '--browser',
        type=str,
        default='chromium',
        choices=['chromium', 'firefox', 'webkit'],
        help='Playwright browser engine to use. Default: chromium.',
    )
    parser.add_argument(
        '--headed',
        action='store_true',
        help='Run the browser in headed mode (non-headless). Useful for debugging.',
    )
    parser.add_argument(
        '--wait_until',
        type=str,
        default='load',
        choices=['load', 'domcontentloaded', 'networkidle'],
        help='Navigation wait condition. Default: load.',
    )
    parser.add_argument(
        '--wait_for_selector',
        type=str,
        default=None,
        help="Optional CSS selector to wait for (often best for SPAs), e.g. 'main' or '#app .loaded'.",
    )
    parser.add_argument(
        '--extra_wait_ms',
        type=int,
        default=0,
        help='Optional extra fixed wait after navigation/selector, in milliseconds (e.g. 500). Default: 0.',
    )
    parser.add_argument(
        '--user_agent',
        type=str,
        default=None,
        help='Optional user-agent string to use for Playwright browser context.',
    )

    parser.add_argument(
        '--output_format',
        type=str,
        default='gfm-raw_html',
        help='Pandoc output format. Default: gfm-raw_html (suppresses raw HTML in output).',
    )
    parser.add_argument(
        '--log_level',
        type=str,
        default='INFO',
        help='Logging level (e.g., DEBUG, INFO, WARNING). Default: INFO.',
    )

    args: argparse.Namespace = parser.parse_args(argv)
    return args


def configure_logging(log_level: str) -> None:
    """Configures logging."""
    level_name: str = log_level.strip().upper()
    level: int = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )


def read_html_file(path: Path) -> str:
    """Reads HTML content from a local file."""
    html: str = ''
    try:
        html = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        raw: bytes = path.read_bytes()
        html = raw.decode('utf-8', errors='replace')

    return html


def fetch_html_rendered_playwright(
    url: str,
    timeout_seconds: float,
    browser_name: str,
    headed: bool,
    wait_until: str,
    wait_for_selector: str | None,
    extra_wait_ms: int,
    user_agent: str | None,
) -> tuple[str, str]:
    """Fetches rendered HTML from a URL by loading it in Playwright and extracting the DOM.

    Returns:
        (html, final_url)
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            'Playwright is not available. Install it (and browser binaries) first. '
            'Example: `uv run playwright install chromium`.'
        ) from exc

    timeout_ms: int = int(timeout_seconds * 1000)
    html: str = ''
    final_url: str = url

    try:
        with sync_playwright() as pw:
            if browser_name == 'chromium':
                browser_type = pw.chromium
            elif browser_name == 'firefox':
                browser_type = pw.firefox
            else:
                browser_type = pw.webkit

            browser = browser_type.launch(headless=not headed)
            if user_agent:
                context = browser.new_context(user_agent=user_agent)
            else:
                context = browser.new_context()

            page = context.new_page()
            page.goto(url, wait_until=wait_until, timeout=timeout_ms)

            if wait_for_selector:
                page.wait_for_selector(wait_for_selector, timeout=timeout_ms)

            if extra_wait_ms > 0:
                page.wait_for_timeout(extra_wait_ms)

            html = page.content()
            final_url = page.url

            context.close()
            browser.close()
    except Exception as exc:  # noqa: BLE001
        error_msg: str = str(exc)
        if "Executable doesn't exist" in error_msg or 'browser binary' in error_msg.lower():
            raise RuntimeError(
                f'Playwright browser binary is missing.\n'
                f'Run this once to install {browser_name}:\n'
                f'  uv run --with playwright playwright install {browser_name}'
            ) from exc
        raise

    return html, final_url


def convert_html_to_markdown(html: str, output_format: str) -> str:
    """Converts HTML to Markdown using Pandoc via pypandoc."""
    input_format: str = 'html-native_divs-native_spans'

    normalized_output_format: str = output_format
    if '+raw_html' in normalized_output_format:
        normalized_output_format = normalized_output_format.replace('+raw_html', '-raw_html')
    if 'raw_html' not in normalized_output_format:
        normalized_output_format = f'{normalized_output_format}-raw_html'

    extra_args: list[str] = ['--wrap=none']

    markdown: str = pypandoc.convert_text(
        source=html,
        to=normalized_output_format,
        format=input_format,
        extra_args=extra_args,
    )
    return markdown


def run(args: argparse.Namespace) -> int:
    """Runs the conversion workflow."""
    exit_code: int = 0

    try:
        html: str = ''
        if args.url:
            html, final_url = fetch_html_rendered_playwright(
                url=str(args.url),
                timeout_seconds=float(args.timeout_seconds),
                browser_name=str(args.browser),
                headed=bool(args.headed),
                wait_until=str(args.wait_until),
                wait_for_selector=(str(args.wait_for_selector) if args.wait_for_selector else None),
                extra_wait_ms=int(args.extra_wait_ms),
                user_agent=(str(args.user_agent) if args.user_agent else None),
            )
            LOGGER.info('Playwright final URL: %s', final_url)
        else:
            in_path: Path = Path(args.html_path)
            if not in_path.exists():
                raise FileNotFoundError(f'Input HTML file does not exist: {in_path}')
            html = read_html_file(in_path)

        markdown: str = convert_html_to_markdown(html=html, output_format=str(args.output_format))
        print(markdown)
    except OSError as exc:
        LOGGER.error('OS error (often means Pandoc is not installed/available): %s', exc)
        exit_code = 1
    except Exception as exc:  # noqa: BLE001
        LOGGER.error('Unhandled error: %s', exc)
        exit_code = 1

    return exit_code


def main() -> None:
    """Orchestrates argument parsing and execution."""
    args: argparse.Namespace = parse_args(sys.argv[1:])
    configure_logging(str(args.log_level))
    exit_code: int = run(args)
    raise SystemExit(exit_code)


if __name__ == '__main__':
    main()
