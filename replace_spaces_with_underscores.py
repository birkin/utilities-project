# /// script
# requires-python = "==3.12.*"
# ///

"""
Just replaces spaces with underscores; that's all!

Part of experimentation for using `uv run THE-GIST-URL`

Usage:
$ uv run https://gist.github.com/birkin/3debb7fdc9b63a3fc8eb3e4ee37091e9 --source "foo bar"
foo_bar
"""

import argparse


def main(original: str) -> None:
    ## transform, print
    result: str = original.replace(' ', '_')
    print(result)


if __name__ == '__main__':
    ## parse args
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description='replace spaces with underscores')
    parser.add_argument('--source', required=True, help='source string to process')
    args: argparse.Namespace = parser.parse_args()
    original: str = args.source
    main(original)
