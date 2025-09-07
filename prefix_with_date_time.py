# /// script
# requires-python = "==3.12.*"
# ///

"""
Just prefixes incoming text with date or date-time; that's all!

Usage:

$ uv run ./prefix_with_date_time.py --source "foo bar"
2025-09-06_foo_bar

Include time in the prefix by adding `--add_timestamp "true"`:
$ uv run ./prefix_with_date_time.py --source "foo bar" --add_timestamp "true"
2025-09-06T21:46:45_foo_bar
"""

import argparse
from datetime import datetime


def main(original: str, add_timestamp: str = 'false') -> None:
    ## transform, print
    date_part: str = datetime.now().strftime('%Y-%m-%d')
    if isinstance(add_timestamp, str) and add_timestamp.lower() == 'true':
        time_part: str = datetime.now().strftime('%H:%M:%S')
        prefix: str = f'{date_part}T{time_part}'
    else:
        prefix: str = date_part
    result: str = f'{prefix}_{original}'
    print(result)


if __name__ == '__main__':
    ## parse args
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description='prefix text with date or date-time')
    parser.add_argument('--source', required=True, help='source string to process')
    parser.add_argument(
        '--add_timestamp', required=False, default='false', help='if "true", append ISO time (HH:MM:SS) to the date'
    )
    args: argparse.Namespace = parser.parse_args()
    original: str = args.source
    add_timestamp: str = args.add_timestamp
    main(original, add_timestamp)
