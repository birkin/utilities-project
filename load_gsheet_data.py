# /// script
# requires-python = "==3.12.*"
# dependencies = [
#   "polars",
#   "httpx"
# ]
# ///

"""
Example of accessing a public google-sheet ("Anyone with the link can view")

Usage:
    $ uv run ./load_gsheet_data.py --sheet_id <sheet_id> --gid <gid>

    ...specifically:
    $ uv run ./load_gsheet_data.py --sheet_id 1qXEqjk56TDF6Zupwqsb-bFrS8G4kS8GXSVzo3-PiZlQ --gid 0

    (that's a publich gsheet with dummy data)
    
Notes...
- assumes `uv` is installed <https://docs.astral.sh/uv/>.
- no need for a venv due to the PEP-723 inline-script-metadata that `uv` can use.
- `polars` is a modern alternative to `pandas`, with a focus on speed and scalability.
- `httpx` is a modern alternative to `requests`, enabling async requests and great performance.
"""

import argparse
from io import StringIO

import httpx
import polars as pl


def load_gsheet_to_polars_df(sheet_id: str, gid: int) -> pl.DataFrame:
    """
    Loads public google sheet as polars dataframe using httpx.

    Notes...
    - Accessing the export url returns a redirect response.
    - Because `httpx`, unlike `requests`, does not follow redirects by default, we need to pass `follow_redirects=True` to the `httpx.Client` constructor.
    """
    url: str = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}'
    with httpx.Client(follow_redirects=True) as client:
        try:
            response = client.get(url)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            print(f'Failed to fetch the Google Sheet. Ensure the sheet is public and IDs are correct.\nError: {e}')
            raise
        csv_data: str = response.text
    df: pl.DataFrame = pl.read_csv(StringIO(csv_data))  # StringIO allows csv_data to be read as a file-like object
    return df


def parse_args() -> argparse.Namespace:
    """
    Parses command-line arguments for sheet_id and gid.
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description='Load a public Google Sheet as a Polars DataFrame.'
    )
    parser.add_argument('--sheet_id', required=True, type=str, help='Google Sheet ID')
    parser.add_argument('--gid', required=True, type=int, help='Worksheet/tab gid')
    return parser.parse_args()


if __name__ == '__main__':
    args: argparse.Namespace = parse_args()
    df: pl.DataFrame = load_gsheet_to_polars_df(args.sheet_id, args.gid)
    head_output: pl.DataFrame = df.head()  # yes, the head method returns a dataframe
    print(head_output)
