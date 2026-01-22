# /// script
# requires-python = "==3.12.*"
# dependencies = [
#   "pypandoc-binary",
#   "httpx"
# ]
# ///
"""
Converts HTML input (URL or local file) to Markdown using Pandoc via pypandoc.
"""

import argparse
import logging
import sys
from pathlib import Path

import httpx
import pypandoc

LOGGER: logging.Logger = logging.getLogger(__name__)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """
    Parses command-line arguments.
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description='Convert HTML (URL or local file) to Markdown using Pandoc (via pypandoc).'
    )

    input_group: argparse._MutuallyExclusiveGroup = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--url',
        type=str,
        help='Input URL to fetch HTML from.',
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
        help='HTTP timeout in seconds (only applies to --in_url). Default: 30.',
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
    """
    Configures logging.
    """
    level_name: str = log_level.strip().upper()
    level: int = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )


def fetch_html(url: str, timeout_seconds: float) -> str:
    """
    Fetches HTML content from a URL.
    """
    headers: dict[str, str] = {'User-Agent': 'html-to-markdown-pypandoc/1.0'}
    timeout: httpx.Timeout = httpx.Timeout(timeout_seconds)

    html: str = ''
    with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
        response: httpx.Response = client.get(url)
        response.raise_for_status()
        html = response.text

    return html


def read_html_file(path: Path) -> str:
    """
    Reads HTML content from a local file.
    """
    html: str = ''
    try:
        html = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        raw: bytes = path.read_bytes()
        html = raw.decode('utf-8', errors='replace')

    return html


def convert_html_to_markdown(html: str, output_format: str) -> str:
    """
    Converts HTML to Markdown using Pandoc via pypandoc.
    """
    ## Drop div/span containers (keep contents), and avoid emitting raw HTML in Markdown.
    input_format: str = 'html-native_divs-native_spans'

    normalized_output_format: str = output_format
    if '+raw_html' in normalized_output_format:
        normalized_output_format = normalized_output_format.replace('+raw_html', '-raw_html')
    if 'raw_html' not in normalized_output_format:
        normalized_output_format = f'{normalized_output_format}-raw_html'

    extra_args: list[str] = ['--wrap=none']

    markdown: str = ''
    markdown = pypandoc.convert_text(
        source=html,
        to=normalized_output_format,
        format=input_format,
        extra_args=extra_args,
    )
    return markdown


def run(args: argparse.Namespace) -> int:
    """
    Runs the conversion workflow.
    """
    exit_code: int = 0

    try:
        html: str = ''
        if args.url:
            html = fetch_html(url=args.url, timeout_seconds=float(args.timeout_seconds))
        else:
            in_path: Path = Path(args.html_path)
            if not in_path.exists():
                raise FileNotFoundError(f'Input HTML file does not exist: {in_path}')
            html = read_html_file(in_path)

        markdown: str = convert_html_to_markdown(html=html, output_format=str(args.output_format))
        print(markdown)
    except httpx.HTTPError as exc:
        LOGGER.error('HTTP error: %s', exc)
        exit_code = 1
    except OSError as exc:
        ## Common case: Pandoc is missing (pypandoc may raise OSError in that case).
        LOGGER.error(
            'OS error (often means Pandoc is not installed/available): %s',
            exc,
        )
        exit_code = 1
    except Exception as exc:  # noqa: BLE001
        LOGGER.error('Unhandled error: %s', exc)
        exit_code = 1

    return exit_code


def main() -> None:
    """
    Orchestrates argument parsing and execution.
    """
    args: argparse.Namespace = parse_args(sys.argv[1:])
    configure_logging(str(args.log_level))
    exit_code: int = run(args)
    raise SystemExit(exit_code)


if __name__ == '__main__':
    main()
