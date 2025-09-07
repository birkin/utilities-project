# /// script
# requires-python = "==3.12.*"
# ///

"""
Just prefixes incoming text with date or date-time; that's all!

Usage:
$ uv run /path/to/prefix_with_date_time.py --source "foo bar"
2025-09-06_foo_bar
"""

import argparse
from datetime import datetime


def main(original: str) -> None:
    ## transform, print
    prefix: str = datetime.now().strftime('%Y-%m-%d')
    result: str = f'{prefix}_{original}'
    print(result)


if __name__ == '__main__':
    ## parse args
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description='replace spaces with underscores')
    parser.add_argument('--source', required=True, help='source string to process')
    args: argparse.Namespace = parser.parse_args()
    original: str = args.source
    main(original)
