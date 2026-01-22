#!/usr/bin/env python3
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
        '--in_url',
        type=str,
        help='Input URL to fetch HTML from.',
    )
    input_group.add_argument(
        '--in_html',
        type=Path,
        help='Path to an input HTML file.',
    )

    parser.add_argument(
        '--out_markdown',
        type=Path,
        required=True,
        help='Path to write output Markdown.',
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
        default='gfm',
        help='Pandoc output format. Default: gfm.',
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


def ensure_parent_dir(path: Path) -> None:
    """
    Ensures the parent directory of a path exists.
    """
    parent: Path = path.parent
    parent.mkdir(parents=True, exist_ok=True)


def convert_html_to_markdown(html: str, output_format: str) -> str:
    """
    Converts HTML to Markdown using Pandoc via pypandoc.
    """
    markdown: str = ''
    markdown = pypandoc.convert_text(
        source=html,
        to=output_format,
        format='html',
    )
    return markdown


def write_text(path: Path, content: str) -> None:
    """
    Writes text content to a file.
    """
    ensure_parent_dir(path)
    path.write_text(content, encoding='utf-8')


def run(args: argparse.Namespace) -> int:
    """
    Runs the conversion workflow.
    """
    exit_code: int = 0

    try:
        html: str = ''
        if args.in_url:
            html = fetch_html(url=args.in_url, timeout_seconds=float(args.timeout_seconds))
        else:
            in_path: Path = Path(args.in_html)
            if not in_path.exists():
                raise FileNotFoundError(f'Input HTML file does not exist: {in_path}')
            html = read_html_file(in_path)

        markdown: str = convert_html_to_markdown(html=html, output_format=str(args.output_format))
        write_text(path=Path(args.out_markdown), content=markdown)

        LOGGER.info('Wrote Markdown to %s', Path(args.out_markdown))
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
