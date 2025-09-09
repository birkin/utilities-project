# /// script
# requires-python = "==3.12.*"
# ///

"""
Generates a random ID without confusing characters (e.g., 'O' and '0')

Usage:
    uv run ./random_id_maker.py  # default length is 10
    uv run ./random_id_maker.py --length 20

Uniqueness:
The results below answer the question of how many IDs of a given length one can generate,
    before the chance that the next one won't be unique (among all IDs in the batch) is less than 99.999%.
{
  "alphabet_size": 54,
  "approximation": {
    "method": "birthday_bound",
    "epsilon": 0.00001,
    "formula": "P(no collision) ≈ exp(-N^2/(2M)) ≥ 0.99999 ⇒ N ≈ sqrt(-2 M ln(0.99999))",
    "note": "Uses -ln(0.99999) ≈ 1e-5"
  },
  "results": [
    { "length": 5,  "max_ids": "95" },
    { "length": 6,  "max_ids": "704" },
    { "length": 7,  "max_ids": "5_174" },
    { "length": 8,  "max_ids": "38_026" },
    { "length": 9,  "max_ids": "279_439" },
    { "length": 10, "max_ids": "2_053_453" },
    { "length": 11, "max_ids": "15_089_740" },
    { "length": 12, "max_ids": "110_886_491" },
    { "length": 13, "max_ids": "814_845_970" },
    { "length": 14, "max_ids": "5_987_870_542" },
    { "length": 15, "max_ids": "44_001_682_423" },
    { "length": 16, "max_ids": "323_345_009_285" },
    { "length": 17, "max_ids": "2_376_090_850_877" },
    { "length": 18, "max_ids": "17_460_630_501_437" },
    { "length": 19, "max_ids": "128_308_905_947_396" },
    { "length": 20, "max_ids": "942_874_047_077_640" }
  ],
  "exact_method_note": "For exact values, solve ∏_{i=0}^{N-1}(1 - i/M) ≥ 0.99999 numerically"
}
"""

import argparse
import secrets

ALPHABET = 'abcdefghjkmnpqrstuvwxyz23456789ABCDEFGHJKMNPQRSTUVWXYZ'


def generate_id_secure(length: int = 10) -> str:
    id_secure: str = ''.join(secrets.choice(ALPHABET) for _ in range(length))
    print(id_secure)
    return id_secure


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate a random ID')
    parser.add_argument('-l', '--length', type=int, default=10, help='Length of the generated ID (default: 10)')
    args = parser.parse_args()

    generate_id_secure(args.length)
