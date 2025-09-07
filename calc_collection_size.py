# /// script
# requires-python = "==3.12.*"
# dependencies = [
#   "httpx"
# ]
# ///


"""
Computes total byte-size for a BDR collection.

Usage:
  uv run ./calc_collection_size.py --collection-pid bdr:bwehb8b8

Optional backfill (slower; calls Item API if size is missing in the search doc):
  uv run ./calc_collection_size.py --collection-pid bdr:bwehb8b8 --backfill-from-item

Tweak page-size if desired (API typically caps at <= 500):
  uv run ./calc_collection_size.py --collection-pid bdr:bwehb8b8 --rows 500
"""

import argparse
import logging
import math
import os
import sys
from collections.abc import Generator, Iterable
from typing import Any

import httpx

log_level_name: str = os.getenv('LOG_LEVEL', 'INFO').upper()
log_level = getattr(
    logging, log_level_name, logging.INFO
)  # maps the string name to the corresponding logging level constant; defaults to INFO
logging.basicConfig(level=log_level)
log = logging.getLogger(__name__)


SEARCH_BASE = 'https://repository.library.brown.edu/api/search/'
ITEM_BASE = 'https://repository.library.brown.edu/api/items/'


## -- secondary helper functions ------------------------------------


def human_bytes(n: int) -> str:
    """
    Formats a byte count into a human-readable string (e.g., KB, MB, GB).

    Called by `print_results()`.
    """
    if n < 1024:
        return f'{n} B'
    units = ['KB', 'MB', 'GB', 'TB', 'PB', 'EB']
    i = int(math.floor(math.log(n, 1024)))
    i = max(0, min(i, len(units)))  # clamp
    val = n / (1024 ** (i + 1))
    unit = units[i] if i < len(units) else 'EB'
    return f'{val:.2f} {unit}'


def fetch_search_page(
    client: httpx.Client,
    collection_pid: str,
    start: int,
    rows: int,
    fields: Iterable[str],
) -> dict[str, Any]:
    """
    Fetches one page of BDR Search API results for a collection.

    Called by `iter_collection_docs()` and `calculate_size()`.
    """
    params = {
        'q': f'rel_is_member_of_collection_ssim:"{collection_pid}"',
        'rows': rows,
        'start': start,
        'fl': ','.join(fields),
    }
    r = client.get(SEARCH_BASE, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_item_size(client: httpx.Client, pid: str) -> int | None:
    """
    Retrieves object size for a PID from the Item API as a fallback.

    Called by `calculate_size()`.
    """
    url = f'{ITEM_BASE}{pid}/'
    r = client.get(url, timeout=30)
    if r.status_code == 403:
        # private or not found; skip
        return None
    r.raise_for_status()
    data = r.json()
    # prefer object_size_lsi; fall back to fed_object_size_lsi
    return data.get('object_size_lsi') or data.get('fed_object_size_lsi') or None


def iter_collection_docs(
    client: httpx.Client,
    collection_pid: str,
    rows: int,
    fields: Iterable[str],
    *,
    first_page: dict[str, Any] | None = None,
) -> Generator[dict[str, Any], None, int]:
    """
    Iterates over all search docs for a collection, yielding docs across pages.

    If ``first_page`` is provided, it will be used as the first page response to
    avoid a duplicate fetch (useful when the caller already requested it to get
    ``numFound``). The generator "returns" ``num_found`` via StopIteration.value,
    but typical callers just iterate docs.
    """
    first = first_page or fetch_search_page(client, collection_pid, 0, rows, fields)
    response = first.get('response', {})
    num_found = int(response.get('numFound', 0))
    docs = response.get('docs', [])
    yield from docs
    start = rows
    while start < num_found:
        page = fetch_search_page(client, collection_pid, start, rows, fields)
        docs = page.get('response', {}).get('docs', [])
        if not docs:
            break
        yield from docs
        start += rows
    return num_found  # not used directly by caller (generator semantics)


## -- primary helper functions --------------------------------------


def print_results(collection_pid: str, results: dict[str, int]) -> None:
    """
    Prints a human-friendly summary of the collection size results.

    Called by `main()`.
    """
    print(f'Collection: {collection_pid}')
    print(f'Items found: {results["num_found"]}')
    print(f'Items with size counted: {results["counted"]}')
    if results['missing']:
        print(f'Items still missing size: {results["missing"]}')
    print(f'Total bytes: {results["total_bytes"]}')
    print(f'Human: {human_bytes(results["total_bytes"])}')


def calculate_size(
    collection_pid: str,
    rows: int,
    backfill_from_item: bool,
) -> dict[str, int]:
    """
    Calculates total bytes for a collection and returns summary stats.

    Returns a dict with keys: num_found, counted, missing, total_bytes.
    """
    fields = ['pid', 'object_size_lsi', 'fed_object_size_lsi']

    total_bytes = 0
    counted = 0
    missing = 0

    with httpx.Client(headers={'Accept': 'application/json'}) as client:
        # get first page to learn numFound for reporting
        first = fetch_search_page(client, collection_pid, 0, rows, fields)
        resp = first.get('response', {})
        num_found = int(resp.get('numFound', 0))
        
        # process all docs via iterator (avoids duplicating pagination logic)
        for d in iter_collection_docs(
            client, collection_pid, rows, fields, first_page=first
        ):
            size = d.get('object_size_lsi') or d.get('fed_object_size_lsi')
            if size is None:
                missing += 1
            else:
                total_bytes += int(size)
                counted += 1

        # optional backfill via Item API for missing sizes
        if backfill_from_item and missing:
            # re-scan via search and backfill sizes from Item API for those still missing
            for d in iter_collection_docs(
                client, collection_pid, rows, ['pid', 'object_size_lsi', 'fed_object_size_lsi']
            ):
                if (d.get('object_size_lsi') or d.get('fed_object_size_lsi')) is None:
                    pid = d.get('pid')
                    if not pid:
                        continue
                    sz = fetch_item_size(client, pid)
                    if sz is not None:
                        total_bytes += int(sz)
                        counted += 1
                        missing -= 1

    return {
        'num_found': num_found,
        'counted': counted,
        'missing': missing,
        'total_bytes': total_bytes,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """
    Parses command-line arguments for collection PID, rows, and backfill flag.

    Called by `main()`.
    """
    parser = argparse.ArgumentParser(description='Sum total bytes for a BDR collection.')
    parser.add_argument('--collection-pid', type=str, required=True, help='e.g., bdr:bwehb8b8')
    parser.add_argument('--rows', type=int, default=500, help='page size (max usually 500)')
    parser.add_argument('--backfill-from-item', action='store_true', help='call Item API when size missing')
    return parser.parse_args(argv)


def main() -> int:
    """
    Main controller function.

    Called by dundermain.
    """
    ## parse args ---------------------------------------------------
    args = parse_args()
    ## calculate size -----------------------------------------------
    collection_pid: str = args.collection_pid
    rows: int = args.rows
    backfill_from_item: bool = args.backfill_from_item
    ## output results -----------------------------------------------
    results = calculate_size(collection_pid, rows, backfill_from_item)
    print_results(collection_pid, results)
    return 0


if __name__ == '__main__':
    sys.exit(main())
